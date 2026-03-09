"""Tests for Box tool."""

import os
import sys
import tempfile
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest


def _make_obj(**attrs):
    """Create a simple object with the given attributes (avoids MagicMock 'name' issue)."""
    obj = MagicMock()
    for k, v in attrs.items():
        setattr(obj, k, v)
    return obj


@pytest.fixture(autouse=True)
def _mock_box_sdk_gen():
    """Insert a fake box_sdk_gen into sys.modules so lazy imports succeed, and set HAS_BOX=True."""
    mock_mod = MagicMock()
    sub_modules = [
        "box_sdk_gen",
        "box_sdk_gen.managers",
        "box_sdk_gen.managers.ai",
        "box_sdk_gen.schemas",
        "box_sdk_gen.schemas.ai_item_ask",
        "box_sdk_gen.schemas.ai_item_base",
    ]
    saved = {name: sys.modules.get(name) for name in sub_modules}
    for name in sub_modules:
        sys.modules[name] = mock_mod

    with patch("strands_pack.box.HAS_BOX", True):
        yield

    for name in sub_modules:
        if saved[name] is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = saved[name]


def _mock_client():
    """Create a mock BoxClient."""
    return MagicMock()


# ---------------------------------------------------------------------------
# get_current_user
# ---------------------------------------------------------------------------


def test_box_get_current_user_success():
    with patch("strands_pack.box._get_client") as mock_gc:
        client = _mock_client()
        user = _make_obj(id="u1", name="Alice", login="alice@example.com", space_used=1024, space_amount=10240)
        client.users.get_user_me.return_value = user
        mock_gc.return_value = client

        from strands_pack import box

        result = box(action="get_current_user")
        assert result["success"] is True
        assert result["user_id"] == "u1"
        assert result["name"] == "Alice"
        assert result["login"] == "alice@example.com"


# ---------------------------------------------------------------------------
# list_folder
# ---------------------------------------------------------------------------


def test_box_list_folder_success():
    with patch("strands_pack.box._get_client") as mock_gc:
        client = _mock_client()
        item1 = _make_obj(type="file", id="f1", name="report.pdf")
        item2 = _make_obj(type="folder", id="d1", name="Drafts")
        client.folders.get_folder_items.return_value = MagicMock(entries=[item1, item2])
        mock_gc.return_value = client

        from strands_pack import box

        result = box(action="list_folder", folder_id="0")
        assert result["success"] is True
        assert result["count"] == 2
        assert result["items"][0]["name"] == "report.pdf"


# ---------------------------------------------------------------------------
# create_folder
# ---------------------------------------------------------------------------


def test_box_create_folder_success():
    with patch("strands_pack.box._get_client") as mock_gc:
        client = _mock_client()
        folder = _make_obj(id="d99", name="Campaign")
        client.folders.create_folder.return_value = folder
        mock_gc.return_value = client

        from strands_pack import box

        result = box(action="create_folder", name="Campaign", parent_folder_id="0")
        assert result["success"] is True
        assert result["folder_id"] == "d99"
        assert result["name"] == "Campaign"


def test_box_create_folder_missing_name():
    with patch("strands_pack.box._get_client") as mock_gc:
        mock_gc.return_value = _mock_client()

        from strands_pack import box

        result = box(action="create_folder")
        assert result["success"] is False
        assert "name" in result["error"]


# ---------------------------------------------------------------------------
# upload_file
# ---------------------------------------------------------------------------


def test_box_upload_file_success():
    with patch("strands_pack.box._get_client") as mock_gc:
        client = _mock_client()
        entry = _make_obj(id="f10", name="hero.png", size=2048)
        client.uploads.upload_file.return_value = MagicMock(entries=[entry])
        mock_gc.return_value = client

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(b"fake-png-data")
            tmp_path = tmp.name

        try:
            from strands_pack import box

            result = box(action="upload_file", file_path=tmp_path, folder_id="0")
            assert result["success"] is True
            assert result["file_id"] == "f10"
            assert result["name"] == "hero.png"
        finally:
            os.unlink(tmp_path)


def test_box_upload_file_not_found():
    with patch("strands_pack.box._get_client") as mock_gc:
        mock_gc.return_value = _mock_client()

        from strands_pack import box

        result = box(action="upload_file", file_path="/nonexistent/file.txt")
        assert result["success"] is False
        assert "File not found" in result["error"]


