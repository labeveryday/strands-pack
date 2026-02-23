#!/usr/bin/env python3
"""
OpenAI Video Agent Example

Demonstrates the openai_video tool for OpenAI's Videos API.

Usage:
    python examples/openai_video_agent.py

Environment:
    OPENAI_API_KEY: Required
"""

import os
import sys

# Add src to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dotenv import load_dotenv

load_dotenv()

from strands import Agent
from strands_pack import openai_video


def main():
    agent = Agent(tools=[openai_video])

    print("=" * 60)
    print("OpenAI Video Agent (Videos API)")
    print("=" * 60)
    print("\nThis agent generates videos using OpenAI's Videos API.")
    print("\nQuick usage tip:")
    print('  Say: "Generate a video of a calico cat playing piano"')
    print("\nThe tool will run create → wait → download and save an .mp4 to ./output by default.")
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


