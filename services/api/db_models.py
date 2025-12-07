"""
SQLAlchemy database models for the Intelligent Web Data Aggregator.

This module defines the database schema using SQLAlchemy ORM models.
These models represent the persistent data structures for tasks, cached parsers, and users.

Normalization to 3NF:
- Domains extracted to lookup table (eliminates derivable domain from URL)
- Task source data separated (reduces row size for frequent task queries)
- Intent data normalized (reusable across tasks)
- Parser samples separated (large blobs isolated)
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional, Dict, Any

from .database import Base


class User(Base):
    """
    Model for storing user authentication data.
    1NF: Atomic values, unique rows via PK
    2NF: All non-key attributes depend on full PK
    3NF: No transitive dependencies
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_active = Column(Boolean, default=True)

    tasks = relationship("ScrapingTask", back_populates="owner")
    scheduled_jobs = relationship("ScheduledJob", back_populates="owner")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}')>"


class Domain(Base):
    """
    Lookup table for domains (3NF normalization).
    Eliminates repeated domain strings and derivable domain from URL.
    """
    __tablename__ = "domains"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)  # e.g., "example.com"
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    parsers = relationship("ParserCache", back_populates="domain_ref")
    
    def __repr__(self) -> str:
        return f"<Domain(id={self.id}, name='{self.name}')>"


class TaskIntent(Base):
    """
    Normalized intent data extracted from user prompts.
    Separated to allow intent reuse and reduce ScrapingTask row size.
    3NF: All attributes depend only on PK, no transitive dependencies.
    """
    __tablename__ = "task_intents"
    
    id = Column(Integer, primary_key=True, index=True)
    target = Column(Text, nullable=True)  # e.g., "job listings", "prices"
    keywords = Column(JSON, nullable=True)  # ["python", "developer", "remote"]
    schema_fields = Column(JSON, nullable=True)  # ["title", "salary", "location"]
    constraints = Column(JSON, nullable=True)  # ["salary > $100k"]
    output_shape = Column(Text, nullable=True)  # "list of job titles with salaries"
    confidence = Column(Float, nullable=True)  # 0.0-1.0
    normalized_hash = Column(String(64), nullable=True, index=True)  # For matching similar intents
    
    # Source extraction hints
    source_type = Column(String(50), nullable=True)  # 'content', 'attribute', 'schema'
    target_attribute = Column(String(50), nullable=True)  # 'href', 'src', etc.
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    tasks = relationship("ScrapingTask", back_populates="intent")
    
    def __repr__(self) -> str:
        return f"<TaskIntent(id={self.id}, target='{self.target}')>"


class TaskSourceData(Base):
    """
    Large source data blobs separated from main task table.
    Reduces ScrapingTask row size for frequent status queries.
    One-to-one with ScrapingTask.
    """
    __tablename__ = "task_source_data"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("scraping_tasks.id"), unique=True, nullable=False)
    
    # Raw page content (can be large)
    page_content = Column(Text, nullable=True)  # innerText from page
    html_content = Column(Text, nullable=True)  # Full HTML if stored
    
    # Network data
    network_requests = Column(JSON, nullable=True)  # Captured XHR/fetch requests
    
    # Chosen source details
    chosen_source_url = Column(Text, nullable=True)
    
    # Relationship
    task = relationship("ScrapingTask", back_populates="source_data")
    
    def __repr__(self) -> str:
        return f"<TaskSourceData(task_id={self.task_id})>"


