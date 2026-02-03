"""
AWS Lambda Tool (guarded)

Create/update/invoke Lambda functions.

This tool is intentionally minimal and security-conscious:
- By default you must provide a role ARN when creating functions.
- Optional dev convenience: you can opt-in to auto-create a minimal **logs-only** execution role
  (similar to AWS Console) when no allowlist is configured.
- Optional allowlists:
  - STRANDS_PACK_LAMBDA_ROLE_ALLOWLIST: comma-separated role ARNs allowed for create/update
  - STRANDS_PACK_LAMBDA_PREFIX: function name prefix (default "agent-")

Requires:
    pip install strands-pack[aws]

Actions
-------
- list_functions
- get_function
- delete_function (requires confirm=True)
- list_event_source_mappings
- create_event_source_mapping
- update_event_source_mapping
- delete_event_source_mapping (requires confirm=True)
- build_zip
    Parameters: source_dir, output_zip_path
- create_function_zip
    Parameters: function_name, role_arn, handler, runtime, zip_path
- update_function_code_zip
    Parameters: function_name, zip_path
- update_function_config
    Parameters: function_name, timeout, memory, description, environment
- invoke
    Parameters: function_name, payload (dict), invocation_type ("RequestResponse"|"Event")
"""

from __future__ import annotations

import json
import os
import re
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from strands import tool

from strands_pack.aws_tags import aws_tags_dict
try:
    import boto3

    HAS_BOTO3 = True
except ImportError:  # pragma: no cover
    boto3 = None
    HAS_BOTO3 = False


def _get_client():
    if not HAS_BOTO3:
        raise ImportError("boto3 not installed. Run: pip install strands-pack[aws]")
    return boto3.client("lambda")


def _get_iam():
    if not HAS_BOTO3:
        raise ImportError("boto3 not installed. Run: pip install strands-pack[aws]")
    return boto3.client("iam")


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
    raw = os.getenv("STRANDS_PACK_LAMBDA_ROLE_ALLOWLIST")
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
        "role_arn not allowlisted. Set STRANDS_PACK_LAMBDA_ROLE_ALLOWLIST to allow it.",
        error_type="RoleNotAllowed",
        role_arn=role_arn,
        allowed_roles=allow,
    )


def _prefix() -> str:
    return os.getenv("STRANDS_PACK_LAMBDA_PREFIX", "agent-")


def _auto_role_enabled() -> bool:
    """
    Auto role creation is a dev convenience and should be explicitly enabled.

    Also: if STRANDS_PACK_LAMBDA_ROLE_ALLOWLIST is set, auto role creation is disabled to
    enforce "production posture" deterministically.
    """
    if _role_allowlist() is not None:
        return False
    return (os.getenv("STRANDS_PACK_LAMBDA_ALLOW_AUTO_ROLE_CREATE", "") or "").strip().lower() in ("1", "true", "yes")


def _sanitize_role_name(name: str) -> str:
    # IAM role names allow [A-Za-z0-9+=,.@-_], max 64 chars.
    safe = re.sub(r"[^A-Za-z0-9+=,.@_-]+", "-", name)
    return safe[:64]


def _ensure_basic_execution_role(function_name: str) -> Dict[str, Any]:
    """
    Create (or reuse) a minimal logs-only Lambda execution role.

    This mimics the AWS Console "basic execution role" behavior:
    - Trust: lambda.amazonaws.com
    - Permissions: AWS managed policy AWSLambdaBasicExecutionRole
    """
    iam = _get_iam()
    role_name = _sanitize_role_name(f"strands-agent-{function_name}-basic")

    assume_role = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }

    created = False
    try:
        resp = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(assume_role),
            Description="strands-pack: Lambda basic execution role (logs only)",
            Tags=[
                {"Key": "managed-by", "Value": "strands-pack"},
                {"Key": "purpose", "Value": "lambda-basic-execution"},
                {"Key": "function", "Value": function_name},
            ],
        )
        created = True
        role_arn = resp["Role"]["Arn"]
    except Exception as e:
        # If role exists, fetch it.
        if "EntityAlreadyExists" not in str(e):
            raise
        role = iam.get_role(RoleName=role_name)["Role"]
        role_arn = role["Arn"]

    # Attach the AWS managed policy for basic logging (idempotent enough).
    iam.attach_role_policy(
        RoleName=role_name,
        PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
    )

    return {"role_name": role_name, "role_arn": role_arn, "created": created}


