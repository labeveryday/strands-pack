"""
EventBridge Scheduler Tool (durable jobs)

Use EventBridge Scheduler to trigger durable jobs at a specific time or on a schedule.

Important: Scheduler triggers a *target* (Lambda, SQS, Step Functions, etc.).
In this repo, the recommended “durable jobs” setup is:
  1) Store job state in DynamoDB
  2) Scheduler triggers SQS with a job_id payload
  3) Your worker/runner consumes SQS, executes the job, updates DynamoDB

This tool focuses on safely creating/managing schedules that target SQS.

Requires:
    pip install strands-pack[aws]

Security model / guardrails
--------------------------
- Optional allowlist for scheduler role ARNs via `STRANDS_PACK_SCHEDULER_ROLE_ALLOWLIST` (comma-separated).
- Optional prefix for schedule names via `STRANDS_PACK_SCHEDULE_PREFIX` (default "agent-").
- Requires explicit role_arn when creating schedules (no implicit IAM).

Actions
-------
- create_schedule
- update_schedule
- delete_schedule
- get_schedule
- list_schedules
- list_schedule_groups
- create_schedule_group
- delete_schedule_group
- pause_schedule
- resume_schedule
- schedule_job (high-level helper: create job record in DynamoDB + create one-time schedule to SQS)
- create_lambda_schedule (Option A: create schedule targeting Lambda + add invoke permission)
- update_lambda_schedule
"""

from __future__ import annotations

import json
import os
import uuid
from typing import Any, Dict, List, Optional

from strands import tool

from strands_pack.aws_tags import aws_tags_list
try:
    import boto3

    HAS_BOTO3 = True
except ImportError:  # pragma: no cover
    boto3 = None
    HAS_BOTO3 = False


def _get_client():
    if not HAS_BOTO3:
        raise ImportError("boto3 not installed. Run: pip install strands-pack[aws]")
    return boto3.client("scheduler")


def _get_lambda():
    if not HAS_BOTO3:
        raise ImportError("boto3 not installed. Run: pip install strands-pack[aws]")
    return boto3.client("lambda")


def _get_sts():
    if not HAS_BOTO3:
        raise ImportError("boto3 not installed. Run: pip install strands-pack[aws]")
    return boto3.client("sts")


def _lambda_prefix() -> str:
    return os.getenv("STRANDS_PACK_LAMBDA_PREFIX", "agent-")


def _extract_lambda_name(function_name_or_arn: str) -> str:
    if function_name_or_arn.startswith("arn:"):
        marker = ":function:"
        if marker in function_name_or_arn:
            tail = function_name_or_arn.split(marker, 1)[1]
            return tail.split(":", 1)[0]
    return function_name_or_arn


def _check_lambda_allowed(function_name_or_arn: str) -> Optional[Dict[str, Any]]:
    pref = _lambda_prefix()
    if not pref:
        return None
    name = _extract_lambda_name(function_name_or_arn)
    if not name.startswith(pref):
        return _err(
            f"Lambda function must start with prefix '{pref}'",
            error_type="NameNotAllowed",
            prefix=pref,
            function_name=name,
        )
    return None


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


def _role_allowlist() -> Optional[List[str]]:
    raw = os.getenv("STRANDS_PACK_SCHEDULER_ROLE_ALLOWLIST")
    if not raw:
        return None
    return [x.strip() for x in raw.split(",") if x.strip()]


def _check_role_allowed(role_arn: str) -> Optional[Dict[str, Any]]:
    allow = _role_allowlist()
    if allow is None:
        return None
    if role_arn in allow:
        return None
    return _err(
        "role_arn not allowlisted. Set STRANDS_PACK_SCHEDULER_ROLE_ALLOWLIST to allow it.",
        error_type="RoleNotAllowed",
        role_arn=role_arn,
        allowed_roles=allow,
    )


def _schedule_prefix() -> str:
    return os.getenv("STRANDS_PACK_SCHEDULE_PREFIX", "agent-")


def _check_name(name: str) -> Optional[Dict[str, Any]]:
    if not name:
        return _err("name is required")
    pref = _schedule_prefix()
    if pref and not name.startswith(pref):
        return _err(f"Schedule name must start with prefix '{pref}'", error_type="NameNotAllowed", prefix=pref)
    return None


