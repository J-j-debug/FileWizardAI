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
from .progress_tracker import tracker
from .settings import CustomFormatter
from .settings import Model
from . import rag_utils
from . import thesis_logic
import shutil

logger = logging.getLogger()
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(CustomFormatter())
logger.addHandler(ch)
db = SQLiteDB()


async def summarize_document(doc: Document, strategy: str = 'fast', force_refresh: bool = False):
    """
    Summarizes a document, ensuring robustness against empty files and invalid cache entries.
    Supports strategies: 'fast' (default), 'full' (vectors/map-reduce).
    """
    file_path = doc.metadata.get('file_path')
    logger.info(f"Processing file: {file_path} with strategy: {strategy}")

    # 1. Validate input document
    if not file_path:
        logger.error("Document is missing file_path in metadata.")
        return None # Or handle as an error

    doc_hash = get_file_hash(file_path)
    summary = None

    # 2. Check for existing, valid summary in the database
    # For 'full' strategy, we check deep_summary first
    # 2. Check for existing, valid summary in the database
    # For 'full' strategy, we check deep_summary first
    if strategy == 'full' and not force_refresh:
        existing_deep = db.get_deep_summary(file_path)
        if existing_deep:
            logger.info(f"Found cached deep summary for {file_path}.")
            return {"file_path": file_path, "summary": existing_deep["deep_summary"]}
            
    # For 'fast', we check the standard summary
    if strategy == 'fast' and not force_refresh and db.is_file_exist(file_path, doc_hash):
        summary = db.get_file_summary(file_path)
        if summary and summary.strip():
            logger.info(f"Found valid cached summary for {file_path}.")
            return {"file_path": file_path, "summary": summary}

    # 3. Handle unreadable or empty documents
    if not doc.text or not doc.text.strip():
        summary = "File is empty or could not be read."
        logger.warning(f"File {file_path} is empty. Using placeholder summary.")
        db.insert_file_summary(file_path, doc_hash, summary)
        return {"file_path": file_path, "summary": summary}

    # 4. Generate new summary
    try:
        model = Model()
        
        if strategy == 'full':
             # Use the map-reduce logic from thesis_logic
             # This automatically saves to deep_summary in DB
             summary = await thesis_logic.summarize_file_map_reduce(file_path)
        else:
            # Default 'fast' strategy
            summary = await model.summarize_document_api(doc.text)
            
        if summary:
            # cache it
            if strategy == 'fast':
                db.insert_file_summary(file_path, doc_hash, summary)
            # 'full' is already cached by summarize_file_map_reduce
            
            logger.info(f"Successfully generated and cached new summary for {file_path}.")
        else:
            summary = "Failed to generate summary."
            logger.error(f"LLM failed to generate summary for {file_path}.")

    except Exception as e:
        summary = f"An error occurred during summarization: {e}"
        logger.error(f"Exception during summarization for {file_path}: {e}")
        if strategy == 'fast':
             db.insert_file_summary(file_path, doc_hash, summary)

    return {"file_path": file_path, "summary": summary}


async def summarize_image_document(doc: ImageDocument, force_refresh: bool = False):
    logger.info(f"Processing image {doc.image_path}")
    image_hash = get_file_hash(doc.image_path)
    if not force_refresh and db.is_file_exist(doc.image_path, image_hash):
        summary = db.get_file_summary(doc.image_path)
    else:
        model = Model()
        summary = await model.summarize_image_api(image_path=doc.image_path)
        db.insert_file_summary(doc.image_path, image_hash, summary)
    return {
        "file_path": doc.image_path,
        "summary": summary
    }


async def dispatch_summarize_document(doc, strategy='fast', force_refresh=False):
    if isinstance(doc, ImageDocument):
        return await summarize_image_document(doc, force_refresh=force_refresh)
    elif isinstance(doc, Document):
        return await summarize_document(doc, strategy=strategy, force_refresh=force_refresh)
    else:
        raise ValueError("Document type not supported")


async def get_summaries(documents, strategy='fast', force_refresh=False):
    docs_summaries = await asyncio.gather(
        *[dispatch_summarize_document(doc, strategy=strategy, force_refresh=force_refresh) for doc in documents]
    )
    return docs_summaries


