from unittest.mock import MagicMock, patch


def test_google_sheets_invalid_action():
    from strands_pack.google_sheets import google_sheets

    res = google_sheets(action="nope")
    assert res["success"] is False
    assert "Unknown action" in res["error"]


def test_create_spreadsheet_calls_api():
    from strands_pack.google_sheets import google_sheets

    with patch("strands_pack.google_sheets._get_service") as mock_get_service:
        mock_service = MagicMock()
        mock_service.spreadsheets.return_value.create.return_value.execute.return_value = {
            "spreadsheetId": "sid",
            "spreadsheetUrl": "https://docs.google.com/spreadsheets/d/sid/edit",
            "properties": {"title": "My Sheet"},
        }
        mock_get_service.return_value = mock_service

        res = google_sheets(action="create_spreadsheet", title="My Sheet")
        assert res["success"] is True
        assert res["spreadsheet_id"] == "sid"
        mock_service.spreadsheets.return_value.create.assert_called_once()


def test_get_spreadsheet_calls_api():
    from strands_pack.google_sheets import google_sheets

    with patch("strands_pack.google_sheets._get_service") as mock_get_service:
        mock_service = MagicMock()
        mock_service.spreadsheets.return_value.get.return_value.execute.return_value = {
            "spreadsheetId": "sid",
            "spreadsheetUrl": "https://docs.google.com/spreadsheets/d/sid/edit",
            "properties": {"title": "My Sheet"},
            "sheets": [{"properties": {"sheetId": 0, "title": "Sheet1", "index": 0}}],
        }
        mock_get_service.return_value = mock_service

        res = google_sheets(action="get_spreadsheet", spreadsheet_id="sid")
        assert res["success"] is True
        assert res["count"] == 1
        assert res["sheets"][0]["sheet_id"] == 0
        mock_service.spreadsheets.return_value.get.assert_called_once()


def test_delete_sheet_by_id_calls_batch_update():
    from strands_pack.google_sheets import google_sheets

    with patch("strands_pack.google_sheets._get_service") as mock_get_service:
        mock_service = MagicMock()
        mock_service.spreadsheets.return_value.batchUpdate.return_value.execute.return_value = {"replies": []}
        mock_get_service.return_value = mock_service

        res = google_sheets(action="delete_sheet", spreadsheet_id="sid", sheet_id=123)
        assert res["success"] is True
        assert res["deleted_sheet_id"] == 123
        mock_service.spreadsheets.return_value.batchUpdate.assert_called_once()


def test_add_sheet_calls_batch_update():
    from strands_pack.google_sheets import google_sheets

    with patch("strands_pack.google_sheets._get_service") as mock_get_service:
        mock_service = MagicMock()
        mock_service.spreadsheets.return_value.batchUpdate.return_value.execute.return_value = {
            "replies": [{"addSheet": {"properties": {"sheetId": 999, "title": "Summary"}}}]
        }
        mock_get_service.return_value = mock_service

        res = google_sheets(action="add_sheet", spreadsheet_id="sid", sheet_name="Summary")
        assert res["success"] is True
        assert res["created_sheet_id"] == 999
        mock_service.spreadsheets.return_value.batchUpdate.assert_called_once()


def test_google_sheets_missing_spreadsheet_id():
    from strands_pack.google_sheets import google_sheets

    with patch("strands_pack.google_sheets._get_service") as mock_get_service:
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        res = google_sheets(action="get_values", range="Sheet1!A1")
        assert res["success"] is False
        assert "spreadsheet_id" in res["error"]


def test_get_values_calls_api():
    from strands_pack.google_sheets import google_sheets

    with patch("strands_pack.google_sheets._get_service") as mock_get_service:
        mock_service = MagicMock()
        mock_service.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = {
            "values": [["a", "b"]]
        }
        mock_get_service.return_value = mock_service

        res = google_sheets(
            action="get_values",
            spreadsheet_id="sid",
            range="Sheet1!A1:B1",
        )
        assert res["success"] is True
        assert res["values"] == [["a", "b"]]

        mock_service.spreadsheets.return_value.values.return_value.get.assert_called_once_with(
            spreadsheetId="sid", range="Sheet1!A1:B1"
        )


def test_get_values_with_render_option():
    from strands_pack.google_sheets import google_sheets

    with patch("strands_pack.google_sheets._get_service") as mock_get_service:
        mock_service = MagicMock()
        mock_service.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = {
            "values": [["100"]]
        }
        mock_get_service.return_value = mock_service

        res = google_sheets(
            action="get_values",
            spreadsheet_id="sid",
            range="Sheet1!A1",
            value_render_option="FORMATTED_VALUE",
        )
        assert res["success"] is True

        mock_service.spreadsheets.return_value.values.return_value.get.assert_called_once_with(
            spreadsheetId="sid", range="Sheet1!A1", valueRenderOption="FORMATTED_VALUE"
        )


