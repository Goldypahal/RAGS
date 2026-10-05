# 🚀 RAGS: Retrieval-Augmented Generation Research & Production Framework

A research framework and benchmarking suite for **Retrieval-Augmented Generation (RAG)** systems. This project explores, implements, and empirically evaluates **9 different RAG architectures**—combining classical computer science data structures (HashMaps, Tries, Inverted Indexes, Knowledge Graphs) with dense vector representations and adaptive query routing.

---

## 📑 Table of Contents

- [Overview](#overview)
- [Repository Structure](#repository-structure)
- [The 9 RAG Architectures](#the-9-rag-architectures)
- [Benchmark & Evaluation Suite](#benchmark--evaluation-suite)
- [Data Pipelines & Generators](#data-pipelines--generators)
- [Quick Start](#quick-start)
- [Research Documentation](#research-documentation)

---

## 🎯 Overview

Modern RAG pipelines often rely solely on approximate nearest neighbor (ANN) vector search. While effective for semantic similarity, dense embeddings struggle with exact entity lookup, prefix autocompletion, structural relationships, and multi-hop inference.

This repository demonstrates how hybridizing data structures yields orders-of-magnitude faster latency ($O(1)$ to $O(m)$) and significantly higher multi-hop retrieval accuracy:

- **Ultra-fast Lookup**: Constant-time $O(1)$ HashMaps and $O(m)$ Tries for immediate key/entity and prefix resolution.
- **Structural Multi-Hop**: Knowledge graphs for capturing citations, entities, and relational hops.
- **Adaptive Routing**: Real-time intent classification dynamically directing queries to optimal retrieval engines.

---

## 📂 Repository Structure

```
RAGS/
├── rags-research-framework/         # Core 9 RAG implementations & benchmark suite
│   ├── 1-vector-rag/               # Dense vector baseline (cosine similarity)
│   ├── 2-graph-rag/                # Graph traversal for relational multi-hop
│   ├── 3-hashmap-rag/              # O(1) constant-time exact match
│   ├── 4-trie-rag/                 # O(m) prefix tree search
│   ├── 5-hashmap-trie-rag/         # Two-tier exact + prefix hybrid
│   ├── 6-hashmap-graph-rag/        # Fast entity lookup + graph reasoning
│   ├── 7-trie-graph-rag/           # Prefix matching + graph expansion
│   ├── 8-inverted-index-graph-rag/ # BM25/keyword index + graph traversal
│   ├── 9-adaptive-retrieval-rag/   # Dynamic query classifier & router
│   ├── benchmark/                  # Evaluation engine & 70+ test queries
│   ├── common/                     # Base classes, Document, RetrievalResult
│   └── run_all_tests.py            # Comprehensive benchmark runner
├── Dataset/                        # Real-world benchmark datasets & SRS specs
│   ├── HotpotQA/                   # Multi-hop QA dataset
│   ├── SQuAD/                      # Fact retrieval dataset
│   ├── GitHubRepos/                # Code dependency & AST graph dataset
│   ├── ResearchPapers/             # Academic paper citation network dataset
│   └── Volume[1-4]_*.md            # Production Software Requirements & Architecture
├── generate_datasets.py            # Dataset builder for SQuAD & HotpotQA
├── generate_arxiv.py               # ArXiv research paper harvest pipeline
└── generate_github_dataset.py      # Python AST parser to code-graph pipeline
```

---

## 🏗️ The 9 RAG Architectures

| # | System | Complexity | Primary Use Case |
|---|---|---|---|
| **1** | **VectorRAG** | $O(n)$ | Dense semantic understanding and conceptual queries |
| **2** | **GraphRAG** | $O(V+E)$ | Multi-hop reasoning across entities, authors, and citation networks |
| **3** | **HashMapRAG** | $O(1)$ | Real-time exact keyword, ID, and term matching |
| **4** | **TrieRAG** | $O(m)$ | Autocomplete, prefix filtering, and hierarchical taxonomy navigation |
| **5** | **HashMap + Trie** | $O(1) + O(m)$ | Two-tier exact match fallback to prefix matching |
| **6** | **HashMap + Graph** | $O(1) + O(V+E)$ | Instant entity entry-point resolution with relational graph reasoning |
| **7** | **Trie + Graph** | $O(m) + O(V+E)$ | Prefix-guided entity entry connecting to graph traversal |
| **8** | **Inverted Index + Graph** | $O(\log n + V + E)$ | Hybrid BM25 keyword relevance combined with graph expansion |
| **9** | **Adaptive Retrieval RAG** | Dynamic | Query intent classification routing to the optimal engine |

---

## 📊 Benchmark & Evaluation Suite

The benchmark engine rigorously tests all 9 systems on identical datasets across **7 query dimensions**:
- **Exact Lookup**: Precise entity and title retrieval
- **Prefix Lookup**: Partial token & autocomplete matching
- **Keyword Search**: BM25 multi-term relevance
- **Semantic Search**: Paraphrased and conceptual queries
- **Relationship Search**: 1-hop connected entity queries
- **Multi-Hop Reasoning**: Multi-step graph reasoning paths
- **Mixed Real-World**: Blended production traffic

### Metrics Measured
- **Accuracy**: Precision@1, Precision@5, Recall@5, MRR (Mean Reciprocal Rank), NDCG
- **Performance**: Latency (p50, p95), CPU, and Memory usage
- **Composite Score**: Weighted multi-objective optimization ranking

---

## ⚡ Quick Start

### 1. Requirements
The core framework is lightweight and runs with the Python Standard Library (Python 3.8+):
```bash
cd rags-research-framework
pip install -r requirements.txt
```

### 2. Run Benchmarks
```bash
# Run comprehensive benchmark across all 9 systems (70 queries)
python run_all_tests.py

# Run interactive demo mode
python run_benchmark.py --mode demo

# Generate comparison plots (saved to benchmark/results/plots/)
python benchmark/generate_plots.py
```

### 3. Basic Code Example
```python
from common.base import Document
from hashmap_rag import HashMapRAG

# Initialize
rag = HashMapRAG()
rag.initialize()

# Ingest documents
docs = [
    Document(doc_id="1", content="Attention Is All You Need introduced Transformers.", title="Attention Paper")
]
rag.add_documents(docs)

# Retrieve
result = rag.retrieve("Attention Paper", top_k=5)
for doc in result.documents:
    print(f"[{doc.doc_id}] {doc.title}: {doc.content}")
```

---

## 📄 Research Documentation

Full documentation and publication templates are available in `rags-research-framework/`:
- `RESEARCH_PAPER_TEMPLATE.md`: Publication-ready paper structure with theoretical and empirical sections.
- `IMPLEMENTATION_GUIDE.md`: Deep dive into data structures, algorithms, and class designs.
- `BENCHMARK_GUIDE.md`: Complete benchmarking protocol and metric specifications.
