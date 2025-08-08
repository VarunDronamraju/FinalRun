import logging
from typing import List, Dict, Any, Optional
import asyncio

logger = logging.getLogger(__name__)

class WebSearchManager:
    def __init__(self):
        self.tavily_client = None
        self.api_key = None
        self.settings = None
        
    def _load_settings(self):
        """Load settings without relative import"""
        if not self.settings:
            import os
            from dotenv import load_dotenv
            load_dotenv()
            self.api_key = os.getenv("TAVILY_API_KEY", "")
            
    def _init_client(self):
        """Initialize Tavily client"""
        if not self.api_key:
            self._load_settings()
            
        if not self.tavily_client and self.api_key:
            try:
                from tavily import TavilyClient
                self.tavily_client = TavilyClient(api_key=self.api_key)
                logger.info("Tavily client initialized successfully")
            except Exception as e:
                logger.error(f"Tavily client initialization failed: {e}")
    
    def is_available(self) -> bool:
        """Check if web search is available"""
        if not self.api_key:
            self._load_settings()
        return bool(self.api_key)
    
    async def search(self, query: str, max_results: int = 3) -> List[Dict[str, Any]]:
        """Search web using Tavily"""
        if not self.is_available():
            logger.warning("Web search not available - no API key")
            return []
        
        try:
            self._init_client()
            
            if not self.tavily_client:
                logger.error("Tavily client not initialized")
                return []
            
            # Use asyncio to run sync tavily client
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.tavily_client.search(
                    query=query,
                    search_depth="basic",
                    max_results=max_results,
                    include_answer=True,
                    include_raw_content=False
                )
            )
            
            results = []
            for result in response.get("results", []):
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "content": result.get("content", ""),
                    "score": result.get("score", 0.0)
                })
            
            logger.info(f"Web search completed: {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return []
    
    def format_web_context(self, results: List[Dict[str, Any]]) -> str:
        """Format web search results as context"""
        if not results:
            return ""
        
        context_parts = []
        for i, result in enumerate(results, 1):
            context_parts.append(
                f"[Web Source {i}] {result['title']}\n{result['content']}\n"
            )
        
        return "\n".join(context_parts)

# Global web search manager
web_search = WebSearchManager()