"""
Local Queue Tool (SQLite-backed, SQS-like)

This provides a developer-simple local queue that mimics the core SQS workflow:
send -> receive (with visibility timeout) -> delete (by receipt_handle).

It is intentionally minimal and uses only Python stdlib + SQLite.

Default DB path:
  - Uses `db_path` if provided
  - Else uses env `SQLITE_DB_PATH` (same convention as the `sqlite` tool)

Actions
-------
- init_db
    Initialize the database schema.
- send
    Parameters: body (required), queue_name (default "default"), delay_seconds (default 0)
- send_batch
    Parameters: messages (required list of dicts, up to 10), queue_name (default "default")
- receive
    Parameters: queue_name (default "default"), max_messages (default 1),
                visibility_timeout (default 30)
- delete
    Parameters: receipt_handle (required)
- delete_batch
    Parameters: receipt_handles (required list[str], up to 10)
- purge
    Parameters: queue_name (optional; if omitted, purges all queues), confirm (required for purge all)
- get_queue_attributes
    Parameters: queue_name (default "default")
- list_queues
    List all queue names in the database.
- change_visibility
    Parameters: receipt_handle (required), visibility_timeout (required)
"""

from __future__ import annotations

import os
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from strands import tool


def _db_path(db_path: Optional[str]) -> Optional[str]:
    return db_path or os.environ.get("SQLITE_DB_PATH") or os.environ.get("STRANDS_SQLITE_DB_PATH")


