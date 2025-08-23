from llama_index.core.schema import ImageDocument
import asyncio
from llama_index.core import Document, SimpleDirectoryReader
from llama_index.core.node_parser import TokenTextSplitter
import os
import logging
from pathlib import Path
import hashlib
import json

from .database import SQLiteDB
from .supabase_db import SupabaseDB
from .settings import CustomFormatter, Model, Settings
import shutil

logger = logging.getLogger()
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(CustomFormatter())
logger.addHandler(ch)

def get_db_instance():
    settings = Settings()
    if settings.DATABASE_TYPE == "sqlite":
        return SQLiteDB(settings.DATABASE_URL)
    elif settings.DATABASE_TYPE == "supabase":
        return SupabaseDB(settings.DATABASE_URL)
    else:
        raise ValueError(f"Unsupported database type: {settings.DATABASE_TYPE}")

db = get_db_instance()
model = Model(db)

DEFAULT_PROMPTS = {
    "summarize_image_prompt": """
        You will be provided with an image. Your task is to analyze the image and provide a structured JSON output with the following fields:
        - "summary": Describe this image in the most concise way possible, capturing only the essential elements and details. Aim for a very brief yet accurate summary.
        - "topic": The main topic of the image (e.g., "nature", "city", "people", "animals", "food", etc.).
        - "tags": A list of relevant keywords or tags for the image.

        It is very important that you only provide the final JSON output without any additional comments or remarks.
        The output should be a single JSON object.
        """.strip(),
    "summarize_document_prompt": """
        You will be provided with the contents of a file. Your task is to analyze the content and provide a structured JSON output with the following fields:
        - "summary": A concise but informative summary of the file's content. The purpose of the summary is to organize files, so make it as specific as possible.
        - "topic": The main topic of the file. Choose from a predefined list of topics if available, otherwise use a short, descriptive topic.
        - "tags": A list of relevant keywords or tags for the file.

        It is very important that you only provide the final JSON output without any additional comments or remarks.
        The output should be a single JSON object.
        """.strip(),
    "create_file_tree_prompt": """
        You will be provided with list of source files and a summary of their contents.
        For each file,propose a new path and filename, using a directory structure that optimally organizes the files using known conventions and best practices.
        Follow good naming conventions. Here are a few guidelines
        - Think about your files : What related files are you working with?
        - Identify metadata (for example, date, sample, experiment) : What information is needed to easily locate a specific file?
        - Abbreviate or encode metadata
        - Use versioning : Are you maintaining different versions of the same file?
        - Think about how you will search for your files : What comes first?
        - Deliberately separate metadata elements : Avoid spaces or special characters in your file names
        If the file is already named well or matches a known convention, set the destination path to the same as the source path.

        Your response must be a JSON object with the following schema, dont add any extra text except the json:
        ```json
        {
            "files": [
                {
                    "src_path": "original file path",
                    "dst_path": "new file path under proposed directory structure with proposed file name"
                }
            ]
        }
        ```
        """.strip(),
    "search_files_prompt": """
        You will be provided with list of source files and a summary of their contents:
        return the files that matches or have a similar content to this search query: {search_query}

        Your response must be a JSON object with the following schema, dont add any extra text except the json:
        ```json
        {
        "files": [
                {
                    "file": "File that matches or have a similar content to the search query"
                }
            ]
        }
        """.strip()
}

db.initialize_prompts(DEFAULT_PROMPTS)


async def summarize_document(doc: Document):
    logger.info(f"Processing file {doc.metadata['file_path']}")
    doc_hash = get_file_hash(doc.metadata['file_path'])
    if db.is_file_exist(doc.metadata['file_path'], doc_hash):
        summary_data = db.get_file_summary(doc.metadata['file_path'])
    else:
        summary_json = await model.summarize_document_api(doc.text)
        try:
            summary_data = json.loads(summary_json)
        except json.JSONDecodeError:
            summary_data = {"summary": summary_json, "topic": "unknown", "tags": "[]"}

        db.insert_file_summary(doc.metadata['file_path'], doc_hash, summary_data['summary'], summary_data['topic'], json.dumps(summary_data['tags']))

    return {
        "file_path": doc.metadata['file_path'],
        "summary": summary_data['summary'],
        "topic": summary_data.get('topic'),
        "tags": summary_data.get('tags')
    }


