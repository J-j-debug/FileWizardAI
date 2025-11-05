import chromadb
from llama_index.core import Document, SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter
from sentence_transformers import SentenceTransformer
from unstructured.partition.auto import partition_auto
from .settings import Model
from .database import SQLiteDB
import asyncio
import logging
import hashlib
import os

logger = logging.getLogger(__name__)

# Cache the model so it's loaded only once
from sentence_transformers.cross_encoder import CrossEncoder
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

def index_documents_structured(elements, collection):
    """
    Processes and indexes document elements with a semantic chunking strategy.
    Groups titles with their subsequent narrative text.
    """
    batch_size = 32
    batch_embeddings, batch_documents, batch_metadatas, batch_ids = [], [], [], []
    chunk_index = 0

    # Group elements by file to process them sequentially
    file_elements = {}
    for el in elements:
        file_path = el.metadata.filename
        if file_path not in file_elements:
            file_elements[file_path] = []
        file_elements[file_path].append(el)

    for file_path, els in file_elements.items():
        # Sort elements by page and coordinates to ensure correct reading order
        els.sort(key=lambda el: (el.metadata.page_number or 0, el.metadata.coordinates.points[0][1] if el.metadata.coordinates else 0))

        current_chunk = ""
        current_metadata = {}
        for i, el in enumerate(els):
            # If we find a title, we start a new chunk
            if el.category == "Title":
                # If the previous chunk was not empty, index it
                if current_chunk:
                    node_id = generate_node_id(file_path, current_metadata.get('page_number', 1), current_chunk, chunk_index)
                    chunk_index += 1
                    batch_embeddings.append(model.encode(current_chunk, convert_to_tensor=False).tolist())
                    batch_documents.append(current_chunk)
                    batch_metadatas.append(standardize_metadata(current_metadata))
                    batch_ids.append(node_id)
                # Start a new chunk with the title text
                current_chunk = el.text
                current_metadata = el.metadata.to_dict()
                current_metadata['file_path'] = file_path # Ensure file_path is set
            else: # For other elements (like NarrativeText), append them to the current chunk
                current_chunk += f"\n\n{el.text}"

            # If it's the last element, make sure to index the final chunk
            if i == len(els) - 1 and current_chunk:
                node_id = generate_node_id(file_path, current_metadata.get('page_number', 1), current_chunk, chunk_index)
                chunk_index += 1
                batch_embeddings.append(model.encode(current_chunk, convert_to_tensor=False).tolist())
                batch_documents.append(current_chunk)
                batch_metadatas.append(standardize_metadata(current_metadata))
                batch_ids.append(node_id)

            # Upsert batch if it's full
            if len(batch_ids) >= batch_size:
                collection.upsert(embeddings=batch_embeddings, documents=batch_documents, metadatas=batch_metadatas, ids=batch_ids)
                batch_embeddings, batch_documents, batch_metadatas, batch_ids = [], [], [], []

    # Upsert any remaining documents
    if batch_ids:
        collection.upsert(embeddings=batch_embeddings, documents=batch_documents, metadatas=batch_metadatas, ids=batch_ids)


async def index_files_from_path(root_path: str, recursive: bool, required_exts: list, use_advanced_indexing: bool = False):
    """Loads documents from a path and indexes them into ChromaDB."""

    collection_name = "file_embeddings_unstructured" if use_advanced_indexing else "file_embeddings"
    logger.info(f"Using collection: {collection_name}")
    chroma_client = get_chroma_client()
    collection = create_collection(chroma_client, name=collection_name)

    if use_advanced_indexing:
        logger.info("Using advanced indexing with Unstructured and semantic chunking.")
        all_elements = []
        # Manually walk the directory to find files and process them
        for root, _, files in os.walk(root_path):
            for file in files:
                if any(file.endswith(ext) for ext in required_exts):
                    file_path = os.path.join(root, file)
                    try:
                        # Use partition_auto to get structured elements
                        elements = partition_auto(filename=file_path, strategy="hi_res")
                        for el in elements:
                            el.metadata.filename = file_path # Add filename to metadata
                        all_elements.extend(elements)
                        logger.info(f"Successfully parsed {len(elements)} elements from {file_path}")
                    except Exception as e:
                        logger.error(f"Failed to parse {file_path}: {e}")

        logger.info(f"Total elements parsed: {len(all_elements)}. Starting indexing.")
        index_documents_structured(all_elements, collection)

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

async def query_rag(query: str, collection, top_k: int = 5, use_reranking: bool = False):
    """
    Queries the RAG pipeline to get a structured response.
    Optionally uses a cross-encoder for re-ranking if `use_reranking` is True.
    """
    # Create an embedding for the user's query
    query_embedding = model.encode(query, convert_to_tensor=False).tolist()

    # Step 1: Initial Retrieval from ChromaDB
    # If re-ranking is enabled, fetch more documents initially (e.g., top 20)
    initial_k = 20 if use_reranking else top_k
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=initial_k,
        include=["documents", "metadatas", "distances"]
    )

    # Unify results
    query_results = results.get('documents', [[]])[0]
    metadatas = results.get('metadatas', [[]])[0]
    distances = results.get('distances', [[]])[0]

    if not query_results:
        return {
            "main_response": {"response": "No relevant documents found.", "source": None},
            "other_relevant_passages": []
        }

    # Step 2: Re-ranking with Cross-Encoder (if enabled)
    if use_reranking:
        logger.info(f"Re-ranking {len(query_results)} documents with cross-encoder...")
        # Create pairs of [query, document] for the cross-encoder
        cross_inp = [[query, doc] for doc in query_results]
        # Get scores from the model
        scores = cross_encoder.predict(cross_inp)

        # Combine documents with their new scores and original metadata
        reranked_results = []
        for i, score in enumerate(scores):
            reranked_results.append({
                "document": query_results[i],
                "metadata": metadatas[i],
                "score": score
            })

        # Sort results by the new score in descending order
        reranked_results.sort(key=lambda x: x["score"], reverse=True)
        # Keep only the top_k results after re-ranking
        unique_results = reranked_results[:top_k]
    else:
        # If not re-ranking, use the original ChromaDB results and heuristics
        combined_results = []
        for i, doc in enumerate(query_results):
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

    # Isolate the best result for the main response
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
