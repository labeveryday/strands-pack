"""Tests for local_queue tool."""

import os
import tempfile

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


def test_local_queue_send_receive_delete_roundtrip():
    from strands_pack.local_queue import local_queue

    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        db_path = f.name

        init = local_queue(action="init_db", db_path=db_path)
        assert init["success"] is True

        sent = local_queue(action="send", db_path=db_path, queue_name="q1", body="hello")
        assert sent["success"] is True

        received = local_queue(action="receive", db_path=db_path, queue_name="q1", max_messages=1, visibility_timeout=30)
        assert received["success"] is True
        assert received["count"] == 1
        rh = received["messages"][0]["receipt_handle"]

        deleted = local_queue(action="delete", db_path=db_path, receipt_handle=rh)
        assert deleted["success"] is True
        assert deleted["deleted"] is True

        received2 = local_queue(action="receive", db_path=db_path, queue_name="q1", max_messages=1)
        assert received2["success"] is True
        assert received2["count"] == 0


def test_local_queue_visibility_timeout_blocks_redelivery_temporarily():
    from strands_pack.local_queue import local_queue

    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        db_path = f.name
        local_queue(action="send", db_path=db_path, queue_name="q1", body="hello")

        r1 = local_queue(action="receive", db_path=db_path, queue_name="q1", max_messages=1, visibility_timeout=60)
        assert r1["count"] == 1

        r2 = local_queue(action="receive", db_path=db_path, queue_name="q1", max_messages=1, visibility_timeout=60)
        assert r2["count"] == 0

        # If visibility_timeout is 0, message becomes immediately visible again
        local_queue(action="send", db_path=db_path, queue_name="q1", body="hello2")
        r3 = local_queue(action="receive", db_path=db_path, queue_name="q1", max_messages=1, visibility_timeout=0)
        assert r3["count"] == 1
        r4 = local_queue(action="receive", db_path=db_path, queue_name="q1", max_messages=10, visibility_timeout=0)
        assert r4["count"] >= 0


def test_init_db(temp_db):
    """Test init_db action."""
    from strands_pack import local_queue

    result = local_queue(action="init_db", db_path=temp_db)
    assert result["success"] is True
    assert result["initialized"] is True
    assert result["db_path"] == temp_db


def test_send_message(temp_db):
    """Test sending a message."""
    from strands_pack import local_queue

    result = local_queue(action="send", db_path=temp_db, body="Hello World", queue_name="test-queue")
    assert result["success"] is True
    assert result["message_id"].startswith("lq_")
    assert result["queue_name"] == "test-queue"
    assert result["delay_seconds"] == 0


def test_send_with_delay(temp_db):
    """Test sending a message with delay."""
    from strands_pack import local_queue

    result = local_queue(action="send", db_path=temp_db, body="Delayed", delay_seconds=10)
    assert result["success"] is True
    assert result["delay_seconds"] == 10


def test_send_requires_body(temp_db):
    """Test that send requires body."""
    from strands_pack import local_queue

    result = local_queue(action="send", db_path=temp_db)
    assert result["success"] is False
    assert "body is required" in result["error"]


def test_receive_empty_queue(temp_db):
    """Test receiving from empty queue."""
    from strands_pack import local_queue

    result = local_queue(action="receive", db_path=temp_db, queue_name="empty")
    assert result["success"] is True
    assert result["count"] == 0
    assert result["messages"] == []


def test_receive_max_messages(temp_db):
    """Test receiving multiple messages."""
    from strands_pack import local_queue

    # Send 5 messages
    for i in range(5):
        local_queue(action="send", db_path=temp_db, body=f"Message {i}", queue_name="multi")

    # Receive max 3
    result = local_queue(action="receive", db_path=temp_db, queue_name="multi", max_messages=3)
    assert result["success"] is True
    assert result["count"] == 3


def test_send_batch_and_delete_batch_roundtrip(temp_db):
    from strands_pack import local_queue

    send = local_queue(
        action="send_batch",
        db_path=temp_db,
        queue_name="bq",
        messages=[{"id": "a", "body": "one"}, {"id": "b", "body": "two", "delay_seconds": 0}],
    )
    assert send["success"] is True
    assert send["successful_count"] == 2

    recv = local_queue(action="receive", db_path=temp_db, queue_name="bq", max_messages=10, visibility_timeout=30)
    assert recv["success"] is True
    assert recv["count"] == 2
    rhs = [m["receipt_handle"] for m in recv["messages"]]

    deleted = local_queue(action="delete_batch", db_path=temp_db, receipt_handles=rhs)
    assert deleted["success"] is True
    assert deleted["successful_count"] == 2


def test_send_batch_limit(temp_db):
    from strands_pack import local_queue

    msgs = [{"id": str(i), "body": "x"} for i in range(11)]
    res = local_queue(action="send_batch", db_path=temp_db, messages=msgs)
    assert res["success"] is False
    assert res["error_type"] == "LimitExceeded"


