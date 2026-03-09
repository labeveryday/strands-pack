"""
Box Platform tool for Strands Agents.

Manage files, folders, metadata, tasks, comments, and shared links in Box.

Requires:
    pip install strands-pack[box]

Authentication (env vars, checked in order):
    BOX_DEVELOPER_TOKEN               - Short-lived dev token (60 min)
    BOX_CLIENT_ID + BOX_CLIENT_SECRET - CCG auth (also set BOX_ENTERPRISE_ID or BOX_USER_ID)
    BOX_JWT_CONFIG_PATH               - Path to JWT config JSON file

Supported actions
-----------------
- get_current_user: Get authenticated user info
- list_folder: List items in a folder (default: root "0")
- list_tree: Recursively list all folders/files as a tree structure
- create_folder: Create a new folder
- upload_file: Upload a local file to Box
- download_file: Download a file from Box to a local path
- get_file_info: Get file details (name, size, dates, owner)
- delete_file: Delete a file (requires confirm=True)
- delete_folder: Delete a folder (requires confirm=True)
- search: Search for content across Box
- create_shared_link: Create a shared link on a file or folder
- apply_metadata: Apply metadata to a file
- get_metadata: Get metadata from a file
- create_task: Create a review task on a file
- assign_task: Assign a task to a user
- create_comment: Add a comment on a file
- ai_ask: Ask questions about a file's content using Box AI
- ai_text_gen: Generate or transform text based on a file using Box AI
- ai_extract: Extract key information from a file using Box AI (freeform)
- ai_extract_structured: Extract structured data using a field schema
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from strands import tool

# ---------------------------------------------------------------------------
# Lazy SDK import
# ---------------------------------------------------------------------------
try:
    from box_sdk_gen import (
        BoxCCGAuth,
        BoxClient,
        BoxDeveloperTokenAuth,
        CCGConfig,
    )

    HAS_BOX = True
except ImportError:
    HAS_BOX = False

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def _get_client() -> "BoxClient":
    """Build a BoxClient using the first available auth method."""
    # 1. Developer token
    dev_token = os.environ.get("BOX_DEVELOPER_TOKEN")
    if dev_token:
        return BoxClient(BoxDeveloperTokenAuth(token=dev_token))

    # 2. CCG — use enterprise_id (service account) or user_id (user scope), not both
    client_id = os.environ.get("BOX_CLIENT_ID")
    client_secret = os.environ.get("BOX_CLIENT_SECRET")
    if client_id and client_secret:
        enterprise_id = os.environ.get("BOX_ENTERPRISE_ID") or None
        user_id = os.environ.get("BOX_USER_ID") or None

        if user_id:
            ccg_config = CCGConfig(
                client_id=client_id,
                client_secret=client_secret,
                user_id=user_id,
            )
        elif enterprise_id:
            ccg_config = CCGConfig(
                client_id=client_id,
                client_secret=client_secret,
                enterprise_id=enterprise_id,
            )
        else:
            raise ValueError("CCG auth requires BOX_ENTERPRISE_ID or BOX_USER_ID. Set one in your .env file.")
        return BoxClient(BoxCCGAuth(config=ccg_config))

    # 3. JWT
    jwt_path = os.environ.get("BOX_JWT_CONFIG_PATH")
    if jwt_path:
        from box_sdk_gen import BoxJWTAuth, JWTConfig

        jwt_config = JWTConfig.from_config_file(config_file_path=jwt_path)
        return BoxClient(BoxJWTAuth(config=jwt_config))

    raise ValueError("No Box credentials found. Set BOX_DEVELOPER_TOKEN, BOX_CLIENT_ID + BOX_CLIENT_SECRET, or BOX_JWT_CONFIG_PATH.")


# ---------------------------------------------------------------------------
# Action handlers
# ---------------------------------------------------------------------------


def _get_current_user(client, **kwargs):
    user = client.users.get_user_me()
    return _ok(
        user_id=user.id,
        name=user.name,
        login=user.login,
        space_used=user.space_used,
        space_amount=user.space_amount,
    )


def _list_folder(client, folder_id="0", **kwargs):
    items = client.folders.get_folder_items(folder_id)
    entries = [{"type": item.type, "id": item.id, "name": item.name} for item in items.entries]
    return _ok(folder_id=folder_id, items=entries, count=len(entries))


def _list_tree(client, folder_id="0", include_files=True, max_depth=5, **kwargs):
    def _build_tree(fid: str, depth: int) -> List[Dict[str, Any]]:
        if depth <= 0:
            return [{"type": "info", "name": "... (max depth reached)"}]
        items = client.folders.get_folder_items(fid)
        nodes = []
        for item in items.entries:
            is_folder = "folder" in str(item.type).lower()
            if not include_files and not is_folder:
                continue
            node: Dict[str, Any] = {"type": "folder" if is_folder else "file", "id": item.id, "name": item.name}
            if is_folder:
                node["children"] = _build_tree(item.id, depth - 1)
            nodes.append(node)
        return nodes

    tree = _build_tree(folder_id, max_depth)

    def _render_tree(nodes: List[Dict[str, Any]], prefix: str = "") -> str:
        lines = []
        for i, node in enumerate(nodes):
            is_last = i == len(nodes) - 1
            connector = "└── " if is_last else "├── "
            icon = "[folder]" if node["type"] == "folder" else "[file]  "
            lines.append(f"{prefix}{connector}{icon} {node['name']}")
            if "children" in node and node["children"]:
                extension = "    " if is_last else "│   "
                lines.append(_render_tree(node["children"], prefix + extension))
        return "\n".join(lines)

    root_info = client.folders.get_folder_by_id(folder_id)
    root_name = root_info.name if folder_id != "0" else "All Files"
    tree_text = f"[folder] {root_name}\n{_render_tree(tree)}"

    return _ok(folder_id=folder_id, tree=tree, tree_text=tree_text)


def _create_folder(client, name="", parent_folder_id="0", **kwargs):
    if not name:
        return _err("name is required for create_folder")
    from box_sdk_gen import CreateFolderParent

    folder = client.folders.create_folder(name, CreateFolderParent(id=parent_folder_id))
    return _ok(folder_id=folder.id, name=folder.name, parent_id=parent_folder_id)


def _upload_file(client, file_path="", folder_id="0", name="", **kwargs):
    if not file_path:
        return _err("file_path is required for upload_file")
    if not os.path.isfile(file_path):
        return _err(f"File not found: {file_path}")
    upload_name = name or os.path.basename(file_path)
    from box_sdk_gen import UploadFileAttributes, UploadFileAttributesParentField

    with open(file_path, "rb") as f:
        uploaded = client.uploads.upload_file(
            UploadFileAttributes(
                name=upload_name,
                parent=UploadFileAttributesParentField(id=folder_id),
            ),
            f,
        )
    entry = uploaded.entries[0]
    return _ok(file_id=entry.id, name=entry.name, size=entry.size, folder_id=folder_id)


def _download_file(client, file_id="", destination_path="", **kwargs):
    if not file_id:
        return _err("file_id is required for download_file")
    dest = destination_path or f"./{file_id}"
    byte_stream = client.downloads.download_file(file_id=file_id)
    with open(dest, "wb") as f:
        f.write(byte_stream.read())
    return _ok(file_id=file_id, saved_to=dest)


def _get_file_info(client, file_id="", **kwargs):
    if not file_id:
        return _err("file_id is required for get_file_info")
    info = client.files.get_file_by_id(file_id)
    return _ok(
        file_id=info.id,
        name=info.name,
        size=info.size,
        created_at=str(info.created_at) if info.created_at else None,
        modified_at=str(info.modified_at) if info.modified_at else None,
        owned_by=info.owned_by.login if info.owned_by else None,
    )


def _delete_file(client, file_id="", confirm=False, **kwargs):
    if not file_id:
        return _err("file_id is required for delete_file")
    if not confirm:
        return _err("Refusing to delete file without confirm=True", error_type="ConfirmationRequired", hint="File deletion is irreversible. Set confirm=True to proceed.")
    client.files.delete_file_by_id(file_id)
    return _ok(deleted_file_id=file_id)


def _delete_folder(client, folder_id="0", confirm=False, **kwargs):
    if not folder_id or folder_id == "0":
        return _err("A valid folder_id is required (cannot delete root)")
    if not confirm:
        return _err("Refusing to delete folder without confirm=True", error_type="ConfirmationRequired", hint="Folder deletion is irreversible. Set confirm=True to proceed.")
    client.folders.delete_folder_by_id(folder_id, recursive=True)
    return _ok(deleted_folder_id=folder_id)


def _search(client, query="", file_extensions=None, ancestor_folder_ids=None, content_types=None, limit=20, **kwargs):
    if not query:
        return _err("query is required for search")
    results = client.search.search_for_content(
        query=query,
        ancestor_folder_ids=ancestor_folder_ids or [],
        file_extensions=file_extensions or [],
        content_types=content_types or [],
        limit=limit,
    )
    entries = [{"type": item.type, "id": item.id, "name": item.name} for item in results.entries]
    return _ok(query=query, results=entries, count=len(entries))


def _create_shared_link(client, file_id="", folder_id="0", access="open", **kwargs):
    if file_id:
        from box_sdk_gen import AddShareLinkToFileSharedLink, AddShareLinkToFileSharedLinkAccessField

        access_map = {
            "open": AddShareLinkToFileSharedLinkAccessField.OPEN,
            "company": AddShareLinkToFileSharedLinkAccessField.COMPANY,
            "collaborators": AddShareLinkToFileSharedLinkAccessField.COLLABORATORS,
        }
        access_val = access_map.get(access, access_map["open"])
        result = client.shared_links_files.add_share_link_to_file(
            file_id, "shared_link", shared_link=AddShareLinkToFileSharedLink(access=access_val),
        )
        return _ok(file_id=file_id, shared_link_url=result.shared_link.url, access=access)
    elif folder_id and folder_id != "0":
        from box_sdk_gen import AddShareLinkToFolderSharedLink, AddShareLinkToFolderSharedLinkAccessField

        access_map_f = {
            "open": AddShareLinkToFolderSharedLinkAccessField.OPEN,
            "company": AddShareLinkToFolderSharedLinkAccessField.COMPANY,
            "collaborators": AddShareLinkToFolderSharedLinkAccessField.COLLABORATORS,
        }
        access_val_f = access_map_f.get(access, access_map_f["open"])
        result = client.shared_links_folders.add_share_link_to_folder(
            folder_id, "shared_link", shared_link=AddShareLinkToFolderSharedLink(access=access_val_f),
        )
        return _ok(folder_id=folder_id, shared_link_url=result.shared_link.url, access=access)
    else:
        return _err("file_id or folder_id is required for create_shared_link")


def _apply_metadata(client, file_id="", template_key="", metadata=None, **kwargs):
    if not file_id:
        return _err("file_id is required for apply_metadata")
    if not template_key:
        return _err("template_key is required for apply_metadata")
    if not metadata:
        return _err("metadata dict is required for apply_metadata")
    from box_sdk_gen import CreateFileMetadataByIdScope

    client.file_metadata.create_file_metadata_by_id(file_id, CreateFileMetadataByIdScope.ENTERPRISE, template_key, metadata)
    return _ok(file_id=file_id, template_key=template_key, applied=True)


def _get_metadata(client, file_id="", template_key="", **kwargs):
    if not file_id:
        return _err("file_id is required for get_metadata")
    if template_key:
        from box_sdk_gen import GetFileMetadataByIdScope

        result = client.file_metadata.get_file_metadata_by_id(file_id, GetFileMetadataByIdScope.ENTERPRISE, template_key)
        return _ok(file_id=file_id, template_key=template_key, metadata=result.extra_data if hasattr(result, "extra_data") else {})
    else:
        result = client.file_metadata.get_file_metadata(file_id)
        entries = [
            {"template": entry.template, "scope": entry.scope, "data": entry.extra_data if hasattr(entry, "extra_data") else {}}
            for entry in result.entries
        ]
        return _ok(file_id=file_id, metadata_instances=entries)


def _create_task(client, file_id="", message="", due_at="", **kwargs):
    if not file_id:
        return _err("file_id is required for create_task")
    from box_sdk_gen import CreateTaskAction, CreateTaskItem, CreateTaskItemTypeField

    task_kwargs: Dict[str, Any] = {
        "item": CreateTaskItem(type=CreateTaskItemTypeField.FILE, id=file_id),
        "action": CreateTaskAction.REVIEW,
    }
    if message:
        task_kwargs["message"] = message
    if due_at:
        task_kwargs["due_at"] = due_at
    task = client.tasks.create_task(**task_kwargs)
    return _ok(task_id=task.id, file_id=file_id, message=message, due_at=due_at)


def _assign_task(client, task_id="", user_id="", **kwargs):
    if not task_id:
        return _err("task_id is required for assign_task")
    if not user_id:
        return _err("user_id is required for assign_task")
    from box_sdk_gen import CreateTaskAssignmentAssignTo, CreateTaskAssignmentTask, CreateTaskAssignmentTaskTypeField

    assignment = client.task_assignments.create_task_assignment(
        CreateTaskAssignmentTask(type=CreateTaskAssignmentTaskTypeField.TASK, id=task_id),
        CreateTaskAssignmentAssignTo(id=user_id),
    )
    return _ok(assignment_id=assignment.id, task_id=task_id, user_id=user_id)


def _create_comment(client, file_id="", message="", **kwargs):
    if not file_id:
        return _err("file_id is required for create_comment")
    if not message:
        return _err("message is required for create_comment")
    from box_sdk_gen import CreateCommentItem, CreateCommentItemTypeField

    comment = client.comments.create_comment(
        message,
        CreateCommentItem(id=file_id, type=CreateCommentItemTypeField.FILE),
    )
    return _ok(comment_id=comment.id, file_id=file_id, message=message)


def _ai_ask(client, file_id="", prompt="", **kwargs):
    if not file_id:
        return _err("file_id is required for ai_ask")
    if not prompt:
        return _err("prompt is required for ai_ask")
    from box_sdk_gen.managers.ai import CreateAiAskMode
    from box_sdk_gen.schemas.ai_item_ask import AiItemAsk, AiItemAskTypeField

    response = client.ai.create_ai_ask(
        CreateAiAskMode.SINGLE_ITEM_QA,
        prompt,
        [AiItemAsk(id=file_id, type=AiItemAskTypeField.FILE)],
    )
    return _ok(
        file_id=file_id,
        prompt=prompt,
        answer=response.answer,
        completion_reason=response.completion_reason if hasattr(response, "completion_reason") else None,
    )


def _ai_text_gen(client, file_id="", prompt="", **kwargs):
    if not file_id:
        return _err("file_id is required for ai_text_gen")
    if not prompt:
        return _err("prompt is required for ai_text_gen")
    from box_sdk_gen.managers.ai import CreateAiTextGenItems, CreateAiTextGenItemsTypeField

    response = client.ai.create_ai_text_gen(
        prompt,
        [CreateAiTextGenItems(id=file_id, type=CreateAiTextGenItemsTypeField.FILE)],
    )
    return _ok(
        file_id=file_id,
        prompt=prompt,
        answer=response.answer,
        completion_reason=response.completion_reason if hasattr(response, "completion_reason") else None,
    )


def _ai_extract(client, file_id="", prompt="", **kwargs):
    if not file_id:
        return _err("file_id is required for ai_extract")
    if not prompt:
        return _err("prompt is required for ai_extract")
    from box_sdk_gen.schemas.ai_item_base import AiItemBase

    response = client.ai.create_ai_extract(
        prompt,
        [AiItemBase(id=file_id)],
    )
    return _ok(
        file_id=file_id,
        prompt=prompt,
        answer=response.answer,
        completion_reason=response.completion_reason if hasattr(response, "completion_reason") else None,
    )


def _ai_extract_structured(client, file_id="", fields=None, **kwargs):
    if not file_id:
        return _err("file_id is required for ai_extract_structured")
    if not fields:
        return _err(
            "fields is required for ai_extract_structured. "
            'Provide a list of dicts with "key", "type", and optionally '
            '"display_name", "description", "prompt", "options".'
        )
    from box_sdk_gen.managers.ai import CreateAiExtractStructuredFields, CreateAiExtractStructuredFieldsOptionsField
    from box_sdk_gen.schemas.ai_item_base import AiItemBase

    structured_fields = []
    for f in fields:
        field_kwargs: Dict[str, Any] = {"key": f["key"], "type": f.get("type", "string")}
        if "display_name" in f:
            field_kwargs["display_name"] = f["display_name"]
        if "description" in f:
            field_kwargs["description"] = f["description"]
        if "prompt" in f:
            field_kwargs["prompt"] = f["prompt"]
        if "options" in f:
            field_kwargs["options"] = [CreateAiExtractStructuredFieldsOptionsField(key=opt["key"]) for opt in f["options"]]
        structured_fields.append(CreateAiExtractStructuredFields(**field_kwargs))

    response = client.ai.create_ai_extract_structured(
        [AiItemBase(id=file_id)],
        fields=structured_fields,
    )
    return _ok(file_id=file_id, answer=response.answer if hasattr(response, "answer") else {})


# ---------------------------------------------------------------------------
# Action dispatch
# ---------------------------------------------------------------------------

_ACTIONS = {
    "get_current_user": _get_current_user,
    "list_folder": _list_folder,
    "list_tree": _list_tree,
    "create_folder": _create_folder,
    "upload_file": _upload_file,
    "download_file": _download_file,
    "get_file_info": _get_file_info,
    "delete_file": _delete_file,
    "delete_folder": _delete_folder,
    "search": _search,
    "create_shared_link": _create_shared_link,
    "apply_metadata": _apply_metadata,
    "get_metadata": _get_metadata,
    "create_task": _create_task,
    "assign_task": _assign_task,
    "create_comment": _create_comment,
    "ai_ask": _ai_ask,
    "ai_text_gen": _ai_text_gen,
    "ai_extract": _ai_extract,
    "ai_extract_structured": _ai_extract_structured,
}


# ---------------------------------------------------------------------------
# Tool
# ---------------------------------------------------------------------------


@tool
def box(
    action: str,
    # Folder params
    folder_id: str = "0",
    parent_folder_id: str = "0",
    name: str = "",
    # File params
    file_id: str = "",
    file_path: str = "",
    destination_path: str = "",
    # Search params
    query: str = "",
    file_extensions: Optional[List[str]] = None,
    ancestor_folder_ids: Optional[List[str]] = None,
    content_types: Optional[List[str]] = None,
    limit: int = 20,
    # Shared link params
    access: str = "open",
    # Metadata params
    template_key: str = "",
    metadata: Optional[Dict[str, Any]] = None,
    # Task params
    task_id: str = "",
    user_id: str = "",
    message: str = "",
    due_at: str = "",
    # AI params
    prompt: str = "",
    fields: Optional[List[Dict[str, Any]]] = None,
    # Tree params
    include_files: bool = True,
    max_depth: int = 5,
    # Safety
    confirm: bool = False,
) -> Dict[str, Any]:
    """Manage files, folders, metadata, tasks, comments, and shared links in Box.

    Args:
        action: The action to perform. One of:
            - "get_current_user": Get authenticated user info
            - "list_folder": List items in a folder
            - "list_tree": Recursively list all folders and files as a tree structure
            - "create_folder": Create a new folder
            - "upload_file": Upload a local file to Box
            - "download_file": Download a file from Box
            - "get_file_info": Get file details
            - "delete_file": Delete a file (requires confirm=True)
            - "delete_folder": Delete a folder (requires confirm=True)
            - "search": Search for content
            - "create_shared_link": Create a shared link
            - "apply_metadata": Apply metadata to a file
            - "get_metadata": Get metadata from a file
            - "create_task": Create a review task on a file
            - "assign_task": Assign a task to a user
            - "create_comment": Add a comment on a file
            - "ai_ask": Ask questions about a file's content using Box AI
            - "ai_text_gen": Generate or transform text based on file content using Box AI
            - "ai_extract": Extract key information from a file using Box AI (freeform)
            - "ai_extract_structured": Extract structured data using a field schema
        folder_id: Box folder ID (default "0" = root). Used by list_folder, create_shared_link.
        parent_folder_id: Parent folder ID for create_folder (default "0" = root).
        name: Name for new folder or uploaded file.
        file_id: Box file ID. Used by download_file, get_file_info, delete_file, create_shared_link, apply_metadata, get_metadata, create_task, create_comment.
        file_path: Local file path for upload_file.
        destination_path: Local destination path for download_file.
        query: Search query string.
        file_extensions: File extensions to filter search results (e.g. ["pdf", "docx"]).
        ancestor_folder_ids: Folder IDs to scope search within.
        content_types: Where to search (e.g. ["name", "description", "file_content"]).
        limit: Max results for search (default 20).
        access: Shared link access level: "open", "company", or "collaborators".
        template_key: Metadata template key (e.g. "campaignAsset").
        metadata: Dict of metadata key-value pairs to apply.
        task_id: Task ID for assign_task.
        user_id: User ID for assign_task.
        message: Message for create_task or create_comment.
        due_at: Due date for create_task (ISO 8601, e.g. "2026-04-01T00:00:00Z").
        prompt: Prompt/question for Box AI actions (ai_ask, ai_text_gen, ai_extract).
        fields: List of field definitions for ai_extract_structured. Each dict should have "key", "type" (string/float/date/enum/multiSelect), and optionally "display_name", "description", "prompt", "options" (list of {"key": "..."}).
        include_files: For list_tree: include files in the tree (default True). Set False for folders only.
        max_depth: For list_tree: maximum recursion depth (default 5).
        confirm: Must be True for destructive actions (delete_file, delete_folder).

    Returns:
        dict with success status and action-specific data.

    Examples:
        # Get current user
        box(action="get_current_user")

        # List root folder
        box(action="list_folder")

        # Create a campaign folder
        box(action="create_folder", name="Aurora Campaign", parent_folder_id="0")

        # Upload a file
        box(action="upload_file", file_path="./output/hero.png", folder_id="12345", name="hero.png")

        # Search for PDFs
        box(action="search", query="quarterly report", file_extensions=["pdf"])

        # Create a review task
        box(action="create_task", file_id="12345", message="Please review this asset")

        # Ask Box AI about a document
        box(action="ai_ask", file_id="12345", prompt="What are the key takeaways?")

        # Extract structured data with a field schema
        box(action="ai_extract_structured", file_id="12345", fields=[
            {"key": "vendor", "type": "string", "prompt": "Who is the vendor?"},
            {"key": "amount", "type": "float", "prompt": "What is the total amount?"},
        ])
    """
    action = (action or "").strip()
    if action not in _ACTIONS:
        return _err(f"Unknown action: {action}", error_type="InvalidAction", available_actions=list(_ACTIONS.keys()))

    if not HAS_BOX:
        return _err('Box SDK not installed. Run: pip install "strands-pack[box]"', error_type="MissingDependency")

    try:
        client = _get_client()
    except Exception as e:
        return _err(str(e), error_type=type(e).__name__, action=action)

    try:
        return _ACTIONS[action](
            client,
            folder_id=folder_id,
            parent_folder_id=parent_folder_id,
            name=name,
            file_id=file_id,
            file_path=file_path,
            destination_path=destination_path,
            query=query,
            file_extensions=file_extensions,
            ancestor_folder_ids=ancestor_folder_ids,
            content_types=content_types,
            limit=limit,
            access=access,
            template_key=template_key,
            metadata=metadata,
            task_id=task_id,
            user_id=user_id,
            message=message,
            due_at=due_at,
            prompt=prompt,
            fields=fields,
            include_files=include_files,
            max_depth=max_depth,
            confirm=confirm,
        )
    except Exception as e:
        return _err(str(e), error_type=type(e).__name__, action=action)
