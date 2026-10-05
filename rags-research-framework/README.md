# RAG Research Framework: Comprehensive Multi-Architecture Comparison

A production-ready research framework for evaluating and comparing 9 different Retrieval-Augmented Generation (RAG) architectures.

## 🎯 Overview

This framework implements and benchmarks 9 distinct RAG architectures to answer fundamental research questions:

- Can intelligent query routing outperform single-method RAG systems?
- What is the speed/accuracy tradeoff for different retrieval methods?
- How does hybrid retrieval reduce hallucination?
- Which architectures scale best with data size?

## 🏗️ Architecture Overview

### 1. **VectorRAG** (Baseline)
```
Query → Embedding Model → Vector Database → Top-K Chunks → LLM
```
- **Characteristics**: Medium latency, high accuracy, medium cost
- **Best for**: General semantic search
- **Complexity**: O(n) where n = number of documents

### 2. **GraphRAG**
```
Documents → Entity Extraction → Knowledge Graph → Graph Traversal → LLM
```
- **Characteristics**: Medium latency, high accuracy, low cost
- **Best for**: Multi-hop reasoning, relationship discovery
- **Complexity**: O(V+E) graph traversal

### 3. **HashMapRAG**
```
Query → Entity Extraction → HashMap → Documents → LLM
```
- **Characteristics**: Excellent latency (O(1)), low accuracy, very low cost
- **Best for**: Exact keyword searches, author names, IDs
- **Complexity**: O(1) average case

### 4. **TrieRAG**
```
Query → Trie Search → Topic Hierarchy → Documents → LLM
```
- **Characteristics**: Excellent latency (O(m)), medium accuracy, low cost
- **Best for**: Autocomplete, prefix matching, hierarchical topics
- **Complexity**: O(m) where m = query length

### 5. **HashMap+TrieRAG**
```
Query → HashMap (main topic) → Trie (subtopics) → Documents
```
- **Characteristics**: Excellent latency, medium-high accuracy
- **Best for**: Multi-level hierarchical search
- **Complexity**: O(1) + O(m)

### 6. **HashMap+GraphRAG** ⭐
```
Query → HashMap (O(1) entity lookup) → Graph Traversal → Documents
```
- **Characteristics**: Excellent latency, high accuracy, low cost
- **Best for**: Fast entity discovery with semantic reasoning
- **Complexity**: O(1) + O(V+E)
- **Key Insight**: Combines speed of HashMap with reasoning of Graph

### 7. **Trie+GraphRAG**
```
Query → Trie (hierarchy) → Graph (relationships) → Documents
```
- **Characteristics**: Good latency, high accuracy, low cost
- **Best for**: Educational content, hierarchical papers
- **Complexity**: O(m) + O(V+E)

### 8. **InvertedIndex+GraphRAG**
```
Query → Inverted Index (keywords) → Graph Expansion → Documents
```
- **Characteristics**: Good latency, high accuracy, very low cost
- **Best for**: Large document collections, traditional search + reasoning
- **Complexity**: O(log n + V+E)
- **Publication Potential**: Strong candidate

### 9. **AdaptiveRetrievalRAG** ⭐⭐ (Main Contribution)
```
Query → Query Classifier
    ├─ Exact → HashMap
    ├─ Prefix → Trie
    ├─ Keyword → Inverted Index
    ├─ Relationship → Graph
    └─ Semantic → Vector DB
    ↓
    Context Merger → LLM
```
- **Characteristics**: Variable but optimal latency, very high accuracy
- **Best for**: Mixed query types, high-quality results required
- **Key Innovation**: Intelligent routing + multi-method fusion
- **Publication Potential**: Excellent - novel approach to RAG

## 📊 Benchmark Metrics

### Speed Metrics
- **Retrieval Latency**: Time to retrieve documents
- **95th Percentile**: Tail latency
- **Throughput**: Queries per second

### Quality Metrics
- **Precision**: Correct retrievals / Total retrievals
- **Recall**: Correct retrievals / Relevant documents
- **MRR (Mean Reciprocal Rank)**: Rank of first relevant result
- **NDCG (Normalized Discounted Cumulative Gain)**: Ranking quality

### Resource Metrics
- **Memory Usage**: MB per document
- **Token Cost**: Embedding and LLM tokens
- **CPU/GPU Usage**: Computational requirements

### Output Quality Metrics
- **Hallucination Rate**: False claims in LLM output
- **Faithfulness**: Adherence to retrieved context
- **Consistency**: Stable results across variations

## 🚀 Quick Start

### Installation

```bash
# Clone or navigate to framework
cd rags-research-framework

# Install dependencies
pip install -r requirements.txt
```

### Running Benchmarks

```bash
# Full comprehensive benchmark
python run_benchmark.py --mode full

# Individual system demonstrations
python run_benchmark.py --mode demo

# Generate research paper structure
python run_benchmark.py --mode paper
```

### Quick Test

```python
from vector_rag import VectorRAG
from common.base import Document

# Create documents
docs = [
    Document(
        doc_id="doc1",
        content="Transformers use attention mechanisms",
        title="Transformers"
    ),
]

# Initialize and retrieve
rag = VectorRAG()
rag.initialize()
rag.add_documents(docs)

result = rag.retrieve("What are transformers?", top_k=5)
for doc in result.documents:
    print(doc.title)
```

## 📂 Project Structure

