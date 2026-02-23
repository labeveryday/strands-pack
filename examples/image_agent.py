#!/usr/bin/env python3
"""
Image Agent Example

Demonstrates the image tool for local image manipulation using Pillow.

Usage:
    python examples/image_agent.py
"""

import os
import sys

# Add src to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from strands import Agent
from strands_pack import image


def main():
    """Run the image agent."""
    agent = Agent(tools=[image])

    print("=" * 60)
    print("Image Agent (Pillow-based)")
    print("=" * 60)
    print("\nThis agent manipulates images using Pillow.")
    print("\nAvailable actions:")
    print("  resize, crop, rotate, convert, compress, get_info,")
    print("  add_text, thumbnail, flip, blur, grayscale, brightness,")
    print("  contrast, sharpen")
    print("\nExample queries:")
    print("  - Get info about photo.jpg")
    print("  - Resize image.png to 800px wide and save as resized.png")
    print("  - Convert photo.png to JPEG format")
    print("  - Add blur with radius 5 to image.jpg")
    print("  - Increase contrast by 25% on photo.jpg")
    print("  - Sharpen the image at blurry.png")
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
