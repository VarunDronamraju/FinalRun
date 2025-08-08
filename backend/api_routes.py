from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import List, Optional
import logging
from datetime import datetime

from config import settings
from schemas import (
    DocumentResponse, DocumentListResponse, HealthResponse,
    ErrorResponse, BaseResponse
)
from utils import (
    get_file_type, validate_file_size, save_uploaded_file,
    generate_file_id
)

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory storage for MVP (will be replaced with database)
documents_store = {}

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        services={
            "api": "running",
            "database": "unknown",
            "qdrant": "unknown", 
            "ollama": "unknown"
        }
    )

@router.post("/documents/upload", response_model=DocumentResponse)
async def upload_document(file: UploadFile = File(...)):
    """Upload document endpoint"""
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        # Validate file size (50MB limit)
        if not validate_file_size(file_size):
            raise HTTPException(
                status_code=413, 
                detail="File too large. Maximum size is 50MB"
            )
        
        # Get file type
        file_type = get_file_type(file.filename)
        if file_type == "unknown":
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Supported: PDF, DOCX, TXT"
            )
        
        # Save file
        file_path = save_uploaded_file(content, file.filename)
        
        # Create document record
        doc_id = generate_file_id()
        document = DocumentResponse(
            id=doc_id,
            title=file.filename,
            file_type=file_type,
            size=file_size,
            upload_time=datetime.now(),
            processing_status="uploaded",
            chunk_count=0
        )
        
        # Store in memory (temporary)
        documents_store[doc_id] = {
            "document": document,
            "file_path": file_path
        }
        
        logger.info(f"Document uploaded: {file.filename} ({file_size} bytes)")
        return document
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Upload failed")

@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    skip: int = 0,
    limit: int = 10
):
    """List documents endpoint"""
    try:
        docs = list(documents_store.values())
        total = len(docs)
        
        # Simple pagination
        paginated_docs = docs[skip:skip + limit]
        
        return DocumentListResponse(
            documents=[item["document"] for item in paginated_docs],
            total=total,
            page=skip // limit + 1,
            limit=limit
        )
        
    except Exception as e:
        logger.error(f"List documents error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list documents")

@router.get("/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: str):
    """Get specific document endpoint"""
    if doc_id not in documents_store:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return documents_store[doc_id]["document"]

@router.delete("/documents/{doc_id}", response_model=BaseResponse)
async def delete_document(doc_id: str):
    """Delete document endpoint"""
    if doc_id not in documents_store:
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        # Remove file (in production, also remove from vector store)
        import os
        file_path = documents_store[doc_id]["file_path"]
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Remove from store
        del documents_store[doc_id]
        
        return BaseResponse(message="Document deleted successfully")
        
    except Exception as e:
        logger.error(f"Delete error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete document")

# Basic system endpoints
@router.get("/system/info")
async def get_system_info():
    """Get system information"""
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "debug": settings.debug,
        "timestamp": datetime.now().isoformat()
    }

@router.get("/system/models")
async def get_available_models():
    """Get available AI models"""
    return {
        "embedding_model": settings.embedding_model,
        "llm_model": settings.ollama_model,
        "status": "not_loaded"
    }