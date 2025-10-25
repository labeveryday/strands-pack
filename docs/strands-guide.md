# Strands Agents - Comprehensive Reference Guide

## Table of Contents
1. [Quick Start](#quick-start)
2. [Core Concepts](#core-concepts)
3. [Creating Tools](#creating-tools)
4. [Multi-Agent Patterns](#multi-agent-patterns)
5. [Advanced Features](#advanced-features)
6. [Best Practices](#best-practices)
7. [Common Use Cases](#common-use-cases)

---

## Quick Start

### Installation
```bash
pip install strands-agents
pip install strands-agents-tools  # Pre-built tools
pip install 'strands-agents[otel]'  # For observability
pip install 'strands-agents[openai]' # If using openai
pip install 'strands-agents[anthropic]' # If using claude
```

### Basic Agent (5 lines)
```python
from strands import Agent
from strands.models.anthropic import AnthropicModel

model = AnthropicModel(
    client_args={"api_key": "your-key"},
    max_tokens=4000,
    model_id="claude-sonnet-4-20250514"
)

agent = Agent(model=model, system_prompt="You are a helpful assistant")
response = agent("What can you help me with?")
```

### Agent with Tools
```python
from strands import Agent, tool
from strands_tools import http_request, file_write

@tool
def get_weather(city: str) -> str:
    """Get weather for a city."""
    return f"Weather in {city}: Sunny, 72°F"

agent = Agent(
    model=model,
    tools=[get_weather, http_request, file_write]
)
response = agent("What's the weather in Seattle?")
```

---

## Core Concepts

### 1. Agent
The main orchestrator that handles:
- LLM interactions
- Tool execution
- Conversation history
- State management

```python
agent = Agent(
    model=model,
    system_prompt="You are a helpful assistant",
    tools=[tool1, tool2],
    callback_handler=None,  # Optional: for streaming
    conversation_manager=None,  # Optional: for history management
    session_manager=None,  # Optional: for persistence
    state={}  # Optional: initial state
)
```

### 2. Models
Strands supports multiple LLM providers:

**Anthropic (Claude)**
```python
from strands.models.anthropic import AnthropicModel

model = AnthropicModel(
    client_args={"api_key": ANTHROPIC_API_KEY},
    max_tokens=4000,
    model_id="claude-sonnet-4-20250514",
    params={"temperature": 0.7}
)
```

**OpenAI**
```python
from strands.models.openai import OpenAIModel

model = OpenAIModel(
    client_args={"api_key": OPENAI_API_KEY},
    model_id="gpt-4",
    params={"max_tokens": 4000, "temperature": 0.7}
)
```

### 3. Tools
Functions that agents can call to interact with external systems.

**Basic Tool**
```python
from strands import tool

@tool
def calculator(expression: str) -> float:
    """Evaluate a mathematical expression.
    
    Args:
        expression: Mathematical expression to evaluate
    
    Returns:
        Result of the calculation
    """
    return eval(expression)
```

**Async Tool**
```python
@tool
async def fetch_data(url: str) -> str:
    """Fetch data from an API (async)."""
    await asyncio.sleep(1)  # Simulated API call
    return "Data from API"
```

**Tool with Context**
```python
from strands import tool, ToolContext

@tool(context=True)
def get_user_data(tool_context: ToolContext) -> str:
    """Get user data from invocation state."""
    user_id = tool_context.invocation_state.get("user_id")
    return f"Data for user: {user_id}"
```

---

## Creating Tools

### Pre-built Tools (strands-agents-tools)
```python
from strands_tools import (
    http_request,      # Web requests
    file_read,         # Read files
    file_write,        # Write files
    calculator,        # Math operations
    current_time,      # Get current time
    retrieve,          # Vector search/RAG
    mem0_memory,       # Memory management
    workflow           # Multi-agent workflows
)
```

### Custom Tool Patterns

**1. Simple Synchronous Tool**
```python
@tool
def get_stock_price(symbol: str) -> str:
    """Get current stock price."""
    # Your logic here
    return f"${symbol}: $150.00"
```

**2. Tool with Multiple Parameters**
```python
@tool
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email.
    
    Args:
        to: Recipient email
        subject: Email subject
        body: Email body
    """
    # Your email logic
    return "Email sent successfully"
```

**3. Tool with Error Handling**
```python
@tool
def safe_api_call(endpoint: str) -> str:
    """Call external API with error handling."""
    try:
        # Your API call
        return "Success"
    except Exception as e:
        return f"Error: {str(e)}"
```

**4. Tool with External Dependencies**
```python
from ddgs import DDGS

@tool
def web_search(query: str, max_results: int = 5) -> str:
    """Search the web for information."""
    try:
        results = DDGS().text(query, max_results=max_results)
        return results if results else "No results found"
    except Exception as e:
        return f"Search error: {e}"
```

---

## Multi-Agent Patterns

Strands offers three orchestration patterns: **Graph**, **Swarm**, and **Workflow**.

### Decision Matrix

| Pattern | Best For | Execution | Cycles Allowed |
|---------|----------|-----------|----------------|
| **Graph** | Structured processes with branching logic | Controlled & Dynamic | Yes |
| **Swarm** | Collaborative tasks with emergent behavior | Sequential & Autonomous | Yes |
| **Workflow** | Repeatable processes with parallelization | Deterministic & Parallel | No |

### 1. Graph Pattern
**Use when:** You need structured flow with conditional branching.

```python
from strands import Agent
from strands.multiagent import GraphBuilder

# Create specialized agents
researcher = Agent(
    name="researcher",
    system_prompt="You are a research specialist..."
)
analyst = Agent(
    name="analyst",
    system_prompt="You analyze data..."
)
writer = Agent(
    name="writer",
    system_prompt="You write reports..."
)

# Build the graph
builder = GraphBuilder()
builder.add_node(researcher, "research")
builder.add_node(analyst, "analysis")
builder.add_node(writer, "report")

# Define flow
builder.add_edge("research", "analysis")
builder.add_edge("analysis", "report")
builder.set_entry_point("research")

# Execute
graph = builder.build()
result = graph("Research AI trends and create a report")
```

**Key Features:**
- Shared state across all agents
- Conditional branching
- Loops allowed
- Full conversation history

### 2. Swarm Pattern
**Use when:** Agents should autonomously hand off tasks.

```python
from strands import Agent
from strands.multiagent import Swarm

# Create team of specialists
researcher = Agent(name="researcher", system_prompt="Research specialist...")
coder = Agent(name="coder", system_prompt="Coding specialist...")
reviewer = Agent(name="reviewer", system_prompt="Code review specialist...")

# Create swarm
swarm = Swarm(
    [researcher, coder, reviewer],
    entry_point=researcher,
    max_handoffs=20,
    max_iterations=20
)

# Execute - agents decide the flow
result = swarm("Build a REST API for a todo app")
```

**Key Features:**
- Agents use `handoff_to_agent` tool
- Emergent behavior
- Shared context
- Autonomous decision-making

### 3. Workflow Pattern
**Use when:** You have a fixed, repeatable process.

```python
from strands import Agent
from strands_tools import workflow

agent = Agent(tools=[workflow])

# Define workflow
agent.tool.workflow(
    action="create",
    workflow_id="data_pipeline",
    tasks=[
        {
            "task_id": "extract",
            "description": "Extract data from source",
            "system_prompt": "You extract data...",
            "priority": 5
        },
        {
            "task_id": "transform",
            "description": "Transform the data",
            "dependencies": ["extract"],
            "system_prompt": "You transform data...",
            "priority": 3
        },
        {
            "task_id": "load",
            "description": "Load data to destination",
            "dependencies": ["transform"],
            "system_prompt": "You load data...",
            "priority": 1
        }
    ]
)

# Execute workflow
agent.tool.workflow(action="start", workflow_id="data_pipeline")
```

**Key Features:**
- Fixed DAG structure
- Parallel execution where possible
- No cycles
- Task-specific context

### Nested Multi-Agent Systems
Combine patterns for complex workflows:

```python
from strands.multiagent import GraphBuilder, Swarm

# Create a swarm for research
research_swarm = Swarm([
    Agent(name="medical_researcher", ...),
    Agent(name="tech_researcher", ...),
    Agent(name="economic_researcher", ...)
])

# Use swarm as a node in a graph
builder = GraphBuilder()
builder.add_node(research_swarm, "research_team")
builder.add_node(analyst, "analysis")
builder.add_edge("research_team", "analysis")

graph = builder.build()
result = graph("Comprehensive AI healthcare report")
```

---

## Advanced Features

### 1. Session Management
Persist agent state across conversations:

```python
from strands.session.file_session_manager import FileSessionManager

session_manager = FileSessionManager(
    session_id="user-123",
    storage_dir="./sessions"
)

agent = Agent(
    model=model,
    session_manager=session_manager,
    state={"user_preferences": {"theme": "dark"}}
)

# State persists across invocations
response = agent("Remember my preferences")
```

### 2. Conversation Management
Control conversation history with summarization:

```python
from strands.agent.conversation_manager import SummarizingConversationManager

conversation_manager = SummarizingConversationManager(
    summary_ratio=0.5,          # Summarize 50% of older messages
    preserve_recent_messages=3  # Keep last 3 exchanges intact
)

agent = Agent(
    model=model,
    conversation_manager=conversation_manager
)
```

### 3. Memory with Mem0
Persistent memory across sessions:

```python
from strands_tools import mem0_memory

agent = Agent(
    model=model,
    tools=[mem0_memory]
)

# Store memory
agent.tool.mem0_memory(
    action="store",
    content="User prefers morning meetings",
    user_id="user-123"
)

# Retrieve memories
agent.tool.mem0_memory(
    action="retrieve",
    query="meeting preferences",
    user_id="user-123"
)
```

### 4. Hooks
Manipulate tool arguments before execution:

```python
from strands.hooks import HookProvider, HookRegistry
from strands.experimental.hooks import BeforeToolInvocationEvent

class ConstantToolArguments(HookProvider):
    """Override tool arguments."""
    
    def __init__(self, fixed_args: dict):
        self._fixed_args = fixed_args
    
    def register_hooks(self, registry: HookRegistry, **kwargs):
        registry.add_callback(
            BeforeToolInvocationEvent,
            self._fix_arguments
        )
    
    def _fix_arguments(self, event: BeforeToolInvocationEvent):
        if params := self._fixed_args.get(event.tool_use["name"]):
            event.tool_use["input"].update(params)

# Use hook
fix_params = ConstantToolArguments({
    "calculator": {"precision": 2}
})

agent = Agent(model=model, tools=[calculator], hooks=[fix_params])
```

### 5. MCP Integration
Connect to Model Context Protocol servers:

```python
from strands.tools.mcp import MCPClient
from mcp import stdio_client, StdioServerParameters

# Connect to MCP server
mcp_client = MCPClient(
    lambda: stdio_client(
        StdioServerParameters(
            command="uvx",
            args=["awslabs.aws-documentation-mcp-server@latest"]
        )
    )
)

# Use MCP tools
with mcp_client:
    tools = mcp_client.list_tools_sync()
    agent = Agent(model=model, tools=[tools])
    agent("Find AWS S3 documentation")
```

### 6. Observability with OpenTelemetry
Track agent execution:

```python
from strands.telemetry import StrandsTelemetry

# Setup tracing
telemetry = StrandsTelemetry()
telemetry.setup_console_exporter()  # Print to console
telemetry.setup_otlp_exporter()     # Send to collector

agent = Agent(
    model=model,
    trace_attributes={
        "session.id": "abc-123",
        "user.id": "user@example.com"
    }
)

# All operations are automatically traced
response = agent("Complex query with multiple tools")

# View metrics
metrics = agent.event_loop_metrics.get_summary()
print(f"Input tokens: {metrics['accumulated_usage']['inputTokens']}")
print(f"Tool calls: {metrics['tool_usage']}")
```

---

## Best Practices

### 1. System Prompts
Be specific and include constraints:

```python
SYSTEM_PROMPT = """You are a customer support agent.

Capabilities:
- Answer product questions
- Process returns (under 30 days)
- Check order status

Rules:
- Never share customer data
- Always verify order ID
- Escalate refunds over $500

Format responses as:
1. Acknowledge issue
2. Provide solution
3. Ask if they need more help
"""
```

### 2. Error Handling
Always handle tool failures gracefully:

```python
@tool
def external_api_call(endpoint: str) -> str:
    """Call external API with proper error handling."""
    try:
        response = requests.get(endpoint, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.Timeout:
        return "Error: Request timed out. Please try again."
    except requests.RequestException as e:
        return f"Error: Unable to reach API. {str(e)}"
```

### 3. Tool Documentation
Write clear docstrings - LLMs read them:

```python
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
        Confirmation message with delivery status
    
    Examples:
        send_notification('slack', 'Deploy complete', 'high')
        send_notification('email', 'Weekly report ready')
    """
    # Implementation
    return f"Sent to {channel}: {message}"
```

### 4. Streaming Callbacks
Show progress to users:

```python
from typing import Any

class StreamingHandler:
    def __call__(self, **kwargs: Any) -> None:
        delta = kwargs.get("delta", {})
        tool_use = kwargs.get("current_tool_use", {})
        
        # Stream text
        if text := delta.get("text"):
            print(text, end="", flush=True)
        
        # Show tool usage
        if tool_name := tool_use.get("name"):
            print(f"\n🛠️  Using: {tool_name}")

agent = Agent(
    model=model,
    callback_handler=StreamingHandler()
)
```

### 5. State Management
Use invocation state for non-prompt data:

```python
# Pass context that shouldn't be in prompts
result = agent(
    "Process this order",
    invocation_state={
        "user_id": "user-123",
        "session_id": "sess-456",
        "db_connection": db_conn
    }
)

# Access in tools
@tool(context=True)
def process_order(order_id: str, tool_context: ToolContext) -> str:
    user_id = tool_context.invocation_state["user_id"]
    db = tool_context.invocation_state["db_connection"]
    # Process order with context
```

### 6. Security
Implement input validation and constraints:

```python
SYSTEM_PROMPT = """You are a secure data analysis agent.

SECURITY CONSTRAINTS:
- Never execute arbitrary code
- Validate all file paths (no ../.. traversal)
- Only read files in /data directory
- Never share API keys or credentials
- Reject SQL injection patterns

Before any file operation:
1. Validate path is in allowed directory
2. Check file size < 10MB
3. Verify file type is allowed
"""

@tool
def read_file(path: str) -> str:
    """Read file with security validation."""
    import os
    
    # Validate path
    abs_path = os.path.abspath(path)
    if not abs_path.startswith("/data/"):
        return "Error: Access denied. Path outside allowed directory."
    
    # Check file exists and size
    if not os.path.exists(abs_path):
        return "Error: File not found."
    
    if os.path.getsize(abs_path) > 10_000_000:
        return "Error: File too large (>10MB)."
    
    # Read file
    with open(abs_path, 'r') as f:
        return f.read()
```

---

## Common Use Cases

### 1. Research Assistant
```python
from strands import Agent
from strands_tools import http_request, file_write

research_agent = Agent(
    model=model,
    system_prompt="""You are a research assistant. When asked to research:
    1. Use http_request to gather information
    2. Synthesize findings
    3. Save report to file with file_write
    """,
    tools=[http_request, file_write]
)

response = research_agent(
    "Research the latest AI agent frameworks and save a summary to report.md"
)
```

### 2. Code Assistant
```python
@tool
def run_tests(test_file: str) -> str:
    """Run pytest on a test file."""
    import subprocess
    result = subprocess.run(
        ["pytest", test_file],
        capture_output=True,
        text=True
    )
    return result.stdout + result.stderr

code_agent = Agent(
    model=model,
    system_prompt="You are a Python coding assistant. Write clean, tested code.",
    tools=[file_read, file_write, run_tests]
)

response = code_agent("Create a function to parse CSV files with unit tests")
```

### 3. Data Analysis Pipeline
```python
analyzer = Agent(name="analyzer", system_prompt="Analyze data...")
reporter = Agent(name="reporter", system_prompt="Generate reports...")

builder = GraphBuilder()
builder.add_node(analyzer, "analysis")
builder.add_node(reporter, "report")
builder.add_edge("analysis", "report")

pipeline = builder.build()
result = pipeline("Analyze sales data and generate Q4 report")
```

### 4. Customer Support System
```python
# Specialized agents
order_agent = Agent(
    name="order_specialist",
    system_prompt="Handle order-related queries..."
)
returns_agent = Agent(
    name="returns_specialist",
    system_prompt="Process returns and refunds..."
)
technical_agent = Agent(
    name="tech_support",
    system_prompt="Solve technical issues..."
)

# Route to appropriate specialist
support_swarm = Swarm([order_agent, returns_agent, technical_agent])
result = support_swarm("My order #12345 arrived damaged, need a refund")
```

### 5. Content Generator
```python
@tool
def get_trending_topics(platform: str) -> str:
    """Get trending topics from social media."""
    # Implementation
    return "AI agents, LLMs, automation"

content_agent = Agent(
    model=model,
    system_prompt="""You are a content creator. Generate:
    - Blog titles (catchy, SEO-friendly)
    - Twitter threads (engaging, informative)
    - YouTube descriptions (clear, keyword-rich)
    """,
    tools=[get_trending_topics, file_write]
)

response = content_agent(
    "Generate 5 blog titles about AI agents based on trending topics"
)
```

### 6. Automated Workflow
```python
agent = Agent(tools=[workflow])

agent.tool.workflow(
    action="create",
    workflow_id="blog_pipeline",
    tasks=[
        {
            "task_id": "research",
            "description": "Research topic on the web",
            "system_prompt": "You research topics thoroughly..."
        },
        {
            "task_id": "outline",
            "description": "Create blog outline",
            "dependencies": ["research"],
            "system_prompt": "You create structured outlines..."
        },
        {
            "task_id": "write",
            "description": "Write full blog post",
            "dependencies": ["outline"],
            "system_prompt": "You write engaging content..."
        },
        {
            "task_id": "seo_optimize",
            "description": "Add SEO keywords and meta",
            "dependencies": ["write"],
            "system_prompt": "You optimize for SEO..."
        }
    ]
)

agent.tool.workflow(action="start", workflow_id="blog_pipeline")
```

---

## Quick Reference

### Common Imports
```python
from strands import Agent, tool, ToolContext
from strands.models.anthropic import AnthropicModel
from strands.models.openai import OpenAIModel
from strands.multiagent import GraphBuilder, Swarm
from strands_tools import (
    http_request, file_read, file_write,
    calculator, current_time, retrieve,
    mem0_memory, workflow
)
```

### Model Configuration
```python
# Anthropic
model = AnthropicModel(
    client_args={"api_key": API_KEY},
    max_tokens=4000,
    model_id="claude-sonnet-4-20250514",
    params={"temperature": 0.7}
)

# OpenAI
model = OpenAIModel(
    client_args={"api_key": API_KEY},
    model_id="gpt-4",
    params={"max_tokens": 4000, "temperature": 0.7}
)
```

### Basic Agent Setup
```python
agent = Agent(
    model=model,
    system_prompt="Your system prompt",
    tools=[tool1, tool2],
    callback_handler=None  # Optional streaming
)

response = agent("Your query")
```

### Metrics and Observability
```python
# Get metrics after execution
metrics = agent.event_loop_metrics.get_summary()

print(f"Input tokens: {metrics['accumulated_usage']['inputTokens']}")
print(f"Output tokens: {metrics['accumulated_usage']['outputTokens']}")
print(f"Tool usage: {metrics['tool_usage']}")
```

---

## Resources

- **Documentation:** https://strandsagents.com/latest/
- **GitHub:** https://github.com/awslabs/strands-agents
- **Pre-built Tools:** `strands-agents-tools` package
- **Community:** AWS Developer Forums

---

## Quick Decision Tree

**Q: Do I need multiple agents?**
- No → Use single Agent with tools
- Yes → Continue

**Q: Is the flow fixed and repeatable?**
- Yes → Use Workflow pattern
- No → Continue

**Q: Do I need branching logic?**
- Yes → Use Graph pattern
- No → Use Swarm pattern

**Q: Do I need persistence?**
- Yes → Add SessionManager
- No → Continue

**Q: Do I need memory across sessions?**
- Yes → Use mem0_memory tool
- No → You're done!

---

## Example: Complete Agent

```python
import os
from strands import Agent, tool
from strands.models.anthropic import AnthropicModel
from strands_tools import http_request, file_write
from dotenv import load_dotenv

load_dotenv()

# Custom tool
@tool
def summarize_text(text: str, max_sentences: int = 3) -> str:
    """Summarize text to specified number of sentences."""
    sentences = text.split('.')
    return '. '.join(sentences[:max_sentences]) + '.'

# Configure model
model = AnthropicModel(
    client_args={"api_key": os.getenv("ANTHROPIC_API_KEY")},
    max_tokens=4000,
    model_id="claude-sonnet-4-20250514",
    params={"temperature": 0.7}
)

# Create agent
agent = Agent(
    model=model,
    system_prompt="""You are a research assistant that:
    1. Searches the web for information
    2. Summarizes findings
    3. Saves reports to files
    
    Always cite sources and be concise.
    """,
    tools=[http_request, summarize_text, file_write]
)

# Use agent
response = agent(
    "Research the latest developments in AI agents and save a summary to research.md"
)

print(response)

# Check metrics
metrics = agent.event_loop_metrics.get_summary()
print(f"\nTokens used: {metrics['accumulated_usage']['totalTokens']}")
```

---

This guide covers 90% of what you'll need to build production-ready agents with Strands. Start simple, add complexity only when needed, and ship working code!