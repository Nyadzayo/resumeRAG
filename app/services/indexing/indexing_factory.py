"""
Factory for creating indexers based on configuration.
Supports multiple indexing strategies and easy switching.
"""

from typing import Dict, Any, List
from .base_indexer import BaseIndexer
from .enhanced_semantic_indexer import EnhancedSemanticIndexer
from .semantic_indexer import SemanticIndexer
from .keyword_indexer import KeywordIndexer
from app.config import settings


class IndexingFactory:
    """Factory for creating indexing strategies"""
    
    _indexer_classes = {
        "semantic": EnhancedSemanticIndexer,  # Use enhanced version by default
        "basic_semantic": SemanticIndexer,
        "keyword": KeywordIndexer,
        # Note: hybrid, metadata, and advanced indexers would be implemented here
    }
    
    @classmethod
    def create_indexer(cls, strategy: str, session_id: str) -> BaseIndexer:
        """
        Create an indexer instance based on strategy
        
        Args:
            strategy: Indexing strategy name
            session_id: Session identifier
            
        Returns:
            BaseIndexer instance
        """
        strategy = strategy.lower()
        
        if strategy not in cls._indexer_classes:
            available = ", ".join(cls._indexer_classes.keys())
            raise ValueError(f"Unknown indexing strategy: {strategy}. Available: {available}")
        
        indexer_class = cls._indexer_classes[strategy]
        return indexer_class(session_id)
    
    @classmethod
    def get_default_indexer(cls, session_id: str) -> BaseIndexer:
        """Create indexer using default strategy from config"""
        return cls.create_indexer(settings.indexing_strategy, session_id)
    
    @classmethod
    def get_available_strategies(cls) -> List[Dict[str, str]]:
        """Get list of available indexing strategies"""
        strategies = []
        
        for strategy_name, strategy_class in cls._indexer_classes.items():
            strategies.append({
                "name": strategy_name,
                "class": strategy_class.__name__,
                "description": cls._get_strategy_description(strategy_name)
            })
        
        return strategies
    
    @classmethod
    def _get_strategy_description(cls, strategy: str) -> str:
        """Get description for indexing strategy"""
        descriptions = {
            "semantic": "Enhanced semantic indexing with multi-strategy retrieval optimized for form filling",
            "basic_semantic": "Basic dense vector embeddings with cosine similarity search",
            "keyword": "BM25 scoring with term frequency analysis",
            "hybrid": "Combination of semantic and keyword indexing",
            "metadata": "Structured data extraction with entity recognition",
            "advanced": "Multi-vector representations with query expansion"
        }
        
        return descriptions.get(strategy, "No description available")


# Convenience functions
def create_indexer(strategy: str = None, session_id: str = None) -> BaseIndexer:
    """Create an indexer with optional strategy override"""
    if strategy is None:
        strategy = settings.indexing_strategy
    
    return IndexingFactory.create_indexer(strategy, session_id)


def get_available_strategies() -> List[Dict[str, str]]:
    """Get available indexing strategies"""
    return IndexingFactory.get_available_strategies()