import logging
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
import uuid

from config import settings
from llm import ollama_client
from web_search import web_search
logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self):
        self.client = None
        self.collection_name = "documents"
    
    def connect(self):
        """Connect to Qdrant"""
        if not self.client:
            self.client = QdrantClient(url=settings.qdrant_url)
            logger.info(f"Connected to Qdrant at {settings.qdrant_url}")
    
    def ensure_collection(self, vector_size: int = 384):
        """Ensure collection exists"""
        if not self.client:
            self.connect()
        
        try:
            collections = self.client.get_collections()
            collection_exists = any(col.name == self.collection_name for col in collections.collections)
            
            if not collection_exists:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
                )
                logger.info(f"Created collection: {self.collection_name}")
            else:
                logger.info(f"Collection exists: {self.collection_name}")
        except Exception as e:
            logger.error(f"Collection setup failed: {e}")
            raise
    
    def store_embeddings(self, doc_id: str, chunks: List[Dict[str, Any]]):
        """Store embeddings in Qdrant"""
        self.connect()
        
        # Get embedding dimension from first chunk
        if chunks and "embedding" in chunks[0]:
            vector_size = len(chunks[0]["embedding"])
            self.ensure_collection(vector_size)
        else:
            raise ValueError("No embeddings found in chunks")
        
        # Prepare points
        points = []
        for chunk in chunks:
            if "embedding" not in chunk:
                continue
                
            point = PointStruct(
                id=chunk["id"],
                vector=chunk["embedding"],
                payload={
                    "document_id": doc_id,
                    "chunk_index": chunk["index"],
                    "text": chunk["text"],
                    "length": chunk["length"],
                    "created_at": chunk["created_at"].isoformat()
                }
            )
            points.append(point)
        
        # Upsert points
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        
        logger.info(f"Stored {len(points)} vectors for document: {doc_id}")
        return len(points)
    
    def search_similar(self, query_vector: List[float], limit: int = 5, doc_filter: Optional[str] = None):
        """Search for similar vectors"""
        self.connect()
        
        search_filter = None
        if doc_filter:
            search_filter = Filter(
                must=[FieldCondition(key="document_id", match=MatchValue(value=doc_filter))]
            )
        
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=limit,
            query_filter=search_filter
        )
        
        return results

# Global vector store
vector_store = VectorStore()



