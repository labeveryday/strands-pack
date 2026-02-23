"""
SQLite Agent Example

A simple agent for local SQLite database operations.

Usage:
    python examples/sqlite_agent.py

Requirements:
    - No external dependencies (uses Python's built-in sqlite3)
"""

from strands import Agent
from strands_pack import sqlite

# Create agent with SQLite tool
agent = Agent(tools=[sqlite])

print("SQLite Agent Ready!")
print("=" * 50)
print("Example commands:")
print("  - Create a database at ./test.db with a users table")
print("  - Insert user John with email john@example.com")
print("  - Query all users from the database")
print("  - Export users table to CSV")
print("  - Show database info")
print("=" * 50)
print()

# Interactive loop
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