async def remove_deleted_files():
    file_paths = db.get_all_files()
    deleted_file_paths = [file_path for file_path in file_paths if not os.path.exists(file_path)]
    db.delete_records(deleted_file_paths)


def load_documents(path: str, recursive: bool, required_exts: list, token_count: int = 6144):
    # If no specific extensions are required, set to None to load all files.
    # An empty list would load no files.
    extensions_to_load = required_exts if required_exts else None
    try:
        reader = SimpleDirectoryReader(
            input_dir=path,
            recursive=recursive,
            required_exts=extensions_to_load,
            errors='ignore'
        )
        # Force initialization to check for files
        # iter_data() actually loads files, but init might raise if input_dir empty? 
        # The stack trace says __init__ calls _add_files calls raise ValueError.
    except ValueError:
        logger.warning(f"No files found in {path} with extensions {extensions_to_load}")
        return []
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


async def get_dir_summaries(path: str, recursive: bool, required_exts: list, token_count: int = 6144, strategy: str = 'fast', force_refresh: bool = False):
    tracker.update(status="Loading documents...", percent=5)
    doc_dicts = load_documents(path, recursive, required_exts, token_count=token_count)
    tracker.update(status=f"Loaded {len(doc_dicts)} documents", percent=10)

    await remove_deleted_files()
    
    # We pass the tracker to get_summaries if we want granular updates there, or we monitor it here if we refactor get_summaries.
    # actually get_summaries uses asyncio.gather, so it's all at once.
    # To get granular progress with asyncio.gather, we'd need a wrapper.
    
    tracker.update(status="Summarizing files...", percent=15, log="Starting parallel summarization...")
    files_summaries = await get_summaries(doc_dicts, strategy=strategy, force_refresh=force_refresh)
    tracker.update(status="Summarization complete", percent=50, log="All files summarized.")

    # Convert path to relative path
    for summary in files_summaries:
        summary["file_path"] = os.path.relpath(summary["file_path"], path)

    return files_summaries


from .advanced_organization import run_advanced_organization

async def run(directory_path: str, recursive: bool, required_exts: list, prompt: str = None, token_count: int = 6144, summary_strategy: str = 'fast', advanced_mode: bool = False, force_refresh: bool = False):
    logger.info("Starting ...")
    logger.info(f"Summarization strategy: {summary_strategy}, Token count: {token_count}, Advanced Mode: {advanced_mode}, Force Refresh: {force_refresh}")

    summaries = await get_dir_summaries(directory_path, recursive, required_exts, token_count=token_count, strategy=summary_strategy, force_refresh=force_refresh)
    model = Model()
    
    if advanced_mode:
        logger.info("Executing Advanced Organization (Two-Pass Taxonomy Mode)")
        tracker.update(status="Advanced Organization: Generating Taxonomy...", percent=60)
        files = await run_advanced_organization(summaries)
    else:
        # Standard "On-the-fly" organization
        tracker.update(status="Standard Organization: Generating File Tree...", percent=60)
        files = await model.create_file_tree_api(summaries, prompt=prompt)

    tracker.update(status="Finalizing...", percent=90)
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

async def run_deep_analysis(root_path: str, recursive: bool, required_exts: list, schema_id: int, schema_data: dict, is_incremental: bool = False):
    """
    Runs a deep analysis on a set of files based on a given schema.
    """
    logger.info(f"Starting deep analysis with schema ID: {schema_id}. Incremental mode: {is_incremental}")

    documents_to_analyze = load_documents(root_path, recursive, required_exts)

    if is_incremental:
        already_analyzed = db.get_analyzed_file_paths(schema_id)
        documents_to_analyze = [
            doc for doc in documents_to_analyze
            if doc.metadata.get('file_path') not in already_analyzed
        ]
        logger.info(f"Found {len(documents_to_analyze)} new file(s) to analyze in incremental mode.")

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
            # Only insert a placeholder if the file isn't already in the summary table.
            if not db.get_file_summary(file_path):
                dummy_hash = get_file_hash(file_path)
                db.insert_file_summary(file_path, dummy_hash, "") # Insert placeholder

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
