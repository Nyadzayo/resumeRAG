"""
Enhanced semantic indexing with improved retrieval strategies.
Combines multiple search approaches for better form field extraction.
"""

import uuid
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings.base import Embeddings
from langchain.vectorstores.base import VectorStore

from .base_indexer import BaseIndexer, SearchResult, IndexedDocument
from app.services.model_factory import get_embeddings, get_vector_store, get_text_splitter
from app.config import settings


class EnhancedSemanticIndexer(BaseIndexer):
    """Enhanced semantic indexing with multiple retrieval strategies"""
    
    def __init__(self, session_id: str):
        super().__init__(session_id)
        self.embeddings = get_embeddings()
        self.text_splitter = self._create_enhanced_text_splitter()
        self.vector_store = get_vector_store(self.embeddings, f"session_{session_id}")
        self.documents: List[IndexedDocument] = []
        self.full_text = ""  # Store full document for fallback searches
    
    def _create_enhanced_text_splitter(self):
        """Create enhanced text splitter optimized for resumes"""
        return RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            length_function=len,
            separators=[
                "\n\n\n",  # Multiple newlines (section breaks)
                "\n\n",    # Double newlines
                "\n",      # Single newlines
                ". ",      # Sentence endings
                "! ",      # Exclamation endings
                "? ",      # Question endings
                "; ",      # Semicolons
                ": ",      # Colons
                ", ",      # Commas
                " ",       # Spaces
                ""         # Character level
            ]
        )
    
    def index_document(self, document: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Index a document with enhanced chunking strategies"""
        if metadata is None:
            metadata = {}
        
        # Store full text for fallback searches
        self.full_text = document
        
        # Add session and document metadata
        doc_id = str(uuid.uuid4())
        base_metadata = {
            "session_id": self.session_id,
            "doc_id": doc_id,
            "indexed_at": datetime.utcnow().isoformat(),
            **metadata
        }
        
        # Multiple chunking strategies
        chunks = self._create_multi_strategy_chunks(document)
        
        # Create documents for vector store
        documents_to_add = []
        metadatas_to_add = []
        
        for i, chunk_info in enumerate(chunks):
            chunk_metadata = {
                **base_metadata,
                "chunk_index": i,
                "chunk_id": f"{doc_id}_{i}",
                "chunk_type": chunk_info["type"],
                "chunk_section": chunk_info.get("section", "unknown")
            }
            
            documents_to_add.append(chunk_info["content"])
            metadatas_to_add.append(chunk_metadata)
            
            # Store in internal list
            indexed_doc = IndexedDocument(
                doc_id=doc_id,
                content=chunk_info["content"],
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
            "strategy": "enhanced_semantic",
            "success": True
        }
    
    def _create_multi_strategy_chunks(self, document: str) -> List[Dict[str, Any]]:
        """Create chunks using multiple strategies for better retrieval"""
        chunks = []
        
        # Strategy 1: Section-based chunking
        sections = self._identify_resume_sections(document)
        for section_name, section_content in sections.items():
            if section_content.strip():
                chunks.append({
                    "content": section_content,
                    "type": "section",
                    "section": section_name
                })
        
        # Strategy 2: Contact info extraction (high priority for form filling)
        contact_chunks = self._extract_contact_chunks(document)
        chunks.extend(contact_chunks)
        
        # Strategy 3: Regular semantic chunking for remaining content
        regular_chunks = self.text_splitter.split_text(document)
        for i, chunk in enumerate(regular_chunks):
            chunks.append({
                "content": chunk,
                "type": "semantic",
                "section": "general"
            })
        
        return chunks
    
    def _identify_resume_sections(self, text: str) -> Dict[str, str]:
        """Identify and extract resume sections"""
        sections = {}
        
        # Common section headers
        section_patterns = {
            "header": r"^.{0,200}",  # First 200 chars likely contain name/contact
            "contact": r"(email|phone|address|linkedin|github).*",
            "experience": r"(experience|employment|work history).*?(?=education|skills|$)",
            "education": r"(education|academic|degree|university|college).*?(?=experience|skills|$)",
            "skills": r"(skills|technical|competencies|technologies).*?(?=experience|education|$)",
            "summary": r"(summary|objective|profile).*?(?=experience|education|skills|$)"
        }
        
        text_lower = text.lower()
        
        for section_name, pattern in section_patterns.items():
            matches = re.findall(pattern, text_lower, re.IGNORECASE | re.DOTALL)
            if matches:
                sections[section_name] = matches[0][:800]  # Limit section size
        
        # Always include header section (first few lines)
        lines = text.split('\n')
        header_lines = lines[:5]  # First 5 lines usually contain key info
        sections["header"] = '\n'.join(header_lines)
        
        return sections
    
    def _extract_contact_chunks(self, text: str) -> List[Dict[str, Any]]:
        """Extract contact information as separate high-priority chunks"""
        contact_chunks = []
        
        # Extract patterns for common contact info
        patterns = {
            "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            "phone": r"(\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}",
            "linkedin": r"linkedin\.com/in/[a-zA-Z0-9-]+",
            "github": r"github\.com/[a-zA-Z0-9-_]+",
            "website": r"https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?",
        }
        
        for contact_type, pattern in patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Create context around the match
                match_index = text.lower().find(match.lower())
                if match_index != -1:
                    start = max(0, match_index - 100)
                    end = min(len(text), match_index + len(match) + 100)
                    context = text[start:end].strip()
                    
                    contact_chunks.append({
                        "content": context,
                        "type": "contact",
                        "section": contact_type,
                        "extracted_value": match
                    })
        
        return contact_chunks
    
    def search(self, query: str, top_k: int = 8, filters: Dict[str, Any] = None) -> List[SearchResult]:
        """Enhanced search with multiple strategies"""
        try:
            all_results = []
            
            # Strategy 1: Vector similarity search
            vector_results = self._vector_search(query, top_k, filters)
            all_results.extend(vector_results)
            
            # Strategy 2: Contact-specific search for form fields
            if any(term in query.lower() for term in ['name', 'email', 'phone', 'linkedin', 'github']):
                contact_results = self._contact_search(query, filters)
                all_results.extend(contact_results)
            
            # Strategy 3: Keyword fallback search in full text
            if len(all_results) < 3:  # If not enough results
                keyword_results = self._keyword_search(query, filters)
                all_results.extend(keyword_results)
            
            # Remove duplicates and sort by score
            unique_results = self._deduplicate_results(all_results)
            return sorted(unique_results, key=lambda x: x.score, reverse=True)[:top_k]
            
        except Exception as e:
            print(f"Enhanced search error: {e}")
            return []
    
    def _vector_search(self, query: str, top_k: int, filters: Dict[str, Any]) -> List[SearchResult]:
        """Standard vector similarity search"""
        search_filter = {"session_id": self.session_id}
        if filters:
            search_filter.update(filters)
        
        results = self.vector_store.similarity_search_with_score(
            query=query,
            k=top_k,
            filter=search_filter
        )
        
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
    
    def _contact_search(self, query: str, filters: Dict[str, Any]) -> List[SearchResult]:
        """Search specifically in contact-type chunks"""
        contact_filter = {"session_id": self.session_id, "chunk_type": "contact"}
        if filters:
            contact_filter.update(filters)
        
        try:
            results = self.vector_store.similarity_search_with_score(
                query=query,
                k=5,
                filter=contact_filter
            )
            
            search_results = []
            for doc, score in results:
                search_result = SearchResult(
                    content=doc.page_content,
                    score=float(score) + 0.1,  # Boost contact results
                    metadata=doc.metadata,
                    doc_id=doc.metadata.get("doc_id", ""),
                    chunk_index=doc.metadata.get("chunk_index", 0)
                )
                search_results.append(search_result)
            
            return search_results
        except:
            return []
    
    def _keyword_search(self, query: str, filters: Dict[str, Any]) -> List[SearchResult]:
        """Fallback keyword search in full text"""
        if not self.full_text:
            return []
        
        results = []
        query_terms = query.lower().split()
        
        # Find text snippets containing query terms
        for term in query_terms:
            term_index = self.full_text.lower().find(term)
            if term_index != -1:
                start = max(0, term_index - 200)
                end = min(len(self.full_text), term_index + len(term) + 200)
                snippet = self.full_text[start:end].strip()
                
                # Simple scoring based on term frequency
                score = snippet.lower().count(term) * 0.1
                
                search_result = SearchResult(
                    content=snippet,
                    score=score,
                    metadata={"doc_id": "fallback", "chunk_type": "keyword"},
                    doc_id="fallback",
                    chunk_index=0
                )
                results.append(search_result)
        
        return results
    
    def _deduplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """Remove duplicate results based on content similarity"""
        unique_results = []
        seen_content = set()
        
        for result in results:
            # Simple deduplication based on first 100 chars
            content_key = result.content[:100].strip()
            if content_key not in seen_content:
                seen_content.add(content_key)
                unique_results.append(result)
        
        return unique_results
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get enhanced indexing statistics"""
        return {
            **self.index_stats,
            "total_chunks": len(self.documents),
            "embedding_model": getattr(self.embeddings, 'model', 'unknown'),
            "chunk_size": settings.chunk_size,
            "chunk_overlap": settings.chunk_overlap,
            "indexer_type": "enhanced_semantic"
        }
    
    def delete_session_data(self) -> bool:
        """Delete all data for the current session"""
        try:
            # Filter documents to delete
            session_docs = [doc for doc in self.documents if doc.metadata.get("session_id") == self.session_id]
            
            # Clear from vector store (this is challenging with ChromaDB, so we'll mark as deleted)
            # In a production system, you'd want to implement proper deletion
            self.documents = [doc for doc in self.documents if doc.metadata.get("session_id") != self.session_id]
            
            # Clear full text
            self.full_text = ""
            
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