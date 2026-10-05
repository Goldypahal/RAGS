"""
Dataset generation and utilities for RAG benchmarking.

Generates realistic research paper datasets for testing.
"""

import json
from typing import List, Dict, Any, Tuple
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.base import Document


class DatasetGenerator:
    """Generate synthetic datasets for benchmarking."""
    
    # Sample research papers dataset
    PAPERS = [
        {
            "id": "paper1",
            "title": "Attention is All You Need",
            "keywords": ["attention", "transformers", "neural networks"],
            "content": "Transformers use attention mechanisms instead of recurrence and convolution. "
                      "We propose a new simple network architecture, the Transformer, based solely on attention "
                      "mechanisms, dispensing with recurrence and convolutions entirely. Experiments on two machine "
                      "translation tasks show these models to be superior in quality while being more parallelizable "
                      "and requiring significantly less time to train.",
            "year": 2017,
            "authors": ["Vaswani", "Shazeer", "Parmar"]
        },
        {
            "id": "paper2",
            "title": "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
            "keywords": ["BERT", "language model", "pre-training", "transformers"],
            "content": "We introduce BERT, a new pre-training approach for natural language understanding which "
                      "obtains state-of-the-art results on a wide array of NLP tasks. BERT is designed to pre-train "
                      "deep bidirectional representations by jointly conditioning on both left and right context in all "
                      "layers. As a result, the pre-trained BERT representations can be fine-tuned with just one additional "
                      "output layer to create state-of-the-art models for a wide range of tasks.",
            "year": 2018,
            "authors": ["Devlin", "Chang", "Lee"]
        },
        {
            "id": "paper3",
            "title": "Language Models are Unsupervised Multitask Learners",
            "keywords": ["GPT-2", "language model", "multitask", "zero-shot"],
            "content": "GPT-2 demonstrates that language models begin learning these tasks without any explicit "
                      "supervision when trained on a new dataset of Internet text assembled as supplements to datasets "
                      "a language model has studied before. Without explicit training on these tasks and with only raw "
                      "unsupervised text and a simple text format as the interface between the tasks and the models, GPT-2 "
                      "achieves reasonable zero-shot performance on many NLP tasks.",
            "year": 2019,
            "authors": ["Radford", "Wu", "Child"]
        },
        {
            "id": "paper4",
            "title": "Language Models are Few-Shot Learners",
            "keywords": ["GPT-3", "few-shot learning", "language model"],
            "content": "Recent work has demonstrated substantial gains on many NLP tasks and benchmarks by "
                      "pre-training on a large corpus of text followed by fine-tuning on a specific task. While typically "
                      "task-agnostic in architecture, this method still requires task-specific fine-tuning datasets of "
                      "thousands or tens of thousands of examples. By contrast, humans can generally perform a new language "
                      "task from only a few examples or from simple instructions.",
            "year": 2020,
            "authors": ["Brown", "Mann", "Ryder"]
        },
        {
            "id": "paper5",
            "title": "An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale",
            "keywords": ["Vision Transformer", "image classification", "transformers"],
            "content": "While the Transformer architecture has become the de-facto standard for natural language "
                      "processing tasks, its applications to computer vision remain limited. We show that a pure transformer "
                      "applied directly to sequences of image patches can perform very well on image classification tasks. "
                      "When pre-trained on large amounts of data and transferred to multiple mid-sized or small image recognition "
                      "benchmarks, Vision Transformer (ViT) attains excellent results.",
            "year": 2021,
            "authors": ["Dosovitskiy", "Beyer", "Kolesnikov"]
        },
        {
            "id": "paper6",
            "title": "Cross-Attention in Coupled Unmixing Nets for Unsupervised Hyperspectral Super-Resolution",
            "keywords": ["attention mechanisms", "hyperspectral imaging", "super-resolution"],
            "content": "Attention mechanisms enable neural networks to focus on relevant parts of the input. "
                      "In hyperspectral imaging, attention mechanisms can improve the performance of super-resolution networks "
                      "by helping them focus on the most informative spectral bands. We propose a method using cross-attention "
                      "to couple the unmixing and super-resolution tasks.",
            "year": 2021,
            "authors": ["Li", "Wei", "Plaza"]
        },
        {
            "id": "paper7",
            "title": "DistilBERT, a distilled version of BERT: smaller, faster, cheaper and lighter",
            "keywords": ["knowledge distillation", "BERT", "model compression"],
            "content": "As Transfer Learning from large-scale pre-trained models becomes more prevalent in Natural Language "
                      "Processing (NLP), operating these large models in on-device and offline settings becomes increasingly important "
                      "for companies wanting to impact a large number of users. In this paper, we present DistilBERT, a new distilled model "
                      "which is 40% smaller than BERT and runs 60% faster while retaining 97% of BERT's language understanding capabilities.",
            "year": 2020,
            "authors": ["Sanh", "Debut", "Goyal"]
        },
        {
            "id": "paper8",
            "title": "Efficient Transformers: A Survey",
            "keywords": ["transformers", "efficiency", "survey", "optimization"],
            "content": "Transformers have become ubiquitous in NLP and beyond. However, their quadratic complexity with respect "
                      "to the sequence length has severely limited their adoption in many scenarios. In this survey, we will provide "
                      "a comprehensive overview of efficient transformer variants that have been proposed to mitigate this problem.",
            "year": 2021,
            "authors": ["Tay", "Dehghani", "Bahri"]
        },
        {
            "id": "paper9",
            "title": "Neural Machine Translation by Jointly Learning to Align and Translate",
            "keywords": ["attention mechanisms", "machine translation", "alignment"],
            "content": "Most neural machine translation systems operate with a fixed-size context vector, a bottleneck that "
                      "limits the model's ability to handle long input sentences. We propose to extend this approach by allowing the model "
                      "to automatically search for parts of a source sentence that are relevant to predicting a target word, without having "
                      "to form these parts as a hard segment explicitly.",
            "year": 2015,
            "authors": ["Bahdanau", "Cho", "Bengio"]
        },
        {
            "id": "paper10",
            "title": "Transformer-XL: Attentive Language Models Beyond a Fixed-Length Context",
            "keywords": ["transformers", "recurrence", "segment-level recurrence"],
            "content": "Transformers have been successfully applied to various NLP tasks. However, the fixed-length context in the "
                      "original Transformer prevents it from modeling longer-term dependency. We propose Transformer-XL, which combines the "
                      "merits of recurrent models and Transformers using a segment-level recurrence mechanism with relative positional encoding.",
            "year": 2019,
            "authors": ["Dai", "Yang", "Yang"]
        }
    ]
    
    @classmethod
    def generate_documents(cls, count: int = 10) -> List[Document]:
        """Generate synthetic documents."""
        documents = []
        
        for i, paper in enumerate(cls.PAPERS[:count]):
            doc = Document(
                doc_id=paper['id'],
                content=paper['content'],
                title=paper['title'],
                keywords=paper['keywords'],
                metadata={
                    'year': paper['year'],
                    'authors': paper['authors'],
                    'type': 'research_paper'
                }
            )
            documents.append(doc)
        
        return documents
    
    @classmethod
    def generate_queries(cls) -> List[Tuple[str, List[str]]]:
        """Generate test queries with ground truth."""
        return [
            ("What are transformers?", ["paper1", "paper8"]),
            ("How does attention work?", ["paper1", "paper9", "paper4"]),
            ("What is BERT?", ["paper2", "paper7"]),
            ("Language models and few-shot learning", ["paper4", "paper3"]),
            ("Efficient transformers", ["paper7", "paper8"]),
            ("Vision transformers for images", ["paper5"]),
            ("Transfer learning with BERT", ["paper2", "paper7"]),
            ("GPT models overview", ["paper3", "paper4"]),
            ("Sequence modeling", ["paper1", "paper10"]),
            ("Deep learning for NLP", ["paper1", "paper2", "paper3"]),
        ]


def load_dataset(filepath: str) -> List[Document]:
    """Load dataset from JSON file."""
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    documents = []
    for item in data:
        doc = Document(
            doc_id=item['doc_id'],
            content=item['content'],
            title=item.get('title', ''),
            keywords=item.get('keywords', []),
            metadata=item.get('metadata', {})
        )
        documents.append(doc)
    
    return documents


def save_dataset(documents: List[Document], filepath: str) -> None:
    """Save dataset to JSON file."""
    data = [doc.to_dict() for doc in documents]
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)


if __name__ == "__main__":
    # Generate and save default dataset
    docs = DatasetGenerator.generate_documents()
    print(f"Generated {len(docs)} documents")
    
    for doc in docs:
        print(f"  - {doc.title}")
    
    queries = DatasetGenerator.generate_queries()
    print(f"\nGenerated {len(queries)} test queries")
