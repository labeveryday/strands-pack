"""
YouTube Analytics Tool

Query channel/video analytics metrics via the YouTube Analytics API (v2).

This is separate from the YouTube Data API v3:
  - YouTube Data API: metadata (videos/channels/playlists), search, captions management
  - YouTube Analytics API: performance metrics (views, watch time, etc.)

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

Supported actions
-----------------
- query_report
    Wrapper around `reports.query`.
    Parameters:
      - ids (default "channel==MINE") (example: "channel==UC_x5XG1...")
      - start_date (required): YYYY-MM-DD
      - end_date (required): YYYY-MM-DD
      - metrics (required): str or list[str] (example: ["views","estimatedMinutesWatched"])
      - dimensions (optional): str or list[str] (example: ["day"] or ["video"])
      - filters (optional): str (example: "video==VIDEO_ID")
      - sort (optional): str or list[str] (example: "-views")
      - max_results (optional int)
      - start_index (optional int)
      - currency (optional str)
      - include_historical_channel_data (optional bool)

Usage examples (Agent)
----------------------
    from strands import Agent
    from strands_pack import youtube_analytics

    agent = Agent(tools=[youtube_analytics])

    # Channel views over the last 7 days (grouped by day)
    agent.tool.youtube_analytics(
        action="query_report",
        start_date="2026-01-01",
        end_date="2026-01-07",
        metrics=["views", "estimatedMinutesWatched"],
        dimensions=["day"],
        sort=["day"],
    )
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Union

from strands import tool

DEFAULT_SCOPES: List[str] = [
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]

try:
    from googleapiclient.discovery import build as _google_build

    HAS_YT_ANALYTICS = True
except ImportError:  # pragma: no cover
    _google_build = None
    HAS_YT_ANALYTICS = False


def _csv(value: Union[str, Sequence[str], None]) -> Optional[str]:
    """Convert a string or list of strings to a comma-separated string."""
    if value is None:
        return None
    if isinstance(value, str):
        v = value.strip()
        return v or None
    items = [str(v).strip() for v in value if str(v).strip()]
    return ",".join(items) if items else None


def _get_service(
    service_account_file: Optional[str] = None,
    authorized_user_file: Optional[str] = None,
    delegated_user: Optional[str] = None,
) -> Any:
    """Get YouTube Analytics service using shared auth."""
    from strands_pack.google_auth import get_credentials

    creds = get_credentials(
        scopes=DEFAULT_SCOPES,
        service_account_file=service_account_file,
        authorized_user_file=authorized_user_file,
        delegated_user=delegated_user,
    )

    if creds is None:
        return None  # Auth needed

    return _google_build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)


def _ok(**data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": True}
    out.update(data)
    return out


def _err(message: str, **data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": False, "error": message}
    out.update(data)
    return out


@tool
def youtube_analytics(
    action: str,
    ids: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    metrics: Optional[Union[str, List[str]]] = None,
    dimensions: Optional[Union[str, List[str]]] = None,
    filters: Optional[str] = None,
    sort: Optional[Union[str, List[str]]] = None,
    max_results: Optional[int] = None,
    start_index: Optional[int] = None,
    currency: Optional[str] = None,
    include_historical_channel_data: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    YouTube Analytics API tool for querying channel and video analytics.

    Args:
        action: The operation to perform. One of:
            - "query_report": Query analytics data
        ids: Channel or content owner ID (default "channel==MINE")
        start_date: Start date in YYYY-MM-DD format (required for query_report)
        end_date: End date in YYYY-MM-DD format (required for query_report)
        metrics: Metrics to retrieve, as string or list (required for query_report)
            Examples: "views", ["views", "estimatedMinutesWatched"]
        dimensions: Dimensions to group by, as string or list (optional)
            Examples: "day", ["day", "video"]
        filters: Filter expression (optional)
            Example: "video==VIDEO_ID"
        sort: Sort order, as string or list (optional)
            Examples: "-views", ["day"]
        max_results: Maximum number of results to return (optional)
        start_index: Index of first result to return (optional)
        currency: Currency for revenue metrics (optional)
        include_historical_channel_data: Include data before channel linked (optional)

    Returns:
        dict with success status and relevant data

    Examples:
        # Get channel views for the last 7 days
        youtube_analytics(
            action="query_report",
            start_date="2026-01-01",
            end_date="2026-01-07",
            metrics=["views", "estimatedMinutesWatched"],
            dimensions=["day"],
            sort=["day"],
        )

        # Get top 10 videos by views
        youtube_analytics(
            action="query_report",
            start_date="2026-01-01",
            end_date="2026-01-31",
            metrics="views",
            dimensions="video",
            sort="-views",
            max_results=10,
        )
    """
    if not HAS_YT_ANALYTICS:
        return _err(
            "Missing YouTube Analytics dependencies. Install with: pip install strands-pack[youtube]"
        )

    valid_actions = ["query_report"]
    action = (action or "").strip()
    if action not in valid_actions:
        return _err(f"Unknown action: {action}", available_actions=valid_actions)

    # Get service
    service = _get_service()
    if service is None:
        from strands_pack.google_auth import needs_auth_response
        return needs_auth_response("youtube_analytics")

    try:
        # query_report
        if action == "query_report":
            if not start_date:
                return _err("start_date is required (YYYY-MM-DD)")
            if not end_date:
                return _err("end_date is required (YYYY-MM-DD)")
            metrics_csv = _csv(metrics)
            if not metrics_csv:
                return _err("metrics is required")

            req: Dict[str, Any] = {
                "ids": ids or "channel==MINE",
                "startDate": start_date,
                "endDate": end_date,
                "metrics": metrics_csv,
            }

            # Add optional parameters
            dimensions_csv = _csv(dimensions)
            if dimensions_csv:
                req["dimensions"] = dimensions_csv

            if filters:
                req["filters"] = filters

            sort_csv = _csv(sort)
            if sort_csv:
                req["sort"] = sort_csv

            if max_results is not None:
                req["maxResults"] = max_results

            if start_index is not None:
                req["startIndex"] = start_index

            if currency:
                req["currency"] = currency

            if include_historical_channel_data is not None:
                req["includeHistoricalChannelData"] = include_historical_channel_data

            resp = service.reports().query(**req).execute()
            return _ok(
                request=req,
                response=resp,
                column_headers=resp.get("columnHeaders", []),
                rows=resp.get("rows", []),
            )

    except Exception as e:
        return _err(str(e), action=action)

    return _err(f"Unhandled action: {action}")
