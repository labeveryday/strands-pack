import json
import os
from importlib import import_module
from pathlib import Path
from unittest.mock import patch

# Import the module (not the tool) for patching
google_auth_mod = import_module("strands_pack.google_auth")


def test_google_auth_merges_existing_scopes_by_default(tmp_path: Path):
    """
    If a token scope metadata file exists, google_auth() should merge those scopes with newly requested ones
    so re-auth doesn't "lose" previously granted access.
    """
    token_path = tmp_path / "token.json"
    scopes_path = tmp_path / "token.json.scopes.json"
    scopes_path.write_text(json.dumps({"scopes": ["https://www.googleapis.com/auth/tasks"]}), encoding="utf-8")

    captured = {}

    def fake_start_auth_loopback(scopes, client_secrets_path=None, token_output_path=None, allow_insecure_transport=False):
        captured["scopes"] = scopes
        captured["allow_insecure_transport"] = allow_insecure_transport
        captured["token_output_path"] = str(token_output_path) if token_output_path else None
        return {"success": True, "auth_url": "x", "token_output_path": str(token_output_path)}

    from strands_pack import google_auth as google_auth_tool

    with patch.object(google_auth_mod, "HAS_OAUTH_LIB", True), patch.object(
        google_auth_mod, "start_auth_loopback", side_effect=fake_start_auth_loopback
    ):
        res = google_auth_tool(
            action="setup",
            preset="sheets",
            token_output_path=str(token_path),
            allow_insecure_transport=True,
        )

    assert res["success"] is True
    assert "https://www.googleapis.com/auth/tasks" in captured["scopes"]
    assert "https://www.googleapis.com/auth/spreadsheets" in captured["scopes"]


def test_google_auth_can_disable_scope_merge(tmp_path: Path):
    token_path = tmp_path / "token.json"
    scopes_path = tmp_path / "token.json.scopes.json"
    scopes_path.write_text(json.dumps({"scopes": ["https://www.googleapis.com/auth/tasks"]}), encoding="utf-8")

    captured = {}

    def fake_start_auth_loopback(scopes, client_secrets_path=None, token_output_path=None, allow_insecure_transport=False):
        captured["scopes"] = scopes
        return {"success": True, "auth_url": "x", "token_output_path": str(token_output_path)}

    from strands_pack import google_auth as google_auth_tool

    with patch.object(google_auth_mod, "HAS_OAUTH_LIB", True), patch.object(
        google_auth_mod, "start_auth_loopback", side_effect=fake_start_auth_loopback
    ):
        res = google_auth_tool(
            action="setup",
            preset="sheets",
            token_output_path=str(token_path),
            allow_insecure_transport=True,
            merge_existing_scopes=False,
        )

    assert res["success"] is True
    assert captured["scopes"] == ["https://www.googleapis.com/auth/spreadsheets"]


def test_google_auth_passes_allow_insecure_transport_flag(tmp_path: Path):
    token_path = tmp_path / "token.json"

    captured = {}

    def fake_start_auth_loopback(scopes, client_secrets_path=None, token_output_path=None, allow_insecure_transport=False):
        captured["allow_insecure_transport"] = allow_insecure_transport
        return {"success": True, "auth_url": "x", "token_output_path": str(token_output_path)}

    from strands_pack import google_auth as google_auth_tool

    with patch.object(google_auth_mod, "HAS_OAUTH_LIB", True), patch.object(
        google_auth_mod, "start_auth_loopback", side_effect=fake_start_auth_loopback
    ):
        res = google_auth_tool(
            action="setup",
            preset="tasks",
            token_output_path=str(token_path),
            allow_insecure_transport=True,
        )

    assert res["success"] is True
    assert captured["allow_insecure_transport"] is True


