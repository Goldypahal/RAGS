"""
InvertedIndex+GraphRAG: Search Engine Speed + Graph Reasoning

Architecture:
    Query → Inverted Index (keyword search) → Graph Expansion → Documents

Like search engines but with semantic reasoning through graphs.
"""

import math
import time
import json
from typing import List, Dict, Set, Any, Optional, Tuple
from collections import Counter, defaultdict
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "2-graph-rag"))

from common.base import Document, RetrievalResult, BaseRAG, TextPreprocessor, rank_scores
from graph_rag import KnowledgeGraph, SimpleEntityExtractor


class InvertedIndex:
    """Inverted index with Okapi BM25 scoring."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        # term -> {doc_id: term frequency}
        self.postings: Dict[str, Dict[str, int]] = defaultdict(dict)
        # doc_id -> document length in tokens
        self.doc_len: Dict[str, int] = {}
        self.total_len = 0
        self.vocab_size = 0

    def add_document(self, doc: Document) -> None:
        """Add document to inverted index."""
        tokens = TextPreprocessor.tokenize(doc.content)

        for term, tf in Counter(tokens).items():
            self.postings[term][doc.doc_id] = tf

        self.doc_len[doc.doc_id] = len(tokens)
        self.total_len += len(tokens)
        self.vocab_size = len(self.postings)

    def idf(self, term: str) -> float:
        """BM25 IDF (Lucene variant, always non-negative)."""
        n_docs = len(self.doc_len)
        df = len(self.postings.get(term, ()))
        return math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))

    def search(self, query: str, limit: int = 1000) -> List[Tuple[str, float]]:
        """BM25-ranked OR search over the query's content terms."""
        if not self.doc_len:
            return []

        avgdl = self.total_len / len(self.doc_len)
        doc_scores: Dict[str, float] = defaultdict(float)

        for term in dict.fromkeys(TextPreprocessor.content_terms(query)):
            postings = self.postings.get(term)
            if not postings:
                continue
            idf = self.idf(term)
            for doc_id, tf in postings.items():
                norm = self.k1 * (1.0 - self.b + self.b * self.doc_len[doc_id] / avgdl)
                doc_scores[doc_id] += idf * tf * (self.k1 + 1.0) / (tf + norm)

        return rank_scores(doc_scores)[:limit]

    def search_and_phrase(self, query: str) -> List[Tuple[str, float]]:
        """BM25-ranked search restricted to documents containing ALL content terms."""
        query_terms = list(dict.fromkeys(TextPreprocessor.content_terms(query)))

        if not query_terms or any(t not in self.postings for t in query_terms):
            return []

        doc_ids = set(self.postings[query_terms[0]])
        for term in query_terms[1:]:
            doc_ids &= self.postings[term].keys()

        return [(d, s) for d, s in self.search(query) if d in doc_ids]


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
        # Graph evidence is scaled relative to the (max-normalized) BM25 score.
        # Fixed a priori, not tuned on benchmark queries.
        self.graph_weight = float(self.config.get('graph_weight', 0.2))

    def initialize(self) -> None:
        """Initialize the system."""
        self.initialized = True

    def index_documents(self, documents: List[Document]) -> None:
        """Index documents."""
        for doc in documents:
            self.index.add_document(doc)

    def add_citation_links(self, links) -> None:
        """Add citation edges between documents."""
        for citing, cited in links:
            self.index.graph.add_doc_link(citing, cited)

    def retrieve(self, query: str, top_k: int = 5,
                 graph_depth: int = 2, use_and_semantics: bool = False) -> RetrievalResult:
        """Retrieve using BM25 + graph expansion."""
        start_time = time.perf_counter()

        search_stats = {'inverted_index': 0, 'graph_expansion': 0}

        # Phase 1: BM25 search, normalized to [0, 1]
        if use_and_semantics:
            initial_results = self.index.inverted_index.search_and_phrase(query)
        else:
            initial_results = self.index.inverted_index.search(query)

        search_stats['inverted_index'] = len(initial_results)

        max_text = max((s for _, s in initial_results), default=0.0)
        doc_scores: Dict[str, float] = (
            {doc_id: s / max_text for doc_id, s in initial_results} if max_text > 0 else {}
        )

        # Phase 2: Extract entities and expand through graph
        graph_scores: Dict[str, float] = {}
        query_entities = self.index.entity_extractor.extract(query, "query")

        for entity_name, _ in query_entities:
            entity_lower = entity_name.lower()
            if entity_lower in self.index.graph.entities:
                search_stats['graph_expansion'] += 1

                entity = self.index.graph.entities[entity_lower]

                # Direct entity docs
                for doc_id in entity.doc_ids:
                    graph_scores[doc_id] = graph_scores.get(doc_id, 0) + 2.0

                # Related entities through graph
                neighbors = self.index.graph.get_neighbors(entity_lower, depth=graph_depth)
                for neighbor in neighbors:
                    if neighbor in self.index.graph.entities:
                        for doc_id in self.index.graph.entities[neighbor].doc_ids:
                            graph_scores[doc_id] = graph_scores.get(doc_id, 0) + 1.0

        max_graph = max(graph_scores.values(), default=0.0)
        if max_graph > 0:
            for doc_id, s in graph_scores.items():
                doc_scores[doc_id] = doc_scores.get(doc_id, 0.0) + self.graph_weight * s / max_graph

        # Phase 3: citation hop from the strongest seeds
        doc_scores = self.index.graph.expand_by_doc_links(doc_scores)

        sorted_docs = rank_scores(doc_scores)
        
        # Build result
        retrieved_docs = []
        scores = []
        
        for doc_id, score in sorted_docs[:top_k]:
            if doc_id in self.index.doc_map:
                retrieved_docs.append(self.index.doc_map[doc_id])
                scores.append(float(score))
        
        retrieval_time = time.perf_counter() - start_time
        self.update_metrics(retrieval_time)

        return RetrievalResult(
            query=query,
            documents=retrieved_docs,
            scores=scores,
            retrieval_time=retrieval_time,
            metadata={
                'method': 'bm25_graph_hybrid',
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
        for term, postings in self.index.inverted_index.postings.items():
            total += sys.getsizeof(term) + sys.getsizeof(postings)
        
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
