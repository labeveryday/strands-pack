from unittest.mock import patch


def test_list_managed_resources_filters_by_tag():
    from strands_pack.managed_resources import list_managed_resources

    class FakeLambda:
        def list_functions(self, **kwargs):
            return {"Functions": [{"FunctionName": "agent-a", "FunctionArn": "arn:aws:lambda:us-east-1:123:function:agent-a"}]}

        def list_tags(self, Resource):
            return {"Tags": {"managed-by": "strands-pack", "env": "prod"}}

    class FakeS3:
        def list_buckets(self):
            from datetime import datetime, timezone

            return {"Buckets": [{"Name": "b1", "CreationDate": datetime(2025, 1, 1, tzinfo=timezone.utc)}]}

        def get_bucket_tagging(self, Bucket):
            return {"TagSet": [{"Key": "managed-by", "Value": "strands-pack"}, {"Key": "env", "Value": "dev"}]}

    def fake_get_client(name):
        if name == "lambda":
            return FakeLambda()
        if name == "s3":
            return FakeS3()
        # Unused services return dummy clients.
        class Dummy:
            pass

        return Dummy()

    with patch("strands_pack.managed_resources._get_client", side_effect=fake_get_client), patch(
        "strands_pack.managed_resources._session_region", return_value="us-east-1"
    ):
        res = list_managed_resources(services=["lambda", "s3"], match_tags={"env": "prod"}, max_per_service=10)

    assert res["success"] is True
    assert len(res["results"]["lambda"]) == 1
    assert len(res["results"]["s3"]) == 0  # env mismatch


def test_list_managed_resources_invalid_service():
    from strands_pack.managed_resources import list_managed_resources

    res = list_managed_resources(services=["nope"])
    assert res["success"] is False
    assert res["error_type"] == "InvalidParameterValue"

