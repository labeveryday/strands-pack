"""
SQS Agent Example

A simple agent for AWS SQS queue and message management.

Usage:
    python examples/sqs_agent.py

Requirements:
    pip install strands-pack[aws]

Environment Variables:
    AWS_ACCESS_KEY_ID - AWS access key
    AWS_SECRET_ACCESS_KEY - AWS secret key
    AWS_DEFAULT_REGION - AWS region (default: us-east-1)
"""

from strands import Agent
from strands_pack import sqs

# Create agent with SQS tool
agent = Agent(tools=[sqs])

print("SQS Agent Ready!")
print("=" * 50)
print("Example commands:")
print("  - List all SQS queues")
print("  - Create a queue called 'my-queue'")
print("  - Create a FIFO queue called 'orders.fifo'")
print("  - Get URL for queue my-queue")
print("  - Get attributes for queue https://sqs...")
print("  - Send 'Hello World' to queue https://sqs...")
print("  - Send message with 60 second delay")
print("  - Receive 5 messages from queue")
print("  - Receive with 20 second long polling")
print("  - Delete message with receipt handle")
print("  - Purge all messages from queue")
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
