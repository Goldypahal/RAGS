# RAG Implementation Guide

A step-by-step guide to understanding and extending the RAG framework.

## Table of Contents
1. [Architecture Decisions](#architecture-decisions)
2. [Adding New Retrieval Methods](#adding-new-retrieval-methods)
3. [Data Flow](#data-flow)
4. [Testing](#testing)
5. [Performance Optimization](#performance-optimization)
6. [Publication Guide](#publication-guide)

## Architecture Decisions

### Base Design Principles

1. **No External ML Dependencies**
   - Core framework uses only Python stdlib
   - Optional dependencies for benchmarking
   - Ensures reproducibility and simplicity

2. **Pluggable Components**
   - Each RAG inherits from `BaseRAG`
   - Standardized `retrieve()` method signature
   - Interchangeable in benchmarking framework

3. **Clear Metrics**
   - Every system returns `RetrievalResult`
   - Consistent timing and memory measurements
   - Comparable across architectures

4. **Extensible Benchmarking**
   - Add metrics without modifying RAG systems
   - Plugin architecture for evaluation methods
   - Support multiple datasets

### Class Hierarchy

```
BaseRAG (abstract)
├── VectorRAG
├── GraphRAG
├── HashMapRAG
├── TrieRAG
├── HashMapTrieRAG
├── HashMapGraphRAG
├── TrieGraphRAG
├── InvertedIndexGraphRAG
└── AdaptiveRetrievalRAG
```

## Adding New Retrieval Methods

### Step 1: Create Directory

```bash
mkdir 10-your-method-rag
```

### Step 2: Implement Core Class

```python
from common.base import Document, RetrievalResult, BaseRAG
from typing import List, Dict, Any, Optional
import time

class YourMethodRAG(BaseRAG):
    """Your method description."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("YourMethodRAG", config)
        # Initialize data structures
        
    def initialize(self) -> None:
        """Initialize the system."""
        self.initialized = True
    
    def index_documents(self, documents: List[Document]) -> None:
        """Index documents for retrieval."""
        for doc in documents:
            # Your indexing logic
            pass
    
    def retrieve(self, query: str, top_k: int = 5) -> RetrievalResult:
        """Retrieve relevant documents."""
        start_time = time.time()
        
        # Your retrieval logic
        retrieved_docs = []
        scores = []
        
        retrieval_time = time.time() - start_time
        self.update_metrics(retrieval_time)
        
        return RetrievalResult(
            query=query,
            documents=retrieved_docs,
            scores=scores,
            retrieval_time=retrieval_time,
            metadata={'method': 'your_method'}
        )
    
    def get_memory_usage(self) -> float:
        """Get memory usage in MB."""
        import sys
        # Calculate and return memory usage
        return 0.0
```

### Step 3: Add to Benchmarking

In `run_benchmark.py`:

```python
from your_module import YourMethodRAG

systems = {
    # ... existing systems
    '10. YourMethodRAG': YourMethodRAG(),
}
```

### Step 4: Test

```bash
python run_benchmark.py --mode demo
```

## Data Flow

### Indexing Phase

```
Input Documents
    ↓
Text Preprocessing
    ├─ Tokenization
    ├─ Keyword Extraction
    └─ Entity Recognition
    ↓
Index Creation
    ├─ Vector Embedding (VectorRAG)
    ├─ Graph Construction (GraphRAG)
    ├─ HashMap Building (HashMapRAG)
    ├─ Trie Construction (TrieRAG)
    └─ Inverted Index (InvertedIndexGraphRAG)
    ↓
Ready for Retrieval
```

### Retrieval Phase

```
Query Input
    ↓
Query Classification (AdaptiveRetrievalRAG)
    ├─ Exact/Prefix/Keyword/Relation/Semantic
    └─ Select Method(s)
    ↓
Retrieval Method(s)
    ├─ Index Lookup
    ├─ Score Calculation
    └─ Top-K Selection
    ↓
Result Merging (if multiple methods)
    ├─ Normalize Scores
    ├─ Weighted Combination
    └─ Re-rank by Final Score
    ↓
Output RetrievalResult
```

## Testing

### Unit Tests

Create `tests/test_rag_systems.py`:

```python
import pytest
from common.base import Document
from vector_rag import VectorRAG

def test_vector_rag_initialization():
    rag = VectorRAG()
    assert not rag.initialized
    rag.initialize()
    assert rag.initialized

def test_vector_rag_indexing():
    docs = [
        Document(doc_id="1", content="test", title="Test"),
    ]
    rag = VectorRAG()
    rag.initialize()
    rag.add_documents(docs)
    assert len(rag.documents) == 1

def test_vector_rag_retrieval():
    docs = [
        Document(doc_id="1", content="Transformers", title="Test"),
    ]
    rag = VectorRAG()
    rag.initialize()
    rag.add_documents(docs)
    
    result = rag.retrieve("Transformers", top_k=1)
    assert len(result.documents) >= 1
    assert result.retrieval_time > 0
```

### Integration Tests

```python
def test_all_systems_on_query():
    docs = [Document(doc_id="1", content="test", title="T")]
    
    systems = [VectorRAG(), GraphRAG(), HashMapRAG()]
    
    for rag in systems:
        rag.initialize()
        rag.add_documents(docs)
        result = rag.retrieve("test", top_k=1)
        
        assert len(result.documents) >= 0
        assert result.retrieval_time >= 0
        assert isinstance(result.scores, list)
```

### Performance Tests

```python
def test_retrieval_latency():
    rag = HashMapRAG()
    rag.initialize()
    
    # Index many documents
    docs = [
        Document(doc_id=f"doc{i}", content=f"content{i}", title=f"Title{i}")
        for i in range(1000)
    ]
    rag.add_documents(docs)
    
    # Measure retrieval time
    result = rag.retrieve("query", top_k=5)
    assert result.retrieval_time < 0.001  # Should be very fast
```

## Performance Optimization

### For VectorRAG
- Use sparse vectors for high-dimensional data
- Implement approximate nearest neighbor search (ANN)
- Cache embeddings

### For GraphRAG
- Use adjacency list representation
- Implement BFS with depth limits
- Memoize traversal results

### For HashMapRAG
- Keep hash load factor < 0.75
- Use string interning for entity names
- Pre-compute frequently accessed keys

### For TrieRAG
- Implement trie compression
- Use bit-manipulation for character storage
- Prune low-frequency branches

### For Adaptive Routing
- Cache query classifications
- Batch parallel method execution
- Use efficient score aggregation

## Publication Guide

### Paper Structure

```
Title: Adaptive Multi-Structure Retrieval for Large Language Models

Abstract:
- Problem: Single-method RAG limitations
- Solution: Intelligent routing + multi-method fusion
- Results: X% improvement over baselines
- Impact: New paradigm for RAG systems

Introduction:
1. Motivation (LLM hallucination, knowledge grounding)
2. Background (RAG, different retrieval methods)
3. Problem statement (single-method limitations)
4. Contributions (novel architecture, comprehensive evaluation)

Related Work:
- RAG systems (Lewis et al., Gao et al.)
- Retrieval methods (BM25, dense retrieval, graph-based)
- Query classification (information retrieval)

Methodology:
1. Nine RAG architectures
2. Benchmark framework
3. Evaluation metrics
4. Experimental setup

Results:
1. Speed comparison
2. Accuracy comparison
3. Cost analysis
4. Scaling behavior
5. Adaptive routing effectiveness

Discussion:
1. Key findings
2. Architectural tradeoffs
3. When to use each method
4. Limitations

Conclusion & Future Work:
```

### Code Publication Checklist

- ✅ All systems in separate folders
- ✅ Common base classes
- ✅ Comprehensive documentation
- ✅ Unit and integration tests
- ✅ Benchmarking suite
- ✅ Example datasets
- ✅ Reproducible results
- ✅ Requirements file
- ✅ Usage examples
- ✅ Performance metrics

### Key Results to Highlight

1. **Novel Architecture**: Adaptive Retrieval achieves comparable latency while improving accuracy
2. **Comprehensive Evaluation**: First systematic comparison of 9 distinct approaches
3. **Practical Guidance**: Decision matrix for architecture selection
4. **Open Source**: Reproducible research framework

## FAQ

### Q: Why no external ML libraries?
A: Ensures reproducibility, simplicity, and independence. Optional dependencies for convenience.

### Q: How do I add a new dataset?
A: Extend `DatasetGenerator` in `datasets/dataset_generator.py`

### Q: Can I use this for production?
A: Yes - framework is production-ready. Choose appropriate architecture for your use case.

### Q: How do I extend the benchmarking?
A: Extend `BenchmarkSuite` in `benchmarks/benchmark_suite.py` with new metrics.

### Q: What about distributed/parallel execution?
A: Architecture supports future extensions. Benchmarking suite can parallelize across systems.

## References

[See README.md for full references]

---

**For questions or contributions, see the main README.md**
