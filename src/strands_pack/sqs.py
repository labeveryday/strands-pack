"""
SQS Tool

Manage AWS SQS queues and messages.

Requires: pip install strands-pack[aws]

Actions
-------
- create_queue: Create a new SQS queue
- delete_queue: Delete an SQS queue
- list_queues: List all SQS queues
- get_queue_url: Get queue URL from queue name
- get_queue_attributes: Get queue configuration and stats
- send: Send a message to a queue
- send_batch: Send multiple messages (up to 10)
- receive: Receive messages from a queue
- delete_message: Delete a single message
- delete_message_batch: Delete multiple messages
- purge: Delete all messages from a queue
- change_visibility: Change message visibility timeout
"""

import json
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
    return boto3.client("sqs")


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
def sqs(
    action: str,
    queue_name: Optional[str] = None,
    queue_url: Optional[str] = None,
    queue_name_prefix: Optional[str] = None,
    message_body: Optional[str] = None,
    messages: Optional[List[Dict[str, Any]]] = None,
    delay_seconds: int = 0,
    message_attributes: Optional[Dict[str, Any]] = None,
    max_messages: int = 1,
    visibility_timeout: int = 30,
    wait_time_seconds: int = 0,
    receipt_handle: Optional[str] = None,
    receipt_handles: Optional[List[str]] = None,
    message_retention_period: int = 345600,
    fifo_queue: bool = False,
    content_based_deduplication: bool = False,
    tags: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Manage AWS SQS queues and messages.

    Args:
        action: The action to perform. One of:
            - "create_queue": Create a new SQS queue.
            - "delete_queue": Delete an SQS queue.
            - "list_queues": List all SQS queues.
            - "get_queue_url": Get queue URL from queue name.
            - "get_queue_attributes": Get queue configuration and stats.
            - "send": Send a message to a queue.
            - "send_batch": Send multiple messages (up to 10).
            - "receive": Receive messages from a queue.
            - "delete_message": Delete a single message.
            - "delete_message_batch": Delete multiple messages.
            - "purge": Delete all messages from a queue.
            - "change_visibility": Change message visibility timeout.
        queue_name: Name for the queue (create_queue, get_queue_url).
        queue_url: URL of the queue (most actions).
        queue_name_prefix: Prefix filter for list_queues.
        message_body: Message content to send.
        messages: List of message dicts for send_batch [{body, delay_seconds, id}].
        delay_seconds: Delay before message becomes available (0-900).
        message_attributes: Message attributes dict.
        max_messages: Max messages to receive (1-10, default 1).
        visibility_timeout: Visibility timeout in seconds (default 30).
        wait_time_seconds: Long polling wait time (0-20, default 0).
        receipt_handle: Receipt handle for delete_message/change_visibility.
        receipt_handles: List of receipt handles for delete_message_batch.
        message_retention_period: Message retention in seconds (60-1209600, default 4 days).
        fifo_queue: Create a FIFO queue (queue name must end in .fifo).
        content_based_deduplication: Enable content-based deduplication for FIFO.

    Returns:
        dict with success status and action-specific data

    Examples:
        >>> sqs(action="create_queue", queue_name="my-queue")
        >>> sqs(action="send", queue_url="https://sqs...", message_body="Hello!")
        >>> sqs(action="receive", queue_url="https://sqs...", max_messages=5, wait_time_seconds=20)
    """
    action = (action or "").strip()

    try:
        client = _get_client()
    except Exception as e:
        return _err(str(e), error_type=type(e).__name__, action=action)

    try:
        if action == "create_queue":
            if not queue_name:
                return _err("queue_name is required")
            attributes: Dict[str, str] = {
                "VisibilityTimeout": str(visibility_timeout),
                "MessageRetentionPeriod": str(message_retention_period),
            }
            if fifo_queue:
                if not queue_name.endswith(".fifo"):
                    return _err("FIFO queue name must end with .fifo")
                attributes["FifoQueue"] = "true"
                if content_based_deduplication:
                    attributes["ContentBasedDeduplication"] = "true"
            resp = client.create_queue(QueueName=queue_name, Attributes=attributes)
            qurl = resp["QueueUrl"]
            try:
                client.tag_queue(QueueUrl=qurl, Tags=aws_tags_dict(component="sqs", tags=tags))
            except Exception as e:
                return _err(
                    f"Queue created but tagging failed: {e}",
                    error_type="TaggingFailed",
                    queue_name=queue_name,
                    queue_url=qurl,
                    hint="Ensure you have sqs:TagQueue permissions.",
                )
            return _ok(
                queue_name=queue_name,
                queue_url=qurl,
                visibility_timeout=visibility_timeout,
                message_retention_period=message_retention_period,
                fifo_queue=fifo_queue,
                tagged=True,
            )

        if action == "delete_queue":
            if not queue_url:
                return _err("queue_url is required")
            client.delete_queue(QueueUrl=queue_url)
            return _ok(queue_url=queue_url, deleted=True)

        if action == "list_queues":
            list_args: Dict[str, Any] = {}
            if queue_name_prefix:
                list_args["QueueNamePrefix"] = queue_name_prefix
            resp = client.list_queues(**list_args)
            queue_urls = resp.get("QueueUrls", []) or []
            queues = []
            for url in queue_urls:
                name = url.split("/")[-1]
                queues.append({"name": name, "url": url})
            return _ok(queues=queues, count=len(queues))

        if action == "get_queue_url":
            if not queue_name:
                return _err("queue_name is required")
            resp = client.get_queue_url(QueueName=queue_name)
            return _ok(queue_name=queue_name, queue_url=resp["QueueUrl"])

        if action == "get_queue_attributes":
            if not queue_url:
                return _err("queue_url is required")
            resp = client.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["All"])
            attrs = resp.get("Attributes", {}) or {}
            return _ok(
                queue_url=queue_url,
                approximate_messages=int(attrs.get("ApproximateNumberOfMessages", 0)),
                approximate_messages_not_visible=int(attrs.get("ApproximateNumberOfMessagesNotVisible", 0)),
                approximate_messages_delayed=int(attrs.get("ApproximateNumberOfMessagesDelayed", 0)),
                visibility_timeout=int(attrs.get("VisibilityTimeout", 30)),
                message_retention_period=int(attrs.get("MessageRetentionPeriod", 345600)),
                created_timestamp=attrs.get("CreatedTimestamp"),
                last_modified_timestamp=attrs.get("LastModifiedTimestamp"),
                queue_arn=attrs.get("QueueArn"),
                fifo_queue=attrs.get("FifoQueue") == "true",
            )

        if action == "send":
            if not queue_url:
                return _err("queue_url is required")
            if not message_body:
                return _err("message_body is required")
            send_args: Dict[str, Any] = {
                "QueueUrl": queue_url,
                "MessageBody": message_body,
            }
            if delay_seconds > 0:
                send_args["DelaySeconds"] = min(delay_seconds, 900)
            if message_attributes:
                send_args["MessageAttributes"] = message_attributes
            resp = client.send_message(**send_args)
            return _ok(
                message_id=resp["MessageId"],
                queue_url=queue_url,
                delay_seconds=delay_seconds,
                message_preview=message_body[:50] + "..." if len(message_body) > 50 else message_body,
            )

        if action == "send_batch":
            if not queue_url:
                return _err("queue_url is required")
            if not messages or not isinstance(messages, list):
                return _err("messages is required (list of dicts with 'body' key)")
            if len(messages) > 10:
                return _err("send_batch supports up to 10 messages", error_type="LimitExceeded")
            entries = []
            for i, msg in enumerate(messages):
                if not isinstance(msg, dict) or "body" not in msg:
                    return _err(f"messages[{i}] must have 'body' key")
                entry: Dict[str, Any] = {
                    "Id": msg.get("id", str(i)),
                    "MessageBody": msg["body"],
                }
                if msg.get("delay_seconds"):
                    entry["DelaySeconds"] = min(int(msg["delay_seconds"]), 900)
                entries.append(entry)
            resp = client.send_message_batch(QueueUrl=queue_url, Entries=entries)
            successful = resp.get("Successful", []) or []
            failed = resp.get("Failed", []) or []
            return _ok(
                queue_url=queue_url,
                successful_count=len(successful),
                failed_count=len(failed),
                successful=[{"id": s.get("Id"), "message_id": s.get("MessageId")} for s in successful],
                failed=[{"id": f.get("Id"), "code": f.get("Code"), "message": f.get("Message")} for f in failed],
            )

        if action == "receive":
            if not queue_url:
                return _err("queue_url is required")
            resp = client.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=min(max(max_messages, 1), 10),
                VisibilityTimeout=visibility_timeout,
                WaitTimeSeconds=min(max(wait_time_seconds, 0), 20),
                AttributeNames=["All"],
                MessageAttributeNames=["All"],
            )
            msgs = resp.get("Messages", []) or []
            formatted = []
            for m in msgs:
                formatted.append({
                    "message_id": m.get("MessageId"),
                    "receipt_handle": m.get("ReceiptHandle"),
                    "body": m.get("Body"),
                    "attributes": m.get("Attributes", {}),
                    "message_attributes": m.get("MessageAttributes", {}),
                })
            return _ok(
                queue_url=queue_url,
                messages=formatted,
                count=len(formatted),
            )

        if action == "delete_message":
            if not queue_url:
                return _err("queue_url is required")
            if not receipt_handle:
                return _err("receipt_handle is required")
            client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
            return _ok(queue_url=queue_url, deleted=True)

        if action == "delete_message_batch":
            if not queue_url:
                return _err("queue_url is required")
            if not receipt_handles or not isinstance(receipt_handles, list):
                return _err("receipt_handles is required (list)")
            if len(receipt_handles) > 10:
                return _err("delete_message_batch supports up to 10 messages", error_type="LimitExceeded")
            entries = [{"Id": str(i), "ReceiptHandle": rh} for i, rh in enumerate(receipt_handles)]
            resp = client.delete_message_batch(QueueUrl=queue_url, Entries=entries)
            successful = resp.get("Successful", []) or []
            failed = resp.get("Failed", []) or []
            return _ok(
                queue_url=queue_url,
                deleted_count=len(successful),
                failed_count=len(failed),
            )

        if action == "purge":
            if not queue_url:
                return _err("queue_url is required")
            client.purge_queue(QueueUrl=queue_url)
            return _ok(queue_url=queue_url, purged=True)

        if action == "change_visibility":
            if not queue_url:
                return _err("queue_url is required")
            if not receipt_handle:
                return _err("receipt_handle is required")
            client.change_message_visibility(
                QueueUrl=queue_url,
                ReceiptHandle=receipt_handle,
                VisibilityTimeout=visibility_timeout,
            )
            return _ok(
                queue_url=queue_url,
                visibility_timeout=visibility_timeout,
                changed=True,
            )

        return _err(
            f"Unknown action: {action}",
            error_type="InvalidAction",
            available_actions=[
                "create_queue",
                "delete_queue",
                "list_queues",
                "get_queue_url",
                "get_queue_attributes",
                "send",
                "send_batch",
                "receive",
                "delete_message",
                "delete_message_batch",
                "purge",
                "change_visibility",
            ],
        )

    except Exception as e:
        return _err(str(e), error_type=type(e).__name__, action=action)
