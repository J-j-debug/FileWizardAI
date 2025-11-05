import chromadb
from llama_index.core import Document, SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter
from sentence_transformers import SentenceTransformer, CrossEncoder
from llama_index.readers.file import UnstructuredReader
from .settings import Model
from .database import SQLiteDB
import asyncio
import logging
import hashlib
import os
from unstructured.partition.auto import partition_auto

logger = logging.getLogger(__name__)

# Cache the model so it's loaded only once
model = SentenceTransformer('all-MiniLM-L6-v2')
cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
db = SQLiteDB()

def get_chroma_client(path="chroma_db"):
    """Initializes and returns a ChromaDB client."""
    return chromadb.PersistentClient(path=path)

def create_collection(client, name="file_embeddings"):
    """Creates a new collection or gets an existing one."""
    return client.get_or_create_collection(name=name)

def generate_node_id(file_path, page_number, content, chunk_index):
    """Generates a deterministic ID for a node based on its content, source, and chunk order."""
    # Use the first 256 characters of the content to keep the hash manageable
    # while still being highly specific.
    text_snippet = content[:256]
    hash_object = hashlib.sha256(f"{file_path}-{page_number}-{text_snippet}-{chunk_index}".encode())
    return hash_object.hexdigest()

def standardize_metadata(metadata):
    """Standardizes page number metadata and ensures file_path exists."""
    page_number = metadata.get("page_number") or metadata.get("page_label", "Unknown")
    metadata["page_number"] = str(page_number) # Ensure page number is a string

    # Clean up old keys if they exist
    if "page_label" in metadata:
        del metadata["page_label"]

    if "file_path" not in metadata:
        metadata["file_path"] = "Unknown"

    return metadata

def index_documents(documents: list[Document], collection):
    """
    Processes and indexes documents in batches with standardized metadata and deterministic IDs.
    """
    splitter = SentenceSplitter(chunk_size=384, chunk_overlap=40)

    batch_size = 32
    batch_embeddings = []
    batch_documents = []
    batch_metadatas = []
    batch_ids = []
    chunk_index = 0

    for doc in documents:
        doc.metadata = standardize_metadata(doc.metadata)

        paragraphs = doc.get_content().split('\n\n')
        for paragraph in paragraphs:
            if paragraph.strip():
                paragraph_doc = Document(text=paragraph, metadata=doc.metadata)
                nodes = splitter.get_nodes_from_documents([paragraph_doc])

                for node in nodes:
                    file_path = node.metadata.get("file_path")
                    page_number = node.metadata.get("page_number")
                    content = node.get_content()

                    node_id = generate_node_id(file_path, page_number, content, chunk_index)
                    chunk_index += 1

                    batch_embeddings.append(model.encode(content, convert_to_tensor=False).tolist())
                    batch_documents.append(content)
                    batch_metadatas.append(node.metadata)
                    batch_ids.append(node_id)

                    if len(batch_ids) >= batch_size:
                        collection.upsert(
                            embeddings=batch_embeddings,
                            documents=batch_documents,
                            metadatas=batch_metadatas,
                            ids=batch_ids
                        )
                        # Reset batches
                        batch_embeddings, batch_documents, batch_metadatas, batch_ids = [], [], [], []

    # Add any remaining documents in the last batch
    if batch_ids:
        collection.upsert(
            embeddings=batch_embeddings,
            documents=batch_documents,
            metadatas=batch_metadatas,
            ids=batch_ids
        )

def index_documents_unstructured(elements, collection):
    """
    Processes elements from Unstructured partition_auto, groups them into semantic chunks,
    and indexes them into ChromaDB.
    """
    batch_size = 32
    batch_embeddings = []
    batch_documents = []
    batch_metadatas = []
    batch_ids = []
    chunk_index = 0

    current_chunk_text = []
    current_chunk_elements = []
    current_chunk_text_length = 0
    # A sensible max length to avoid overly large chunks that might lose focus.
    # This is character length, not token length.
    max_chunk_length = 1500

    def process_chunk():
        nonlocal chunk_index, batch_embeddings, batch_documents, batch_metadatas, batch_ids
        if not current_chunk_elements:
            return

        combined_text = "\n\n".join(current_chunk_text)

        first_element = current_chunk_elements[0]
        metadata = standardize_metadata(first_element.metadata.to_dict())

        file_path = metadata.get("file_path", "Unknown")
        page_number = metadata.get("page_number", "Unknown")

        node_id = generate_node_id(file_path, page_number, combined_text, chunk_index)
        chunk_index += 1

        batch_documents.append(combined_text)
        batch_metadatas.append(metadata)
        batch_ids.append(node_id)
        batch_embeddings.append(model.encode(combined_text, convert_to_tensor=False).tolist())

        if len(batch_ids) >= batch_size:
            collection.upsert(embeddings=batch_embeddings, documents=batch_documents, metadatas=batch_metadatas, ids=batch_ids)
            batch_embeddings, batch_documents, batch_metadatas, batch_ids = [], [], [], []

    for element in elements:
        element_text_length = len(element.text)

        # Titles or tables usually start a new logical block
        is_new_section_start = element.category in ["Title", "Table"]

        # Condition to split: new section starts or chunk gets too long
        if (is_new_section_start and current_chunk_elements) or \
           (current_chunk_text_length + element_text_length > max_chunk_length and current_chunk_elements):
            process_chunk()
            # Reset for the next chunk
            current_chunk_text = []
            current_chunk_elements = []
            current_chunk_text_length = 0

        current_chunk_elements.append(element)
        current_chunk_text.append(element.text)
        current_chunk_text_length += element_text_length

    # Process any remaining chunk after the loop
    process_chunk()

    # Upsert any remaining items in the last batch
    if batch_ids:
        collection.upsert(embeddings=batch_embeddings, documents=batch_documents, metadatas=batch_metadatas, ids=batch_ids)

    logger.info(f"Successfully indexed {chunk_index} semantic chunks.")


