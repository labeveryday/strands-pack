"""
Approval API Lambda handler (secure route)

Implements:
  - GET  /approve?job_id=...&token=...  -> shows a confirmation page (no state change)
  - POST /approve  (token in body)      -> marks job APPROVED, sets status=QUEUED, enqueues SQS
  - POST /reject   (token in body)      -> marks job REJECTED, sets status=CANCELLED

Security properties:
  - Tokens are random and short-lived
  - Only token hashes are stored in DynamoDB (SHA256(token + pepper))
  - Tokens are one-time-use (approval.used flag)
  - POST is required to actually approve/reject (prevents link preview execution)

Environment variables required:
  - JOBS_TABLE_NAME: DynamoDB table name
  - JOBS_NAMESPACE: namespace string (default "default")
  - TOKEN_PEPPER: secret string used to hash tokens (store in Secrets Manager or Lambda env var)
  - SQS_QUEUE_URL: queue URL to enqueue approved jobs for immediate execution
  - APPROVAL_BASE_PATH: base path for routes (default "")

Optional:
  - PAGE_TITLE: page title
"""

from __future__ import annotations

import hashlib
import html
import json
import os
import time
from typing import Any, Dict, Optional, Tuple

import boto3


def _env(name: str, default: Optional[str] = None) -> str:
    v = os.getenv(name, default)
    if v is None:
        raise ValueError(f"Missing env var: {name}")
    return v


def _hash_token(token: str, pepper: str) -> str:
    h = hashlib.sha256()
    h.update((token + pepper).encode("utf-8"))
    return h.hexdigest()


def _ddb():
    return boto3.client("dynamodb")


def _sqs():
    return boto3.client("sqs")


def _resp(status: int, body: str, content_type: str = "text/html") -> Dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": content_type,
            "Cache-Control": "no-store",
        },
        "body": body,
    }


def _json(status: int, obj: Dict[str, Any]) -> Dict[str, Any]:
    return _resp(status, json.dumps(obj), "application/json")


def _parse_event(event: Dict[str, Any]) -> Tuple[str, str, Dict[str, Any]]:
    method = (event.get("requestContext", {}).get("http", {}).get("method") or event.get("httpMethod") or "").upper()
    raw_path = event.get("rawPath") or event.get("path") or "/"
    qs = event.get("queryStringParameters") or {}
    return method, raw_path, qs


def _read_body_json(event: Dict[str, Any]) -> Dict[str, Any]:
    body = event.get("body") or ""
    if event.get("isBase64Encoded"):
        import base64

        body = base64.b64decode(body).decode("utf-8", errors="replace")
    try:
        return json.loads(body) if body else {}
    except Exception:
        return {}


def _job_key(namespace: str, job_id: str) -> Dict[str, Any]:
    return {
        "pk": {"S": f"jobs#{namespace}"},
        "sk": {"S": f"job#{job_id}"},
    }


def _get_job(table: str, namespace: str, job_id: str) -> Optional[Dict[str, Any]]:
    resp = _ddb().get_item(TableName=table, Key=_job_key(namespace, job_id))
    return resp.get("Item")


def _render_confirm_page(job_id: str, token: str, action: str, job_summary: str) -> str:
    title = html.escape(os.getenv("PAGE_TITLE", "Approve job"))
    safe_job = html.escape(job_id)
    safe_summary = html.escape(job_summary)
    # POST endpoints - token moves to body to minimize logging.
    return f"""<!doctype html>
<html>
  <head><meta charset="utf-8"/><title>{title}</title></head>
  <body style="font-family: sans-serif; max-width: 720px; margin: 40px auto;">
    <h2>{title}</h2>
    <p><strong>Job:</strong> {safe_job}</p>
    <pre style="background:#f6f8fa; padding:12px; border-radius:8px;">{safe_summary}</pre>
    <form method="post" action="{action}">
      <input type="hidden" name="job_id" value="{safe_job}"/>
      <input type="hidden" name="token" value="{html.escape(token)}"/>
      <button type="submit">Confirm</button>
    </form>
    <p style="color:#666; font-size: 12px;">This action requires POST to prevent accidental execution by link previews.</p>
  </body>
</html>
"""


