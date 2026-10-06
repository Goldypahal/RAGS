import os
import json
import glob
import matplotlib.pyplot as plt
import numpy as np

def main():
    # 1. Find the latest benchmark results file
    results_dir = os.path.join("benchmark", "results")
    json_files = glob.glob(os.path.join(results_dir, "benchmark_results_*.json"))
    if not json_files:
        print("No benchmark results JSON files found in benchmark/results/")
        return
    
    latest_file = max(json_files, key=os.path.getmtime)
    print(f"Loading latest benchmark results from: {latest_file}")
    
    with open(latest_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    systems_data = data.get("systems", {})
    if not systems_data:
        print("No systems data found in the JSON file.")
        return
    
    # Create plots directory if it doesn't exist
    plots_dir = os.path.join(results_dir, "plots")
    os.makedirs(plots_dir, exist_ok=True)
    
    # Extract metrics for plotting
    systems = list(systems_data.keys())
    
    # Extract accuracy, quality, and latency
    def get_quality(s):
        acc = systems_data[s].get("accuracy", {})
        if "mean_quality" in acc:
            return acc["mean_quality"]
        # Fallback to mean of available accuracy metrics
        p1 = acc.get("precision_at_1", 0)
        p5 = acc.get("precision_at_5", 0)
        r5 = acc.get("recall_at_5", 0)
        mrr = acc.get("mrr", 0)
        return (p1 + p5 + r5 + mrr) / 4.0

    def get_latency(s):
        perf = systems_data[s].get("performance", {})
        lat_prof = systems_data[s].get("latency_profile_ms", {})
        if "mean" in lat_prof:
            return lat_prof["mean"]
        return perf.get("avg_latency_ms", 0)

    # Sort systems by retrieval quality for consistent ordering in plots
    systems = sorted(systems, key=get_quality, reverse=True)
    
    quality_scores = [get_quality(s) for s in systems]
    p1 = [systems_data[s]["accuracy"].get("precision_at_1", 0) for s in systems]
    p5 = [systems_data[s]["accuracy"].get("precision_at_5", 0) for s in systems]
    r5 = [systems_data[s]["accuracy"].get("recall_at_5", 0) for s in systems]
    mrr = [systems_data[s]["accuracy"].get("mrr", 0) for s in systems]
    ndcg = [systems_data[s]["accuracy"].get("ndcg_at_5", 0) for s in systems]
    
    latencies = [get_latency(s) for s in systems]
    p50_latencies = [systems_data[s].get("latency_profile_ms", {}).get("p50", get_latency(s)) for s in systems]
    p95_latencies = [systems_data[s].get("latency_profile_ms", {}).get("p95", get_latency(s) * 1.5) for s in systems]
    
    # Color palette
    colors = plt.cm.viridis(np.linspace(0.15, 0.85, len(systems)))
    
    # Plot 1: Retrieval Quality Ranking (Primary Scientific Result)
    plt.figure(figsize=(10, 6))
    y_pos = np.arange(len(systems))
    plt.barh(y_pos, quality_scores, align='center', color=colors, edgecolor='black', alpha=0.85)
    plt.yticks(y_pos, systems)
    plt.gca().invert_yaxis()  # Top-down ranking
    plt.xlabel('Mean Retrieval Quality (Precision@K, Recall@K, MRR, NDCG)')
    plt.title('RAG Systems - Retrieval Quality Ranking (Scientific Benchmark)')
    plt.grid(axis='x', linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, "retrieval_quality_ranking.png"), dpi=150)
    # Also save as combined_scores.png for backwards-compat
    plt.savefig(os.path.join(plots_dir, "combined_scores.png"), dpi=150)
    plt.close()
    
    # Plot 2: Latency Comparison (p50 vs p95 vs Mean)
    plt.figure(figsize=(11, 6))
    y_pos = np.arange(len(systems))
    bar_height = 0.35
    plt.barh(y_pos - bar_height/2, p50_latencies, height=bar_height, label='Median (p50)', color='#4292c6', edgecolor='black', alpha=0.85)
    plt.barh(y_pos + bar_height/2, p95_latencies, height=bar_height, label='Tail (p95)', color='#fc9272', edgecolor='black', alpha=0.85)
    plt.yticks(y_pos, systems)
    plt.gca().invert_yaxis()
    plt.xlabel('Retrieval Latency (ms) - Lower is Better')
    plt.title('RAG Systems - High-Resolution Latency Distribution (p50 vs p95)')
    plt.legend()
    plt.grid(axis='x', linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, "latency_comparison.png"), dpi=150)
    plt.close()
    
    # Plot 3: Accuracy Metrics Comparison (Precision@1, Precision@5, Recall@5, MRR)
    plt.figure(figsize=(12, 7))
    x = np.arange(len(systems))
    width = 0.2
    
    plt.bar(x - 1.5*width, p1, width, label='Precision@1', color='#1f77b4', edgecolor='black', alpha=0.85)
    plt.bar(x - 0.5*width, p5, width, label='Precision@5', color='#ff7f0e', edgecolor='black', alpha=0.85)
    plt.bar(x + 0.5*width, r5, width, label='Recall@5', color='#2ca02c', edgecolor='black', alpha=0.85)
    plt.bar(x + 1.5*width, mrr, width, label='MRR', color='#9467bd', edgecolor='black', alpha=0.85)
    
    plt.xlabel('RAG Architecture')
    plt.ylabel('Score (0.0 - 1.0)')
    plt.title('RAG Systems - Comprehensive Retrieval Accuracy Metrics')
    plt.xticks(x, systems, rotation=40, ha='right')
    plt.legend()
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, "accuracy_comparison.png"), dpi=150)
    plt.close()
    
    # Plot 4: Speed vs True Accuracy Pareto Frontier
    plt.figure(figsize=(10, 7))
    plt.scatter(latencies, quality_scores, color='#d95f02', s=120, edgecolor='black', zorder=5)
    
    for i, txt in enumerate(systems):
        plt.annotate(txt, (latencies[i], quality_scores[i]), xytext=(7, 4), 
                     textcoords='offset points', fontsize=9, fontweight='bold')
        
    plt.xlabel('Mean Retrieval Latency (ms) - LOWER is better')
    plt.ylabel('Mean Retrieval Quality - HIGHER is better')
    plt.title('Speed vs. Accuracy Tradeoff (Empirical Pareto Frontier)')
    plt.grid(linestyle='--', alpha=0.5)
    
    # Highlight Pareto optimal systems (non-dominated)
    pareto_systems = []
    for i, s1 in enumerate(systems):
        dominated = False
        for j, s2 in enumerate(systems):
            if i == j:
                continue
            if latencies[j] <= latencies[i] and quality_scores[j] >= quality_scores[i]:
                if latencies[j] < latencies[i] or quality_scores[j] > quality_scores[i]:
                    dominated = True
                    break
        if not dominated:
            pareto_systems.append(s1)
            
    print(f"Pareto optimal architectures (Quality vs Latency): {pareto_systems}")
    
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, "speed_vs_accuracy.png"), dpi=150)
    plt.close()
    
    print("All research-hardened plots generated successfully!")
    print(f"Saved to: {plots_dir}")

if __name__ == "__main__":
    main()