def test_box_upload_file_missing_path():
    with patch("strands_pack.box._get_client") as mock_gc:
        mock_gc.return_value = _mock_client()

        from strands_pack import box

        result = box(action="upload_file")
        assert result["success"] is False
        assert "file_path" in result["error"]


# ---------------------------------------------------------------------------
# download_file
# ---------------------------------------------------------------------------


def test_box_download_file_success():
    with patch("strands_pack.box._get_client") as mock_gc:
        client = _mock_client()
        stream = MagicMock()
        stream.read.return_value = b"file-content"
        client.downloads.download_file.return_value = stream
        mock_gc.return_value = client

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            dest = tmp.name

        try:
            from strands_pack import box

            result = box(action="download_file", file_id="f1", destination_path=dest)
            assert result["success"] is True
            assert result["saved_to"] == dest
            with open(dest, "rb") as f:
                assert f.read() == b"file-content"
        finally:
            os.unlink(dest)


def test_box_download_file_missing_id():
    with patch("strands_pack.box._get_client") as mock_gc:
        mock_gc.return_value = _mock_client()

        from strands_pack import box

        result = box(action="download_file")
        assert result["success"] is False
        assert "file_id" in result["error"]


# ---------------------------------------------------------------------------
# get_file_info
# ---------------------------------------------------------------------------


def test_box_get_file_info_success():
    with patch("strands_pack.box._get_client") as mock_gc:
        client = _mock_client()
        info = _make_obj(id="f1", name="report.pdf", size=5000, created_at="2026-01-01T00:00:00Z", modified_at="2026-02-01T00:00:00Z")
        info.owned_by = _make_obj(login="alice@example.com")
        client.files.get_file_by_id.return_value = info
        mock_gc.return_value = client

        from strands_pack import box

        result = box(action="get_file_info", file_id="f1")
        assert result["success"] is True
        assert result["name"] == "report.pdf"
        assert result["owned_by"] == "alice@example.com"


# ---------------------------------------------------------------------------
# delete_file
# ---------------------------------------------------------------------------


def test_box_delete_file_success():
    with patch("strands_pack.box._get_client") as mock_gc:
        client = _mock_client()
        mock_gc.return_value = client

        from strands_pack import box

        result = box(action="delete_file", file_id="f1", confirm=True)
        assert result["success"] is True
        assert result["deleted_file_id"] == "f1"
        client.files.delete_file_by_id.assert_called_once_with("f1")


def test_box_delete_file_no_confirm():
    with patch("strands_pack.box._get_client") as mock_gc:
        mock_gc.return_value = _mock_client()

        from strands_pack import box

        result = box(action="delete_file", file_id="f1")
        assert result["success"] is False
        assert result["error_type"] == "ConfirmationRequired"


# ---------------------------------------------------------------------------
# delete_folder
# ---------------------------------------------------------------------------


def test_box_delete_folder_success():
    with patch("strands_pack.box._get_client") as mock_gc:
        client = _mock_client()
        mock_gc.return_value = client

        from strands_pack import box

        result = box(action="delete_folder", folder_id="d5", confirm=True)
        assert result["success"] is True
        assert result["deleted_folder_id"] == "d5"


def test_box_delete_folder_no_confirm():
    with patch("strands_pack.box._get_client") as mock_gc:
        mock_gc.return_value = _mock_client()

        from strands_pack import box

        result = box(action="delete_folder", folder_id="d5")
        assert result["success"] is False
        assert result["error_type"] == "ConfirmationRequired"


def test_box_delete_folder_root():
    with patch("strands_pack.box._get_client") as mock_gc:
        mock_gc.return_value = _mock_client()

        from strands_pack import box

        result = box(action="delete_folder", folder_id="0", confirm=True)
        assert result["success"] is False
        assert "root" in result["error"].lower()


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


def test_box_search_success():
    with patch("strands_pack.box._get_client") as mock_gc:
        client = _mock_client()
        item = _make_obj(type="file", id="f2", name="Q4 Report.pdf")
        client.search.search_for_content.return_value = MagicMock(entries=[item])
        mock_gc.return_value = client

        from strands_pack import box

        result = box(action="search", query="Q4 Report")
        assert result["success"] is True
        assert result["count"] == 1
        assert result["results"][0]["name"] == "Q4 Report.pdf"


def test_box_search_missing_query():
    with patch("strands_pack.box._get_client") as mock_gc:
        mock_gc.return_value = _mock_client()

        from strands_pack import box

        result = box(action="search")
        assert result["success"] is False
        assert "query" in result["error"]


