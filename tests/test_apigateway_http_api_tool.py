from unittest.mock import patch


def test_apigateway_name_prefix_guard(monkeypatch):
    from strands_pack.apigateway_http_api import apigateway_http_api

    monkeypatch.setenv("STRANDS_PACK_API_PREFIX", "agent-")

    class FakeApiGw:
        def create_api(self, **kwargs):
            return {"ApiId": "a", "ApiEndpoint": "https://x"}

    with patch("strands_pack.apigateway_http_api._get_apigw", return_value=FakeApiGw()):
        res = apigateway_http_api(action="create_http_api", name="bad")
    assert res["success"] is False
    assert res["error_type"] == "NameNotAllowed"


def test_apigateway_add_lambda_route_auto_adds_permission(monkeypatch):
    from strands_pack.apigateway_http_api import apigateway_http_api

    monkeypatch.setenv("STRANDS_PACK_LAMBDA_PREFIX", "agent-")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCOUNT_ID", "123456789012")

    class FakeApiGw:
        def create_integration(self, **kwargs):
            return {"IntegrationId": "i"}

        def create_route(self, **kwargs):
            return {"RouteId": "r"}

    class FakeLambda:
        def __init__(self):
            self.calls = []

        def add_permission(self, **kwargs):
            self.calls.append(kwargs)
            return {}

    lam = FakeLambda()
    with patch("strands_pack.apigateway_http_api._get_apigw", return_value=FakeApiGw()), patch(
        "strands_pack.apigateway_http_api._get_lambda", return_value=lam
    ):
        res = apigateway_http_api(
            action="add_lambda_route",
            api_id="a1",
            route_key="GET /x",
            lambda_arn="arn:aws:lambda:us-east-1:123456789012:function:agent-fn",
        )

    assert res["success"] is True
    assert res["permission"] is not None
    assert lam.calls, "expected add_permission to be called"
    assert lam.calls[0]["Principal"] == "apigateway.amazonaws.com"
    # Production-minded default: route-scoped permission if possible
    assert "/$default/GET/x" in lam.calls[0]["SourceArn"]


def test_apigateway_add_lambda_route_can_disable_auto_permission(monkeypatch):
    from strands_pack.apigateway_http_api import apigateway_http_api

    class FakeApiGw:
        def create_integration(self, **kwargs):
            return {"IntegrationId": "i"}

        def create_route(self, **kwargs):
            return {"RouteId": "r"}

    class FakeLambda:
        def add_permission(self, **kwargs):  # pragma: no cover
            raise AssertionError("should not be called when auto_add_permission=False")

    with patch("strands_pack.apigateway_http_api._get_apigw", return_value=FakeApiGw()), patch(
        "strands_pack.apigateway_http_api._get_lambda", return_value=FakeLambda()
    ):
        res = apigateway_http_api(
            action="add_lambda_route",
            api_id="a1",
            route_key="GET /x",
            lambda_arn="arn:aws:lambda:us-east-1:123456789012:function:agent-fn",
            auto_add_permission=False,
        )

    assert res["success"] is True
    assert res["permission"] is None


def test_apigateway_http_create_jwt_authorizer(monkeypatch):
    from strands_pack.apigateway_http_api import apigateway_http_api

    class FakeApiGw:
        def create_authorizer(self, **kwargs):
            assert kwargs["AuthorizerType"] == "JWT"
            return {"AuthorizerId": "auth1"}

    with patch("strands_pack.apigateway_http_api._get_apigw", return_value=FakeApiGw()):
        res = apigateway_http_api(
            action="create_jwt_authorizer",
            api_id="a1",
            name="agent-jwt",
            issuer="https://example.com",
            audience=["aud1"],
        )

    assert res["success"] is True
    assert res["authorizer_id"] == "auth1"


def test_apigateway_http_add_lambda_route_with_jwt_authorizer(monkeypatch):
    from strands_pack.apigateway_http_api import apigateway_http_api

    monkeypatch.setenv("STRANDS_PACK_LAMBDA_PREFIX", "agent-")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCOUNT_ID", "123456789012")

    class FakeApiGw:
        def __init__(self):
            self.route_args = None

        def create_integration(self, **kwargs):
            return {"IntegrationId": "i"}

        def create_route(self, **kwargs):
            self.route_args = kwargs
            return {"RouteId": "r"}

    class FakeLambda:
        def add_permission(self, **kwargs):
            return {}

    gw = FakeApiGw()
    with patch("strands_pack.apigateway_http_api._get_apigw", return_value=gw), patch(
        "strands_pack.apigateway_http_api._get_lambda", return_value=FakeLambda()
    ):
        res = apigateway_http_api(
            action="add_lambda_route",
            api_id="a1",
            route_key="GET /x",
            lambda_arn="arn:aws:lambda:us-east-1:123456789012:function:agent-fn",
            authorization_type="JWT",
            authorizer_id="auth1",
            authorization_scopes=["scope1"],
        )

    assert res["success"] is True
    assert gw.route_args["AuthorizationType"] == "JWT"
    assert gw.route_args["AuthorizerId"] == "auth1"
    assert gw.route_args["AuthorizationScopes"] == ["scope1"]


