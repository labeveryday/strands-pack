# strands-pack

[![PyPI version](https://badge.fury.io/py/strands-pack.svg)](https://badge.fury.io/py/strands-pack)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-832%20passed-brightgreen.svg)](https://github.com/labeveryday/strands-pack)

**51 ready-to-use tools for [Strands Agents](https://github.com/strands-agents/sdk-python)**

AI media generation, AWS services, Google Workspace, social platforms, smart home, and more.

---

## Installation

```bash
pip install strands-pack
```

Install optional dependencies for specific tools:

```bash
pip install strands-pack[gemini]     # Gemini AI (image, video, music)
pip install strands-pack[openai]     # OpenAI (image, video, embeddings)
pip install strands-pack[aws]        # AWS (S3, DynamoDB, Lambda, SQS, SNS)
pip install strands-pack[gmail]      # Gmail API
pip install strands-pack[discord]    # Discord bot
pip install strands-pack[all]        # Everything
```

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

### Productivity

| Tool | Description |
|------|-------------|
| `notion` | Pages and databases |
| `calendly` | Scheduling |
| `excel` | Excel file manipulation |
| `pdf` | PDF operations |
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

Created by **Du'An Lightfoot** ([@labeveryday](https://github.com/labeveryday))
