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

class DocumentResponse(BaseModel):
    id: str
    title: str
    file_type: str
    size: int
    upload_time: datetime
    processing_status: str
    chunk_count: int = 0

class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int
    page: int
    limit: int

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Optional[str] = None