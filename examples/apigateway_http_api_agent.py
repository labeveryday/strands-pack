"""
API Gateway HTTP API Agent Example

A simple agent for AWS API Gateway HTTP API operations.

Usage:
    python examples/apigateway_http_api_agent.py

Requirements:
    pip install strands-pack[aws]

Environment Variables:
    AWS_ACCESS_KEY_ID - AWS access key
    AWS_SECRET_ACCESS_KEY - AWS secret key
    AWS_DEFAULT_REGION - AWS region (default: us-east-1)
    STRANDS_PACK_API_PREFIX - API name prefix (default: "agent-")
    STRANDS_PACK_LAMBDA_PREFIX - Lambda name prefix (default: "agent-")

Note:
    HTTP APIs (v2) do NOT support API keys + usage plans.
    Use apigateway_rest_api if you need throttling/quotas.
"""

from strands import Agent
from strands_pack import apigateway_http_api

# Create agent with API Gateway HTTP API tool
agent = Agent(tools=[apigateway_http_api])

print("API Gateway HTTP API Agent Ready!")
print("=" * 50)
print("Example commands:")
print("  - List all HTTP APIs")
print("  - Create an HTTP API called agent-my-api")
print("  - Get details for API abc123")
print("  - Create a stage for API abc123")
print("  - Add a GET /hello route to API abc123 with Lambda arn:...")
print("  - Create a JWT authorizer for API abc123")
print("  - Delete API abc123")
print("=" * 50)
print()
print("Note: API names must start with prefix (default 'agent-')")
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
