from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import List, Optional
import logging
from datetime import datetime

from config import settings    
from schemas import (
    DocumentResponse, DocumentListResponse, HealthResponse,
    ErrorResponse, BaseResponse, DocumentChunksResponse,
    ProcessDocumentRequest, DocumentChunk
)
from utils import (
    get_file_type, validate_file_size, save_uploaded_file,
    generate_file_id, validate_chunk_quality
)
from documents import document_processor
from schemas import EmbeddingResponse, DocumentChunkWithEmbedding

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
                detail="Unsupported file type. Supported: PDF, DOCX, TXT, MD"
            )
        
        # Save file
        file_path = save_uploaded_file(content, file.filename)
        
        # Extract text
        try:
            extracted_text = document_processor.extract_text(file_path, file_type)
            text_preview = extracted_text[:200] + "..." if len(extracted_text) > 200 else extracted_text
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            extracted_text = ""
            text_preview = "Text extraction failed"
        
        # Create document record
        doc_id = generate_file_id()
        document = DocumentResponse(
            id=doc_id,
            title=file.filename,
            file_type=file_type,
            size=file_size,
            upload_time=datetime.now(),
            processing_status="extracted",
            chunk_count=0,
            text_preview=text_preview
        )
        
        # Store in memory (temporary)
        documents_store[doc_id] = {
            "document": document,
            "file_path": file_path,
            "extracted_text": extracted_text,
            "chunks": []
        }
        
        logger.info(f"Document uploaded and processed: {file.filename} ({file_size} bytes)")
        return document
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Upload failed")

@router.post("/documents/{doc_id}/process", response_model=DocumentChunksResponse)
async def process_document(
    doc_id: str,
    request: ProcessDocumentRequest = ProcessDocumentRequest()
):
    """Process document into chunks"""
    if doc_id not in documents_store:
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        doc_data = documents_store[doc_id]
        extracted_text = doc_data["extracted_text"]
        
        if not extracted_text:
            raise HTTPException(status_code=400, detail="No text extracted from document")
        
        # Chunk the document
        chunks = document_processor.chunk_document(
            extracted_text,
            chunk_size=request.chunk_size,
            overlap=request.overlap
        )
        
        # Filter out poor quality chunks
        quality_chunks = [
            chunk for chunk in chunks
            if validate_chunk_quality(chunk["text"])
        ]
        
        # Convert to response format
        chunk_responses = [
            DocumentChunk(
                id=chunk["id"],
                index=chunk["index"],
                text=chunk["text"],
                length=chunk["length"],
                created_at=chunk["created_at"]
            )
            for chunk in quality_chunks
        ]
        
        # Update document with chunks
        doc_data["chunks"] = quality_chunks
        doc_data["document"].chunk_count = len(quality_chunks)
        doc_data["document"].processing_status = "chunked"
        
        logger.info(f"Document chunked: {doc_id} ({len(quality_chunks)} chunks)")
        
        return DocumentChunksResponse(
            document_id=doc_id,
            chunks=chunk_responses,
            total_chunks=len(quality_chunks)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Processing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Document processing failed")

@router.get("/documents/{doc_id}/chunks", response_model=DocumentChunksResponse)
async def get_document_chunks(doc_id: str):
    """Get document chunks"""
    if doc_id not in documents_store:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc_data = documents_store[doc_id]
    chunks = doc_data.get("chunks", [])
    
    chunk_responses = [
        DocumentChunk(
            id=chunk["id"],
            index=chunk["index"],
            text=chunk["text"],
            length=chunk["length"],
            created_at=chunk["created_at"]
        )
        for chunk in chunks
    ]
    
    return DocumentChunksResponse(
        document_id=doc_id,
        chunks=chunk_responses,
        total_chunks=len(chunks)
    )

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
        # Remove file
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

# System endpoints
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

@router.post("/documents/{doc_id}/embeddings", response_model=EmbeddingResponse)
async def generate_embeddings(doc_id: str):
    """Generate embeddings for document chunks"""
    if doc_id not in documents_store:
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        doc_data = documents_store[doc_id]
        chunks = doc_data.get("chunks", [])
        
        if not chunks:
            raise HTTPException(status_code=400, detail="Document not chunked yet")
        
        # Generate embeddings
        chunks_with_embeddings = document_processor.process_document_with_embeddings(doc_id, chunks)
        
        # Update storage
        doc_data["chunks"] = chunks_with_embeddings
        doc_data["document"].processing_status = "embedded"
        
        # Get embedding dimension
        from embedding import embedding_engine
        embedding_dim = embedding_engine.get_embedding_dimension()
        
        logger.info(f"Embeddings generated for document: {doc_id}")
        
        return EmbeddingResponse(
            document_id=doc_id,
            chunks_processed=len(chunks_with_embeddings),
            embedding_dimension=embedding_dim,
            status="completed"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Embedding generation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Embedding generation failed")