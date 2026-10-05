"""
GraphRAG: Knowledge Graph-based Retrieval

Architecture:
    Documents → Entity Extraction → Knowledge Graph → Graph Traversal → Context Builder → LLM

Uses relationships between entities for reasoning.
"""

import time
import json
from typing import List, Dict, Set, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.base import Document, RetrievalResult, BaseRAG, TextPreprocessor


@dataclass
class Entity:
    """Represents an entity in the knowledge graph."""
    name: str
    entity_type: str
    doc_ids: Set[str] = field(default_factory=set)
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'entity_type': self.entity_type,
            'doc_ids': list(self.doc_ids),
            'description': self.description
        }


@dataclass
class Relationship:
    """Represents a relationship between entities."""
    source: str
    target: str
    relation_type: str
    weight: float = 1.0
    evidence: List[str] = field(default_factory=list)


class SimpleEntityExtractor:
    """Simple entity extraction based on patterns."""
    
    ENTITY_PATTERNS = {
        'model': ['transformer', 'bert', 'gpt', 'lstm', 'rnn', 'cnn', 'model'],
        'technology': ['attention', 'embedding', 'layer', 'architecture'],
        'person': ['hinton', 'lecun', 'bengio', 'sutskever'],
        'concept': ['learning', 'training', 'loss', 'optimization']
    }
    
    @classmethod
    def extract(cls, text: str, doc_id: str) -> List[Tuple[str, str]]:
        """Extract entities from text."""
        entities = []
        text_lower = text.lower()
        
        for entity_type, patterns in cls.ENTITY_PATTERNS.items():
            for pattern in patterns:
                if pattern in text_lower:
                    # Find context around entity
                    idx = text_lower.find(pattern)
                    entities.append((pattern, entity_type))
        
        return list(set(entities))


class KnowledgeGraph:
    """Simple knowledge graph implementation."""
    
    def __init__(self):
        self.entities: Dict[str, Entity] = {}
        self.relationships: List[Relationship] = []
        self.adjacency: Dict[str, Set[str]] = {}
        
    def add_entity(self, name: str, entity_type: str, doc_id: str) -> None:
        """Add entity to graph."""
        name_lower = name.lower()
        
        if name_lower not in self.entities:
            self.entities[name_lower] = Entity(name=name_lower, entity_type=entity_type)
            self.adjacency[name_lower] = set()
        
        self.entities[name_lower].doc_ids.add(doc_id)
    
    def add_relationship(self, source: str, target: str, relation_type: str, 
                         weight: float = 1.0, evidence: List[str] = None) -> None:
        """Add relationship between entities."""
        source_lower = source.lower()
        target_lower = target.lower()
        
        # Create entities if needed
        if source_lower not in self.entities:
            self.entities[source_lower] = Entity(name=source_lower, entity_type="unknown")
            self.adjacency[source_lower] = set()
        
        if target_lower not in self.entities:
            self.entities[target_lower] = Entity(name=target_lower, entity_type="unknown")
            self.adjacency[target_lower] = set()
        
        # Add relationship
        rel = Relationship(source_lower, target_lower, relation_type, weight, evidence or [])
        self.relationships.append(rel)
        
        # Update adjacency
        self.adjacency[source_lower].add(target_lower)
    
    def get_neighbors(self, entity_name: str, depth: int = 1) -> Set[str]:
        """Get all neighbors within depth."""
        entity_lower = entity_name.lower()
        visited = {entity_lower}
        to_visit = {entity_lower}
        
        for _ in range(depth):
            next_level = set()
            for node in to_visit:
                neighbors = self.adjacency.get(node, set())
                next_level.update(neighbors - visited)
            visited.update(next_level)
            to_visit = next_level
        
        return visited - {entity_lower}
    
    def get_path(self, start: str, end: str, max_depth: int = 3) -> Optional[List[str]]:
        """BFS to find shortest path between entities."""
        start_lower = start.lower()
        end_lower = end.lower()
        
        if start_lower not in self.entities or end_lower not in self.entities:
            return None
        
        queue = [(start_lower, [start_lower])]
        visited = {start_lower}
        
        while queue:
            node, path = queue.pop(0)
            
            if node == end_lower:
                return path
            
            if len(path) < max_depth:
                for neighbor in self.adjacency.get(node, set()):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((neighbor, path + [neighbor]))
        
        return None
    
    def get_subgraph(self, entities: Set[str], depth: int = 1) -> Tuple[Set[str], List[Relationship]]:
        """Get subgraph around given entities."""
        subgraph_entities = set()
        subgraph_rels = []
        
        # Find all neighbors
        for entity in entities:
            subgraph_entities.add(entity.lower())
            neighbors = self.get_neighbors(entity, depth)
            subgraph_entities.update(neighbors)
        
        # Find relationships within subgraph
        for rel in self.relationships:
            if rel.source in subgraph_entities and rel.target in subgraph_entities:
                subgraph_rels.append(rel)
        
        return subgraph_entities, subgraph_rels


