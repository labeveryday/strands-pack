# strands-pack

[![Awesome Strands Agents](https://img.shields.io/badge/Awesome-Strands%20Agents-00FF77?style=flat-square&logo=data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjkwIiBoZWlnaHQ9IjQ2MyIgdmlld0JveD0iMCAwIDI5MCA0NjMiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik05Ny4yOTAyIDUyLjc4ODRDODUuMDY3NCA0OS4xNjY3IDcyLjIyMzQgNTYuMTM4OSA2OC42MDE3IDY4LjM2MTZDNjQuOTgwMSA4MC41ODQzIDcxLjk1MjQgOTMuNDI4MyA4NC4xNzQ5IDk3LjA1MDFMMjM1LjExNyAxMzkuNzc1QzI0NS4yMjMgMTQyLjc2OSAyNDYuMzU3IDE1Ni42MjggMjM2Ljg3NCAxNjEuMjI2TDMyLjU0NiAyNjAuMjkxQy0xNC45NDM5IDI4My4zMTYgLTkuMTYxMDcgMzUyLjc0IDQxLjQ4MzUgMzY3LjU5MUwxODkuNTUxIDQxMS4wMDlMMTkwLjEyNSA0MTEuMTY5QzIwMi4xODMgNDE0LjM3NiAyMTQuNjY1IDQwNy4zOTYgMjE4LjE5NiAzOTUuMzU1QzIyMS43ODQgMzgzLjEyMiAyMTQuNzc0IDM3MC4yOTYgMjAyLjU0MSAzNjYuNzA5TDU0LjQ3MzggMzIzLjI5MUM0NC4zNDQ3IDMyMC4zMjEgNDMuMTg3OSAzMDYuNDM2IDUyLjY4NTcgMzAxLjgzMUwyNTcuMDE0IDIwMi43NjZDMzA0LjQzMiAxNzkuNzc2IDI5OC43NTggMTEwLjQ4MyAyNDguMjMzIDk1LjUxMkw5Ny4yOTAyIDUyLjc4ODRaIiBmaWxsPSIjRkZGRkZGIi8+CjxwYXRoIGQ9Ik0yNTkuMTQ3IDAuOTgxODEyQzI3MS4zODkgLTIuNTc0OTggMjg0LjE5NyA0LjQ2NTcxIDI4Ny43NTQgMTYuNzA3NEMyOTEuMzExIDI4Ljk0OTIgMjg0LjI3IDQxLjc1NyAyNzIuMDI4IDQ1LjMxMzhMNzEuMTcyNyAxMDMuNjcxQzQwLjcxNDIgMTEyLjUyMSAzNy4xOTc2IDE1NC4yNjIgNjUuNzQ1OSAxNjguMDgzTDI0MS4zNDMgMjUzLjA5M0MzMDcuODcyIDI4NS4zMDIgMjk5Ljc5NCAzODIuNTQ2IDIyOC44NjIgNDAzLjMzNkwzMC40MDQxIDQ2MS41MDJDMTguMTcwNyA0NjUuMDg4IDUuMzQ3MDggNDU4LjA3OCAxLjc2MTUzIDQ0NS44NDRDLTEuODIzOSA0MzMuNjExIDUuMTg2MzcgNDIwLjc4NyAxNy40MTk3IDQxNy4yMDJMMjE1Ljg3OCAzNTkuMDM1QzI0Ni4yNzcgMzUwLjEyNSAyNDkuNzM5IDMwOC40NDkgMjIxLjIyNiAyOTQuNjQ1TDQ1LjYyOTcgMjA5LjYzNUMtMjAuOTgzNCAxNzcuMzg2IC0xMi43NzcyIDc5Ljk4OTMgNTguMjkyOCA1OS4zNDAyTDI1OS4xNDcgMC45ODE4MTJaIiBmaWxsPSIjRkZGRkZGIi8+Cjwvc3ZnPgo=&logoColor=white)](https://github.com/cagataycali/awesome-strands-agents)

[![PyPI version](https://badge.fury.io/py/strands-pack.svg)](https://badge.fury.io/py/strands-pack)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-893%20passed-brightgreen.svg)](https://github.com/labeveryday/strands-pack)

**54 ready-to-use tools for [Strands Agents](https://github.com/strands-agents/sdk-python)**

AI media generation, AWS services, Google Workspace, social platforms, smart home, and more.

---

## Installation

```bash
pip install strands-pack                    # lightweight core
pip install strands-pack[aws]               # add AWS tools (boto3)
pip install strands-pack[gmail,youtube]     # add specific tools
pip install strands-pack[all]               # install everything
```

Install only the extras you need. Each tool's dependencies are listed in the optional groups below.

---

## Quick Start

```python
from strands import Agent
from strands_pack import gemini_image, gmail, discord, sqlite

agent = Agent(tools=[gemini_image, gmail, discord, sqlite])

agent("Generate an image of a mountain sunset")
agent("Send an email to team@company.com about the project update")
agent("Post 'Hello World!' to the announcements channel")
agent("Create a tasks table and add 'Review PR' as a new task")
```

---

## Tools

### AI & Media

| Tool | Description |
|------|-------------|
| `gemini_image` | Image generation/editing (Google Gemini) |
| `gemini_video` | Video generation (Google Veo) |
| `gemini_music` | Music generation (Google Lyria) |
| `openai_image` | Image generation/editing/analysis (OpenAI) |
| `openai_video` | Video generation (OpenAI Sora) |
| `carbon` | Code screenshots |
| `ffmpeg` | Video/audio processing |

### AWS

| Tool | Description |
|------|-------------|
| `s3` | Bucket and object operations |
| `dynamodb` | NoSQL database operations |
| `lambda_tool` | Function management and invocation |
| `sqs` | Message queue operations |
| `sns` | Pub/sub notifications |
| `eventbridge_scheduler` | Scheduled tasks |
| `apigateway_http_api` | HTTP APIs with Lambda |
| `apigateway_rest_api` | REST APIs with API keys |
| `secrets_manager` | Secrets access (safe-by-default) |
| `list_managed_resources` | Inventory of strands-pack managed resources |

### Google Workspace

| Tool | Description |
|------|-------------|
| `gmail` | Send/read emails, attachments |
| `google_calendar` | Events and scheduling |
| `google_drive` | File management |
| `google_sheets` | Spreadsheet operations |
| `google_docs` | Document editing |
| `google_tasks` | Task lists |
| `google_forms` | Forms and responses |

### YouTube

| Tool | Description |
|------|-------------|
| `youtube_read` | Search, metadata, playlists |
| `youtube_write` | Update videos, manage playlists |
| `youtube_analytics` | Channel statistics |
| `youtube_transcript` | Get video transcripts |

- **Auth model**
  - **`youtube_read`**: API key only (`YOUTUBE_API_KEY`)
  - **`youtube_write` / `youtube_analytics`**: OAuth required
  - **`youtube_transcript`**: no auth (public videos)

### Social & Communication

| Tool | Description |
|------|-------------|
| `discord` | Messages, channels, threads (13 actions) |
| `github` | Repos, issues, PRs (21 actions) |
| `linkedin` | Posts and profile |
| `x` | Twitter/X (read-only) |
| `twilio_tool` | SMS, voice, WhatsApp |

### Cloud Storage

| Tool | Description |
|------|-------------|
| `box` | Box Platform: files, folders, metadata, tasks, shared links, Box AI (20 actions) |

### Productivity

| Tool | Description |
|------|-------------|
| `notion` | Pages and databases |
| `calendly` | Scheduling |
| `excel` | Excel file manipulation |
| `pdf` | PDF operations |
| `pdf_to_markdown` | PDF to markdown conversion (LLM-ready) |
| `image` | Image processing |
| `audio` | Audio processing |
| `qrcode_tool` | QR code generation/reading |

### Data & Storage

| Tool | Description |
|------|-------------|
| `sqlite` | Local SQL database |
| `chromadb_tool` | Vector database |
| `local_queue` | SQLite-backed queue (SQS-like) |
| `local_scheduler` | SQLite-backed scheduler |
| `local_embeddings` | Local embeddings (SentenceTransformers) |
| `openai_embeddings` | OpenAI embeddings API |
| `keyword_search` | BM25 keyword search for hybrid retrieval |

### Developer & Utilities

| Tool | Description |
|------|-------------|
| `playwright_browser` | Browser automation |
| `grab_code` | Read source code with line numbers |
| `skills` | Reusable multi-tool workflows |
| `notify` | Local sound notifications |
| `hue` | Philips Hue smart lighting (23 actions) |

---

## Environment Variables

Set the variables for the tools you use:

```bash
# AI Services
GOOGLE_API_KEY=           # Gemini tools
OPENAI_API_KEY=           # OpenAI tools

# AWS
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_DEFAULT_REGION=

# Google Workspace (OAuth token path)
GOOGLE_AUTHORIZED_USER_FILE=secrets/token.json

# YouTube (read-only public data via API key)
YOUTUBE_API_KEY=
# Optional defaults (so you can omit IDs in prompts)
YOUTUBE_CHANNEL_ID=
YOUTUBE_UPLOADS_PLAYLIST_ID=

# Box (choose one auth method)
BOX_DEVELOPER_TOKEN=              # Testing (60 min)
# BOX_CLIENT_ID=                  # CCG auth
# BOX_CLIENT_SECRET=
# BOX_JWT_CONFIG_PATH=            # JWT config file

# Social
DISCORD_BOT_TOKEN=
GITHUB_TOKEN=
NOTION_TOKEN=

# See env.example for all options
```

---

## Google Workspace Authentication

Google tools use OAuth, not API keys. Generate a token:

```bash
# 1. Create OAuth Desktop app in Google Cloud Console
# 2. Download client_secret.json
# 3. Run:
python examples/google_oauth_token.py \
  --client-secrets client_secret.json \
  --preset gmail \
  --out secrets/token.json
```

Or use the `google_auth` tool interactively:

```python
from strands_pack import google_auth

result = google_auth(action="setup", preset="gmail", token_output_path="secrets/token.json")
print(result["auth_url"])  # Open this URL, approve access
```

---

## Examples

```python
# Generate an image
from strands_pack import gemini_image
result = gemini_image(action="generate", prompt="A cat in space", output_filename="cat.png")

# Send a Discord message
from strands_pack import discord
discord(action="send_message", channel_id="123456", content="Hello!")

# Query a database
from strands_pack import sqlite
sqlite(action="query", db_path="app.db", sql="SELECT * FROM users")

# Control smart lights
from strands_pack import hue
hue(action="set_light", light_id=1, on=True, brightness=200, hue=10000)
```

Check each tool's docstring for all available actions:

```python
from strands_pack import discord
help(discord)
```

---

## Development

```bash
git clone https://github.com/labeveryday/strands-pack.git
cd strands-pack
pip install -e ".[dev]"
pytest
```

---

## License

MIT License

---

Created by [Du'An Lightfoot](https://duanlightfoot.com) | [@labeveryday](https://github.com/labeveryday)
