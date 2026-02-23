#!/usr/bin/env python3
"""
Unified Strands Pack Agent

Interactive agent with all strands-pack tools available.
Select which tools to enable via command line or edit ENABLED_TOOLS below.

Usage:
    python examples/agent.py                    # Use default tools
    python examples/agent.py discord github    # Use specific tools
    python examples/agent.py --list            # List all available tools

Type 'exit' or 'quit' to end the session.
"""
import os
import sys
from pathlib import Path

# Load .env
_dotenv_path = Path.cwd() / ".env"
if not _dotenv_path.exists():
    _dotenv_path = Path(__file__).resolve().parents[1] / ".env"

try:
    from dotenv import load_dotenv
    if _dotenv_path.exists():
        load_dotenv(_dotenv_path)
except ImportError:
    pass

# Make Google auth path absolute if relative
_google_token = os.environ.get("GOOGLE_AUTHORIZED_USER_FILE", "")
if _google_token and not Path(_google_token).is_absolute():
    os.environ["GOOGLE_AUTHORIZED_USER_FILE"] = str(Path.cwd() / _google_token)

# =============================================================================
# TOOL REGISTRY - All available tools
# =============================================================================
TOOLS = {
    # Communication & Social
    "discord": ("discord", "Discord bot - send messages, manage channels, threads"),
    "gmail": ("gmail", "Gmail - send/read emails"),
    "twilio": ("twilio_tool", "Twilio - SMS and voice calls"),
    "x": ("x", "X/Twitter - read tweets, search (read-only)"),
    "linkedin": ("linkedin", "LinkedIn - posts and profile"),

    # Google Workspace
    "google_calendar": ("google_calendar", "Google Calendar - events management"),
    "google_docs": ("google_docs", "Google Docs - document editing"),
    "google_drive": ("google_drive", "Google Drive - file management"),
    "google_forms": ("google_forms", "Google Forms - create forms, read responses"),
    "google_sheets": ("google_sheets", "Google Sheets - spreadsheet operations"),
    "google_tasks": ("google_tasks", "Google Tasks - task lists"),

    # YouTube
    "youtube": ("youtube", "YouTube Data API - search, channels, playlists"),
    "youtube_analytics": ("youtube_analytics", "YouTube Analytics - channel stats"),
    "youtube_transcript": ("youtube_transcript", "YouTube transcripts - get captions"),

    # AWS Services
    "s3": ("s3", "AWS S3 - bucket and object operations"),
    "dynamodb": ("dynamodb", "AWS DynamoDB - NoSQL database"),
    "lambda": ("lambda_tool", "AWS Lambda - serverless functions"),
    "sns": ("sns", "AWS SNS - notifications"),
    "sqs": ("sqs", "AWS SQS - message queues"),
    "secrets_manager": ("secrets_manager", "AWS Secrets Manager"),
    "eventbridge": ("eventbridge_scheduler", "AWS EventBridge Scheduler"),
    "apigateway": ("apigateway_http_api", "AWS API Gateway HTTP API"),

    # Databases
    "sqlite": ("sqlite", "SQLite - local SQL database"),
    "chromadb": ("chromadb_tool", "ChromaDB - vector database"),

    # Productivity
    "notion": ("notion", "Notion - pages and databases"),
    "calendly": ("calendly", "Calendly - scheduling"),
    "excel": ("excel", "Excel - .xlsx file manipulation"),

    # Media & Files
    "image": ("image", "Image processing - resize, crop, convert"),
    "pdf": ("pdf", "PDF operations - read, extract, merge"),
    "audio": ("audio", "Audio processing - convert, trim, merge"),
    "ffmpeg": ("ffmpeg", "FFmpeg - video/audio processing"),
    "qrcode": ("qrcode_tool", "QR codes - generate and read"),
    "carbon": ("carbon", "Carbon - code screenshots"),

    # AI & Generation
    "gemini_image": ("gemini_image", "Gemini - image generation/editing"),
    "gemini_video": ("gemini_video", "Veo - video generation"),
    "gemini_music": ("gemini_music", "Lyria - music generation"),

    # Developer Tools
    "github": ("github", "GitHub - repos, issues, PRs"),
    "playwright": ("playwright_browser", "Playwright - browser automation"),
    "grab_code": ("grab_code", "Code reader - extract code from files"),

    # Smart Home
    "hue": ("hue", "Philips Hue - smart lighting"),

    # Agent Utilities
    "skills": ("skills", "Skills - load reusable multi-tool workflows"),
    "notify": ("notify", "Notify - local sound notifications"),
}

