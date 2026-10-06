# 🔬 Adaptive Structure-Aware Retrieval: RAG Research & Benchmarking Framework

An experimental research framework and benchmarking testbed for evaluating and comparing **9 different retrieval architectures** for Retrieval-Augmented Generation (RAG) systems.

**Status**: 🧪 *Research Prototype & Experimental Benchmarking Framework undergoing empirical validation*

## 🎯 Research Questions & Core Hypothesis

This framework investigates the hypothesis that **no single retrieval index is optimal across all query intents**:
- **Semantic Queries** favor dense vector spaces ($\mathcal{O}(n \cdot d)$).
- **Exact & Identifier Lookups** favor constant-time HashMaps (expected $\mathcal{O}(1)$).
- **Hierarchical & Prefix Queries** favor Trie representations ($\mathcal{O}(m + z)$).
- **Relational & Citation Reasoning** favor Subgraph traversals ($\mathcal{O}(k \cdot \bar{d}^h)$).
- **Adaptive Query Routing** can achieve non-dominated Pareto tradeoffs across accuracy, query latency, and index footprint.

## 🏗️ Architecture Overview

### 1. **VectorRAG** (Baseline)
```
Query → Embedding Model → Dense Vector Space → Top-K Cosine Similarity → Context
```
- **Characteristics**: Dense semantic representations, higher latency due to model inference
- **Best for**: General semantic similarity and paraphrase matching
- **Complexity**: $\mathcal{O}(n \cdot d)$ where $n$ is corpus size and $d$ is embedding dimension (linear scan without ANN index)

### 2. **GraphRAG**
```
Corpus → Entity/Relation Graph → Subgraph Traversal → Context
```
- **Characteristics**: Structural reasoning, multi-hop connection paths
- **Best for**: Citation tracking, co-authorship networks, relational hops
- **Complexity**: $\mathcal{O}(k \cdot \bar{d}^h)$ bounded $h$-hop traversal from $k$ seeds with average node degree $\bar{d}$

### 3. **HashMapRAG**
```
Query → Key Normalization → Hash Table Lookup → Context
```
- **Characteristics**: Microsecond retrieval, zero semantic generalization
- **Best for**: Exact keyword matching, author/paper IDs, canonical titles
- **Complexity**: Expected $\mathcal{O}(1)$ average case (subject to hash collision resolution)

### 4. **TrieRAG**
```
Query → Prefix Tree Walk → Subtree Enumeration → Context
```
- **Characteristics**: Fast prefix matching, hierarchical taxonomy traversal
- **Best for**: Autocomplete, prefix lookup, hierarchical topic classification
- **Complexity**: $\mathcal{O}(m + z)$ where $m$ is prefix length and $z$ is count of matching enumerated tokens

### 5. **HashMap+TrieRAG**
```
Query → Exact HashMap Check (O(1)) → Fallback to Trie Subtree Walk (O(m+z)) → Context
```
- **Characteristics**: Two-tier exact match with prefix exploration
- **Best for**: Multi-level hierarchical search and entity resolution
- **Complexity**: Expected $\mathcal{O}(1) + \mathcal{O}(m + z)$

### 6. **HashMap+GraphRAG**
```
Query → HashMap Entity Entry-point (O(1)) → Local Graph Expansion → Context
```
- **Characteristics**: Instant entry-point resolution coupled with relational graph reasoning
- **Best for**: Known entity multi-hop neighborhood exploration
- **Complexity**: Expected $\mathcal{O}(1) + \mathcal{O}(k \cdot \bar{d}^h)$

### 7. **Trie+GraphRAG**
```
Query → Trie Prefix Exploration → Seed Entity Identification → Graph Traversal → Context
```
- **Characteristics**: Prefix-tolerant entry points connecting into entity relationship networks
- **Best for**: Partial query formulation and taxonomical graph exploration
- **Complexity**: $\mathcal{O}(m + z) + \mathcal{O}(k \cdot \bar{d}^h)$

### 8. **InvertedIndex+GraphRAG** ⭐ (Pareto-Optimal)
```
Query → Token Inverted Index (BM25/TF) → Top Seed Expansion → Graph Reasoning → Context
```
- **Characteristics**: Sub-millisecond retrieval, high keyword relevance, graph structural expansion
- **Best for**: Large corpora combining lexical search with relationship verification
- **Complexity**: Posting list intersection $\mathcal{O}(L) + \mathcal{O}(k \cdot \bar{d}^h)$

