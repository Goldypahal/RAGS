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
    # Sort systems by combined score for consistent ordering in plots
    systems = sorted(systems, key=lambda s: systems_data[s]["combined_score"], reverse=True)
    
    combined_scores = [systems_data[s]["combined_score"] for s in systems]
    p1 = [systems_data[s]["accuracy"]["precision_at_1"] for s in systems]
    p5 = [systems_data[s]["accuracy"]["precision_at_5"] for s in systems]
    r5 = [systems_data[s]["accuracy"]["recall_at_5"] for s in systems]
    mrr = [systems_data[s]["accuracy"]["mrr"] for s in systems]
    ndcg = [systems_data[s]["accuracy"]["ndcg_at_5"] for s in systems]
    
    latency = [systems_data[s]["performance"]["avg_latency_ms"] for s in systems]
    memory = [systems_data[s]["performance"]["avg_memory_mb"] for s in systems]
    
    # Color palette
    colors = plt.cm.plasma(np.linspace(0.1, 0.9, len(systems)))
    
    # Plot 1: Combined Scores
    plt.figure(figsize=(10, 6))
    y_pos = np.arange(len(systems))
    plt.barh(y_pos, combined_scores, align='center', color=colors, edgecolor='black', alpha=0.8)
    plt.yticks(y_pos, systems)
    plt.gca().invert_yaxis()  # Top-down ranking
    plt.xlabel('Combined Score (higher is better)')
    plt.title('RAG Architecture Comparison - Combined Score')
    plt.grid(axis='x', linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, "combined_scores.png"), dpi=150)
    plt.close()
    
    # Plot 2: Latency Comparison
    plt.figure(figsize=(10, 6))
    plt.barh(y_pos, latency, align='center', color='skyblue', edgecolor='black', alpha=0.8)
    plt.yticks(y_pos, systems)
    plt.gca().invert_yaxis()
    plt.xlabel('Average Retrieval Latency (ms) - lower is better')
    plt.title('RAG Architecture Comparison - Latency')
    plt.grid(axis='x', linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, "latency_comparison.png"), dpi=150)
    plt.close()
    
    # Plot 3: Accuracy Metrics Comparison (Precision@1, Precision@5, Recall@5)
    plt.figure(figsize=(12, 7))
    x = np.arange(len(systems))
    width = 0.25
    
    plt.bar(x - width, p1, width, label='Precision@1', color='#1f77b4', edgecolor='black', alpha=0.8)
    plt.bar(x, p5, width, label='Precision@5', color='#ff7f0e', edgecolor='black', alpha=0.8)
    plt.bar(x + width, r5, width, label='Recall@5', color='#2ca02c', edgecolor='black', alpha=0.8)
    
    plt.xlabel('RAG Architecture')
    plt.ylabel('Score')
    plt.title('RAG Architecture Comparison - Accuracy Metrics')
    plt.xticks(x, systems, rotation=45, ha='right')
    plt.legend()
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, "accuracy_comparison.png"), dpi=150)
    plt.close()
    
    # Plot 4: Speed vs Accuracy Pareto Frontier
    plt.figure(figsize=(10, 7))
    # Note: For Pareto, higher combined_score and lower latency is better
    plt.scatter(latency, combined_scores, color='red', s=100, edgecolor='black', zorder=5)
    
    for i, txt in enumerate(systems):
        # Add labels with offset to avoid overlap
        plt.annotate(txt, (latency[i], combined_scores[i]), xytext=(7, 4), 
                     textcoords='offset points', fontsize=9, fontweight='bold')
        
    plt.xlabel('Average Latency (ms) - LOWER is better')
    plt.ylabel('Combined Score - HIGHER is better')
    plt.title('Speed vs. Accuracy Tradeoff (Pareto Space)')
    plt.grid(linestyle='--', alpha=0.5)
    
    # Highlight Pareto optimal systems (best tradeoff)
    # A system is Pareto optimal if no other system has both higher score and lower latency.
    pareto_systems = []
    for i, s1 in enumerate(systems):
        dominated = False
        for j, s2 in enumerate(systems):
            if i == j:
                continue
            # If s2 is faster and has a higher score, then s1 is dominated
            if latency[j] <= latency[i] and combined_scores[j] >= combined_scores[i]:
                if latency[j] < latency[i] or combined_scores[j] > combined_scores[i]:
                    dominated = True
                    break
        if not dominated:
            pareto_systems.append(s1)
            
    print(f"Pareto optimal architectures: {pareto_systems}")
    
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, "speed_vs_accuracy.png"), dpi=150)
    plt.close()
    
    print("All plots generated successfully!")
    print(f"Saved to: {plots_dir}")

if __name__ == "__main__":
    main()
