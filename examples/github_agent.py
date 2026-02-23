#!/usr/bin/env python3
"""
GitHub Agent Example

Demonstrates the github tool for repository, issue, and PR management.

Usage:
    python examples/github_agent.py

Requirements:
    pip install strands-pack[github]
    export GITHUB_TOKEN=ghp_xxx  # Personal Access Token
"""

import os
import sys

# Add src to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dotenv import load_dotenv

load_dotenv()

from strands import Agent
from strands_pack import github


def main():
    """Run the GitHub agent."""
    agent = Agent(tools=[github])

    print("=" * 60)
    print("GitHub Agent")
    print("=" * 60)
    print("\nThis agent manages GitHub repos, issues, and PRs.")
    print("\nAvailable actions (21 total):")
    print("\n  User & Repo:")
    print("    get_user, get_repo, list_repos, search_code")
    print("\n  Issues:")
    print("    list_issues, get_issue, create_issue, close_issue")
    print("    create_comment, set_labels, add_labels, remove_label")
    print("\n  Pull Requests:")
    print("    list_prs, get_pr, create_pr, update_pr, merge_pr")
    print("    list_pr_files, get_pr_diff")
    print("\n  File Operations (no git required):")
    print("    get_file_contents, create_or_update_file")
    print("\nExample queries:")
    print("  - Get my user info")
    print("  - List open PRs on strands-agents/strands-agents")
    print("  - Get the README.md from labeveryday/aws-projects")
    print("  - Create a file test.txt with 'hello world' in my-repo on main")
    print("\nType 'quit' or 'exit' to end.\n")

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
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
