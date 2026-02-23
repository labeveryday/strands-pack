"""
DynamoDB Agent Example

A simple agent for Amazon DynamoDB operations - great for job queues and state management.

Usage:
    python examples/dynamodb_agent.py

Requirements:
    pip install strands-pack[aws]

Environment Variables:
    AWS_ACCESS_KEY_ID - AWS access key
    AWS_SECRET_ACCESS_KEY - AWS secret key
    AWS_DEFAULT_REGION - AWS region (default: us-east-1)
    STRANDS_PACK_DDB_TABLE_ALLOWLIST - Optional comma-separated list of allowed tables
"""

from strands import Agent
from strands_pack import dynamodb

# Create agent with DynamoDB tool
agent = Agent(tools=[dynamodb])

print("DynamoDB Agent Ready!")
print("=" * 50)
print("Example commands:")
print("  - Create a jobs table called 'my-jobs'")
print("  - Describe the my-jobs table")
print("  - Put an item in my-jobs with pk='user#123', sk='task#001'")
print("  - Get the item from my-jobs with pk='user#123', sk='task#001'")
print("  - Batch put 3 items to my-jobs")
print("  - Update the item to set status to 'completed'")
print("  - Query jobs with status 'PENDING'")
print("  - Scan my-jobs table for all items (limit 10)")
print("  - Delete the item from my-jobs")
print("=" * 50)
print()
print("Note: Items use DynamoDB attribute format, e.g., {\"S\": \"value\"}")
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
