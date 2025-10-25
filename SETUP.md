# Quick Setup Guide

Follow these steps to set up your agent project from this template:

## 1. Initial Setup (5 minutes)

```bash
# Clone or create from template
git clone <your-template-repo> my-agent-project
cd my-agent-project

# Create Python virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env
```

## 2. Configure API Keys

Edit `.env` and add your keys:

```env
ANTHROPIC_API_KEY=sk-ant-xxxxx
```

Get your Anthropic API key from: https://console.anthropic.com/

## 3. Test the Template

```bash
# Run the example agent
python example_agent.py

# Or use the interactive main
python main.py
```

You should see the agent respond to queries!

## 4. Build Your Agent (30 minutes)

### Option A: Modify main.py directly

1. Open `main.py`
2. Update `SYSTEM_PROMPT` with your agent's instructions
3. Replace `example_tool` with your custom tool
4. Run: `python main.py`

### Option B: Create new agent file

1. Copy `example_agent.py` to `my_agent.py`
2. Modify the tools and system prompt
3. Run: `python my_agent.py`

## 5. Quick Reference

### Creating a Tool

```python
@tool
def my_tool(param: str) -> str:
    """What the tool does.
    
    Args:
        param: Parameter description
    
    Returns:
        What it returns
    """
    # Your logic here
    return "result"
```

### Using Pre-built Tools

```python
from strands_tools import http_request, file_write, calculator

agent = Agent(
    model=model,
    tools=[http_request, file_write, calculator]
)
```

### Running in Different Modes

```bash
# Interactive chat
python main.py

# Single query
python main.py "What is 2 + 2?"

# Run example
python example_agent.py
```

## 6. Next Steps

- [ ] Build your first agent (2-4 hours)
- [ ] Test with real inputs
- [ ] Document usage in README
- [ ] Create demo video
- [ ] Push to GitHub
- [ ] Share publicly

## Troubleshooting

**"Module not found" error:**
```bash
pip install -r requirements.txt
```

**"API key not set" error:**
- Check `.env` file exists
- Verify `ANTHROPIC_API_KEY` is set
- Make sure you activated the virtual environment

**Agent not working:**
- Check the system prompt is clear
- Verify tool docstrings are descriptive
- Add error handling to tools

## Resources

- Full guide: `docs/strands-guide.md`
- Strands docs: https://strandsagents.com/latest/
- Example agents: `example_agent.py`

---

**Ready to build? Start with `python main.py` and ship something today!**