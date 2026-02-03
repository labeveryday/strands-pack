"""Tests for Twilio tool."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_message_response():
    """Mock message response from Twilio."""
    return {
        "sid": "SM123456789",
        "from": "+15551234567",
        "to": "+15559876543",
        "body": "Test message",
        "status": "queued",
        "direction": "outbound-api",
        "date_created": "2024-01-15T10:00:00Z",
        "date_sent": None,
        "price": None,
        "price_unit": "USD",
        "error_code": None,
        "error_message": None,
    }


@pytest.fixture
def mock_call_response():
    """Mock call response from Twilio."""
    return {
        "sid": "CA123456789",
        "from": "+15551234567",
        "to": "+15559876543",
        "status": "queued",
        "direction": "outbound-api",
        "duration": None,
        "start_time": None,
        "end_time": None,
        "price": None,
        "price_unit": "USD",
    }


def test_twilio_send_sms_success(mock_message_response):
    """Test sending SMS successfully."""
    with patch("strands_pack.twilio_tool._get_requests") as mock_get_requests:
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = mock_message_response
        mock_requests.post.return_value = mock_response
        mock_get_requests.return_value = mock_requests

        with patch("strands_pack.twilio_tool._get_credentials", return_value=("AC123", "token123")):
            with patch("strands_pack.twilio_tool._get_default_from", return_value="+15551234567"):
                from strands_pack import twilio_tool

                result = twilio_tool(
                    action="send_sms",
                    to="+15559876543",
                    body="Test message",
                )

                assert result["success"] is True
                assert result["action"] == "send_sms"
                assert result["message"]["sid"] == "SM123456789"
                assert result["message"]["status"] == "queued"


def test_twilio_send_sms_missing_to():
    """Test error when 'to' is missing."""
    from strands_pack import twilio_tool

    result = twilio_tool(action="send_sms", body="Test")

    assert result["success"] is False
    assert "to" in result["error"]


def test_twilio_send_sms_missing_body():
    """Test error when 'body' is missing."""
    from strands_pack import twilio_tool

    result = twilio_tool(action="send_sms", to="+15559876543")

    assert result["success"] is False
    assert "body" in result["error"]


def test_twilio_send_whatsapp_success(mock_message_response):
    """Test sending WhatsApp message successfully."""
    with patch("strands_pack.twilio_tool._get_requests") as mock_get_requests:
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = mock_message_response
        mock_requests.post.return_value = mock_response
        mock_get_requests.return_value = mock_requests

        with patch("strands_pack.twilio_tool._get_credentials", return_value=("AC123", "token123")):
            with patch("strands_pack.twilio_tool._get_default_from", return_value="+15551234567"):
                from strands_pack import twilio_tool

                result = twilio_tool(
                    action="send_whatsapp",
                    to="+15559876543",
                    body="Test WhatsApp message",
                )

                assert result["success"] is True
                assert result["action"] == "send_whatsapp"

                # Verify whatsapp: prefix was added
                call_args = mock_requests.post.call_args
                assert "whatsapp:" in call_args[1]["data"]["To"]


def test_twilio_make_call_success(mock_call_response):
    """Test making a call successfully."""
    with patch("strands_pack.twilio_tool._get_requests") as mock_get_requests:
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = mock_call_response
        mock_requests.post.return_value = mock_response
        mock_get_requests.return_value = mock_requests

        with patch("strands_pack.twilio_tool._get_credentials", return_value=("AC123", "token123")):
            with patch("strands_pack.twilio_tool._get_default_from", return_value="+15551234567"):
                from strands_pack import twilio_tool

                result = twilio_tool(
                    action="make_call",
                    to="+15559876543",
                    twiml="<Response><Say>Hello!</Say></Response>",
                )

                assert result["success"] is True
                assert result["action"] == "make_call"
                assert result["call"]["sid"] == "CA123456789"


def test_twilio_make_call_missing_twiml_and_url():
    """Test error when neither twiml nor url is provided."""
    with patch("strands_pack.twilio_tool._get_credentials", return_value=("AC123", "token123")):
        with patch("strands_pack.twilio_tool._get_default_from", return_value="+15551234567"):
            from strands_pack import twilio_tool

            result = twilio_tool(action="make_call", to="+15559876543")

            assert result["success"] is False
            assert "twiml" in result["error"] or "url" in result["error"]


def test_twilio_get_message_success(mock_message_response):
    """Test getting a message successfully."""
    with patch("strands_pack.twilio_tool._get_requests") as mock_get_requests:
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_message_response
        mock_requests.get.return_value = mock_response
        mock_get_requests.return_value = mock_requests

        with patch("strands_pack.twilio_tool._get_credentials", return_value=("AC123", "token123")):
            from strands_pack import twilio_tool

            result = twilio_tool(action="get_message", message_sid="SM123456789")

            assert result["success"] is True
            assert result["action"] == "get_message"
            assert result["message"]["sid"] == "SM123456789"


def test_twilio_list_messages_success(mock_message_response):
    """Test listing messages successfully."""
    with patch("strands_pack.twilio_tool._get_requests") as mock_get_requests:
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": [mock_message_response]}
        mock_requests.get.return_value = mock_response
        mock_get_requests.return_value = mock_requests

        with patch("strands_pack.twilio_tool._get_credentials", return_value=("AC123", "token123")):
            from strands_pack import twilio_tool

            result = twilio_tool(action="list_messages", limit=10)

            assert result["success"] is True
            assert result["action"] == "list_messages"
            assert result["count"] == 1


def test_twilio_lookup_success():
    """Test phone number lookup successfully."""
    with patch("strands_pack.twilio_tool._get_requests") as mock_get_requests:
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "phone_number": "+15551234567",
            "national_format": "(555) 123-4567",
            "country_code": "US",
            "carrier": {"name": "Verizon"},
        }
        mock_requests.get.return_value = mock_response
        mock_get_requests.return_value = mock_requests

        with patch("strands_pack.twilio_tool._get_credentials", return_value=("AC123", "token123")):
            from strands_pack import twilio_tool

            result = twilio_tool(action="lookup", phone_number="+15551234567")

            assert result["success"] is True
            assert result["action"] == "lookup"
            assert result["lookup"]["country_code"] == "US"


def test_twilio_get_account_success():
    """Test getting account info successfully."""
    with patch("strands_pack.twilio_tool._get_requests") as mock_get_requests:
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "sid": "AC123456789",
            "friendly_name": "Test Account",
            "status": "active",
            "type": "Full",
            "date_created": "2020-01-01T00:00:00Z",
        }
        mock_requests.get.return_value = mock_response
        mock_get_requests.return_value = mock_requests

        with patch("strands_pack.twilio_tool._get_credentials", return_value=("AC123", "token123")):
            from strands_pack import twilio_tool

            result = twilio_tool(action="get_account")

            assert result["success"] is True
            assert result["action"] == "get_account"
            assert result["account"]["status"] == "active"


def test_twilio_missing_credentials():
    """Test error when credentials are not set."""
    with patch.dict("os.environ", {}, clear=True):
        from strands_pack import twilio_tool

        result = twilio_tool(action="send_sms", to="+15559876543", body="Test")

        assert result["success"] is False
        assert "TWILIO" in result["error"]


def test_twilio_api_error():
    """Test handling of Twilio API errors."""
    with patch("strands_pack.twilio_tool._get_requests") as mock_get_requests:
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "code": 21211,
            "message": "Invalid 'To' Phone Number",
        }
        mock_requests.post.return_value = mock_response
        mock_get_requests.return_value = mock_requests

        with patch("strands_pack.twilio_tool._get_credentials", return_value=("AC123", "token123")):
            with patch("strands_pack.twilio_tool._get_default_from", return_value="+15551234567"):
                from strands_pack import twilio_tool

                result = twilio_tool(
                    action="send_sms",
                    to="invalid",
                    body="Test",
                )

                assert result["success"] is False
                assert "21211" in result["error"] or "Invalid" in result["error"]


def test_twilio_unknown_action():
    """Test error for unknown action."""
    from strands_pack import twilio_tool

    result = twilio_tool(action="unknown_action")

    assert result["success"] is False
    assert "Unknown action" in result["error"]
    assert "available_actions" in result
