#!/usr/bin/env python3
"""
Google Sheets Agent Example

A simple chat loop for testing google_sheets tool.

Usage:
    pip install strands-pack[sheets]
    python examples/google_sheets_agent.py

Type 'exit' or 'quit' to end the session.
"""
import os
import sys

from pathlib import Path

# Get repo root (parent of examples/)
_repo_root = Path(__file__).resolve().parent.parent

# Change to repo root so secrets/ is found
os.chdir(_repo_root)

# Add src to path for local development
sys.path.insert(0, str(_repo_root / "src"))

from strands import Agent
from strands_pack import google_docs, google_auth


def main():
    agent = Agent(tools=[google_docs, google_auth])

    print("\nGoogle Docs Agent Ready!")
    print("Tools: google_docs, google_auth")
    print("Try:")
    print("  - 'Check my auth status'")
    print("  - 'Set up Google Docs authentication'")
    print("  - 'Create a sample document'")
    print("  - 'Get values from my document'")
    print("  - 'Update values in my document'")
    print("  - 'Append values to my document'")
    print("  - 'Clear values from my document'")
    print("Type 'exit' to quit.\n")

    while True:
        try:
            prompt = input("You: ").strip()
            if prompt.lower() in ("exit", "quit", "q"):
                break
            if prompt:
                agent(prompt)
                print()
        except (KeyboardInterrupt, EOFError):
            break

    print("Goodbye!")


if __name__ == "__main__":
    main()
