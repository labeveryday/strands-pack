from unittest.mock import patch


def test_lambda_tool_invalid_action():
    from strands_pack.lambda_tool import lambda_tool

    with patch("strands_pack.lambda_tool._get_client"):
        res = lambda_tool(action="nope")
    assert res["success"] is False
    assert res["error_type"] == "InvalidAction"


def test_lambda_tool_prefix_guard(monkeypatch):
    from strands_pack.lambda_tool import lambda_tool

    monkeypatch.setenv("STRANDS_PACK_LAMBDA_PREFIX", "agent-")

    class FakeClient:
        def get_function(self, **kwargs):
            return {}

    with patch("strands_pack.lambda_tool._get_client", return_value=FakeClient()):
        res = lambda_tool(action="get_function", function_name="badname")
    assert res["success"] is False
    assert res["error_type"] == "NameNotAllowed"


def test_lambda_tool_create_function_requires_role_by_default(tmp_path, monkeypatch):
    """Without role_arn and without auto_create_role opt-in, creation should fail."""
    from strands_pack.lambda_tool import lambda_tool

    monkeypatch.delenv("STRANDS_PACK_LAMBDA_ROLE_ALLOWLIST", raising=False)
    monkeypatch.delenv("STRANDS_PACK_LAMBDA_ALLOW_AUTO_ROLE_CREATE", raising=False)

    zip_path = tmp_path / "f.zip"
    zip_path.write_bytes(b"PK\x05\x06" + b"\x00" * 18)  # empty zip

    class FakeLambda:
        def create_function(self, **kwargs):  # pragma: no cover
            return {"FunctionArn": "arn"}

    with patch("strands_pack.lambda_tool._get_client", return_value=FakeLambda()):
        res = lambda_tool(
            action="create_function_zip",
            function_name="agent-fn",
            handler="index.handler",
            runtime="python3.11",
            zip_path=str(zip_path),
        )
    assert res["success"] is False
    assert res["error_type"] == "RoleRequired"


def test_lambda_tool_create_function_blocks_auto_role_when_allowlist_set(tmp_path, monkeypatch):
    """Allowlist implies production posture; auto role creation must be blocked."""
    from strands_pack.lambda_tool import lambda_tool

    monkeypatch.setenv("STRANDS_PACK_LAMBDA_ROLE_ALLOWLIST", "arn:aws:iam::123:role/allowed")
    monkeypatch.setenv("STRANDS_PACK_LAMBDA_ALLOW_AUTO_ROLE_CREATE", "true")

    zip_path = tmp_path / "f.zip"
    zip_path.write_bytes(b"PK\x05\x06" + b"\x00" * 18)

    class FakeLambda:
        def create_function(self, **kwargs):  # pragma: no cover
            return {"FunctionArn": "arn"}

    with patch("strands_pack.lambda_tool._get_client", return_value=FakeLambda()):
        res = lambda_tool(
            action="create_function_zip",
            function_name="agent-fn",
            handler="index.handler",
            runtime="python3.11",
            zip_path=str(zip_path),
            auto_create_role=True,
        )
    assert res["success"] is False
    assert res["error_type"] == "RoleRequired"


def test_lambda_tool_create_function_auto_creates_basic_role(tmp_path, monkeypatch):
    """With explicit opt-in, tool can auto-create logs-only role when no allowlist is set."""
    from strands_pack.lambda_tool import lambda_tool

    monkeypatch.delenv("STRANDS_PACK_LAMBDA_ROLE_ALLOWLIST", raising=False)
    monkeypatch.setenv("STRANDS_PACK_LAMBDA_ALLOW_AUTO_ROLE_CREATE", "true")

    zip_path = tmp_path / "f.zip"
    zip_path.write_bytes(b"PK\x05\x06" + b"\x00" * 18)

    class FakeLambda:
        def create_function(self, **kwargs):
            assert "Role" in kwargs
            return {"FunctionArn": "arn:aws:lambda:::function:agent-fn"}

    class FakeIam:
        def __init__(self):
            self.created = False
            self.attached = False

        def create_role(self, **kwargs):
            self.created = True
            return {"Role": {"Arn": "arn:aws:iam::123:role/strands-agent-agent-fn-basic"}}

        def get_role(self, **kwargs):  # pragma: no cover
            return {"Role": {"Arn": "arn:aws:iam::123:role/strands-agent-agent-fn-basic"}}

        def attach_role_policy(self, **kwargs):
            self.attached = True
            return {}

    iam = FakeIam()
    with patch("strands_pack.lambda_tool._get_client", return_value=FakeLambda()), patch(
        "strands_pack.lambda_tool._get_iam", return_value=iam
    ):
        res = lambda_tool(
            action="create_function_zip",
            function_name="agent-fn",
            handler="index.handler",
            runtime="python3.11",
            zip_path=str(zip_path),
            auto_create_role=True,
        )

    assert res["success"] is True
    assert res["role_auto_created"] is True
    assert iam.created is True
    assert iam.attached is True


def test_lambda_tool_create_event_source_mapping_requires_prefix(monkeypatch):
    """Event source mapping creation should enforce lambda prefix guard."""
    from strands_pack.lambda_tool import lambda_tool

    monkeypatch.setenv("STRANDS_PACK_LAMBDA_PREFIX", "agent-")

    class FakeClient:
        def create_event_source_mapping(self, **kwargs):  # pragma: no cover
            return {}

    with patch("strands_pack.lambda_tool._get_client", return_value=FakeClient()):
        res = lambda_tool(
            action="create_event_source_mapping",
            function_name="not-agent",
            event_source_arn="arn:aws:sqs:us-east-1:123456789012:my-queue",
        )
    assert res["success"] is False
    assert res["error_type"] == "NameNotAllowed"


def test_lambda_tool_create_event_source_mapping_success(monkeypatch):
    from strands_pack.lambda_tool import lambda_tool

    monkeypatch.setenv("STRANDS_PACK_LAMBDA_PREFIX", "agent-")

    class FakeClient:
        def create_event_source_mapping(self, **kwargs):
            assert kwargs["FunctionName"] == "agent-worker"
            assert kwargs["EventSourceArn"].startswith("arn:aws:sqs:")
            return {
                "UUID": "uuid-123",
                "FunctionArn": "arn:aws:lambda:us-east-1:123:function:agent-worker",
                "EventSourceArn": kwargs["EventSourceArn"],
                "State": "Creating",
                "BatchSize": kwargs.get("BatchSize"),
                "MaximumBatchingWindowInSeconds": kwargs.get("MaximumBatchingWindowInSeconds"),
            }

    with patch("strands_pack.lambda_tool._get_client", return_value=FakeClient()):
        res = lambda_tool(
            action="create_event_source_mapping",
            function_name="agent-worker",
            event_source_arn="arn:aws:sqs:us-east-1:123456789012:my-queue",
            batch_size=10,
            maximum_batching_window_seconds=0,
            report_batch_item_failures=True,
        )
    assert res["success"] is True
    assert res["created"] is True
    assert res["uuid"] == "uuid-123"


def test_lambda_tool_delete_event_source_mapping_requires_confirm():
    from strands_pack.lambda_tool import lambda_tool

    class FakeClient:
        def delete_event_source_mapping(self, **kwargs):  # pragma: no cover
            return {}

    with patch("strands_pack.lambda_tool._get_client", return_value=FakeClient()):
        res = lambda_tool(action="delete_event_source_mapping", uuid="uuid-123")
    assert res["success"] is False
    assert res["error_type"] == "ConfirmationRequired"


