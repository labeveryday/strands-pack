"""
API Gateway HTTP API Tool (minimal)

Create a simple HTTP API (API Gateway v2) to front Lambda functions, suitable for:
- approval links (GET page + POST approve/reject)

Important limitation:
- HTTP APIs (v2) do NOT support API keys + usage plans. If you need throttling/quotas via usage plans,
  use `apigateway_rest_api` (API Gateway REST APIs / v1).

This is intentionally minimal and guarded:
- API names must start with STRANDS_PACK_API_PREFIX (default "agent-")

Requires:
    pip install strands-pack[aws]

Actions
-------
- list_apis
    Parameters: max_results (default 50)
- create_http_api
    Parameters: name (required)
- create_stage
    Parameters: api_id (required), stage_name (default "$default"), auto_deploy (default True)
- create_jwt_authorizer
    Parameters: api_id (required), name (required), issuer (required), audience (required list[str])
- add_lambda_route
    Parameters: api_id (required), route_key (required, e.g. "GET /approve"), lambda_arn (required)
    Optional: auto_add_permission (default True), function_name_or_arn (optional; defaults to lambda_arn)
    Optional auth: authorization_type ("NONE"|"JWT"|"AWS_IAM"), authorizer_id (for JWT), authorization_scopes (list[str])
    Optional permission scoping: permission_scope ("api"|"route", default "route" when possible), stage_name (default "$default")
- add_lambda_permission
    Parameters: function_name_or_arn (required), api_id (required), statement_id (optional)
- get_api
- delete_api
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

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
    return boto3.client("apigatewayv2")


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


def _prefix() -> str:
    return os.getenv("STRANDS_PACK_API_PREFIX", "agent-")


def _lambda_prefix() -> str:
    # Reuse the same env var as lambda_tool for consistency
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


def _check_name(name: str) -> Optional[Dict[str, Any]]:
    if not name:
        return _err("name is required")
    pref = _prefix()
    if pref and not name.startswith(pref):
        return _err(f"API name must start with prefix '{pref}'", error_type="NameNotAllowed", prefix=pref)
    return None


def _get_region_account(*, strict: bool) -> Dict[str, str]:
    """
    Resolve region/account for SourceArn construction.

    In production, passing strict=True avoids overly-broad permissions.
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


def _source_arn_for_http_api(api_id: str, *, region: str, account: str, stage_name: str, route_key: Optional[str], scope: str) -> str:
    # Execute API ARN format:
    # arn:aws:execute-api:{region}:{account}:{apiId}/{stage}/{method}/{path}
    if scope == "route" and route_key and " " in route_key:
        method, path = route_key.split(" ", 1)
        method = method.strip().upper() or "*"
        path = (path.strip() or "/").lstrip("/")
        # RouteKey path always starts with '/', but execute-api ARN uses path without leading '/'.
        path_part = path if path else "*"
        return f"arn:aws:execute-api:{region}:{account}:{api_id}/{stage_name}/{method}/{path_part}"
    return f"arn:aws:execute-api:{region}:{account}:{api_id}/*/*/*"


