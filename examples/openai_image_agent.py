#!/usr/bin/env python3
"""
GPT Image Agent Example

Demonstrates the openai_image tool for AI image generation and editing.

Usage:
    python examples/openai_image_agent.py

Environment:
    OPENAI_API_KEY: Required - OpenAI API key
"""

import os
import sys

# Add src to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dotenv import load_dotenv


load_dotenv()

from strands import Agent
from strands_pack import openai_image


def main():
    """Run the GPT image agent."""
    agent = Agent(tools=[openai_image])

    print("=" * 60)
    print("GPT Image Agent")
    print("=" * 60)
    print("\nThis agent generates and edits images using OpenAI GPT.")
    print("\nAvailable actions:")
    print("  generate   - Create images from text prompts")
    print("  edit       - Modify existing images with prompts")
    print("  analyze    - Analyze image effectiveness (GPT-4o vision)")
    print("  optimize   - Optimize image for platform")
    print("  variations - Generate variations of an image")
    print("\nModels:")
    print("  gpt-image-1 (default) - OpenAI's latest image model")
    print("  dall-e-3 - Fallback model")
    print("\nStyles: photorealistic, illustration, cartoon, minimalist,")
    print("        dramatic, professional, vintage, watercolor, 3d")
    print("\nPlatforms: youtube, instagram, twitter, facebook, blog")
    print("\nExample queries:")
    print("  - Generate an image of a sunset over mountains")
    print("  - Create a photorealistic image of a coffee shop")
    print("  - Generate 3 variations of a minimalist logo")
    print("  - Edit photo.png to add a rainbow in the sky")
    print("  - Analyze thumbnail.png for YouTube effectiveness")
    print("  - Optimize image.png for Instagram")
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
