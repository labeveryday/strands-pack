"""
Notify Tool (Local Sound)
------------------------

Local-only sound notifications (best-effort).

Important:
- Cloud runtimes (Lambda/ECS/EC2) cannot "play a sound" for a human, so this tool
  does **not** attempt to deliver remote notifications (use `sns` or other tools
  for that).

Requires:
    - Local sound: no extra dependencies (uses system tools best-effort)

"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, Literal, Optional

from strands import tool

Action = Literal["notify", "beep", "play_file"]
Level = Literal["info", "success", "warning", "error"]

_RECENT: Deque[float] = deque()
_RECENT_DEDUPE: Dict[str, float] = {}


def _ok(**data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": True}
    out.update(data)
    return out


def _err(message: str, **data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": False, "error": message}
    out.update(data)
    return out


def _is_aws_runtime() -> bool:
    # Lambda: AWS_LAMBDA_FUNCTION_NAME / AWS_EXECUTION_ENV / LAMBDA_TASK_ROOT
    if os.getenv("AWS_LAMBDA_FUNCTION_NAME") or os.getenv("LAMBDA_TASK_ROOT") or os.getenv("AWS_EXECUTION_ENV"):
        return True
    # ECS: metadata URI env vars
    if os.getenv("ECS_CONTAINER_METADATA_URI") or os.getenv("ECS_CONTAINER_METADATA_URI_V4"):
        return True
    return False


def _rate_limit_ok(rate_limit_per_minute: int) -> bool:
    if rate_limit_per_minute <= 0:
        return True
    now = time.time()
    window = 60.0
    while _RECENT and (now - _RECENT[0]) > window:
        _RECENT.popleft()
    if len(_RECENT) >= rate_limit_per_minute:
        return False
    _RECENT.append(now)
    return True


def _dedupe_ok(dedupe_key: Optional[str], dedupe_window_seconds: int) -> bool:
    if not dedupe_key:
        return True
    now = time.time()
    last = _RECENT_DEDUPE.get(dedupe_key)
    if last is not None and (now - last) < dedupe_window_seconds:
        return False
    _RECENT_DEDUPE[dedupe_key] = now
    return True


def _play_beep() -> None:
    # Terminal bell (best-effort)
    try:
        sys.stdout.write("\a")
        sys.stdout.flush()
    except Exception:
        pass

    # macOS: also try a system sound for better reliability
    if sys.platform == "darwin":
        afplay = shutil.which("afplay")
        if afplay:
            # System sound file usually exists; if not, fallback silently.
            candidates = [
                "/System/Library/Sounds/Glass.aiff",
                "/System/Library/Sounds/Ping.aiff",
                "/System/Library/Sounds/Pop.aiff",
            ]
            for c in candidates:
                if Path(c).exists():
                    try:
                        subprocess.run([afplay, c], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        break
                    except Exception:
                        continue


def _play_file(path: str) -> None:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")

    # Prefer OS-native players. Best-effort only.
    if sys.platform == "darwin":
        player = shutil.which("afplay")
        if not player:
            raise RuntimeError("afplay not found on PATH")
        subprocess.run([player, str(p)], check=False)
        return

    if sys.platform.startswith("linux"):
        # Try aplay, then paplay
        player = shutil.which("aplay") or shutil.which("paplay")
        if not player:
            raise RuntimeError("No audio player found (aplay/paplay) on PATH")
        subprocess.run([player, str(p)], check=False)
        return

    # Windows: PowerShell PlaySound
    if sys.platform.startswith("win"):
        ps = shutil.which("powershell") or shutil.which("pwsh")
        if not ps:
            raise RuntimeError("PowerShell not found on PATH")
        escaped_path = str(p).replace("'", "''")
        cmd = (
            "[void][System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms');"
            f"$p='{escaped_path}';"
            "$player = New-Object System.Media.SoundPlayer($p);"
            "$player.PlaySync();"
        )
        subprocess.run([ps, "-NoProfile", "-Command", cmd], check=False)
        return

    raise RuntimeError(f"Unsupported platform for play_file: {sys.platform}")


@tool
def notify(
    action: str,
    title: Optional[str] = None,
    message: Optional[str] = None,
    level: str = "info",
    sound: bool = True,
    sound_path: Optional[str] = None,
    rate_limit_per_minute: int = 10,
    dedupe_key: Optional[str] = None,
    dedupe_window_seconds: int = 30,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Notify the user via local sound (best-effort).

    Args:
        action: One of:
            - "notify": Play a beep or a local sound file (best-effort)
            - "beep": Play a local beep (best-effort)
            - "play_file": Play a local audio file (best-effort)
        title: Short title for the notification.
        message: Human-readable message body.
        level: "info" | "success" | "warning" | "error"
        sound: For action="notify", whether to play a sound.
        sound_path: For action="play_file", path to a local audio file; for notify, optional (plays this file instead of beep).
        rate_limit_per_minute: Safety limit to avoid spam. Set <=0 to disable.
        dedupe_key: Optional key to suppress repeated notifications in a short window.
        dedupe_window_seconds: Window for dedupe_key suppression.
        extra: Optional extra fields to include in payload.

    Returns:
        dict with:
            - success: bool
            - backend: backend used (for notify)
            - routed_to: "local"/"sns"/"webhook"/"none" (for notify)
            - message_id/status_code (when applicable)
    """
    valid_actions = ("notify", "beep", "play_file")
    if action not in valid_actions:
        return _err(f"Invalid action '{action}'. Must be one of: {list(valid_actions)}")

    if level not in ("info", "success", "warning", "error"):
        return _err("level must be one of: info, success, warning, error")

    if not _rate_limit_ok(rate_limit_per_minute):
        return _err("Rate limited: too many notifications per minute", error_type="RateLimited")
    if not _dedupe_ok(dedupe_key, dedupe_window_seconds):
        return _err("Duplicate suppressed", error_type="Deduped")

    if action == "beep":
        if _is_aws_runtime():
            return _ok(action="beep", routed_to="none", note="Local sound not available in AWS runtime")
        _play_beep()
        return _ok(action="beep", routed_to="local")

    if action == "play_file":
        if not sound_path:
            return _err("'sound_path' is required for action 'play_file'")
        if _is_aws_runtime():
            return _ok(action="play_file", routed_to="none", note="Local sound not available in AWS runtime")
        try:
            _play_file(sound_path)
            return _ok(action="play_file", routed_to="local", sound_path=sound_path)
        except Exception as e:
            return _err(str(e), action="play_file", sound_path=sound_path)

    # action == "notify"
    payload: Dict[str, Any] = {
        "title": title or "Agent notification",
        "message": message or "",
        "level": level,
        "timestamp": int(time.time()),
    }
    if extra:
        payload["extra"] = extra

    if _is_aws_runtime():
        return _ok(action="notify", routed_to="none", note="Local sound not available in AWS runtime", payload=payload)

    if sound:
        try:
            if sound_path:
                _play_file(sound_path)
            else:
                _play_beep()
        except Exception:
            # best-effort; still return success
            pass
    return _ok(action="notify", routed_to="local", payload=payload)


