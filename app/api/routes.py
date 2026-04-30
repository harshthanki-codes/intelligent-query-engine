from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
import uuid
import time

from app.database import get_db
from app.schemas import (
    QueryRequest, QueryResponse, QueryHistoryResponse, QueryHistoryItem,
    AnalyticsResponse, CostTrackingResponse, BatchQueryRequest, BatchQueryResponse
)
from app.models import User, QueryHistory, QueryAnalytics, CostTracking, Transaction
from app.services.sql_generator import generate_sql_from_query
from app.services.query_executor import execute_query
from app.services.insights import generate_insight
from app.services.cache import get_cached_result, set_cached_result
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


def get_or_create_user(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.user_id == str(user_id)).first()
    if not user:
        user = User(user_id=str(user_id))
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


@router.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest, db: Session = Depends(get_db)):
    """Convert natural language query to SQL and return insights"""
    user = get_or_create_user(db, request.user_id)
    query_id = str(uuid.uuid4())
    start_time = time.time()
    
    try:
        cached = False
        cached_result = get_cached_result(request.user_id, request.question)
        
        if cached_result:
            logger.info(f"Cache hit for user {request.user_id}")
            cached = True
            result_data = cached_result
            execution_time = 0.0
            generated_sql = ""
            insight_text = ""
        else:
            logger.info(f"Processing new query for user {request.user_id}: {request.question}")
            
            generated_sql = generate_sql_from_query(request.question, user.id)
            logger.debug(f"Generated SQL: {generated_sql}")
            
            result = execute_query(db, generated_sql, user.id)
            
            if result.get("success"):
                result_data = {
                    "columns": result["columns"],
                    "rows": result["rows"],
                    "row_count": result["row_count"]
                }
                
                insight_text = generate_insight(request.question, result)
                
                set_cached_result(request.user_id, request.question, result_data)
            else:
                raise Exception(result.get("error", "Query execution failed"))
            
            execution_time = (time.time() - start_time) * 1000
        
        query_history = QueryHistory(
            id=query_id,
            user_id=user.id,
            natural_language_query=request.question,
            generated_sql=generated_sql,
            query_result=str(result_data) if result_data else None,
            insight_text=insight_text,
            execution_time_ms=execution_time,
            result_count=result_data.get("row_count", 0) if result_data else 0,
            success=True,
            cached=cached
        )
        db.add(query_history)
        
        analytics = db.query(QueryAnalytics).filter(QueryAnalytics.user_id == user.id).first()
        if analytics:
            analytics.query_count += 1
            analytics.successful_queries += 1
            analytics.average_execution_time_ms = (
                (analytics.average_execution_time_ms * (analytics.query_count - 1) + execution_time) 
                / analytics.query_count
            )
            if cached:
                analytics.cache_hit_rate = (
                    (analytics.cache_hit_rate * (analytics.query_count - 1) + 1) / analytics.query_count
                )
            analytics.total_results_fetched += result_data.get("row_count", 0) if result_data else 0
            db.commit()
        
        db.commit()
        
        return QueryResponse(
            query_id=query_id,
            success=True,
            sql_generated=generated_sql,
            result=result_data,
            insight=insight_text,
            execution_time_ms=execution_time,
            cached=cached
        )
    
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        logger.error(f"Query processing failed: {str(e)}", exc_info=True)
        
        query_history = QueryHistory(
            id=query_id,
            user_id=user.id,
            natural_language_query=request.question,
            generated_sql="",
            success=False,
            error_message=str(e),
            execution_time_ms=execution_time
        )
        db.add(query_history)
        
        analytics = db.query(QueryAnalytics).filter(QueryAnalytics.user_id == user.id).first()
        if analytics:
            analytics.query_count += 1
            analytics.failed_queries += 1
            db.commit()
        
        db.commit()
        
        return QueryResponse(
            query_id=query_id,
            success=False,
            sql_generated="",
            result=None,
            insight="",
            execution_time_ms=execution_time,
            cached=False,
            error=str(e)
        )


