"""
AWS Secrets Manager Tool (Safe-by-default)

This tool is intentionally designed to be *safe by default* when used with LLM agents:
it does NOT return secret values in tool outputs, because tool outputs are typically
sent back to the model/provider.

Instead, it can:
- list secrets metadata
- fetch a secret from AWS Secrets Manager and return an *opaque reference* (secret_ref)
  stored only in-process memory
- allow other code/tools to resolve the secret by secret_ref *internally* (not exposed as a tool action)

Requires:
    pip install strands-pack[aws]

Supported actions
-----------------
- list_secrets
    List secrets (metadata only).

- describe_secret
    Get detailed metadata for a secret (does NOT return values).

- tag_secret
    Add/remove tags on a secret (does NOT return values).

- get_secret_ref
    Fetch a secret value from AWS Secrets Manager and store it in an in-memory cache.
    Returns: secret_ref (opaque), plus safe metadata (name/arn/version_id/length).

- delete_secret
    Delete a secret (destructive; requires confirm=True).
    By default, this only allows deleting secrets tagged `managed-by=strands-pack`.

- delete_secret_ref
    Delete an in-memory cached secret reference.

Security notes
--------------
Tool outputs are visible to the model. Returning secrets would leak them to your LLM provider.
This tool does not implement a "reveal" action on purpose.
"""

from __future__ import annotations

import base64
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

from strands import tool

try:
    import boto3

    HAS_BOTO3 = True
except ImportError:  # pragma: no cover
    boto3 = None
    HAS_BOTO3 = False


@dataclass
class _CachedSecret:
    created_at: float
    secret_id: str
    version_id: Optional[str]
    secret_bytes: bytes


_SECRET_CACHE: Dict[str, _CachedSecret] = {}

# Default TTL for in-memory secret refs. Can be overridden per call.
DEFAULT_TTL_SECONDS = 15 * 60


def _get_client():
    if not HAS_BOTO3:
        raise ImportError("boto3 not installed. Run: pip install strands-pack[aws]")
    return boto3.client("secretsmanager")


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


def _purge_expired():
    now = time.time()
    expired = [k for k, v in _SECRET_CACHE.items() if now - v.created_at > DEFAULT_TTL_SECONDS]
    for k in expired:
        _SECRET_CACHE.pop(k, None)


def resolve_secret_ref(secret_ref: str) -> bytes:
    """
    INTERNAL helper (not a tool action):
    Resolve a secret_ref into raw bytes for other Python code/tools.
    """
    _purge_expired()
    entry = _SECRET_CACHE.get(secret_ref)
    if not entry:
        raise KeyError("secret_ref not found (or expired)")
    return entry.secret_bytes