# ---------------------------------------------------------------------------
# create_shared_link (file)
# ---------------------------------------------------------------------------


def test_box_create_shared_link_file():
    with patch("strands_pack.box._get_client") as mock_gc:
        client = _mock_client()
        shared_link = MagicMock(url="https://box.com/s/abc123")
        client.shared_links_files.add_share_link_to_file.return_value = MagicMock(shared_link=shared_link)
        mock_gc.return_value = client

        from strands_pack import box

        result = box(action="create_shared_link", file_id="f1", access="open")
        assert result["success"] is True
        assert result["shared_link_url"] == "https://box.com/s/abc123"


# ---------------------------------------------------------------------------
# apply_metadata / get_metadata
# ---------------------------------------------------------------------------


def test_box_apply_metadata_success():
    with patch("strands_pack.box._get_client") as mock_gc:
        client = _mock_client()
        mock_gc.return_value = client

        from strands_pack import box

        result = box(action="apply_metadata", file_id="f1", template_key="campaign", metadata={"status": "active"})
        assert result["success"] is True
        assert result["applied"] is True


def test_box_apply_metadata_missing_params():
    with patch("strands_pack.box._get_client") as mock_gc:
        mock_gc.return_value = _mock_client()

        from strands_pack import box

        result = box(action="apply_metadata", file_id="f1")
        assert result["success"] is False
        assert "template_key" in result["error"]


def test_box_get_metadata_with_template():
    with patch("strands_pack.box._get_client") as mock_gc:
        client = _mock_client()
        meta_result = MagicMock()
        meta_result.extra_data = {"status": "active"}
        client.file_metadata.get_file_metadata_by_id.return_value = meta_result
        mock_gc.return_value = client

        from strands_pack import box

        result = box(action="get_metadata", file_id="f1", template_key="campaign")
        assert result["success"] is True
        assert result["metadata"]["status"] == "active"


def test_box_get_metadata_all():
    with patch("strands_pack.box._get_client") as mock_gc:
        client = _mock_client()
        entry = MagicMock(template="campaign", scope="enterprise")
        entry.extra_data = {"status": "draft"}
        client.file_metadata.get_file_metadata.return_value = MagicMock(entries=[entry])
        mock_gc.return_value = client

        from strands_pack import box

        result = box(action="get_metadata", file_id="f1")
        assert result["success"] is True
        assert len(result["metadata_instances"]) == 1


# ---------------------------------------------------------------------------
# create_task / assign_task
# ---------------------------------------------------------------------------


def test_box_create_task_success():
    with patch("strands_pack.box._get_client") as mock_gc:
        client = _mock_client()
        client.tasks.create_task.return_value = _make_obj(id="t1")
        mock_gc.return_value = client

        from strands_pack import box

        result = box(action="create_task", file_id="f1", message="Review please")
        assert result["success"] is True
        assert result["task_id"] == "t1"


def test_box_assign_task_success():
    with patch("strands_pack.box._get_client") as mock_gc:
        client = _mock_client()
        client.task_assignments.create_task_assignment.return_value = _make_obj(id="a1")
        mock_gc.return_value = client

        from strands_pack import box

        result = box(action="assign_task", task_id="t1", user_id="u1")
        assert result["success"] is True
        assert result["assignment_id"] == "a1"


def test_box_assign_task_missing_params():
    with patch("strands_pack.box._get_client") as mock_gc:
        mock_gc.return_value = _mock_client()

        from strands_pack import box

        result = box(action="assign_task")
        assert result["success"] is False
        assert "task_id" in result["error"]


# ---------------------------------------------------------------------------
# create_comment
# ---------------------------------------------------------------------------


def test_box_create_comment_success():
    with patch("strands_pack.box._get_client") as mock_gc:
        client = _mock_client()
        client.comments.create_comment.return_value = _make_obj(id="c1")
        mock_gc.return_value = client

        from strands_pack import box

        result = box(action="create_comment", file_id="f1", message="Looks good!")
        assert result["success"] is True
        assert result["comment_id"] == "c1"


def test_box_create_comment_missing_message():
    with patch("strands_pack.box._get_client") as mock_gc:
        mock_gc.return_value = _mock_client()

        from strands_pack import box

        result = box(action="create_comment", file_id="f1")
        assert result["success"] is False
        assert "message" in result["error"]


