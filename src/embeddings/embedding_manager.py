from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
import numpy as np
import logging
from pathlib import Path
import pickle
from config import settings

class EmbeddingManager:
    
    
    def __init__(self, model_name: str = None, cache_dir: str = None):
        self.model_name = model_name or settings.embedding_model
        self.cache_dir = Path(cache_dir or f"{settings.vector_db_path}/embeddings_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
        self.model = None
        self._load_model()
    
    def _load_model(self):
        
        try:
            self.logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            self.logger.info("Embedding model loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load embedding model: {str(e)}")
            raise
    
    def generate_embeddings(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        
        if not texts:
            return np.array([])
        
        try:
            clean_texts = [self._clean_text(text) for text in texts if text.strip()]
            
            if not clean_texts:
                self.logger.warning("No valid texts to embed after cleaning")
                return np.array([])
            
            self.logger.info(f"Generating embeddings for {len(clean_texts)} texts")
            embeddings = self.model.encode(
                clean_texts,
                batch_size=batch_size,
                show_progress_bar=True,
                convert_to_numpy=True
            )
            
            self.logger.info(f"Generated embeddings shape: {embeddings.shape}")
            return embeddings
            
        except Exception as e:
            self.logger.error(f"Error generating embeddings: {str(e)}")
            raise
    
    def generate_query_embedding(self, query: str) -> np.ndarray:
       
        try:
            clean_query = self._clean_text(query)
            if not clean_query.strip():
                raise ValueError("Empty query after cleaning")
            
            embedding = self.model.encode([clean_query], convert_to_numpy=True)
            return embedding[0]
            
        except Exception as e:
            self.logger.error(f"Error generating query embedding: {str(e)}")
            raise
    
    def _clean_text(self, text: str) -> str:
        
        if not text:
            return ""
        
        cleaned = text.strip()
        
        cleaned = ' '.join(cleaned.split())
        
        if len(cleaned) > 2000:
            cleaned = cleaned[:2000] + "..."
            
        return cleaned
    
    def compute_similarity(self, 
                          embedding1: np.ndarray, 
                          embedding2: np.ndarray) -> float:
       
        try:
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
            return float(similarity)
            
        except Exception as e:
            self.logger.error(f"Error computing similarity: {str(e)}")
            return 0.0
    
    def save_embeddings(self, embeddings: np.ndarray, filename: str):
        
        try:
            filepath = self.cache_dir / f"{filename}.pkl"
            with open(filepath, 'wb') as f:
                pickle.dump(embeddings, f)
            self.logger.info(f"Embeddings saved to {filepath}")
        except Exception as e:
            self.logger.error(f"Error saving embeddings: {str(e)}")
            raise
    
    def load_embeddings(self, filename: str) -> Optional[np.ndarray]:
        
        try:
            filepath = self.cache_dir / f"{filename}.pkl"
            if filepath.exists():
                with open(filepath, 'rb') as f:
                    embeddings = pickle.load(f)
                self.logger.info(f"Embeddings loaded from {filepath}")
                return embeddings
            else:
                self.logger.warning(f"Embeddings file not found: {filepath}")
                return None
        except Exception as e:
            self.logger.error(f"Error loading embeddings: {str(e)}")
            return None
    
    def get_model_info(self) -> Dict[str, Any]:
        
        return {
            "model_name": self.model_name,
            "max_seq_length": getattr(self.model, 'max_seq_length', 'Unknown'),
            "embedding_dimension": self.model.get_sentence_embedding_dimension(),
            "cache_dir": str(self.cache_dir)
        } 