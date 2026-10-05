import os
import json
import random
from typing import List, Dict, Any

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def save_json(data, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def generate_hotpot_qa(output_dir: str):
    """Generate HotpotQA benchmark dataset"""
    print("Generating HotpotQA dataset...")
    ensure_dir(output_dir)
    try:
        from datasets import load_dataset
        # Load a small portion of HotpotQA for benchmarking
        dataset = load_dataset("hotpot_qa", "distractor", split="validation[:500]")
        
        documents = []
        tests = []
        
        doc_map = {}
        for item in dataset:
            test_id = item['id']
            question = item['question']
            answer = item['answer']
            
            # Extract supporting facts
            supporting_facts = set(item['supporting_facts']['title'])
            expected_ids = []
            
            # Extract context paragraphs
            for title, sentences in zip(item['context']['title'], item['context']['sentences']):
                doc_id = f"hotpot_{title.replace(' ', '_')}"
                if doc_id not in doc_map:
                    doc = {
                        "id": doc_id,
                        "title": title,
                        "content": " ".join(sentences),
                        "type": "wikipedia_article"
                    }
                    documents.append(doc)
                    doc_map[doc_id] = doc
                
                if title in supporting_facts:
                    expected_ids.append(doc_id)
            
            tests.append({
                "id": test_id,
                "query": question,
                "answer": answer,
                "expected_ids": expected_ids,
                "type": "multi_hop"
            })
            
        save_json(documents, os.path.join(output_dir, "papers.json"))
        ensure_dir(os.path.join(output_dir, "tests"))
        save_json(tests, os.path.join(output_dir, "tests", "multi_hop_reasoning.json"))
        print(f"HotpotQA: {len(documents)} documents, {len(tests)} tests saved.")
    except Exception as e:
        print(f"Error generating HotpotQA: {e}")

def generate_squad(output_dir: str):
    """Generate SQuAD benchmark dataset"""
    print("Generating SQuAD dataset...")
    ensure_dir(output_dir)
    try:
        from datasets import load_dataset
        dataset = load_dataset("squad", split="validation[:1000]")
        
        documents = []
        tests = []
        doc_map = {}
        
        for i, item in enumerate(dataset):
            test_id = item['id']
            question = item['question']
            context = item['context']
            
            # Using hash of context as doc ID to avoid duplicates
            import hashlib
            doc_id = f"squad_{hashlib.md5(context.encode()).hexdigest()[:10]}"
            
            if doc_id not in doc_map:
                doc = {
                    "id": doc_id,
                    "title": item['title'],
                    "content": context,
                    "type": "fact_retrieval"
                }
                documents.append(doc)
                doc_map[doc_id] = doc
            
            tests.append({
                "id": test_id,
                "query": question,
                "expected_ids": [doc_id],
                "type": "single_hop"
            })
            
        save_json(documents, os.path.join(output_dir, "documents.json"))
        ensure_dir(os.path.join(output_dir, "tests"))
        save_json(tests, os.path.join(output_dir, "tests", "fact_retrieval.json"))
        print(f"SQuAD: {len(documents)} documents, {len(tests)} tests saved.")
    except Exception as e:
        print(f"Error generating SQuAD: {e}")

def generate_research_papers(output_dir: str):
    """Generate Research Papers dataset using official arxiv API"""
    print("Generating Research Papers dataset (using arxiv API)...")
    ensure_dir(output_dir)
    try:
        import arxiv
        import time
        
        # Construct the default API client.
        client = arxiv.Client(
            page_size = 100,
            delay_seconds = 3,
            num_retries = 3
        )
        
        # Search for ML/AI papers
        search = arxiv.Search(
            query = "cat:cs.AI OR cat:cs.LG OR cat:cs.CV",
            max_results = 2000,
            sort_by = arxiv.SortCriterion.SubmittedDate
        )
        
        papers = []
        authors_dict = {}
        topics_dict = {}
        
        print("Fetching papers from arXiv (this might take a minute)...")
        results = list(client.results(search))
        
        for item in results:
            paper_id = f"arxiv_{item.get_short_id()}"
            authors_list = [a.name for a in item.authors]
            categories = item.categories
            
            paper = {
                "id": paper_id,
                "title": item.title,
                "abstract": item.summary.replace("\n", " "),
                "content": item.title + "\n" + item.summary.replace("\n", " "),
                "year": item.published.year if item.published else 2023,
                "authors": authors_list,
                "topics": categories,
                "citations_count": random.randint(0, 100) # Mock since it's not in this dataset
            }
            papers.append(paper)
            
            # Build authors
            for author_name in paper['authors']:
                a_id = f"author_{hash(author_name) % 100000}"
                if a_id not in authors_dict:
                    authors_dict[a_id] = {"id": a_id, "name": author_name, "papers": []}
                authors_dict[a_id]["papers"].append(paper_id)
                
            # Build topics
            for topic_name in paper['topics']:
                t_id = f"topic_{topic_name.replace('.', '_')}"
                if t_id not in topics_dict:
                    topics_dict[t_id] = {"id": t_id, "name": topic_name, "papers": []}
                topics_dict[t_id]["papers"].append(paper_id)
        
        # Save datasets
        save_json(papers, os.path.join(output_dir, "papers.json"))
        save_json(list(authors_dict.values()), os.path.join(output_dir, "authors.json"))
        save_json(list(topics_dict.values()), os.path.join(output_dir, "topics.json"))
        
        # Generate citations (mock graph connections)
        citations = []
        for p in papers:
            if random.random() < 0.3: # 30% chance to cite something
                num_citations = random.randint(1, 5)
                targets = random.sample(papers, num_citations)
                for t in targets:
                    if t['id'] != p['id']:
                        citations.append({
                            "source": p['id'],
                            "target": t['id'],
                            "context": f"As shown in {t['title']}, this is effective."
                        })
        save_json(citations, os.path.join(output_dir, "citations.json"))
        
        # Create some test queries
        ensure_dir(os.path.join(output_dir, "tests"))
        
        # Semantic search
        semantic_tests = []
        for p in random.sample(papers, min(50, len(papers))):
            query = f"Papers about {p['title'].split()[:3]} and {p['topics'][0] if p['topics'] else 'ML'}"
            semantic_tests.append({"id": f"sem_{p['id']}", "query": query, "expected_ids": [p['id']], "type": "semantic"})
        save_json(semantic_tests, os.path.join(output_dir, "tests", "semantic_search.json"))
        
        # Exact lookup
        exact_tests = []
        for p in random.sample(papers, min(50, len(papers))):
            exact_tests.append({"id": f"ex_{p['id']}", "query": p['title'], "expected_ids": [p['id']], "type": "exact"})
        save_json(exact_tests, os.path.join(output_dir, "tests", "exact_lookup.json"))
        
        print(f"Research Papers: {len(papers)} papers saved.")
    except Exception as e:
        print(f"Error generating Research Papers: {e}")

if __name__ == "__main__":
    base_dir = r"g:\Desktop\RAGS\Dataset"
    ensure_dir(base_dir)
    
    print("--- Starting Dataset Generation ---")
    generate_hotpot_qa(os.path.join(base_dir, "HotpotQA"))
    # generate_squad(os.path.join(base_dir, "SQuAD"))
    # generate_research_papers(os.path.join(base_dir, "ResearchPapers"))
    print("--- Finished ---")