# ---------------------------------------------------------------------------
# ai_ask
# ---------------------------------------------------------------------------


def test_box_ai_ask_success():
    with patch("strands_pack.box._get_client") as mock_gc:
        client = _mock_client()
        response = MagicMock(answer="The key takeaway is growth.", completion_reason="done")
        client.ai.create_ai_ask.return_value = response
        mock_gc.return_value = client

        from strands_pack import box

        result = box(action="ai_ask", file_id="f1", prompt="Key takeaways?")
        assert result["success"] is True
        assert result["answer"] == "The key takeaway is growth."


def test_box_ai_ask_missing_params():
    with patch("strands_pack.box._get_client") as mock_gc:
        mock_gc.return_value = _mock_client()

        from strands_pack import box

        result = box(action="ai_ask", file_id="f1")
        assert result["success"] is False
        assert "prompt" in result["error"]


# ---------------------------------------------------------------------------
# ai_text_gen
# ---------------------------------------------------------------------------


def test_box_ai_text_gen_success():
    with patch("strands_pack.box._get_client") as mock_gc:
        client = _mock_client()
        response = MagicMock(answer="Here is a summary...", completion_reason="done")
        client.ai.create_ai_text_gen.return_value = response
        mock_gc.return_value = client

        from strands_pack import box

        result = box(action="ai_text_gen", file_id="f1", prompt="Summarize this")
        assert result["success"] is True
        assert "summary" in result["answer"].lower()


# ---------------------------------------------------------------------------
# ai_extract
# ---------------------------------------------------------------------------


def test_box_ai_extract_success():
    with patch("strands_pack.box._get_client") as mock_gc:
        client = _mock_client()
        response = MagicMock(answer="vendor: Acme, amount: $5000", completion_reason="done")
        client.ai.create_ai_extract.return_value = response
        mock_gc.return_value = client

        from strands_pack import box

        result = box(action="ai_extract", file_id="f1", prompt="vendor, amount")
        assert result["success"] is True
        assert "Acme" in result["answer"]


# ---------------------------------------------------------------------------
# ai_extract_structured
# ---------------------------------------------------------------------------


def test_box_ai_extract_structured_success():
    with patch("strands_pack.box._get_client") as mock_gc:
        client = _mock_client()
        response = MagicMock(answer={"vendor": "Acme", "amount": 5000.0})
        client.ai.create_ai_extract_structured.return_value = response
        mock_gc.return_value = client

        from strands_pack import box

        result = box(
            action="ai_extract_structured",
            file_id="f1",
            fields=[
                {"key": "vendor", "type": "string", "prompt": "Who is the vendor?"},
                {"key": "amount", "type": "float", "prompt": "Total amount?"},
            ],
        )
        assert result["success"] is True
        assert result["answer"]["vendor"] == "Acme"


def test_box_ai_extract_structured_missing_fields():
    with patch("strands_pack.box._get_client") as mock_gc:
        mock_gc.return_value = _mock_client()

        from strands_pack import box

        result = box(action="ai_extract_structured", file_id="f1")
        assert result["success"] is False
        assert "fields" in result["error"]


# ---------------------------------------------------------------------------
# Error handling / edge cases
# ---------------------------------------------------------------------------


def test_box_unknown_action():
    from strands_pack import box

    result = box(action="unknown_action")
    assert result["success"] is False
    assert "Unknown action" in result["error"]
    assert "available_actions" in result


def test_box_missing_sdk():
    """HAS_BOX=False (overrides the autouse fixture)."""
    with patch("strands_pack.box.HAS_BOX", False):
        from strands_pack import box

        result = box(action="get_current_user")
        assert result["success"] is False
        assert result["error_type"] == "MissingDependency"


def test_box_auth_failure():
    with patch("strands_pack.box._get_client") as mock_gc:
        mock_gc.side_effect = ValueError("No Box credentials found.")

        from strands_pack import box

        result = box(action="get_current_user")
        assert result["success"] is False
        assert "credentials" in result["error"].lower()


def test_box_api_exception():
    with patch("strands_pack.box._get_client") as mock_gc:
        client = _mock_client()
        client.users.get_user_me.side_effect = RuntimeError("API rate limit exceeded")
        mock_gc.return_value = client

        from strands_pack import box

        result = box(action="get_current_user")
        assert result["success"] is False
        assert result["error_type"] == "RuntimeError"
        assert "rate limit" in result["error"].lower()
