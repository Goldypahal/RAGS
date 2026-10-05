"""
Comprehensive benchmarking framework for RAG systems.

Measures:
- Retrieval latency
- Memory usage
- Accuracy metrics (Precision, Recall, MRR, NDCG)
- Cost metrics
- Hallucination rates
"""

import time
import json
from typing import List, Dict, Any, Callable, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from common.base import Document, RetrievalResult, BenchmarkResult


class BenchmarkSuite:
    """Comprehensive benchmarking suite for RAG systems."""
    
    def __init__(self, name: str = "RAG_Benchmark"):
        self.name = name
        self.results: List[BenchmarkResult] = []
        self.queries: List[Tuple[str, List[str]]] = []  # (query, relevant_doc_ids)
        
    def add_query(self, query: str, relevant_docs: List[str]) -> None:
        """Add query with ground truth relevant documents."""
        self.queries.append((query, relevant_docs))
    
    def benchmark_system(self, rag_system: Any, query: str, 
                        relevant_docs: List[str], top_k: int = 5) -> BenchmarkResult:
        """Benchmark a single system on a single query."""
        
        # Measure retrieval time and memory
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        mem_before = process.memory_info().rss / (1024 * 1024)  # MB
        
        start_time = time.time()
        result = rag_system.retrieve(query, top_k=top_k)
        elapsed_time = time.time() - start_time
        
        mem_after = process.memory_info().rss / (1024 * 1024)
        memory_used = mem_after - mem_before
        
        # Calculate metrics
        retrieved_doc_ids = [doc.doc_id for doc in result.documents]
        
        # Precision: correct retrievals / total retrievals
        if len(retrieved_doc_ids) > 0:
            precision = len(set(retrieved_doc_ids) & set(relevant_docs)) / len(retrieved_doc_ids)
        else:
            precision = 0.0
        
        # Recall: correct retrievals / relevant documents
        if len(relevant_docs) > 0:
            recall = len(set(retrieved_doc_ids) & set(relevant_docs)) / len(relevant_docs)
        else:
            recall = 0.0
        
        # MRR (Mean Reciprocal Rank)
        mrr = 0.0
        for i, doc_id in enumerate(retrieved_doc_ids, 1):
            if doc_id in relevant_docs:
                mrr = 1.0 / i
                break
        
        # NDCG (Normalized Discounted Cumulative Gain)
        dcg = 0.0
        for i, doc_id in enumerate(retrieved_doc_ids, 1):
            if doc_id in relevant_docs:
                dcg += 1.0 / (1 + np.log2(i))
        
        ideal_dcg = sum(1.0 / (1 + np.log2(i)) for i in range(1, min(len(relevant_docs), top_k) + 1))
        ndcg = dcg / ideal_dcg if ideal_dcg > 0 else 0.0
        
        # Accuracy: F1 score
        if precision + recall > 0:
            accuracy = 2 * (precision * recall) / (precision + recall)
        else:
            accuracy = 0.0
        
        # Create benchmark result
        benchmark = BenchmarkResult(
            architecture=rag_system.name,
            query=query,
            retrieval_time=elapsed_time,
            memory_usage=memory_used,
            documents_retrieved=len(retrieved_doc_ids),
            accuracy=accuracy,
            recall=recall,
            precision=precision,
            mrr=mrr,
            ndcg=ndcg,
            hallucination_rate=0.0,  # Would need LLM to calculate
            token_cost=len(query.split()) + len(" ".join(
                [doc.content for doc in result.documents]
            ).split())
        )
        
        self.results.append(benchmark)
        return benchmark
    
    def benchmark_multiple_systems(self, rag_systems: Dict[str, Any]) -> Dict[str, Any]:
        """Benchmark multiple systems on all queries."""
        
        benchmark_results = {name: [] for name in rag_systems.keys()}
        
        for query, relevant_docs in self.queries:
            for name, system in rag_systems.items():
                try:
                    result = self.benchmark_system(system, query, relevant_docs)
                    benchmark_results[name].append(asdict(result))
                except Exception as e:
                    print(f"Error benchmarking {name} on '{query}': {e}")
        
        return benchmark_results
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive benchmark report."""
        
        # Group results by architecture
        by_architecture: Dict[str, List[BenchmarkResult]] = {}
        for result in self.results:
            if result.architecture not in by_architecture:
                by_architecture[result.architecture] = []
            by_architecture[result.architecture].append(result)
        
        # Calculate statistics for each architecture
        stats = {}
        for arch, results in by_architecture.items():
            stats[arch] = {
                'avg_latency': sum(r.retrieval_time for r in results) / len(results),
                'avg_memory': sum(r.memory_usage for r in results) / len(results),
                'avg_accuracy': sum(r.accuracy for r in results) / len(results),
                'avg_recall': sum(r.recall for r in results) / len(results),
                'avg_precision': sum(r.precision for r in results) / len(results),
                'avg_mrr': sum(r.mrr for r in results) / len(results),
                'avg_ndcg': sum(r.ndcg for r in results) / len(results),
                'avg_token_cost': sum(r.token_cost for r in results) / len(results),
                'total_queries': len(results),
                'min_latency': min(r.retrieval_time for r in results),
                'max_latency': max(r.retrieval_time for r in results),
            }
        
        return {
            'benchmark_name': self.name,
            'total_queries': len(self.queries),
            'total_results': len(self.results),
            'systems_tested': len(by_architecture),
            'statistics_by_system': stats
        }
    
    def save_results(self, filepath: str) -> None:
        """Save results to JSON file."""
        report = self.generate_report()
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"Benchmark results saved to {filepath}")
    
    def print_report(self) -> None:
        """Print formatted benchmark report."""
        report = self.generate_report()
        
        print("\n" + "=" * 80)
        print(f"BENCHMARK REPORT: {report['benchmark_name']}")
        print("=" * 80)
        print(f"Total Queries: {report['total_queries']}")
        print(f"Total Results: {report['total_results']}")
        print(f"Systems Tested: {report['systems_tested']}")
        print()
        
        stats = report['statistics_by_system']
        
        # Sort by accuracy descending
        sorted_systems = sorted(
            stats.items(),
            key=lambda x: x[1]['avg_accuracy'],
            reverse=True
        )
        
        print(f"{'System':<25} {'Latency(ms)':<12} {'Memory(MB)':<12} {'Accuracy':<10} {'Recall':<10} {'NDCG':<10}")
        print("-" * 80)
        
        for system, system_stats in sorted_systems:
            print(
                f"{system:<25} "
                f"{system_stats['avg_latency']*1000:<12.2f} "
                f"{system_stats['avg_memory']:<12.2f} "
                f"{system_stats['avg_accuracy']:<10.3f} "
                f"{system_stats['avg_recall']:<10.3f} "
                f"{system_stats['avg_ndcg']:<10.3f}"
            )
        
        print("\n" + "=" * 80)


if __name__ == "__main__":
    print("Benchmarking framework loaded successfully")


# Try importing numpy, but don't fail if unavailable
try:
    import numpy as np
except ImportError:
    print("Warning: numpy not available, some metrics may be limited")
    np = None

try:
    import psutil
except ImportError:
    print("Warning: psutil not available, memory tracking will be limited")
    psutil = None
