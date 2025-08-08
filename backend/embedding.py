import logging
from typing import List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
import torch

logger = logging.getLogger(__name__)

class EmbeddingEngine:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Embedding engine initialized with device: {self.device}")
    
    def load_model(self):
        """Load embedding model"""
        if self.model is None:
            logger.info(f"Loading model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name, device=self.device)
            logger.info("Model loaded successfully")
    
    def embed_texts(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Generate embeddings for list of texts"""
        if not self.model:
            self.load_model()
        
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        
        return embeddings.tolist()
    
    def embed_single_text(self, text: str) -> List[float]:
        """Generate embedding for single text"""
        return self.embed_texts([text])[0]
    
    def get_embedding_dimension(self) -> int:
        """Get embedding dimension"""
        if not self.model:
            self.load_model()
        return self.model.get_sentence_embedding_dimension()

# Global embedding engine
embedding_engine = EmbeddingEngine()