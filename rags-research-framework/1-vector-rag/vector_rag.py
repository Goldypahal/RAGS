"""
VectorRAG: Traditional RAG using vector embeddings (Baseline)

Architecture:
    Query → Embedding Model → Vector Database → Top-K Chunks → LLM

This is the standard RAG baseline for comparison.
"""

import time
import json
from typing import List, Dict, Any, Optional
import numpy as np
from pathlib import Path

# Import base classes
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.base import (
    Document, RetrievalResult, BaseRAG, TextPreprocessor
)


class SimpleEmbedder:
    """Simple embedding model (hash-based for reproducibility)."""
    
    def __init__(self, embedding_dim: int = 128):
        self.embedding_dim = embedding_dim
        self.cache = {}
        
    def build_vocab(self, documents: List[Document]) -> None:
        """Placeholder - not needed for hash-based embeddings."""
        pass
    
    def embed(self, text: str, doc_id: str = "") -> np.ndarray:
        """Create deterministic embedding using hash."""
        import hashlib
        
        # Use cache if available
        if text in self.cache:
            return self.cache[text]
        
        # Create deterministic embedding using hash
        hash_obj = hashlib.md5(text.encode())
        hash_bytes = hash_obj.digest()
        
        # Convert hash bytes to embedding
        embedding = np.zeros(self.embedding_dim)
        for i in range(self.embedding_dim):
            byte_val = hash_bytes[i % len(hash_bytes)]
            embedding[i] = (byte_val / 255.0) - 0.5  # Range: [-0.5, 0.5]
        
        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        self.cache[text] = embedding
        return embedding


class SentenceTransformerEmbedder:
    """Real semantic embedding model using SentenceTransformer."""
    
    _model = None
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.model_name = model_name
        self.cache = {}
        self.embedding_dim = 384
        
    @classmethod
    def get_model(cls, model_name: str):
        if cls._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                cls._model = SentenceTransformer(model_name)
            except Exception as e:
                print(f"Error loading model {model_name}: {e}")
                raise e
        return cls._model
        
    def build_vocab(self, documents: List[Document]) -> None:
        """Placeholder - not needed for sentence transformers."""
        pass
        
    def embed(self, text: str, doc_id: str = "") -> np.ndarray:
        if text in self.cache:
            return self.cache[text]
            
        model = self.get_model(self.model_name)
        embedding = model.encode(text, convert_to_numpy=True)
        
        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
            
        self.cache[text] = embedding
        return embedding



class VectorDatabase:
    """Simple in-memory vector database."""
    
    def __init__(self):
        self.vectors: Dict[str, np.ndarray] = {}
        self.doc_map: Dict[str, Document] = {}
        
    def add(self, doc_id: str, vector: np.ndarray, document: Document) -> None:
        """Add vector to database."""
        self.vectors[doc_id] = vector
        self.doc_map[doc_id] = document
    
    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[tuple]:
        """Search for similar vectors using cosine similarity."""
        if not self.vectors:
            return []
        
        results = []
        
        for doc_id, vector in self.vectors.items():
            # Cosine similarity
            norm_q = np.linalg.norm(query_vector)
            norm_v = np.linalg.norm(vector)
            
            if norm_q == 0 or norm_v == 0:
                similarity = 0.0
            else:
                similarity = np.dot(query_vector, vector) / (norm_q * norm_v)
            
            results.append((doc_id, similarity))
        
        # Sort by similarity descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
    
    def get_document(self, doc_id: str) -> Optional[Document]:
        """Get document by ID."""
        return self.doc_map.get(doc_id)


