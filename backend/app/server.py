from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .run import run, update_file
from . import rag_utils
from .settings import FILE_STRUCTURE_DEFAULT_PROMPT
import os
import subprocess
import platform
import base64
import mimetypes
import asyncio
from fastapi import Response
from fastapi.responses import FileResponse
from .database import SQLiteDB
from pydantic import BaseModel
import json

# Helper for path normalization
def normalize_path(path: str) -> str:
    # Replace backslashes with forward slashes and remove any trailing slashes
    return os.path.normpath(path).replace("\\", "/")

# Pydantic models for request bodies
class NotebookCreate(BaseModel):
    name: str
    description: str = ""

class NotebookUpdate(BaseModel):
    name: str
    description: str

class NotebookFiles(BaseModel):
    file_paths: list[str]

class IndexRequest(BaseModel):
    file_paths: list[str]
    use_advanced_indexing: bool = False


app = FastAPI()
db = SQLiteDB()

@app.on_event("startup")
async def startup_event():
    # This will run in a separate thread to not block the server startup.
    asyncio.create_task(rag_utils.warm_up_unstructured())

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get('/')
def get_angular_app():
    return FileResponse("app/static/index.html")

# --- Notebooks Endpoints ---

@app.post("/notebooks", status_code=201)
async def create_notebook(notebook: NotebookCreate):
    notebook_id = db.create_notebook(notebook.name, notebook.description)
    if notebook_id is None:
        raise HTTPException(status_code=409, detail=f"A notebook with the name '{notebook.name}' already exists.")
    return {"id": notebook_id, "name": notebook.name, "description": notebook.description}

@app.get("/notebooks")
async def get_notebooks():
    notebooks = db.get_notebooks()
    return [{"id": n[0], "name": n[1], "description": n[2]} for n in notebooks]

@app.put("/notebooks/{notebook_id}")
async def update_notebook(notebook_id: int, notebook: NotebookUpdate):
    success = db.update_notebook(notebook_id, notebook.name, notebook.description)
    if not success:
        raise HTTPException(status_code=409, detail=f"A notebook with the name '{notebook.name}' already exists.")
    return {"message": "Notebook updated successfully"}

@app.delete("/notebooks/{notebook_id}")
async def delete_notebook(notebook_id: int):
    # First, delete associated ChromaDB collections
    rag_utils.delete_notebook_collections(notebook_id)
    # Then, delete the notebook from the database
    db.delete_notebook(notebook_id)
    return {"message": "Notebook and associated data deleted successfully"}

import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.post("/notebooks/{notebook_id}/files", status_code=201)
async def add_files_to_notebook(notebook_id: int, files: NotebookFiles):
    normalized_paths = [normalize_path(p) for p in files.file_paths]
    success = db.add_files_to_notebook(notebook_id, normalized_paths)
    if not success:
        raise HTTPException(status_code=400, detail="Error adding files. Ensure file paths are valid and not already in the notebook.")

    for file_path in normalized_paths:
        logger.info(f"File added to notebook {notebook_id}: {file_path}")

    return {"message": "Files added to notebook successfully"}

@app.get("/notebooks/{notebook_id}/files")
async def get_notebook_files(notebook_id: int):
    files = db.get_files_for_notebook(notebook_id)
    return {"file_paths": files}

@app.delete("/notebooks/{notebook_id}/files")
async def remove_files_from_notebook(notebook_id: int, files: NotebookFiles):
    normalized_paths = [normalize_path(p) for p in files.file_paths]
    db.remove_files_from_notebook(notebook_id, normalized_paths)
    return {"message": "Files removed from notebook successfully"}

@app.post("/notebooks/{notebook_id}/index")
async def index_notebook_files(notebook_id: int, request: IndexRequest):
    try:
        await rag_utils.index_files_for_notebook(
            notebook_id=notebook_id,
            file_paths=request.file_paths,
            use_advanced_indexing=request.use_advanced_indexing
        )
        return {"message": f"Files for notebook {notebook_id} indexed successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to index files for notebook {notebook_id}: {e}")

@app.get("/notebooks/{notebook_id}/search")
async def search_in_notebook(notebook_id: int, query: str, use_advanced_indexing: bool = False, top_k: int = 5, prompt_template: str = None):
    collection_name = rag_utils.get_notebook_collection_name(notebook_id, use_advanced_indexing)

    try:
        chroma_client = rag_utils.get_chroma_client()
        # Use get_collection to ensure it exists before querying
        collection = chroma_client.get_collection(name=collection_name)

        result = await rag_utils.query_rag(query, collection, top_k, prompt_template)
        return result
    except Exception as e:
        # Handle cases where the collection might not exist yet
        raise HTTPException(status_code=404, detail=f"Could not find collection for notebook {notebook_id}. Have you indexed any files? Error: {e}")


@app.get("/default_prompt")
async def get_default_prompt():
    return {"prompt": FILE_STRUCTURE_DEFAULT_PROMPT}


@app.get("/get_files")
async def get_files(root_path: str, recursive: bool, required_exts: str, prompt: str = None):
    if not os.path.exists(root_path):
        return HTTPException(status_code=404, detail=f"Path doesn't exist: {root_path}")
    required_exts = required_exts.split(';')
    files = await run(root_path, recursive, required_exts, prompt=prompt)
    return {
        "root_path": root_path,
        "items": files
    }


@app.post("/update_files")
async def update_files(request: Request):
    data = await request.json()
    root_path = data.get('root_path')
    items = data.get('items')
    for item in items:
        try:
            update_file(root_path, item)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error while moving file: {e}")
    return {"message": "Files moved successfully"}