def _target_sqs(queue_arn: str, role_arn: str, input_obj: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "Arn": queue_arn,
        "RoleArn": role_arn,
        "Input": json.dumps(input_obj),
    }


def _target_lambda(lambda_arn: str, role_arn: str, input_obj: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "Arn": lambda_arn,
        "RoleArn": role_arn,
        "Input": json.dumps(input_obj),
    }


def _schedule_source_arn(group_name: str, name: str) -> str:
    # arn:aws:scheduler:REGION:ACCOUNT:schedule/GROUP/NAME
    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "*"
    account = os.getenv("AWS_ACCOUNT_ID")
    if not account:
        try:
            account = _get_sts().get_caller_identity().get("Account")
        except Exception:
            account = "*"
    return f"arn:aws:scheduler:{region}:{account}:schedule/{group_name}/{name}"


def _action_create_lambda_schedule(client, **kwargs) -> Dict[str, Any]:
    name = kwargs.get("name")
    chk = _check_name(name)
    if chk:
        return chk

    schedule_expression = kwargs.get("schedule_expression")
    if not schedule_expression:
        return _err("schedule_expression is required (e.g., at(2026-02-01T10:00:00) or rate(5 minutes))")

    lambda_arn = kwargs.get("lambda_arn")
    role_arn = kwargs.get("role_arn")
    if not lambda_arn or not role_arn:
        return _err("lambda_arn and role_arn are required for Lambda target schedules")
    role_chk = _check_role_allowed(role_arn)
    if role_chk:
        return role_chk
    lchk = _check_lambda_allowed(lambda_arn)
    if lchk:
        return lchk

    input_obj = kwargs.get("input") or {}
    if not isinstance(input_obj, dict):
        return _err("input must be a dict (will be JSON-encoded)")

    group_name = kwargs.get("group_name") or "default"
    req: Dict[str, Any] = {
        "Name": name,
        "GroupName": group_name,
        "ScheduleExpression": schedule_expression,
        "FlexibleTimeWindow": {"Mode": "OFF"},
        "Target": _target_lambda(lambda_arn, role_arn, input_obj),
        "State": (kwargs.get("state") or "ENABLED").upper(),
    }
    if schedule_expression.strip().lower().startswith("at(") and kwargs.get("action_after_completion") is None:
        req["ActionAfterCompletion"] = "DELETE"
    elif kwargs.get("action_after_completion"):
        req["ActionAfterCompletion"] = kwargs["action_after_completion"]
    if kwargs.get("description"):
        req["Description"] = kwargs["description"]

    client.create_schedule(**req)
    # Tag the schedule resource (cost allocation / governance).
    try:
        client.tag_resource(
            ResourceArn=_schedule_source_arn(group_name, name),
            Tags=aws_tags_list(component="scheduler", tags=kwargs.get("tags")),
        )
    except Exception as e:
        return _err(
            f"Schedule created but tagging failed: {e}",
            error_type="TaggingFailed",
            name=name,
            group_name=group_name,
            hint="Ensure you have scheduler:TagResource permissions and a resolvable AWS account id (AWS_ACCOUNT_ID or sts:GetCallerIdentity).",
        )

    # Option A: add invoke permission so Scheduler can invoke Lambda, scoped to this schedule ARN.
    statement_id = kwargs.get("statement_id") or f"scheduler-invoke-{group_name}-{name}"
    source_arn = _schedule_source_arn(group_name, name)
    lam = _get_lambda()
    try:
        lam.add_permission(
            FunctionName=lambda_arn,
            StatementId=statement_id,
            Action="lambda:InvokeFunction",
            Principal="scheduler.amazonaws.com",
            SourceArn=source_arn,
        )
    except Exception as e:
        if "ResourceConflictException" not in str(e):
            raise

    return _ok(
        action="create_lambda_schedule",
        name=name,
        group_name=group_name,
        lambda_arn=lambda_arn,
        created=True,
        permission={"statement_id": statement_id, "source_arn": source_arn},
    )


