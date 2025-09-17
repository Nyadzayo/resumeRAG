"""
Keyword-based indexing using BM25 and TF-IDF scoring.
Alternative indexing strategy for exact match requirements.
"""

import uuid
import math
from collections import Counter, defaultdict
from typing import List, Dict, Any, Optional
from datetime import datetime
import re

from .base_indexer import BaseIndexer, SearchResult, IndexedDocument
from app.config import settings


class KeywordIndexer(BaseIndexer):
    """Keyword-based indexing using BM25 algorithm"""
    
    def __init__(self, session_id: str):
        super().__init__(session_id)
        self.documents: List[IndexedDocument] = []
        self.term_frequencies: Dict[str, Dict[str, int]] = {}
        self.document_frequencies: Dict[str, int] = {}
        self.total_documents = 0
        self.avg_doc_length = 0
        self.doc_lengths: Dict[str, int] = {}
        
        # BM25 parameters
        self.k1 = 1.5
        self.b = 0.75
    
    def _preprocess_text(self, text: str) -> List[str]:
        """Preprocess text for keyword indexing"""
        # Convert to lowercase and split into words
        text = text.lower()
        # Remove punctuation and split
        words = re.findall(r'\b\w+\b', text)
        return words
    
    def _chunk_text(self, text: str) -> List[str]:
        """Split text into chunks for indexing"""
        # Simple sentence-based chunking for keyword indexing
        sentences = re.split(r'[.!?]+', text)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            if len(current_chunk) + len(sentence) < settings.chunk_size:
                current_chunk += " " + sentence if current_chunk else sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks if chunks else [text]
    
    def index_document(self, document: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Index a document using keyword extraction and BM25"""
        if metadata is None:
            metadata = {}
        
        # Generate document ID
        doc_id = str(uuid.uuid4())
        base_metadata = {
            "session_id": self.session_id,
            "doc_id": doc_id,
            "indexed_at": datetime.utcnow().isoformat(),
            **metadata
        }
        
        # Chunk the document
        chunks = self._chunk_text(document)
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}_{i}"
            chunk_metadata = {
                **base_metadata,
                "chunk_index": i,
                "chunk_id": chunk_id
            }
            
            # Preprocess text
            words = self._preprocess_text(chunk)
            word_counts = Counter(words)
            
            # Store document
            indexed_doc = IndexedDocument(
                doc_id=chunk_id,
                content=chunk,
                metadata=chunk_metadata,
                chunk_index=i,
                created_at=datetime.utcnow()
            )
            self.documents.append(indexed_doc)
            
            # Update term frequencies
            self.term_frequencies[chunk_id] = dict(word_counts)
            self.doc_lengths[chunk_id] = len(words)
            
            # Update document frequencies
            unique_words = set(words)
            for word in unique_words:
                self.document_frequencies[word] = self.document_frequencies.get(word, 0) + 1
        
        self.total_documents += len(chunks)
        self._update_avg_doc_length()
        
        # Update statistics
        self.update_stats(documents_added=1, chunks_added=len(chunks))
        
        return {
            "doc_id": doc_id,
            "chunks_created": len(chunks),
            "strategy": "keyword",
            "success": True
        }
    
    def _update_avg_doc_length(self):
        """Update average document length for BM25"""
        if self.doc_lengths:
            self.avg_doc_length = sum(self.doc_lengths.values()) / len(self.doc_lengths)
    
    def _calculate_bm25_score(self, query_terms: List[str], doc_id: str) -> float:
        """Calculate BM25 score for a document"""
        if doc_id not in self.term_frequencies:
            return 0.0
        
        score = 0.0
        doc_length = self.doc_lengths.get(doc_id, 0)
        
        for term in query_terms:
            if term in self.term_frequencies[doc_id]:
                tf = self.term_frequencies[doc_id][term]
                df = self.document_frequencies.get(term, 0)
                
                if df == 0:
                    continue
                
                # IDF calculation
                idf = math.log((self.total_documents - df + 0.5) / (df + 0.5))
                
                # BM25 formula
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * (doc_length / self.avg_doc_length))
                
                score += idf * (numerator / denominator)
        
        return score
    
    def search(self, query: str, top_k: int = 5, filters: Dict[str, Any] = None) -> List[SearchResult]:
        """Search using BM25 keyword scoring"""
        if not self.documents:
            return []
        
        # Preprocess query
        query_terms = self._preprocess_text(query)
        if not query_terms:
            return []
        
        # Calculate scores for all documents
        scores = []
        for doc in self.documents:
            # Apply session filter
            if doc.metadata.get("session_id") != self.session_id:
                continue
            
            # Apply additional filters
            if filters:
                skip_doc = False
                for key, value in filters.items():
                    if doc.metadata.get(key) != value:
                        skip_doc = True
                        break
                if skip_doc:
                    continue
            
            score = self._calculate_bm25_score(query_terms, doc.doc_id)
            if score > 0:
                scores.append((doc, score))
        
        # Sort by score and return top_k
        scores.sort(key=lambda x: x[1], reverse=True)
        scores = scores[:top_k]
        
        # Convert to SearchResult objects
        results = []
        for doc, score in scores:
            result = SearchResult(
                content=doc.content,
                score=score,
                metadata=doc.metadata,
                doc_id=doc.metadata.get("doc_id", ""),
                chunk_index=doc.chunk_index
            )
            results.append(result)
        
        return results
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get indexing statistics"""
        return {
            **self.index_stats,
            "total_chunks": len(self.documents),
            "unique_terms": len(self.document_frequencies),
            "avg_doc_length": self.avg_doc_length,
            "bm25_k1": self.k1,
            "bm25_b": self.b
        }
    
    def delete_session_data(self) -> bool:
        """Delete all data for the current session"""
        try:
            # Filter out session documents
            session_docs = [doc for doc in self.documents if doc.metadata.get("session_id") == self.session_id]
            self.documents = [doc for doc in self.documents if doc.metadata.get("session_id") != self.session_id]
            
            # Remove term frequencies for session documents
            for doc in session_docs:
                if doc.doc_id in self.term_frequencies:
                    del self.term_frequencies[doc.doc_id]
                if doc.doc_id in self.doc_lengths:
                    del self.doc_lengths[doc.doc_id]
            
            # Recalculate document frequencies
            self.document_frequencies = {}
            for doc_id, term_freq in self.term_frequencies.items():
                for term in term_freq.keys():
                    self.document_frequencies[term] = self.document_frequencies.get(term, 0) + 1
            
            self.total_documents = len(self.documents)
            self._update_avg_doc_length()
            
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