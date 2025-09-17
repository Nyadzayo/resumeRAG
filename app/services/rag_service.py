"""
Core RAG service for ResumeRAG system.
Handles document ingestion, vector storage, and information extraction.
"""

import uuid
import io
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# Document processing
import PyPDF2
from docx import Document

# LangChain components
from langchain.schema import Document as LCDocument
from langchain.prompts import PromptTemplate

from app.config import settings
from app.services.model_factory import get_llm, get_embeddings
from app.services.indexing.indexing_factory import create_indexer
from app.services.extractors.entity_extractor import EntityExtractor
from app.services.extractors.section_parser import SectionParser
from app.schemas import (
    QueryResponse, UploadResponse, MetadataExtractionResult,
    EntityExtractionResult
)


# LLM Extraction Prompt Template
EXTRACTION_PROMPT = """You are an expert AI assistant specializing in extracting specific information from resume text. Your task is to act as a precise data parser and return information in a strict JSON format.

**Instructions:**
1. Carefully analyze the provided "Context" which contains snippets from a resume.
2. Find the single piece of information that directly answers the "Query".
3. The answer must be concise and extracted *exactly* from the provided context. Do not infer, modify, or add information.
4. Look for common patterns:
   - Names usually appear at the top of resumes
   - Contact info (email, phone) typically in header sections
   - URLs and links are often in contact sections
   - Job titles and companies appear in experience sections
5. Determine a "confidence" score between 0.0 and 1.0:
   - 1.0: The answer is explicitly stated and clearly visible
   - 0.8: The answer is clearly stated but may require minor extraction
   - 0.5: The answer is implied or requires interpretation
   - 0.2: The information is partially present but unclear
   - 0.0: The answer is not found in the context
6. If you cannot find the answer in the context, the "answer" field must be `null` and the "confidence" must be `0.0`.
7. Your final output must be a single JSON object and nothing else.

**Context from Resume:**
\"\"\"
{retrieved_chunks}
\"\"\"

**Query:**
"{user_query}"

**Output JSON:**
```json
{{
  "answer": "The extracted piece of information, or null if not found",
  "confidence": <float between 0.0 and 1.0>,
  "reasoning": "A brief explanation for your confidence score and extraction."
}}
```"""


