#!/usr/bin/env python3
"""
Calendly Agent Example

Demonstrates the calendly tool for managing scheduling and events.

Usage:
    python examples/calendly_agent.py

Environment:
    CALENDLY_TOKEN: Personal Access Token from Calendly

Setup:
    1. Go to Calendly -> Integrations & apps -> API and webhooks
    2. Click "Get a token now" under Personal Access Tokens
    3. Name it and create, then copy the token
    4. Set CALENDLY_TOKEN in your .env file
"""

import os
import sys

# Add src to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dotenv import load_dotenv

load_dotenv()

from strands import Agent
from strands_pack import calendly


def main():
    """Run the calendly agent."""
    agent = Agent(tools=[calendly])

    print("=" * 60)
    print("Calendly Agent")
    print("=" * 60)
    print("\nThis agent manages your Calendly scheduling and events.")
    print("\nAvailable actions:")
    print("  get_current_user     - Get your Calendly profile")
    print("  list_event_types     - List your event types (meeting types)")
    print("  get_event_type       - Get details of a specific event type")
    print("  list_scheduled_events - List your scheduled meetings")
    print("  get_scheduled_event  - Get details of a specific meeting")
    print("  list_event_invitees  - List invitees for a meeting")
    print("  cancel_event         - Cancel a scheduled meeting")
    print("\nWebhooks (requires paid plan):")
    print("  create_webhook       - Subscribe to booking notifications")
    print("  list_webhooks        - List webhook subscriptions")
    print("  delete_webhook       - Remove a webhook")
    print("\nExample queries:")
    print("  - Who am I on Calendly?")
    print("  - List my event types")
    print("  - Show my upcoming meetings")
    print("  - List scheduled events for this week")
    print("  - Get details of event type <uuid>")
    print("  - Cancel meeting <uuid> because I'm sick")
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
