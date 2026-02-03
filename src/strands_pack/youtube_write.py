"""
YouTube Write Tool

Update YouTube video metadata (title/description/tags) and manage playlist membership.

This tool is intentionally **OAuth-only** (no API key), because write operations require
user authorization.

Authentication
--------------
Uses shared Google authentication from google_auth module.
Credentials are auto-detected from:
1. secrets/token.json (or GOOGLE_AUTHORIZED_USER_FILE env var)
2. Service account via GOOGLE_APPLICATION_CREDENTIALS env var (note: YouTube write access
   is typically done via authorized-user OAuth rather than service accounts)

Recommended OAuth scopes (write)
--------------------------------
- https://www.googleapis.com/auth/youtube.force-ssl

Optional defaults (env)
-----------------------
- YOUTUBE_UPLOADS_PLAYLIST_ID: Default `playlist_id` if omitted (recommended)
- Legacy aliases (still supported): MY_UPLOADED_VIDEO_PLAYLIST_ID

Supported actions
-----------------
- update_video_metadata
    Update a video’s title, description, and/or tags (safe: preserves unspecified fields).

- add_video_to_playlist
    Add a video to a playlist.

- remove_video_from_playlist
    Remove a video from a playlist (by playlistItemId, or by playlist_id + video_id lookup).

- create_playlist
    Create a playlist (title/description/privacy).

- update_playlist
    Update playlist metadata (title/description/privacy).

- delete_playlist
    Delete a playlist (**requires confirm_text**).

- delete_video
    Delete a video (**requires confirm_text**).

- delete_video_if_private
    Delete a video only if its privacyStatus == private (**requires confirm_text**).

- set_thumbnail
    Upload a custom thumbnail image for a video.

- set_video_privacy
    Set a video privacy status: public/unlisted/private (**requires confirm_text**).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from strands import tool

WRITE_SCOPES: List[str] = [
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

try:
    from googleapiclient.discovery import build as _google_build
    from googleapiclient.http import MediaFileUpload

    HAS_YOUTUBE = True
except ImportError:  # pragma: no cover
    _google_build = None
    MediaFileUpload = None
    HAS_YOUTUBE = False


def _ok(**data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": True}
    out.update(data)
    return out


def _err(message: str, **data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": False, "error": message}
    out.update(data)
    return out


def _get_default_uploaded_playlist_id() -> Optional[str]:
    for k in (
        "YOUTUBE_UPLOADS_PLAYLIST_ID",
        "YOUTUBE_UPLOADED_VIDEO_PLAYLIST_ID",
        "YOUTUBE_DEFAULT_UPLOADED_PLAYLIST_ID",
        "YOUTUBE_DEFAULT_UPLOADS_PLAYLIST_ID",
        "MY_UPLOADED_VIDEO_PLAYLIST_ID",
    ):
        v = os.environ.get(k)
        if v and v.strip():
            return v.strip()
    return None


def _get_write_service(
    service_account_file: Optional[str] = None,
    authorized_user_file: Optional[str] = None,
    delegated_user: Optional[str] = None,
) -> Any:
    from strands_pack.google_auth import get_credentials

    creds = get_credentials(
        scopes=WRITE_SCOPES,
        service_account_file=service_account_file,
        authorized_user_file=authorized_user_file,
        delegated_user=delegated_user,
    )
    if creds is None:
        return None
    return _google_build("youtube", "v3", credentials=creds, cache_discovery=False)


def _require_confirm_text(*, action: str, confirm_text: Optional[str], expected: str) -> Optional[Dict[str, Any]]:
    if confirm_text != expected:
        return _err(
            f"Destructive action requires confirm_text='{expected}'",
            action=action,
            expected_confirm_text=expected,
        )
    return None


def _set_video_privacy(service: Any, video_id: str, privacy_status: str) -> Dict[str, Any]:
    allowed = {"public", "unlisted", "private"}
    ps = (privacy_status or "").strip().lower()
    if ps not in allowed:
        return _err("privacy_status must be one of: public, unlisted, private", privacy_status=privacy_status)

    existing = service.videos().list(part="status", id=video_id).execute()
    items = existing.get("items", []) if isinstance(existing, dict) else []
    if not items:
        return _err("Video not found or not accessible", video_id=video_id)

    status = (items[0] or {}).get("status") or {}
    status["privacyStatus"] = ps
    body = {"id": video_id, "status": status}
    resp = service.videos().update(part="status", body=body).execute()
    return _ok(video_id=video_id, privacy_status=ps, response=resp)


def _delete_video(service: Any, video_id: str) -> Dict[str, Any]:
    service.videos().delete(id=video_id).execute()
    return _ok(video_id=video_id, deleted=True)


def _delete_video_if_private(service: Any, video_id: str) -> Dict[str, Any]:
    existing = service.videos().list(part="status", id=video_id).execute()
    items = existing.get("items", []) if isinstance(existing, dict) else []
    if not items:
        return _err("Video not found or not accessible", video_id=video_id)

    status = (items[0] or {}).get("status") or {}
    ps = (status.get("privacyStatus") or "").strip().lower()
    if ps != "private":
        return _err("Refusing to delete: video is not private", video_id=video_id, privacy_status=ps)
    return _delete_video(service, video_id)


def _create_playlist(
    service: Any,
    title: str,
    description: Optional[str],
    privacy_status: str,
) -> Dict[str, Any]:
    ps = (privacy_status or "").strip().lower()
    if ps not in {"public", "unlisted", "private"}:
        return _err("privacy_status must be one of: public, unlisted, private", privacy_status=privacy_status)
    body = {
        "snippet": {"title": title, "description": description or ""},
        "status": {"privacyStatus": ps},
    }
    resp = service.playlists().insert(part="snippet,status", body=body).execute()
    playlist_id = resp.get("id") if isinstance(resp, dict) else None
    return _ok(playlist_id=playlist_id, response=resp)


def _update_playlist(
    service: Any,
    playlist_id: str,
    title: Optional[str],
    description: Optional[str],
    privacy_status: Optional[str],
) -> Dict[str, Any]:
    # Fetch existing to preserve unspecified fields
    existing = service.playlists().list(part="snippet,status", id=playlist_id).execute()
    items = existing.get("items", []) if isinstance(existing, dict) else []
    if not items:
        return _err("Playlist not found or not accessible", playlist_id=playlist_id)

    snippet = (items[0] or {}).get("snippet") or {}
    status = (items[0] or {}).get("status") or {}
    if title is not None:
        snippet["title"] = title
    if description is not None:
        snippet["description"] = description
    if privacy_status is not None:
        ps = (privacy_status or "").strip().lower()
        if ps not in {"public", "unlisted", "private"}:
            return _err("privacy_status must be one of: public, unlisted, private", privacy_status=privacy_status)
        status["privacyStatus"] = ps

    body = {"id": playlist_id, "snippet": snippet, "status": status}
    resp = service.playlists().update(part="snippet,status", body=body).execute()
    return _ok(playlist_id=playlist_id, response=resp)


def _delete_playlist(service: Any, playlist_id: str) -> Dict[str, Any]:
    service.playlists().delete(id=playlist_id).execute()
    return _ok(playlist_id=playlist_id, deleted=True)


def _set_thumbnail(service: Any, video_id: str, thumbnail_path: str) -> Dict[str, Any]:
    if MediaFileUpload is None:
        return _err("Missing googleapiclient.http.MediaFileUpload (install google-api-python-client)")
    p = Path(thumbnail_path)
    if not p.exists():
        return _err("thumbnail_path does not exist", thumbnail_path=thumbnail_path)
    media = MediaFileUpload(str(p), mimetype="image/*", resumable=False)
    resp = service.thumbnails().set(videoId=video_id, media_body=media).execute()
    return _ok(video_id=video_id, thumbnail_path=str(p), response=resp)

def _update_video_metadata(
    service: Any,
    video_id: str,
    title: Optional[str],
    description: Optional[str],
    tags: Optional[List[str]],
    category_id: Optional[str],
) -> Dict[str, Any]:
    # Read existing snippet to avoid overwriting fields the caller didn't specify.
    existing = service.videos().list(part="snippet", id=video_id).execute()
    items = existing.get("items", []) if isinstance(existing, dict) else []
    if not items:
        return _err("Video not found or not accessible", video_id=video_id)

    snippet = (items[0] or {}).get("snippet") or {}
    if title is not None:
        snippet["title"] = title
    if description is not None:
        snippet["description"] = description
    if tags is not None:
        snippet["tags"] = [str(t) for t in tags]
    if category_id is not None:
        snippet["categoryId"] = str(category_id)

    body = {"id": video_id, "snippet": snippet}
    resp = service.videos().update(part="snippet", body=body).execute()
    return _ok(video_id=video_id, response=resp)


def _add_video_to_playlist(
    service: Any,
    playlist_id: str,
    video_id: str,
    position: Optional[int],
) -> Dict[str, Any]:
    snippet: Dict[str, Any] = {
        "playlistId": playlist_id,
        "resourceId": {"kind": "youtube#video", "videoId": video_id},
    }
    if position is not None:
        snippet["position"] = int(position)
    body = {"snippet": snippet}
    resp = service.playlistItems().insert(part="snippet", body=body).execute()
    playlist_item_id = resp.get("id") if isinstance(resp, dict) else None
    return _ok(playlist_id=playlist_id, video_id=video_id, playlist_item_id=playlist_item_id, response=resp)


def _remove_video_from_playlist(
    service: Any,
    *,
    playlist_item_id: Optional[str],
    playlist_id: Optional[str],
    video_id: Optional[str],
    max_to_scan: int,
) -> Dict[str, Any]:
    if playlist_item_id:
        service.playlistItems().delete(id=playlist_item_id).execute()
        return _ok(playlist_item_id=playlist_item_id, removed=True)

    if not playlist_id or not video_id:
        return _err("Provide playlist_item_id OR (playlist_id AND video_id)")

    # Find playlistItemId by scanning playlist items. Cap scanning for safety.
    scanned = 0
    page_token = None
    found_id = None
    while scanned < max_to_scan:
        resp = service.playlistItems().list(
            part="snippet",
            playlistId=playlist_id,
            maxResults=min(50, max_to_scan - scanned),
            pageToken=page_token,
        ).execute()
        items = resp.get("items", []) if isinstance(resp, dict) else []
        scanned += len(items)
        for it in items:
            sn = (it or {}).get("snippet") or {}
            rid = sn.get("resourceId") or {}
            if rid.get("videoId") == video_id:
                found_id = it.get("id")
                break
        if found_id:
            break
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    if not found_id:
        return _err("Video not found in playlist (or scan cap reached)", playlist_id=playlist_id, video_id=video_id, scanned=scanned)

    service.playlistItems().delete(id=found_id).execute()
    return _ok(playlist_id=playlist_id, video_id=video_id, playlist_item_id=found_id, removed=True, scanned=scanned)


@tool
def youtube_write(
    action: str,
    # Common identifiers
    video_id: Optional[str] = None,
    playlist_id: Optional[str] = None,
    playlist_item_id: Optional[str] = None,
    # Metadata updates
    title: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    category_id: Optional[str] = None,
    privacy_status: Optional[str] = None,
    thumbnail_path: Optional[str] = None,
    # Playlist operations
    position: Optional[int] = None,
    max_to_scan: int = 200,
    # Safety
    confirm_text: Optional[str] = None,
    # Auth parameters (optional - uses shared auth by default)
    service_account_file: Optional[str] = None,
    authorized_user_file: Optional[str] = None,
    delegated_user: Optional[str] = None,
) -> Dict[str, Any]:
    """
    YouTube Data API v3 WRITE tool for updating video metadata and managing playlists.

    Args:
        action: One of:
            - "update_video_metadata"
            - "add_video_to_playlist"
            - "remove_video_from_playlist"
            - "create_playlist"
            - "update_playlist"
            - "delete_playlist"
            - "delete_video"
            - "delete_video_if_private"
            - "set_thumbnail"
            - "set_video_privacy"
        video_id: Target YouTube video ID.
        playlist_id: Target playlist ID (optional for remove if playlist_item_id is provided).
            If omitted for playlist actions, defaults to YOUTUBE_UPLOADS_PLAYLIST_ID (or legacy MY_UPLOADED_VIDEO_PLAYLIST_ID) when available.
        playlist_item_id: PlaylistItem ID to remove directly (preferred).
        title: New title (update_video_metadata).
        description: New description (update_video_metadata).
        tags: New tags (update_video_metadata).
        category_id: New categoryId (update_video_metadata).
        position: Optional playlist position (add_video_to_playlist).
        max_to_scan: Safety cap for scanning playlist items when removing by (playlist_id + video_id).
        confirm_text: Required confirmation string for destructive actions (delete/unlist/private).
        service_account_file / authorized_user_file / delegated_user: Optional auth overrides.

    Returns:
        dict with success status and relevant data.
    """
    if not HAS_YOUTUBE:
        return _err("Missing YouTube dependencies. Install with: pip install strands-pack[youtube]")

    action = (action or "").strip()
    valid_actions = [
        "update_video_metadata",
        "add_video_to_playlist",
        "remove_video_from_playlist",
        "create_playlist",
        "update_playlist",
        "delete_playlist",
        "delete_video",
        "delete_video_if_private",
        "set_thumbnail",
        "set_video_privacy",
    ]
    if action not in valid_actions:
        return _err(f"Unknown action: {action}", available_actions=valid_actions)

    if playlist_id is None:
        playlist_id = _get_default_uploaded_playlist_id()

    service = _get_write_service(
        service_account_file=service_account_file,
        authorized_user_file=authorized_user_file,
        delegated_user=delegated_user,
    )
    if service is None:
        from strands_pack.google_auth import needs_auth_response

        # Use a dedicated preset so we request the correct write scopes.
        return needs_auth_response("youtube_write")

    try:
        if action == "update_video_metadata":
            if not video_id:
                return _err("video_id is required")
            if title is None and description is None and tags is None and category_id is None:
                return _err("Provide at least one of: title, description, tags, category_id")
            return _update_video_metadata(
                service=service,
                video_id=video_id,
                title=title,
                description=description,
                tags=tags,
                category_id=category_id,
            )

        if action == "add_video_to_playlist":
            if not video_id:
                return _err("video_id is required")
            if not playlist_id:
                return _err("playlist_id is required (or set YOUTUBE_UPLOADS_PLAYLIST_ID)")
            return _add_video_to_playlist(service=service, playlist_id=playlist_id, video_id=video_id, position=position)

        if action == "remove_video_from_playlist":
            if playlist_item_id is None and not video_id:
                return _err("video_id is required when playlist_item_id is not provided")
            if playlist_item_id is None and not playlist_id:
                return _err("playlist_id is required when playlist_item_id is not provided (or set YOUTUBE_UPLOADS_PLAYLIST_ID)")
            return _remove_video_from_playlist(
                service=service,
                playlist_item_id=playlist_item_id,
                playlist_id=playlist_id,
                video_id=video_id,
                max_to_scan=int(max_to_scan or 200),
            )

        if action == "create_playlist":
            if not title:
                return _err("title is required")
            return _create_playlist(service=service, title=title, description=description, privacy_status=privacy_status or "private")

        if action == "update_playlist":
            if not playlist_id:
                return _err("playlist_id is required")
            if title is None and description is None and privacy_status is None:
                return _err("Provide at least one of: title, description, privacy_status")
            return _update_playlist(
                service=service,
                playlist_id=playlist_id,
                title=title,
                description=description,
                privacy_status=privacy_status,
            )

        if action == "delete_playlist":
            if not playlist_id:
                return _err("playlist_id is required")
            expected = f"DELETE_PLAYLIST {playlist_id}"
            if err := _require_confirm_text(action=action, confirm_text=confirm_text, expected=expected):
                return err
            return _delete_playlist(service=service, playlist_id=playlist_id)

        if action == "delete_video":
            if not video_id:
                return _err("video_id is required")
            expected = f"DELETE_VIDEO {video_id}"
            if err := _require_confirm_text(action=action, confirm_text=confirm_text, expected=expected):
                return err
            return _delete_video(service=service, video_id=video_id)

        if action == "delete_video_if_private":
            if not video_id:
                return _err("video_id is required")
            expected = f"DELETE_PRIVATE_VIDEO {video_id}"
            if err := _require_confirm_text(action=action, confirm_text=confirm_text, expected=expected):
                return err
            return _delete_video_if_private(service=service, video_id=video_id)

        if action == "set_thumbnail":
            if not video_id:
                return _err("video_id is required")
            if not thumbnail_path:
                return _err("thumbnail_path is required")
            return _set_thumbnail(service=service, video_id=video_id, thumbnail_path=thumbnail_path)

        if action == "set_video_privacy":
            if not video_id:
                return _err("video_id is required")
            if not privacy_status:
                return _err("privacy_status is required")
            expected = f"SET_PRIVACY {video_id} {(privacy_status or '').strip().lower()}"
            if err := _require_confirm_text(action=action, confirm_text=confirm_text, expected=expected):
                return err
            return _set_video_privacy(service=service, video_id=video_id, privacy_status=privacy_status)

    except Exception as e:
        return _err(str(e), action=action)

    return _err(f"Unhandled action: {action}")


