"""
Example Tools for Strands Agents
Demonstrates various tool patterns including custom tools, built-in tools, and MCP integration.
"""
import os
import asyncio
from typing import Optional
from dotenv import load_dotenv

from strands import Agent, tool, ToolContext
from strands.models.anthropic import AnthropicModel

# Built-in tools from strands-agents-tools
from strands_tools import (
    http_request,    # Make HTTP requests
    file_read,       # Read files
    file_write,      # Write files
    calculator,      # Math operations
    current_time,    # Get current time
    retrieve,        # Vector search/RAG
    # mem0_memory,   # Uncomment if you have MEM0_API_KEY
)

# MCP integration
from strands.tools.mcp import MCPClient
from mcp import stdio_client, StdioServerParameters

load_dotenv()

# ============================================================================
# PATTERN 1: Simple Synchronous Tool
# ============================================================================

@tool
def get_weather(city: str) -> str:
    """Get weather information for a city.
    
    Args:
        city: Name of the city
    
    Returns:
        Weather description
    """
    # In production, call a real weather API
    weather_data = {
        "Seattle": "Cloudy, 55°F",
        "San Francisco": "Foggy, 62°F",
        "Miami": "Sunny, 85°F",
        "New York": "Rainy, 48°F"
    }
    return weather_data.get(city, f"Weather data not available for {city}")


# ============================================================================
# PATTERN 2: Tool with Multiple Parameters
# ============================================================================

@tool
def send_notification(
    channel: str,
    message: str,
    urgency: str = "normal"
) -> str:
    """Send a notification to a communication channel.
    
    Args:
        channel: Target channel ('email', 'slack', 'sms')
        message: Notification message to send
        urgency: Priority level ('low', 'normal', 'high')
    
    Returns:
        Confirmation message
    """
    valid_channels = ["email", "slack", "sms"]
    if channel not in valid_channels:
        return f"Error: Invalid channel. Use: {', '.join(valid_channels)}"
    
    return f"✓ Sent {urgency} priority message to {channel}: {message}"


# ============================================================================
# PATTERN 3: Tool with Error Handling
# ============================================================================

@tool
def divide_numbers(a: float, b: float) -> str:
    """Safely divide two numbers with error handling.
    
    Args:
        a: Numerator
        b: Denominator
    
    Returns:
        Result of division or error message
    """
    try:
        if b == 0:
            return "Error: Cannot divide by zero"
        result = a / b
        return f"{a} ÷ {b} = {result}"
    except Exception as e:
        return f"Error: {str(e)}"


# ============================================================================
# PATTERN 4: Async Tool (for concurrent execution)
# ============================================================================

@tool
async def fetch_api_data(endpoint: str) -> str:
    """Fetch data from an API asynchronously.
    
    Async tools are invoked concurrently by Strands for better performance.
    
    Args:
        endpoint: API endpoint to call
    
    Returns:
        API response data
    """
    # Simulate API call
    await asyncio.sleep(1)
    return f"Data from {endpoint}: [API Response]"


# ============================================================================
# PATTERN 5: Tool with Context (Access invocation state)
# ============================================================================

@tool(context=True)
def get_user_preferences(tool_context: ToolContext) -> str:
    """Get user preferences from invocation state.
    
    This tool has access to invocation_state passed to the agent.
    
    Returns:
        User preferences
    """
    user_id = tool_context.invocation_state.get("user_id", "unknown")
    preferences = tool_context.invocation_state.get("preferences", {})
    
    if not preferences:
        return f"No preferences found for user: {user_id}"
    
    prefs_list = [f"{k}: {v}" for k, v in preferences.items()]
    return f"User {user_id} preferences:\n" + "\n".join(prefs_list)


# ============================================================================
# PATTERN 6: Tool with External API
# ============================================================================

