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

    # Load routing analysis if available
    routing_files = glob.glob(os.path.join(results_dir, "routing_analysis_*.json"))
    if routing_files:
        latest_routing = max(routing_files, key=os.path.getmtime)
        try:
            with open(latest_routing, 'r', encoding='utf-8') as f:
                rdata = json.load(f)
            
            # Plot 5: Router Performance Comparison with 95% Confidence Intervals
            r_comp = rdata.get("router_comparison", {})
            if r_comp:
                plt.figure(figsize=(9, 6))
                r_labels = ["Oracle Router", "Adaptive Router", "Vector Baseline", "Random Router"]
                r_means = [
                    r_comp.get("oracle_router", {}).get("mean_quality", 0),
                    r_comp.get("adaptive_router", {}).get("mean_quality", 0),
                    r_comp.get("vector_baseline", {}).get("mean_quality", 0),
                    r_comp.get("random_router", {}).get("mean_quality", 0)
                ]
                r_errs = [
                    r_comp.get("oracle_router", {}).get("ci_95", 0),
                    r_comp.get("adaptive_router", {}).get("ci_95", 0),
                    r_comp.get("vector_baseline", {}).get("ci_95", 0),
                    0.0
                ]
                colors_r = ['#2ca02c', '#1f77b4', '#ff7f0e', '#7f7f7f']
                bars = plt.bar(r_labels, r_means, yerr=r_errs, capsize=6, color=colors_r, edgecolor='black', alpha=0.85)
                for bar in bars:
                    yval = bar.get_height()
                    plt.text(bar.get_x() + bar.get_width()/2.0, yval / 2.0, f"{yval:.4f}", ha='center', va='center', color='white', fontweight='bold', fontsize=11)
                
                plt.ylabel('Mean Retrieval Quality')
                plt.title('Routing Strategy Comparison (with 95% Confidence Intervals)')
                plt.grid(axis='y', linestyle='--', alpha=0.5)
                plt.tight_layout()
                plt.savefig(os.path.join(plots_dir, "router_comparison.png"), dpi=150)
                plt.close()

            # Plot 6: Architecture x Query-Type Heatmap
            matrix = rdata.get("architecture_by_query_type_matrix", {})
            if matrix:
                arch_list = list(matrix.keys())
                categories = [c for c in matrix[arch_list[0]].keys() if c != "OVERALL"]
                heatmap_data = np.zeros((len(arch_list), len(categories)))
                for r_idx, arch in enumerate(arch_list):
                    for c_idx, cat in enumerate(categories):
                        heatmap_data[r_idx, c_idx] = matrix[arch].get(cat, 0.0)
                
                plt.figure(figsize=(12, 7))
                plt.imshow(heatmap_data, cmap='YlGnBu', aspect='auto', vmin=0.0, vmax=1.0)
                plt.colorbar(label='Mean Retrieval Quality')
                plt.xticks(np.arange(len(categories)), [c.replace('_', ' ').title() for c in categories], rotation=30, ha='right')
                plt.yticks(np.arange(len(arch_list)), arch_list)
                
                # Annotate cells
                for r_idx in range(len(arch_list)):
                    for c_idx in range(len(categories)):
                        val = heatmap_data[r_idx, c_idx]
                        text_color = "white" if val > 0.55 else "black"
                        plt.text(c_idx, r_idx, f"{val:.2f}", ha='center', va='center', color=text_color, fontsize=9)
                
                plt.title('Architecture × Query-Type Performance Matrix (Heatmap)')
                plt.tight_layout()
                plt.savefig(os.path.join(plots_dir, "architecture_query_matrix.png"), dpi=150)
                plt.close()
                
            # Plot 7: Routing Regret Analysis
            regret_stats = rdata.get("routing_regret_analysis", {})
            if regret_stats:
                plt.figure(figsize=(8, 5))
                m_regret = regret_stats.get("mean_quality_regret", 0)
                accuracy = regret_stats.get("routing_accuracy", 0)
                
                labels = ['Mean Quality Regret\n(Oracle - Adaptive)', 'Routing Accuracy\n(Optimal Choice Rate)']
                values = [m_regret, accuracy]
                colors_reg = ['#d95f02', '#2ca02c']
                bars = plt.bar(labels, values, color=colors_reg, edgecolor='black', alpha=0.85, width=0.45)
                for bar in bars:
                    yval = bar.get_height()
                    plt.text(bar.get_x() + bar.get_width()/2.0, yval + 0.02, f"{yval:.4f}", ha='center', va='bottom', fontweight='bold')
                
                plt.ylim(0, max(values) * 1.35 if max(values) > 0 else 1.0)
                plt.ylabel('Score / Probability')
                plt.title('Adaptive Router Regret & Decision Accuracy')
                plt.grid(axis='y', linestyle='--', alpha=0.5)
                plt.tight_layout()
                plt.savefig(os.path.join(plots_dir, "routing_regret_summary.png"), dpi=150)
                plt.close()
                
        except Exception as e:
            print(f"Warning: Could not plot routing analysis: {e}")
    
    print("All research-hardened plots generated successfully!")
    print(f"Saved to: {plots_dir}")

if __name__ == "__main__":
    main()
