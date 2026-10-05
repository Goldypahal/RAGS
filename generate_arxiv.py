import os
import json
import random

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def save_json(data, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def generate_research_papers(output_dir: str):
    print("Generating Research Papers dataset (using arxiv API)...")
    ensure_dir(output_dir)
    try:
        import arxiv
        import time
        
        client = arxiv.Client(
            page_size = 50,
            delay_seconds = 3,
            num_retries = 5
        )
        
        search = arxiv.Search(
            query = "cat:cs.AI",
            max_results = 200, # Smaller batch to prevent timeout
            sort_by = arxiv.SortCriterion.SubmittedDate
        )
        
        papers = []
        authors_dict = {}
        topics_dict = {}
        
        print("Fetching papers from arXiv...")
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
                "citations_count": random.randint(0, 100)
            }
            papers.append(paper)
            
            for author_name in paper['authors']:
                a_id = f"author_{hash(author_name) % 100000}"
                if a_id not in authors_dict:
                    authors_dict[a_id] = {"id": a_id, "name": author_name, "papers": []}
                authors_dict[a_id]["papers"].append(paper_id)
                
            for topic_name in paper['topics']:
                t_id = f"topic_{topic_name.replace('.', '_')}"
                if t_id not in topics_dict:
                    topics_dict[t_id] = {"id": t_id, "name": topic_name, "papers": []}
                topics_dict[t_id]["papers"].append(paper_id)
        
        save_json(papers, os.path.join(output_dir, "papers.json"))
        save_json(list(authors_dict.values()), os.path.join(output_dir, "authors.json"))
        save_json(list(topics_dict.values()), os.path.join(output_dir, "topics.json"))
        
        citations = []
        for p in papers:
            if random.random() < 0.3:
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
        
        ensure_dir(os.path.join(output_dir, "tests"))
        
        semantic_tests = []
        for p in random.sample(papers, min(50, len(papers))):
            query = f"Papers about {p['title'].split()[:3]} and {p['topics'][0] if p['topics'] else 'ML'}"
            semantic_tests.append({"id": f"sem_{p['id']}", "query": query, "expected_ids": [p['id']], "type": "semantic"})
        save_json(semantic_tests, os.path.join(output_dir, "tests", "semantic_search.json"))
        
        exact_tests = []
        for p in random.sample(papers, min(50, len(papers))):
            exact_tests.append({"id": f"ex_{p['id']}", "query": p['title'], "expected_ids": [p['id']], "type": "exact"})
        save_json(exact_tests, os.path.join(output_dir, "tests", "exact_lookup.json"))
        
        print(f"Research Papers: {len(papers)} papers saved.")
    except Exception as e:
        print(f"Error generating Research Papers: {e}")

if __name__ == "__main__":
    generate_research_papers(r"g:\Desktop\RAGS\Dataset\ResearchPapers")
