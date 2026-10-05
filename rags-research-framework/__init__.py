"""RAG Research Framework - Production-Ready Research Implementation"""

__version__ = "1.0.0"
__author__ = "RAG Research Team"
__description__ = "Comprehensive comparison of 9 RAG architectures"

from common.base import (
    Document,
    RetrievalResult,
    BenchmarkResult,
    BaseRAG,
    QueryClassifier,
    TextPreprocessor,
)

__all__ = [
    'Document',
    'RetrievalResult',
    'BenchmarkResult',
    'BaseRAG',
    'QueryClassifier',
    'TextPreprocessor',
]
