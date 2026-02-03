"""
Calendly Tool

Manage Calendly scheduling and events.

Requires:
    pip install strands-pack[calendly]

Authentication:
    Set CALENDLY_TOKEN environment variable with your Personal Access Token.

Supported actions
-----------------
- get_current_user
    Parameters: none
- list_event_types
    Parameters: active (optional), count (optional, default 20)
- get_event_type
    Parameters: event_type_uuid (required)
- list_scheduled_events
    Parameters: status (optional: "active", "canceled"), min_start_time (optional),
                max_start_time (optional), count (optional, default 20)
- get_scheduled_event
    Parameters: event_uuid (required)
- list_event_invitees
    Parameters: event_uuid (required), status (optional), count (optional, default 20)
- cancel_event
    Parameters: event_uuid (required), reason (optional)
- create_webhook
    Parameters: url (required), events (required - list), scope (required: "user" or "organization")
- list_webhooks
    Parameters: scope (optional: "user" or "organization"), count (optional, default 20)
- delete_webhook
    Parameters: webhook_uuid (required)

- create_event_type
    Create a new one-on-one event type (best-effort; API availability depends on Calendly plan/account).
    Parameters: name (required), duration (required, minutes), description (optional), slug (optional),
                active (optional), event_type_payload (optional dict)

- update_event_type
    Update an event type (best-effort; may require specific plan/account).
    Parameters: event_type_uuid (required), name (optional), duration (optional), description (optional),
                slug (optional), active (optional), event_type_payload (optional dict)

- create_scheduling_link
    Create a single-use scheduling link for an event type.
    Parameters: event_type_uuid (required unless event_type_uri provided), event_type_uri (optional),
                max_event_count (optional, default 1)

- get_available_times
    Get available time slots for an event type.
    Parameters: event_type_uuid (required unless event_type_uri provided), event_type_uri (optional),
                start_time (required), end_time (required), timezone (optional), count (optional, default 20)

- get_busy_times
    Get busy times for the current user.
    Parameters: start_time (required), end_time (required)

Notes:
  - All times should be in ISO 8601 format
  - UUIDs are the last part of Calendly URIs (e.g., from https://api.calendly.com/users/UUID)
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from strands import tool

# Lazy import for requests
_requests = None


def _get_requests():
    global _requests
    if _requests is None:
        try:
            import requests
            _requests = requests
        except ImportError:
            raise ImportError("requests not installed. Run: pip install strands-pack[calendly]") from None
    return _requests


def _get_token():
    token = os.environ.get("CALENDLY_TOKEN")
    if not token:
        raise ValueError("CALENDLY_TOKEN environment variable is not set")
    return token


def _get_headers():
    return {
        "Authorization": f"Bearer {_get_token()}",
        "Content-Type": "application/json",
    }


BASE_URL = "https://api.calendly.com"


def _ok(**data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": True}
    out.update(data)
    return out


def _err(message: str, *, error_type: Optional[str] = None, **data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": False, "error": message}
    if error_type:
        out["error_type"] = error_type
    out.update(data)
    return out


def _extract_uuid(uri: str) -> str:
    """Extract UUID from a Calendly URI."""
    if uri:
        return uri.rstrip("/").split("/")[-1]
    return ""

def _event_type_uri(event_type_uuid: str) -> str:
    return f"{BASE_URL}/event_types/{event_type_uuid}"


def _get_current_user(**kwargs) -> Dict[str, Any]:
    """Get current authenticated user."""
    requests = _get_requests()

    response = requests.get(f"{BASE_URL}/users/me", headers=_get_headers(), timeout=30)
    response.raise_for_status()

    data = response.json()
    user = data.get("resource", {})

    return _ok(
        action="get_current_user",
        user={
            "uri": user.get("uri"),
            "uuid": _extract_uuid(user.get("uri", "")),
            "name": user.get("name"),
            "email": user.get("email"),
            "slug": user.get("slug"),
            "scheduling_url": user.get("scheduling_url"),
            "timezone": user.get("timezone"),
            "current_organization": user.get("current_organization"),
        },
    )

def _create_event_type(
    name: Optional[str] = None,
    duration: Optional[int] = None,
    description: Optional[str] = None,
    slug: Optional[str] = None,
    active: Optional[bool] = None,
    event_type_payload: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Create an event type (one-on-one).

    Notes:
      - Calendly API support for creating event types may depend on account/plan.
      - This implementation is best-effort and allows `event_type_payload` for forward-compat.
    """
    if not name:
        return _err("name is required")
    if duration is None:
        return _err("duration is required (minutes)")

    requests = _get_requests()

    user_response = _get_current_user()
    if not user_response.get("success"):
        return user_response
    user_uri = user_response["user"]["uri"]

    payload: Dict[str, Any] = {
        "name": str(name),
        "duration": int(duration),
        # Many accounts use kind=solo for one-on-one event types.
        "kind": "solo",
        "owner": user_uri,
    }
    if description is not None:
        payload["description_plain"] = str(description)
    if slug is not None:
        payload["slug"] = str(slug)
    if active is not None:
        payload["active"] = bool(active)
    if isinstance(event_type_payload, dict):
        payload.update(event_type_payload)

    response = requests.post(f"{BASE_URL}/event_types", headers=_get_headers(), json=payload, timeout=30)
    response.raise_for_status()
    data = response.json()
    et = data.get("resource", {}) if isinstance(data, dict) else {}
    return _ok(
        action="create_event_type",
        event_type={
            "uri": et.get("uri"),
            "uuid": _extract_uuid(et.get("uri", "")),
            "name": et.get("name"),
            "active": et.get("active"),
            "slug": et.get("slug"),
            "scheduling_url": et.get("scheduling_url"),
            "duration": et.get("duration"),
            "kind": et.get("kind"),
            "description_plain": et.get("description_plain"),
        },
        raw=data,
    )


