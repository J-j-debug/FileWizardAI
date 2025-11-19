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
from .settings import CustomFormatter
from .settings import Model
from . import rag_utils
import shutil

logger = logging.getLogger()
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(CustomFormatter())
logger.addHandler(ch)
db = SQLiteDB()


async def summarize_document(doc: Document):
    logger.info(f"Processing file {doc.metadata['file_path']}")
    doc_hash = get_file_hash(doc.metadata['file_path'])
    if db.is_file_exist(doc.metadata['file_path'], doc_hash):
        summary = db.get_file_summary(doc.metadata['file_path'])
    else:
        model = Model()
        summary = await model.summarize_document_api(doc.text)
        db.insert_file_summary(doc.metadata['file_path'], doc_hash, summary)
    return {
        "file_path": doc.metadata['file_path'],
        "summary": summary
    }


async def summarize_image_document(doc: ImageDocument):
    logger.info(f"Processing image {doc.image_path}")
    image_hash = get_file_hash(doc.image_path)
    if db.is_file_exist(doc.image_path, image_hash):
        summary = db.get_file_summary(doc.image_path)
    else:
        model = Model()
        summary = await model.summarize_image_api(image_path=doc.image_path)
        db.insert_file_summary(doc.image_path, image_hash, summary)
    return {
        "file_path": doc.image_path,
        "summary": summary
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


def load_documents(path: str, recursive: bool, required_exts: list, token_count: int = 6144):
    reader = SimpleDirectoryReader(
        input_dir=path,
        recursive=recursive,
        required_exts=required_exts,
        errors='ignore'
    )
    splitter = TokenTextSplitter(chunk_size=token_count)
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


async def get_dir_summaries(path: str, recursive: bool, required_exts: list, token_count: int = 6144):
    doc_dicts = load_documents(path, recursive, required_exts, token_count=token_count)

    await remove_deleted_files()
    files_summaries = await get_summaries(doc_dicts)

    # Convert path to relative path
    for summary in files_summaries:
        summary["file_path"] = os.path.relpath(summary["file_path"], path)

    return files_summaries


async def run(directory_path: str, recursive: bool, required_exts: list, prompt: str = None, token_count: int = 6144, summary_strategy: str = 'fast'):
    logger.info("Starting ...")
    logger.info(f"Summarization strategy: {summary_strategy}, Token count: {token_count}")

    summaries = await get_dir_summaries(directory_path, recursive, required_exts, token_count=token_count)
    model = Model()
    files = await model.create_file_tree_api(summaries, prompt=prompt)

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


def get_file_hash(file_path):
    hash_func = hashlib.new('sha256')
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            hash_func.update(chunk)
    return hash_func.hexdigest()

async def run_deep_analysis(root_path: str, recursive: bool, required_exts: list, schema_id: int, schema_data: dict):
    """
    Runs a deep analysis on a set of files based on a given schema.
    """
    logger.info(f"Starting deep analysis with schema ID: {schema_id}")

    # Use the robust load_documents function
    documents_to_analyze = load_documents(root_path, recursive, required_exts)

    all_results = []
    model = Model()

    for doc in documents_to_analyze:
        file_path = doc.metadata.get('file_path', 'unknown_file')
        try:
            content = doc.text

            # Prepare prompts for the LLM
            tasks = []
            # 1. Summary
            summary_full_prompt = f"{schema_data['summary_prompt']}\n\n{content}"
            tasks.append(model.generate_text_api(summary_full_prompt))

            # 2. Complementary Questions
            for q_data in schema_data['complementary_questions']:
                question_prompt = f"Répondez à la question suivante en vous basant sur le document fourni. Document: \"{content}\"\n\nQuestion: \"{q_data['question']}\""
                if q_data['isYesNo']:
                    question_prompt += " Répondez uniquement par 'Oui' ou 'Non'."
                tasks.append(model.generate_text_api(question_prompt))

            # 3. Tagging
            tags_prompt = f"Le document suivant parle-t-il des sujets suivants: {schema_data['tags']}? Pour chaque tag, indiquez 'Oui' ou 'Non'. Document: \"{content}\""
            tasks.append(model.generate_text_api(tags_prompt))

            # Execute all LLM calls in parallel
            llm_responses = await asyncio.gather(*tasks)

            # Process responses
            summary_response = llm_responses[0]
            questions_responses = llm_responses[1:-1]
            tags_response = llm_responses[-1]

            file_results = {
                "summary": summary_response,
                "questions": {},
                "tags": tags_response
            }
            for i, q_data in enumerate(schema_data['complementary_questions']):
                file_results["questions"][q_data['question']] = questions_responses[i]

            # Ensure the file exists in the summary table to satisfy the foreign key constraint.
            # We use a dummy hash and summary because this table is not the primary source for deep analysis results.
            dummy_hash = get_file_hash(file_path)
            db.insert_file_summary(file_path, dummy_hash, "")

            db.save_analysis_result(
                schema_id=schema_id,
                file_path=file_path,
                results=json.dumps(file_results)
            )
            all_results.append({"file_path": file_path, "analysis": file_results})
            logger.info(f"Successfully analyzed and saved results for {file_path}")

        except Exception as e:
            logger.error(f"Failed to analyze file {file_path}: {e}")

    return all_results