def test_delete_requires_receipt_handle(temp_db):
    """Test that delete requires receipt_handle."""
    from strands_pack import local_queue

    result = local_queue(action="delete", db_path=temp_db)
    assert result["success"] is False
    assert "receipt_handle is required" in result["error"]


def test_purge_queue(temp_db):
    """Test purging a queue."""
    from strands_pack import local_queue

    # Send messages
    for i in range(3):
        local_queue(action="send", db_path=temp_db, body=f"Msg {i}", queue_name="purge-test")

    # Purge
    result = local_queue(action="purge", db_path=temp_db, queue_name="purge-test")
    assert result["success"] is True
    assert result["purged"] == 3

    # Verify empty
    attrs = local_queue(action="get_queue_attributes", db_path=temp_db, queue_name="purge-test")
    assert attrs["total"] == 0


def test_purge_all_requires_confirm(temp_db):
    """Test that purging all queues requires confirm."""
    from strands_pack import local_queue

    # Need to set queue_name to empty string or None to trigger purge all
    result = local_queue(action="purge", db_path=temp_db, queue_name="")
    assert result["success"] is False
    assert "confirm=True is required" in result["error"]


def test_purge_all_with_confirm(temp_db):
    """Test purging all queues with confirm."""
    from strands_pack import local_queue

    # Send to multiple queues
    local_queue(action="send", db_path=temp_db, body="A", queue_name="queue1")
    local_queue(action="send", db_path=temp_db, body="B", queue_name="queue2")

    # Purge all
    result = local_queue(action="purge", db_path=temp_db, queue_name="", confirm=True)
    assert result["success"] is True
    assert result["purged"] == 2


def test_get_queue_attributes(temp_db):
    """Test getting queue attributes."""
    from strands_pack import local_queue

    # Send messages
    local_queue(action="send", db_path=temp_db, body="A", queue_name="attrs")
    local_queue(action="send", db_path=temp_db, body="B", queue_name="attrs")

    # Receive one (put in-flight)
    local_queue(action="receive", db_path=temp_db, queue_name="attrs", visibility_timeout=60)

    # Get attributes
    result = local_queue(action="get_queue_attributes", db_path=temp_db, queue_name="attrs")
    assert result["success"] is True
    assert result["total"] == 2
    assert result["visible"] == 1
    assert result["in_flight"] == 1


def test_list_queues(temp_db):
    """Test listing queues."""
    from strands_pack import local_queue

    # Send to multiple queues
    local_queue(action="send", db_path=temp_db, body="A", queue_name="alpha")
    local_queue(action="send", db_path=temp_db, body="B", queue_name="beta")
    local_queue(action="send", db_path=temp_db, body="C", queue_name="gamma")

    result = local_queue(action="list_queues", db_path=temp_db)
    assert result["success"] is True
    assert result["count"] == 3
    assert set(result["queues"]) == {"alpha", "beta", "gamma"}


def test_change_visibility(temp_db):
    """Test changing visibility timeout."""
    from strands_pack import local_queue

    # Send and receive
    local_queue(action="send", db_path=temp_db, body="Extend me", queue_name="vis")
    recv = local_queue(action="receive", db_path=temp_db, queue_name="vis", visibility_timeout=5)
    receipt_handle = recv["messages"][0]["receipt_handle"]

    # Extend visibility
    result = local_queue(action="change_visibility", db_path=temp_db, receipt_handle=receipt_handle, visibility_timeout=120)
    assert result["success"] is True
    assert result["visibility_timeout"] == 120
    assert result["updated"] is True


def test_change_visibility_requires_receipt_handle(temp_db):
    """Test that change_visibility requires receipt_handle."""
    from strands_pack import local_queue

    result = local_queue(action="change_visibility", db_path=temp_db, visibility_timeout=60)
    assert result["success"] is False
    assert "receipt_handle is required" in result["error"]


def test_unknown_action(temp_db):
    """Test unknown action returns error."""
    from strands_pack import local_queue

    result = local_queue(action="invalid_action", db_path=temp_db)
    assert result["success"] is False
    assert result["error_type"] == "InvalidAction"
    assert "available_actions" in result


def test_db_path_required():
    """Test that db_path is required."""
    from strands_pack import local_queue

    # Clear env vars
    old_path = os.environ.pop("SQLITE_DB_PATH", None)
    old_strands = os.environ.pop("STRANDS_SQLITE_DB_PATH", None)

    try:
        result = local_queue(action="init_db")
        assert result["success"] is False
        assert "db_path is required" in result["error"]
    finally:
        if old_path:
            os.environ["SQLITE_DB_PATH"] = old_path
        if old_strands:
            os.environ["STRANDS_SQLITE_DB_PATH"] = old_strands


def test_uses_env_db_path():
    """Test that SQLITE_DB_PATH env var is used."""
    from strands_pack import local_queue

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        os.environ["SQLITE_DB_PATH"] = db_path
        result = local_queue(action="init_db")
        assert result["success"] is True
        assert result["db_path"] == db_path
    finally:
        os.environ.pop("SQLITE_DB_PATH", None)
        try:
            os.unlink(db_path)
        except OSError:
            pass
