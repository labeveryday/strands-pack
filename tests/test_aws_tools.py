"""Tests for AWS SNS and SQS tools."""

from unittest.mock import MagicMock, patch


# =============================================================================
# Boto3 Import Error Tests
# =============================================================================

class TestBoto3ImportErrors:
    """Test that tools handle missing boto3 gracefully."""

    @patch("strands_pack.sns._get_client")
    def test_sns_returns_error_on_import_failure(self, mock_get_client):
        """Test that sns returns error dict when boto3 is missing."""
        from strands_pack import sns

        mock_get_client.side_effect = ImportError("boto3 not installed. Run: pip install strands-pack[aws]")

        result = sns(action="create_topic", topic_name="test-topic")

        assert result["success"] is False
        assert "boto3 not installed" in result["error"]

    @patch("strands_pack.sqs._get_client")
    def test_sqs_returns_error_on_import_failure(self, mock_get_client):
        """Test that sqs returns error dict when boto3 is missing."""
        from strands_pack import sqs

        mock_get_client.side_effect = ImportError("boto3 not installed. Run: pip install strands-pack[aws]")

        result = sqs(action="create_queue", queue_name="test-queue")

        assert result["success"] is False
        assert "boto3 not installed" in result["error"]


# =============================================================================
# SNS Tools Tests with Mocking
# =============================================================================

class TestSNSCreateTopic:
    """Test sns create_topic action."""

    @patch("strands_pack.sns._get_client")
    def test_create_topic_success(self, mock_get_client):
        """Test successful topic creation."""
        mock_client = MagicMock()
        mock_client.create_topic.return_value = {
            "TopicArn": "arn:aws:sns:us-east-1:123456789012:my-topic"
        }
        mock_get_client.return_value = mock_client

        from strands_pack import sns

        result = sns(action="create_topic", topic_name="my-topic")

        assert result["success"] is True
        assert result["topic_name"] == "my-topic"
        assert "arn:aws:sns" in result["topic_arn"]

    @patch("strands_pack.sns._get_client")
    def test_create_topic_with_display_name(self, mock_get_client):
        """Test topic creation with display name."""
        mock_client = MagicMock()
        mock_client.create_topic.return_value = {
            "TopicArn": "arn:aws:sns:us-east-1:123456789012:alerts"
        }
        mock_get_client.return_value = mock_client

        from strands_pack import sns

        result = sns(action="create_topic", topic_name="alerts", display_name="System Alerts")

        assert result["success"] is True
        assert result["display_name"] == "System Alerts"
        mock_client.create_topic.assert_called_once()
        call_kwargs = mock_client.create_topic.call_args[1]
        assert call_kwargs["Name"] == "alerts"
        assert call_kwargs["Attributes"]["DisplayName"] == "System Alerts"
        assert "Tags" in call_kwargs
        assert any(t.get("Key") == "managed-by" and t.get("Value") == "strands-pack" for t in call_kwargs["Tags"])


