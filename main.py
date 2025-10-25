"""
Main entry point for AI agents.
Provides interactive chat interface for testing agents.
"""
import os
import sys
from dotenv import load_dotenv
from strands import Agent, tool
from strands.models.anthropic import AnthropicModel

# Load environment variables
load_dotenv()

# ========================================
# CUSTOMIZE YOUR AGENT BELOW
# ========================================

@tool
def example_tool(input: str) -> str:
    """Replace this with your custom tool.
    
    Args:
        input: Description of input parameter
    
    Returns:
        Description of what the tool returns
    """
    return f"Processed: {input}"

# System prompt for your agent
SYSTEM_PROMPT = """You are a helpful AI assistant.

Replace this with your specific agent instructions.

Capabilities:
- List what your agent can do
- Be specific about constraints
- Include any important rules

Always be helpful and accurate.
"""

# ========================================

def create_agent():
    """Create and configure the agent."""
    
    # Get API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Error: ANTHROPIC_API_KEY not found")
        print("   Create a .env file with your API key")
        sys.exit(1)
    
    # Configure model
    model = AnthropicModel(
        client_args={"api_key": api_key},
        max_tokens=4000,
        model_id=os.getenv("ANTHROPIC_MODEL_ID", "claude-sonnet-4-20250514"),
        params={"temperature": 0.7}
    )
    
    # Create agent
    # Add your tools to the list below
    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[example_tool]  # Add your tools here
    )
    
    return agent

def interactive_mode(agent):
    """Run agent in interactive chat mode."""
    print("🤖 AI Agent (type 'quit' to exit, 'metrics' to see usage)\n")
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            if user_input.lower() == 'metrics':
                metrics = agent.event_loop_metrics.get_summary()
                print("\n📊 Token Usage:")
                print(f"  Input:  {metrics['accumulated_usage']['inputTokens']:,}")
                print(f"  Output: {metrics['accumulated_usage']['outputTokens']:,}")
                print(f"  Total:  {metrics['accumulated_usage']['totalTokens']:,}\n")
                continue
            
            # Get response
            response = agent(user_input)
            print(f"\nAgent: {response}\n")
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")

def single_query_mode(agent, query):
    """Run agent with a single query."""
    print(f"🤖 AI Agent\n")
    print(f"Query: {query}\n")
    
    try:
        response = agent(query)
        print(f"Response: {response}\n")
        
        # Show metrics
        metrics = agent.event_loop_metrics.get_summary()
        print("📊 Metrics:")
        print(f"  Tokens: {metrics['accumulated_usage']['totalTokens']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    """Main entry point."""
    
    # Show help
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("AI Agent Template\n")
        print("Usage:")
        print("  python main.py              # Interactive mode")
        print("  python main.py 'query'      # Single query")
        print("  python main.py --help       # Show this help")
        return
    
    # Create agent
    try:
        agent = create_agent()
    except Exception as e:
        print(f"❌ Failed to create agent: {e}")
        return
    
    # Run in appropriate mode
    if len(sys.argv) > 1:
        # Single query mode
        query = ' '.join(sys.argv[1:])
        single_query_mode(agent, query)
    else:
        # Interactive mode
        interactive_mode(agent)

if __name__ == "__main__":
    main()