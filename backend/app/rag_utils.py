import chromadb
from llama_index.core import Document, SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter
from sentence_transformers import SentenceTransformer
from llama_index.readers.file import UnstructuredReader
from .settings import Model
from .database import SQLiteDB
import asyncio
import logging
import hashlib

logger = logging.getLogger(__name__)

# Cache the model so it's loaded only once
model = SentenceTransformer('all-MiniLM-L6-v2')
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

async def index_files_from_path(root_path: str, recursive: bool, required_exts: list, use_advanced_indexing: bool = False):
    """Loads documents from a path and indexes them into ChromaDB."""

    reader = None
    if use_advanced_indexing:
        logger.info("Using advanced indexing with Unstructured.")
        unstructured_reader = UnstructuredReader()
        reader = SimpleDirectoryReader(
            input_dir=root_path,
            recursive=recursive,
            required_exts=required_exts,
            file_extractor={".pdf": unstructured_reader, ".docx": unstructured_reader},
            errors='warn'
        )
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

    collection_name = "file_embeddings_unstructured" if use_advanced_indexing else "file_embeddings"
    logger.info(f"Using collection: {collection_name}")

    chroma_client = get_chroma_client()
    collection = create_collection(chroma_client, name=collection_name)

    index_documents(documents, collection)

async def query_rag(query: str, collection, top_k: int = 5):
    """Queries the RAG pipeline to get a structured response with a main answer and other relevant passages."""
    # Create an embedding for the user's query
    query_embedding = model.encode(query, convert_to_tensor=False).tolist()

    # Query ChromaDB for the most relevant document chunks
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )

    # Unify and filter results
    query_results = results.get('documents', [[]])[0]
    metadatas = results.get('metadatas', [[]])[0]
    distances = results.get('distances', [[]])[0]

    combined_results = []
    for i, doc in enumerate(query_results):
        combined_results.append({
            "document": doc,
            "metadata": metadatas[i],
            "distance": distances[i]
        })

    if not combined_results:
        return {
            "main_response": {"response": "No relevant documents found.", "source": None},
            "other_relevant_passages": []
        }

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
