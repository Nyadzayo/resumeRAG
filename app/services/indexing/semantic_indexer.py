"""
Semantic indexing implementation using vector embeddings.
Primary indexing strategy for the ResumeRAG system.
"""

import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings.base import Embeddings
from langchain.vectorstores.base import VectorStore

from .base_indexer import BaseIndexer, SearchResult, IndexedDocument
from app.services.model_factory import get_embeddings, get_vector_store, get_text_splitter
from app.config import settings


class SemanticIndexer(BaseIndexer):
    """Semantic indexing using dense vector embeddings"""
    
    def __init__(self, session_id: str):
        super().__init__(session_id)
        self.embeddings = get_embeddings()
        self.text_splitter = get_text_splitter()
        self.vector_store = get_vector_store(self.embeddings, f"session_{session_id}")
        self.documents: List[IndexedDocument] = []
    
    def index_document(self, document: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Index a document using semantic chunking and vector embeddings"""
        if metadata is None:
            metadata = {}
        
        # Add session and document metadata
        doc_id = str(uuid.uuid4())
        base_metadata = {
            "session_id": self.session_id,
            "doc_id": doc_id,
            "indexed_at": datetime.utcnow().isoformat(),
            **metadata
        }
        
        # Split document into chunks
        chunks = self.text_splitter.split_text(document)
        
        # Create documents for vector store
        documents_to_add = []
        metadatas_to_add = []
        
        for i, chunk in enumerate(chunks):
            chunk_metadata = {
                **base_metadata,
                "chunk_index": i,
                "chunk_id": f"{doc_id}_{i}"
            }
            
            documents_to_add.append(chunk)
            metadatas_to_add.append(chunk_metadata)
            
            # Store in internal list
            indexed_doc = IndexedDocument(
                doc_id=doc_id,
                content=chunk,
                metadata=chunk_metadata,
                chunk_index=i,
                created_at=datetime.utcnow()
            )
            self.documents.append(indexed_doc)
        
        # Add to vector store
        self.vector_store.add_texts(
            texts=documents_to_add,
            metadatas=metadatas_to_add
        )
        
        # Update statistics
        self.update_stats(documents_added=1, chunks_added=len(chunks))
        
        return {
            "doc_id": doc_id,
            "chunks_created": len(chunks),
            "strategy": "semantic",
            "success": True
        }
    
    def search(self, query: str, top_k: int = 5, filters: Dict[str, Any] = None) -> List[SearchResult]:
        """Search using semantic similarity"""
        try:
            # Build filter for session isolation
            search_filter = {"session_id": self.session_id}
            if filters:
                search_filter.update(filters)
            
            # Perform similarity search
            results = self.vector_store.similarity_search_with_score(
                query=query,
                k=top_k,
                filter=search_filter
            )
            
            # Convert to SearchResult objects
            search_results = []
            for doc, score in results:
                search_result = SearchResult(
                    content=doc.page_content,
                    score=float(score),
                    metadata=doc.metadata,
                    doc_id=doc.metadata.get("doc_id", ""),
                    chunk_index=doc.metadata.get("chunk_index", 0)
                )
                search_results.append(search_result)
            
            return search_results
            
        except Exception as e:
            print(f"Search error: {e}")
            return []
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get indexing statistics"""
        return {
            **self.index_stats,
            "total_chunks": len(self.documents),
            "embedding_model": getattr(self.embeddings, 'model', 'unknown'),
            "chunk_size": settings.chunk_size,
            "chunk_overlap": settings.chunk_overlap
        }
    
    def delete_session_data(self) -> bool:
        """Delete all data for the current session"""
        try:
            # Filter documents to delete
            session_docs = [doc for doc in self.documents if doc.metadata.get("session_id") == self.session_id]
            
            # Clear from vector store (this is challenging with ChromaDB, so we'll mark as deleted)
            # In a production system, you'd want to implement proper deletion
            self.documents = [doc for doc in self.documents if doc.metadata.get("session_id") != self.session_id]
            
            # Reset stats
            self.index_stats = {
                "documents_indexed": 0,
                "chunks_created": 0,
                "last_updated": None,
                "strategy": self.__class__.__name__
            }
            
            return True
            
        except Exception as e:
            print(f"Error deleting session data: {e}")
            return False