def test_google_auth_gmail_preset_includes_modify_labels_compose(tmp_path: Path):
    from strands_pack import google_auth as google_auth_tool

    captured = {}

    def fake_start_auth_loopback(scopes, client_secrets_path=None, token_output_path=None, allow_insecure_transport=False):
        captured["scopes"] = scopes
        return {"success": True, "auth_url": "x", "token_output_path": str(token_output_path)}

    with patch.object(google_auth_mod, "HAS_OAUTH_LIB", True), patch.object(
        google_auth_mod, "start_auth_loopback", side_effect=fake_start_auth_loopback
    ):
        res = google_auth_tool(
            action="setup",
            preset="gmail",
            token_output_path=str(tmp_path / "token.json"),
            allow_insecure_transport=True,
        )

    assert res["success"] is True
    assert "https://www.googleapis.com/auth/gmail.modify" in captured["scopes"]
    assert "https://www.googleapis.com/auth/gmail.labels" in captured["scopes"]
    assert "https://www.googleapis.com/auth/gmail.compose" in captured["scopes"]


def test_google_auth_all_preset_includes_multiple_services(tmp_path: Path):
    from strands_pack import google_auth as google_auth_tool

    captured = {}

    def fake_start_auth_loopback(scopes, client_secrets_path=None, token_output_path=None, allow_insecure_transport=False):
        captured["scopes"] = scopes
        return {"success": True, "auth_url": "x", "token_output_path": str(token_output_path)}

    with patch.object(google_auth_mod, "HAS_OAUTH_LIB", True), patch.object(
        google_auth_mod, "start_auth_loopback", side_effect=fake_start_auth_loopback
    ):
        res = google_auth_tool(
            action="setup",
            preset="all",
            token_output_path=str(tmp_path / "token.json"),
            allow_insecure_transport=True,
        )

    assert res["success"] is True
    # A few representative scopes from different tools
    assert "https://www.googleapis.com/auth/drive" in captured["scopes"]
    assert "https://www.googleapis.com/auth/calendar" in captured["scopes"]
    assert "https://www.googleapis.com/auth/spreadsheets" in captured["scopes"]
    assert "https://www.googleapis.com/auth/gmail.modify" in captured["scopes"]


def test_needs_auth_response_includes_missing_scopes(tmp_path: Path, monkeypatch):
    # Point token path to temp and write a scopes metadata file with one scope
    token_path = tmp_path / "token.json"
    scopes_path = tmp_path / "token.json.scopes.json"
    scopes_path.write_text(json.dumps({"scopes": ["https://www.googleapis.com/auth/tasks"]}), encoding="utf-8")

    monkeypatch.setenv("GOOGLE_AUTHORIZED_USER_FILE", str(token_path))

    resp = google_auth_mod.needs_auth_response("sheets")
    assert resp["auth_required"] is True
    assert resp["token_path"].endswith("token.json")
    assert "existing_scopes" in resp and "missing_scopes" in resp and "scopes_union" in resp
    assert "https://www.googleapis.com/auth/tasks" in resp["existing_scopes"]
    assert "https://www.googleapis.com/auth/spreadsheets" in resp["missing_scopes"]
    assert "https://www.googleapis.com/auth/spreadsheets" in resp["scopes_union"]

def test_start_auth_loopback_requires_insecure_transport_opt_in(tmp_path: Path):
    """
    start_auth_loopback should not silently enable insecure transport. If neither the env var nor the
    explicit flag is set, it should fail with an insecure_transport error before touching oauth libs.
    """
    # Provide an existing client secrets file so we get past the "file not found" check.
    client_secrets = tmp_path / "client_secret.json"
    client_secrets.write_text("{}", encoding="utf-8")

    with patch.object(google_auth_mod, "HAS_OAUTH_LIB", True), patch.dict(os.environ, {"OAUTHLIB_INSECURE_TRANSPORT": ""}, clear=False):
        res = google_auth_mod.start_auth_loopback(
            scopes=["https://www.googleapis.com/auth/tasks"],
            client_secrets_path=client_secrets,
            token_output_path=tmp_path / "token.json",
            allow_insecure_transport=False,
        )

    assert res["success"] is False
    assert "insecure_transport" in res["error"]


