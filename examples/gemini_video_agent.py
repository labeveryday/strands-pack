#!/usr/bin/env python3
"""
Gemini Video Agent Example

Demonstrates the gemini_video tool for AI video generation.

Usage:
    python examples/gemini_video_agent.py

Environment:
    GOOGLE_API_KEY: Required - Google AI API key
"""

import os
import sys

# Add src to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dotenv import load_dotenv

load_dotenv()

from strands import Agent
from strands_pack import gemini_video


def main():
    """Run the Gemini video agent."""
    agent = Agent(tools=[gemini_video])

    print("=" * 60)
    print("Gemini Video Agent (Veo 3.1)")
    print("=" * 60)
    print("\nThis agent generates videos using Google Veo.")
    print("\nAvailable actions:")
    print("  generate       - Create video from text prompt")
    print("  image_to_video - Create video from image + prompt")
    print("\nKey parameters:")
    print("  duration_seconds: 5 or 8 (default: 8)")
    print("  aspect_ratio: 16:9, 9:16, 1:1")
    print("  resolution: 720p, 1080p")
    print("\nExample queries:")
    print("  - Generate a video of a sunset over mountains")
    print("  - Create a video of a robot dancing")
    print("  - Take unicorn.png and make it jump over a rainbow")
    print("  - Generate a 9:16 vertical video for TikTok")
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
