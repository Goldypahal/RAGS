"""
Train and Evaluate the Learned Query Router against the 700-query benchmark.
Compares Heuristic Router vs Learned Router vs Oracle Ceiling.
"""

import sys
import os
import glob
import json
import time
import numpy as np
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

if sys.platform == 'win32':
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

from benchmark.learned_router import LearnedRouter


def main():
    print("=" * 80)
    print("🧠 TRAINING & EVALUATING LEARNED QUERY ROUTER (PHASE 4)")
    print("=" * 80)
    
    # 1. Load latest benchmark results
    results_dir = Path(__file__).parent / "results"
    json_files = glob.glob(str(results_dir / "benchmark_results_*.json"))
    if not json_files:
        print("No benchmark results JSON found.")
        return
        
    latest_file = max(json_files, key=os.path.getmtime)
    print(f"\n📂 Loading detailed benchmark results from: {os.path.basename(latest_file)}")
    
    with open(latest_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    # Extract query results across all systems
    detailed = data.get("metrics", [])
    if not detailed:
        print("No metrics results found.")
        return
        
    # Group results by query
    queries_by_id = {}
    for res in detailed:
        qid = (res["test_type"], res["query"])
        if qid not in queries_by_id:
            queries_by_id[qid] = {
                'query': res['query'],
                'query_type': res['test_type'],
                'system_qualities': {},
                'system_latencies': {}
            }
        sys_name = res['system']
        # Quality = mean of P@1, P@5, R@5, MRR, NDCG@5
        q = (res['precision_at_1'] + res['precision_at_5'] + res['recall_at_5'] + res['mrr'] + res['ndcg_at_5']) / 5.0
        queries_by_id[qid]['system_qualities'][sys_name] = q
        queries_by_id[qid]['system_latencies'][sys_name] = res['retrieval_time_ms']
        
    print(f"✓ Found {len(queries_by_id)} unique evaluated queries across {len(data['systems'])} systems")
    
    # Prepare training dataset
    queries = []
    oracle_targets = []
    oracle_qualities = []
    heuristic_qualities = []
    random_qualities = []
    all_system_scores = []
    
    for qid, qdata in queries_by_id.items():
        q = qdata['query']
        scores = qdata['system_qualities']
        
        # Oracle system
        best_sys = max(scores.keys(), key=lambda s: scores[s])
        oracle_q = scores[best_sys]
        
        # Adaptive (heuristic) quality
        # AdaptiveRetrievalRAG score
        heur_q = scores.get('AdaptiveRetrievalRAG', 0.0)
        
        # Random expected
        rand_q = float(np.mean(list(scores.values())))
        
        queries.append(q)
        oracle_targets.append(best_sys)
        oracle_qualities.append(oracle_q)
        heuristic_qualities.append(heur_q)
        random_qualities.append(rand_q)
        all_system_scores.append(scores)
        
    # 2. Train Learned Router with 5-fold cross-validation
    router = LearnedRouter(C=1.5)
    train_results = router.train(queries, oracle_targets)
    
    print(f"\n⚙️  Cross-Validation Training Results:")
    print(f"  • Sample count:      {train_results['n_samples']}")
    print(f"  • Feature dimension: {train_results['n_features']}")
    print(f"  • Classes:           {train_results['classes']}")
    print(f"  • 5-Fold CV Accuracy: {train_results['cv_accuracy']*100:.2f}%\n")
    
    # 3. Evaluate Routing Performance and Quality Regret
    # We measure latency of learned prediction
    t0 = time.perf_counter_ns()
    learned_predictions = [router.predict(q) for q in queries]
    t1 = time.perf_counter_ns()
    avg_inference_latency_ms = ((t1 - t0) / len(queries)) / 1_000_000.0
    
    learned_qualities = []
    learned_optimal_matches = 0
    
    for idx, (chosen_sys, conf) in enumerate(learned_predictions):
        score = all_system_scores[idx].get(chosen_sys, 0.0)
        learned_qualities.append(score)
        if chosen_sys == oracle_targets[idx]:
            learned_optimal_matches += 1
            
    # Metrics computation
    mean_oracle = np.mean(oracle_qualities)
    mean_learned = np.mean(learned_qualities)
    mean_heuristic = np.mean(heuristic_qualities)
    mean_vector = np.mean([s.get('VectorRAG', 0.0) for s in all_system_scores])
    mean_random = np.mean(random_qualities)
    
    regret_oracle_learned = np.mean([max(0.0, o - l) for o, l in zip(oracle_qualities, learned_qualities)])
    regret_oracle_heuristic = np.mean([max(0.0, o - h) for o, h in zip(oracle_qualities, heuristic_qualities)])
    
    accuracy_learned = learned_optimal_matches / len(queries)
    
    print("=" * 80)
    print("📊 ROUTER COMPARISON SUMMARY (PHASE 4)")
    print("=" * 80)
    print(f"{'Router Architecture':<28} {'Mean Quality':<14} {'Oracle Gap':<14} {'Regret':<10}")
    print("-" * 80)
    print(f"{'Oracle Router (Theoretical)':<28} {mean_oracle:<14.4f} {'100.0%':<14} {'0.0000':<10}")
    print(f"{'Learned Router (Phase 4)':<28} {mean_learned:<14.4f} {mean_learned/mean_oracle*100:<13.1f}% {regret_oracle_learned:<10.4f}")
    print(f"{'VectorRAG Baseline':<28} {mean_vector:<14.4f} {mean_vector/mean_oracle*100:<13.1f}% {'—':<10}")
    print(f"{'Adaptive Router (Heuristic)':<28} {mean_heuristic:<14.4f} {mean_heuristic/mean_oracle*100:<13.1f}% {regret_oracle_heuristic:<10.4f}")
    print(f"{'Random Router (Null)':<28} {mean_random:<14.4f} {mean_random/mean_oracle*100:<13.1f}% {'—':<10}")
    print("-" * 80)
    print(f"⚡ Learned Router Inference Latency: {avg_inference_latency_ms:.3f} ms per query")
    print(f"🎯 Learned Routing Optimal Match Rate: {accuracy_learned*100:.1f}%\n")
    
    # Save model
    model_path = Path(__file__).parent / "results" / "learned_router_model.joblib"
    router.save(str(model_path))
    print(f"💾 Trained model saved to: {model_path}")
    
    # Save comparison JSON
    summary = {
        'timestamp': time.time(),
        'n_queries': len(queries),
        'oracle_quality': float(mean_oracle),
        'learned_router_quality': float(mean_learned),
        'vector_baseline_quality': float(mean_vector),
        'heuristic_adaptive_quality': float(mean_heuristic),
        'random_quality': float(mean_random),
        'learned_quality_regret': float(regret_oracle_learned),
        'heuristic_quality_regret': float(regret_oracle_heuristic),
        'learned_accuracy': float(accuracy_learned),
        'avg_inference_latency_ms': float(avg_inference_latency_ms)
    }
    
    out_json = Path(__file__).parent / "results" / "learned_router_evaluation.json"
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    print(f"💾 Evaluation summary saved to: {out_json}")


if __name__ == "__main__":
    main()
