import requests
import json
from typing import Dict, Any

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


def generate_insight(question: str, query_result: Dict[str, Any]) -> str:
    """Generate human-readable insights from query results using Ollama"""
    
    if not query_result.get("success"):
        return "Unable to generate insight due to query execution error."
    
    columns = query_result.get("columns", [])
    rows = query_result.get("rows", [])
    row_count = query_result.get("row_count", 0)
    
    if row_count == 0:
        return "No data available for the given query. Please check your filters or date range."
    
    result_summary = format_result_for_llm(columns, rows)
    
    prompt = f"""You are a financial analyst assistant. Generate a concise, human-readable insight from the following query result.

Original Question: {question}

Query Results:
{result_summary}

Provide:
1. A direct answer to the question
2. Key insights or patterns observed
3. One relevant recommendation or observation (if applicable)

Keep the response to 2-3 sentences maximum. Be specific with numbers."""
    
    try:
        logger.debug("Calling Ollama to generate insights")
        
        response = requests.post(
            f"{settings.ollama_base_url}/api/generate",
            json={
                "model": settings.ollama_model,
                "prompt": prompt,
                "stream": False,
                "temperature": 0.3,
            },
            timeout=30
        )
        
        if response.status_code != 200:
            logger.error(f"Ollama returned status {response.status_code}")
            return "Unable to generate insight at this time."
        
        result = response.json()
        insight = result.get("response", "").strip()
        
        if not insight:
            return "Unable to generate insight from the query results."
        
        logger.debug(f"Generated insight: {insight[:100]}...")
        return insight
    
    except requests.exceptions.Timeout:
        logger.error("Ollama insight generation timed out")
        return "Insight generation timed out. Results are displayed above."
    except requests.exceptions.ConnectionError:
        logger.error("Could not connect to Ollama for insights")
        return "Unable to connect to insight service. Results are displayed above."
    except Exception as e:
        logger.error(f"Insight generation failed: {str(e)}", exc_info=True)
        return f"Unable to generate insight: {str(e)}"


def format_result_for_llm(columns: list, rows: list, max_rows: int = 10) -> str:
    """Format query results as readable text for LLM"""
    
    if not columns or not rows:
        return "No results"
    
    lines = []
    lines.append(f"Columns: {', '.join(columns)}")
    lines.append(f"Total rows: {len(rows)}")
    lines.append("\nData (first {0} rows):".format(min(max_rows, len(rows))))
    
    for i, row in enumerate(rows[:max_rows]):
        row_str = ", ".join(str(val) for val in row)
        lines.append(f"  {i+1}. {row_str}")
    
    if len(rows) > max_rows:
        lines.append(f"  ... and {len(rows) - max_rows} more rows")
    
    return "\n".join(lines)


def summarize_multiple_results(questions_and_results: list) -> str:
    """Generate a summary insight from multiple query results"""
    
    if not questions_and_results:
        return "No results to summarize."
    
    summary_parts = []
    
    for question, result in questions_and_results:
        if result.get("success"):
            summary_parts.append(f"Q: {question}\nA: {result.get('insight', 'No insight generated')}")
    
    if not summary_parts:
        return "Unable to generate summary insights."
    
    combined = "\n\n".join(summary_parts)
    
    prompt = f"""Provide a brief executive summary of the following financial query results:

{combined}

Summary (2-3 sentences):"""
    
    try:
        response = requests.post(
            f"{settings.ollama_base_url}/api/generate",
            json={
                "model": settings.ollama_model,
                "prompt": prompt,
                "stream": False,
                "temperature": 0.2,
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get("response", "").strip()
    except Exception as e:
        logger.warning(f"Summary generation failed: {str(e)}")
    
    return combined