class TestSNSDeleteTopic:
    """Test sns delete_topic action."""

    @patch("strands_pack.sns._get_client")
    def test_delete_topic_success(self, mock_get_client):
        """Test successful topic deletion."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        from strands_pack import sns

        topic_arn = "arn:aws:sns:us-east-1:123456789012:my-topic"
        result = sns(action="delete_topic", topic_arn=topic_arn)

        assert result["success"] is True
        assert result["deleted"] is True
        mock_client.delete_topic.assert_called_once_with(TopicArn=topic_arn)


class TestSNSListTopics:
    """Test sns list_topics action."""

    @patch("strands_pack.sns._get_client")
    def test_list_topics_success(self, mock_get_client):
        """Test successful topic listing."""
        mock_client = MagicMock()
        mock_client.list_topics.return_value = {
            "Topics": [
                {"TopicArn": "arn:aws:sns:us-east-1:123456789012:topic1"},
                {"TopicArn": "arn:aws:sns:us-east-1:123456789012:topic2"},
            ]
        }
        mock_get_client.return_value = mock_client

        from strands_pack import sns

        result = sns(action="list_topics")

        assert result["success"] is True
        assert result["count"] == 2
        assert len(result["topics"]) == 2

    @patch("strands_pack.sns._get_client")
    def test_list_topics_empty(self, mock_get_client):
        """Test listing topics when none exist."""
        mock_client = MagicMock()
        mock_client.list_topics.return_value = {"Topics": []}
        mock_get_client.return_value = mock_client

        from strands_pack import sns

        result = sns(action="list_topics")
        assert result["success"] is True
        assert result["count"] == 0


class TestSNSPublish:
    """Test sns publish action."""

    @patch("strands_pack.sns._get_client")
    def test_publish_success(self, mock_get_client):
        """Test successful message publishing."""
        mock_client = MagicMock()
        mock_client.publish.return_value = {"MessageId": "msg-123456"}
        mock_get_client.return_value = mock_client

        from strands_pack import sns

        topic_arn = "arn:aws:sns:us-east-1:123456789012:my-topic"
        result = sns(action="publish", topic_arn=topic_arn, message="Hello World!")

        assert result["success"] is True
        assert result["message_id"] == "msg-123456"
        assert "Hello World!" in result["message_preview"]

    @patch("strands_pack.sns._get_client")
    def test_publish_with_subject(self, mock_get_client):
        """Test publishing message with subject."""
        mock_client = MagicMock()
        mock_client.publish.return_value = {"MessageId": "msg-789"}
        mock_get_client.return_value = mock_client

        from strands_pack import sns

        topic_arn = "arn:aws:sns:us-east-1:123456789012:alerts"
        result = sns(action="publish", topic_arn=topic_arn, message="Server down!", subject="Critical Alert")

        assert result["subject"] == "Critical Alert"
        mock_client.publish.assert_called_once_with(
            TopicArn=topic_arn,
            Message="Server down!",
            Subject="Critical Alert"
        )


class TestSNSSubscribe:
    """Test sns subscribe action."""

    @patch("strands_pack.sns._get_client")
    def test_subscribe_success(self, mock_get_client):
        """Test successful subscription creation."""
        mock_client = MagicMock()
        mock_client.subscribe.return_value = {
            "SubscriptionArn": "arn:aws:sns:us-east-1:123456789012:alerts:sub123"
        }
        mock_get_client.return_value = mock_client

        from strands_pack import sns

        topic_arn = "arn:aws:sns:us-east-1:123456789012:alerts"
        result = sns(action="subscribe", topic_arn=topic_arn, protocol="email", endpoint="user@example.com")

        assert result["success"] is True
        assert result["protocol"] == "email"
        assert result["endpoint"] == "user@example.com"
        assert result["pending_confirmation"] is False


class TestSNSSubscribeLambda:
    """Test sns subscribe_lambda action (Option A)."""

    @patch("strands_pack.sns._get_lambda")
    @patch("strands_pack.sns._get_client")
    def test_subscribe_lambda_adds_permission_and_subscribes(self, mock_get_client, mock_get_lambda):
        mock_sns = MagicMock()
        mock_sns.subscribe.return_value = {"SubscriptionArn": "arn:aws:sns:us-east-1:123456789012:alerts:sub123"}
        mock_get_client.return_value = mock_sns

        mock_lambda = MagicMock()
        mock_lambda.get_function.return_value = {
            "Configuration": {"FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:agent-handler"}
        }
        mock_get_lambda.return_value = mock_lambda

        from strands_pack import sns

        topic_arn = "arn:aws:sns:us-east-1:123456789012:alerts"
        res = sns(action="subscribe_lambda", topic_arn=topic_arn, lambda_name="agent-handler")

        assert res["success"] is True
        assert res["protocol"] == "lambda"
        assert "arn:aws:lambda" in res["endpoint"]
        assert res["permission_added"] in (True, False)

        mock_lambda.add_permission.assert_called_once()
        _, kwargs = mock_lambda.add_permission.call_args
        assert kwargs["Principal"] == "sns.amazonaws.com"
        assert kwargs["SourceArn"] == topic_arn
        assert kwargs["Action"] == "lambda:InvokeFunction"

        mock_sns.subscribe.assert_called_once()


class TestSNSUnsubscribe:
    """Test sns unsubscribe action."""

    @patch("strands_pack.sns._get_client")
    def test_unsubscribe_success(self, mock_get_client):
        """Test successful subscription deletion."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        from strands_pack import sns

        sub_arn = "arn:aws:sns:us-east-1:123456789012:topic:sub123"
        result = sns(action="unsubscribe", subscription_arn=sub_arn)

        assert result["success"] is True
        assert result["unsubscribed"] is True
        mock_client.unsubscribe.assert_called_once_with(SubscriptionArn=sub_arn)


