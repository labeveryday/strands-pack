"""
Secrets Manager Agent Example

A simple agent for AWS Secrets Manager operations.

Usage:
    python examples/secrets_manager_agent.py

Requirements:
    pip install strands-pack[aws]

Environment Variables:
    AWS_ACCESS_KEY_ID - AWS access key
    AWS_SECRET_ACCESS_KEY - AWS secret key
    AWS_DEFAULT_REGION - AWS region (default: us-east-1)

Security Note:
    This tool is safe-by-default - it NEVER returns secret values.
    It returns opaque references that can be resolved internally by Python code.
"""

from strands import Agent
from strands_pack import secrets_manager

# Create agent with Secrets Manager tool
agent = Agent(tools=[secrets_manager])

print("Secrets Manager Agent Ready!")
print("=" * 50)
print("Example commands:")
print("  - List all secrets")
print("  - Describe secret my-secret")
print("  - Get a reference to secret my-api-key")
print("  - Add tag environment=prod to secret my-secret")
print("  - Remove the environment tag from my-secret")
print("  - Delete secret my-old-secret (requires confirm)")
print("=" * 50)
print()
print("Note: Secret values are NEVER returned for security.")
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
