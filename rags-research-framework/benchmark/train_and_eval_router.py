"""
Training and Held-Out Evaluation of the Learned Query Router.

Protocol:
1. Group-wise 60/20/20 Train / Validation / Test split (seed = 42). Groups are the
   anchor paper (or semantic prompt) recorded in the test suite's "group" field, so
   template variants of the same paper never straddle train and test.
2. Features and classifier are fitted on Train only.
3. The regularization strength C is selected on Validation; the final model is
   refit on Train+Validation and scored once on Test.
4. Labels are the best FIXED system per query (AdaptiveRetrievalRAG excluded, since
   it is the thing being routed). Ties, which are common, go to the system with the
   lowest median training latency, then by name.
5. Baselines on Test: Oracle, best single fixed system chosen on Train, the
   AdaptiveRetrievalRAG as benchmarked, and the random-router expectation.
6. Cross-domain transfer: train on lexical categories, test on reasoning categories.

Usage:
    python benchmark/train_and_eval_router.py [--results PATH] [--test-dir DIR]
"""

import sys
import os
import glob
import json
import time
import argparse
import numpy as np
from pathlib import Path
from typing import Dict, List, Any

# Ensure UTF-8 output on Windows consoles
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmark.learned_router import LearnedRouter

ADAPTIVE = "AdaptiveRetrievalRAG"
TIE_TOLERANCE = 1e-9
C_GRID = [0.1, 0.3, 1.0, 3.0, 10.0]
LEXICAL_TYPES = {'exact_lookup', 'prefix_lookup', 'keyword_search'}
REASONING_TYPES = {'semantic_search', 'relationship_search', 'multi_hop_reasoning'}


