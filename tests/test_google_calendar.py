from unittest.mock import MagicMock, patch


def test_google_calendar_invalid_action():
    from strands_pack.google_calendar import google_calendar

    with patch("strands_pack.google_calendar._get_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        res = google_calendar(action="nope")
        assert res["success"] is False
        assert "Unknown action" in res["error"]
        assert "available_actions" in res


def test_google_calendar_missing_event_id():
    from strands_pack.google_calendar import google_calendar

    with patch("strands_pack.google_calendar._get_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        res = google_calendar(action="get_event", calendar_id="primary")
        assert res["success"] is False
        assert "event_id" in res["error"]


def test_list_calendars_calls_api():
    from strands_pack.google_calendar import google_calendar

    with patch("strands_pack.google_calendar._get_service") as mock_get_service:
        service = MagicMock()
        service.calendarList.return_value.list.return_value.execute.return_value = {
            "items": [{"id": "primary"}]
        }
        mock_get_service.return_value = service

        res = google_calendar(action="list_calendars")
        assert res["success"] is True
        assert res["count"] == 1
        assert res["calendars"][0]["id"] == "primary"
        service.calendarList.return_value.list.assert_called_once_with()


def test_list_events_passes_query_params():
    from strands_pack.google_calendar import google_calendar

    with patch("strands_pack.google_calendar._get_service") as mock_get_service:
        service = MagicMock()
        service.events.return_value.list.return_value.execute.return_value = {
            "items": [{"id": "evt_1"}]
        }
        mock_get_service.return_value = service

        res = google_calendar(
            action="list_events",
            calendar_id="primary",
            time_min="2026-01-01T00:00:00Z",
            time_max="2026-02-01T00:00:00Z",
            max_results=5,
            single_events=True,
            order_by="startTime",
            q="standup",
        )

        assert res["success"] is True
        assert res["count"] == 1
        assert res["events"][0]["id"] == "evt_1"

        service.events.return_value.list.assert_called_once_with(
            calendarId="primary",
            maxResults=5,
            singleEvents=True,
            orderBy="startTime",
            timeMin="2026-01-01T00:00:00Z",
            timeMax="2026-02-01T00:00:00Z",
            q="standup",
        )


def test_create_event_calls_insert():
    from strands_pack.google_calendar import google_calendar

    with patch("strands_pack.google_calendar._get_service") as mock_get_service:
        service = MagicMock()
        service.events.return_value.insert.return_value.execute.return_value = {"id": "created_evt"}
        mock_get_service.return_value = service

        event = {
            "summary": "Demo",
            "start": {"dateTime": "2026-01-31T10:00:00Z"},
            "end": {"dateTime": "2026-01-31T10:30:00Z"},
        }

        res = google_calendar(
            action="create_event",
            calendar_id="primary",
            event=event,
        )

        assert res["success"] is True
        assert res["event"]["id"] == "created_evt"
        service.events.return_value.insert.assert_called_once_with(calendarId="primary", body=event)


def test_get_event_requires_event_id():
    from strands_pack.google_calendar import google_calendar

    with patch("strands_pack.google_calendar._get_service") as mock_get_service:
        service = MagicMock()
        mock_get_service.return_value = service

        res = google_calendar(action="get_event", calendar_id="primary", event_id="")
        assert res["success"] is False
        assert "event_id is required" in res["error"]
        assert service.events.called is False


def test_get_event_calls_api():
    from strands_pack.google_calendar import google_calendar

    with patch("strands_pack.google_calendar._get_service") as mock_get_service:
        service = MagicMock()
        service.events.return_value.get.return_value.execute.return_value = {
            "id": "evt_1",
            "summary": "Test Event"
        }
        mock_get_service.return_value = service

        res = google_calendar(action="get_event", calendar_id="primary", event_id="evt_1")
        assert res["success"] is True
        assert res["event"]["id"] == "evt_1"
        assert res["event_id"] == "evt_1"
        service.events.return_value.get.assert_called_once_with(calendarId="primary", eventId="evt_1")


def test_update_event_requires_event_id():
    from strands_pack.google_calendar import google_calendar

    with patch("strands_pack.google_calendar._get_service") as mock_get_service:
        service = MagicMock()
        mock_get_service.return_value = service

        res = google_calendar(action="update_event", calendar_id="primary", event={"summary": "New"})
        assert res["success"] is False
        assert "event_id is required" in res["error"]


def test_update_event_requires_event():
    from strands_pack.google_calendar import google_calendar

    with patch("strands_pack.google_calendar._get_service") as mock_get_service:
        service = MagicMock()
        mock_get_service.return_value = service

        res = google_calendar(action="update_event", calendar_id="primary", event_id="evt_1")
        assert res["success"] is False
        assert "event is required" in res["error"]


def test_update_event_uses_patch():
    from strands_pack.google_calendar import google_calendar

    with patch("strands_pack.google_calendar._get_service") as mock_get_service:
        service = MagicMock()
        service.events.return_value.patch.return_value.execute.return_value = {
            "id": "evt_1",
            "summary": "Updated"
        }
        mock_get_service.return_value = service

        res = google_calendar(
            action="update_event",
            calendar_id="primary",
            event_id="evt_1",
            event={"summary": "Updated"},
            patch=True,
        )
        assert res["success"] is True
        assert res["event"]["summary"] == "Updated"
        assert res["patch"] is True
        service.events.return_value.patch.assert_called_once()


def test_update_event_uses_update():
    from strands_pack.google_calendar import google_calendar

    with patch("strands_pack.google_calendar._get_service") as mock_get_service:
        service = MagicMock()
        service.events.return_value.update.return_value.execute.return_value = {
            "id": "evt_1",
            "summary": "Full Update"
        }
        mock_get_service.return_value = service

        res = google_calendar(
            action="update_event",
            calendar_id="primary",
            event_id="evt_1",
            event={"summary": "Full Update"},
            patch=False,
        )
        assert res["success"] is True
        assert res["patch"] is False
        service.events.return_value.update.assert_called_once()


def test_delete_event_requires_event_id():
    from strands_pack.google_calendar import google_calendar

    with patch("strands_pack.google_calendar._get_service") as mock_get_service:
        service = MagicMock()
        mock_get_service.return_value = service

        res = google_calendar(action="delete_event", calendar_id="primary")
        assert res["success"] is False
        assert "event_id is required" in res["error"]


def test_delete_event_calls_api():
    from strands_pack.google_calendar import google_calendar

    with patch("strands_pack.google_calendar._get_service") as mock_get_service:
        service = MagicMock()
        mock_get_service.return_value = service

        res = google_calendar(action="delete_event", calendar_id="primary", event_id="evt_1")
        assert res["success"] is True
        assert res["deleted"] is True
        assert res["event_id"] == "evt_1"
        service.events.return_value.delete.assert_called_once()


def test_quick_add_requires_text():
    from strands_pack.google_calendar import google_calendar

    with patch("strands_pack.google_calendar._get_service") as mock_get_service:
        service = MagicMock()
        mock_get_service.return_value = service

        res = google_calendar(action="quick_add", calendar_id="primary")
        assert res["success"] is False
        assert "text is required" in res["error"]


def test_quick_add_calls_api():
    from strands_pack.google_calendar import google_calendar

    with patch("strands_pack.google_calendar._get_service") as mock_get_service:
        service = MagicMock()
        service.events.return_value.quickAdd.return_value.execute.return_value = {
            "id": "quick_evt",
            "summary": "Coffee tomorrow 10am"
        }
        mock_get_service.return_value = service

        res = google_calendar(action="quick_add", calendar_id="primary", text="Coffee tomorrow 10am")
        assert res["success"] is True
        assert res["event"]["id"] == "quick_evt"
        service.events.return_value.quickAdd.assert_called_once_with(calendarId="primary", text="Coffee tomorrow 10am")


def test_google_calendar_auth_required():
    from strands_pack.google_calendar import google_calendar

    with patch("strands_pack.google_calendar._get_service") as mock_get_service:
        mock_get_service.return_value = None  # No credentials

        res = google_calendar(action="list_calendars")
        assert res["success"] is False
        assert res.get("auth_required") is True


def test_create_event_with_send_updates():
    from strands_pack.google_calendar import google_calendar

    with patch("strands_pack.google_calendar._get_service") as mock_get_service:
        service = MagicMock()
        service.events.return_value.insert.return_value.execute.return_value = {"id": "evt_1"}
        mock_get_service.return_value = service

        event = {"summary": "Meeting"}

        res = google_calendar(
            action="create_event",
            calendar_id="primary",
            event=event,
            send_updates="all",
        )

        assert res["success"] is True
        service.events.return_value.insert.assert_called_once_with(
            calendarId="primary",
            body=event,
            sendUpdates="all",
        )


def test_default_calendar_id():
    from strands_pack.google_calendar import google_calendar

    with patch("strands_pack.google_calendar._get_service") as mock_get_service:
        service = MagicMock()
        service.events.return_value.list.return_value.execute.return_value = {"items": []}
        mock_get_service.return_value = service

        res = google_calendar(action="list_events")  # No calendar_id provided
        assert res["success"] is True
        assert res["calendar_id"] == "primary"
