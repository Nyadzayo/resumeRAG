"""
Pydantic models for API requests and responses.
Defines data validation and serialization schemas for the ResumeRAG system.
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, validator
import uuid
from datetime import datetime


class UploadRequest(BaseModel):
    """Request model for file upload"""
    pass  # File upload is handled via form data


class UploadResponse(BaseModel):
    """Response model for successful file upload"""
    session_id: str = Field(..., description="Unique session identifier")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    file_type: str = Field(..., description="File type/extension")
    chunks_created: int = Field(..., description="Number of text chunks created")
    message: str = Field(default="File uploaded and processed successfully")
    
    @validator('session_id')
    def validate_session_id(cls, v):
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError('session_id must be a valid UUID')


class QueryRequest(BaseModel):
    """Request model for querying resume data"""
    query: str = Field(..., min_length=1, max_length=1000, description="Natural language query")
    session_id: str = Field(..., description="Session identifier from upload")
    query_type: Optional[Literal["single_fact", "list_items", "summary"]] = Field(
        default="single_fact", description="Type of query being performed"
    )
    
    @validator('session_id')
    def validate_session_id(cls, v):
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError('session_id must be a valid UUID')


class QueryResponse(BaseModel):
    """Response model for query results"""
    answer: Optional[str] = Field(..., description="Extracted information or null if not found")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    reasoning: str = Field(..., description="Explanation for the confidence score")
    query_type: str = Field(..., description="Type of query performed")
    retrieved_chunks: Optional[List[str]] = Field(
        default=None, description="Text chunks used for extraction (for debugging)"
    )
    processing_time_ms: Optional[float] = Field(
        default=None, description="Time taken to process the query in milliseconds"
    )


class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str = Field(default="healthy")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(default="1.0.0")
    services: Dict[str, str] = Field(default_factory=dict, description="Status of dependent services")


class ErrorResponse(BaseModel):
    """Standard error response model"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SessionDeleteResponse(BaseModel):
    """Response model for session deletion"""
    session_id: str = Field(..., description="Deleted session identifier")
    message: str = Field(default="Session deleted successfully")
    chunks_deleted: Optional[int] = Field(default=None, description="Number of chunks removed")


class IndexStatsResponse(BaseModel):
    """Response model for indexing statistics"""
    session_id: str = Field(..., description="Session identifier")
    indexing_strategy: str = Field(..., description="Current indexing strategy")
    total_chunks: int = Field(..., description="Total number of indexed chunks")
    total_documents: int = Field(..., description="Total number of documents")
    index_size_mb: Optional[float] = Field(default=None, description="Index size in megabytes")
    last_updated: datetime = Field(..., description="Last index update timestamp")
    metadata_extracted: bool = Field(..., description="Whether metadata extraction was performed")
    entities_found: Optional[List[str]] = Field(
        default=None, description="Extracted entities if entity recognition was enabled"
    )


class ReindexRequest(BaseModel):
    """Request model for reindexing with different strategy"""
    indexing_strategy: Literal["semantic", "keyword", "hybrid", "metadata", "advanced"] = Field(
        ..., description="New indexing strategy to apply"
    )
    chunk_size: Optional[int] = Field(default=None, ge=100, le=2000, description="New chunk size")
    chunk_overlap: Optional[int] = Field(default=None, ge=0, le=500, description="New chunk overlap")
    enable_metadata_extraction: Optional[bool] = Field(
        default=None, description="Enable metadata extraction"
    )
    enable_entity_recognition: Optional[bool] = Field(
        default=None, description="Enable entity recognition"
    )


class ReindexResponse(BaseModel):
    """Response model for reindexing operation"""
    session_id: str = Field(..., description="Session identifier")
    old_strategy: str = Field(..., description="Previous indexing strategy")
    new_strategy: str = Field(..., description="New indexing strategy")
    chunks_created: int = Field(..., description="Number of new chunks created")
    processing_time_ms: float = Field(..., description="Time taken for reindexing")
    message: str = Field(default="Reindexing completed successfully")


