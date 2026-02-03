"""
Google OAuth Authentication - Shared Module

Provides shared authentication for all Google Workspace tools.
When credentials are missing, you can run an OAuth flow to generate an "authorized user" token JSON.

Usage:
    from strands_pack.google_auth import get_credentials, needs_auth_response

    # In your Google tool:
    creds = get_credentials(scopes=["https://www.googleapis.com/auth/tasks"])
    if creds is None:
        return needs_auth_response("tasks")

Standalone Tool:
    from strands import Agent
    from strands_pack import google_auth

    agent = Agent(tools=[google_auth])
    agent("Check my Google auth status")
    agent("Set up Google Tasks authentication")
"""

from __future__ import annotations

import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
from urllib.parse import parse_qs, urlparse

from strands import tool

# Scope presets for different Google services
SCOPE_PRESETS: Dict[str, List[str]] = {
    "tasks": ["https://www.googleapis.com/auth/tasks"],
    "forms": [
        "https://www.googleapis.com/auth/forms.body",
        "https://www.googleapis.com/auth/forms.responses.readonly",
    ],
    "calendar": ["https://www.googleapis.com/auth/calendar"],
    "gmail": [
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.labels",
        "https://www.googleapis.com/auth/gmail.compose",
    ],
    "drive": ["https://www.googleapis.com/auth/drive"],
    "sheets": ["https://www.googleapis.com/auth/spreadsheets"],
    "docs": ["https://www.googleapis.com/auth/documents"],
    "youtube": ["https://www.googleapis.com/auth/youtube.readonly"],
    "youtube_analytics": ["https://www.googleapis.com/auth/yt-analytics.readonly"],
    # Write access (used by youtube_write tool)
    "youtube_write": ["https://www.googleapis.com/auth/youtube.force-ssl"],
}

# Union preset: convenient “one-time auth” for local dev or single-tenant production.
# (For multi-tenant SaaS, you’d typically do incremental consent in the app UI.)
SCOPE_PRESETS["all"] = sorted({s for scopes in SCOPE_PRESETS.values() for s in scopes})

try:
    from google.oauth2.credentials import Credentials as UserCredentials
    from google.oauth2 import service_account
    from google.auth import default as google_auth_default
    from google.auth.transport.requests import Request

    HAS_GOOGLE_AUTH = True
except ImportError:
    UserCredentials = None
    service_account = None
    google_auth_default = None
    Request = None
    HAS_GOOGLE_AUTH = False

try:
    from google_auth_oauthlib.flow import InstalledAppFlow

    HAS_OAUTH_LIB = True
except ImportError:
    InstalledAppFlow = None
    HAS_OAUTH_LIB = False


_PENDING_FLOWS: Dict[str, Dict[str, Any]] = {}


def _get_secrets_dir() -> Path:
    """Get the secrets directory path."""
    return Path.cwd() / "secrets"


def _get_token_path() -> Path:
    """Get token path from env or default to secrets/token.json."""
    env_path = os.environ.get("GOOGLE_AUTHORIZED_USER_FILE")
    if env_path:
        p = Path(env_path)
        if not p.is_absolute():
            p = Path.cwd() / p
        return p.resolve()
    return _get_secrets_dir() / "token.json"


def _get_client_secrets_path() -> Optional[Path]:
    """Find client secrets file."""
    # Check env var first
    env_path = os.environ.get("GOOGLE_CLIENT_SECRETS_FILE")
    if env_path:
        p = Path(env_path)
        if not p.is_absolute():
            p = Path.cwd() / p
        if p.exists():
            return p.resolve()

    # Check secrets directory
    secrets_dir = _get_secrets_dir()
    if secrets_dir.exists():
        # Look for client_secret*.json
        for f in secrets_dir.glob("client_secret*.json"):
            return f.resolve()
        # Also check for credentials.json
        creds_file = secrets_dir / "credentials.json"
        if creds_file.exists():
            return creds_file.resolve()

    # Check current directory
    for name in ["client_secret.json", "credentials.json"]:
        p = Path.cwd() / name
        if p.exists():
            return p.resolve()

    return None


