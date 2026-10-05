"""
Base classes for RAG systems.
Publication-ready implementations for research.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
import hashlib
import time


@dataclass
class Document:
    """Represents a document in the knowledge base."""
    doc_id: str
    content: str
    title: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    keywords: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert document to dictionary."""
        return {
            'doc_id': self.doc_id,
            'content': self.content,
            'title': self.title,
            'metadata': self.metadata,
            'keywords': self.keywords,
            'created_at': self.created_at
        }


@dataclass
class RetrievalResult:
    """Represents a retrieval result."""
    query: str
    documents: List[Document]
    scores: List[float]
    retrieval_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'query': self.query,
            'documents': [doc.to_dict() for doc in self.documents],
            'scores': self.scores,
            'retrieval_time': self.retrieval_time,
            'metadata': self.metadata
        }


@dataclass
class BenchmarkResult:
    """Represents benchmark metrics."""
    architecture: str
    query: str
    retrieval_time: float
    memory_usage: float
    documents_retrieved: int
    accuracy: float = 0.0
    recall: float = 0.0
    precision: float = 0.0
    mrr: float = 0.0  # Mean Reciprocal Rank
    ndcg: float = 0.0  # Normalized Discounted Cumulative Gain
    hallucination_rate: float = 0.0
    token_cost: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'architecture': self.architecture,
            'query': self.query,
            'retrieval_time': self.retrieval_time,
            'memory_usage': self.memory_usage,
            'documents_retrieved': self.documents_retrieved,
            'accuracy': self.accuracy,
            'recall': self.recall,
            'precision': self.precision,
            'mrr': self.mrr,
            'ndcg': self.ndcg,
            'hallucination_rate': self.hallucination_rate,
            'token_cost': self.token_cost
        }


class BaseRAG(ABC):
    """Base class for all RAG implementations."""
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
        self.documents: List[Document] = []
        self.initialized = False
        self.metrics = {
            'total_queries': 0,
            'total_retrieval_time': 0.0,
            'avg_retrieval_time': 0.0
        }
        
    @abstractmethod
    def initialize(self) -> None:
        """Initialize the RAG system."""
        pass
    
    @abstractmethod
    def index_documents(self, documents: List[Document]) -> None:
        """Index documents for retrieval."""
        pass
    
    @abstractmethod
    def retrieve(self, query: str, top_k: int = 5) -> RetrievalResult:
        """Retrieve relevant documents."""
        pass
    
    def add_documents(self, documents: List[Document]) -> None:
        """Add documents to the system."""
        self.documents.extend(documents)
        self.index_documents(documents)
    
    def clear(self) -> None:
        """Clear all indexed data."""
        self.documents = []
        self.metrics = {
            'total_queries': 0,
            'total_retrieval_time': 0.0,
            'avg_retrieval_time': 0.0
        }
    
    def update_metrics(self, retrieval_time: float) -> None:
        """Update system metrics."""
        self.metrics['total_queries'] += 1
        self.metrics['total_retrieval_time'] += retrieval_time
        self.metrics['avg_retrieval_time'] = (
            self.metrics['total_retrieval_time'] / 
            self.metrics['total_queries']
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get system metrics."""
        return self.metrics.copy()
    
    def get_memory_usage(self) -> float:
        """Get memory usage in MB. Override in subclasses for accuracy."""
        import sys
        return sum(
            sys.getsizeof(doc) for doc in self.documents
        ) / (1024 * 1024)
    
    @staticmethod
    def hash_text(text: str) -> str:
        """Generate hash of text."""
        return hashlib.sha256(text.encode()).hexdigest()[:8]


class QueryClassifier:
    """Classify queries for adaptive retrieval."""
    
    EXACT_KEYWORDS = {'what is', 'define', 'what are', 'who is', 'which'}
    PREFIX_KEYWORDS = {'autocomplete', 'suggest', 'complete', 'find similar'}
    RELATION_KEYWORDS = {'related', 'connected', 'how', 'why', 'evolve', 'depend'}
    SEMANTIC_KEYWORDS = {'about', 'discuss', 'explain', 'summarize', 'describe'}
    
    @classmethod
    def classify(cls, query: str) -> str:
        """Classify query type."""
        query_lower = query.lower()
        
        # Check for exact queries
        if any(kw in query_lower for kw in cls.EXACT_KEYWORDS):
            return 'exact'
        
        # Check for prefix queries
        if any(kw in query_lower for kw in cls.PREFIX_KEYWORDS):
            return 'prefix'
        
        # Check for relationship queries
        if any(kw in query_lower for kw in cls.RELATION_KEYWORDS):
            return 'relationship'
        
        # Default to semantic
        return 'semantic'


class TextPreprocessor:
    """Text preprocessing utilities."""
    
    @staticmethod
    def normalize(text: str) -> str:
        """Normalize text."""
        return text.lower().strip()
    
    @staticmethod
    def extract_keywords(text: str, n_keywords: int = 10) -> List[str]:
        """Extract keywords from text."""
        # Simple keyword extraction - split and filter
        words = text.lower().split()
        # Remove common stopwords
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'be', 'have', 'has', 'do',
            'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might'
        }
        keywords = [w for w in words if w not in stopwords and len(w) > 3]
        return list(dict.fromkeys(keywords))[:n_keywords]
    
    @staticmethod
    def tokenize(text: str) -> List[str]:
        """Simple tokenization."""
        return text.lower().split()


if __name__ == "__main__":
    print("Base RAG module loaded successfully")
