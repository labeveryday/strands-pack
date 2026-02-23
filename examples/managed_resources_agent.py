#!/usr/bin/env python3
"""
Managed Resources Agent Example

Demonstrates the list_managed_resources tool for auditing AWS resources
created by strands-pack tools.

Usage:
    python examples/managed_resources_agent.py
"""

import os
import sys

# Add src to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from strands import Agent
from strands_pack import list_managed_resources


def main():
    """Run the managed resources agent."""
    agent = Agent(tools=[list_managed_resources])

    print("=" * 60)
    print("Managed Resources Agent")
    print("=" * 60)
    print("\nThis agent lists AWS resources tagged as managed by strands-pack.")
    print("Resources are identified by the tag: managed-by=strands-pack")
    print("\nSupported services: lambda, dynamodb, s3, sqs, sns,")
    print("                    apigateway_http, apigateway_rest, scheduler")
    print("\nExample queries:")
    print("  - List all managed resources")
    print("  - Show only Lambda functions managed by strands-pack")
    print("  - Find SQS queues with env=dev tag")
    print("  - List managed API Gateway endpoints")
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