@tool
def apigateway_http_api(
    action: str,
    name: Optional[str] = None,
    api_id: Optional[str] = None,
    stage_name: str = "$default",
    auto_deploy: bool = True,
    route_key: Optional[str] = None,
    lambda_arn: Optional[str] = None,
    function_name_or_arn: Optional[str] = None,
    auto_add_permission: bool = True,
    authorization_type: str = "NONE",
    authorizer_id: Optional[str] = None,
    authorization_scopes: Optional[list] = None,
    statement_id: Optional[str] = None,
    permission_scope: str = "route",
    strict_aws_ids: bool = True,
    issuer: Optional[str] = None,
    audience: Optional[list] = None,
    max_results: int = 50,
    tags: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    API Gateway HTTP API tool for Lambda integration.

    Note: HTTP APIs (v2) do NOT support API keys + usage plans.
    Use `apigateway_rest_api` if you need throttling/quotas.

    Args:
        action: The action to perform. One of:
            - "list_apis": List all HTTP APIs.
            - "create_http_api": Create a new HTTP API.
            - "get_api": Get details of an HTTP API.
            - "delete_api": Delete an HTTP API.
            - "create_stage": Create a deployment stage.
            - "create_jwt_authorizer": Create a JWT authorizer.
            - "add_lambda_route": Add a route that invokes a Lambda function.
            - "add_lambda_permission": Manually add Lambda invoke permission.
        name: API or authorizer name (must start with prefix, default "agent-").
        api_id: API ID (for most actions).
        stage_name: Stage name (default "$default").
        auto_deploy: Auto-deploy stage changes (default True).
        route_key: Route key like "GET /items" or "POST /users".
        lambda_arn: Lambda function ARN for the route target.
        function_name_or_arn: Lambda function for permission (defaults to lambda_arn).
        auto_add_permission: Automatically add Lambda invoke permission (default True).
        authorization_type: "NONE", "JWT", or "AWS_IAM" (default "NONE").
        authorizer_id: Authorizer ID (required when authorization_type="JWT").
        authorization_scopes: OAuth scopes for JWT authorization.
        statement_id: Lambda permission statement ID.
        permission_scope: "route" or "api" for permission scoping (default "route").
        strict_aws_ids: Require region/account for strict permission ARNs (default True).
        issuer: JWT issuer URL (for create_jwt_authorizer).
        audience: JWT audience list (for create_jwt_authorizer).
        max_results: Maximum APIs to list (default 50).
        tags: Optional AWS tags to apply when creating taggable API Gateway resources.

    Returns:
        dict with success status and action-specific data

    Examples:
        >>> apigateway_http_api(action="list_apis")
        >>> apigateway_http_api(action="create_http_api", name="agent-my-api")
        >>> apigateway_http_api(action="add_lambda_route", api_id="abc123",
        ...     route_key="GET /hello", lambda_arn="arn:aws:lambda:...")
    """
    action = (action or "").strip()

    try:
        apigw = _get_apigw()
    except Exception as e:
        return _err(str(e), error_type=type(e).__name__, action=action)

    try:
        if action == "list_apis":
            resp = apigw.get_apis(MaxResults=str(min(max_results, 100)))
            apis = resp.get("Items", []) or []
            formatted = []
            for api in apis:
                formatted.append({
                    "api_id": api.get("ApiId"),
                    "name": api.get("Name"),
                    "protocol_type": api.get("ProtocolType"),
                    "api_endpoint": api.get("ApiEndpoint"),
                    "created_date": api.get("CreatedDate").isoformat() if api.get("CreatedDate") else None,
                })
            return _ok(apis=formatted, count=len(formatted), next_token=resp.get("NextToken"))

        if action == "create_http_api":
            chk = _check_name(name)
            if chk:
                return chk
            resp = apigw.create_api(Name=name, ProtocolType="HTTP", Tags=aws_tags_dict(component="apigateway-http", tags=tags))
            return _ok(api_id=resp.get("ApiId"), api_endpoint=resp.get("ApiEndpoint"), name=name)

        if action == "create_stage":
            if not api_id:
                return _err("api_id is required")
            apigw.create_stage(ApiId=api_id, StageName=stage_name, AutoDeploy=auto_deploy)
            return _ok(api_id=api_id, stage_name=stage_name, created=True)

        if action == "create_jwt_authorizer":
            if not api_id or not name or not issuer or not audience:
                return _err("api_id, name, issuer, and audience are required")
            if not isinstance(audience, list) or not all(isinstance(x, str) and x.strip() for x in audience):
                return _err("audience must be a non-empty list[str]", error_type="InvalidParameterValue")

            resp = apigw.create_authorizer(
                ApiId=api_id,
                Name=name,
                AuthorizerType="JWT",
                IdentitySource=["$request.header.Authorization"],
                JwtConfiguration={"Issuer": issuer, "Audience": audience},
                Tags=aws_tags_dict(component="apigateway-http", tags=tags),
            )
            return _ok(
                api_id=api_id,
                authorizer_id=resp.get("AuthorizerId"),
                name=name,
                issuer=issuer,
                audience=audience,
            )

        if action == "add_lambda_route":
            if not api_id or not route_key or not lambda_arn:
                return _err("api_id, route_key, and lambda_arn are required")

            fn_for_perm = function_name_or_arn or lambda_arn
            if auto_add_permission:
                chk = _check_lambda_allowed(fn_for_perm)
                if chk:
                    return chk

            auth_type = (authorization_type or "NONE").strip().upper()
            if auth_type not in ("NONE", "JWT", "AWS_IAM"):
                return _err(
                    "authorization_type must be one of: NONE, JWT, AWS_IAM",
                    error_type="InvalidParameterValue",
                    authorization_type=auth_type,
                )
            if auth_type == "JWT" and not authorizer_id:
                return _err("authorizer_id is required when authorization_type=JWT", error_type="InvalidParameterValue")

            # Integration
            integ = apigw.create_integration(
                ApiId=api_id,
                IntegrationType="AWS_PROXY",
                IntegrationUri=lambda_arn,
                PayloadFormatVersion="2.0",
            )
            integ_id = integ.get("IntegrationId")

            # Route
            route_args: Dict[str, Any] = {"ApiId": api_id, "RouteKey": route_key, "Target": f"integrations/{integ_id}"}
            if auth_type != "NONE":
                route_args["AuthorizationType"] = auth_type
                if auth_type == "JWT":
                    route_args["AuthorizerId"] = authorizer_id
                    if isinstance(authorization_scopes, list) and authorization_scopes:
                        route_args["AuthorizationScopes"] = authorization_scopes
            route = apigw.create_route(**route_args)

            perm_result = None
            if auto_add_permission:
                stmt_id = statement_id or f"apigw-invoke-{api_id}"
                perm_scope = (permission_scope or "route").strip().lower()

                ids = _get_region_account(strict=strict_aws_ids)
                if "error" in ids:
                    return _err(ids["error"], error_type="MissingAWSIdentity", **ids)
                source_arn = _source_arn_for_http_api(
                    api_id,
                    region=ids["region"],
                    account=ids["account"],
                    stage_name=stage_name,
                    route_key=route_key,
                    scope=perm_scope,
                )

                lam = _get_lambda()
                try:
                    lam.add_permission(
                        FunctionName=fn_for_perm,
                        StatementId=stmt_id,
                        Action="lambda:InvokeFunction",
                        Principal="apigateway.amazonaws.com",
                        SourceArn=source_arn,
                    )
                except Exception as e:
                    if "ResourceConflictException" not in str(e):
                        raise

                perm_result = {
                    "function_name_or_arn": fn_for_perm,
                    "statement_id": stmt_id,
                    "source_arn": source_arn,
                    "permission_scope": perm_scope,
                }

            return _ok(
                api_id=api_id,
                route_id=route.get("RouteId"),
                integration_id=integ_id,
                route_key=route_key,
                authorization_type=auth_type,
                authorizer_id=authorizer_id,
                permission=perm_result,
            )

        if action == "add_lambda_permission":
            if not api_id or not function_name_or_arn:
                return _err("api_id and function_name_or_arn are required")
            stmt_id = statement_id or "apigw-invoke"

            lam = _get_lambda()
            region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "*"
            account = os.getenv("AWS_ACCOUNT_ID") or "*"
            source_arn = f"arn:aws:execute-api:{region}:{account}:{api_id}/*/*/*"

            lam.add_permission(
                FunctionName=function_name_or_arn,
                StatementId=stmt_id,
                Action="lambda:InvokeFunction",
                Principal="apigateway.amazonaws.com",
                SourceArn=source_arn,
            )
            return _ok(function_name_or_arn=function_name_or_arn, api_id=api_id, statement_id=stmt_id, source_arn=source_arn)

        if action == "get_api":
            if not api_id:
                return _err("api_id is required")
            resp = apigw.get_api(ApiId=api_id)
            return _ok(api=resp)

        if action == "delete_api":
            if not api_id:
                return _err("api_id is required")
            apigw.delete_api(ApiId=api_id)
            return _ok(api_id=api_id, deleted=True)

        return _err(
            f"Unknown action: {action}",
            error_type="InvalidAction",
            available_actions=[
                "list_apis",
                "create_http_api",
                "get_api",
                "delete_api",
                "create_stage",
                "create_jwt_authorizer",
                "add_lambda_route",
                "add_lambda_permission",
            ],
        )

    except Exception as e:
        return _err(str(e), error_type=type(e).__name__, action=action)