def _action_update_lambda_schedule(client, **kwargs) -> Dict[str, Any]:
    name = kwargs.get("name")
    chk = _check_name(name)
    if chk:
        return chk
    group_name = kwargs.get("group_name") or "default"
    schedule_expression = kwargs.get("schedule_expression")
    if not schedule_expression:
        return _err("schedule_expression is required")

    lambda_arn = kwargs.get("lambda_arn")
    role_arn = kwargs.get("role_arn")
    if not lambda_arn or not role_arn:
        return _err("lambda_arn and role_arn are required")
    role_chk = _check_role_allowed(role_arn)
    if role_chk:
        return role_chk
    lchk = _check_lambda_allowed(lambda_arn)
    if lchk:
        return lchk

    input_obj = kwargs.get("input") or {}
    if not isinstance(input_obj, dict):
        return _err("input must be a dict")

    req: Dict[str, Any] = {
        "Name": name,
        "GroupName": group_name,
        "ScheduleExpression": schedule_expression,
        "FlexibleTimeWindow": {"Mode": "OFF"},
        "Target": _target_lambda(lambda_arn, role_arn, input_obj),
        "State": (kwargs.get("state") or "ENABLED").upper(),
    }
    if schedule_expression.strip().lower().startswith("at(") and kwargs.get("action_after_completion") is None:
        req["ActionAfterCompletion"] = "DELETE"
    elif kwargs.get("action_after_completion"):
        req["ActionAfterCompletion"] = kwargs["action_after_completion"]
    if kwargs.get("description"):
        req["Description"] = kwargs["description"]
    client.update_schedule(**req)

    # Ensure permission exists (idempotent)
    statement_id = kwargs.get("statement_id") or f"scheduler-invoke-{group_name}-{name}"
    source_arn = _schedule_source_arn(group_name, name)
    lam = _get_lambda()
    try:
        lam.add_permission(
            FunctionName=lambda_arn,
            StatementId=statement_id,
            Action="lambda:InvokeFunction",
            Principal="scheduler.amazonaws.com",
            SourceArn=source_arn,
        )
    except Exception as e:
        if "ResourceConflictException" not in str(e):
            raise

    return _ok(
        action="update_lambda_schedule",
        name=name,
        group_name=group_name,
        lambda_arn=lambda_arn,
        updated=True,
        permission={"statement_id": statement_id, "source_arn": source_arn},
    )

def _action_create_schedule(client, **kwargs) -> Dict[str, Any]:
    name = kwargs.get("name")
    chk = _check_name(name)
    if chk:
        return chk

    schedule_expression = kwargs.get("schedule_expression")
    if not schedule_expression:
        return _err("schedule_expression is required (e.g., at(2026-02-01T10:00:00) or rate(5 minutes))")

    queue_arn = kwargs.get("queue_arn")
    role_arn = kwargs.get("role_arn")
    if not queue_arn or not role_arn:
        return _err("queue_arn and role_arn are required for SQS target schedules")
    role_chk = _check_role_allowed(role_arn)
    if role_chk:
        return role_chk

    input_obj = kwargs.get("input") or {}
    if not isinstance(input_obj, dict):
        return _err("input must be a dict (will be JSON-encoded)")

    group_name = kwargs.get("group_name") or "default"

    req: Dict[str, Any] = {
        "Name": name,
        "GroupName": group_name,
        "ScheduleExpression": schedule_expression,
        "FlexibleTimeWindow": {"Mode": "OFF"},
        "Target": _target_sqs(queue_arn, role_arn, input_obj),
        "State": (kwargs.get("state") or "ENABLED").upper(),
    }
    # For one-time schedules, delete after completion by default to avoid clutter.
    if schedule_expression.strip().lower().startswith("at(") and kwargs.get("action_after_completion") is None:
        req["ActionAfterCompletion"] = "DELETE"
    elif kwargs.get("action_after_completion"):
        req["ActionAfterCompletion"] = kwargs["action_after_completion"]
    if kwargs.get("description"):
        req["Description"] = kwargs["description"]
    if kwargs.get("start_date"):
        req["StartDate"] = kwargs["start_date"]
    if kwargs.get("end_date"):
        req["EndDate"] = kwargs["end_date"]

    client.create_schedule(**req)
    try:
        client.tag_resource(
            ResourceArn=_schedule_source_arn(group_name, name),
            Tags=aws_tags_list(component="scheduler", tags=kwargs.get("tags")),
        )
    except Exception as e:
        return _err(
            f"Schedule created but tagging failed: {e}",
            error_type="TaggingFailed",
            name=name,
            group_name=group_name,
        )
    return _ok(name=name, group_name=group_name, created=True, tagged=True)


