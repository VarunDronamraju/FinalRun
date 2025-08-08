from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import List, Optional
import logging
from datetime import datetime
from fastapi.responses import StreamingResponse
import asyncio
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
from documents import document_processor, process_document_with_embeddings
from schemas import EmbeddingResponse, DocumentChunkWithEmbedding
from rag import vector_store, rag_pipeline
from llm import ollama_client
from web_search import web_search

from sqlalchemy.orm import Session
from database import get_db, init_database, DBDocument, DBChunk
from documents import save_document_to_db, save_chunks_to_db, update_document_status



logger = logging.getLogger(__name__)
router = APIRouter()
def get_database() -> Session:
    return next(get_db())
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
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_database)
):
    """Upload document endpoint with database storage"""
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
        
        # Generate document ID
        doc_id = generate_file_id()
        
        # Save to database
        try:
            db_document = save_document_to_db(
                db=db,
                doc_id=doc_id,
                title=file.filename,
                file_path=file_path,
                file_type=file_type,
                file_size=file_size,
                text_preview=text_preview
            )
            
            # Create response
            document = DocumentResponse(
                id=db_document.id,
                title=db_document.title,
                file_type=db_document.file_type,
                size=db_document.file_size,
                upload_time=db_document.upload_time,
                processing_status=db_document.processing_status,
                chunk_count=db_document.chunk_count,
                text_preview=db_document.text_preview
            )
            
        except Exception as db_error:
            logger.error(f"Database save failed: {db_error}")
            # Fallback to memory storage
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
        
        # Store in memory for backward compatibility
        documents_store[doc_id] = {
            "document": document,
            "file_path": file_path,
            "extracted_text": extracted_text,
            "chunks": []
        }
        
        logger.info(f"Document uploaded: {file.filename} ({file_size} bytes)")
        return document
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Upload failed")