class TestSNSListSubscriptions:
    """Test sns list_subscriptions action."""

    @patch("strands_pack.sns._get_client")
    def test_list_subscriptions_all(self, mock_get_client):
        """Test listing all subscriptions."""
        mock_client = MagicMock()
        mock_client.list_subscriptions.return_value = {
            "Subscriptions": [
                {
                    "SubscriptionArn": "arn:aws:sns:us-east-1:123456789012:topic1:abc",
                    "Protocol": "email",
                    "Endpoint": "user@example.com",
                    "TopicArn": "arn:aws:sns:us-east-1:123456789012:topic1"
                }
            ]
        }
        mock_get_client.return_value = mock_client

        from strands_pack import sns

        result = sns(action="list_subscriptions")

        assert result["success"] is True
        assert result["count"] == 1
        assert result["subscriptions"][0]["protocol"] == "email"

    @patch("strands_pack.sns._get_client")
    def test_list_subscriptions_by_topic(self, mock_get_client):
        """Test listing subscriptions filtered by topic."""
        mock_client = MagicMock()
        mock_client.list_subscriptions_by_topic.return_value = {
            "Subscriptions": [
                {
                    "SubscriptionArn": "arn:aws:sns:us-east-1:123456789012:alerts:xyz",
                    "Protocol": "sqs",
                    "Endpoint": "arn:aws:sqs:us-east-1:123456789012:alert-queue",
                    "TopicArn": "arn:aws:sns:us-east-1:123456789012:alerts"
                }
            ]
        }
        mock_get_client.return_value = mock_client

        from strands_pack import sns

        topic_arn = "arn:aws:sns:us-east-1:123456789012:alerts"
        result = sns(action="list_subscriptions", topic_arn=topic_arn)

        assert result["success"] is True
        mock_client.list_subscriptions_by_topic.assert_called_once_with(TopicArn=topic_arn)


class TestSNSGetTopicAttributes:
    """Test sns get_topic_attributes action."""

    @patch("strands_pack.sns._get_client")
    def test_get_topic_attributes_success(self, mock_get_client):
        """Test getting topic attributes."""
        mock_client = MagicMock()
        mock_client.get_topic_attributes.return_value = {
            "Attributes": {
                "DisplayName": "My Topic",
                "Owner": "123456789012",
                "SubscriptionsConfirmed": "5",
                "SubscriptionsPending": "1",
                "SubscriptionsDeleted": "0",
            }
        }
        mock_get_client.return_value = mock_client

        from strands_pack import sns

        topic_arn = "arn:aws:sns:us-east-1:123456789012:my-topic"
        result = sns(action="get_topic_attributes", topic_arn=topic_arn)

        assert result["success"] is True
        assert result["subscriptions_confirmed"] == 5


class TestSNSUnknownAction:
    """Test sns with unknown action."""

    def test_unknown_action(self):
        """Test that unknown action returns error."""
        from strands_pack import sns

        result = sns(action="unknown_action")

        assert result["success"] is False
        assert "Unknown action" in result["error"]
        assert "available_actions" in result


# =============================================================================
# SQS Tools Tests with Mocking
# =============================================================================

