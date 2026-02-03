"""
Gmail Tool

Interact with the Gmail API to send and read emails.

Installation:
    pip install "strands-pack[gmail]"

Authentication
--------------
Uses shared Google authentication from google_auth module.
Credentials are auto-detected from:
1. secrets/token.json (or GOOGLE_AUTHORIZED_USER_FILE env var)
2. Service account via GOOGLE_APPLICATION_CREDENTIALS env var

If no valid credentials exist, the tool will prompt you to authenticate.

Supported actions
-----------------
- send: Send an email
- list_messages: List/search messages
- get_message: Get a message by ID
- list_attachments: List attachment metadata for a message
- download_attachment: Download a specific attachment to disk
- download_attachments: Download all attachments for a message to a directory
- reply: Reply to a message (keeps thread)
- forward: Forward a message (attaches original as .eml)
- trash_message: Move a message to trash (recoverable)
- delete_message: Permanently delete a message (requires confirm=True)
- mark_read: Mark message as read
- mark_unread: Mark message as unread
- add_label / remove_label: Add/remove label(s)
- list_labels / create_label: Manage labels
- create_draft / send_draft: Draft workflow
- trash_by_query / trash_messages: Bulk trash (batched; safer)
- delete_by_query / delete_messages: Bulk permanent delete (batched; requires confirm=True)
- get_profile: Get the authenticated user's profile

Usage (Agent)
-------------
    from strands import Agent
    from strands_pack import gmail

    agent = Agent(tools=[gmail])
    agent("Send an email to someone@example.com with subject Hello")
    agent("List my recent emails")
    agent("Get the email with id abc123")
"""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from email.message import EmailMessage
from typing import Any, Dict, List, Optional

from strands import tool

DEFAULT_SCOPES: List[str] = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    # Needed for modifying labels/read state and trash/delete operations
    "https://www.googleapis.com/auth/gmail.modify",
    # Needed for label management
    "https://www.googleapis.com/auth/gmail.labels",
    # Needed for drafts workflow
    "https://www.googleapis.com/auth/gmail.compose",
]

try:
    from googleapiclient.discovery import build as _google_build

    HAS_GMAIL = True
except ImportError:  # pragma: no cover
    _google_build = None
    HAS_GMAIL = False


def _get_service(
    service_account_file: Optional[str] = None,
    authorized_user_file: Optional[str] = None,
    delegated_user: Optional[str] = None,
) -> Any:
    """Get Gmail service using shared auth."""
    from strands_pack.google_auth import get_credentials

    creds = get_credentials(
        scopes=DEFAULT_SCOPES,
        service_account_file=service_account_file,
        authorized_user_file=authorized_user_file,
        delegated_user=delegated_user,
    )

    if creds is None:
        return None  # Auth needed

    return _google_build("gmail", "v1", credentials=creds, cache_discovery=False)


