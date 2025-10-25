"""
Production-Ready Agent Template
Copy this file as a starting point for building production agents.
"""
import os
import sys
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from dotenv import load_dotenv

from strands import Agent, tool, ToolContext
from strands.models.anthropic import AnthropicModel
from strands_tools import http_request, file_write, current_time

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    """Agent configuration."""
    
    # Model settings
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    MODEL_ID = os.getenv("ANTHROPIC_MODEL_ID", "claude-sonnet-4-20250514")
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4000"))
    TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))
    
    # Agent settings
    AGENT_NAME = "ProductionAgent"
    VERSION = "1.0.0"
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration."""
        if not cls.ANTHROPIC_API_KEY:
            logger.error("ANTHROPIC_API_KEY not set in environment")
            return False
        return True


# ============================================================================
# CUSTOM TOOLS
# ============================================================================

@tool
def example_tool(input_data: str) -> str:
    """Replace this with your production tool.
    
    Args:
        input_data: Description of what this parameter does
    
    Returns:
        Description of what this returns
    
    Examples:
        >>> example_tool("test data")
        "Processed: test data"
    """
    try:
        # Your production logic here
        result = f"Processed: {input_data}"
        logger.info(f"Tool executed successfully: {input_data[:50]}...")
        return result
    except Exception as e:
        logger.error(f"Tool error: {e}")
        return f"Error: {str(e)}"


@tool(context=True)
def context_aware_tool(
    operation: str,
    tool_context: ToolContext
) -> str:
    """Tool that uses invocation context.
    
    Args:
        operation: The operation to perform
        tool_context: Context provided by the agent
    
    Returns:
        Operation result
    """
    try:
        # Access invocation state
        user_id = tool_context.invocation_state.get("user_id", "unknown")
        session_id = tool_context.invocation_state.get("session_id", "unknown")
        
        logger.info(f"Operation '{operation}' for user={user_id}, session={session_id}")
        
        # Your logic here
        return f"Executed {operation} for user {user_id}"
        
    except Exception as e:
        logger.error(f"Context tool error: {e}")
        return f"Error: {str(e)}"


# ============================================================================
# AGENT FACTORY
# ============================================================================

class ProductionAgent:
    """Production-ready agent with monitoring and error handling."""
    
    def __init__(
        self,
        system_prompt: Optional[str] = None,
        tools: Optional[list] = None,
        enable_metrics: bool = True
    ):
        """Initialize the production agent.
        
        Args:
            system_prompt: Custom system prompt (uses default if None)
            tools: List of tools (uses defaults if None)
            enable_metrics: Whether to track and log metrics
        """
        # Validate configuration
        if not Config.validate():
            raise ValueError("Invalid configuration. Check environment variables.")
        
        self.enable_metrics = enable_metrics
        self.system_prompt = system_prompt or self._default_system_prompt()
        self.tools = tools or self._default_tools()
        
        # Create model
        self.model = self._create_model()
        
        # Create agent
        self.agent = Agent(
            model=self.model,
            system_prompt=self.system_prompt,
            tools=self.tools
        )
        
        logger.info(f"Initialized {Config.AGENT_NAME} v{Config.VERSION}")
    
    def _default_system_prompt(self) -> str:
        """Default system prompt for the agent."""
        return """You are a production AI agent.

Capabilities:
- Process user requests accurately
- Use available tools when appropriate
- Provide clear, actionable responses
- Handle errors gracefully

Rules:
- Always validate inputs
- Provide informative error messages
- Be concise but thorough
- Ask for clarification if needed

