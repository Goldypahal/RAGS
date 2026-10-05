"""
InvertedIndex+GraphRAG: Search Engine Speed + Graph Reasoning

Architecture:
    Query → Inverted Index (keyword search) → Graph Expansion → Documents

Like search engines but with semantic reasoning through graphs.
"""

import time
import json
from typing import List, Dict, Set, Any, Optional, Tuple
from collections import defaultdict
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "2-graph-rag"))

from common.base import Document, RetrievalResult, BaseRAG, TextPreprocessor
from graph_rag import KnowledgeGraph, SimpleEntityExtractor


class InvertedIndex:
    """Traditional inverted index like search engines."""
    
    def __init__(self):
        # word -> posting list (doc_ids)
        self.postings: Dict[str, Set[str]] = defaultdict(set)
        # doc_id -> document frequency for scoring
        self.doc_freq: Dict[str, int] = defaultdict(int)
        self.vocab_size = 0
        
    def add_document(self, doc: Document) -> None:
        """Add document to inverted index."""
        words = set(TextPreprocessor.tokenize(doc.content))
        
        for word in words:
            self.postings[word].add(doc.doc_id)
        
        self.doc_freq[doc.doc_id] = len(words)
        self.vocab_size = len(self.postings)
    
    def search(self, query: str, limit: int = 1000) -> List[Tuple[str, int]]:
        """Search for query terms and return matching documents."""
        query_terms = TextPreprocessor.tokenize(query)
        
        # Find documents matching ANY query term (OR semantics)
        doc_scores: Dict[str, int] = defaultdict(int)
        
        for term in query_terms:
            if term in self.postings:
                for doc_id in self.postings[term]:
                    doc_scores[doc_id] += 1
        
        # Sort by relevance
        results = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        return results[:limit]
    
    def search_and_phrase(self, query: str) -> List[Tuple[str, int]]:
        """Search for ALL terms (AND semantics)."""
        query_terms = TextPreprocessor.tokenize(query)
        
        if not query_terms:
            return []
        
        # Start with first term
        doc_ids = self.postings[query_terms[0]].copy()
        
        # Intersect with other terms
        for term in query_terms[1:]:
            if term in self.postings:
                doc_ids &= self.postings[term]
            else:
                doc_ids = set()
                break
        
        return [(doc_id, len(query_terms)) for doc_id in doc_ids]


class InvertedIndexGraphIndex:
    """Inverted Index + Knowledge Graph combination."""
    
    def __init__(self):
        self.inverted_index = InvertedIndex()
        self.graph = KnowledgeGraph()
        self.doc_map: Dict[str, Document] = {}
        self.entity_extractor = SimpleEntityExtractor()
        
    def add_document(self, doc: Document) -> None:
        """Add document to index."""
        self.doc_map[doc.doc_id] = doc
        
        # Index in inverted index
        self.inverted_index.add_document(doc)
        
        # Extract entities for graph
        entities = self.entity_extractor.extract(doc.content, doc.doc_id)
        for entity_name, entity_type in entities:
            self.graph.add_entity(entity_name, entity_type, doc.doc_id)
        
        # Add relationships
        entity_names = [e[0] for e in entities]
        for i, source in enumerate(entity_names):
            for target in entity_names[i+1:]:
                self.graph.add_relationship(source, target, "co-occurs")


