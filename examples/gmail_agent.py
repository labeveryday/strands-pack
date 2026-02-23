#!/usr/bin/env python3
"""
Gmail Agent Example

A simple chat loop for testing gmail tool.

Usage:
    pip install strands-pack[gmail]
    python examples/gmail_agent.py

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
from strands_pack import gmail, google_auth


def main():
    agent = Agent(tools=[gmail, google_auth])

    print("\nGmail Agent Ready!")
    print("Tools: gmail, google_auth")
    print("Try:")
    print("  - 'Check my auth status'")
    print("  - 'Set up Gmail authentication'")
    print("  - 'Send an email with an attachment and a link'")
    print("  - 'List my recent emails'")
    print("  - 'Reply to message <id>'")
    print("  - 'Forward message <id> to someone@example.com'")
    print("  - 'List my labels' / 'Create a label called Receipts'")
    print("  - 'Mark message <id> as read/unread'")
    print("  - 'Trash message <id>' (safe) / 'Delete message <id>' (permanent, requires confirm)")
    print("  - 'Create a draft email' / 'Send draft <id>'")
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
