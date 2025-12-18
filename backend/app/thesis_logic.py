import asyncio
import logging
import json
import os
from .database import SQLiteDB
from .settings import Model
from . import rag_utils

logger = logging.getLogger(__name__)

db = SQLiteDB()

async def summarize_file_map_reduce(file_path: str, chunk_token_size: int = 10000) -> str:
    """
    Summarizes a large file using a Map-Reduce strategy:
    1. Splits the file into large chunks.
    2. Summarizes each chunk (Map).
    3. Summarizes the combined summaries (Reduce).
    """
    logger.info(f"Starting Map-Reduce summarization for {file_path}")
    
    # 1. Load Document
    # Use "Smart Loading" (Unstructured) to get cleaner text and handle OCR if needed
    elements = rag_utils.load_document_unstructured(file_path)
    
    if not elements:
        return "Empty file or failed to read."
        
    # 2. Smart Grouping into Chunks
    # We want chunks of approximately chunk_token_size * 4 chars (~40k chars).
    # We iterate through elements and accumulate text until we hit the limit or a major section break (optional).
    # For now, let's just accumulate text to respect the size limit.
    
    target_chunk_char_size = chunk_token_size * 4
    chunks = []
    current_chunk = []
    current_size = 0
    
    for element in elements:
        text = str(element)
        text_len = len(text)
        
        # If adding this element exceeds target size substantially (e.g. > 110%), push current chunk
        # AND we have enough content (at least 50% of target)
        if current_size + text_len > target_chunk_char_size:
            chunks.append("\n\n".join(current_chunk))
            current_chunk = []
            current_size = 0
            
        current_chunk.append(text)
        current_size += text_len
        
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))
    
    logger.info(f"Split {file_path} into {len(chunks)} smart chunks using Unstructured.")

    model = Model()
    
    # Map Step
    chunk_summaries = []
    # Process in parallel with semaphore if needed, but for now simple gather
    # We might hit rate limits, so maybe sequential or small batch is safer? 
    # Let's try parallel but limited by the Model class's internal logic/locks if any?
    # The Model class provided in settings.py handles some retries but not explicit rate limiting for parallel calls beyond the key rotation.
    
    tasks = []
    for chunk in chunks:
        prompt = "Summarize this section of the text in verified detail."
        # We reuse generate_text_api or summarize_document_api logic
        # customized prompt:
        summary_prompt = f"Summarize the following text, capturing the key points and details. Text:\n\n{chunk[:100]}... (truncated for log)"
        # actually passing full chunk
        tasks.append(model.generate_text_api(f"Please provide a comprehensive summary of the following text section:\n\n{chunk}"))

    chunk_summaries = await asyncio.gather(*tasks)
    
    # Reduce Step
    combined_summary_text = "\n\n".join(chunk_summaries)
    
    if len(chunks) == 1:
        final_summary = chunk_summaries[0]
    else:
        final_summary = await model.generate_text_api(f"Succinctly summarize the following summaries to provide a coherent overview of the entire document:\n\n{combined_summary_text}")
    
    # Save to DB
    # We need a method in DB to save deep_summary
    db.save_deep_summary(file_path, final_summary, intermediate_summaries=chunk_summaries)
    
    return final_summary

async def generate_thesis_structure(project_id: int, chapters: list[dict], use_advanced_indexing: bool = True):
    """
    For each chapter, find relevant files using Global Relevance Scoring logic:
    - Query the vector DB for the chapter (Title + Description)
    - Group chunks by file
    - Assign file score = Max(chunk_scores) (Max-Pooling)
    - Return sorted list of files per chapter
    """
    logger.info(f"Generating thesis structure for project {project_id} with {len(chapters)} chapters.")
    
    # 1. Get Collection
    chroma_client = rag_utils.get_chroma_client()
    collection_name = "file_embeddings_unstructured" if use_advanced_indexing else "file_embeddings"
    
    try:
        collection = chroma_client.get_collection(name=collection_name)
    except Exception as e:
        logger.warning(f"Collection {collection_name} not found or error accessing it: {e}. Returning empty structure.")
        # Save empty structure so UI stops spinning effectively (or just return empty)
        # But we should save it so subsequent get_structure calls return empty list instead of 404/null
        structure = []
        db.save_thesis_structure(project_id, json.dumps(structure))
        return structure
        
    structure = []
    
    try:
        for chapter in chapters:
            chapter_title = chapter.get("title", "Untitled")
            # ... loop body ...
            # We need to protect the loop content too
            pass 
    except Exception as e:
        logger.error(f"Error during structure generation loop: {e}")
        # Return partial structure or fail? safer to return what we have
        return structure

    for chapter in chapters:
        chapter_title = chapter.get("title", "Untitled")
        chapter_desc = chapter.get("description", "")
        query = f"{chapter_title}: {chapter_desc}"
        
        logger.info(f"Processing chapter: {chapter_title}")
        
        try:
             # Retrieve raw chunks with re-ranking (High K to ensure broad search before max-pooling)
             chunks = await rag_utils.retrieve_relevant_chunks(query, collection, top_k=100)
        except Exception as e:
             logger.error(f"Error retrieving chunks for {chapter_title}: {e}")
             chunks = []

        # Group by file and find max score (Max-Pooling)
        
        # Collect all raw scores first to find min/max for normalization
        all_scores = [chunk["score"] for chunk in chunks]
        if all_scores:
            min_score = min(all_scores)
            max_score = max(all_scores)
            score_range = max_score - min_score
        else:
            min_score = 0
            max_score = 1
            score_range = 1

        files_data = {}
        for chunk in chunks:
            file_path = chunk["metadata"].get("file_path")
            
            # Normalize with Min-Max Scaling (Relative to this query result set)
            # This ensures the best result is 1.0 and worst is 0.0 (or close to it)
            # helping user see relative ranking even if absolute logits are low.
            raw_score = chunk["score"]
            if score_range > 0:
                normalized_score = (raw_score - min_score) / score_range
            else:
                normalized_score = 1.0 # All same score

            content = chunk["document"] # The excerpt
            
            if file_path not in files_data:
                files_data[file_path] = {
                    "score": normalized_score,
                    "excerpt": content,
                    "metadata": chunk["metadata"]
                }
            else:
                # Update if better score found
                if normalized_score > files_data[file_path]["score"]:
                    files_data[file_path]["score"] = normalized_score
                    files_data[file_path]["excerpt"] = content
        
        # Convert to list and sort
        sorted_files = sorted(files_data.values(), key=lambda x: x["score"], reverse=True)
        
        # Add basic file info (name)
        for f in sorted_files:
            f["filename"] = os.path.basename(f["metadata"].get("file_path", ""))
            
        structure.append({
            "chapter_title": chapter_title,
            "chapter_description": chapter_desc,
            "relevant_files": sorted_files
        })
        
    # Save to DB
    structure_json = json.dumps(structure)
    db.save_thesis_structure(project_id, structure_json)
    
    return structure
