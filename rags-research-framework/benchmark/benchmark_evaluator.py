"""
Comprehensive benchmark evaluation suite for all RAG systems.

This module provides utilities to:
1. Load benchmark datasets and tests
2. Evaluate RAG systems against different test types
3. Calculate metrics (precision, recall, MRR, NDCG, latency, memory, cost)
4. Generate comprehensive reports
5. Compare systems and create scorecards
"""

import json
import time
import psutil
import os
from typing import List, Dict, Tuple, Any
from dataclasses import dataclass
from datetime import datetime


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
    """Calculate evaluation metrics."""
    
    @staticmethod
    def calculate_precision_at_k(retrieved: List[str], relevant: List[str], k: int) -> float:
        """
        Calculate precision@k.
        
        Args:
            retrieved: List of retrieved document IDs
            relevant: List of relevant document IDs
            k: Number of top results to consider
            
        Returns:
            Precision@k value (0.0 to 1.0)
        """
        if k == 0:
            return 0.0
        
        top_k = set(retrieved[:k])
        relevant_set = set(relevant)
        
        if not top_k:
            return 0.0
        
        correct = len(top_k.intersection(relevant_set))
        return correct / min(k, len(top_k))
    
    @staticmethod
    def calculate_recall_at_k(retrieved: List[str], relevant: List[str], k: int) -> float:
        """
        Calculate recall@k.
        
        Args:
            retrieved: List of retrieved document IDs
            relevant: List of relevant document IDs
            k: Number of top results to consider
            
        Returns:
            Recall@k value (0.0 to 1.0)
        """
        if not relevant:
            return 0.0
        
        top_k = set(retrieved[:k])
        relevant_set = set(relevant)
        
        correct = len(top_k.intersection(relevant_set))
        return correct / len(relevant_set)
    
    @staticmethod
    def calculate_mrr(retrieved: List[str], relevant: List[str]) -> float:
        """
        Calculate Mean Reciprocal Rank.
        
        Args:
            retrieved: List of retrieved document IDs
            relevant: List of relevant document IDs
            
        Returns:
            MRR value (0.0 to 1.0)
        """
        relevant_set = set(relevant)
        
        for rank, doc_id in enumerate(retrieved, 1):
            if doc_id in relevant_set:
                return 1.0 / rank
        
        return 0.0
    
    @staticmethod
    def calculate_ndcg_at_k(retrieved: List[str], relevant: List[str], k: int) -> float:
        """
        Calculate Normalized Discounted Cumulative Gain@k.
        
        Args:
            retrieved: List of retrieved document IDs
            relevant: List of relevant document IDs
            k: Number of top results to consider
            
        Returns:
            NDCG@k value (0.0 to 1.0)
        """
        if not relevant or k == 0:
            return 0.0
        
        relevant_set = set(relevant)
        
        # Calculate DCG
        dcg = 0.0
        for rank, doc_id in enumerate(retrieved[:k], 1):
            if doc_id in relevant_set:
                dcg += 1.0 / (1 + log2(rank))
        
        # Calculate Ideal DCG
        ideal_dcg = 0.0
        for rank in range(1, min(len(relevant), k) + 1):
            ideal_dcg += 1.0 / (1 + log2(rank))
        
        if ideal_dcg == 0:
            return 0.0
        
        return dcg / ideal_dcg
    
    @staticmethod
    def calculate_cost(tokens_used: int, model: str = "gpt-3.5-turbo") -> float:
        """
        Calculate estimated cost based on tokens.
        
        Args:
            tokens_used: Number of tokens consumed
            model: Model name for pricing lookup
            
        Returns:
            Estimated cost in USD
        """
        # GPT-3.5-turbo pricing: $0.002 per 1K tokens (approx)
        pricing = {
            "gpt-3.5-turbo": 0.002 / 1000,
            "gpt-4": 0.03 / 1000,
            "claude": 0.008 / 1000,
        }
        
        rate = pricing.get(model, 0.002 / 1000)
        return tokens_used * rate


