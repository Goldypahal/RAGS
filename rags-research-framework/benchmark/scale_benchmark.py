"""
Scale Benchmark: template-generated multi-category query suite over benchmark/dataset.

Generates up to 100 distinct query strings per category:
1. Exact Lookup        2. Prefix Lookup       3. Keyword Search
4. Semantic Search     5. Relationship Search 6. Multi-Hop Reasoning
7. Mixed Realistic Workload

Caveat: the corpus has 10 papers, so each category is ~10 anchor papers x ~10
templates. Queries sharing an anchor are strongly correlated; treat the effective
sample size as closer to the number of anchors than the number of queries, and
split by the "group" field (anchor paper) when training anything on these queries.

Ground truth is derived from the data, never from list position:
- semantic: hand-mapped prompt -> paper (by abstract content)
- relationship: venue/year/author metadata and citations.json, per template
- multi-hop: anchor paper plus its 1-hop citation neighbors
Queries whose ground truth would be empty are skipped.
"""

import os
import re
import sys
import io
import json
import random
from pathlib import Path
from typing import List, Dict, Any, Set

_STOP = {
    'the', 'a', 'an', 'and', 'or', 'of', 'for', 'in', 'on', 'at', 'to', 'with', 'by',
    'is', 'are', 'from', 'as', 'terms', 'keyword', 'lookup', 'ref'
}


def _tokens(text: str) -> Set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOP and not t.isdigit()}

