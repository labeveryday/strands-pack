"""Gemini Music Agent Example

A simple chat loop for testing gemini_music tool.

Usage:
    pip install strands-pack[gemini]
    python examples/gemini_music_agent.py

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

from dotenv import load_dotenv
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY is not set")

from strands import Agent
from strands_pack import gemini_music


def main():
    agent = Agent(tools=[gemini_music])

    print("\nGemini Music Agent Ready!")
    print("Tools: gemini_music")
    print("Try:")
    print("  - 'Generate a simple music'")
    print("  - 'Generate a music with weighted prompts'")
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