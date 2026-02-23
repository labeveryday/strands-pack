"""
S3 Agent Example

A simple agent for Amazon S3 bucket and object operations.

Usage:
    python examples/s3_agent.py

Requirements:
    pip install strands-pack[aws]

Environment Variables:
    AWS_ACCESS_KEY_ID - AWS access key
    AWS_SECRET_ACCESS_KEY - AWS secret key
    AWS_DEFAULT_REGION - AWS region (default: us-east-1)
"""

from strands import Agent
from strands_pack import s3

# Create agent with S3 tool
agent = Agent(tools=[s3])

print("S3 Agent Ready!")
print("=" * 50)
print("Example commands:")
print("  - List all my S3 buckets")
print("  - List objects in bucket-name with prefix 'data/'")
print("  - Get metadata for bucket-name/file.txt")
print("  - Write 'Hello World' to bucket-name/test.txt")
print("  - Read the text from bucket-name/config.json")
print("  - Copy bucket-name/source.txt to bucket-name/backup/source.txt")
print("  - Generate a presigned URL for bucket-name/file.pdf")
print("  - Create a new bucket called my-new-bucket")
print("  - Delete object data/old.txt from bucket-name")
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
