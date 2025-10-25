# Strands Agents AI Agent Template

**A production-ready template for building AI agents with AWS Strands Agents.**

Created by [Du'An Lightfoot](https://duanlightfoot.com) | [@labeveryday](https://github.com/labeveryday)

---

## What This Is

A standardized template for building, documenting, and deploying AI agents quickly. Optimized for:
- **Speed:** 2-4 hours from idea to working agent
- **Consistency:** Same structure for all agents
- **Documentation:** Built-in guide and examples
- **Shipping:** Focus on working code, not infrastructure

## Quick Start

```bash
# 1. Use this template (GitHub button or clone)
git clone https://github.com/labeveryday/strands_starter.git
cd strands_starter

# 2. Set up Python environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Add your API keys to .env

# 5. Run the example agent
python main.py
```

## Repository Structure

```
strands_starter/
├── main.py                    # Agent entry point
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variables template
├── .gitignore                # Git ignore rules
├── README.md                 # This file
├── docs/
│   └── strands-guide.md      # Comprehensive Strands reference
├── agents/                   # Your agent implementations
│   └── example_agent.py      # Example agent
└── tools/                    # Custom tools
    └── example_tool.py       # Example tool
```

## Building Your First Agent

### 1. Create Agent File
```bash
cp agents/example_agent.py agents/my_agent.py
```

### 2. Define Your Agent
```python
from strands import Agent, tool
from strands.models.anthropic import AnthropicModel
import os

# Custom tool
@tool
def my_tool(input: str) -> str:
    """What your tool does."""
    return f"Processed: {input}"

# Configure model
model = AnthropicModel(
    client_args={"api_key": os.getenv("ANTHROPIC_API_KEY")},
    max_tokens=4000,
    model_id="claude-sonnet-4-20250514"
)

# Create agent
agent = Agent(
    model=model,
    system_prompt="You are a helpful assistant that...",
    tools=[my_tool]
)

# Run
if __name__ == "__main__":
    response = agent("Your query here")
    print(response)
```

### 3. Test It
```bash
python agents/my_agent.py
```

### 4. Document It
Update this README with your agent's purpose and usage.

## Environment Setup

Create a `.env` file with:

```env
# Required
ANTHROPIC_API_KEY=your_key_here

# Optional (if using OpenAI)
OPENAI_API_KEY=your_key_here

# Optional (if using Mem0)
MEM0_API_KEY=your_key_here

# Optional (if using AWS services)
AWS_ACCESS_KEY_ID=your_key_here
AWS_SECRET_ACCESS_KEY=your_key_here
AWS_REGION=us-east-1
```

## Dependencies

Core dependencies (`requirements.txt`):

```txt
strands-agents
strands-agents-tools
python-dotenv
```

Optional:

```txt
strands-agents[otel]  # For observability
duckduckgo-search     # For web search
```

## Available Resources

- **[Strands Guide](docs/strands-guide.md)** - Comprehensive reference
- **[Strands Docs](https://strandsagents.com/latest/)** - Official documentation
- **[Example Agents](agents/)** - Working examples

## Agent Ideas

**Simple (2-4 hours each):**
- [ ] Twitter thread generator (blog → tweets)
- [ ] Blog title generator (transcript → titles)
- [ ] YouTube comment responder
- [ ] Meeting notes → action items
- [ ] GitHub issue triager

**Complex (1-2 days each):**
- [ ] Multi-agent research system
- [ ] Code review assistant
- [ ] Customer support automation

## Development Workflow

1. **Build:** Create agent in `agents/` folder
2. **Test:** Run locally with test inputs
3. **Document:** Update README with usage
4. **Demo:** Record video showing it working
5. **Ship:** Push to GitHub, share publicly

## Best Practices

### Keep It Simple
- Start with single agent + tools
- Add multi-agent patterns only when needed
- Use pre-built tools from `strands-agents-tools`

### Make It Observable
```python
# Add metrics tracking
metrics = agent.event_loop_metrics.get_summary()
print(f"Tokens used: {metrics['accumulated_usage']['totalTokens']}")
```

### Handle Errors
```python
@tool
def safe_operation(input: str) -> str:
    """Always handle failures gracefully."""
    try:
        # Your logic
        return "Success"
    except Exception as e:
        return f"Error: {str(e)}"
```

### Document for LLMs
```python
@tool
def clear_tool(param: str) -> str:
    """Write detailed docstrings - the LLM reads them!
    
    Args:
        param: Explain what this parameter does
    
    Returns:
        What the tool returns
    
    Example:
        clear_tool("sample input")
    """
    return "result"
```

## Testing Your Agent

```python
# Basic test
def test_agent():
    agent = Agent(model=model, tools=[tool1])
    
    # Test cases
    test_inputs = [
        "Simple query",
        "Query that requires tool",
        "Edge case"
    ]
    
    for test in test_inputs:
        try:
            response = agent(test)
            print(f"✅ {test}: {response}")
        except Exception as e:
            print(f"❌ {test}: {e}")

if __name__ == "__main__":
    test_agent()
```

## Deployment Options

### Local (Start Here)
python main.py

### Amazon Bedrock AgentCore (Production)

Deploy to AWS-managed runtime in 10 minutes.

**Quick deploy:**
```bash
pip install bedrock-agentcore-starter-toolkit
agentcore configure -e my_agent.py
agentcore launch
```

**See [DEPLOYMENT.md](docs/deployment.md) for full guide.**
```

### Cloud (When Needed)
- AWS Lambda (serverless)
- EC2 (persistent)
- ECS (containerized)
- Amazon Bedrock AgentCore (Best approach): https://aws.github.io/bedrock-agentcore-starter-toolkit/user-guide/runtime/quickstart.html

**Note:** Start local, deploy when you have users.

## Common Patterns

### 1. Simple Tool Agent
```python
agent = Agent(model=model, tools=[tool1, tool2])
agent("Do something")
```

### 2. Multi-Agent Graph
```python
from strands.multiagent import GraphBuilder

builder = GraphBuilder()
builder.add_node(agent1, "step1")
builder.add_node(agent2, "step2")
builder.add_edge("step1", "step2")

graph = builder.build()
graph("Complex task")
```

### 3. Memory-Enabled Agent
```python
from strands_tools import mem0_memory

agent = Agent(
    model=model,
    tools=[mem0_memory]
)

# Store memory
agent.tool.mem0_memory(
    action="store",
    content="User fact",
    user_id="user-123"
)
```

## Troubleshooting

### "Module not found"
```bash
pip install -r requirements.txt
```

### "API key not set"
Check your `.env` file has the correct keys.

### "Tool not working"
Check tool docstring and error handling.

### "Out of tokens"
Monitor usage with `event_loop_metrics`.


## Example prompts:

```
Using the Strands Agents guide, create a Twitter thread generator that:
- Takes a blog post URL as input
- Extracts key points
- Generates a 5-tweet thread
- Saves to a JSON file

Use the patterns from the guide and keep it simple.
```

## Contributing

This is a personal template, but feel free to:
- Fork for your own use
- Submit issues if you find bugs
- Share improvements

## License

MIT License - Use freely, build amazing things.

## About

Built by **Du'An Lightfoot** ([@labeveryday](https://github.com/labeveryday))
- Website: [duanlightfoot.com](https://duanlightfoot.com)
- YouTube: [LabEveryday](https://youtube.com/@labeveryday)
- Focus: Building AI agents, teaching others, creating in public

---

**Ready to build? Start with `agents/example_agent.py` and ship something today.**
