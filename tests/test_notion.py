"""Tests for Notion tool."""

from unittest.mock import MagicMock, patch


def test_notion_create_page_success():
    """Test creating a page successfully."""
    with patch("strands_pack.notion._get_notion_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.pages.create.return_value = {
            "id": "page-123",
            "object": "page",
            "created_time": "2024-01-01T00:00:00.000Z",
            "last_edited_time": "2024-01-01T00:00:00.000Z",
            "archived": False,
            "url": "https://notion.so/page-123",
            "parent": {"page_id": "parent-456"},
            "properties": {},
        }
        mock_get_client.return_value = mock_client

        from strands_pack import notion

        result = notion(
            action="create_page",
            parent_id="parent-456",
            title="Test Page",
        )

        assert result["success"] is True
        assert result["action"] == "create_page"
        assert result["page"]["id"] == "page-123"
        mock_client.pages.create.assert_called_once()


def test_notion_get_page_success():
    """Test getting a page successfully."""
    with patch("strands_pack.notion._get_notion_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.pages.retrieve.return_value = {
            "id": "page-123",
            "object": "page",
            "created_time": "2024-01-01T00:00:00.000Z",
            "last_edited_time": "2024-01-01T00:00:00.000Z",
            "archived": False,
            "url": "https://notion.so/page-123",
            "parent": {"page_id": "parent-456"},
            "properties": {"title": {"title": [{"text": {"content": "Test"}}]}},
        }
        mock_get_client.return_value = mock_client

        from strands_pack import notion

        result = notion(action="get_page", page_id="page-123")

        assert result["success"] is True
        assert result["action"] == "get_page"
        assert result["page"]["id"] == "page-123"


def test_notion_update_page_success():
    """Test updating a page successfully."""
    with patch("strands_pack.notion._get_notion_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.pages.update.return_value = {
            "id": "page-123",
            "object": "page",
            "created_time": "2024-01-01T00:00:00.000Z",
            "last_edited_time": "2024-01-02T00:00:00.000Z",
            "archived": True,
            "url": "https://notion.so/page-123",
            "parent": {"page_id": "parent-456"},
            "properties": {},
        }
        mock_get_client.return_value = mock_client

        from strands_pack import notion

        result = notion(action="update_page", page_id="page-123", archived=True)

        assert result["success"] is True
        assert result["action"] == "update_page"
        assert result["page"]["archived"] is True


def test_notion_query_database_success():
    """Test querying a database successfully."""
    with patch("strands_pack.notion._get_notion_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.databases.query.return_value = {
            "results": [
                {
                    "id": "page-1",
                    "object": "page",
                    "created_time": "2024-01-01T00:00:00.000Z",
                    "last_edited_time": "2024-01-01T00:00:00.000Z",
                    "archived": False,
                    "url": "https://notion.so/page-1",
                    "parent": {"database_id": "db-123"},
                    "properties": {},
                },
            ],
            "has_more": False,
            "next_cursor": None,
        }
        mock_get_client.return_value = mock_client

        from strands_pack import notion

        result = notion(action="query_database", database_id="db-123")

        assert result["success"] is True
        assert result["action"] == "query_database"
        assert result["count"] == 1


def test_notion_create_database_success():
    """Test creating a database successfully."""
    with patch("strands_pack.notion._get_notion_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.databases.create.return_value = {
            "id": "db-123",
            "object": "database",
            "created_time": "2024-01-01T00:00:00.000Z",
            "title": [{"text": {"content": "Tasks"}}],
            "url": "https://notion.so/db-123",
            "properties": {"Name": {"title": {}}},
        }
        mock_get_client.return_value = mock_client

        from strands_pack import notion

        result = notion(
            action="create_database",
            parent_id="page-123",
            title="Tasks",
            properties={"Name": {"title": {}}},
        )

        assert result["success"] is True
        assert result["action"] == "create_database"
        assert result["database"]["id"] == "db-123"


def test_notion_append_blocks_success():
    """Test appending blocks successfully."""
    with patch("strands_pack.notion._get_notion_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.blocks.children.append.return_value = {
            "results": [
                {"id": "block-1", "type": "paragraph"},
            ],
        }
        mock_get_client.return_value = mock_client

        from strands_pack import notion

        result = notion(
            action="append_blocks",
            block_id="page-123",
            children=[{"type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": "Hello"}}]}}],
        )

        assert result["success"] is True
        assert result["action"] == "append_blocks"
        assert result["blocks_appended"] == 1


def test_notion_get_blocks_success():
    """Test getting blocks successfully."""
    with patch("strands_pack.notion._get_notion_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.blocks.children.list.return_value = {
            "results": [
                {"id": "block-1", "type": "paragraph"},
                {"id": "block-2", "type": "heading_1"},
            ],
            "has_more": False,
            "next_cursor": None,
        }
        mock_get_client.return_value = mock_client

        from strands_pack import notion

        result = notion(action="get_blocks", block_id="page-123")

        assert result["success"] is True
        assert result["action"] == "get_blocks"
        assert result["count"] == 2


def test_notion_search_success():
    """Test searching successfully."""
    with patch("strands_pack.notion._get_notion_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.search.return_value = {
            "results": [
                {
                    "id": "page-1",
                    "object": "page",
                    "created_time": "2024-01-01T00:00:00.000Z",
                    "last_edited_time": "2024-01-01T00:00:00.000Z",
                    "archived": False,
                    "url": "https://notion.so/page-1",
                    "parent": {"workspace": True},
                    "properties": {},
                },
            ],
            "has_more": False,
            "next_cursor": None,
        }
        mock_get_client.return_value = mock_client

        from strands_pack import notion

        result = notion(action="search", query="test")

        assert result["success"] is True
        assert result["action"] == "search"
        assert result["count"] == 1


def test_notion_missing_required_params():
    """Test error when required params are missing."""
    with patch("strands_pack.notion._get_notion_client") as mock_get_client:
        mock_get_client.return_value = MagicMock()

        from strands_pack import notion

        result = notion(action="create_page", title="Test")  # Missing parent_id

        assert result["success"] is False
        assert "parent_id" in result["error"]


def test_notion_missing_token():
    """Test error when token is not set."""
    with patch.dict("os.environ", {}, clear=True):
        with patch("strands_pack.notion._notion_client", None):
            from strands_pack import notion

            result = notion(action="get_page", page_id="test")

            assert result["success"] is False
            # May fail with import error if notion-client not installed, or missing token
            assert "NOTION_TOKEN" in result["error"] or "not installed" in result["error"]


def test_notion_unknown_action():
    """Test error for unknown action."""
    from strands_pack import notion

    result = notion(action="unknown_action")

    assert result["success"] is False
    assert "Unknown action" in result["error"]
    assert "available_actions" in result
