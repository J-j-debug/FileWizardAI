
import asyncio
import json
from . import run
from .settings import Model
from .database import SQLiteDB
import logging

logger = logging.getLogger(__name__)
db = SQLiteDB()

async def execute_analysis(schema_id: int, root_path: str, recursive: bool, required_exts: list[str], strategy: str, token_count: int):
    """
    Main function to execute a deep analysis based on a schema and a list of files.
    """
    schema_row = db.get_analysis_schema(schema_id)
    if not schema_row:
        raise ValueError(f"Schema with ID {schema_id} not found.")

    schema_id, schema_name, schema_data_str = schema_row
    schema_data = json.loads(schema_data_str)
    questions = schema_data.get('questions', [])
    tags = schema_data.get('tags', [])

    # Load documents asynchronously within the background task
    docs = run.load_documents(root_path, recursive=recursive, required_exts=required_exts, token_count=token_count)

    model = Model()

    for doc in docs:
        file_path = doc.metadata.get('file_path')
        if not file_path:
            continue

        try:
            content = doc.text
            # Construct the prompt
            prompt = build_deep_analysis_prompt(content, questions, tags)

            # Call the LLM
            response_json = await model.execute_deep_analysis_prompt(prompt)

            # Save the result
            db.save_analysis_result(schema_id, file_path, json.dumps(response_json))
            logger.info(f"Successfully analyzed and saved results for: {file_path}")

        except Exception as e:
            logger.error(f"Failed to analyze file {file_path}: {e}")

    return {"message": f"Analysis '{schema_name}' completed on {len(file_paths)} files."}


def build_deep_analysis_prompt(content: str, questions: list[str], tags: list[str]) -> str:
    """Builds the structured prompt for the LLM."""

    question_lines = "\n".join([f'"{i+1}": "{q}"' for i, q in enumerate(questions)])
    tag_lines = ", ".join([f'"{t}"' for t in tags])

    prompt = f"""
    You are an expert document analyst. Based on the document content provided below, answer the following questions and identify the applicable tags.
    Your response MUST be a valid JSON object with the keys "answers" and "tags".

    **Document Content:**
    ---
    {content}
    ---

    **Questions:**
    Please provide answers to the following questions in the "answers" object of your JSON response. The keys should correspond to the question numbers.
    {{
        {question_lines}
    }}

    **Tags:**
    From the following list, identify all tags that apply to the document. Provide the list in the "tags" array of your JSON response.
    [{tag_lines}]

    **JSON Response format:**
    {{
      "answers": {{
        "1": "Your answer to question 1",
        "2": "Your answer to question 2"
      }},
      "tags": ["applicable_tag_1", "applicable_tag_2"]
    }}
    """.strip()
    return prompt
