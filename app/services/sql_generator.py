import requests
import re
from typing import Optional

from app.config import get_settings
from app.utils.validators import validate_sql_safety, validate_aggregation, validate_query_structure
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

SCHEMA_CONTEXT = """
You are a SQL expert. Convert natural language questions into PostgreSQL SELECT queries.

Database Schema:
- Table: transactions
- id (INTEGER PRIMARY KEY)
- user_id (INTEGER FOREIGN KEY)
- amount (FLOAT)
- category (VARCHAR) - Examples: Food, Groceries, Utilities, Entertainment, Transport, Rent, Shopping, Subscriptions
- merchant (VARCHAR)
- transaction_date (TIMESTAMP)
- description (TEXT)

Rules:
1. ONLY generate SELECT statements
2. Always filter by user_id when mentioned or inferred
3. For date ranges, use transaction_date
4. Use aggregation functions (COUNT, SUM, AVG, MIN, MAX) as needed
5. Return only the SQL query, no explanation
6. Use proper SQL syntax
7. Do NOT use any dangerous keywords (DROP, DELETE, ALTER, etc.)

Examples:
Q: "How much did I spend on food?"
A: SELECT SUM(amount) FROM transactions WHERE user_id = ? AND category = 'Food'

Q: "Show my top 3 spending categories"
A: SELECT category, SUM(amount) as total FROM transactions WHERE user_id = ? GROUP BY category ORDER BY total DESC LIMIT 3

Q: "What was my average transaction amount?"
A: SELECT AVG(amount) FROM transactions WHERE user_id = ?
"""


def generate_sql_from_query(question: str, user_id: int) -> str:
    """Convert natural language query to SQL using Ollama"""
    
    prompt = f"""{SCHEMA_CONTEXT}

User ID: {user_id}
Question: {question}

Generate only the SQL query:"""
    
    try:
        logger.debug(f"Calling Ollama with prompt for question: {question}")
        
        response = requests.post(
            f"{settings.ollama_base_url}/api/generate",
            json={
                "model": settings.ollama_model,
                "prompt": prompt,
                "stream": False,
                "temperature": 0.1,
            },
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"Ollama returned status {response.status_code}")
        
        result = response.json()
        sql = result.get("response", "").strip()
        
        sql = re.sub(r'```sql\n?', '', sql)
        sql = re.sub(r'```\n?', '', sql)
        sql = sql.strip()
        
        logger.debug(f"Generated SQL: {sql}")
        
        safe, msg = validate_sql_safety(sql)
        if not safe:
            raise Exception(f"SQL safety validation failed: {msg}")
        
        valid, msg = validate_query_structure(sql)
        if not valid:
            raise Exception(f"SQL structure validation failed: {msg}")
        
        agg_valid, msg = validate_aggregation(sql)
        if not agg_valid:
            raise Exception(f"SQL aggregation validation failed: {msg}")
        
        sql = sql.replace("?", str(user_id))
        
        return sql
    
    except requests.exceptions.Timeout:
        logger.error("Ollama request timed out")
        raise Exception("LLM processing timed out. Please try again.")
    except requests.exceptions.ConnectionError:
        logger.error("Could not connect to Ollama")
        raise Exception("LLM service unavailable. Ensure Ollama is running on localhost:11434")
    except Exception as e:
        logger.error(f"SQL generation failed: {str(e)}", exc_info=True)
        raise Exception(f"Failed to generate SQL: {str(e)}")