class GraphRAG(BaseRAG):
    """
    Knowledge Graph RAG system.
    
    Metrics:
    - Latency: Medium (graph traversal)
    - Accuracy: High (semantic relationships)
    - Cost: Low (no embedding needed)
    - Memory: Medium (graph structure)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("GraphRAG", config)
        self.graph = KnowledgeGraph()
        self.doc_map: Dict[str, Document] = {}
        self.entity_extractor = SimpleEntityExtractor()
        
    def initialize(self) -> None:
        """Initialize the system."""
        self.initialized = True
    
    def index_documents(self, documents: List[Document]) -> None:
        """Index documents and build knowledge graph."""
        for doc in documents:
            self.doc_map[doc.doc_id] = doc
            
            # Extract entities
            entities = self.entity_extractor.extract(doc.content, doc.doc_id)
            for entity_name, entity_type in entities:
                self.graph.add_entity(entity_name, entity_type, doc.doc_id)
            
            # Create relationships between entities in same document
            entity_names = [e[0] for e in entities]
            for i, source in enumerate(entity_names):
                for target in entity_names[i+1:]:
                    self.graph.add_relationship(
                        source, target, "co-occurs", weight=1.0,
                        evidence=[doc.doc_id]
                    )
    
    def retrieve(self, query: str, top_k: int = 5) -> RetrievalResult:
        """Retrieve documents using graph traversal."""
        start_time = time.time()
        
        # Extract entities from query
        query_entities = self.entity_extractor.extract(query, "query")
        query_entity_names = [e[0] for e in query_entities]
        
        # Find related documents
        doc_scores: Dict[str, float] = {}
        
        for entity_name, _ in query_entities:
            entity_lower = entity_name.lower()
            
            if entity_lower in self.graph.entities:
                entity = self.graph.entities[entity_lower]
                
                # Direct match
                for doc_id in entity.doc_ids:
                    doc_scores[doc_id] = doc_scores.get(doc_id, 0) + 2.0
                
                # Neighbors
                neighbors = self.graph.get_neighbors(entity_lower, depth=2)
                for neighbor in neighbors:
                    if neighbor in self.graph.entities:
                        for doc_id in self.graph.entities[neighbor].doc_ids:
                            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + 1.0
        
        # Sort by score
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Build result
        retrieved_docs = []
        scores = []
        
        for doc_id, score in sorted_docs[:top_k]:
            if doc_id in self.doc_map:
                retrieved_docs.append(self.doc_map[doc_id])
                scores.append(float(score))
        
        retrieval_time = time.time() - start_time
        self.update_metrics(retrieval_time)
        
        return RetrievalResult(
            query=query,
            documents=retrieved_docs,
            scores=scores,
            retrieval_time=retrieval_time,
            metadata={
                'method': 'graph_traversal',
                'query_entities': query_entity_names,
                'graph_nodes': len(self.graph.entities),
                'graph_edges': len(self.graph.relationships)
            }
        )
    
    def get_memory_usage(self) -> float:
        """Get memory usage in MB."""
        import sys
        
        total = sys.getsizeof(self.graph.entities)
        total += sys.getsizeof(self.graph.relationships)
        total += sys.getsizeof(self.graph.adjacency)
        
        for entity in self.graph.entities.values():
            total += sys.getsizeof(entity.name)
        
        for rel in self.graph.relationships:
            total += sys.getsizeof(rel.source)
            total += sys.getsizeof(rel.target)
        
        return total / (1024 * 1024)


def demo():
    """Demonstration of GraphRAG."""
    docs = [
        Document(
            doc_id="doc1",
            content="Transformers are neural network architectures using attention mechanisms.",
            title="Transformers"
        ),
        Document(
            doc_id="doc2",
            content="BERT is built on transformer architecture for language understanding.",
            title="BERT"
        ),
        Document(
            doc_id="doc3",
            content="Attention mechanism is the core of transformer model.",
            title="Attention"
        ),
    ]
    
    rag = GraphRAG()
    rag.initialize()
    rag.add_documents(docs)
    
    queries = [
        "What is BERT?",
        "How do transformers work?",
        "Explain attention"
    ]
    
    print("=" * 60)
    print("GraphRAG Demonstration")
    print("=" * 60)
    
    for query in queries:
        result = rag.retrieve(query, top_k=3)
        print(f"\nQuery: {query}")
        print(f"Retrieval Time: {result.retrieval_time:.4f}s")
        for i, doc in enumerate(result.documents, 1):
            print(f"  [{i}] {doc.title}")
    
    print(f"\n\nGraph Statistics:")
    print(f"  Nodes: {len(rag.graph.entities)}")
    print(f"  Edges: {len(rag.graph.relationships)}")
    print(f"  Memory: {rag.get_memory_usage():.2f} MB")


if __name__ == "__main__":
    demo()
