"""
Configuration management for ResumeRAG system.
Provides modular configuration for different AI providers and indexing strategies.
"""

import os
from typing import Literal, Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration settings"""
    
    # API Keys
    google_api_key: Optional[str] = Field(default=None, alias="GOOGLE_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    
    # Provider Selection
    embedding_provider: Literal["google", "openai", "huggingface"] = Field(
        default="google", alias="EMBEDDING_PROVIDER"
    )
    llm_provider: Literal["google", "openai", "llama"] = Field(
        default="google", alias="LLM_PROVIDER"
    )
    vector_store_provider: Literal["chromadb", "faiss"] = Field(
        default="chromadb", alias="VECTOR_STORE_PROVIDER"
    )
    
    # Google Generative AI Settings
    google_embedding_model: str = Field(
        default="models/text-embedding-004", alias="GOOGLE_EMBEDDING_MODEL"
    )
    google_llm_model: str = Field(default="gemini-1.5-flash", alias="GOOGLE_LLM_MODEL")
    
    # OpenAI Settings
    openai_embedding_model: str = Field(
        default="text-embedding-3-small", alias="OPENAI_EMBEDDING_MODEL"
    )
    openai_llm_model: str = Field(default="gpt-3.5-turbo", alias="OPENAI_LLM_MODEL")
    
    # ChromaDB Settings
    chromadb_persist_directory: str = Field(
        default="./chroma_db", alias="CHROMADB_PERSIST_DIRECTORY"
    )
    chromadb_collection_name: str = Field(
        default="resumes", alias="CHROMADB_COLLECTION_NAME"
    )
    
    # Indexing Strategy Configuration
    indexing_strategy: Literal["semantic", "keyword", "hybrid", "metadata", "advanced"] = Field(
        default="semantic", alias="INDEXING_STRATEGY"
    )
    chunk_size: int = Field(default=800, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=100, alias="CHUNK_OVERLAP")
    enable_metadata_extraction: bool = Field(
        default=True, alias="ENABLE_METADATA_EXTRACTION"
    )
    enable_entity_recognition: bool = Field(
        default=True, alias="ENABLE_ENTITY_RECOGNITION"
    )
    rerank_results: bool = Field(default=False, alias="RERANK_RESULTS")
    index_update_strategy: Literal["replace", "merge", "append"] = Field(
        default="replace", alias="INDEX_UPDATE_STRATEGY"
    )
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    debug: bool = Field(default=True, alias="DEBUG")
    
    # File Upload Configuration
    max_file_size: int = Field(default=10485760, alias="MAX_FILE_SIZE")  # 10MB
    allowed_file_types: str = Field(default="pdf,docx,txt", alias="ALLOWED_FILE_TYPES")
    
    @property
    def allowed_extensions(self) -> list[str]:
        return [ext.strip().lower() for ext in self.allowed_file_types.split(",")]
    
    # Caching Configuration
    redis_url: str = Field(default="redis://localhost:6379", alias="REDIS_URL")
    enable_caching: bool = Field(default=False, alias="ENABLE_CACHING")
    
    # Session Management Configuration
    session_timeout: int = Field(default=3600, alias="SESSION_TIMEOUT")  # 1 hour
    
    def validate_api_keys(self) -> None:
        """Validate that required API keys are present based on provider settings"""
        if self.embedding_provider == "google" or self.llm_provider == "google":
            if not self.google_api_key:
                raise ValueError("GOOGLE_API_KEY is required when using Google providers")
        
        if self.embedding_provider == "openai" or self.llm_provider == "openai":
            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY is required when using OpenAI providers")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()