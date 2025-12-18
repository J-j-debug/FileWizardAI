from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .run import run, update_file
from . import rag_utils
import os
import subprocess
import platform
import base64
import mimetypes
import asyncio
from fastapi import Response
from fastapi.responses import FileResponse
from .database import SQLiteDB
from . import run as file_operations
from pydantic import BaseModel
import json
from typing import List

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

class ComplementaryQuestion(BaseModel):
    question: str
    isYesNo: bool

class DeepAnalysisRequest(BaseModel):
    root_path: str
    recursive: bool
    required_exts: List[str]
    summary_prompt: str
    complementary_questions: List[ComplementaryQuestion]
    tags: str
    schema_name: str = None
    is_incremental: bool = False


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


from .settings import Model

@app.get("/default_prompt")
async def get_default_prompt():
    from .settings import Model
    # This is not the cleanest way, but it's safe from import errors.
    # We get the default prompt string directly from the method's defaults.
    default_prompt = Model.create_file_tree_api_chunk.__defaults__[0]
    return {"prompt": default_prompt}

@app.get("/get_files")
async def get_files(root_path: str, recursive: bool, required_exts: str, prompt: str = None, token_count: int = 6144, summary_strategy: str = 'fast'):
    if not os.path.exists(root_path):
        return HTTPException(status_code=404, detail=f"Path doesn't exist: {root_path}")
    required_exts = required_exts.split(';')
    files = await run(root_path, recursive, required_exts, prompt=prompt, token_count=token_count, summary_strategy=summary_strategy)
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
    ollama_text_models, ollama_image_models = rag_utils.get_ollama_models()

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
                "text_models": ollama_text_models,
                "image_models": ollama_image_models,
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

@app.get("/analysis_schemas")
async def get_analysis_schemas():
    schemas = db.get_analysis_schemas()
    return [{"id": s[0], "name": s[1], "schema_data": json.loads(s[2])} for s in schemas]

@app.get("/analysis_schemas/{schema_id}")
async def get_analysis_schema(schema_id: int):
    schema = db.get_analysis_schema(schema_id)
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found.")
    return {"id": schema[0], "name": schema[1], "schema_data": json.loads(schema[2])}

@app.get("/analysis_schemas/{schema_id}/results")
async def get_analysis_schema_results(schema_id: int):
    results = db.get_analysis_results(schema_id)
    if not results:
        return {"results": []}

    formatted_results = [
        {"file_path": r[0], "analysis": json.loads(r[1])} for r in results
    ]
    return {"results": formatted_results}


@app.post("/deep_analysis")
async def deep_analysis(request: DeepAnalysisRequest):
    if not os.path.exists(request.root_path):
        raise HTTPException(status_code=404, detail=f"Path doesn't exist: {request.root_path}")

    # Use the schema name provided by the user, or generate one if not provided
    schema_name = request.schema_name if request.schema_name else f"Analysis_{int(time.time())}"

    schema_data = {
        "summary_prompt": request.summary_prompt,
        "complementary_questions": [q.dict() for q in request.complementary_questions],
        "tags": request.tags
    }

    schema_id = db.get_schema_by_name(schema_name)
    if schema_id is None:
        schema_id = db.create_analysis_schema(name=schema_name, schema_data=json.dumps(schema_data))
        if schema_id is None:
             raise HTTPException(status_code=500, detail="Failed to create new analysis schema.")

    if not request.is_incremental:
        # Overwrite mode: delete previous results for this schema
        db.delete_analysis_results(schema_id)

    analysis_results = await file_operations.run_deep_analysis(
        root_path=request.root_path,
        recursive=request.recursive,
        required_exts=request.required_exts,
        schema_id=schema_id,
        schema_data=schema_data,
        is_incremental=request.is_incremental
    )

    # After analysis, fetch all results for the schema to return a complete view
    all_schema_results = db.get_analysis_results(schema_id)

    # Format the results before sending
    formatted_results = [
        {"file_path": r[0], "analysis": json.loads(r[1])} for r in all_schema_results
    ]

    return {"schema_id": schema_id, "results": formatted_results}



# --- Thesis Manager Endpoints ---
from . import thesis_logic

class ThesisProjectCreate(BaseModel):
    name: str
    description: str = ""

