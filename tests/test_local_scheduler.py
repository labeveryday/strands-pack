"""Tests for local_scheduler tool."""

import os
import tempfile
import time

import pytest


@pytest.fixture
def temp_db():
    """Create a temporary database file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    try:
        os.unlink(db_path)
    except OSError:
        pass


def test_local_scheduler_enqueues_into_local_queue():
    from strands_pack.local_queue import local_queue
    from strands_pack.local_scheduler import local_scheduler

    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        db_path = f.name

        # schedule something in the past so it's due immediately
        due = int(time.time()) - 1
        sch = local_scheduler(
            action="schedule_at",
            db_path=db_path,
            run_at_epoch=due,
            queue_name="q1",
            message_body="job1",
        )
        assert sch["success"] is True

        ran = local_scheduler(action="run_due", db_path=db_path, max_to_run=10, delete_after=True)
        assert ran["success"] is True
        assert ran["count"] == 1

        msg = local_queue(action="receive", db_path=db_path, queue_name="q1", max_messages=1, visibility_timeout=0)
        assert msg["success"] is True
        assert msg["count"] == 1
        assert msg["messages"][0]["body"] == "job1"


def test_local_scheduler_cancel_schedule():
    from strands_pack.local_scheduler import local_scheduler

    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        db_path = f.name
        sch = local_scheduler(action="schedule_in", db_path=db_path, delay_seconds=60, queue_name="q1", message_body="job2")
        assert sch["success"] is True

        cancelled = local_scheduler(action="cancel_schedule", db_path=db_path, schedule_id=sch["schedule_id"])
        assert cancelled["success"] is True
        assert cancelled["cancelled"] is True


def test_init_db(temp_db):
    """Test init_db action."""
    from strands_pack import local_scheduler

    result = local_scheduler(action="init_db", db_path=temp_db)
    assert result["success"] is True
    assert result["initialized"] is True
    assert result["db_path"] == temp_db


def test_schedule_at(temp_db):
    """Test scheduling at a specific epoch time."""
    from strands_pack import local_scheduler

    future = int(time.time()) + 3600  # 1 hour from now
    result = local_scheduler(
        action="schedule_at",
        db_path=temp_db,
        run_at_epoch=future,
        message_body="Test message",
        queue_name="test-queue",
        schedule_name="my-schedule",
    )
    assert result["success"] is True
    assert result["schedule_id"].startswith("ls_")
    assert result["run_at_epoch"] == future
    assert result["queue_name"] == "test-queue"
    assert result["schedule_name"] == "my-schedule"


def test_schedule_at_requires_run_at_epoch(temp_db):
    """Test that schedule_at requires run_at_epoch."""
    from strands_pack import local_scheduler

    result = local_scheduler(action="schedule_at", db_path=temp_db, message_body="test")
    assert result["success"] is False
    assert "run_at_epoch is required" in result["error"]


def test_schedule_at_requires_message_body(temp_db):
    """Test that schedule_at requires message_body."""
    from strands_pack import local_scheduler

    result = local_scheduler(action="schedule_at", db_path=temp_db, run_at_epoch=int(time.time()))
    assert result["success"] is False
    assert "message_body is required" in result["error"]


def test_schedule_in(temp_db):
    """Test scheduling with delay."""
    from strands_pack import local_scheduler

    result = local_scheduler(
        action="schedule_in",
        db_path=temp_db,
        delay_seconds=120,
        message_body="Delayed message",
    )
    assert result["success"] is True
    assert result["delay_seconds"] == 120
    # run_at_epoch should be approximately now + 120
    assert result["run_at_epoch"] >= int(time.time()) + 119


def test_schedule_in_requires_delay_seconds(temp_db):
    """Test that schedule_in requires delay_seconds."""
    from strands_pack import local_scheduler

    result = local_scheduler(action="schedule_in", db_path=temp_db, message_body="test")
    assert result["success"] is False
    assert "delay_seconds is required" in result["error"]


def test_schedule_in_requires_message_body(temp_db):
    """Test that schedule_in requires message_body."""
    from strands_pack import local_scheduler

    result = local_scheduler(action="schedule_in", db_path=temp_db, delay_seconds=60)
    assert result["success"] is False
    assert "message_body is required" in result["error"]


def test_get_schedule(temp_db):
    """Test getting a schedule by ID."""
    from strands_pack import local_scheduler

    # Create a schedule
    sch = local_scheduler(
        action="schedule_in",
        db_path=temp_db,
        delay_seconds=60,
        message_body="Get me",
        schedule_name="get-test",
    )

    # Get it
    result = local_scheduler(action="get_schedule", db_path=temp_db, schedule_id=sch["schedule_id"])
    assert result["success"] is True
    assert result["schedule"]["schedule_id"] == sch["schedule_id"]
    assert result["schedule"]["message_body"] == "Get me"
    assert result["schedule"]["schedule_name"] == "get-test"


def test_get_schedule_not_found(temp_db):
    """Test getting a non-existent schedule."""
    from strands_pack import local_scheduler

    result = local_scheduler(action="get_schedule", db_path=temp_db, schedule_id="ls_nonexistent")
    assert result["success"] is False
    assert result["error_type"] == "NotFound"


def test_get_schedule_requires_schedule_id(temp_db):
    """Test that get_schedule requires schedule_id."""
    from strands_pack import local_scheduler

    result = local_scheduler(action="get_schedule", db_path=temp_db)
    assert result["success"] is False
    assert "schedule_id is required" in result["error"]


def test_list_schedules(temp_db):
    """Test listing schedules."""
    from strands_pack import local_scheduler

    # Create multiple schedules
    for i in range(3):
        local_scheduler(
            action="schedule_in",
            db_path=temp_db,
            delay_seconds=60 + i,
            message_body=f"Schedule {i}",
        )

    result = local_scheduler(action="list_schedules", db_path=temp_db)
    assert result["success"] is True
    assert result["count"] == 3


def test_list_schedules_excludes_fired_by_default(temp_db):
    """Test that list_schedules excludes fired schedules by default."""
    from strands_pack import local_scheduler

    # Create a schedule in the past
    past = int(time.time()) - 10
    local_scheduler(action="schedule_at", db_path=temp_db, run_at_epoch=past, message_body="Past")

    # Run it (with delete_after=False to keep it marked as fired)
    local_scheduler(action="run_due", db_path=temp_db, delete_after=False)

    # Create a pending schedule
    local_scheduler(action="schedule_in", db_path=temp_db, delay_seconds=3600, message_body="Future")

    # List without fired
    result = local_scheduler(action="list_schedules", db_path=temp_db, include_fired=False)
    assert result["count"] == 1

    # List with fired
    result_with_fired = local_scheduler(action="list_schedules", db_path=temp_db, include_fired=True)
    assert result_with_fired["count"] == 2


def test_cancel_schedule_requires_schedule_id(temp_db):
    """Test that cancel_schedule requires schedule_id."""
    from strands_pack import local_scheduler

    result = local_scheduler(action="cancel_schedule", db_path=temp_db)
    assert result["success"] is False
    assert "schedule_id is required" in result["error"]


def test_update_schedule_updates_fields(temp_db):
    from strands_pack import local_scheduler

    sch = local_scheduler(action="schedule_in", db_path=temp_db, delay_seconds=60, message_body="old", schedule_name="n1")
    assert sch["success"] is True

    upd = local_scheduler(action="update_schedule", db_path=temp_db, schedule_id=sch["schedule_id"], message_body="new", schedule_name="n2")
    assert upd["success"] is True

    got = local_scheduler(action="get_schedule", db_path=temp_db, schedule_id=sch["schedule_id"])
    assert got["success"] is True
    assert got["schedule"]["message_body"] == "new"
    assert got["schedule"]["schedule_name"] == "n2"


def test_schedule_rate_is_recurring_and_reschedules(temp_db):
    from strands_pack import local_scheduler

    sch = local_scheduler(
        action="schedule_rate",
        db_path=temp_db,
        schedule_expression="rate(1 seconds)",
        message_body="tick",
        queue_name="q1",
    )
    assert sch["success"] is True
    sid = sch["schedule_id"]

    # Force it due now
    upd = local_scheduler(action="update_schedule", db_path=temp_db, schedule_id=sid, run_at_epoch=int(time.time()) - 1)
    assert upd["success"] is True

    ran = local_scheduler(action="run_due", db_path=temp_db, delete_after=True)
    assert ran["success"] is True
    assert ran["count"] == 1

    got = local_scheduler(action="get_schedule", db_path=temp_db, schedule_id=sid)
    assert got["success"] is True
    assert got["schedule"]["interval_seconds"] is not None
    assert got["schedule"]["schedule_expression"] is not None
    # Still exists (recurring)
    assert got["schedule"]["fired_at"] is None


def test_run_due_respects_run_at_epoch(temp_db):
    """Test that run_due only fires schedules that are due."""
    from strands_pack import local_scheduler

    # Create a schedule in the future
    future = int(time.time()) + 3600
    local_scheduler(action="schedule_at", db_path=temp_db, run_at_epoch=future, message_body="Future")

    # Run due - should fire nothing
    result = local_scheduler(action="run_due", db_path=temp_db)
    assert result["count"] == 0


def test_run_due_delete_after_true(temp_db):
    """Test that run_due with delete_after=True removes schedules."""
    from strands_pack import local_scheduler

    past = int(time.time()) - 10
    local_scheduler(action="schedule_at", db_path=temp_db, run_at_epoch=past, message_body="Delete me")

    # Run with delete_after=True (default)
    result = local_scheduler(action="run_due", db_path=temp_db, delete_after=True)
    assert result["count"] == 1

    # List schedules - should be empty
    list_result = local_scheduler(action="list_schedules", db_path=temp_db, include_fired=True)
    assert list_result["count"] == 0


def test_run_due_delete_after_false(temp_db):
    """Test that run_due with delete_after=False marks schedules as fired."""
    from strands_pack import local_scheduler

    past = int(time.time()) - 10
    local_scheduler(action="schedule_at", db_path=temp_db, run_at_epoch=past, message_body="Keep me")

    # Run with delete_after=False
    result = local_scheduler(action="run_due", db_path=temp_db, delete_after=False)
    assert result["count"] == 1

    # List schedules with fired - should still exist
    list_result = local_scheduler(action="list_schedules", db_path=temp_db, include_fired=True)
    assert list_result["count"] == 1
    assert list_result["schedules"][0]["fired_at"] is not None


def test_unknown_action(temp_db):
    """Test unknown action returns error."""
    from strands_pack import local_scheduler

    result = local_scheduler(action="invalid_action", db_path=temp_db)
    assert result["success"] is False
    assert result["error_type"] == "InvalidAction"
    assert "available_actions" in result


def test_db_path_required():
    """Test that db_path is required."""
    from strands_pack import local_scheduler

    # Clear env vars
    old_path = os.environ.pop("SQLITE_DB_PATH", None)
    old_strands = os.environ.pop("STRANDS_SQLITE_DB_PATH", None)

    try:
        result = local_scheduler(action="init_db")
        assert result["success"] is False
        assert "db_path is required" in result["error"]
    finally:
        if old_path:
            os.environ["SQLITE_DB_PATH"] = old_path
        if old_strands:
            os.environ["STRANDS_SQLITE_DB_PATH"] = old_strands
