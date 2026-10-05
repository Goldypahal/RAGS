"""
Trie+GraphRAG: Hierarchical Search + Graph Reasoning

Architecture:
    Query → Trie (prefix/hierarchy) → Graph (relationships) → Documents

Combines hierarchical organization with semantic relationships.
"""

import time
import json
from typing import List, Dict, Set, Any, Optional
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "4-trie-rag"))
sys.path.insert(0, str(Path(__file__).parent.parent / "2-graph-rag"))

from common.base import Document, RetrievalResult, BaseRAG, TextPreprocessor
from trie_rag import Trie, TopicHierarchy
from graph_rag import KnowledgeGraph, SimpleEntityExtractor


class TrieGraphIndex:
    """Combined Trie for hierarchy + Graph for relationships."""
    
    def __init__(self):
        self.trie = Trie()
        self.hierarchy = TopicHierarchy()
        self.graph = KnowledgeGraph()
        self.doc_map: Dict[str, Document] = {}
        self.entity_extractor = SimpleEntityExtractor()
        
    def add_document(self, doc: Document) -> None:
        """Add document to both Trie and Graph."""
        self.doc_map[doc.doc_id] = doc
        
        # Index in Trie
        keywords = doc.keywords or TextPreprocessor.extract_keywords(doc.content)
        for keyword in keywords:
            self.trie.insert(keyword, doc.doc_id)
        
        if doc.title:
            self.trie.insert(doc.title, doc.doc_id)
            self.hierarchy.add_document(doc.doc_id, doc.title)
        
        # Extract entities for graph
        entities = self.entity_extractor.extract(doc.content, doc.doc_id)
        for entity_name, entity_type in entities:
            self.graph.add_entity(entity_name, entity_type, doc.doc_id)
        
        # Add relationships
        entity_names = [e[0] for e in entities]
        for i, source in enumerate(entity_names):
            for target in entity_names[i+1:]:
                self.graph.add_relationship(source, target, "co-occurs")


class TrieGraphRAG(BaseRAG):
    """
    Trie+Graph hybrid RAG system.
    
    Characteristics:
    - Latency: Good (O(m) + O(V+E))
    - Accuracy: High (hierarchy + relationships)
    - Cost: Low
    - Memory: Medium
    
    Best for:
    - Educational content
    - Hierarchical topics with relationships
    - Research papers with cross-references
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("Trie+GraphRAG", config)
        self.index = TrieGraphIndex()
        
    def initialize(self) -> None:
        """Initialize the system."""
        self.initialized = True
    
    def index_documents(self, documents: List[Document]) -> None:
        """Index documents."""
        for doc in documents:
            self.index.add_document(doc)
    
    def retrieve(self, query: str, top_k: int = 5, 
                 graph_depth: int = 2) -> RetrievalResult:
        """Retrieve using Trie + Graph traversal."""
        start_time = time.time()
        
        query_lower = query.lower()
        query_terms = query_lower.split()
        
        doc_scores: Dict[str, float] = {}
        search_methods = {'trie': 0, 'graph': 0}
        
        # Phase 1: Trie search for each term
        for term in query_terms:
            # Exact match in Trie
            exact_docs = self.index.trie.exact_search(term)
            if exact_docs:
                search_methods['trie'] += 1
                for doc_id in exact_docs:
                    doc_scores[doc_id] = doc_scores.get(doc_id, 0) + 2.0
            
            # Prefix match in Trie
            prefix_results = self.index.trie.search_prefix(term, limit=30)
            for word, doc_ids in prefix_results:
                for doc_id in doc_ids:
                    doc_scores[doc_id] = doc_scores.get(doc_id, 0) + 1.0
        
        # Phase 2: Extract entities and expand through graph
        query_entities = self.index.entity_extractor.extract(query, "query")
        
        for entity_name, _ in query_entities:
            entity_lower = entity_name.lower()
            if entity_lower in self.index.graph.entities:
                search_methods['graph'] += 1
                
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
                'method': 'trie_graph_hybrid',
                'query_terms': query_terms,
                'trie_searches': search_methods['trie'],
                'graph_searches': search_methods['graph'],
                'graph_depth': graph_depth,
                'graph_nodes': len(self.index.graph.entities),
                'trie_nodes': self._count_trie_nodes()
            }
        )
    
    def _count_trie_nodes(self) -> int:
        """Count nodes in trie."""
        def count(node):
            total = 1
            for child in node.children.values():
                total += count(child)
            return total
        return count(self.index.trie.root)
    
    def get_memory_usage(self) -> float:
        """Get memory usage in MB."""
        import sys
        
        def size_of_trie(node):
            total = sys.getsizeof(node)
            for child in node.children.values():
                total += size_of_trie(child)
            return total
        
        total = size_of_trie(self.index.trie.root)
        total += sys.getsizeof(self.index.hierarchy.topics)
        total += sys.getsizeof(self.index.graph.entities)
        total += sys.getsizeof(self.index.graph.relationships)
        
        return total / (1024 * 1024)


def demo():
    """Demonstration of Trie+GraphRAG."""
    docs = [
        Document(
            doc_id="doc1",
            content="Transformers use attention mechanisms",
            title="Transformers",
            keywords=["transformers", "attention"]
        ),
        Document(
            doc_id="doc2",
            content="Transfer learning with transformers",
            title="Transfer Learning",
            keywords=["transfer", "learning", "transformers"]
        ),
        Document(
            doc_id="doc3",
            content="Attention mechanisms explained",
            title="Attention",
            keywords=["attention", "mechanisms"]
        ),
    ]
    
    rag = TrieGraphRAG()
    rag.initialize()
    rag.add_documents(docs)
    
    queries = [
        "trans attention",
        "transfer mechanisms",
        "learning"
    ]
    
    print("=" * 60)
    print("Trie+GraphRAG Demonstration")
    print("=" * 60)
    
    for query in queries:
        result = rag.retrieve(query, top_k=3)
        print(f"\nQuery: {query}")
        print(f"Retrieval Time: {result.retrieval_time*1000:.2f}ms")
        print(f"Trie Searches: {result.metadata['trie_searches']}, "
              f"Graph Searches: {result.metadata['graph_searches']}")
        for i, (doc, score) in enumerate(zip(result.documents, result.scores), 1):
            print(f"  [{i}] {doc.title} (score: {score:.1f})")
    
    print(f"\n\nIndex Statistics:")
    print(f"  Trie Nodes: {rag._count_trie_nodes()}")
    print(f"  Graph Nodes: {len(rag.index.graph.entities)}")
    print(f"  Documents: {len(rag.index.doc_map)}")
    print(f"  Memory: {rag.get_memory_usage():.2f} MB")


if __name__ == "__main__":
    demo()
