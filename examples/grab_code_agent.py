#!/usr/bin/env python3
"""
Grab Code Agent Example

Demonstrates the grab_code tool for reading code from files.

Usage:
    python examples/grab_code_agent.py

Note:
    This tool works with local files. No API keys needed.
    It returns code in markdown format with line numbers.
"""

import os
import sys

# Add src to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dotenv import load_dotenv

load_dotenv()

from strands import Agent
from strands_pack import grab_code


def main():
    """Run the grab_code agent."""
    agent = Agent(tools=[grab_code])

    print("=" * 60)
    print("Grab Code Agent")
    print("=" * 60)
    print("\nThis agent reads code from files with formatting.")
    print("\nParameters:")
    print("  path            - File path to read (required)")
    print("  start_line      - Starting line number (1-based)")
    print("  end_line        - Ending line number (1-based)")
    print("  max_lines       - Max lines to return (default 400)")
    print("  with_line_numbers - Include line numbers (default True)")
    print("\nExample queries:")
    print("  - Read the file src/strands_pack/excel.py")
    print("  - Show me lines 50-100 of src/strands_pack/hue.py")
    print("  - Read pyproject.toml without line numbers")
    print("  - Show the first 20 lines of README.md")
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
