"""
DynamoDB Tool (agent-safe defaults)

Use DynamoDB as durable state for agents: job queues, run history, profiles, idempotency keys.

Do you need to create the table first?
-------------------------------------
Yes — DynamoDB operations require an existing table. To make this easy, this tool includes
`create_jobs_table` which provisions a recommended schema for durable jobs.

Security model
--------------
Tool outputs are visible to the model. This tool implements guardrails:
- Optional allowlist for table names (env var `STRANDS_PACK_DDB_TABLE_ALLOWLIST`, comma-separated).
- Limits on scans/queries (max items) and disallows unbounded scans by default.
- Basic redaction of sensitive field names in returned items.

Requires:
    pip install strands-pack[aws]

Recommended durable jobs pattern (single user, multiple agents)
--------------------------------------------------------------
One shared table, partitioned by "namespace" + "job_id".

Jobs table schema created by `create_jobs_table`:
  - PK:  pk  (string)  e.g. "jobs#default"
  - SK:  sk  (string)  e.g. "job#<job_id>"
  - GSI1 (gsi1pk, gsi1sk) for listing by status + due time:
      gsi1pk: "status#<status>" (e.g. status#PENDING)
      gsi1sk: "<due_at>#<job_id>" (due_at is ISO8601 or epoch string)

Actions
-------
- create_jobs_table
- put_item / get_item / update_item / delete_item
- query_jobs_by_status
- describe_table / delete_table (confirm)
- batch_write_item / batch_get_item
- scan (capped) / query (generic)
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

from strands import tool

from strands_pack.aws_tags import aws_tags_list
try:
    import boto3

    HAS_BOTO3 = True
except ImportError:  # pragma: no cover
    boto3 = None
    HAS_BOTO3 = False


SENSITIVE_KEY_PARTS = ("secret", "token", "password", "api_key", "apikey", "access_key", "private", "credential")


def _get_client():
    if not HAS_BOTO3:
        raise ImportError("boto3 not installed. Run: pip install strands-pack[aws]")
    return boto3.client("dynamodb")


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


def _allowlist() -> Optional[List[str]]:
    raw = os.getenv("STRANDS_PACK_DDB_TABLE_ALLOWLIST")
    if not raw:
        return None
    return [x.strip() for x in raw.split(",") if x.strip()]


def _check_table_allowed(table_name: str) -> Optional[Dict[str, Any]]:
    allow = _allowlist()
    if allow is None:
        return None
    if table_name in allow:
        return None
    return _err(
        f"Table not allowed: {table_name}. Set STRANDS_PACK_DDB_TABLE_ALLOWLIST to allow it.",
        error_type="TableNotAllowed",
        allowed_tables=allow,
    )


def _redact_item(item: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(item, dict):
        return item
    out: Dict[str, Any] = {}
    for k, v in item.items():
        kl = str(k).lower()
        if any(p in kl for p in SENSITIVE_KEY_PARTS):
            out[k] = "***REDACTED***"
        else:
            out[k] = v
    return out


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _action_create_jobs_table(client, **kwargs) -> Dict[str, Any]:
    table_name = kwargs.get("table_name")
    if not table_name:
        return _err("table_name is required")
    chk = _check_table_allowed(table_name)
    if chk:
        return chk

    billing_mode = (kwargs.get("billing_mode", "PAY_PER_REQUEST") or "PAY_PER_REQUEST").upper()
    if billing_mode not in ("PAY_PER_REQUEST", "PROVISIONED"):
        return _err("billing_mode must be PAY_PER_REQUEST or PROVISIONED")

    attribute_definitions = [
        {"AttributeName": "pk", "AttributeType": "S"},
        {"AttributeName": "sk", "AttributeType": "S"},
        {"AttributeName": "gsi1pk", "AttributeType": "S"},
        {"AttributeName": "gsi1sk", "AttributeType": "S"},
    ]

    key_schema = [
        {"AttributeName": "pk", "KeyType": "HASH"},
        {"AttributeName": "sk", "KeyType": "RANGE"},
    ]

    gsi = [
        {
            "IndexName": "gsi1",
            "KeySchema": [
                {"AttributeName": "gsi1pk", "KeyType": "HASH"},
                {"AttributeName": "gsi1sk", "KeyType": "RANGE"},
            ],
            "Projection": {"ProjectionType": "ALL"},
        }
    ]

    req: Dict[str, Any] = {
        "TableName": table_name,
        "AttributeDefinitions": attribute_definitions,
        "KeySchema": key_schema,
        "GlobalSecondaryIndexes": gsi,
        "BillingMode": billing_mode,
        "Tags": aws_tags_list(component="dynamodb", tags=kwargs.get("tags")),
    }

    if billing_mode == "PROVISIONED":
        req["ProvisionedThroughput"] = {
            "ReadCapacityUnits": int(kwargs.get("read_capacity", 5)),
            "WriteCapacityUnits": int(kwargs.get("write_capacity", 5)),
        }
        req["GlobalSecondaryIndexes"][0]["ProvisionedThroughput"] = {
            "ReadCapacityUnits": int(kwargs.get("gsi_read_capacity", 5)),
            "WriteCapacityUnits": int(kwargs.get("gsi_write_capacity", 5)),
        }

    resp = client.create_table(**req)
    return _ok(table_name=table_name, status=resp.get("TableDescription", {}).get("TableStatus"), response=resp)


def _action_put_item(client, **kwargs) -> Dict[str, Any]:
    table_name = kwargs.get("table_name")
    item = kwargs.get("item")
    if not table_name:
        return _err("table_name is required")
    if not isinstance(item, dict) or not item:
        return _err("item is required (dict)")
    chk = _check_table_allowed(table_name)
    if chk:
        return chk
    # Encourage idempotency: allow optional condition_expression + expression_values
    req: Dict[str, Any] = {"TableName": table_name, "Item": item}
    if kwargs.get("condition_expression"):
        req["ConditionExpression"] = kwargs["condition_expression"]
    if kwargs.get("expression_attribute_values"):
        req["ExpressionAttributeValues"] = kwargs["expression_attribute_values"]
    if kwargs.get("expression_attribute_names"):
        req["ExpressionAttributeNames"] = kwargs["expression_attribute_names"]
    client.put_item(**req)
    return _ok(table_name=table_name, written=True)


def _action_get_item(client, **kwargs) -> Dict[str, Any]:
    table_name = kwargs.get("table_name")
    key = kwargs.get("key")
    if not table_name:
        return _err("table_name is required")
    if not isinstance(key, dict) or not key:
        return _err("key is required (dict)")
    chk = _check_table_allowed(table_name)
    if chk:
        return chk
    req: Dict[str, Any] = {"TableName": table_name, "Key": key, "ConsistentRead": bool(kwargs.get("consistent_read", False))}
    if kwargs.get("projection_expression"):
        req["ProjectionExpression"] = kwargs["projection_expression"]
    if kwargs.get("expression_attribute_names"):
        req["ExpressionAttributeNames"] = kwargs["expression_attribute_names"]
    resp = client.get_item(**req)
    item = resp.get("Item")
    if item is None:
        return _ok(table_name=table_name, item=None, found=False)
    return _ok(table_name=table_name, item=_redact_item(item), found=True)


def _action_update_item(client, **kwargs) -> Dict[str, Any]:
    table_name = kwargs.get("table_name")
    key = kwargs.get("key")
    update_expression = kwargs.get("update_expression")
    if not table_name:
        return _err("table_name is required")
    if not isinstance(key, dict) or not key:
        return _err("key is required (dict)")
    if not update_expression:
        return _err("update_expression is required")
    chk = _check_table_allowed(table_name)
    if chk:
        return chk

    req: Dict[str, Any] = {
        "TableName": table_name,
        "Key": key,
        "UpdateExpression": update_expression,
        "ReturnValues": kwargs.get("return_values", "ALL_NEW"),
    }
    if kwargs.get("condition_expression"):
        req["ConditionExpression"] = kwargs["condition_expression"]
    if kwargs.get("expression_attribute_values"):
        req["ExpressionAttributeValues"] = kwargs["expression_attribute_values"]
    if kwargs.get("expression_attribute_names"):
        req["ExpressionAttributeNames"] = kwargs["expression_attribute_names"]
    resp = client.update_item(**req)
    attrs = resp.get("Attributes")
    return _ok(table_name=table_name, attributes=_redact_item(attrs) if isinstance(attrs, dict) else attrs)


def _action_delete_item(client, **kwargs) -> Dict[str, Any]:
    table_name = kwargs.get("table_name")
    key = kwargs.get("key")
    if not table_name:
        return _err("table_name is required")
    if not isinstance(key, dict) or not key:
        return _err("key is required (dict)")
    chk = _check_table_allowed(table_name)
    if chk:
        return chk
    req: Dict[str, Any] = {"TableName": table_name, "Key": key}
    if kwargs.get("condition_expression"):
        req["ConditionExpression"] = kwargs["condition_expression"]
    client.delete_item(**req)
    return _ok(table_name=table_name, deleted=True)


def _action_query_jobs_by_status(client, **kwargs) -> Dict[str, Any]:
    """
    Opinionated query for the jobs table created by create_jobs_table.
    Reads via GSI1 by status and optional due_at upper bound (prefix).
    """
    table_name = kwargs.get("table_name")
    namespace = kwargs.get("namespace", "default")
    status = (kwargs.get("status") or "PENDING").upper()
    limit = int(kwargs.get("limit", 25))
    if limit > 100:
        limit = 100
    if not table_name:
        return _err("table_name is required")
    chk = _check_table_allowed(table_name)
    if chk:
        return chk

    gsi1pk = f"status#{status}"
    due_before = kwargs.get("due_before")  # string prefix (ISO) recommended

    expr_names = {"#pk": "gsi1pk"}
    expr_values: Dict[str, Any] = {":pk": {"S": gsi1pk}}
    key_cond = "#pk = :pk"

    resp = client.query(
        TableName=table_name,
        IndexName="gsi1",
        KeyConditionExpression=key_cond,
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_values,
        Limit=limit,
        ScanIndexForward=True,
    )
    items = resp.get("Items", []) or []
    if due_before:
        filtered = []
        for it in items:
            sk = it.get("gsi1sk", {}).get("S", "")
            due = sk.split("#", 1)[0] if "#" in sk else sk
            if due and due <= str(due_before):
                filtered.append(it)
        items = filtered

    return _ok(
        table_name=table_name,
        namespace=namespace,
        status=status,
        jobs=[_redact_item(i) for i in items],
        count=len(items),
        note="Uses GSI1; due_before filtering is approximate and limited by query limit.",
    )


def _action_describe_table(client, **kwargs) -> Dict[str, Any]:
    table_name = kwargs.get("table_name")
    if not table_name:
        return _err("table_name is required")
    chk = _check_table_allowed(table_name)
    if chk:
        return chk
    resp = client.describe_table(TableName=table_name)
    td = resp.get("Table", {}) or {}
    return _ok(
        action="describe_table",
        table_name=table_name,
        status=td.get("TableStatus"),
        item_count=td.get("ItemCount"),
        size_bytes=td.get("TableSizeBytes"),
        billing_mode=(td.get("BillingModeSummary") or {}).get("BillingMode"),
        arn=td.get("TableArn"),
        key_schema=td.get("KeySchema"),
        attribute_definitions=td.get("AttributeDefinitions"),
        gsi=td.get("GlobalSecondaryIndexes"),
        lsi=td.get("LocalSecondaryIndexes"),
        stream_specification=td.get("StreamSpecification"),
        response=resp,
    )


def _action_delete_table(client, **kwargs) -> Dict[str, Any]:
    table_name = kwargs.get("table_name")
    confirm = bool(kwargs.get("confirm", False))
    if not table_name:
        return _err("table_name is required")
    chk = _check_table_allowed(table_name)
    if chk:
        return chk
    if not confirm:
        return _err(
            "Refusing to delete table without confirm=True",
            error_type="ConfirmationRequired",
            hint="Table deletion is irreversible. Pass confirm=True to proceed.",
        )
    resp = client.delete_table(TableName=table_name)
    return _ok(action="delete_table", table_name=table_name, deleted=True, response=resp)


def _action_batch_write_item(client, **kwargs) -> Dict[str, Any]:
    """
    Batch write (put/delete) up to 25 items total per request.
    Accepts either request_items (raw) OR (table_name + put_items/delete_keys).
    """
    request_items = kwargs.get("request_items")
    table_name = kwargs.get("table_name")
    put_items = kwargs.get("put_items") or []
    delete_keys = kwargs.get("delete_keys") or []

    if request_items is None:
        if not table_name:
            return _err("table_name is required (or provide request_items)")
        chk = _check_table_allowed(table_name)
        if chk:
            return chk
        if not isinstance(put_items, list) or not isinstance(delete_keys, list):
            return _err("put_items and delete_keys must be lists")
        ops = []
        for it in put_items:
            if not isinstance(it, dict) or not it:
                return _err("put_items must contain DynamoDB attribute-value dict items")
            ops.append({"PutRequest": {"Item": it}})
        for k in delete_keys:
            if not isinstance(k, dict) or not k:
                return _err("delete_keys must contain DynamoDB attribute-value dict keys")
            ops.append({"DeleteRequest": {"Key": k}})
        if len(ops) == 0:
            return _err("No operations provided (put_items/delete_keys empty)")
        if len(ops) > 25:
            return _err("batch_write_item supports up to 25 operations per request", error_type="LimitExceeded")
        request_items = {table_name: ops}
    else:
        # Validate allowlist for all tables in request_items
        if not isinstance(request_items, dict) or not request_items:
            return _err("request_items must be a non-empty dict")
        for tn in request_items.keys():
            chk = _check_table_allowed(tn)
            if chk:
                return chk

    resp = client.batch_write_item(RequestItems=request_items)
    unprocessed = resp.get("UnprocessedItems") or {}
    # Redact any sensitive values in returned unprocessed items
    redacted_unprocessed: Dict[str, Any] = {}
    for tn, reqs in unprocessed.items():
        out_reqs = []
        for r in reqs or []:
            if "PutRequest" in r and "Item" in r["PutRequest"]:
                out_reqs.append({"PutRequest": {"Item": _redact_item(r["PutRequest"]["Item"])}})
            elif "DeleteRequest" in r and "Key" in r["DeleteRequest"]:
                out_reqs.append({"DeleteRequest": {"Key": _redact_item(r["DeleteRequest"]["Key"])}})
            else:
                out_reqs.append(r)
        redacted_unprocessed[tn] = out_reqs

    return _ok(
        action="batch_write_item",
        unprocessed_items=redacted_unprocessed,
        unprocessed_count=sum(len(v or []) for v in (unprocessed or {}).values()),
        response=resp,
    )


def _action_batch_get_item(client, **kwargs) -> Dict[str, Any]:
    """
    Batch get up to 100 items per request (per AWS API limits).
    Accepts either request_items (raw) OR (table_name + keys).
    """
    request_items = kwargs.get("request_items")
    table_name = kwargs.get("table_name")
    keys = kwargs.get("keys") or []
    projection_expression = kwargs.get("projection_expression")
    expression_attribute_names = kwargs.get("expression_attribute_names")
    consistent_read = bool(kwargs.get("consistent_read", False))

    if request_items is None:
        if not table_name:
            return _err("table_name is required (or provide request_items)")
        chk = _check_table_allowed(table_name)
        if chk:
            return chk
        if not isinstance(keys, list) or not keys:
            return _err("keys is required (list of key dicts)")
        if len(keys) > 100:
            return _err("batch_get_item supports up to 100 keys per request", error_type="LimitExceeded")
        req: Dict[str, Any] = {"Keys": keys, "ConsistentRead": consistent_read}
        if projection_expression:
            req["ProjectionExpression"] = projection_expression
        if expression_attribute_names:
            req["ExpressionAttributeNames"] = expression_attribute_names
        request_items = {table_name: req}
    else:
        if not isinstance(request_items, dict) or not request_items:
            return _err("request_items must be a non-empty dict")
        for tn in request_items.keys():
            chk = _check_table_allowed(tn)
            if chk:
                return chk

    resp = client.batch_get_item(RequestItems=request_items)
    responses = resp.get("Responses") or {}
    out_responses: Dict[str, Any] = {}
    for tn, items in responses.items():
        out_responses[tn] = [_redact_item(i) for i in (items or [])]
    return _ok(
        action="batch_get_item",
        responses=out_responses,
        unprocessed_keys=resp.get("UnprocessedKeys") or {},
        response=resp,
    )


def _action_scan(client, **kwargs) -> Dict[str, Any]:
    """Capped full-table scan for admin/debug use."""
    table_name = kwargs.get("table_name")
    if not table_name:
        return _err("table_name is required")
    chk = _check_table_allowed(table_name)
    if chk:
        return chk

    max_items = int(kwargs.get("max_items", 25))
    if max_items <= 0:
        return _err("max_items must be > 0")
    if max_items > 200:
        max_items = 200

    req: Dict[str, Any] = {"TableName": table_name, "Limit": min(100, max_items)}
    if kwargs.get("filter_expression"):
        req["FilterExpression"] = kwargs["filter_expression"]
    if kwargs.get("expression_attribute_values"):
        req["ExpressionAttributeValues"] = kwargs["expression_attribute_values"]
    if kwargs.get("expression_attribute_names"):
        req["ExpressionAttributeNames"] = kwargs["expression_attribute_names"]
    if kwargs.get("projection_expression"):
        req["ProjectionExpression"] = kwargs["projection_expression"]
    if kwargs.get("exclusive_start_key"):
        req["ExclusiveStartKey"] = kwargs["exclusive_start_key"]
    req["ConsistentRead"] = bool(kwargs.get("consistent_read", False))

    items: List[Dict[str, Any]] = []
    scanned = 0
    last_evaluated_key = None
    while True:
        resp = client.scan(**req)
        batch = resp.get("Items") or []
        scanned += int(resp.get("ScannedCount", 0) or 0)
        for it in batch:
            if len(items) >= max_items:
                break
            items.append(_redact_item(it))
        last_evaluated_key = resp.get("LastEvaluatedKey")
        if len(items) >= max_items or not last_evaluated_key:
            break
        req["ExclusiveStartKey"] = last_evaluated_key

    return _ok(
        action="scan",
        table_name=table_name,
        items=items,
        count=len(items),
        scanned_count=scanned,
        last_evaluated_key=last_evaluated_key,
        note="Scan is capped for safety; use exclusive_start_key to paginate.",
    )


def _action_query(client, **kwargs) -> Dict[str, Any]:
    """Generic DynamoDB Query (recommended over Scan)."""
    table_name = kwargs.get("table_name")
    key_condition_expression = kwargs.get("key_condition_expression")
    if not table_name:
        return _err("table_name is required")
    if not key_condition_expression:
        return _err("key_condition_expression is required")
    chk = _check_table_allowed(table_name)
    if chk:
        return chk

    limit = int(kwargs.get("limit", 25))
    if limit > 200:
        limit = 200
    if limit <= 0:
        return _err("limit must be > 0")

    req: Dict[str, Any] = {"TableName": table_name, "KeyConditionExpression": key_condition_expression, "Limit": min(100, limit)}
    if kwargs.get("index_name"):
        req["IndexName"] = kwargs["index_name"]
    if kwargs.get("filter_expression"):
        req["FilterExpression"] = kwargs["filter_expression"]
    if kwargs.get("expression_attribute_values"):
        req["ExpressionAttributeValues"] = kwargs["expression_attribute_values"]
    if kwargs.get("expression_attribute_names"):
        req["ExpressionAttributeNames"] = kwargs["expression_attribute_names"]
    if kwargs.get("projection_expression"):
        req["ProjectionExpression"] = kwargs["projection_expression"]
    if kwargs.get("scan_index_forward") is not None:
        req["ScanIndexForward"] = bool(kwargs.get("scan_index_forward"))
    if kwargs.get("exclusive_start_key"):
        req["ExclusiveStartKey"] = kwargs["exclusive_start_key"]
    req["ConsistentRead"] = bool(kwargs.get("consistent_read", False))

    items: List[Dict[str, Any]] = []
    last_evaluated_key = None
    while True:
        resp = client.query(**req)
        batch = resp.get("Items") or []
        for it in batch:
            if len(items) >= limit:
                break
            items.append(_redact_item(it))
        last_evaluated_key = resp.get("LastEvaluatedKey")
        if len(items) >= limit or not last_evaluated_key:
            break
        req["ExclusiveStartKey"] = last_evaluated_key

    return _ok(
        action="query",
        table_name=table_name,
        items=items,
        count=len(items),
        last_evaluated_key=last_evaluated_key,
    )

_ACTIONS = {
    "create_jobs_table": _action_create_jobs_table,
    "put_item": _action_put_item,
    "get_item": _action_get_item,
    "update_item": _action_update_item,
    "delete_item": _action_delete_item,
    "query_jobs_by_status": _action_query_jobs_by_status,
    "describe_table": _action_describe_table,
    "delete_table": _action_delete_table,
    "batch_write_item": _action_batch_write_item,
    "batch_get_item": _action_batch_get_item,
    "scan": _action_scan,
    "query": _action_query,
}


@tool
def dynamodb(
    action: str,
    table_name: Optional[str] = None,
    item: Optional[Dict[str, Any]] = None,
    key: Optional[Dict[str, Any]] = None,
    update_expression: Optional[str] = None,
    condition_expression: Optional[str] = None,
    expression_attribute_values: Optional[Dict[str, Any]] = None,
    expression_attribute_names: Optional[Dict[str, str]] = None,
    projection_expression: Optional[str] = None,
    consistent_read: bool = False,
    return_values: str = "ALL_NEW",
    billing_mode: str = "PAY_PER_REQUEST",
    read_capacity: int = 5,
    write_capacity: int = 5,
    gsi_read_capacity: int = 5,
    gsi_write_capacity: int = 5,
    namespace: str = "default",
    status: str = "PENDING",
    limit: int = 25,
    due_before: Optional[str] = None,
    # generic query/scan/table mgmt
    index_name: Optional[str] = None,
    key_condition_expression: Optional[str] = None,
    filter_expression: Optional[str] = None,
    scan_index_forward: Optional[bool] = None,
    exclusive_start_key: Optional[Dict[str, Any]] = None,
    max_items: int = 25,
    # batch ops
    request_items: Optional[Dict[str, Any]] = None,
    keys: Optional[List[Dict[str, Any]]] = None,
    put_items: Optional[List[Dict[str, Any]]] = None,
    delete_keys: Optional[List[Dict[str, Any]]] = None,
    # destructive guard
    confirm: bool = False,
    tags: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    DynamoDB operations for durable agent state, job queues, and data storage.

    Args:
        action: The action to perform. One of:
            - "create_jobs_table": Create a table with recommended schema for job queues.
            - "put_item": Write an item to the table.
            - "get_item": Read an item by key.
            - "update_item": Update an existing item.
            - "delete_item": Delete an item by key.
            - "query_jobs_by_status": Query jobs by status using GSI1.
            - "describe_table": Describe a table (status, item count, schema).
            - "delete_table": Delete a table (requires confirm=True).
            - "batch_write_item": Batch put/delete (up to 25 operations).
            - "batch_get_item": Batch get (up to 100 keys).
            - "scan": Capped full table scan (safety limit).
            - "query": Generic DynamoDB Query (recommended over scan).
        table_name: DynamoDB table name.
        item: Item to write (dict with DynamoDB attribute format).
        key: Primary key for get/update/delete (dict with DynamoDB attribute format).
        update_expression: DynamoDB update expression (e.g., "SET #status = :s").
        condition_expression: Conditional expression for writes.
        expression_attribute_values: Values for expressions (e.g., {":s": {"S": "DONE"}}).
        expression_attribute_names: Name substitutions for reserved words.
        projection_expression: Attributes to return for get_item.
        consistent_read: Use strongly consistent reads (default False).
        return_values: What to return after update (default "ALL_NEW").
        billing_mode: PAY_PER_REQUEST or PROVISIONED (for create_jobs_table).
        read_capacity: Provisioned read capacity units.
        write_capacity: Provisioned write capacity units.
        gsi_read_capacity: GSI read capacity units.
        gsi_write_capacity: GSI write capacity units.
        namespace: Job namespace for query_jobs_by_status (default "default").
        status: Job status to query (default "PENDING").
        limit: Max items for query (default 25, max 100).
        due_before: Optional due date filter for jobs (ISO format).
        index_name: Index name for query (optional).
        key_condition_expression: For query: KeyConditionExpression string.
        filter_expression: For query/scan: FilterExpression string (optional).
        scan_index_forward: For query: True/False sort order (optional).
        exclusive_start_key: For query/scan: pagination start key (optional).
        max_items: For scan: cap returned items (default 25, max 200).
        request_items: For batch_get_item/batch_write_item: raw RequestItems dict (advanced).
        keys: For batch_get_item: list of key dicts (when request_items not provided).
        put_items: For batch_write_item: list of item dicts (when request_items not provided).
        delete_keys: For batch_write_item: list of key dicts (when request_items not provided).
        confirm: Required for destructive actions like delete_table.
        tags: Optional tags to apply to created resources (e.g., create_jobs_table).

    Returns:
        dict with success status and action-specific data

    Examples:
        >>> dynamodb(action="create_jobs_table", table_name="my-jobs")
        >>> dynamodb(action="put_item", table_name="my-jobs", item={"pk": {"S": "jobs#default"}, "sk": {"S": "job#123"}})
        >>> dynamodb(action="get_item", table_name="my-jobs", key={"pk": {"S": "jobs#default"}, "sk": {"S": "job#123"}})
    """
    action = (action or "").strip()
    if action not in _ACTIONS:
        return _err(
            f"Unknown action: {action}",
            error_type="InvalidAction",
            available_actions=sorted(_ACTIONS.keys()),
        )

    # Build kwargs for action functions
    kwargs: Dict[str, Any] = {}
    if table_name is not None:
        kwargs["table_name"] = table_name
    if item is not None:
        kwargs["item"] = item
    if key is not None:
        kwargs["key"] = key
    if update_expression is not None:
        kwargs["update_expression"] = update_expression
    if condition_expression is not None:
        kwargs["condition_expression"] = condition_expression
    if expression_attribute_values is not None:
        kwargs["expression_attribute_values"] = expression_attribute_values
    if expression_attribute_names is not None:
        kwargs["expression_attribute_names"] = expression_attribute_names
    if projection_expression is not None:
        kwargs["projection_expression"] = projection_expression
    kwargs["consistent_read"] = consistent_read
    kwargs["return_values"] = return_values
    kwargs["billing_mode"] = billing_mode
    kwargs["read_capacity"] = read_capacity
    kwargs["write_capacity"] = write_capacity
    kwargs["gsi_read_capacity"] = gsi_read_capacity
    kwargs["gsi_write_capacity"] = gsi_write_capacity
    kwargs["namespace"] = namespace
    kwargs["status"] = status
    kwargs["limit"] = limit
    if due_before is not None:
        kwargs["due_before"] = due_before
    if index_name is not None:
        kwargs["index_name"] = index_name
    if key_condition_expression is not None:
        kwargs["key_condition_expression"] = key_condition_expression
    if filter_expression is not None:
        kwargs["filter_expression"] = filter_expression
    if scan_index_forward is not None:
        kwargs["scan_index_forward"] = scan_index_forward
    if exclusive_start_key is not None:
        kwargs["exclusive_start_key"] = exclusive_start_key
    kwargs["max_items"] = max_items
    if request_items is not None:
        kwargs["request_items"] = request_items
    if keys is not None:
        kwargs["keys"] = keys
    if put_items is not None:
        kwargs["put_items"] = put_items
    if delete_keys is not None:
        kwargs["delete_keys"] = delete_keys
    kwargs["confirm"] = confirm
    if tags is not None:
        kwargs["tags"] = tags

    try:
        client = _get_client()
        return _ACTIONS[action](client, **kwargs)
    except Exception as e:
        return _err(str(e), error_type=type(e).__name__, action=action)


