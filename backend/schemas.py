from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class BaseResponse(BaseModel):
    success: bool = True
    message: str = "Success"

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    services: Dict[str, str]

class DocumentUpload(BaseModel):
    title: str
    file_type: str
    size: int

class DocumentChunk(BaseModel):
    id: str
    index: int
    text: str
    length: int
    created_at: datetime

class DocumentResponse(BaseModel):
    id: str
    title: str
    file_type: str
    size: int
    upload_time: datetime
    processing_status: str
    chunk_count: int = 0
    text_preview: Optional[str] = None

class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int
    page: int
    limit: int

class DocumentChunksResponse(BaseModel):
    document_id: str
    chunks: List[DocumentChunk]
    total_chunks: int

class ProcessDocumentRequest(BaseModel):
    chunk_size: int = 1000
    overlap: int = 100

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Optional[str] = None