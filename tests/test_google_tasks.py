from unittest.mock import MagicMock, patch


def test_google_tasks_invalid_action():
    from strands_pack.google_tasks import google_tasks

    with patch("strands_pack.google_tasks._get_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        res = google_tasks(action="nope")
        assert res["success"] is False
        assert "Unknown action" in res["error"]


def test_google_tasks_missing_tasklist_id():
    from strands_pack.google_tasks import google_tasks

    with patch("strands_pack.google_tasks._get_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        res = google_tasks(action="list_tasks")
        assert res["success"] is False
        assert "tasklist_id" in res["error"]


def test_google_tasks_missing_title():
    from strands_pack.google_tasks import google_tasks

    with patch("strands_pack.google_tasks._get_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        res = google_tasks(action="create_task", tasklist_id="tl1")
        assert res["success"] is False
        assert "title" in res["error"]


def test_google_tasks_missing_task_id():
    from strands_pack.google_tasks import google_tasks

    with patch("strands_pack.google_tasks._get_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        res = google_tasks(action="complete_task", tasklist_id="tl1")
        assert res["success"] is False
        assert "task_id" in res["error"]


def test_list_tasklists_calls_api():
    from strands_pack.google_tasks import google_tasks

    with patch("strands_pack.google_tasks._get_service") as mock_get_service:
        service = MagicMock()
        service.tasklists.return_value.list.return_value.execute.return_value = {
            "items": [{"id": "tl1", "title": "My Tasks"}]
        }
        mock_get_service.return_value = service

        res = google_tasks(action="list_tasklists")
        assert res["success"] is True
        assert res["count"] == 1
        assert res["tasklists"][0]["id"] == "tl1"


def test_list_tasks_calls_api():
    from strands_pack.google_tasks import google_tasks

    with patch("strands_pack.google_tasks._get_service") as mock_get_service:
        service = MagicMock()
        service.tasks.return_value.list.return_value.execute.return_value = {
            "items": [{"id": "t1", "title": "Task 1"}]
        }
        mock_get_service.return_value = service

        res = google_tasks(action="list_tasks", tasklist_id="tl1")
        assert res["success"] is True
        assert res["count"] == 1
        assert res["tasks"][0]["id"] == "t1"
        assert res["tasklist_id"] == "tl1"


def test_create_task_calls_api():
    from strands_pack.google_tasks import google_tasks

    with patch("strands_pack.google_tasks._get_service") as mock_get_service:
        service = MagicMock()
        service.tasks.return_value.insert.return_value.execute.return_value = {
            "id": "t1",
            "title": "Do it"
        }
        mock_get_service.return_value = service

        res = google_tasks(action="create_task", tasklist_id="tl1", title="Do it")
        assert res["success"] is True
        assert res["task"]["id"] == "t1"
        assert res["tasklist_id"] == "tl1"


def test_create_task_with_notes_and_due():
    from strands_pack.google_tasks import google_tasks

    with patch("strands_pack.google_tasks._get_service") as mock_get_service:
        service = MagicMock()
        service.tasks.return_value.insert.return_value.execute.return_value = {
            "id": "t1",
            "title": "Do it",
            "notes": "Some notes",
            "due": "2025-12-01T00:00:00Z"
        }
        mock_get_service.return_value = service

        res = google_tasks(
            action="create_task",
            tasklist_id="tl1",
            title="Do it",
            notes="Some notes",
            due="2025-12-01T00:00:00Z",
        )
        assert res["success"] is True
        assert res["task"]["id"] == "t1"


def test_complete_task_calls_api():
    from strands_pack.google_tasks import google_tasks

    with patch("strands_pack.google_tasks._get_service") as mock_get_service:
        service = MagicMock()
        service.tasks.return_value.get.return_value.execute.return_value = {
            "id": "t1",
            "status": "needsAction"
        }
        service.tasks.return_value.update.return_value.execute.return_value = {
            "id": "t1",
            "status": "completed"
        }
        mock_get_service.return_value = service

        res = google_tasks(
            action="complete_task",
            tasklist_id="tl1",
            task_id="t1",
        )
        assert res["success"] is True
        assert res["task"]["status"] == "completed"
        assert res["task_id"] == "t1"


def test_google_tasks_auth_required():
    from strands_pack.google_tasks import google_tasks

    with patch("strands_pack.google_tasks._get_service") as mock_get_service:
        mock_get_service.return_value = None  # No credentials

        res = google_tasks(action="list_tasklists")
        assert res["success"] is False
        assert res.get("auth_required") is True
