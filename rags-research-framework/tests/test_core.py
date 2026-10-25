"""Regression tests for retrieval correctness, determinism and benchmark labels."""

import json
import os
import subprocess
import sys
import textwrap

import pytest

from conftest import ROOT
from common.base import Document, RetrievalResult, TextPreprocessor, rank_scores
from benchmark.benchmark_evaluator import MetricsCalculator


def make_docs():
    return [
        Document("d1", "Title: Attention Is All You Need\n\nThe transformer relies on attention.",
                 title="Attention Is All You Need", keywords=["transformer", "attention"]),
        Document("d2", "Title: BERT\n\nBidirectional encoder pre-training with a transformer model.",
                 title="BERT", keywords=["bert", "bidirectional"]),
        Document("d3", "Title: Seq2Seq\n\nLSTM encoder decoder for sequence learning.",
                 title="Seq2Seq", keywords=["lstm", "sequence"]),
        Document("d4", "Title: Zebra\n\nAn unrelated document about zebras and quokkas.",
                 title="Zebra", keywords=["zebra"]),
    ]


# ---------------------------------------------------------------- metrics

def test_ir_metrics_known_values():
    calc = MetricsCalculator()
    retrieved = ["a", "x", "b", "y", "z"]
    relevant = ["a", "b"]
    assert calc.calculate_precision_at_k(retrieved, relevant, 5) == pytest.approx(0.4)
    assert calc.calculate_recall_at_k(retrieved, relevant, 5) == pytest.approx(1.0)
    assert calc.calculate_mrr(["x", "a"], relevant) == pytest.approx(0.5)
    # DCG = 1 + 1/log2(4) = 1.5 ; IDCG = 1 + 1/log2(3)
    assert calc.calculate_ndcg_at_k(retrieved, relevant, 5) == pytest.approx(1.5 / (1 + 1 / 1.5849625007))


# ---------------------------------------------------------------- text + ranking

def test_tokenize_strips_punctuation():
    assert TextPreprocessor.tokenize("Transformers? BERT: pre-training!") == ["transformers", "bert", "pre", "training"]


def test_content_terms_falls_back_when_all_stopwords():
    assert TextPreprocessor.content_terms("what is the") == ["what", "is", "the"]
    assert TextPreprocessor.content_terms("what is BERT") == ["bert"]


def test_rank_scores_breaks_ties_by_doc_id():
    assert rank_scores({"b": 1.0, "a": 1.0, "c": 2.0}) == [("c", 2.0), ("a", 1.0), ("b", 1.0)]


# ---------------------------------------------------------------- systems

def test_bm25_prefers_rare_term():
    from inverted_index_graph_rag import InvertedIndex
    idx = InvertedIndex()
    for d in make_docs():
        idx.add_document(d)
    # "transformer" appears in 2 docs, "lstm" in 1 -> lstm has higher idf
    assert idx.idf("lstm") > idx.idf("transformer") > 0
    assert idx.search("lstm transformer")[0][0] == "d3"
    assert idx.search("quokkas")[0][0] == "d4"


def test_hashmap_exact_title_hit():
    from hashmap_rag import HashMapRAG
    rag = HashMapRAG()
    rag.initialize()
    rag.add_documents(make_docs())
    assert rag.retrieve("Attention Is All You Need?", top_k=3).documents[0].doc_id == "d1"


def test_hashmap_graph_retrieve_does_not_mutate_index():
    from hashmap_graph_rag import HashMapGraphRAG
    rag = HashMapGraphRAG()
    rag.initialize()
    rag.add_documents(make_docs())
    before = {k: set(v) for k, v in rag.index.entity_hashmap.items()}
    for q in ["transformer attention", "lstm model", "bert"]:
        rag.retrieve(q)
    assert rag.index.entity_hashmap == before


def test_citation_links_reach_unmatched_document():
    from graph_rag import GraphRAG
    rag = GraphRAG()
    rag.initialize()
    rag.add_documents(make_docs())
    assert "d4" not in [d.doc_id for d in rag.retrieve("lstm").documents]
    rag.add_citation_links([("d3", "d4")])
    assert "d4" in [d.doc_id for d in rag.retrieve("lstm").documents]


def test_rrf_merge_is_rank_based():
    from adaptive_rag import ContextMerger
    docs = make_docs()
    big_scale = RetrievalResult("q", [docs[0], docs[1]], [500.0, 499.0], 0.0)
    small_scale = RetrievalResult("q", [docs[1], docs[2]], [0.9, 0.1], 0.0)
    merged, _ = ContextMerger.merge({"a": big_scale, "b": small_scale}, {"a": 1.0, "b": 1.0}, top_k=3)
    # d2 is ranked by both methods, so it wins regardless of the 500x score scale gap
    assert [d.doc_id for d in merged] == ["d2", "d1", "d3"]