@tool
def search_github(query: str, max_results: int = 5) -> str:
    """Search GitHub repositories.
    
    Args:
        query: Search query
        max_results: Maximum number of results (default: 5)
    
    Returns:
        Search results
    """
    try:
        import requests
        
        url = "https://api.github.com/search/repositories"
        params = {"q": query, "per_page": max_results, "sort": "stars"}
        headers = {"Accept": "application/vnd.github.v3+json"}
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        repos = data.get("items", [])
        
        if not repos:
            return f"No repositories found for: {query}"
        
        results = []
        for repo in repos[:max_results]:
            results.append(
                f"• {repo['full_name']} - ⭐ {repo['stargazers_count']}\n"
                f"  {repo['description']}\n"
                f"  {repo['html_url']}"
            )
        
        return "\n\n".join(results)
        
    except Exception as e:
        return f"Error searching GitHub: {str(e)}"


# ============================================================================
# PATTERN 7: Tool with File Operations
# ============================================================================

@tool
def count_lines_in_file(filepath: str) -> str:
    """Count lines in a text file.
    
    Args:
        filepath: Path to the file
    
    Returns:
        Number of lines in the file
    """
    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
        return f"File '{filepath}' contains {len(lines)} lines"
    except FileNotFoundError:
        return f"Error: File '{filepath}' not found"
    except Exception as e:
        return f"Error reading file: {str(e)}"


# ============================================================================
# PATTERN 8: Tool with Validation
# ============================================================================

@tool
def validate_email(email: str) -> str:
    """Validate an email address format.
    
    Args:
        email: Email address to validate
    
    Returns:
        Validation result
    """
    import re
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if re.match(pattern, email):
        return f"✓ Valid email: {email}"
    else:
        return f"✗ Invalid email format: {email}"


# ============================================================================
# MCP INTEGRATION EXAMPLE
# ============================================================================

def create_mcp_agent():
    """
    Example: Using MCP (Model Context Protocol) servers.
    
    MCP allows you to connect to external servers that provide tools.
    Common MCP servers:
    - AWS Documentation: awslabs.aws-documentation-mcp-server
    - AWS Pricing: awslabs.aws-pricing-mcp-server
    - File system: @modelcontextprotocol/server-filesystem
    - Git: @modelcontextprotocol/server-git
    """
    
    # Check if AWS credentials are available
    if not os.getenv("AWS_ACCESS_KEY_ID"):
        print("⚠️  MCP example requires AWS credentials")
        print("   Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env")
        return None
    
    # Create MCP client for AWS Documentation
    aws_docs_mcp = MCPClient(
        lambda: stdio_client(
            StdioServerParameters(
                command="uvx",
                args=["awslabs.aws-documentation-mcp-server@latest"]
            )
        )
    )
    
    # Create model
    model = AnthropicModel(
        client_args={"api_key": os.getenv("ANTHROPIC_API_KEY")},
        max_tokens=4000,
        model_id="claude-sonnet-4-20250514"
    )
    
    print("🔌 Connecting to MCP server...")
    
    # Use MCP tools with context manager
    with aws_docs_mcp:
        # List available tools from MCP server
        mcp_tools = aws_docs_mcp.list_tools_sync()
        
        print(f"✓ Connected! Found {len(mcp_tools)} MCP tools:")
        for tool in mcp_tools:
            print(f"  • {tool.tool_name}")
        
        # Create agent with MCP tools + custom tools
        agent = Agent(
            model=model,
            system_prompt="You are an AWS expert assistant with access to official documentation.",
            tools=[mcp_tools, file_write]  # Combine MCP tools with built-in tools
        )
        
        # Use the agent
        response = agent("Find documentation about S3 bucket policies")
        print(f"\n📝 Response:\n{response}")
        
        return agent
    
    return None


# ============================================================================
# DEMO: Using Different Tool Patterns
# ============================================================================

