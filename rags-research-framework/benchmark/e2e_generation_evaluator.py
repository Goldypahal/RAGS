"""
End-to-End RAG Generation & Faithfulness / Hallucination Benchmark (Phase 4).

Rigorously evaluates the downstream generative performance of all 9 RAG architectures:
1. Context Assembly: Standardized grounded prompt synthesis
2. Generation Engine: Answers generated from retrieved contexts
3. Faithfulness / Groundedness: Claim-level entailment against retrieved context
4. Hallucination Rate: Unsupported claim proportion (1.0 - Faithfulness)
5. Context Recall: Ground-truth reference fact coverage in retrieved context
6. Answer Relevance: Query-answer semantic alignment
"""

import sys
import os
import io
import time
import json
import re
import numpy as np
from typing import Dict, List, Tuple, Any, Optional, Set
from dataclasses import dataclass, field
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.base import Document, RetrievalResult


@dataclass
class GenerationResult:
    """End-to-end generation and validation result for a query."""
    query_id: str
    query: str
    query_type: str
    system_name: str
    retrieved_doc_ids: List[str]
    retrieved_contexts: List[str]
    generated_answer: str
    atomic_claims: List[str]
    supported_claims: List[str]
    unsupported_claims: List[str]
    faithfulness: float          # |supported| / |claims|
    hallucination_rate: float    # 1.0 - faithfulness
    context_recall: float        # coverage of gold facts in retrieved context
    answer_relevance: float      # query-answer alignment
    latency_ms: float


class AtomicClaimExtractor:
    """Decomposes generated text into atomic, verifiable factual propositions."""
    
    @staticmethod
    def extract_claims(text: str) -> List[str]:
        # Split text into declarative statements / clauses
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        claims = []
        for sent in sentences:
            sent = sent.strip()
            if not sent or len(sent.split()) < 3:
                continue
            # Filter non-assertive meta phrases
            if sent.lower().startswith(("i don't know", "based on", "the provided", "according to")):
                # Strip framing clause
                sent = re.sub(r'^(based on the [^,]+,\s*|according to [^,]+,\s*)', '', sent, flags=re.I)
            claims.append(sent)
        return claims if claims else [text.strip()]


class FaithfulnessVerifier:
    """
    Verifies claim entailment against retrieved context documents.
    Implements token-intersection, entity presence, and semantic containment verification.
    """
    
    STOPWORDS = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'in', 'on', 'at', 'by',
        'for', 'with', 'about', 'against', 'between', 'into', 'through', 'during',
        'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down', 'of',
        'and', 'or', 'not', 'no', 'this', 'that', 'these', 'those', 'it', 'its'
    }
    
    @classmethod
    def verify_claim(cls, claim: str, context: str) -> bool:
        """
        Verify if a factual claim is entailed by the retrieved context.
        """
        if not context:
            return False
            
        context_lower = context.lower()
        claim_lower = claim.lower()
        
        # 1. Direct substring containment
        if claim_lower in context_lower:
            return True
            
        # 2. Extract salient entities and content tokens
        tokens = [w for w in re.findall(r'\b[a-zA-Z0-9_\-\.]+\b', claim_lower) if w not in cls.STOPWORDS]
        if not tokens:
            return True
            
        # 3. Check entity containment (capitalized words, numbers, paper IDs)
        entities = re.findall(r'\b([A-Z][a-z0-9]+|\d+|paper_\d+)\b', claim)
        for ent in entities:
            if ent.lower() not in context_lower:
                # Entity hallucination detected!
                return False
                
        # 4. Check token coverage ratio (fraction of claim keywords appearing in context)
        present = sum(1 for t in tokens if t in context_lower)
        coverage = present / len(tokens)
        
        # Entailed if at least 75% of factual content tokens are attested in context
        return coverage >= 0.75


class RAGGenerator:
    """
    Standardized grounded generator.
    Given retrieved context passages, synthesizes an answer strictly grounded in the evidence.
    """
    
    @staticmethod
    def generate(query: str, retrieved_docs: List[Document]) -> str:
        if not retrieved_docs:
            return "I am unable to answer this question because no relevant context was retrieved."
            
        # Concatenate and prioritize the top passages
        combined_text = " ".join([d.content for d in retrieved_docs[:3]])
        sentences = re.split(r'(?<=[.!?])\s+', combined_text)
        
        # Query keywords
        q_words = set(re.findall(r'\b[a-zA-Z0-9]+\b', query.lower())) - FaithfulnessVerifier.STOPWORDS
        
        # Rank context sentences by overlap with query
        ranked_sents = []
        for s in sentences:
            s_clean = s.strip()
            if len(s_clean.split()) < 4:
                continue
            s_words = set(re.findall(r'\b[a-zA-Z0-9]+\b', s_clean.lower()))
            overlap = len(q_words.intersection(s_words))
            if overlap > 0:
                ranked_sents.append((overlap, s_clean))
                
        ranked_sents.sort(key=lambda x: x[0], reverse=True)
        
        if ranked_sents:
            # Take top 2-3 most relevant grounded facts
            selected = [s[1] for s in ranked_sents[:2]]
            return " ".join(selected)
        else:
            # Fallback to first available document abstract/content sentence
            first_sent = sentences[0] if sentences else ""
            return first_sent


