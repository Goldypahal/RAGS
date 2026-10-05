"""
HashMap+GraphRAG: O(1) Entity Lookup + Graph Reasoning

Architecture:
    Query → HashMap (O(1) entity lookup) → Graph Traversal → Context

Combines speed of HashMap with reasoning power of graphs.
"""

import time
import json
from typing import List, Dict, Set, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "2-graph-rag"))
sys.path.insert(0, str(Path(__file__).parent.parent / "3-hashmap-rag"))

from common.base import Document, RetrievalResult, BaseRAG, TextPreprocessor
from graph_rag import KnowledgeGraph, SimpleEntityExtractor
from hashmap_rag import HashMapIndex


class HashMapGraphIndex:
    """Combined HashMap for O(1) entity lookup + graph for reasoning."""
    
    def __init__(self):
        self.entity_hashmap: Dict[str, Set[str]] = {}  # entity -> doc_ids
        self.graph = KnowledgeGraph()
        self.doc_map: Dict[str, Document] = {}
        self.entity_extractor = SimpleEntityExtractor()
        
    def add_document(self, doc: Document) -> None:
        """Add document to both HashMap and Graph."""
        self.doc_map[doc.doc_id] = doc
        
        # Extract entities
        entities = self.entity_extractor.extract(doc.content, doc.doc_id)
        
        # Add to HashMap (O(1) access)
        for entity_name, entity_type in entities:
            entity_lower = entity_name.lower()
            if entity_lower not in self.entity_hashmap:
                self.entity_hashmap[entity_lower] = set()
            self.entity_hashmap[entity_lower].add(doc.doc_id)
        
        # Add to Graph
        for entity_name, entity_type in entities:
            self.graph.add_entity(entity_name, entity_type, doc.doc_id)
        
        # Add relationships between entities in document
        entity_names = [e[0] for e in entities]
        for i, source in enumerate(entity_names):
            for target in entity_names[i+1:]:
                self.graph.add_relationship(source, target, "co-occurs")
    
    def quick_lookup(self, entity: str) -> Set[str]:
        """O(1) HashMap lookup."""
        return self.entity_hashmap.get(entity.lower(), set())
    
    def expand_with_graph(self, entity: str, depth: int = 2) -> Set[str]:
        """Expand entity search through graph."""
        doc_ids = self.quick_lookup(entity)
        
        # Get related entities through graph
        neighbors = self.graph.get_neighbors(entity.lower(), depth=depth)
        for neighbor in neighbors:
            doc_ids.update(self.graph.entities[neighbor].doc_ids)
        
        return doc_ids


class HashMapGraphRAG(BaseRAG):
    """
    HashMap+Graph hybrid RAG system.
    
    Characteristics:
    - Latency: Excellent (O(1) HashMap + O(V+E) graph traversal)
    - Accuracy: High (semantic relationships through graph)
    - Cost: Low
    - Memory: Medium
    
    Best for:
    - Mixed exact + relationship queries
    - Efficient entity discovery with reasoning
    - Question answering
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("HashMap+GraphRAG", config)
        self.index = HashMapGraphIndex()
        
    def initialize(self) -> None:
        """Initialize the system."""
        self.initialized = True
    
    def index_documents(self, documents: List[Document]) -> None:
        """Index documents."""
        for doc in documents:
            self.index.add_document(doc)
    
    def retrieve(self, query: str, top_k: int = 5, 
                 graph_depth: int = 2) -> RetrievalResult:
        """Retrieve using HashMap + Graph traversal."""
        start_time = time.time()
        
        # Extract entities from query
        query_entities = self.index.entity_extractor.extract(query, "query")
        query_entity_names = [e[0] for e in query_entities]
        
        doc_scores: Dict[str, float] = {}
        lookup_results = []
        
        # Phase 1: HashMap lookups (O(1) each)
        for entity_name, _ in query_entities:
            entity_lower = entity_name.lower()
            
            # Direct HashMap lookup
            direct_docs = self.index.quick_lookup(entity_name)
            if direct_docs:
                lookup_results.append((entity_name, 'direct_match'))
                for doc_id in direct_docs:
                    doc_scores[doc_id] = doc_scores.get(doc_id, 0) + 3.0
            
            # Phase 2: Graph expansion for each entity
            related_docs = self.index.expand_with_graph(entity_name, depth=graph_depth)
            for doc_id in related_docs:
                # Weight graph-based results lower than direct matches
                if doc_id not in direct_docs:
                    doc_scores[doc_id] = doc_scores.get(doc_id, 0) + 1.0
                lookup_results.append((entity_name, 'graph_expansion'))
        
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
                'method': 'hashmap_graph_hybrid',
                'query_entities': query_entity_names,
                'graph_depth': graph_depth,
                'hashmap_lookups': len([r for r in lookup_results if r[1] == 'direct_match']),
                'graph_expansions': len([r for r in lookup_results if r[1] == 'graph_expansion']),
                'graph_nodes': len(self.index.graph.entities),
                'graph_edges': len(self.index.graph.relationships)
            }
        )
    
    def get_memory_usage(self) -> float:
        """Get memory usage in MB."""
        import sys
        
        total = sys.getsizeof(self.index.entity_hashmap)
        for k, v in self.index.entity_hashmap.items():
            total += sys.getsizeof(k) + sys.getsizeof(v)
        
        total += sys.getsizeof(self.index.graph.entities)
        total += sys.getsizeof(self.index.graph.relationships)
        total += sys.getsizeof(self.index.graph.adjacency)
        
        for entity in self.index.graph.entities.values():
            total += sys.getsizeof(entity.name)
        
        return total / (1024 * 1024)


def demo():
    """Demonstration of HashMap+GraphRAG."""
    docs = [
        Document(
            doc_id="doc1",
            content="Transformers use attention mechanisms for parallel processing",
            title="Transformers"
        ),
        Document(
            doc_id="doc2",
            content="BERT is built on transformer architecture",
            title="BERT"
        ),
        Document(
            doc_id="doc3",
            content="Attention mechanism enables efficient computation",
            title="Attention"
        ),
        Document(
            doc_id="doc4",
            content="GPT uses transformer models for language generation",
            title="GPT"
        ),
    ]
    
    rag = HashMapGraphRAG()
    rag.initialize()
    rag.add_documents(docs)
    
    queries = [
        "What is BERT?",
        "How do transformers work?",
        "Attention mechanism"
    ]
    
    print("=" * 60)
    print("HashMap+GraphRAG Demonstration")
    print("=" * 60)
    
    for query in queries:
        result = rag.retrieve(query, top_k=3, graph_depth=2)
        print(f"\nQuery: {query}")
        print(f"Retrieval Time: {result.retrieval_time*1000:.2f}ms")
        print(f"Entities Found: {result.metadata['query_entities']}")
        print(f"HashMap Lookups: {result.metadata['hashmap_lookups']}, "
              f"Graph Expansions: {result.metadata['graph_expansions']}")
        for i, (doc, score) in enumerate(zip(result.documents, result.scores), 1):
            print(f"  [{i}] {doc.title} (score: {score:.1f})")
    
    print(f"\n\nIndex Statistics:")
    print(f"  Entities: {len(rag.index.entity_hashmap)}")
    print(f"  Graph Nodes: {len(rag.index.graph.entities)}")
    print(f"  Graph Edges: {len(rag.index.graph.relationships)}")
    print(f"  Documents: {len(rag.index.doc_map)}")
    print(f"  Memory: {rag.get_memory_usage():.2f} MB")


if __name__ == "__main__":
    demo()
