"""Tests for X (Twitter) tool."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_user_data():
    """Create mock user data from API."""
    return {
        "id": "12345",
        "username": "testuser",
        "name": "Test User",
        "description": "A test user",
        "location": "Test City",
        "url": "https://example.com",
        "profile_image_url": "https://example.com/avatar.jpg",
        "verified": False,
        "created_at": "2020-01-01T00:00:00.000Z",
        "public_metrics": {
            "followers_count": 100,
            "following_count": 50,
            "tweet_count": 500,
        },
    }


@pytest.fixture
def mock_tweet_data():
    """Create mock tweet data from API."""
    return {
        "id": "98765",
        "text": "This is a test tweet",
        "author_id": "12345",
        "created_at": "2024-01-15T10:00:00.000Z",
        "conversation_id": "98765",
        "public_metrics": {
            "retweet_count": 10,
            "reply_count": 5,
            "like_count": 50,
        },
        "possibly_sensitive": False,
        "lang": "en",
        "source": "Twitter Web App",
        "reply_settings": "everyone",
    }


def test_x_get_user_success(mock_user_data):
    """Test getting a user by username successfully."""
    with patch("strands_pack.x._get_requests") as mock_get_requests:
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": mock_user_data}
        mock_requests.get.return_value = mock_response
        mock_get_requests.return_value = mock_requests

        with patch("strands_pack.x._get_token", return_value="test-token"):
            from strands_pack import x

            result = x(action="get_user", username="testuser")

            assert result["success"] is True
            assert result["action"] == "get_user"
            assert result["user"]["username"] == "testuser"
            assert result["user"]["name"] == "Test User"


def test_x_get_user_strips_at_symbol(mock_user_data):
    """Test that @ is stripped from username."""
    with patch("strands_pack.x._get_requests") as mock_get_requests:
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": mock_user_data}
        mock_requests.get.return_value = mock_response
        mock_get_requests.return_value = mock_requests

        with patch("strands_pack.x._get_token", return_value="test-token"):
            from strands_pack import x

            result = x(action="get_user", username="@testuser")

            assert result["success"] is True
            # Verify the API was called without @
            call_args = mock_requests.get.call_args
            assert "@" not in call_args[0][0]


def test_x_get_user_not_found():
    """Test error when user is not found."""
    with patch("strands_pack.x._get_requests") as mock_get_requests:
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}  # No data
        mock_requests.get.return_value = mock_response
        mock_get_requests.return_value = mock_requests

        with patch("strands_pack.x._get_token", return_value="test-token"):
            from strands_pack import x

            result = x(action="get_user", username="nonexistent")

            assert result["success"] is False
            assert "not found" in result["error"].lower()


def test_x_get_user_by_id_success(mock_user_data):
    """Test getting a user by ID successfully."""
    with patch("strands_pack.x._get_requests") as mock_get_requests:
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": mock_user_data}
        mock_requests.get.return_value = mock_response
        mock_get_requests.return_value = mock_requests

        with patch("strands_pack.x._get_token", return_value="test-token"):
            from strands_pack import x

            result = x(action="get_user_by_id", user_id="12345")

            assert result["success"] is True
            assert result["action"] == "get_user_by_id"
            assert result["user"]["id"] == "12345"


def test_x_get_user_tweets_success(mock_tweet_data):
    """Test getting user tweets successfully."""
    with patch("strands_pack.x._get_requests") as mock_get_requests:
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [mock_tweet_data]}
        mock_requests.get.return_value = mock_response
        mock_get_requests.return_value = mock_requests

        with patch("strands_pack.x._get_token", return_value="test-token"):
            from strands_pack import x

            result = x(action="get_user_tweets", user_id="12345")

            assert result["success"] is True
            assert result["action"] == "get_user_tweets"
            assert result["count"] == 1
            assert result["tweets"][0]["text"] == "This is a test tweet"


def test_x_get_tweet_success(mock_tweet_data):
    """Test getting a single tweet successfully."""
    with patch("strands_pack.x._get_requests") as mock_get_requests:
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": mock_tweet_data}
        mock_requests.get.return_value = mock_response
        mock_get_requests.return_value = mock_requests

        with patch("strands_pack.x._get_token", return_value="test-token"):
            from strands_pack import x

            result = x(action="get_tweet", tweet_id="98765")

            assert result["success"] is True
            assert result["action"] == "get_tweet"
            assert result["tweet"]["id"] == "98765"


def test_x_search_recent_success(mock_tweet_data):
    """Test searching recent tweets successfully."""
    with patch("strands_pack.x._get_requests") as mock_get_requests:
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [mock_tweet_data]}
        mock_requests.get.return_value = mock_response
        mock_get_requests.return_value = mock_requests

        with patch("strands_pack.x._get_token", return_value="test-token"):
            from strands_pack import x

            result = x(action="search_recent", query="python")

            assert result["success"] is True
            assert result["action"] == "search_recent"
            assert result["query"] == "python"
            assert result["count"] == 1


def test_x_get_user_followers_success(mock_user_data):
    """Test getting user followers successfully."""
    with patch("strands_pack.x._get_requests") as mock_get_requests:
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [mock_user_data]}
        mock_requests.get.return_value = mock_response
        mock_get_requests.return_value = mock_requests

        with patch("strands_pack.x._get_token", return_value="test-token"):
            from strands_pack import x

            result = x(action="get_user_followers", user_id="12345")

            assert result["success"] is True
            assert result["action"] == "get_user_followers"
            assert result["count"] == 1


def test_x_rate_limit_error():
    """Test handling rate limit errors."""
    with patch("strands_pack.x._get_requests") as mock_get_requests:
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_requests.get.return_value = mock_response
        mock_get_requests.return_value = mock_requests

        with patch("strands_pack.x._get_token", return_value="test-token"):
            from strands_pack import x

            result = x(action="get_user", username="testuser")

            assert result["success"] is False
            assert "rate limit" in result["error"].lower()


def test_x_unauthorized_error():
    """Test handling unauthorized errors."""
    with patch("strands_pack.x._get_requests") as mock_get_requests:
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_requests.get.return_value = mock_response
        mock_get_requests.return_value = mock_requests

        with patch("strands_pack.x._get_token", return_value="invalid-token"):
            from strands_pack import x

            result = x(action="get_user", username="testuser")

            assert result["success"] is False
            assert "token" in result["error"].lower() or "invalid" in result["error"].lower()


def test_x_missing_required_params():
    """Test error when required params are missing."""
    from strands_pack import x

    result = x(action="get_user")  # Missing username

    assert result["success"] is False
    assert "username" in result["error"]


def test_x_missing_token():
    """Test error when token is not set."""
    with patch.dict("os.environ", {}, clear=True):
        from strands_pack import x

        result = x(action="get_user", username="test")

        assert result["success"] is False
        assert "X_BEARER_TOKEN" in result["error"]


def test_x_unknown_action():
    """Test error for unknown action."""
    from strands_pack import x

    result = x(action="unknown_action")

    assert result["success"] is False
    assert "Unknown action" in result["error"]
    assert "available_actions" in result
