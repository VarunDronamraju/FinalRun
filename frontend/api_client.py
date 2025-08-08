"""
API Client for RAG Desktop Application
Handles all HTTP communication with the FastAPI backend
"""

import httpx
import json
import logging
import asyncio
from typing import Optional, Dict, List, Any, AsyncGenerator
from pathlib import Path
import os

logger = logging.getLogger(__name__)

class APIClient:
    """Async HTTP client for backend communication"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.timeout = httpx.Timeout(30.0, connect=5.0)
        self.session: Optional[httpx.AsyncClient] = None
        self.auth_token: Optional[str] = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
        
    async def connect(self):
        """Initialize HTTP session"""
        if self.session is None:
            self.session = httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True
            )
        logger.info(f"Connected to API at {self.base_url}")
        
    async def disconnect(self):
        """Close HTTP session"""
        if self.session:
            await self.session.aclose()
            self.session = None
        logger.info("Disconnected from API")
        
    def get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "RAG-Desktop/1.0"
        }
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers
        
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with error handling"""
        if not self.session:
            await self.connect()
            
        url = f"{self.base_url}{endpoint}"
        headers = kwargs.pop("headers", {})
        headers.update(self.get_headers())
        
        try:
            response = await self.session.request(
                method=method,
                url=url,
                headers=headers,
                **kwargs
            )
            response.raise_for_status()
            
            # Handle different content types
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                return response.json()
            else:
                return {"data": response.text}
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP {e.response.status_code}: {e.response.text}")
            raise APIError(f"HTTP {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"Request failed: {e}")
            raise APIError(f"Connection failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise APIError(f"Unexpected error: {e}")
    
    # Health and System Endpoints
    async def test_connection(self) -> bool:
        """Test if backend is accessible"""
        try:
            result = await self._make_request("GET", "/api/v1/health")
            return result.get("status") == "healthy"
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
            
    async def get_system_status(self) -> Dict[str, Any]:
        """Get detailed system status"""
        return await self._make_request("GET", "/api/v1/health")
        
    async def get_available_models(self) -> List[str]:
        """Get list of available LLM models"""
        try:
            result = await self._make_request("GET", "/api/v1/llm/status")
            return result.get("available_models", [])
        except Exception:
            return ["gemma:2b"]  # Default fallback
    
    # Document Management Endpoints
    async def upload_document(self, file_path: str, progress_callback=None) -> Dict[str, Any]:
        """Upload a document to the backend"""
        if not self.session:
            await self.connect()
            
        file_path = Path(file_path)
        if not file_path.exists():
            raise APIError(f"File not found: {file_path}")
            
        try:
            with open(file_path, 'rb') as f:
                files = {
                    "file": (file_path.name, f, "application/octet-stream")
                }
                
                # Remove content-type from headers for multipart
                headers = {k: v for k, v in self.get_headers().items() 
                          if k.lower() != "content-type"}
                
                response = await self.session.post(
                    f"{self.base_url}/api/v1/documents/upload",
                    files=files,
                    headers=headers
                )
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            logger.error(f"Upload failed for {file_path}: {e}")
            raise APIError(f"Upload failed: {e}")
            
    async def get_documents(self, skip: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        """Get paginated list of documents"""
        params = {"skip": skip, "limit": limit}
        result = await self._make_request("GET", "/api/v1/documents", params=params)
        return result if isinstance(result, list) else result.get("documents", [])
        
    async def get_document_details(self, doc_id: str) -> Dict[str, Any]:
        """Get detailed information about a document"""
        return await self._make_request("GET", f"/api/v1/documents/{doc_id}")
        
    async def delete_document(self, doc_id: str) -> bool:
        """Delete a document and its embeddings"""
        try:
            await self._make_request("DELETE", f"/api/v1/documents/{doc_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {e}")
            return False
            
    async def process_document(self, doc_id: str) -> Dict[str, Any]:
        """Process document (chunking and embedding)"""
        return await self._make_request("POST", f"/api/v1/documents/{doc_id}/process")
        
    async def get_document_chunks(self, doc_id: str) -> List[Dict[str, Any]]:
        """Get chunks for a specific document"""
        result = await self._make_request("GET", f"/api/v1/documents/{doc_id}/chunks")
        return result if isinstance(result, list) else result.get("chunks", [])
    
    # RAG and Search Endpoints
    async def rag_query(self, query: str, max_results: int = 5) -> str:
        """Send RAG query with fallback"""
        payload = {
            "query": query,
            "max_results": max_results,
            "use_fallback": True
        }
        result = await self._make_request("POST", "/api/v1/rag/answer-with-fallback", json=payload)
        return result.get("answer", "No response received")
        
    async def semantic_search(self, query: str, document_ids: Optional[List[str]] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Perform semantic search across documents"""
        payload = {
            "query": query,
            "limit": limit
        }
        if document_ids:
            payload["document_ids"] = document_ids
            
        result = await self._make_request("POST", "/api/v1/search/semantic", json=payload)
        return result if isinstance(result, list) else result.get("results", [])
        
    async def web_search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Perform web search using TAVILY"""
        payload = {
            "query": query,
            "max_results": max_results
        }
        result = await self._make_request("POST", "/api/v1/search/web", json=payload)
        return result if isinstance(result, list) else result.get("results", [])
    
    # Streaming Endpoints
    async def stream_rag_query(self, query: str, max_results: int = 5) -> AsyncGenerator[str, None]:
        """Stream RAG query response"""
        if not self.session:
            await self.connect()
            
        payload = {
            "query": query,
            "max_results": max_results,
            "use_fallback": True
        }
        
        try:
            async with self.session.stream(
                "POST",
                f"{self.base_url}/api/v1/rag/stream",
                json=payload,
                headers=self.get_headers()
            ) as response:
                response.raise_for_status()
                
                async for chunk in response.aiter_text():
                    if chunk.strip():
                        yield chunk
                        
        except Exception as e:
            logger.error(f"Streaming query failed: {e}")
            yield f"Error: {str(e)}"
    
    # Chat Management (Future Implementation)
    async def create_chat_session(self) -> str:
        """Create a new chat session"""
        result = await self._make_request("POST", "/api/v1/chat/new")
        return result.get("session_id", "")
        
    async def get_chat_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get chat history for a session"""
        params = {"limit": limit}
        result = await self._make_request("GET", f"/api/v1/chat/history/{session_id}", params=params)
        return result if isinstance(result, list) else result.get("messages", [])
        
    async def delete_chat_session(self, session_id: str) -> bool:
        """Delete a chat session"""
        try:
            await self._make_request("DELETE", f"/api/v1/chat/{session_id}")
            return True
        except Exception:
            return False
    
    # Authentication (Future Implementation)
    def set_auth_token(self, token: str):
        """Set authentication token"""
        self.auth_token = token
        logger.info("Authentication token set")
        
    def clear_auth_token(self):
        """Clear authentication token"""
        self.auth_token = None
        logger.info("Authentication token cleared")

class APIError(Exception):
    """Custom exception for API errors"""
    pass

# Synchronous wrapper for use in Qt threads
class SyncAPIClient:
    """Synchronous wrapper for APIClient to use in Qt threads"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        
    def _run_async(self, coro):
        """Run async coroutine in new event loop"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)
        finally:
            try:
                loop.close()
            except:
                pass
    
    def test_connection(self) -> bool:
        """Sync version of test_connection"""
        async def _test():
            async with APIClient(self.base_url) as client:
                return await client.test_connection()
        return self._run_async(_test())
        
    def upload_document(self, file_path: str) -> Dict[str, Any]:
        """Sync version of upload_document"""
        async def _upload():
            async with APIClient(self.base_url) as client:
                return await client.upload_document(file_path)
        return self._run_async(_upload())
        
    def get_documents(self) -> List[Dict[str, Any]]:
        """Sync version of get_documents"""
        async def _get_docs():
            async with APIClient(self.base_url) as client:
                return await client.get_documents()
        return self._run_async(_get_docs())
        
    def rag_query(self, query: str) -> str:
        """Sync version of rag_query"""
        async def _query():
            async with APIClient(self.base_url) as client:
                return await client.rag_query(query)
        return self._run_async(_query())
        
    def semantic_search(self, query: str) -> List[Dict[str, Any]]:
        """Sync version of semantic_search"""
        async def _search():
            async with APIClient(self.base_url) as client:
                return await client.semantic_search(query)
        return self._run_async(_search())

# Global API client instance
api_client = SyncAPIClient()