@router.post("/documents/{doc_id}/process", response_model=DocumentChunksResponse)
async def process_document(
    doc_id: str,
    request: ProcessDocumentRequest = ProcessDocumentRequest(),
    db: Session = Depends(get_database)
):
    """Process document into chunks with database storage"""
    # Check in database first
    db_document = db.query(DBDocument).filter(DBDocument.id == doc_id).first()
    if not db_document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        # Get extracted text (from memory store for now)
        doc_data = documents_store.get(doc_id)
        if not doc_data:
            # Load from file if not in memory
            extracted_text = document_processor.extract_text(db_document.file_path, db_document.file_type)
        else:
            extracted_text = doc_data["extracted_text"]
        
        if not extracted_text:
            raise HTTPException(status_code=400, detail="No text extracted from document")
        
        # Chunk the document
        chunks = document_processor.chunk_document(
            extracted_text,
            chunk_size=request.chunk_size,
            overlap=request.overlap
        )
        
        # Filter quality chunks
        quality_chunks = [
            chunk for chunk in chunks
            if validate_chunk_quality(chunk["text"])
        ]
        
        # Save chunks to database
        save_chunks_to_db(db, doc_id, quality_chunks)
        
        # Update document status
        update_document_status(db, doc_id, "chunked", len(quality_chunks))
        
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
        
        # Update memory store for backward compatibility
        if doc_id in documents_store:
            documents_store[doc_id]["chunks"] = quality_chunks
            documents_store[doc_id]["document"].chunk_count = len(quality_chunks)
            documents_store[doc_id]["document"].processing_status = "chunked"
        
        logger.info(f"Document chunked and saved to DB: {doc_id} ({len(quality_chunks)} chunks)")
        
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
    limit: int = 10,
    db: Session = Depends(get_database)
):
    """List documents from database"""
    try:
        # Query from database
        documents = db.query(DBDocument).offset(skip).limit(limit).all()
        total = db.query(DBDocument).count()
        
        # Convert to response format
        document_responses = [
            DocumentResponse(
                id=doc.id,
                title=doc.title,
                file_type=doc.file_type,
                size=doc.file_size,
                upload_time=doc.upload_time,
                processing_status=doc.processing_status,
                chunk_count=doc.chunk_count,
                text_preview=doc.text_preview
            )
            for doc in documents
        ]
        
        return DocumentListResponse(
            documents=document_responses,
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
        chunks_with_embeddings = process_document_with_embeddings(doc_id, chunks)
        
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


@router.post("/documents/{doc_id}/store", response_model=BaseResponse)
async def store_document_vectors(doc_id: str):
    """Store document embeddings in vector database"""
    if doc_id not in documents_store:
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        doc_data = documents_store[doc_id]
        chunks = doc_data.get("chunks", [])
        
        if not chunks:
            raise HTTPException(status_code=400, detail="No chunks found")
        
        # Check if embeddings exist
        if not chunks[0].get("embedding"):
            raise HTTPException(status_code=400, detail="No embeddings found. Generate embeddings first")
        
        # Store in Qdrant
        stored_count = vector_store.store_embeddings(doc_id, chunks)
        
        # Update document status
        doc_data["document"].processing_status = "stored"
        
        logger.info(f"Vectors stored for document: {doc_id}")
        
        return BaseResponse(message=f"Stored {stored_count} vectors successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Vector storage error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Vector storage failed")

@router.post("/search/semantic")
async def semantic_search(request: dict):
    """Semantic search across documents"""
    try:
        query = request.get("query")
        limit = request.get("limit", 5)
        document_id = request.get("document_id")
        
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")
        
        # Generate query embedding - Fix the import
        from embedding import embedding_engine
        query_embedding = embedding_engine.embed_single_text(query)
        
        # Search vectors
        results = vector_store.search_similar(
            query_vector=query_embedding,
            limit=limit,
            doc_filter=document_id
        )
        
        # Format results
        search_results = []
        for result in results:
            search_results.append({
                "chunk_id": result.id,
                "score": result.score,
                "text": result.payload.get("text", ""),
                "document_id": result.payload.get("document_id", ""),
                "chunk_index": result.payload.get("chunk_index", 0)
            })
        
        return {
            "query": query,
            "results": search_results,
            "total_found": len(search_results)
        }
        
    except Exception as e:
        logger.error(f"Semantic search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Semantic search failed")

# Add import

@router.post("/rag/query")
async def rag_query(request: dict):
    """RAG query endpoint"""
    try:
        query = request.get("query")
        max_results = request.get("max_results", 5)
        max_context_length = request.get("max_context_length", 2000)
        
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")
        
        # Retrieve context
        context = rag_pipeline.retrieve_context(
            query=query,
            max_results=max_results,
            max_context_length=max_context_length
        )
        
        # Build prompt
        prompt = rag_pipeline.build_rag_prompt(query, context)
        
        return {
            "query": query,
            "context": context,
            "prompt": prompt,
            "status": "context_retrieved"
        }
        
    except Exception as e:
        logger.error(f"RAG query error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="RAG query failed")




@router.post("/llm/generate")
async def generate_llm_response(request: dict):
    """Generate LLM response"""
    try:
        prompt = request.get("prompt")
        if not prompt:
            raise HTTPException(status_code=400, detail="Prompt is required")
        
        # Check if Ollama is available
        if not await ollama_client.is_available():
            raise HTTPException(status_code=503, detail="Ollama service unavailable")
        
        response = await ollama_client.generate_response(prompt)
        
        return {
            "prompt": prompt,
            "response": response,
            "model": settings.ollama_model
        }
        
    except Exception as e:
        logger.error(f"LLM generation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="LLM generation failed")

@router.post("/rag/answer")
async def rag_answer(request: dict):
    """Complete RAG pipeline with answer generation"""
    try:
        query = request.get("query")
        max_results = request.get("max_results", 5)
        
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")
        
        # Check if Ollama is available
        if not await ollama_client.is_available():
            raise HTTPException(status_code=503, detail="Ollama service unavailable")
        
        result = await rag_pipeline.generate_answer(query, max_results)
        return result
        
    except Exception as e:
        logger.error(f"RAG answer error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="RAG answer failed")

@router.post("/rag/stream")
async def rag_stream_answer(request: dict):
    """Stream RAG answer"""
    try:
        query = request.get("query")
        max_results = request.get("max_results", 5)
        
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")
        
        # Check if Ollama is available
        if not await ollama_client.is_available():
            raise HTTPException(status_code=503, detail="Ollama service unavailable")
        
        async def generate():
            async for chunk in rag_pipeline.stream_answer(query, max_results):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/plain",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )
        
    except Exception as e:
        logger.error(f"RAG streaming error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="RAG streaming failed")

@router.get("/llm/status")
async def llm_status():
    """Check LLM service status"""
    ollama_available = await ollama_client.is_available()
    
    return {
        "ollama_available": ollama_available,
        "ollama_url": settings.ollama_url,
        "model": settings.ollama_model,
        "status": "ready" if ollama_available else "unavailable"
    }

@router.post("/rag/answer-with-fallback")
async def rag_answer_with_fallback(request: dict):
    """RAG with web search fallback"""
    try:
        query = request.get("query")
        max_results = request.get("max_results", 5)
        use_fallback = request.get("use_fallback", True)
        
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")
        
        # Check if Ollama is available
        if not await ollama_client.is_available():
            raise HTTPException(status_code=503, detail="Ollama service unavailable")
        
        result = await rag_pipeline.generate_answer_with_fallback(
            query, max_results, use_fallback
        )
        return result
        
    except Exception as e:
        logger.error(f"RAG fallback error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="RAG with fallback failed")

@router.post("/search/web")
async def web_search_endpoint(request: dict):
    """Web search endpoint"""
    try:
        query = request.get("query")
        max_results = request.get("max_results", 3)
        
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")
        
        if not web_search.is_available():
            raise HTTPException(status_code=503, detail="Web search not available")
        
        results = await web_search.search(query, max_results)
        
        return {
            "query": query,
            "results": results,
            "total_found": len(results)
        }
        
    except Exception as e:
        logger.error(f"Web search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Web search failed")

# REPLACE the search_capabilities function with:
@router.get("/search/capabilities")
async def search_capabilities():
    """Get search capabilities"""
    try:
        web_available = web_search.is_available()
    except:
        web_available = False
        
    import os
    from dotenv import load_dotenv
    load_dotenv()
    tavily_key = os.getenv("TAVILY_API_KEY", "")
    
    return {
        "local_search": True,
        "web_search": web_available,
        "fallback_enabled": web_available,
        "tavily_configured": bool(tavily_key)
    }