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
    if _dotenv_path.exists() and not any(
        os.environ.get(k)
        for k in ("DISCORD_BOT_TOKEN", "DISCORD_GUILD_ID", "DISCORD_CHANNEL_ID")
    ):
        print("Note: Found a .env file but python-dotenv isn't installed, so it won't be loaded automatically.")
        print('Install with: pip install "strands-pack[dotenv]" (or: pip install python-dotenv)')
        print("Or export vars manually in your shell before running this script.")


def _print_env_status() -> None:
    """Print a quick status so local users can confirm .env/export worked (without leaking secrets)."""
    missing = []
    for key in ("DISCORD_BOT_TOKEN", "DISCORD_GUILD_ID", "DISCORD_CHANNEL_ID"):
        if not os.environ.get(key):
            missing.append(key)

    if missing:
        print("Discord env vars missing (set via shell export or .env): " + ", ".join(missing))
        print("Tip: guild/channel IDs are optional, but without DISCORD_GUILD_ID the tool can't list channels by default.")
    else:
        print("Discord env vars detected: DISCORD_BOT_TOKEN, DISCORD_GUILD_ID, DISCORD_CHANNEL_ID")

from strands import Agent

from strands_pack import discord


def main():
    _print_env_status()
    agent = Agent(tools=[discord])

    print("Interactive Agent Ready!")
    print("Tools: discord")
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
