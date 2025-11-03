import chromadb
from llama_index.core import Document, SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter
from sentence_transformers import SentenceTransformer
from llama_index.readers.file import UnstructuredReader
from .settings import Model
from .database import SQLiteDB
import asyncio
import logging

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

def index_documents(documents: list[Document], collection):
    """Our robust hybrid paragraph/sentence splitter."""
    splitter = SentenceSplitter(chunk_size=512, chunk_overlap=50)
    for doc in documents:
        paragraphs = doc.get_content().split('\n\n')
        for paragraph in paragraphs:
            if paragraph.strip():
                paragraph_doc = Document(text=paragraph, metadata=doc.metadata)
                nodes = splitter.get_nodes_from_documents([paragraph_doc])
                for node in nodes:
                    file_path = node.metadata.get("file_path", "Unknown")
                    page_number = node.metadata.get("page_label", "Unknown")
                    embedding = model.encode(node.get_content(), convert_to_tensor=False).tolist()
                    collection.add(
                        embeddings=[embedding],
                        documents=[node.get_content()],
                        metadatas=[{"file_path": file_path, "page": page_number, **node.metadata}],
                        ids=[f"{file_path}_page{page_number}_{node.node_id}"]
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

    chroma_client = get_chroma_client()
    collection = create_collection(chroma_client)

    index_documents(documents, collection)

def get_file_hash(file_path):
    """Computes the SHA256 hash of a file."""
    import hashlib
    hash_func = hashlib.new('sha256')
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            hash_func.update(chunk)
    return hash_func.hexdigest()

async def query_rag(query: str, collection):
    """Queries the RAG pipeline to get a response."""
    # Create an embedding for the user's query
    query_embedding = model.encode(query, convert_to_tensor=False).tolist()

    # Query ChromaDB for the most relevant document chunks
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=5  # Return the top 5 most relevant chunks
    )

    # Combine the query and the retrieved chunks into a prompt
    prompt = f"Question: {query}\n\n"
    prompt += "Answer the question based on the following context:\n\n"
    for doc in results['documents'][0]:
        prompt += f"- {doc}\n"

    # Use the existing Model class to call the LLM
    llm = Model()
    context_str = "\n".join([doc for doc in results['documents'][0]])
    response = await llm.generate_rag_response_api(context_str, query)

    # Return the response and the sources
    return {
        "response": response,
        "sources": results['metadatas'][0]
    }
