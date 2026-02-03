"""
Google Docs Tool

Interact with the Google Docs API (v1) to create documents and edit their contents.

This tool follows the same "consolidated tool" pattern as other modules in this repo:
one function with an `action` parameter that selects the operation.

Installation:
    pip install "strands-pack[docs]"

Authentication
--------------
Uses shared Google authentication from google_auth module.
Credentials are auto-detected from:
1. secrets/token.json (or GOOGLE_AUTHORIZED_USER_FILE env var)
2. Service account via GOOGLE_APPLICATION_CREDENTIALS env var

If no valid credentials exist, the tool will prompt you to authenticate.

Supported actions
-----------------
- create_document: Create a new Google Doc (optional: title)
- get_document: Fetch document structure (requires: document_id)
- append_text: Append text at the end of the document body (requires: document_id, text)
- replace_text: Replace text occurrences (requires: document_id, contains_text, replace_text; optional: match_case)
- insert_text: Insert text at a specific document index (requires: document_id, index, text)
- insert_hyperlink: Insert linked text at a specific index (requires: document_id, index, text, url)
- insert_image: Insert an inline image at a specific index (requires: document_id, index, image_uri; optional: width_pt, height_pt)

Usage (Agent)
-------------
    from strands import Agent
    from strands_pack import google_docs

    agent = Agent(tools=[google_docs])
    agent("Create a new document called Agent Report")
    agent("Append some text to document ID xyz")
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from strands import tool

DEFAULT_SCOPES: List[str] = [
    "https://www.googleapis.com/auth/documents",
]

try:
    from googleapiclient.discovery import build as _google_build

    HAS_GOOGLE_DOCS = True
except ImportError:  # pragma: no cover
    _google_build = None
    HAS_GOOGLE_DOCS = False


def _get_service(
    service_account_file: Optional[str] = None,
    authorized_user_file: Optional[str] = None,
    delegated_user: Optional[str] = None,
) -> Any:
    """Get Google Docs service using shared auth."""
    from strands_pack.google_auth import get_credentials

    creds = get_credentials(
        scopes=DEFAULT_SCOPES,
        service_account_file=service_account_file,
        authorized_user_file=authorized_user_file,
        delegated_user=delegated_user,
    )

    if creds is None:
        return None  # Auth needed

    return _google_build("docs", "v1", credentials=creds, cache_discovery=False)


def _ok(**data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": True}
    out.update(data)
    return out


def _err(message: str, **data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": False, "error": message}
    out.update(data)
    return out


def _doc_url(document_id: str) -> str:
    # Docs URLs are stable and can be constructed without an extra Drive call.
    return f"https://docs.google.com/document/d/{document_id}/edit"


@tool
def google_docs(
    action: str,
    document_id: Optional[str] = None,
    title: Optional[str] = None,
    text: Optional[str] = None,
    index: Optional[int] = None,
    url: Optional[str] = None,
    image_uri: Optional[str] = None,
    width_pt: Optional[float] = None,
    height_pt: Optional[float] = None,
    contains_text: Optional[str] = None,
    replace_text: Optional[str] = None,
    match_case: bool = True,
) -> Dict[str, Any]:
    """
    Google Docs API tool for creating and editing documents.

    Args:
        action: The operation to perform. One of:
            - "create_document": Create a new Google Doc
            - "get_document": Fetch document structure
            - "append_text": Append text at the end of the document body
            - "replace_text": Replace text occurrences
            - "insert_text": Insert text at a specific index
            - "insert_hyperlink": Insert linked text at a specific index
            - "insert_image": Insert an inline image at a specific index
        document_id: ID of the document (required for get_document, append_text, replace_text)
        title: Title for the new document (optional, for create_document)
        text: Text to append (required for append_text)
        index: Document index for insertion (required for insert_text/insert_hyperlink/insert_image)
        url: Hyperlink URL (required for insert_hyperlink)
        image_uri: Publicly accessible image URL (required for insert_image)
        width_pt: Image width in points (optional for insert_image)
        height_pt: Image height in points (optional for insert_image)
        contains_text: Text to search for (required for replace_text)
        replace_text: Replacement text (required for replace_text)
        match_case: Whether to match case when replacing (default True, for replace_text)

    Returns:
        dict with success status and relevant data

    Examples:
        # Create a document
        google_docs(action="create_document", title="My Report")

        # Get document structure
        google_docs(action="get_document", document_id="1abc...")

        # Append text
        google_docs(action="append_text", document_id="1abc...", text="Hello world!")

        # Replace text
        google_docs(action="replace_text", document_id="1abc...", contains_text="{{NAME}}", replace_text="Alice")

        # Insert text at index
        google_docs(action="insert_text", document_id="1abc...", index=1, text="Hello\\n")

        # Insert hyperlink at index
        google_docs(action="insert_hyperlink", document_id="1abc...", index=1, text="OpenAI", url="https://openai.com")

        # Insert inline image (image_uri must be reachable by Google)
        google_docs(action="insert_image", document_id="1abc...", index=1, image_uri="https://example.com/image.png", width_pt=200, height_pt=120)
    """
    if not HAS_GOOGLE_DOCS:
        return _err(
            "Missing Google Docs dependencies. Install with: pip install strands-pack[docs]"
        )

    valid_actions = [
        "create_document",
        "get_document",
        "append_text",
        "replace_text",
        "insert_text",
        "insert_hyperlink",
        "insert_image",
    ]
    action = (action or "").strip()
    if action not in valid_actions:
        return _err(f"Unknown action: {action}", available_actions=valid_actions)

    # Get service
    service = _get_service()
    if service is None:
        from strands_pack.google_auth import needs_auth_response
        return needs_auth_response("docs")

    try:
        # create_document
        if action == "create_document":
            body: Dict[str, Any] = {}
            if title:
                body["title"] = title
            doc = service.documents().create(body=body).execute()
            doc_id = doc.get("documentId")
            return _ok(document=doc, document_id=doc_id, document_url=_doc_url(doc_id) if doc_id else None)

        # get_document
        if action == "get_document":
            if not document_id:
                return _err("document_id is required for get_document")
            doc = service.documents().get(documentId=document_id).execute()
            return _ok(document=doc, document_id=document_id, document_url=_doc_url(document_id))

        # append_text
        if action == "append_text":
            if not document_id:
                return _err("document_id is required for append_text")
            if text is None:
                return _err("text is required for append_text")
            requests = [{"insertText": {"endOfSegmentLocation": {"segmentId": ""}, "text": str(text)}}]
            resp = service.documents().batchUpdate(documentId=document_id, body={"requests": requests}).execute()
            return _ok(document_id=document_id, result=resp)

        # replace_text
        if action == "replace_text":
            if not document_id:
                return _err("document_id is required for replace_text")
            if not contains_text:
                return _err("contains_text is required for replace_text")
            if replace_text is None:
                return _err("replace_text is required for replace_text")
            requests = [
                {
                    "replaceAllText": {
                        "containsText": {"text": contains_text, "matchCase": bool(match_case)},
                        "replaceText": str(replace_text),
                    }
                }
            ]
            resp = service.documents().batchUpdate(documentId=document_id, body={"requests": requests}).execute()
            return _ok(document_id=document_id, result=resp)

        # insert_text
        if action == "insert_text":
            if not document_id:
                return _err("document_id is required for insert_text")
            if index is None:
                return _err("index is required for insert_text")
            if text is None:
                return _err("text is required for insert_text")
            requests = [{"insertText": {"location": {"index": int(index)}, "text": str(text)}}]
            resp = service.documents().batchUpdate(documentId=document_id, body={"requests": requests}).execute()
            return _ok(document_id=document_id, result=resp)

        # insert_hyperlink
        if action == "insert_hyperlink":
            if not document_id:
                return _err("document_id is required for insert_hyperlink")
            if index is None:
                return _err("index is required for insert_hyperlink")
            if text is None:
                return _err("text is required for insert_hyperlink")
            if not url:
                return _err("url is required for insert_hyperlink")
            start = int(index)
            end = start + len(str(text))
            requests = [
                {"insertText": {"location": {"index": start}, "text": str(text)}},
                {
                    "updateTextStyle": {
                        "range": {"startIndex": start, "endIndex": end},
                        "textStyle": {"link": {"url": str(url)}},
                        "fields": "link",
                    }
                },
            ]
            resp = service.documents().batchUpdate(documentId=document_id, body={"requests": requests}).execute()
            return _ok(document_id=document_id, result=resp)

        # insert_image
        if action == "insert_image":
            if not document_id:
                return _err("document_id is required for insert_image")
            if index is None:
                return _err("index is required for insert_image")
            if not image_uri:
                return _err("image_uri is required for insert_image")
            req: Dict[str, Any] = {
                "insertInlineImage": {
                    "location": {"index": int(index)},
                    "uri": str(image_uri),
                }
            }
            if width_pt or height_pt:
                size: Dict[str, Any] = {}
                if width_pt is not None:
                    size["width"] = {"magnitude": float(width_pt), "unit": "PT"}
                if height_pt is not None:
                    size["height"] = {"magnitude": float(height_pt), "unit": "PT"}
                req["insertInlineImage"]["objectSize"] = size
            requests = [req]
            resp = service.documents().batchUpdate(documentId=document_id, body={"requests": requests}).execute()
            return _ok(document_id=document_id, result=resp)

    except Exception as e:
        return _err(str(e), action=action)

    return _err(f"Unhandled action: {action}")
