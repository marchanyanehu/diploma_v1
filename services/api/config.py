"""
Configuration settings for the FastAPI application.

This module handles environment variables and application configuration
for different deployment environments (development, testing, production).
"""

import os
from typing import Optional, List
from pydantic import Field, BaseModel

try:  # Attempt to import pydantic_settings (preferred)
    from pydantic_settings import BaseSettings as _PSBase, SettingsConfigDict  # type: ignore
    BaseForSettings = _PSBase  # type: ignore
    _USE_SETTINGS_FALLBACK = False
except Exception:  # noqa: BLE001
    BaseForSettings = BaseModel  # type: ignore
    SettingsConfigDict = lambda **_: None  # type: ignore
    _USE_SETTINGS_FALLBACK = True

# Constants
DEFAULT_REDIS_URL = "redis://localhost:6379/0"


class Settings(BaseForSettings):  # type: ignore[misc]
    """Application settings loaded from environment variables.

    Includes a graceful fallback if pydantic-settings is unavailable or mismatched.
    """

    if not _USE_SETTINGS_FALLBACK:  # only valid when real pydantic_settings present
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
    # We support multiple providers via LiteLLM. Keys are optional; specific provider
    # clients (e.g. Gemini) are resolved at runtime inside shared.llm_client.
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    google_api_key: Optional[str] = Field(default=None, alias="GOOGLE_API_KEY")
    gemini_api_key: Optional[str] = Field(default=None, alias="GEMINI_API_KEY")
    llm_provider: str = Field(default="gemini", alias="LLM_PROVIDER")  # default to gemini for project focus
    llm_model: str = Field(default="gemini-2.0-flash", alias="LLM_MODEL")
    
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
    def cors_origins_list(self) -> List[str]:
        """Convert CORS origins string to list."""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",")]


# Global settings instance
try:
    settings = Settings()
except Exception:
    # As an extreme fallback construct with defaults only
    settings = Settings()  # relying on default values
