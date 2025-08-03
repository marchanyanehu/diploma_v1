"""
Configuration settings for the FastAPI application.

This module handles environment variables and application configuration
for different deployment environments (development, testing, production).
"""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Constants
DEFAULT_REDIS_URL = "redis://localhost:6379/0"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )
    
    # API Configuration
    api_title: str = Field(default="Intelligent Web Data Aggregator", alias="API_TITLE")
    api_version: str = Field(default="1.0.0", alias="API_VERSION")
    debug: bool = Field(default=False, alias="DEBUG")
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    
    # Database Configuration
    database_url: Optional[str] = Field(default=None, alias="DATABASE_URL")
    db_host: str = Field(default="localhost", alias="DB_HOST")
    db_port: int = Field(default=5432, alias="DB_PORT")
    db_name: str = Field(default="diploma_db", alias="DB_NAME")
    db_user: str = Field(default="postgres", alias="DB_USER")
    db_password: str = Field(default="", alias="DB_PASSWORD")
    
    # Redis Configuration (for Celery)
    redis_url: str = Field(default=DEFAULT_REDIS_URL, alias="REDIS_URL")
    
    # Celery Configuration
    celery_broker_url: str = Field(default=DEFAULT_REDIS_URL, alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default=DEFAULT_REDIS_URL, alias="CELERY_RESULT_BACKEND")
    
    # LLM API Configuration
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    llm_provider: str = Field(default="openai", alias="LLM_PROVIDER")
    llm_model: str = Field(default="gpt-3.5-turbo", alias="LLM_MODEL")
    
    # Security
    secret_key: str = Field(default="your-secret-key-change-in-production", alias="SECRET_KEY")
    
    # CORS
    cors_origins: str = Field(default="*", alias="CORS_ORIGINS")
    
    @property
    def database_dsn(self) -> str:
        """Construct database DSN from individual components."""
        if self.database_url:
            return self.database_url
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def cors_origins_list(self) -> list[str]:
        """Convert CORS origins string to list."""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",")]


# Global settings instance
settings = Settings()
