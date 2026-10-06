"""
Executable Publication-Grade End-to-End Generation & Faithfulness Benchmark.

Features:
- Deterministic random sampling with explicit seed (seed = 42)
- Real LLM Generation (google/flan-t5-small)
- Semantic NLI Claim Entailment Judge
- Dense Embedding Cosine Answer Relevance (all-MiniLM-L6-v2)
- 95% Bootstrap Confidence Intervals (B = 1,000)
- Paired Significance Testing vs VectorRAG
- Empirical Latency Ratio Computation
"""

import sys
import os
import io
import time
import json
import argparse
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

base_dir = Path(__file__).parent.parent
sys.path.insert(0, str(base_dir))
sys.path.insert(0, str(base_dir / "1-vector-rag"))
sys.path.insert(0, str(base_dir / "2-graph-rag"))
sys.path.insert(0, str(base_dir / "3-hashmap-rag"))
sys.path.insert(0, str(base_dir / "4-trie-rag"))
sys.path.insert(0, str(base_dir / "5-hashmap-trie-rag"))
sys.path.insert(0, str(base_dir / "6-hashmap-graph-rag"))
sys.path.insert(0, str(base_dir / "7-trie-graph-rag"))
sys.path.insert(0, str(base_dir / "8-inverted-index-graph-rag"))
sys.path.insert(0, str(base_dir / "9-adaptive-retrieval-rag"))

from common.base import Document
from vector_rag import VectorRAG
from graph_rag import GraphRAG
from hashmap_rag import HashMapRAG
from trie_rag import TrieRAG
from hashmap_trie_rag import HashMapTrieRAG
from hashmap_graph_rag import HashMapGraphRAG
from trie_graph_rag import TrieGraphRAG
from inverted_index_graph_rag import InvertedIndexGraphRAG
from adaptive_rag import AdaptiveRetrievalRAG

from benchmark.benchmark_evaluator import BenchmarkLoader
from benchmark.e2e_generation_evaluator import E2EGenerationEvaluator


def load_dataset(dataset_dir: str = "benchmark/dataset"):
    papers = BenchmarkLoader.load_papers(dataset_dir)
    documents = []
    paper_lookup = {}
    for p in papers:
        c_text = p.get('content', p.get('abstract', ''))
        full_c = f"Title: {p.get('title', '')}\n\n{c_text}"
        doc = Document(
            doc_id=p['id'],
            content=full_c,
            title=p.get('title', ''),
            keywords=p.get('keywords', []),
            metadata={'year': p.get('year'), 'venue': p.get('venue'), 'authors': p.get('authors', [])}
        )
        documents.append(doc)
        paper_lookup[p['id']] = p
    return documents, paper_lookup


def init_systems(documents):
    systems = {
        'VectorRAG': VectorRAG(),
        'InvertedIndexGraphRAG': InvertedIndexGraphRAG(),
        'AdaptiveRetrievalRAG': AdaptiveRetrievalRAG(),
        'TrieGraphRAG': TrieGraphRAG(),
        'TrieRAG': TrieRAG(),
        'HashMapTrieRAG': HashMapTrieRAG(),
        'GraphRAG': GraphRAG(),
        'HashMapGraphRAG': HashMapGraphRAG(),
        'HashMapRAG': HashMapRAG(),
    }
    for name, s in systems.items():
        s.initialize()
        s.add_documents(documents)
    return systems