def test_vector_rag_tfidf_and_no_silent_fallback():
    from vector_rag import VectorRAG
    rag = VectorRAG({"embedder": "tfidf"})
    rag.initialize()
    rag.add_documents(make_docs())
    res = rag.retrieve("zebras and quokkas", top_k=2)
    assert res.documents[0].doc_id == "d4"
    assert res.metadata["embedding_model"] == "tfidf"

    try:
        import sentence_transformers  # noqa: F401
    except ImportError:
        with pytest.raises(RuntimeError, match="sentence-transformers"):
            VectorRAG()


def test_answer_em_f1():
    pytest.importorskip("torch")
    from benchmark.e2e_generation_evaluator import answer_em_f1
    assert answer_em_f1("The Eiffel Tower!", "eiffel tower") == (1.0, 1.0)
    em, f1 = answer_em_f1("Devlin et al", "Jacob Devlin")
    assert em == 0.0 and f1 == pytest.approx(0.4)  # 1 shared token: P = 1/3, R = 1/2
    assert answer_em_f1("no", "yes") == (0.0, 0.0)


DETERMINISM_SCRIPT = textwrap.dedent("""
    import json, sys
    sys.path[:0] = {paths!r}
    from common.base import Document
    from graph_rag import GraphRAG
    from hashmap_rag import HashMapRAG
    from trie_rag import TrieRAG
    from hashmap_trie_rag import HashMapTrieRAG
    from hashmap_graph_rag import HashMapGraphRAG
    from trie_graph_rag import TrieGraphRAG
    from inverted_index_graph_rag import InvertedIndexGraphRAG
    docs = [Document("p%02d" % i, "Title: t%d\\n\\nthe transformer model attention layer learning %s" % (i, "x" * i),
                     title="t%d" % i) for i in range(12)]
    out = {{}}
    for cls in [GraphRAG, HashMapRAG, TrieRAG, HashMapTrieRAG, HashMapGraphRAG, TrieGraphRAG, InvertedIndexGraphRAG]:
        r = cls(); r.initialize(); r.add_documents(docs)
        out[cls.__name__] = [[d.doc_id for d in r.retrieve(q).documents] for q in ["transformer", "attention model", "layer"]]
    print(json.dumps(out, sort_keys=True))
""")


def test_rankings_identical_across_hash_seeds():
    paths = [str(ROOT)] + [str(ROOT / p) for p in os.listdir(ROOT) if p[:1].isdigit()]
    script = DETERMINISM_SCRIPT.format(paths=paths)
    outputs = []
    for seed in ("1", "2", "3"):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        outputs.append(subprocess.run([sys.executable, "-c", script], env=env,
                                      capture_output=True, text=True, check=True).stdout)
    assert outputs[0] == outputs[1] == outputs[2]


# ---------------------------------------------------------------- benchmark labels

@pytest.fixture(scope="module")
def scaled_suite(tmp_path_factory):
    from benchmark.scale_benchmark import generate_scaled_suite
    out = tmp_path_factory.mktemp("scaled")
    generate_scaled_suite(dataset_dir=str(ROOT / "benchmark" / "dataset"), output_dir=str(out))
    return {f[:-5]: json.load(open(out / f, encoding="utf-8")) for f in os.listdir(out)}


def test_no_empty_ground_truth(scaled_suite):
    for name, tests in scaled_suite.items():
        assert all(t["expected_doc_ids"] for t in tests), name
        assert all("group" in t for t in tests), name


def test_semantic_labels_match_prompt_content(scaled_suite):
    by_query = {t["query"]: t["expected_doc_ids"] for t in scaled_suite["semantic_search"]}
    multi_head = [ids for q, ids in by_query.items() if "multi-head attention" in q]
    assert multi_head and all(ids == ["paper_001"] for ids in multi_head)
    vit = [ids for q, ids in by_query.items() if "patch-based computer vision" in q]
    assert vit and all(ids == ["paper_005"] for ids in vit)


def test_prefix_gold_contains_every_matching_title(scaled_suite):
    lang = [t for t in scaled_suite["prefix_lookup"] if t["query"] == "Language Models"]
    assert lang and sorted(lang[0]["expected_doc_ids"]) == ["paper_003", "paper_004"]
