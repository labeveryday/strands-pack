"""
Google Calendar Tool

Interact with the Google Calendar API (v3) to list calendars and manage events.

Installation:
    pip install "strands-pack[calendar]"

Authentication
--------------
Uses shared Google authentication from google_auth module.
Credentials are auto-detected from:
1. secrets/token.json (or GOOGLE_AUTHORIZED_USER_FILE env var)
2. Service account via GOOGLE_APPLICATION_CREDENTIALS env var

If no valid credentials exist, the tool will prompt you to authenticate.

Supported actions
-----------------
- list_calendars: List all calendars
- list_events: List events (requires calendar_id)
- get_event: Get a specific event (requires calendar_id, event_id)
- create_event: Create an event (requires calendar_id, event dict)
- update_event: Update an event (requires calendar_id, event_id, event dict)
- delete_event: Delete an event (requires calendar_id, event_id)
- quick_add: Quick add event from text (requires calendar_id, text)

Usage (Agent)
-------------
    from strands import Agent
    from strands_pack import google_calendar

    agent = Agent(tools=[google_calendar])
    agent("List my calendars")
    agent("Show my events for this week")
    agent("Create a meeting called Team Sync tomorrow at 3pm")
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from strands import tool

DEFAULT_SCOPES: List[str] = [
    "https://www.googleapis.com/auth/calendar",
]

try:
    from googleapiclient.discovery import build as _google_build

    HAS_GOOGLE_CALENDAR = True
except ImportError:  # pragma: no cover
    _google_build = None
    HAS_GOOGLE_CALENDAR = False


def _get_service(
    service_account_file: Optional[str] = None,
    authorized_user_file: Optional[str] = None,
    delegated_user: Optional[str] = None,
) -> Any:
    """Get Google Calendar service using shared auth."""
    from strands_pack.google_auth import get_credentials

    creds = get_credentials(
        scopes=DEFAULT_SCOPES,
        service_account_file=service_account_file,
        authorized_user_file=authorized_user_file,
        delegated_user=delegated_user,
    )

    if creds is None:
        return None  # Auth needed

    return _google_build("calendar", "v3", credentials=creds, cache_discovery=False)


def _ok(**data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": True}
    out.update(data)
    return out


def _err(message: str, **data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": False, "error": message}
    out.update(data)
    return out


@tool
def google_calendar(
    action: str,
    calendar_id: Optional[str] = None,
    event_id: Optional[str] = None,
    event: Optional[Dict[str, Any]] = None,
    text: Optional[str] = None,
    time_min: Optional[str] = None,
    time_max: Optional[str] = None,
    max_results: int = 25,
    single_events: bool = True,
    order_by: str = "startTime",
    q: Optional[str] = None,
    send_updates: Optional[str] = None,
    patch: bool = True,
) -> Dict[str, Any]:
    """
    Google Calendar API tool for managing calendars and events.

    Args:
        action: The operation to perform. One of:
            - "list_calendars": List all calendars
            - "list_events": List events in a calendar
            - "get_event": Get a specific event
            - "create_event": Create a new event
            - "update_event": Update an existing event
            - "delete_event": Delete an event
            - "quick_add": Quick add event from natural language text
        calendar_id: ID of the calendar (default "primary", required for most actions)
        event_id: ID of the event (required for get_event, update_event, delete_event)
        event: Event data dict (required for create_event, update_event)
        text: Natural language text for quick_add (required for quick_add)
        time_min: Start of time range in RFC3339 format (optional, for list_events)
        time_max: End of time range in RFC3339 format (optional, for list_events)
        max_results: Maximum number of events to return (default 25, for list_events)
        single_events: Whether to expand recurring events (default True, for list_events)
        order_by: Order of events (default "startTime", for list_events)
        q: Free-text search query (optional, for list_events)
        send_updates: Notification setting ("all", "externalOnly", "none") for event operations
        patch: Use patch (partial update) vs full update (default True, for update_event)

    Returns:
        dict with success status and relevant data

    Examples:
        # List all calendars
        google_calendar(action="list_calendars")

        # List events in a calendar
        google_calendar(action="list_events", calendar_id="primary", max_results=10)

        # Get a specific event
        google_calendar(action="get_event", calendar_id="primary", event_id="abc123")

        # Create an event
        google_calendar(
            action="create_event",
            calendar_id="primary",
            event={
                "summary": "Team Sync",
                "start": {"dateTime": "2026-02-03T17:00:00Z"},
                "end": {"dateTime": "2026-02-03T17:30:00Z"},
            }
        )

        # Quick add from text
        google_calendar(action="quick_add", calendar_id="primary", text="Coffee with Sam tomorrow 10am")
    """
    if not HAS_GOOGLE_CALENDAR:
        return _err(
            "Missing Google Calendar dependencies. Install with: pip install strands-pack[calendar]"
        )

    valid_actions = ["list_calendars", "list_events", "get_event", "create_event", "update_event", "delete_event", "quick_add"]
    action = (action or "").strip()
    if action not in valid_actions:
        return _err(f"Unknown action: {action}", available_actions=valid_actions)

    # Get service
    service = _get_service()
    if service is None:
        from strands_pack.google_auth import needs_auth_response
        return needs_auth_response("calendar")

    # Default calendar_id to "primary" for actions that need it
    cal_id = calendar_id or "primary"

    try:
        # list_calendars
        if action == "list_calendars":
            resp = service.calendarList().list().execute()
            items = resp.get("items", []) or []
            return _ok(calendars=items, count=len(items))

        # list_events
        if action == "list_events":
            req: Dict[str, Any] = {
                "calendarId": cal_id,
                "maxResults": int(max_results),
                "singleEvents": bool(single_events),
                "orderBy": order_by,
            }
            if time_min:
                req["timeMin"] = time_min
            if time_max:
                req["timeMax"] = time_max
            if q:
                req["q"] = q

            resp = service.events().list(**req).execute()
            items = resp.get("items", []) or []
            return _ok(events=items, count=len(items), calendar_id=cal_id, query=req)

        # get_event
        if action == "get_event":
            if not event_id:
                return _err("event_id is required for get_event")
            ev = service.events().get(calendarId=cal_id, eventId=event_id).execute()
            return _ok(event=ev, calendar_id=cal_id, event_id=event_id)

        # create_event
        if action == "create_event":
            if not event:
                return _err("event is required for create_event (dict matching the Calendar API Event resource)")
            req = {"calendarId": cal_id, "body": event}
            if send_updates:
                req["sendUpdates"] = send_updates
            created = service.events().insert(**req).execute()
            return _ok(event=created, calendar_id=cal_id)

        # update_event
        if action == "update_event":
            if not event_id:
                return _err("event_id is required for update_event")
            if not event:
                return _err("event is required for update_event (dict matching the Calendar API Event resource)")
            req = {"calendarId": cal_id, "eventId": event_id, "body": event}
            if send_updates:
                req["sendUpdates"] = send_updates
            if patch:
                updated = service.events().patch(**req).execute()
            else:
                updated = service.events().update(**req).execute()
            return _ok(event=updated, calendar_id=cal_id, event_id=event_id, patch=patch)

        # delete_event
        if action == "delete_event":
            if not event_id:
                return _err("event_id is required for delete_event")
            req = {"calendarId": cal_id, "eventId": event_id}
            if send_updates:
                req["sendUpdates"] = send_updates
            service.events().delete(**req).execute()
            return _ok(calendar_id=cal_id, event_id=event_id, deleted=True)

        # quick_add
        if action == "quick_add":
            if not text:
                return _err("text is required for quick_add")
            req = {"calendarId": cal_id, "text": text}
            if send_updates:
                req["sendUpdates"] = send_updates
            created = service.events().quickAdd(**req).execute()
            return _ok(event=created, calendar_id=cal_id)

    except Exception as e:
        return _err(str(e), action=action)

    return _err(f"Unhandled action: {action}")
