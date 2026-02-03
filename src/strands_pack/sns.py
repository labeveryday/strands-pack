"""
SNS Tool

Manage AWS SNS topics, subscriptions, and message publishing.

Requires: pip install strands-pack[aws]

Actions
-------
- create_topic: Create a new SNS topic
- delete_topic: Delete an SNS topic
- list_topics: List all SNS topics
- get_topic_attributes: Get topic configuration details
- publish: Publish a message to a topic
- subscribe: Create a subscription to a topic
- subscribe_lambda: Subscribe a Lambda function to a topic (Option A: also adds lambda:AddPermission)
- unsubscribe: Remove a subscription
- list_subscriptions: List subscriptions (optionally filtered by topic)
- confirm_subscription: Confirm a pending subscription
"""

from __future__ import annotations

import os
import re
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
    return boto3.client("sns")


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


def _sanitize_statement_id(statement_id: str) -> str:
    # Lambda StatementId: up to 100 chars; allow [0-9A-Za-z-_]
    safe = re.sub(r"[^0-9A-Za-z-_]+", "-", (statement_id or "").strip())
    return (safe or "sns-invoke").strip("-")[:100]


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
def sns(
    action: str,
    topic_name: Optional[str] = None,
    topic_arn: Optional[str] = None,
    display_name: Optional[str] = None,
    message: Optional[str] = None,
    subject: Optional[str] = None,
    message_attributes: Optional[Dict[str, Any]] = None,
    protocol: Optional[str] = None,
    endpoint: Optional[str] = None,
    subscription_arn: Optional[str] = None,
    token: Optional[str] = None,
    filter_policy: Optional[Dict[str, Any]] = None,
    lambda_name: Optional[str] = None,
    lambda_arn: Optional[str] = None,
    statement_id: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Manage AWS SNS topics, subscriptions, and message publishing.

    Args:
        action: The action to perform. One of:
            - "create_topic": Create a new SNS topic.
            - "delete_topic": Delete an SNS topic.
            - "list_topics": List all SNS topics.
            - "get_topic_attributes": Get topic configuration details.
            - "publish": Publish a message to a topic.
            - "subscribe": Subscribe to a topic.
            - "subscribe_lambda": Subscribe a Lambda function to a topic (adds invoke permission).
            - "unsubscribe": Remove a subscription.
            - "list_subscriptions": List subscriptions.
            - "confirm_subscription": Confirm a pending subscription.
        topic_name: Name for the new topic (create_topic).
        topic_arn: ARN of the topic (most actions).
        display_name: Display name for the topic (create_topic).
        message: Message content to publish.
        subject: Subject line for email subscriptions.
        message_attributes: Message attributes dict for publish.
        protocol: Subscription protocol (email, sms, sqs, http, https, lambda).
        endpoint: Subscription endpoint (email address, phone, URL, ARN).
        subscription_arn: ARN of the subscription (unsubscribe).
        token: Confirmation token (confirm_subscription).
        filter_policy: Subscription filter policy dict.
        lambda_name: Lambda function name (subscribe_lambda).
        lambda_arn: Lambda function ARN (subscribe_lambda).
        statement_id: Optional Lambda permission statement id (subscribe_lambda).

    Returns:
        dict with success status and action-specific data

    Examples:
        >>> sns(action="create_topic", topic_name="my-alerts")
        >>> sns(action="publish", topic_arn="arn:aws:sns:...", message="Hello!")
        >>> sns(action="subscribe", topic_arn="arn:aws:sns:...", protocol="email", endpoint="user@example.com")
    """
    action = (action or "").strip()

    try:
        client = _get_client()
    except Exception as e:
        return _err(str(e), error_type=type(e).__name__, action=action)

    try:
        if action == "create_topic":
            if not topic_name:
                return _err("topic_name is required")
            create_args: Dict[str, Any] = {"Name": topic_name}
            if display_name:
                create_args["Attributes"] = {"DisplayName": display_name}
            create_args["Tags"] = aws_tags_list(component="sns", tags=tags)
            resp = client.create_topic(**create_args)
            return _ok(
                topic_name=topic_name,
                topic_arn=resp["TopicArn"],
                display_name=display_name,
                tagged=True,
            )

        if action == "delete_topic":
            if not topic_arn:
                return _err("topic_arn is required")
            client.delete_topic(TopicArn=topic_arn)
            return _ok(topic_arn=topic_arn, deleted=True)

        if action == "list_topics":
            resp = client.list_topics()
            topics = resp.get("Topics", []) or []
            formatted = []
            for t in topics:
                arn = t.get("TopicArn", "")
                name = arn.split(":")[-1] if arn else ""
                formatted.append({"name": name, "arn": arn})
            return _ok(topics=formatted, count=len(formatted))

        if action == "get_topic_attributes":
            if not topic_arn:
                return _err("topic_arn is required")
            resp = client.get_topic_attributes(TopicArn=topic_arn)
            attrs = resp.get("Attributes", {}) or {}
            return _ok(
                topic_arn=topic_arn,
                display_name=attrs.get("DisplayName"),
                owner=attrs.get("Owner"),
                subscriptions_confirmed=int(attrs.get("SubscriptionsConfirmed", 0)),
                subscriptions_pending=int(attrs.get("SubscriptionsPending", 0)),
                subscriptions_deleted=int(attrs.get("SubscriptionsDeleted", 0)),
                policy=attrs.get("Policy"),
            )

        if action == "publish":
            if not topic_arn:
                return _err("topic_arn is required")
            if not message:
                return _err("message is required")
            pub_args: Dict[str, Any] = {"TopicArn": topic_arn, "Message": message}
            if subject:
                pub_args["Subject"] = subject
            if message_attributes:
                pub_args["MessageAttributes"] = message_attributes
            resp = client.publish(**pub_args)
            return _ok(
                message_id=resp["MessageId"],
                topic_arn=topic_arn,
                subject=subject,
                message_preview=message[:50] + "..." if len(message) > 50 else message,
            )

        if action == "subscribe":
            if not topic_arn:
                return _err("topic_arn is required")
            if not protocol:
                return _err("protocol is required (email, sms, sqs, http, https, lambda)")
            if not endpoint:
                return _err("endpoint is required")
            sub_args: Dict[str, Any] = {
                "TopicArn": topic_arn,
                "Protocol": protocol,
                "Endpoint": endpoint,
            }
            if filter_policy:
                import json
                sub_args["Attributes"] = {"FilterPolicy": json.dumps(filter_policy)}
            resp = client.subscribe(**sub_args)
            sub_arn = resp.get("SubscriptionArn", "")
            return _ok(
                topic_arn=topic_arn,
                protocol=protocol,
                endpoint=endpoint,
                subscription_arn=sub_arn,
                pending_confirmation=sub_arn == "pending confirmation",
            )

        if action == "subscribe_lambda":
            if not topic_arn:
                return _err("topic_arn is required")

            target_arn = lambda_arn
            if not target_arn and lambda_name:
                chk = _check_lambda_allowed(lambda_name)
                if chk:
                    return chk
                lam = _get_lambda()
                resp = lam.get_function(FunctionName=lambda_name)
                cfg = resp.get("Configuration", {}) or {}
                target_arn = cfg.get("FunctionArn")
                if not target_arn:
                    return _err("Could not resolve FunctionArn from get_function", error_type="InvalidLambdaResponse")
            if not target_arn and endpoint:
                # Allow passing a Lambda ARN via endpoint for convenience.
                target_arn = endpoint

            if not target_arn:
                return _err("lambda_arn or lambda_name (or endpoint as lambda ARN) is required")

            chk = _check_lambda_allowed(target_arn)
            if chk:
                return chk

            # Option A: add invoke permission so SNS can invoke Lambda, scoped to this topic ARN.
            lam = _get_lambda()
            topic_name_for_id = topic_arn.split(":")[-1] if topic_arn else "topic"
            fn_name_for_id = _extract_lambda_name(target_arn)
            sid = _sanitize_statement_id(statement_id or f"sns-invoke-{topic_name_for_id}-{fn_name_for_id}")
            permission_added = False
            try:
                lam.add_permission(
                    FunctionName=target_arn,
                    StatementId=sid,
                    Action="lambda:InvokeFunction",
                    Principal="sns.amazonaws.com",
                    SourceArn=topic_arn,
                )
                permission_added = True
            except Exception as e:
                # Idempotency: ignore if statement already exists.
                if "ResourceConflictException" not in str(e) and "already exists" not in str(e):
                    raise

            sub_args: Dict[str, Any] = {
                "TopicArn": topic_arn,
                "Protocol": "lambda",
                "Endpoint": target_arn,
            }
            if filter_policy:
                import json
                sub_args["Attributes"] = {"FilterPolicy": json.dumps(filter_policy)}
            resp = client.subscribe(**sub_args)
            sub_arn = resp.get("SubscriptionArn", "")
            return _ok(
                topic_arn=topic_arn,
                protocol="lambda",
                endpoint=target_arn,
                subscription_arn=sub_arn,
                pending_confirmation=sub_arn == "pending confirmation",
                permission_added=permission_added,
                statement_id=sid,
            )

        if action == "unsubscribe":
            if not subscription_arn:
                return _err("subscription_arn is required")
            client.unsubscribe(SubscriptionArn=subscription_arn)
            return _ok(subscription_arn=subscription_arn, unsubscribed=True)

        if action == "list_subscriptions":
            if topic_arn:
                resp = client.list_subscriptions_by_topic(TopicArn=topic_arn)
            else:
                resp = client.list_subscriptions()
            subs = resp.get("Subscriptions", []) or []
            formatted: List[Dict[str, Any]] = []
            for s in subs:
                t_arn = s.get("TopicArn", "")
                formatted.append({
                    "topic": t_arn.split(":")[-1] if t_arn else "",
                    "topic_arn": t_arn,
                    "protocol": s.get("Protocol"),
                    "endpoint": s.get("Endpoint"),
                    "subscription_arn": s.get("SubscriptionArn"),
                })
            return _ok(
                subscriptions=formatted,
                count=len(formatted),
                topic_filter=topic_arn,
            )

        if action == "confirm_subscription":
            if not topic_arn:
                return _err("topic_arn is required")
            if not token:
                return _err("token is required")
            resp = client.confirm_subscription(TopicArn=topic_arn, Token=token)
            return _ok(
                topic_arn=topic_arn,
                subscription_arn=resp.get("SubscriptionArn"),
                confirmed=True,
            )

        return _err(
            f"Unknown action: {action}",
            error_type="InvalidAction",
            available_actions=[
                "create_topic",
                "delete_topic",
                "list_topics",
                "get_topic_attributes",
                "publish",
                "subscribe",
                "subscribe_lambda",
                "unsubscribe",
                "list_subscriptions",
                "confirm_subscription",
            ],
        )

    except Exception as e:
        return _err(str(e), error_type=type(e).__name__, action=action)
