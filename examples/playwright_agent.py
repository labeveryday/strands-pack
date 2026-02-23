#!/usr/bin/env python3
"""
Playwright Browser Agent Example

Demonstrates the playwright_browser tool for browser automation.

Usage:
    python examples/playwright_agent.py

Requirements:
    pip install strands-pack[playwright]
    playwright install chromium

Note:
    By default, the browser is visible (headless=False).
    Say "run headless" or set headless=True to hide the browser.
"""

import os
import sys

# Add src to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dotenv import load_dotenv

load_dotenv()

from strands import Agent
from strands_pack import playwright_browser


def main():
    """Run the playwright agent."""
    agent = Agent(tools=[playwright_browser])

    print("=" * 60)
    print("Playwright Browser Agent")
    print("=" * 60)
    print("\nThis agent automates browser interactions.")
    print("\nAvailable actions:")
    print("  navigate     - Go to a URL")
    print("  screenshot   - Take a screenshot")
    print("  extract_text - Get visible text from page")
    print("  click        - Click an element by selector")
    print("  fill         - Fill a form field (clears first)")
    print("  type         - Type text into an element")
    print("  wait         - Wait for an element state")
    print("  evaluate     - Run JavaScript on the page")
    print("  close_session - Close a persisted browser session")
    print("\nSession persistence:")
    print("  Use session_id to keep browser open between calls.")
    print("  Example: navigate with session_id='s1', then click, then close_session")
    print("\nExample queries:")
    print("  - Navigate to https://example.com")
    print("  - Take a screenshot of https://google.com")
    print("  - Get the text from https://news.ycombinator.com")
    print("  - Navigate to google.com, search for 'python', take a screenshot")
    print("  - Click the button with text 'Submit'")
    print("  - Run this headless: screenshot https://example.com")
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
