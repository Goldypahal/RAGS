"""
Adaptive Retrieval RAG: Query Router + Multi-Method Retrieval

Architecture:
    Query → Query Classifier
        ├─ Exact → HashMap
        ├─ Prefix → Trie
        ├─ Keyword → Inverted Index
        ├─ Relationship → Graph
        └─ Semantic → Vector DB
    ↓
    Reciprocal Rank Fusion → LLM

Routes each query to two retrieval methods (run sequentially) and fuses their rankings.
"""

import time
import json
from typing import List, Dict, Set, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "1-vector-rag"))
sys.path.insert(0, str(Path(__file__).parent.parent / "3-hashmap-rag"))
sys.path.insert(0, str(Path(__file__).parent.parent / "4-trie-rag"))
sys.path.insert(0, str(Path(__file__).parent.parent / "2-graph-rag"))
sys.path.insert(0, str(Path(__file__).parent.parent / "8-inverted-index-graph-rag"))

from common.base import (
    Document, RetrievalResult, BaseRAG, TextPreprocessor, QueryClassifier, rank_scores
)
from vector_rag import VectorRAG
from hashmap_rag import HashMapRAG
from trie_rag import TrieRAG
from graph_rag import GraphRAG
from inverted_index_graph_rag import InvertedIndexGraphRAG


@dataclass
class RoutingDecision:
    """Records query routing decision."""
    query: str
    query_type: str
    methods_used: List[str]
    retrieval_times: Dict[str, float]
    results_per_method: Dict[str, int]
    final_doc_count: int


class QueryRouter:
    """Routes queries to appropriate retrieval methods."""
    
    SYSTEM_TO_METHODS = {
        'VectorRAG': ['vector', 'inverted_index'],
        'InvertedIndexGraphRAG': ['inverted_index', 'graph'],
        'TrieRAG': ['trie', 'inverted_index'],
        'TrieGraphRAG': ['trie', 'graph'],
        'HashMapTrieRAG': ['hashmap', 'trie'],
        'HashMapGraphRAG': ['hashmap', 'graph'],
        'GraphRAG': ['graph', 'inverted_index'],
        'HashMapRAG': ['hashmap', 'vector']
    }
    
    def __init__(self, learned_router_path: Optional[str] = None):
        """
        Heuristic routing by default. Pass ``learned_router_path`` to route with a
        model saved by ``benchmark/train_and_eval_router.py``. Never load a router
        trained on the same queries you are about to benchmark.
        """
        self.routing_history: List[RoutingDecision] = []
        self.learned_router = None
        if learned_router_path:
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from benchmark.learned_router import LearnedRouter
            self.learned_router = LearnedRouter.load(learned_router_path)
        
    def route(self, query: str) -> Tuple[str, List[str]]:
        """Determine best retrieval method(s) for query."""
        if self.learned_router is not None:
            pred_sys, conf = self.learned_router.predict(query)
            methods = self.SYSTEM_TO_METHODS.get(pred_sys, ['inverted_index', 'vector'])
            return f"learned_{pred_sys}", methods
            
        query_type = QueryClassifier.classify(query)
        methods = []
        
        if query_type == 'exact':
            methods = ['hashmap', 'vector']  # Primary + backup
        elif query_type == 'prefix':
            methods = ['trie', 'inverted_index']
        elif query_type == 'keyword':
            methods = ['inverted_index', 'vector']
        elif query_type == 'relationship':
            methods = ['graph', 'inverted_index']
        elif query_type == 'semantic':
            methods = ['vector', 'graph']
        else:  # Default to mixed approach
            methods = ['vector', 'graph', 'inverted_index']
        
        return query_type, methods
    
    def record_decision(self, decision: RoutingDecision) -> None:
        """Record routing decision for analysis."""
        self.routing_history.append(decision)