class ThesisStructureRequest(BaseModel):
    chapters: List[dict] # [{"title": "...", "description": "..."}]
    use_advanced_indexing: bool = True

@app.post("/thesis_projects", status_code=201)
async def create_thesis_project(project: ThesisProjectCreate):
    project_id = db.create_thesis_project(project.name, project.description)
    if project_id is None:
        raise HTTPException(status_code=409, detail=f"A project with the name '{project.name}' already exists.")
    return {"id": project_id, "name": project.name, "description": project.description}

@app.get("/thesis_projects")
async def get_thesis_projects():
    projects = db.get_thesis_projects()
    return [{"id": p[0], "name": p[1], "description": p[2], "created_at": p[3]} for p in projects]

@app.post("/thesis_projects/{project_id}/generate_structure")
async def generate_thesis_structure_endpoint(project_id: int, request: ThesisStructureRequest):
    # Verify project exists
    if not db.get_thesis_project(project_id):
        raise HTTPException(status_code=404, detail="Thesis project not found.")
        
    try:
        structure = await thesis_logic.generate_thesis_structure(
            project_id=project_id,
            chapters=request.chapters,
            use_advanced_indexing=request.use_advanced_indexing
        )
        return {"structure": structure}
    except Exception as e:
        logger.error(f"Error generating structure: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate structure: {e}")

@app.put("/thesis_projects/{project_id}/plan")
async def save_thesis_plan_endpoint(project_id: int, request: ThesisStructureRequest):
    # We reuse ThesisStructureRequest structure (chapters list)
    try:
        plan_json = json.dumps(request.chapters)
        db.save_thesis_plan(project_id, plan_json)
        return {"message": "Plan saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save plan: {e}")

@app.get("/thesis_projects/{project_id}/plan")
async def get_thesis_plan_endpoint(project_id: int):
    plan_json = db.get_thesis_plan(project_id)
    if plan_json:
        return json.loads(plan_json)
    return []

@app.get("/thesis_projects/{project_id}/structure")
async def get_thesis_structure_endpoint(project_id: int):
    structure = db.get_thesis_structure(project_id)
    if structure:
        return json.loads(structure)
    return []

class DeepSummaryRequest(BaseModel):
    file_path: str

@app.post("/deep_summary")
async def generate_deep_summary_endpoint(request: DeepSummaryRequest):
    """
    Retrieves the deep summary from DB or generates it if missing.
    """
    file_path = request.file_path
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    # Check cache first
    cached_data = db.get_deep_summary(file_path)
    if cached_data:
         # formatted dict from db
         return {"deep_summary": cached_data["deep_summary"], "intermediate_summaries": cached_data["intermediate_summaries"], "cached": True}
         
    # Generate
    try:
        # thesis_logic.summarize_file_map_reduce returns only the string summary currently
        # But it saves both to DB. safely we can re-read DB or update logic return.
        # Let's update logic return to be clean, or just re-read DB. Re-reading DB is safest for consistency.
        summary_text = await thesis_logic.summarize_file_map_reduce(file_path)
        
        # Re-fetch to get the full object (including intermediates) that was just saved
        cached_data = db.get_deep_summary(file_path)
        if cached_data:
             return {"deep_summary": cached_data["deep_summary"], "intermediate_summaries": cached_data["intermediate_summaries"], "cached": False}
        
        # Fallback
        return {"deep_summary": summary_text, "intermediate_summaries": [], "cached": False}
    except Exception as e:
        logger.error(f"Error generating deep summary for {file_path}: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {e}")
    structure_json = db.get_thesis_structure(project_id)
    if not structure_json:
        return {"structure": []}
    return {"structure": json.loads(structure_json)}

class DeepSummaryRequest(BaseModel):
    file_path: str

@app.post("/files/deep_summary")
async def generate_deep_summary_endpoint(request: DeepSummaryRequest):
    if not os.path.exists(request.file_path):
        raise HTTPException(status_code=404, detail="File not found.")
        
    try:
        summary = await thesis_logic.summarize_file_map_reduce(request.file_path)
        return {"file_path": request.file_path, "deep_summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate deep summary: {e}")

@app.get("/files/deep_summary")
async def get_deep_summary_endpoint(file_path: str):
    summary = db.get_deep_summary(file_path)
    return {"file_path": file_path, "deep_summary": summary}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, port=8000)
