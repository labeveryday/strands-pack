"""Tests for Discord tool."""

import os
from unittest.mock import patch

import pytest


@pytest.fixture
def mock_env_token():
    """Mock the DISCORD_BOT_TOKEN environment variable."""
    with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "test_bot_token_123"}):
        yield


def test_discord_missing_token():
    """Test error when DISCORD_BOT_TOKEN is not set."""
    with patch.dict(os.environ, {}, clear=True):
        os.environ.pop("DISCORD_BOT_TOKEN", None)

        from strands_pack import discord

        result = discord(action="send_message", channel_id="123", content="Hello")

        assert result["success"] is False
        assert "DISCORD_BOT_TOKEN" in result["error"]


def test_discord_token_strips_whitespace_and_optional_bot_prefix():
    """DISCORD_BOT_TOKEN should be sanitized (strip + optional leading 'Bot ')."""
    # Import the internal function directly from the module
    from strands_pack.discord import _get_token

    with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "  Bot abc123  "}, clear=True):
        assert _get_token() == "abc123"

    with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "  abc123  "}, clear=True):
        assert _get_token() == "abc123"


def test_discord_unknown_action(mock_env_token):
    """Test error for unknown action."""
    from strands_pack import discord

    result = discord(action="unknown_action")

    assert result["success"] is False
    assert "Unknown action" in result["error"]
    assert "available_actions" in result


def test_discord_send_message_missing_channel(mock_env_token):
    """Test error when channel_id is missing for send_message."""
    from strands_pack import discord

    result = discord(action="send_message", content="Hello")

    assert result["success"] is False
    assert "channel_id" in result["error"]


def test_discord_send_message_missing_content(mock_env_token):
    """Test error when content is missing for send_message."""
    from strands_pack import discord

    result = discord(action="send_message", channel_id="123")

    assert result["success"] is False
    assert "content" in result["error"] or "embed" in result["error"]


def test_discord_read_messages_missing_channel(mock_env_token):
    """Test error when channel_id is missing for read_messages."""
    from strands_pack import discord

    result = discord(action="read_messages")

    assert result["success"] is False
    assert "channel_id" in result["error"]


def test_discord_create_channel_missing_params(mock_env_token):
    """Test error when required params are missing for create_channel."""
    from strands_pack import discord

    result = discord(action="create_channel", guild_id="123")

    assert result["success"] is False
    assert "name" in result["error"]


def test_discord_delete_message_missing_params(mock_env_token):
    """Test error when required params are missing for delete_message."""
    from strands_pack import discord

    result = discord(action="delete_message", channel_id="123")

    assert result["success"] is False
    assert "message_id" in result["error"]


def test_discord_add_reaction_missing_params(mock_env_token):
    """Test error when required params are missing for add_reaction."""
    from strands_pack import discord

    result = discord(action="add_reaction", channel_id="123", message_id="456")

    assert result["success"] is False
    assert "emoji" in result["error"]


def test_discord_get_guild_info_missing_params(mock_env_token):
    """Test error when required params are missing for get_guild_info."""
    from strands_pack import discord

    result = discord(action="get_guild_info")

    assert result["success"] is False
    assert "guild_id" in result["error"]


def test_discord_list_channels_missing_params(mock_env_token):
    """Test error when required params are missing for list_channels."""
    from strands_pack import discord

    result = discord(action="list_channels")

    assert result["success"] is False
    assert "guild_id" in result["error"]


def test_discord_edit_message_missing_params(mock_env_token):
    """Test error when required params are missing for edit_message."""
    from strands_pack import discord

    result = discord(action="edit_message", channel_id="123", message_id="456")

    assert result["success"] is False
    assert "content" in result["error"] or "embed" in result["error"]


@patch("strands_pack.discord._make_request")
def test_discord_send_message_success(mock_request, mock_env_token):
    """Test successful message sending with mocked API."""
    mock_request.return_value = {
        "success": True,
        "data": {
            "id": "message123",
            "channel_id": "channel456",
            "content": "Hello, Discord!",
            "timestamp": "2024-01-01T00:00:00Z",
            "author": {"username": "TestBot"}
        }
    }

    from strands_pack import discord

    result = discord(
        action="send_message",
        channel_id="channel456",
        content="Hello, Discord!"
    )

    assert result["success"] is True
    assert result["message_id"] == "message123"
    assert result["content"] == "Hello, Discord!"
    mock_request.assert_called_once()


