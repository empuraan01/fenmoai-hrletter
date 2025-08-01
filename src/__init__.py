


__version__ = "1.0.0"
__author__ = "FenmoAI Team"

# Core imports
from .document_processor import PDFParser, IntelligentTextChunker
from .data import EmployeeManager
from .agent import GeminiClient, RAGEngine
from .embeddings import EmbeddingManager, VectorStore

__all__ = [
    "PDFParser",
    "IntelligentTextChunker", 
    "EmployeeManager",
    "GeminiClient",
    "RAGEngine",
    "EmbeddingManager",
    "VectorStore"
] 