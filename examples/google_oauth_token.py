#!/usr/bin/env python3
"""
Generate an "authorized user" OAuth token JSON (token.json) for Google Workspace tools.

This script runs Google's Installed App OAuth flow (local browser consent) and writes a token
file that can be used with tools in this repo:
  - Gmail: token_path="token.json"
  - Calendar/Docs/Forms/Drive/Sheets/Tasks: auth_type="authorized_user", authorized_user_file="token.json"

Prereqs:
  1) In Google Cloud Console: APIs & Services -> Credentials -> Create OAuth client ID
     - Application type: Desktop app
     - Download the client secret JSON (e.g., client_secret.json)
  2) Enable the APIs you need (see README).

Usage:
  python examples/google_oauth_token.py --client-secrets client_secret.json --preset gmail --out token.json
  python examples/google_oauth_token.py --client-secrets client_secret.json --scopes "scope1,scope2" --out token.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List


PRESETS = {
    # Least-privilege defaults; expand scopes as needed.
    "gmail": [
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.labels",
        "https://www.googleapis.com/auth/gmail.compose",
    ],
    "calendar": [
        "https://www.googleapis.com/auth/calendar",
    ],
    "docs": [
        "https://www.googleapis.com/auth/documents",
    ],
    "forms": [
        "https://www.googleapis.com/auth/forms.body",
        "https://www.googleapis.com/auth/forms.responses.readonly",
    ],
    "drive": [
        "https://www.googleapis.com/auth/drive",
    ],
    "sheets": [
        "https://www.googleapis.com/auth/spreadsheets",
    ],
    "tasks": [
        "https://www.googleapis.com/auth/tasks",
    ],
    "youtube": [
        "https://www.googleapis.com/auth/youtube.readonly",
    ],
    "youtube_analytics": [
        "https://www.googleapis.com/auth/yt-analytics.readonly",
    ],
}


def _split_scopes(scopes: str) -> List[str]:
    return [s.strip() for s in scopes.split(",") if s.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate an authorized-user OAuth token JSON for Google tools.")
    parser.add_argument(
        "--client-secrets",
        required=True,
        help="Path to OAuth client secret JSON (Desktop app).",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--preset",
        choices=sorted(PRESETS.keys()),
        help="Predefined scope bundle for a tool (least-privilege-ish defaults).",
    )
    group.add_argument(
        "--scopes",
        help="Comma-separated list of OAuth scopes to request.",
    )
    parser.add_argument(
        "--out",
        default="token.json",
        help='Output path for authorized-user token JSON (default: "token.json").',
    )
    parser.add_argument(
        "--no-local-server",
        action="store_true",
        help="Use an out-of-band flow (paste a code) instead of starting a local redirect server.",
    )
    args = parser.parse_args()

    client_secrets = Path(args.client_secrets).expanduser().resolve()
    if not client_secrets.exists():
        raise SystemExit(f"Client secrets file not found: {client_secrets}")

    scopes = PRESETS[args.preset] if args.preset else _split_scopes(args.scopes)
    if not scopes:
        raise SystemExit("No scopes provided.")

    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as e:  # pragma: no cover
        raise SystemExit(
            "google-auth-oauthlib is not installed. Install with: pip install google-auth-oauthlib"
        ) from e

    flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets), scopes=scopes)
    if args.no_local_server:
        creds = flow.run_console()
    else:
        # Spins up a local redirect server and opens the browser.
        creds = flow.run_local_server(port=0)

    out_path.write_text(creds.to_json(), encoding="utf-8")

    meta_path = out_path.with_suffix(out_path.suffix + ".scopes.json")
    meta_path.write_text(json.dumps({"scopes": scopes}, indent=2), encoding="utf-8")

    print(f"Wrote authorized-user token to: {out_path}")
    print(f"Wrote scopes metadata to: {meta_path}")
    print("Keep these files secret (they grant account access).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


