"""
API Client for RAG Desktop Application
Handles communication with the backend API
"""

import asyncio
import logging
import httpx
from typing import Dict, Any, List, Optional, AsyncGenerator
from pathlib import Path

logger = logging.getLogger(__name__)

class APIClient:
    """Async API client for backend communication"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.auth_token: Optional[str] = None
        self.client: Optional[httpx.AsyncClient] = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
        
    async def connect(self):
        """Connect to the API"""
        try:
            self.client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30.0,
                headers={"User-Agent": "RAG-Desktop/1.0"}
            )
            logger.info(f"Connected to API at {self.base_url}")
        except Exception as e:
            logger.error(f"Failed to connect to API: {e}")
            raise
            
    async def disconnect(self):
        """Disconnect from the API"""
        if self.client:
            await self.client.aclose()
            logger.info("Disconnected from API")
            
    def get_headers(self) -> Dict[str, str]:
        """Get request headers"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers
        
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to API"""
        if not self.client:
            raise Exception("API client not connected")
            
        url = f"{self.base_url}{endpoint}"
        headers = self.get_headers()
        
        try:
            response = await self.client.request(
                method=method,
                url=url,
                headers=headers,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise
            
    async def test_connection(self) -> bool:
        """Test API connection"""
        try:
            await self._make_request("GET", "/api/v1/health")
            return True
        except Exception:
            return False
            
    async def get_system_status(self) -> Dict[str, Any]:
        """Get system status"""
        return await self._make_request("GET", "/api/v1/health")
        
    async def get_available_models(self) -> List[str]:
        """Get available AI models"""
        try:
            response = await self._make_request("GET", "/api/v1/system/models")
            return response.get("models", [])
        except Exception:
            return []
            
    async def upload_document(self, file_path: str, progress_callback=None) -> Dict[str, Any]:
        """Upload document to API"""
        if not Path(file_path).exists():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        try:
            with open(file_path, "rb") as f:
                files = {"file": (Path(file_path).name, f, "application/octet-stream")}
                response = await self.client.post(
                    f"{self.base_url}/api/v1/documents/upload",
                    files=files,
                    headers={"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else {}
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            raise
            
    async def get_documents(self, skip: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        """Get list of documents"""
        try:
            response = await self._make_request("GET", f"/api/v1/documents?skip={skip}&limit={limit}")
            return response.get("documents", [])
        except Exception:
            return []
            
    async def get_document_details(self, doc_id: str) -> Dict[str, Any]:
        """Get document details"""
        return await self._make_request("GET", f"/api/v1/documents/{doc_id}")
        
    async def delete_document(self, doc_id: str) -> bool:
        """Delete document"""
        try:
            await self._make_request("DELETE", f"/api/v1/documents/{doc_id}")
            return True
        except Exception:
            return False
            
    async def process_document(self, doc_id: str) -> Dict[str, Any]:
        """Process document"""
        return await self._make_request("POST", f"/api/v1/documents/{doc_id}/process")
        
    async def get_document_chunks(self, doc_id: str) -> List[Dict[str, Any]]:
        """Get document chunks"""
        try:
            response = await self._make_request("GET", f"/api/v1/documents/{doc_id}/chunks")
            return response.get("chunks", [])
        except Exception:
            return []
            
    async def rag_query(self, query: str, max_results: int = 5) -> str:
        """Perform RAG query"""
        try:
            response = await self._make_request(
                "POST", 
                "/api/v1/rag/answer-with-fallback",
                json={"query": query, "max_results": max_results}
            )
            return response.get("answer", "No answer available")
        except Exception as e:
            logger.error(f"RAG query failed: {e}")
            return f"Error: {e}"
            
    async def semantic_search(self, query: str, document_ids: Optional[List[str]] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Perform semantic search"""
        try:
            payload = {"query": query, "limit": limit}
            if document_ids:
                payload["document_ids"] = document_ids
            response = await self._make_request("POST", "/api/v1/search/semantic", json=payload)
            return response.get("results", [])
        except Exception:
            return []
            
    async def web_search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Perform web search"""
        try:
            response = await self._make_request(
                "POST", 
                "/api/v1/search/web",
                json={"query": query, "max_results": max_results}
            )
            return response.get("results", [])
        except Exception:
            return []
            
    async def stream_rag_query(self, query: str, max_results: int = 5) -> AsyncGenerator[str, None]:
        """Stream RAG query response"""
        try:
            async with self.client.stream(
                "POST",
                f"{self.base_url}/api/v1/rag/stream",
                json={"query": query, "max_results": max_results},
                headers=self.get_headers()
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix
                        if data == "[DONE]":
                            break
                        yield data
        except Exception as e:
            logger.error(f"Stream RAG query failed: {e}")
            yield f"Error: {e}"
            
    # Chat session management
    async def create_chat_session(self) -> str:
        """Create new chat session"""
        try:
            response = await self._make_request("POST", "/api/v1/chat/sessions")
            return response.get("session_id", "")
        except Exception:
            return ""
            
    async def get_chat_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get chat history"""
        try:
            response = await self._make_request("GET", f"/api/v1/chat/sessions/{session_id}/messages?limit={limit}")
            return response.get("messages", [])
        except Exception:
            return []
            
    async def delete_chat_session(self, session_id: str) -> bool:
        """Delete chat session"""
        try:
            await self._make_request("DELETE", f"/api/v1/chat/sessions/{session_id}")
            return True
        except Exception:
            return False
    
    # Authentication methods
    def set_auth_token(self, token: str):
        """Set authentication token"""
        self.auth_token = token
        logger.info("Authentication token set")
        
    def clear_auth_token(self):
        """Clear authentication token"""
        self.auth_token = None
        logger.info("Authentication token cleared")
        
    async def google_oauth_login(self) -> Dict[str, str]:
        """Initiate Google OAuth flow"""
        return await self._make_request("POST", "/api/v1/auth/google/login")
        
    async def google_oauth_callback(self, code: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Google OAuth callback"""
        return await self._make_request("POST", "/api/v1/auth/google/callback", json=payload)
        
    async def refresh_auth_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh authentication token"""
        payload = {"refresh_token": refresh_token}
        return await self._make_request("POST", "/api/v1/auth/refresh", json=payload)
        
    async def logout(self) -> bool:
        """Logout and invalidate session"""
        try:
            await self._make_request("POST", "/api/v1/auth/logout")
            return True
        except Exception:
            return False
            
    async def get_user_profile(self) -> Dict[str, Any]:
        """Get current user profile"""
        return await self._make_request("GET", "/api/v1/auth/profile")

class APIError(Exception):
    """Custom exception for API errors"""
    pass

# Synchronous wrapper for use in Qt threads
class SyncAPIClient:
    """Synchronous wrapper for APIClient to use in Qt threads"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.auth_token: Optional[str] = None
        
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
    
    def set_auth_token(self, token: str):
        """Set authentication token"""
        self.auth_token = token
        
    def clear_auth_token(self):
        """Clear authentication token"""
        self.auth_token = None
    
    def test_connection(self) -> bool:
        """Sync version of test_connection"""
        async def _test():
            async with APIClient(self.base_url) as client:
                if self.auth_token:
                    client.set_auth_token(self.auth_token)
                return await client.test_connection()
        return self._run_async(_test())
        
    def upload_document(self, file_path: str) -> Dict[str, Any]:
        """Sync version of upload_document"""
        async def _upload():
            async with APIClient(self.base_url) as client:
                if self.auth_token:
                    client.set_auth_token(self.auth_token)
                return await client.upload_document(file_path)
        return self._run_async(_upload())
        
    def get_documents(self) -> List[Dict[str, Any]]:
        """Sync version of get_documents"""
        async def _get_docs():
            async with APIClient(self.base_url) as client:
                if self.auth_token:
                    client.set_auth_token(self.auth_token)
                return await client.get_documents()
        return self._run_async(_get_docs())
        
    def rag_query(self, query: str) -> str:
        """Sync version of rag_query"""
        async def _query():
            async with APIClient(self.base_url) as client:
                if self.auth_token:
                    client.set_auth_token(self.auth_token)
                return await client.rag_query(query)
        return self._run_async(_query())
        
    def semantic_search(self, query: str) -> List[Dict[str, Any]]:
        """Sync version of semantic_search"""
        async def _search():
            async with APIClient(self.base_url) as client:
                if self.auth_token:
                    client.set_auth_token(self.auth_token)
                return await client.semantic_search(query)
        return self._run_async(_search())
        
    # Authentication methods
    def google_oauth_login(self) -> Dict[str, Any]:
        """Sync version of google_oauth_login"""
        async def _login():
            async with APIClient(self.base_url) as client:
                return await client.google_oauth_login()
        return self._run_async(_login())
        
    def google_oauth_callback(self, code: str, is_mock: bool = False) -> Dict[str, Any]:
        """Sync version of google_oauth_callback"""
        async def _callback():
            async with APIClient(self.base_url) as client:
                payload = {"code": code, "is_mock": is_mock}
                return await client.google_oauth_callback(code, payload)
        return self._run_async(_callback())
        
    def refresh_auth_token(self, refresh_token: str) -> Dict[str, Any]:
        """Sync version of refresh_auth_token"""
        async def _refresh():
            async with APIClient(self.base_url) as client:
                return await client.refresh_auth_token(refresh_token)
        return self._run_async(_refresh())
        
    def get_user_profile(self) -> Dict[str, Any]:
        """Sync version of get_user_profile"""
        async def _profile():
            async with APIClient(self.base_url) as client:
                if self.auth_token:
                    client.set_auth_token(self.auth_token)
                return await client.get_user_profile()
        return self._run_async(_profile())
        
    def logout_user(self) -> bool:
        """Sync version of logout"""
        async def _logout():
            async with APIClient(self.base_url) as client:
                if self.auth_token:
                    client.set_auth_token(self.auth_token)
                return await client.logout()
        return self._run_async(_logout())

# Global API client instance
api_client = SyncAPIClient()