class RAGPipeline:
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.fallback_threshold = 0.3  # If best result score below this, use web search
    
    def retrieve_context(self, query: str, max_results: int = 5, max_context_length: int = 2000) -> str:
        """Retrieve relevant context for query"""
        from embedding import embedding_engine
        
        # Generate query embedding
        query_embedding = embedding_engine.embed_single_text(query)
        
        # Search similar chunks
        results = self.vector_store.search_similar(
            query_vector=query_embedding,
            limit=max_results
        )
        
        # Build context from results
        context_parts = []
        total_length = 0
        
        for result in results:
            text = result.payload.get("text", "")
            if total_length + len(text) > max_context_length:
                break
            context_parts.append(f"[Score: {result.score:.3f}] {text}")
            total_length += len(text)
        
        return "\n\n".join(context_parts)
    
    def should_use_fallback(self, local_results: List, query: str) -> bool:
        """Determine if web search fallback should be used"""
        if not local_results:
            return True
        
        # Check if best result score is below threshold
        best_score = max(result.score for result in local_results) if local_results else 0
        
        if best_score < self.fallback_threshold:
            logger.info(f"Using web fallback - best local score: {best_score}")
            return True
        
        # Check for time-sensitive queries
        time_indicators = ["latest", "recent", "current", "today", "2024", "2025", "now"]
        if any(indicator in query.lower() for indicator in time_indicators):
            logger.info("Using web fallback - time-sensitive query detected")
            return True
        
        return False
    
    async def retrieve_context_with_fallback(
        self, 
        query: str, 
        max_results: int = 5, 
        max_context_length: int = 2000,
        use_fallback: bool = True
    ) -> Dict[str, Any]:
        """Retrieve context with web search fallback"""
        from embedding import embedding_engine
        
        # First try local search
        query_embedding = embedding_engine.embed_single_text(query)
        local_results = self.vector_store.search_similar(
            query_vector=query_embedding,
            limit=max_results
        )
        
        local_context = ""
        web_context = ""
        
        # Build local context
        if local_results:
            context_parts = []
            total_length = 0
            
            for result in local_results:
                text = result.payload.get("text", "")
                if total_length + len(text) > max_context_length // 2:  # Reserve space for web
                    break
                context_parts.append(f"[Local Score: {result.score:.3f}] {text}")
                total_length += len(text)
            
            local_context = "\n\n".join(context_parts)
        
        # Check if web fallback needed
        use_web = use_fallback and self.should_use_fallback(local_results, query)
        
        if use_web:
            try:
                from web_search import web_search
                web_results = await web_search.search(query, max_results=3)
                web_context = web_search.format_web_context(web_results)
            except Exception as e:
                logger.error(f"Web search fallback failed: {e}")
        
        return {
            "local_context": local_context,
            "web_context": web_context,
            "used_fallback": use_web,
            "local_results_count": len(local_results),
            "fallback_triggered": use_web
        }
    
    def build_hybrid_prompt(self, query: str, local_context: str, web_context: str) -> str:
        """Build prompt with both local and web context"""
        prompt_parts = ["You are a helpful assistant. Answer the question using the provided information."]
        
        if local_context:
            prompt_parts.append(f"\nLocal Knowledge Base:\n{local_context}")
        
        if web_context:
            prompt_parts.append(f"\nWeb Search Results:\n{web_context}")
        
        if not local_context and not web_context:
            prompt_parts.append("\nNo specific context found. Please answer based on your general knowledge.")
        
        prompt_parts.extend([
            f"\nQuestion: {query}",
            "\nPlease provide a comprehensive answer. If using web sources, mention that the information is from recent web search. If the information is insufficient, state that clearly.",
            "\nAnswer:"
        ])
        
        return "\n".join(prompt_parts)
    
    async def generate_answer_with_fallback(
        self, 
        query: str, 
        max_results: int = 5,
        use_fallback: bool = True
    ) -> Dict[str, Any]:
        """Complete RAG pipeline with web fallback"""
        try:
            # Retrieve context with fallback
            context_data = await self.retrieve_context_with_fallback(
                query, max_results, use_fallback=use_fallback
            )
            
            # Build hybrid prompt
            prompt = self.build_hybrid_prompt(
                query, 
                context_data["local_context"], 
                context_data["web_context"]
            )
            
            # Generate answer
            answer = await ollama_client.generate_response(prompt)
            
            return {
                "query": query,
                "answer": answer,
                "local_context": context_data["local_context"],
                "web_context": context_data["web_context"],
                "used_fallback": context_data["used_fallback"],
                "local_results_count": context_data["local_results_count"],
                "status": "completed"
            }
            
        except Exception as e:
            logger.error(f"RAG with fallback failed: {e}")
            return {
                "query": query,
                "answer": f"Error: {str(e)}",
                "local_context": "",
                "web_context": "",
                "used_fallback": False,
                "local_results_count": 0,
                "status": "error"
            }

    def build_rag_prompt(self, query: str, context: str) -> str:
        """Build RAG prompt for LLM"""
        return f"""Context information:
{context}

Question: {query}

Please answer the question based on the provided context. If the context doesn't contain enough information to answer the question, say so clearly.

Answer:"""
    
    async def generate_answer(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Complete RAG pipeline with LLM generation"""
        try:
            # Retrieve context
            context = self.retrieve_context(query, max_results)
            
            # Build prompt
            prompt = self.build_rag_prompt(query, context)
            
            # Generate answer
            answer = await ollama_client.generate_response(prompt)
            
            return {
                "query": query,
                "context": context,
                "answer": answer,
                "status": "completed"
            }
            
        except Exception as e:
            logger.error(f"RAG generation failed: {e}")
            return {
                "query": query,
                "context": "",
                "answer": f"Error: {str(e)}",
                "status": "error"
            }
    
    async def stream_answer(self, query: str, max_results: int = 5):
        """Stream RAG answer"""
        try:
            # Retrieve context
            context = self.retrieve_context(query, max_results)
            
            # Build prompt
            prompt = self.build_rag_prompt(query, context)
            
            # Stream answer
            async for chunk in ollama_client.stream_response(prompt):
                yield chunk
                
        except Exception as e:
            logger.error(f"RAG streaming failed: {e}")
            yield f"Error: {str(e)}"

# Update global pipeline
rag_pipeline = RAGPipeline(vector_store)