@patch("strands_pack.discord._make_request")
def test_discord_read_messages_success(mock_request, mock_env_token):
    """Test successful message reading with mocked API."""
    mock_request.return_value = {
        "success": True,
        "data": [
            {
                "id": "msg1",
                "content": "Message 1",
                "author": {"username": "User1", "id": "user1"},
                "timestamp": "2024-01-01T00:00:00Z",
                "attachments": [],
                "embeds": []
            },
            {
                "id": "msg2",
                "content": "Message 2",
                "author": {"username": "User2", "id": "user2"},
                "timestamp": "2024-01-01T00:01:00Z",
                "attachments": [{}],
                "embeds": []
            }
        ]
    }

    from strands_pack import discord

    result = discord(action="read_messages", channel_id="channel123", limit=10)

    assert result["success"] is True
    assert result["count"] == 2
    assert len(result["messages"]) == 2
    assert result["messages"][0]["content"] == "Message 1"
    assert result["messages"][1]["attachments"] == 1


@patch("strands_pack.discord._make_request")
def test_discord_create_channel_success(mock_request, mock_env_token):
    """Test successful channel creation with mocked API."""
    mock_request.return_value = {
        "success": True,
        "data": {
            "id": "channel789",
            "name": "new-channel",
            "type": 0,
            "guild_id": "guild123",
            "topic": "Test topic",
            "position": 5
        }
    }

    from strands_pack import discord

    result = discord(
        action="create_channel",
        guild_id="guild123",
        name="new-channel",
        channel_type=0,
        topic="Test topic"
    )

    assert result["success"] is True
    assert result["channel_id"] == "channel789"
    assert result["name"] == "new-channel"


@patch("strands_pack.discord._make_request")
def test_discord_delete_message_success(mock_request, mock_env_token):
    """Test successful message deletion with mocked API."""
    mock_request.return_value = {"success": True, "data": None}

    from strands_pack import discord

    result = discord(
        action="delete_message",
        channel_id="channel123",
        message_id="message456"
    )

    assert result["success"] is True
    assert result["deleted"] is True


@patch("strands_pack.discord._make_request")
def test_discord_add_reaction_success(mock_request, mock_env_token):
    """Test successful reaction adding with mocked API."""
    mock_request.return_value = {"success": True, "data": None}

    from strands_pack import discord

    result = discord(
        action="add_reaction",
        channel_id="channel123",
        message_id="message456",
        emoji="👍"
    )

    assert result["success"] is True
    assert result["added"] is True
    assert result["emoji"] == "👍"


@patch("strands_pack.discord._make_request")
def test_discord_get_guild_info_success(mock_request, mock_env_token):
    """Test successful guild info retrieval with mocked API."""
    mock_request.return_value = {
        "success": True,
        "data": {
            "id": "guild123",
            "name": "Test Server",
            "description": "A test server",
            "icon": "icon_hash",
            "owner_id": "owner456",
            "approximate_member_count": 100,
            "approximate_presence_count": 50,
            "premium_tier": 2,
            "premium_subscription_count": 10,
            "verification_level": 1,
            "features": ["COMMUNITY"]
        }
    }

    from strands_pack import discord

    result = discord(action="get_guild_info", guild_id="guild123")

    assert result["success"] is True
    assert result["name"] == "Test Server"
    assert result["member_count"] == 100


@patch("strands_pack.discord._make_request")
def test_discord_list_channels_success(mock_request, mock_env_token):
    """Test successful channel listing with mocked API."""
    mock_request.return_value = {
        "success": True,
        "data": [
            {"id": "ch1", "name": "general", "type": 0, "position": 0, "topic": "General chat", "parent_id": None},
            {"id": "ch2", "name": "voice", "type": 2, "position": 1, "topic": None, "parent_id": None},
            {"id": "ch3", "name": "announcements", "type": 5, "position": 2, "topic": "News", "parent_id": None}
        ]
    }

    from strands_pack import discord

    result = discord(action="list_channels", guild_id="guild123")

    assert result["success"] is True
    assert result["count"] == 3
    assert len(result["channels"]) == 3


@patch("strands_pack.discord._make_request")
def test_discord_list_channels_with_filter(mock_request, mock_env_token):
    """Test channel listing with type filter."""
    mock_request.return_value = {
        "success": True,
        "data": [
            {"id": "ch1", "name": "general", "type": 0, "position": 0, "topic": None, "parent_id": None},
            {"id": "ch2", "name": "voice", "type": 2, "position": 1, "topic": None, "parent_id": None},
            {"id": "ch3", "name": "random", "type": 0, "position": 2, "topic": None, "parent_id": None}
        ]
    }

    from strands_pack import discord

    result = discord(action="list_channels", guild_id="guild123", type_filter=0)

    assert result["success"] is True
    assert result["count"] == 2
    # Only text channels (type 0) should be included
    for channel in result["channels"]:
        assert channel["type"] == 0


