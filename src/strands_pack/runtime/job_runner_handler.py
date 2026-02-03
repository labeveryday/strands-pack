"""
SQS Job Runner Lambda handler (durable jobs)

This Lambda is intended to be wired to an SQS queue as an event source mapping.
Each SQS message should include JSON:
  { "job_id": "...", "namespace": "default", "table_name": "agent-jobs" }

Execution model:
  - Load job record from DynamoDB
  - Only claim jobs in status QUEUED (or PENDING for deterministic schedules)
  - Transition to RUNNING (conditional)
  - Execute:
      - deterministic: run based on job.type (placeholder for your own actions)
      - agent: call an external agent endpoint (placeholder)
  - Write DONE / FAILED

Environment variables:
  - JOBS_TABLE_NAME (optional): default table if message doesn't include it
  - JOBS_NAMESPACE (optional): default namespace if message doesn't include it
  - RUNNER_MODE: "deterministic" | "agent" (default "deterministic")
  - AGENT_WEBHOOK_URL: required if RUNNER_MODE="agent"

Security:
  - This runner never includes secrets in logs.
  - It should run with least-privilege IAM (DynamoDB read/update for the jobs table; optional network).
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional

import boto3


def _ddb():
    return boto3.client("dynamodb")


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _job_key(namespace: str, job_id: str) -> Dict[str, Any]:
    return {"pk": {"S": f"jobs#{namespace}"}, "sk": {"S": f"job#{job_id}"}}


def _get_item(table: str, namespace: str, job_id: str) -> Optional[Dict[str, Any]]:
    resp = _ddb().get_item(TableName=table, Key=_job_key(namespace, job_id))
    return resp.get("Item")


def _set_status(table: str, namespace: str, job_id: str, expected: str, new: str) -> bool:
    try:
        _ddb().update_item(
            TableName=table,
            Key=_job_key(namespace, job_id),
            ConditionExpression="#st = :e",
            UpdateExpression="SET #st=:n, updated_at=:u",
            ExpressionAttributeNames={"#st": "status"},
            ExpressionAttributeValues={":e": {"S": expected}, ":n": {"S": new}, ":u": {"S": _now()}},
        )
        return True
    except Exception:
        return False


def _write_result(table: str, namespace: str, job_id: str, status: str, result_summary: str, error: str = "") -> None:
    expr = "SET #st=:s, updated_at=:u, result_summary=:r"
    values: Dict[str, Any] = {":s": {"S": status}, ":u": {"S": _now()}, ":r": {"S": result_summary[:2000]}}
    if error:
        expr += ", last_error=:e"
        values[":e"] = {"S": error[:2000]}
    _ddb().update_item(
        TableName=table,
        Key=_job_key(namespace, job_id),
        UpdateExpression=expr,
        ExpressionAttributeNames={"#st": "status"},
        ExpressionAttributeValues=values,
    )


def _execute_deterministic(job: Dict[str, Any]) -> str:
    # Placeholder: you can implement a dispatch table based on job["type"]["S"].
    job_type = (job.get("type") or {}).get("S", "UNKNOWN")
    return f"deterministic job executed: type={job_type}"


def _execute_agent(job: Dict[str, Any]) -> str:
    # Placeholder: call your agent runtime endpoint if you want LLM-in-the-loop.
    # This module intentionally does not implement HTTP calls to avoid leaking secrets in example code.
    url = os.getenv("AGENT_WEBHOOK_URL")
    if not url:
        raise RuntimeError("AGENT_WEBHOOK_URL is required for RUNNER_MODE=agent")
    job_id = (job.get("job_id") or {}).get("S", "")
    return f"agent job would be executed via webhook: {url} (job_id={job_id})"


def handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    default_table = os.getenv("JOBS_TABLE_NAME")
    default_namespace = os.getenv("JOBS_NAMESPACE", "default")
    mode = (os.getenv("RUNNER_MODE", "deterministic") or "deterministic").lower()

    records = event.get("Records", []) or []
    processed = 0
    errors = 0

    for r in records:
        try:
            body = r.get("body") or ""
            msg = json.loads(body) if body else {}
            job_id = msg.get("job_id")
            table = msg.get("table_name") or default_table
            namespace = msg.get("namespace") or default_namespace
            if not job_id or not table:
                errors += 1
                continue

            job = _get_item(table, namespace, job_id)
            if not job:
                processed += 1
                continue

            status = (job.get("status") or {}).get("S", "")
            # Claim only QUEUED jobs (for immediate execution path)
            if status != "QUEUED":
                processed += 1
                continue

            claimed = _set_status(table, namespace, job_id, expected="QUEUED", new="RUNNING")
            if not claimed:
                processed += 1
                continue

            try:
                if mode == "agent":
                    result = _execute_agent(job)
                else:
                    result = _execute_deterministic(job)
                _write_result(table, namespace, job_id, status="DONE", result_summary=result)
            except Exception as ex:
                _write_result(table, namespace, job_id, status="FAILED", result_summary="failed", error=str(ex))
                errors += 1

            processed += 1

        except Exception:
            errors += 1

    return {"processed": processed, "errors": errors}


