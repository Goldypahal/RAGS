#!/usr/bin/env python3
"""
Comprehensive Benchmark Runner - Tests all 9 RAG systems against all 70 test queries
Usage: python run_all_tests.py
"""

import sys
import os
import time
import json
from datetime import datetime
from pathlib import Path

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

def initialize_rag_systems(dataset_dir: str):
    """Initialize all 9 RAG systems with benchmark data."""
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
    
    # Initialize each system and add documents
    for system_name, system in systems.items():
        system.initialize()
        system.add_documents(documents)
        print(f"  ✓ {system_name} initialized with {len(documents)} documents")
    
    return systems, papers, authors, topics, citations


def load_all_test_suites(test_dir: str):
    """Load all 7 test suites."""
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


def run_benchmark_suite(systems, test_suites):
    """Run comprehensive benchmark across all systems and tests."""
    evaluator = BenchmarkEvaluator()
    total_tests = sum(len(tests) for tests in test_suites.values())
    completed = 0
    
    print(f"\n⚙️  Running benchmark suite ({total_tests} total tests)...\n")
    
    for suite_name, tests in test_suites.items():
        print(f"📊 Testing: {suite_name.upper()}")
        
        for test in tests:
            test_id = test.get('id', tests.index(test))
            query = test['query']
            expected_docs = test.get('expected_doc_ids', test.get('expected_ids', []))
            
            # Run each system on this test
            for system_name, system in systems.items():
                try:
                    # Measure retrieval
                    start_time = time.time()
                    result = system.retrieve(query, top_k=5)
                    elapsed_ms = (time.time() - start_time) * 1000
                    
                    # Extract document IDs
                    retrieved_docs = [doc.doc_id for doc in result.documents]
                    
                    # Estimate tokens (simple approximation)
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
                    print(f"    ⚠️  Error - {system_name} on {query[:30]}: {str(e)}")
            
            completed += 1
            if completed % 10 == 0:
                print(f"  Progress: {completed}/{total_tests} tests completed")
    
    return evaluator


def generate_detailed_report(evaluator):
    """Generate comprehensive report with rankings and analysis."""
    print("\n" + "="*80)
    print("📈 COMPREHENSIVE BENCHMARK RESULTS")
    print("="*80 + "\n")
    
    # Generate main report
    report = evaluator.generate_report()
    
    # Print rankings
    print("🏆 SYSTEM RANKINGS (by Combined Score)\n")
    print("Rank | System                    | Score | Accuracy | Latency | Memory")
    print("-" * 75)
    
    for i, entry in enumerate(report['ranking'], 1):
        system_name = entry['system']
        score = entry['score']
        metrics = report['systems'][system_name]
        
        accuracy = metrics['accuracy'].get('precision_at_1', 0)
        latency = metrics['performance'].get('avg_latency_ms', 0)
        memory = metrics['performance'].get('avg_memory_mb', 0)
        
        print(f"{i:4d} | {system_name:25s} | {score:5.3f} | {accuracy:8.3f} | {latency:7.1f}ms | {memory:6.1f}MB")
    
    print("\n" + "-"*75)
    print(f"Total Tests Run: {report['total_tests']}")
    print(f"Timestamp: {report['timestamp']}\n")
    
    # Detailed system breakdown
    print("\n📊 DETAILED SYSTEM ANALYSIS\n")
    
    for system_name in sorted(report['systems'].keys()):
        metrics = report['systems'][system_name]
        print(f"\n{system_name}")
        print("─" * 75)
        
        print("  Accuracy Metrics:")
        accuracy = metrics.get('accuracy', {})
        print(f"    • Precision@1:  {accuracy.get('precision_at_1', 0):.3f}")
        print(f"    • Precision@5:  {accuracy.get('precision_at_5', 0):.3f}")
        print(f"    • Recall@5:     {accuracy.get('recall_at_5', 0):.3f}")
        print(f"    • MRR:          {accuracy.get('mrr', 0):.3f}")
        print(f"    • NDCG@5:       {accuracy.get('ndcg_at_5', 0):.3f}")
        
        print("  Performance Metrics:")
        perf = metrics.get('performance', {})
        print(f"    • Avg Latency:  {perf.get('avg_latency_ms', 0):.2f}ms")
        print(f"    • P50 Latency:  {perf.get('p50_latency_ms', 0):.2f}ms")
        print(f"    • P95 Latency:  {perf.get('p95_latency_ms', 0):.2f}ms")
        print(f"    • Memory Usage: {perf.get('avg_memory_mb', 0):.2f}MB")
        print(f"    • CPU Usage:    {perf.get('avg_cpu_percent', 0):.1f}%")
        
        print("  Cost Metrics:")
        cost = metrics.get('cost', {})
        print(f"    • Total Tokens: {cost.get('total_tokens_used', 0)}")
        print(f"    • Avg Tokens:   {cost.get('avg_tokens_used', 0):.0f}")
        print(f"    • Total Cost:   ${cost.get('total_usd_cost', 0):.4f}")
        print(f"    • Avg Cost:     ${cost.get('avg_usd_cost', 0):.6f}")
        
        print(f"  Score: {report['ranking'][next((i for i, r in enumerate(report['ranking']) if r['system'] == system_name), 0)]['score']:.4f}")
    
    # Per-test-type analysis
    print("\n\n📋 PERFORMANCE BY TEST TYPE\n")
    
    test_types = {}
    for metric in report.get('metrics', []):
        test_type = metric['test_type']
        if test_type not in test_types:
            test_types[test_type] = []
        test_types[test_type].append(metric)
    
    for test_type in sorted(test_types.keys()):
        tests = test_types[test_type]
        avg_p1 = sum(t.get('precision_at_1', 0) for t in tests) / len(tests)
        avg_lat = sum(t.get('retrieval_time_ms', 0) for t in tests) / len(tests)
        
        print(f"  {test_type:25s}: P@1={avg_p1:.3f}, Lat={avg_lat:.1f}ms")
    
    return report


def save_results(report, evaluator):
    """Save detailed results to JSON."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = Path("benchmark/results")
    results_dir.mkdir(exist_ok=True)
    
    output_file = results_dir / f"benchmark_results_{timestamp}.json"
    evaluator.save_results(f"benchmark_results_{timestamp}.json")
    print(f"\n💾 Results saved to: {output_file}")
    
    # Also save human-readable summary
    summary_file = results_dir / f"summary_{timestamp}.txt"
    with open(summary_file, 'w') as f:
        f.write("BENCHMARK RESULTS SUMMARY\n")
        f.write("=" * 80 + "\n")
        f.write(f"Timestamp: {datetime.now().isoformat()}\n\n")
        
        f.write("SYSTEM RANKINGS\n")
        f.write("-" * 80 + "\n")
        for i, entry in enumerate(report['ranking'], 1):
            f.write(f"{i}. {entry['system']}: {entry['score']:.4f}\n")
    
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
        
        # Initialize systems
        systems, papers, authors, topics, citations = initialize_rag_systems(dataset_dir)
        
        # Load tests
        test_suites = load_all_test_suites(test_dir)
        
        # Run benchmark
        print(f"\n📊 Testing {len(systems)} systems on {sum(len(tests) for tests in test_suites.values())} queries\n")
        evaluator = run_benchmark_suite(systems, test_suites)
        
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