def _ok(**data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": True}
    out.update(data)
    return out


def _err(message: str, **data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": False, "error": message}
    out.update(data)
    return out


def _normalize_recipients(value: Optional[str | List[str]]) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [v for v in value if v]


def _build_raw_email(
    *,
    to: Optional[str | List[str]],
    subject: str,
    body_text: Optional[str] = None,
    body_html: Optional[str] = None,
    cc: Optional[str | List[str]] = None,
    bcc: Optional[str | List[str]] = None,
    from_email: Optional[str] = None,
    reply_to: Optional[str] = None,
    attachments: Optional[List[str]] = None,
    headers: Optional[Dict[str, str]] = None,
) -> str:
    msg = EmailMessage()

    to_list = _normalize_recipients(to)
    if not to_list:
        raise ValueError("to is required")

    msg["To"] = ", ".join(to_list)
    msg["Subject"] = subject or ""

    if from_email:
        msg["From"] = from_email
    if reply_to:
        msg["Reply-To"] = reply_to
    for k, v in (headers or {}).items():
        if v is None:
            continue
        msg[k] = str(v)

    cc_list = _normalize_recipients(cc)
    if cc_list:
        msg["Cc"] = ", ".join(cc_list)

    bcc_list = _normalize_recipients(bcc)
    if bcc_list:
        msg["Bcc"] = ", ".join(bcc_list)

    if body_html and body_text:
        msg.set_content(body_text)
        msg.add_alternative(body_html, subtype="html")
    elif body_html:
        # Keep this as a single-part HTML email.
        msg.set_content(body_html, subtype="html")
    else:
        msg.set_content(body_text or "")

    for file_path in attachments or []:
        p = Path(str(file_path)).expanduser()
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(f"Attachment not found: {file_path}")
        mime, _enc = mimetypes.guess_type(str(p))
        if not mime:
            mime = "application/octet-stream"
        maintype, subtype = mime.split("/", 1)
        msg.add_attachment(p.read_bytes(), maintype=maintype, subtype=subtype, filename=p.name)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    return raw


def _walk_parts(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flatten a Gmail message payload into a list of part dicts."""
    out: List[Dict[str, Any]] = []
    stack = [payload]
    while stack:
        p = stack.pop()
        out.append(p)
        for child in p.get("parts") or []:
            stack.append(child)
    return out


def _extract_attachments(message: Dict[str, Any], include_inline: bool = False) -> List[Dict[str, Any]]:
    payload = message.get("payload") or {}
    parts = _walk_parts(payload) if isinstance(payload, dict) else []
    attachments: List[Dict[str, Any]] = []
    for p in parts:
        filename = p.get("filename") or ""
        body = p.get("body") or {}
        attachment_id = body.get("attachmentId")
        if not attachment_id:
            continue
        headers = {h.get("name"): h.get("value") for h in (p.get("headers") or []) if isinstance(h, dict)}
        content_disposition = (headers.get("Content-Disposition") or "").lower()
        is_inline = "inline" in content_disposition
        if is_inline and not include_inline:
            continue
        attachments.append(
            {
                "filename": filename,
                "attachment_id": attachment_id,
                "mime_type": p.get("mimeType"),
                "size": body.get("size"),
                "part_id": p.get("partId"),
                "inline": is_inline,
            }
        )
    return attachments


def _headers_map(message: Dict[str, Any]) -> Dict[str, str]:
    payload = message.get("payload") or {}
    headers = payload.get("headers") or []
    out: Dict[str, str] = {}
    for h in headers:
        if not isinstance(h, dict):
            continue
        name = h.get("name")
        value = h.get("value")
        if name and value:
            out[str(name)] = str(value)
    return out


def _re_subject(subject: str) -> str:
    s = (subject or "").strip()
    if not s:
        return "Re:"
    return s if s.lower().startswith("re:") else f"Re: {s}"


def _fwd_subject(subject: str) -> str:
    s = (subject or "").strip()
    if not s:
        return "Fwd:"
    return s if s.lower().startswith("fwd:") else f"Fwd: {s}"


@tool
def gmail(
    action: str,
    message_id: Optional[str] = None,
    attachment_id: Optional[str] = None,
    draft_id: Optional[str] = None,
    to: Optional[str | List[str]] = None,
    subject: Optional[str] = None,
    body_text: Optional[str] = None,
    body_html: Optional[str] = None,
    attachments: Optional[List[str]] = None,
    cc: Optional[str | List[str]] = None,
    bcc: Optional[str | List[str]] = None,
    from_email: Optional[str] = None,
    reply_to: Optional[str] = None,
    q: Optional[str] = None,
    label_ids: Optional[List[str]] = None,
    max_results: int = 10,
    include_spam_trash: bool = False,
    format: str = "full",
    include_inline_attachments: bool = False,
    output_path: Optional[str] = None,
    output_dir: Optional[str] = None,
    label_id: Optional[str] = None,
    label_name: Optional[str] = None,
    add_label_ids: Optional[List[str]] = None,
    remove_label_ids: Optional[List[str]] = None,
    confirm: bool = False,
    message_ids: Optional[List[str]] = None,
    max_to_process: Optional[int] = None,
    user_id: str = "me",
) -> Dict[str, Any]:
    """
    Gmail API tool for sending and reading emails.

    Args:
        action: The operation to perform. One of:
            - "send": Send an email
            - "list_messages": List/search messages
            - "get_message": Get a message by ID
            - "list_attachments": List attachment metadata for a message
            - "download_attachment": Download a specific attachment to disk
            - "download_attachments": Download all attachments for a message to a directory
            - "reply": Reply to a message (keeps thread)
            - "forward": Forward a message (keeps original as attached .eml)
            - "trash_message": Move a message to trash (recoverable)
            - "delete_message": Permanently delete a message (requires confirm=True)
            - "mark_read": Mark a message as read
            - "mark_unread": Mark a message as unread
            - "add_label": Add label(s) to a message
            - "remove_label": Remove label(s) from a message
            - "list_labels": List labels
            - "create_label": Create a label
            - "create_draft": Create a draft
            - "send_draft": Send an existing draft
            - "trash_by_query": Trash many messages matching a Gmail query (batched)
            - "delete_by_query": Permanently delete many messages matching a Gmail query (batched; requires confirm=True)
            - "trash_messages": Trash many messages by message_ids (batched)
            - "delete_messages": Permanently delete many messages by message_ids (batched; requires confirm=True)
            - "get_profile": Get user profile
        message_id: ID of the message (required for get_message, list_attachments, download_attachment(s), reply/forward, message operations)
        attachment_id: Attachment ID (required for download_attachment)
        draft_id: Draft ID (required for send_draft)
        to: Recipient email(s) (required for send, can be string or list)
        subject: Email subject (for send)
        body_text: Plain text body (for send)
        body_html: HTML body (for send). Use this to include hyperlinks, e.g. <a href="https://...">text</a>
        attachments: List of file paths to attach (optional, for send)
        cc: CC recipient(s) (optional, for send)
        bcc: BCC recipient(s) (optional, for send)
        from_email: From email address (optional, for send)
        reply_to: Reply-to address (optional, for send)
        q: Gmail search query (optional, for list_messages)
        label_ids: Filter by label IDs (optional, for list_messages)
        max_results: Maximum number of messages to return (default 10, for list_messages)
        include_spam_trash: Include spam/trash in results (default False, for list_messages)
        format: Message format: "full"|"metadata"|"minimal"|"raw" (default "full", for get_message)
        include_inline_attachments: Include inline attachments when listing/downloading (default False)
        output_path: Where to save a downloaded attachment (required for download_attachment)
        output_dir: Where to save downloaded attachments (required for download_attachments)
        label_id: Label id (for add_label/remove_label)
        label_name: Label name (for create_label)
        add_label_ids: Label IDs to add (advanced; for add_label)
        remove_label_ids: Label IDs to remove (advanced; for remove_label)
        confirm: Required for permanently destructive actions (delete_message)
        message_ids: List of message IDs (for trash_messages/delete_messages)
        max_to_process: Optional cap for batch operations (safety/preview), e.g. 100
        user_id: User ID (default "me")

    Returns:
        dict with success status and relevant data

    Examples:
        # Send an email
        gmail(action="send", to="someone@example.com", subject="Hello", body_text="Hi!")

        # Send with HTML (hyperlinks) and attachments
        gmail(
            action="send",
            to="someone@example.com",
            subject="Links + attachment",
            body_html='See <a href="https://example.com">this link</a>.',
            attachments=["./report.pdf"],
        )

        # List messages with search
        gmail(action="list_messages", q="from:someone@example.com", max_results=5)

        # Get a specific message
        gmail(action="get_message", message_id="abc123", format="metadata")

        # List attachments for a message
        gmail(action="list_attachments", message_id="abc123")

        # Download a specific attachment
        gmail(action="download_attachment", message_id="abc123", attachment_id="ATTACHMENT_ID", output_path="downloads/file.bin")

        # Get user profile
        gmail(action="get_profile")
    """
    if not HAS_GMAIL:
        return _err(
            "Missing Gmail dependencies. Install with: pip install strands-pack[gmail]"
        )

    valid_actions = [
        "send",
        "list_messages",
        "get_message",
        "list_attachments",
        "download_attachment",
        "download_attachments",
        "reply",
        "forward",
        "trash_message",
        "delete_message",
        "mark_read",
        "mark_unread",
        "add_label",
        "remove_label",
        "list_labels",
        "create_label",
        "create_draft",
        "send_draft",
        "trash_by_query",
        "delete_by_query",
        "trash_messages",
        "delete_messages",
        "get_profile",
    ]
    action = (action or "").strip()
    if action not in valid_actions:
        return _err(f"Unknown action: {action}", available_actions=valid_actions)

    # Get service
    service = _get_service()
    if service is None:
        from strands_pack.google_auth import needs_auth_response
        return needs_auth_response("gmail")

    try:
        # send
        if action == "send":
            if not to:
                return _err("to is required for send")
            raw = _build_raw_email(
                to=to,
                subject=subject or "",
                body_text=body_text,
                body_html=body_html,
                attachments=attachments,
                cc=cc,
                bcc=bcc,
                from_email=from_email,
                reply_to=reply_to,
            )
            resp = (
                service.users()
                .messages()
                .send(userId=user_id, body={"raw": raw})
                .execute()
            )
            return _ok(user_id=user_id, message=resp)

        # list_attachments
        if action == "list_attachments":
            if not message_id:
                return _err("message_id is required for list_attachments")
            msg = (
                service.users()
                .messages()
                .get(userId=user_id, id=message_id, format="full")
                .execute()
            )
            attachments_out = _extract_attachments(msg, include_inline=bool(include_inline_attachments))
            return _ok(user_id=user_id, message_id=message_id, count=len(attachments_out), attachments=attachments_out)

        # download_attachment
        if action == "download_attachment":
            if not message_id:
                return _err("message_id is required for download_attachment")
            if not attachment_id:
                return _err("attachment_id is required for download_attachment")
            if not output_path:
                return _err("output_path is required for download_attachment")
            out_path = Path(output_path).expanduser()
            out_path.parent.mkdir(parents=True, exist_ok=True)
            resp = (
                service.users()
                .messages()
                .attachments()
                .get(userId=user_id, messageId=message_id, id=attachment_id)
                .execute()
            )
            data = resp.get("data") or ""
            out_path.write_bytes(base64.urlsafe_b64decode(data.encode("utf-8")))
            return _ok(user_id=user_id, message_id=message_id, attachment_id=attachment_id, output_path=str(out_path))

        # download_attachments
        if action == "download_attachments":
            if not message_id:
                return _err("message_id is required for download_attachments")
            if not output_dir:
                return _err("output_dir is required for download_attachments")
            out_dir = Path(output_dir).expanduser()
            out_dir.mkdir(parents=True, exist_ok=True)
            msg = (
                service.users()
                .messages()
                .get(userId=user_id, id=message_id, format="full")
                .execute()
            )
            attachments_out = _extract_attachments(msg, include_inline=bool(include_inline_attachments))
            saved: List[Dict[str, Any]] = []
            for a in attachments_out:
                a_id = a["attachment_id"]
                a_name = a.get("filename") or f"attachment-{a_id}"
                target = out_dir / a_name
                resp = (
                    service.users()
                    .messages()
                    .attachments()
                    .get(userId=user_id, messageId=message_id, id=a_id)
                    .execute()
                )
                data = resp.get("data") or ""
                target.write_bytes(base64.urlsafe_b64decode(data.encode("utf-8")))
                saved.append({"attachment_id": a_id, "filename": a_name, "output_path": str(target)})
            return _ok(user_id=user_id, message_id=message_id, output_dir=str(out_dir), count=len(saved), saved=saved)

        # list_labels
        if action == "list_labels":
            resp = service.users().labels().list(userId=user_id).execute()
            labels = resp.get("labels", []) or []
            return _ok(user_id=user_id, labels=labels, count=len(labels))

        # create_label
        if action == "create_label":
            if not label_name:
                return _err("label_name is required for create_label")
            body = {"name": str(label_name), "labelListVisibility": "labelShow", "messageListVisibility": "show"}
            created = service.users().labels().create(userId=user_id, body=body).execute()
            return _ok(user_id=user_id, label=created)

        # mark_read / mark_unread / add_label / remove_label
        if action in ("mark_read", "mark_unread", "add_label", "remove_label"):
            if not message_id:
                return _err(f"message_id is required for {action}")

            adds: List[str] = []
            removes: List[str] = []

            if action == "mark_read":
                removes = ["UNREAD"]
            elif action == "mark_unread":
                adds = ["UNREAD"]
            elif action == "add_label":
                if label_id:
                    adds = [label_id]
                elif add_label_ids:
                    adds = list(add_label_ids)
                else:
                    return _err("label_id or add_label_ids is required for add_label")
            elif action == "remove_label":
                if label_id:
                    removes = [label_id]
                elif remove_label_ids:
                    removes = list(remove_label_ids)
                else:
                    return _err("label_id or remove_label_ids is required for remove_label")

            body = {"addLabelIds": adds, "removeLabelIds": removes}
            resp = service.users().messages().modify(userId=user_id, id=message_id, body=body).execute()
            return _ok(user_id=user_id, message_id=message_id, action=action, modified=resp, add_label_ids=adds, remove_label_ids=removes)

        # trash_message
        if action == "trash_message":
            if not message_id:
                return _err("message_id is required for trash_message")
            resp = service.users().messages().trash(userId=user_id, id=message_id).execute()
            return _ok(user_id=user_id, message_id=message_id, trashed=True, message=resp)

        # delete_message (permanent)
        if action == "delete_message":
            if not message_id:
                return _err("message_id is required for delete_message")
            if not confirm:
                return _err(
                    "Refusing to permanently delete without confirm=True",
                    action=action,
                    message_id=message_id,
                    hint="Use trash_message for a safer delete, or pass confirm=True to permanently delete.",
                )
            service.users().messages().delete(userId=user_id, id=message_id).execute()
            return _ok(user_id=user_id, message_id=message_id, deleted=True)

        def _chunk(lst: List[str], n: int) -> List[List[str]]:
            return [lst[i : i + n] for i in range(0, len(lst), n)]

        def _list_ids_for_query(query: str, limit: Optional[int]) -> List[str]:
            ids: List[str] = []
            page_token: Optional[str] = None
            while True:
                req: Dict[str, Any] = {"userId": user_id, "q": query, "maxResults": 500}
                if page_token:
                    req["pageToken"] = page_token
                resp = service.users().messages().list(**req).execute()
                batch = [m.get("id") for m in (resp.get("messages") or []) if m.get("id")]
                ids.extend(batch)
                if limit is not None and len(ids) >= limit:
                    return ids[:limit]
                page_token = resp.get("nextPageToken")
                if not page_token:
                    return ids

        def _batch_trash(ids: List[str]) -> Dict[str, Any]:
            # Gmail supports batchModify for labels; TRASH is a system label.
            service.users().messages().batchModify(
                userId=user_id,
                body={"ids": ids, "addLabelIds": ["TRASH"], "removeLabelIds": []},
            ).execute()
            return {"count": len(ids)}

        def _batch_delete(ids: List[str]) -> Dict[str, Any]:
            service.users().messages().batchDelete(userId=user_id, body={"ids": ids}).execute()
            return {"count": len(ids)}

        # trash_messages (batched)
        if action == "trash_messages":
            if not message_ids:
                return _err("message_ids is required for trash_messages")
            ids = [str(i) for i in message_ids if str(i).strip()]
            if max_to_process is not None:
                ids = ids[: int(max_to_process)]
            total = 0
            for chunk in _chunk(ids, 1000):
                total += _batch_trash(chunk)["count"]
            return _ok(user_id=user_id, action=action, trashed=True, count=total)

        # delete_messages (batched; permanent)
        if action == "delete_messages":
            if not message_ids:
                return _err("message_ids is required for delete_messages")
            if not confirm:
                return _err(
                    "Refusing to permanently delete without confirm=True",
                    action=action,
                    hint="Use trash_messages for a safer delete, or pass confirm=True to permanently delete.",
                )
            ids = [str(i) for i in message_ids if str(i).strip()]
            if max_to_process is not None:
                ids = ids[: int(max_to_process)]
            total = 0
            for chunk in _chunk(ids, 1000):
                total += _batch_delete(chunk)["count"]
            return _ok(user_id=user_id, action=action, deleted=True, count=total)

        # trash_by_query (batched)
        if action == "trash_by_query":
            if not q:
                return _err("q is required for trash_by_query")
            ids = _list_ids_for_query(q, max_to_process)
            total = 0
            for chunk in _chunk(ids, 1000):
                total += _batch_trash(chunk)["count"]
            return _ok(user_id=user_id, action=action, q=q, trashed=True, count=total)

        # delete_by_query (batched; permanent)
        if action == "delete_by_query":
            if not q:
                return _err("q is required for delete_by_query")
            if not confirm:
                return _err(
                    "Refusing to permanently delete without confirm=True",
                    action=action,
                    q=q,
                    hint="Use trash_by_query for a safer delete, or pass confirm=True to permanently delete.",
                )
            ids = _list_ids_for_query(q, max_to_process)
            total = 0
            for chunk in _chunk(ids, 1000):
                total += _batch_delete(chunk)["count"]
            return _ok(user_id=user_id, action=action, q=q, deleted=True, count=total)

        # create_draft
        if action == "create_draft":
            if not to:
                return _err("to is required for create_draft")
            raw = _build_raw_email(
                to=to,
                subject=subject or "",
                body_text=body_text,
                body_html=body_html,
                attachments=attachments,
                cc=cc,
                bcc=bcc,
                from_email=from_email,
                reply_to=reply_to,
            )
            resp = service.users().drafts().create(userId=user_id, body={"message": {"raw": raw}}).execute()
            return _ok(user_id=user_id, draft=resp)

        # send_draft
        if action == "send_draft":
            if not draft_id:
                return _err("draft_id is required for send_draft")
            resp = service.users().drafts().send(userId=user_id, body={"id": draft_id}).execute()
            return _ok(user_id=user_id, draft_id=draft_id, message=resp)

        # reply (keeps thread)
        if action == "reply":
            if not message_id:
                return _err("message_id is required for reply")
            if body_text is None and body_html is None:
                return _err("body_text or body_html is required for reply")
            original = service.users().messages().get(userId=user_id, id=message_id, format="metadata").execute()
            headers = _headers_map(original)
            thread_id = original.get("threadId")
            to_addr = headers.get("Reply-To") or headers.get("From")
            if not to_addr:
                return _err("Could not determine reply recipient (missing Reply-To/From)")
            msg_id = headers.get("Message-ID")
            refs = headers.get("References", "")
            new_headers: Dict[str, str] = {}
            if msg_id:
                new_headers["In-Reply-To"] = msg_id
                new_headers["References"] = (refs + " " + msg_id).strip() if refs else msg_id
            raw = _build_raw_email(
                to=to_addr,
                subject=_re_subject(headers.get("Subject", subject or "")),
                body_text=body_text,
                body_html=body_html,
                attachments=attachments,
                headers=new_headers,
            )
            resp = service.users().messages().send(userId=user_id, body={"raw": raw, "threadId": thread_id}).execute()
            return _ok(user_id=user_id, message=resp, thread_id=thread_id, replied_to=message_id)

        # forward (attach original as .eml)
        if action == "forward":
            if not message_id:
                return _err("message_id is required for forward")
            if not to:
                return _err("to is required for forward")
            original = service.users().messages().get(userId=user_id, id=message_id, format="raw").execute()
            headers = service.users().messages().get(userId=user_id, id=message_id, format="metadata").execute()
            hmap = _headers_map(headers)
            raw_original = original.get("raw") or ""
            try:
                original_bytes = base64.urlsafe_b64decode(raw_original.encode("utf-8"))
            except Exception:
                original_bytes = b""

            # Write original to a temp file-like on disk? Avoid. Attach bytes directly.
            eml_name = f"forwarded-{message_id}.eml"

            # Build email and attach original message
            msg = EmailMessage()
            to_list = _normalize_recipients(to)
            if not to_list:
                return _err("to is required for forward")
            msg["To"] = ", ".join(to_list)
            msg["Subject"] = _fwd_subject(hmap.get("Subject", subject or ""))
            if body_html and body_text:
                msg.set_content(body_text)
                msg.add_alternative(body_html, subtype="html")
            elif body_html:
                msg.set_content(body_html, subtype="html")
            else:
                msg.set_content(body_text or "")
            if original_bytes:
                msg.add_attachment(original_bytes, maintype="message", subtype="rfc822", filename=eml_name)
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
            resp = service.users().messages().send(userId=user_id, body={"raw": raw}).execute()
            return _ok(user_id=user_id, message=resp, forwarded_from=message_id)

        # list_messages
        if action == "list_messages":
            req_kwargs: Dict[str, Any] = {
                "userId": user_id,
                "maxResults": int(max_results),
                "includeSpamTrash": bool(include_spam_trash),
            }
            if q:
                req_kwargs["q"] = q
            if label_ids:
                req_kwargs["labelIds"] = label_ids

            resp = service.users().messages().list(**req_kwargs).execute()
            return _ok(
                user_id=user_id,
                messages=resp.get("messages", []),
                next_page_token=resp.get("nextPageToken"),
                result_size_estimate=resp.get("resultSizeEstimate"),
            )

        # get_message
        if action == "get_message":
            if not message_id:
                return _err("message_id is required for get_message")
            resp = (
                service.users()
                .messages()
                .get(userId=user_id, id=message_id, format=format)
                .execute()
            )
            return _ok(user_id=user_id, message=resp)

        # get_profile
        if action == "get_profile":
            resp = service.users().getProfile(userId=user_id).execute()
            return _ok(user_id=user_id, profile=resp)

    except Exception as e:
        return _err(str(e), action=action)

    return _err(f"Unhandled action: {action}")
