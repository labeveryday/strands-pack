"""
S3 Tool

Manage Amazon S3 buckets and objects.

Requires:
    pip install strands-pack[aws]

Supported actions
-----------------
- list_buckets
- list_objects
    Parameters: bucket (required), prefix (optional), max_keys (default 100)
- head_object
    Parameters: bucket (required), key (required)
- download_file
    Parameters: bucket (required), key (required), output_path (required)
- upload_file
    Parameters: bucket (required), key (required), file_path (required), content_type (optional)
- put_text
    Parameters: bucket (required), key (required), text (required), content_type (default "text/plain")
- get_text
    Parameters: bucket (required), key (required), max_bytes (default 200000)
- copy_object
    Parameters: source_bucket (required), source_key (required), bucket (required), key (required)
- add_lambda_trigger
    Parameters: bucket (required), lambda_arn (required), events (optional), prefix (optional), suffix (optional)
  Notes: Configures bucket notifications AND adds Lambda invoke permission for S3 (Option A).
- delete_object
    Parameters: bucket (required), key (required)
- create_bucket
    Parameters: bucket (required), region (optional)
- delete_bucket
    Parameters: bucket (required), confirm (required True)
- presign_url
    Parameters: bucket (required), key (required), expires_in (default 3600), method ("get"|"put")

Notes:
  - This tool avoids returning raw binary data directly. Downloads go to disk.
"""

from __future__ import annotations

import os
from pathlib import Path
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
    return boto3.client("s3")


def _get_lambda():
    if not HAS_BOTO3:
        raise ImportError("boto3 not installed. Run: pip install strands-pack[aws]")
    return boto3.client("lambda")


def _lambda_prefix() -> str:
    return os.getenv("STRANDS_PACK_LAMBDA_PREFIX", "agent-")


def _extract_lambda_name(function_name_or_arn: str) -> str:
    # arn:aws:lambda:REGION:ACCOUNT:function:NAME[:QUALIFIER]
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