def _action_update_schedule(client, **kwargs) -> Dict[str, Any]:
    name = kwargs.get("name")
    chk = _check_name(name)
    if chk:
        return chk
    group_name = kwargs.get("group_name") or "default"
    schedule_expression = kwargs.get("schedule_expression")
    if not schedule_expression:
        return _err("schedule_expression is required")

    queue_arn = kwargs.get("queue_arn")
    role_arn = kwargs.get("role_arn")
    if not queue_arn or not role_arn:
        return _err("queue_arn and role_arn are required")
    role_chk = _check_role_allowed(role_arn)
    if role_chk:
        return role_chk

    input_obj = kwargs.get("input") or {}
    if not isinstance(input_obj, dict):
        return _err("input must be a dict")

    req: Dict[str, Any] = {
        "Name": name,
        "GroupName": group_name,
        "ScheduleExpression": schedule_expression,
        "FlexibleTimeWindow": {"Mode": "OFF"},
        "Target": _target_sqs(queue_arn, role_arn, input_obj),
        "State": (kwargs.get("state") or "ENABLED").upper(),
    }
    if schedule_expression.strip().lower().startswith("at(") and kwargs.get("action_after_completion") is None:
        req["ActionAfterCompletion"] = "DELETE"
    elif kwargs.get("action_after_completion"):
        req["ActionAfterCompletion"] = kwargs["action_after_completion"]
    if kwargs.get("description"):
        req["Description"] = kwargs["description"]
    client.update_schedule(**req)
    return _ok(name=name, group_name=group_name, updated=True)


def _action_delete_schedule(client, **kwargs) -> Dict[str, Any]:
    name = kwargs.get("name")
    chk = _check_name(name)
    if chk:
        return chk
    group_name = kwargs.get("group_name") or "default"
    client.delete_schedule(Name=name, GroupName=group_name)
    return _ok(name=name, group_name=group_name, deleted=True)


def _action_get_schedule(client, **kwargs) -> Dict[str, Any]:
    name = kwargs.get("name")
    chk = _check_name(name)
    if chk:
        return chk
    group_name = kwargs.get("group_name") or "default"
    resp = client.get_schedule(Name=name, GroupName=group_name)
    # Return a safe subset
    out = {
        "Name": resp.get("Name"),
        "GroupName": resp.get("GroupName"),
        "State": resp.get("State"),
        "ScheduleExpression": resp.get("ScheduleExpression"),
        "Description": resp.get("Description"),
        "Target": {"Arn": (resp.get("Target") or {}).get("Arn")},
    }
    return _ok(schedule=out)


def _action_list_schedules(client, **kwargs) -> Dict[str, Any]:
    group_name = kwargs.get("group_name") or "default"
    max_results = int(kwargs.get("max_results", 50))
    if max_results > 100:
        max_results = 100
    req: Dict[str, Any] = {"GroupName": group_name, "MaxResults": max_results}
    resp = client.list_schedules(**req)
    items = resp.get("Schedules", []) or []
    # Safe subset
    schedules = [{"Name": s.get("Name"), "State": s.get("State"), "ScheduleExpression": s.get("ScheduleExpression")} for s in items]
    return _ok(group_name=group_name, schedules=schedules, count=len(schedules), next_token=resp.get("NextToken"))


def _action_list_schedule_groups(client, **kwargs) -> Dict[str, Any]:
    max_results = int(kwargs.get("max_results", 50))
    if max_results > 100:
        max_results = 100
    resp = client.list_schedule_groups(MaxResults=max_results)
    groups = resp.get("ScheduleGroups", []) or []
    formatted = []
    for g in groups:
        formatted.append(
            {
                "Name": g.get("Name"),
                "Arn": g.get("Arn"),
                "State": g.get("State"),
                "CreationDate": g.get("CreationDate").isoformat() if g.get("CreationDate") else None,
                "LastModificationDate": g.get("LastModificationDate").isoformat() if g.get("LastModificationDate") else None,
            }
        )
    return _ok(schedule_groups=formatted, count=len(formatted), next_token=resp.get("NextToken"))