@router.get("/history", response_model=QueryHistoryResponse)
async def get_query_history(
    user_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Retrieve paginated query history for a user"""
    user = get_or_create_user(db, user_id)
    
    total = db.query(QueryHistory).filter(QueryHistory.user_id == user.id).count()
    
    queries = db.query(QueryHistory).filter(
        QueryHistory.user_id == user.id
    ).order_by(desc(QueryHistory.created_at)).offset(
        (page - 1) * limit
    ).limit(limit).all()
    
    items = [
        QueryHistoryItem(
            id=q.id,
            natural_language_query=q.natural_language_query,
            generated_sql=q.generated_sql,
            result_count=q.result_count,
            success=q.success,
            insight_text=q.insight_text,
            execution_time_ms=q.execution_time_ms,
            created_at=q.created_at
        )
        for q in queries
    ]
    
    return QueryHistoryResponse(
        total=total,
        page=page,
        limit=limit,
        items=items
    )


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(user_id: int, db: Session = Depends(get_db)):
    """Get user query analytics and performance metrics"""
    user = get_or_create_user(db, user_id)
    
    analytics = db.query(QueryAnalytics).filter(QueryAnalytics.user_id == user.id).first()
    
    if not analytics:
        analytics = QueryAnalytics(user_id=user.id)
        db.add(analytics)
        db.commit()
        db.refresh(analytics)
    
    last_query = db.query(QueryHistory).filter(
        QueryHistory.user_id == user.id
    ).order_by(desc(QueryHistory.created_at)).first()
    
    return AnalyticsResponse(
        user_id=user.id,
        query_count=analytics.query_count,
        successful_queries=analytics.successful_queries,
        failed_queries=analytics.failed_queries,
        average_execution_time_ms=analytics.average_execution_time_ms,
        cache_hit_rate=analytics.cache_hit_rate,
        total_results_fetched=analytics.total_results_fetched,
        last_query_date=last_query.created_at if last_query else None
    )


@router.get("/costs", response_model=CostTrackingResponse)
async def get_costs(
    user_id: int,
    period: str = Query("monthly", regex="^(daily|weekly|monthly)$"),
    db: Session = Depends(get_db)
):
    """Get cost breakdown for user queries and operations"""
    user = get_or_create_user(db, user_id)
    
    costs = db.query(CostTracking).filter(CostTracking.user_id == user.id).all()
    
    total_cost = sum(c.cost_amount for c in costs)
    
    cost_breakdown = {}
    for cost in costs:
        cost_type = cost.cost_type
        if cost_type not in cost_breakdown:
            cost_breakdown[cost_type] = 0.0
        cost_breakdown[cost_type] += cost.cost_amount
    
    return CostTrackingResponse(
        user_id=user.id,
        total_cost=total_cost,
        cost_breakdown=cost_breakdown,
        period=period
    )


@router.post("/batch-query", response_model=BatchQueryResponse)
async def process_batch_queries(
    request: BatchQueryRequest,
    db: Session = Depends(get_db)
):
    """Process multiple queries in a single batch request"""
    user = get_or_create_user(db, request.user_id)
    batch_id = f"batch_{uuid.uuid4()}"
    
    results = []
    successful = 0
    failed = 0
    
    for question in request.questions:
        query_request = QueryRequest(user_id=request.user_id, question=question)
        
        try:
            result = await process_query(query_request, db)
            results.append(result)
            if result.success:
                successful += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"Batch query processing failed: {str(e)}")
            failed += 1
            results.append(QueryResponse(
                query_id=str(uuid.uuid4()),
                success=False,
                sql_generated="",
                result=None,
                insight="",
                execution_time_ms=0.0,
                cached=False,
                error=str(e)
            ))
    
    return BatchQueryResponse(
        batch_id=batch_id,
        user_id=request.user_id,
        total_queries=len(request.questions),
        successful=successful,
        failed=failed,
        results=results
    )