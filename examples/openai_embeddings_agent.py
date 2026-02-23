#!/usr/bin/env python3
"""
OpenAI Embeddings Agent Example

Demonstrates the openai_embeddings tool for semantic search and similarity.

Usage:
    python examples/openai_embeddings_agent.py

Requirements:
    pip install strands-pack[openai]

Environment:
    OPENAI_API_KEY - Your OpenAI API key
"""

import json
import os
import sys
from typing import List, Tuple

# Add src to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dotenv import load_dotenv

load_dotenv()

from strands import Agent
from strands_pack import openai_embeddings


def load_knowledge_base(path: str) -> List[dict]:
    """Load FAQ knowledge base from JSON file."""
    with open(path, "r") as f:
        data = json.load(f)
    return data.get("faqs", [])


def build_index(faqs: List[dict]) -> Tuple[List[dict], List[List[float]]]:
    """Build embeddings index for FAQs using OpenAI."""
    texts = [f"{faq['question']} {faq['answer']}" for faq in faqs]

    result = openai_embeddings(action="embed_texts", texts=texts, normalize=True)
    if not result.get("success"):
        raise RuntimeError(f"Failed to embed texts: {result.get('error')}")

    return faqs, result["embeddings"]


def search(query: str, faqs: List[dict], embeddings: List[List[float]], top_k: int = 3) -> List[dict]:
    """Search for most relevant FAQs given a query."""
    result = openai_embeddings(action="embed_query", text=query, normalize=True)
    if not result.get("success"):
        raise RuntimeError(f"Failed to embed query: {result.get('error')}")

    query_embedding = result["embedding"]

    # Use the similarity action to score each FAQ
    scored = []
    for faq, emb in zip(faqs, embeddings):
        sim_result = openai_embeddings(
            action="similarity",
            embedding_a=query_embedding,
            embedding_b=emb,
        )
        if sim_result.get("success"):
            scored.append((sim_result["similarity"], faq))

    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)

    return [{"score": round(s, 4), **faq} for s, faq in scored[:top_k]]


def main():
    """Run the OpenAI embeddings demo."""
    print("=" * 60)
    print("OpenAI Embeddings - Semantic Search Demo")
    print("=" * 60)

    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("\nError: OPENAI_API_KEY environment variable not set")
        print("Set it in your .env file or export it in your shell")
        return

    # Load knowledge base
    kb_path = os.path.join(os.path.dirname(__file__), "inputs", "knowledge_base.json")
    if not os.path.exists(kb_path):
        print(f"Error: Knowledge base not found at {kb_path}")
        return

    print("\nLoading knowledge base...")
    faqs = load_knowledge_base(kb_path)
    print(f"Loaded {len(faqs)} FAQs")

    print("\nBuilding embeddings index with OpenAI...")
    try:
        faqs, embeddings = build_index(faqs)
        print(f"Index built! Embedding dimensions: {len(embeddings[0])}")
    except Exception as e:
        print(f"Error building index: {e}")
        return

    print("\n" + "-" * 60)
    print("Semantic Search Ready!")
    print("Ask questions about the knowledge base.")
    print("Type 'quit' or 'exit' to end.\n")

    while True:
        try:
            user_input = input("Query: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q"):
                print("Goodbye!")
                break

            results = search(user_input, faqs, embeddings, top_k=3)

            print(f"\nTop {len(results)} results:\n")
            for i, r in enumerate(results, 1):
                print(f"{i}. [{r['category']}] (score: {r['score']})")
                print(f"   Q: {r['question']}")
                print(f"   A: {r['answer'][:100]}...")
                print()

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