def load_query_items(results_path: str, test_dir: str) -> List[Dict[str, Any]]:
    """Group per-system metrics by query and attach each query's split group."""
    with open(results_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    groups: Dict[tuple, str] = {}
    for path in glob.glob(os.path.join(test_dir, "*.json")):
        with open(path, 'r', encoding='utf-8') as f:
            for t in json.load(f):
                groups[(t.get('type'), t['query'])] = t.get('group', t['query'])

    items: Dict[tuple, Dict[str, Any]] = {}
    for res in data.get("metrics", []):
        key = (res["test_type"], res["query"])
        item = items.setdefault(key, {
            'query': res['query'],
            'query_type': res['test_type'],
            'group': groups.get(key, res['query']),
            'qualities': {},
            'latencies': {}
        })
        q = (res['precision_at_1'] + res['precision_at_5'] + res['recall_at_5'] + res['mrr'] + res['ndcg_at_5']) / 5.0
        item['qualities'][res['system']] = q
        item['latencies'][res['system']] = res['retrieval_time_ms']
    return list(items.values())


def fixed_systems(item: Dict[str, Any]) -> Dict[str, float]:
    return {s: q for s, q in item['qualities'].items() if s != ADAPTIVE}


def label(item: Dict[str, Any], cost_rank: Dict[str, int]) -> str:
    """Best fixed system; ties go to the cheaper system, then by name."""
    fixed = fixed_systems(item)
    best_q = max(fixed.values())
    tied = [s for s, q in fixed.items() if q >= best_q - TIE_TOLERANCE]
    return min(tied, key=lambda s: (cost_rank.get(s, len(cost_rank)), s))


def latency_cost_rank(items: List[Dict[str, Any]]) -> Dict[str, int]:
    systems = sorted({s for it in items for s in fixed_systems(it)})
    medians = {s: float(np.median([it['latencies'][s] for it in items if s in it['latencies']])) for s in systems}
    return {s: i for i, s in enumerate(sorted(systems, key=lambda s: (medians[s], s)))}


def routed_quality(router: LearnedRouter, items: List[Dict[str, Any]]) -> List[float]:
    return [fixed_systems(it).get(router.predict(it['query'])[0], 0.0) for it in items]


def group_split(items: List[Dict[str, Any]], seed: int = 42):
    groups = sorted({it['group'] for it in items})
    rng = np.random.default_rng(seed)
    rng.shuffle(groups)
    n_train = int(round(0.6 * len(groups)))
    n_val = int(round(0.2 * len(groups)))
    train_g = set(groups[:n_train])
    val_g = set(groups[n_train:n_train + n_val])
    test_g = set(groups[n_train + n_val:])
    pick = lambda gs: [it for it in items if it['group'] in gs]
    return pick(train_g), pick(val_g), pick(test_g), (train_g, val_g, test_g)


def main():
    parser = argparse.ArgumentParser(description="Train and evaluate the learned router")
    parser.add_argument("--results", default=None, help="benchmark_results_*.json (default: newest)")
    parser.add_argument("--test-dir", default="benchmark/tests/scaled", help="Test suites the results came from")
    parser.add_argument("--save", default=str(Path(__file__).parent / "results" / "learned_router_model.joblib"))
    args = parser.parse_args()

    print("=" * 85)
    print("🧠 LEARNED ROUTER: GROUP-SPLIT HELD-OUT EVALUATION")
    print("=" * 85)

    results_path = args.results
    if results_path is None:
        json_files = glob.glob(str(Path(__file__).parent / "results" / "benchmark_results_*.json"))
        if not json_files:
            print("No benchmark results JSON found.")
            return
        results_path = max(json_files, key=os.path.getmtime)
    print(f"\n📂 Results: {results_path}")

    items = load_query_items(results_path, args.test_dir)
    if not items:
        print("No metrics results found.")
        return
    n_groups = len({it['group'] for it in items})
    print(f"✓ {len(items)} distinct queries in {n_groups} groups")

    train, val, test, (train_g, val_g, test_g) = group_split(items)
    print(f"\n📊 Group-wise split: train {len(train)} queries / {len(train_g)} groups, "
          f"val {len(val)} / {len(val_g)}, test {len(test)} / {len(test_g)}")
    print(f"   Test groups: {sorted(test_g)}")

    cost_rank = latency_cost_rank(train)

    # Select C on validation
    val_scores = {}
    for C in C_GRID:
        r = LearnedRouter(C=C)
        r.train([it['query'] for it in train], [label(it, cost_rank) for it in train])
        val_scores[C] = float(np.mean(routed_quality(r, val))) if val else 0.0
    best_C = max(C_GRID, key=lambda c: (val_scores[c], -c))
    print(f"\n🔧 Validation quality by C: " + ", ".join(f"{c}: {q:.4f}" for c, q in val_scores.items()))
    print(f"   Selected C = {best_C}")

    # Refit on train + val, score once on test
    fit_items = train + val
    router = LearnedRouter(C=best_C)
    train_meta = router.train([it['query'] for it in fit_items], [label(it, cost_rank) for it in fit_items])

    t0 = time.perf_counter_ns()
    preds = [router.predict(it['query'])[0] for it in test]
    t1 = time.perf_counter_ns()
    avg_inference_ms = ((t1 - t0) / max(1, len(test))) / 1_000_000.0

    fixed_names = sorted({s for it in fit_items for s in fixed_systems(it)})
    best_fixed = max(fixed_names, key=lambda s: (np.mean([fixed_systems(it).get(s, 0.0) for it in fit_items]), s))

    oracle_q, learned_q, fixed_q, adaptive_q, random_q = [], [], [], [], []
    oracle_ties = 0
    eps_optimal = 0
    EPSILON = 0.05
    for it, pred in zip(test, preds):
        fixed = fixed_systems(it)
        o = max(fixed.values())
        l = fixed.get(pred, 0.0)
        oracle_q.append(o)
        learned_q.append(l)
        fixed_q.append(fixed.get(best_fixed, 0.0))
        adaptive_q.append(it['qualities'].get(ADAPTIVE, 0.0))
        random_q.append(float(np.mean(list(fixed.values()))))
        oracle_ties += l >= o - TIE_TOLERANCE
        eps_optimal += l >= o - EPSILON

    m = lambda xs: float(np.mean(xs)) if xs else 0.0
    mean_oracle = m(oracle_q)
    pct = lambda x: (x / mean_oracle * 100) if mean_oracle > 0 else 0.0

    print("\n" + "=" * 85)
    print(f"🏆 HELD-OUT TEST (N = {len(test)} queries from {len(test_g)} unseen groups)")
    print("=" * 85)
    print(f"{'Router':<40} {'Quality':<10} {'% Oracle':<10}")
    print("-" * 85)
    rows = [
        ("Oracle (best fixed system per query)", mean_oracle),
        ("Learned router", m(learned_q)),
        (f"Best single system on train ({best_fixed})", m(fixed_q)),
        (f"{ADAPTIVE} (as benchmarked)", m(adaptive_q)),
        ("Random router (expected)", m(random_q)),
    ]
    for name, q in rows:
        print(f"{name:<40} {q:<10.4f} {pct(q):<9.1f}%")
    print("-" * 85)
    print(f"🎯 Routed system ties the oracle:  {oracle_ties / max(1, len(test)) * 100:.2f}%")
    print(f"🎯 Within ε = {EPSILON} of the oracle:  {eps_optimal / max(1, len(test)) * 100:.2f}%")
    print(f"⚡ Router inference:               {avg_inference_ms:.3f} ms/query")
    if len(test_g) < 5:
        print(f"⚠️  Only {len(test_g)} test groups: these numbers have very wide uncertainty.")

    # Cross-domain transfer
    cd_train = [it for it in items if it['query_type'] in LEXICAL_TYPES]
    cd_test = [it for it in items if it['query_type'] in REASONING_TYPES]
    cross_domain = None
    if cd_train and cd_test:
        cd_rank = latency_cost_rank(cd_train)
        cd_router = LearnedRouter(C=best_C)
        cd_router.train([it['query'] for it in cd_train], [label(it, cd_rank) for it in cd_train])
        cd_l = routed_quality(cd_router, cd_test)
        cd_o = [max(fixed_systems(it).values()) for it in cd_test]
        cross_domain = {
            'train_samples': len(cd_train),
            'test_samples': len(cd_test),
            'learned_quality': m(cd_l),
            'oracle_quality': m(cd_o),
        }
        print(f"\n🌐 Cross-domain (lexical -> reasoning): {m(cd_l):.4f} "
              f"({m(cd_l) / max(1e-9, m(cd_o)) * 100:.1f}% of oracle), N = {len(cd_test)}")

    # Save the final router with provenance, so nobody loads it on its own training queries
    router.save(args.save)
    meta = {
        'source_results': os.path.abspath(results_path),
        'test_dir': args.test_dir,
        'split_seed': 42,
        'train_val_groups': sorted(train_g | val_g),
        'test_groups': sorted(test_g),
        'C': best_C,
        'classes': train_meta['classes'],
        'warning': 'Do not benchmark AdaptiveRetrievalRAG with this router on queries from train_val_groups.'
    }
    with open(os.path.splitext(args.save)[0] + ".meta.json", 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2)
    print(f"\n💾 Router saved to {args.save} (+ .meta.json provenance)")

    summary = {
        'total_unique_queries': len(items),
        'n_groups': n_groups,
        'train_samples': len(train), 'val_samples': len(val), 'test_samples': len(test),
        'test_groups': sorted(test_g),
        'split': 'group-wise by anchor paper / prompt',
        'split_seed': 42,
        'selected_C': best_C,
        'validation_quality_by_C': val_scores,
        'test_metrics': {
            'oracle_quality': mean_oracle,
            'learned_router_quality': m(learned_q),
            'best_fixed_system_on_train': best_fixed,
            'best_fixed_system_quality': m(fixed_q),
            'adaptive_as_benchmarked_quality': m(adaptive_q),
            'random_quality': m(random_q),
            'oracle_tie_rate': oracle_ties / max(1, len(test)),
            'epsilon_optimal_rate': eps_optimal / max(1, len(test)),
            'avg_inference_latency_ms': avg_inference_ms
        },
        'cross_domain': cross_domain
    }
    out_json = Path(__file__).parent / "results" / "learned_router_evaluation_leakfree.json"
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    print(f"💾 Evaluation saved to: {out_json}")


if __name__ == "__main__":
    main()
