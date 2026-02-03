# strands-pack

[![PyPI version](https://badge.fury.io/py/strands-pack.svg)](https://badge.fury.io/py/strands-pack)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-831%20passed-brightgreen.svg)](https://github.com/labeveryday/strands-pack)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

Custom tool library for [Strands Agents](https://github.com/strands-agents/sdk-python) by LabEveryday.

A collection of 51 tools that extend Strands Agents with capabilities for AI-powered media generation, cloud services, productivity APIs, smart home control, and more.

Created by **Du'An Lightfoot** ([@labeveryday](https://github.com/labeveryday))
- Website: [duanlightfoot.com](https://duanlightfoot.com)
- YouTube: [LabEveryday](https://youtube.com/@labeveryday)

---

## Installation

```bash
# Basic installation
pip install strands-pack

# Install specific tool dependencies
pip install strands-pack[gemini]      # AI media generation
pip install strands-pack[openai]      # OpenAI (openai_image, openai_video, openai_embeddings)
pip install strands-pack[dotenv]      # Load .env files in examples (local dev convenience)
pip install strands-pack[google_auth] # Google OAuth helper (google_auth tool + token generator)
pip install strands-pack[aws]         # AWS services (SNS, SQS, S3, DynamoDB, Lambda)
pip install strands-pack[notion]      # Notion API
pip install strands-pack[discord]     # Discord bot
pip install strands-pack[github]      # GitHub API
pip install strands-pack[hue]         # Philips Hue smart lighting

# Install all dependencies
pip install strands-pack[all]
```

## Quick Start

```python
from strands import Agent
from strands_pack import gemini_image, openai_image, sqlite, hue

agent = Agent(tools=[gemini_image, openai_image, sqlite, hue])

agent("Generate an image of a sunset over mountains")
agent("Analyze this thumbnail for YouTube effectiveness")
agent("Create a SQLite database to track my tasks")
agent("Turn on the office lights and set them to blue")
```

---

## Available Tools

Each tool includes detailed usage examples in its source file docstring.

### AI & Media Generation

| Tool | Install | Description |
|------|---------|-------------|
| `gemini_image` | `[gemini]` | Image generation and editing with Google Gemini |
| `gemini_video` | `[gemini]` | Video generation with Google Veo |
| `gemini_music` | `[gemini]` | Music generation with Google Lyria |
| `openai_image` | `[openai]` | Image generation, editing, analysis with OpenAI GPT |
| `openai_video` | `[openai]` | Video generation with OpenAI Videos API (Sora models) |
| `carbon` | `[carbon]` | Code screenshot generation via Carbon.now.sh |
| `ffmpeg` | - | Video cutting, concatenation, and audio extraction |

### AWS Services

| Tool | Install | Description |
|------|---------|-------------|
| `sns` | `[aws]` | SNS topic and subscription management |
| `sqs` | `[aws]` | SQS queue and message management |
| `s3` | `[aws]` | S3 bucket and object operations |
| `dynamodb` | `[aws]` | DynamoDB table and item operations |
| `lambda_tool` | `[aws]` | Lambda function management and invocation |
| `eventbridge_scheduler` | `[aws]` | EventBridge schedule management |
| `apigateway_http_api` | `[aws]` | API Gateway HTTP API (v2): Lambda routes + JWT/IAM auth (no API keys/usage plans) |
| `apigateway_rest_api` | `[aws]` | API Gateway REST API with API keys + usage plans |
| `secrets_manager` | `[aws]` | Secrets Manager access (safe-by-default) |
| `list_managed_resources` | `[aws]` | Inventory of AWS resources tagged `managed-by=strands-pack` |

## AWS “agent infrastructure” vision (recommended workflow)

This repo is designed so an agent can safely stand up a small, serverless “agent app”:

- **State**: `dynamodb` (create table + put/get/update/query/scan)
- **Code**: `lambda_tool` (create functions from zip)
- **Triggers**:
  - **API Gateway → Lambda**: `apigateway_http_api` (route creation auto-adds invoke permission)
  - **S3 → Lambda**: `s3(action="add_lambda_trigger")` (configures bucket notifications + invoke permission)
  - **Scheduler → Lambda**: `eventbridge_scheduler(action="create_lambda_schedule")` (creates schedule + invoke permission)

### Lambda execution role requirement

When creating a Lambda, the AWS API requires an execution role ARN.

- **Production posture**: set `STRANDS_PACK_LAMBDA_ROLE_ALLOWLIST` and pass an explicit allowlisted `role_arn`.
- **Dev posture**: if no allowlist is set, you can opt-in to logs-only auto role creation by setting
  `STRANDS_PACK_LAMBDA_ALLOW_AUTO_ROLE_CREATE=true` and calling `lambda_tool(..., auto_create_role=True)`.

### Current coverage + remaining gaps

Your “full serverless flow” looks like this:

- **S3 bucket** → Lambda
- **SQS queue** → Lambda (poll-based)
- **EventBridge (Scheduler)** → Lambda
- **API Gateway** → Lambda
- Lambda → **S3 / DynamoDB** (execution permissions via role)

**Current state (what works today):**

- **S3 trigger**: `s3(action="add_lambda_trigger", ...)` configures bucket notifications + invoke permission
- **SNS trigger**: `sns(action="subscribe_lambda", ...)` subscribes Lambda + adds invoke permission
- **SQS trigger**: `lambda_tool(action="create_event_source_mapping", ...)` creates poll-based event source mapping
- **API Gateway (HTTP) trigger**: `apigateway_http_api(action="add_lambda_route", ...)` auto-adds invoke permission
- **API Gateway (REST) trigger**: `apigateway_rest_api(action="create_rest_lambda_api", ...)` creates API with keys + usage plans
- **Scheduler trigger**: `eventbridge_scheduler(action="create_lambda_schedule", ...)` creates schedule + invoke permission
- **DynamoDB tables + items**: `dynamodb` supports table describe/delete(confirm), batch ops, scan (capped), and generic query
- **S3 ops**: `s3` supports copy/head, bucket create/delete(confirm)
- **Inventory**: `list_managed_resources(...)` lists resources tagged `managed-by=strands-pack` across supported AWS services

### Tagging (production-minded defaults)

All AWS resources created by strands-pack tools are tagged with at least:
- `managed-by=strands-pack`
- `component=<tool>`

You can add organization-specific tags (e.g., `env`, `owner`, `cost-center`) by setting `STRANDS_PACK_AWS_TAGS`
or passing `tags={...}` to supported create actions.

**Remaining considerations:**

- **Execution-role templates for data access**: logs-only auto-role is dev-only; real workloads need a role that grants
  least-privilege access to your agent buckets/tables (ideally provisioned via IaC + allowlist).

### Google Workspace

| Tool | Install | Description |
|------|---------|-------------|
| `gmail` | `[gmail]` | Send emails, list/search messages |
| `google_calendar` | `[calendar]` | Calendar and event management |
| `google_drive` | `[drive]` | File upload, download, and search |
| `google_sheets` | `[sheets]` | Spreadsheet read/write operations |
| `google_docs` | `[docs]` | Document creation and editing |
| `google_tasks` | `[tasks]` | Task list management |
| `google_forms` | `[forms]` | Form creation and response management |
| `youtube_read` | `[youtube]` | YouTube Data API (read): search, metadata, playlists, captions |
| `youtube_write` | `[youtube]` | YouTube Data API (write): update title/description/tags + playlist membership |
| `youtube_analytics` | `[youtube]` | YouTube Analytics API |
| `youtube_transcript` | `[youtube_transcript]` | Public transcript extraction |

Notes:
- `youtube` remains as a backwards-compatible alias to `youtube_read`.

### Developer Tools

| Tool | Install | Description |
|------|---------|-------------|
| `github` | `[github]` | Issues, PRs, repos, and code search (21 actions) |
| `playwright_browser` | `[playwright]` | Browser automation: navigate, screenshot, click, fill, extract |
| `grab_code` | - | Read source code with line numbers |

### Social & Communication

| Tool | Install | Description |
|------|---------|-------------|
| `discord` | `[discord]` | Discord bot messaging and channel management (13 actions) |
| `linkedin` | `[linkedin]` | Profile and posting (limited API) |
| `x` | `[x]` | Twitter/X read-only operations |
| `twilio_tool` | `[twilio]` | SMS, voice calls, and WhatsApp |

### Productivity

| Tool | Install | Description |
|------|---------|-------------|
| `notion` | `[notion]` | Pages, databases, and blocks |
| `calendly` | `[calendly]` | Scheduling and event management |
| `excel` | `[excel]` | Local .xlsx file manipulation |
| `pdf` | `[pdf]` | PDF text extraction, merge, split |
| `image` | `[image]` | Image resize, crop, convert, watermark |
| `audio` | `[audio]` | Audio trim, concat, convert, normalize |
| `qrcode_tool` | `[qrcode]` | QR code generation and decoding |

### Data & Storage

| Tool | Install | Description |
|------|---------|-------------|
| `sqlite` | - | Local SQLite database operations |
| `local_queue` | - | Local SQLite-backed queue (SQS-like) |
| `local_scheduler` | - | Local SQLite-backed scheduler (EventBridge-like) |
| `local_embeddings` | `[local_embeddings]` | Local embeddings via SentenceTransformers (no API keys) |
| `openai_embeddings` | `[openai_embeddings]` | OpenAI embeddings API |
| `chromadb_tool` | `[chromadb]` | Vector database for semantic search |

## Local durable jobs (developer-simple)

If you want the durable-jobs pattern locally (no AWS), you can combine:

- **State**: `sqlite` (or direct SQLite file)
- **Queue**: `local_queue` (SQS-like: send/receive/delete, plus send_batch/delete_batch)
- **Scheduler**: `local_scheduler` (EventBridge-like: schedule_at/schedule_in/schedule_rate, update_schedule, and `run_due`)

Important: `local_scheduler` only runs when you call `run_due` periodically.
In local dev, that’s typically a simple loop or a cron job.

Example flow:

```python
from strands_pack import local_scheduler, local_queue

db_path = "./data/app.db"

# Schedule a message in 60 seconds
local_scheduler(
    action="schedule_in",
    db_path=db_path,
    delay_seconds=60,
    queue_name="jobs",
    message_body='{"job_id":"123"}',
)

# In a dev loop, enqueue due schedules...
local_scheduler(action="run_due", db_path=db_path, max_to_run=50)

# ...and consume messages
msg = local_queue(action="receive", db_path=db_path, queue_name="jobs", max_messages=1)
```

## Embeddings + vector search (quick pattern)

If you want semantic search locally:

1) Generate embeddings with `local_embeddings`  
2) Store and query them with `chromadb_tool`

If you prefer OpenAI-hosted embeddings, use `openai_embeddings` instead.

### Smart Home

| Tool | Install | Description |
|------|---------|-------------|
| `hue` | `[hue]` | Philips Hue smart lighting (23 actions: lights, groups, scenes, toggle, blink, effects) |

### Agent Utilities

| Tool | Install | Description |
|------|---------|-------------|
| `skills` | - | Load reusable multi-tool workflow instructions (Anthropic agentskills.io format) |
| `notify` | - | Local sound notifications (beep, play_file) with rate limiting |

### Utility Functions

| Function | Description |
|----------|-------------|
| `validate_email` | Email format validation |
| `count_lines_in_file` | File line counting |
| `save_json` / `load_json` | JSON file operations |
| `format_timestamp` | Timestamp formatting |
| `extract_urls` | URL extraction from text |
| `word_count` | Text analysis |

---

## Environment Variables

Set these based on which tools you use:

| Variable | Tools |
|----------|-------|
| `GOOGLE_API_KEY` | gemini_image, gemini_video, gemini_music |
| `OPENAI_API_KEY` | openai_image, openai_embeddings, openai_video |
| `GOOGLE_APPLICATION_CREDENTIALS` (optional) | Google Workspace tools (Calendar/Docs/Forms/Drive/Sheets/Tasks via ADC) |
| `GOOGLE_AUTHORIZED_USER_FILE` (optional) | Google Workspace tools (authorized-user OAuth token JSON path) |
| `GOOGLE_CLIENT_SECRETS_FILE` (optional) | google_auth (OAuth Desktop app client secrets JSON path) |
| `OAUTHLIB_INSECURE_TRANSPORT` (dev-only) | google_auth (localhost loopback OAuth; set to `1` for local dev, or pass `allow_insecure_transport=True`) |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION` | All AWS tools |
| `AWS_ACCOUNT_ID` (optional) | Used for more-specific Lambda invoke permission source ARNs (API Gateway / Scheduler) |
| `STRANDS_PACK_AWS_TAGS` (optional) | Extra AWS tags to apply to resources created by strands-pack (JSON or `k=v` pairs) |
| `STRANDS_PACK_LAMBDA_PREFIX` (optional) | lambda_tool + Lambda-trigger tools (default `agent-`) |
| `STRANDS_PACK_LAMBDA_ROLE_ALLOWLIST` (optional) | lambda_tool role allowlist (production posture) |
| `STRANDS_PACK_LAMBDA_ALLOW_AUTO_ROLE_CREATE` (dev-only) | lambda_tool can auto-create logs-only execution role when role_arn omitted |
| `STRANDS_PACK_API_PREFIX` (optional) | apigateway_http_api name guard (default `agent-`) |
| `STRANDS_PACK_SCHEDULE_PREFIX` (optional) | eventbridge_scheduler name guard (default `agent-`) |
| `DISCORD_BOT_TOKEN` | discord |
| `DISCORD_GUILD_ID` (optional) | discord |
| `DISCORD_CHANNEL_ID` (optional) | discord |
| `GITHUB_TOKEN` | github |
| `NOTION_TOKEN` | notion |
| `CALENDLY_TOKEN` | calendly |
| `LINKEDIN_ACCESS_TOKEN` | linkedin |
| `X_BEARER_TOKEN` | x |
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER` | twilio_tool |
| `HUE_BRIDGE_IP` | hue |

See `env.example` for a complete template.

Note: tools read from **process environment variables**. If you use a `.env` file locally,
either export variables in your shell or install `python-dotenv` and use the example scripts,
which will auto-load `.env` when available.

## Google Workspace (Gmail/Calendar/Docs/Forms) authentication

Most Google Workspace tools in this repo **do not use single "API key" env vars**. Instead they use Google Auth in one of these modes:

- **Enable these Google APIs in your Google Cloud project** (Google Cloud Console → APIs & Services → Library):
  - **Gmail tool**: **Gmail API**
  - **Google Calendar tool**: **Google Calendar API**
  - **Google Docs tool**: **Google Docs API**
  - **Google Forms tool**: **Google Forms API**
  - **Google Drive tool**: **Google Drive API**
  - **Google Sheets tool**: **Google Sheets API**
  - **Google Tasks tool**: **Google Tasks API**
  - **YouTube tool**: **YouTube Data API v3**
  - **YouTube Analytics tool**: **YouTube Analytics API**

- **Application Default Credentials (ADC)** (default for Calendar/Docs/Forms):
  - Local dev: run `gcloud auth application-default login` (optionally with scopes)
  - Server/GCP: attach a service account, or set `GOOGLE_APPLICATION_CREDENTIALS` to a service-account JSON file

- **Service account JSON**:
  - Pass `auth_type="service_account"` and `service_account_file="/path/to/service-account.json"`
  - Optional `delegated_user="user@domain.com"` if you configured domain-wide delegation

- **Authorized user token JSON (OAuth)**:
  - Pass `auth_type="authorized_user"` and `authorized_user_file="/path/to/token.json"`
  - For Gmail, pass `token_path="/path/to/token.json"`
  - To generate `token.json`, create a **Desktop app** OAuth client in Google Cloud, download the client secret JSON,
    then run:

```bash
python examples/google_oauth_token.py --client-secrets /path/to/client_secret.json --preset gmail --out token.json
```

You can also generate (and manage) the token from inside a Strands agent using the `google_auth` tool (recommended output path: `secrets/token.json`):

```python
from strands import Agent
from strands_pack import google_auth

agent = Agent(tools=[google_auth])
result = agent.tool.google_auth(action="setup", preset="forms", token_output_path="secrets/token.json")
# Open result["auth_url"] in your browser, approve access, then check:
# agent.tool.google_auth(action="status")  # token_exists should become True
```

Each tool’s module docstring includes the supported auth parameters and default scopes.

### Gmail: HTML + attachments

- **Hyperlinks**: send HTML bodies via `body_html` (use `<a href="...">text</a>`).
- **Attachments**: pass `attachments=[...]` with local file paths.
- **Download attachments**: use `list_attachments` and `download_attachment(s)`.

### Drive: export Google-native files

Use `google_drive(action="export_file", ...)` to export Docs/Sheets/Slides into common formats.

Common export MIME types:
- Docs → PDF: `application/pdf`
- Docs → DOCX: `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- Sheets → XLSX: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- Sheets → CSV: `text/csv`

---

## Usage Examples

Each tool's source file contains detailed usage examples in its docstring. For example:

```python
from strands_pack import hue

# View the tool's documentation and examples
help(hue)
```

Or check the source files in `src/strands_pack/` for comprehensive examples of each action.

An interactive example is available in the `examples/` folder.

---

## Development

```bash
# Clone and install
git clone https://github.com/labeveryday/strands-pack.git
cd strands-pack
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src tests

# Security scan
bandit -r src/
```

## License

MIT License

---

**Ready to build? Import the tools and start creating intelligent agents.**
