"""
Google Tasks Tool

Interact with the Google Tasks API (v1) to manage task lists and tasks.

Installation:
    pip install "strands-pack[tasks]"

Authentication
--------------
Uses shared Google authentication from google_auth module.
Credentials are auto-detected from:
1. secrets/token.json (or GOOGLE_AUTHORIZED_USER_FILE env var)
2. Service account via GOOGLE_APPLICATION_CREDENTIALS env var

If no valid credentials exist, the tool will prompt you to authenticate.

Supported actions
-----------------
- list_tasklists: List all task lists
- list_tasks: List tasks in a task list (requires tasklist_id)
- create_task: Create a task (requires tasklist_id, title)
- complete_task: Mark a task completed (requires tasklist_id, task_id)

Usage (Agent)
-------------
    from strands import Agent
    from strands_pack import google_tasks

    agent = Agent(tools=[google_tasks])
    agent("List my task lists")
    agent("List tasks in my default task list")
    agent("Create a task called Review PR")
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from strands import tool

DEFAULT_SCOPES: List[str] = [
    "https://www.googleapis.com/auth/tasks",
]

try:
    from googleapiclient.discovery import build as _google_build

    HAS_GOOGLE_TASKS = True
except ImportError:  # pragma: no cover
    _google_build = None
    HAS_GOOGLE_TASKS = False


def _get_service(
    service_account_file: Optional[str] = None,
    authorized_user_file: Optional[str] = None,
    delegated_user: Optional[str] = None,
) -> Any:
    """Get Google Tasks service using shared auth."""
    from strands_pack.google_auth import get_credentials

    creds = get_credentials(
        scopes=DEFAULT_SCOPES,
        service_account_file=service_account_file,
        authorized_user_file=authorized_user_file,
        delegated_user=delegated_user,
    )

    if creds is None:
        return None  # Auth needed

    return _google_build("tasks", "v1", credentials=creds, cache_discovery=False)


def _ok(**data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": True}
    out.update(data)
    return out


def _err(message: str, **data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": False, "error": message}
    out.update(data)
    return out


@tool
def google_tasks(
    action: str,
    tasklist_id: Optional[str] = None,
    task_id: Optional[str] = None,
    title: Optional[str] = None,
    notes: Optional[str] = None,
    due: Optional[str] = None,
    status: Optional[str] = None,
    max_results: int = 50,
    show_completed: bool = True,
) -> Dict[str, Any]:
    """
    Google Tasks API tool for managing task lists and tasks.

    Args:
        action: The operation to perform. One of:
            - "list_tasklists": List all task lists
            - "list_tasks": List tasks in a task list
            - "create_task": Create a new task
            - "complete_task": Mark a task as completed
        tasklist_id: ID of the task list (required for list_tasks, create_task, complete_task)
        task_id: ID of the task (required for complete_task)
        title: Title of the task (required for create_task)
        notes: Notes/description for the task (optional, for create_task)
        due: Due date in RFC3339 format (optional, for create_task)
        status: Task status (optional, for create_task)
        max_results: Maximum number of tasks to return (default 50, for list_tasks)
        show_completed: Whether to show completed tasks (default True, for list_tasks)

    Returns:
        dict with success status and relevant data

    Examples:
        # List all task lists
        google_tasks(action="list_tasklists")

        # List tasks in a task list
        google_tasks(action="list_tasks", tasklist_id="MDg5MzE...")

        # Create a task
        google_tasks(action="create_task", tasklist_id="MDg5MzE...", title="Review PR")

        # Complete a task
        google_tasks(action="complete_task", tasklist_id="MDg5MzE...", task_id="Y3ZaM...")
    """
    if not HAS_GOOGLE_TASKS:
        return _err(
            "Missing Google Tasks dependencies. Install with: pip install strands-pack[tasks]"
        )

    valid_actions = ["list_tasklists", "list_tasks", "create_task", "complete_task"]
    action = (action or "").strip()
    if action not in valid_actions:
        return _err(f"Unknown action: {action}", available_actions=valid_actions)

    # Get service
    service = _get_service()
    if service is None:
        from strands_pack.google_auth import needs_auth_response
        return needs_auth_response("tasks")

    try:
        # list_tasklists
        if action == "list_tasklists":
            resp = service.tasklists().list().execute()
            items = resp.get("items", []) or []
            return _ok(tasklists=items, count=len(items))

        # list_tasks
        if action == "list_tasks":
            if not tasklist_id:
                return _err("tasklist_id is required for list_tasks")
            resp = service.tasks().list(
                tasklist=tasklist_id,
                maxResults=int(max_results),
                showCompleted=bool(show_completed),
            ).execute()
            items = resp.get("items", []) or []
            return _ok(tasklist_id=tasklist_id, tasks=items, count=len(items))

        # create_task
        if action == "create_task":
            if not tasklist_id:
                return _err("tasklist_id is required for create_task")
            if not title:
                return _err("title is required for create_task")
            body: Dict[str, Any] = {"title": title}
            if notes:
                body["notes"] = notes
            if due:
                body["due"] = due
            if status:
                body["status"] = status
            created = service.tasks().insert(tasklist=tasklist_id, body=body).execute()
            return _ok(tasklist_id=tasklist_id, task=created)

        # complete_task
        if action == "complete_task":
            if not tasklist_id:
                return _err("tasklist_id is required for complete_task")
            if not task_id:
                return _err("task_id is required for complete_task")
            existing = service.tasks().get(tasklist=tasklist_id, task=task_id).execute()
            existing["status"] = "completed"
            updated = service.tasks().update(
                tasklist=tasklist_id, task=task_id, body=existing
            ).execute()
            return _ok(tasklist_id=tasklist_id, task_id=task_id, task=updated)

    except Exception as e:
        return _err(str(e), action=action)

    return _err(f"Unhandled action: {action}")
