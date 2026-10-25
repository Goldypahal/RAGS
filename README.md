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

This repository asks whether hybridizing classical data structures with retrieval can match dense vectors at lower cost:

- **Lookup structures**: $O(1)$ HashMaps and $O(m)$ Tries for key/entity and prefix resolution.
- **Structural multi-hop**: graphs over entity co-occurrence and (where available) citations.
- **Adaptive routing**: query classification directing queries to a retrieval engine.

See the benchmark results below for what the evidence currently supports: BM25 is the strongest lexical system, and routing and the entity graph do not yet beat it.

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
| **8** | **Inverted Index + Graph** | $\mathcal{O}(L) + \mathcal{O}(k \cdot \bar{d}^h)$ | Okapi BM25 keyword relevance combined with graph expansion |
| **9** | **Adaptive Retrieval RAG** | $\mathcal{O}(c) + \mathcal{O}(\text{engine})$ | Dynamic query morphology routing to the optimal indexing engine |

---

## 📊 Benchmark & Evaluation Suite

All 9 systems run under identical conditions; every report includes per-system 95% bootstrap CIs and paired Wilcoxon tests against the best system. Three datasets:

| Dataset | Docs | Queries | Ground truth |
|---|---:|---:|---|
| `Dataset/HotpotQA` | 4,937 | 500 | Real multi-hop questions, gold supporting paragraphs |
| `Dataset/SQuAD` | 93 | 1,000 | Real extractive questions, gold paragraph |
| `benchmark/dataset` + `tests/scaled` | **10** | 658 | Template-generated (10 anchor papers × ~10 templates) |

> ⚠️ The scaled suite is a **smoke test**, not evidence: with 10 documents, `top_k=5` returns half the corpus, and its 658 queries are variations on 10 anchors. Use HotpotQA/SQuAD for claims.

### Results (2026-10-25)

Quality = mean of P@1, P@5, R@5, MRR, NDCG@5. Δ is the paired per-query difference to BM25 (InvertedIndexGraphRAG), with a 95% bootstrap CI. Dense rows use `--embedder minilm` (all-MiniLM-L6-v2); TF-IDF rows use the lexical stand-in. The lexical systems give identical results under either flag. Latency is measured on CPU and includes query encoding.

| Architecture | HotpotQA quality | Δ vs BM25 [95% CI] | SQuAD quality | Δ vs BM25 [95% CI] | HotpotQA p50 |
|---|:---:|:---:|:---:|:---:|---:|
| VectorRAG (MiniLM, dense) | **0.689** | +0.011 [−0.014, +0.037] | 0.643 | −0.055 [−0.075, −0.034] | 21.6 ms |
| **InvertedIndexGraphRAG** (BM25) | 0.678 | — | **0.698** | — | 3.5 ms |
| AdaptiveRetrievalRAG (MiniLM) | 0.669 | −0.009 [−0.035, +0.016] | 0.621 | −0.077 [−0.097, −0.057] | 21.9 ms |
| VectorRAG (TF-IDF) | 0.665 | −0.014 [−0.030, +0.003] | 0.678 | −0.021 [−0.031, −0.010] | 7.2 ms |
| AdaptiveRetrievalRAG (TF-IDF) | 0.647 | −0.031 [−0.049, −0.013] | 0.645 | −0.053 [−0.067, −0.039] | 7.6 ms |
| HashMapRAG | 0.611 | −0.068 | 0.295 | −0.403 | 0.7 ms |
| HashMapTrieRAG | 0.516 | −0.163 | 0.306 | −0.393 | 1.5 ms |
| TrieGraphRAG | 0.514 | −0.165 | 0.307 | −0.391 | 46.0 ms |
| TrieRAG | 0.513 | −0.165 | 0.305 | −0.394 | 47.1 ms |
| GraphRAG | 0.001 | −0.677 | 0.011 | −0.687 | 0.04 ms |
| HashMapGraphRAG | 0.000 | −0.678 | 0.012 | −0.686 | 0.04 ms |

What the data supports:
- **BM25 matches dense retrieval on HotpotQA and beats it on SQuAD,** at about 1/6 of the latency. On HotpotQA, MiniLM's +0.011 is within the CI (Wilcoxon p = 0.69). On SQuAD, BM25 leads by 0.055 (p = 6.6e-08), likely because SQuAD questions reuse the passage's wording.
- **The adaptive router never beats the best single system.** It is tied with or significantly worse than BM25 on every dataset and embedder.
- **The speed advantage is real but modest:** about 6× (3.5 ms vs 21.6 ms), mostly the cost of encoding the query, not the earlier "330×".
- **The co-occurrence graph adds nothing on real data.** Its entity extractor matches ~20 hard-coded ML words, so GraphRAG and HashMapGraphRAG score ≈ 0 outside the toy corpus. Citation edges (`citations.json`) help only where citations exist.
- **Tries don't scale as implemented:** about 47 ms p50 at 4.9k docs, slower than dense vector search (21.6 ms).

### Learned router (scaled suite, group-wise split)

The split is by anchor paper/prompt (12 train / 4 val / 4 test groups), and `C` is chosen on validation. On 135 held-out queries the router reaches 0.734 (92.6% of oracle), vs 0.697 for the best single system chosen on train. With only 4 test groups, treat this as indicative. Cross-domain transfer (lexical → reasoning) reaches 30% of oracle. Reproduce with `python benchmark/train_and_eval_router.py --results <scaled results json>`.

### End-to-end generation: pending re-run
Earlier faithfulness numbers are superseded. A first HotpotQA run with the fixed evaluator found two problems, both now fixed or flagged in code:
- **Prompt bug:** the context was formatted as `[1] Title: …`, and Flan-T5-small answered with the bracket (`"[2]"`) in about 25% of queries, for every system.
- **Faithfulness is not a valid metric for short answers:** the NLI judge entailed 0 of 12 answers that exactly matched the gold answer. Use answer **EM/F1** (now reported when the dataset has reference answers) as the primary E2E metric.

Re-run with:
```bash
python benchmark/run_e2e_generation_benchmark.py --dataset ../Dataset/HotpotQA --samples-per-type 100
```

---

## ⚡ Quick Start

### 1. Requirements
Python 3.9+. See `requirements.txt`: dense retrieval and the E2E benchmark need `sentence-transformers`/`torch`; everything else needs only numpy, scipy and scikit-learn.
```bash
cd rags-research-framework
pip install -r requirements.txt
python -m pytest tests          # regression tests
```

### 2. Run Benchmarks
```bash
# Real datasets (use these for claims)
python run_all_tests.py --dataset ../Dataset/HotpotQA
python run_all_tests.py --dataset ../Dataset/SQuAD

# Without sentence-transformers, use the lexical TF-IDF stand-in for VectorRAG (label it as such)
python run_all_tests.py --dataset ../Dataset/HotpotQA --embedder tfidf

# Toy 10-document smoke test
python benchmark/scale_benchmark.py && python run_all_tests.py --scale

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
