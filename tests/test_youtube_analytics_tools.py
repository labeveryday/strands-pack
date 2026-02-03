"""Tests for YouTube Analytics tool (offline/mocked)."""

from unittest.mock import MagicMock, patch


def test_youtube_analytics_unknown_action():
    from strands_pack.youtube_analytics import youtube_analytics

    with patch("strands_pack.youtube_analytics._get_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        result = youtube_analytics(action="nope")
        assert result["success"] is False
        assert "available_actions" in result


def test_youtube_analytics_requires_start_date():
    from strands_pack.youtube_analytics import youtube_analytics

    with patch("strands_pack.youtube_analytics._get_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        result = youtube_analytics(action="query_report")
        assert result["success"] is False
        assert "start_date is required" in result["error"]


def test_youtube_analytics_requires_end_date():
    from strands_pack.youtube_analytics import youtube_analytics

    with patch("strands_pack.youtube_analytics._get_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        result = youtube_analytics(action="query_report", start_date="2026-01-01")
        assert result["success"] is False
        assert "end_date is required" in result["error"]


def test_youtube_analytics_requires_metrics():
    from strands_pack.youtube_analytics import youtube_analytics

    with patch("strands_pack.youtube_analytics._get_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        result = youtube_analytics(
            action="query_report",
            start_date="2026-01-01",
            end_date="2026-01-07",
        )
        assert result["success"] is False
        assert "metrics is required" in result["error"]


def test_youtube_analytics_query_report_calls_api():
    from strands_pack.youtube_analytics import youtube_analytics

    with patch("strands_pack.youtube_analytics._get_service") as mock_get_service:
        service = MagicMock()
        service.reports.return_value.query.return_value.execute.return_value = {
            "columnHeaders": [{"name": "day"}],
            "rows": [["2026-01-01"]],
        }
        mock_get_service.return_value = service

        result = youtube_analytics(
            action="query_report",
            start_date="2026-01-01",
            end_date="2026-01-07",
            metrics=["views", "estimatedMinutesWatched"],
            dimensions=["day"],
            sort=["day"],
        )

        assert result["success"] is True
        service.reports.return_value.query.assert_called_once()
        _, call_kwargs = service.reports.return_value.query.call_args
        assert call_kwargs["startDate"] == "2026-01-01"
        assert call_kwargs["endDate"] == "2026-01-07"
        assert call_kwargs["metrics"] == "views,estimatedMinutesWatched"
        assert call_kwargs["dimensions"] == "day"
        assert call_kwargs["sort"] == "day"


def test_youtube_analytics_query_report_with_all_params():
    from strands_pack.youtube_analytics import youtube_analytics

    with patch("strands_pack.youtube_analytics._get_service") as mock_get_service:
        service = MagicMock()
        service.reports.return_value.query.return_value.execute.return_value = {
            "columnHeaders": [{"name": "views"}],
            "rows": [[1000]],
        }
        mock_get_service.return_value = service

        result = youtube_analytics(
            action="query_report",
            ids="channel==UC_x5XG1",
            start_date="2026-01-01",
            end_date="2026-01-31",
            metrics="views",
            dimensions="video",
            filters="video==VIDEO_ID",
            sort="-views",
            max_results=10,
            start_index=0,
            currency="USD",
            include_historical_channel_data=True,
        )

        assert result["success"] is True
        _, call_kwargs = service.reports.return_value.query.call_args
        assert call_kwargs["ids"] == "channel==UC_x5XG1"
        assert call_kwargs["maxResults"] == 10
        assert call_kwargs["startIndex"] == 0
        assert call_kwargs["currency"] == "USD"
        assert call_kwargs["includeHistoricalChannelData"] is True
        assert call_kwargs["filters"] == "video==VIDEO_ID"


def test_youtube_analytics_default_ids():
    from strands_pack.youtube_analytics import youtube_analytics

    with patch("strands_pack.youtube_analytics._get_service") as mock_get_service:
        service = MagicMock()
        service.reports.return_value.query.return_value.execute.return_value = {
            "columnHeaders": [],
            "rows": [],
        }
        mock_get_service.return_value = service

        result = youtube_analytics(
            action="query_report",
            start_date="2026-01-01",
            end_date="2026-01-07",
            metrics="views",
        )

        assert result["success"] is True
        _, call_kwargs = service.reports.return_value.query.call_args
        assert call_kwargs["ids"] == "channel==MINE"


def test_youtube_analytics_auth_required():
    from strands_pack.youtube_analytics import youtube_analytics

    with patch("strands_pack.youtube_analytics._get_service") as mock_get_service:
        mock_get_service.return_value = None  # No credentials

        result = youtube_analytics(action="query_report")
        assert result["success"] is False
        assert result.get("auth_required") is True


def test_youtube_analytics_api_error():
    from strands_pack.youtube_analytics import youtube_analytics

    with patch("strands_pack.youtube_analytics._get_service") as mock_get_service:
        service = MagicMock()
        service.reports.return_value.query.return_value.execute.side_effect = Exception(
            "API Error"
        )
        mock_get_service.return_value = service

        result = youtube_analytics(
            action="query_report",
            start_date="2026-01-01",
            end_date="2026-01-07",
            metrics="views",
        )

        assert result["success"] is False
        assert "API Error" in result["error"]
