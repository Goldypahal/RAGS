#!/usr/bin/env python3
"""
Comprehensive Benchmark Runner - Tests all 9 RAG systems against all 70 test queries
Usage: python run_all_tests.py
"""

import sys
import os
import io
import time
import json
from datetime import datetime
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from benchmark.benchmark_evaluator import BenchmarkEvaluator, BenchmarkLoader, MetricsCalculator
from common.base import BaseRAG, RetrievalResult, Document

# Import all 9 RAG systems
sys.path.insert(0, str(Path(__file__).parent / "1-vector-rag"))
sys.path.insert(0, str(Path(__file__).parent / "2-graph-rag"))
sys.path.insert(0, str(Path(__file__).parent / "3-hashmap-rag"))
sys.path.insert(0, str(Path(__file__).parent / "4-trie-rag"))
sys.path.insert(0, str(Path(__file__).parent / "5-hashmap-trie-rag"))
sys.path.insert(0, str(Path(__file__).parent / "6-hashmap-graph-rag"))
sys.path.insert(0, str(Path(__file__).parent / "7-trie-graph-rag"))
sys.path.insert(0, str(Path(__file__).parent / "8-inverted-index-graph-rag"))
sys.path.insert(0, str(Path(__file__).parent / "9-adaptive-retrieval-rag"))

from vector_rag import VectorRAG
from graph_rag import GraphRAG
from hashmap_rag import HashMapRAG
from trie_rag import TrieRAG
from hashmap_trie_rag import HashMapTrieRAG
from hashmap_graph_rag import HashMapGraphRAG
from trie_graph_rag import TrieGraphRAG
from inverted_index_graph_rag import InvertedIndexGraphRAG
from adaptive_rag import AdaptiveRetrievalRAG


import argparse
import psutil

def initialize_rag_systems(dataset_dir: str):
    """
    Initialize all 9 RAG systems with benchmark data.
    Decouples and records index construction time and differential memory footprint.
    """
    print(f"🚀 Initializing all 9 RAG systems with dataset {dataset_dir}...")
    
    # Load shared data
    papers = BenchmarkLoader.load_papers(dataset_dir)
    try:
        authors = BenchmarkLoader.load_authors(dataset_dir)
    except FileNotFoundError:
        authors = []
    try:
        topics = BenchmarkLoader.load_topics(dataset_dir)
    except FileNotFoundError:
        topics = []
    try:
        citations = BenchmarkLoader.load_citations(dataset_dir)
    except FileNotFoundError:
        citations = []
    
    # Create systems
    systems = {
        "VectorRAG": VectorRAG(),
        "GraphRAG": GraphRAG(),
        "HashMapRAG": HashMapRAG(),
        "TrieRAG": TrieRAG(),
        "HashMapTrieRAG": HashMapTrieRAG(),
        "HashMapGraphRAG": HashMapGraphRAG(),
        "TrieGraphRAG": TrieGraphRAG(),
        "InvertedIndexGraphRAG": InvertedIndexGraphRAG(),
        "AdaptiveRetrievalRAG": AdaptiveRetrievalRAG(),
    }
    
    # Create documents from papers
    documents = []
    for paper in papers:
        content_text = paper.get('content', paper.get('abstract', ''))
        full_content = f"Title: {paper.get('title', '')}\n\n{content_text}"
        doc = Document(
            doc_id=paper['id'],
            content=full_content,
            title=paper.get('title', ''),
            keywords=paper.get('keywords', []),
            metadata={
                'year': paper.get('year'),
                'venue': paper.get('venue'),
                'authors': paper.get('authors', []),
                'topics': paper.get('topics', []),
                'citations': paper.get('citations_count', 0),
            }
        )
        documents.append(doc)
    
    # Profile index construction for each system separately
    process = psutil.Process(os.getpid())
    build_stats = {}
    
    for system_name, system in systems.items():
        # Baseline memory before index build
        mem_before = process.memory_info().rss / (1024 * 1024)
        t_start = time.perf_counter_ns()
        
        system.initialize()
        system.add_documents(documents)
        
        t_end = time.perf_counter_ns()
        mem_after = process.memory_info().rss / (1024 * 1024)
        
        build_time_ms = (t_end - t_start) / 1_000_000.0
        index_memory_mb = max(0.0, mem_after - mem_before)
        build_stats[system_name] = (build_time_ms, index_memory_mb)
        
        print(f"  ✓ {system_name:<24} built in {build_time_ms:6.1f}ms | Index RAM: ~{index_memory_mb:4.1f}MB ({len(documents)} docs)")
    
    return systems, papers, authors, topics, citations, build_stats


def load_all_test_suites(test_dir: str):
    """Load all test suites."""
    print(f"\n📋 Loading test suites from {test_dir}...")
    test_suites = {}
    suite_names = [
        "exact_lookup",
        "prefix_lookup", 
        "keyword_search",
        "semantic_search",
        "relationship_search",
        "multi_hop_reasoning",
        "mixed_queries",
        "multi_hop_qa",
        "fact_retrieval"
    ]
    
    for suite_name in suite_names:
        try:
            tests = BenchmarkLoader.load_test_suite(suite_name, test_dir=test_dir)
            test_suites[suite_name] = tests
            print(f"  ✓ {suite_name}: {len(tests)} tests")
        except FileNotFoundError:
            print(f"  ⚠ {suite_name}: not found, skipping")
    
    return test_suites


