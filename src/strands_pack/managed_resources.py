"""
Managed AWS Resources Tool

List AWS resources created/managed by strands-pack tools, identified by tags:
- managed-by=strands-pack

This is a production-minded helper for:
- cleanup
- inventory
- governance / cost allocation verification

Safety:
- hard caps per service and total results to avoid runaway enumeration
- returns metadata only (no secret values)

Requires:
    pip install strands-pack[aws]
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from strands import tool

try:
    import boto3

    HAS_BOTO3 = True
except ImportError:  # pragma: no cover
    boto3 = None
    HAS_BOTO3 = False


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


def _session_region() -> Optional[str]:
    return os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or (boto3.session.Session().region_name if HAS_BOTO3 else None)


def _get_client(service: str):
    if not HAS_BOTO3:
        raise ImportError("boto3 not installed. Run: pip install strands-pack[aws]")
    return boto3.client(service)


def _tags_to_dict(tags: Any) -> Dict[str, str]:
    """
    Normalize tags from various AWS shapes:
    - dict[str,str]
    - list[{Key,Value}]
    - list[{key,value}]
    """
    if tags is None:
        return {}
    if isinstance(tags, dict):
        return {str(k): str(v) for k, v in tags.items() if k is not None and v is not None}
    if isinstance(tags, list):
        out: Dict[str, str] = {}
        for t in tags:
            if not isinstance(t, dict):
                continue
            k = t.get("Key") if "Key" in t else t.get("key")
            v = t.get("Value") if "Value" in t else t.get("value")
            if k is None or v is None:
                continue
            out[str(k)] = str(v)
        return out
    return {}


def _match_tags(tag_dict: Dict[str, str], required: Dict[str, str]) -> bool:
    for k, v in required.items():
        if tag_dict.get(k) != v:
            return False
    return True


def _list_s3(max_items: int, required_tags: Dict[str, str]) -> List[Dict[str, Any]]:
    s3 = _get_client("s3")
    resp = s3.list_buckets()
    out: List[Dict[str, Any]] = []
    for b in (resp.get("Buckets", []) or [])[: max_items * 5]:
        name = b.get("Name")
        if not name:
            continue
        try:
            tags = s3.get_bucket_tagging(Bucket=name).get("TagSet", [])
        except Exception:
            tags = []
        tdict = _tags_to_dict(tags)
        if not _match_tags(tdict, required_tags):
            continue
        out.append({"type": "s3_bucket", "name": name, "created": b.get("CreationDate").isoformat() if b.get("CreationDate") else None, "tags": tdict})
        if len(out) >= max_items:
            break
    return out


def _list_sqs(max_items: int, required_tags: Dict[str, str]) -> List[Dict[str, Any]]:
    sqs = _get_client("sqs")
    resp = sqs.list_queues(MaxResults=min(max_items * 5, 1000))
    urls = resp.get("QueueUrls", []) or []
    out: List[Dict[str, Any]] = []
    for url in urls:
        try:
            tags = sqs.list_queue_tags(QueueUrl=url).get("Tags", {})
        except Exception:
            tags = {}
        tdict = _tags_to_dict(tags)
        if not _match_tags(tdict, required_tags):
            continue
        out.append({"type": "sqs_queue", "url": url, "name": url.split("/")[-1], "tags": tdict})
        if len(out) >= max_items:
            break
    return out


def _list_sns(max_items: int, required_tags: Dict[str, str]) -> List[Dict[str, Any]]:
    sns = _get_client("sns")
    out: List[Dict[str, Any]] = []
    token = None
    while True:
        req: Dict[str, Any] = {}
        if token:
            req["NextToken"] = token
        resp = sns.list_topics(**req)
        topics = resp.get("Topics", []) or []
        for t in topics:
            arn = t.get("TopicArn")
            if not arn:
                continue
            try:
                tags = sns.list_tags_for_resource(ResourceArn=arn).get("Tags", [])
            except Exception:
                tags = []
            tdict = _tags_to_dict(tags)
            if not _match_tags(tdict, required_tags):
                continue
            out.append({"type": "sns_topic", "arn": arn, "name": arn.split(":")[-1], "tags": tdict})
            if len(out) >= max_items:
                return out
        token = resp.get("NextToken")
        if not token:
            break
    return out


def _list_lambda(max_items: int, required_tags: Dict[str, str]) -> List[Dict[str, Any]]:
    lam = _get_client("lambda")
    out: List[Dict[str, Any]] = []
    marker = None
    while True:
        req: Dict[str, Any] = {"MaxItems": min(max_items * 5, 1000)}
        if marker:
            req["Marker"] = marker
        resp = lam.list_functions(**req)
        funcs = resp.get("Functions", []) or []
        for f in funcs:
            arn = f.get("FunctionArn")
            name = f.get("FunctionName")
            if not arn or not name:
                continue
            try:
                tags = lam.list_tags(Resource=arn).get("Tags", {})
            except Exception:
                tags = {}
            tdict = _tags_to_dict(tags)
            if not _match_tags(tdict, required_tags):
                continue
            out.append({"type": "lambda_function", "name": name, "arn": arn, "runtime": f.get("Runtime"), "last_modified": f.get("LastModified"), "tags": tdict})
            if len(out) >= max_items:
                return out
        marker = resp.get("NextMarker")
        if not marker:
            break
    return out


def _list_dynamodb(max_items: int, required_tags: Dict[str, str]) -> List[Dict[str, Any]]:
    ddb = _get_client("dynamodb")
    out: List[Dict[str, Any]] = []
    start = None
    while True:
        req: Dict[str, Any] = {"Limit": min(max_items * 5, 100)}
        if start:
            req["ExclusiveStartTableName"] = start
        resp = ddb.list_tables(**req)
        names = resp.get("TableNames", []) or []
        for name in names:
            try:
                desc = ddb.describe_table(TableName=name).get("Table", {}) or {}
                arn = desc.get("TableArn")
            except Exception:
                arn = None
            if not arn:
                continue
            try:
                tags = ddb.list_tags_of_resource(ResourceArn=arn).get("Tags", [])
            except Exception:
                tags = []
            tdict = _tags_to_dict(tags)
            if not _match_tags(tdict, required_tags):
                continue
            out.append({"type": "dynamodb_table", "name": name, "arn": arn, "status": desc.get("TableStatus"), "tags": tdict})
            if len(out) >= max_items:
                return out
        start = resp.get("LastEvaluatedTableName")
        if not start:
            break
    return out


def _list_apigw_v2_http_apis(max_items: int, required_tags: Dict[str, str]) -> List[Dict[str, Any]]:
    region = _session_region()
    if not region:
        return []
    apigw2 = _get_client("apigatewayv2")
    out: List[Dict[str, Any]] = []
    token = None
    while True:
        req: Dict[str, Any] = {"MaxResults": str(min(max_items * 5, 100))}
        if token:
            req["NextToken"] = token
        resp = apigw2.get_apis(**req)
        items = resp.get("Items", []) or []
        for api in items:
            api_id = api.get("ApiId")
            if not api_id:
                continue
            arn = f"arn:aws:apigateway:{region}::/apis/{api_id}"
            try:
                tags = apigw2.get_tags(ResourceArn=arn).get("Tags", {})
            except Exception:
                tags = {}
            tdict = _tags_to_dict(tags)
            if not _match_tags(tdict, required_tags):
                continue
            out.append({"type": "apigateway_http_api", "api_id": api_id, "name": api.get("Name"), "api_endpoint": api.get("ApiEndpoint"), "tags": tdict})
            if len(out) >= max_items:
                return out
        token = resp.get("NextToken")
        if not token:
            break
    return out


def _list_apigw_v1_rest(max_items: int, required_tags: Dict[str, str]) -> List[Dict[str, Any]]:
    region = _session_region()
    if not region:
        return []
    apigw = _get_client("apigateway")
    out: List[Dict[str, Any]] = []
    pos = None
    while True:
        req: Dict[str, Any] = {"limit": min(max_items * 5, 500)}
        if pos:
            req["position"] = pos
        resp = apigw.get_rest_apis(**req)
        items = resp.get("items", []) or []
        for api in items:
            api_id = api.get("id")
            if not api_id:
                continue
            arn = f"arn:aws:apigateway:{region}::/restapis/{api_id}"
            try:
                tags = apigw.get_tags(resourceArn=arn).get("tags", {})
            except Exception:
                tags = {}
            tdict = _tags_to_dict(tags)
            if not _match_tags(tdict, required_tags):
                continue
            out.append({"type": "apigateway_rest_api", "rest_api_id": api_id, "name": api.get("name"), "tags": tdict})
            if len(out) >= max_items:
                return out
        pos = resp.get("position")
        if not pos:
            break
    return out


def _list_scheduler(max_items: int, required_tags: Dict[str, str]) -> List[Dict[str, Any]]:
    scheduler = _get_client("scheduler")
    out: List[Dict[str, Any]] = []
    # list schedule groups first
    gresp = scheduler.list_schedule_groups(MaxResults=min(max_items * 5, 100))
    groups = gresp.get("ScheduleGroups", []) or []
    for g in groups:
        group_name = g.get("Name")
        if not group_name:
            continue
        resp = scheduler.list_schedules(GroupName=group_name, MaxResults=min(max_items * 5, 100))
        schedules = resp.get("Schedules", []) or []
        for s in schedules:
            arn = s.get("Arn")
            name = s.get("Name")
            if not arn or not name:
                continue
            try:
                tags = scheduler.list_tags_for_resource(ResourceArn=arn).get("Tags", [])
            except Exception:
                tags = []
            tdict = _tags_to_dict(tags)
            if not _match_tags(tdict, required_tags):
                continue
            out.append({"type": "scheduler_schedule", "name": name, "group_name": group_name, "arn": arn, "state": s.get("State"), "tags": tdict})
            if len(out) >= max_items:
                return out
    return out


_SERVICE_IMPLS = {
    "s3": _list_s3,
    "sqs": _list_sqs,
    "sns": _list_sns,
    "lambda": _list_lambda,
    "dynamodb": _list_dynamodb,
    "apigateway_http": _list_apigw_v2_http_apis,
    "apigateway_rest": _list_apigw_v1_rest,
    "scheduler": _list_scheduler,
}


@tool
def list_managed_resources(
    services: Optional[List[str]] = None,
    match_tags: Optional[Dict[str, str]] = None,
    max_per_service: int = 50,
    max_total: int = 200,
) -> Dict[str, Any]:
    """
    List AWS resources tagged as managed by strands-pack.

    Args:
        services: Optional list of services to scan. Defaults to:
            ["lambda","dynamodb","s3","sqs","sns","apigateway_http","apigateway_rest","scheduler"]
        match_tags: Additional required tags (e.g., {"env":"prod"}). `managed-by=strands-pack` is always required.
        max_per_service: Max results per service (default 50).
        max_total: Max results total across all services (default 200).

    Returns:
        dict with per-service results and totals.
    """
    if not HAS_BOTO3:
        return _err("boto3 not installed. Run: pip install strands-pack[aws]", error_type="ImportError")

    req = {"managed-by": "strands-pack"}
    if match_tags:
        req.update({str(k): str(v) for k, v in match_tags.items() if k is not None and v is not None})

    svc_list = services or ["lambda", "dynamodb", "s3", "sqs", "sns", "apigateway_http", "apigateway_rest", "scheduler"]
    unknown = [s for s in svc_list if s not in _SERVICE_IMPLS]
    if unknown:
        return _err("Unknown services requested", error_type="InvalidParameterValue", unknown_services=unknown, supported_services=sorted(_SERVICE_IMPLS.keys()))

    max_per_service = max(1, min(int(max_per_service), 500))
    max_total = max(1, min(int(max_total), 2000))

    results: Dict[str, Any] = {}
    total = 0
    errors: Dict[str, str] = {}

    for svc in svc_list:
        if total >= max_total:
            break
        try:
            items = _SERVICE_IMPLS[svc](min(max_per_service, max_total - total), req)
            results[svc] = items
            total += len(items)
        except Exception as e:
            errors[svc] = str(e)
            results[svc] = []

    return _ok(
        required_tags=req,
        results=results,
        total=total,
        errors=errors or None,
        supported_services=sorted(_SERVICE_IMPLS.keys()),
        note="This tool lists metadata only. It is intended for inventory/cleanup of strands-pack managed resources.",
    )