@tool
def s3(
    action: str,
    bucket: Optional[str] = None,
    key: Optional[str] = None,
    source_bucket: Optional[str] = None,
    source_key: Optional[str] = None,
    prefix: Optional[str] = None,
    max_keys: int = 100,
    output_path: Optional[str] = None,
    file_path: Optional[str] = None,
    text: Optional[str] = None,
    content_type: Optional[str] = None,
    max_bytes: int = 200000,
    expires_in: int = 3600,
    method: str = "get",
    region: Optional[str] = None,
    confirm: bool = False,
    lambda_arn: Optional[str] = None,
    events: Optional[List[str]] = None,
    suffix: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Manage Amazon S3 buckets and objects.

    Args:
        action: The action to perform. One of:
            - "list_buckets": List all S3 buckets in the account.
            - "list_objects": List objects in a bucket.
            - "head_object": Get object metadata (no download).
            - "download_file": Download an object to a local file.
            - "upload_file": Upload a local file to S3.
            - "put_text": Write text content directly to S3.
            - "get_text": Read text content from S3.
            - "copy_object": Copy an object to another key/bucket.
            - "delete_object": Delete an object from S3.
            - "create_bucket": Create a new bucket.
            - "delete_bucket": Delete an empty bucket (requires confirm=True).
            - "presign_url": Generate a presigned URL for temporary access.
        bucket: S3 bucket name (required for most actions).
        key: Object key/path in the bucket.
        source_bucket: Source bucket (for copy_object).
        source_key: Source key (for copy_object).
        prefix: Filter prefix for list_objects.
        max_keys: Maximum objects to return for list_objects (default 100).
        output_path: Local file path for download_file.
        file_path: Local file path for upload_file.
        text: Text content for put_text.
        content_type: MIME type for uploads (e.g., "text/plain", "application/json").
        max_bytes: Maximum bytes to read for get_text (default 200000).
        expires_in: Presigned URL expiration in seconds (default 3600).
        method: Presigned URL method - "get" or "put" (default "get").
        region: AWS region for create_bucket (optional).
        confirm: Required for destructive actions like delete_bucket.
        lambda_arn: Lambda function ARN (for add_lambda_trigger).
        events: S3 event types for add_lambda_trigger (default ["s3:ObjectCreated:*"]).
        suffix: Optional suffix filter for add_lambda_trigger.

    Returns:
        dict with success status and action-specific data

    Examples:
        >>> s3(action="list_buckets")
        >>> s3(action="list_objects", bucket="my-bucket", prefix="data/")
        >>> s3(action="upload_file", bucket="my-bucket", key="file.txt", file_path="./local.txt")
        >>> s3(action="get_text", bucket="my-bucket", key="config.json")
    """
    action = (action or "").strip()

    try:
        client = _get_client()
    except Exception as e:
        return _err(str(e), error_type=type(e).__name__, action=action)

    try:
        if action == "list_buckets":
            resp = client.list_buckets()
            buckets = [{"name": b.get("Name"), "created": b.get("CreationDate").isoformat() if b.get("CreationDate") else None} for b in resp.get("Buckets", [])]
            return _ok(buckets=buckets, count=len(buckets))

        if action == "list_objects":
            if not bucket:
                return _err("bucket is required")
            req: Dict[str, Any] = {"Bucket": bucket, "MaxKeys": max_keys}
            if prefix:
                req["Prefix"] = prefix
            resp = client.list_objects_v2(**req)
            contents = resp.get("Contents", []) or []
            objects = [
                {
                    "key": o.get("Key"),
                    "size": o.get("Size"),
                    "etag": o.get("ETag"),
                    "last_modified": o.get("LastModified").isoformat() if o.get("LastModified") else None,
                }
                for o in contents
            ]
            return _ok(bucket=bucket, prefix=prefix, objects=objects, count=len(objects), is_truncated=resp.get("IsTruncated", False))

        if action == "head_object":
            if not bucket or not key:
                return _err("bucket and key are required")
            resp = client.head_object(Bucket=bucket, Key=key)
            # Keep response small and JSON-friendly.
            return _ok(
                bucket=bucket,
                key=key,
                size=resp.get("ContentLength"),
                content_type=resp.get("ContentType"),
                etag=resp.get("ETag"),
                last_modified=resp.get("LastModified").isoformat() if resp.get("LastModified") else None,
                metadata=resp.get("Metadata") or {},
                storage_class=resp.get("StorageClass"),
                version_id=resp.get("VersionId"),
            )

        if action == "download_file":
            if not bucket or not key or not output_path:
                return _err("bucket, key, and output_path are required")
            path = Path(output_path).expanduser()
            path.parent.mkdir(parents=True, exist_ok=True)
            client.download_file(bucket, key, str(path))
            return _ok(bucket=bucket, key=key, output_path=str(path))

        if action == "upload_file":
            if not bucket or not key or not file_path:
                return _err("bucket, key, and file_path are required")
            p = Path(file_path).expanduser()
            if not p.exists():
                return _err(f"file_path not found: {file_path}", error_type="FileNotFoundError")
            extra = {}
            if content_type:
                extra["ContentType"] = content_type
            client.upload_file(str(p), bucket, key, ExtraArgs=extra or None)
            return _ok(bucket=bucket, key=key, file_path=str(p))

        if action == "put_text":
            if not bucket or not key or text is None:
                return _err("bucket, key, and text are required")
            ct = content_type or "text/plain"
            client.put_object(Bucket=bucket, Key=key, Body=str(text).encode("utf-8"), ContentType=ct)
            return _ok(bucket=bucket, key=key, bytes=len(str(text).encode('utf-8')))

        if action == "get_text":
            if not bucket or not key:
                return _err("bucket and key are required")
            resp = client.get_object(Bucket=bucket, Key=key)
            body = resp["Body"].read(max_bytes + 1)
            truncated = len(body) > max_bytes
            if truncated:
                body = body[:max_bytes]
            text_content = body.decode("utf-8", errors="replace")
            return _ok(bucket=bucket, key=key, text=text_content, truncated=truncated, bytes=len(body))

        if action == "copy_object":
            if not source_bucket or not source_key or not bucket or not key:
                return _err("source_bucket, source_key, bucket, and key are required")
            copy_source = {"Bucket": source_bucket, "Key": source_key}
            client.copy_object(Bucket=bucket, Key=key, CopySource=copy_source)
            return _ok(
                source_bucket=source_bucket,
                source_key=source_key,
                bucket=bucket,
                key=key,
                copied=True,
            )

        if action == "add_lambda_trigger":
            if not bucket or not lambda_arn:
                return _err("bucket and lambda_arn are required")
            chk = _check_lambda_allowed(lambda_arn)
            if chk:
                return chk

            # 1) Add permission so S3 can invoke Lambda
            lam = _get_lambda()
            # SourceArn for bucket: arn:aws:s3:::bucket-name
            source_arn = f"arn:aws:s3:::{bucket}"
            statement_id = f"s3-invoke-{bucket}"
            try:
                lam.add_permission(
                    FunctionName=lambda_arn,
                    StatementId=statement_id,
                    Action="lambda:InvokeFunction",
                    Principal="s3.amazonaws.com",
                    SourceArn=source_arn,
                )
            except Exception as e:
                if "ResourceConflictException" not in str(e):
                    raise

            # 2) Configure bucket notification to invoke the Lambda
            ev = events or ["s3:ObjectCreated:*"]
            notif: Dict[str, Any] = {
                "LambdaFunctionConfigurations": [
                    {
                        "LambdaFunctionArn": lambda_arn,
                        "Events": ev,
                    }
                ]
            }
            if prefix or suffix:
                rules = []
                if prefix:
                    rules.append({"Name": "prefix", "Value": prefix})
                if suffix:
                    rules.append({"Name": "suffix", "Value": suffix})
                notif["LambdaFunctionConfigurations"][0]["Filter"] = {
                    "Key": {"FilterRules": rules}
                }

            client.put_bucket_notification_configuration(
                Bucket=bucket,
                NotificationConfiguration=notif,
            )

            return _ok(
                bucket=bucket,
                lambda_arn=lambda_arn,
                events=ev,
                prefix=prefix,
                suffix=suffix,
                configured=True,
                permission={"statement_id": statement_id, "source_arn": source_arn},
            )

        if action == "delete_object":
            if not bucket or not key:
                return _err("bucket and key are required")
            client.delete_object(Bucket=bucket, Key=key)
            return _ok(bucket=bucket, key=key, deleted=True)

        if action == "create_bucket":
            if not bucket:
                return _err("bucket is required")
            # us-east-1 uses no LocationConstraint
            if region and region != "us-east-1":
                client.create_bucket(
                    Bucket=bucket,
                    CreateBucketConfiguration={"LocationConstraint": region},
                )
            else:
                client.create_bucket(Bucket=bucket)
            try:
                client.put_bucket_tagging(
                    Bucket=bucket,
                    Tagging={"TagSet": aws_tags_list(component="s3", tags=tags)},
                )
            except Exception as e:
                return _err(
                    f"Bucket created but tagging failed: {e}",
                    error_type="TaggingFailed",
                    bucket=bucket,
                    hint="Ensure you have s3:PutBucketTagging permissions.",
                )
            return _ok(bucket=bucket, created=True, region=region or "us-east-1", tagged=True)

        if action == "delete_bucket":
            if not bucket:
                return _err("bucket is required")
            if not confirm:
                return _err(
                    "Refusing to delete bucket without confirm=True",
                    error_type="ConfirmationRequired",
                    hint="Bucket deletion is irreversible and requires the bucket to be empty.",
                )
            client.delete_bucket(Bucket=bucket)
            return _ok(bucket=bucket, deleted=True)

        if action == "presign_url":
            if not bucket or not key:
                return _err("bucket and key are required")
            m = (method or "get").lower()
            if m not in ("get", "put"):
                return _err("method must be 'get' or 'put'")
            client_method = "get_object" if m == "get" else "put_object"
            url = client.generate_presigned_url(
                ClientMethod=client_method,
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=expires_in,
            )
            return _ok(bucket=bucket, key=key, url=url, expires_in=expires_in, method=m)

        return _err(
            f"Unknown action: {action}",
            error_type="InvalidAction",
            available_actions=[
                "list_buckets",
                "list_objects",
                "head_object",
                "download_file",
                "upload_file",
                "put_text",
                "get_text",
                "copy_object",
                "add_lambda_trigger",
                "delete_object",
                "create_bucket",
                "delete_bucket",
                "presign_url",
            ],
        )

    except Exception as e:
        return _err(str(e), error_type=type(e).__name__, action=action)