def _action_create_schedule_group(client, **kwargs) -> Dict[str, Any]:
    group_name = kwargs.get("group_name")
    if not group_name:
        return _err("group_name is required")
    # Production-minded: reuse schedule prefix guard for group names as well.
    pref = _schedule_prefix()
    if pref and not str(group_name).startswith(pref):
        return _err(
            f"Schedule group name must start with prefix '{pref}'",
            error_type="NameNotAllowed",
            prefix=pref,
            group_name=group_name,
        )
    req: Dict[str, Any] = {"Name": group_name, "Tags": aws_tags_list(component="scheduler", tags=kwargs.get("tags"))}
    resp = client.create_schedule_group(**req)
    return _ok(group_name=group_name, created=True, arn=resp.get("ScheduleGroupArn"))


def _action_delete_schedule_group(client, **kwargs) -> Dict[str, Any]:
    group_name = kwargs.get("group_name")
    if not group_name:
        return _err("group_name is required")
    if not bool(kwargs.get("confirm", False)):
        return _err(
            "Refusing to delete schedule group without confirm=True",
            error_type="ConfirmationRequired",
            hint="Deleting a schedule group is destructive. Pass confirm=True to proceed.",
        )
    client.delete_schedule_group(Name=group_name)
    return _ok(group_name=group_name, deleted=True)


def _action_pause_schedule(client, **kwargs) -> Dict[str, Any]:
    name = kwargs.get("name")
    chk = _check_name(name)
    if chk:
        return chk
    group_name = kwargs.get("group_name") or "default"
    current = client.get_schedule(Name=name, GroupName=group_name)
    req: Dict[str, Any] = {
        "Name": name,
        "GroupName": group_name,
        "ScheduleExpression": current.get("ScheduleExpression"),
        "FlexibleTimeWindow": current.get("FlexibleTimeWindow"),
        "Target": current.get("Target"),
        "State": "DISABLED",
    }
    for k in ("Description", "StartDate", "EndDate", "ActionAfterCompletion"):
        if current.get(k) is not None:
            req[k] = current.get(k)
    client.update_schedule(**req)
    return _ok(action="pause_schedule", name=name, group_name=group_name, state="DISABLED", updated=True)


def _action_resume_schedule(client, **kwargs) -> Dict[str, Any]:
    name = kwargs.get("name")
    chk = _check_name(name)
    if chk:
        return chk
    group_name = kwargs.get("group_name") or "default"
    current = client.get_schedule(Name=name, GroupName=group_name)
    req: Dict[str, Any] = {
        "Name": name,
        "GroupName": group_name,
        "ScheduleExpression": current.get("ScheduleExpression"),
        "FlexibleTimeWindow": current.get("FlexibleTimeWindow"),
        "Target": current.get("Target"),
        "State": "ENABLED",
    }
    for k in ("Description", "StartDate", "EndDate", "ActionAfterCompletion"):
        if current.get(k) is not None:
            req[k] = current.get(k)
    client.update_schedule(**req)
    return _ok(action="resume_schedule", name=name, group_name=group_name, state="ENABLED", updated=True)