def _load_token(token_path: Path) -> Optional[Any]:
    """Load existing token if valid."""
    if not HAS_GOOGLE_AUTH:
        return None
    if not token_path.exists():
        return None

    try:
        creds = UserCredentials.from_authorized_user_file(str(token_path))
        # Try to refresh if expired
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Save refreshed token
            token_path.write_text(creds.to_json(), encoding="utf-8")
        return creds
    except Exception:
        return None


def _token_has_scopes(token_path: Path, required_scopes: List[str]) -> bool:
    """Check if token has required scopes."""
    scopes_file = token_path.with_suffix(token_path.suffix + ".scopes.json")
    if not scopes_file.exists():
        # Try to read from token itself
        if token_path.exists():
            try:
                with open(token_path) as f:
                    data = json.load(f)
                    token_scopes = data.get("scopes", [])
                    return all(s in token_scopes for s in required_scopes)
            except Exception:
                pass
        return False

    try:
        with open(scopes_file) as f:
            data = json.load(f)
            token_scopes = data.get("scopes", [])
            return all(s in token_scopes for s in required_scopes)
    except Exception:
        return False


def _token_scopes(token_path: Path) -> List[str]:
    """Best-effort read of scopes for a token (from *.scopes.json or the token itself)."""
    scopes_file = token_path.with_suffix(token_path.suffix + ".scopes.json")
    if scopes_file.exists():
        try:
            with open(scopes_file) as f:
                data = json.load(f)
                return [str(s).strip() for s in (data.get("scopes", []) or []) if str(s).strip()]
        except Exception:
            return []
    if token_path.exists():
        try:
            with open(token_path) as f:
                data = json.load(f)
                return [str(s).strip() for s in (data.get("scopes", []) or []) if str(s).strip()]
        except Exception:
            return []
    return []


def get_credentials(
    scopes: List[str],
    service_account_file: Optional[str] = None,
    authorized_user_file: Optional[str] = None,
    delegated_user: Optional[str] = None,
) -> Optional[Any]:
    """
    Get valid Google credentials.

    Returns credentials if available and valid, None if auth is needed.

    Args:
        scopes: Required OAuth scopes
        service_account_file: Path to service account JSON (optional)
        authorized_user_file: Path to user token JSON (optional, uses default if not set)
        delegated_user: User to impersonate with service account (optional)
    """
    if not HAS_GOOGLE_AUTH:
        return None

    # Try service account first if provided
    sa_file = service_account_file or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if sa_file:
        sa_path = Path(sa_file)
        if not sa_path.is_absolute():
            sa_path = Path.cwd() / sa_path
        if sa_path.exists():
            try:
                creds = service_account.Credentials.from_service_account_file(
                    str(sa_path), scopes=scopes
                )
                if delegated_user or os.environ.get("GOOGLE_DELEGATED_USER"):
                    creds = creds.with_subject(
                        delegated_user or os.environ.get("GOOGLE_DELEGATED_USER")
                    )
                return creds
            except Exception:
                pass

    # Try authorized user token
    if authorized_user_file:
        token_path = Path(authorized_user_file)
        if not token_path.is_absolute():
            token_path = Path.cwd() / token_path
    else:
        token_path = _get_token_path()

    # Check if token exists and has required scopes
    if token_path.exists() and _token_has_scopes(token_path, scopes):
        creds = _load_token(token_path)
        if creds and creds.valid:
            return creds

    # No valid credentials found
    return None


