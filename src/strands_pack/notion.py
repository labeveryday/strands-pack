"""
Notion Tool

Manage Notion pages, databases, and blocks.

Requires:
    pip install strands-pack[notion]

Authentication:
    Set NOTION_TOKEN environment variable with your Integration token.

Supported actions
-----------------
- create_page
    Parameters: parent_id (required), title (required), properties (optional), children (optional)
- get_page
    Parameters: page_id (required)
- update_page
    Parameters: page_id (required), properties (optional), archived (optional)
- query_database
    Parameters: database_id (required), filter (optional), sorts (optional), page_size (optional)
- create_database
    Parameters: parent_id (required), title (required), properties (required)
- append_blocks
    Parameters: block_id (required), children (required - list of block objects)
- get_blocks
    Parameters: block_id (required), page_size (optional)
- search
    Parameters: query (required), filter (optional), sort (optional), page_size (optional)

Notes:
  - parent_id can be a page_id or database_id depending on the context
  - Properties format varies by database schema
  - See Notion API docs for block and property formats
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from strands import tool

# Lazy import for notion-client
_notion_client = None


def _get_notion_client():
    global _notion_client
    if _notion_client is None:
        try:
            from notion_client import Client
            _notion_client = Client
        except ImportError:
            raise ImportError("notion-client not installed. Run: pip install strands-pack[notion]") from None

    token = os.environ.get("NOTION_TOKEN")
    if not token:
        raise ValueError("NOTION_TOKEN environment variable is not set")

    return _notion_client(auth=token)


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


def _extract_page_info(page: Dict[str, Any]) -> Dict[str, Any]:
    """Extract relevant information from a page object."""
    return {
        "id": page.get("id"),
        "object": page.get("object"),
        "created_time": page.get("created_time"),
        "last_edited_time": page.get("last_edited_time"),
        "archived": page.get("archived"),
        "url": page.get("url"),
        "parent": page.get("parent"),
        "properties": page.get("properties"),
    }


def _create_page(parent_id: str, title: str, properties: Optional[Dict] = None,
                 children: Optional[List[Dict]] = None, **kwargs) -> Dict[str, Any]:
    """Create a new page."""
    if not parent_id:
        return _err("parent_id is required")
    if not title:
        return _err("title is required")

    client = _get_notion_client()

    # Determine parent type based on ID format (heuristic)
    # Databases typically have different IDs than pages
    parent = {"page_id": parent_id}

    # Build properties with title
    page_properties = properties or {}
    if "title" not in page_properties and "Title" not in page_properties:
        page_properties["title"] = {
            "title": [{"text": {"content": title}}]
        }

    request_body: Dict[str, Any] = {
        "parent": parent,
        "properties": page_properties,
    }

    if children:
        request_body["children"] = children

    try:
        page = client.pages.create(**request_body)
    except Exception as e:
        # Try with database_id if page_id failed
        if "page_id" in str(e):
            parent = {"database_id": parent_id}
            request_body["parent"] = parent
            page = client.pages.create(**request_body)
        else:
            raise

    return _ok(
        action="create_page",
        page=_extract_page_info(page),
    )


def _get_page(page_id: str, **kwargs) -> Dict[str, Any]:
    """Get a page by ID."""
    if not page_id:
        return _err("page_id is required")

    client = _get_notion_client()
    page = client.pages.retrieve(page_id=page_id)

    return _ok(
        action="get_page",
        page=_extract_page_info(page),
    )


def _update_page(page_id: str, properties: Optional[Dict] = None,
                 archived: Optional[bool] = None, **kwargs) -> Dict[str, Any]:
    """Update a page."""
    if not page_id:
        return _err("page_id is required")
    if properties is None and archived is None:
        return _err("At least one of properties or archived is required")

    client = _get_notion_client()

    update_body: Dict[str, Any] = {}
    if properties is not None:
        update_body["properties"] = properties
    if archived is not None:
        update_body["archived"] = archived

    page = client.pages.update(page_id=page_id, **update_body)

    return _ok(
        action="update_page",
        page=_extract_page_info(page),
    )


def _query_database(database_id: str, filter: Optional[Dict] = None,
                    sorts: Optional[List[Dict]] = None, page_size: int = 100,
                    **kwargs) -> Dict[str, Any]:
    """Query a database."""
    if not database_id:
        return _err("database_id is required")

    client = _get_notion_client()

    query_body: Dict[str, Any] = {"page_size": min(page_size, 100)}
    if filter:
        query_body["filter"] = filter
    if sorts:
        query_body["sorts"] = sorts

    response = client.databases.query(database_id=database_id, **query_body)

    results = [_extract_page_info(page) for page in response.get("results", [])]

    return _ok(
        action="query_database",
        database_id=database_id,
        results=results,
        count=len(results),
        has_more=response.get("has_more", False),
        next_cursor=response.get("next_cursor"),
    )


def _create_database(parent_id: str, title: str, properties: Dict[str, Any],
                     **kwargs) -> Dict[str, Any]:
    """Create a new database."""
    if not parent_id:
        return _err("parent_id is required")
    if not title:
        return _err("title is required")
    if not properties:
        return _err("properties is required (database schema)")

    client = _get_notion_client()

    database = client.databases.create(
        parent={"page_id": parent_id},
        title=[{"text": {"content": title}}],
        properties=properties,
    )

    return _ok(
        action="create_database",
        database={
            "id": database.get("id"),
            "object": database.get("object"),
            "created_time": database.get("created_time"),
            "title": title,
            "url": database.get("url"),
            "properties": database.get("properties"),
        },
    )


def _append_blocks(block_id: str, children: List[Dict], **kwargs) -> Dict[str, Any]:
    """Append blocks to a page or block."""
    if not block_id:
        return _err("block_id is required")
    if not children:
        return _err("children is required (list of block objects)")

    client = _get_notion_client()

    response = client.blocks.children.append(block_id=block_id, children=children)

    results = response.get("results", [])

    return _ok(
        action="append_blocks",
        block_id=block_id,
        blocks_appended=len(results),
        results=results,
    )


def _get_blocks(block_id: str, page_size: int = 100, **kwargs) -> Dict[str, Any]:
    """Get child blocks of a page or block."""
    if not block_id:
        return _err("block_id is required")

    client = _get_notion_client()

    response = client.blocks.children.list(block_id=block_id, page_size=min(page_size, 100))

    results = response.get("results", [])

    return _ok(
        action="get_blocks",
        block_id=block_id,
        blocks=results,
        count=len(results),
        has_more=response.get("has_more", False),
        next_cursor=response.get("next_cursor"),
    )


def _search(query: str, filter: Optional[Dict] = None, sort: Optional[Dict] = None,
            page_size: int = 100, **kwargs) -> Dict[str, Any]:
    """Search for pages and databases."""
    if not query:
        return _err("query is required")

    client = _get_notion_client()

    search_body: Dict[str, Any] = {
        "query": query,
        "page_size": min(page_size, 100),
    }
    if filter:
        search_body["filter"] = filter
    if sort:
        search_body["sort"] = sort

    response = client.search(**search_body)

    results = []
    for item in response.get("results", []):
        if item.get("object") == "page":
            results.append(_extract_page_info(item))
        else:
            # Database or other object
            results.append({
                "id": item.get("id"),
                "object": item.get("object"),
                "created_time": item.get("created_time"),
                "title": item.get("title"),
                "url": item.get("url"),
            })

    return _ok(
        action="search",
        query=query,
        results=results,
        count=len(results),
        has_more=response.get("has_more", False),
        next_cursor=response.get("next_cursor"),
    )


_ACTIONS = {
    "create_page": _create_page,
    "get_page": _get_page,
    "update_page": _update_page,
    "query_database": _query_database,
    "create_database": _create_database,
    "append_blocks": _append_blocks,
    "get_blocks": _get_blocks,
    "search": _search,
}


@tool
def notion(
    action: str,
    # Common identifiers
    page_id: Optional[str] = None,
    parent_id: Optional[str] = None,
    database_id: Optional[str] = None,
    block_id: Optional[str] = None,
    # Content parameters
    title: Optional[str] = None,
    query: Optional[str] = None,
    properties: Optional[Dict[str, Any]] = None,
    children: Optional[List[Dict[str, Any]]] = None,
    # Query/filter parameters
    filter: Optional[Dict[str, Any]] = None,
    sorts: Optional[List[Dict[str, Any]]] = None,
    sort: Optional[Dict[str, Any]] = None,
    page_size: int = 100,
    # Update parameters
    archived: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Manage Notion pages, databases, and blocks.

    Actions:
    - create_page: Create a new page in a database or as child of another page
    - get_page: Retrieve a page by ID
    - update_page: Update page properties or archive status
    - query_database: Query a database with optional filters and sorts
    - create_database: Create a new database with a schema
    - append_blocks: Append content blocks to a page or block
    - get_blocks: Get child blocks of a page or block
    - search: Search for pages and databases

    Args:
        action: The action to perform (create_page, get_page, update_page,
                query_database, create_database, append_blocks, get_blocks, search)
        page_id: The ID of a page (for get_page, update_page)
        parent_id: The ID of the parent page/database (for create_page, create_database)
        database_id: The ID of a database (for query_database)
        block_id: The ID of a block/page (for append_blocks, get_blocks)
        title: The title for a new page or database (for create_page, create_database)
        query: The search query string (for search)
        properties: Properties dict for pages or database schema (for create_page,
                    update_page, create_database)
        children: List of block objects to add (for create_page, append_blocks)
        filter: Filter object for queries or searches (for query_database, search)
        sorts: List of sort objects (for query_database)
        sort: Sort object (for search)
        page_size: Number of results to return, max 100 (default: 100)
        archived: Whether to archive/unarchive a page (for update_page)

    Returns:
        dict with success status and action-specific data

    Authentication:
        Set NOTION_TOKEN environment variable with your Integration token.
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
    if page_id is not None:
        kwargs["page_id"] = page_id
    if parent_id is not None:
        kwargs["parent_id"] = parent_id
    if database_id is not None:
        kwargs["database_id"] = database_id
    if block_id is not None:
        kwargs["block_id"] = block_id
    if title is not None:
        kwargs["title"] = title
    if query is not None:
        kwargs["query"] = query
    if properties is not None:
        kwargs["properties"] = properties
    if children is not None:
        kwargs["children"] = children
    if filter is not None:
        kwargs["filter"] = filter
    if sorts is not None:
        kwargs["sorts"] = sorts
    if sort is not None:
        kwargs["sort"] = sort
    if page_size != 100:
        kwargs["page_size"] = page_size
    if archived is not None:
        kwargs["archived"] = archived

    try:
        return _ACTIONS[action](**kwargs)
    except ImportError as e:
        return _err(str(e), error_type="ImportError")
    except ValueError as e:
        return _err(str(e), error_type="ValueError")
    except Exception as e:
        return _err(str(e), error_type=type(e).__name__, action=action)
