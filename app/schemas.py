from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Any, Dict


class QueryRequest(BaseModel):
    user_id: int = Field(..., description="User ID")
    question: str = Field(..., description="Natural language question")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "question": "How much did I spend on food last month?"
            }
        }


class TransactionResponse(BaseModel):
    id: int
    user_id: int
    amount: float
    category: str
    merchant: Optional[str]
    transaction_date: datetime
    description: Optional[str]
    
    class Config:
        from_attributes = True


class QueryResultData(BaseModel):
    columns: List[str]
    rows: List[List[Any]]
    row_count: int


class QueryResponse(BaseModel):
    query_id: str
    success: bool
    sql_generated: str
    result: Optional[QueryResultData]
    insight: str
    execution_time_ms: float
    cached: bool
    error: Optional[str] = None
    
    class Config:
        from_attributes = True


class QueryHistoryItem(BaseModel):
    id: str
    natural_language_query: str
    generated_sql: str
    result_count: int
    success: bool
    insight_text: Optional[str]
    execution_time_ms: Optional[float]
    created_at: datetime
    
    class Config:
        from_attributes = True


class QueryHistoryResponse(BaseModel):
    total: int
    page: int
    limit: int
    items: List[QueryHistoryItem]


class AnalyticsResponse(BaseModel):
    user_id: int
    query_count: int
    successful_queries: int
    failed_queries: int
    average_execution_time_ms: float
    cache_hit_rate: float
    total_results_fetched: int
    last_query_date: Optional[datetime]
    
    class Config:
        from_attributes = True


class CostTrackingResponse(BaseModel):
    user_id: int
    total_cost: float
    cost_breakdown: Dict[str, float]
    period: str


class HealthCheckResponse(BaseModel):
    status: str
    version: str
    database_connected: bool
    ollama_connected: bool
    cache_available: bool


class BatchQueryRequest(BaseModel):
    user_id: int
    questions: List[str] = Field(..., min_items=1, max_items=10)
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "questions": [
                    "How much did I spend on food?",
                    "What was my largest transaction?"
                ]
            }
        }


class BatchQueryResponse(BaseModel):
    batch_id: str
    user_id: int
    total_queries: int
    successful: int
    failed: int
    results: List[QueryResponse]