def demo_basic_tools():
    """Demonstrate basic tool usage."""
    print("=" * 60)
    print("DEMO 1: Basic Tools")
    print("=" * 60)
    
    # Configure model
    model = AnthropicModel(
        client_args={"api_key": os.getenv("ANTHROPIC_API_KEY")},
        max_tokens=4000,
        model_id="claude-sonnet-4-20250514"
    )
    
    # Create agent with custom tools
    agent = Agent(
        model=model,
        system_prompt="You are a helpful assistant with various tools.",
        tools=[
            get_weather,
            send_notification,
            divide_numbers,
            validate_email
        ]
    )
    
    # Test queries
    queries = [
        "What's the weather in Seattle?",
        "Send an urgent notification to slack saying 'Deploy complete'",
        "Divide 100 by 5",
        "Is user@example.com a valid email?"
    ]
    
    for query in queries:
        print(f"\n❓ {query}")
        response = agent(query)
        print(f"💬 {response}")


def demo_builtin_tools():
    """Demonstrate built-in Strands tools."""
    print("\n" + "=" * 60)
    print("DEMO 2: Built-in Strands Tools")
    print("=" * 60)
    
    model = AnthropicModel(
        client_args={"api_key": os.getenv("ANTHROPIC_API_KEY")},
        max_tokens=4000,
        model_id="claude-sonnet-4-20250514"
    )
    
    # Agent with built-in tools
    agent = Agent(
        model=model,
        system_prompt="You are an assistant with web search and file operations.",
        tools=[
            http_request,   # Web requests
            file_write,     # Write files
            current_time,   # Get time
            calculator      # Math
        ]
    )
    
    # Test query
    query = "What time is it? Calculate 25 * 17, then save the result to calculation.txt"
    print(f"\n❓ {query}")
    response = agent(query)
    print(f"💬 {response}")


def demo_context_tool():
    """Demonstrate tool with context access."""
    print("\n" + "=" * 60)
    print("DEMO 3: Tool with Context")
    print("=" * 60)
    
    model = AnthropicModel(
        client_args={"api_key": os.getenv("ANTHROPIC_API_KEY")},
        max_tokens=4000,
        model_id="claude-sonnet-4-20250514"
    )
    
    agent = Agent(
        model=model,
        system_prompt="You can access user preferences.",
        tools=[get_user_preferences]
    )
    
    # Pass invocation state
    response = agent(
        "What are my preferences?",
        invocation_state={
            "user_id": "user-123",
            "preferences": {
                "theme": "dark",
                "language": "en",
                "notifications": "enabled"
            }
        }
    )
    
    print(f"\n💬 {response}")


async def demo_async_tools():
    """Demonstrate async tool execution."""
    print("\n" + "=" * 60)
    print("DEMO 4: Async Tools (Concurrent Execution)")
    print("=" * 60)
    
    model = AnthropicModel(
        client_args={"api_key": os.getenv("ANTHROPIC_API_KEY")},
        max_tokens=4000,
        model_id="claude-sonnet-4-20250514"
    )
    
    agent = Agent(
        model=model,
        system_prompt="You can fetch data from APIs concurrently.",
        tools=[fetch_api_data]
    )
    
    # This will invoke multiple API calls concurrently
    response = await agent.invoke_async(
        "Fetch data from /users, /posts, and /comments endpoints"
    )
    
    print(f"\n💬 {response}")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Run all demonstrations."""
    
    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ Error: ANTHROPIC_API_KEY not found in .env")
        print("   Create a .env file with your API key")
        return
    
    print("🤖 Strands Agent Tools Examples\n")
    
    # Run demos
    try:
        # Demo 1: Custom tools
        demo_basic_tools()
        
        # Demo 2: Built-in tools
        demo_builtin_tools()
        
        # Demo 3: Context tool
        demo_context_tool()
        
        # Demo 4: Async tools
        print("\n" + "=" * 60)
        print("DEMO 4: Async Tools")
        print("=" * 60)
        asyncio.run(demo_async_tools())
        
        # Demo 5: MCP integration (optional)
        if os.getenv("AWS_ACCESS_KEY_ID"):
            print("\n" + "=" * 60)
            print("DEMO 5: MCP Integration")
            print("=" * 60)
            create_mcp_agent()
        else:
            print("\n" + "=" * 60)
            print("DEMO 5: MCP Integration (Skipped)")
            print("=" * 60)
            print("⚠️  Set AWS credentials in .env to run MCP demo")
        
        print("\n" + "=" * 60)
        print("✅ All demos complete!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()