class ContextMerger:
    """Merges results from multiple retrieval methods with weighted Reciprocal Rank Fusion."""

    RRF_K = 60  # Cormack et al. (2009)

    @staticmethod
    def merge(results: Dict[str, RetrievalResult], method_weights: Dict[str, float],
              top_k: int = 5) -> Tuple[List[Document], List[float]]:
        """
        Fuse rankings by rank, not raw score: each method emits scores on its own
        scale (cosine <= 1, BM25 unbounded, trie hit counts), so score-based
        mixing lets whichever scale is largest dominate.
        """
        doc_scores: Dict[str, float] = {}
        doc_map: Dict[str, Document] = {}

        for method, result in results.items():
            weight = method_weights.get(method, 1.0)

            for rank, doc in enumerate(result.documents, 1):
                doc_map[doc.doc_id] = doc
                doc_scores[doc.doc_id] = doc_scores.get(doc.doc_id, 0.0) + weight / (ContextMerger.RRF_K + rank)

        sorted_items = rank_scores(doc_scores)
        
        merged_docs = []
        merged_scores = []
        
        for doc_id, score in sorted_items[:top_k]:
            merged_docs.append(doc_map[doc_id])
            merged_scores.append(float(score))
        
        return merged_docs, merged_scores


class AdaptiveRetrievalRAG(BaseRAG):
    """
    Adaptive Multi-Method Retrieval RAG.
    
    Characteristics:
    - Latency: Sum of the selected methods (run sequentially)
    - Accuracy: Very High (multiple confirmation)
    - Cost: Medium (multiple lookups, but smart routing)
    - Memory: Medium-High (multiple indices)
    
    Best for:
    - General-purpose retrieval
    - Unknown query types
    - High-quality results required
    - Publication: STRONG CANDIDATE
    
    Research Question:
    Can intelligent query routing + method fusion outperform 
    single-method systems?
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("AdaptiveRetrievalRAG", config)
        
        # Initialize all sub-systems (config is forwarded, e.g. {'embedder': 'tfidf'})
        self.vector_rag = VectorRAG(self.config)
        self.hashmap_rag = HashMapRAG(self.config)
        self.trie_rag = TrieRAG(self.config)
        self.graph_rag = GraphRAG(self.config)
        self.inverted_rag = InvertedIndexGraphRAG(self.config)

        self.router = QueryRouter(self.config.get('learned_router_path'))
        self.merger = ContextMerger()
        
        # Method weights for merging
        self.method_weights = {
            'hashmap': 2.0,      # Exact matches are high confidence
            'trie': 1.5,         # Hierarchical matches
            'inverted_index': 1.5,  # Keyword matches
            'graph': 1.8,        # Relationship matches
            'vector': 1.3        # Semantic matches
        }
        
    def initialize(self) -> None:
        """Initialize all sub-systems."""
        self.vector_rag.initialize()
        self.hashmap_rag.initialize()
        self.trie_rag.initialize()
        self.graph_rag.initialize()
        self.inverted_rag.initialize()
        self.initialized = True
    
    def index_documents(self, documents: List[Document]) -> None:
        """Index documents in all sub-systems."""
        # Index in all systems
        self.vector_rag.add_documents(documents)
        self.hashmap_rag.add_documents(documents)
        self.trie_rag.add_documents(documents)
        self.graph_rag.add_documents(documents)
        self.inverted_rag.add_documents(documents)

    def add_citation_links(self, links) -> None:
        """Forward citation edges to the graph-backed sub-systems."""
        links = list(links)
        self.graph_rag.add_citation_links(links)
        self.inverted_rag.add_citation_links(links)

    def retrieve(self, query: str, top_k: int = 5) -> RetrievalResult:
        """Retrieve using adaptive routing."""
        start_time = time.perf_counter()

        # Route query to appropriate methods
        query_type, methods = self.router.route(query)

        # Execute selected retrieval methods
        results = {}
        retrieval_times = {}

        for method in methods:
            method_start = time.perf_counter()
            try:
                if method == 'hashmap':
                    results['hashmap'] = self.hashmap_rag.retrieve(query, top_k)
                elif method == 'trie':
                    results['trie'] = self.trie_rag.retrieve(query, top_k)
                elif method == 'graph':
                    results['graph'] = self.graph_rag.retrieve(query, top_k)
                elif method == 'vector':
                    results['vector'] = self.vector_rag.retrieve(query, top_k)
                elif method == 'inverted_index':
                    results['inverted_index'] = self.inverted_rag.retrieve(query, top_k)
                
                retrieval_times[method] = time.perf_counter() - method_start
            except Exception as e:
                print(f"Error in {method} retrieval: {e}")
                continue
        
        # Merge results
        selected_weights = {m: self.method_weights.get(m, 1.0) for m in results.keys()}
        merged_docs, merged_scores = self.merger.merge(results, selected_weights, top_k)
        
        # Record routing decision
        results_per_method = {m: len(r.documents) for m, r in results.items()}
        decision = RoutingDecision(
            query=query,
            query_type=query_type,
            methods_used=methods,
            retrieval_times=retrieval_times,
            results_per_method=results_per_method,
            final_doc_count=len(merged_docs)
        )
        self.router.record_decision(decision)
        
        total_time = time.perf_counter() - start_time
        self.update_metrics(total_time)
        
        return RetrievalResult(
            query=query,
            documents=merged_docs,
            scores=merged_scores,
            retrieval_time=total_time,
            metadata={
                'method': 'adaptive_routing',
                'query_type': query_type,
                'methods_used': methods,
                'method_times': retrieval_times,
                'results_per_method': results_per_method,
                'fusion_method': 'weighted_rrf'
            }
        )
    
    def get_memory_usage(self) -> float:
        """Get total memory usage."""
        return (
            self.vector_rag.get_memory_usage() +
            self.hashmap_rag.get_memory_usage() +
            self.trie_rag.get_memory_usage() +
            self.graph_rag.get_memory_usage() +
            self.inverted_rag.get_memory_usage()
        )
    
    def get_routing_statistics(self) -> Dict[str, Any]:
        """Get routing statistics."""
        total_queries = len(self.router.routing_history)
        
        if total_queries == 0:
            return {'total_queries': 0}
        
        query_types = {}
        method_usage = {}
        
        for decision in self.router.routing_history:
            # Count query types
            query_types[decision.query_type] = query_types.get(decision.query_type, 0) + 1
            
            # Count method usage
            for method in decision.methods_used:
                method_usage[method] = method_usage.get(method, 0) + 1
        
        return {
            'total_queries': total_queries,
            'query_type_distribution': query_types,
            'method_usage_distribution': method_usage
        }


def demo():
    """Demonstration of Adaptive Retrieval RAG."""
    docs = [
        Document(
            doc_id="doc1",
            content="Transformers use attention mechanisms for parallel processing",
            title="Transformers",
            keywords=["transformers", "attention", "neural"]
        ),
        Document(
            doc_id="doc2",
            content="BERT is a bidirectional encoder transformer model",
            title="BERT",
            keywords=["bert", "transformer", "language"]
        ),
        Document(
            doc_id="doc3",
            content="Transfer learning improves model performance",
            title="Transfer Learning",
            keywords=["transfer", "learning"]
        ),
        Document(
            doc_id="doc4",
            content="Attention mechanisms enable efficient computation",
            title="Attention",
            keywords=["attention", "mechanisms", "efficient"]
        ),
    ]
    
    rag = AdaptiveRetrievalRAG()
    rag.initialize()
    rag.add_documents(docs)
    
    # Mix of different query types
    queries = [
        "What is BERT?",           # Exact
        "trans",                    # Prefix
        "How do transformers work?", # Relationship
        "attention mechanisms",      # Keyword
    ]
    
    print("=" * 70)
    print("Adaptive Retrieval RAG Demonstration")
    print("=" * 70)
    
    for query in queries:
        result = rag.retrieve(query, top_k=3)
        print(f"\nQuery: {query}")
        print(f"Query Type: {result.metadata['query_type']}")
        print(f"Methods Used: {result.metadata['methods_used']}")
        print(f"Retrieval Time: {result.retrieval_time*1000:.2f}ms")
        for i, (doc, score) in enumerate(zip(result.documents, result.scores), 1):
            print(f"  [{i}] {doc.title} (score: {score:.2f})")
    
    stats = rag.get_routing_statistics()
    print(f"\n\nRouting Statistics:")
    print(f"  Total Queries: {stats['total_queries']}")
    print(f"  Query Types: {json.dumps(stats['query_type_distribution'], indent=2)}")
    print(f"  Method Usage: {json.dumps(stats['method_usage_distribution'], indent=2)}")
    
    print(f"\nMemory Usage: {rag.get_memory_usage():.2f} MB")


if __name__ == "__main__":
    demo()