### 9. **AdaptiveRetrievalRAG** ⭐⭐ (Core Research Focus)
```
Query → Intent Classifier
    ├─ Exact Identifier    → HashMapRAG
    ├─ Prefix/Partial       → TrieRAG
    ├─ Multi-Keyword        → InvertedIndexGraphRAG
    ├─ Relational/Citation  → GraphRAG
    └─ Conceptual/Semantic  → VectorRAG
    ↓
    Result Verification & Context Assembly
```
- **Characteristics**: Dynamically matches query morphology to the optimal indexing data structure
- **Best for**: Heterogeneous workloads spanning exact lookups, multi-hop reasoning, and conceptual queries
- **Complexity**: Routing classification $\mathcal{O}(c) + \mathcal{O}(\text{selected retriever})$

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

## 🔬 Empirical Benchmark Findings (Hardened Protocol)

Results from the standardized benchmark suite across 75 test queries spanning 7 categories (Exact, Prefix, Keyword, Semantic, Relational, Multi-Hop, Mixed):

### 1. Retrieval Quality (Primary Scientific Metric)
1. 🏆 **VectorRAG** — Quality: **0.4023** (P@5: 0.1360, MRR: 0.4811, NDCG@5: 0.4600)
2. 🥈 **InvertedIndex+GraphRAG** — Quality: **0.3749** (P@5: 0.1360, MRR: 0.4433, NDCG@5: 0.4315)
3. 🥉 **Trie+GraphRAG** — Quality: **0.3190** (P@5: 0.1200, MRR: 0.3682, NDCG@5: 0.3635)
4. **TrieRAG** — Quality: 0.3156 (P@5: 0.1093, MRR: 0.3778, NDCG@5: 0.3551)
5. **HashMap+TrieRAG** — Quality: 0.3011 (P@5: 0.0960, MRR: 0.3733, NDCG@5: 0.3368)
6. **AdaptiveRetrievalRAG** — Quality: 0.2829 (P@5: 0.1120, MRR: 0.3278, NDCG@5: 0.3251)
7. **GraphRAG** — Quality: 0.1731 (P@5: 0.0800, MRR: 0.1898, NDCG@5: 0.1995)
8. **HashMapRAG** — Quality: 0.1376 (P@5: 0.0400, MRR: 0.1733, NDCG@5: 0.1539)
9. **HashMap+GraphRAG** — Quality: 0.1255 (P@5: 0.0747, MRR: 0.1247, NDCG@5: 0.1516)

### 2. High-Resolution Latency Profiles (Decoupled Performance)
1. ⚡ **HashMapRAG** — p50: **0.03 ms**, Mean: 0.03 ms, Build: 0.1 ms, RAM: ~0.0 MB
2. ⚡ **HashMap+GraphRAG** — p50: **0.04 ms**, Mean: 0.04 ms, Build: 0.5 ms, RAM: ~0.0 MB
3. ⚡ **GraphRAG** — p50: **0.04 ms**, Mean: 0.05 ms, Build: 0.7 ms, RAM: ~0.0 MB
4. ⚡ **InvertedIndex+GraphRAG** — p50: **0.04 ms**, Mean: 0.06 ms, Build: 1.2 ms, RAM: ~0.1 MB
5. ⚡ **HashMap+TrieRAG** — p50: **0.07 ms**, Mean: 0.09 ms, Build: 9.4 ms, RAM: ~0.0 MB
6. **Trie+GraphRAG** — p50: 0.27 ms, Mean: 0.33 ms, Build: 3.3 ms, RAM: ~0.0 MB
7. **TrieRAG** — p50: 0.30 ms, Mean: 0.36 ms, Build: 4.7 ms, RAM: ~0.0 MB
8. **AdaptiveRetrievalRAG** — p50: 17.02 ms, Mean: 17.80 ms, Build: 423.7 ms, RAM: ~0.8 MB
9. **VectorRAG** — p50: 18.24 ms, Mean: 20.37 ms, Build: 871.8 ms, RAM: ~49.0 MB

### 3. Empirical Pareto Frontier (Quality vs Latency Tradeoff)
Non-dominated architectures defining the optimal empirical boundary (`speed_vs_accuracy.png`):
- **Maximum Quality**: `VectorRAG` (0.4023 Quality, 20.37 ms)
- **High-Quality / Sub-millisecond**: `InvertedIndex+GraphRAG` (0.3749 Quality, 0.06 ms — **340x faster than VectorRAG with 93% quality**)
- **Graph Traversal**: `GraphRAG` (0.1731 Quality, 0.05 ms)
- **Minimum Latency**: `HashMapRAG` (0.1376 Quality, 0.03 ms)

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