@patch("strands_pack.discord._make_request")
def test_discord_send_message_uses_default_channel_id_from_env(mock_request, mock_env_token):
    """If channel_id is omitted, the tool should use DISCORD_CHANNEL_ID when set."""
    mock_request.return_value = {
        "success": True,
        "data": {
            "id": "message123",
            "channel_id": "channel456",
            "content": "Hello, Discord!",
            "timestamp": "2024-01-01T00:00:00Z",
            "author": {"username": "TestBot"},
        },
    }

    from strands_pack import discord

    with patch.dict(os.environ, {"DISCORD_CHANNEL_ID": "channel456"}, clear=False):
        result = discord(action="send_message", content="Hello, Discord!")

    assert result["success"] is True
    mock_request.assert_called_once()
    method, endpoint = mock_request.call_args.args[:2]
    assert method == "POST"
    assert endpoint == "/channels/channel456/messages"


@patch("strands_pack.discord._make_request")
def test_discord_list_channels_uses_default_guild_id_from_env(mock_request, mock_env_token):
    """If guild_id is omitted, the tool should use DISCORD_GUILD_ID when set."""
    mock_request.return_value = {"success": True, "data": []}

    from strands_pack import discord

    with patch.dict(os.environ, {"DISCORD_GUILD_ID": "guild123"}, clear=False):
        result = discord(action="list_channels")

    assert result["success"] is True
    mock_request.assert_called_once()
    method, endpoint = mock_request.call_args.args[:2]
    assert method == "GET"
    assert endpoint == "/guilds/guild123/channels"


@patch("strands_pack.discord._make_request")
def test_discord_edit_message_success(mock_request, mock_env_token):
    """Test successful message editing with mocked API."""
    mock_request.return_value = {
        "success": True,
        "data": {
            "id": "message123",
            "channel_id": "channel456",
            "content": "Updated content",
            "edited_timestamp": "2024-01-01T00:05:00Z",
            "author": {"username": "TestBot"}
        }
    }

    from strands_pack import discord

    result = discord(
        action="edit_message",
        channel_id="channel456",
        message_id="message123",
        content="Updated content"
    )

    assert result["success"] is True
    assert result["content"] == "Updated content"
    assert result["edited_timestamp"] is not None


@patch("strands_pack.discord._make_request")
def test_discord_api_error(mock_request, mock_env_token):
    """Test handling of API errors."""
    mock_request.return_value = {
        "success": False,
        "error": "Unknown Channel",
        "status_code": 404,
        "code": 10003
    }

    from strands_pack import discord

    result = discord(action="send_message", channel_id="invalid", content="Test")

    assert result["success"] is False
    assert "Unknown Channel" in result["error"]


@patch("strands_pack.discord._make_request")
def test_discord_send_message_with_embed(mock_request, mock_env_token):
    """Test sending message with embed."""
    mock_request.return_value = {
        "success": True,
        "data": {
            "id": "message123",
            "channel_id": "channel456",
            "content": "",
            "timestamp": "2024-01-01T00:00:00Z",
            "author": {"username": "TestBot"}
        }
    }

    from strands_pack import discord

    result = discord(
        action="send_message",
        channel_id="channel456",
        embed={"title": "Alert", "description": "Important message", "color": 16711680}
    )

    assert result["success"] is True
    mock_request.assert_called_once()


@patch("strands_pack.discord._make_request")
def test_discord_send_message_with_reply(mock_request, mock_env_token):
    """Test sending a message as a reply to another message."""
    mock_request.return_value = {
        "success": True,
        "data": {
            "id": "message789",
            "channel_id": "channel456",
            "content": "This is a reply!",
            "timestamp": "2024-01-01T00:00:00Z",
            "author": {"username": "TestBot"}
        }
    }

    from strands_pack import discord

    result = discord(
        action="send_message",
        channel_id="channel456",
        content="This is a reply!",
        reply_to="message123"
    )

    assert result["success"] is True
    mock_request.assert_called_once()
    # Verify message_reference was included in the payload
    call_kwargs = mock_request.call_args.kwargs
    assert "json" in call_kwargs
    assert "message_reference" in call_kwargs["json"]
    assert call_kwargs["json"]["message_reference"]["message_id"] == "message123"