def main():
    parser = argparse.ArgumentParser(description="Publication-Grade End-to-End Generation Benchmark")
    parser.add_argument("--samples-per-type", type=int, default=10, help="Queries sampled per category (default: 10, total 70 queries)")
    args = parser.parse_args()
    
    print("\n" + "=" * 85)
    print("🤖 PUBLICATION-GRADE END-TO-END RAG GENERATION & FAITHFULNESS BENCHMARK")
    print("=" * 85 + "\n")
    
    dataset_dir = "benchmark/dataset"
    documents, paper_lookup = load_dataset(dataset_dir)
    print(f"✓ Loaded {len(documents)} corpus documents")
    
    print("⚡ Initializing 9 RAG retrieval architectures...")
    systems = init_systems(documents)
    print("✓ All 9 systems initialized")
    
    test_dir = "benchmark/tests/scaled"
    categories = [
        "exact_lookup",
        "keyword_search",
        "semantic_search",
        "relationship_search",
        "multi_hop_reasoning",
        "mixed_queries",
        "prefix_lookup"
    ]
    
    # Deterministic uniform random sampling with fixed seed
    rng = np.random.default_rng(42)
    selected_tests = []
    
    for cat in categories:
        tests = BenchmarkLoader.load_test_suite(cat, test_dir=test_dir)
        n_sample = min(len(tests), args.samples_per_type)
        sample_indices = rng.choice(len(tests), size=n_sample, replace=False)
        for idx in sample_indices:
            t = tests[idx]
            t['category'] = cat
            selected_tests.append(t)
            
    total_evals = len(selected_tests) * len(systems)
    print(f"✓ Selected {len(selected_tests)} queries via seed=42 uniform sampling ({args.samples_per_type} per category)")
    print(f"📊 Total End-to-End evaluations to execute: {total_evals} (real LLM generation + NLI entailment)\n")
    
    evaluator = E2EGenerationEvaluator()
    completed = 0
    total = len(selected_tests)
    
    for t_idx, test in enumerate(selected_tests):
        qid = test.get('id', str(t_idx))
        query = test['query']
        category = test['category']
        expected_doc_ids = test.get('expected_doc_ids', [])
        
        for sys_name, system in systems.items():
            t0 = time.perf_counter_ns()
            res = system.retrieve(query, top_k=3)
            t1 = time.perf_counter_ns()
            ret_ms = (t1 - t0) / 1_000_000.0
            
            evaluator.evaluate_query(
                query_id=qid,
                query=query,
                query_type=category,
                system_name=sys_name,
                retrieved_docs=res.documents,
                expected_doc_ids=expected_doc_ids,
                retrieval_time_ms=ret_ms
            )
            
        completed += 1
        if completed % 10 == 0 or completed == total:
            print(f"  Progress: {completed}/{total} queries generated & evaluated ({completed * len(systems)}/{total_evals} evals)")
            
    # Compute summary with 95% Bootstrap CIs
    print("\n📐 Computing 95% Bootstrap Confidence Intervals (B = 1,000 resamples)...")
    summary = evaluator.summarize_with_bootstrap(n_bootstraps=1000)
    
    # Paired Statistical Significance vs VectorRAG
    vec_results = [r for r in evaluator.results if r.system_name == 'VectorRAG']
    paired_significance = {}
    
    for sys_name in systems.keys():
        if sys_name == 'VectorRAG':
            continue
        s_results = [r for r in evaluator.results if r.system_name == sys_name]
        
        diff_faith = [s.faithfulness - v.faithfulness for s, v in zip(s_results, vec_results)]
        diff_recall = [s.context_recall - v.context_recall for s, v in zip(s_results, vec_results)]
        diff_relev = [s.answer_relevance - v.answer_relevance for s, v in zip(s_results, vec_results)]
        
        t_f, p_f = stats.ttest_rel([s.faithfulness for s in s_results], [v.faithfulness for v in vec_results])
        t_r, p_r = stats.ttest_rel([s.context_recall for s in s_results], [v.context_recall for v in vec_results])
        
        paired_significance[sys_name] = {
            'delta_faithfulness': round(float(np.mean(diff_faith)), 4),
            'p_value_faithfulness': round(float(p_f), 4) if not np.isnan(p_f) else 1.0,
            'delta_context_recall': round(float(np.mean(diff_recall)), 4),
            'p_value_context_recall': round(float(p_r), 4) if not np.isnan(p_r) else 1.0,
            'delta_answer_relevance': round(float(np.mean(diff_relev)), 4)
        }
        
    summary['paired_significance_vs_vector'] = paired_significance
    
    # Empirical Speedup Ratio calculation
    vec_lat = summary['systems']['VectorRAG']['latency_ms']['mean']
    inv_lat = summary['systems']['InvertedIndexGraphRAG']['latency_ms']['mean']
    empirical_speedup = round(vec_lat / max(1e-6, inv_lat), 1)
    summary['empirical_speedup_vector_vs_inverted_graph'] = empirical_speedup
    
    print("\n" + "=" * 95)
    print("🏆 RIGOROUS END-TO-END GENERATION & SEMANTIC FAITHFULNESS REPORT")
    print("=" * 95)
    print(f"{'System':<24} {'Faithfulness (95% CI)':<26} {'Hallucination':<16} {'Context Recall':<16} {'Ans Relevance':<14}")
    print("-" * 95)
    
    for sys_name in summary['rankings_by_faithfulness']:
        m = summary['systems'][sys_name]
        f_val = m['faithfulness']['mean'] * 100
        f_ci = [m['faithfulness']['ci_95'][0] * 100, m['faithfulness']['ci_95'][1] * 100]
        h_val = m['hallucination_rate']['mean'] * 100
        r_val = m['context_recall']['mean'] * 100
        a_val = m['answer_relevance']['mean'] * 100
        
        print(f"{sys_name:<24} "
              f"{f_val:5.1f}% [{f_ci[0]:4.1f}%, {f_ci[1]:4.1f}%]     "
              f"{h_val:5.1f}%          "
              f"{r_val:5.1f}%          "
              f"{a_val:5.1f}%")
              
    print("=" * 95)
    print(f"⚡ Empirical Latency Ratio: VectorRAG ({vec_lat:.1f}ms) vs InvertedIndexGraphRAG ({inv_lat:.1f}ms) = {empirical_speedup}× faster\n")
    
    # Save clean telemetry
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_dir = Path(__file__).parent / "results"
    out_json = out_dir / f"e2e_generation_results_rigorous_{timestamp}.json"
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    print(f"💾 Full telemetry saved to: {out_json}")
    
    # Generate Plots with 95% Error Bars
    plots_dir = out_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    
    systems_ranked = summary['rankings_by_faithfulness']
    means = [summary['systems'][s]['faithfulness']['mean'] * 100 for s in systems_ranked]
    ci_err_lower = [means[i] - summary['systems'][s]['faithfulness']['ci_95'][0] * 100 for i, s in enumerate(systems_ranked)]
    ci_err_upper = [summary['systems'][s]['faithfulness']['ci_95'][1] * 100 - means[i] for i, s in enumerate(systems_ranked)]
    
    plt.figure(figsize=(10, 6))
    y = np.arange(len(systems_ranked))
    plt.barh(y, means, xerr=[ci_err_lower, ci_err_upper], capsize=5, color='#2ca02c', edgecolor='black', alpha=0.85)
    plt.yticks(y, systems_ranked)
    plt.gca().invert_yaxis()
    plt.xlabel('Semantic Faithfulness (%) via NLI Entailment [with 95% Bootstrap CI]')
    plt.title('RAG Architectures - End-to-End Generative Faithfulness (Flan-T5 + NLI Judge)')
    plt.grid(axis='x', linestyle='--', alpha=0.5)
    plt.tight_layout()
    p1 = plots_dir / "e2e_faithfulness_comparison.png"
    plt.savefig(p1, dpi=150)
    plt.close()
    print(f"📊 Saved publication plot: {p1}")
    
    # Plot 2: Answer Relevance vs Context Recall
    recalls = [summary['systems'][s]['context_recall']['mean'] * 100 for s in systems_ranked]
    relevs = [summary['systems'][s]['answer_relevance']['mean'] * 100 for s in systems_ranked]
    
    plt.figure(figsize=(10, 6))
    plt.scatter(recalls, relevs, s=120, color='#1f77b4', edgecolor='black', zorder=5)
    for i, s in enumerate(systems_ranked):
        plt.annotate(s, (recalls[i], relevs[i]), xytext=(6, 4), textcoords='offset points', fontsize=9, fontweight='bold')
    plt.xlabel('Context Recall (%) - Ground-Truth Documents Retrieved')
    plt.ylabel('Semantic Answer Relevance (%) - Cosine Similarity to Query')
    plt.title('RAG Generation - Context Recall vs Semantic Answer Relevance')
    plt.grid(linestyle='--', alpha=0.5)
    plt.tight_layout()
    p2 = plots_dir / "e2e_recall_vs_relevance.png"
    plt.savefig(p2, dpi=150)
    plt.close()
    print(f"📊 Saved publication plot: {p2}")
    
    print("\n✅ PUBLICATION-GRADE PHASE 4 BENCHMARK COMPLETED SUCCESSFULLY!\n")


if __name__ == "__main__":
    main()