class InvertedIndexGraphRAG(BaseRAG):
    """
    Inverted Index + Graph hybrid RAG.
    
    Characteristics:
    - Latency: Good (inverted index + graph traversal)
    - Accuracy: High (keyword + relationship matching)
    - Cost: Very Low (no embeddings)
    - Memory: Low-Medium
    
    Best for:
    - Large document collections
    - Traditional search + semantic reasoning
    - Information retrieval tasks
    - Publication: Strong candidate
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("InvertedIndex+GraphRAG", config)
        self.index = InvertedIndexGraphIndex()
        
    def initialize(self) -> None:
        """Initialize the system."""
        self.initialized = True
    
    def index_documents(self, documents: List[Document]) -> None:
        """Index documents."""
        for doc in documents:
            self.index.add_document(doc)
    
    def retrieve(self, query: str, top_k: int = 5, 
                 graph_depth: int = 2, use_and_semantics: bool = False) -> RetrievalResult:
        """Retrieve using inverted index + graph expansion."""
        start_time = time.time()
        
        doc_scores: Dict[str, float] = {}
        search_stats = {'inverted_index': 0, 'graph_expansion': 0}
        
        # Phase 1: Inverted Index search
        if use_and_semantics:
            initial_results = self.index.inverted_index.search_and_phrase(query)
        else:
            initial_results = self.index.inverted_index.search(query)
        
        search_stats['inverted_index'] = len(initial_results)
        
        for doc_id, score in initial_results:
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + float(score) * 2.0
        
        # Phase 2: Extract entities and expand through graph
        query_entities = self.index.entity_extractor.extract(query, "query")
        
        for entity_name, _ in query_entities:
            entity_lower = entity_name.lower()
            if entity_lower in self.index.graph.entities:
                search_stats['graph_expansion'] += 1
                
                entity = self.index.graph.entities[entity_lower]
                
                # Direct entity docs
                for doc_id in entity.doc_ids:
                    doc_scores[doc_id] = doc_scores.get(doc_id, 0) + 2.0
                
                # Related entities through graph
                neighbors = self.index.graph.get_neighbors(entity_lower, depth=graph_depth)
                for neighbor in neighbors:
                    if neighbor in self.index.graph.entities:
                        for doc_id in self.index.graph.entities[neighbor].doc_ids:
                            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + 1.0
        
        # Sort by score
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Build result
        retrieved_docs = []
        scores = []
        
        for doc_id, score in sorted_docs[:top_k]:
            if doc_id in self.index.doc_map:
                retrieved_docs.append(self.index.doc_map[doc_id])
                scores.append(float(score))
        
        retrieval_time = time.time() - start_time
        self.update_metrics(retrieval_time)
        
        return RetrievalResult(
            query=query,
            documents=retrieved_docs,
            scores=scores,
            retrieval_time=retrieval_time,
            metadata={
                'method': 'inverted_index_graph_hybrid',
                'inverted_index_matches': search_stats['inverted_index'],
                'graph_expansions': search_stats['graph_expansion'],
                'graph_depth': graph_depth,
                'and_semantics': use_and_semantics,
                'vocab_size': self.index.inverted_index.vocab_size,
                'graph_nodes': len(self.index.graph.entities),
                'graph_edges': len(self.index.graph.relationships)
            }
        )
    
    def get_memory_usage(self) -> float:
        """Get memory usage in MB."""
        import sys
        
        total = sys.getsizeof(self.index.inverted_index.postings)
        for term, doc_ids in self.index.inverted_index.postings.items():
            total += sys.getsizeof(term) + sys.getsizeof(doc_ids)
        
        total += sys.getsizeof(self.index.graph.entities)
        total += sys.getsizeof(self.index.graph.relationships)
        
        for entity in self.index.graph.entities.values():
            total += sys.getsizeof(entity.name)
        
        return total / (1024 * 1024)


def demo():
    """Demonstration of InvertedIndex+GraphRAG."""
    docs = [
        Document(
            doc_id="doc1",
            content="Transformers use attention mechanisms for parallel processing",
            title="Transformers"
        ),
        Document(
            doc_id="doc2",
            content="BERT is a bidirectional encoder transformer model",
            title="BERT"
        ),
        Document(
            doc_id="doc3",
            content="Attention mechanism enables efficient computation in transformers",
            title="Attention"
        ),
        Document(
            doc_id="doc4",
            content="GPT uses autoregressive transformer models for language generation",
            title="GPT"
        ),
    ]
    
    rag = InvertedIndexGraphRAG()
    rag.initialize()
    rag.add_documents(docs)
    
    queries = [
        "transformer attention",
        "BERT model",
        "attention mechanisms"
    ]
    
    print("=" * 60)
    print("InvertedIndex+GraphRAG Demonstration")
    print("=" * 60)
    
    for query in queries:
        result = rag.retrieve(query, top_k=3, graph_depth=2)
        print(f"\nQuery: {query}")
        print(f"Retrieval Time: {result.retrieval_time*1000:.2f}ms")
        print(f"Index Matches: {result.metadata['inverted_index_matches']}, "
              f"Graph Expansions: {result.metadata['graph_expansions']}")
        for i, (doc, score) in enumerate(zip(result.documents, result.scores), 1):
            print(f"  [{i}] {doc.title} (score: {score:.1f})")
    
    print(f"\n\nIndex Statistics:")
    print(f"  Vocabulary: {rag.index.inverted_index.vocab_size} terms")
    print(f"  Graph Nodes: {len(rag.index.graph.entities)}")
    print(f"  Graph Edges: {len(rag.index.graph.relationships)}")
    print(f"  Documents: {len(rag.index.doc_map)}")
    print(f"  Memory: {rag.get_memory_usage():.2f} MB")


if __name__ == "__main__":
    demo()