def _check_name(name: str) -> Optional[Dict[str, Any]]:
    if not name:
        return _err("function_name is required")
    pref = _prefix()
    if pref and not name.startswith(pref):
        return _err(f"function_name must start with prefix '{pref}'", error_type="NameNotAllowed", prefix=pref)
    return None


@tool
def lambda_tool(
    action: str,
    function_name: Optional[str] = None,
    event_source_arn: Optional[str] = None,
    uuid: Optional[str] = None,
    enabled: Optional[bool] = None,
    batch_size: int = 10,
    maximum_batching_window_seconds: int = 0,
    report_batch_item_failures: bool = False,
    source_dir: Optional[str] = None,
    output_zip_path: Optional[str] = None,
    zip_path: Optional[str] = None,
    role_arn: Optional[str] = None,
    handler: Optional[str] = None,
    runtime: Optional[str] = None,
    timeout: int = 30,
    memory: int = 256,
    description: Optional[str] = None,
    environment: Optional[Dict[str, str]] = None,
    publish: bool = True,
    payload: Optional[Dict[str, Any]] = None,
    invocation_type: str = "RequestResponse",
    max_items: int = 50,
    confirm: bool = False,
    auto_create_role: bool = False,
    tags: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    AWS Lambda operations for serverless functions.

    Args:
        action: The action to perform. One of:
            - "list_functions": List Lambda functions in the account.
            - "get_function": Get details of a specific function.
            - "delete_function": Delete a function (requires confirm=True).
            - "list_event_source_mappings": List event source mappings (e.g., SQS -> Lambda polling).
            - "create_event_source_mapping": Create an event source mapping (e.g., SQS -> Lambda).
            - "update_event_source_mapping": Update an event source mapping by UUID.
            - "delete_event_source_mapping": Delete an event source mapping by UUID (requires confirm=True).
            - "build_zip": Create a deployment zip from a source directory.
            - "create_function_zip": Create a new Lambda function from a zip file.
            - "update_function_code_zip": Update function code from a zip file.
            - "update_function_config": Update function configuration (timeout, memory, etc).
            - "invoke": Invoke a Lambda function.
        function_name: Name of the Lambda function (must start with prefix, default "agent-").
        event_source_arn: Event source ARN for event source mappings (e.g., SQS queue ARN).
        uuid: Event source mapping UUID (update/delete).
        enabled: Enable/disable an event source mapping (create/update). If None, AWS default applies.
        batch_size: Batch size for event source mapping (SQS supports 1-10; default 10).
        maximum_batching_window_seconds: Maximum batching window (SQS supports 0-300; default 0).
        report_batch_item_failures: If True, enables partial batch failure reporting (SQS).
        source_dir: Source directory for build_zip action.
        output_zip_path: Output path for the zip file (build_zip action).
        zip_path: Path to zip file for create/update actions.
        role_arn: IAM role ARN for the function (create_function_zip).
        auto_create_role: If True, and no role_arn is provided, auto-create a minimal logs-only execution role.
            This is disabled when STRANDS_PACK_LAMBDA_ROLE_ALLOWLIST is set. You must also opt-in via
            STRANDS_PACK_LAMBDA_ALLOW_AUTO_ROLE_CREATE=true.
        handler: Function handler (e.g., "index.handler") for create_function_zip.
        runtime: Runtime (e.g., "python3.11") for create_function_zip.
        timeout: Function timeout in seconds (default 30).
        memory: Function memory in MB (default 256).
        description: Function description.
        environment: Environment variables dict for create/update config.
        publish: Whether to publish a new version (default True).
        payload: Payload dict for invoke action.
        invocation_type: "RequestResponse" (sync) or "Event" (async) for invoke.
        max_items: Maximum functions to return for list_functions (default 50).
        confirm: Required for delete_function action.

    Returns:
        dict with success status and action-specific data

    Examples:
        >>> lambda_tool(action="list_functions")
        >>> lambda_tool(action="build_zip", source_dir="./src", output_zip_path="./deploy.zip")
        >>> lambda_tool(action="invoke", function_name="agent-hello", payload={"name": "World"})
    """
    action = (action or "").strip()
    try:
        client = _get_client()
    except Exception as e:
        return _err(str(e), error_type=type(e).__name__, action=action)

    try:
        if action == "build_zip":
            if not source_dir or not output_zip_path:
                return _err("source_dir and output_zip_path are required")
            src = Path(source_dir).expanduser()
            if not src.exists() or not src.is_dir():
                return _err(f"source_dir not found or not a directory: {source_dir}", error_type="FileNotFoundError")
            out = Path(output_zip_path).expanduser()
            out.parent.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for p in src.rglob("*"):
                    if p.is_dir():
                        continue
                    rel = p.relative_to(src)
                    # Skip common junk
                    if rel.name.startswith(".") or "__pycache__" in rel.parts:
                        continue
                    zf.write(p, arcname=str(rel))

            return _ok(source_dir=str(src), output_zip_path=str(out), built=True)

        if action == "list_functions":
            resp = client.list_functions(MaxItems=max_items)
            funcs = resp.get("Functions", []) or []
            # Safe subset
            out_funcs = [{"FunctionName": f.get("FunctionName"), "Runtime": f.get("Runtime"), "LastModified": f.get("LastModified")} for f in funcs]
            return _ok(functions=out_funcs, count=len(out_funcs), next_marker=resp.get("NextMarker"))

        if action == "get_function":
            chk = _check_name(function_name)
            if chk:
                return chk
            resp = client.get_function(FunctionName=function_name)
            cfg = resp.get("Configuration", {}) or {}
            return _ok(
                configuration={
                    "FunctionName": cfg.get("FunctionName"),
                    "Runtime": cfg.get("Runtime"),
                    "Handler": cfg.get("Handler"),
                    "Role": cfg.get("Role"),
                    "Timeout": cfg.get("Timeout"),
                    "MemorySize": cfg.get("MemorySize"),
                    "Description": cfg.get("Description"),
                    "LastModified": cfg.get("LastModified"),
                }
            )

        if action == "delete_function":
            chk = _check_name(function_name)
            if chk:
                return chk
            if not confirm:
                return _err(
                    "Refusing to delete function without confirm=True",
                    error_type="ConfirmationRequired",
                    hint="Function deletion is irreversible. Pass confirm=True to proceed.",
                )
            client.delete_function(FunctionName=function_name)
            return _ok(function_name=function_name, deleted=True)

        if action == "list_event_source_mappings":
            req: Dict[str, Any] = {"MaxItems": max_items}
            if function_name:
                chk = _check_name(function_name)
                if chk:
                    return chk
                req["FunctionName"] = function_name
            if event_source_arn:
                req["EventSourceArn"] = event_source_arn
            resp = client.list_event_source_mappings(**req)
            mappings = resp.get("EventSourceMappings", []) or []
            # Keep response small and JSON-friendly.
            out = []
            for m in mappings:
                out.append(
                    {
                        "uuid": m.get("UUID"),
                        "function_arn": m.get("FunctionArn"),
                        "event_source_arn": m.get("EventSourceArn"),
                        "state": m.get("State"),
                        "batch_size": m.get("BatchSize"),
                        "maximum_batching_window_seconds": m.get("MaximumBatchingWindowInSeconds"),
                        "last_modified": m.get("LastModified").isoformat() if m.get("LastModified") else None,
                    }
                )
            return _ok(
                event_source_mappings=out,
                count=len(out),
                next_marker=resp.get("NextMarker"),
                function_filter=function_name,
                event_source_filter=event_source_arn,
            )

        if action == "create_event_source_mapping":
            chk = _check_name(function_name)
            if chk:
                return chk
            if not event_source_arn:
                return _err("event_source_arn is required")
            if batch_size < 1 or batch_size > 10:
                return _err("batch_size must be between 1 and 10 for SQS", error_type="InvalidParameterValue", batch_size=batch_size)
            if maximum_batching_window_seconds < 0 or maximum_batching_window_seconds > 300:
                return _err(
                    "maximum_batching_window_seconds must be between 0 and 300 for SQS",
                    error_type="InvalidParameterValue",
                    maximum_batching_window_seconds=maximum_batching_window_seconds,
                )
            req = {
                "FunctionName": function_name,
                "EventSourceArn": event_source_arn,
                "BatchSize": batch_size,
                "MaximumBatchingWindowInSeconds": maximum_batching_window_seconds,
            }
            if enabled is not None:
                req["Enabled"] = bool(enabled)
            if report_batch_item_failures:
                req["FunctionResponseTypes"] = ["ReportBatchItemFailures"]
            resp = client.create_event_source_mapping(**req)
            return _ok(
                created=True,
                uuid=resp.get("UUID"),
                function_arn=resp.get("FunctionArn"),
                event_source_arn=resp.get("EventSourceArn"),
                state=resp.get("State"),
                batch_size=resp.get("BatchSize"),
                maximum_batching_window_seconds=resp.get("MaximumBatchingWindowInSeconds"),
            )

        if action == "update_event_source_mapping":
            if not uuid:
                return _err("uuid is required")
            req: Dict[str, Any] = {"UUID": uuid}
            if enabled is not None:
                req["Enabled"] = bool(enabled)
            if batch_size is not None:
                if batch_size < 1 or batch_size > 10:
                    return _err("batch_size must be between 1 and 10 for SQS", error_type="InvalidParameterValue", batch_size=batch_size)
                req["BatchSize"] = batch_size
            if maximum_batching_window_seconds is not None:
                if maximum_batching_window_seconds < 0 or maximum_batching_window_seconds > 300:
                    return _err(
                        "maximum_batching_window_seconds must be between 0 and 300 for SQS",
                        error_type="InvalidParameterValue",
                        maximum_batching_window_seconds=maximum_batching_window_seconds,
                    )
                req["MaximumBatchingWindowInSeconds"] = maximum_batching_window_seconds
            if report_batch_item_failures:
                req["FunctionResponseTypes"] = ["ReportBatchItemFailures"]
            resp = client.update_event_source_mapping(**req)
            return _ok(
                updated=True,
                uuid=resp.get("UUID"),
                function_arn=resp.get("FunctionArn"),
                event_source_arn=resp.get("EventSourceArn"),
                state=resp.get("State"),
                batch_size=resp.get("BatchSize"),
                maximum_batching_window_seconds=resp.get("MaximumBatchingWindowInSeconds"),
            )

        if action == "delete_event_source_mapping":
            if not uuid:
                return _err("uuid is required")
            if not confirm:
                return _err(
                    "Refusing to delete event source mapping without confirm=True",
                    error_type="ConfirmationRequired",
                    hint="Deleting an event source mapping stops the trigger. Pass confirm=True to proceed.",
                )
            resp = client.delete_event_source_mapping(UUID=uuid)
            return _ok(deleted=True, uuid=resp.get("UUID"), state=resp.get("State"))

        if action == "create_function_zip":
            chk = _check_name(function_name)
            if chk:
                return chk
            role_meta = None
            if not role_arn:
                if _role_allowlist() is not None:
                    return _err(
                        "role_arn is required when STRANDS_PACK_LAMBDA_ROLE_ALLOWLIST is set",
                        error_type="RoleRequired",
                    )
                if not auto_create_role or not _auto_role_enabled():
                    return _err(
                        "role_arn is required (or enable auto_create_role + STRANDS_PACK_LAMBDA_ALLOW_AUTO_ROLE_CREATE=true for logs-only role)",
                        error_type="RoleRequired",
                    )
                role_meta = _ensure_basic_execution_role(function_name)
                role_arn = role_meta["role_arn"]
            else:
                role_chk = _check_role_allowed(role_arn)
                if role_chk:
                    return role_chk

            if not handler or not runtime or not zip_path:
                return _err("handler, runtime, and zip_path are required")

            p = Path(zip_path).expanduser()
            if not p.exists():
                return _err(f"zip_path not found: {zip_path}", error_type="FileNotFoundError")

            zip_bytes = p.read_bytes()
            create_args: Dict[str, Any] = {
                "FunctionName": function_name,
                "Role": role_arn,
                "Runtime": runtime,
                "Handler": handler,
                "Code": {"ZipFile": zip_bytes},
                "Timeout": timeout,
                "MemorySize": memory,
                "Publish": publish,
                "Description": description or "Created by strands-pack",
                "Tags": aws_tags_dict(component="lambda", tags=tags),
            }
            if environment:
                create_args["Environment"] = {"Variables": environment}

            resp = client.create_function(**create_args)
            return _ok(
                function_name=function_name,
                created=True,
                arn=resp.get("FunctionArn"),
                role_arn=role_arn,
                role_auto_created=bool(role_meta["created"]) if role_meta else False,
                role_name=role_meta["role_name"] if role_meta else None,
            )

        if action == "update_function_code_zip":
            chk = _check_name(function_name)
            if chk:
                return chk
            if not zip_path:
                return _err("zip_path is required")
            p = Path(zip_path).expanduser()
            if not p.exists():
                return _err(f"zip_path not found: {zip_path}", error_type="FileNotFoundError")
            zip_bytes = p.read_bytes()
            resp = client.update_function_code(FunctionName=function_name, ZipFile=zip_bytes, Publish=publish)
            return _ok(function_name=function_name, updated=True, version=resp.get("Version"))

        if action == "update_function_config":
            chk = _check_name(function_name)
            if chk:
                return chk
            update_args: Dict[str, Any] = {"FunctionName": function_name}
            if timeout:
                update_args["Timeout"] = timeout
            if memory:
                update_args["MemorySize"] = memory
            if description is not None:
                update_args["Description"] = description
            if environment is not None:
                update_args["Environment"] = {"Variables": environment}

            resp = client.update_function_configuration(**update_args)
            return _ok(
                function_name=function_name,
                updated=True,
                timeout=resp.get("Timeout"),
                memory=resp.get("MemorySize"),
                description=resp.get("Description"),
            )

        if action == "invoke":
            chk = _check_name(function_name)
            if chk:
                return chk
            invoke_payload = payload or {}
            if not isinstance(invoke_payload, dict):
                return _err("payload must be a dict")
            resp = client.invoke(
                FunctionName=function_name,
                InvocationType=invocation_type,
                Payload=json.dumps(invoke_payload).encode("utf-8"),
            )
            # Do not stream arbitrary large payloads back; cap size.
            out_bytes = b""
            if resp.get("Payload") is not None and invocation_type == "RequestResponse":
                out_bytes = resp["Payload"].read(20000)
            out_text = out_bytes.decode("utf-8", errors="replace") if out_bytes else ""
            return _ok(function_name=function_name, status_code=resp.get("StatusCode"), response=out_text)

        return _err(
            f"Unknown action: {action}",
            error_type="InvalidAction",
            available_actions=[
                "list_functions",
                "get_function",
                "delete_function",
                "list_event_source_mappings",
                "create_event_source_mapping",
                "update_event_source_mapping",
                "delete_event_source_mapping",
                "build_zip",
                "create_function_zip",
                "update_function_code_zip",
                "update_function_config",
                "invoke",
            ],
        )
    except Exception as e:
        return _err(str(e), error_type=type(e).__name__, action=action)
