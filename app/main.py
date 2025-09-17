"""
FastAPI application for ResumeRAG system.
Provides REST API endpoints for resume upload and querying.
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.services.rag_service import rag_service
from app.services.model_factory import ModelFactory
from app.services.indexing.indexing_factory import get_available_strategies
from app.services.form_mapper import form_mapper
from app.schemas import (
    QueryRequest, QueryResponse, UploadResponse, HealthResponse,
    ErrorResponse, SessionDeleteResponse, IndexStatsResponse,
    ReindexRequest, ReindexResponse, IndexingStrategiesResponse,
    ConfigUpdateRequest, ConfigUpdateResponse, FormFieldRequest,
    BulkExtractRequest, FormFieldResponse, BulkExtractResponse,
    FormTemplateResponse
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="ResumeRAG API",
    description="Retrieval-Augmented Generation system for resume information extraction",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for frontend
if os.path.exists("frontend"):
    app.mount("/static", StaticFiles(directory="frontend"), name="static")


# Dependency for file validation
async def validate_file(file: UploadFile = File(...)) -> UploadFile:
    """Validate uploaded file"""
    # Check file size
    if file.size and file.size > settings.max_file_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {settings.max_file_size} bytes"
        )
    
    # Check file type
    file_extension = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
    if file_extension not in settings.allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not supported. Allowed types: {settings.allowed_extensions}"
        )
    
    return file


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="InternalServerError",
            message="An unexpected error occurred"
        ).dict()
    )


@app.get("/", response_model=dict)
async def root():
    """Root endpoint - redirect to docs or serve frontend"""
    return {
        "message": "ResumeRAG API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "frontend_url": "/static/index.html"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        # Validate configuration
        model_status = ModelFactory.validate_configuration()
        
        services_status = {
            "embeddings": model_status["embedding_status"],
            "llm": model_status["llm_status"],
            "vector_store": model_status["vector_store_status"]
        }
        
        overall_status = "healthy" if all(s == "ready" for s in services_status.values()) else "degraded"
        
        return HealthResponse(
            status=overall_status,
            services=services_status
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            services={"error": str(e)}
        )


@app.post("/upload", response_model=UploadResponse)
async def upload_resume(file: UploadFile = Depends(validate_file)):
    """
    Upload and process a resume file
    
    - **file**: Resume file (PDF, DOCX, or TXT)
    
    Returns session ID for subsequent queries
    """
    try:
        # Read file content
        file_content = await file.read()
        file_extension = file.filename.split('.')[-1].lower()
        
        # Process the resume
        result = await rag_service.ingest_resume(
            file_content=file_content,
            filename=file.filename,
            file_type=file_extension
        )
        
        logger.info(f"Successfully processed resume: {file.filename}, Session: {result.session_id}")
        return result
        
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.post("/query", response_model=QueryResponse)
async def query_resume(request: QueryRequest):
    """
    Query resume data using natural language
    
    - **query**: Natural language question about the resume
    - **session_id**: Session ID from upload response
    - **query_type**: Type of query (single_fact, list_items, summary)
    
    Returns extracted information with confidence score
    """
    try:
        result = await rag_service.query_resume(
            query=request.query,
            session_id=request.session_id,
            query_type=request.query_type
        )
        
        logger.info(f"Query processed for session {request.session_id}: {request.query}")
        return result
        
    except Exception as e:
        logger.error(f"Query failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.delete("/session/{session_id}", response_model=SessionDeleteResponse)
async def delete_session(session_id: str):
    """
    Delete session data and cleanup resources
    
    - **session_id**: Session identifier to delete
    """
    try:
        success = rag_service.delete_session(session_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        logger.info(f"Session deleted: {session_id}")
        return SessionDeleteResponse(session_id=session_id)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete session failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/session/{session_id}/stats", response_model=IndexStatsResponse)
async def get_session_stats(session_id: str):
    """
    Get indexing statistics for a session
    
    - **session_id**: Session identifier
    """
    try:
        stats = rag_service.get_session_stats(session_id)
        
        if not stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        index_stats = stats["index_stats"]
        
        return IndexStatsResponse(
            session_id=session_id,
            indexing_strategy=index_stats["strategy"],
            total_chunks=index_stats["chunks_created"],
            total_documents=index_stats["documents_indexed"],
            last_updated=datetime.fromisoformat(stats["upload_time"]),
            metadata_extracted=bool(stats["metadata"].get("extracted_entities")),
            entities_found=[
                key.replace("entity_", "") 
                for key in stats["metadata"].keys() 
                if key.startswith("entity_")
            ]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get session stats failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/sessions", response_model=List[Dict[str, Any]])
async def list_sessions():
    """List all active sessions"""
    try:
        sessions = rag_service.get_all_sessions()
        return sessions
    except Exception as e:
        logger.error(f"List sessions failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/index/strategies", response_model=IndexingStrategiesResponse)
async def get_indexing_strategies():
    """Get available indexing strategies"""
    try:
        strategies = get_available_strategies()
        return IndexingStrategiesResponse(
            strategies=strategies,
            current_default=settings.indexing_strategy
        )
    except Exception as e:
        logger.error(f"Get indexing strategies failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/reindex/{session_id}", response_model=ReindexResponse)
async def reindex_session(session_id: str, request: ReindexRequest):
    """
    Reindex session data with different strategy
    
    - **session_id**: Session to reindex
    - **indexing_strategy**: New indexing strategy to apply
    """
    try:
        # This would require implementing reindexing logic in RAG service
        # For now, return a placeholder response
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Reindexing functionality not yet implemented"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reindex failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/index/configure", response_model=ConfigUpdateResponse)
async def update_indexing_config(request: ConfigUpdateRequest):
    """
    Update indexing configuration
    
    - **chunk_size**: New chunk size
    - **chunk_overlap**: New chunk overlap
    - **enable_metadata_extraction**: Enable/disable metadata extraction
    """
    try:
        # This would require implementing configuration update logic
        # For now, return a placeholder response
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Configuration update functionality not yet implemented"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Config update failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Example query endpoints for quick testing
@app.get("/examples/queries")
async def get_example_queries():
    """Get example queries for testing"""
    return {
        "single_fact": [
            "What is the email address?",
            "What is the phone number?", 
            "What is the full name?",
            "What is the current job title?",
            "What university did they attend?"
        ],
        "list_items": [
            "List all technical skills",
            "List all programming languages",
            "List all work experiences",
            "List all certifications"
        ],
        "summary": [
            "Summarize the work experience",
            "Summarize the educational background",
            "What are the key qualifications?"
        ]
    }


# Form Filling Endpoints
@app.post("/extract", response_model=FormFieldResponse)
async def extract_form_field(request: FormFieldRequest):
    """
    Extract a single form field value from resume
    
    - **field_label**: Form field label (e.g., 'First Name', 'Email Address')
    - **session_id**: Session ID from upload response
    
    Optimized for form auto-filling in Chrome extensions
    """
    try:
        # Get standardized query for the field
        field_info = form_mapper.get_field_info(request.field_label)
        
        if field_info:
            query = field_info.extraction_query
            field_name = field_info.field_name
            field_type = field_info.field_type.value
        else:
            # Fallback for unmapped fields
            query = request.field_label
            field_name = request.field_label.lower().replace(" ", "_")
            field_type = "other"
        
        # Use existing RAG service to extract the information
        result = await rag_service.query_resume(
            query=query,
            session_id=request.session_id,
            query_type="single_fact"
        )
        
        return FormFieldResponse(
            field_label=request.field_label,
            field_name=field_name,
            value=result.answer,
            confidence=result.confidence,
            field_type=field_type
        )
        
    except Exception as e:
        logger.error(f"Form field extraction failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.post("/extract/bulk", response_model=BulkExtractResponse)
async def extract_multiple_fields(request: BulkExtractRequest):
    """
    Extract multiple form fields at once for efficient form filling
    
    - **fields**: List of form field labels to extract
    - **session_id**: Session ID from upload response
    
    Perfect for filling entire forms in one API call
    """
    try:
        import time
        start_time = time.time()
        
        extracted_fields = []
        
        for field_label in request.fields:
            # Get standardized query for the field
            field_info = form_mapper.get_field_info(field_label)
            
            if field_info:
                query = field_info.extraction_query
                field_name = field_info.field_name
                field_type = field_info.field_type.value
            else:
                # Fallback for unmapped fields
                query = field_label
                field_name = field_label.lower().replace(" ", "_")
                field_type = "other"
            
            # Extract the field value
            result = await rag_service.query_resume(
                query=query,
                session_id=request.session_id,
                query_type="single_fact"
            )
            
            extracted_fields.append(FormFieldResponse(
                field_label=field_label,
                field_name=field_name,
                value=result.answer,
                confidence=result.confidence,
                field_type=field_type
            ))
        
        processing_time = (time.time() - start_time) * 1000
        successful_extractions = sum(1 for field in extracted_fields if field.value is not None)
        
        return BulkExtractResponse(
            session_id=request.session_id,
            total_fields=len(request.fields),
            extracted_fields=successful_extractions,
            fields=extracted_fields,
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        logger.error(f"Bulk extraction failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.get("/form/templates", response_model=FormTemplateResponse)
async def get_form_templates():
    """
    Get form field templates for different types of applications
    
    Returns organized form fields by category for demo and testing
    """
    try:
        templates = form_mapper.get_example_form_fields()
        
        # Get most common fields
        common_fields = [
            "First Name", "Last Name", "Email", "Phone", 
            "Current Job Title", "University", "Skills"
        ]
        
        return FormTemplateResponse(
            templates=templates,
            common_fields=common_fields
        )
        
    except Exception as e:
        logger.error(f"Get form templates failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


if __name__ == "__main__":
    import uvicorn
    
    # Validate configuration on startup
    try:
        settings.validate_api_keys()
        logger.info("Configuration validated successfully")
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        raise
    
    # Start server
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if settings.debug else "warning"
    )