"""
Factory functions for creating AI models based on configuration.
Supports multiple providers: Google, OpenAI, and HuggingFace.
"""

import os
from typing import Any
from langchain.embeddings.base import Embeddings
from langchain.llms.base import LLM
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain.vectorstores.base import VectorStore
from langchain_community.vectorstores import Chroma
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings


class ModelFactory:
    """Factory class for creating AI models and vector stores"""
    
    @staticmethod
    def create_embeddings() -> Embeddings:
        """Create embeddings model based on configuration"""
        provider = settings.embedding_provider.lower()
        
        if provider == "google":
            if not settings.google_api_key:
                raise ValueError("Google API key is required for Google embeddings")
            
            os.environ["GOOGLE_API_KEY"] = settings.google_api_key
            return GoogleGenerativeAIEmbeddings(
                model=settings.google_embedding_model
            )
        
        elif provider == "openai":
            if not settings.openai_api_key:
                raise ValueError("OpenAI API key is required for OpenAI embeddings")
            
            try:
                from langchain_openai import OpenAIEmbeddings
                return OpenAIEmbeddings(
                    openai_api_key=settings.openai_api_key,
                    model=settings.openai_embedding_model
                )
            except ImportError:
                raise ImportError("langchain-openai package is required for OpenAI embeddings")
        
        elif provider == "huggingface":
            try:
                from langchain_community.embeddings import HuggingFaceEmbeddings
                return HuggingFaceEmbeddings(
                    model_name="sentence-transformers/all-MiniLM-L6-v2"
                )
            except ImportError:
                raise ImportError("sentence-transformers package is required for HuggingFace embeddings")
        
        else:
            raise ValueError(f"Unsupported embedding provider: {provider}")
    
    @staticmethod
    def create_llm() -> LLM:
        """Create LLM model based on configuration"""
        provider = settings.llm_provider.lower()
        
        if provider == "google":
            if not settings.google_api_key:
                raise ValueError("Google API key is required for Google LLM")
            
            os.environ["GOOGLE_API_KEY"] = settings.google_api_key
            return ChatGoogleGenerativeAI(
                model=settings.google_llm_model,
                temperature=0.1,
                max_output_tokens=2048
            )
        
        elif provider == "openai":
            if not settings.openai_api_key:
                raise ValueError("OpenAI API key is required for OpenAI LLM")
            
            try:
                from langchain_openai import ChatOpenAI
                return ChatOpenAI(
                    openai_api_key=settings.openai_api_key,
                    model=settings.openai_llm_model,
                    temperature=0.1,
                    max_tokens=2048
                )
            except ImportError:
                raise ImportError("langchain-openai package is required for OpenAI LLM")
        
        elif provider == "llama":
            try:
                from langchain_community.llms import Ollama
                return Ollama(
                    model="llama2",
                    temperature=0.1
                )
            except ImportError:
                raise ImportError("Ollama package is required for Llama LLM")
        
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
    
    @staticmethod
    def create_vector_store(embeddings: Embeddings, collection_name: str = None) -> VectorStore:
        """Create vector store based on configuration"""
        provider = settings.vector_store_provider.lower()
        
        if provider == "chromadb":
            if collection_name is None:
                collection_name = settings.chromadb_collection_name
            
            # Create ChromaDB client with persistence
            chroma_client = chromadb.PersistentClient(
                path=settings.chromadb_persist_directory,
                settings=ChromaSettings(
                    allow_reset=True,
                    anonymized_telemetry=False
                )
            )
            
            return Chroma(
                client=chroma_client,
                collection_name=collection_name,
                embedding_function=embeddings
            )
        
        elif provider == "faiss":
            try:
                from langchain_community.vectorstores import FAISS
                # FAISS requires initialization with documents, so we return the class
                # The actual initialization will be done in the RAG service
                return FAISS
            except ImportError:
                raise ImportError("faiss-cpu package is required for FAISS vector store")
        
        else:
            raise ValueError(f"Unsupported vector store provider: {provider}")
    
    @staticmethod
    def get_text_splitter():
        """Create text splitter for chunking documents"""
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        
        return RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap, 
            length_function=len,
            separators=["\n\n", "\n", ". ", "! ", "? ", "; ", ": ", " ", ""]
        )
    
    @staticmethod
    def validate_configuration() -> dict:
        """Validate current configuration and return status"""
        status = {
            "embedding_provider": settings.embedding_provider,
            "llm_provider": settings.llm_provider,
            "vector_store_provider": settings.vector_store_provider,
            "errors": []
        }
        
        # Check embedding provider
        try:
            ModelFactory.create_embeddings()
            status["embedding_status"] = "ready"
        except Exception as e:
            status["embedding_status"] = "error"
            status["errors"].append(f"Embedding provider error: {str(e)}")
        
        # Check LLM provider
        try:
            ModelFactory.create_llm()
            status["llm_status"] = "ready"
        except Exception as e:
            status["llm_status"] = "error"
            status["errors"].append(f"LLM provider error: {str(e)}")
        
        # Check vector store
        try:
            # Create dummy embeddings for vector store test
            from langchain_community.embeddings import HuggingFaceEmbeddings
            dummy_embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
            ModelFactory.create_vector_store(dummy_embeddings, "test_collection")
            status["vector_store_status"] = "ready"
        except Exception as e:
            status["vector_store_status"] = "error"
            status["errors"].append(f"Vector store error: {str(e)}")
        
        return status


# Convenience functions for quick access
def get_embeddings() -> Embeddings:
    """Get configured embeddings model"""
    return ModelFactory.create_embeddings()


def get_llm() -> LLM:
    """Get configured LLM model"""
    return ModelFactory.create_llm()


def get_vector_store(embeddings: Embeddings, collection_name: str = None) -> VectorStore:
    """Get configured vector store"""
    return ModelFactory.create_vector_store(embeddings, collection_name)


def get_text_splitter():
    """Get configured text splitter"""
    return ModelFactory.get_text_splitter()