class IndexingStrategiesResponse(BaseModel):
    """Response model for available indexing strategies"""
    strategies: List[Dict[str, str]] = Field(..., description="Available indexing strategies")
    current_default: str = Field(..., description="Current default strategy")


class ConfigUpdateRequest(BaseModel):
    """Request model for updating indexing configuration"""
    chunk_size: Optional[int] = Field(default=None, ge=100, le=2000)
    chunk_overlap: Optional[int] = Field(default=None, ge=0, le=500)
    enable_metadata_extraction: Optional[bool] = Field(default=None)
    enable_entity_recognition: Optional[bool] = Field(default=None)
    rerank_results: Optional[bool] = Field(default=None)


class ConfigUpdateResponse(BaseModel):
    """Response model for configuration update"""
    message: str = Field(default="Configuration updated successfully")
    updated_settings: Dict[str, Any] = Field(..., description="Updated configuration values")


class EntityExtractionResult(BaseModel):
    """Model for extracted entities"""
    entity_type: str = Field(..., description="Type of entity (person, organization, etc.)")
    entity_value: str = Field(..., description="Extracted entity value")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence")
    source_chunk: Optional[str] = Field(default=None, description="Source text chunk")


class MetadataExtractionResult(BaseModel):
    """Model for extracted resume metadata"""
    sections: Dict[str, List[str]] = Field(
        default_factory=dict, description="Detected resume sections and their content"
    )
    entities: List[EntityExtractionResult] = Field(
        default_factory=list, description="Extracted entities"
    )
    structured_data: Dict[str, Any] = Field(
        default_factory=dict, description="Structured data extracted from resume"
    )


# Query type specific response models
class SingleFactResponse(QueryResponse):
    """Response for single fact queries (email, phone, name, etc.)"""
    pass


class ListItemsResponse(QueryResponse):
    """Response for list-based queries (skills, experiences, etc.)"""
    items: Optional[List[str]] = Field(default=None, description="Extracted list items")


class SummaryResponse(QueryResponse):
    """Response for summary queries (education background, work history, etc.)"""
    summary_sections: Optional[Dict[str, str]] = Field(
        default=None, description="Organized summary by section"
    )


# Form filling specific models
class FormFieldRequest(BaseModel):
    """Request model for extracting specific form fields"""
    field_label: str = Field(..., description="Form field label (e.g., 'First Name', 'Email Address')")
    session_id: str = Field(..., description="Session identifier from upload")
    
    @validator('session_id')
    def validate_session_id(cls, v):
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError('session_id must be a valid UUID')


class BulkExtractRequest(BaseModel):
    """Request model for extracting multiple form fields at once"""
    fields: List[str] = Field(..., description="List of form field labels to extract")
    session_id: str = Field(..., description="Session identifier from upload")
    
    @validator('session_id')
    def validate_session_id(cls, v):
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError('session_id must be a valid UUID')
    
    @validator('fields')
    def validate_fields(cls, v):
        if not v or len(v) == 0:
            raise ValueError('At least one field must be specified')
        if len(v) > 20:
            raise ValueError('Maximum 20 fields can be extracted at once')
        return v


class FormFieldResponse(BaseModel):
    """Response model for a single form field extraction"""
    field_label: str = Field(..., description="Original field label")
    field_name: str = Field(..., description="Standardized field name")
    value: Optional[str] = Field(..., description="Extracted value or null if not found")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence")
    field_type: str = Field(..., description="Type of field (personal_info, contact, etc.)")
    

class BulkExtractResponse(BaseModel):
    """Response model for bulk form field extraction"""
    session_id: str = Field(..., description="Session identifier")
    total_fields: int = Field(..., description="Total number of fields requested")
    extracted_fields: int = Field(..., description="Number of fields successfully extracted")
    fields: List[FormFieldResponse] = Field(..., description="Extracted field data")
    processing_time_ms: float = Field(..., description="Total processing time")
    

class FormTemplateResponse(BaseModel):
    """Response model for form templates and examples"""
    templates: Dict[str, List[Dict[str, Any]]] = Field(
        ..., description="Form templates organized by category"
    )
    common_fields: List[str] = Field(..., description="Most commonly used form fields")