```
rags-research-framework/
├── 1-vector-rag/              # Baseline vector-based RAG
├── 2-graph-rag/               # Knowledge graph RAG
├── 3-hashmap-rag/             # HashMap-based RAG
├── 4-trie-rag/                # Trie-based RAG
├── 5-hashmap-trie-rag/        # Hybrid: HashMap + Trie
├── 6-hashmap-graph-rag/       # Hybrid: HashMap + Graph ⭐
├── 7-trie-graph-rag/          # Hybrid: Trie + Graph
├── 8-inverted-index-graph-rag/# Hybrid: Inverted Index + Graph
├── 9-adaptive-retrieval-rag/  # Query routing + fusion ⭐⭐
├── common/                    # Base classes and utilities
├── benchmarks/                # Benchmarking framework
├── datasets/                  # Dataset generation and utilities
├── tests/                     # Unit and integration tests
├── run_benchmark.py           # Main entry point
└── requirements.txt           # Dependencies
```

## 🔬 Research Findings (Preliminary)

### Speed Rankings
1. **HashMapRAG** - O(1) perfect for exact matches
2. **InvertedIndex+GraphRAG** - Fast search engine + graph
3. **TrieRAG** - Good prefix matching
4. **HashMap+GraphRAG** - Combines speed and reasoning
5. **AdaptiveRetrievalRAG** - Smart routing overhead

### Accuracy Rankings
1. **AdaptiveRetrievalRAG** - Multiple confirmations
2. **VectorRAG + GraphRAG** - Semantic understanding
3. **InvertedIndex+GraphRAG** - Search + reasoning
4. **HashMap+GraphRAG** - Fast with context
5. **Trie+GraphRAG** - Hierarchical + relational

### Cost-Effectiveness Rankings
1. **HashMapRAG** - Minimal resources
2. **InvertedIndex+GraphRAG** - No embeddings needed
3. **TrieRAG** - Compact data structure
4. **HashMap+GraphRAG** - Low overhead hybrid
5. **AdaptiveRetrievalRAG** - Multiple indices

## 🎓 Key Research Questions

1. **Routing Effectiveness**: Does query classification improve retrieval over uniform methods?
2. **Fusion Strategies**: How should scores from different methods be combined?
3. **Scaling**: Which architectures maintain performance as datasets grow?
4. **Latency Bounds**: Can we guarantee retrieval latency with adaptive routing?
5. **Semantic Understanding**: Does graph reasoning reduce hallucination vs vector-only?

## 📈 Expected Results

### Performance Matrix

| Architecture | Speed | Accuracy | Memory | Cost | Scalability |
|---|---|---|---|---|---|
| VectorRAG | 🟡 | 🟢 | 🟡 | 🟡 | 🟡 |
| GraphRAG | 🟡 | 🟢 | 🟡 | 🟢 | 🟡 |
| HashMapRAG | 🟢 | 🟡 | 🟢 | 🟢 | 🟢 |
| TrieRAG | 🟢 | 🟡 | 🟢 | 🟢 | 🟢 |
| HashMap+Trie | 🟢 | 🟡 | 🟡 | 🟢 | 🟢 |
| HashMap+Graph | 🟢 | 🟢 | 🟡 | 🟢 | 🟡 |
| Trie+Graph | 🟡 | 🟢 | 🟡 | 🟢 | 🟡 |
| Inverted+Graph | 🟡 | 🟢 | 🟡 | 🟢 | 🟡 |
| **Adaptive** | 🟡 | 🟢 | 🟡 | 🟡 | 🟡 |

## 🔧 Implementation Notes

### Production-Ready Features
- ✅ No external ML libraries required (except numpy/psutil for benchmarking)
- ✅ Reproducible results with deterministic seeds
- ✅ Comprehensive logging and metrics
- ✅ Clean separation of concerns
- ✅ Extensible architecture for new methods
- ✅ Full type hints for IDE support
- ✅ Unit tests and integration tests

### Dependencies
- Python 3.8+
- numpy (optional, for benchmarking)
- psutil (optional, for memory tracking)

## 📖 Documentation

### For Researchers
- See `RESEARCH_PAPER_STRUCTURE.md` for publication-ready outline
- Check `benchmarks/` for evaluation methodology
- Review `datasets/` for benchmark construction

### For Practitioners
- Start with individual system demos in `run_benchmark.py`
- Choose appropriate architecture based on use case
- Use benchmarking suite to validate performance

## 🎯 Publication Opportunities

### Primary Paper
**"Adaptive Multi-Structure Retrieval for Large Language Models"**
- Novel query-aware routing system
- Comprehensive 9-system comparison
- Evidence-based architecture selection guide

### Secondary Papers
1. **Graph-Enhanced Entity Retrieval** (HashMap+GraphRAG)
2. **Cost-Effective RAG Alternatives** (Inverted Index comparison)
3. **Hierarchical Search Semantics** (Trie+Graph fusion)

## 🔄 Reproducibility

All results are reproducible with:
```bash
python run_benchmark.py --mode full --output results_v1.json
```

Results include:
- Complete timing data
- Memory profiles
- Accuracy metrics
- System configurations

## 🤝 Contributing

To add a new RAG architecture:

1. Create new directory: `N-name-rag/`
2. Inherit from `BaseRAG` in `common/base.py`
3. Implement `index_documents()` and `retrieve()`
4. Add to `run_benchmark.py`
5. Document in this README

## 📝 License

Research framework - Use for academic and commercial purposes.

## 🔗 References

- Vaswani et al. (2017): "Attention is All You Need"
- Devlin et al. (2018): "BERT: Pre-training of Deep Bidirectional Transformers"
- Lewis et al. (2020): "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"
- Gao et al. (2023): "Retrieval-Augmented Generation for Large Language Models: A Survey"

---

**Framework Version**: 1.0  
**Last Updated**: 2024  
**Status**: Production-Ready for Research
