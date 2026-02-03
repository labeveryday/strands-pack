"""
API Gateway REST API Tool (API keys + usage plans)

This tool uses **API Gateway REST APIs (v1)**, which support:
- API keys
- usage plans (throttling + quotas)

If you need API keys / usage plans, you generally want REST APIs, not HTTP APIs.

Guardrails:
- API names must start with `STRANDS_PACK_API_PREFIX` (default "agent-")
- Lambda functions must start with `STRANDS_PACK_LAMBDA_PREFIX` (default "agent-")

Requires:
    pip install strands-pack[aws]

Actions
-------
- create_rest_lambda_api
    Creates a REST API + route to Lambda + deployment stage + (optional) API key & usage plan.
    Parameters:
      - name (required)
      - path (default "/")
      - method (default "ANY")
      - lambda_arn (required)
      - stage_name (default "prod")
      - require_api_key (default True)
      - create_api_key (default True)
      - create_usage_plan (default True)
      - throttle_rate_limit (default 1.0)
      - throttle_burst_limit (default 2)
      - quota_limit (optional)
      - quota_period ("DAY"|"WEEK"|"MONTH", optional)

Lower-level actions are also available for advanced workflows:
- create_rest_api
- add_lambda_route
- deploy_api
- create_usage_plan
- create_api_key
- attach_api_key_to_usage_plan
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple

from strands import tool

from strands_pack.aws_tags import aws_tags_dict
try:
    import boto3

    HAS_BOTO3 = True
except ImportError:  # pragma: no cover
    boto3 = None
    HAS_BOTO3 = False


def _get_apigw():
    if not HAS_BOTO3:
        raise ImportError("boto3 not installed. Run: pip install strands-pack[aws]")
    return boto3.client("apigateway")


def _get_lambda():
    if not HAS_BOTO3:
        raise ImportError("boto3 not installed. Run: pip install strands-pack[aws]")
    return boto3.client("lambda")


def _get_sts():
    if not HAS_BOTO3:
        raise ImportError("boto3 not installed. Run: pip install strands-pack[aws]")
    return boto3.client("sts")


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


def _api_prefix() -> str:
    return os.getenv("STRANDS_PACK_API_PREFIX", "agent-")


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


def _check_api_name(name: str) -> Optional[Dict[str, Any]]:
    if not name:
        return _err("name is required")
    pref = _api_prefix()
    if pref and not name.startswith(pref):
        return _err(f"API name must start with prefix '{pref}'", error_type="NameNotAllowed", prefix=pref)
    return None


def _get_region_account(*, strict: bool) -> Dict[str, str]:
    """
    Resolve region/account for SourceArn construction.

    In production, strict=True avoids overly-broad permissions.
    """
    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
    account = os.getenv("AWS_ACCOUNT_ID")

    if not region:
        try:
            import boto3 as _boto3  # type: ignore

            region = _boto3.session.Session().region_name
        except Exception:
            region = None

    if not account:
        try:
            account = _get_sts().get_caller_identity().get("Account")
        except Exception:
            account = None

    if strict and (not region or not account):
        return {
            "error": "Could not determine AWS region/account for strict permission scoping.",
            "hint": "Set AWS_DEFAULT_REGION (or AWS_REGION) and AWS_ACCOUNT_ID (or ensure AWS credentials allow sts:GetCallerIdentity).",
            "region": region,
            "account": account,
        }

    return {"region": region or "*", "account": account or "*"}


def _source_arn_for_rest_api(
    rest_api_id: str, *, region: str, account: str, stage_name: str, method: str, path: str, scope: str
) -> str:
    # arn:aws:execute-api:{region}:{account}:{apiId}/{stage}/{method}/{path}
    if scope == "route":
        m = (method or "*").upper()
        norm = (path or "/").strip()
        if not norm.startswith("/"):
            norm = "/" + norm
        path_part = norm.lstrip("/") or "*"
        return f"arn:aws:execute-api:{region}:{account}:{rest_api_id}/{stage_name}/{m}/{path_part}"
    if scope == "stage":
        return f"arn:aws:execute-api:{region}:{account}:{rest_api_id}/{stage_name}/*/*"
    return f"arn:aws:execute-api:{region}:{account}:{rest_api_id}/*/*/*"


def _integration_uri(lambda_arn: str, *, region: str) -> str:
    # REST API (v1) Lambda proxy integration URI:
    # arn:aws:apigateway:{region}:lambda:path/2015-03-31/functions/{lambdaArn}/invocations
    return f"arn:aws:apigateway:{region}:lambda:path/2015-03-31/functions/{lambda_arn}/invocations"


def _apigw_region() -> Optional[str]:
    return os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or boto3.session.Session().region_name


def _apigw_resource_arn(region: str, resource_path: str) -> str:
    # API Gateway tag_resource uses ARNs like:
    # arn:aws:apigateway:{region}::/restapis/{restApiId}
    return f"arn:aws:apigateway:{region}::{resource_path}"


def _tag_apigw_resource(apigw, *, region: str, resource_path: str, tags: Dict[str, str]) -> None:
    apigw.tag_resource(resourceArn=_apigw_resource_arn(region, resource_path), tags=tags)


def _list_resources(apigw, rest_api_id: str) -> Dict[str, str]:
    resp = apigw.get_resources(restApiId=rest_api_id, limit=500)
    items = resp.get("items", []) or []
    # Map by full path (e.g. "/" or "/foo/bar")
    by_path: Dict[str, str] = {}
    for r in items:
        p = r.get("path")
        rid = r.get("id")
        if p and rid:
            by_path[p] = rid
    return by_path


def _ensure_resource_path(apigw, rest_api_id: str, path: str) -> Tuple[str, str]:
    """
    Ensure the resource exists for the given path. Returns (resource_id, normalized_path).
    """
    norm = (path or "/").strip()
    if not norm.startswith("/"):
        norm = "/" + norm
    if norm == "":
        norm = "/"
    # Root always exists
    resources = _list_resources(apigw, rest_api_id)
    if norm in resources:
        return resources[norm], norm
    if "/" not in resources:
        # root resource should exist as "/"
        raise RuntimeError("API Gateway resources missing root '/' resource")

    # Create nested resources one segment at a time
    cur_path = "/"
    cur_id = resources["/"]
    for seg in [s for s in norm.split("/") if s]:
        next_path = cur_path.rstrip("/") + "/" + seg
        resources = _list_resources(apigw, rest_api_id)
        if next_path in resources:
            cur_path, cur_id = next_path, resources[next_path]
            continue
        created = apigw.create_resource(restApiId=rest_api_id, parentId=cur_id, pathPart=seg)
        cur_path, cur_id = next_path, created["id"]
    return cur_id, norm


@tool
def apigateway_rest_api(
    action: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    rest_api_id: Optional[str] = None,
    path: str = "/",
    method: str = "ANY",
    lambda_arn: Optional[str] = None,
    stage_name: str = "prod",
    require_api_key: bool = True,
    auto_add_permission: bool = True,
    permission_scope: str = "stage",
    strict_aws_ids: bool = True,
    statement_id: Optional[str] = None,
    throttle_rate_limit: float = 1.0,
    throttle_burst_limit: int = 2,
    quota_limit: Optional[int] = None,
    quota_period: Optional[str] = None,
    enabled: bool = True,
    usage_plan_id: Optional[str] = None,
    api_key_id: Optional[str] = None,
    create_api_key: bool = True,
    create_usage_plan: bool = True,
    tags: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Manage API Gateway REST APIs (v1) with API keys and usage plans.

    Args:
        action: The action to perform. One of:
            - "create_rest_api": Create a new REST API.
            - "add_lambda_route": Add a Lambda proxy route to an existing REST API.
            - "deploy_api": Deploy the REST API to a stage.
            - "create_usage_plan": Create a usage plan with throttling/quotas.
            - "create_api_key": Create an API key.
            - "attach_api_key_to_usage_plan": Attach an API key to a usage plan.
            - "create_rest_lambda_api": High-level action that creates API + route + deployment + key + plan.
        name: API/key/plan name (required for create_rest_api, create_api_key, create_usage_plan, create_rest_lambda_api).
        description: Optional description for the API or deployment.
        rest_api_id: REST API ID (required for add_lambda_route, deploy_api, create_usage_plan).
        path: Route path (default "/").
        method: HTTP method - "ANY", "GET", "POST", etc. (default "ANY").
        lambda_arn: Lambda function ARN (required for add_lambda_route, create_rest_lambda_api).
        stage_name: Deployment stage name (default "prod").
        require_api_key: Whether the route requires an API key (default True).
        auto_add_permission: Auto-add Lambda invoke permission for API Gateway (default True).
        permission_scope: Scope for Lambda permission - "route", "stage", or "api" (default "stage").
        strict_aws_ids: Require region/account for strict permission scoping (default True).
        statement_id: Custom statement ID for Lambda permission (optional).
        throttle_rate_limit: Requests per second limit (default 1.0).
        throttle_burst_limit: Burst limit (default 2).
        quota_limit: Optional quota limit (requires quota_period).
        quota_period: Quota period - "DAY", "WEEK", or "MONTH" (optional).
        enabled: Whether API key is enabled (default True).
        usage_plan_id: Usage plan ID (for attach_api_key_to_usage_plan).
        api_key_id: API key ID (for attach_api_key_to_usage_plan).
        create_api_key: Create an API key in create_rest_lambda_api (default True).
        create_usage_plan: Create a usage plan in create_rest_lambda_api (default True).
        tags: Optional tags dict to apply to created resources.

    Returns:
        dict with success status and action-specific data

    Examples:
        >>> apigateway_rest_api(action="create_rest_api", name="agent-my-api")
        >>> apigateway_rest_api(action="add_lambda_route", rest_api_id="abc123", lambda_arn="arn:aws:lambda:...")
        >>> apigateway_rest_api(action="create_rest_lambda_api", name="agent-api", lambda_arn="arn:aws:lambda:...")
    """
    action = (action or "").strip()

    # Build kwargs dict from explicit parameters for internal use
    kwargs: Dict[str, Any] = {
        "name": name,
        "description": description,
        "rest_api_id": rest_api_id,
        "path": path,
        "method": method,
        "lambda_arn": lambda_arn,
        "stage_name": stage_name,
        "require_api_key": require_api_key,
        "auto_add_permission": auto_add_permission,
        "permission_scope": permission_scope,
        "strict_aws_ids": strict_aws_ids,
        "statement_id": statement_id,
        "throttle_rate_limit": throttle_rate_limit,
        "throttle_burst_limit": throttle_burst_limit,
        "quota_limit": quota_limit,
        "quota_period": quota_period,
        "enabled": enabled,
        "usage_plan_id": usage_plan_id,
        "api_key_id": api_key_id,
        "create_api_key": create_api_key,
        "create_usage_plan": create_usage_plan,
        "tags": tags,
    }

    try:
        apigw = _get_apigw()
    except Exception as e:
        return _err(str(e), error_type=type(e).__name__, action=action)

    try:
        if action == "create_rest_api":
            chk = _check_api_name(name)
            if chk:
                return chk
            resp = apigw.create_rest_api(
                name=name,
                description=description,
                endpointConfiguration={"types": ["REGIONAL"]},
            )
            region = _apigw_region()
            if not region:
                return _err(
                    "REST API created but could not determine region for tagging",
                    error_type="TaggingFailed",
                    rest_api_id=resp.get("id"),
                    hint="Set AWS_DEFAULT_REGION (or AWS_REGION).",
                )
            try:
                _tag_apigw_resource(
                    apigw,
                    region=region,
                    resource_path=f"/restapis/{resp.get('id')}",
                    tags=aws_tags_dict(component="apigateway-rest", tags=tags),
                )
            except Exception as e:
                return _err(
                    f"REST API created but tagging failed: {e}",
                    error_type="TaggingFailed",
                    rest_api_id=resp.get("id"),
                )
            return _ok(rest_api_id=resp.get("id"), name=name)

        if action == "add_lambda_route":
            method_upper = (method or "ANY").upper()
            permission_scope_lower = (permission_scope or "stage").strip().lower()

            if not rest_api_id or not lambda_arn:
                return _err("rest_api_id and lambda_arn are required")
            if auto_add_permission:
                chk = _check_lambda_allowed(lambda_arn)
                if chk:
                    return chk

            ids = _get_region_account(strict=strict_aws_ids)
            if "error" in ids:
                return _err(ids["error"], error_type="MissingAWSIdentity", **ids)
            region, account = ids["region"], ids["account"]
            resource_id, norm_path = _ensure_resource_path(apigw, rest_api_id, path)

            # Method (proxy)
            apigw.put_method(
                restApiId=rest_api_id,
                resourceId=resource_id,
                httpMethod=method_upper,
                authorizationType="NONE",
                apiKeyRequired=require_api_key,
            )

            # Integration
            apigw.put_integration(
                restApiId=rest_api_id,
                resourceId=resource_id,
                httpMethod=method_upper,
                type="AWS_PROXY",
                integrationHttpMethod="POST",
                uri=_integration_uri(lambda_arn, region=region),
            )

            perm_result = None
            if auto_add_permission:
                stmt_id = statement_id or f"apigw-rest-invoke-{rest_api_id}"
                source_arn = _source_arn_for_rest_api(
                    rest_api_id,
                    region=region,
                    account=account,
                    stage_name=stage_name,
                    method=method_upper,
                    path=norm_path,
                    scope=permission_scope_lower,
                )
                lam = _get_lambda()
                try:
                    lam.add_permission(
                        FunctionName=lambda_arn,
                        StatementId=stmt_id,
                        Action="lambda:InvokeFunction",
                        Principal="apigateway.amazonaws.com",
                        SourceArn=source_arn,
                    )
                except Exception as e:
                    if "ResourceConflictException" not in str(e):
                        raise
                perm_result = {"statement_id": stmt_id, "source_arn": source_arn, "permission_scope": permission_scope_lower}

            return _ok(
                rest_api_id=rest_api_id,
                path=norm_path,
                method=method_upper,
                resource_id=resource_id,
                lambda_arn=lambda_arn,
                require_api_key=require_api_key,
                permission=perm_result,
            )

        if action == "deploy_api":
            if not rest_api_id:
                return _err("rest_api_id is required")
            resp = apigw.create_deployment(restApiId=rest_api_id, stageName=stage_name, description=description)
            return _ok(rest_api_id=rest_api_id, stage_name=stage_name, deployment_id=resp.get("id"), deployed=True)

        if action == "create_usage_plan":
            if not name or not rest_api_id:
                return _err("name and rest_api_id are required")
            plan_args: Dict[str, Any] = {
                "name": name,
                "apiStages": [{"apiId": rest_api_id, "stage": stage_name}],
                "throttle": {"rateLimit": throttle_rate_limit, "burstLimit": throttle_burst_limit},
            }
            if quota_limit is not None and quota_period:
                plan_args["quota"] = {"limit": int(quota_limit), "period": quota_period}

            resp = apigw.create_usage_plan(**plan_args)
            region = _apigw_region()
            if region:
                try:
                    _tag_apigw_resource(
                        apigw,
                        region=region,
                        resource_path=f"/usageplans/{resp.get('id')}",
                        tags=aws_tags_dict(component="apigateway-rest", tags=tags),
                    )
                except Exception as e:
                    return _err(
                        f"Usage plan created but tagging failed: {e}",
                        error_type="TaggingFailed",
                        usage_plan_id=resp.get("id"),
                    )
            return _ok(
                usage_plan_id=resp.get("id"),
                name=name,
                rest_api_id=rest_api_id,
                stage_name=stage_name,
                throttle=plan_args["throttle"],
                quota=plan_args.get("quota"),
            )

        if action == "create_api_key":
            if not name:
                return _err("name is required")
            resp = apigw.create_api_key(name=name, enabled=enabled, description=description)
            key_id = resp.get("id")
            region = _apigw_region()
            if region and key_id:
                try:
                    _tag_apigw_resource(
                        apigw,
                        region=region,
                        resource_path=f"/apikeys/{key_id}",
                        tags=aws_tags_dict(component="apigateway-rest", tags=tags),
                    )
                except Exception as e:
                    return _err(
                        f"API key created but tagging failed: {e}",
                        error_type="TaggingFailed",
                        api_key_id=key_id,
                    )
            # Ensure we return the value (only available when includeValue=True)
            key_value = None
            if key_id:
                got = apigw.get_api_key(apiKey=key_id, includeValue=True)
                key_value = got.get("value")
            return _ok(api_key_id=key_id, api_key_value=key_value, enabled=enabled, name=name)

        if action == "attach_api_key_to_usage_plan":
            if not usage_plan_id or not api_key_id:
                return _err("usage_plan_id and api_key_id are required")
            resp = apigw.create_usage_plan_key(usagePlanId=usage_plan_id, keyId=api_key_id, keyType="API_KEY")
            return _ok(
                attached=True,
                usage_plan_id=usage_plan_id,
                api_key_id=api_key_id,
                usage_plan_key_id=resp.get("id"),
            )

        if action == "create_rest_lambda_api":
            chk = _check_api_name(name)
            if chk:
                return chk

            if not lambda_arn:
                return _err("lambda_arn is required")
            chk = _check_lambda_allowed(lambda_arn)
            if chk:
                return chk

            method_upper = (method or "ANY").upper()

            # 1) Create API
            api = apigw.create_rest_api(name=name, endpointConfiguration={"types": ["REGIONAL"]})
            created_rest_api_id = api.get("id")
            region = _apigw_region()
            if not region:
                return _err(
                    "REST API created but could not determine region for tagging",
                    error_type="TaggingFailed",
                    rest_api_id=created_rest_api_id,
                    hint="Set AWS_DEFAULT_REGION (or AWS_REGION).",
                )
            try:
                _tag_apigw_resource(
                    apigw,
                    region=region,
                    resource_path=f"/restapis/{created_rest_api_id}",
                    tags=aws_tags_dict(component="apigateway-rest", tags=tags),
                )
            except Exception as e:
                return _err(f"REST API created but tagging failed: {e}", error_type="TaggingFailed", rest_api_id=created_rest_api_id)

            # 2) Route -> Lambda (proxy)
            route_res = apigateway_rest_api(
                action="add_lambda_route",
                rest_api_id=created_rest_api_id,
                path=path,
                method=method_upper,
                lambda_arn=lambda_arn,
                require_api_key=require_api_key,
                auto_add_permission=True,
                stage_name=stage_name,
                permission_scope="stage",
            )
            if not route_res.get("success"):
                return route_res

            # 3) Deploy stage
            dep = apigw.create_deployment(restApiId=created_rest_api_id, stageName=stage_name)

            # 4) Usage plan (+ stage binding) and API key
            usage_plan_result = None
            api_key_result = None
            attached = None

            if create_usage_plan:
                plan_args: Dict[str, Any] = {
                    "name": f"{name}-{stage_name}-plan",
                    "apiStages": [{"apiId": created_rest_api_id, "stage": stage_name}],
                    "throttle": {"rateLimit": throttle_rate_limit, "burstLimit": throttle_burst_limit},
                }
                if quota_limit is not None and quota_period:
                    plan_args["quota"] = {"limit": int(quota_limit), "period": quota_period}
                usage_plan_result = apigw.create_usage_plan(**plan_args)
                try:
                    _tag_apigw_resource(
                        apigw,
                        region=region,
                        resource_path=f"/usageplans/{usage_plan_result.get('id')}",
                        tags=aws_tags_dict(component="apigateway-rest", tags=tags),
                    )
                except Exception as e:
                    return _err(
                        f"Usage plan created but tagging failed: {e}",
                        error_type="TaggingFailed",
                        usage_plan_id=usage_plan_result.get("id"),
                    )

            if create_api_key:
                created_key = apigw.create_api_key(name=f"{name}-{stage_name}-key", enabled=True)
                key_id = created_key.get("id")
                if key_id:
                    try:
                        _tag_apigw_resource(
                            apigw,
                            region=region,
                            resource_path=f"/apikeys/{key_id}",
                            tags=aws_tags_dict(component="apigateway-rest", tags=tags),
                        )
                    except Exception as e:
                        return _err(
                            f"API key created but tagging failed: {e}",
                            error_type="TaggingFailed",
                            api_key_id=key_id,
                        )
                key_value = None
                if key_id:
                    got = apigw.get_api_key(apiKey=key_id, includeValue=True)
                    key_value = got.get("value")
                api_key_result = {"api_key_id": key_id, "api_key_value": key_value}

            if usage_plan_result and api_key_result and usage_plan_result.get("id") and api_key_result.get("api_key_id"):
                upk = apigw.create_usage_plan_key(
                    usagePlanId=usage_plan_result["id"],
                    keyId=api_key_result["api_key_id"],
                    keyType="API_KEY",
                )
                attached = {"usage_plan_key_id": upk.get("id")}

            # Best-effort invoke URL construction.
            norm_path = route_res.get("path") or (path if (path or "/").startswith("/") else f"/{path}")
            base = f"https://{created_rest_api_id}.execute-api.{region}.amazonaws.com/{stage_name}"
            invoke_url = base + ("" if norm_path == "/" else norm_path)

            return _ok(
                rest_api_id=created_rest_api_id,
                name=name,
                stage_name=stage_name,
                deployment_id=dep.get("id"),
                invoke_url=invoke_url,
                route=route_res,
                require_api_key=require_api_key,
                usage_plan_id=usage_plan_result.get("id") if usage_plan_result else None,
                api_key_id=api_key_result.get("api_key_id") if api_key_result else None,
                api_key_value=api_key_result.get("api_key_value") if api_key_result else None,
                throttle={"rateLimit": throttle_rate_limit, "burstLimit": throttle_burst_limit} if usage_plan_result else None,
                quota=usage_plan_result.get("quota") if usage_plan_result else None,
                attached=attached,
            )

        return _err(
            f"Unknown action: {action}",
            error_type="InvalidAction",
            available_actions=[
                "create_rest_api",
                "add_lambda_route",
                "deploy_api",
                "create_usage_plan",
                "create_api_key",
                "attach_api_key_to_usage_plan",
                "create_rest_lambda_api",
            ],
        )

    except Exception as e:
        return _err(str(e), error_type=type(e).__name__, action=action)


