#!/usr/bin/env python3
"""
Carbon Agent Example

Demonstrates the carbon tool for generating beautiful code screenshots.

Usage:
    python examples/carbon_agent.py

Requirements:
    pip install strands-pack[carbon]
    playwright install chromium
"""

import os
import sys

# Add src to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dotenv import load_dotenv

load_dotenv()

from strands import Agent
from strands_pack import carbon


def main():
    """Run the Carbon code screenshot agent."""
    agent = Agent(tools=[carbon])

    print("=" * 60)
    print("Carbon Code Screenshot Agent")
    print("=" * 60)
    print("\nThis agent generates beautiful code screenshots using Carbon.")
    print("\nAvailable actions:")
    print("  generate          - Create screenshot from code string")
    print("  generate_from_file - Create screenshot from source file")
    print("  list_themes       - List available color themes")
    print("\nPopular themes:")
    print("  Dark: dracula, monokai, synthwave-84, night-owl, one-dark")
    print("  Light: one-light, solarized-light, yeti")
    print("  Minimal: nord, seti, vscode")
    print("\nExample queries:")
    print("  - Generate a screenshot of print('Hello World') in Python")
    print("  - Create a code image from src/main.py with dracula theme")
    print("  - Screenshot lines 10-50 of app.js with monokai theme")
    print("  - List available themes")
    print("  - Generate code image with line numbers enabled")
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
