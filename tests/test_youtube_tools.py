"""Tests for YouTube read tool (offline/mocked)."""

from unittest.mock import MagicMock, patch


def test_youtube_unknown_action():
    from strands_pack import youtube_read

    with patch("strands_pack.youtube_read._get_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        result = youtube_read(action="nope")
        assert result["success"] is False
        assert "available_actions" in result


def test_youtube_search_requires_q():
    from strands_pack import youtube_read

    with patch("strands_pack.youtube_read._get_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        result = youtube_read(action="search")
        assert result["success"] is False
        assert "q is required" in result["error"]


def test_youtube_search_calls_api():
    from strands_pack import youtube_read

    mock_service = MagicMock()
    mock_service.search.return_value.list.return_value.execute.return_value = {
        "items": [{"id": 1}]
    }

    with patch("strands_pack.youtube_read._get_service") as mock_get_service:
        mock_get_service.return_value = mock_service
        result = youtube_read(
            action="search", q="ai agents", max_results=5, search_type="video"
        )
        assert result["success"] is True
        mock_service.search.return_value.list.assert_called_once()
        _, call_kwargs = mock_service.search.return_value.list.call_args
        assert call_kwargs["q"] == "ai agents"
        assert call_kwargs["maxResults"] == 5
        assert call_kwargs["type"] == "video"


def test_youtube_search_video_filters_duration_definition():
    from strands_pack import youtube_read

    mock_service = MagicMock()
    mock_service.search.return_value.list.return_value.execute.return_value = {
        "items": [{"id": 1}]
    }

    with patch("strands_pack.youtube_read._get_service") as mock_get_service:
        mock_get_service.return_value = mock_service
        result = youtube_read(
            action="search",
            q="lofi",
            search_type="video",
            video_duration="short",
            video_definition="high",
            max_results=3,
        )
        assert result["success"] is True
        _, call_kwargs = mock_service.search.return_value.list.call_args
        assert call_kwargs["videoDuration"] == "short"
        assert call_kwargs["videoDefinition"] == "high"


def test_youtube_search_video_filters_rejected_for_non_video():
    from strands_pack import youtube_read

    with patch("strands_pack.youtube_read._get_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        result = youtube_read(
            action="search",
            q="channels",
            search_type="channel",
            video_duration="short",
        )
        assert result["success"] is False
        assert "only valid when search_type='video'" in result["error"]


def test_youtube_get_videos_calls_api():
    from strands_pack import youtube_read

    mock_service = MagicMock()
    mock_service.videos.return_value.list.return_value.execute.return_value = {
        "items": [{"id": "x"}]
    }

    with patch("strands_pack.youtube_read._get_service") as mock_get_service:
        mock_get_service.return_value = mock_service
        result = youtube_read(action="get_videos", video_ids=["a", "b"], part="snippet")
        assert result["success"] is True
        mock_service.videos.return_value.list.assert_called_once_with(
            part="snippet", id="a,b"
        )


def test_youtube_get_channels_requires_selector():
    from strands_pack import youtube_read

    with patch("strands_pack.youtube_read._get_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        result = youtube_read(action="get_channels")
        assert result["success"] is False
        assert "Provide one of:" in result["error"]


def test_youtube_list_playlist_items_requires_playlist_id():
    from strands_pack import youtube_read

    with patch("strands_pack.youtube_read._get_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        result = youtube_read(action="list_playlist_items")
        assert result["success"] is False
        assert "playlist_id is required" in result["error"]


def test_youtube_list_playlist_items_uses_env_default_playlist_id(monkeypatch):
    from strands_pack import youtube_read

    mock_service = MagicMock()
    mock_service.playlistItems.return_value.list.return_value.execute.return_value = {
        "items": [{"id": "it1"}],
    }

    monkeypatch.setenv("MY_UPLOADED_VIDEO_PLAYLIST_ID", "PL_UPLOADS_123")
    with patch("strands_pack.youtube_read._get_service") as mock_get_service:
        mock_get_service.return_value = mock_service
        result = youtube_read(action="list_playlist_items")
        assert result["success"] is True
        mock_service.playlistItems.return_value.list.assert_called_once()
        _, call_kwargs = mock_service.playlistItems.return_value.list.call_args
        assert call_kwargs["playlistId"] == "PL_UPLOADS_123"


def test_youtube_get_comments_requires_video_id():
    from strands_pack import youtube_read

    with patch("strands_pack.youtube_read._get_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        result = youtube_read(action="get_comments")
        assert result["success"] is False
        assert "video_id is required" in result["error"]


def test_youtube_get_comments_calls_api():
    from strands_pack import youtube_read

    mock_service = MagicMock()
    mock_service.commentThreads.return_value.list.return_value.execute.return_value = {
        "items": [{"id": "ct1"}],
        "nextPageToken": "tok",
    }

    with patch("strands_pack.youtube_read._get_service") as mock_get_service:
        mock_get_service.return_value = mock_service
        result = youtube_read(action="get_comments", video_id="v1", max_results=5, include_replies=True)
        assert result["success"] is True
        mock_service.commentThreads.return_value.list.assert_called_once()
        _, call_kwargs = mock_service.commentThreads.return_value.list.call_args
        assert call_kwargs["videoId"] == "v1"
        assert call_kwargs["maxResults"] == 5
        assert call_kwargs["part"] == "snippet,replies"
        assert call_kwargs["textFormat"] == "plainText"
        assert result["items"] == [{"id": "ct1"}]
        assert result["next_page_token"] == "tok"


def test_youtube_list_playlists_requires_channel_id():
    from strands_pack import youtube_read

    with patch("strands_pack.youtube_read._get_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        result = youtube_read(action="list_playlists")
        assert result["success"] is False
        assert "channel_id is required" in result["error"]


def test_youtube_list_playlists_uses_env_default_channel_id(monkeypatch):
    from strands_pack import youtube_read

    mock_service = MagicMock()
    mock_service.playlists.return_value.list.return_value.execute.return_value = {
        "items": [{"id": "pl1"}],
        "nextPageToken": None,
    }

    monkeypatch.setenv("MY_CHANNEL_ID", "UC_ENV_123")
    with patch("strands_pack.youtube_read._get_service") as mock_get_service:
        mock_get_service.return_value = mock_service
        result = youtube_read(action="list_playlists")
        assert result["success"] is True
        mock_service.playlists.return_value.list.assert_called_once()
        _, call_kwargs = mock_service.playlists.return_value.list.call_args
        assert call_kwargs["channelId"] == "UC_ENV_123"


def test_youtube_list_playlists_uses_env_youtube_channel_id(monkeypatch):
    from strands_pack import youtube_read

    mock_service = MagicMock()
    mock_service.playlists.return_value.list.return_value.execute.return_value = {
        "items": [{"id": "pl1"}],
        "nextPageToken": None,
    }

    monkeypatch.setenv("YOUTUBE_CHANNEL_ID", "UC_ENV_456")
    with patch("strands_pack.youtube_read._get_service") as mock_get_service:
        mock_get_service.return_value = mock_service
        result = youtube_read(action="list_playlists")
        assert result["success"] is True
        _, call_kwargs = mock_service.playlists.return_value.list.call_args
        assert call_kwargs["channelId"] == "UC_ENV_456"


def test_youtube_list_playlist_items_uses_env_youtube_uploads_playlist_id(monkeypatch):
    from strands_pack import youtube_read

    mock_service = MagicMock()
    mock_service.playlistItems.return_value.list.return_value.execute.return_value = {
        "items": [{"id": "it1"}],
    }

    monkeypatch.setenv("YOUTUBE_UPLOADS_PLAYLIST_ID", "PL_ENV_456")
    with patch("strands_pack.youtube_read._get_service") as mock_get_service:
        mock_get_service.return_value = mock_service
        result = youtube_read(action="list_playlist_items")
        assert result["success"] is True
        _, call_kwargs = mock_service.playlistItems.return_value.list.call_args
        assert call_kwargs["playlistId"] == "PL_ENV_456"


def test_youtube_list_playlists_calls_api():
    from strands_pack import youtube_read

    mock_service = MagicMock()
    mock_service.playlists.return_value.list.return_value.execute.return_value = {
        "items": [{"id": "pl1"}],
        "nextPageToken": "token123",
    }

    with patch("strands_pack.youtube_read._get_service") as mock_get_service:
        mock_get_service.return_value = mock_service
        result = youtube_read(
            action="list_playlists", channel_id="UC123", max_results=5
        )
        assert result["success"] is True
        assert result["items"] == [{"id": "pl1"}]
        assert result["next_page_token"] == "token123"


def test_youtube_get_channels_by_id():
    from strands_pack import youtube_read

    mock_service = MagicMock()
    mock_service.channels.return_value.list.return_value.execute.return_value = {
        "items": [{"id": "ch1", "snippet": {"title": "Test Channel"}}]
    }

    with patch("strands_pack.youtube_read._get_service") as mock_get_service:
        mock_get_service.return_value = mock_service
        result = youtube_read(action="get_channels", channel_ids=["ch1"])
        assert result["success"] is True
        assert len(result["items"]) == 1


def test_youtube_api_key_required():
    from strands_pack import youtube_read

    with patch("strands_pack.youtube_read._get_service") as mock_get_service:
        mock_get_service.return_value = None
        result = youtube_read(action="search", q="test")
        assert result["success"] is False
        assert "YOUTUBE_API_KEY" in result["error"]
        assert "hint" in result
