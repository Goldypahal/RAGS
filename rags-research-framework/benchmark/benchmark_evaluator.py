"""
Comprehensive benchmark evaluation suite for all RAG systems.

This module provides utilities to:
1. Load benchmark datasets and tests
2. Evaluate RAG systems against different test types
3. Calculate metrics (precision, recall, MRR, NDCG, latency, memory, cost)
4. Generate comprehensive reports
5. Compare systems and create scorecards
"""

import sys
import os
import io
import json
import time
import psutil
from typing import List, Dict, Tuple, Any
from dataclasses import dataclass
from datetime import datetime

# Ensure UTF-8 output on Windows consoles
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass


@dataclass
class EvaluationMetrics:
    """Stores evaluation metrics for a single test."""
    system_name: str
    test_type: str
    test_id: int
    query: str
    
    # Retrieval metrics
    precision_at_1: float = 0.0
    precision_at_5: float = 0.0
    recall_at_5: float = 0.0
    mrr: float = 0.0  # Mean Reciprocal Rank
    ndcg_at_5: float = 0.0  # Normalized Discounted Cumulative Gain
    
    # Performance metrics
    retrieval_time_ms: float = 0.0
    memory_used_mb: float = 0.0
    cpu_percent: float = 0.0
    
    # Cost metrics
    tokens_used: int = 0
    estimated_cost_usd: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            'system': self.system_name,
            'test_type': self.test_type,
            'test_id': self.test_id,
            'query': self.query,
            'precision_at_1': self.precision_at_1,
            'precision_at_5': self.precision_at_5,
            'recall_at_5': self.recall_at_5,
            'mrr': self.mrr,
            'ndcg_at_5': self.ndcg_at_5,
            'retrieval_time_ms': self.retrieval_time_ms,
            'memory_used_mb': self.memory_used_mb,
            'cpu_percent': self.cpu_percent,
            'tokens_used': self.tokens_used,
            'estimated_cost_usd': self.estimated_cost_usd
        }


class BenchmarkLoader:
    """Load benchmark datasets and tests."""
    
    @staticmethod
    def load_papers(dataset_dir: str = "benchmark/dataset") -> List[Dict[str, Any]]:
        """Load papers dataset."""
        path = os.path.join(dataset_dir, "papers.json")
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @staticmethod
    def load_authors(dataset_dir: str = "benchmark/dataset") -> List[Dict[str, Any]]:
        """Load authors dataset."""
        path = os.path.join(dataset_dir, "authors.json")
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @staticmethod
    def load_topics(dataset_dir: str = "benchmark/dataset") -> List[Dict[str, Any]]:
        """Load topics dataset."""
        path = os.path.join(dataset_dir, "topics.json")
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @staticmethod
    def load_citations(dataset_dir: str = "benchmark/dataset") -> List[Dict[str, Any]]:
        """Load citations dataset."""
        path = os.path.join(dataset_dir, "citations.json")
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @staticmethod
    def load_test_suite(test_name: str, test_dir: str = "benchmark/tests") -> List[Dict[str, Any]]:
        """Load specific test suite."""
        path = os.path.join(test_dir, f"{test_name}.json")
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)


