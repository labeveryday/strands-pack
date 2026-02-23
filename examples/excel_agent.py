#!/usr/bin/env python3
"""
Excel Agent Example

Demonstrates the excel tool for .xlsx file manipulation.

Usage:
    python examples/excel_agent.py

Requirements:
    pip install strands-pack[excel]

Note:
    This tool works with local .xlsx files. No API keys needed.
"""

import os
import sys

# Add src to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dotenv import load_dotenv

load_dotenv()

from strands import Agent
from strands_pack import excel


def main():
    """Run the excel agent."""
    agent = Agent(tools=[excel])

    print("=" * 60)
    print("Excel Agent")
    print("=" * 60)
    print("\nThis agent manipulates Excel (.xlsx) files locally.")
    print("\nAvailable actions:")
    print("  create_workbook  - Create a new Excel file")
    print("  read_workbook    - Read entire workbook or sheet")
    print("  read_range       - Read a specific cell range (e.g., A1:C10)")
    print("  write_range      - Write data to a cell range")
    print("  add_sheet        - Add a new sheet")
    print("  delete_sheet     - Delete a sheet")
    print("  list_sheets      - List all sheets in workbook")
    print("  get_info         - Get workbook metadata")
    print("  apply_formula    - Apply a formula to a cell")
    print("  save_as          - Save workbook to a new file")
    print("\nExample queries:")
    print("  - Create a new workbook called test.xlsx")
    print("  - Read the file sales.xlsx")
    print("  - Read cells A1 to C10 from report.xlsx")
    print("  - Write [[1,2,3],[4,5,6]] to A1 in test.xlsx")
    print("  - Add a sheet called 'Summary' to data.xlsx")
    print("  - List all sheets in budget.xlsx")
    print("  - Apply formula =SUM(A1:A10) to cell B1 in test.xlsx")
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
