# Google Auth in `strands-pack`

This library shares **one authentication layer** across all Google tools (Gmail, Calendar, Drive, Docs, Sheets, Tasks, YouTube, YouTube Analytics, etc.) via `src/strands_pack/google_auth.py`.

## Key idea: one token, many tools (scope union)

Google user OAuth tokens are **scoped**. If you mint a token with only one tool’s scopes and later need another tool, you must **re-authorize** to add scopes.

`strands-pack` is designed so you keep **one token file** and “upgrade” it over time:

- All Google tools call `get_credentials(scopes=[...])`.
- If your current token doesn’t include the required scopes, the tool returns an `auth_required` response with what to do next.
- The `google_auth` tool supports **scope merging** (union) so you don’t “lose” previously granted access when you add a new tool.

## Authentication modes supported

### 1) Authorized user OAuth token (recommended for “act as me”)

This is the common “installed app” / “login in browser” flow that creates an **authorized-user token JSON** (with a refresh token) that the tools can reuse.

- Stored as a JSON file (default: `./secrets/token.json`)
- Used by tools when no service account/ADC is provided

**Environment variables**
- `GOOGLE_AUTHORIZED_USER_FILE`: path to the token JSON to use (defaults to `./secrets/token.json`)
- `GOOGLE_CLIENT_SECRETS_FILE`: path to OAuth client secrets JSON downloaded from Google Cloud Console (Desktop app client)
- `OAUTHLIB_INSECURE_TRANSPORT=1`: *local-dev only* for loopback `http://localhost` OAuth redirects

### 2) Service account / Application Default Credentials (ADC)

If you’re running on a server or GCP environment, you can use ADC or a service account key file.

**Environment variables**
- `GOOGLE_APPLICATION_CREDENTIALS`: path to service account JSON (enables service account credentials)
- `GOOGLE_DELEGATED_USER`: optional user email for domain-wide delegation (Google Workspace admin feature)

Notes:
- Many consumer/YouTube “write” workflows are typically authorized-user OAuth, not service accounts.

## How tools decide which credentials to use

When a Google tool needs credentials, it uses this precedence (simplified):

1. **Service account**: if `GOOGLE_APPLICATION_CREDENTIALS` is set (or `service_account_file` passed), create service-account credentials for the tool’s required scopes (optionally with delegation).
2. **Authorized user token**: otherwise load from `GOOGLE_AUTHORIZED_USER_FILE` (or default `./secrets/token.json`) and verify it includes required scopes.
3. If nothing valid exists, return `auth_required`.

## Token file + scopes metadata

When you authenticate, the library writes:

- `token.json` (authorized-user credential JSON)
- `token.json.scopes.json` (a small metadata file that records which scopes were requested)

This scope metadata is used so later auth requests can **merge** (“union”) scopes instead of replacing them.

## The `google_auth` tool (how you authenticate)

The library provides a Strands tool `google_auth(...)` to help create/upgrade your token.

### Recommended workflows

#### A) One-time “enable everything” (fastest for single-user dev)

Authenticate once with the union of scopes:

- `google_auth(action="setup", preset="all", allow_insecure_transport=True)`

This is the simplest way to avoid repeated prompts while you develop.

#### B) Incremental “approve as needed” (least-privilege)

Authenticate tool-by-tool; the token is upgraded to include the union:

- `google_auth(action="setup", preset="drive", allow_insecure_transport=True)`
- later: `google_auth(action="setup", preset="gmail", allow_insecure_transport=True)`
- later: `google_auth(action="setup", preset="calendar", allow_insecure_transport=True)`

Because `merge_existing_scopes=True` by default, you keep one token file with a growing scope set.

### Presets

Presets live in `SCOPE_PRESETS` in `src/strands_pack/google_auth.py`.

Common ones:
- `gmail`, `calendar`, `drive`, `docs`, `sheets`, `tasks`, `forms`
- `youtube`, `youtube_analytics`
- `youtube_write` (write scope for `youtube_write` tool)
- `all` (union of all presets)

### What you get when auth is required

Google tools will typically return a structured payload like:

- `auth_required: true`
- `preset` + `scopes`
- `token_path`
- `existing_scopes`, `missing_scopes`, `scopes_union`
- `action_needed` and `action_needed_union`

The intent is that an agent (or your UI) can:
- show the auth link / instruction
- let you approve
- then continue once the token exists with the needed scopes

## Production guidance (what “make it work” means in prod)

For production apps, don’t do a localhost loopback flow on the server.

Recommended patterns:

- **Single-tenant (you only)**: keep one encrypted token store (DB/Secrets Manager/etc.), use the same “scope union” strategy, and re-auth when new features need new scopes.
- **Multi-tenant (many users)**: store per-user credentials, and use incremental consent in your web UI. Your agent should detect `auth_required` and route the user through your UI’s OAuth flow.

Never store refresh tokens in `.env`. Use a secure secret store.