class RAGService:
    """Core RAG service for resume processing and querying"""
    
    def __init__(self):
        self.llm = get_llm()
        self.entity_extractor = EntityExtractor()
        self.section_parser = SectionParser()
        self.active_sessions: Dict[str, Any] = {}
    
    async def ingest_resume(self, file_content: bytes, filename: str, file_type: str) -> UploadResponse:
        """
        Ingest a resume file and create vector embeddings
        
        Args:
            file_content: Raw file bytes
            filename: Original filename
            file_type: File extension/type
            
        Returns:
            UploadResponse with session details
        """
        try:
            # Generate session ID
            session_id = str(uuid.uuid4())
            
            # Extract text from file
            text_content = self._extract_text_from_file(file_content, file_type)
            
            if not text_content.strip():
                raise ValueError("No text content found in the uploaded file")
            
            # Create indexer for this session
            indexer = create_indexer(session_id=session_id)
            
            # Prepare metadata
            metadata = {
                "filename": filename,
                "file_type": file_type,
                "file_size": len(file_content),
                "upload_time": datetime.utcnow().isoformat()
            }
            
            # Extract entities and sections if enabled
            if settings.enable_metadata_extraction:
                extracted_metadata = self._extract_metadata(text_content)
                metadata.update(extracted_metadata)
            
            # Index the document
            index_result = indexer.index_document(text_content, metadata)
            
            # Store session info
            self.active_sessions[session_id] = {
                "indexer": indexer,
                "filename": filename,
                "file_type": file_type,
                "upload_time": datetime.utcnow(),
                "metadata": metadata,
                "text_content": text_content
            }
            
            return UploadResponse(
                session_id=session_id,
                filename=filename,
                file_size=len(file_content),
                file_type=file_type,
                chunks_created=index_result["chunks_created"]
            )
            
        except Exception as e:
            raise Exception(f"Failed to ingest resume: {str(e)}")
    
    async def query_resume(self, query: str, session_id: str, query_type: str = "single_fact") -> QueryResponse:
        """
        Query resume data using RAG
        
        Args:
            query: Natural language query
            session_id: Session identifier
            query_type: Type of query (single_fact, list_items, summary)
            
        Returns:
            QueryResponse with extracted information
        """
        start_time = time.time()
        
        try:
            # Validate session
            if session_id not in self.active_sessions:
                raise ValueError(f"Session {session_id} not found")
            
            session_data = self.active_sessions[session_id]
            indexer = session_data["indexer"]
            
            # Retrieve relevant chunks - increased from 5 to 8 for better coverage
            search_results = indexer.search(query, top_k=8)
            
            if not search_results:
                return QueryResponse(
                    answer=None,
                    confidence=0.0,
                    reasoning="No relevant information found in the resume",
                    query_type=query_type,
                    processing_time_ms=(time.time() - start_time) * 1000
                )
            
            # Prepare context for LLM
            retrieved_chunks = "\n\n".join([result.content for result in search_results])
            
            # Create prompt
            prompt = PromptTemplate(
                template=EXTRACTION_PROMPT,
                input_variables=["retrieved_chunks", "user_query"]
            )
            
            formatted_prompt = prompt.format(
                retrieved_chunks=retrieved_chunks,
                user_query=query
            )
            
            # Query LLM
            llm_response = self.llm.invoke(formatted_prompt)
            
            # Parse LLM response
            extraction_result = self._parse_llm_response(llm_response.content if hasattr(llm_response, 'content') else str(llm_response))
            
            processing_time = (time.time() - start_time) * 1000
            
            return QueryResponse(
                answer=extraction_result.get("answer"),
                confidence=extraction_result.get("confidence", 0.0),
                reasoning=extraction_result.get("reasoning", ""),
                query_type=query_type,
                retrieved_chunks=[result.content for result in search_results] if settings.debug else None,
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            return QueryResponse(
                answer=None,
                confidence=0.0,
                reasoning=f"Error processing query: {str(e)}",
                query_type=query_type,
                processing_time_ms=processing_time
            )
    
    def _extract_text_from_file(self, file_content: bytes, file_type: str) -> str:
        """Extract text content from different file types"""
        file_type = file_type.lower()
        
        try:
            if file_type == "pdf":
                return self._extract_text_from_pdf(file_content)
            elif file_type in ["docx", "doc"]:
                return self._extract_text_from_docx(file_content)
            elif file_type == "txt":
                return file_content.decode('utf-8')
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
        except Exception as e:
            raise Exception(f"Failed to extract text from {file_type} file: {str(e)}")
    
    def _extract_text_from_pdf(self, file_content: bytes) -> str:
        """Extract text from PDF file"""
        try:
            pdf_file = io.BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text_content = ""
            for page in pdf_reader.pages:
                text_content += page.extract_text() + "\n"
            
            return text_content.strip()
        except Exception as e:
            raise Exception(f"Failed to process PDF: {str(e)}")
    
    def _extract_text_from_docx(self, file_content: bytes) -> str:
        """Extract text from DOCX file"""
        try:
            docx_file = io.BytesIO(file_content)
            doc = Document(docx_file)
            
            text_content = ""
            for paragraph in doc.paragraphs:
                text_content += paragraph.text + "\n"
            
            return text_content.strip()
        except Exception as e:
            raise Exception(f"Failed to process DOCX: {str(e)}")
    
    def _extract_metadata(self, text: str) -> Dict[str, Any]:
        """Extract metadata from resume text"""
        metadata = {}
        
        try:
            # Extract entities
            if settings.enable_entity_recognition:
                entities = self.entity_extractor.extract_all(text)
                best_entities = self.entity_extractor.get_best_entities_by_type(entities)
                
                # Convert to serializable format
                entities_data = {}
                for entity_type, entity in best_entities.items():
                    # Store only the entity value as string for ChromaDB compatibility
                    entities_data[f"entity_{entity_type}"] = str(entity.value)
                
                metadata["extracted_entities"] = len(entities_data)
                metadata.update(entities_data)  # Add entities as separate fields
            
            # Extract sections
            sections = self.section_parser.parse_sections(text)
            sections_dict = self.section_parser.get_sections_dict(sections)
            # Convert sections to simple string values for ChromaDB
            for key, value in sections_dict.items():
                metadata[f"section_{key}"] = str(value)[:500]  # Limit length
            
            # Extract structured data
            structured_data = self.section_parser.extract_structured_data(sections)
            metadata["has_structured_data"] = len(structured_data) > 0
            
        except Exception as e:
            metadata["metadata_extraction_error"] = str(e)
        
        return metadata
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM JSON response safely"""
        try:
            # Try to find JSON block in response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
            else:
                # Fallback: try to parse entire response
                return json.loads(response)
                
        except json.JSONDecodeError:
            # If JSON parsing fails, return a default response
            return {
                "answer": None,
                "confidence": 0.0,
                "reasoning": "Failed to parse LLM response"
            }
    
    def delete_session(self, session_id: str) -> bool:
        """Delete session data"""
        try:
            if session_id in self.active_sessions:
                session_data = self.active_sessions[session_id]
                indexer = session_data["indexer"]
                
                # Delete indexer data
                indexer.delete_session_data()
                
                # Remove from active sessions
                del self.active_sessions[session_id]
                
                return True
            return False
        except Exception as e:
            print(f"Error deleting session {session_id}: {e}")
            return False
    
    def get_session_stats(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a session"""
        if session_id not in self.active_sessions:
            return None
        
        session_data = self.active_sessions[session_id]
        indexer = session_data["indexer"]
        
        stats = {
            "session_id": session_id,
            "filename": session_data["filename"],
            "upload_time": session_data["upload_time"].isoformat(),
            "index_stats": indexer.get_index_stats(),
            "metadata": session_data.get("metadata", {})
        }
        
        return stats
    
    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """Get information about all active sessions"""
        sessions = []
        for session_id, session_data in self.active_sessions.items():
            sessions.append({
                "session_id": session_id,
                "filename": session_data["filename"],
                "upload_time": session_data["upload_time"].isoformat(),
                "file_type": session_data["file_type"]
            })
        return sessions


# Global RAG service instance
rag_service = RAGService()