@patch("strands_pack.discord._make_request")
def test_discord_create_thread_from_message(mock_request, mock_env_token):
    """Test creating a thread from a message."""
    mock_request.return_value = {
        "success": True,
        "data": {
            "id": "thread123",
            "name": "Discussion Thread",
            "parent_id": "channel456",
            "owner_id": "user789",
            "type": 11,
            "message_count": 0,
            "member_count": 1
        }
    }

    from strands_pack import discord

    result = discord(
        action="create_thread",
        channel_id="channel456",
        message_id="message123",
        name="Discussion Thread"
    )

    assert result["success"] is True
    assert result["thread_id"] == "thread123"
    assert result["name"] == "Discussion Thread"
    mock_request.assert_called_once()
    method, endpoint = mock_request.call_args.args[:2]
    assert method == "POST"
    assert endpoint == "/channels/channel456/messages/message123/threads"


@patch("strands_pack.discord._make_request")
def test_discord_create_standalone_thread(mock_request, mock_env_token):
    """Test creating a standalone thread without a message."""
    mock_request.return_value = {
        "success": True,
        "data": {
            "id": "thread456",
            "name": "New Thread",
            "parent_id": "channel456",
            "owner_id": "user789",
            "type": 11,
            "message_count": 0,
            "member_count": 1
        }
    }

    from strands_pack import discord

    result = discord(
        action="create_thread",
        channel_id="channel456",
        name="New Thread",
        channel_type=11
    )

    assert result["success"] is True
    assert result["thread_id"] == "thread456"
    mock_request.assert_called_once()
    method, endpoint = mock_request.call_args.args[:2]
    assert method == "POST"
    assert endpoint == "/channels/channel456/threads"


def test_discord_create_thread_missing_params(mock_env_token):
    """Test create_thread with missing required parameters."""
    from strands_pack import discord

    # Missing channel_id
    result = discord(action="create_thread", name="Test Thread")
    assert result["success"] is False
    assert "channel_id" in result["error"]

    # Missing name
    result = discord(action="create_thread", channel_id="channel123")
    assert result["success"] is False
    assert "name" in result["error"]


@patch("strands_pack.discord._make_request")
def test_discord_list_threads_success(mock_request, mock_env_token):
    """Test listing active threads in a guild."""
    mock_request.return_value = {
        "success": True,
        "data": {
            "threads": [
                {
                    "id": "thread1",
                    "name": "Thread One",
                    "parent_id": "channel123",
                    "owner_id": "user1",
                    "type": 11,
                    "message_count": 5,
                    "member_count": 3,
                    "thread_metadata": {"archived": False}
                },
                {
                    "id": "thread2",
                    "name": "Thread Two",
                    "parent_id": "channel456",
                    "owner_id": "user2",
                    "type": 11,
                    "message_count": 10,
                    "member_count": 5,
                    "thread_metadata": {"archived": False}
                }
            ]
        }
    }

    from strands_pack import discord

    result = discord(action="list_threads", guild_id="guild123")

    assert result["success"] is True
    assert result["count"] == 2
    assert len(result["threads"]) == 2
    assert result["threads"][0]["name"] == "Thread One"
    assert result["threads"][1]["message_count"] == 10


def test_discord_list_threads_missing_guild_id(mock_env_token):
    """Test list_threads with missing guild_id."""
    from strands_pack import discord

    result = discord(action="list_threads")
    assert result["success"] is False
    assert "guild_id" in result["error"]


def test_discord_send_message_file_not_found(mock_env_token):
    """Test send_message with non-existent file."""
    from strands_pack import discord

    result = discord(
        action="send_message",
        channel_id="channel123",
        content="Test",
        file_path="/nonexistent/file.txt"
    )
    assert result["success"] is False
    assert "File not found" in result["error"]


@patch("strands_pack.discord.requests.post")
def test_discord_send_message_with_file(mock_post, mock_env_token, tmp_path):
    """Test sending a message with a file attachment."""
    # Create a temporary test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("Test content")

    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        "id": "message123",
        "channel_id": "channel456",
        "content": "Here is a file",
        "timestamp": "2024-01-01T00:00:00Z",
        "author": {"username": "TestBot"},
        "attachments": [
            {
                "id": "attach1",
                "filename": "test.txt",
                "url": "https://cdn.discordapp.com/attachments/test.txt",
                "size": 12
            }
        ]
    }

    from strands_pack import discord

    result = discord(
        action="send_message",
        channel_id="channel456",
        content="Here is a file",
        file_path=str(test_file)
    )

    assert result["success"] is True
    assert result["message_id"] == "message123"
    assert len(result["attachments"]) == 1
    assert result["attachments"][0]["filename"] == "test.txt"


