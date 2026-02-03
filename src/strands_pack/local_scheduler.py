"""
Local Scheduler Tool (SQLite-backed, EventBridge-like)

This is a developer-simple local scheduler that stores schedules in SQLite and, when run,
enqueues messages into `local_queue`.

Important: Unlike AWS EventBridge Scheduler, this does not run automatically unless you
call `run_due` periodically (e.g., from a dev script, a loop, or cron).

Default DB path:
  - Uses `db_path` if provided
  - Else uses env `SQLITE_DB_PATH`

Actions
-------
- init_db
    Initialize the database schema.
- schedule_at
    Parameters: run_at_epoch (required), message_body (required), queue_name (default "default"), schedule_name (optional)
- schedule_in
    Parameters: delay_seconds (required), message_body (required), queue_name (default "default"), schedule_name (optional)
- schedule_rate
    Parameters: schedule_expression (required, e.g. "rate(5 minutes)"), message_body (required), queue_name (default "default"), schedule_name (optional)
- get_schedule
    Parameters: schedule_id (required)
- list_schedules
    Parameters: include_fired (default False), limit (default 100)
- update_schedule
    Parameters: schedule_id (required), plus any fields to update (message_body/queue_name/run_at_epoch/delay_seconds/schedule_expression/schedule_name)
- cancel_schedule
    Parameters: schedule_id (required)
- run_due
    Parameters: max_to_run (default 50), delete_after (default True)
"""

from __future__ import annotations

import os
import re
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from strands import tool

