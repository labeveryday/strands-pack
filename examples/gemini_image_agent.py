#!/usr/bin/env python3
"""
Gemini Image Agent Example

Demonstrates the gemini_image tool for AI image generation and editing.

Usage:
    python examples/gemini_image_agent.py

Environment:
    GOOGLE_API_KEY: Required - Google AI API key
"""

import os
import sys

# Add src to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from strands import Agent
from strands_pack import gemini_image


def main():
    """Run the gemini image agent."""
    agent = Agent(tools=[gemini_image])

    print("=" * 60)
    print("Gemini Image Agent")
    print("=" * 60)
    print("\nThis agent generates and edits images using Google Gemini.")
    print("\nAvailable actions:")
    print("  generate - Create images from text descriptions")
    print("  edit     - Modify existing images with prompts")
    print("\nModels:")
    print("  gemini-3-pro-image-preview (default) - Higher quality, more features")
    print("  gemini-2.5-flash-image - Faster generation")
    print("\nKey parameters:")
    print("  aspect_ratio: 1:1, 16:9, 9:16, 4:3, 3:4, etc.")
    print("  image_size: 1K, 2K, 4K (Gemini 3 Pro only)")
    print("  num_images: Generate multiple variations (1-8)")
    print("  output_format: png, jpeg, webp")
    print("  output_filename: Custom filename (without extension)")
    print("\nExample queries:")
    print("  - Generate an image of a sunset over mountains")
    print("  - Create a 16:9 image of a futuristic city at night")
    print("  - Generate 3 variations of a cat in watercolor style")
    print("  - Generate a logo and save as logo.png in jpeg format")
    print("  - Edit photo.png to add a rainbow in the sky")
    print("  - Take my_image.png and change the background to a beach")
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