def run_benchmark_suite(systems, test_suites, build_stats=None):
    """Run comprehensive benchmark across all systems and tests with warm-ups and high-res timing."""
    evaluator = BenchmarkEvaluator()
    if build_stats:
        for sys_name, (b_time, b_mem) in build_stats.items():
            evaluator.record_build_stats(sys_name, b_time, b_mem)
            
    total_tests = sum(len(tests) for tests in test_suites.values())
    completed = 0
    
    # Warm-up phase: run sample queries to eliminate runtime JIT / allocation cold start artifacts
    print("\n🔥 Warming up systems (2 queries to prime caches)...")
    for system in systems.values():
        try:
            system.retrieve("warmup attention query", top_k=2)
            system.retrieve("deep learning neural", top_k=2)
        except Exception:
            pass
    print("  ✓ Warm-up complete.")
    
    print(f"\n⚙️  Running benchmark suite ({total_tests} total tests across {len(systems)} systems)...\n")
    
    for suite_name, tests in test_suites.items():
        print(f"📊 Testing: {suite_name.upper()} ({len(tests)} queries)")
        
        for test in tests:
            test_id = test.get('id', tests.index(test))
            query = test['query']
            expected_docs = test.get('expected_doc_ids', test.get('expected_ids', []))
            
            # Run each system on this test
            for system_name, system in systems.items():
                try:
                    # High-resolution nanosecond measurement
                    t_start = time.perf_counter_ns()
                    result = system.retrieve(query, top_k=5)
                    t_end = time.perf_counter_ns()
                    elapsed_ms = (t_end - t_start) / 1_000_000.0
                    
                    # Extract document IDs
                    retrieved_docs = [doc.doc_id for doc in result.documents]
                    
                    # Synthetic token proxy (query words + retrieved context estimate)
                    tokens_used = len(query.split()) + len(retrieved_docs) * 50
                    
                    # Evaluate
                    evaluator.evaluate_retrieval(
                        system_name=system_name,
                        test_type=suite_name,
                        test_id=test_id,
                        query=query,
                        retrieved_docs=retrieved_docs,
                        relevant_docs=expected_docs,
                        retrieval_time_ms=elapsed_ms,
                        tokens_used=tokens_used
                    )
                    
                except Exception as e:
                    print(f"    ⚠️  Error - {system_name} on '{query[:30]}': {str(e)}")
            
            completed += 1
            if completed % 10 == 0:
                print(f"  Progress: {completed}/{total_tests} test queries processed")
    
    return evaluator


def generate_detailed_report(evaluator):
    """Generate comprehensive report with rankings and analysis."""
    evaluator.print_report()
    return evaluator.generate_report()


def save_results(report, evaluator):
    """Save detailed results to JSON and markdown summary."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = Path("benchmark/results")
    results_dir.mkdir(exist_ok=True)
    
    output_file = results_dir / f"benchmark_results_{timestamp}.json"
    evaluator.save_results(f"benchmark_results_{timestamp}.json")
    print(f"\n💾 Results saved to: {output_file}")
    
    # Save formatted human-readable summary
    summary_file = results_dir / f"summary_{timestamp}.txt"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("BENCHMARK RESULTS SUMMARY (RESEARCH-HARDENED)\n")
        f.write("=" * 85 + "\n")
        f.write(f"Timestamp: {datetime.now().isoformat()}\n\n")
        
        f.write("RANKINGS BY RETRIEVAL QUALITY (Primary Metric)\n")
        f.write("-" * 85 + "\n")
        for entry in report.get('ranking_by_quality', []):
            name = entry['system']
            acc = report['systems'][name]['accuracy']
            f.write(f"{entry['rank']}. {name:<26} Quality: {acc['mean_quality']:.4f} (P@5: {acc['precision_at_5']:.4f}, MRR: {acc['mrr']:.4f})\n")
            
        f.write("\nLATENCY & PERFORMANCE PROFILES (Decoupled)\n")
        f.write("-" * 85 + "\n")
        for name, metrics in report['systems'].items():
            lat = metrics['latency_profile_ms']
            idx = metrics['index_construction']
            f.write(f"{name:<26} p50: {lat['p50']:6.2f}ms | p95: {lat['p95']:6.2f}ms | Mean: {lat['mean']:6.2f}ms | Build: {idx['build_time_ms']:5.1f}ms\n")
            
        f.write("\nCOMPOSITE UTILITY RANKINGS (Secondary Metric)\n")
        f.write("-" * 85 + "\n")
        for entry in report.get('ranking_by_utility', []):
            f.write(f"{entry['rank']}. {entry['system']:<26} Utility: {entry['utility']:.4f}\n")
    
    print(f"📄 Summary saved to: {summary_file}\n")


def main():
    parser = argparse.ArgumentParser(description="Run RAG Benchmarks")
    parser.add_argument("--dataset", type=str, default="benchmark/dataset", help="Path to the dataset directory")
    args = parser.parse_args()
    
    dataset_dir = args.dataset
    test_dir = os.path.join(dataset_dir, "tests") if "Dataset" in dataset_dir else "benchmark/tests"

    try:
        print("\n" + "="*80)
        print("🎯 COMPREHENSIVE RAG BENCHMARK SUITE")
        print("="*80 + "\n")
        
        # Initialize systems and record decoupled build stats
        systems, papers, authors, topics, citations, build_stats = initialize_rag_systems(dataset_dir)
        
        # Load tests
        test_suites = load_all_test_suites(test_dir)
        
        # Run benchmark
        print(f"\n📊 Testing {len(systems)} systems on {sum(len(tests) for tests in test_suites.values())} queries\n")
        evaluator = run_benchmark_suite(systems, test_suites, build_stats=build_stats)
        
        # Generate report
        report = generate_detailed_report(evaluator)
        
        # Save results
        save_results(report, evaluator)
        
        print("\n" + "="*80)
        print("✅ BENCHMARK COMPLETE!")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
