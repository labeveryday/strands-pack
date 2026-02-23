"""
EventBridge Scheduler Agent Example

A simple agent for AWS EventBridge Scheduler operations.

Usage:
    python examples/eventbridge_scheduler_agent.py

Requirements:
    pip install strands-pack[aws]

Environment Variables:
    AWS_ACCESS_KEY_ID - AWS access key
    AWS_SECRET_ACCESS_KEY - AWS secret key
    AWS_DEFAULT_REGION - AWS region (default: us-east-1)
    STRANDS_PACK_SCHEDULE_PREFIX - Schedule name prefix (default: "agent-")
    STRANDS_PACK_SCHEDULER_ROLE_ALLOWLIST - Comma-separated allowed role ARNs
"""

from strands import Agent
from strands_pack import eventbridge_scheduler

# Create agent with EventBridge Scheduler tool
agent = Agent(tools=[eventbridge_scheduler])

print("EventBridge Scheduler Agent Ready!")
print("=" * 50)
print("Example commands:")
print("  - List all schedule groups")
print("  - List all schedules")
print("  - List schedules in group my-group")
print("  - Get schedule agent-my-job")
print("  - Pause schedule agent-my-job")
print("  - Resume schedule agent-my-job")
print("  - Create a schedule group called agent-jobs")
print("  - Delete schedule group agent-jobs (requires confirm)")
print("=" * 50)
print()
print("Note: Schedule names must start with prefix (default 'agent-')")
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