def _update_event_type(
    event_type_uuid: Optional[str] = None,
    name: Optional[str] = None,
    duration: Optional[int] = None,
    description: Optional[str] = None,
    slug: Optional[str] = None,
    active: Optional[bool] = None,
    event_type_payload: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Update an event type (best-effort; plan/account dependent)."""
    if not event_type_uuid:
        return _err("event_type_uuid is required")

    if (
        name is None
        and duration is None
        and description is None
        and slug is None
        and active is None
        and not isinstance(event_type_payload, dict)
    ):
        return _err("Provide at least one field to update (name/duration/description/slug/active/event_type_payload)")

    requests = _get_requests()

    payload: Dict[str, Any] = {}
    if name is not None:
        payload["name"] = str(name)
    if duration is not None:
        payload["duration"] = int(duration)
    if description is not None:
        payload["description_plain"] = str(description)
    if slug is not None:
        payload["slug"] = str(slug)
    if active is not None:
        payload["active"] = bool(active)
    if isinstance(event_type_payload, dict):
        payload.update(event_type_payload)

    response = requests.patch(f"{BASE_URL}/event_types/{event_type_uuid}", headers=_get_headers(), json=payload, timeout=30)
    response.raise_for_status()
    data = response.json()
    et = data.get("resource", {}) if isinstance(data, dict) else {}
    return _ok(
        action="update_event_type",
        event_type_uuid=event_type_uuid,
        event_type={
            "uri": et.get("uri"),
            "uuid": _extract_uuid(et.get("uri", "")),
            "name": et.get("name"),
            "active": et.get("active"),
            "slug": et.get("slug"),
            "scheduling_url": et.get("scheduling_url"),
            "duration": et.get("duration"),
            "kind": et.get("kind"),
            "description_plain": et.get("description_plain"),
        },
        raw=data,
    )


def _create_scheduling_link(
    event_type_uuid: Optional[str] = None,
    event_type_uri: Optional[str] = None,
    max_event_count: int = 1,
    **kwargs,
) -> Dict[str, Any]:
    """Create a (typically) single-use scheduling link for an event type."""
    if not event_type_uri:
        if not event_type_uuid:
            return _err("Provide event_type_uuid or event_type_uri")
        event_type_uri = _event_type_uri(event_type_uuid)

    requests = _get_requests()
    payload = {
        "max_event_count": int(max_event_count or 1),
        "owner": event_type_uri,
        "owner_type": "EventType",
    }
    response = requests.post(f"{BASE_URL}/scheduling_links", headers=_get_headers(), json=payload, timeout=30)
    response.raise_for_status()
    data = response.json()
    res = data.get("resource", {}) if isinstance(data, dict) else {}
    return _ok(
        action="create_scheduling_link",
        scheduling_link={
            "booking_url": res.get("booking_url"),
            "owner": res.get("owner"),
            "max_event_count": res.get("max_event_count"),
        },
        raw=data,
    )


def _get_available_times(
    event_type_uuid: Optional[str] = None,
    event_type_uri: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    timezone: Optional[str] = None,
    count: int = 20,
    **kwargs,
) -> Dict[str, Any]:
    """Get available time slots for an event type (best-effort; endpoint may vary by account/API version)."""
    if not event_type_uri:
        if not event_type_uuid:
            return _err("Provide event_type_uuid or event_type_uri")
        event_type_uri = _event_type_uri(event_type_uuid)
    if not start_time:
        return _err("start_time is required (ISO 8601)")
    if not end_time:
        return _err("end_time is required (ISO 8601)")

    requests = _get_requests()
    params: Dict[str, Any] = {
        "event_type": event_type_uri,
        "start_time": start_time,
        "end_time": end_time,
        "count": min(int(count or 20), 100),
    }
    if timezone:
        params["timezone"] = timezone

    response = requests.get(f"{BASE_URL}/event_type_available_times", headers=_get_headers(), params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    return _ok(
        action="get_available_times",
        event_type=event_type_uri,
        start_time=start_time,
        end_time=end_time,
        timezone=timezone,
        slots=data.get("collection", []) if isinstance(data, dict) else [],
        raw=data,
    )


def _get_busy_times(
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Get busy times for the current user (best-effort)."""
    if not start_time:
        return _err("start_time is required (ISO 8601)")
    if not end_time:
        return _err("end_time is required (ISO 8601)")

    requests = _get_requests()
    user_response = _get_current_user()
    if not user_response.get("success"):
        return user_response
    user_uri = user_response["user"]["uri"]

    params = {"user": user_uri, "start_time": start_time, "end_time": end_time}
    response = requests.get(f"{BASE_URL}/user_busy_times", headers=_get_headers(), params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    return _ok(
        action="get_busy_times",
        user=user_uri,
        start_time=start_time,
        end_time=end_time,
        busy_times=data.get("collection", []) if isinstance(data, dict) else [],
        raw=data,
    )


def _list_event_types(active: Optional[bool] = None, count: int = 20, **kwargs) -> Dict[str, Any]:
    """List event types for the current user."""
    requests = _get_requests()

    # First get current user to get their URI
    user_response = _get_current_user()
    if not user_response.get("success"):
        return user_response

    user_uri = user_response["user"]["uri"]

    params: Dict[str, Any] = {
        "user": user_uri,
        "count": min(count, 100),
    }
    if active is not None:
        params["active"] = str(active).lower()

    response = requests.get(f"{BASE_URL}/event_types", headers=_get_headers(), params=params, timeout=30)
    response.raise_for_status()

    data = response.json()
    event_types = []
    for et in data.get("collection", []):
        event_types.append({
            "uri": et.get("uri"),
            "uuid": _extract_uuid(et.get("uri", "")),
            "name": et.get("name"),
            "active": et.get("active"),
            "slug": et.get("slug"),
            "scheduling_url": et.get("scheduling_url"),
            "duration": et.get("duration"),
            "kind": et.get("kind"),
            "description_plain": et.get("description_plain"),
        })

    return _ok(
        action="list_event_types",
        event_types=event_types,
        count=len(event_types),
    )


def _get_event_type(event_type_uuid: str, **kwargs) -> Dict[str, Any]:
    """Get a specific event type."""
    if not event_type_uuid:
        return _err("event_type_uuid is required")

    requests = _get_requests()

    response = requests.get(f"{BASE_URL}/event_types/{event_type_uuid}", headers=_get_headers(), timeout=30)
    response.raise_for_status()

    data = response.json()
    et = data.get("resource", {})

    return _ok(
        action="get_event_type",
        event_type={
            "uri": et.get("uri"),
            "uuid": _extract_uuid(et.get("uri", "")),
            "name": et.get("name"),
            "active": et.get("active"),
            "slug": et.get("slug"),
            "scheduling_url": et.get("scheduling_url"),
            "duration": et.get("duration"),
            "kind": et.get("kind"),
            "description_plain": et.get("description_plain"),
            "description_html": et.get("description_html"),
            "color": et.get("color"),
        },
    )


def _list_scheduled_events(status: Optional[str] = None, min_start_time: Optional[str] = None,
                           max_start_time: Optional[str] = None, count: int = 20,
                           **kwargs) -> Dict[str, Any]:
    """List scheduled events."""
    requests = _get_requests()

    # First get current user to get their URI
    user_response = _get_current_user()
    if not user_response.get("success"):
        return user_response

    user_uri = user_response["user"]["uri"]

    params: Dict[str, Any] = {
        "user": user_uri,
        "count": min(count, 100),
    }
    if status:
        params["status"] = status
    if min_start_time:
        params["min_start_time"] = min_start_time
    if max_start_time:
        params["max_start_time"] = max_start_time

    response = requests.get(f"{BASE_URL}/scheduled_events", headers=_get_headers(), params=params, timeout=30)
    response.raise_for_status()

    data = response.json()
    events = []
    for event in data.get("collection", []):
        events.append({
            "uri": event.get("uri"),
            "uuid": _extract_uuid(event.get("uri", "")),
            "name": event.get("name"),
            "status": event.get("status"),
            "start_time": event.get("start_time"),
            "end_time": event.get("end_time"),
            "event_type": event.get("event_type"),
            "location": event.get("location"),
            "created_at": event.get("created_at"),
            "updated_at": event.get("updated_at"),
            "cancellation": event.get("cancellation"),
        })

    return _ok(
        action="list_scheduled_events",
        events=events,
        count=len(events),
    )


def _get_scheduled_event(event_uuid: str, **kwargs) -> Dict[str, Any]:
    """Get a specific scheduled event."""
    if not event_uuid:
        return _err("event_uuid is required")

    requests = _get_requests()

    response = requests.get(f"{BASE_URL}/scheduled_events/{event_uuid}", headers=_get_headers(), timeout=30)
    response.raise_for_status()

    data = response.json()
    event = data.get("resource", {})

    return _ok(
        action="get_scheduled_event",
        event={
            "uri": event.get("uri"),
            "uuid": _extract_uuid(event.get("uri", "")),
            "name": event.get("name"),
            "status": event.get("status"),
            "start_time": event.get("start_time"),
            "end_time": event.get("end_time"),
            "event_type": event.get("event_type"),
            "location": event.get("location"),
            "invitees_counter": event.get("invitees_counter"),
            "created_at": event.get("created_at"),
            "updated_at": event.get("updated_at"),
            "cancellation": event.get("cancellation"),
            "event_memberships": event.get("event_memberships"),
            "event_guests": event.get("event_guests"),
        },
    )


def _list_event_invitees(event_uuid: str, status: Optional[str] = None,
                         count: int = 20, **kwargs) -> Dict[str, Any]:
    """List invitees for a scheduled event."""
    if not event_uuid:
        return _err("event_uuid is required")

    requests = _get_requests()

    params: Dict[str, Any] = {"count": min(count, 100)}
    if status:
        params["status"] = status

    response = requests.get(
        f"{BASE_URL}/scheduled_events/{event_uuid}/invitees",
        headers=_get_headers(),
        params=params,
        timeout=30
    )
    response.raise_for_status()

    data = response.json()
    invitees = []
    for inv in data.get("collection", []):
        invitees.append({
            "uri": inv.get("uri"),
            "uuid": _extract_uuid(inv.get("uri", "")),
            "name": inv.get("name"),
            "email": inv.get("email"),
            "status": inv.get("status"),
            "timezone": inv.get("timezone"),
            "created_at": inv.get("created_at"),
            "updated_at": inv.get("updated_at"),
            "questions_and_answers": inv.get("questions_and_answers"),
            "cancellation": inv.get("cancellation"),
        })

    return _ok(
        action="list_event_invitees",
        event_uuid=event_uuid,
        invitees=invitees,
        count=len(invitees),
    )


def _cancel_event(event_uuid: str, reason: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """Cancel a scheduled event."""
    if not event_uuid:
        return _err("event_uuid is required")

    requests = _get_requests()

    body: Dict[str, Any] = {}
    if reason:
        body["reason"] = reason

    response = requests.post(
        f"{BASE_URL}/scheduled_events/{event_uuid}/cancellation",
        headers=_get_headers(),
        json=body,
        timeout=30
    )
    response.raise_for_status()

    data = response.json()
    cancellation = data.get("resource", {})

    return _ok(
        action="cancel_event",
        event_uuid=event_uuid,
        cancellation={
            "canceled_by": cancellation.get("canceled_by"),
            "reason": cancellation.get("reason"),
            "canceler_type": cancellation.get("canceler_type"),
        },
    )


def _create_webhook(url: str, events: List[str], scope: str, **kwargs) -> Dict[str, Any]:
    """Create a webhook subscription."""
    if not url:
        return _err("url is required")
    if not events:
        return _err("events is required (list of event types)")
    if not scope:
        return _err("scope is required ('user' or 'organization')")

    if scope not in ("user", "organization"):
        return _err("scope must be 'user' or 'organization'")

    requests = _get_requests()

    # Get current user
    user_response = _get_current_user()
    if not user_response.get("success"):
        return user_response

    user_uri = user_response["user"]["uri"]
    org_uri = user_response["user"].get("current_organization")

    body = {
        "url": url,
        "events": events,
        "scope": scope,
    }

    if scope == "user":
        body["user"] = user_uri
    else:
        if not org_uri:
            return _err("Organization not found for current user")
        body["organization"] = org_uri

    response = requests.post(f"{BASE_URL}/webhook_subscriptions", headers=_get_headers(), json=body, timeout=30)
    response.raise_for_status()

    data = response.json()
    webhook = data.get("resource", {})

    return _ok(
        action="create_webhook",
        webhook={
            "uri": webhook.get("uri"),
            "uuid": _extract_uuid(webhook.get("uri", "")),
            "callback_url": webhook.get("callback_url"),
            "events": webhook.get("events"),
            "scope": webhook.get("scope"),
            "state": webhook.get("state"),
            "created_at": webhook.get("created_at"),
        },
    )


def _list_webhooks(scope: Optional[str] = None, count: int = 20, **kwargs) -> Dict[str, Any]:
    """List webhook subscriptions."""
    requests = _get_requests()

    # Get current user
    user_response = _get_current_user()
    if not user_response.get("success"):
        return user_response

    user_uri = user_response["user"]["uri"]
    org_uri = user_response["user"].get("current_organization")

    params: Dict[str, Any] = {"count": min(count, 100)}

    if scope == "user":
        params["user"] = user_uri
        params["scope"] = "user"
    elif scope == "organization":
        if org_uri:
            params["organization"] = org_uri
            params["scope"] = "organization"
        else:
            return _err("Organization not found for current user")
    else:
        # Default to user scope
        params["user"] = user_uri
        params["scope"] = "user"

    response = requests.get(f"{BASE_URL}/webhook_subscriptions", headers=_get_headers(), params=params, timeout=30)
    response.raise_for_status()

    data = response.json()
    webhooks = []
    for wh in data.get("collection", []):
        webhooks.append({
            "uri": wh.get("uri"),
            "uuid": _extract_uuid(wh.get("uri", "")),
            "callback_url": wh.get("callback_url"),
            "events": wh.get("events"),
            "scope": wh.get("scope"),
            "state": wh.get("state"),
            "created_at": wh.get("created_at"),
        })

    return _ok(
        action="list_webhooks",
        webhooks=webhooks,
        count=len(webhooks),
    )


def _delete_webhook(webhook_uuid: str, **kwargs) -> Dict[str, Any]:
    """Delete a webhook subscription."""
    if not webhook_uuid:
        return _err("webhook_uuid is required")

    requests = _get_requests()

    response = requests.delete(f"{BASE_URL}/webhook_subscriptions/{webhook_uuid}", headers=_get_headers(), timeout=30)
    response.raise_for_status()

    return _ok(
        action="delete_webhook",
        webhook_uuid=webhook_uuid,
        deleted=True,
    )


def _list_availability_schedules(event_type_uuid: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """List availability schedules for an event type."""
    if not event_type_uuid:
        return _err("event_type_uuid is required")

    requests = _get_requests()

    response = requests.get(
        f"{BASE_URL}/event_type_available_times",
        headers=_get_headers(),
        params={"event_type": f"{BASE_URL}/event_types/{event_type_uuid}"},
        timeout=30
    )

    # Try the availability schedules endpoint
    response = requests.get(
        f"{BASE_URL}/event_types/{event_type_uuid}/availability_schedules",
        headers=_get_headers(),
        timeout=30
    )
    response.raise_for_status()

    data = response.json()
    schedules = data.get("collection", [])

    return _ok(
        action="list_availability_schedules",
        event_type_uuid=event_type_uuid,
        schedules=schedules,
        count=len(schedules),
    )


def _get_user_availability_schedule(schedule_uuid: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """Get a user's availability schedule."""
    if not schedule_uuid:
        # Get current user's default schedule
        user_response = _get_current_user()
        if not user_response.get("success"):
            return user_response

        user_uuid = user_response["user"]["uuid"]
        requests = _get_requests()

        # List user's availability schedules
        response = requests.get(
            f"{BASE_URL}/user_availability_schedules",
            headers=_get_headers(),
            params={"user": f"{BASE_URL}/users/{user_uuid}"},
            timeout=30
        )
        response.raise_for_status()

        data = response.json()
        schedules = []
        for sched in data.get("collection", []):
            schedules.append({
                "uri": sched.get("uri"),
                "uuid": _extract_uuid(sched.get("uri", "")),
                "name": sched.get("name"),
                "default": sched.get("default"),
                "timezone": sched.get("timezone"),
                "rules": sched.get("rules"),
            })

        return _ok(
            action="get_user_availability_schedule",
            schedules=schedules,
            count=len(schedules),
        )

    requests = _get_requests()
    response = requests.get(
        f"{BASE_URL}/user_availability_schedules/{schedule_uuid}",
        headers=_get_headers(),
        timeout=30
    )
    response.raise_for_status()

    data = response.json()
    sched = data.get("resource", {})

    return _ok(
        action="get_user_availability_schedule",
        schedule={
            "uri": sched.get("uri"),
            "uuid": _extract_uuid(sched.get("uri", "")),
            "name": sched.get("name"),
            "default": sched.get("default"),
            "timezone": sched.get("timezone"),
            "rules": sched.get("rules"),
        },
    )


def _update_availability(
    schedule_uuid: Optional[str] = None,
    name: Optional[str] = None,
    timezone: Optional[str] = None,
    rules: Optional[List[Dict[str, Any]]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Update a user's availability schedule.

    Rules format example:
    [
        {
            "type": "wday",
            "wday": "monday",
            "intervals": [{"from": "09:00", "to": "17:00"}]
        },
        {
            "type": "date",
            "date": "2026-02-10",
            "intervals": [{"from": "10:00", "to": "12:00"}]
        }
    ]

    Note: Updating rules REPLACES all existing rules. Get current rules first,
    modify them, then pass all rules to this action.
    """
    if not schedule_uuid:
        return _err("schedule_uuid is required")

    requests = _get_requests()

    body: Dict[str, Any] = {}
    if name is not None:
        body["name"] = name
    if timezone is not None:
        body["timezone"] = timezone
    if rules is not None:
        body["rules"] = rules

    if not body:
        return _err("At least one of name, timezone, or rules is required")

    response = requests.patch(
        f"{BASE_URL}/user_availability_schedules/{schedule_uuid}",
        headers=_get_headers(),
        json=body,
        timeout=30
    )
    response.raise_for_status()

    data = response.json()
    sched = data.get("resource", {})

    return _ok(
        action="update_availability",
        schedule={
            "uri": sched.get("uri"),
            "uuid": _extract_uuid(sched.get("uri", "")),
            "name": sched.get("name"),
            "default": sched.get("default"),
            "timezone": sched.get("timezone"),
            "rules": sched.get("rules"),
        },
    )


_ACTIONS = {
    "get_current_user": _get_current_user,
    "list_event_types": _list_event_types,
    "get_event_type": _get_event_type,
    "list_scheduled_events": _list_scheduled_events,
    "get_scheduled_event": _get_scheduled_event,
    "list_event_invitees": _list_event_invitees,
    "cancel_event": _cancel_event,
    "create_webhook": _create_webhook,
    "list_webhooks": _list_webhooks,
    "delete_webhook": _delete_webhook,
    "create_event_type": _create_event_type,
    "update_event_type": _update_event_type,
    "create_scheduling_link": _create_scheduling_link,
    "get_available_times": _get_available_times,
    "get_busy_times": _get_busy_times,
    "get_user_availability_schedule": _get_user_availability_schedule,
}


@tool
def calendly(
    action: str,
    event_type_uuid: Optional[str] = None,
    event_uuid: Optional[str] = None,
    webhook_uuid: Optional[str] = None,
    active: Optional[bool] = None,
    status: Optional[str] = None,
    min_start_time: Optional[str] = None,
    max_start_time: Optional[str] = None,
    count: Optional[int] = None,
    url: Optional[str] = None,
    events: Optional[List[str]] = None,
    scope: Optional[str] = None,
    reason: Optional[str] = None,
    # New actions params
    name: Optional[str] = None,
    duration: Optional[int] = None,
    description: Optional[str] = None,
    slug: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    timezone: Optional[str] = None,
    max_event_count: Optional[int] = None,
    event_type_uri: Optional[str] = None,
    event_type_payload: Optional[Dict[str, Any]] = None,
    # Availability schedule params
    schedule_uuid: Optional[str] = None,
    rules: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Manage Calendly scheduling and events.

    Actions:
    - get_current_user: Get current authenticated user info
    - list_event_types: List available event types
    - get_event_type: Get a specific event type
    - list_scheduled_events: List scheduled events
    - get_scheduled_event: Get a specific scheduled event
    - list_event_invitees: List invitees for a scheduled event
    - cancel_event: Cancel a scheduled event
    - create_webhook: Create a webhook subscription
    - list_webhooks: List webhook subscriptions
    - delete_webhook: Delete a webhook subscription
    - create_event_type: Create a new one-on-one event type
    - update_event_type: Update an existing event type
    - create_scheduling_link: Create a single-use booking link for an event type
    - get_available_times: Get available time slots for an event type
    - get_busy_times: Get busy times for the current user
    - get_user_availability_schedule: Get user's availability schedule(s) (read-only, API doesn't support updates)

    Args:
        action: The action to perform
        event_type_uuid: UUID of the event type (for get_event_type)
        event_uuid: UUID of the scheduled event (for get_scheduled_event, list_event_invitees, cancel_event)
        webhook_uuid: UUID of the webhook (for delete_webhook)
        active: Filter event types by active status (for list_event_types)
        status: Filter by status - "active" or "canceled" (for list_scheduled_events, list_event_invitees)
        min_start_time: Minimum start time in ISO 8601 format (for list_scheduled_events)
        max_start_time: Maximum start time in ISO 8601 format (for list_scheduled_events)
        count: Maximum number of results to return, default 20 (for list_event_types, list_scheduled_events, list_event_invitees, list_webhooks)
        url: Callback URL for webhook (for create_webhook)
        events: List of event types to subscribe to (for create_webhook)
        scope: Scope for webhook - "user" or "organization" (for create_webhook, list_webhooks)
        reason: Cancellation reason (for cancel_event)
        name: Name/title (for create_event_type / update_event_type)
        duration: Duration in minutes (for create_event_type / update_event_type)
        description: Description (for create_event_type / update_event_type)
        slug: Slug (for create_event_type / update_event_type)
        start_time: ISO 8601 start time (for get_available_times / get_busy_times)
        end_time: ISO 8601 end time (for get_available_times / get_busy_times)
        timezone: IANA timezone (for get_available_times)
        max_event_count: Max bookings allowed for a scheduling link (for create_scheduling_link, default 1)
        event_type_uri: Full event type URI (optional alternative to event_type_uuid)
        event_type_payload: Optional dict merged into event type create/update payload

    Returns:
        dict with success status and action-specific data

    Authentication:
        Set CALENDLY_TOKEN environment variable with your Personal Access Token.
    """
    action = (action or "").strip().lower()

    if action not in _ACTIONS:
        return _err(
            f"Unknown action: {action}",
            error_type="InvalidAction",
            available_actions=list(_ACTIONS.keys()),
        )

    # Build kwargs from explicit parameters
    kwargs: Dict[str, Any] = {}
    if event_type_uuid is not None:
        kwargs["event_type_uuid"] = event_type_uuid
    if event_uuid is not None:
        kwargs["event_uuid"] = event_uuid
    if webhook_uuid is not None:
        kwargs["webhook_uuid"] = webhook_uuid
    if active is not None:
        kwargs["active"] = active
    if status is not None:
        kwargs["status"] = status
    if min_start_time is not None:
        kwargs["min_start_time"] = min_start_time
    if max_start_time is not None:
        kwargs["max_start_time"] = max_start_time
    if count is not None:
        kwargs["count"] = count
    if url is not None:
        kwargs["url"] = url
    if events is not None:
        kwargs["events"] = events
    if scope is not None:
        kwargs["scope"] = scope
    if reason is not None:
        kwargs["reason"] = reason
    if name is not None:
        kwargs["name"] = name
    if duration is not None:
        kwargs["duration"] = duration
    if description is not None:
        kwargs["description"] = description
    if slug is not None:
        kwargs["slug"] = slug
    if start_time is not None:
        kwargs["start_time"] = start_time
    if end_time is not None:
        kwargs["end_time"] = end_time
    if timezone is not None:
        kwargs["timezone"] = timezone
    if max_event_count is not None:
        kwargs["max_event_count"] = max_event_count
    if event_type_uri is not None:
        kwargs["event_type_uri"] = event_type_uri
    if event_type_payload is not None:
        kwargs["event_type_payload"] = event_type_payload
    if schedule_uuid is not None:
        kwargs["schedule_uuid"] = schedule_uuid
    if rules is not None:
        kwargs["rules"] = rules

    try:
        return _ACTIONS[action](**kwargs)
    except ImportError as e:
        return _err(str(e), error_type="ImportError")
    except ValueError as e:
        return _err(str(e), error_type="ValueError")
    except Exception as e:
        error_message = str(e)
        # Handle HTTP errors
        if hasattr(e, "response"):
            try:
                error_data = e.response.json()
                error_message = error_data.get("message", str(e))
            except Exception:
                pass
        return _err(error_message, error_type=type(e).__name__, action=action)
