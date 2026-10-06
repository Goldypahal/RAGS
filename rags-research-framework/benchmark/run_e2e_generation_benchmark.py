"""
Run End-to-End Generation & Faithfulness Benchmark (Phase 4).

Evaluates all 9 RAG architectures across:
1. Downstream Generated Answers
2. Faithfulness / Groundedness
3. Hallucination Rates
4. Context Recall
5. Answer Relevance
6. Generation Latency
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

# Ensure UTF-8 output on Windows consoles
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Add paths
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
        'TrieRAG': TrieRAG(),
        'AdaptiveRetrievalRAG': AdaptiveRetrievalRAG(),
        'TrieGraphRAG': TrieGraphRAG(),
        'HashMapTrieRAG': HashMapTrieRAG(),
        'HashMapGraphRAG': HashMapGraphRAG(),
        'GraphRAG': GraphRAG(),
        'HashMapRAG': HashMapRAG(),
    }
    for name, s in systems.items():
        s.initialize()
        s.add_documents(documents)
    return systems


def main():
    parser = argparse.ArgumentParser(description="End-to-End Generation & Faithfulness Benchmark")
    parser.add_argument("--samples-per-type", type=int, default=25, help="Number of queries per type (default: 25)")
    args = parser.parse_args()
    
    print("\n" + "=" * 85)
    print("🤖 PHASE 4: END-TO-END RAG GENERATION & FAITHFULNESS / HALLUCINATION BENCHMARK")
    print("=" * 85 + "\n")
    
    dataset_dir = "benchmark/dataset"
    documents, paper_lookup = load_dataset(dataset_dir)
    print(f"✓ Loaded {len(documents)} corpus documents")
    
    print("⚡ Initializing 9 RAG architectures...")
    systems = init_systems(documents)
    print("✓ All 9 systems initialized")
    
    # Load test queries
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
    
    selected_tests = []
    for cat in categories:
        tests = BenchmarkLoader.load_test_suite(cat, test_dir=test_dir)
        sampled = tests[:args.samples_per_type]
        for t in sampled:
            t['category'] = cat
            selected_tests.append(t)
            
    print(f"✓ Selected {len(selected_tests)} queries ({args.samples_per_type} per category across {len(categories)} categories)")
    print(f"📊 Total End-to-End evaluations to perform: {len(selected_tests) * len(systems)}\n")
    
    evaluator = E2EGenerationEvaluator()
    completed = 0
    total = len(selected_tests)
    
    for t_idx, test in enumerate(selected_tests):
        qid = test.get('id', str(t_idx))
        query = test['query']
        category = test['category']
        expected_doc_ids = test.get('expected_doc_ids', [])
        
        # Build gold factual propositions from expected documents
        gold_facts = []
        for did in expected_doc_ids:
            if did in paper_lookup:
                p = paper_lookup[did]
                gold_facts.append(f"{p['title']} was published in {p.get('year', '')}")
                gold_facts.append(f"{p['title']} authored by {', '.join(p.get('authors', [])[:2])}")
                
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
                expected_facts=gold_facts,
                retrieval_time_ms=ret_ms,
                expected_doc_ids=expected_doc_ids
            )
            
        completed += 1
        if completed % 25 == 0 or completed == total:
            print(f"  Progress: {completed}/{total} test queries evaluated across all 9 systems")
            
    # Summarize results
    summary = evaluator.summarize()
    
    print("\n" + "=" * 85)
    print("🏆 END-TO-END RAG GENERATION & FAITHFULNESS REPORT")
    print("=" * 85)
    print(f"{'System':<24} {'Faithfulness':<14} {'Hallucination':<15} {'Context Recall':<16} {'Ans Relevance':<14}")
    print("-" * 85)
    
    for sys_name in summary['system_rankings_by_faithfulness']:
        metrics = summary['systems'][sys_name]
        print(f"{sys_name:<24} "
              f"{metrics['mean_faithfulness']*100:6.2f}%       "
              f"{metrics['mean_hallucination_rate']*100:6.2f}%         "
              f"{metrics['mean_context_recall']*100:6.2f}%           "
              f"{metrics['mean_answer_relevance']*100:6.2f}%")
              
    print("=" * 85)
    
    # Save JSON results
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_dir = Path(__file__).parent / "results"
    out_json = out_dir / f"e2e_generation_results_{timestamp}.json"
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    print(f"\n💾 Saved full telemetry to: {out_json}")
    
    # Generate Plots
    plots_dir = out_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    
    systems_ranked = summary['system_rankings_by_faithfulness']
    faith_scores = [summary['systems'][s]['mean_faithfulness'] * 100 for s in systems_ranked]
    halluc_scores = [summary['systems'][s]['mean_hallucination_rate'] * 100 for s in systems_ranked]
    recall_scores = [summary['systems'][s]['mean_context_recall'] * 100 for s in systems_ranked]
    
    # Plot 1: Faithfulness vs Hallucination Rate
    plt.figure(figsize=(11, 6))
    y = np.arange(len(systems_ranked))
    height = 0.35
    plt.barh(y - height/2, faith_scores, height=height, label='Faithfulness (Grounded)', color='#2ca02c', edgecolor='black', alpha=0.85)
    plt.barh(y + height/2, halluc_scores, height=height, label='Hallucination Rate', color='#d62728', edgecolor='black', alpha=0.85)
    plt.yticks(y, systems_ranked)
    plt.gca().invert_yaxis()
    plt.xlabel('Percentage (%)')
    plt.title('RAG Architectures - End-to-End Answer Faithfulness vs Hallucination Rate')
    plt.legend()
    plt.grid(axis='x', linestyle='--', alpha=0.5)
    plt.tight_layout()
    plot1_path = plots_dir / "e2e_faithfulness_comparison.png"
    plt.savefig(plot1_path, dpi=150)
    plt.close()
    print(f"📊 Saved faithfulness comparison plot to: {plot1_path}")
    
    # Plot 2: Hallucination Rate by Query Type (Relational & Multi-Hop focus)
    plt.figure(figsize=(12, 7))
    categories_plot = ["relationship_search", "multi_hop_reasoning", "semantic_search", "exact_lookup"]
    key_systems = ['VectorRAG', 'InvertedIndexGraphRAG', 'GraphRAG', 'TrieGraphRAG', 'AdaptiveRetrievalRAG']
    x = np.arange(len(categories_plot))
    w = 0.16
    colors_k = ['#1f77b4', '#2ca02c', '#9467bd', '#ff7f0e', '#17becf']
    
    for i, sys_k in enumerate(key_systems):
        if sys_k in summary['systems']:
            by_q = summary['systems'][sys_k]['by_query_type']
            h_rates = [by_q.get(c, {}).get('hallucination_rate', 0.0) * 100 for c in categories_plot]
            plt.bar(x + (i - 2)*w, h_rates, width=w, label=sys_k, color=colors_k[i], edgecolor='black', alpha=0.85)
            
    plt.xticks(x, [c.replace('_', ' ').title() for c in categories_plot])
    plt.ylabel('Hallucination Rate (%) - LOWER is better')
    plt.title('Hallucination Rate by Query Type (Testing Graph vs. Vector Hallucination Mitigation)')
    plt.legend()
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    plt.tight_layout()
    plot2_path = plots_dir / "e2e_hallucination_by_query_type.png"
    plt.savefig(plot2_path, dpi=150)
    plt.close()
    print(f"📊 Saved query-type hallucination plot to: {plot2_path}")
    print("\n✅ PHASE 4 BENCHMARK COMPLETE!\n")


if __name__ == "__main__":
    main()
