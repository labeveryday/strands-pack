from unittest.mock import patch


def test_dynamodb_invalid_action():
    from strands_pack.dynamodb import dynamodb

    res = dynamodb(action="nope")
    assert res["success"] is False
    assert res["error_type"] == "InvalidAction"


def test_dynamodb_table_allowlist(monkeypatch):
    from strands_pack.dynamodb import dynamodb

    monkeypatch.setenv("STRANDS_PACK_DDB_TABLE_ALLOWLIST", "allowed")

    class FakeClient:
        def get_item(self, **kwargs):
            return {}

    with patch("strands_pack.dynamodb._get_client", return_value=FakeClient()):
        res = dynamodb(action="get_item", table_name="not-allowed", key={"pk": {"S": "x"}})
    assert res["success"] is False
    assert res["error_type"] == "TableNotAllowed"


def test_dynamodb_describe_table_calls_client():
    from strands_pack.dynamodb import dynamodb

    class FakeClient:
        def describe_table(self, **kwargs):
            assert kwargs["TableName"] == "t"
            return {"Table": {"TableStatus": "ACTIVE", "ItemCount": 3, "TableSizeBytes": 10}}

    with patch("strands_pack.dynamodb._get_client", return_value=FakeClient()):
        res = dynamodb(action="describe_table", table_name="t")
    assert res["success"] is True
    assert res["status"] == "ACTIVE"
    assert res["item_count"] == 3


def test_dynamodb_delete_table_requires_confirm():
    from strands_pack.dynamodb import dynamodb

    class FakeClient:
        def delete_table(self, **kwargs):
            return {}

    with patch("strands_pack.dynamodb._get_client", return_value=FakeClient()):
        res = dynamodb(action="delete_table", table_name="t")
    assert res["success"] is False
    assert res["error_type"] == "ConfirmationRequired"


def test_dynamodb_batch_write_item_limit_enforced():
    from strands_pack.dynamodb import dynamodb

    class FakeClient:
        def batch_write_item(self, **kwargs):
            return {}

    # 26 put ops should fail
    puts = [{"pk": {"S": str(i)}} for i in range(26)]
    with patch("strands_pack.dynamodb._get_client", return_value=FakeClient()):
        res = dynamodb(action="batch_write_item", table_name="t", put_items=puts)
    assert res["success"] is False
    assert res["error_type"] == "LimitExceeded"


def test_dynamodb_batch_get_item_limit_enforced():
    from strands_pack.dynamodb import dynamodb

    class FakeClient:
        def batch_get_item(self, **kwargs):
            return {}

    keys = [{"pk": {"S": str(i)}} for i in range(101)]
    with patch("strands_pack.dynamodb._get_client", return_value=FakeClient()):
        res = dynamodb(action="batch_get_item", table_name="t", keys=keys)
    assert res["success"] is False
    assert res["error_type"] == "LimitExceeded"


def test_dynamodb_scan_is_capped():
    from strands_pack.dynamodb import dynamodb

    class FakeClient:
        def __init__(self):
            self.calls = 0

        def scan(self, **kwargs):
            self.calls += 1
            # Return 100 items per page
            items = [{"pk": {"S": str(i)}} for i in range(100)]
            # Only one page
            return {"Items": items, "ScannedCount": len(items)}

    client = FakeClient()
    with patch("strands_pack.dynamodb._get_client", return_value=client):
        res = dynamodb(action="scan", table_name="t", max_items=10)
    assert res["success"] is True
    assert res["count"] == 10


