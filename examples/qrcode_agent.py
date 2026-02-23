#!/usr/bin/env python3
"""
QR Code Agent Example

Demonstrates the qrcode_tool for generating and decoding QR codes.

Usage:
    python examples/qrcode_agent.py
"""

import os
import sys

# Add src to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dotenv import load_dotenv

load_dotenv()

from strands import Agent
from strands_pack import qrcode_tool


def main():
    """Run the QR code agent."""
    agent = Agent(tools=[qrcode_tool])

    print("=" * 60)
    print("QR Code Agent")
    print("=" * 60)
    print("\nThis agent generates and decodes QR codes and barcodes.")
    print("\nAvailable actions:")
    print("  generate        - Create a QR code image")
    print("  generate_styled - Create styled QR with custom colors")
    print("  generate_svg    - Create QR code as SVG")
    print("  generate_barcode - Create a barcode (code128, ean13, etc.)")
    print("  decode          - Decode first QR code from image")
    print("  decode_all      - Decode all QR codes from image")
    print("  decode_barcode  - Decode barcodes from image")
    print("  get_info        - Get info about codes in image")
    print("\nExample queries:")
    print("  - Generate a QR code for https://example.com")
    print("  - Create a blue QR code with yellow background for 'Hello'")
    print("  - Generate an SVG QR code for my WiFi password")
    print("  - Create a code128 barcode for product ID 12345")
    print("  - Decode the QR code in image.png")
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
