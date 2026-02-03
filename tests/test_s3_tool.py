from unittest.mock import patch


def test_s3_invalid_action_returns_error():
    from strands_pack.s3 import s3

    # Test invalid action - may return import error or invalid action error
    res = s3(action="nope")
    assert res["success"] is False


def test_s3_put_text_validates_args():
    from strands_pack.s3 import s3

    class FakeClient:
        def put_object(self, **kwargs):
            return {}

    with patch("strands_pack.s3._get_client", return_value=FakeClient()):
        res = s3(action="put_text", bucket="", key="k", text="hi")
    assert res["success"] is False
    assert "bucket" in res["error"]


def test_s3_head_object_returns_metadata():
    from datetime import datetime, timezone
    from strands_pack.s3 import s3

    class FakeClient:
        def head_object(self, **kwargs):
            return {
                "ContentLength": 123,
                "ContentType": "text/plain",
                "ETag": '"abc"',
                "LastModified": datetime(2025, 1, 1, tzinfo=timezone.utc),
                "Metadata": {"x": "y"},
            }

    with patch("strands_pack.s3._get_client", return_value=FakeClient()):
        res = s3(action="head_object", bucket="b", key="k")
    assert res["success"] is True
    assert res["size"] == 123
    assert res["content_type"] == "text/plain"


def test_s3_copy_object_validates_args():
    from strands_pack.s3 import s3

    class FakeClient:
        def copy_object(self, **kwargs):
            return {}

    with patch("strands_pack.s3._get_client", return_value=FakeClient()):
        res = s3(action="copy_object", bucket="b", key="dst", source_bucket="", source_key="src")
    assert res["success"] is False
    assert "source_bucket" in res["error"]


def test_s3_create_bucket_calls_client():
    from strands_pack.s3 import s3

    class FakeClient:
        def __init__(self):
            self.calls = []

        def create_bucket(self, **kwargs):
            self.calls.append(kwargs)
            return {}

        def put_bucket_tagging(self, **kwargs):
            # Mock tagging call
            return {}

    client = FakeClient()
    with patch("strands_pack.s3._get_client", return_value=client):
        res = s3(action="create_bucket", bucket="my-bucket", region="us-east-1")
    assert res["success"] is True
    assert client.calls and client.calls[0]["Bucket"] == "my-bucket"


def test_s3_delete_bucket_requires_confirm():
    from strands_pack.s3 import s3

    class FakeClient:
        def delete_bucket(self, **kwargs):
            return {}

    with patch("strands_pack.s3._get_client", return_value=FakeClient()):
        res = s3(action="delete_bucket", bucket="b")
    assert res["success"] is False
    assert res.get("error_type") == "ConfirmationRequired"


def test_s3_add_lambda_trigger_calls_permission_and_notification(monkeypatch):
    from strands_pack.s3 import s3

    monkeypatch.setenv("STRANDS_PACK_LAMBDA_PREFIX", "agent-")

    class FakeS3:
        def __init__(self):
            self.notif_calls = []

        def put_bucket_notification_configuration(self, **kwargs):
            self.notif_calls.append(kwargs)
            return {}

    class FakeLambda:
        def __init__(self):
            self.perm_calls = []

        def add_permission(self, **kwargs):
            self.perm_calls.append(kwargs)
            return {}

    s3c = FakeS3()
    lam = FakeLambda()

    with patch("strands_pack.s3._get_client", return_value=s3c), patch("strands_pack.s3._get_lambda", return_value=lam):
        res = s3(
            action="add_lambda_trigger",
            bucket="b",
            lambda_arn="arn:aws:lambda:us-east-1:123:function:agent-fn",
            prefix="in/",
        )

    assert res["success"] is True
    assert lam.perm_calls
    assert s3c.notif_calls


