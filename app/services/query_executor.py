import time
from typing import Dict, Any, List

from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.utils.logger import get_logger

logger = get_logger(__name__)

MAX_RESULT_ROWS = 10000
QUERY_TIMEOUT = 30


def execute_query(db: Session, sql: str, user_id: int) -> Dict[str, Any]:
    """Execute SQL query safely with timeout and result limits"""
    
    if not sql or not sql.strip():
        return {
            "success": False,
            "error": "Empty SQL query",
            "columns": [],
            "rows": [],
            "row_count": 0
        }
    
    try:
        logger.debug(f"Executing SQL for user {user_id}: {sql[:100]}...")
        start_time = time.time()
        
        result = db.execute(text(sql))
        
        execution_time = time.time() - start_time
        logger.debug(f"Query executed in {execution_time:.2f}s")
        
        if execution_time > QUERY_TIMEOUT:
            return {
                "success": False,
                "error": f"Query exceeded timeout ({QUERY_TIMEOUT}s)",
                "columns": [],
                "rows": [],
                "row_count": 0
            }
        
        columns = list(result.keys()) if result.keys() else []
        rows = []
        row_count = 0
        
        for row in result:
            if row_count >= MAX_RESULT_ROWS:
                logger.warning(f"Result set exceeded {MAX_RESULT_ROWS} rows, truncating")
                break
            
            row_data = list(row)
            rows.append(row_data)
            row_count += 1
        
        logger.info(f"Query successful: {row_count} rows returned for user {user_id}")
        
        return {
            "success": True,
            "columns": columns,
            "rows": rows,
            "row_count": row_count
        }
    
    except SQLAlchemyError as e:
        logger.error(f"SQL execution error: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": f"SQL execution error: {str(e)}",
            "columns": [],
            "rows": [],
            "row_count": 0
        }
    
    except Exception as e:
        logger.error(f"Unexpected error during query execution: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": f"Query execution failed: {str(e)}",
            "columns": [],
            "rows": [],
            "row_count": 0
        }


def validate_result_structure(result: Dict[str, Any]) -> bool:
    """Validate result dictionary has required fields"""
    required_fields = {"success", "columns", "rows", "row_count"}
    return all(field in result for field in required_fields)