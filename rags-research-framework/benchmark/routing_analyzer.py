"""
Routing Analyzer: Scientific evaluation of query-adaptive retrieval.

Implements:
1. Oracle Router (theoretical upper-bound retrieval performance)
2. Adaptive Router (learned/heuristic query-directed routing)
3. Fixed Retriever Baselines (VectorRAG, InvertedIndexGraphRAG, etc.)
4. Random Router (null hypothesis baseline)
5. Routing Regret: Regret(q) = Oracle(q) - Chosen(q) for Quality and Latency
6. Architecture x Query-Type Performance Matrix
7. Statistical Significance Testing (95% Confidence Intervals, Paired t-tests)
"""

import math
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class QueryRoutingRecord:
    """Detailed routing evaluation record for a single query."""
    query_id: Any
    query: str
    query_type: str
    oracle_system: str
    oracle_quality: float
    oracle_latency_ms: float
    adaptive_chosen_system: str
    adaptive_quality: float
    adaptive_latency_ms: float
    vector_quality: float
    vector_latency_ms: float
    best_fixed_quality: float
    random_quality: float
    quality_regret: float
    latency_regret_ms: float
    system_scores: Dict[str, float] = field(default_factory=dict)
    system_latencies: Dict[str, float] = field(default_factory=dict)