def _action_schedule_job(client, **kwargs) -> Dict[str, Any]:
    """
    High-level helper: writes a job record to DynamoDB and creates a one-time schedule that sends an SQS message.

    Required:
      - table_name (DynamoDB jobs table)
      - queue_arn (SQS target arn)
      - role_arn (scheduler role arn that can sqs:SendMessage)
      - run_at (Scheduler expression: at(YYYY-MM-DDThh:mm:ss) ) OR schedule_expression passed directly

    Optional:
      - payload (dict): stored in DynamoDB + included in SQS message input
      - namespace (default "default")
      - job_id (if omitted, generated)
    """
    table_name = kwargs.get("table_name")
    queue_arn = kwargs.get("queue_arn")
    role_arn = kwargs.get("role_arn")
    if not table_name or not queue_arn or not role_arn:
        return _err("table_name, queue_arn, and role_arn are required")
    role_chk = _check_role_allowed(role_arn)
    if role_chk:
        return role_chk

    namespace = kwargs.get("namespace", "default")
    job_id = kwargs.get("job_id") or uuid.uuid4().hex
    payload = kwargs.get("payload") or {}
    if not isinstance(payload, dict):
        return _err("payload must be a dict")

    # scheduler expression
    schedule_expression = kwargs.get("schedule_expression")
    run_at = kwargs.get("run_at")
    if not schedule_expression:
        if not run_at:
            return _err("Provide schedule_expression or run_at (e.g. 2026-02-01T10:00:00)")
        schedule_expression = f"at({run_at})"

    # Compose schedule name (prefixed)
    name = f"{_schedule_prefix()}{namespace}-{job_id}"
    chk = _check_name(name)
    if chk:
        return chk

    # Write job record via DynamoDB tool (import locally to avoid circulars)
    from strands_pack.dynamodb import dynamodb as _ddb_tool

    pk = {"S": f"jobs#{namespace}"}
    sk = {"S": f"job#{job_id}"}
    status = "PENDING"
    due_at = run_at or schedule_expression
    item = {
        "pk": pk,
        "sk": sk,
        "job_id": {"S": job_id},
        "namespace": {"S": str(namespace)},
        "status": {"S": status},
        "created_at": {"S": __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime())},
        "due_at": {"S": str(due_at)},
        "gsi1pk": {"S": f"status#{status}"},
        "gsi1sk": {"S": f"{due_at}#{job_id}"},
        "payload_json": {"S": json.dumps(payload)},
    }

    put_res = _ddb_tool(action="put_item", table_name=table_name, item=item)
    if not put_res.get("success"):
        return _err("Failed to write job to DynamoDB", error_type="DynamoDBError", details=put_res)

    # Create schedule targeting SQS with job_id (and namespace) only; payload is in DynamoDB.
    input_obj = {"job_id": job_id, "namespace": namespace, "table_name": table_name}

    group_name = kwargs.get("group_name") or "default"
    create_req: Dict[str, Any] = {
        "Name": name,
        "GroupName": group_name,
        "ScheduleExpression": schedule_expression,
        "FlexibleTimeWindow": {"Mode": "OFF"},
        "Target": _target_sqs(queue_arn, role_arn, input_obj),
        "State": "ENABLED",
        "Description": f"strands-pack job {job_id}",
    }
    if schedule_expression.strip().lower().startswith("at("):
        create_req["ActionAfterCompletion"] = "DELETE"
    client.create_schedule(**create_req)
    try:
        client.tag_resource(
            ResourceArn=_schedule_source_arn(group_name, name),
            Tags=aws_tags_list(component="scheduler", tags=kwargs.get("tags")),
        )
    except Exception as e:
        return _err(
            f"Schedule created but tagging failed: {e}",
            error_type="TaggingFailed",
            schedule_name=name,
            group_name=group_name,
        )

    return _ok(
        job_id=job_id,
        namespace=namespace,
        schedule_name=name,
        group_name=group_name,
        schedule_expression=schedule_expression,
        note="Schedule will send job_id to SQS. You still need a worker to consume SQS and run the job.",
    )


_ACTIONS = {
    "create_schedule": _action_create_schedule,
    "update_schedule": _action_update_schedule,
    "delete_schedule": _action_delete_schedule,
    "get_schedule": _action_get_schedule,
    "list_schedules": _action_list_schedules,
    "list_schedule_groups": _action_list_schedule_groups,
    "create_schedule_group": _action_create_schedule_group,
    "delete_schedule_group": _action_delete_schedule_group,
    "pause_schedule": _action_pause_schedule,
    "resume_schedule": _action_resume_schedule,
    "schedule_job": _action_schedule_job,
    "create_lambda_schedule": _action_create_lambda_schedule,
    "update_lambda_schedule": _action_update_lambda_schedule,
}


