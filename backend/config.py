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
    google_redirect_uri: str = "http://localhost:8080/auth/callback"
    
    # JWT settings
    jwt_secret_key: str = "20b65ba89001e24c49f1af548fc2bb456dcdb039"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # ML model settings
    embedding_model: str = "all-MiniLM-L6-v2"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "gemma:2b"
    
    # TAVILY settings
    tavily_api_key: str = ""
    
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

    # Embedding model settings

     # Qdrant settings  
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: Optional[str] = None
    qdrant_collection_name: str = "documents"
    
    class Config:
        env_file = ".env"

settings = Settings()