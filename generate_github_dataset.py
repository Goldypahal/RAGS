import os
import json
import ast
from pathlib import Path
import random

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def save_json(data, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def generate_github_dataset(repo_path: str, output_dir: str):
    """Parses a local python repository into the Benchmark format"""
    print(f"Parsing repository {repo_path}...")
    ensure_dir(output_dir)
    
    documents = [] # maps to papers
    modules_dict = {} # maps to authors
    folders_dict = {} # maps to topics
    imports_list = [] # maps to citations
    
    base_path = Path(repo_path)
    if not base_path.exists():
        print(f"Repo {repo_path} not found!")
        return
        
    for py_file in base_path.rglob("*.py"):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            rel_path = py_file.relative_to(base_path).as_posix()
            doc_id = f"file_{rel_path.replace('/', '_').replace('.', '_')}"
            
            # Module name (e.g., flask.app)
            module_name = rel_path.replace('/', '.').replace('.py', '')
            if module_name.endswith('.__init__'):
                module_name = module_name[:-9]
                
            # Folder name as topic
            folder = py_file.parent.name
            
            # Parse AST to get imports and functions
            try:
                tree = ast.parse(content)
            except SyntaxError:
                continue
                
            imported_modules = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imported_modules.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imported_modules.append(node.module)
            
            doc = {
                "id": doc_id,
                "title": rel_path,
                "abstract": f"Python source code file {rel_path}",
                "content": content,
                "year": 2024,
                "authors": [module_name], # using module as author
                "topics": [folder], # using folder as topic
                "citations_count": len(imported_modules),
                "_raw_imports": imported_modules
            }
            documents.append(doc)
            
            # Build authors (modules)
            if module_name not in modules_dict:
                modules_dict[module_name] = {"id": f"author_{module_name}", "name": module_name, "papers": []}
            modules_dict[module_name]["papers"].append(doc_id)
            
            # Build topics (folders)
            t_id = f"topic_{folder}"
            if t_id not in folders_dict:
                folders_dict[t_id] = {"id": t_id, "name": folder, "papers": []}
            folders_dict[t_id]["papers"].append(doc_id)
            
        except Exception as e:
            pass

    # Build citations (imports)
    # We need to map module names back to file doc_ids
    module_to_doc = {list(v["papers"])[0]: k for k, v in modules_dict.items() if v["papers"]}
    name_to_doc = {k: list(v["papers"])[0] for k, v in modules_dict.items() if v["papers"]}
    
    for doc in documents:
        for imp in doc["_raw_imports"]:
            # Basic matching
            target_doc_id = name_to_doc.get(imp)
            if target_doc_id and target_doc_id != doc["id"]:
                imports_list.append({
                    "source": doc["id"],
                    "target": target_doc_id,
                    "context": f"File {doc['title']} imports module {imp}"
                })
        del doc["_raw_imports"] # Clean up
        
    # Save datasets
    save_json(documents, os.path.join(output_dir, "papers.json"))
    save_json(list(modules_dict.values()), os.path.join(output_dir, "authors.json"))
    save_json(list(folders_dict.values()), os.path.join(output_dir, "topics.json"))
    save_json(imports_list, os.path.join(output_dir, "citations.json"))
    
    # Create some test queries
    ensure_dir(os.path.join(output_dir, "tests"))
    
    # Semantic search
    semantic_tests = []
    for d in random.sample(documents, min(20, len(documents))):
        query = f"How is {d['title']} implemented?"
        semantic_tests.append({"id": f"sem_{d['id']}", "query": query, "expected_ids": [d['id']], "type": "semantic"})
    save_json(semantic_tests, os.path.join(output_dir, "tests", "semantic_search.json"))
    
    # Exact lookup
    exact_tests = []
    for d in random.sample(documents, min(20, len(documents))):
        exact_tests.append({"id": f"ex_{d['id']}", "query": d['title'], "expected_ids": [d['id']], "type": "exact"})
    save_json(exact_tests, os.path.join(output_dir, "tests", "exact_lookup.json"))
    
    print(f"GitHub Repo: {len(documents)} files parsed and saved.")

if __name__ == "__main__":
    import sys
    repo = sys.argv[1] if len(sys.argv) > 1 else r"g:\Desktop\RAGS\Dataset\flask_repo"
    out_dir = sys.argv[2] if len(sys.argv) > 2 else r"g:\Desktop\RAGS\Dataset\GitHubRepos"
    generate_github_dataset(repo, out_dir)
