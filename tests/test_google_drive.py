from unittest.mock import MagicMock, patch


def test_google_drive_invalid_action():
    from strands_pack.google_drive import google_drive

    with patch("strands_pack.google_drive._get_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        res = google_drive(action="nope")
        assert res["success"] is False
        assert res["error_type"] == "InvalidAction"
        assert "available_actions" in res


def test_google_drive_missing_file_id():
    from strands_pack.google_drive import google_drive

    with patch("strands_pack.google_drive._get_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        res = google_drive(action="get_file")
        assert res["success"] is False
        assert "file_id is required" in res["error"]


def test_list_files_passes_query_params():
    from strands_pack.google_drive import google_drive

    mock_service = MagicMock()
    mock_service.files.return_value.list.return_value.execute.return_value = {
        "files": [{"id": "f1"}],
        "nextPageToken": "tok",
    }

    with patch("strands_pack.google_drive._get_service") as mock_get_service:
        mock_get_service.return_value = mock_service

        res = google_drive(
            action="list_files",
            q="name contains 'report' and trashed=false",
            page_size=5,
            page_token="p",
        )

        assert res["success"] is True
        assert res["count"] == 1
        assert res["files"][0]["id"] == "f1"
        assert res["next_page_token"] == "tok"

        mock_service.files.return_value.list.assert_called_once()
        _, kwargs = mock_service.files.return_value.list.call_args
        assert kwargs["q"] == "name contains 'report' and trashed=false"
        assert kwargs["pageSize"] == 5
        assert kwargs["pageToken"] == "p"
        assert "fields" in kwargs


def test_get_file_requires_file_id_without_calling_api():
    from strands_pack.google_drive import google_drive

    mock_service = MagicMock()

    with patch("strands_pack.google_drive._get_service") as mock_get_service:
        mock_get_service.return_value = mock_service

        res = google_drive(action="get_file", file_id="")
        assert res["success"] is False
        assert "file_id is required" in res["error"]
        assert mock_service.files.called is False


def test_delete_file_calls_delete():
    from strands_pack.google_drive import google_drive

    mock_service = MagicMock()
    mock_service.files.return_value.delete.return_value.execute.return_value = {}

    with patch("strands_pack.google_drive._get_service") as mock_get_service:
        mock_get_service.return_value = mock_service

        res = google_drive(action="delete_file", file_id="abc")
        assert res["success"] is False
        assert "confirm" in res["error"].lower()

        res2 = google_drive(action="delete_file", file_id="abc", confirm=True)
        assert res2["success"] is True
        assert res2["deleted"] is True


def test_delete_spreadsheet_alias_calls_delete():
    from strands_pack.google_drive import google_drive

    mock_service = MagicMock()
    mock_service.files.return_value.delete.return_value.execute.return_value = {}

    with patch("strands_pack.google_drive._get_service") as mock_get_service:
        mock_get_service.return_value = mock_service

        res = google_drive(action="delete_spreadsheet", file_id="abc")
        assert res["success"] is True
        assert res["deleted"] is True
        assert res["action"] == "delete_spreadsheet"
        mock_service.files.return_value.delete.assert_called_once_with(fileId="abc")


def test_create_folder():
    from strands_pack.google_drive import google_drive

    mock_service = MagicMock()
    mock_service.files.return_value.create.return_value.execute.return_value = {
        "id": "folder123",
        "name": "My Folder",
        "mimeType": "application/vnd.google-apps.folder",
    }

    with patch("strands_pack.google_drive._get_service") as mock_get_service:
        mock_get_service.return_value = mock_service

        res = google_drive(action="create_folder", name="My Folder", parent_id="parent123")
        assert res["success"] is True
        assert res["folder"]["id"] == "folder123"
        assert res["folder"]["name"] == "My Folder"

        mock_service.files.return_value.create.assert_called_once()
        call_kwargs = mock_service.files.return_value.create.call_args[1]
        assert call_kwargs["body"]["name"] == "My Folder"
        assert call_kwargs["body"]["mimeType"] == "application/vnd.google-apps.folder"
        assert call_kwargs["body"]["parents"] == ["parent123"]


def test_create_folder_requires_name():
    from strands_pack.google_drive import google_drive

    mock_service = MagicMock()

    with patch("strands_pack.google_drive._get_service") as mock_get_service:
        mock_get_service.return_value = mock_service

        res = google_drive(action="create_folder")
        assert res["success"] is False
        assert "name is required" in res["error"]


def test_get_file_success():
    from strands_pack.google_drive import google_drive

    mock_service = MagicMock()
    mock_service.files.return_value.get.return_value.execute.return_value = {
        "id": "file123",
        "name": "test.pdf",
        "mimeType": "application/pdf",
    }

    with patch("strands_pack.google_drive._get_service") as mock_get_service:
        mock_get_service.return_value = mock_service

        res = google_drive(action="get_file", file_id="file123")
        assert res["success"] is True
        assert res["file"]["id"] == "file123"
        assert res["file_id"] == "file123"


def test_auth_required_when_no_credentials():
    from strands_pack.google_drive import google_drive

    with patch("strands_pack.google_drive._get_service") as mock_get_service:
        mock_get_service.return_value = None  # Simulates no credentials

        res = google_drive(action="list_files")
        assert res["success"] is False
        assert res["auth_required"] is True
        assert "drive" in res.get("preset", "").lower() or "Authentication required" in res.get("error", "")


def test_export_file_calls_export_media(tmp_path):
    from strands_pack.google_drive import google_drive

    mock_service = MagicMock()
    mock_service.files.return_value.export_media.return_value = MagicMock()

    class FakeDownloader:
        def __init__(self, fh, request):
            self._done = False
        def next_chunk(self):
            if self._done:
                return None, True
            self._done = True
            return None, True

    with patch("strands_pack.google_drive._get_service") as mock_get_service, patch(
        "strands_pack.google_drive._MediaIoBaseDownload", FakeDownloader
    ):
        mock_get_service.return_value = mock_service
        out = tmp_path / "doc.pdf"
        res = google_drive(action="export_file", file_id="fid", export_mime_type="application/pdf", output_path=str(out))
        assert res["success"] is True
        mock_service.files.return_value.export_media.assert_called_once_with(fileId="fid", mimeType="application/pdf")


def test_trash_and_restore_call_update():
    from strands_pack.google_drive import google_drive

    mock_service = MagicMock()
    mock_service.files.return_value.update.return_value.execute.return_value = {"id": "f1", "trashed": True}

    with patch("strands_pack.google_drive._get_service") as mock_get_service:
        mock_get_service.return_value = mock_service

        res = google_drive(action="trash_file", file_id="f1")
        assert res["success"] is True
        assert res["trashed"] is True

        res2 = google_drive(action="restore_file", file_id="f1")
        assert res2["success"] is True
        assert res2["trashed"] is False


def test_rename_file_calls_update():
    from strands_pack.google_drive import google_drive

    mock_service = MagicMock()
    mock_service.files.return_value.update.return_value.execute.return_value = {"id": "f1", "name": "New"}

    with patch("strands_pack.google_drive._get_service") as mock_get_service:
        mock_get_service.return_value = mock_service

        res = google_drive(action="rename_file", file_id="f1", new_name="New")
        assert res["success"] is True
        mock_service.files.return_value.update.assert_called_once()


def test_copy_file_calls_copy():
    from strands_pack.google_drive import google_drive

    mock_service = MagicMock()
    mock_service.files.return_value.copy.return_value.execute.return_value = {"id": "c1"}

    with patch("strands_pack.google_drive._get_service") as mock_get_service:
        mock_get_service.return_value = mock_service

        res = google_drive(action="copy_file", file_id="f1", new_name="Copy", destination_folder_id="dest")
        assert res["success"] is True
        mock_service.files.return_value.copy.assert_called_once()


def test_move_file_calls_get_then_update():
    from strands_pack.google_drive import google_drive

    mock_service = MagicMock()
    mock_service.files.return_value.get.return_value.execute.return_value = {"parents": ["p1", "p2"]}
    mock_service.files.return_value.update.return_value.execute.return_value = {"id": "f1", "parents": ["dest"]}

    with patch("strands_pack.google_drive._get_service") as mock_get_service:
        mock_get_service.return_value = mock_service

        res = google_drive(action="move_file", file_id="f1", destination_folder_id="dest")
        assert res["success"] is True
        assert res["removed_parents"] == ["p1", "p2"]
        assert res["added_parent"] == "dest"


def test_get_quota_calls_about_get():
    from strands_pack.google_drive import google_drive

    mock_service = MagicMock()
    mock_service.about.return_value.get.return_value.execute.return_value = {"storageQuota": {"limit": "1"}}

    with patch("strands_pack.google_drive._get_service") as mock_get_service:
        mock_get_service.return_value = mock_service

        res = google_drive(action="get_quota")
        assert res["success"] is True
        mock_service.about.return_value.get.assert_called_once_with(fields="storageQuota,user")
