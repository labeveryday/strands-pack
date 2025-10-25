"""
Example Agent: Simple Q&A Assistant
Demonstrates basic agent setup with custom tools.
"""
import os
from dotenv import load_dotenv
from strands import Agent, tool
from strands.models.anthropic import AnthropicModel

# Load environment variables
load_dotenv()

# Custom tool example
@tool
def get_timestamp() -> str:
    """Get the current timestamp."""
    from datetime import datetime
    return datetime.now().isoformat()

@tool
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression safely.
    
    Args:
        expression: Math expression to evaluate (e.g., "2 + 2", "10 * 5")
    
    Returns:
        Result of the calculation
    """
    try:
        # Only allow safe mathematical operations
        allowed_chars = set('0123456789+-*/(). ')
        if not all(c in allowed_chars for c in expression):
            return "Error: Only basic math operations allowed"
        
        result = eval(expression)
        return f"{expression} = {result}"
    except Exception as e:
        return f"Error calculating: {str(e)}"

def create_agent():
    """Create and configure the agent."""
    
    # Get API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in .env file")
    
    # Configure model
    model = AnthropicModel(
        client_args={"api_key": api_key},
        max_tokens=4000,
        model_id=os.getenv("ANTHROPIC_MODEL_ID", "claude-sonnet-4-20250514"),
        params={"temperature": 0.7}
    )
    
    # Create agent with tools
    agent = Agent(
        model=model,
        system_prompt="""You are a helpful assistant that can:
        - Answer questions using your knowledge
        - Get the current timestamp when asked about time
        - Perform mathematical calculations
        
        Be concise and friendly.
        """,
        tools=[get_timestamp, calculate]
    )
    
    return agent

def main():
    """Run the example agent."""
    print("🤖 Example Agent - Simple Q&A Assistant\n")
    
    # Create agent
    agent = create_agent()
    
    # Example queries
    queries = [
        "What time is it?",
        "Calculate 15 * 23 + 100",
        "What is the capital of France?",
    ]
    
    for query in queries:
        print(f"❓ Query: {query}")
        response = agent(query)
        print(f"💬 Response: {response}\n")
    
    # Show metrics
    metrics = agent.event_loop_metrics.get_summary()
    print("📊 Metrics:")
    print(f"  Total tokens: {metrics['accumulated_usage']['totalTokens']}")
    print(f"  Input tokens: {metrics['accumulated_usage']['inputTokens']}")
    print(f"  Output tokens: {metrics['accumulated_usage']['outputTokens']}")

if __name__ == "__main__":
    main()