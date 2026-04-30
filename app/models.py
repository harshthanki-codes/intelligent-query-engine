from sqlalchemy import Column, Integer, Float, String, DateTime, Text, Boolean, Index, ForeignKey, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    transactions = relationship("Transaction", back_populates="user")
    queries = relationship("QueryHistory", back_populates="user")
    
    __table_args__ = (
        Index("idx_user_id", "user_id"),
    )


class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    category = Column(String(255), nullable=False, index=True)
    merchant = Column(String(255), nullable=True)
    transaction_date = Column(DateTime, nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="transactions")
    
    __table_args__ = (
        Index("idx_user_date", "user_id", "transaction_date"),
        Index("idx_category", "category"),
        Index("idx_merchant", "merchant"),
    )


class QueryHistory(Base):
    __tablename__ = "query_history"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    natural_language_query = Column(Text, nullable=False)
    generated_sql = Column(Text, nullable=False)
    query_result = Column(Text, nullable=True)
    insight_text = Column(Text, nullable=True)
    execution_time_ms = Column(Float, nullable=True)
    result_count = Column(Integer, default=0)
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    cached = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    user = relationship("User", back_populates="queries")
    
    __table_args__ = (
        Index("idx_user_created", "user_id", "created_at"),
    )


class QueryAnalytics(Base):
    __tablename__ = "query_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    query_count = Column(Integer, default=0)
    successful_queries = Column(Integer, default=0)
    failed_queries = Column(Integer, default=0)
    average_execution_time_ms = Column(Float, default=0.0)
    cache_hit_rate = Column(Float, default=0.0)
    total_results_fetched = Column(Integer, default=0)
    last_query_date = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_user_analytics", "user_id"),
    )


class CostTracking(Base):
    __tablename__ = "cost_tracking"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    query_id = Column(String(36), ForeignKey("query_history.id"), nullable=True)
    cost_type = Column(String(50), nullable=False)
    cost_amount = Column(Float, default=0.0)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index("idx_user_cost", "user_id", "created_at"),
    )