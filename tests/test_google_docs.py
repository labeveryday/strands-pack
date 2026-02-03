from unittest.mock import MagicMock, patch


def test_google_docs_invalid_action():
    from strands_pack.google_docs import google_docs

    with patch("strands_pack.google_docs._get_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        res = google_docs(action="nope")
        assert res["success"] is False
        assert "Unknown action" in res["error"]


def test_google_docs_missing_document_id():
    from strands_pack.google_docs import google_docs

    with patch("strands_pack.google_docs._get_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        res = google_docs(action="get_document")
        assert res["success"] is False
        assert "document_id" in res["error"]


def test_create_document_calls_api():
    from strands_pack.google_docs import google_docs

    with patch("strands_pack.google_docs._get_service") as mock_get_service:
        service = MagicMock()
        service.documents.return_value.create.return_value.execute.return_value = {"documentId": "d1"}
        mock_get_service.return_value = service

        res = google_docs(action="create_document", title="T")
        assert res["success"] is True
        assert res["document"]["documentId"] == "d1"
        assert res["document_url"].endswith("/document/d/d1/edit")


def test_get_document_calls_api():
    from strands_pack.google_docs import google_docs

    with patch("strands_pack.google_docs._get_service") as mock_get_service:
        service = MagicMock()
        service.documents.return_value.get.return_value.execute.return_value = {
            "documentId": "d1",
            "title": "My Doc"
        }
        mock_get_service.return_value = service

        res = google_docs(action="get_document", document_id="d1")
        assert res["success"] is True
        assert res["document"]["documentId"] == "d1"
        assert res["document_id"] == "d1"


def test_append_text_calls_api():
    from strands_pack.google_docs import google_docs

    with patch("strands_pack.google_docs._get_service") as mock_get_service:
        service = MagicMock()
        service.documents.return_value.batchUpdate.return_value.execute.return_value = {"replies": []}
        mock_get_service.return_value = service

        res = google_docs(action="append_text", document_id="d1", text="Hello world!")
        assert res["success"] is True
        assert res["document_id"] == "d1"
        service.documents.return_value.batchUpdate.assert_called_once()


def test_append_text_missing_text():
    from strands_pack.google_docs import google_docs

    with patch("strands_pack.google_docs._get_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        res = google_docs(action="append_text", document_id="d1")
        assert res["success"] is False
        assert "text" in res["error"]


def test_replace_text_calls_batch_update():
    from strands_pack.google_docs import google_docs

    with patch("strands_pack.google_docs._get_service") as mock_get_service:
        service = MagicMock()
        service.documents.return_value.batchUpdate.return_value.execute.return_value = {"replies": []}
        mock_get_service.return_value = service

        res = google_docs(
            action="replace_text",
            document_id="d1",
            contains_text="{{NAME}}",
            replace_text="Sam",
            match_case=True,
        )
        assert res["success"] is True
        service.documents.return_value.batchUpdate.assert_called_once()


def test_replace_text_missing_contains_text():
    from strands_pack.google_docs import google_docs

    with patch("strands_pack.google_docs._get_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        res = google_docs(action="replace_text", document_id="d1", replace_text="Sam")
        assert res["success"] is False
        assert "contains_text" in res["error"]


def test_replace_text_missing_replace_text():
    from strands_pack.google_docs import google_docs

    with patch("strands_pack.google_docs._get_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        res = google_docs(action="replace_text", document_id="d1", contains_text="{{NAME}}")
        assert res["success"] is False
        assert "replace_text" in res["error"]


def test_insert_text_calls_batch_update():
    from strands_pack.google_docs import google_docs

    with patch("strands_pack.google_docs._get_service") as mock_get_service:
        service = MagicMock()
        service.documents.return_value.batchUpdate.return_value.execute.return_value = {"replies": []}
        mock_get_service.return_value = service

        res = google_docs(action="insert_text", document_id="d1", index=1, text="Hi")
        assert res["success"] is True
        service.documents.return_value.batchUpdate.assert_called_once()


def test_insert_hyperlink_builds_requests():
    from strands_pack.google_docs import google_docs

    with patch("strands_pack.google_docs._get_service") as mock_get_service:
        service = MagicMock()
        service.documents.return_value.batchUpdate.return_value.execute.return_value = {"replies": []}
        mock_get_service.return_value = service

        res = google_docs(action="insert_hyperlink", document_id="d1", index=1, text="OpenAI", url="https://openai.com")
        assert res["success"] is True

        _, kwargs = service.documents.return_value.batchUpdate.call_args
        reqs = kwargs["body"]["requests"]
        assert reqs[0]["insertText"]["text"] == "OpenAI"
        assert reqs[1]["updateTextStyle"]["textStyle"]["link"]["url"] == "https://openai.com"


def test_insert_image_builds_request():
    from strands_pack.google_docs import google_docs

    with patch("strands_pack.google_docs._get_service") as mock_get_service:
        service = MagicMock()
        service.documents.return_value.batchUpdate.return_value.execute.return_value = {"replies": []}
        mock_get_service.return_value = service

        res = google_docs(action="insert_image", document_id="d1", index=1, image_uri="https://example.com/a.png", width_pt=100, height_pt=50)
        assert res["success"] is True

        _, kwargs = service.documents.return_value.batchUpdate.call_args
        req = kwargs["body"]["requests"][0]["insertInlineImage"]
        assert req["uri"] == "https://example.com/a.png"
        assert req["objectSize"]["width"]["magnitude"] == 100.0
        assert req["objectSize"]["height"]["magnitude"] == 50.0

def test_google_docs_auth_required():
    from strands_pack.google_docs import google_docs

    with patch("strands_pack.google_docs._get_service") as mock_get_service:
        mock_get_service.return_value = None  # No credentials

        res = google_docs(action="get_document", document_id="d1")
        assert res["success"] is False
        assert res.get("auth_required") is True