class ScrapingTask(Base):
    """
    Model for storing scraping task information and status.
    
    3NF Normalized:
    - Large blobs moved to TaskSourceData (one-to-one)
    - Intent data moved to TaskIntent (many-to-one, allows reuse)
    - All remaining attributes depend only on task PK
    """
    
    __tablename__ = "scraping_tasks"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Task identification
    task_id = Column(String(255), unique=True, index=True, nullable=False)
    
    # Request data
    url = Column(Text, nullable=False)
    user_prompt = Column(Text, nullable=False)
    
    # Task status and metadata
    status = Column(String(50), nullable=False, default="PENDING")  # PENDING, IN_PROGRESS, SUCCESS, FAILED
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    
    # Results
    extracted_data = Column(JSON, nullable=True)  # Final extracted data as JSON
    total_matches = Column(Integer, nullable=True)  # Number of matches found
    
    # Processing metadata
    processing_time_seconds = Column(Integer, nullable=True)
    used_cached_parser = Column(Boolean, default=False, nullable=False)
    
    # Relationships (normalized)
    intent_id = Column(Integer, ForeignKey("task_intents.id"), nullable=True)
    intent = relationship("TaskIntent", back_populates="tasks")
    
    used_parser_id = Column(Integer, ForeignKey("parsers_cache.id"), nullable=True)
    used_parser = relationship("ParserCache", back_populates="tasks")

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    owner = relationship("User", back_populates="tasks")
    
    # One-to-one with source data
    source_data = relationship("TaskSourceData", back_populates="task", uselist=False)
    
    def __repr__(self) -> str:
        return f"<ScrapingTask(id={self.id}, task_id='{self.task_id}', status='{self.status}')>"


class ParserSample(Base):
    """
    Sample input/output data for parser validation.
    Separated from ParserCache to reduce row size.
    One-to-one with ParserCache.
    """
    __tablename__ = "parser_samples"
    
    id = Column(Integer, primary_key=True, index=True)
    parser_id = Column(Integer, ForeignKey("parsers_cache.id"), unique=True, nullable=False)
    
    sample_input = Column(Text, nullable=True)  # Sample source content
    sample_output = Column(JSON, nullable=True)  # Expected extraction results
    
    # Relationship
    parser = relationship("ParserCache", back_populates="samples")
    
    def __repr__(self) -> str:
        return f"<ParserSample(parser_id={self.parser_id})>"


class ParserCache(Base):
    """
    Model for caching successful regex parsers.
    
    3NF Normalized:
    - Domain extracted to Domain lookup table (eliminates transitive dependency)
    - Sample data moved to ParserSample (reduces row size)
    - All remaining attributes depend only on parser PK
    """
    
    __tablename__ = "parsers_cache"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # URL pattern matching
    url_pattern = Column(String(500), nullable=False, index=True)
    
    # Domain reference (normalized - was derived from url_pattern, violating 3NF)
    domain_id = Column(Integer, ForeignKey("domains.id"), nullable=False)
    domain_ref = relationship("Domain", back_populates="parsers")
    
    # User intent matching
    user_intent = Column(Text, nullable=False)  # Normalized user prompt
    intent_keywords = Column(JSON, nullable=True)  # Keywords for matching
    target_data_type = Column(String(100), nullable=True)  # "job_listings", "prices"
    normalized_intent_hash = Column(String(64), nullable=True, index=True)
    keyword_set = Column(JSON, nullable=True)  # Canonical keywords for overlap
    
    # Parser information
    generated_regex = Column(Text, nullable=False)
    source_type = Column(String(50), nullable=False)  # 'HTML', 'JSON', 'XML', 'SCHEMA'
    source_identifier = Column(Text, nullable=True)
    
    # Validation and performance metrics
    test_matches_count = Column(Integer, nullable=False)
    confidence_score = Column(Integer, default=100, nullable=False)
    success_rate = Column(Integer, default=100, nullable=False)
    times_used = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    created_by_task_id = Column(String(255), nullable=False)
    
    # LLM context
    llm_model_used = Column(String(100), nullable=True)
    generation_attempts = Column(Integer, default=1, nullable=False)
    
    # Relationships
    tasks = relationship("ScrapingTask", back_populates="used_parser")
    samples = relationship("ParserSample", back_populates="parser", uselist=False)
    
    def __repr__(self) -> str:
        return f"<ParserCache(id={self.id}, target='{self.target_data_type}')>"


class ScheduledJob(Base):
    """
    Model for scheduled scraping tasks.
    Already in 3NF - all attributes depend only on job PK.
    """
    __tablename__ = "scheduled_jobs"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(Text, nullable=False)
    prompt = Column(Text, nullable=False)
    schedule_cron = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True)
    
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="scheduled_jobs")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<ScheduledJob(id={self.id}, cron='{self.schedule_cron}')>"
