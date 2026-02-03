"""Tests for Google Forms tool (offline/mocked)."""

from unittest.mock import MagicMock, patch


def test_google_forms_unknown_action():
    from strands_pack import google_forms

    with patch("strands_pack.google_forms._get_forms_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        result = google_forms(action="nope")
        assert result["success"] is False
        assert "available_actions" in result


def test_google_forms_create_form_calls_api():
    from strands_pack import google_forms

    with patch("strands_pack.google_forms._get_forms_service") as mock_get_service:
        service = MagicMock()
        mock_get_service.return_value = service
        forms = service.forms.return_value
        forms.create.return_value.execute.return_value = {"formId": "F1"}

        result = google_forms(action="create_form", form={"info": {"title": "T"}})
        assert result["success"] is True
        forms.create.assert_called_once_with(body={"info": {"title": "T"}})


def test_google_forms_create_form_requires_form():
    from strands_pack import google_forms

    with patch("strands_pack.google_forms._get_forms_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        result = google_forms(action="create_form")
        assert result["success"] is False
        assert "form is required" in result["error"]


def test_google_forms_get_form_requires_id():
    from strands_pack import google_forms

    with patch("strands_pack.google_forms._get_forms_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        result = google_forms(action="get_form")
        assert result["success"] is False
        assert "form_id is required" in result["error"]


def test_google_forms_get_form_calls_api():
    from strands_pack import google_forms

    with patch("strands_pack.google_forms._get_forms_service") as mock_get_service:
        service = MagicMock()
        mock_get_service.return_value = service
        forms = service.forms.return_value
        forms.get.return_value.execute.return_value = {"formId": "F1"}

        result = google_forms(action="get_form", form_id="F1")
        assert result["success"] is True
        forms.get.assert_called_once_with(formId="F1")


def test_google_forms_batch_update_calls_api():
    from strands_pack import google_forms

    with patch("strands_pack.google_forms._get_forms_service") as mock_get_service:
        service = MagicMock()
        mock_get_service.return_value = service
        forms = service.forms.return_value
        forms.batchUpdate.return_value.execute.return_value = {"replies": []}

        result = google_forms(
            action="batch_update",
            form_id="F1",
            requests=[{"noop": {}}],
            include_form_in_response=True,
        )
        assert result["success"] is True
        forms.batchUpdate.assert_called_once_with(
            formId="F1",
            body={"requests": [{"noop": {}}], "includeFormInResponse": True},
        )


def test_google_forms_batch_update_requires_form_id():
    from strands_pack import google_forms

    with patch("strands_pack.google_forms._get_forms_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        result = google_forms(action="batch_update", requests=[{"noop": {}}])
        assert result["success"] is False
        assert "form_id is required" in result["error"]


def test_google_forms_batch_update_requires_requests():
    from strands_pack import google_forms

    with patch("strands_pack.google_forms._get_forms_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        result = google_forms(action="batch_update", form_id="F1")
        assert result["success"] is False
        assert "requests is required" in result["error"]


def test_google_forms_set_publish_settings_calls_api():
    from strands_pack import google_forms

    with patch("strands_pack.google_forms._get_forms_service") as mock_get_service:
        service = MagicMock()
        mock_get_service.return_value = service
        forms = service.forms.return_value
        forms.setPublishSettings.return_value.execute.return_value = {"publishSettings": {}}

        result = google_forms(
            action="set_publish_settings",
            form_id="F1",
            publish_settings={"publishSettings": {"isPublished": True}},
        )
        assert result["success"] is True
        forms.setPublishSettings.assert_called_once_with(
            formId="F1", body={"publishSettings": {"isPublished": True}}
        )


def test_google_forms_set_publish_settings_requires_form_id():
    from strands_pack import google_forms

    with patch("strands_pack.google_forms._get_forms_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        result = google_forms(
            action="set_publish_settings",
            publish_settings={"publishSettings": {"isPublished": True}},
        )
        assert result["success"] is False
        assert "form_id is required" in result["error"]


def test_google_forms_set_publish_settings_requires_settings():
    from strands_pack import google_forms

    with patch("strands_pack.google_forms._get_forms_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        result = google_forms(action="set_publish_settings", form_id="F1")
        assert result["success"] is False
        assert "publish_settings is required" in result["error"]


def test_google_forms_list_responses_calls_api():
    from strands_pack import google_forms

    with patch("strands_pack.google_forms._get_forms_service") as mock_get_service:
        service = MagicMock()
        mock_get_service.return_value = service
        responses = service.forms.return_value.responses.return_value
        responses.list.return_value.execute.return_value = {"responses": [{"responseId": "R1"}]}

        result = google_forms(action="list_responses", form_id="F1", page_size=10)
        assert result["success"] is True
        assert result["responses"] == [{"responseId": "R1"}]
        responses.list.assert_called_once_with(formId="F1", pageSize=10)


def test_google_forms_list_responses_requires_form_id():
    from strands_pack import google_forms

    with patch("strands_pack.google_forms._get_forms_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        result = google_forms(action="list_responses")
        assert result["success"] is False
        assert "form_id is required" in result["error"]


def test_google_forms_get_response_calls_api():
    from strands_pack import google_forms

    with patch("strands_pack.google_forms._get_forms_service") as mock_get_service:
        service = MagicMock()
        mock_get_service.return_value = service
        responses = service.forms.return_value.responses.return_value
        responses.get.return_value.execute.return_value = {"responseId": "R1"}

        result = google_forms(action="get_response", form_id="F1", response_id="R1")
        assert result["success"] is True
        responses.get.assert_called_once_with(formId="F1", responseId="R1")


def test_google_forms_get_response_requires_form_id():
    from strands_pack import google_forms

    with patch("strands_pack.google_forms._get_forms_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        result = google_forms(action="get_response", response_id="R1")
        assert result["success"] is False
        assert "form_id is required" in result["error"]


def test_google_forms_get_response_requires_response_id():
    from strands_pack import google_forms

    with patch("strands_pack.google_forms._get_forms_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        result = google_forms(action="get_response", form_id="F1")
        assert result["success"] is False
        assert "response_id is required" in result["error"]


def test_google_forms_watches_calls_api():
    from strands_pack import google_forms

    with patch("strands_pack.google_forms._get_forms_service") as mock_get_service:
        service = MagicMock()
        mock_get_service.return_value = service
        watches = service.forms.return_value.watches.return_value

        # create_watch
        watches.create.return_value.execute.return_value = {"watchId": "W1"}
        result = google_forms(action="create_watch", form_id="F1", watch={"target": "x"})
        assert result["success"] is True
        watches.create.assert_called_once_with(formId="F1", body={"target": "x"})

        # list_watches
        watches.list.return_value.execute.return_value = {"watches": [{"watchId": "W1"}]}
        result = google_forms(action="list_watches", form_id="F1")
        assert result["success"] is True
        watches.list.assert_called_once_with(formId="F1")

        # renew_watch
        watches.renew.return_value.execute.return_value = {"watchId": "W1"}
        result = google_forms(action="renew_watch", form_id="F1", watch_id="W1")
        assert result["success"] is True
        watches.renew.assert_called_once_with(formId="F1", watchId="W1", body={})

        # delete_watch
        watches.delete.return_value.execute.return_value = {}
        result = google_forms(action="delete_watch", form_id="F1", watch_id="W1")
        assert result["success"] is True
        watches.delete.assert_called_once_with(formId="F1", watchId="W1")


def test_google_forms_create_watch_requires_form_id():
    from strands_pack import google_forms

    with patch("strands_pack.google_forms._get_forms_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        result = google_forms(action="create_watch", watch={"target": "x"})
        assert result["success"] is False
        assert "form_id is required" in result["error"]


def test_google_forms_create_watch_requires_watch():
    from strands_pack import google_forms

    with patch("strands_pack.google_forms._get_forms_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        result = google_forms(action="create_watch", form_id="F1")
        assert result["success"] is False
        assert "watch is required" in result["error"]


def test_google_forms_delete_watch_requires_form_id():
    from strands_pack import google_forms

    with patch("strands_pack.google_forms._get_forms_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        result = google_forms(action="delete_watch", watch_id="W1")
        assert result["success"] is False
        assert "form_id is required" in result["error"]


def test_google_forms_delete_watch_requires_watch_id():
    from strands_pack import google_forms

    with patch("strands_pack.google_forms._get_forms_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        result = google_forms(action="delete_watch", form_id="F1")
        assert result["success"] is False
        assert "watch_id is required" in result["error"]


def test_google_forms_list_watches_requires_form_id():
    from strands_pack import google_forms

    with patch("strands_pack.google_forms._get_forms_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        result = google_forms(action="list_watches")
        assert result["success"] is False
        assert "form_id is required" in result["error"]


def test_google_forms_renew_watch_requires_form_id():
    from strands_pack import google_forms

    with patch("strands_pack.google_forms._get_forms_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        result = google_forms(action="renew_watch", watch_id="W1")
        assert result["success"] is False
        assert "form_id is required" in result["error"]


def test_google_forms_renew_watch_requires_watch_id():
    from strands_pack import google_forms

    with patch("strands_pack.google_forms._get_forms_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        result = google_forms(action="renew_watch", form_id="F1")
        assert result["success"] is False
        assert "watch_id is required" in result["error"]


def test_google_forms_auth_needed():
    from strands_pack import google_forms

    with patch("strands_pack.google_forms._get_forms_service") as mock_get_service:
        mock_get_service.return_value = None  # Simulate no credentials
        result = google_forms(action="get_form", form_id="F1")
        assert result["success"] is False
        assert result.get("auth_required") is True or "auth" in result.get("error", "").lower()
