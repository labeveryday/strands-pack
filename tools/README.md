# Custom Tools Directory

Store your custom tools here to keep your project organized.

## Structure

```
tools/
├── README.md           # This file
├── __init__.py         # Makes this a Python package
├── web_tools.py        # Web-related tools
├── data_tools.py       # Data processing tools
├── api_tools.py        # External API integrations
└── utils.py            # Utility functions
```

## Creating a Tool Module

**Example: `tools/web_tools.py`**

```python
"""Web-related tools for agents."""
from strands import tool
import requests

@tool
def fetch_url(url: str) -> str:
    """Fetch content from a URL.
    
    Args:
        url: The URL to fetch
    
    Returns:
        Page content or error message
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        return f"Error fetching URL: {str(e)}"

@tool
def check_website_status(url: str) -> str:
    """Check if a website is online.
    
    Args:
        url: The website URL to check
    
    Returns:
        Status message
    """
    try:
        response = requests.head(url, timeout=5)
        return f"{url} is {'online' if response.ok else 'offline'} (Status: {response.status_code})"
    except Exception as e:
        return f"Error checking {url}: {str(e)}"
```

## Using Custom Tools in Your Agent

```python
# In your agent file
from tools.web_tools import fetch_url, check_website_status
from tools.data_tools import parse_json, format_table

agent = Agent(
    model=model,
    tools=[
        fetch_url,
        check_website_status,
        parse_json,
        format_table
    ]
)
```

## Tool Organization Best Practices

### 1. Group by Category

```
tools/
├── web_tools.py        # HTTP requests, scraping, APIs
├── file_tools.py       # File operations, parsing
├── data_tools.py       # Data processing, formatting
├── notification_tools.py  # Email, Slack, SMS
└── analysis_tools.py   # Analytics, calculations
```

### 2. One File Per Domain

Keep related tools together:

```python
# tools/github_tools.py
@tool
def search_repos(...): ...

@tool
def get_repo_info(...): ...

@tool
def list_issues(...): ...
```

### 3. Document Every Tool

```python
@tool
def example_tool(param: str) -> str:
    """Clear description of what the tool does.
    
    Args:
        param: What this parameter is for
    
    Returns:
        What the tool returns
    
    Examples:
        >>> example_tool("test")
        "result"
    """
    return f"Processed: {param}"
```

### 4. Handle Errors Gracefully

```python
@tool
def safe_tool(input: str) -> str:
    """Tool with proper error handling."""
    try:
        # Your logic
        return "Success"
    except ValueError as e:
        return f"Invalid input: {e}"
    except Exception as e:
        return f"Error: {e}"
```

### 5. Add Type Hints

```python
from typing import Optional, List, Dict

@tool
def typed_tool(
    required: str,
    optional: Optional[int] = None,
    items: List[str] = []
) -> Dict[str, any]:
    """Tool with proper type hints."""
    return {"result": required}
```

## Common Tool Patterns

### API Integration Tool
```python
@tool
def call_external_api(endpoint: str) -> str:
    """Call an external API."""
    import requests
    try:
        response = requests.get(
            f"https://api.example.com/{endpoint}",
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return f"API Error: {e}"
```

### File Processing Tool
```python
@tool
def process_csv(filepath: str) -> str:
    """Process a CSV file."""
    import csv
    try:
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        return f"Processed {len(rows)} rows from {filepath}"
    except Exception as e:
        return f"Error: {e}"
```

### Async Tool
```python
import asyncio

@tool
async def async_operation(data: str) -> str:
    """Perform async operation."""
    await asyncio.sleep(1)  # Simulated async work
    return f"Async result: {data}"
```

### Tool with Context
```python
from strands import tool, ToolContext

@tool(context=True)
def contextual_tool(tool_context: ToolContext) -> str:
    """Tool that accesses invocation state."""
    user_id = tool_context.invocation_state.get("user_id")
    return f"Processing for user: {user_id}"
```

## Testing Your Tools

Create a test file for your tools:

**`tools/test_tools.py`**
```python
from tools.web_tools import fetch_url, check_website_status

def test_fetch_url():
    result = fetch_url("https://example.com")
    assert "Example Domain" in result
    print("✓ fetch_url works")

def test_check_status():
    result = check_website_status("https://google.com")
    assert "online" in result
    print("✓ check_website_status works")

if __name__ == "__main__":
    test_fetch_url()
    test_check_status()
    print("\n✅ All tools working!")
```

## Quick Reference

**Import tools:**
```python
from tools.web_tools import fetch_url
from tools.data_tools import parse_json
```

**Use in agent:**
```python
agent = Agent(
    model=model,
    tools=[fetch_url, parse_json]
)
```

**Combine with built-in tools:**
```python
from strands_tools import http_request, file_write
from tools.web_tools import fetch_url

agent = Agent(
    model=model,
    tools=[http_request, file_write, fetch_url]
)
```

---

**Pro Tip:** Start with a single `custom_tools.py` file. Only split into multiple files when you have 5+ tools.