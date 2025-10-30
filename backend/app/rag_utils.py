import chromadb
from llama_index.core import Document, SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter
from sentence_transformers import SentenceTransformer
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
    """Indexes a list of documents into a ChromaDB collection."""
    for doc in documents:
        # The document object from llama-index now represents a single page
        file_path = doc.metadata.get("file_path", "Unknown")
        page_number = doc.metadata.get("page_label", "Unknown")

        # Pre-split the document by paragraphs
        paragraphs = doc.get_content().split('\n\n')

        splitter = SentenceSplitter(chunk_size=512, chunk_overlap=50)

        # Process each paragraph
        for paragraph in paragraphs:
            if not paragraph.strip():
                continue

            # Create a Document for the paragraph and let the splitter handle it.
            # If the paragraph is smaller than chunk_size, it's treated as one node.
            # If it's larger, it's intelligently split into sentences.
            paragraph_doc = Document(text=paragraph, metadata=doc.metadata)
            nodes = splitter.get_nodes_from_documents([paragraph_doc])

            # Index each resulting node
            for node in nodes:
                embedding = model.encode(node.get_content(), convert_to_tensor=False).tolist()
                collection.add(
                    embeddings=[embedding],
                    documents=[node.get_content()],
                    metadatas=[{"file_path": file_path, "page": page_number}],
                    ids=[f"{file_path}_page{page_number}_{node.node_id}"]
                )

async def index_files_from_path(root_path: str, recursive: bool, required_exts: list):
    """Loads documents from a path and indexes them into ChromaDB."""
    reader = SimpleDirectoryReader(
        input_dir=root_path,
        recursive=recursive,
        required_exts=required_exts,
        # Use 'warn' to see potential issues instead of ignoring them
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