# Default tools to enable (edit this list)
DEFAULT_TOOLS = ["discord", "github", "google_forms"]


def load_tool(name: str):
    """Dynamically import a tool by name."""
    import importlib
    module_name, _ = TOOLS[name]
    module = importlib.import_module(f"strands_pack.{module_name.split('.')[-1]}")
    return getattr(module, module_name)


def list_tools():
    """Print all available tools."""
    print("\nAvailable Tools:")
    print("=" * 60)

    categories = {
        "Communication & Social": ["discord", "gmail", "twilio", "x", "linkedin"],
        "Google Workspace": ["google_calendar", "google_docs", "google_drive", "google_forms", "google_sheets", "google_tasks"],
        "YouTube": ["youtube", "youtube_analytics", "youtube_transcript"],
        "AWS Services": ["s3", "dynamodb", "lambda", "sns", "sqs", "secrets_manager", "eventbridge", "apigateway"],
        "Databases": ["sqlite", "chromadb"],
        "Productivity": ["notion", "calendly", "excel"],
        "Media & Files": ["image", "pdf", "audio", "ffmpeg", "qrcode", "carbon"],
        "AI & Generation": ["gemini_image", "gemini_video", "gemini_music"],
        "Developer Tools": ["github", "playwright", "grab_code"],
        "Smart Home": ["hue"],
        "Agent Utilities": ["skills", "notify"],
    }

    for category, tool_names in categories.items():
        print(f"\n{category}:")
        for name in tool_names:
            if name in TOOLS:
                _, desc = TOOLS[name]
                print(f"  {name:20} - {desc}")

    print("\n" + "=" * 60)
    print("Usage: python examples/agent.py <tool1> <tool2> ...")
    print("Example: python examples/agent.py discord github google_forms")


def main():
    args = sys.argv[1:]

    # Handle --list flag
    if "--list" in args or "-l" in args:
        list_tools()
        return

    # Determine which tools to load
    if args:
        tool_names = [t for t in args if t in TOOLS]
        invalid = [t for t in args if t not in TOOLS and not t.startswith("-")]
        if invalid:
            print(f"Unknown tools: {', '.join(invalid)}")
            print("Use --list to see available tools")
            return
    else:
        tool_names = DEFAULT_TOOLS

    if not tool_names:
        print("No tools selected. Use --list to see available tools.")
        return

    # Load selected tools
    tools = []
    print("Loading tools...")
    for name in tool_names:
        try:
            tool = load_tool(name)
            tools.append(tool)
            print(f"  + {name}")
        except ImportError as e:
            print(f"  - {name} (missing dependencies: {e})")

    if not tools:
        print("No tools loaded successfully.")
        return

    # Create agent
    from strands import Agent
    agent = Agent(tools=tools)

    print(f"\nAgent Ready! Tools: {', '.join(tool_names)}")
    print("Type 'exit' to quit.\n")

    while True:
        try:
            prompt = input("You: ").strip()
            if prompt.lower() in ("exit", "quit", "q"):
                break
            if prompt == "--list":
                list_tools()
                continue
            if prompt:
                agent(prompt)
                print()
        except (KeyboardInterrupt, EOFError):
            break

    print("Goodbye!")


if __name__ == "__main__":
    main()