def test_update_values_calls_api():
    from strands_pack.google_sheets import google_sheets

    with patch("strands_pack.google_sheets._get_service") as mock_get_service:
        mock_service = MagicMock()
        mock_service.spreadsheets.return_value.values.return_value.update.return_value.execute.return_value = {
            "updatedCells": 2
        }
        mock_get_service.return_value = mock_service

        res = google_sheets(
            action="update_values",
            spreadsheet_id="sid",
            range="Sheet1!A1",
            values=[["Hello", "World"]],
        )
        assert res["success"] is True
        assert "updated" in res

        mock_service.spreadsheets.return_value.values.return_value.update.assert_called_once_with(
            spreadsheetId="sid",
            range="Sheet1!A1",
            valueInputOption="USER_ENTERED",
            body={"values": [["Hello", "World"]]},
        )


def test_update_values_missing_values():
    from strands_pack.google_sheets import google_sheets

    with patch("strands_pack.google_sheets._get_service") as mock_get_service:
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        res = google_sheets(
            action="update_values",
            spreadsheet_id="sid",
            range="Sheet1!A1",
        )
        assert res["success"] is False
        assert "values" in res["error"]


def test_append_values_calls_api():
    from strands_pack.google_sheets import google_sheets

    with patch("strands_pack.google_sheets._get_service") as mock_get_service:
        mock_service = MagicMock()
        mock_service.spreadsheets.return_value.values.return_value.append.return_value.execute.return_value = {
            "updates": {"updatedRows": 1}
        }
        mock_get_service.return_value = mock_service

        res = google_sheets(
            action="append_values",
            spreadsheet_id="sid",
            range="Sheet1!A:C",
            values=[["x", "y", "z"]],
        )
        assert res["success"] is True
        assert "appended" in res

        mock_service.spreadsheets.return_value.values.return_value.append.assert_called_once_with(
            spreadsheetId="sid",
            range="Sheet1!A:C",
            valueInputOption="USER_ENTERED",
            body={"values": [["x", "y", "z"]]},
        )


def test_append_values_with_insert_option():
    from strands_pack.google_sheets import google_sheets

    with patch("strands_pack.google_sheets._get_service") as mock_get_service:
        mock_service = MagicMock()
        mock_service.spreadsheets.return_value.values.return_value.append.return_value.execute.return_value = {
            "updates": {"updatedRows": 1}
        }
        mock_get_service.return_value = mock_service

        res = google_sheets(
            action="append_values",
            spreadsheet_id="sid",
            range="Sheet1!A:C",
            values=[["x", "y", "z"]],
            insert_data_option="INSERT_ROWS",
        )
        assert res["success"] is True

        mock_service.spreadsheets.return_value.values.return_value.append.assert_called_once_with(
            spreadsheetId="sid",
            range="Sheet1!A:C",
            valueInputOption="USER_ENTERED",
            body={"values": [["x", "y", "z"]]},
            insertDataOption="INSERT_ROWS",
        )


def test_clear_values_calls_api():
    from strands_pack.google_sheets import google_sheets

    with patch("strands_pack.google_sheets._get_service") as mock_get_service:
        mock_service = MagicMock()
        mock_service.spreadsheets.return_value.values.return_value.clear.return_value.execute.return_value = {
            "clearedRange": "Sheet1!A1:C10"
        }
        mock_get_service.return_value = mock_service

        res = google_sheets(
            action="clear_values",
            spreadsheet_id="sid",
            range="Sheet1!A1:C10",
        )
        assert res["success"] is True
        assert "cleared" in res

        mock_service.spreadsheets.return_value.values.return_value.clear.assert_called_once_with(
            spreadsheetId="sid",
            range="Sheet1!A1:C10",
            body={},
        )


def test_auth_needed_returns_auth_response():
    from strands_pack.google_sheets import google_sheets

    with patch("strands_pack.google_sheets._get_service") as mock_get_service:
        mock_get_service.return_value = None  # Simulate no auth

        with patch("strands_pack.google_auth.needs_auth_response") as mock_needs_auth:
            mock_needs_auth.return_value = {
                "success": False,
                "error": "Authentication required for Google Sheets",
                "auth_required": True,
            }

            res = google_sheets(
                action="get_values",
                spreadsheet_id="sid",
                range="Sheet1!A1",
            )
            assert res["success"] is False
            assert res["auth_required"] is True
            mock_needs_auth.assert_called_once_with("sheets")


def test_api_exception_returns_error():
    from strands_pack.google_sheets import google_sheets

    with patch("strands_pack.google_sheets._get_service") as mock_get_service:
        mock_service = MagicMock()
        mock_service.spreadsheets.return_value.values.return_value.get.return_value.execute.side_effect = Exception(
            "API error"
        )
        mock_get_service.return_value = mock_service

        res = google_sheets(
            action="get_values",
            spreadsheet_id="sid",
            range="Sheet1!A1",
        )
        assert res["success"] is False
        assert "API error" in res["error"]
