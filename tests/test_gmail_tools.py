"""Tests for Gmail tool (offline/mocked)."""

import base64
from unittest.mock import MagicMock, patch


def _decode_raw(raw: str) -> str:
    data = base64.urlsafe_b64decode(raw.encode("utf-8"))
    return data.decode("utf-8", errors="replace")


def test_gmail_unknown_action():
    from strands_pack import gmail

    with patch("strands_pack.gmail._get_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        result = gmail(action="nope")
        assert result["success"] is False
        assert "available_actions" in result


def test_gmail_send_builds_raw_and_calls_api():
    from strands_pack import gmail

    with patch("strands_pack.gmail._get_service") as mock_get_service:
        service = MagicMock()
        messages = service.users.return_value.messages.return_value
        messages.send.return_value.execute.return_value = {"id": "msg_123", "threadId": "thr_456"}
        mock_get_service.return_value = service

        result = gmail(
            action="send",
            to="to@example.com",
            subject="Test subject",
            body_text="Hello world",
        )

        assert result["success"] is True
        messages.send.assert_called_once()

        _, call_kwargs = messages.send.call_args
        assert call_kwargs["userId"] == "me"
        assert "raw" in call_kwargs["body"]

        decoded = _decode_raw(call_kwargs["body"]["raw"])
        assert "Subject: Test subject" in decoded
        assert "To: to@example.com" in decoded
        assert "Hello world" in decoded


def test_gmail_send_with_html_contains_hyperlink():
    from strands_pack import gmail

    with patch("strands_pack.gmail._get_service") as mock_get_service:
        service = MagicMock()
        messages = service.users.return_value.messages.return_value
        messages.send.return_value.execute.return_value = {"id": "msg_123"}
        mock_get_service.return_value = service

        result = gmail(
            action="send",
            to="to@example.com",
            subject="HTML",
            body_html='See <a href="https://example.com">this link</a>.',
        )

        assert result["success"] is True
        _, call_kwargs = messages.send.call_args
        decoded = _decode_raw(call_kwargs["body"]["raw"])
        assert 'href="https://example.com"' in decoded


def test_gmail_list_attachments_parses_payload():
    from strands_pack import gmail

    with patch("strands_pack.gmail._get_service") as mock_get_service:
        service = MagicMock()
        messages = service.users.return_value.messages.return_value
        messages.get.return_value.execute.return_value = {
            "id": "m1",
            "payload": {
                "mimeType": "multipart/mixed",
                "parts": [
                    {"mimeType": "text/plain", "body": {"size": 10}},
                    {
                        "filename": "report.pdf",
                        "mimeType": "application/pdf",
                        "partId": "2",
                        "body": {"attachmentId": "att1", "size": 123},
                        "headers": [{"name": "Content-Disposition", "value": "attachment"}],
                    },
                ],
            },
        }
        mock_get_service.return_value = service

        res = gmail(action="list_attachments", message_id="m1")
        assert res["success"] is True
        assert res["count"] == 1
        assert res["attachments"][0]["filename"] == "report.pdf"
        assert res["attachments"][0]["attachment_id"] == "att1"


def test_gmail_download_attachment_writes_file(tmp_path):
    import base64

    from strands_pack import gmail

    with patch("strands_pack.gmail._get_service") as mock_get_service:
        service = MagicMock()
        attachments_api = service.users.return_value.messages.return_value.attachments.return_value
        attachments_api.get.return_value.execute.return_value = {
            "data": base64.urlsafe_b64encode(b"hello").decode("utf-8")
        }
        mock_get_service.return_value = service

        out = tmp_path / "a.bin"
        res = gmail(action="download_attachment", message_id="m1", attachment_id="att1", output_path=str(out))
        assert res["success"] is True
        assert out.read_bytes() == b"hello"

def test_gmail_send_requires_to():
    from strands_pack import gmail

    with patch("strands_pack.gmail._get_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        result = gmail(action="send", subject="Test", body_text="Hello")
        assert result["success"] is False
        assert "to is required" in result["error"]


def test_gmail_send_with_cc_bcc():
    from strands_pack import gmail

    with patch("strands_pack.gmail._get_service") as mock_get_service:
        service = MagicMock()
        messages = service.users.return_value.messages.return_value
        messages.send.return_value.execute.return_value = {"id": "msg_123"}
        mock_get_service.return_value = service

        result = gmail(
            action="send",
            to="to@example.com",
            cc="cc@example.com",
            bcc="bcc@example.com",
            subject="Test",
            body_text="Hello",
        )

        assert result["success"] is True
        _, call_kwargs = messages.send.call_args
        decoded = _decode_raw(call_kwargs["body"]["raw"])
        assert "Cc: cc@example.com" in decoded
        assert "Bcc: bcc@example.com" in decoded


def test_gmail_list_messages_calls_api():
    from strands_pack import gmail

    with patch("strands_pack.gmail._get_service") as mock_get_service:
        service = MagicMock()
        messages = service.users.return_value.messages.return_value
        messages.list.return_value.execute.return_value = {
            "messages": [{"id": "1"}, {"id": "2"}],
            "resultSizeEstimate": 2,
        }
        mock_get_service.return_value = service

        result = gmail(
            action="list_messages",
            q="from:someone@example.com",
            label_ids=["INBOX"],
            max_results=5,
        )

        assert result["success"] is True
        assert result["messages"] == [{"id": "1"}, {"id": "2"}]
        messages.list.assert_called_once()

        _, call_kwargs = messages.list.call_args
        assert call_kwargs["userId"] == "me"
        assert call_kwargs["q"] == "from:someone@example.com"
        assert call_kwargs["labelIds"] == ["INBOX"]
        assert call_kwargs["maxResults"] == 5


def test_gmail_get_message_requires_id():
    from strands_pack import gmail

    with patch("strands_pack.gmail._get_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        result = gmail(action="get_message")
        assert result["success"] is False
        assert "message_id is required" in result["error"]


def test_gmail_get_message_calls_api():
    from strands_pack import gmail

    with patch("strands_pack.gmail._get_service") as mock_get_service:
        service = MagicMock()
        messages = service.users.return_value.messages.return_value
        messages.get.return_value.execute.return_value = {"id": "abc", "snippet": "hello"}
        mock_get_service.return_value = service

        result = gmail(action="get_message", message_id="abc", format="metadata")
        assert result["success"] is True
        assert result["message"]["id"] == "abc"

        messages.get.assert_called_once_with(userId="me", id="abc", format="metadata")


def test_gmail_get_profile_calls_api():
    from strands_pack import gmail

    with patch("strands_pack.gmail._get_service") as mock_get_service:
        service = MagicMock()
        service.users.return_value.getProfile.return_value.execute.return_value = {"emailAddress": "me@example.com"}
        mock_get_service.return_value = service

        result = gmail(action="get_profile")
        assert result["success"] is True
        assert result["profile"]["emailAddress"] == "me@example.com"


def test_gmail_auth_required():
    from strands_pack import gmail

    with patch("strands_pack.gmail._get_service") as mock_get_service:
        mock_get_service.return_value = None  # No credentials

        result = gmail(action="list_messages")
        assert result["success"] is False
        assert result.get("auth_required") is True


def test_gmail_mark_read_calls_modify():
    from strands_pack import gmail

    with patch("strands_pack.gmail._get_service") as mock_get_service:
        service = MagicMock()
        messages = service.users.return_value.messages.return_value
        messages.modify.return_value.execute.return_value = {"id": "m1", "labelIds": ["INBOX"]}
        mock_get_service.return_value = service

        res = gmail(action="mark_read", message_id="m1")
        assert res["success"] is True
        messages.modify.assert_called_once()


def test_gmail_trash_message_calls_trash():
    from strands_pack import gmail

    with patch("strands_pack.gmail._get_service") as mock_get_service:
        service = MagicMock()
        messages = service.users.return_value.messages.return_value
        messages.trash.return_value.execute.return_value = {"id": "m1"}
        mock_get_service.return_value = service

        res = gmail(action="trash_message", message_id="m1")
        assert res["success"] is True
        messages.trash.assert_called_once_with(userId="me", id="m1")


def test_gmail_delete_message_requires_confirm():
    from strands_pack import gmail

    with patch("strands_pack.gmail._get_service") as mock_get_service:
        service = MagicMock()
        mock_get_service.return_value = service

        res = gmail(action="delete_message", message_id="m1")
        assert res["success"] is False
        assert "confirm" in res["error"].lower()


def test_gmail_list_labels_calls_api():
    from strands_pack import gmail

    with patch("strands_pack.gmail._get_service") as mock_get_service:
        service = MagicMock()
        service.users.return_value.labels.return_value.list.return_value.execute.return_value = {"labels": [{"id": "L1"}]}
        mock_get_service.return_value = service

        res = gmail(action="list_labels")
        assert res["success"] is True
        assert res["count"] == 1


def test_gmail_create_label_calls_api():
    from strands_pack import gmail

    with patch("strands_pack.gmail._get_service") as mock_get_service:
        service = MagicMock()
        service.users.return_value.labels.return_value.create.return_value.execute.return_value = {"id": "L1", "name": "Receipts"}
        mock_get_service.return_value = service

        res = gmail(action="create_label", label_name="Receipts")
        assert res["success"] is True
        assert res["label"]["name"] == "Receipts"


def test_gmail_add_label_calls_modify():
    from strands_pack import gmail

    with patch("strands_pack.gmail._get_service") as mock_get_service:
        service = MagicMock()
        messages = service.users.return_value.messages.return_value
        messages.modify.return_value.execute.return_value = {"id": "m1"}
        mock_get_service.return_value = service

        res = gmail(action="add_label", message_id="m1", label_id="L1")
        assert res["success"] is True
        messages.modify.assert_called_once()


def test_gmail_remove_label_calls_modify():
    from strands_pack import gmail

    with patch("strands_pack.gmail._get_service") as mock_get_service:
        service = MagicMock()
        messages = service.users.return_value.messages.return_value
        messages.modify.return_value.execute.return_value = {"id": "m1"}
        mock_get_service.return_value = service

        res = gmail(action="remove_label", message_id="m1", label_id="L1")
        assert res["success"] is True
        messages.modify.assert_called_once()


def test_gmail_create_draft_calls_api():
    from strands_pack import gmail

    with patch("strands_pack.gmail._get_service") as mock_get_service:
        service = MagicMock()
        service.users.return_value.drafts.return_value.create.return_value.execute.return_value = {"id": "d1"}
        mock_get_service.return_value = service

        res = gmail(action="create_draft", to="to@example.com", subject="S", body_text="B")
        assert res["success"] is True


def test_gmail_send_draft_calls_api():
    from strands_pack import gmail

    with patch("strands_pack.gmail._get_service") as mock_get_service:
        service = MagicMock()
        service.users.return_value.drafts.return_value.send.return_value.execute.return_value = {"id": "m1"}
        mock_get_service.return_value = service

        res = gmail(action="send_draft", draft_id="d1")
        assert res["success"] is True


def test_gmail_reply_sends_in_thread_and_sets_reply_headers():
    from strands_pack import gmail

    with patch("strands_pack.gmail._get_service") as mock_get_service:
        service = MagicMock()
        messages = service.users.return_value.messages.return_value
        # metadata fetch for headers/thread
        messages.get.return_value.execute.side_effect = [
            {
                "id": "m1",
                "threadId": "t1",
                "payload": {"headers": [{"name": "From", "value": "a@example.com"}, {"name": "Subject", "value": "Hi"}, {"name": "Message-ID", "value": "<mid>"}]},
            }
        ]
        messages.send.return_value.execute.return_value = {"id": "m2", "threadId": "t1"}
        mock_get_service.return_value = service

        res = gmail(action="reply", message_id="m1", body_text="Reply")
        assert res["success"] is True
        _, kwargs = messages.send.call_args
        assert kwargs["body"]["threadId"] == "t1"


def test_gmail_forward_sends_message():
    from strands_pack import gmail

    with patch("strands_pack.gmail._get_service") as mock_get_service:
        service = MagicMock()
        messages = service.users.return_value.messages.return_value
        messages.get.return_value.execute.side_effect = [
            {"raw": "aGVsbG8="},  # "hello" base64url, decodeable though not full RFC822
            {"payload": {"headers": [{"name": "Subject", "value": "Hi"}]}},
        ]
        messages.send.return_value.execute.return_value = {"id": "m2"}
        mock_get_service.return_value = service

        res = gmail(action="forward", message_id="m1", to="to@example.com", body_text="FYI")
        assert res["success"] is True
        messages.send.assert_called_once()


def test_gmail_trash_by_query_uses_batch_modify():
    from strands_pack import gmail

    with patch("strands_pack.gmail._get_service") as mock_get_service:
        service = MagicMock()
        messages = service.users.return_value.messages.return_value
        messages.list.return_value.execute.return_value = {"messages": [{"id": "m1"}, {"id": "m2"}]}
        messages.batchModify.return_value.execute.return_value = {}
        mock_get_service.return_value = service

        res = gmail(action="trash_by_query", q="from:udacity")
        assert res["success"] is True
        assert res["trashed"] is True
        assert res["count"] == 2
        messages.batchModify.assert_called_once()


def test_gmail_delete_by_query_requires_confirm():
    from strands_pack import gmail

    with patch("strands_pack.gmail._get_service") as mock_get_service:
        mock_get_service.return_value = MagicMock()
        res = gmail(action="delete_by_query", q="from:udacity")
        assert res["success"] is False
        assert "confirm" in res["error"].lower()