Current time: {current_time}
Agent version: {version}
""".format(
            current_time=datetime.now().isoformat(),
            version=Config.VERSION
        )
    
    def _default_tools(self) -> list:
        """Default tools for the agent."""
        return [
            example_tool,
            context_aware_tool,
            http_request,
            file_write,
            current_time
        ]
    
    def _create_model(self) -> AnthropicModel:
        """Create the language model."""
        return AnthropicModel(
            client_args={"api_key": Config.ANTHROPIC_API_KEY},
            max_tokens=Config.MAX_TOKENS,
            model_id=Config.MODEL_ID,
            params={"temperature": Config.TEMPERATURE}
        )
    
    def __call__(
        self,
        query: str,
        invocation_state: Optional[Dict[str, Any]] = None
    ) -> str:
        """Invoke the agent with a query.
        
        Args:
            query: User query
            invocation_state: Optional state to pass to tools
        
        Returns:
            Agent response
        """
        try:
            logger.info(f"Processing query: {query[:100]}...")
            
            # Invoke agent
            response = self.agent(query, invocation_state=invocation_state)
            
            # Log metrics if enabled
            if self.enable_metrics:
                self._log_metrics()
            
            logger.info("Query processed successfully")
            return response
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return f"I apologize, but I encountered an error: {str(e)}"
    
    def _log_metrics(self):
        """Log agent metrics."""
        try:
            metrics = self.agent.event_loop_metrics.get_summary()
            usage = metrics.get('accumulated_usage', {})
            
            logger.info(
                f"Metrics - "
                f"Input: {usage.get('inputTokens', 0):,}, "
                f"Output: {usage.get('outputTokens', 0):,}, "
                f"Total: {usage.get('totalTokens', 0):,}"
            )
            
            # Log tool usage
            tool_usage = metrics.get('tool_usage', {})
            if tool_usage:
                for tool_name, data in tool_usage.items():
                    stats = data.get('execution_stats', {})
                    logger.info(
                        f"Tool '{tool_name}': "
                        f"{stats.get('call_count', 0)} calls, "
                        f"{stats.get('success_rate', 0)*100:.1f}% success"
                    )
        except Exception as e:
            logger.warning(f"Failed to log metrics: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current agent metrics.
        
        Returns:
            Dictionary of metrics
        """
        return self.agent.event_loop_metrics.get_summary()


# ============================================================================
# CLI INTERFACE
# ============================================================================

def interactive_mode(agent: ProductionAgent):
    """Run agent in interactive mode."""
    print(f"🤖 {Config.AGENT_NAME} v{Config.VERSION}")
    print("Commands: 'quit' to exit, 'metrics' to view usage\n")
    
    session_id = datetime.now().isoformat()
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            if user_input.lower() == 'metrics':
                metrics = agent.get_metrics()
                usage = metrics['accumulated_usage']
                print(f"\n📊 Session Metrics:")
                print(f"  Input tokens:  {usage['inputTokens']:,}")
                print(f"  Output tokens: {usage['outputTokens']:,}")
                print(f"  Total tokens:  {usage['totalTokens']:,}\n")
                continue
            
            # Process query with invocation state
            response = agent(
                user_input,
                invocation_state={
                    "user_id": "cli-user",
                    "session_id": session_id
                }
            )
            
            print(f"\n{Config.AGENT_NAME}: {response}\n")
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")
            logger.exception("Unexpected error in interactive mode")


def single_query_mode(agent: ProductionAgent, query: str):
    """Process a single query."""
    print(f"🤖 {Config.AGENT_NAME} v{Config.VERSION}\n")
    print(f"Query: {query}\n")
    
    try:
        response = agent(query)
        print(f"Response:\n{response}\n")
        
        # Show metrics
        metrics = agent.get_metrics()
        usage = metrics['accumulated_usage']
        print(f"📊 Tokens used: {usage['totalTokens']:,}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.exception("Error in single query mode")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point."""
    
    # Parse arguments
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print(f"{Config.AGENT_NAME} v{Config.VERSION}\n")
        print("Usage:")
        print("  python production_agent.py              # Interactive mode")
        print("  python production_agent.py 'query'      # Single query")
        print("  python production_agent.py --help       # Show this help")
        return
    
    # Validate configuration
    if not Config.validate():
        print("❌ Configuration error. Check your .env file.")
        return
    
    try:
        # Create agent
        logger.info("Starting agent...")
        agent = ProductionAgent()
        
        # Run in appropriate mode
        if len(sys.argv) > 1:
            # Single query
            query = ' '.join(sys.argv[1:])
            single_query_mode(agent, query)
        else:
            # Interactive mode
            interactive_mode(agent)
            
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        logger.exception("Fatal error")
        sys.exit(1)


if __name__ == "__main__":
    main()