class VectorRAG(BaseRAG):
    """
    Vector-based RAG system.
    
    Metrics:
    - Latency: Medium (embedding + search)
    - Accuracy: High (semantic understanding)
    - Cost: Medium (embedding computation)
    - Memory: Medium
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("VectorRAG", config)
        # Try to use real semantic embeddings; fall back to hash-based baseline
        try:
            self.embedder = SentenceTransformerEmbedder()
            # Warm up the model on init so first query latency is not skewed
            SentenceTransformerEmbedder.get_model('all-MiniLM-L6-v2')
            print("[VectorRAG] Using SentenceTransformerEmbedder (all-MiniLM-L6-v2)")
        except Exception as e:
            print(f"[VectorRAG] SentenceTransformer unavailable ({e}), falling back to SimpleEmbedder")
            self.embedder = SimpleEmbedder()
        self.vector_db = VectorDatabase()
        self.embed_cache = {}
        
    def initialize(self) -> None:
        """Initialize the system."""
        self.initialized = True
        
    def index_documents(self, documents: List[Document]) -> None:
        """Index documents by creating embeddings."""
        # Embed and index each document
        for doc in documents:
            vector = self.embedder.embed(doc.content, doc.doc_id)
            self.vector_db.add(doc.doc_id, vector, doc)
    
    def retrieve(self, query: str, top_k: int = 5) -> RetrievalResult:
        """Retrieve relevant documents using vector similarity."""
        start_time = time.time()
        
        # Embed query
        query_vector = self.embedder.embed(query)
        
        # Search vector database
        search_results = self.vector_db.search(query_vector, top_k)
        
        # Build result
        retrieved_docs = []
        scores = []
        
        for doc_id, score in search_results:
            doc = self.vector_db.get_document(doc_id)
            if doc:
                retrieved_docs.append(doc)
                scores.append(float(score))
        
        retrieval_time = time.time() - start_time
        self.update_metrics(retrieval_time)
        
        return RetrievalResult(
            query=query,
            documents=retrieved_docs,
            scores=scores,
            retrieval_time=retrieval_time,
            metadata={
                'method': 'vector_similarity',
                'embedding_model': 'tf-idf',
                'vector_dimension': self.embedder.embedding_dim
            }
        )
    
    def get_memory_usage(self) -> float:
        """Get memory usage in MB."""
        import sys
        
        total = sys.getsizeof(self.embed_cache)
        total += sys.getsizeof(self.vector_db.vectors)
        total += sys.getsizeof(self.vector_db.doc_map)
        
        for vector in self.vector_db.vectors.values():
            total += vector.nbytes
        
        for doc in self.documents:
            total += sys.getsizeof(doc.content)
        
        return total / (1024 * 1024)


def demo():
    """Demonstration of VectorRAG."""
    # Create sample documents
    docs = [
        Document(
            doc_id="doc1",
            content="Transformers are neural network architectures based on attention mechanisms.",
            title="Transformers",
            keywords=["transformers", "attention", "neural networks"]
        ),
        Document(
            doc_id="doc2",
            content="BERT is a bidirectional encoder representation transformer model.",
            title="BERT",
            keywords=["BERT", "language model", "transformers"]
        ),
        Document(
            doc_id="doc3",
            content="GPT uses autoregressive transformer language models.",
            title="GPT",
            keywords=["GPT", "language generation", "transformers"]
        ),
        Document(
            doc_id="doc4",
            content="Attention mechanisms enable parallel processing in transformers.",
            title="Attention Mechanisms",
            keywords=["attention", "mechanism", "parallel"]
        ),
    ]
    
    # Initialize RAG
    rag = VectorRAG()
    rag.initialize()
    rag.add_documents(docs)
    
    # Test queries
    queries = [
        "What is BERT?",
        "How do transformers work?",
        "Attention mechanisms explanation",
    ]
    
    print("=" * 60)
    print("VectorRAG Demonstration")
    print("=" * 60)
    
    for query in queries:
        result = rag.retrieve(query, top_k=3)
        print(f"\nQuery: {query}")
        print(f"Retrieval Time: {result.retrieval_time:.4f}s")
        for i, (doc, score) in enumerate(zip(result.documents, result.scores), 1):
            print(f"  [{i}] {doc.title} (score: {score:.3f})")
    
    print(f"\n\nMemory Usage: {rag.get_memory_usage():.2f} MB")
    print(f"Metrics: {json.dumps(rag.get_metrics(), indent=2)}")


if __name__ == "__main__":
    demo()