@tool
def eventbridge_scheduler(
    action: str,
    name: Optional[str] = None,
    group_name: Optional[str] = None,
    schedule_expression: Optional[str] = None,
    queue_arn: Optional[str] = None,
    lambda_arn: Optional[str] = None,
    role_arn: Optional[str] = None,
    input: Optional[Dict[str, Any]] = None,
    state: Optional[str] = None,
    description: Optional[str] = None,
    action_after_completion: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    statement_id: Optional[str] = None,
    max_results: int = 50,
    table_name: Optional[str] = None,
    run_at: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    namespace: Optional[str] = None,
    job_id: Optional[str] = None,
    confirm: bool = False,
    tags: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    EventBridge Scheduler tool for durable jobs and Lambda triggers.

    Args:
        action: The action to perform. One of:
            - "list_schedules": List all schedules in a group.
            - "list_schedule_groups": List schedule groups.
            - "create_schedule_group": Create a schedule group.
            - "delete_schedule_group": Delete a schedule group (requires confirm=True).
            - "get_schedule": Get details of a specific schedule.
            - "create_schedule": Create a schedule targeting SQS.
            - "update_schedule": Update an existing SQS-targeted schedule.
            - "delete_schedule": Delete a schedule.
            - "pause_schedule": Disable an existing schedule (preserves config).
            - "resume_schedule": Enable an existing schedule (preserves config).
            - "create_lambda_schedule": Create a schedule targeting Lambda (adds invoke permission).
            - "update_lambda_schedule": Update a Lambda-targeted schedule.
            - "schedule_job": High-level helper: create DynamoDB job + one-time SQS schedule.
        name: Schedule name (must start with prefix, default "agent-").
        group_name: Schedule group name (default "default").
        schedule_expression: Cron/rate expression (e.g., "rate(5 minutes)", "at(2026-02-01T10:00:00)").
        queue_arn: SQS queue ARN for SQS-targeted schedules.
        lambda_arn: Lambda function ARN for Lambda-targeted schedules.
        role_arn: IAM role ARN for the scheduler to assume.
        input: Input payload dict to send to target (JSON-encoded).
        state: Schedule state ("ENABLED" or "DISABLED").
        description: Schedule description.
        action_after_completion: What to do after one-time schedule ("DELETE", "NONE").
        start_date: Schedule start date.
        end_date: Schedule end date.
        statement_id: Lambda permission statement ID (for Lambda schedules).
        max_results: Maximum schedules to list (default 50).
        table_name: DynamoDB table name (for schedule_job).
        run_at: ISO datetime for one-time schedule (for schedule_job).
        payload: Job payload dict (for schedule_job).
        namespace: Job namespace (for schedule_job, default "default").
        job_id: Job ID (for schedule_job, auto-generated if omitted).
        confirm: Required for destructive actions like delete_schedule_group.
        tags: Optional tags to apply to created schedules and schedule groups.

    Returns:
        dict with success status and action-specific data

    Examples:
        >>> eventbridge_scheduler(action="list_schedules")
        >>> eventbridge_scheduler(action="create_lambda_schedule", name="agent-test",
        ...     schedule_expression="rate(5 minutes)", lambda_arn="arn:aws:lambda:...",
        ...     role_arn="arn:aws:iam::...")
    """
    action = (action or "").strip()
    if action not in _ACTIONS:
        return _err(
            f"Unknown action: {action}",
            error_type="InvalidAction",
            available_actions=sorted(_ACTIONS.keys()),
        )

    # Build kwargs from explicit parameters
    kwargs: Dict[str, Any] = {}
    if name is not None:
        kwargs["name"] = name
    if group_name is not None:
        kwargs["group_name"] = group_name
    if schedule_expression is not None:
        kwargs["schedule_expression"] = schedule_expression
    if queue_arn is not None:
        kwargs["queue_arn"] = queue_arn
    if lambda_arn is not None:
        kwargs["lambda_arn"] = lambda_arn
    if role_arn is not None:
        kwargs["role_arn"] = role_arn
    if input is not None:
        kwargs["input"] = input
    if state is not None:
        kwargs["state"] = state
    if description is not None:
        kwargs["description"] = description
    if action_after_completion is not None:
        kwargs["action_after_completion"] = action_after_completion
    if start_date is not None:
        kwargs["start_date"] = start_date
    if end_date is not None:
        kwargs["end_date"] = end_date
    if statement_id is not None:
        kwargs["statement_id"] = statement_id
    if max_results != 50:
        kwargs["max_results"] = max_results
    if table_name is not None:
        kwargs["table_name"] = table_name
    if run_at is not None:
        kwargs["run_at"] = run_at
    if payload is not None:
        kwargs["payload"] = payload
    if namespace is not None:
        kwargs["namespace"] = namespace
    if job_id is not None:
        kwargs["job_id"] = job_id
    if confirm:
        kwargs["confirm"] = True
    if tags is not None:
        kwargs["tags"] = tags

    try:
        client = _get_client()
        return _ACTIONS[action](client, **kwargs)
    except Exception as e:
        return _err(str(e), error_type=type(e).__name__, action=action)