def _connect(path: str) -> sqlite3.Connection:
    p = Path(path).expanduser()
    if str(p) != ":memory:":
        p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    return conn


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


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS local_queue_messages (
            id TEXT PRIMARY KEY,
            queue_name TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            visible_at INTEGER NOT NULL,
            receipt_handle TEXT,
            receipt_expires_at INTEGER
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_lq_visible ON local_queue_messages(queue_name, visible_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_lq_receipt ON local_queue_messages(receipt_handle)")
    conn.commit()


@tool
def local_queue(
    action: str,
    db_path: Optional[str] = None,
    queue_name: str = "default",
    body: Optional[str] = None,
    messages: Optional[List[Dict[str, Any]]] = None,
    delay_seconds: int = 0,
    max_messages: int = 1,
    visibility_timeout: int = 30,
    receipt_handle: Optional[str] = None,
    receipt_handles: Optional[List[str]] = None,
    confirm: bool = False,
    max_message_bytes: int = 262144,
) -> Dict[str, Any]:
    """
    Local SQLite-backed queue (SQS-like) for development and testing.

    Args:
        action: The action to perform. One of:
            - "init_db": Initialize database schema.
            - "send": Send a message to a queue.
            - "send_batch": Send multiple messages to a queue (up to 10).
            - "receive": Receive messages from a queue.
            - "delete": Delete a message by receipt handle.
            - "delete_batch": Delete multiple messages (up to 10 receipt handles).
            - "purge": Delete all messages from a queue (or all queues).
            - "get_queue_attributes": Get queue statistics.
            - "list_queues": List all queue names.
            - "change_visibility": Extend or reset visibility timeout.
        db_path: Path to SQLite database. Defaults to SQLITE_DB_PATH env var.
        queue_name: Queue name (default "default").
        body: Message body (required for send).
        messages: List of message dicts for send_batch [{body, delay_seconds, id}].
        delay_seconds: Delay before message becomes visible (default 0).
        max_messages: Max messages to receive (1-10, default 1).
        visibility_timeout: Seconds before message becomes visible again (default 30).
        receipt_handle: Receipt handle for delete/change_visibility.
        receipt_handles: Receipt handles for delete_batch.
        confirm: Required True to purge all queues (when queue_name not specified).
        max_message_bytes: Max UTF-8 bytes per message body (default 262144 ~ 256KB).

    Returns:
        dict with success status and action-specific data

    Examples:
        >>> local_queue(action="send", body="Hello", queue_name="tasks")
        >>> local_queue(action="receive", queue_name="tasks")
        >>> local_queue(action="delete", receipt_handle="lqr_abc123")
    """
    action = (action or "").strip().lower()
    path = _db_path(db_path)
    if not path:
        return _err("db_path is required (or set SQLITE_DB_PATH)")

    try:
        conn = _connect(path)
        try:
            _ensure_schema(conn)

            if action == "init_db":
                return _ok(db_path=path, initialized=True)

            if action == "send":
                if body is None:
                    return _err("body is required")
                b = str(body)
                if len(b.encode("utf-8")) > int(max_message_bytes):
                    return _err(
                        "body exceeds max_message_bytes",
                        error_type="MessageTooLarge",
                        max_message_bytes=int(max_message_bytes),
                        byte_length=len(b.encode("utf-8")),
                    )
                now = int(time.time())
                msg_id = f"lq_{uuid.uuid4().hex}"
                visible_at = now + max(0, int(delay_seconds))
                conn.execute(
                    "INSERT INTO local_queue_messages(id, queue_name, body, created_at, visible_at) VALUES (?, ?, ?, ?, ?)",
                    (msg_id, queue_name, b, now, visible_at),
                )
                conn.commit()
                return _ok(message_id=msg_id, queue_name=queue_name, delay_seconds=int(delay_seconds))

            if action == "send_batch":
                if not messages or not isinstance(messages, list):
                    return _err("messages is required (list of dicts with 'body' key)")
                if len(messages) > 10:
                    return _err("send_batch supports up to 10 messages", error_type="LimitExceeded")
                now = int(time.time())
                successful: List[Dict[str, Any]] = []
                failed: List[Dict[str, Any]] = []
                inserts: List[tuple] = []
                for i, msg in enumerate(messages):
                    if not isinstance(msg, dict) or "body" not in msg:
                        failed.append({"id": str(i), "code": "InvalidMessage", "message": "missing body"})
                        continue
                    mid = str(msg.get("id", str(i)))
                    b = str(msg.get("body", ""))
                    byte_len = len(b.encode("utf-8"))
                    if byte_len > int(max_message_bytes):
                        failed.append(
                            {
                                "id": mid,
                                "code": "MessageTooLarge",
                                "message": f"body exceeds max_message_bytes={int(max_message_bytes)}",
                                "byte_length": byte_len,
                            }
                        )
                        continue
                    dly = max(0, int(msg.get("delay_seconds", 0)))
                    msg_id = f"lq_{uuid.uuid4().hex}"
                    visible_at = now + dly
                    inserts.append((msg_id, queue_name, b, now, visible_at))
                    successful.append({"id": mid, "message_id": msg_id, "delay_seconds": dly})

                if inserts:
                    conn.executemany(
                        "INSERT INTO local_queue_messages(id, queue_name, body, created_at, visible_at) VALUES (?, ?, ?, ?, ?)",
                        inserts,
                    )
                    conn.commit()

                return _ok(
                    queue_name=queue_name,
                    successful=successful,
                    failed=failed,
                    successful_count=len(successful),
                    failed_count=len(failed),
                )

            if action == "receive":
                max_msgs = max(1, min(10, int(max_messages)))
                vis_timeout = max(0, int(visibility_timeout))

                now = int(time.time())
                # Select visible (not currently in-flight) messages.
                rows = conn.execute(
                    """
                    SELECT * FROM local_queue_messages
                    WHERE queue_name = ?
                      AND visible_at <= ?
                      AND (receipt_handle IS NULL OR receipt_expires_at IS NULL OR receipt_expires_at <= ?)
                    ORDER BY created_at ASC
                    LIMIT ?
                    """,
                    (queue_name, now, now, max_msgs),
                ).fetchall()

                messages: List[Dict[str, Any]] = []
                for r in rows:
                    rh = f"lqr_{uuid.uuid4().hex}"
                    expires = now + vis_timeout
                    conn.execute(
                        "UPDATE local_queue_messages SET receipt_handle=?, receipt_expires_at=? WHERE id=?",
                        (rh, expires, r["id"]),
                    )
                    messages.append(
                        {
                            "message_id": r["id"],
                            "receipt_handle": rh,
                            "body": r["body"],
                            "queue_name": r["queue_name"],
                        }
                    )
                conn.commit()
                return _ok(queue_name=queue_name, messages=messages, count=len(messages), visibility_timeout=vis_timeout)

            if action == "delete":
                if not receipt_handle:
                    return _err("receipt_handle is required")
                cur = conn.execute("DELETE FROM local_queue_messages WHERE receipt_handle = ?", (receipt_handle,))
                conn.commit()
                return _ok(receipt_handle=receipt_handle, deleted=cur.rowcount > 0)

            if action == "delete_batch":
                if not receipt_handles or not isinstance(receipt_handles, list):
                    return _err("receipt_handles is required (list[str])")
                if len(receipt_handles) > 10:
                    return _err("delete_batch supports up to 10 receipt_handles", error_type="LimitExceeded")
                successful: List[Dict[str, Any]] = []
                failed: List[Dict[str, Any]] = []
                for i, rh in enumerate(receipt_handles):
                    if not rh:
                        failed.append({"id": str(i), "code": "InvalidReceiptHandle", "message": "empty receipt_handle"})
                        continue
                    cur = conn.execute("DELETE FROM local_queue_messages WHERE receipt_handle = ?", (rh,))
                    if cur.rowcount > 0:
                        successful.append({"id": str(i), "receipt_handle": rh})
                    else:
                        failed.append({"id": str(i), "receipt_handle": rh, "code": "NotFound", "message": "receipt_handle not found"})
                conn.commit()
                return _ok(successful=successful, failed=failed, successful_count=len(successful), failed_count=len(failed))

            if action == "purge":
                # Safety: require confirm=True to purge all queues
                if queue_name == "default" and not confirm:
                    # Check if they really meant default or forgot to specify
                    pass  # Allow purging "default" without confirm
                if queue_name:
                    cur = conn.execute("DELETE FROM local_queue_messages WHERE queue_name = ?", (queue_name,))
                else:
                    if not confirm:
                        return _err("confirm=True is required to purge all queues", error_type="ConfirmRequired")
                    cur = conn.execute("DELETE FROM local_queue_messages")
                conn.commit()
                return _ok(queue_name=queue_name or "*", purged=cur.rowcount)

            if action == "get_queue_attributes":
                now = int(time.time())
                visible = conn.execute(
                    """
                    SELECT COUNT(*) AS c FROM local_queue_messages
                    WHERE queue_name = ?
                      AND visible_at <= ?
                      AND (receipt_handle IS NULL OR receipt_expires_at IS NULL OR receipt_expires_at <= ?)
                    """,
                    (queue_name, now, now),
                ).fetchone()["c"]
                in_flight = conn.execute(
                    """
                    SELECT COUNT(*) AS c FROM local_queue_messages
                    WHERE queue_name = ?
                      AND receipt_handle IS NOT NULL
                      AND receipt_expires_at IS NOT NULL
                      AND receipt_expires_at > ?
                    """,
                    (queue_name, now),
                ).fetchone()["c"]
                total = conn.execute(
                    "SELECT COUNT(*) AS c FROM local_queue_messages WHERE queue_name = ?",
                    (queue_name,),
                ).fetchone()["c"]
                return _ok(queue_name=queue_name, visible=visible, in_flight=in_flight, total=total)

            if action == "list_queues":
                rows = conn.execute(
                    "SELECT DISTINCT queue_name FROM local_queue_messages ORDER BY queue_name"
                ).fetchall()
                queues = [r["queue_name"] for r in rows]
                return _ok(queues=queues, count=len(queues))

            if action == "change_visibility":
                if not receipt_handle:
                    return _err("receipt_handle is required")
                vis_timeout = max(0, int(visibility_timeout))
                now = int(time.time())
                expires = now + vis_timeout
                cur = conn.execute(
                    "UPDATE local_queue_messages SET receipt_expires_at = ? WHERE receipt_handle = ?",
                    (expires, receipt_handle),
                )
                conn.commit()
                return _ok(receipt_handle=receipt_handle, visibility_timeout=vis_timeout, updated=cur.rowcount > 0)

            return _err(
                f"Unknown action: {action}",
                error_type="InvalidAction",
                available_actions=[
                    "init_db",
                    "send",
                    "send_batch",
                    "receive",
                    "delete",
                    "delete_batch",
                    "purge",
                    "get_queue_attributes",
                    "list_queues",
                    "change_visibility",
                ],
            )

        finally:
            conn.close()

    except sqlite3.Error as e:
        return _err(str(e), error_type="SQLiteError", action=action)
    except Exception as e:
        return _err(str(e), error_type=type(e).__name__, action=action)
