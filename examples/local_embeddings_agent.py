#!/usr/bin/env python3
"""
Local Embeddings Agent Example

Demonstrates a realistic RAG-style agent using:
- local embeddings (no API keys)
- a persistent vector DB (ChromaDB)
- a Strands `Agent` that retrieves context by calling the tools directly

Usage:
    python examples/local_embeddings_agent.py

Requirements:
    pip install "strands-pack[local_embeddings,chromadb]"

Notes:
    This example uses a Strands `Agent`, which requires an LLM configured for Strands
    in your environment. Retrieval (embeddings + Chroma) is local/offline.
"""

import json
import os
import sys
from typing import List

# Add src to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dotenv import load_dotenv

load_dotenv()

from strands import Agent
from strands_pack import chromadb_tool, local_embeddings


def load_knowledge_base(path: str) -> List[dict]:
    """Load FAQ knowledge base from JSON file."""
    with open(path, "r") as f:
        data = json.load(f)
    return data.get("faqs", [])


def _collection_name(kb_path: str) -> str:
    base = os.path.splitext(os.path.basename(kb_path))[0]
    # Chroma collection naming is fairly permissive; keep it simple.
    return f"kb_{base}_faqs"


def build_or_update_index(faqs: List[dict], kb_path: str) -> dict:
    """Build (or upsert) a persistent ChromaDB index for FAQs."""
    name = _collection_name(kb_path)

    # Ensure collection exists
    res = chromadb_tool(action="get_or_create_collection", name=name, metadata={"source": kb_path, "type": "faq"})
    if not res.get("success"):
        raise RuntimeError(f"Failed to create/get collection: {res.get('error')}")

    # Embed docs locally (normalized vectors are helpful for stable similarity behavior)
    docs = [f"Q: {faq.get('question','')}\nA: {faq.get('answer','')}" for faq in faqs]
    emb = local_embeddings(action="embed_texts", texts=docs, normalize=True)
    if not emb.get("success"):
        raise RuntimeError(f"Failed to embed texts: {emb.get('error')}")

    ids = [f"faq-{i}" for i in range(len(faqs))]
    metadatas = [
        {
            "category": faq.get("category"),
            "question": faq.get("question"),
            "answer": faq.get("answer"),
        }
        for faq in faqs
    ]

    up = chromadb_tool(
        action="upsert",
        collection=name,
        ids=ids,
        documents=docs,
        embeddings=emb["embeddings"],
        metadatas=metadatas,
    )
    if not up.get("success"):
        raise RuntimeError(f"Failed to upsert into Chroma: {up.get('error')}")

    return {
        "collection": name,
        "count": len(faqs),
        "dimensions": emb.get("dimensions"),
        "model": emb.get("model"),
    }


def main():
    """Run the local embeddings demo."""
    print("=" * 60)
    print("Local Embeddings - RAG Agent Demo")
    print("=" * 60)

    # Load knowledge base
    kb_path = os.path.join(os.path.dirname(__file__), "inputs", "knowledge_base.json")
    if not os.path.exists(kb_path):
        print(f"Error: Knowledge base not found at {kb_path}")
        return

    print("\nLoading knowledge base...")
    faqs = load_knowledge_base(kb_path)
    print(f"Loaded {len(faqs)} FAQs")

    print("\nBuilding persistent embeddings index in ChromaDB (first run may download model ~90MB)...")
    try:
        info = build_or_update_index(faqs, kb_path)
        persist_dir = os.environ.get("CHROMA_PERSIST_DIRECTORY") or "./chroma_data"
        print(f"Index ready! Collection: {info['collection']}")
        print(f"Embedding model: {info['model']} (dims: {info['dimensions']})")
        print(f"Chroma persist dir: {persist_dir}")
    except Exception as e:
        print(f"Error building index: {e}")
        print("\nMake sure you have installed: pip install \"strands-pack[local_embeddings,chromadb]\"")
        return

    # Create the RAG agent (LLM + primitive local retrieval tools).
    # This is intentionally "raw tools" style: the agent must call `local_embeddings`
    # and then `chromadb_tool` to retrieve sources before answering.
    agent = Agent(tools=[local_embeddings, chromadb_tool])

    print("\n" + "-" * 60)
    print("RAG Agent Ready!")
    print("Ask questions about the knowledge base (the agent will retrieve sources first).")
    print("Type 'quit' or 'exit' to end.\n")

    while True:
        try:
            user_input = input("Query: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q"):
                print("Goodbye!")
                break

            prompt = (
                "You are a helpful assistant answering questions using a local FAQ knowledge base.\n"
                "Before answering, you MUST retrieve sources from the knowledge base using the provided tools.\n"
                "\n"
                "Retrieval recipe (do this first):\n"
                f"1) Call local_embeddings(action='embed_query', text=<user question>, normalize=True)\n"
                f"2) Call chromadb_tool(action='query', collection='{info['collection']}', query_embeddings=[[<embedding>]], "
                "n_results=5, include=['metadatas','distances'])\n"
                "\n"
                "Answering rules:\n"
                "- Use ONLY the retrieved sources to answer.\n"
                "- If the KB doesn't contain the answer, say you don't know based on the KB.\n"
                "- At the end, include a short 'Sources:' list citing the FAQ ids or questions you used.\n\n"
                f"User question: {user_input}"
            )
            response = agent(prompt)
            print(f"\nAgent: {response}\n")

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
