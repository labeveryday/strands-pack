"""
Lambda Agent Example

A simple agent for AWS Lambda function management.

Usage:
    python examples/lambda_agent.py

Requirements:
    pip install strands-pack[aws]

Environment Variables:
    AWS_ACCESS_KEY_ID - AWS access key
    AWS_SECRET_ACCESS_KEY - AWS secret key
    AWS_DEFAULT_REGION - AWS region (default: us-east-1)
    STRANDS_PACK_LAMBDA_PREFIX - Function name prefix (default: "agent-")
    STRANDS_PACK_LAMBDA_ROLE_ALLOWLIST - Comma-separated allowed role ARNs
"""

from strands import Agent
from strands_pack import lambda_tool

# Create agent with Lambda tool
agent = Agent(tools=[lambda_tool])

print("Lambda Agent Ready!")
print("=" * 50)
print("Example commands:")
print("  - List all Lambda functions")
print("  - Get details for function agent-hello")
print("  - Build a zip from ./src to ./deploy.zip")
print("  - Create function agent-hello with runtime python3.11")
print("  - Update agent-hello code from deploy.zip")
print("  - Invoke agent-hello with payload {\"name\": \"World\"}")
print("  - Update agent-hello config to 512MB memory")
print("=" * 50)
print()
print("Note: Function names must start with prefix (default 'agent-')")
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
