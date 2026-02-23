"""
ChromaDB Agent Example

A simple agent for vector database operations and semantic search.

Usage:
    python examples/chromadb_agent.py

Requirements:
    pip install strands-pack[chromadb]

Environment Variables (optional):
    CHROMA_PERSIST_DIRECTORY - Default storage location (default: ./chroma_data)
"""

from strands import Agent
from strands_pack import chromadb_tool

# Create agent with ChromaDB tool
agent = Agent(tools=[chromadb_tool])

print("ChromaDB Agent Ready!")
print("=" * 50)
print("Example commands:")
print("  - Create a collection called 'documents'")
print("  - Add these docs: 'Python is great', 'JavaScript is popular'")
print("  - Search for documents about programming languages")
print("  - How many documents are in the collection?")
print("  - List all collections")
print("=" * 50)
print()
print("Tip: Use ':memory:' for in-memory storage (no persistence)")
print()

# Interactive loop
while True:
    try:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        response = agent(user_input)
        print(f"\nAgent: {response}\n")
    except KeyboardInterrupt:
        print("\nGoodbye!")
        break
