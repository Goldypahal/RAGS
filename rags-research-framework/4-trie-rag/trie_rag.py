"""
TrieRAG: Trie-based Hierarchical Retrieval

Architecture:
    Query → Trie Search → Topic Hierarchy → Documents

Great for prefix matching and hierarchical organization.
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
class TrieNode:
    """Node in the Trie."""
    char: str = ""
    is_end: bool = False
    doc_ids: Set[str] = field(default_factory=set)
    children: Dict[str, 'TrieNode'] = field(default_factory=dict)
    prefix: str = ""


class Trie:
    """Trie data structure for hierarchical search."""
    
    def __init__(self):
        self.root = TrieNode()
        self.all_terms = set()
        
    def insert(self, word: str, doc_id: str) -> None:
        """Insert word and associate with document."""
        word_lower = word.lower()
        self.all_terms.add(word_lower)
        
        node = self.root
        
        for i, char in enumerate(word_lower):
            if char not in node.children:
                new_node = TrieNode(char=char)
                new_node.prefix = word_lower[:i+1]
                node.children[char] = new_node
            
            node = node.children[char]
            node.doc_ids.add(doc_id)
        
        node.is_end = True
    
    def search_prefix(self, prefix: str, limit: int = 100) -> List[Tuple[str, Set[str]]]:
        """Search for all words with given prefix."""
        prefix_lower = prefix.lower()
        node = self.root
        
        # Navigate to prefix node
        for char in prefix_lower:
            if char not in node.children:
                return []
            node = node.children[char]
        
        # Collect all words from this node
        results = []
        self._collect_words(node, "", results, limit)
        
        return [(prefix_lower + word, doc_ids) for word, doc_ids in results]
    
    def _collect_words(self, node: TrieNode, current: str, 
                       results: List[Tuple[str, Set[str]]], limit: int) -> None:
        """Recursively collect words."""
        if len(results) >= limit:
            return
        
        if node.is_end:
            results.append((current, node.doc_ids.copy()))
        
        for char, child in sorted(node.children.items()):
            if len(results) < limit:
                self._collect_words(child, current + char, results, limit)
    
    def exact_search(self, word: str) -> Set[str]:
        """Exact word search."""
        word_lower = word.lower()
        node = self.root
        
        for char in word_lower:
            if char not in node.children:
                return set()
            node = node.children[char]
        
        if node.is_end:
            return node.doc_ids.copy()
        
        return set()


class TopicHierarchy:
    """Hierarchical organization of topics."""
    
    def __init__(self):
        self.topics: Dict[str, Dict[str, Any]] = {}
        self.hierarchy: Dict[str, List[str]] = {}
        
    def add_topic(self, topic: str, parent: Optional[str] = None) -> None:
        """Add topic to hierarchy."""
        topic_lower = topic.lower()
        self.topics[topic_lower] = {
            'parent': parent.lower() if parent else None,
            'docs': set()
        }
        
        if parent:
            parent_lower = parent.lower()
            if parent_lower not in self.hierarchy:
                self.hierarchy[parent_lower] = []
            if topic_lower not in self.hierarchy[parent_lower]:
                self.hierarchy[parent_lower].append(topic_lower)
    
    def add_document(self, doc_id: str, topic: str) -> None:
        """Add document to topic."""
        topic_lower = topic.lower()
        if topic_lower not in self.topics:
            self.add_topic(topic_lower)
        self.topics[topic_lower]['docs'].add(doc_id)
    
    def get_subtopics(self, topic: str) -> List[str]:
        """Get all subtopics."""
        return self.hierarchy.get(topic.lower(), [])
    
    def get_documents(self, topic: str, include_subtopics: bool = True) -> Set[str]:
        """Get documents in topic."""
        topic_lower = topic.lower()
        docs = self.topics.get(topic_lower, {}).get('docs', set()).copy()
        
        if include_subtopics:
            for subtopic in self.get_subtopics(topic_lower):
                docs.update(self.get_documents(subtopic, include_subtopics=True))
        
        return docs


class TrieRAG(BaseRAG):
    """
    Trie-based RAG system with hierarchical organization.
    
    Characteristics:
    - Latency: Excellent (O(m) where m = query length)
    - Accuracy: Medium (hierarchical matching)
    - Cost: Very Low
    - Memory: Low
    
    Best for:
    - Prefix/autocomplete queries
    - Topic hierarchies
    - Educational content
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("TrieRAG", config)
        self.trie = Trie()
        self.hierarchy = TopicHierarchy()
        self.doc_map: Dict[str, Document] = {}
        
    def initialize(self) -> None:
        """Initialize the system."""
        self.initialized = True
    
    def index_documents(self, documents: List[Document]) -> None:
        """Index documents using Trie."""
        for doc in documents:
            self.doc_map[doc.doc_id] = doc
            
            # Index keywords
            keywords = doc.keywords or TextPreprocessor.extract_keywords(doc.content)
            for keyword in keywords:
                self.trie.insert(keyword, doc.doc_id)
            
            # Index title
            if doc.title:
                self.trie.insert(doc.title, doc.doc_id)
                self.hierarchy.add_document(doc.doc_id, doc.title)
    
    def retrieve(self, query: str, top_k: int = 5) -> RetrievalResult:
        """Retrieve documents using Trie."""
        start_time = time.time()
        
        # Extract query terms
        query_lower = query.lower()
        query_terms = query_lower.split()
        
        # Search for each term
        doc_scores: Dict[str, float] = {}
        
        for term in query_terms:
            # Exact match
            exact_docs = self.trie.exact_search(term)
            for doc_id in exact_docs:
                doc_scores[doc_id] = doc_scores.get(doc_id, 0) + 2.0
            
            # Prefix match
            prefix_results = self.trie.search_prefix(term, limit=50)
            for word, doc_ids in prefix_results:
                for doc_id in doc_ids:
                    # Weight prefix matches lower
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
                'method': 'trie_hierarchical',
                'query_terms': query_terms,
                'trie_nodes': self._count_trie_nodes(),
                'lookup_complexity': 'O(m)'
            }
        )
    
    def _count_trie_nodes(self) -> int:
        """Count nodes in trie."""
        def count(node):
            total = 1
            for child in node.children.values():
                total += count(child)
            return total
        
        return count(self.trie.root)
    
    def get_memory_usage(self) -> float:
        """Get memory usage in MB."""
        import sys
        
        def size_of_trie(node):
            total = sys.getsizeof(node)
            for child in node.children.values():
                total += size_of_trie(child)
            return total
        
        total = size_of_trie(self.trie.root)
        total += sys.getsizeof(self.hierarchy.topics)
        total += sys.getsizeof(self.hierarchy.hierarchy)
        
        return total / (1024 * 1024)


def demo():
    """Demonstration of TrieRAG."""
    docs = [
        Document(
            doc_id="doc1",
            content="Transformers use attention mechanisms",
            title="Transformers",
            keywords=["transformers", "attention", "neural"]
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
            keywords=["attention", "mechanisms", "explained"]
        ),
    ]
    
    rag = TrieRAG()
    rag.initialize()
    rag.add_documents(docs)
    
    queries = [
        "trans",
        "attention",
        "transfer learning"
    ]
    
    print("=" * 60)
    print("TrieRAG Demonstration")
    print("=" * 60)
    
    for query in queries:
        result = rag.retrieve(query, top_k=3)
        print(f"\nQuery: {query}")
        print(f"Retrieval Time: {result.retrieval_time*1000:.2f}ms")
        for i, (doc, score) in enumerate(zip(result.documents, result.scores), 1):
            print(f"  [{i}] {doc.title} (score: {score:.1f})")
    
    print(f"\n\nTrie Statistics:")
    print(f"  Nodes: {rag._count_trie_nodes()}")
    print(f"  Documents: {len(rag.doc_map)}")
    print(f"  Memory: {rag.get_memory_usage():.2f} MB")


if __name__ == "__main__":
    demo()
