"""
HashMapRAG: Direct HashMap-based Retrieval

Architecture:
    Query → Entity Extraction → HashMap Lookup → Documents

O(1) exact matching. Very fast but semantic-blind.
"""

import time
import json
from typing import List, Dict, Set, Any, Optional
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.base import Document, RetrievalResult, BaseRAG, TextPreprocessor


class HashMapIndex:
    """HashMap-based index for exact matching."""
    
    def __init__(self):
        # entity_name -> list of doc_ids
        self.entity_index: Dict[str, Set[str]] = {}
        # doc_id -> document
        self.doc_map: Dict[str, Document] = {}
        # Store all unique entities
        self.entities: Set[str] = set()
        
    def add_document(self, doc: Document) -> None:
        """Add document to index."""
        self.doc_map[doc.doc_id] = doc
        
        # Index keywords
        keywords = doc.keywords or TextPreprocessor.extract_keywords(doc.content)
        for keyword in keywords:
            key = keyword.lower()
            if key not in self.entity_index:
                self.entity_index[key] = set()
            self.entity_index[key].add(doc.doc_id)
            self.entities.add(key)
        
        # Index title
        if doc.title:
            title_key = doc.title.lower()
            if title_key not in self.entity_index:
                self.entity_index[title_key] = set()
            self.entity_index[title_key].add(doc.doc_id)
            self.entities.add(title_key)
    
    def lookup(self, query_term: str) -> Set[str]:
        """O(1) lookup by exact term."""
        key = query_term.lower()
        return self.entity_index.get(key, set())
    
    def lookup_multi(self, query_terms: List[str]) -> Set[str]:
        """Lookup multiple terms and return union."""
        results = set()
        for term in query_terms:
            results.update(self.lookup(term))
        return results
    
    def get_document(self, doc_id: str) -> Optional[Document]:
        """Get document by ID."""
        return self.doc_map.get(doc_id)


class HashMapRAG(BaseRAG):
    """
    HashMap-based RAG system.
    
    Characteristics:
    - Latency: Excellent (O(1) lookups)
    - Accuracy: Low-Medium (exact matching only)
    - Cost: Very Low
    - Memory: Low
    
    Best for:
    - Exact keyword searches
    - Author names
    - Paper IDs
    - Specific terms
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("HashMapRAG", config)
        self.index = HashMapIndex()
        
    def initialize(self) -> None:
        """Initialize the system."""
        self.initialized = True
    
    def index_documents(self, documents: List[Document]) -> None:
        """Index documents into HashMap."""
        for doc in documents:
            self.index.add_document(doc)
    
    def retrieve(self, query: str, top_k: int = 5) -> RetrievalResult:
        """Retrieve documents using HashMap lookup."""
        start_time = time.time()
        
        # Extract query terms
        query_terms = TextPreprocessor.extract_keywords(query, n_keywords=10)
        
        # HashMap lookup
        doc_ids = self.index.lookup_multi(query_terms)
        
        # Score documents by frequency of matching terms
        doc_scores: Dict[str, float] = {}
        for term in query_terms:
            matching_docs = self.index.lookup(term)
            for doc_id in matching_docs:
                doc_scores[doc_id] = doc_scores.get(doc_id, 0) + 1.0
        
        # Sort by score
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Build result
        retrieved_docs = []
        scores = []
        
        for doc_id, score in sorted_docs[:top_k]:
            doc = self.index.get_document(doc_id)
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
                'method': 'hashmap_exact_match',
                'query_terms': query_terms,
                'index_size': len(self.index.entity_index),
                'lookup_complexity': 'O(1)'
            }
        )
    
    def get_memory_usage(self) -> float:
        """Get memory usage in MB."""
        import sys
        
        total = sys.getsizeof(self.index.entity_index)
        total += sys.getsizeof(self.index.doc_map)
        total += sys.getsizeof(self.index.entities)
        
        for key, doc_ids in self.index.entity_index.items():
            total += sys.getsizeof(key)
            total += sys.getsizeof(doc_ids)
        
        return total / (1024 * 1024)


def demo():
    """Demonstration of HashMapRAG."""
    docs = [
        Document(
            doc_id="doc1",
            content="Transformers use attention mechanisms",
            title="Transformers",
            keywords=["transformers", "attention", "neural"]
        ),
        Document(
            doc_id="doc2",
            content="BERT is a transformer-based model",
            title="BERT",
            keywords=["bert", "transformer", "language"]
        ),
        Document(
            doc_id="doc3",
            content="Attention is fundamental to transformers",
            title="Attention Mechanisms",
            keywords=["attention", "mechanisms", "transformers"]
        ),
    ]
    
    rag = HashMapRAG()
    rag.initialize()
    rag.add_documents(docs)
    
    queries = [
        "transformers",
        "attention",
        "bert language model"
    ]
    
    print("=" * 60)
    print("HashMapRAG Demonstration")
    print("=" * 60)
    
    for query in queries:
        result = rag.retrieve(query, top_k=3)
        print(f"\nQuery: {query}")
        print(f"Retrieval Time: {result.retrieval_time*1000:.2f}ms")
        for i, (doc, score) in enumerate(zip(result.documents, result.scores), 1):
            print(f"  [{i}] {doc.title} (matches: {int(score)})")
    
    print(f"\n\nIndex Statistics:")
    print(f"  Index Size: {len(rag.index.entity_index)}")
    print(f"  Documents: {len(rag.index.doc_map)}")
    print(f"  Memory: {rag.get_memory_usage():.2f} MB")


if __name__ == "__main__":
    demo()