class MetricsCalculator:
    """Calculate standard information retrieval evaluation metrics."""
    
    @staticmethod
    def calculate_precision_at_k(retrieved: List[str], relevant: List[str], k: int) -> float:
        """
        Calculate standard Precision@k: (number of relevant items in top-k) / k.
        
        Args:
            retrieved: List of retrieved document IDs (ordered)
            relevant: List of relevant document IDs
            k: Cutoff rank
            
        Returns:
            Precision@k value (0.0 to 1.0)
        """
        if k <= 0:
            return 0.0
        
        relevant_set = set(relevant)
        # Deduplicate while preserving first-seen ranking order
        seen = set()
        top_k = []
        for doc_id in retrieved:
            if doc_id not in seen:
                seen.add(doc_id)
                top_k.append(doc_id)
            if len(top_k) == k:
                break
                
        if not top_k:
            return 0.0
            
        correct = sum(1 for doc_id in top_k if doc_id in relevant_set)
        return correct / k
    
    @staticmethod
    def calculate_recall_at_k(retrieved: List[str], relevant: List[str], k: int) -> float:
        """
        Calculate Recall@k: (number of relevant items in top-k) / (total relevant items).
        
        Args:
            retrieved: List of retrieved document IDs (ordered)
            relevant: List of relevant document IDs
            k: Cutoff rank
            
        Returns:
            Recall@k value (0.0 to 1.0)
        """
        if not relevant or k <= 0:
            return 0.0
            
        relevant_set = set(relevant)
        seen = set()
        top_k = []
        for doc_id in retrieved:
            if doc_id not in seen:
                seen.add(doc_id)
                top_k.append(doc_id)
            if len(top_k) == k:
                break
                
        correct = sum(1 for doc_id in top_k if doc_id in relevant_set)
        return correct / len(relevant_set)
    
    @staticmethod
    def calculate_mrr(retrieved: List[str], relevant: List[str]) -> float:
        """
        Calculate Mean Reciprocal Rank (MRR) based on first relevant document rank.
        
        Args:
            retrieved: List of retrieved document IDs (ordered)
            relevant: List of relevant document IDs
            
        Returns:
            Reciprocal rank (1/rank) or 0.0 if no relevant items found
        """
        if not relevant:
            return 0.0
            
        relevant_set = set(relevant)
        seen = set()
        rank = 1
        for doc_id in retrieved:
            if doc_id in seen:
                continue
            seen.add(doc_id)
            if doc_id in relevant_set:
                return 1.0 / rank
            rank += 1
            
        return 0.0
    
    @staticmethod
    def calculate_ndcg_at_k(retrieved: List[str], relevant: List[str], k: int) -> float:
        """
        Calculate Normalized Discounted Cumulative Gain@k (NDCG@k).
        
        Args:
            retrieved: List of retrieved document IDs (ordered)
            relevant: List of relevant document IDs
            k: Cutoff rank
            
        Returns:
            NDCG@k value (0.0 to 1.0)
        """
        import math
        if not relevant or k <= 0:
            return 0.0
            
        relevant_set = set(relevant)
        seen = set()
        top_k = []
        for doc_id in retrieved:
            if doc_id not in seen:
                seen.add(doc_id)
                top_k.append(doc_id)
            if len(top_k) == k:
                break
                
        # Calculate DCG: sum of 1 / log2(rank + 1) for relevant docs
        dcg = 0.0
        for rank, doc_id in enumerate(top_k, 1):
            if doc_id in relevant_set:
                dcg += 1.0 / math.log2(rank + 1)
                
        # Calculate Ideal DCG (IDCG)
        ideal_dcg = sum(1.0 / math.log2(r + 1) for r in range(1, min(len(relevant_set), k) + 1))
        
        if ideal_dcg == 0:
            return 0.0
            
        return dcg / ideal_dcg


