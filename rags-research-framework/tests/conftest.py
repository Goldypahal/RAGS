import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT))
for sub in [
    "1-vector-rag", "2-graph-rag", "3-hashmap-rag", "4-trie-rag", "5-hashmap-trie-rag",
    "6-hashmap-graph-rag", "7-trie-graph-rag", "8-inverted-index-graph-rag", "9-adaptive-retrieval-rag",
]:
    sys.path.insert(0, str(ROOT / sub))
