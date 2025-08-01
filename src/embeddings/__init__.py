"""
Embeddings and vector database module for document retrieval and similarity search.
"""

from .embedding_manager import EmbeddingManager
from .vector_store import VectorStore

__all__ = [
    "EmbeddingManager",
    "VectorStore"
] 