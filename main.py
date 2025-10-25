"""
Example agent to test tools.
Provides interactive chat interface for testing agents.
"""
from strands import Agent


# Create agent that can load tools
agent = Agent(
    load_tools_from_directory=True
)

while True:
    # Get user input
    prompt = input("\nUser: ")
    if prompt == "exit" or prompt=="quit":
        break
    else:
        agent(prompt)
        print("\n")
