from unittest.mock import patch


def test_apigateway_rest_name_prefix_guard(monkeypatch):
    from strands_pack.apigateway_rest_api import apigateway_rest_api

    monkeypatch.setenv("STRANDS_PACK_API_PREFIX", "agent-")

    class FakeApiGw:
        def create_rest_api(self, **kwargs):
            return {"id": "r1"}

    with patch("strands_pack.apigateway_rest_api._get_apigw", return_value=FakeApiGw()):
        res = apigateway_rest_api(action="create_rest_api", name="bad")
    assert res["success"] is False
    assert res["error_type"] == "NameNotAllowed"


def test_apigateway_rest_create_rest_lambda_api_creates_key_and_plan(monkeypatch):
    from strands_pack.apigateway_rest_api import apigateway_rest_api

    monkeypatch.setenv("STRANDS_PACK_API_PREFIX", "agent-")
    monkeypatch.setenv("STRANDS_PACK_LAMBDA_PREFIX", "agent-")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCOUNT_ID", "123456789012")

    class FakeApiGw:
        def __init__(self):
            self.calls = []

        def create_rest_api(self, **kwargs):
            self.calls.append(("create_rest_api", kwargs))
            return {"id": "api123"}

        def tag_resource(self, **kwargs):
            self.calls.append(("tag_resource", kwargs))
            return {}

        def get_resources(self, **kwargs):
            # Root only
            return {"items": [{"id": "root", "path": "/"}]}

        def create_resource(self, **kwargs):
            self.calls.append(("create_resource", kwargs))
            return {"id": "res1"}

        def put_method(self, **kwargs):
            self.calls.append(("put_method", kwargs))
            return {}

        def put_integration(self, **kwargs):
            self.calls.append(("put_integration", kwargs))
            return {}

        def create_deployment(self, **kwargs):
            self.calls.append(("create_deployment", kwargs))
            return {"id": "dep1"}

        def create_usage_plan(self, **kwargs):
            self.calls.append(("create_usage_plan", kwargs))
            return {"id": "plan1"}

        def create_api_key(self, **kwargs):
            self.calls.append(("create_api_key", kwargs))
            return {"id": "key1"}

        def get_api_key(self, **kwargs):
            self.calls.append(("get_api_key", kwargs))
            return {"id": "key1", "value": "secret-value"}

        def create_usage_plan_key(self, **kwargs):
            self.calls.append(("create_usage_plan_key", kwargs))
            return {"id": "upk1"}

    class FakeLambda:
        def __init__(self):
            self.calls = []

        def add_permission(self, **kwargs):
            self.calls.append(kwargs)
            return {}

    gw = FakeApiGw()
    lam = FakeLambda()

    with patch("strands_pack.apigateway_rest_api._get_apigw", return_value=gw), patch(
        "strands_pack.apigateway_rest_api._get_lambda", return_value=lam
    ):
        res = apigateway_rest_api(
            action="create_rest_lambda_api",
            name="agent-api",
            path="/hook",
            method="ANY",
            lambda_arn="arn:aws:lambda:us-east-1:123456789012:function:agent-fn",
            stage_name="prod",
            throttle_rate_limit=2.0,
            throttle_burst_limit=5,
        )

    assert res["success"] is True
    assert res["rest_api_id"] == "api123"
    assert res["api_key_value"] == "secret-value"
    assert res["usage_plan_id"] == "plan1"
    assert lam.calls, "expected lambda add_permission"
    assert lam.calls[0]["Principal"] == "apigateway.amazonaws.com"
    # Default in the high-level creator is stage-scoped permission
    assert "/prod/" in lam.calls[0]["SourceArn"]
    assert any(c[0] == "tag_resource" for c in gw.calls)


