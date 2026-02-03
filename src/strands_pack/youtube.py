"""
YouTube Tool

Interact with the YouTube Data API v3 to search and retrieve metadata for public resources
(videos, channels, playlists, etc.). This tool is optimized for agent use and supports
request shaping via `part` and `fields`.

Reference:
    https://developers.google.com/youtube/v3/getting-started

Installation:
    pip install "strands-pack[youtube]"

Authentication
--------------
Uses shared Google authentication from google_auth module.
Credentials are auto-detected from:
1. secrets/token.json (or GOOGLE_AUTHORIZED_USER_FILE env var)
2. Service account via GOOGLE_APPLICATION_CREDENTIALS env var

If no valid credentials exist, the tool will prompt you to authenticate.

For public data access only, you can also use an API key:
- Set YOUTUBE_API_KEY environment variable, or
- Pass api_key parameter directly

Optional defaults (env)
-----------------------
- MY_CHANNEL_ID: Default `channel_id` if omitted
- MY_UPLOADED_VIDEO_PLAYLIST_ID: Default `playlist_id` if omitted (e.g., your "Uploads" playlist)

Notes:
    - Many YouTube operations require OAuth 2.0 authorization; API keys work only for
      public data requests. See the official overview for details and quota guidance.
    - `part` is required for most list/get calls. Use `fields` to reduce response size.

Supported actions
-----------------
- search: Search for videos, channels, or playlists
- get_videos: Get video details by ID(s)
- get_channels: Get channel details by ID(s) or username
- list_playlists: List playlists for a channel
- list_playlist_items: List items in a playlist
- get_comments: List top-level comments (and optionally replies) for a video
- list_captions: List caption tracks for a video (OAuth required)
- download_caption: Download a caption track to disk (OAuth required)

Tool name
---------
This module exposes **youtube_read** as the primary tool name.
For backwards compatibility, `youtube` remains as an alias to `youtube_read`.

Usage examples (Agent)
----------------------
    from strands import Agent
    from strands_pack import youtube_read

    agent = Agent(tools=[youtube_read])

    # Search for videos
    agent("Search YouTube for 'how to build ai agents'")

    # Get video details
    agent("Get details for video dQw4w9WgXcQ")

    # List playlists for a channel
    agent("List playlists for channel UC_x5XG1OV2P6uZZ5FSM9Ttw")
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

from strands import tool

DEFAULT_SCOPES: List[str] = [
    "https://www.googleapis.com/auth/youtube.readonly",
]

try:
    from googleapiclient.discovery import build as _google_build

    HAS_YOUTUBE = True
except ImportError:  # pragma: no cover
    _google_build = None
    HAS_YOUTUBE = False


def _get_service(
    api_key: Optional[str] = None,
    service_account_file: Optional[str] = None,
    authorized_user_file: Optional[str] = None,
    delegated_user: Optional[str] = None,
) -> Any:
    """Get YouTube service using shared auth or API key."""
    # Check for API key first (simplest auth for public data)
    key = api_key or os.environ.get("YOUTUBE_API_KEY")
    if key:
        return _google_build("youtube", "v3", developerKey=key, cache_discovery=False)

    # Use shared Google auth
    from strands_pack.google_auth import get_credentials

    creds = get_credentials(
        scopes=DEFAULT_SCOPES,
        service_account_file=service_account_file,
        authorized_user_file=authorized_user_file,
        delegated_user=delegated_user,
    )

    if creds is None:
        return None  # Auth needed

    return _google_build("youtube", "v3", credentials=creds, cache_discovery=False)


def _get_default_channel_id() -> Optional[str]:
    # Requested defaults
    for k in ("MY_CHANNEL_ID",):
        v = os.environ.get(k)
        if v and v.strip():
            return v.strip()
    # Common alternative names
    for k in ("YOUTUBE_CHANNEL_ID", "YOUTUBE_DEFAULT_CHANNEL_ID"):
        v = os.environ.get(k)
        if v and v.strip():
            return v.strip()
    return None


def _get_default_uploaded_playlist_id() -> Optional[str]:
    # Requested defaults
    for k in ("MY_UPLOADED_VIDEO_PLAYLIST_ID",):
        v = os.environ.get(k)
        if v and v.strip():
            return v.strip()
    # Common alternative names
    for k in ("YOUTUBE_UPLOADED_VIDEO_PLAYLIST_ID", "YOUTUBE_DEFAULT_UPLOADED_PLAYLIST_ID"):
        v = os.environ.get(k)
        if v and v.strip():
            return v.strip()
    return None


def _ok(**data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": True}
    out.update(data)
    return out


def _err(message: str, **data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": False, "error": message}
    out.update(data)
    return out


def _normalize_ids(value: Union[str, Sequence[str], None], name: str) -> str:
    """Normalize ID(s) to comma-separated string."""
    if value is None:
        raise ValueError(f"{name} is required")
    if isinstance(value, str):
        v = value.strip()
        if not v:
            raise ValueError(f"{name} is required")
        return v
    items = [str(v).strip() for v in value if str(v).strip()]
    if not items:
        raise ValueError(f"{name} is required")
    return ",".join(items)


def _search(
    service: Any,
    q: Optional[str],
    part: str,
    search_type: str,
    max_results: int,
    channel_id: Optional[str],
    video_duration: Optional[str],
    video_definition: Optional[str],
    order: Optional[str],
    published_after: Optional[str],
    published_before: Optional[str],
    page_token: Optional[str],
    fields: Optional[str],
) -> Dict[str, Any]:
    if not q:
        return _err("q is required for search")

    req: Dict[str, Any] = {
        "part": part,
        "q": q,
        "maxResults": max_results,
        "type": search_type,
    }

    # Video-only filters (only valid when type=video)
    if search_type != "video" and (video_duration or video_definition):
        return _err("video_duration/video_definition filters are only valid when search_type='video'")
    if video_duration:
        req["videoDuration"] = video_duration
    if video_definition:
        req["videoDefinition"] = video_definition

    if channel_id:
        req["channelId"] = channel_id
    if order:
        req["order"] = order
    if published_after:
        req["publishedAfter"] = published_after
    if published_before:
        req["publishedBefore"] = published_before
    if page_token:
        req["pageToken"] = page_token
    if fields:
        req["fields"] = fields

    resp = service.search().list(**req).execute()
    return _ok(
        response=resp,
        items=resp.get("items", []),
        next_page_token=resp.get("nextPageToken"),
    )


def _get_videos(
    service: Any,
    video_ids: Optional[Union[str, List[str]]],
    part: str,
    fields: Optional[str],
) -> Dict[str, Any]:
    ids = _normalize_ids(video_ids, "video_ids")

    req: Dict[str, Any] = {"part": part, "id": ids}
    if fields:
        req["fields"] = fields

    resp = service.videos().list(**req).execute()
    return _ok(response=resp, items=resp.get("items", []))


def _get_channels(
    service: Any,
    channel_ids: Optional[Union[str, List[str]]],
    for_username: Optional[str],
    mine: bool,
    part: str,
    fields: Optional[str],
) -> Dict[str, Any]:
    req: Dict[str, Any] = {"part": part}

    if mine:
        req["mine"] = True
    elif for_username:
        req["forUsername"] = for_username
    elif channel_ids:
        req["id"] = _normalize_ids(channel_ids, "channel_ids")
    else:
        return _err("Provide one of: channel_ids, for_username, or mine=True")

    if fields:
        req["fields"] = fields

    resp = service.channels().list(**req).execute()
    return _ok(response=resp, items=resp.get("items", []))


def _list_playlists(
    service: Any,
    channel_id: Optional[str],
    mine: bool,
    part: str,
    max_results: int,
    page_token: Optional[str],
    fields: Optional[str],
) -> Dict[str, Any]:
    if not mine and not channel_id:
        return _err("Provide one of: channel_id or mine=True")

    req: Dict[str, Any] = {"part": part, "maxResults": max_results}
    if mine:
        req["mine"] = True
    if channel_id:
        req["channelId"] = channel_id
    if page_token:
        req["pageToken"] = page_token
    if fields:
        req["fields"] = fields

    resp = service.playlists().list(**req).execute()
    return _ok(
        response=resp,
        items=resp.get("items", []),
        next_page_token=resp.get("nextPageToken"),
    )


def _list_playlist_items(
    service: Any,
    playlist_id: Optional[str],
    part: str,
    max_results: int,
    page_token: Optional[str],
    fields: Optional[str],
) -> Dict[str, Any]:
    if not playlist_id:
        return _err("playlist_id is required")

    req: Dict[str, Any] = {
        "part": part,
        "playlistId": playlist_id,
        "maxResults": max_results,
    }
    if page_token:
        req["pageToken"] = page_token
    if fields:
        req["fields"] = fields

    resp = service.playlistItems().list(**req).execute()
    return _ok(
        response=resp,
        items=resp.get("items", []),
        next_page_token=resp.get("nextPageToken"),
    )


def _get_comments(
    service: Any,
    video_id: Optional[str],
    part: str,
    max_results: int,
    page_token: Optional[str],
    order: Optional[str],
    text_format: str,
    include_replies: bool,
    fields: Optional[str],
) -> Dict[str, Any]:
    """
    Get comments for a video via commentThreads.list.

    Notes:
      - This returns "threads" (top-level comments) and optionally a preview of replies
        when include_replies=True and part includes "replies".
    """
    if not video_id:
        return _err("video_id is required")

    use_part = part or ("snippet,replies" if include_replies else "snippet")
    req: Dict[str, Any] = {
        "part": use_part,
        "videoId": video_id,
        "maxResults": max_results,
        "textFormat": text_format,
    }
    if page_token:
        req["pageToken"] = page_token
    if order:
        req["order"] = order
    if fields:
        req["fields"] = fields

    resp = service.commentThreads().list(**req).execute()
    return _ok(
        response=resp,
        items=resp.get("items", []),
        next_page_token=resp.get("nextPageToken"),
    )


def _list_captions(
    service: Any,
    video_id: Optional[str],
    part: str,
    fields: Optional[str],
) -> Dict[str, Any]:
    if not video_id:
        return _err("video_id is required")

    req: Dict[str, Any] = {"part": part, "videoId": video_id}
    if fields:
        req["fields"] = fields

    resp = service.captions().list(**req).execute()
    return _ok(response=resp, items=resp.get("items", []))


def _download_caption(
    service: Any,
    caption_id: Optional[str],
    output_path: Optional[str],
    tfmt: str,
) -> Dict[str, Any]:
    if not caption_id:
        return _err("caption_id is required")
    if not output_path:
        return _err("output_path is required")

    # Note: The YouTube Data API only allows caption download if the authenticated user
    # has access to that caption track. For most videos you don't own, this will fail.
    data = service.captions().download(id=caption_id, tfmt=tfmt).execute()

    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(data, bytes):
        p.write_bytes(data)
    else:
        # Best-effort for clients that return str
        p.write_text(str(data), encoding="utf-8")

    return _ok(caption_id=caption_id, output_path=str(p.absolute()), format=tfmt)


@tool
def youtube_read(
    action: str,
    # Search parameters
    q: Optional[str] = None,
    search_type: str = "video",
    video_duration: Optional[str] = None,
    video_definition: Optional[str] = None,
    order: Optional[str] = None,
    published_after: Optional[str] = None,
    published_before: Optional[str] = None,
    # Video parameters
    video_ids: Optional[Union[str, List[str]]] = None,
    video_id: Optional[str] = None,
    # Channel parameters
    channel_ids: Optional[Union[str, List[str]]] = None,
    channel_id: Optional[str] = None,
    for_username: Optional[str] = None,
    mine: bool = False,
    # Playlist parameters
    playlist_id: Optional[str] = None,
    # Caption parameters
    caption_id: Optional[str] = None,
    output_path: Optional[str] = None,
    tfmt: str = "srt",
    # Comment parameters
    include_replies: bool = False,
    text_format: str = "plainText",
    # Common parameters
    part: Optional[str] = None,
    fields: Optional[str] = None,
    max_results: int = 10,
    page_token: Optional[str] = None,
    # Auth parameters (optional - uses shared auth by default)
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    YouTube Data API v3 READ tool for searching and retrieving video metadata.

    Args:
        action: The operation to perform. One of:
            - "search": Search for videos, channels, or playlists
            - "get_videos": Get video details by ID(s)
            - "get_channels": Get channel details
            - "list_playlists": List playlists for a channel
            - "list_playlist_items": List items in a playlist
            - "get_comments": List comments for a video
            - "list_captions": List caption tracks for a video (OAuth required)
            - "download_caption": Download a caption track (OAuth required)
        q: Search query text (required for search)
        search_type: Type of search results - "video", "channel", or "playlist" (default "video")
        video_duration: Video duration filter (search_type="video" only): "any", "short", "medium", "long"
        video_definition: Video definition filter (search_type="video" only): "any", "standard", "high"
        order: Sort order - "date", "rating", "relevance", "title", "videoCount", "viewCount"
        published_after: Filter by publish date (RFC3339 format)
        published_before: Filter by publish date (RFC3339 format)
        video_ids: Video ID(s) for get_videos (string or list)
        video_id: Video ID for list_captions
        channel_ids: Channel ID(s) for get_channels (string or list)
        channel_id: Channel ID for search or list_playlists
        for_username: Username for get_channels
        mine: Use authenticated user's data (requires OAuth)
        playlist_id: Playlist ID for list_playlist_items
        include_replies: Include replies when listing comments (get_comments)
        text_format: Comment text format: "plainText" or "html" (get_comments)
        caption_id: Caption track ID for download_caption
        output_path: File path for download_caption output
        tfmt: Caption format - "srt" or "vtt" (default "srt")
        part: API response parts (default varies by action)
        fields: Field mask to reduce response size
        max_results: Maximum results to return (default 10)
        page_token: Token for pagination
        api_key: YouTube API key (optional, uses shared auth if not provided)

    Returns:
        dict with success status and relevant data

    Examples:
        # Search for videos
        youtube(action="search", q="how to build ai agents", max_results=5)

        # Get video details
        youtube(action="get_videos", video_ids=["dQw4w9WgXcQ"])

        # Get channel details
        youtube(action="get_channels", channel_ids=["UC_x5XG1OV2P6uZZ5FSM9Ttw"])

        # List playlists for a channel
        youtube(action="list_playlists", channel_id="UC_x5XG1OV2P6uZZ5FSM9Ttw")

        # List items in a playlist
        youtube(action="list_playlist_items", playlist_id="PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf")
    """
    if not HAS_YOUTUBE:
        return _err(
            "Missing YouTube dependencies. Install with: pip install strands-pack[youtube]"
        )

    valid_actions = [
        "search",
        "get_videos",
        "get_channels",
        "list_playlists",
        "list_playlist_items",
        "get_comments",
        "list_captions",
        "download_caption",
    ]
    action = (action or "").strip()
    if action not in valid_actions:
        return _err(f"Unknown action: {action}", available_actions=valid_actions)

    # Get service
    service = _get_service(api_key=api_key)
    if service is None:
        from strands_pack.google_auth import needs_auth_response

        # Auth preset name remains "youtube" (shared across youtube_read/youtube_write).
        return needs_auth_response("youtube")

    try:
        # Apply env defaults (only when caller didn't provide an explicit value)
        if channel_id is None:
            channel_id = _get_default_channel_id()
        if playlist_id is None:
            playlist_id = _get_default_uploaded_playlist_id()

        # search
        if action == "search":
            return _search(
                service=service,
                q=q,
                part=part or "snippet",
                search_type=search_type,
                max_results=max_results,
                channel_id=channel_id,
                video_duration=video_duration,
                video_definition=video_definition,
                order=order,
                published_after=published_after,
                published_before=published_before,
                page_token=page_token,
                fields=fields,
            )

        # get_videos
        if action == "get_videos":
            return _get_videos(
                service=service,
                video_ids=video_ids,
                part=part or "snippet,contentDetails,statistics",
                fields=fields,
            )

        # get_channels
        if action == "get_channels":
            return _get_channels(
                service=service,
                channel_ids=channel_ids,
                for_username=for_username,
                mine=mine,
                part=part or "snippet,contentDetails,statistics",
                fields=fields,
            )

        # list_playlists
        if action == "list_playlists":
            return _list_playlists(
                service=service,
                channel_id=channel_id,
                mine=mine,
                part=part or "snippet,contentDetails",
                max_results=max_results,
                page_token=page_token,
                fields=fields,
            )

        # list_playlist_items
        if action == "list_playlist_items":
            return _list_playlist_items(
                service=service,
                playlist_id=playlist_id,
                part=part or "snippet,contentDetails",
                max_results=max_results,
                page_token=page_token,
                fields=fields,
            )

        # get_comments
        if action == "get_comments":
            return _get_comments(
                service=service,
                video_id=video_id,
                part=part or "",
                max_results=max_results,
                page_token=page_token,
                order=order,
                text_format=text_format,
                include_replies=bool(include_replies),
                fields=fields,
            )

        # list_captions
        if action == "list_captions":
            return _list_captions(
                service=service,
                video_id=video_id,
                part=part or "snippet",
                fields=fields,
            )

        # download_caption
        if action == "download_caption":
            return _download_caption(
                service=service,
                caption_id=caption_id,
                output_path=output_path,
                tfmt=tfmt,
            )

    except Exception as e:
        return _err(str(e), action=action)

    return _err(f"Unhandled action: {action}")


# Backwards-compatible alias (keep old import path working)
youtube = youtube_read