async def summarize_image_document(doc: ImageDocument):
    logger.info(f"Processing image {doc.image_path}")
    image_hash = get_file_hash(doc.image_path)
    if db.is_file_exist(doc.image_path, image_hash):
        summary_data = db.get_file_summary(doc.image_path)
    else:
        summary_json = await model.summarize_image_api(image_path=doc.image_path)
        try:
            summary_data = json.loads(summary_json)
        except json.JSONDecodeError:
            summary_data = {"summary": summary_json, "topic": "unknown", "tags": "[]"}

        db.insert_file_summary(doc.image_path, image_hash, summary_data['summary'], summary_data['topic'], json.dumps(summary_data['tags']))

    return {
        "file_path": doc.image_path,
        "summary": summary_data['summary'],
        "topic": summary_data.get('topic'),
        "tags": summary_data.get('tags')
    }


async def dispatch_summarize_document(doc):
    if isinstance(doc, ImageDocument):
        return await summarize_image_document(doc)
    elif isinstance(doc, Document):
        return await summarize_document(doc)
    else:
        raise ValueError("Document type not supported")


async def get_summaries(documents):
    docs_summaries = await asyncio.gather(
        *[dispatch_summarize_document(doc) for doc in documents]
    )
    return docs_summaries


async def remove_deleted_files():
    file_paths = db.get_all_files()
    deleted_file_paths = [file_path for file_path in file_paths if not os.path.exists(file_path)]
    db.delete_records(deleted_file_paths)


def load_documents(path: str, recursive: bool, required_exts: list):
    reader = SimpleDirectoryReader(
        input_dir=path,
        recursive=recursive,
        required_exts=required_exts,
        errors='ignore'
    )
    splitter = TokenTextSplitter(chunk_size=6144)
    documents = []
    for docs in reader.iter_data():
        # By default, llama index split files into multiple "documents"
        if len(docs) > 1:
            try:
                # So we first join all the document contexts, then truncate by token count
                text = splitter.split_text("\n".join([d.text for d in docs]))[0]
                documents.append(Document(text=text, metadata=docs[0].metadata))
            except Exception as e:
                logger.error(f"Error reading file {docs[0].metadata['file_path']} \n")  # , e.args)
        else:
            documents.append(docs[0])
    return documents


async def get_dir_summaries(path: str, recursive: bool, required_exts: list):
    doc_dicts = load_documents(path, recursive, required_exts)
    await remove_deleted_files()
    files_summaries = await get_summaries(doc_dicts)

    # Convert path to relative path
    for summary in files_summaries:
        summary["file_path"] = os.path.relpath(summary["file_path"], path)

    return files_summaries


async def run(directory_path: str, recursive: bool, required_exts: list):
    logger.info("Starting ...")

    summaries = await get_dir_summaries(directory_path, recursive, required_exts)
    files = await model.create_file_tree_api(summaries)

    # Recursively create dictionary from file paths
    tree = {}
    for file in files:
        parts = Path(file["dst_path"]).parts
        current = tree
        for part in parts:
            current = current.setdefault(part, {})

    return files


def update_file(root_path, item):
    src_file = root_path + "/" + item["src_path"]
    dst_file = root_path + "/" + item["dst_path"]
    dst_dir = os.path.dirname(dst_file)
    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)
    if os.path.isfile(src_file):
        shutil.move(src_file, dst_file)
        new_hash = get_file_hash(dst_file)
        db.update_file(src_file, dst_file, new_hash)


async def search_files(root_path: str, recursive: bool, required_exts: list, search_query: str):
    summaries = await get_dir_summaries(root_path, recursive, required_exts)
    files = await model.search_files_api(summaries, search_query)
    return files


def get_file_hash(file_path):
    hash_func = hashlib.new('sha256')
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            hash_func.update(chunk)
    return hash_func.hexdigest()
