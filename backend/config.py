from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Database settings
    database_url: str = "postgresql://postgres:qwerty12345@localhost:5433/ragbot"
    
    # Qdrant settings
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_batch_size: int = 32
    embedding_cache_dir: str = "./models"

    # OAuth settings
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "urn:ietf:wg:oauth:2.0:oob"
    
    # JWT settings
    jwt_secret_key: str = "20b65ba89001e24c49f1af548fc2bb456dcdb039"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # ML model settings
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "gemma:2b"
    
    # App settings
    app_name: str = "RAG Desktop App"
    app_version: str = "1.0.0"
    debug: bool = True
    
    # AWS S3 settings
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    s3_bucket_name: str = "ragbot-conversations"
    s3_region: str = "us-east-1"
    disable_s3: bool = False

    # Qdrant settings  
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: Optional[str] = None
    qdrant_collection_name: str = "documents"

    ollama_timeout: int = 60

    # RAG settings
    rag_max_results: int = 10
    rag_max_context_length: int = 10000

    # Tavily settings
    tavily_api_key: str = ""
    web_search_enabled: bool = True
    fallback_threshold: float = 0.3 
    
    # Additional frontend/CORS settings
    jwt_expiration_hours: int = 24
    frontend_url: str = "http://localhost:3000"
    cors_origins: str = '["http://localhost:3000","http://localhost:8080"]'
    
    class Config:
        env_file = "../.env"
        case_sensitive = False

settings = Settings()