# Ensure UTF-8 output on Windows consoles
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def save_json(data: Any, path: str):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def generate_scaled_suite(dataset_dir: str = "benchmark/dataset", output_dir: str = "benchmark/tests/scaled"):
    """Generate 700 completely unique benchmark queries across 7 categories."""
    ensure_dir(output_dir)
    random.seed(42)
    
    papers_path = os.path.join(dataset_dir, "papers.json")
    with open(papers_path, 'r', encoding='utf-8') as f:
        papers = json.load(f)
        
    try:
        with open(os.path.join(dataset_dir, "citations.json"), 'r', encoding='utf-8') as f:
            citations = json.load(f)
    except Exception:
        citations = []
        
    try:
        with open(os.path.join(dataset_dir, "authors.json"), 'r', encoding='utf-8') as f:
            authors = json.load(f)
    except Exception:
        authors = []
        
    paper_map = {p['id']: p for p in papers}
    paper_ids = [p['id'] for p in papers]

    cites: Dict[str, List[str]] = {pid: [] for pid in paper_ids}     # pid -> papers it cites
    cited_by: Dict[str, List[str]] = {pid: [] for pid in paper_ids}  # pid -> papers citing it
    for cit in citations:
        a, b = cit.get('citing_paper'), cit.get('cited_paper')
        if a in paper_map and b in paper_map:
            cites[a].append(b)
            cited_by[b].append(a)

    def neighbors(pid: str) -> List[str]:
        return sorted(set(cites[pid]) | set(cited_by[pid]))

    def by_author(author: str) -> List[str]:
        return [p['id'] for p in papers if author in (p.get('authors') or [])]

    all_seen_queries: Set[str] = set()
    
    # -------------------------------------------------------------
    # 1. Exact Lookup (100 unique queries)
    # -------------------------------------------------------------
    exact_queries = []
    exact_templates = [
        "What is {title}?",
        "Paper: {title}",
        "{title}",
        "Explain {title}",
        "Lookup document {id}: {title}",
        "Retrieve exact paper {title}",
        "Find publication record for {title}",
        "Canonical entry for {title}",
        "Definition of {title}",
        "Exact match search for {title}"
    ]
    for idx in range(100):
        paper = papers[idx % len(papers)]
        tmpl = exact_templates[(idx // len(papers)) % len(exact_templates)]
        q_text = tmpl.format(title=paper['title'], id=paper['id'])
        if q_text in all_seen_queries:
            q_text = f"Exact reference [{paper['id']}]: {paper['title']} (variant {idx})"
        all_seen_queries.add(q_text)
        exact_queries.append({
            "id": f"exact_{idx+1:03d}",
            "query": q_text,
            "expected_doc_ids": [paper['id']],
            "type": "exact_lookup",
            "difficulty": "easy",
            "group": paper['id']
        })
    save_json(exact_queries, os.path.join(output_dir, "exact_lookup.json"))
    print(f"  ✓ Exact Lookup: {len(exact_queries)} unique queries")

    # -------------------------------------------------------------
    # 2. Prefix Lookup (100 unique queries)
    # -------------------------------------------------------------
    prefix_queries = []
    for idx in range(100):
        paper = papers[idx % len(papers)]
        title = paper['title']
        words = title.split()
        
        step = (idx // len(papers)) % 10
        if step == 0:
            prefix_phrase = words[0][:min(len(words[0]), 4 + (idx % 3))]
        elif step < 5:
            n_words = min(len(words), step + 1)
            prefix_phrase = " ".join(words[:n_words])
        else:
            # Character prefixes of the title that may end mid-word: 6, 9, 12, 15, 18 chars
            prefix_phrase = title[:6 + 3 * (step - 5)].rstrip()

        if prefix_phrase in all_seen_queries:
            continue
        all_seen_queries.add(prefix_phrase)

        # Every title with this prefix is a correct completion (e.g. "Language Models" -> 003 and 004)
        prefix_lower = prefix_phrase.lower()
        gold = [paper['id']] + sorted(
            p['id'] for p in papers
            if p['id'] != paper['id'] and p['title'].lower().startswith(prefix_lower)
        )

        prefix_queries.append({
            "id": f"prefix_{idx+1:03d}",
            "query": prefix_phrase,
            "expected_doc_ids": gold,
            "type": "prefix_lookup",
            "difficulty": "medium",
            "group": paper['id']
        })
    save_json(prefix_queries, os.path.join(output_dir, "prefix_lookup.json"))
    print(f"  ✓ Prefix Lookup: {len(prefix_queries)} unique queries")

    # -------------------------------------------------------------
    # 3. Keyword Search (100 unique queries)
    # -------------------------------------------------------------
    keyword_queries = []
    for idx in range(100):
        paper = papers[idx % len(papers)]
        keywords = paper.get('keywords', paper.get('topics', []))
        if not keywords:
            keywords = [w for w in paper['title'].split() if len(w) > 3]
            
        k_count = 2 + (idx % 2)
        sample_kws = random.sample(keywords, min(len(keywords), k_count))
        venue = paper.get('venue', '')
        year = str(paper.get('year', ''))
        
        tag = (idx // len(papers))
        if tag == 0:
            q_text = " ".join(sample_kws)
        elif tag == 1:
            q_text = f"{' '.join(sample_kws)} {year}"
        elif tag == 2:
            q_text = f"{venue} {' '.join(sample_kws)}"
        elif tag == 3:
            q_text = f"keyword lookup: {' '.join(sample_kws)}"
        else:
            q_text = f"{' '.join(sample_kws)} terms {idx}"
            
        if q_text in all_seen_queries:
            q_text = f"{q_text} ref_{idx}"
        all_seen_queries.add(q_text)
        
        # Relevant = papers sharing whole content tokens with the query via title/keywords,
        # ranked by overlap; the anchor paper is always included.
        q_tokens = _tokens(" ".join(sample_kws))
        overlaps = []
        for p in papers:
            p_tokens = _tokens(p['title'] + " " + " ".join(p.get('keywords', [])))
            n = len(q_tokens & p_tokens)
            if n and p['id'] != paper['id']:
                overlaps.append((-n, p['id']))
        matches = [paper['id']] + [pid for _, pid in sorted(overlaps)]

        keyword_queries.append({
            "id": f"keyword_{idx+1:03d}",
            "query": q_text,
            "expected_doc_ids": matches[:5],
            "type": "keyword_search",
            "difficulty": "medium",
            "group": paper['id']
        })
    save_json(keyword_queries, os.path.join(output_dir, "keyword_search.json"))
    print(f"  ✓ Keyword Search: {len(keyword_queries)} unique queries")

    # -------------------------------------------------------------
    # 4. Semantic Search (100 unique queries)
    # -------------------------------------------------------------
    semantic_queries = []
    semantic_prompts = [
        "How do self-attention mechanisms replace recurrence in sequence modeling?",
        "Explain the impact of bidirectional context representations on language understanding.",
        "What allows large language models to generalize across tasks in zero-shot settings?",
        "How does in-context few-shot prompting eliminate task-specific parameter fine-tuning?",
        "Describe the adaptation of pure transformer architectures to patch-based computer vision.",
        "How does masked language modeling train deep bidirectional encoders?",
        "What are the scaling laws governing parameter count in multi-layer transformer models?",
        "Explain how multi-head attention projects inputs into multiple representation subspaces.",
        "What advantages do feed-forward self-attention networks possess over traditional LSTMs?",
        "Discuss task-agnostic few-shot performance in autoregressive language generators."
    ]
    variations = [
        "In deep learning literature, {p}",
        "Provide a comprehensive technical overview: {p}",
        "What theoretical evidence demonstrates that: {p}",
        "Survey findings regarding: {p}",
        "Empirical analysis: {p}",
        "Explain clearly: {p}",
        "From an architectural perspective: {p}",
        "Review modern methodologies: {p}",
        "Detailed investigation into: {p}",
        "Scientific inquiry: {p}"
    ]
    
    # Hand-mapped from each prompt's content to the paper whose abstract answers it.
    # (Previously papers[idx % N], i.e. prompts 5-9 were labeled with unrelated papers 006-010.)
    semantic_targets = [
        "paper_001",  # self-attention replacing recurrence -> Attention Is All You Need
        "paper_002",  # bidirectional context representations -> BERT
        "paper_003",  # zero-shot generalization -> GPT-2
        "paper_004",  # in-context few-shot without fine-tuning -> GPT-3
        "paper_005",  # pure transformer on image patches -> ViT
        "paper_002",  # masked language modeling, bidirectional encoders -> BERT
        "paper_004",  # scaling up parameter count -> GPT-3
        "paper_001",  # multi-head attention subspaces -> Attention Is All You Need
        "paper_001",  # self-attention vs LSTMs -> Attention Is All You Need
        "paper_004",  # task-agnostic few-shot autoregressive -> GPT-3
    ]
    assert len(semantic_targets) == len(semantic_prompts)

    for idx in range(100):
        prompt_idx = idx % len(semantic_prompts)
        base_prompt = semantic_prompts[prompt_idx]
        var_tmpl = variations[(idx // len(semantic_prompts)) % len(variations)]
        q_text = var_tmpl.format(p=base_prompt)

        if q_text in all_seen_queries:
            continue
        all_seen_queries.add(q_text)

        target_id = semantic_targets[prompt_idx]
        if target_id not in paper_map:
            continue
        semantic_queries.append({
            "id": f"semantic_{idx+1:03d}",
            "query": q_text,
            "expected_doc_ids": [target_id],
            "type": "semantic_search",
            "difficulty": "hard",
            "group": f"prompt_{prompt_idx}"
        })
    save_json(semantic_queries, os.path.join(output_dir, "semantic_search.json"))
    print(f"  ✓ Semantic Search: {len(semantic_queries)} unique queries")

    # -------------------------------------------------------------
    # 5. Relationship Search (100 unique queries)
    # -------------------------------------------------------------
    relationship_queries = []
    rel_templates = [
        "Which papers were published at {venue} in {year}?",
        "Find all works authored or co-authored by {author}.",
        "What papers cite or directly build upon {title}?",
        "Identify direct citation links originating from {title}.",
        "Which models in the citation network reference {author}?",
        "List research publications presented at {venue}.",
        "Trace the co-authorship network of {author}.",
        "Which foundational models cite {title} as prior art?",
        "Find papers connected to {topic} at {venue}.",
        "List all citations connecting {title} to subsequent publications."
    ]
    for idx in range(100):
        paper = papers[idx % len(papers)]
        pid = paper['id']
        venue = paper.get('venue', 'NeurIPS')
        year = paper.get('year', 2020)
        auth = (paper.get('authors') or ['Vaswani, A.'])[0]
        topic = (paper.get('topics') or ['transformers'])[0]
        t_idx = (idx // len(papers)) % len(rel_templates)
        tmpl = rel_templates[t_idx]

        q_text = tmpl.format(venue=venue, year=year, author=auth, title=paper['title'], topic=topic)
        if q_text in all_seen_queries:
            continue

        # Ground truth follows what the template actually asks for
        if t_idx == 0:    # published at {venue} in {year}
            gold = [p['id'] for p in papers if p.get('venue') == venue and p.get('year') == year]
        elif t_idx in (1, 6):  # works / co-authorship network of {author}
            gold = by_author(auth)
        elif t_idx in (2, 7, 9):  # papers citing {title}
            gold = sorted(cited_by[pid])
        elif t_idx == 3:  # citations originating from {title}
            gold = sorted(cites[pid])
        elif t_idx == 4:  # papers citing any work by {author}
            gold = sorted({c for a in by_author(auth) for c in cited_by[a]})
        elif t_idx == 5:  # presented at {venue}
            gold = [p['id'] for p in papers if p.get('venue') == venue]
        else:             # connected to {topic} at {venue}
            gold = [p['id'] for p in papers
                    if p.get('venue') == venue and topic in (p.get('topics') or [])]
        if not gold:
            continue
        all_seen_queries.add(q_text)

        relationship_queries.append({
            "id": f"relation_{idx+1:03d}",
            "query": q_text,
            "expected_doc_ids": gold,
            "type": "relationship_search",
            "difficulty": "medium",
            "group": pid
        })
    save_json(relationship_queries, os.path.join(output_dir, "relationship_search.json"))
    print(f"  ✓ Relationship Search: {len(relationship_queries)} unique queries")

    # -------------------------------------------------------------
    # 6. Multi-Hop Reasoning (100 unique queries)
    # -------------------------------------------------------------
    multi_hop_queries = []
    mh_templates = [
        "If BERT builds on {title}, what subsequent model scaled this architecture to 175B parameters?",
        "Trace the influence path from {author} through GPT-2 to Vision Transformers.",
        "What common architectural principle links {title} to subsequent autoregressive models?",
        "Connect {author}'s self-attention to {venue} publications in {year}.",
        "Follow the citation path from {title} through bidirectional modeling to modern LLMs.",
        "How did innovations in {title} enable zero-shot multitask learners?",
        "Identify the lineage from recurrent replacement in {year} to vision patch processing.",
        "Which authors of {title} influenced transformer scaling laws in {venue}?",
        "Connect multi-head attention in {title} to masked pre-training architectures.",
        "What 2-hop sequence connects {author} to vision recognition transformers?"
    ]
    for idx in range(100):
        paper = papers[idx % len(papers)]
        auth = (paper.get('authors') or ['Vaswani, A.'])[0]
        venue = paper.get('venue', 'NeurIPS')
        year = paper.get('year', 2017)
        tmpl = mh_templates[(idx // len(papers)) % len(mh_templates)]
        
        q_text = tmpl.format(title=paper['title'], author=auth, venue=venue, year=year)
        if q_text in all_seen_queries:
            continue
        all_seen_queries.add(q_text)

        # Expected papers: the anchor plus its real 1-hop citation neighbors
        # (previously: the next paper in file order, which is not a hop)
        multi_hop_queries.append({
            "id": f"multihop_{idx+1:03d}",
            "query": q_text,
            "expected_doc_ids": [paper['id']] + neighbors(paper['id']),
            "type": "multi_hop_reasoning",
            "difficulty": "hard",
            "group": paper['id']
        })
    save_json(multi_hop_queries, os.path.join(output_dir, "multi_hop_reasoning.json"))
    print(f"  ✓ Multi-Hop Reasoning: {len(multi_hop_queries)} unique queries")

    # -------------------------------------------------------------
    # 7. Mixed Realistic Workload (100 unique queries)
    # -------------------------------------------------------------
    mixed_queries = []
    mixed_templates = [
        "Lookup paper {title} and its citations at {venue}",
        "{author} {title} transformer model",
        "Prefix search: {prefix} with keyword {keyword}",
        "Does {title} compare self-attention to LSTMs in {year}?",
        "Find paper {id} mentioning {topic}",
        "What are the main results of {title} published in {venue}?",
        "Survey of {topic} models citing {title}",
        "Exact title {title} with year filter {year}",
        "Abstract summary for {title} by {author}",
        "Multi-modal application of {title} architecture"
    ]
    for idx in range(100):
        paper = papers[idx % len(papers)]
        auth = (paper.get('authors') or ['Vaswani, A.'])[0].split(',')[0]
        venue = paper.get('venue', 'NeurIPS')
        year = paper.get('year', 2017)
        words = paper['title'].split()
        prefix = " ".join(words[:min(2, len(words))])
        kws = paper.get('keywords', ['attention'])
        topic = (paper.get('topics') or ['NLP'])[0]
        tmpl = mixed_templates[(idx // len(papers)) % len(mixed_templates)]
        
        q_text = tmpl.format(
            title=paper['title'],
            author=auth,
            venue=venue,
            year=year,
            prefix=prefix,
            keyword=kws[0] if kws else 'attention',
            id=paper['id'],
            topic=topic
        )
        if q_text in all_seen_queries:
            continue
        all_seen_queries.add(q_text)

        mixed_queries.append({
            "id": f"mixed_{idx+1:03d}",
            "query": q_text,
            "expected_doc_ids": [paper['id']],
            "type": "mixed_queries",
            "difficulty": "medium",
            "group": paper['id']
        })
    save_json(mixed_queries, os.path.join(output_dir, "mixed_queries.json"))
    print(f"  ✓ Mixed Workload: {len(mixed_queries)} unique queries")
    
    n_groups = len({p['id'] for p in papers})
    print(f"\n🎉 Generated {len(all_seen_queries)} unique query strings across 7 suites "
          f"(anchored on {n_groups} papers; see module docstring on effective sample size)")


if __name__ == "__main__":
    generate_scaled_suite()