def log2(x: float) -> float:
    """Calculate log base 2."""
    return __import__('math').log2(x)


class BenchmarkEvaluator:
    """Main benchmark evaluation orchestrator."""
    
    def __init__(self, results_dir: str = "benchmark/results"):
        """Initialize evaluator."""
        self.results_dir = results_dir
        self.metrics: List[EvaluationMetrics] = []
        self.loader = BenchmarkLoader()
        self.calculator = MetricsCalculator()
        
        if not os.path.exists(results_dir):
            os.makedirs(results_dir)
    
    def evaluate_retrieval(
        self,
        system_name: str,
        test_type: str,
        test_id: int,
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
            test_type: Type of test (exact, semantic, etc.)
            test_id: Test ID
            query: Query string
            retrieved_docs: List of retrieved document IDs
            relevant_docs: List of relevant document IDs
            retrieval_time_ms: Retrieval time in milliseconds
            tokens_used: Number of tokens consumed
            
        Returns:
            EvaluationMetrics object
        """
        metrics = EvaluationMetrics(
            system_name=system_name,
            test_type=test_type,
            test_id=test_id,
            query=query
        )
        
        # Calculate retrieval metrics
        metrics.precision_at_1 = self.calculator.calculate_precision_at_k(retrieved_docs, relevant_docs, 1)
        metrics.precision_at_5 = self.calculator.calculate_precision_at_k(retrieved_docs, relevant_docs, 5)
        metrics.recall_at_5 = self.calculator.calculate_recall_at_k(retrieved_docs, relevant_docs, 5)
        metrics.mrr = self.calculator.calculate_mrr(retrieved_docs, relevant_docs)
        metrics.ndcg_at_5 = self.calculator.calculate_ndcg_at_k(retrieved_docs, relevant_docs, 5)
        
        # Set performance metrics
        metrics.retrieval_time_ms = retrieval_time_ms
        metrics.tokens_used = tokens_used
        metrics.estimated_cost_usd = self.calculator.calculate_cost(tokens_used)
        
        # Memory usage (estimate based on system)
        try:
            process = psutil.Process(os.getpid())
            metrics.memory_used_mb = process.memory_info().rss / 1024 / 1024
            metrics.cpu_percent = process.cpu_percent(interval=0.1)
        except:
            metrics.memory_used_mb = 0.0
            metrics.cpu_percent = 0.0
        
        self.metrics.append(metrics)
        return metrics
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive benchmark report."""
        if not self.metrics:
            return {"error": "No metrics recorded"}
        
        # Group by system
        by_system = {}
        for metric in self.metrics:
            if metric.system_name not in by_system:
                by_system[metric.system_name] = []
            by_system[metric.system_name].append(metric)
        
        # Calculate aggregates
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(self.metrics),
            "systems": {}
        }
        
        for system_name, system_metrics in by_system.items():
            avg_precision_1 = sum(m.precision_at_1 for m in system_metrics) / len(system_metrics)
            avg_precision_5 = sum(m.precision_at_5 for m in system_metrics) / len(system_metrics)
            avg_recall_5 = sum(m.recall_at_5 for m in system_metrics) / len(system_metrics)
            avg_mrr = sum(m.mrr for m in system_metrics) / len(system_metrics)
            avg_ndcg = sum(m.ndcg_at_5 for m in system_metrics) / len(system_metrics)
            
            avg_latency = sum(m.retrieval_time_ms for m in system_metrics) / len(system_metrics)
            max_latency = max(m.retrieval_time_ms for m in system_metrics)
            min_latency = min(m.retrieval_time_ms for m in system_metrics)
            
            avg_memory = sum(m.memory_used_mb for m in system_metrics) / len(system_metrics)
            total_cost = sum(m.estimated_cost_usd for m in system_metrics)
            
            # Calculate combined score
            score = (
                0.2 * avg_precision_1 +
                0.2 * avg_precision_5 +
                0.2 * avg_recall_5 +
                0.2 * avg_mrr +
                0.1 * min(1.0, avg_latency / 100) +  # Normalize latency
                0.1 * min(1.0, avg_memory / 1000)     # Normalize memory
            )
            
            report["systems"][system_name] = {
                "tests_run": len(system_metrics),
                "accuracy": {
                    "precision_at_1": round(avg_precision_1, 4),
                    "precision_at_5": round(avg_precision_5, 4),
                    "recall_at_5": round(avg_recall_5, 4),
                    "mrr": round(avg_mrr, 4),
                    "ndcg_at_5": round(avg_ndcg, 4)
                },
                "performance": {
                    "avg_latency_ms": round(avg_latency, 2),
                    "min_latency_ms": round(min_latency, 2),
                    "max_latency_ms": round(max_latency, 2),
                    "avg_memory_mb": round(avg_memory, 2)
                },
                "cost": {
                    "total_cost_usd": round(total_cost, 6),
                    "avg_cost_per_query": round(total_cost / len(system_metrics), 6)
                },
                "combined_score": round(score, 4)
            }
        
        # Rank systems
        ranked = sorted(
            report["systems"].items(),
            key=lambda x: x[1]["combined_score"],
            reverse=True
        )
        
        report["ranking"] = [
            {"rank": i+1, "system": name, "score": data["combined_score"]}
            for i, (name, data) in enumerate(ranked)
        ]
        
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
        """Print formatted report."""
        report = self.generate_report()
        
        print("\n" + "="*80)
        print("BENCHMARK REPORT")
        print("="*80)
        print(f"Timestamp: {report['timestamp']}")
        print(f"Total Tests: {report['total_tests']}\n")
        
        print("RANKING:")
        print("-" * 80)
        for rank_info in report.get("ranking", []):
            print(f"{rank_info['rank']}. {rank_info['system']}: {rank_info['score']:.4f}")
        
        print("\nDETAILED METRICS:")
        print("-" * 80)
        
        for system_name, metrics in report["systems"].items():
            print(f"\n{system_name}:")
            print(f"  Tests Run: {metrics['tests_run']}")
            print(f"  Accuracy:")
            print(f"    Precision@1: {metrics['accuracy']['precision_at_1']:.4f}")
            print(f"    Precision@5: {metrics['accuracy']['precision_at_5']:.4f}")
            print(f"    Recall@5: {metrics['accuracy']['recall_at_5']:.4f}")
            print(f"    MRR: {metrics['accuracy']['mrr']:.4f}")
            print(f"    NDCG@5: {metrics['accuracy']['ndcg_at_5']:.4f}")
            print(f"  Performance:")
            print(f"    Avg Latency: {metrics['performance']['avg_latency_ms']:.2f}ms")
            print(f"    Latency Range: {metrics['performance']['min_latency_ms']:.2f}ms - {metrics['performance']['max_latency_ms']:.2f}ms")
            print(f"    Avg Memory: {metrics['performance']['avg_memory_mb']:.2f}MB")
            print(f"  Cost:")
            print(f"    Total Cost: ${metrics['cost']['total_cost_usd']:.6f}")
            print(f"    Avg per Query: ${metrics['cost']['avg_cost_per_query']:.6f}")
            print(f"  Combined Score: {metrics['combined_score']:.4f}")
        
        print("\n" + "="*80)


if __name__ == "__main__":
    # Example usage
    evaluator = BenchmarkEvaluator()
    
    # Load benchmark data
    papers = BenchmarkLoader.load_papers()
    exact_tests = BenchmarkLoader.load_test_suite("exact_lookup")
    
    print(f"Loaded {len(papers)} papers")
    print(f"Loaded {len(exact_tests)} exact lookup tests")
    print("\nBenchmark infrastructure ready!")
