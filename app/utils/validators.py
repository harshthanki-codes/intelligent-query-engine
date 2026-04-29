import re
from typing import Set


DANGEROUS_KEYWORDS = {
    "DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE", 
    "REPLACE", "INSERT", "UPDATE", "GRANT", "REVOKE",
    "EXEC", "EXECUTE", "SCRIPT", "PRAGMA"
}

ALLOWED_AGGREGATIONS = {"COUNT", "SUM", "AVG", "MIN", "MAX", "STRING_AGG"}

ALLOWED_CLAUSES = {"WHERE", "GROUP", "ORDER", "LIMIT", "HAVING", "JOIN", "LEFT", "RIGHT", "INNER"}


def validate_sql_safety(sql: str) -> tuple[bool, str]:
    """Check SQL for dangerous operations"""
    sql_upper = sql.upper().strip()
    
    for keyword in DANGEROUS_KEYWORDS:
        if re.search(rf'\b{keyword}\b', sql_upper):
            return False, f"SQL contains dangerous keyword: {keyword}"
    
    if ";" in sql and not sql.rstrip().endswith(";"):
        return False, "Multiple SQL statements detected"
    
    if "--" in sql or "/*" in sql:
        return False, "SQL comments detected"
    
    if "${" in sql or "{" in sql or "%" in sql:
        return False, "Potential template injection detected"
    
    return True, "SQL is safe"


def validate_aggregation(sql: str) -> tuple[bool, str]:
    """Verify SQL uses only allowed aggregations"""
    sql_upper = sql.upper()
    
    found_aggs = set(re.findall(r'\b(COUNT|SUM|AVG|MIN|MAX|STRING_AGG)\s*\(', sql_upper))
    
    if found_aggs and not found_aggs.issubset(ALLOWED_AGGREGATIONS):
        invalid = found_aggs - ALLOWED_AGGREGATIONS
        return False, f"Unsupported aggregations: {invalid}"
    
    return True, "Aggregations are valid"


def validate_query_structure(sql: str) -> tuple[bool, str]:
    """Ensure query follows expected SELECT pattern"""
    sql = sql.strip()
    
    if not sql.upper().startswith("SELECT"):
        return False, "Query must be a SELECT statement"
    
    if not re.search(r'\bFROM\s+transactions\b', sql, re.IGNORECASE):
        return False, "Query must reference 'transactions' table"
    
    return True, "Query structure is valid"


def sanitize_identifier(identifier: str) -> str:
    """Remove potentially dangerous characters from column/table names"""
    return re.sub(r'[^\w\d_]', '', identifier)