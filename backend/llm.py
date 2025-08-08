import logging
import httpx
import json
from typing import Iterator, Optional, Dict, Any
from config import settings

logger = logging.getLogger(__name__)

class OllamaClient:
    def __init__(self):
        self.base_url = settings.ollama_url
        self.model = settings.ollama_model
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def is_available(self) -> bool:
        """Check if Ollama is available"""
        try:
            response = await self.client.get(f"{self.base_url}/api/version")
            return response.status_code == 200
        except:
            return False
    
    async def pull_model(self) -> bool:
        """Pull model if not available"""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/pull",
                json={"name": self.model}
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Model pull failed: {e}")
            return False
    
    async def generate_response(self, prompt: str, stream: bool = False) -> str:
        """Generate response from Ollama"""
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": stream
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json=payload
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama error: {response.status_code}")
            
            if stream:
                return response.text
            else:
                result = response.json()
                return result.get("response", "")
                
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise
    
    async def stream_response(self, prompt: str) -> Iterator[str]:
        """Stream response from Ollama"""
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": True
            }
            
            async with self.client.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json=payload
            ) as response:
                if response.status_code != 200:
                    raise Exception(f"Ollama error: {response.status_code}")
                
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if "response" in data:
                                yield data["response"]
                            if data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            logger.error(f"Streaming failed: {e}")
            yield f"Error: {str(e)}"

# Global Ollama client
ollama_client = OllamaClient()