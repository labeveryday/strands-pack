"""Tests for LinkedIn tool."""

from unittest.mock import MagicMock, patch


def test_linkedin_get_profile_success():
    """Test getting profile successfully."""
    with patch("strands_pack.linkedin._get_requests") as mock_get_requests:
        mock_requests = MagicMock()

        # Mock userinfo response
        userinfo_response = MagicMock()
        userinfo_response.status_code = 200
        userinfo_response.json.return_value = {
            "sub": "user-123",
            "name": "Test User",
            "given_name": "Test",
            "family_name": "User",
            "email": "test@example.com",
            "email_verified": True,
            "picture": "https://example.com/photo.jpg",
        }
        userinfo_response.raise_for_status = MagicMock()

        # Mock /me response (may fail, that's ok)
        me_response = MagicMock()
        me_response.status_code = 403
        me_response.json.return_value = {}

        mock_requests.get.side_effect = [userinfo_response, me_response]
        mock_get_requests.return_value = mock_requests

        with patch("strands_pack.linkedin._get_token", return_value="test-token"):
            from strands_pack import linkedin

            result = linkedin(action="get_profile")

            assert result["success"] is True
            assert result["action"] == "get_profile"
            assert result["profile"]["name"] == "Test User"
            assert result["profile"]["email"] == "test@example.com"


def test_linkedin_get_profile_unauthorized():
    """Test error when token is invalid."""
    with patch("strands_pack.linkedin._get_requests") as mock_get_requests:
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_requests.get.return_value = mock_response
        mock_get_requests.return_value = mock_requests

        with patch("strands_pack.linkedin._get_token", return_value="invalid-token"):
            from strands_pack import linkedin

            result = linkedin(action="get_profile")

            assert result["success"] is False
            assert "AuthenticationError" in result.get("error_type", "") or "Invalid" in result.get("error", "")


def test_linkedin_get_connections_permission_denied():
    """Test connections API requires special permission."""
    with patch("strands_pack.linkedin._get_requests") as mock_get_requests:
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_requests.get.return_value = mock_response
        mock_get_requests.return_value = mock_requests

        with patch("strands_pack.linkedin._get_token", return_value="test-token"):
            from strands_pack import linkedin

            result = linkedin(action="get_connections")

            assert result["success"] is False
            assert "PermissionError" in result.get("error_type", "") or "denied" in result.get("error", "").lower()


def test_linkedin_create_post_success():
    """Test creating a post successfully."""
    with patch("strands_pack.linkedin._get_requests") as mock_get_requests:
        mock_requests = MagicMock()

        # Mock profile response
        userinfo_response = MagicMock()
        userinfo_response.status_code = 200
        userinfo_response.json.return_value = {
            "sub": "user-123",
            "name": "Test User",
        }
        userinfo_response.raise_for_status = MagicMock()

        me_response = MagicMock()
        me_response.status_code = 403

        # Mock post response
        post_response = MagicMock()
        post_response.status_code = 201
        post_response.headers = {"X-RestLi-Id": "share-123"}
        post_response.raise_for_status = MagicMock()

        mock_requests.get.side_effect = [userinfo_response, me_response]
        mock_requests.post.return_value = post_response
        mock_get_requests.return_value = mock_requests

        with patch("strands_pack.linkedin._get_token", return_value="test-token"):
            from strands_pack import linkedin

            result = linkedin(
                action="create_post",
                text="Hello LinkedIn!",
                visibility="PUBLIC",
            )

            assert result["success"] is True
            assert result["action"] == "create_post"
            assert result["post_id"] == "share-123"


def test_linkedin_create_post_missing_text():
    """Test error when text is missing."""
    from strands_pack import linkedin

    result = linkedin(action="create_post")

    assert result["success"] is False
    assert "text" in result["error"]


def test_linkedin_share_url_success():
    """Test sharing a URL successfully."""
    with patch("strands_pack.linkedin._get_requests") as mock_get_requests:
        mock_requests = MagicMock()

        # Mock profile response
        userinfo_response = MagicMock()
        userinfo_response.status_code = 200
        userinfo_response.json.return_value = {"sub": "user-123"}
        userinfo_response.raise_for_status = MagicMock()

        me_response = MagicMock()
        me_response.status_code = 403

        # Mock post response
        post_response = MagicMock()
        post_response.status_code = 201
        post_response.headers = {"X-RestLi-Id": "share-456"}
        post_response.raise_for_status = MagicMock()

        mock_requests.get.side_effect = [userinfo_response, me_response]
        mock_requests.post.return_value = post_response
        mock_get_requests.return_value = mock_requests

        with patch("strands_pack.linkedin._get_token", return_value="test-token"):
            from strands_pack import linkedin

            result = linkedin(
                action="share_url",
                url="https://example.com/article",
                comment="Check this out!",
            )

            assert result["success"] is True
            assert result["action"] == "share_url"
            assert result["url"] == "https://example.com/article"


def test_linkedin_delete_post_success():
    """Test deleting a post successfully."""
    with patch("strands_pack.linkedin._get_requests") as mock_get_requests:
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.raise_for_status = MagicMock()
        mock_requests.delete.return_value = mock_response
        mock_get_requests.return_value = mock_requests

        with patch("strands_pack.linkedin._get_token", return_value="test-token"):
            from strands_pack import linkedin

            result = linkedin(action="delete_post", post_id="share-123")

            assert result["success"] is True
            assert result["action"] == "delete_post"
            assert result["deleted"] is True


def test_linkedin_delete_post_not_found():
    """Test error when post is not found."""
    with patch("strands_pack.linkedin._get_requests") as mock_get_requests:
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_requests.delete.return_value = mock_response
        mock_get_requests.return_value = mock_requests

        with patch("strands_pack.linkedin._get_token", return_value="test-token"):
            from strands_pack import linkedin

            result = linkedin(action="delete_post", post_id="nonexistent")

            assert result["success"] is False
            assert "not found" in result["error"].lower()


def test_linkedin_missing_token():
    """Test error when token is not set."""
    with patch.dict("os.environ", {}, clear=True):
        from strands_pack import linkedin

        result = linkedin(action="get_profile")

        assert result["success"] is False
        assert "LINKEDIN_ACCESS_TOKEN" in result["error"]


def test_linkedin_unknown_action():
    """Test error for unknown action."""
    from strands_pack import linkedin

    result = linkedin(action="unknown_action")

    assert result["success"] is False
    assert "Unknown action" in result["error"]
    assert "available_actions" in result
