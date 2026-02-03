from unittest.mock import patch


def test_secrets_manager_invalid_action():
    from strands_pack.secrets_manager import secrets_manager

    res = secrets_manager(action="nope")
    assert res["success"] is False
    assert res["error_type"] == "InvalidAction"


def test_secrets_manager_get_secret_ref_does_not_return_secret():
    from strands_pack.secrets_manager import secrets_manager

    class FakeClient:
        def get_secret_value(self, SecretId):
            return {"SecretString": "SUPER_SECRET", "VersionId": "v1"}

    with patch("strands_pack.secrets_manager._get_client", return_value=FakeClient()):
        res = secrets_manager(action="get_secret_ref", secret_id="name")
    assert res["success"] is True
    assert "secret_ref" in res
    assert "SUPER_SECRET" not in str(res)


def test_secrets_manager_describe_secret_returns_metadata_only():
    from strands_pack.secrets_manager import secrets_manager

    class FakeClient:
        def describe_secret(self, SecretId):
            return {
                "ARN": "arn:aws:secretsmanager:us-east-1:123:secret:my",
                "Name": "my",
                "Description": "d",
                "Tags": [{"Key": "managed-by", "Value": "strands-pack"}],
            }

    with patch("strands_pack.secrets_manager._get_client", return_value=FakeClient()):
        res = secrets_manager(action="describe_secret", secret_id="my")
    assert res["success"] is True
    assert res["name"] == "my"
    assert "SUPER_SECRET" not in str(res)


def test_secrets_manager_tag_secret_calls_tag_and_untag():
    from strands_pack.secrets_manager import secrets_manager

    class FakeClient:
        def __init__(self):
            self.tagged = False
            self.untagged = False

        def tag_resource(self, **kwargs):
            self.tagged = True
            assert kwargs["SecretId"] == "my"
            return {}

        def untag_resource(self, **kwargs):
            self.untagged = True
            assert kwargs["SecretId"] == "my"
            return {}

    fc = FakeClient()
    with patch("strands_pack.secrets_manager._get_client", return_value=fc):
        res = secrets_manager(action="tag_secret", secret_id="my", add_tags={"a": "b"}, remove_tag_keys=["x"])
    assert res["success"] is True
    assert fc.tagged is True
    assert fc.untagged is True


def test_secrets_manager_delete_secret_requires_confirm():
    from strands_pack.secrets_manager import secrets_manager

    res = secrets_manager(action="delete_secret", secret_id="my")
    assert res["success"] is False
    assert res["error_type"] == "ConfirmationRequired"


def test_secrets_manager_delete_secret_requires_managed_tag_by_default():
    from strands_pack.secrets_manager import secrets_manager

    class FakeClient:
        def describe_secret(self, SecretId):
            return {"Tags": [{"Key": "managed-by", "Value": "someone-else"}]}

        def delete_secret(self, **kwargs):  # pragma: no cover
            return {}

    with patch("strands_pack.secrets_manager._get_client", return_value=FakeClient()):
        res = secrets_manager(action="delete_secret", secret_id="my", confirm=True)
    assert res["success"] is False
    assert res["error_type"] == "NotManaged"


