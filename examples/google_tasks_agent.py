#!/usr/bin/env python3
"""
Google Tasks Agent Example

Interactive agent for managing Google Tasks.

Usage:
    python examples/google_tasks_agent.py

First run will prompt for OAuth authorization.
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
from strands_pack import google_tasks, google_auth


def main():
    agent = Agent(tools=[google_tasks, google_auth])

    print("Google Tasks Agent Ready!")
    print("Tools: google_tasks, google_auth")
    print()
    print("Try:")
    print("  - 'Check my auth status'")
    print("  - 'Set up Google Tasks authentication'")
    print("  - 'List my task lists'")
    print("  - 'Create a task called Review PR'")
    print()
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
