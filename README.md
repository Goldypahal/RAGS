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

| # | System | Algorithmic Complexity | Primary Use Case |
|---|---|---|---|
| **1** | **VectorRAG** | $\mathcal{O}(n \cdot d)$ | Dense semantic understanding and conceptual queries |
| **2** | **GraphRAG** | $\mathcal{O}(k \cdot \bar{d}^h)$ | Multi-hop reasoning across entities, authors, and citation networks |
| **3** | **HashMapRAG** | Expected $\mathcal{O}(1)$ | Real-time exact keyword, ID, and canonical term matching |
| **4** | **TrieRAG** | $\mathcal{O}(m + z)$ | Autocomplete, prefix filtering, and hierarchical taxonomy navigation |
| **5** | **HashMap + Trie** | Expected $\mathcal{O}(1) + \mathcal{O}(m + z)$ | Two-tier exact match fallback to prefix matching |
| **6** | **HashMap + Graph** | Expected $\mathcal{O}(1) + \mathcal{O}(k \cdot \bar{d}^h)$ | Instant entity entry-point resolution with relational graph reasoning |
| **7** | **Trie + Graph** | $\mathcal{O}(m + z) + \mathcal{O}(k \cdot \bar{d}^h)$ | Prefix-guided entity entry connecting to graph traversal |
| **8** | **Inverted Index + Graph** ⭐ | $\mathcal{O}(L) + \mathcal{O}(k \cdot \bar{d}^h)$ | Hybrid BM25 keyword relevance combined with graph expansion |
| **9** | **Adaptive Retrieval RAG** | $\mathcal{O}(c) + \mathcal{O}(\text{engine})$ | Dynamic query morphology routing to the optimal indexing engine |

---

## 📊 Benchmark & Evaluation Suite (Hardened Protocol)

The evaluation suite rigorously tests all 9 systems under identical conditions across **7 query dimensions** with two testing suites:
- **Standard Suite**: 75 curated test queries.
- **Scaled Benchmark Suite (`--scale`)**: 700 test queries (100 per category, 6,300 total evaluations) providing high statistical power.

### Scaled Benchmark Results (700 Queries, N=6,300)

| Rank | Architecture | Retrieval Quality (0-1) | P@5 | MRR | NDCG@5 | Latency p50 | Latency p95 | Index RAM | Build Time |
|---|---|---|---|---|---|---|---|---|---|
| **1** | **VectorRAG** | **0.7051** | 0.2649 | 0.8390 | 0.8053 | 0.12 ms | 28.68 ms | 49.1 MB | 301.6 ms |
| **2** | **InvertedIndexGraphRAG** ⭐ | **0.6474** | 0.2506 | 0.7656 | 0.7245 | **0.05 ms** | **0.10 ms** | <0.1 MB | 0.6 ms |
| **3** | **TrieRAG** | **0.5909** | 0.2066 | 0.7102 | 0.6666 | 0.32 ms | 0.57 ms | <0.1 MB | 1.7 ms |
| **4** | **AdaptiveRetrievalRAG** | **0.5826** | 0.2340 | 0.6863 | 0.6595 | 0.21 ms | 24.64 ms | 0.2 MB | 272.1 ms |
| **5** | **TrieGraphRAG** | **0.5625** | 0.2026 | 0.6759 | 0.6307 | 0.33 ms | 0.60 ms | 0.8 MB | 2.7 ms |
| **6** | **HashMapTrieRAG** | **0.5404** | 0.1754 | 0.6660 | 0.6079 | 0.10 ms | 0.42 ms | 0.3 MB | 3.7 ms |
| **7** | **HashMapGraphRAG** | **0.3252** | 0.1657 | 0.3665 | 0.3697 | 0.04 ms | 0.08 ms | <0.1 MB | 0.3 ms |
| **8** | **GraphRAG** | **0.3135** | 0.1597 | 0.3420 | 0.3564 | 0.04 ms | 0.08 ms | <0.1 MB | 0.2 ms |
| **9** | **HashMapRAG** | **0.2047** | 0.0583 | 0.2686 | 0.2212 | **0.02 ms** | **0.04 ms** | <0.1 MB | 0.1 ms |

> **Key Pareto Finding**: `InvertedIndexGraphRAG` achieves **91.8% of VectorRAG's retrieval quality** while running **119× faster at the mean (0.06 ms vs 7.14 ms)** with virtually zero additional memory footprint (<0.1 MB vs 49.1 MB).

---

### 🧠 The Oracle Router & Routing Regret Experiment

To test whether dynamic routing outperforms fixed retrieval architectures, we implemented an **Oracle Router** (theoretical upper-bound selecting $\arg\max_i \text{Quality}(S_i, q)$ for each query):

- **Oracle Upper Bound**: **0.7839** ($\pm 0.0126$ at 95% CI) — **+7.88 points over VectorRAG**. This proves that no single static retriever is universally optimal across all query types.
- **VectorRAG Baseline**: **0.7051** ($\pm 0.0191$).
- **Adaptive Router**: **0.5373** (Query analyzer) / **0.5826** (System overall) — reaches **68.5% of Oracle potential**.
- **Random Router Baseline**: **0.4969** (Null hypothesis).
- **Mean Quality Regret**: **0.2466** ($Best(q) - Chosen(q)$).
- **Routing Decision Accuracy**: **29.3%** optimal system match rate.

---

### 📊 Architecture × Query-Type Performance Matrix

Mean retrieval quality across heterogeneous query categories:

| Architecture | Exact Lookup | Keyword Search | Mixed Queries | Multi-Hop | Prefix Lookup | Relationship | Semantic Search |
|---|---|---|---|---|---|---|---|
| **VectorRAG** | **0.722** | 0.774 | **0.733** | **0.833** | 0.787 | 0.454 | **0.635** |
| **InvertedIndexGraphRAG** | 0.672 | 0.742 | 0.651 | 0.763 | **0.790** | **0.542** | 0.372 |
| **TrieGraphRAG** | 0.538 | **0.809** | 0.573 | 0.588 | 0.731 | 0.325 | 0.374 |
| **TrieRAG** | 0.569 | 0.806 | 0.618 | 0.648 | 0.755 | 0.324 | 0.417 |
| **AdaptiveRetrievalRAG** | 0.622 | 0.686 | 0.565 | 0.440 | **0.799** | 0.459 | 0.507 |
| **HashMapTrieRAG** | 0.508 | 0.730 | 0.558 | 0.513 | 0.752 | 0.308 | 0.414 |
| **HashMapGraphRAG** | 0.312 | 0.409 | 0.315 | 0.445 | 0.239 | 0.265 | 0.291 |
| **GraphRAG** | 0.359 | 0.350 | 0.312 | 0.344 | 0.287 | 0.253 | 0.291 |
| **HashMapRAG** | 0.185 | 0.513 | 0.244 | 0.265 | 0.059 | 0.000 | 0.168 |

> **Key Discovery**: Classical and graph-hybrid structures outperform dense vectors in specific domains: `TrieGraphRAG` and `TrieRAG` exceed `VectorRAG` on keyword queries (0.809 vs 0.774), while `InvertedIndexGraphRAG` outperforms `VectorRAG` on relationship search (0.542 vs 0.454) and prefix lookups (0.790 vs 0.787).

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
