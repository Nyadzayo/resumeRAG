"""
Base indexing interface and abstract classes for the ResumeRAG system.
Defines the contract for different indexing strategies.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class IndexedDocument:
    """Represents an indexed document with metadata"""
    doc_id: str
    content: str
    metadata: Dict[str, Any]
    chunk_index: int
    created_at: datetime
    
    
@dataclass
class SearchResult:
    """Represents a search result from the index"""
    content: str
    score: float
    metadata: Dict[str, Any]
    doc_id: str
    chunk_index: int


class BaseIndexer(ABC):
    """Abstract base class for document indexing strategies"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.index_stats = {
            "documents_indexed": 0,
            "chunks_created": 0,
            "last_updated": None,
            "strategy": self.__class__.__name__
        }
    
    @abstractmethod
    def index_document(self, document: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Index a document with optional metadata
        
        Args:
            document: The document text to index
            metadata: Optional metadata dictionary
            
        Returns:
            Dictionary with indexing results and statistics
        """
        pass
    
    @abstractmethod
    def search(self, query: str, top_k: int = 5, filters: Dict[str, Any] = None) -> List[SearchResult]:
        """
        Search the index for relevant documents
        
        Args:
            query: Search query string
            top_k: Number of results to return
            filters: Optional filters to apply
            
        Returns:
            List of SearchResult objects
        """
        pass
    
    @abstractmethod
    def get_index_stats(self) -> Dict[str, Any]:
        """
        Get indexing statistics
        
        Returns:
            Dictionary with index statistics
        """
        pass
    
    @abstractmethod
    def delete_session_data(self) -> bool:
        """
        Delete all data for the current session
        
        Returns:
            True if successful, False otherwise
        """
        pass
    
    def update_stats(self, documents_added: int = 0, chunks_added: int = 0):
        """Update internal statistics"""
        self.index_stats["documents_indexed"] += documents_added
        self.index_stats["chunks_created"] += chunks_added
        self.index_stats["last_updated"] = datetime.utcnow()