@app.post("/open_file")
async def open_file(request: Request):
    data = await request.json()
    file_path = data.get('file_path')
    if not os.path.exists(file_path):
        return HTTPException(status_code=404, detail=f"File doesn't exist: {file_path}")
    current_os = platform.system()
    try:
        if current_os == "Windows":
            os.startfile(file_path)
        elif current_os == "Darwin":
            subprocess.run(["open", file_path])
        elif current_os == "Linux":
            subprocess.run(["xdg-open", file_path])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error while opening file: {e}")
    return {"message": "Files opened successfully"}


@app.get("/download")
async def download_file(encoded_path: str):
    try:
        file_path = base64.b64decode(encoded_path).decode('utf-8')
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 encoding.")

    # A more robust security check to prevent directory traversal
    # This normalizes the path and checks its components
    normalized_path = os.path.normpath(file_path)
    if not os.path.isabs(normalized_path) or ".." in normalized_path.split(os.sep):
        raise HTTPException(status_code=400, detail="Invalid or relative path specified.")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File at path: {file_path} does not exist.")

    if os.path.isdir(file_path):
        raise HTTPException(status_code=400, detail="Specified path is a directory, not a file.")

    media_type, _ = mimetypes.guess_type(file_path)
    if media_type is None:
        media_type = 'application/octet-stream'

    headers = {
        'Content-Disposition': f'inline; filename="{os.path.basename(file_path)}"'
    }

    return FileResponse(file_path, media_type=media_type, headers=headers)


@app.get("/rag_search")
async def rag_search(query: str, collection_name: str = "file_embeddings", top_k: int = 5, prompt_template: str = None):
    chroma_client = rag_utils.get_chroma_client()
    collection = rag_utils.create_collection(chroma_client, name=collection_name)
    result = await rag_utils.query_rag(query, collection, top_k, prompt_template)
    return result

@app.post("/index_files")
async def index_files(request: Request):
    data = await request.json()
    root_path = data.get('root_path')
    recursive = data.get('recursive')
    required_exts = data.get('required_exts', "")
    use_advanced_indexing = data.get('use_advanced_indexing', False)

    if not os.path.exists(root_path):
        return HTTPException(status_code=404, detail=f"Path doesn't exist: {root_path}")

    required_exts = required_exts.split(';') if required_exts else []
    await rag_utils.index_files_from_path(
        root_path=root_path,
        recursive=recursive,
        required_exts=required_exts,
        use_advanced_indexing=use_advanced_indexing
    )
    return {"message": "Files indexed successfully"}


@app.get("/llm_providers")
async def get_llm_providers():
    return {
        "providers": [
            {
                "name": "Groq",
                "text_endpoint": "https://api.groq.com/openai/v1",
                "image_endpoint": "https://api.groq.com/openai/v1",
                "text_models": ["llama3-70b-8192", "llama3-8b-8192", "mixtral-8x7b-32768"],
                "image_models": ["llava-v1.5-7b-4096-preview"],
                "api_key_prefix": "gsk_"
            },
            {
                "name": "OpenAI",
                "text_endpoint": "https://api.openai.com/v1",
                "image_endpoint": "https://api.openai.com/v1",
                "text_models": ["gpt-4o", "gpt-4", "gpt-3.5-turbo"],
                "image_models": ["gpt-4o", "gpt-4-vision-preview"],
                "api_key_prefix": "sk-"
            },
            {
                "name": "Ollama",
                "text_endpoint": "http://localhost:11434/v1",
                "image_endpoint": "http://localhost:11434/v1",
                "text_models": ["gemma2:latest", "llama3:latest", "mistral:latest"],
                "image_models": ["moondream:latest", "llava:latest"],
                "api_key_prefix": "ollama"
            },
            {
                "name": "Hugging Face",
                "text_endpoint": "https://api-inference.huggingface.co/v1",
                "image_endpoint": "https://api-inference.huggingface.co/v1",
                "text_models": ["microsoft/Phi-3-mini-4k-instruct", "mistralai/Mistral-7B-Instruct-v0.1"],
                "image_models": ["nlpconnect/vit-gpt2-image-captioning"],
                "api_key_prefix": "hf_"
            }
        ]
    }


@app.post("/llm_config")
async def update_llm_config(request: Request):
    data = await request.json()
    
    # Create .env content ensuring valid JSON for lists and quoted strings
    env_content = (
        f'TEXT_API_END_POINT="{data["text_endpoint"]}"\n'
        f'TEXT_MODEL_NAME="{data["text_model"]}"\n'
        f'TEXT_API_KEYS={json.dumps(data["text_api_keys"])}\n'
        f'\n'
        f'IMAGE_API_END_POINT="{data["image_endpoint"]}"\n'
        f'IMAGE_MODEL_NAME="{data["image_model"]}"\n'
        f'IMAGE_API_KEYS={json.dumps(data["image_api_keys"])}\n'
    )
    
    # Write to .env file
    try:
        with open('.env', 'w') as f:
            f.write(env_content)
        return {"message": "LLM configuration updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating configuration: {e}")


@app.get("/current_llm_config")
async def get_current_llm_config():
    try:
        from .settings import Settings
        settings = Settings()
        return {
            "text_endpoint": settings.TEXT_API_END_POINT,
            "text_model": settings.TEXT_MODEL_NAME,
            "text_api_keys": settings.TEXT_API_KEYS,
            "image_endpoint": settings.IMAGE_API_END_POINT,
            "image_model": settings.IMAGE_MODEL_NAME,
            "image_api_keys": settings.IMAGE_API_KEYS
        }
    except Exception as e:
        return {
            "text_endpoint": "",
            "text_model": "",
            "text_api_keys": [],
            "image_endpoint": "",
            "image_model": "",
            "image_api_keys": []
        }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, port=8000)
