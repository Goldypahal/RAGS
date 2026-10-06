"""
Scale Benchmark: Generates a high-power, multi-category benchmark suite (700 queries).

Produces 100 queries for each of the 7 research categories:
1. Exact Lookup (100)
2. Prefix Lookup (100)
3. Keyword Search (100)
4. Semantic Search (100)
5. Relationship Search (100)
6. Multi-Hop Reasoning (100)
7. Mixed Realistic Workload (100)
Total: 700 curated queries with ground-truth expected document IDs.
"""

import os
import sys
import io
import json
import random
from pathlib import Path
from typing import List, Dict, Any

# Ensure UTF-8 output on Windows consoles
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def save_json(data: Any, path: str):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def generate_scaled_suite(dataset_dir: str = "benchmark/dataset", output_dir: str = "benchmark/tests/scaled"):
    """Generate 700 benchmark queries across 7 categories."""
    ensure_dir(output_dir)
    random.seed(42)  # Deterministic seed for reproducible research
    
    # Load papers
    papers_path = os.path.join(dataset_dir, "papers.json")
    with open(papers_path, 'r', encoding='utf-8') as f:
        papers = json.load(f)
        
    try:
        with open(os.path.join(dataset_dir, "citations.json"), 'r', encoding='utf-8') as f:
            citations = json.load(f)
    except Exception:
        citations = []
        
    paper_ids = [p['id'] for p in papers]
    paper_map = {p['id']: p for p in papers}
    
    print(f"Generating 700 scaled test queries from {len(papers)} documents...")
    
    # 1. Exact Lookup (100 queries)
    exact_queries = []
    for i in range(100):
        paper = papers[i % len(papers)]
        query_variants = [
            f"What is {paper['title']}?",
            f"Paper: {paper['title']}",
            f"{paper['title']}",
            f"Explain {paper['title']}",
            f"Lookup document {paper['id']}"
        ]
        q_text = query_variants[(i // len(papers)) % len(query_variants)]
        exact_queries.append({
            "id": f"exact_{i+1:03d}",
            "query": q_text,
            "expected_doc_ids": [paper['id']],
            "type": "exact_lookup",
            "difficulty": "easy"
        })
    save_json(exact_queries, os.path.join(output_dir, "exact_lookup.json"))
    print(f"  ✓ Exact Lookup: {len(exact_queries)} queries")
    
    # 2. Prefix Lookup (100 queries)
    prefix_queries = []
    for i in range(100):
        paper = papers[i % len(papers)]
        title = paper['title']
        words = title.split()
        prefix_len = max(1, min(len(words), (i % 3) + 1))
        prefix_phrase = " ".join(words[:prefix_len])
        prefix_queries.append({
            "id": f"prefix_{i+1:03d}",
            "query": prefix_phrase,
            "expected_doc_ids": [paper['id']],
            "type": "prefix_lookup",
            "difficulty": "easy" if prefix_len > 1 else "medium"
        })
    save_json(prefix_queries, os.path.join(output_dir, "prefix_lookup.json"))
    print(f"  ✓ Prefix Lookup: {len(prefix_queries)} queries")
    
    # 3. Keyword Search (100 queries)
    keyword_queries = []
    for i in range(100):
        paper = papers[i % len(papers)]
        keywords = paper.get('keywords', paper.get('topics', []))
        if not keywords:
            keywords = [w for w in paper['title'].split() if len(w) > 3]
        sample_kws = random.sample(keywords, min(len(keywords), random.randint(2, 3)))
        q_text = " ".join(sample_kws)
        # Find all papers sharing any of these keywords
        matching_papers = [
            p['id'] for p in papers 
            if any(kw.lower() in " ".join(p.get('keywords', [])).lower() or kw.lower() in p['title'].lower() for kw in sample_kws)
        ]
        if paper['id'] not in matching_papers:
            matching_papers.append(paper['id'])
        keyword_queries.append({
            "id": f"keyword_{i+1:03d}",
            "query": q_text,
            "expected_doc_ids": matching_papers[:5],
            "type": "keyword_search",
            "difficulty": "medium"
        })
    save_json(keyword_queries, os.path.join(output_dir, "keyword_search.json"))
    print(f"  ✓ Keyword Search: {len(keyword_queries)} queries")
    
    # 4. Semantic Search (100 queries)
    semantic_queries = []
    semantic_templates = [
        "How do models using {topic} perform on modern benchmarks?",
        "Explain the theoretical foundations of {topic} in sequence modeling.",
        "What are the main advantages and limitations of {topic}?",
        "Describe how deep neural networks apply {topic} to natural language.",
        "A survey on computational efficiency and scalability of {topic}."
    ]
    for i in range(100):
        paper = papers[i % len(papers)]
        topic = (paper.get('topics') or ['neural architectures'])[0]
        template = semantic_templates[i % len(semantic_templates)]
        q_text = template.format(topic=topic)
        semantic_queries.append({
            "id": f"semantic_{i+1:03d}",
            "query": q_text,
            "expected_doc_ids": [paper['id']],
            "type": "semantic_search",
            "difficulty": "hard"
        })
    save_json(semantic_queries, os.path.join(output_dir, "semantic_search.json"))
    print(f"  ✓ Semantic Search: {len(semantic_queries)} queries")
    
    # 5. Relationship Search (100 queries)
    relationship_queries = []
    for i in range(100):
        paper = papers[i % len(papers)]
        venue = paper.get('venue', 'NeurIPS')
        year = paper.get('year', 2020)
        q_templates = [
            f"Which papers were published at {venue}?",
            f"Find all papers authored by {paper['authors'][0] if paper.get('authors') else 'researchers'}",
            f"What models cite or build upon {paper['title']}?",
            f"Which publications from {year} introduce attention or transformers?"
        ]
        q_text = q_templates[i % len(q_templates)]
        # Related papers sharing venue, year, or citation
        related = [p['id'] for p in papers if p.get('venue') == venue or p.get('year') == year]
        if paper['id'] not in related:
            related.append(paper['id'])
        relationship_queries.append({
            "id": f"rel_{i+1:03d}",
            "query": q_text,
            "expected_doc_ids": related[:5],
            "type": "relationship_search",
            "difficulty": "medium"
        })
    save_json(relationship_queries, os.path.join(output_dir, "relationship_search.json"))
    print(f"  ✓ Relationship Search: {len(relationship_queries)} queries")
    
    # 6. Multi-Hop Reasoning (100 queries)
    multihop_queries = []
    for i in range(100):
        p1 = papers[i % len(papers)]
        p2 = papers[(i + 1) % len(papers)]
        q_templates = [
            f"Compare the attention mechanisms in {p1['title']} and {p2['title']}.",
            f"How does the architecture in {p2['title']} extend the concepts in {p1['title']}?",
            f"What is the connection between {p1.get('topics', ['AI'])[0]} and {p2.get('topics', ['ML'])[0]}?",
            f"Trace the evolutionary path from {p1['title']} through downstream models to {p2['title']}."
        ]
        q_text = q_templates[i % len(q_templates)]
        multihop_queries.append({
            "id": f"multihop_{i+1:03d}",
            "query": q_text,
            "expected_doc_ids": [p1['id'], p2['id']],
            "type": "multi_hop_reasoning",
            "difficulty": "hard"
        })
    save_json(multihop_queries, os.path.join(output_dir, "multi_hop_reasoning.json"))
    print(f"  ✓ Multi-Hop Reasoning: {len(multihop_queries)} queries")
    
    # 7. Mixed Queries (100 queries)
    mixed_queries = []
    all_types = [exact_queries, prefix_queries, keyword_queries, semantic_queries, relationship_queries, multihop_queries]
    for i in range(100):
        source_suite = all_types[i % len(all_types)]
        source_q = source_suite[i % len(source_suite)]
        mixed_queries.append({
            "id": f"mixed_{i+1:03d}",
            "query": source_q["query"],
            "expected_doc_ids": source_q["expected_doc_ids"],
            "type": "mixed_queries",
            "difficulty": source_q["difficulty"]
        })
    save_json(mixed_queries, os.path.join(output_dir, "mixed_queries.json"))
    print(f"  ✓ Mixed Workload: {len(mixed_queries)} queries")
    
    total = sum([len(exact_queries), len(prefix_queries), len(keyword_queries), len(semantic_queries), len(relationship_queries), len(multihop_queries), len(mixed_queries)])
    print(f"\n🎉 Successfully generated {total} scaled queries in {output_dir}/")
    return total

if __name__ == "__main__":
    generate_scaled_suite()