class RoutingAnalyzer:
    """Evaluates routing efficacy and computes regret metrics."""
    
    def __init__(self):
        self.records: List[QueryRoutingRecord] = []
        
    def add_query_evaluation(
        self,
        query_id: Any,
        query: str,
        query_type: str,
        system_qualities: Dict[str, float],
        system_latencies: Dict[str, float],
        adaptive_chosen_system: str
    ) -> QueryRoutingRecord:
        """
        Record and analyze a single query across all systems.
        """
        # Determine Oracle (system with highest retrieval quality)
        best_sys = max(system_qualities.keys(), key=lambda s: system_qualities[s])
        oracle_quality = system_qualities[best_sys]
        oracle_latency = system_latencies.get(best_sys, 0.0)
        
        # Adaptive performance
        # If adaptive itself is evaluated, look up its score; otherwise use chosen system's score
        adaptive_quality = system_qualities.get(adaptive_chosen_system, 0.0)
        adaptive_latency = system_latencies.get(adaptive_chosen_system, 0.0)
        
        # Baselines
        vector_quality = system_qualities.get("VectorRAG", 0.0)
        vector_latency = system_latencies.get("VectorRAG", 0.0)
        
        # Random baseline: expected mean across all candidate systems
        random_quality = float(np.mean(list(system_qualities.values())))
        
        # Regret calculations
        quality_regret = max(0.0, oracle_quality - adaptive_quality)
        latency_regret = adaptive_latency - oracle_latency
        
        record = QueryRoutingRecord(
            query_id=query_id,
            query=query,
            query_type=query_type,
            oracle_system=best_sys,
            oracle_quality=round(oracle_quality, 4),
            oracle_latency_ms=round(oracle_latency, 3),
            adaptive_chosen_system=adaptive_chosen_system,
            adaptive_quality=round(adaptive_quality, 4),
            adaptive_latency_ms=round(adaptive_latency, 3),
            vector_quality=round(vector_quality, 4),
            vector_latency_ms=round(vector_latency, 3),
            best_fixed_quality=0.0,  # Computed at aggregate level
            random_quality=round(random_quality, 4),
            quality_regret=round(quality_regret, 4),
            latency_regret_ms=round(latency_regret, 3),
            system_scores=system_qualities,
            system_latencies=system_latencies
        )
        self.records.append(record)
        return record

    def compute_summary(self) -> Dict[str, Any]:
        """Compute aggregate routing evaluation metrics and statistical analysis."""
        if not self.records:
            return {"error": "No routing records available"}
            
        n = len(self.records)
        oracle_qualities = [r.oracle_quality for r in self.records]
        adaptive_qualities = [r.adaptive_quality for r in self.records]
        vector_qualities = [r.vector_quality for r in self.records]
        random_qualities = [r.random_quality for r in self.records]
        regrets = [r.quality_regret for r in self.records]
        
        # Determine best fixed single architecture across entire dataset
        system_names = list(self.records[0].system_scores.keys())
        fixed_means = {}
        for sys in system_names:
            fixed_means[sys] = float(np.mean([r.system_scores.get(sys, 0.0) for r in self.records]))
        best_fixed_sys = max(fixed_means.keys(), key=lambda s: fixed_means[s])
        best_fixed_mean = fixed_means[best_fixed_sys]
        
        # Routing Accuracy: percentage of times Adaptive chose the Oracle best system
        correct_routes = sum(1 for r in self.records if r.adaptive_chosen_system == r.oracle_system)
        routing_accuracy = correct_routes / n
        
        # Means & Standard Deviations
        mean_oracle = float(np.mean(oracle_qualities))
        mean_adaptive = float(np.mean(adaptive_qualities))
        mean_vector = float(np.mean(vector_qualities))
        mean_random = float(np.mean(random_qualities))
        mean_regret = float(np.mean(regrets))
        std_regret = float(np.std(regrets))
        
        # 95% Confidence Intervals: 1.96 * std / sqrt(n)
        ci_adaptive = 1.96 * float(np.std(adaptive_qualities)) / math.sqrt(n)
        ci_vector = 1.96 * float(np.std(vector_qualities)) / math.sqrt(n)
        ci_oracle = 1.96 * float(np.std(oracle_qualities)) / math.sqrt(n)
        
        # Paired t-test: Adaptive vs VectorBaseline
        diffs = np.array(adaptive_qualities) - np.array(vector_qualities)
        t_stat = float(np.mean(diffs) / (np.std(diffs, ddof=1) / math.sqrt(n))) if np.std(diffs, ddof=1) > 0 else 0.0
        
        # Architecture x Query-Type Matrix
        categories = sorted(list(set(r.query_type for r in self.records)))
        matrix = {sys: {} for sys in system_names}
        category_counts = {cat: 0 for cat in categories}
        
        for cat in categories:
            cat_records = [r for r in self.records if r.query_type == cat]
            category_counts[cat] = len(cat_records)
            for sys in system_names:
                scores = [r.system_scores.get(sys, 0.0) for r in cat_records]
                matrix[sys][cat] = round(float(np.mean(scores)), 4) if scores else 0.0
                
        # Overall column in matrix
        for sys in system_names:
            matrix[sys]["OVERALL"] = round(fixed_means[sys], 4)
            
        return {
            "total_queries_evaluated": n,
            "router_comparison": {
                "oracle_router": {
                    "mean_quality": round(mean_oracle, 4),
                    "ci_95": round(ci_oracle, 4)
                },
                "adaptive_router": {
                    "mean_quality": round(mean_adaptive, 4),
                    "ci_95": round(ci_adaptive, 4),
                    "oracle_gap_ratio": round(mean_adaptive / mean_oracle, 4) if mean_oracle > 0 else 0.0
                },
                "best_fixed_architecture": {
                    "system": best_fixed_sys,
                    "mean_quality": round(best_fixed_mean, 4)
                },
                "vector_baseline": {
                    "mean_quality": round(mean_vector, 4),
                    "ci_95": round(ci_vector, 4)
                },
                "random_router": {
                    "mean_quality": round(mean_random, 4)
                }
            },
            "routing_regret_analysis": {
                "mean_quality_regret": round(mean_regret, 4),
                "std_quality_regret": round(std_regret, 4),
                "routing_accuracy": round(routing_accuracy, 4),
                "paired_t_statistic_vs_vector": round(t_stat, 3)
            },
            "category_counts": category_counts,
            "architecture_by_query_type_matrix": matrix
        }
        
    def print_summary(self):
        """Print formatted scientific table of routing results."""
        summary = self.compute_summary()
        if "error" in summary:
            print(summary["error"])
            return
            
        comp = summary["router_comparison"]
        regret = summary["routing_regret_analysis"]
        matrix = summary["architecture_by_query_type_matrix"]
        
        print("\n" + "=" * 90)
        print("🧠 SCIENTIFIC ROUTING EVALUATION (THE ORACLE & REGRET EXPERIMENT)")
        print("=" * 90)
        print(f"Total Queries Evaluated: {summary['total_queries_evaluated']}\n")
        
        print("🏆 ROUTER COMPETITIVE ANALYSIS:")
        print("-" * 90)
        print(f"{'Router Model':<28} {'Mean Quality (0-1)':<20} {'95% Conf. Interval':<20} {'% of Oracle':<15}")
        print("-" * 90)
        print(f"{'Oracle Router (Upper Bound)':<28} {comp['oracle_router']['mean_quality']:<20.4f} ±{comp['oracle_router']['ci_95']:<19.4f} 100.0%")
        print(f"{'Adaptive Router (Structure)':<28} {comp['adaptive_router']['mean_quality']:<20.4f} ±{comp['adaptive_router']['ci_95']:<19.4f} {comp['adaptive_router']['oracle_gap_ratio']*100:.1f}%")
        print(f"{'Best Fixed Architecture':<28} {comp['best_fixed_architecture']['mean_quality']:<20.4f} ({comp['best_fixed_architecture']['system']})")
        print(f"{'VectorRAG Baseline':<28} {comp['vector_baseline']['mean_quality']:<20.4f} ±{comp['vector_baseline']['ci_95']:<19.4f}")
        print(f"{'Random Router (Null Baseline)':<28} {comp['random_router']['mean_quality']:<20.4f}")
        
        print("\n📉 ROUTING REGRET & ACCURACY:")
        print("-" * 90)
        print(f"  • Mean Quality Regret:       {regret['mean_quality_regret']:.4f} (Avg quality loss when chosen ≠ oracle)")
        print(f"  • Routing Accuracy:          {regret['routing_accuracy']*100:.1f}% of queries matched the Oracle optimal engine")
        print(f"  • Paired t-test vs. Vector:  t = {regret['paired_t_statistic_vs_vector']:.3f}")
        
        print("\n📊 ARCHITECTURE × QUERY-TYPE PERFORMANCE MATRIX:")
        print("-" * 90)
        categories = sorted(list(summary["category_counts"].keys()))
        header = f"{'System':<24} " + " ".join(f"{cat[:8]:>9}" for cat in categories) + f" {'OVERALL':>9}"
        print(header)
        print("-" * 90)
        
        for sys_name in sorted(matrix.keys()):
            row = f"{sys_name:<24} "
            for cat in categories:
                row += f"{matrix[sys_name].get(cat, 0.0):>9.3f} "
            row += f"{matrix[sys_name].get('OVERALL', 0.0):>9.3f}"
            print(row)
            
        print("=" * 90 + "\n")
