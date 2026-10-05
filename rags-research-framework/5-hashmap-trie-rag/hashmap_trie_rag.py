"""
HashMap+TrieRAG: Combined HashMap and Trie

Architecture:
    Query → HashMap (main topic) → Trie (subtopics) → Documents

Two-level lookup: fast main topic selection, then detailed search.
"""

import time
import json
from typing import List, Dict, Set, Any, Optional, Tuple
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "3-hashmap-rag"))
sys.path.insert(0, str(Path(__file__).parent.parent / "4-trie-rag"))

from common.base import Document, RetrievalResult, BaseRAG, TextPreprocessor
from hashmap_rag import HashMapIndex
from trie_rag import Trie


class HashMapTrieIndex:
    """Two-level index: HashMap for main topics, Trie for subtopics."""
    
    def __init__(self):
        # HashMap: main topic -> Trie
        self.main_topics: Dict[str, Trie] = {}
        # Direct document storage
        self.doc_map: Dict[str, Document] = {}
        # Track which documents belong to which main topic
        self.topic_documents: Dict[str, Set[str]] = {}
        
    def add_document(self, doc: Document, main_topic: Optional[str] = None) -> None:
        """Add document with optional main topic."""
        self.doc_map[doc.doc_id] = doc
        
        # Determine main topic
        if main_topic:
            topic = main_topic.lower()
        else:
            # Use first keyword as topic, or title
            topic = (doc.keywords[0].lower() if doc.keywords else 
                    doc.title.lower() if doc.title else "general")
        
        # Create Trie for topic if not exists
        if topic not in self.main_topics:
            self.main_topics[topic] = Trie()
            self.topic_documents[topic] = set()
        
        # Add to topic's Trie
        keywords = doc.keywords or TextPreprocessor.extract_keywords(doc.content)
        for keyword in keywords:
            self.main_topics[topic].insert(keyword, doc.doc_id)
        
        if doc.title:
            self.main_topics[topic].insert(doc.title, doc.doc_id)
        
        self.topic_documents[topic].add(doc.doc_id)
    
    def lookup_main_topic(self, topic: str) -> Optional[Trie]:
        """O(1) lookup for main topic."""
        return self.main_topics.get(topic.lower())
    
    def search_in_topic(self, topic: str, query: str) -> Set[str]:
        """Search within a specific topic."""
        trie = self.lookup_main_topic(topic)
        if not trie:
            return set()
        
        doc_ids = set()
        for term in query.lower().split():
            # Exact match
            doc_ids.update(trie.exact_search(term))
            # Prefix match
            prefix_results = trie.search_prefix(term)
            for _, ids in prefix_results:
                doc_ids.update(ids)
        
        return doc_ids


class HashMapTrieRAG(BaseRAG):
    """
    Two-level HashMap+Trie RAG system.
    
    Characteristics:
    - Latency: Excellent (O(1) + O(m))
    - Accuracy: Medium (hierarchy + prefix matching)
    - Cost: Very Low
    - Memory: Low-Medium
    
    Best for:
    - Hierarchical topics with subtopics
    - Multi-level search
    - Fast main category selection
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("HashMap+TrieRAG", config)
        self.index = HashMapTrieIndex()
        
    def initialize(self) -> None:
        """Initialize the system."""
        self.initialized = True
    
    def index_documents(self, documents: List[Document]) -> None:
        """Index documents with two-level structure."""
        for doc in documents:
            # Categorize document
            main_topic = self._extract_main_topic(doc)
            self.index.add_document(doc, main_topic)
    
    def _extract_main_topic(self, doc: Document) -> str:
        """Extract main topic from document."""
        # Look for common main topics
        content_lower = doc.content.lower()
        title_lower = doc.title.lower() if doc.title else ""
        
        main_topics = ['ai', 'machine learning', 'deep learning', 'nlp', 
                      'physics', 'chemistry', 'biology', 'astronomy']
        
        for topic in main_topics:
            if topic in content_lower or topic in title_lower:
                return topic
        
        # Default to first keyword
        return (doc.keywords[0].lower() if doc.keywords else "general")
    
    def retrieve(self, query: str, top_k: int = 5) -> RetrievalResult:
        """Retrieve using two-level lookup."""
        start_time = time.time()
        
        query_lower = query.lower()
        query_terms = query_lower.split()
        
        doc_scores: Dict[str, float] = {}
        retrieved_topics = []
        
        # First level: HashMap - find relevant main topics
        for term in query_terms:
            if term in self.index.main_topics:
                retrieved_topics.append(term)
        
        # If no exact topic match, search all topics
        if not retrieved_topics:
            retrieved_topics = list(self.index.main_topics.keys())
        
        # Second level: Trie - search within selected topics
        for topic in retrieved_topics:
            trie = self.index.main_topics[topic]
            
            for term in query_terms:
                # Exact match in Trie
                exact_docs = trie.exact_search(term)
                for doc_id in exact_docs:
                    doc_scores[doc_id] = doc_scores.get(doc_id, 0) + 2.0
                
                # Prefix match in Trie
                prefix_results = trie.search_prefix(term, limit=20)
                for _, doc_ids in prefix_results:
                    for doc_id in doc_ids:
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
                'method': 'two_level_hashmap_trie',
                'query_terms': query_terms,
                'main_topics_searched': len(retrieved_topics),
                'levels': 2
            }
        )
    
    def get_memory_usage(self) -> float:
        """Get memory usage in MB."""
        import sys
        
        total = sys.getsizeof(self.index.main_topics)
        total += sys.getsizeof(self.index.doc_map)
        total += sys.getsizeof(self.index.topic_documents)
        
        for topic, trie in self.index.main_topics.items():
            total += sys.getsizeof(topic)
            
            def size_of_trie(node):
                t = sys.getsizeof(node)
                for child in node.children.values():
                    t += size_of_trie(child)
                return t
            
            total += size_of_trie(trie.root)
        
        return total / (1024 * 1024)


def demo():
    """Demonstration of HashMap+TrieRAG."""
    docs = [
        Document(
            doc_id="doc1",
            content="Deep learning transformers for NLP",
            title="Transformers in NLP",
            keywords=["transformers", "nlp", "learning"]
        ),
        Document(
            doc_id="doc2",
            content="Attention mechanisms in machine learning",
            title="Attention Mechanisms",
            keywords=["attention", "learning", "neural"]
        ),
        Document(
            doc_id="doc3",
            content="Transfer learning with transformers",
            title="Transfer Learning",
            keywords=["transfer", "learning", "transformers"]
        ),
    ]
    
    rag = HashMapTrieRAG()
    rag.initialize()
    rag.add_documents(docs)
    
    queries = [
        "transformers learning",
        "attention mechanisms",
        "transfer"
    ]
    
    print("=" * 60)
    print("HashMap+TrieRAG Demonstration")
    print("=" * 60)
    
    for query in queries:
        result = rag.retrieve(query, top_k=3)
        print(f"\nQuery: {query}")
        print(f"Retrieval Time: {result.retrieval_time*1000:.2f}ms")
        for i, (doc, score) in enumerate(zip(result.documents, result.scores), 1):
            print(f"  [{i}] {doc.title} (score: {score:.1f})")
    
    print(f"\n\nIndex Statistics:")
    print(f"  Main Topics: {len(rag.index.main_topics)}")
    print(f"  Documents: {len(rag.index.doc_map)}")
    print(f"  Memory: {rag.get_memory_usage():.2f} MB")


if __name__ == "__main__":
    demo()
