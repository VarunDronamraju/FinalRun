#!/usr/bin/env python3
import logging
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def download_embedding_model(model_name: str = "all-MiniLM-L6-v2"):
    """Download and cache embedding model"""
    try:
        logger.info(f"Downloading model: {model_name}")
        model = SentenceTransformer(model_name)
        logger.info(f"Model downloaded and cached successfully")
        logger.info(f"Embedding dimension: {model.get_sentence_embedding_dimension()}")
        return True
    except Exception as e:
        logger.error(f"Model download failed: {e}")
        return False

if __name__ == "__main__":
    success = download_embedding_model()
    exit(0 if success else 1)