#!/usr/bin/env python3
"""
Notify Agent Example

Demonstrates the notify tool for local sound notifications.

Usage:
    python examples/notify_agent.py

Note:
    This tool plays sounds locally. It will not work in cloud environments
    (Lambda, ECS, EC2) - use SNS for remote notifications instead.
"""

import os
import sys

# Add src to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dotenv import load_dotenv

load_dotenv()

from strands import Agent
from strands_pack import notify


def main():
    """Run the notify agent."""
    agent = Agent(tools=[notify])

    print("=" * 60)
    print("Notify Agent")
    print("=" * 60)
    print("\nThis agent plays local sound notifications.")
    print("\nAvailable actions:")
    print("  notify    - Send notification with optional sound")
    print("  beep      - Play simple system beep")
    print("  play_file - Play custom audio file")
    print("\nNotification levels: info, success, warning, error")
    print("\nExample queries:")
    print("  - Beep to get my attention")
    print("  - Send a success notification saying 'Task complete!'")
    print("  - Play a warning notification")
    print("  - Notify me with title 'Build Done' and message 'All tests passed'")
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
