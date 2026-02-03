"""Tests for Calendly tool."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_user_response():
    """Mock response for get_current_user."""
    return {
        "resource": {
            "uri": "https://api.calendly.com/users/user-123",
            "name": "Test User",
            "email": "test@example.com",
            "slug": "testuser",
            "scheduling_url": "https://calendly.com/testuser",
            "timezone": "America/New_York",
            "current_organization": "https://api.calendly.com/organizations/org-123",
        }
    }


def test_calendly_get_current_user_success(mock_user_response):
    """Test getting current user successfully."""
    with patch("strands_pack.calendly._get_requests") as mock_get_requests:
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = mock_user_response
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response
        mock_get_requests.return_value = mock_requests

        with patch("strands_pack.calendly._get_token", return_value="test-token"):
            from strands_pack import calendly

            result = calendly(action="get_current_user")

            assert result["success"] is True
            assert result["action"] == "get_current_user"
            assert result["user"]["name"] == "Test User"
            assert result["user"]["uuid"] == "user-123"


def test_calendly_list_event_types_success(mock_user_response):
    """Test listing event types successfully."""
    with patch("strands_pack.calendly._get_requests") as mock_get_requests:
        mock_requests = MagicMock()

        # First call for get_current_user
        user_response = MagicMock()
        user_response.json.return_value = mock_user_response
        user_response.raise_for_status = MagicMock()

        # Second call for list_event_types
        events_response = MagicMock()
        events_response.json.return_value = {
            "collection": [
                {
                    "uri": "https://api.calendly.com/event_types/et-123",
                    "name": "30 Minute Meeting",
                    "active": True,
                    "slug": "30min",
                    "scheduling_url": "https://calendly.com/testuser/30min",
                    "duration": 30,
                    "kind": "solo",
                },
            ],
        }
        events_response.raise_for_status = MagicMock()

        mock_requests.get.side_effect = [user_response, events_response]
        mock_get_requests.return_value = mock_requests

        with patch("strands_pack.calendly._get_token", return_value="test-token"):
            from strands_pack import calendly

            result = calendly(action="list_event_types")

            assert result["success"] is True
            assert result["action"] == "list_event_types"
            assert result["count"] == 1
            assert result["event_types"][0]["name"] == "30 Minute Meeting"


def test_calendly_get_event_type_success():
    """Test getting an event type successfully."""
    with patch("strands_pack.calendly._get_requests") as mock_get_requests:
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "resource": {
                "uri": "https://api.calendly.com/event_types/et-123",
                "name": "30 Minute Meeting",
                "active": True,
                "duration": 30,
            },
        }
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response
        mock_get_requests.return_value = mock_requests

        with patch("strands_pack.calendly._get_token", return_value="test-token"):
            from strands_pack import calendly

            result = calendly(action="get_event_type", event_type_uuid="et-123")

            assert result["success"] is True
            assert result["action"] == "get_event_type"
            assert result["event_type"]["name"] == "30 Minute Meeting"


def test_calendly_list_scheduled_events_success(mock_user_response):
    """Test listing scheduled events successfully."""
    with patch("strands_pack.calendly._get_requests") as mock_get_requests:
        mock_requests = MagicMock()

        user_response = MagicMock()
        user_response.json.return_value = mock_user_response
        user_response.raise_for_status = MagicMock()

        events_response = MagicMock()
        events_response.json.return_value = {
            "collection": [
                {
                    "uri": "https://api.calendly.com/scheduled_events/ev-123",
                    "name": "Meeting with John",
                    "status": "active",
                    "start_time": "2024-01-15T10:00:00Z",
                    "end_time": "2024-01-15T10:30:00Z",
                },
            ],
        }
        events_response.raise_for_status = MagicMock()

        mock_requests.get.side_effect = [user_response, events_response]
        mock_get_requests.return_value = mock_requests

        with patch("strands_pack.calendly._get_token", return_value="test-token"):
            from strands_pack import calendly

            result = calendly(action="list_scheduled_events")

            assert result["success"] is True
            assert result["action"] == "list_scheduled_events"
            assert result["count"] == 1


def test_calendly_cancel_event_success():
    """Test canceling an event successfully."""
    with patch("strands_pack.calendly._get_requests") as mock_get_requests:
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "resource": {
                "canceled_by": "Test User",
                "reason": "Schedule conflict",
                "canceler_type": "host",
            },
        }
        mock_response.raise_for_status = MagicMock()
        mock_requests.post.return_value = mock_response
        mock_get_requests.return_value = mock_requests

        with patch("strands_pack.calendly._get_token", return_value="test-token"):
            from strands_pack import calendly

            result = calendly(
                action="cancel_event",
                event_uuid="ev-123",
                reason="Schedule conflict",
            )

            assert result["success"] is True
            assert result["action"] == "cancel_event"
            assert result["cancellation"]["reason"] == "Schedule conflict"


def test_calendly_delete_webhook_success():
    """Test deleting a webhook successfully."""
    with patch("strands_pack.calendly._get_requests") as mock_get_requests:
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_requests.delete.return_value = mock_response
        mock_get_requests.return_value = mock_requests

        with patch("strands_pack.calendly._get_token", return_value="test-token"):
            from strands_pack import calendly

            result = calendly(action="delete_webhook", webhook_uuid="wh-123")

            assert result["success"] is True
            assert result["action"] == "delete_webhook"
            assert result["deleted"] is True


def test_calendly_missing_required_params():
    """Test error when required params are missing."""
    from strands_pack import calendly

    result = calendly(action="get_event_type")  # Missing event_type_uuid

    assert result["success"] is False
    assert "event_type_uuid" in result["error"]


def test_calendly_missing_token():
    """Test error when token is not set."""
    with patch.dict("os.environ", {}, clear=True):
        from strands_pack import calendly

        result = calendly(action="get_current_user")

        assert result["success"] is False
        assert "CALENDLY_TOKEN" in result["error"]


def test_calendly_unknown_action():
    """Test error for unknown action."""
    from strands_pack import calendly

    result = calendly(action="unknown_action")

    assert result["success"] is False
    assert "Unknown action" in result["error"]
    assert "available_actions" in result


def test_calendly_create_event_type_success(mock_user_response):
    """Test creating an event type successfully (mocked)."""
    with patch("strands_pack.calendly._get_requests") as mock_get_requests:
        mock_requests = MagicMock()

        # First call for get_current_user
        user_response = MagicMock()
        user_response.json.return_value = mock_user_response
        user_response.raise_for_status = MagicMock()

        # Create event type call
        create_response = MagicMock()
        create_response.json.return_value = {
            "resource": {
                "uri": "https://api.calendly.com/event_types/et-999",
                "name": "Test Event",
                "active": True,
                "duration": 30,
                "kind": "solo",
                "scheduling_url": "https://calendly.com/testuser/test-event",
            }
        }
        create_response.raise_for_status = MagicMock()

        mock_requests.get.side_effect = [user_response]
        mock_requests.post.return_value = create_response
        mock_get_requests.return_value = mock_requests

        with patch("strands_pack.calendly._get_token", return_value="test-token"):
            from strands_pack import calendly

            result = calendly(action="create_event_type", name="Test Event", duration=30)

            assert result["success"] is True
            assert result["action"] == "create_event_type"
            assert result["event_type"]["name"] == "Test Event"
            mock_requests.post.assert_called_once()


def test_calendly_update_event_type_success():
    """Test updating an event type successfully (mocked)."""
    with patch("strands_pack.calendly._get_requests") as mock_get_requests:
        mock_requests = MagicMock()

        update_response = MagicMock()
        update_response.json.return_value = {
            "resource": {
                "uri": "https://api.calendly.com/event_types/et-123",
                "name": "Updated Name",
                "active": True,
                "duration": 45,
                "kind": "solo",
            }
        }
        update_response.raise_for_status = MagicMock()

        mock_requests.patch.return_value = update_response
        mock_get_requests.return_value = mock_requests

        with patch("strands_pack.calendly._get_token", return_value="test-token"):
            from strands_pack import calendly

            result = calendly(action="update_event_type", event_type_uuid="et-123", name="Updated Name", duration=45)
            assert result["success"] is True
            assert result["action"] == "update_event_type"
            assert result["event_type"]["name"] == "Updated Name"
            mock_requests.patch.assert_called_once()


def test_calendly_create_scheduling_link_success():
    """Test creating a scheduling link successfully (mocked)."""
    with patch("strands_pack.calendly._get_requests") as mock_get_requests:
        mock_requests = MagicMock()

        link_response = MagicMock()
        link_response.json.return_value = {
            "resource": {
                "booking_url": "https://calendly.com/s/abc123",
                "owner": "https://api.calendly.com/event_types/et-123",
                "max_event_count": 1,
            }
        }
        link_response.raise_for_status = MagicMock()

        mock_requests.post.return_value = link_response
        mock_get_requests.return_value = mock_requests

        with patch("strands_pack.calendly._get_token", return_value="test-token"):
            from strands_pack import calendly

            result = calendly(action="create_scheduling_link", event_type_uuid="et-123")
            assert result["success"] is True
            assert result["action"] == "create_scheduling_link"
            assert "booking_url" in result["scheduling_link"]


def test_calendly_get_available_times_success():
    """Test getting available times successfully (mocked)."""
    with patch("strands_pack.calendly._get_requests") as mock_get_requests:
        mock_requests = MagicMock()

        resp = MagicMock()
        resp.json.return_value = {"collection": [{"start_time": "2026-01-01T10:00:00Z"}]}
        resp.raise_for_status = MagicMock()
        mock_requests.get.return_value = resp
        mock_get_requests.return_value = mock_requests

        with patch("strands_pack.calendly._get_token", return_value="test-token"):
            from strands_pack import calendly

            result = calendly(
                action="get_available_times",
                event_type_uuid="et-123",
                start_time="2026-01-01T00:00:00Z",
                end_time="2026-01-02T00:00:00Z",
            )
            assert result["success"] is True
            assert result["action"] == "get_available_times"
            assert len(result["slots"]) == 1


def test_calendly_get_busy_times_success(mock_user_response):
    """Test getting busy times successfully (mocked)."""
    with patch("strands_pack.calendly._get_requests") as mock_get_requests:
        mock_requests = MagicMock()

        # First call for get_current_user
        user_response = MagicMock()
        user_response.json.return_value = mock_user_response
        user_response.raise_for_status = MagicMock()

        busy_response = MagicMock()
        busy_response.json.return_value = {"collection": [{"start_time": "2026-01-01T10:00:00Z", "end_time": "2026-01-01T11:00:00Z"}]}
        busy_response.raise_for_status = MagicMock()

        mock_requests.get.side_effect = [user_response, busy_response]
        mock_get_requests.return_value = mock_requests

        with patch("strands_pack.calendly._get_token", return_value="test-token"):
            from strands_pack import calendly

            result = calendly(action="get_busy_times", start_time="2026-01-01T00:00:00Z", end_time="2026-01-02T00:00:00Z")
            assert result["success"] is True
            assert result["action"] == "get_busy_times"
            assert len(result["busy_times"]) == 1
