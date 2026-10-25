"""
VectorRAG: Traditional RAG using vector embeddings (Baseline)

Architecture:
    Query → Embedding Model → Vector Database → Top-K Chunks → LLM

This is the standard RAG baseline for comparison.

Embedders (config={'embedder': ...}):
    'minilm' (default)  all-MiniLM-L6-v2 dense embeddings; requires sentence-transformers
    'tfidf'             TF-IDF cosine; a lexical stand-in, NOT a dense semantic baseline
    'hash'              md5-derived vectors; non-semantic, only for plumbing tests

There is deliberately no silent fallback: a missing dependency raises instead of
quietly benchmarking a different (random) embedder under the same name.
"""

import time
import json
import hashlib
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
    """md5-derived vectors. Deterministic but carries no semantic signal."""

    name = 'hash-md5'

    def __init__(self, embedding_dim: int = 128):
        self.embedding_dim = embedding_dim

    def fit(self, texts: List[str]) -> None:
        pass

    def embed(self, text: str) -> np.ndarray:
        hash_bytes = hashlib.md5(text.encode()).digest()
        embedding = np.array(
            [(hash_bytes[i % len(hash_bytes)] / 255.0) - 0.5 for i in range(self.embedding_dim)]
        )
        norm = np.linalg.norm(embedding)
        return embedding / norm if norm > 0 else embedding

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        return np.stack([self.embed(t) for t in texts]) if texts else np.zeros((0, self.embedding_dim))


class SentenceTransformerEmbedder:
    """Dense semantic embeddings via SentenceTransformer."""

    _models: Dict[str, Any] = {}

    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.model_name = model_name
        self.name = model_name
        self.cache: Dict[str, np.ndarray] = {}
        self.model = self.get_model(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()

    @classmethod
    def get_model(cls, model_name: str):
        if model_name not in cls._models:
            from sentence_transformers import SentenceTransformer
            cls._models[model_name] = SentenceTransformer(model_name)
        return cls._models[model_name]

    def fit(self, texts: List[str]) -> None:
        pass

    def embed(self, text: str) -> np.ndarray:
        if text not in self.cache:
            self.cache[text] = self.model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
        return self.cache[text]

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        missing = [t for t in dict.fromkeys(texts) if t not in self.cache]
        if missing:
            vecs = self.model.encode(missing, batch_size=64, convert_to_numpy=True, normalize_embeddings=True)
            self.cache.update(zip(missing, vecs))
        return np.stack([self.cache[t] for t in texts]) if texts else np.zeros((0, self.embedding_dim))


class TfidfEmbedder:
    """L2-normalized TF-IDF vectors (sparse). Lexical, fitted on the indexed corpus."""

    name = 'tfidf'

    def __init__(self):
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.vectorizer = TfidfVectorizer(sublinear_tf=True, stop_words='english')
        self.embedding_dim = 0

    def fit(self, texts: List[str]) -> None:
        self.vectorizer.fit(texts)
        self.embedding_dim = len(self.vectorizer.vocabulary_)

    def embed(self, text: str):
        return self.vectorizer.transform([text])

    def embed_batch(self, texts: List[str]):
        return self.vectorizer.transform(texts)


def build_embedder(name: str):
    """Construct an embedder by name; raises instead of silently substituting another."""
    if name == 'minilm':
        try:
            import sentence_transformers  # noqa: F401
        except ImportError as e:
            raise RuntimeError(
                "VectorRAG(embedder='minilm') requires sentence-transformers "
                "(pip install sentence-transformers). Use config={'embedder': 'tfidf'} "
                "for a lexical stand-in, and label results accordingly."
            ) from e
        return SentenceTransformerEmbedder()
    if name == 'tfidf':
        return TfidfEmbedder()
    if name == 'hash':
        return SimpleEmbedder()
    raise ValueError(f"Unknown embedder '{name}' (expected 'minilm', 'tfidf' or 'hash')")


class VectorDatabase:
    """In-memory exact cosine search over a single stacked (dense or sparse) matrix."""

    def __init__(self):
        self.doc_ids: List[str] = []
        self.doc_map: Dict[str, Document] = {}
        self.matrix = None

    def build(self, documents: List[Document], matrix) -> None:
        """Replace the index with row-aligned documents and vectors (rows are L2-normalized)."""
        self.doc_ids = [d.doc_id for d in documents]
        self._id_array = np.array(self.doc_ids)
        self.doc_map = {d.doc_id: d for d in documents}
        self.matrix = matrix

    def search(self, query_vector, top_k: int = 5) -> List[tuple]:
        """Top-k by cosine similarity, ties broken by doc_id."""
        if self.matrix is None or not self.doc_ids:
            return []

        if hasattr(query_vector, 'toarray'):
            sims = np.asarray((self.matrix @ query_vector.T).toarray()).ravel()
        else:
            sims = np.asarray(self.matrix @ query_vector).ravel()

        # lexsort: last key is primary -> score desc, then doc_id asc
        order = np.lexsort((self._id_array, -sims))[:top_k]
        return [(self.doc_ids[i], float(sims[i])) for i in order]

    def get_document(self, doc_id: str) -> Optional[Document]:
        """Get document by ID."""
        return self.doc_map.get(doc_id)


class VectorRAG(BaseRAG):
    """
    Vector-based RAG system.

    Metrics:
    - Latency: Medium (query embedding dominates; search is one matrix product)
    - Accuracy: High (semantic understanding)
    - Cost: Medium (embedding computation)
    - Memory: Medium
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("VectorRAG", config)
        self.embedder_name = self.config.get('embedder', 'minilm')
        self.embedder = build_embedder(self.embedder_name)
        self.vector_db = VectorDatabase()

    def initialize(self) -> None:
        """Initialize the system."""
        self.initialized = True

    def index_documents(self, documents: List[Document]) -> None:
        """(Re)build the index over all documents added so far."""
        texts = [doc.content for doc in self.documents]
        self.embedder.fit(texts)
        self.vector_db.build(self.documents, self.embedder.embed_batch(texts))

    def retrieve(self, query: str, top_k: int = 5) -> RetrievalResult:
        """Retrieve relevant documents using vector similarity."""
        start_time = time.perf_counter()

        query_vector = self.embedder.embed(query)
        search_results = self.vector_db.search(query_vector, top_k)

        retrieved_docs = []
        scores = []

        for doc_id, score in search_results:
            doc = self.vector_db.get_document(doc_id)
            if doc:
                retrieved_docs.append(doc)
                scores.append(score)

        retrieval_time = time.perf_counter() - start_time
        self.update_metrics(retrieval_time)

        return RetrievalResult(
            query=query,
            documents=retrieved_docs,
            scores=scores,
            retrieval_time=retrieval_time,
            metadata={
                'method': 'vector_similarity',
                'embedding_model': self.embedder.name,
                'vector_dimension': self.embedder.embedding_dim
            }
        )

    def get_memory_usage(self) -> float:
        """Index memory in MB (vectors only; excludes model weights)."""
        m = self.vector_db.matrix
        if m is None:
            return 0.0
        if hasattr(m, 'data'):
            total = m.data.nbytes + getattr(m, 'indices', np.empty(0)).nbytes + getattr(m, 'indptr', np.empty(0)).nbytes
        else:
            total = m.nbytes
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
