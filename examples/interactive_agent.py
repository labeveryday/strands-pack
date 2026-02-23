#!/usr/bin/env python3
"""
Interactive Agent Example

A simple chat loop for testing strands-pack tools.

Usage:
    pip install strands-pack[all]
    python examples/interactive_agent.py

Type 'exit' or 'quit' to end the session.
"""
import os
from pathlib import Path

_dotenv_path = Path.cwd() / ".env"
if not _dotenv_path.exists():
    # Fallback to repo root when running from a different working directory.
    _dotenv_path = Path(__file__).resolve().parents[1] / ".env"

try:
    from dotenv import load_dotenv

    if _dotenv_path.exists():
        load_dotenv(_dotenv_path)
except ImportError:
    # Keep this generic: this example is used for many tools, not just Discord.
    if _dotenv_path.exists():
        print("Note: Found a .env file but python-dotenv isn't installed, so it won't be loaded automatically.")
        print('Install with: pip install "strands-pack[dotenv]" (or: pip install python-dotenv)')
        print("Or export vars manually in your shell before running this script.")

from strands import Agent
from strands_pack import sqlite, grab_code, skills


def main():
    agent = Agent(tools=[sqlite, grab_code, skills])

    print("Interactive Agent Ready!")
    print("Tools: sqlite, grab_code, skills")
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