class TestSQSCreateQueue:
    """Test sqs create_queue action."""

    @patch("strands_pack.sqs._get_client")
    def test_create_queue_success(self, mock_get_client):
        """Test successful queue creation."""
        mock_client = MagicMock()
        mock_client.create_queue.return_value = {
            "QueueUrl": "https://sqs.us-east-1.amazonaws.com/123456789012/my-queue"
        }
        mock_get_client.return_value = mock_client

        from strands_pack import sqs

        result = sqs(action="create_queue", queue_name="my-queue")

        assert result["success"] is True
        assert result["queue_name"] == "my-queue"
        assert "https://sqs" in result["queue_url"]
        assert mock_client.tag_queue.called

    @patch("strands_pack.sqs._get_client")
    def test_create_queue_with_custom_settings(self, mock_get_client):
        """Test queue creation with custom settings."""
        mock_client = MagicMock()
        mock_client.create_queue.return_value = {
            "QueueUrl": "https://sqs.us-east-1.amazonaws.com/123456789012/priority-queue"
        }
        mock_get_client.return_value = mock_client

        from strands_pack import sqs

        result = sqs(action="create_queue", queue_name="priority-queue", visibility_timeout=60, message_retention_period=86400)

        assert result["visibility_timeout"] == 60
        assert result["message_retention_period"] == 86400


class TestSQSDeleteQueue:
    """Test sqs delete_queue action."""

    @patch("strands_pack.sqs._get_client")
    def test_delete_queue_success(self, mock_get_client):
        """Test successful queue deletion."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        from strands_pack import sqs

        queue_url = "https://sqs.us-east-1.amazonaws.com/123456789012/my-queue"
        result = sqs(action="delete_queue", queue_url=queue_url)

        assert result["success"] is True
        assert result["deleted"] is True
        mock_client.delete_queue.assert_called_once_with(QueueUrl=queue_url)


class TestSQSListQueues:
    """Test sqs list_queues action."""

    @patch("strands_pack.sqs._get_client")
    def test_list_queues_success(self, mock_get_client):
        """Test successful queue listing."""
        mock_client = MagicMock()
        mock_client.list_queues.return_value = {
            "QueueUrls": [
                "https://sqs.us-east-1.amazonaws.com/123456789012/queue1",
                "https://sqs.us-east-1.amazonaws.com/123456789012/queue2",
            ]
        }
        mock_get_client.return_value = mock_client

        from strands_pack import sqs

        result = sqs(action="list_queues")

        assert result["success"] is True
        assert result["count"] == 2

    @patch("strands_pack.sqs._get_client")
    def test_list_queues_with_prefix(self, mock_get_client):
        """Test listing queues with prefix filter."""
        mock_client = MagicMock()
        mock_client.list_queues.return_value = {
            "QueueUrls": [
                "https://sqs.us-east-1.amazonaws.com/123456789012/prod-orders",
                "https://sqs.us-east-1.amazonaws.com/123456789012/prod-events",
            ]
        }
        mock_get_client.return_value = mock_client

        from strands_pack import sqs

        result = sqs(action="list_queues", queue_name_prefix="prod-")

        assert result["success"] is True
        mock_client.list_queues.assert_called_once_with(QueueNamePrefix="prod-")


class TestSQSSend:
    """Test sqs send action."""

    @patch("strands_pack.sqs._get_client")
    def test_send_success(self, mock_get_client):
        """Test successful message sending."""
        mock_client = MagicMock()
        mock_client.send_message.return_value = {"MessageId": "msg-123"}
        mock_get_client.return_value = mock_client

        from strands_pack import sqs

        queue_url = "https://sqs.us-east-1.amazonaws.com/123456789012/my-queue"
        result = sqs(action="send", queue_url=queue_url, message_body="Hello World!")

        assert result["success"] is True
        assert result["message_id"] == "msg-123"
        assert "Hello World!" in result["message_preview"]

    @patch("strands_pack.sqs._get_client")
    def test_send_with_delay(self, mock_get_client):
        """Test sending message with delay."""
        mock_client = MagicMock()
        mock_client.send_message.return_value = {"MessageId": "msg-456"}
        mock_get_client.return_value = mock_client

        from strands_pack import sqs

        queue_url = "https://sqs.us-east-1.amazonaws.com/123456789012/my-queue"
        result = sqs(action="send", queue_url=queue_url, message_body="Delayed message", delay_seconds=60)

        assert result["delay_seconds"] == 60


class TestSQSReceive:
    """Test sqs receive action."""

    @patch("strands_pack.sqs._get_client")
    def test_receive_success(self, mock_get_client):
        """Test successful message receiving."""
        mock_client = MagicMock()
        mock_client.receive_message.return_value = {
            "Messages": [
                {
                    "MessageId": "msg-abc",
                    "ReceiptHandle": "receipt-123",
                    "Body": "Test message content",
                    "Attributes": {"SentTimestamp": "1234567890"}
                }
            ]
        }
        mock_get_client.return_value = mock_client

        from strands_pack import sqs

        queue_url = "https://sqs.us-east-1.amazonaws.com/123456789012/my-queue"
        result = sqs(action="receive", queue_url=queue_url)

        assert result["count"] == 1
        assert result["messages"][0]["message_id"] == "msg-abc"
        assert result["messages"][0]["body"] == "Test message content"


class TestSQSPurge:
    """Test sqs purge action."""

    @patch("strands_pack.sqs._get_client")
    def test_purge_success(self, mock_get_client):
        """Test successful queue purge."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        from strands_pack import sqs

        queue_url = "https://sqs.us-east-1.amazonaws.com/123456789012/my-queue"
        result = sqs(action="purge", queue_url=queue_url)

        assert result["success"] is True
        assert result["purged"] is True
        mock_client.purge_queue.assert_called_once_with(QueueUrl=queue_url)