from strands_pack.local_queue import local_queue


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
        CREATE TABLE IF NOT EXISTS local_schedules (
            schedule_id TEXT PRIMARY KEY,
            schedule_name TEXT,
            run_at_epoch INTEGER NOT NULL,
            queue_name TEXT NOT NULL,
            message_body TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            fired_at INTEGER
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ls_due ON local_schedules(fired_at, run_at_epoch)")
    # Migrations for recurring schedules / metadata
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(local_schedules)").fetchall()}
    if "schedule_expression" not in cols:
        conn.execute("ALTER TABLE local_schedules ADD COLUMN schedule_expression TEXT")
    if "interval_seconds" not in cols:
        conn.execute("ALTER TABLE local_schedules ADD COLUMN interval_seconds INTEGER")
    if "last_fired_at" not in cols:
        conn.execute("ALTER TABLE local_schedules ADD COLUMN last_fired_at INTEGER")
    conn.commit()


def _parse_rate_expression(expr: str) -> Optional[int]:
    """
    Parse a minimal EventBridge-style rate expression:
      rate(5 minutes)
      rate(1 minute)
      rate(30 seconds)
      rate(2 hours)
    Returns interval seconds or None if invalid.
    """
    if not expr:
        return None
    m = re.match(r"(?i)^\s*rate\(\s*(\d+)\s*(second|seconds|minute|minutes|hour|hours)\s*\)\s*$", expr.strip())
    if not m:
        return None
    n = int(m.group(1))
    unit = m.group(2).lower()
    if n < 1:
        return None
    if unit.startswith("second"):
        return n
    if unit.startswith("minute"):
        return n * 60
    if unit.startswith("hour"):
        return n * 3600
    return None


@tool
def local_scheduler(
    action: str,
    db_path: Optional[str] = None,
    schedule_id: Optional[str] = None,
    schedule_name: Optional[str] = None,
    run_at_epoch: Optional[int] = None,
    delay_seconds: Optional[int] = None,
    schedule_expression: Optional[str] = None,
    message_body: Optional[str] = None,
    queue_name: str = "default",
    include_fired: bool = False,
    limit: int = 100,
    max_to_run: int = 50,
    delete_after: bool = True,
) -> Dict[str, Any]:
    """
    Local SQLite-backed scheduler (EventBridge-like) for development and testing.

    Note: Unlike AWS EventBridge Scheduler, this does not run automatically.
    You must call `run_due` periodically to fire due schedules.

    Args:
        action: The action to perform. One of:
            - "init_db": Initialize database schema.
            - "schedule_at": Schedule a message at a specific epoch time.
            - "schedule_in": Schedule a message after a delay (seconds).
            - "schedule_rate": Schedule a recurring message using a rate() expression.
            - "get_schedule": Get details of a schedule.
            - "list_schedules": List all schedules.
            - "update_schedule": Update schedule fields safely.
            - "cancel_schedule": Cancel (delete) a schedule.
            - "run_due": Fire all due schedules (enqueues to local_queue).
        db_path: Path to SQLite database. Defaults to SQLITE_DB_PATH env var.
        schedule_id: Schedule ID (for get/cancel).
        schedule_name: Optional human-readable name for the schedule.
        run_at_epoch: Unix epoch timestamp when schedule should fire (for schedule_at).
        delay_seconds: Seconds from now when schedule should fire (for schedule_in).
        schedule_expression: Recurring schedule expression (for schedule_rate / update_schedule).
        message_body: Message body to enqueue when schedule fires.
        queue_name: Queue name to enqueue message to (default "default").
        include_fired: Include already-fired schedules in list (default False).
        limit: Max schedules to return in list (default 100, max 500).
        max_to_run: Max schedules to fire in run_due (default 50, max 500).
        delete_after: Delete schedule after firing (default True). If False, marks as fired.

    Returns:
        dict with success status and action-specific data

    Examples:
        >>> local_scheduler(action="schedule_in", delay_seconds=60, message_body="reminder")
        >>> local_scheduler(action="list_schedules")
        >>> local_scheduler(action="run_due")
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

            if action == "schedule_at":
                if run_at_epoch is None:
                    return _err("run_at_epoch is required (int epoch seconds)")
                if message_body is None:
                    return _err("message_body is required")
                sid = f"ls_{uuid.uuid4().hex}"
                now = int(time.time())
                conn.execute(
                    """
                    INSERT INTO local_schedules(schedule_id, schedule_name, run_at_epoch, queue_name, message_body, created_at, fired_at)
                    VALUES (?, ?, ?, ?, ?, ?, NULL)
                    """,
                    (sid, schedule_name, int(run_at_epoch), queue_name, str(message_body), now),
                )
                conn.commit()
                return _ok(schedule_id=sid, schedule_name=schedule_name, run_at_epoch=int(run_at_epoch), queue_name=queue_name)

            if action == "schedule_in":
                if delay_seconds is None:
                    return _err("delay_seconds is required")
                if message_body is None:
                    return _err("message_body is required")
                run_at = int(time.time()) + max(0, int(delay_seconds))
                sid = f"ls_{uuid.uuid4().hex}"
                now = int(time.time())
                conn.execute(
                    """
                    INSERT INTO local_schedules(schedule_id, schedule_name, run_at_epoch, queue_name, message_body, created_at, fired_at)
                    VALUES (?, ?, ?, ?, ?, ?, NULL)
                    """,
                    (sid, schedule_name, run_at, queue_name, str(message_body), now),
                )
                conn.commit()
                return _ok(schedule_id=sid, schedule_name=schedule_name, run_at_epoch=run_at, queue_name=queue_name, delay_seconds=int(delay_seconds))

            if action == "schedule_rate":
                if not schedule_expression:
                    return _err('schedule_expression is required (e.g., "rate(5 minutes)")')
                if message_body is None:
                    return _err("message_body is required")
                interval = _parse_rate_expression(str(schedule_expression))
                if interval is None:
                    return _err("Invalid schedule_expression (supported: rate(N seconds|minutes|hours))", error_type="InvalidScheduleExpression")
                now = int(time.time())
                run_at = now + interval
                sid = f"ls_{uuid.uuid4().hex}"
                conn.execute(
                    """
                    INSERT INTO local_schedules(schedule_id, schedule_name, run_at_epoch, queue_name, message_body, created_at, fired_at, schedule_expression, interval_seconds, last_fired_at)
                    VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?, NULL)
                    """,
                    (sid, schedule_name, run_at, queue_name, str(message_body), now, str(schedule_expression), int(interval)),
                )
                conn.commit()
                return _ok(
                    schedule_id=sid,
                    schedule_name=schedule_name,
                    queue_name=queue_name,
                    schedule_expression=str(schedule_expression),
                    interval_seconds=int(interval),
                    run_at_epoch=run_at,
                    recurring=True,
                )

            if action == "get_schedule":
                if not schedule_id:
                    return _err("schedule_id is required")
                row = conn.execute(
                    "SELECT * FROM local_schedules WHERE schedule_id = ?",
                    (schedule_id,),
                ).fetchone()
                if not row:
                    return _err("Schedule not found", error_type="NotFound", schedule_id=schedule_id)
                return _ok(schedule=dict(row))

            if action == "list_schedules":
                lim = max(1, min(500, int(limit)))
                if include_fired:
                    rows = conn.execute(
                        "SELECT * FROM local_schedules ORDER BY run_at_epoch ASC LIMIT ?",
                        (lim,),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT * FROM local_schedules WHERE fired_at IS NULL ORDER BY run_at_epoch ASC LIMIT ?",
                        (lim,),
                    ).fetchall()
                schedules = [dict(r) for r in rows]
                return _ok(schedules=schedules, count=len(schedules))

            if action == "update_schedule":
                if not schedule_id:
                    return _err("schedule_id is required")
                row = conn.execute("SELECT * FROM local_schedules WHERE schedule_id = ?", (schedule_id,)).fetchone()
                if not row:
                    return _err("Schedule not found", error_type="NotFound", schedule_id=schedule_id)

                updates: Dict[str, Any] = {}
                if schedule_name is not None:
                    updates["schedule_name"] = schedule_name
                if queue_name is not None:
                    updates["queue_name"] = queue_name
                if message_body is not None:
                    updates["message_body"] = str(message_body)

                if run_at_epoch is not None:
                    updates["run_at_epoch"] = int(run_at_epoch)
                    # if explicitly rescheduling, clear fired marker
                    updates["fired_at"] = None
                if delay_seconds is not None:
                    updates["run_at_epoch"] = int(time.time()) + max(0, int(delay_seconds))
                    updates["fired_at"] = None

                if schedule_expression is not None:
                    interval = _parse_rate_expression(str(schedule_expression))
                    if interval is None:
                        return _err("Invalid schedule_expression (supported: rate(N seconds|minutes|hours))", error_type="InvalidScheduleExpression")
                    updates["schedule_expression"] = str(schedule_expression)
                    updates["interval_seconds"] = int(interval)
                    updates["run_at_epoch"] = int(time.time()) + int(interval)
                    updates["fired_at"] = None

                if not updates:
                    return _err("No fields to update", error_type="InvalidParameterValue")

                # Build SQL dynamically
                cols = []
                vals = []
                for k, v in updates.items():
                    cols.append(f"{k} = ?")
                    vals.append(v)
                vals.append(schedule_id)
                conn.execute(f"UPDATE local_schedules SET {', '.join(cols)} WHERE schedule_id = ?", tuple(vals))
                conn.commit()
                return _ok(schedule_id=schedule_id, updated=True, updated_fields=sorted(updates.keys()))

            if action == "cancel_schedule":
                if not schedule_id:
                    return _err("schedule_id is required")
                cur = conn.execute("DELETE FROM local_schedules WHERE schedule_id = ?", (schedule_id,))
                conn.commit()
                return _ok(schedule_id=schedule_id, cancelled=cur.rowcount > 0)

            if action == "run_due":
                max_run = max(1, min(500, int(max_to_run)))
                now = int(time.time())

                rows = conn.execute(
                    """
                    SELECT * FROM local_schedules
                    WHERE fired_at IS NULL AND run_at_epoch <= ?
                    ORDER BY run_at_epoch ASC
                    LIMIT ?
                    """,
                    (now, max_run),
                ).fetchall()

                ran: List[Dict[str, Any]] = []
                for r in rows:
                    # enqueue into local_queue
                    send_res = local_queue(
                        action="send",
                        db_path=path,
                        queue_name=r["queue_name"],
                        body=r["message_body"],
                        delay_seconds=0,
                    )
                    if not send_res.get("success"):
                        continue

                    ran.append({"schedule_id": r["schedule_id"], "message_id": send_res.get("message_id")})

                    interval = r["interval_seconds"]
                    if interval is not None:
                        # recurring: reschedule instead of deleting/marking fired
                        next_run = now + int(interval)
                        conn.execute(
                            "UPDATE local_schedules SET last_fired_at = ?, run_at_epoch = ?, fired_at = NULL WHERE schedule_id = ?",
                            (now, next_run, r["schedule_id"]),
                        )
                    else:
                        if delete_after:
                            conn.execute("DELETE FROM local_schedules WHERE schedule_id = ?", (r["schedule_id"],))
                        else:
                            conn.execute("UPDATE local_schedules SET fired_at = ? WHERE schedule_id = ?", (now, r["schedule_id"]))

                conn.commit()
                return _ok(ran=ran, count=len(ran), now=now, delete_after=delete_after)

            return _err(
                f"Unknown action: {action}",
                error_type="InvalidAction",
                available_actions=[
                    "init_db",
                    "schedule_at",
                    "schedule_in",
                    "schedule_rate",
                    "get_schedule",
                    "list_schedules",
                    "update_schedule",
                    "cancel_schedule",
                    "run_due",
                ],
            )

        finally:
            conn.close()

    except sqlite3.Error as e:
        return _err(str(e), error_type="SQLiteError", action=action)
    except Exception as e:
        return _err(str(e), error_type=type(e).__name__, action=action)
