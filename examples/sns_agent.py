"""
SNS Agent Example

A simple agent for AWS SNS topic and message management.

Usage:
    python examples/sns_agent.py

Requirements:
    pip install strands-pack[aws]

Environment Variables:
    AWS_ACCESS_KEY_ID - AWS access key
    AWS_SECRET_ACCESS_KEY - AWS secret key
    AWS_DEFAULT_REGION - AWS region (default: us-east-1)
"""

from strands import Agent
from strands_pack import sns

# Create agent with SNS tool
agent = Agent(tools=[sns])

print("SNS Agent Ready!")
print("=" * 50)
print("Example commands:")
print("  - List all SNS topics")
print("  - Create a topic called 'my-alerts'")
print("  - Get attributes for topic arn:aws:sns:...")
print("  - Publish 'Hello World' to topic arn:aws:sns:...")
print("  - Publish with subject 'Alert' to topic")
print("  - Subscribe email user@example.com to topic")
print("  - Subscribe SQS queue to topic")
print("  - List all subscriptions")
print("  - Unsubscribe arn:aws:sns:...:subscription")
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