class BenchmarkEvaluator:
    """Main benchmark evaluation orchestrator with rigorous statistical tracking."""
    
    def __init__(self, results_dir: str = "benchmark/results"):
        """Initialize evaluator."""
        self.results_dir = results_dir
        self.metrics: List[EvaluationMetrics] = []
        self.loader = BenchmarkLoader()
        self.calculator = MetricsCalculator()
        self.system_build_stats: Dict[str, Dict[str, float]] = {}
        
        if not os.path.exists(results_dir):
            os.makedirs(results_dir)
            
    def record_build_stats(self, system_name: str, build_time_ms: float, index_memory_mb: float):
        """Record decoupled index construction statistics."""
        self.system_build_stats[system_name] = {
            "build_time_ms": round(build_time_ms, 2),
            "index_memory_mb": round(index_memory_mb, 2)
        }
    
    def evaluate_retrieval(
        self,
        system_name: str,
        test_type: str,
        test_id: Any,
        query: str,
        retrieved_docs: List[str],
        relevant_docs: List[str],
        retrieval_time_ms: float,
        tokens_used: int = 0
    ) -> EvaluationMetrics:
        """
        Evaluate a single retrieval result.
        
        Args:
            system_name: Name of RAG system
            test_type: Type of test (exact, semantic, multi_hop, etc.)
            test_id: Test identifier
            query: Query string
            retrieved_docs: Ordered list of retrieved document IDs
            relevant_docs: List of ground-truth relevant document IDs
            retrieval_time_ms: High-resolution retrieval time in milliseconds
            tokens_used: Synthetic proxy of query + context words
            
        Returns:
            EvaluationMetrics object
        """
        metrics = EvaluationMetrics(
            system_name=system_name,
            test_type=test_type,
            test_id=test_id if isinstance(test_id, int) else hash(str(test_id)) % 100000,
            query=query
        )
        
        # Calculate standard IR retrieval metrics
        metrics.precision_at_1 = self.calculator.calculate_precision_at_k(retrieved_docs, relevant_docs, 1)
        metrics.precision_at_5 = self.calculator.calculate_precision_at_k(retrieved_docs, relevant_docs, 5)
        metrics.recall_at_5 = self.calculator.calculate_recall_at_k(retrieved_docs, relevant_docs, 5)
        metrics.mrr = self.calculator.calculate_mrr(retrieved_docs, relevant_docs)
        metrics.ndcg_at_5 = self.calculator.calculate_ndcg_at_k(retrieved_docs, relevant_docs, 5)
        
        # Performance metrics
        metrics.retrieval_time_ms = retrieval_time_ms
        metrics.tokens_used = tokens_used
        metrics.estimated_cost_usd = 0.0  # Decoupled: retrieval benchmark does not make LLM calls
        
        self.metrics.append(metrics)
        return metrics
    
    def generate_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive, publication-grade benchmark report.
        Reports Accuracy, Latency distribution (p50, p95, p99, std),
        Decoupled Index Build metrics, and a mathematically sound composite utility.
        """
        import numpy as np
        
        if not self.metrics:
            return {"error": "No metrics recorded"}
        
        # Group metrics by system
        by_system = {}
        for metric in self.metrics:
            if metric.system_name not in by_system:
                by_system[metric.system_name] = []
            by_system[metric.system_name].append(metric)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(self.metrics),
            "systems": {}
        }
        
        for system_name, system_metrics in by_system.items():
            n = len(system_metrics)
            avg_precision_1 = sum(m.precision_at_1 for m in system_metrics) / n
            avg_precision_5 = sum(m.precision_at_5 for m in system_metrics) / n
            avg_recall_5 = sum(m.recall_at_5 for m in system_metrics) / n
            avg_mrr = sum(m.mrr for m in system_metrics) / n
            avg_ndcg = sum(m.ndcg_at_5 for m in system_metrics) / n
            
            # Latency statistics across all query runs
            latencies = [m.retrieval_time_ms for m in system_metrics]
            avg_latency = float(np.mean(latencies))
            p50_latency = float(np.percentile(latencies, 50))
            p95_latency = float(np.percentile(latencies, 95))
            p99_latency = float(np.percentile(latencies, 99))
            std_latency = float(np.std(latencies))
            min_latency = float(np.min(latencies))
            max_latency = float(np.max(latencies))
            
            # Index construction stats
            build_stats = self.system_build_stats.get(system_name, {
                "build_time_ms": 0.0,
                "index_memory_mb": 0.0
            })
            
            # Pure retrieval quality score (mean of standard metrics)
            retrieval_quality = (avg_precision_1 + avg_precision_5 + avg_recall_5 + avg_mrr + avg_ndcg) / 5.0
            
            # Mathematically sound efficiency scaling (penalty for latency and memory)
            # Higher latency -> smaller factor, bounded in (0, 1]
            latency_scale_ms = 10.0   # 10ms reference scale
            memory_scale_mb = 50.0    # 50MB reference scale
            latency_efficiency = 1.0 / (1.0 + avg_latency / latency_scale_ms)
            memory_efficiency = 1.0 / (1.0 + build_stats["index_memory_mb"] / memory_scale_mb)
            
            # Composite utility (secondary metric): Quality (70%) + Latency Efficiency (20%) + Memory (10%)
            composite_utility = (
                0.70 * retrieval_quality +
                0.20 * latency_efficiency +
                0.10 * memory_efficiency
            )
            
            report["systems"][system_name] = {
                "tests_run": n,
                "accuracy": {
                    "precision_at_1": round(avg_precision_1, 4),
                    "precision_at_5": round(avg_precision_5, 4),
                    "recall_at_5": round(avg_recall_5, 4),
                    "mrr": round(avg_mrr, 4),
                    "ndcg_at_5": round(avg_ndcg, 4),
                    "mean_quality": round(retrieval_quality, 4)
                },
                "latency_profile_ms": {
                    "mean": round(avg_latency, 3),
                    "p50": round(p50_latency, 3),
                    "p95": round(p95_latency, 3),
                    "p99": round(p99_latency, 3),
                    "std_dev": round(std_latency, 3),
                    "min": round(min_latency, 3),
                    "max": round(max_latency, 3)
                },
                "index_construction": {
                    "build_time_ms": build_stats["build_time_ms"],
                    "index_memory_mb": build_stats["index_memory_mb"]
                },
                "composite_utility": round(composite_utility, 4),
                # Backward-compatibility alias
                "combined_score": round(composite_utility, 4)
            }
        
        # Rankings: Rank primarily by Retrieval Quality, secondary by Composite Utility
        ranked_by_quality = sorted(
            report["systems"].items(),
            key=lambda x: x[1]["accuracy"]["mean_quality"],
            reverse=True
        )
        ranked_by_utility = sorted(
            report["systems"].items(),
            key=lambda x: x[1]["composite_utility"],
            reverse=True
        )
        
        report["ranking_by_quality"] = [
            {"rank": i+1, "system": name, "quality": data["accuracy"]["mean_quality"]}
            for i, (name, data) in enumerate(ranked_by_quality)
        ]
        report["ranking_by_utility"] = [
            {"rank": i+1, "system": name, "utility": data["composite_utility"]}
            for i, (name, data) in enumerate(ranked_by_utility)
        ]
        report["ranking"] = report["ranking_by_utility"]
        
        return report
    
    def save_results(self, filename: str = None):
        """Save results to JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"benchmark_results_{timestamp}.json"
        
        filepath = os.path.join(self.results_dir, filename)
        
        report = self.generate_report()
        report["metrics"] = [m.to_dict() for m in self.metrics]
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Results saved to: {filepath}")
        return filepath
    
    def print_report(self):
        """Print formatted publication-grade report with decoupled dimensions."""
        report = self.generate_report()
        
        print("\n" + "="*85)
        print("📊 RIGOROUS RETRIEVAL BENCHMARK REPORT")
        print("="*85)
        print(f"Timestamp: {report['timestamp']}")
        print(f"Total Tests Run: {report['total_tests']}\n")
        
        print("🏆 RANKINGS BY RETRIEVAL QUALITY (Primary Scientific Metric):")
        print("-" * 85)
        print(f"{'Rank':<5} {'System':<28} {'Mean Quality':<15} {'P@5':<10} {'MRR':<10} {'NDCG@5':<10}")
        print("-" * 85)
        for rank_info in report.get("ranking_by_quality", []):
            name = rank_info["system"]
            acc = report["systems"][name]["accuracy"]
            print(f"{rank_info['rank']:<5} {name:<28} {acc['mean_quality']:<15.4f} {acc['precision_at_5']:<10.4f} {acc['mrr']:<10.4f} {acc['ndcg_at_5']:<10.4f}")
            
        print("\n⚡ LATENCY PROFILE & INDEX CONSTRUCTION (Decoupled Performance):")
        print("-" * 85)
        print(f"{'System':<28} {'p50 (ms)':<10} {'p95 (ms)':<10} {'p99 (ms)':<10} {'Mean (ms)':<10} {'Std (ms)':<10} {'Build (ms)':<12} {'RAM (MB)':<10}")
        print("-" * 85)
        for name, metrics in report["systems"].items():
            lat = metrics["latency_profile_ms"]
            idx = metrics["index_construction"]
            print(f"{name:<28} {lat['p50']:<10.2f} {lat['p95']:<10.2f} {lat['p99']:<10.2f} {lat['mean']:<10.2f} {lat['std_dev']:<10.2f} {idx['build_time_ms']:<12.1f} {idx['index_memory_mb']:<10.1f}")
            
        print("\n🎯 COMPOSITE EFFICIENCY UTILITY (Secondary Bounded Score):")
        print("-" * 85)
        for rank_info in report.get("ranking_by_utility", []):
            name = rank_info["system"]
            print(f"{rank_info['rank']}. {name:<28} Utility: {rank_info['utility']:.4f}")
        
        print("\n" + "="*85)


if __name__ == "__main__":
    # Example usage
    evaluator = BenchmarkEvaluator()
    
    # Load benchmark data
    papers = BenchmarkLoader.load_papers()
    exact_tests = BenchmarkLoader.load_test_suite("exact_lookup")
    
    print(f"Loaded {len(papers)} papers")
    print(f"Loaded {len(exact_tests)} exact lookup tests")
    print("\nBenchmark infrastructure ready!")
