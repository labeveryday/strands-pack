#!/usr/bin/env python3
"""
Box Agent Example

An interactive agent for managing Box files, folders, metadata, tasks, and AI features.

Usage:
    pip install strands-pack[box]
    python examples/box_agent.py

Required env vars (one auth method):
    BOX_DEVELOPER_TOKEN               - Short-lived dev token (60 min, easiest for testing)
    BOX_CLIENT_ID + BOX_CLIENT_SECRET - CCG auth (+ BOX_ENTERPRISE_ID or BOX_USER_ID)
    BOX_JWT_CONFIG_PATH               - Path to JWT config JSON file

Type 'exit' or 'quit' to end the session.
"""
import os
from pathlib import Path

_dotenv_path = Path.cwd() / ".env"
if not _dotenv_path.exists():
    _dotenv_path = Path(__file__).resolve().parents[1] / ".env"

try:
    from dotenv import load_dotenv

    if _dotenv_path.exists():
        load_dotenv(_dotenv_path)
except ImportError:
    if _dotenv_path.exists() and not any(
        os.environ.get(k)
        for k in ("BOX_DEVELOPER_TOKEN", "BOX_CLIENT_ID", "BOX_JWT_CONFIG_PATH")
    ):
        print("Note: Found a .env file but python-dotenv isn't installed, so it won't be loaded automatically.")
        print('Install with: pip install "strands-pack[dotenv]" (or: pip install python-dotenv)')
        print("Or export vars manually in your shell before running this script.")


def _print_env_status() -> None:
    """Print a quick status so local users can confirm auth is configured."""
    if os.environ.get("BOX_DEVELOPER_TOKEN"):
        print("Box auth: Developer token detected (expires after 60 min)")
    elif os.environ.get("BOX_CLIENT_ID") and os.environ.get("BOX_CLIENT_SECRET"):
        scope = "user" if os.environ.get("BOX_USER_ID") else "enterprise" if os.environ.get("BOX_ENTERPRISE_ID") else "unknown"
        print(f"Box auth: CCG ({scope} scope)")
    elif os.environ.get("BOX_JWT_CONFIG_PATH"):
        print(f"Box auth: JWT config at {os.environ['BOX_JWT_CONFIG_PATH']}")
    else:
        print("Box auth: No credentials detected. Set BOX_DEVELOPER_TOKEN, BOX_CLIENT_ID+BOX_CLIENT_SECRET, or BOX_JWT_CONFIG_PATH.")

from strands import Agent

from strands_pack import box


def main():
    _print_env_status()
    agent = Agent(tools=[box])

    print("\nInteractive Box Agent Ready!")
    print("Tools: box (20 actions — files, folders, search, metadata, tasks, Box AI)")
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