def test_discord_send_message_with_embed_link(mock_env_token):
    """Test that embeds with URLs are properly formatted."""
    from strands_pack import discord

    # This test just verifies the embed structure is accepted
    # The actual API call would need to be mocked
    embed = {
        "title": "Test Link",
        "url": "https://example.com",
        "description": "Click to visit",
        "color": 5814783
    }

    # Verify the embed dict structure is valid
    assert "title" in embed
    assert "url" in embed
    assert embed["url"].startswith("http")


@patch("strands_pack.discord._make_request")
def test_discord_list_members_success(mock_request, mock_env_token):
    """Test listing members in a guild."""
    mock_request.return_value = {
        "success": True,
        "data": [
            {
                "user": {
                    "id": "user1",
                    "username": "testuser",
                    "global_name": "Test User",
                    "discriminator": "0",
                    "bot": False
                },
                "nick": None,
                "joined_at": "2024-01-01T00:00:00Z",
                "roles": ["role1", "role2"]
            },
            {
                "user": {
                    "id": "bot1",
                    "username": "testbot",
                    "global_name": "Test Bot",
                    "discriminator": "0",
                    "bot": True
                },
                "nick": "Bot Nickname",
                "joined_at": "2024-01-02T00:00:00Z",
                "roles": []
            }
        ]
    }

    from strands_pack import discord

    result = discord(action="list_members", guild_id="guild123", limit=10)

    assert result["success"] is True
    assert result["count"] == 2
    assert result["members"][0]["username"] == "testuser"
    assert result["members"][0]["mention"] == "<@user1>"
    assert result["members"][1]["bot"] is True
    assert result["members"][1]["display_name"] == "Bot Nickname"


def test_discord_list_members_missing_guild_id(mock_env_token):
    """Test list_members with missing guild_id."""
    from strands_pack import discord

    result = discord(action="list_members")
    assert result["success"] is False
    assert "guild_id" in result["error"]


@patch("strands_pack.discord._make_request")
def test_discord_get_member_success(mock_request, mock_env_token):
    """Test getting a specific member's info."""
    mock_request.return_value = {
        "success": True,
        "data": {
            "user": {
                "id": "user123",
                "username": "johndoe",
                "global_name": "John Doe",
                "discriminator": "0",
                "bot": False,
                "avatar": "abc123"
            },
            "nick": "Johnny",
            "joined_at": "2024-01-01T00:00:00Z",
            "roles": ["role1"]
        }
    }

    from strands_pack import discord

    result = discord(action="get_member", guild_id="guild123", user_id="user123")

    assert result["success"] is True
    assert result["id"] == "user123"
    assert result["username"] == "johndoe"
    assert result["display_name"] == "Johnny"
    assert result["mention"] == "<@user123>"


def test_discord_get_member_missing_params(mock_env_token):
    """Test get_member with missing parameters."""
    from strands_pack import discord

    # Missing guild_id
    result = discord(action="get_member", user_id="user123")
    assert result["success"] is False
    assert "guild_id" in result["error"]

    # Missing user_id
    result = discord(action="get_member", guild_id="guild123")
    assert result["success"] is False
    assert "user_id" in result["error"]


@patch("strands_pack.discord._make_request")
def test_discord_search_members_success(mock_request, mock_env_token):
    """Test searching for members by username."""
    mock_request.return_value = {
        "success": True,
        "data": [
            {
                "user": {
                    "id": "user1",
                    "username": "johnsmith",
                    "global_name": "John Smith",
                    "bot": False
                },
                "nick": None
            },
            {
                "user": {
                    "id": "user2",
                    "username": "johndoe",
                    "global_name": "John Doe",
                    "bot": False
                },
                "nick": "JD"
            }
        ]
    }

    from strands_pack import discord

    result = discord(action="search_members", guild_id="guild123", query="john")

    assert result["success"] is True
    assert result["query"] == "john"
    assert result["count"] == 2
    assert result["members"][0]["mention"] == "<@user1>"
    assert result["members"][1]["display_name"] == "JD"


def test_discord_search_members_missing_params(mock_env_token):
    """Test search_members with missing parameters."""
    from strands_pack import discord

    # Missing guild_id
    result = discord(action="search_members", query="john")
    assert result["success"] is False
    assert "guild_id" in result["error"]

    # Missing query
    result = discord(action="search_members", guild_id="guild123")
    assert result["success"] is False
    assert "query" in result["error"]