class TestSQSGetQueueAttributes:
    """Test sqs get_queue_attributes action."""

    @patch("strands_pack.sqs._get_client")
    def test_get_queue_attributes_success(self, mock_get_client):
        """Test getting queue attributes."""
        mock_client = MagicMock()
        mock_client.get_queue_attributes.return_value = {
            "Attributes": {
                "ApproximateNumberOfMessages": "5",
                "ApproximateNumberOfMessagesNotVisible": "2",
                "ApproximateNumberOfMessagesDelayed": "1",
                "VisibilityTimeout": "30",
                "MessageRetentionPeriod": "345600",
            }
        }
        mock_get_client.return_value = mock_client

        from strands_pack import sqs

        queue_url = "https://sqs.us-east-1.amazonaws.com/123456789012/my-queue"
        result = sqs(action="get_queue_attributes", queue_url=queue_url)

        assert result["approximate_messages"] == 5
        assert result["approximate_messages_not_visible"] == 2
        assert result["approximate_messages_delayed"] == 1


class TestSQSDeleteMessage:
    """Test sqs delete_message action."""

    @patch("strands_pack.sqs._get_client")
    def test_delete_message_success(self, mock_get_client):
        """Test successful message deletion."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        from strands_pack import sqs

        queue_url = "https://sqs.us-east-1.amazonaws.com/123456789012/my-queue"
        result = sqs(action="delete_message", queue_url=queue_url, receipt_handle="handle-123")

        assert result["success"] is True
        assert result["deleted"] is True
        mock_client.delete_message.assert_called_once()


class TestSQSDeleteMessageBatch:
    """Test sqs delete_message_batch action."""

    @patch("strands_pack.sqs._get_client")
    def test_delete_message_batch_success(self, mock_get_client):
        """Test successful batch message deletion."""
        mock_client = MagicMock()
        mock_client.delete_message_batch.return_value = {
            "Successful": [{"Id": "0"}, {"Id": "1"}, {"Id": "2"}],
            "Failed": []
        }
        mock_get_client.return_value = mock_client

        from strands_pack import sqs

        queue_url = "https://sqs.us-east-1.amazonaws.com/123456789012/my-queue"
        result = sqs(action="delete_message_batch", queue_url=queue_url, receipt_handles=["h1", "h2", "h3"])

        assert result["success"] is True
        assert result["deleted_count"] == 3
        assert result["failed_count"] == 0


class TestSQSUnknownAction:
    """Test sqs with unknown action."""

    def test_unknown_action(self):
        """Test that unknown action returns error."""
        from strands_pack import sqs

        result = sqs(action="unknown_action")

        assert result["success"] is False
        assert "Unknown action" in result["error"]
        assert "available_actions" in result
