"""Tests for YouTube write tool (offline/mocked)."""

from unittest.mock import MagicMock, patch


def test_youtube_write_unknown_action():
    from strands_pack import youtube_write

    with patch("strands_pack.youtube_write._get_write_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        result = youtube_write(action="nope")
        assert result["success"] is False
        assert "available_actions" in result


def test_youtube_write_auth_required():
    from strands_pack import youtube_write

    with patch("strands_pack.youtube_write._get_write_service") as mock_get_service:
        mock_get_service.return_value = None
        with patch("strands_pack.google_auth.needs_auth_response") as mock_auth:
            mock_auth.return_value = {"success": False, "auth_required": True}
            result = youtube_write(action="update_video_metadata", video_id="v1", title="x")
            assert result["success"] is False
            assert result["auth_required"] is True
            # Uses dedicated "youtube_write" preset for auth
            mock_auth.assert_called_once_with("youtube_write")


def test_youtube_write_update_video_metadata_calls_update():
    from strands_pack import youtube_write

    mock_service = MagicMock()
    # Existing snippet fetch
    mock_service.videos.return_value.list.return_value.execute.return_value = {
        "items": [{"snippet": {"title": "old", "description": "d", "categoryId": "22", "tags": ["a"]}}]
    }
    # Update response
    mock_service.videos.return_value.update.return_value.execute.return_value = {"id": "v1"}

    with patch("strands_pack.youtube_write._get_write_service") as mock_get_service:
        mock_get_service.return_value = mock_service
        result = youtube_write(action="update_video_metadata", video_id="v1", title="new title", tags=["t1", "t2"])
        assert result["success"] is True
        mock_service.videos.return_value.list.assert_called_once_with(part="snippet", id="v1")
        mock_service.videos.return_value.update.assert_called_once()
        _, call_kwargs = mock_service.videos.return_value.update.call_args
        assert call_kwargs["part"] == "snippet"
        assert call_kwargs["body"]["id"] == "v1"
        assert call_kwargs["body"]["snippet"]["title"] == "new title"
        assert call_kwargs["body"]["snippet"]["tags"] == ["t1", "t2"]
        # preserved fields
        assert call_kwargs["body"]["snippet"]["description"] == "d"
        assert call_kwargs["body"]["snippet"]["categoryId"] == "22"


def test_youtube_write_add_video_to_playlist_calls_insert(monkeypatch):
    from strands_pack import youtube_write

    mock_service = MagicMock()
    mock_service.playlistItems.return_value.insert.return_value.execute.return_value = {"id": "pli1"}

    monkeypatch.setenv("MY_UPLOADED_VIDEO_PLAYLIST_ID", "PL_ENV")
    with patch("strands_pack.youtube_write._get_write_service") as mock_get_service:
        mock_get_service.return_value = mock_service
        result = youtube_write(action="add_video_to_playlist", video_id="v1")
        assert result["success"] is True
        mock_service.playlistItems.return_value.insert.assert_called_once()
        _, call_kwargs = mock_service.playlistItems.return_value.insert.call_args
        assert call_kwargs["part"] == "snippet"
        assert call_kwargs["body"]["snippet"]["playlistId"] == "PL_ENV"
        assert call_kwargs["body"]["snippet"]["resourceId"]["videoId"] == "v1"


def test_youtube_write_add_video_to_playlist_uses_youtube_uploads_playlist_id(monkeypatch):
    from strands_pack import youtube_write

    mock_service = MagicMock()
    mock_service.playlistItems.return_value.insert.return_value.execute.return_value = {"id": "pli1"}

    monkeypatch.setenv("YOUTUBE_UPLOADS_PLAYLIST_ID", "PL_ENV_2")
    with patch("strands_pack.youtube_write._get_write_service") as mock_get_service:
        mock_get_service.return_value = mock_service
        result = youtube_write(action="add_video_to_playlist", video_id="v1")
        assert result["success"] is True
        _, call_kwargs = mock_service.playlistItems.return_value.insert.call_args
        assert call_kwargs["body"]["snippet"]["playlistId"] == "PL_ENV_2"


def test_youtube_write_remove_by_playlist_item_id_calls_delete():
    from strands_pack import youtube_write

    mock_service = MagicMock()
    mock_service.playlistItems.return_value.delete.return_value.execute.return_value = {}

    with patch("strands_pack.youtube_write._get_write_service") as mock_get_service:
        mock_get_service.return_value = mock_service
        result = youtube_write(action="remove_video_from_playlist", playlist_item_id="pli1")
        assert result["success"] is True
        mock_service.playlistItems.return_value.delete.assert_called_once_with(id="pli1")


def test_youtube_write_delete_video_requires_confirm_text():
    from strands_pack import youtube_write

    mock_service = MagicMock()
    mock_service.videos.return_value.delete.return_value.execute.return_value = {}

    with patch("strands_pack.youtube_write._get_write_service") as mock_get_service:
        mock_get_service.return_value = mock_service
        res = youtube_write(action="delete_video", video_id="v1")
        assert res["success"] is False
        assert "confirm_text" in res["error"]

        res2 = youtube_write(action="delete_video", video_id="v1", confirm_text="DELETE_VIDEO v1")
        assert res2["success"] is True
        mock_service.videos.return_value.delete.assert_called_once_with(id="v1")


def test_youtube_write_delete_playlist_requires_confirm_text():
    from strands_pack import youtube_write

    mock_service = MagicMock()
    mock_service.playlists.return_value.delete.return_value.execute.return_value = {}

    with patch("strands_pack.youtube_write._get_write_service") as mock_get_service:
        mock_get_service.return_value = mock_service
        res = youtube_write(action="delete_playlist", playlist_id="pl1")
        assert res["success"] is False

        res2 = youtube_write(action="delete_playlist", playlist_id="pl1", confirm_text="DELETE_PLAYLIST pl1")
        assert res2["success"] is True
        mock_service.playlists.return_value.delete.assert_called_once_with(id="pl1")


def test_youtube_write_set_privacy_requires_confirm_text():
    from strands_pack import youtube_write

    mock_service = MagicMock()
    mock_service.videos.return_value.list.return_value.execute.return_value = {"items": [{"status": {"privacyStatus": "public"}}]}
    mock_service.videos.return_value.update.return_value.execute.return_value = {"id": "v1"}

    with patch("strands_pack.youtube_write._get_write_service") as mock_get_service:
        mock_get_service.return_value = mock_service
        res = youtube_write(action="set_video_privacy", video_id="v1", privacy_status="private")
        assert res["success"] is False

        res2 = youtube_write(
            action="set_video_privacy",
            video_id="v1",
            privacy_status="private",
            confirm_text="SET_PRIVACY v1 private",
        )
        assert res2["success"] is True
        mock_service.videos.return_value.update.assert_called_once()


