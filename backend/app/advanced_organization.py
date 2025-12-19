import logging
import json
import asyncio
from .settings import Model

logger = logging.getLogger(__name__)

from .progress_tracker import tracker

async def generate_taxonomy(summaries: list, model: Model) -> list:
    """
    Phase 1: Generates a global taxonomy from a list of file summaries using a Map-Reduce approach.
    """
    logger.info(f"Starting Taxonomy Generation with {len(summaries)} summaries.")
    tracker.update(status="Phase 1: Generates a global taxonomy...", percent=60, log="Generating taxonomy proposals...")
    
    # 1. Map: unique batches
    batch_size = 50 
    batches = [summaries[i:i + batch_size] for i in range(0, len(summaries), batch_size)]
    
    proposal_tasks = [model.generate_taxonomy_proposal_api([{"path": s["file_path"], "summary": s["summary"]} for s in batch]) for batch in batches]
        
    # Execute Map in parallel
    logger.info(f"Requests {len(proposal_tasks)} taxonomy proposals...")
    proposals = await asyncio.gather(*proposal_tasks)
    
    # Filter valid proposals
    valid_proposals = [p for p in proposals if p and isinstance(p, list)]
    
    if not valid_proposals:
        logger.warning("No valid taxonomy proposals received. Fallback to basic list.")
        tracker.update(log="No valid taxonomy proposals. Using fallback.")
        return ["Miscellaneous"]

    # 2. Reduce: Merge into Master Taxonomy
    logger.info("Merging proposals into Master Taxonomy...")
    tracker.update(status="Phase 1: Merging taxonomy...", percent=70, log=f"Merging {len(valid_proposals)} proposals...")
    master_taxonomy = await model.merge_taxonomies_api(valid_proposals)
    
    logger.info(f"Master Taxonomy generated with {len(master_taxonomy)} categories.")
    tracker.update(log=f"Taxonomy generated: {master_taxonomy}")
    return master_taxonomy

async def assign_files_to_taxonomy(summaries: list, taxonomy: list, model: Model) -> list:
    """
    Phase 2: Assigns each file to one of the categories in the Master Taxonomy.
    """
    logger.info("Starting strict file assignment to taxonomy...")
    tracker.update(status="Phase 2: Assigning files to taxonomy...", percent=75)
    
    batch_size = 20
    batches = [summaries[i:i + batch_size] for i in range(0, len(summaries), batch_size)]
    total_batches = len(batches)
    
    # Create tasks for parallel execution
    tasks = []
    for batch in batches:
        batch_data = [{"path": s["file_path"], "summary": s["summary"]} for s in batch]
        tasks.append(asyncio.create_task(model.assign_files_to_taxonomy_api(batch_data, taxonomy)))
        
    # Execute Assignments with live progress
    results = []
    completed_count = 0
    
    for task in asyncio.as_completed(tasks):
        batch_result = await task
        results.append(batch_result)
        completed_count += 1
        # Calculate progress from 75% to 95%
        progress = 75 + int((completed_count / total_batches) * 20)
        tracker.update(status=f"Assigning files: Batch {completed_count}/{total_batches}", percent=progress)
    
    # Flatten results
    file_tree = []
    for batch_result in results:
        if batch_result and isinstance(batch_result, list):
            file_tree.extend(batch_result)
            
    return file_tree

async def run_advanced_organization(summaries: list) -> list:
    """
    Orchestrator for the Advanced (Two-Pass) Organization.
    """
    model = Model()
    
    # Phase 1: Generate Global Taxonomy
    taxonomy = await generate_taxonomy(summaries, model)
    
    # Phase 2: Assign Files STRICTLY to this taxonomy
    file_tree = await assign_files_to_taxonomy(summaries, taxonomy, model)
    
    return file_tree