def run_oauth_flow(
    scopes: List[str],
    client_secrets_path: Optional[Path] = None,
    token_output_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Run OAuth flow (blocking) using a localhost redirect server.

    This prints an authorization URL and waits until the user completes consent in their browser.

    Returns dict with success status, token path, or error.
    """
    if not HAS_OAUTH_LIB:
        return {
            "success": False,
            "error": "google-auth-oauthlib not installed. Run: pip install google-auth-oauthlib",
        }

    # Find client secrets
    secrets_path = client_secrets_path or _get_client_secrets_path()
    if not secrets_path or not secrets_path.exists():
        return {
            "success": False,
            "error": "Client secrets file not found",
            "hint": "Download OAuth client JSON from Google Cloud Console and save to secrets/client_secret.json",
            "searched_locations": [
                "GOOGLE_CLIENT_SECRETS_FILE env var",
                "secrets/client_secret*.json",
                "secrets/credentials.json",
                "client_secret.json",
            ],
        }

    # Determine output path
    out_path = token_output_path or _get_token_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # NOTE: This blocking helper is kept for backwards compatibility, but it is not
    # ideal inside an agent loop (it waits). Prefer google_auth(action="start", ...).
    result = start_auth_loopback(scopes=scopes, client_secrets_path=secrets_path, token_output_path=out_path)
    if not result.get("success"):
        return result
    auth_id = result.get("auth_id")
    # Wait until done or error
    for _ in range(600):  # ~300s at 0.5s
        state = _PENDING_FLOWS.get(auth_id or "")
        if not state:
            break
        if state.get("done"):
            return {
                "success": True,
                "message": "Authentication successful! Token saved.",
                "token_path": state.get("token_output_path"),
                "scopes": scopes,
            }
        if state.get("error"):
            return {"success": False, "error": state.get("error")}
        time.sleep(0.5)
    return {"success": False, "error": "Timed out waiting for authorization", "auth_url": result.get("auth_url")}


def run_oauth_flow_console(
    scopes: List[str],
    client_secrets_path: Optional[Path] = None,
    token_output_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Run OAuth flow using console mode - user pastes the auth code.

    Avoids redirect/port issues with local server approach.
    """
    if not HAS_OAUTH_LIB:
        return {
            "success": False,
            "error": "google-auth-oauthlib not installed. Run: pip install google-auth-oauthlib",
        }

    # Find client secrets
    secrets_path = client_secrets_path or _get_client_secrets_path()
    if not secrets_path or not secrets_path.exists():
        return {
            "success": False,
            "error": "Client secrets file not found",
            "hint": "Download OAuth client JSON from Google Cloud Console and save to secrets/client_secret.json",
        }

    # Determine output path
    out_path = token_output_path or _get_token_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        flow = InstalledAppFlow.from_client_secrets_file(str(secrets_path), scopes=scopes)

        # Some versions don't provide run_console(). In general, console flows are not a great fit for
        # tool calls (they require interactive user input). Keep this as a "helpful pointer".
        auth_url, state = flow.authorization_url(prompt="consent", access_type="offline")

        if hasattr(flow, "run_console"):
            creds = flow.run_console()  # type: ignore[attr-defined]
            out_path.write_text(creds.to_json(), encoding="utf-8")
            scopes_path = out_path.with_suffix(out_path.suffix + ".scopes.json")
            scopes_path.write_text(json.dumps({"scopes": scopes}, indent=2), encoding="utf-8")
            return {"success": True, "message": "Authentication successful! Token saved.", "token_path": str(out_path), "scopes": scopes}

        return {
            "success": False,
            "error": "Console auth is not supported by your installed google-auth-oauthlib version (missing run_console).",
            "auth_url": auth_url,
            "state": state,
            "hint": "Use google_auth(action='setup'/'start') loopback flow for local dev, or run examples/google_oauth_token.py.",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def _pick_free_port() -> int:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return int(s.getsockname()[1])


def start_auth_loopback(
    scopes: List[str],
    client_secrets_path: Optional[Path] = None,
    token_output_path: Optional[Path] = None,
    allow_insecure_transport: bool = False,
) -> Dict[str, Any]:
    """
    Start a non-blocking OAuth flow using a localhost (loopback) redirect server.

    Returns an authorization URL immediately and starts a background thread that waits for
    the browser redirect and saves the token JSON when consent completes.
    """
    if not HAS_OAUTH_LIB:
        return {"success": False, "error": "google-auth-oauthlib not installed. Run: pip install google-auth-oauthlib"}

    secrets_path = client_secrets_path or _get_client_secrets_path()
    if not secrets_path or not secrets_path.exists():
        return {
            "success": False,
            "error": "Client secrets file not found",
            "hint": "Download OAuth client JSON from Google Cloud Console and save to secrets/client_secret.json",
        }

    out_path = token_output_path or _get_token_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # OAuthlib enforces HTTPS by default. For local development loopback redirects to localhost (http://localhost:*),
    # oauthlib requires OAUTHLIB_INSECURE_TRANSPORT=1. We do NOT enable this silently for production safety.
    if allow_insecure_transport:
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    elif os.environ.get("OAUTHLIB_INSECURE_TRANSPORT") != "1":
        return {
            "success": False,
            "error": "(insecure_transport) OAuth 2 MUST utilize https.",
            "hint": "For local dev loopback OAuth, set OAUTHLIB_INSECURE_TRANSPORT=1 (dev-only). In production, use an HTTPS redirect URI in your web app.",
        }

    flow = InstalledAppFlow.from_client_secrets_file(str(secrets_path), scopes=scopes)
    port = _pick_free_port()
    redirect_uri = f"http://localhost:{port}/"
    flow.redirect_uri = redirect_uri
    auth_url, state = flow.authorization_url(prompt="consent", access_type="offline")

    auth_id = str(state or "") or f"auth-{int(time.time())}"

    _PENDING_FLOWS[auth_id] = {
        "auth_id": auth_id,
        "auth_url": auth_url,
        "port": port,
        "token_output_path": str(out_path),
        "client_secrets_path": str(secrets_path),
        "scopes": scopes,
        "started_at": time.time(),
        "finished_at": None,
        "done": False,
        "error": None,
    }

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            try:
                parsed = urlparse(self.path)
                params = parse_qs(parsed.query or "")
                code = (params.get("code") or [None])[0]
                returned_state = (params.get("state") or [None])[0]

                if not code:
                    raise ValueError("Missing 'code' in callback URL.")
                if state and returned_state and returned_state != state:
                    raise ValueError("(mismatching_state) CSRF Warning! State not equal in request and response.")

                auth_response = f"{redirect_uri}?code={code}&state={returned_state or ''}"
                flow.fetch_token(authorization_response=auth_response)
                creds = flow.credentials

                out_path.write_text(creds.to_json(), encoding="utf-8")
                scopes_path = out_path.with_suffix(out_path.suffix + ".scopes.json")
                scopes_path.write_text(json.dumps({"scopes": scopes}, indent=2), encoding="utf-8")
                _PENDING_FLOWS[auth_id]["done"] = True

                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"Authorization successful. You can close this tab.")
            except Exception as e:  # pragma: no cover
                _PENDING_FLOWS[auth_id]["error"] = str(e)
                _PENDING_FLOWS[auth_id]["done"] = False
                self.send_response(500)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(f"Authorization failed: {e}".encode("utf-8"))
            finally:
                # Shutdown the server after handling one request.
                threading.Thread(target=httpd.shutdown, daemon=True).start()

        def log_message(self, format, *args):  # noqa: A002
            # Silence server logs in agent runs.
            return

    def _worker():
        try:
            # Local redirect server to capture the OAuth callback.
            nonlocal httpd
            httpd = HTTPServer(("localhost", port), _Handler)
            _PENDING_FLOWS[auth_id]["listening"] = True
            httpd.serve_forever()
        except Exception as e:
            _PENDING_FLOWS[auth_id]["error"] = str(e)
            _PENDING_FLOWS[auth_id]["done"] = False
        finally:
            _PENDING_FLOWS[auth_id]["finished_at"] = time.time()

    httpd: HTTPServer
    t = threading.Thread(target=_worker, daemon=True)
    _PENDING_FLOWS[auth_id]["thread"] = t
    t.start()

    return {
        "success": True,
        "auth_id": auth_id,
        "auth_url": auth_url,
        "token_output_path": str(out_path),
        "message": "Open auth_url in your browser to authorize. Then run google_auth(action='status') until token_exists is true.",
    }


def start_auth(
    scopes: List[str],
    client_secrets_path: Optional[Path] = None,
    redirect_uri: str = "urn:ietf:wg:oauth:2.0:oob",
) -> Dict[str, Any]:
    """
    Start a manual two-step OAuth flow (non-blocking).

    Returns an authorization URL plus an auth_id that can be passed to complete_auth().
    Note: Some Google clients may not support OOB anymore. If completion fails, use action="setup"
    (localhost redirect) instead.
    """
    if not HAS_OAUTH_LIB:
        return {"success": False, "error": "google-auth-oauthlib not installed. Run: pip install google-auth-oauthlib"}

    secrets_path = client_secrets_path or _get_client_secrets_path()
    if not secrets_path or not secrets_path.exists():
        return {
            "success": False,
            "error": "Client secrets file not found",
            "hint": "Download OAuth client JSON from Google Cloud Console and save to secrets/client_secret.json",
        }

    flow = InstalledAppFlow.from_client_secrets_file(str(secrets_path), scopes=scopes)
    flow.redirect_uri = redirect_uri
    auth_url, state = flow.authorization_url(prompt="consent", access_type="offline")

    auth_id = str(state or "") or str(len(_PENDING_FLOWS) + 1)
    _PENDING_FLOWS[auth_id] = {
        "flow": flow,
        "auth_id": auth_id,
        "auth_url": auth_url,
        "scopes": scopes,
        "started_at": time.time(),
        "finished_at": None,
        "done": False,
        "error": None,
    }

    return {
        "success": True,
        "auth_url": auth_url,
        "auth_id": auth_id,
        "message": "Open auth_url, approve access, then call google_auth(action='complete', auth_id=..., code=...).",
    }


def complete_auth(
    *,
    auth_id: str,
    code: str,
    token_output_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Complete a two-step OAuth flow started by start_auth()."""
    entry = _PENDING_FLOWS.get(auth_id)
    if not entry or not isinstance(entry, dict) or "flow" not in entry:
        return {"success": False, "error": f"Unknown auth_id: {auth_id}", "hint": "Call google_auth(action='start', ...) first."}
    flow = entry["flow"]

    out_path = token_output_path or _get_token_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        flow.fetch_token(code=code)
        creds = flow.credentials
        out_path.write_text(creds.to_json(), encoding="utf-8")
        scopes_path = out_path.with_suffix(out_path.suffix + ".scopes.json")
        scopes_path.write_text(json.dumps({"scopes": getattr(flow, 'scopes', [])}, indent=2), encoding="utf-8")
        _PENDING_FLOWS.pop(auth_id, None)
        return {"success": True, "message": "Authentication successful! Token saved.", "token_path": str(out_path)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def needs_auth_response(preset: str, scopes: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Generate a response indicating auth is needed.

    Use this in Google tools when credentials are missing.
    """
    scope_list = scopes or SCOPE_PRESETS.get(preset, [])
    client_secrets = _get_client_secrets_path()

    if not client_secrets:
        return {
            "success": False,
            "error": "Authentication required but no client secrets found",
            "auth_required": True,
            "preset": preset,
            "hint": "Download OAuth client JSON from Google Cloud Console and save to secrets/client_secret.json",
        }

    token_path = _get_token_path()
    existing_scopes = _token_scopes(token_path)
    missing_scopes = [s for s in scope_list if s not in set(existing_scopes)]
    union_scopes = sorted(set(existing_scopes).union(scope_list))

    return {
        "success": False,
        "error": f"Authentication required for Google {preset.title()}",
        "auth_required": True,
        "preset": preset,
        "scopes": scope_list,
        "token_path": str(token_path),
        "existing_scopes": existing_scopes,
        "missing_scopes": missing_scopes,
        "scopes_union": union_scopes,
        "action_needed": f'Run: google_auth(action="setup", preset="{preset}") to authenticate',
        "action_needed_union": (
            'Run: google_auth(action="setup", scopes="'
            + ",".join(union_scopes)
            + '") to upgrade your existing token to the union of scopes'
        ),
    }


# =============================================================================
# Standalone Tool
# =============================================================================


@tool
def google_auth(
    action: Literal["status", "setup", "setup_console", "start", "complete", "revoke"],
    preset: Optional[str] = None,
    scopes: Optional[str] = None,
    code: Optional[str] = None,
    auth_id: Optional[str] = None,
    client_secrets_file: Optional[str] = None,
    token_output_path: Optional[str] = None,
    allow_insecure_transport: bool = False,
    merge_existing_scopes: bool = True,
) -> Dict[str, Any]:
    """
    Google OAuth authentication tool.

    Authentication options:
    - setup: one-shot, blocking localhost flow (prints URL, waits until completed)
    - setup_console: one-shot, blocking console flow (paste code)
    - start: non-blocking loopback flow (returns auth_url immediately; saves token after you complete consent)
    - complete: legacy/manual flow (requires auth_id + code). Prefer start/setup instead.

    Args:
        action: One of:
            - status: Check current auth status
            - setup: Run blocking localhost OAuth flow and save token
            - setup_console: Run blocking console OAuth flow and save token
            - start: Start non-blocking loopback OAuth flow (returns auth_url + auth_id)
            - complete: Complete legacy/manual flow (requires auth_id + code)
            - revoke: Delete existing token
        preset: Scope preset (tasks, forms, calendar, gmail, drive, sheets, docs, youtube, youtube_analytics)
        scopes: Custom scopes (comma-separated) - alternative to preset
        code: Authorization code from Google (for action="complete")
        auth_id: Auth id from action="start" (for action="complete")
        client_secrets_file: Optional path to OAuth client secrets JSON (defaults to env/auto-detect)
        token_output_path: Optional path to write token JSON (defaults to GOOGLE_AUTHORIZED_USER_FILE or secrets/token.json)
        allow_insecure_transport: Set True to enable local-dev loopback OAuth over http://localhost (dev-only)
        merge_existing_scopes: If a token already exists, merge its recorded scopes with newly requested scopes (default True)

    Examples:
        google_auth(action="status")
        google_auth(action="setup", preset="tasks")
        google_auth(action="setup_console", preset="tasks")
        google_auth(action="start", preset="tasks")
        google_auth(action="complete", auth_id="...", code="...")
        google_auth(action="revoke")
    """
    if action == "status":
        token_path = _get_token_path()
        client_secrets = _get_client_secrets_path()

        result = {
            "success": True,
            "action": "status",
            "token_exists": token_path.exists(),
            "token_path": str(token_path),
            "client_secrets_found": client_secrets is not None,
            "client_secrets_path": str(client_secrets) if client_secrets else None,
            "available_presets": list(SCOPE_PRESETS.keys()),
        }

        if _PENDING_FLOWS:
            result["pending_auth"] = {
                k: {
                    "done": (v.get("done") if isinstance(v, dict) else None),
                    "error": (v.get("error") if isinstance(v, dict) else None),
                    "started_at": (v.get("started_at") if isinstance(v, dict) else None),
                    "finished_at": (v.get("finished_at") if isinstance(v, dict) else None),
                    "token_output_path": (v.get("token_output_path") if isinstance(v, dict) else None),
                    "listening": (v.get("listening") if isinstance(v, dict) else None),
                    "auth_url": (v.get("auth_url") if isinstance(v, dict) else None),
                }
                for k, v in _PENDING_FLOWS.items()
            }

        if token_path.exists():
            scopes_file = token_path.with_suffix(token_path.suffix + ".scopes.json")
            if scopes_file.exists():
                try:
                    with open(scopes_file) as f:
                        data = json.load(f)
                        result["current_scopes"] = data.get("scopes", [])
                except Exception:
                    pass

        return result

    if action == "revoke":
        token_path = _get_token_path()
        scopes_file = token_path.with_suffix(token_path.suffix + ".scopes.json")

        deleted = []
        if token_path.exists():
            token_path.unlink()
            deleted.append(str(token_path))
        if scopes_file.exists():
            scopes_file.unlink()
            deleted.append(str(scopes_file))

        if deleted:
            return {"success": True, "message": "Token revoked", "deleted": deleted}
        return {"success": True, "message": "No token found to revoke"}

    # Determine scopes
    if preset:
        if preset not in SCOPE_PRESETS:
            return {
                "success": False,
                "error": f"Unknown preset: {preset}",
                "available_presets": list(SCOPE_PRESETS.keys()),
            }
        scope_list = SCOPE_PRESETS[preset]
    elif scopes:
        scope_list = [s.strip() for s in scopes.split(",") if s.strip()]
    else:
        return {
            "success": False,
            "error": "Must specify 'preset' or 'scopes'",
            "available_presets": list(SCOPE_PRESETS.keys()),
        }

    secrets_path = None
    if client_secrets_file:
        secrets_path = Path(client_secrets_file)
        if not secrets_path.is_absolute():
            secrets_path = Path.cwd() / secrets_path
        secrets_path = secrets_path.resolve()

    out_path = None
    if token_output_path:
        out_path = Path(token_output_path)
        if not out_path.is_absolute():
            out_path = Path.cwd() / out_path
        out_path = out_path.resolve()

    # If a token already exists with other scopes, merge them so users don't "lose" prior access
    # when requesting a new preset (common during development).
    if merge_existing_scopes:
        token_path = out_path or _get_token_path()
        scopes_file = token_path.with_suffix(token_path.suffix + ".scopes.json")
        existing: List[str] = []
        if scopes_file.exists():
            try:
                with open(scopes_file) as f:
                    data = json.load(f)
                    existing = [str(s).strip() for s in (data.get("scopes", []) or []) if str(s).strip()]
            except Exception:
                existing = []
        if existing:
            scope_list = sorted(set(existing).union(scope_list))

    if action == "setup":
        if not HAS_OAUTH_LIB:
            return {
                "success": False,
                "error": "google-auth-oauthlib not installed. Run: pip install google-auth-oauthlib",
            }
        # Agent-friendly: return auth_url immediately and write the token after the user completes consent.
        return start_auth_loopback(
            scope_list,
            client_secrets_path=secrets_path,
            token_output_path=out_path,
            allow_insecure_transport=allow_insecure_transport,
        )

    if action == "setup_console":
        return run_oauth_flow_console(scope_list, client_secrets_path=secrets_path, token_output_path=out_path)

    if action == "start":
        return start_auth_loopback(
            scope_list,
            client_secrets_path=secrets_path,
            token_output_path=out_path,
            allow_insecure_transport=allow_insecure_transport,
        )

    if action == "complete":
        if not auth_id or not code:
            return {"success": False, "error": "auth_id and code are required for action='complete'"}
        return complete_auth(auth_id=auth_id, code=code, token_output_path=out_path)

    return {"success": False, "error": f"Unknown action: {action}", "available_actions": ["status", "setup", "setup_console", "start", "complete", "revoke"]}