def _parse_form_encoded(body: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for part in (body or "").split("&"):
        if not part:
            continue
        if "=" in part:
            k, v = part.split("=", 1)
        else:
            k, v = part, ""
        # minimal decoding
        k = k.replace("+", " ")
        v = v.replace("+", " ")
        try:
            from urllib.parse import unquote_plus

            k = unquote_plus(k)
            v = unquote_plus(v)
        except Exception:
            pass
        out[k] = v
    return out


def _read_post_fields(event: Dict[str, Any]) -> Dict[str, str]:
    body = event.get("body") or ""
    if event.get("isBase64Encoded"):
        import base64

        body = base64.b64decode(body).decode("utf-8", errors="replace")
    # Support either JSON body or form-encoded
    if body.strip().startswith("{"):
        j = _read_body_json(event)
        return {str(k): str(v) for k, v in (j or {}).items()}
    return _parse_form_encoded(body)


def _validate_token(
    item: Dict[str, Any],
    token: str,
    pepper: str,
    which: str,
    now_epoch: int,
) -> Tuple[bool, str]:
    approval = item.get("approval", {}).get("M") if isinstance(item.get("approval"), dict) else None
    # If approval is stored flattened, support both.
    expires_at = None
    used = None
    approve_hash = None
    reject_hash = None
    if approval and isinstance(approval, dict):
        expires_at = approval.get("expires_at", {}).get("N")
        used = approval.get("used", {}).get("BOOL")
        approve_hash = approval.get("approve_hash", {}).get("S")
        reject_hash = approval.get("reject_hash", {}).get("S")
    else:
        expires_at = (item.get("approval_expires_at") or {}).get("N")
        used = (item.get("approval_used") or {}).get("BOOL")
        approve_hash = (item.get("approval_approve_hash") or {}).get("S")
        reject_hash = (item.get("approval_reject_hash") or {}).get("S")

    if used is True:
        return False, "Token already used."
    if expires_at is None:
        return False, "No approval token on job."
    if int(float(expires_at)) < now_epoch:
        return False, "Token expired."

    presented = _hash_token(token, pepper)
    if which == "approve" and approve_hash and presented == approve_hash:
        return True, "ok"
    if which == "reject" and reject_hash and presented == reject_hash:
        return True, "ok"
    return False, "Invalid token."


def handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    table = _env("JOBS_TABLE_NAME")
    namespace = _env("JOBS_NAMESPACE", "default")
    pepper = _env("TOKEN_PEPPER")
    queue_url = _env("SQS_QUEUE_URL")
    base_path = os.getenv("APPROVAL_BASE_PATH", "")

    method, raw_path, qs = _parse_event(event)
    path = raw_path[len(base_path) :] if base_path and raw_path.startswith(base_path) else raw_path

    now = int(time.time())

    if method == "GET" and path in ("/approve", "/reject"):
        job_id = qs.get("job_id") or ""
        token = qs.get("token") or ""
        if not job_id or not token:
            return _resp(400, "Missing job_id or token", "text/plain")
        item = _get_job(table, namespace, job_id)
        if not item:
            return _resp(404, "Job not found", "text/plain")

        which = "approve" if path == "/approve" else "reject"
        ok, msg = _validate_token(item, token, pepper, which, now)
        if not ok:
            return _resp(403, msg, "text/plain")

        # Render summary from safe fields
        status = (item.get("status") or {}).get("S", "")
        due_at = (item.get("due_at") or {}).get("S", "")
        job_type = (item.get("type") or {}).get("S", "")
        summary = f"type={job_type}\\nstatus={status}\\ndue_at={due_at}"
        return _resp(200, _render_confirm_page(job_id, token, path, summary), "text/html")

    if method == "POST" and path in ("/approve", "/reject"):
        fields = _read_post_fields(event)
        job_id = fields.get("job_id") or ""
        token = fields.get("token") or ""
        if not job_id or not token:
            return _resp(400, "Missing job_id or token", "text/plain")
        item = _get_job(table, namespace, job_id)
        if not item:
            return _resp(404, "Job not found", "text/plain")

        which = "approve" if path == "/approve" else "reject"
        ok, msg = _validate_token(item, token, pepper, which, now)
        if not ok:
            return _resp(403, msg, "text/plain")

        ddb = _ddb()

        if which == "approve":
            # Update status to QUEUED and mark token used (conditional).
            ddb.update_item(
                TableName=table,
                Key=_job_key(namespace, job_id),
                ConditionExpression="attribute_not_exists(approval_used) OR approval_used = :f",
                UpdateExpression="SET approval_used=:t, approval_status=:s, approval_decided_at=:d, #st=:q",
                ExpressionAttributeNames={"#st": "status"},
                ExpressionAttributeValues={
                    ":t": {"BOOL": True},
                    ":f": {"BOOL": False},
                    ":s": {"S": "APPROVED"},
                    ":d": {"N": str(now)},
                    ":q": {"S": "QUEUED"},
                },
            )
            # Enqueue to SQS for immediate execution
            _sqs().send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps({"job_id": job_id, "namespace": namespace, "table_name": table}),
            )
            return _resp(200, "Approved. Job queued for immediate execution.", "text/plain")

        # reject
        ddb.update_item(
            TableName=table,
            Key=_job_key(namespace, job_id),
            ConditionExpression="attribute_not_exists(approval_used) OR approval_used = :f",
            UpdateExpression="SET approval_used=:t, approval_status=:s, approval_decided_at=:d, #st=:c",
            ExpressionAttributeNames={"#st": "status"},
            ExpressionAttributeValues={
                ":t": {"BOOL": True},
                ":f": {"BOOL": False},
                ":s": {"S": "REJECTED"},
                ":d": {"N": str(now)},
                ":c": {"S": "CANCELLED"},
            },
        )
        return _resp(200, "Rejected. Job cancelled.", "text/plain")

    return _json(404, {"error": "Not found"})