class E2EGenerationEvaluator:
    """
    Orchestrates the complete End-to-End evaluation across all 9 RAG architectures.
    """
    
    def __init__(self):
        self.results: List[GenerationResult] = []
        
    def evaluate_query(
        self,
        query_id: str,
        query: str,
        query_type: str,
        system_name: str,
        retrieved_docs: List[Document],
        expected_facts: List[str],
        retrieval_time_ms: float,
        expected_doc_ids: Optional[List[str]] = None
    ) -> GenerationResult:
        t0 = time.perf_counter_ns()
        
        # 1. Assemble context
        context_str = "\n".join([f"[{d.doc_id}] {d.title}: {d.content}" for d in retrieved_docs])
        doc_ids = [d.doc_id for d in retrieved_docs]
        
        # 2. Generate answer
        answer = RAGGenerator.generate(query, retrieved_docs)
        
        t1 = time.perf_counter_ns()
        gen_time_ms = (t1 - t0) / 1_000_000.0
        total_time_ms = retrieval_time_ms + gen_time_ms
        
        # 3. Extract atomic claims from generated answer
        claims = AtomicClaimExtractor.extract_claims(answer)
        
        # 4. Verify faithfulness (grounding)
        supported = []
        unsupported = []
        for c in claims:
            if FaithfulnessVerifier.verify_claim(c, context_str):
                supported.append(c)
            else:
                unsupported.append(c)
                
        faithfulness = len(supported) / max(1, len(claims))
        hallucination_rate = 1.0 - faithfulness
        
        # 5. Measure Context Recall (coverage of gold documents and reference facts)
        if expected_doc_ids:
            covered = sum(1 for did in expected_doc_ids if did in doc_ids)
            context_recall = covered / len(expected_doc_ids)
        elif expected_facts:
            covered_facts = sum(
                1 for f in expected_facts 
                if FaithfulnessVerifier.verify_claim(f, context_str)
            )
            context_recall = covered_facts / len(expected_facts)
        else:
            context_recall = 1.0 if retrieved_docs else 0.0
            
        # 6. Measure Answer Relevance (overlap with query intent)
        q_tokens = set(re.findall(r'\b[a-zA-Z0-9]+\b', query.lower())) - FaithfulnessVerifier.STOPWORDS
        ans_tokens = set(re.findall(r'\b[a-zA-Z0-9]+\b', answer.lower())) - FaithfulnessVerifier.STOPWORDS
        if q_tokens and ans_tokens:
            precision = len(q_tokens.intersection(ans_tokens)) / len(ans_tokens)
            recall = len(q_tokens.intersection(ans_tokens)) / len(q_tokens)
            answer_relevance = 2 * (precision * recall) / max(1e-6, (precision + recall))
        else:
            answer_relevance = 0.0
            
        res = GenerationResult(
            query_id=query_id,
            query=query,
            query_type=query_type,
            system_name=system_name,
            retrieved_doc_ids=doc_ids,
            retrieved_contexts=[d.content for d in retrieved_docs],
            generated_answer=answer,
            atomic_claims=claims,
            supported_claims=supported,
            unsupported_claims=unsupported,
            faithfulness=round(faithfulness, 4),
            hallucination_rate=round(hallucination_rate, 4),
            context_recall=round(context_recall, 4),
            answer_relevance=round(answer_relevance, 4),
            latency_ms=round(total_time_ms, 3)
        )
        self.results.append(res)
        return res
        
    def summarize(self) -> Dict[str, Any]:
        """Aggregate results across architectures and query types."""
        systems = set(r.system_name for r in self.results)
        query_types = set(r.query_type for r in self.results)
        
        system_summary = {}
        for s in systems:
            s_res = [r for r in self.results if r.system_name == s]
            system_summary[s] = {
                'total_queries': len(s_res),
                'mean_faithfulness': round(float(np.mean([r.faithfulness for r in s_res])), 4),
                'mean_hallucination_rate': round(float(np.mean([r.hallucination_rate for r in s_res])), 4),
                'mean_context_recall': round(float(np.mean([r.context_recall for r in s_res])), 4),
                'mean_answer_relevance': round(float(np.mean([r.answer_relevance for r in s_res])), 4),
                'mean_latency_ms': round(float(np.mean([r.latency_ms for r in s_res])), 3),
                'by_query_type': {}
            }
            for qt in query_types:
                sq_res = [r for r in s_res if r.query_type == qt]
                if sq_res:
                    system_summary[s]['by_query_type'][qt] = {
                        'faithfulness': round(float(np.mean([r.faithfulness for r in sq_res])), 4),
                        'hallucination_rate': round(float(np.mean([r.hallucination_rate for r in sq_res])), 4),
                        'context_recall': round(float(np.mean([r.context_recall for r in sq_res])), 4)
                    }
                    
        return {
            'total_evaluations': len(self.results),
            'system_rankings_by_faithfulness': sorted(
                system_summary.keys(),
                key=lambda s: system_summary[s]['mean_faithfulness'],
                reverse=True
            ),
            'system_rankings_by_hallucination_rate': sorted(
                system_summary.keys(),
                key=lambda s: system_summary[s]['mean_hallucination_rate']
            ),
            'systems': system_summary
        }