async def index_files_from_path(root_path: str, recursive: bool, required_exts: list, use_advanced_indexing: bool = False):
    """Loads documents from a path and indexes them into ChromaDB."""
    collection_name = "file_embeddings_unstructured" if use_advanced_indexing else "file_embeddings"
    logger.info(f"Using collection: {collection_name}")
    chroma_client = get_chroma_client()
    collection = create_collection(chroma_client, name=collection_name)

    if use_advanced_indexing:
        logger.info("Using advanced indexing with Unstructured partition_auto.")

        files_to_process = []
        if recursive:
            for dirpath, _, filenames in os.walk(root_path):
                for filename in filenames:
                    files_to_process.append(os.path.join(dirpath, filename))
        else:
            files_to_process = [os.path.join(root_path, f) for f in os.listdir(root_path) if os.path.isfile(os.path.join(root_path, f))]

        filtered_files = [f for f in files_to_process if any(f.endswith(ext) for ext in required_exts)]
        logger.info(f"Found {len(filtered_files)} file(s) to process with Unstructured.")

        all_elements = []
        for filename in filtered_files:
            try:
                # Use "hi_res" strategy for PDFs for better layout detection
                strategy = "hi_res" if filename.endswith(".pdf") else "auto"
                elements = partition_auto(filename=filename, strategy=strategy)
                for element in elements:
                    # Keep the original filename for display
                    element.metadata.filename = os.path.basename(filename)
                    # Add full path for unique identification and access
                    element.metadata.file_path = filename
                all_elements.extend(elements)
            except Exception as e:
                logger.error(f"Failed to process {filename} with Unstructured: {e}")

        # This new function will handle the semantic chunking and indexing
        index_documents_unstructured(all_elements, collection)

    else:
        logger.info("Using standard indexing.")
        reader = SimpleDirectoryReader(
            input_dir=root_path,
            recursive=recursive,
            required_exts=required_exts,
            errors='warn'
        )
        documents = reader.load_data()
        logger.info(f"Loaded {len(documents)} document(s) from the specified path.")
        index_documents(documents, collection)

async def query_rag(query: str, collection, top_k: int = 5):
    """
    Queries the RAG pipeline with an optional re-ranking step for the advanced collection.
    """
    query_embedding = model.encode(query, convert_to_tensor=False).tolist()

    # For re-ranking, we fetch more initial results.
    initial_results_count = top_k * 4 if collection.name == "file_embeddings_unstructured" else top_k

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=initial_results_count,
        include=["documents", "metadatas", "distances"]
    )

    documents = results.get('documents', [[]])[0]
    metadatas = results.get('metadatas', [[]])[0]
    distances = results.get('distances', [[]])[0]

    if not documents:
        return {"main_response": {"response": "No relevant documents found.", "source": None}, "other_relevant_passages": []}

    # --- Re-ranking logic for the advanced pipeline ---
    if collection.name == "file_embeddings_unstructured":
        logger.info(f"Applying CrossEncoder re-ranking to {len(documents)} results.")
        # Create pairs of [query, document] for scoring
        sentence_pairs = [[query, doc] for doc in documents]

        # Compute scores and sort
        scores = cross_encoder.predict(sentence_pairs)
        scored_results = sorted(zip(scores, documents, metadatas), key=lambda x: x[0], reverse=True)

        # Reconstruct the results list with the top re-ranked items
        unique_results = []
        seen = set()
        for score, doc, meta in scored_results:
            identifier = (meta["file_path"], doc[:50])
            if identifier not in seen:
                unique_results.append({"document": doc, "metadata": meta, "score": score})
                seen.add(identifier)
            if len(unique_results) >= top_k:
                break

    # --- Standard logic for the default pipeline ---
    else:
        combined_results = []
        for i, doc in enumerate(documents):
            combined_results.append({
                "document": doc,
                "metadata": metadatas[i],
                "distance": distances[i]
            })

        # Filter by distance margin
        best_distance = combined_results[0]["distance"]
        distance_threshold = best_distance + 0.05
        filtered_results = [res for res in combined_results if res["distance"] <= distance_threshold]

        # Deduplicate
        unique_results = []
        seen = set()
        for res in filtered_results:
            identifier = (res["metadata"]["file_path"], res["document"][:50])
            if identifier not in seen:
                unique_results.append(res)
                seen.add(identifier)

    if not unique_results:
         return {"main_response": {"response": "No relevant documents found after filtering.", "source": None}, "other_relevant_passages": []}

    best_result = unique_results[0]
    other_relevant_passages = unique_results[1:]

    # Generate the main response using only the best context
    llm = Model()
    main_response_text = await llm.generate_rag_response_api(best_result["document"], query)

    main_response = {
        "response": main_response_text,
        "source": best_result["metadata"]
    }

    # Return the new structured response
    return {
        "main_response": main_response,
        "other_relevant_passages": other_relevant_passages
    }
