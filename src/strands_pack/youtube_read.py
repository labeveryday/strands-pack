"""
YouTube Read Tool

Interact with the YouTube Data API v3 to search and retrieve metadata for public resources
(videos, channels, playlists, comments). This tool uses API key authentication only.

Reference:
    https://developers.google.com/youtube/v3/getting-started

Installation:
    pip install "strands-pack[youtube]"

Authentication
--------------
Requires a YouTube API key:
    - Set YOUTUBE_API_KEY environment variable, or
    - Pass api_key parameter directly

Get an API key from Google Cloud Console → APIs & Services → Credentials.

Optional defaults (env)
-----------------------
- YOUTUBE_CHANNEL_ID: Default channel_id (so you can omit it in prompts)
- YOUTUBE_UPLOADS_PLAYLIST_ID: Default playlist_id for uploads

Supported actions
-----------------
- search: Search for videos, channels, or playlists
- get_videos: Get video details by ID(s)
- get_channels: Get channel details by ID(s) or username
- list_playlists: List playlists for a channel
- list_playlist_items: List items in a playlist
- get_comments: List top-level comments for a video

Note: For caption/transcript access, use youtube_transcript (public) or youtube_write (OAuth).

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
from typing import Any, Dict, List, Optional, Sequence, Union

from strands import tool

try:
    from googleapiclient.discovery import build as _google_build

    HAS_YOUTUBE = True
except ImportError:  # pragma: no cover
    _google_build = None
    HAS_YOUTUBE = False


def _get_service(api_key: Optional[str] = None) -> Any:
    """Get YouTube service using API key."""
    key = api_key or os.environ.get("YOUTUBE_API_KEY")
    if not key or not str(key).strip():
        return None
    return _google_build("youtube", "v3", developerKey=key, cache_discovery=False)


def _get_default_channel_id() -> Optional[str]:
    for k in ("YOUTUBE_CHANNEL_ID", "YOUTUBE_DEFAULT_CHANNEL_ID", "MY_CHANNEL_ID"):
        v = os.environ.get(k)
        if v and v.strip():
            return v.strip()
    return None


def _get_default_uploaded_playlist_id() -> Optional[str]:
    for k in (
        "YOUTUBE_UPLOADS_PLAYLIST_ID",
        "YOUTUBE_UPLOADED_VIDEO_PLAYLIST_ID",
        "YOUTUBE_DEFAULT_UPLOADED_PLAYLIST_ID",
        "MY_UPLOADED_VIDEO_PLAYLIST_ID",
    ):
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
    part: str,
    fields: Optional[str],
) -> Dict[str, Any]:
    req: Dict[str, Any] = {"part": part}

    if for_username:
        req["forUsername"] = for_username
    elif channel_ids:
        req["id"] = _normalize_ids(channel_ids, "channel_ids")
    else:
        return _err("Provide one of: channel_ids or for_username")

    if fields:
        req["fields"] = fields

    resp = service.channels().list(**req).execute()
    return _ok(response=resp, items=resp.get("items", []))


def _list_playlists(
    service: Any,
    channel_id: Optional[str],
    part: str,
    max_results: int,
    page_token: Optional[str],
    fields: Optional[str],
) -> Dict[str, Any]:
    if not channel_id:
        return _err("channel_id is required")

    req: Dict[str, Any] = {"part": part, "maxResults": max_results, "channelId": channel_id}
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
    # Playlist parameters
    playlist_id: Optional[str] = None,
    # Comment parameters
    include_replies: bool = False,
    text_format: str = "plainText",
    # Common parameters
    part: Optional[str] = None,
    fields: Optional[str] = None,
    max_results: int = 10,
    page_token: Optional[str] = None,
    # Auth
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    YouTube Data API v3 READ tool for searching and retrieving public video metadata.

    Requires YOUTUBE_API_KEY environment variable or api_key parameter.

    Environment defaults (so you can omit IDs in prompts):
        YOUTUBE_CHANNEL_ID: Used by get_channels, list_playlists, and search
        YOUTUBE_UPLOADS_PLAYLIST_ID: Used by list_playlist_items

    Args:
        action: The operation to perform. One of:
            - "search": Search for videos, channels, or playlists
            - "get_videos": Get video details by ID(s)
            - "get_channels": Get channel details (uses YOUTUBE_CHANNEL_ID if no ID provided)
            - "list_playlists": List playlists for a channel
            - "list_playlist_items": List items in a playlist
            - "get_comments": List comments for a video
        q: Search query text (required for search)
        search_type: Type of search - "video", "channel", or "playlist" (default "video")
        video_duration: Duration filter (search_type="video" only): "any", "short", "medium", "long"
        video_definition: Definition filter (search_type="video" only): "any", "standard", "high"
        order: Sort order - "date", "rating", "relevance", "title", "videoCount", "viewCount"
        published_after: Filter by publish date (RFC3339 format)
        published_before: Filter by publish date (RFC3339 format)
        video_ids: Video ID(s) for get_videos
        video_id: Video ID for get_comments
        channel_ids: Channel ID(s) for get_channels (defaults to YOUTUBE_CHANNEL_ID)
        channel_id: Channel ID for search or list_playlists (defaults to YOUTUBE_CHANNEL_ID)
        for_username: Username for get_channels
        playlist_id: Playlist ID for list_playlist_items (defaults to YOUTUBE_UPLOADS_PLAYLIST_ID)
        include_replies: Include replies when listing comments
        text_format: Comment format: "plainText" or "html"
        part: API response parts (default varies by action)
        fields: Field mask to reduce response size
        max_results: Maximum results (default 10)
        page_token: Token for pagination
        api_key: YouTube API key (or set YOUTUBE_API_KEY env var)

    Returns:
        dict with success status and relevant data

    Examples:
        youtube_read(action="search", q="python tutorial", max_results=5)
        youtube_read(action="get_videos", video_ids="dQw4w9WgXcQ")
        youtube_read(action="get_channels")  # Uses YOUTUBE_CHANNEL_ID env var
        youtube_read(action="get_channels", channel_ids="UC_x5XG1OV2P6uZZ5FSM9Ttw")
        youtube_read(action="list_playlists", channel_id="UC_x5XG1OV2P6uZZ5FSM9Ttw")
    """
    if not HAS_YOUTUBE:
        return _err("Missing dependencies. Install with: pip install strands-pack[youtube]")

    valid_actions = [
        "search",
        "get_videos",
        "get_channels",
        "list_playlists",
        "list_playlist_items",
        "get_comments",
    ]
    action = (action or "").strip()
    if action not in valid_actions:
        return _err(f"Unknown action: {action}", available_actions=valid_actions)

    service = _get_service(api_key=api_key)
    if service is None:
        return _err(
            "YOUTUBE_API_KEY is required. Set the environment variable or pass api_key parameter.",
            hint="Get an API key from Google Cloud Console → APIs & Services → Credentials",
        )

    try:
        # Apply env defaults
        if channel_id is None:
            channel_id = _get_default_channel_id()
        if playlist_id is None:
            playlist_id = _get_default_uploaded_playlist_id()

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

        if action == "get_videos":
            return _get_videos(
                service=service,
                video_ids=video_ids,
                part=part or "snippet,contentDetails,statistics",
                fields=fields,
            )

        if action == "get_channels":
            # Use default channel_id if no selector provided
            use_channel_ids = channel_ids
            if not channel_ids and not for_username and channel_id:
                use_channel_ids = channel_id
            return _get_channels(
                service=service,
                channel_ids=use_channel_ids,
                for_username=for_username,
                part=part or "snippet,contentDetails,statistics",
                fields=fields,
            )

        if action == "list_playlists":
            return _list_playlists(
                service=service,
                channel_id=channel_id,
                part=part or "snippet,contentDetails",
                max_results=max_results,
                page_token=page_token,
                fields=fields,
            )

        if action == "list_playlist_items":
            return _list_playlist_items(
                service=service,
                playlist_id=playlist_id,
                part=part or "snippet,contentDetails",
                max_results=max_results,
                page_token=page_token,
                fields=fields,
            )

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

    except Exception as e:
        return _err(str(e), action=action)

    return _err(f"Unhandled action: {action}")


# Backwards-compatible alias
youtube = youtube_read
