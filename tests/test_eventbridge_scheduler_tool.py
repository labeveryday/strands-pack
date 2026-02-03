from unittest.mock import patch


def test_scheduler_name_prefix_guard(monkeypatch):
    from strands_pack.eventbridge_scheduler import eventbridge_scheduler

    monkeypatch.setenv("STRANDS_PACK_SCHEDULE_PREFIX", "agent-")

    class FakeClient:
        def create_schedule(self, **kwargs):
            return {}

    with patch("strands_pack.eventbridge_scheduler._get_client", return_value=FakeClient()):
        res = eventbridge_scheduler(
            action="create_schedule",
            name="badname",
            schedule_expression="rate(5 minutes)",
            queue_arn="arn:aws:sqs:us-east-1:123:queue",
            role_arn="arn:aws:iam::123:role/role",
            input={"x": 1},
        )
    assert res["success"] is False
    assert res["error_type"] == "NameNotAllowed"


def test_scheduler_create_lambda_schedule_adds_permission(monkeypatch):
    from strands_pack.eventbridge_scheduler import eventbridge_scheduler

    monkeypatch.setenv("STRANDS_PACK_SCHEDULE_PREFIX", "agent-")
    monkeypatch.setenv("STRANDS_PACK_LAMBDA_PREFIX", "agent-")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCOUNT_ID", "123456789012")

    class FakeScheduler:
        def create_schedule(self, **kwargs):
            return {}

        def tag_resource(self, **kwargs):
            return {}

    class FakeLambda:
        def __init__(self):
            self.calls = []

        def add_permission(self, **kwargs):
            self.calls.append(kwargs)
            return {}

    lam = FakeLambda()
    with patch("strands_pack.eventbridge_scheduler._get_client", return_value=FakeScheduler()), patch(
        "strands_pack.eventbridge_scheduler._get_lambda", return_value=lam
    ):
        res = eventbridge_scheduler(
            action="create_lambda_schedule",
            name="agent-test",
            schedule_expression="rate(5 minutes)",
            lambda_arn="arn:aws:lambda:us-east-1:123456789012:function:agent-fn",
            role_arn="arn:aws:iam::123456789012:role/role",
            input={"x": 1},
        )

    assert res["success"] is True
    assert lam.calls


def test_scheduler_list_schedule_groups(monkeypatch):
    from strands_pack.eventbridge_scheduler import eventbridge_scheduler

    class FakeClient:
        def list_schedule_groups(self, **kwargs):
            return {"ScheduleGroups": [{"Name": "agent-g", "Arn": "arn", "State": "ACTIVE"}]}

    with patch("strands_pack.eventbridge_scheduler._get_client", return_value=FakeClient()):
        res = eventbridge_scheduler(action="list_schedule_groups")
    assert res["success"] is True
    assert res["count"] == 1


def test_scheduler_create_schedule_group_prefix_guard(monkeypatch):
    from strands_pack.eventbridge_scheduler import eventbridge_scheduler

    monkeypatch.setenv("STRANDS_PACK_SCHEDULE_PREFIX", "agent-")

    class FakeClient:
        def create_schedule_group(self, **kwargs):
            return {"ScheduleGroupArn": "arn"}

    with patch("strands_pack.eventbridge_scheduler._get_client", return_value=FakeClient()):
        res = eventbridge_scheduler(action="create_schedule_group", group_name="bad")
    assert res["success"] is False
    assert res["error_type"] == "NameNotAllowed"


def test_scheduler_delete_schedule_group_requires_confirm():
    from strands_pack.eventbridge_scheduler import eventbridge_scheduler

    class FakeClient:
        def delete_schedule_group(self, **kwargs):  # pragma: no cover
            return {}

    with patch("strands_pack.eventbridge_scheduler._get_client", return_value=FakeClient()):
        res = eventbridge_scheduler(action="delete_schedule_group", group_name="agent-g")
    assert res["success"] is False
    assert res["error_type"] == "ConfirmationRequired"


def test_scheduler_pause_and_resume_schedule_preserves_config(monkeypatch):
    from strands_pack.eventbridge_scheduler import eventbridge_scheduler

    monkeypatch.setenv("STRANDS_PACK_SCHEDULE_PREFIX", "agent-")

    class FakeClient:
        def __init__(self):
            self.updated = []

        def get_schedule(self, **kwargs):
            return {
                "ScheduleExpression": "rate(5 minutes)",
                "FlexibleTimeWindow": {"Mode": "OFF"},
                "Target": {"Arn": "arn:aws:sqs:us-east-1:123:q", "RoleArn": "arn:aws:iam::123:role/r", "Input": "{}"},
                "Description": "d",
            }

        def update_schedule(self, **kwargs):
            self.updated.append(kwargs)
            return {}

        def tag_resource(self, **kwargs):  # pragma: no cover
            return {}

    fc = FakeClient()
    with patch("strands_pack.eventbridge_scheduler._get_client", return_value=fc):
        r1 = eventbridge_scheduler(action="pause_schedule", name="agent-x")
        r2 = eventbridge_scheduler(action="resume_schedule", name="agent-x")

    assert r1["success"] is True and r1["state"] == "DISABLED"
    assert r2["success"] is True and r2["state"] == "ENABLED"
    assert fc.updated[0]["State"] == "DISABLED"
    assert fc.updated[1]["State"] == "ENABLED"


