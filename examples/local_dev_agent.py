#!/usr/bin/env python3
"""
Local Dev Agent Example

Demonstrates the local_queue and local_scheduler tools for local development
without AWS dependencies. Uses SQLite for persistence.

Usage:
    export SQLITE_DB_PATH=/tmp/dev.db
    python examples/local_dev_agent.py
"""

import os
import sys

# Add src to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from strands import Agent
from strands_pack import local_queue, local_scheduler


def main():
    """Run the local dev agent."""
    # Set a default DB path if not set
    if not os.environ.get("SQLITE_DB_PATH"):
        os.environ["SQLITE_DB_PATH"] = "/tmp/strands_dev.db"

    agent = Agent(tools=[local_queue, local_scheduler])

    print("=" * 60)
    print("Local Dev Agent (SQLite-backed Queue + Scheduler)")
    print("=" * 60)
    print(f"\nDatabase: {os.environ['SQLITE_DB_PATH']}")
    print("\nThis agent provides SQS-like queue and EventBridge-like scheduler")
    print("functionality for local development without AWS.")
    print("\nQueue actions: send, receive, delete, purge, list_queues,")
    print("               get_queue_attributes, change_visibility")
    print("\nScheduler actions: schedule_at, schedule_in, get_schedule,")
    print("                   list_schedules, cancel_schedule, run_due")
    print("\nExample queries:")
    print("  - Send a message 'hello world' to the tasks queue")
    print("  - Receive messages from the tasks queue")
    print("  - Schedule a reminder in 60 seconds")
    print("  - List all pending schedules")
    print("  - Run all due schedules")
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