@tool
def secrets_manager(
    action: str,
    secret_id: Optional[str] = None,
    secret_ref: Optional[str] = None,
    max_results: int = 50,
    ttl_seconds: Optional[int] = None,
    add_tags: Optional[Dict[str, str]] = None,
    remove_tag_keys: Optional[list[str]] = None,
    confirm: bool = False,
    recovery_window_days: int = 7,
    force_delete_without_recovery: bool = False,
    allow_unmanaged: bool = False,
) -> Dict[str, Any]:
    """
    Safe-by-default AWS Secrets Manager tool.

    Args:
        action: The action to perform. One of:
            - "list_secrets": List secrets metadata (does NOT return values).
            - "describe_secret": Get secret metadata (does NOT return values).
            - "tag_secret": Add/remove tags on a secret (does NOT return values).
            - "get_secret_ref": Fetch secret and return opaque reference (safe).
            - "delete_secret": Delete a secret (destructive; requires confirm=True).
            - "delete_secret_ref": Remove cached secret reference.
        secret_id: Secret name or ARN (for get_secret_ref).
        secret_ref: Opaque reference returned by get_secret_ref (for delete_secret_ref).
        max_results: Maximum secrets to list (default 50, for list_secrets).
        ttl_seconds: Time-to-live for cached secret ref (for get_secret_ref).
        add_tags: Tags to add/update on the secret (for tag_secret).
        remove_tag_keys: Tag keys to remove from the secret (for tag_secret).
        confirm: Required for delete_secret.
        recovery_window_days: Recovery window (7-30) for delete_secret. Ignored if force_delete_without_recovery=True.
        force_delete_without_recovery: If True, deletes immediately (dangerous).
        allow_unmanaged: If False (default), delete_secret is only allowed for secrets tagged managed-by=strands-pack.

    Returns:
        dict with success status and action-specific data.
        Note: Secret values are NEVER returned in tool output.

    Examples:
        >>> secrets_manager(action="list_secrets")
        >>> secrets_manager(action="get_secret_ref", secret_id="my-secret")
        >>> secrets_manager(action="delete_secret_ref", secret_ref="smref_abc123")
    """
    action = (action or "").strip()

    if action == "list_secrets":
        try:
            client = _get_client()
            resp = client.list_secrets(MaxResults=int(max_results))
            # Only return metadata-safe fields
            secrets = []
            for s in resp.get("SecretList", []) or []:
                secrets.append(
                    {
                        "arn": s.get("ARN"),
                        "name": s.get("Name"),
                        "description": s.get("Description"),
                        "last_changed_date": s.get("LastChangedDate").isoformat() if s.get("LastChangedDate") else None,
                        "tags": s.get("Tags"),
                    }
                )
            return _ok(secrets=secrets, count=len(secrets), next_token=resp.get("NextToken"))
        except Exception as e:
            return _err(str(e), error_type=type(e).__name__, action=action)

    if action == "describe_secret":
        if not secret_id:
            return _err("secret_id is required (secret name or ARN)")
        try:
            client = _get_client()
            resp = client.describe_secret(SecretId=secret_id)
            # Metadata only; never return values.
            return _ok(
                secret_id=secret_id,
                arn=resp.get("ARN"),
                name=resp.get("Name"),
                description=resp.get("Description"),
                kms_key_id=resp.get("KmsKeyId"),
                created_date=resp.get("CreatedDate").isoformat() if resp.get("CreatedDate") else None,
                last_changed_date=resp.get("LastChangedDate").isoformat() if resp.get("LastChangedDate") else None,
                last_accessed_date=resp.get("LastAccessedDate").isoformat() if resp.get("LastAccessedDate") else None,
                deleted_date=resp.get("DeletedDate").isoformat() if resp.get("DeletedDate") else None,
                rotation_enabled=bool(resp.get("RotationEnabled")),
                rotation_lambda_arn=resp.get("RotationLambdaARN"),
                rotation_rules=resp.get("RotationRules"),
                tags=resp.get("Tags") or [],
            )
        except Exception as e:
            return _err(str(e), error_type=type(e).__name__, action=action)

    if action == "tag_secret":
        if not secret_id:
            return _err("secret_id is required (secret name or ARN)")
        if not add_tags and not remove_tag_keys:
            return _err("add_tags or remove_tag_keys is required")
        try:
            client = _get_client()
            if add_tags:
                if not isinstance(add_tags, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in add_tags.items()):
                    return _err("add_tags must be a dict[str, str]", error_type="InvalidParameterValue")
                client.tag_resource(
                    SecretId=secret_id,
                    Tags=[{"Key": k, "Value": v} for k, v in add_tags.items()],
                )
            if remove_tag_keys:
                if not isinstance(remove_tag_keys, list) or not all(isinstance(k, str) and k for k in remove_tag_keys):
                    return _err("remove_tag_keys must be a list[str]", error_type="InvalidParameterValue")
                client.untag_resource(SecretId=secret_id, TagKeys=remove_tag_keys)
            return _ok(secret_id=secret_id, tagged=bool(add_tags), untagged=bool(remove_tag_keys))
        except Exception as e:
            return _err(str(e), error_type=type(e).__name__, action=action)

    if action == "get_secret_ref":
        if not secret_id:
            return _err("secret_id is required (secret name or ARN)")

        if ttl_seconds is not None:
            try:
                global DEFAULT_TTL_SECONDS
                DEFAULT_TTL_SECONDS = int(ttl_seconds)
            except Exception:
                return _err("ttl_seconds must be an integer")

        try:
            client = _get_client()
            resp = client.get_secret_value(SecretId=secret_id)

            secret_bytes: bytes
            if "SecretBinary" in resp and resp["SecretBinary"] is not None:
                secret_bytes = resp["SecretBinary"]
                if isinstance(secret_bytes, str):
                    secret_bytes = base64.b64decode(secret_bytes)
            else:
                secret_str = resp.get("SecretString", "")
                secret_bytes = secret_str.encode("utf-8")

            ref = f"smref_{uuid.uuid4().hex}"
            _SECRET_CACHE[ref] = _CachedSecret(
                created_at=time.time(),
                secret_id=str(secret_id),
                version_id=resp.get("VersionId"),
                secret_bytes=secret_bytes,
            )

            return _ok(
                secret_ref=ref,
                secret_id=str(secret_id),
                version_id=resp.get("VersionId"),
                byte_length=len(secret_bytes),
                ttl_seconds=DEFAULT_TTL_SECONDS,
                note="Secret value not returned. Use secret_ref internally from Python code.",
            )
        except Exception as e:
            return _err(str(e), error_type=type(e).__name__, action=action)

    if action == "delete_secret":
        if not secret_id:
            return _err("secret_id is required (secret name or ARN)")
        if not confirm:
            return _err(
                "Refusing to delete secret without confirm=True",
                error_type="ConfirmationRequired",
                hint="Secret deletion is destructive. Pass confirm=True to proceed.",
            )
        if force_delete_without_recovery and not allow_unmanaged:
            # Extra guard: immediate deletion only allowed when caller explicitly opts in to unmanaged deletion.
            return _err(
                "Refusing force_delete_without_recovery unless allow_unmanaged=True",
                error_type="UnsafeOperation",
                hint="Immediate deletion is dangerous. If you truly want this, set allow_unmanaged=True and confirm=True.",
            )
        try:
            client = _get_client()
            # Guardrail: only delete secrets managed by this library unless explicitly allowed.
            if not allow_unmanaged:
                meta = client.describe_secret(SecretId=secret_id)
                tags = meta.get("Tags") or []
                managed = any(t.get("Key") == "managed-by" and t.get("Value") == "strands-pack" for t in tags)
                if not managed:
                    return _err(
                        "Refusing to delete secret not tagged managed-by=strands-pack",
                        error_type="NotManaged",
                        secret_id=secret_id,
                        hint="To delete unmanaged secrets, set allow_unmanaged=True (still requires confirm=True).",
                    )

            req: Dict[str, Any] = {"SecretId": secret_id}
            if force_delete_without_recovery:
                req["ForceDeleteWithoutRecovery"] = True
            else:
                # AWS allows 7-30 days; keep safe defaults.
                days = max(7, min(int(recovery_window_days), 30))
                req["RecoveryWindowInDays"] = days
            resp = client.delete_secret(**req)
            return _ok(
                secret_id=secret_id,
                arn=resp.get("ARN"),
                name=resp.get("Name"),
                deletion_date=resp.get("DeletionDate").isoformat() if resp.get("DeletionDate") else None,
                force_delete_without_recovery=bool(force_delete_without_recovery),
                recovery_window_days=req.get("RecoveryWindowInDays"),
                deleted=True,
            )
        except Exception as e:
            return _err(str(e), error_type=type(e).__name__, action=action)

    if action == "delete_secret_ref":
        if not secret_ref:
            return _err("secret_ref is required")
        removed = _SECRET_CACHE.pop(secret_ref, None) is not None
        return _ok(secret_ref=secret_ref, deleted=removed)

    return _err(
        f"Unknown action: {action}",
        error_type="InvalidAction",
        available_actions=["list_secrets", "describe_secret", "tag_secret", "get_secret_ref", "delete_secret", "delete_secret_ref"],
    )


