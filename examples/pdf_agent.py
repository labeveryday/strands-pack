#!/usr/bin/env python3
"""
PDF Agent Example

Demonstrates the pdf tool for PDF manipulation using PyMuPDF.

Usage:
    python examples/pdf_agent.py
"""

import os
import sys

# Add src to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from strands import Agent
from strands_pack import pdf


def main():
    """Run the pdf agent."""
    agent = Agent(tools=[pdf])

    print("=" * 60)
    print("PDF Agent (PyMuPDF-based)")
    print("=" * 60)
    print("\nThis agent manipulates PDF files using PyMuPDF.")
    print("\nAvailable actions:")
    print("  extract_text, extract_pages, delete_pages, merge, split,")
    print("  get_info, to_images, rotate_pages, add_watermark,")
    print("  search_text, add_page_numbers")
    print("\nExample queries:")
    print("  - Get info about document.pdf")
    print("  - Extract text from report.pdf")
    print("  - Merge invoice1.pdf and invoice2.pdf into combined.pdf")
    print("  - Split document.pdf into individual pages in ./pages/")
    print("  - Delete pages 2 and 5 from document.pdf")
    print("  - Search for 'confidential' in document.pdf")
    print("  - Add page numbers to report.pdf")
    print("  - Add watermark 'DRAFT' to document.pdf")
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
