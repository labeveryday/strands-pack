"""
Google Forms Tool

Interact with the Google Forms API (v1) to create/read forms, manage publish settings,
read responses, and manage watches.

Reference:
    https://developers.google.com/workspace/forms/api/reference/rest

Installation:
    pip install "strands-pack[forms]"

Authentication
--------------
Uses shared Google authentication from google_auth module.
Credentials are auto-detected from:
1. secrets/token.json (or GOOGLE_AUTHORIZED_USER_FILE env var)
2. Service account via GOOGLE_APPLICATION_CREDENTIALS env var

If no valid credentials exist, the tool will prompt you to authenticate.

Supported actions
-----------------
Forms:
- create_form: Create a new form (requires form)
- get_form: Get a form (requires form_id)
- batch_update: Batch update a form (requires form_id, requests)
- set_publish_settings: Set publish settings (requires form_id, publish_settings)

Responses:
- get_response: Get a single response (requires form_id, response_id)
- list_responses: List responses (requires form_id)

Watches:
- create_watch: Create a watch (requires form_id, watch)
- delete_watch: Delete a watch (requires form_id, watch_id)
- list_watches: List watches (requires form_id)
- renew_watch: Renew a watch (requires form_id, watch_id)

Usage (Agent)
-------------
    from strands import Agent
    from strands_pack import google_forms

    agent = Agent(tools=[google_forms])
    agent("Create a form titled Customer Feedback")
    agent("List responses for form ID abc123")
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from strands import tool

DEFAULT_SCOPES: List[str] = [
    "https://www.googleapis.com/auth/forms.body",
    "https://www.googleapis.com/auth/forms.responses.readonly",
]

try:
    from googleapiclient.discovery import build as _google_build

    HAS_GOOGLE_FORMS = True
except ImportError:  # pragma: no cover
    _google_build = None
    HAS_GOOGLE_FORMS = False


def _get_forms_service(
    service_account_file: Optional[str] = None,
    authorized_user_file: Optional[str] = None,
    delegated_user: Optional[str] = None,
) -> Any:
    """Get Google Forms service using shared auth."""
    from strands_pack.google_auth import get_credentials

    creds = get_credentials(
        scopes=DEFAULT_SCOPES,
        service_account_file=service_account_file,
        authorized_user_file=authorized_user_file,
        delegated_user=delegated_user,
    )

    if creds is None:
        return None  # Auth needed

    return _google_build("forms", "v1", credentials=creds, cache_discovery=False)


def _ok(**data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": True}
    out.update(data)
    return out


def _err(message: str, **data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": False, "error": message}
    out.update(data)
    return out


@tool
def google_forms(
    action: str,
    form_id: Optional[str] = None,
    form: Optional[Dict[str, Any]] = None,
    requests: Optional[List[Dict[str, Any]]] = None,
    response_id: Optional[str] = None,
    watch: Optional[Dict[str, Any]] = None,
    watch_id: Optional[str] = None,
    page_size: int = 100,
    page_token: Optional[str] = None,
    include_form_in_response: bool = False,
    publish_settings: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Google Forms API tool for managing forms, responses, and watches.

    Args:
        action: The operation to perform. One of:
            - "create_form": Create a new form
            - "get_form": Get a form by ID
            - "batch_update": Batch update a form
            - "set_publish_settings": Set publish settings for a form
            - "get_response": Get a single form response
            - "list_responses": List form responses
            - "create_watch": Create a watch on a form
            - "delete_watch": Delete a watch
            - "list_watches": List watches for a form
            - "renew_watch": Renew a watch
        form_id: ID of the form (required for most actions except create_form)
        form: Form resource dict for create_form (required for create_form)
        requests: List of batch update requests (required for batch_update)
        response_id: ID of the response (required for get_response)
        watch: Watch resource dict (required for create_watch)
        watch_id: ID of the watch (required for delete_watch, renew_watch)
        page_size: Maximum responses to return (default 100, for list_responses)
        page_token: Pagination token (optional, for list_responses)
        include_form_in_response: Include form in batch_update response (default False)
        publish_settings: Publish settings dict (required for set_publish_settings)

    Returns:
        dict with success status and relevant data

    Examples:
        # Create a form
        google_forms(action="create_form", form={"info": {"title": "Feedback"}})

        # Get a form
        google_forms(action="get_form", form_id="abc123")

        # Batch update a form
        google_forms(action="batch_update", form_id="abc123", requests=[...])

        # List responses
        google_forms(action="list_responses", form_id="abc123", page_size=50)

        # Get a single response
        google_forms(action="get_response", form_id="abc123", response_id="resp1")
    """
    if not HAS_GOOGLE_FORMS:
        return _err(
            "Missing Google Forms dependencies. Install with: pip install strands-pack[forms]"
        )

    valid_actions = [
        "create_form",
        "get_form",
        "batch_update",
        "set_publish_settings",
        "get_response",
        "list_responses",
        "create_watch",
        "delete_watch",
        "list_watches",
        "renew_watch",
    ]
    action = (action or "").strip()
    if action not in valid_actions:
        return _err(f"Unknown action: {action}", available_actions=valid_actions)

    # Get service
    service = _get_forms_service()
    if service is None:
        from strands_pack.google_auth import needs_auth_response

        return needs_auth_response("forms")

    try:
        # create_form
        if action == "create_form":
            if not form:
                return _err("form is required for create_form")
            resp = service.forms().create(body=form).execute()
            return _ok(form=resp)

        # get_form
        if action == "get_form":
            if not form_id:
                return _err("form_id is required for get_form")
            resp = service.forms().get(formId=form_id).execute()
            return _ok(form_id=form_id, form=resp)

        # batch_update
        if action == "batch_update":
            if not form_id:
                return _err("form_id is required for batch_update")
            if not requests:
                return _err("requests is required for batch_update")
            body = {"requests": requests, "includeFormInResponse": include_form_in_response}
            resp = service.forms().batchUpdate(formId=form_id, body=body).execute()
            return _ok(form_id=form_id, response=resp)

        # set_publish_settings
        if action == "set_publish_settings":
            if not form_id:
                return _err("form_id is required for set_publish_settings")
            if not publish_settings:
                return _err("publish_settings is required for set_publish_settings")
            resp = service.forms().setPublishSettings(formId=form_id, body=publish_settings).execute()
            return _ok(form_id=form_id, response=resp)

        # get_response
        if action == "get_response":
            if not form_id:
                return _err("form_id is required for get_response")
            if not response_id:
                return _err("response_id is required for get_response")
            resp = service.forms().responses().get(formId=form_id, responseId=response_id).execute()
            return _ok(form_id=form_id, response_id=response_id, response=resp)

        # list_responses
        if action == "list_responses":
            if not form_id:
                return _err("form_id is required for list_responses")
            req_kwargs: Dict[str, Any] = {"formId": form_id, "pageSize": int(page_size)}
            if page_token:
                req_kwargs["pageToken"] = page_token
            resp = service.forms().responses().list(**req_kwargs).execute()
            return _ok(
                form_id=form_id,
                responses=resp.get("responses", []),
                next_page_token=resp.get("nextPageToken"),
            )

        # create_watch
        if action == "create_watch":
            if not form_id:
                return _err("form_id is required for create_watch")
            if not watch:
                return _err("watch is required for create_watch")
            resp = service.forms().watches().create(formId=form_id, body=watch).execute()
            return _ok(form_id=form_id, watch=resp)

        # delete_watch
        if action == "delete_watch":
            if not form_id:
                return _err("form_id is required for delete_watch")
            if not watch_id:
                return _err("watch_id is required for delete_watch")
            service.forms().watches().delete(formId=form_id, watchId=watch_id).execute()
            return _ok(form_id=form_id, watch_id=watch_id)

        # list_watches
        if action == "list_watches":
            if not form_id:
                return _err("form_id is required for list_watches")
            resp = service.forms().watches().list(formId=form_id).execute()
            return _ok(
                form_id=form_id,
                watches=resp.get("watches", []),
                next_page_token=resp.get("nextPageToken"),
            )

        # renew_watch
        if action == "renew_watch":
            if not form_id:
                return _err("form_id is required for renew_watch")
            if not watch_id:
                return _err("watch_id is required for renew_watch")
            resp = service.forms().watches().renew(formId=form_id, watchId=watch_id, body={}).execute()
            return _ok(form_id=form_id, watch_id=watch_id, watch=resp)

    except Exception as e:
        return _err(str(e), action=action)

    return _err(f"Unhandled action: {action}")
