# Strands Agents Tools 

A comprehensive collection of custom tools for to extend agent capabilities.

Created by [Du'An Lightfoot](https://duanlightfoot.com) | [@labeveryday](https://github.com/labeveryday)

---


## Current Tools

### AWS Messaging Suite
- **SNS Tools** (`tools/sns_tools.py`) - Create topics, manage subscriptions, publish messages
- **SQS Tools** (`tools/sqs_tools.py`) - Queue management, message handling, monitoring

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/labeveryday/strands-tools.git
cd strands-tools

# 2. Set up Python environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -e .

# 4. Configure AWS credentials (for AWS tools)
aws configure  # or set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY

# 5. Run the example
python main.py
```

## Repository Structure

```
strands-tools/
├── README.md              # This file
├── pyproject.toml         # Project configuration
├── main.py               # Example usage
├── tools/
│   ├── __init__.py       # Package init
│   ├── README.md         # Tool development guide
│   ├── sns_tools.py      # SNS topic & subscription management
│   └── sqs_tools.py      # SQS queue & message management
└── .python-version       # Python version
```

## Using the Tools

### 1. Import Tools in Your Agent

```python
from strands import Agent

# Create agent with loaded tools from ./tools
agent = Agent(
    load_tools_from_directory=True
)
```

### 2. Example Workflow

```python
# Run agent with messaging workflow
response = agent("""
Create an SNS topic called 'notifications' and an SQS queue called 'alerts'.
Then publish a test message to the topic.
""")
print(response)
```


## Tool Features

### SNS Tools (`tools/sns_tools.py`)
- `create_topic()` - Create new SNS topics with display names
- `delete_topic()` - Remove topics safely  
- `list_topics()` - View all available topics
- `create_subscription()` - Subscribe endpoints (email, SQS, HTTP, etc.)
- `delete_subscription()` - Remove subscriptions
- `list_subscriptions()` - View topic subscriptions
- `publish_message()` - Send messages with optional subjects
- `verify_topic_exists()` - Check topic availability

### SQS Tools (`tools/sqs_tools.py`)
- `create_queue()` - Create queues with custom settings
- `delete_queue()` - Remove queues completely
- `list_queues()` - View all queues (with optional filtering)
- `send_message()` - Send direct messages to queues
- `receive_message()` - Get messages with long polling
- `purge_queue()` - Clear all messages from a queue
- `get_queue_message_count()` - Monitor queue statistics
- `verify_message_delivered()` - Check SNS→SQS message flow
- `cleanup_queue_messages()` - Delete specific messages

## Prerequisites

- **Python 3.10+**
- **AWS Account** with SNS/SQS permissions
- **AWS CLI configured** or environment variables set

## Dependencies

Dependencies are managed in `pyproject.toml`:

```toml
[project]
dependencies = [
    "strands-agents",
    "strands-agents-tools"
]
```

## Available Resources

- **[Strands Documentation](https://strandsagents.com/latest/)** - Official Strands docs
- **[AWS SNS Guide](https://docs.aws.amazon.com/sns/)** - AWS SNS documentation  
- **[AWS SQS Guide](https://docs.aws.amazon.com/sqs/)** - AWS SQS documentation

## Contributing

Contributions welcome! This repository is open for:
- Bug reports and fixes
- New tool additions
- Documentation improvements
- Performance optimizations

## License

MIT License - Use freely, build amazing things.

## About the Author

Built by **Du'An Lightfoot** ([@labeveryday](https://github.com/labeveryday))
- Website: [duanlightfoot.com](https://duanlightfoot.com)
- YouTube: [LabEveryday](https://youtube.com/@labeveryday)  
- Focus: AI agents, cloud infrastructure, teaching in public

---

**Ready to build? Import the tools and start creating intelligent agents today.**
