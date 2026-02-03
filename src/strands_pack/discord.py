"""
Discord Tool

Discord bot messaging and channel management using REST API.

Usage Examples:
    from strands import Agent
    from strands_pack import discord

    agent = Agent(tools=[discord])

    # Send a message to a channel
    agent.tool.discord(action="send_message", channel_id="123456789", content="Hello, Discord!")

    # Send a message with embed
    agent.tool.discord(action="send_message", channel_id="123456789", content="Check this out!", embed={"title": "Alert", "description": "Important message"})

    # Reply to a message
    agent.tool.discord(action="send_message", channel_id="123456789", content="This is a reply!", reply_to="987654321")

    # Send a file
    agent.tool.discord(action="send_message", channel_id="123456789", content="Check out this file!", file_path="/path/to/file.png")

    # Send multiple files
    agent.tool.discord(action="send_message", channel_id="123456789", content="Here are the files", file_paths=["/path/to/file1.png", "/path/to/file2.pdf"])

    # Send an embed with a link and image
    agent.tool.discord(action="send_message", channel_id="123456789", embed={
        "title": "Check out this link!",
        "url": "https://example.com",
        "description": "Click the title to visit",
        "image": {"url": "https://example.com/image.png"},
        "color": 5814783
    })

    # Read messages from a channel
    agent.tool.discord(action="read_messages", channel_id="123456789", limit=10)

    # Create a thread from a message
    agent.tool.discord(action="create_thread", channel_id="123456789", message_id="987654321", name="Discussion Thread")

    # Create a thread without a message (standalone)
    agent.tool.discord(action="create_thread", channel_id="123456789", name="New Thread", type=11)

    # List active threads in a guild
    agent.tool.discord(action="list_threads", guild_id="123456789")

    # List members in a guild
    agent.tool.discord(action="list_members", guild_id="123456789", limit=50)

    # Search for a member by username
    agent.tool.discord(action="search_members", guild_id="123456789", query="john")

    # Get a specific member's info
    agent.tool.discord(action="get_member", guild_id="123456789", user_id="987654321")

    # Mention a user in a message (use <@user_id> format)
    agent.tool.discord(action="send_message", channel_id="123456789", content="Hey <@987654321>, check this out!")

    # Create a new channel
    agent.tool.discord(action="create_channel", guild_id="123456789", name="new-channel", type=0)

    # Delete a message
    agent.tool.discord(action="delete_message", channel_id="123456789", message_id="987654321")

    # Add a reaction to a message
    agent.tool.discord(action="add_reaction", channel_id="123456789", message_id="987654321", emoji="👍")

    # Get guild (server) info
    agent.tool.discord(action="get_guild_info", guild_id="123456789")

    # List channels in a guild
    agent.tool.discord(action="list_channels", guild_id="123456789")

    # Edit a message
    agent.tool.discord(action="edit_message", channel_id="123456789", message_id="987654321", content="Updated content")

Available Actions:
    - send_message: Send a message to a channel (supports replies, files, embeds)
        Parameters: channel_id (str), content (str), embed (dict), tts (bool), reply_to (str), file_path (str), file_paths (list)
    - read_messages: Read messages from a channel or thread
        Parameters: channel_id (str), limit (int), before (str), after (str)
    - create_channel: Create a new channel
        Parameters: guild_id (str), name (str), type (int), topic (str), category_id (str)
    - create_thread: Create a thread from a message or standalone
        Parameters: channel_id (str), name (str), message_id (str), type (int), auto_archive_duration (int)
    - list_threads: List active threads in a guild
        Parameters: guild_id (str)
    - list_members: List members in a guild
        Parameters: guild_id (str), limit (int), after (str)
    - get_member: Get info about a specific member
        Parameters: guild_id (str), user_id (str)
    - search_members: Search for members by username
        Parameters: guild_id (str), query (str), limit (int)
    - delete_message: Delete a message
        Parameters: channel_id (str), message_id (str)
    - add_reaction: Add a reaction to a message
        Parameters: channel_id (str), message_id (str), emoji (str)
    - get_guild_info: Get guild (server) information
        Parameters: guild_id (str)
    - list_channels: List channels in a guild
        Parameters: guild_id (str), type_filter (int)
    - edit_message: Edit a message
        Parameters: channel_id (str), message_id (str), content (str), embed (dict)

Channel Types:
    0 = GUILD_TEXT
    2 = GUILD_VOICE
    4 = GUILD_CATEGORY
    5 = GUILD_ANNOUNCEMENT
    10 = ANNOUNCEMENT_THREAD
    11 = PUBLIC_THREAD
    12 = PRIVATE_THREAD
    13 = GUILD_STAGE_VOICE
    15 = GUILD_FORUM

Environment Variables:
    DISCORD_BOT_TOKEN: Discord bot token (required)
    DISCORD_GUILD_ID: Default guild/server ID (optional; used when guild_id not provided)
    DISCORD_CHANNEL_ID: Default channel/thread ID (optional; used when channel_id not provided)
    DISCORD_DEFAULT_GUILD_ID: Alias for DISCORD_GUILD_ID (optional)
    DISCORD_DEFAULT_CHANNEL_ID: Alias for DISCORD_CHANNEL_ID (optional)

Requirements:
    pip install strands-pack[discord]
"""

import os
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from strands import tool

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


DISCORD_API_BASE = "https://discord.com/api/v10"


def _check_requests() -> Optional[Dict[str, Any]]:
    """Check if requests is installed."""
    if not HAS_REQUESTS:
        return {
            "success": False,
            "error": "requests not installed. Run: pip install strands-pack[discord]"
        }
    return None


def _get_token() -> Optional[str]:
    """Get Discord bot token from environment."""
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        return None
    token = token.strip()
    # Allow users to paste tokens with a leading "Bot " prefix (we add it in headers).
    if token.lower().startswith("bot "):
        token = token[4:].strip()
    return token or None


def _get_default_guild_id() -> Optional[str]:
    """Get default Discord guild/server ID from environment (optional)."""
    return os.environ.get("DISCORD_GUILD_ID") or os.environ.get("DISCORD_DEFAULT_GUILD_ID")


def _get_default_channel_id() -> Optional[str]:
    """Get default Discord channel/thread ID from environment (optional)."""
    return os.environ.get("DISCORD_CHANNEL_ID") or os.environ.get("DISCORD_DEFAULT_CHANNEL_ID")


def _apply_env_defaults(action: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply optional environment variable defaults to common parameters.

    This is a convenience feature so callers can omit IDs when they are constant
    for a session (e.g., default guild/channel).
    """
    # Copy to avoid mutating caller dict
    out = dict(kwargs)

    if not out.get("guild_id"):
        if default_guild_id := _get_default_guild_id():
            out["guild_id"] = default_guild_id

    if not out.get("channel_id"):
        if default_channel_id := _get_default_channel_id():
            out["channel_id"] = default_channel_id

    return out


def _get_headers() -> Dict[str, str]:
    """Get headers for Discord API requests."""
    token = _get_token()
    return {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json",
        "User-Agent": "Strands-Pack-Discord/1.0"
    }


def _make_request(method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
    """Make a request to Discord API."""
    url = f"{DISCORD_API_BASE}{endpoint}"
    headers = _get_headers()

    try:
        response = requests.request(method, url, headers=headers, timeout=30, **kwargs)
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "hint": "Network/request failure. Check connectivity and that 'requests' is installed.",
        }

    if response.status_code >= 400:
        error_data: Dict[str, Any] = {}
        if response.text:
            try:
                error_data = response.json()
            except Exception:
                error_data = {"message": response.text}

        hint = None
        if response.status_code == 401:
            hint = "Unauthorized (401). Your bot token is invalid, revoked, or not being loaded correctly."
        elif response.status_code == 403:
            hint = "Forbidden (403). The bot may not be in that server, or lacks permissions (e.g., View Channels)."
        elif response.status_code == 404:
            hint = "Not found (404). The guild/channel ID may be wrong, or the bot cannot access it."

        return {
            "success": False,
            "error": error_data.get("message", f"HTTP {response.status_code}"),
            "status_code": response.status_code,
            "code": error_data.get("code"),
            "endpoint": endpoint,
            "hint": hint,
        }

    if response.status_code == 204:
        return {"success": True, "data": None}

    return {"success": True, "data": response.json()}


def _action_send_message(**kwargs) -> Dict[str, Any]:
    """Send a message to a channel or thread, optionally with files, embeds, or as a reply."""
    import json as json_module
    from pathlib import Path

    channel_id = kwargs.get("channel_id")
    content = kwargs.get("content")
    embed = kwargs.get("embed")
    tts = kwargs.get("tts", False)
    reply_to = kwargs.get("reply_to")
    file_path = kwargs.get("file_path")  # Single file path
    file_paths = kwargs.get("file_paths")  # Multiple file paths

    if not channel_id:
        return {"success": False, "error": "channel_id is required"}
    if not content and not embed and not file_path and not file_paths:
        return {"success": False, "error": "content, embed, or file is required"}

    # Collect files to upload
    files_to_upload = []
    if file_path:
        files_to_upload.append(file_path)
    if file_paths:
        files_to_upload.extend(file_paths)

    # If we have files, use multipart/form-data
    if files_to_upload:
        # Validate files exist
        for fp in files_to_upload:
            if not Path(fp).exists():
                return {"success": False, "error": f"File not found: {fp}"}

        # Build payload_json for the message content
        payload = {"tts": tts}
        if content:
            payload["content"] = content
        if embed:
            payload["embeds"] = [embed] if isinstance(embed, dict) else embed
        if reply_to:
            payload["message_reference"] = {"message_id": reply_to}

        # Prepare multipart form data
        url = f"{DISCORD_API_BASE}/channels/{channel_id}/messages"
        token = _get_token()
        headers = {
            "Authorization": f"Bot {token}",
            "User-Agent": "Strands-Pack-Discord/1.0"
        }

        try:
            # Build files dict for requests
            files = {}
            for i, fp in enumerate(files_to_upload):
                p = Path(fp)
                files[f"files[{i}]"] = (p.name, open(p, "rb"))

            # Add payload_json as form field
            data = {"payload_json": json_module.dumps(payload)}

            response = requests.post(url, headers=headers, data=data, files=files, timeout=60)

            # Close file handles
            for f in files.values():
                f[1].close()

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "hint": "File upload failed"
            }

        if response.status_code >= 400:
            error_data = {}
            try:
                error_data = response.json()
            except Exception:
                error_data = {"message": response.text}
            return {
                "success": False,
                "error": error_data.get("message", f"HTTP {response.status_code}"),
                "status_code": response.status_code
            }

        msg = response.json()
        attachments = [
            {"id": a["id"], "filename": a["filename"], "url": a["url"], "size": a.get("size")}
            for a in msg.get("attachments", [])
        ]
        return {
            "success": True,
            "action": "send_message",
            "message_id": msg["id"],
            "channel_id": msg["channel_id"],
            "content": msg.get("content", ""),
            "timestamp": msg["timestamp"],
            "author": msg["author"]["username"],
            "attachments": attachments
        }

    # Standard JSON request (no files)
    payload = {"tts": tts}
    if content:
        payload["content"] = content
    if embed:
        payload["embeds"] = [embed] if isinstance(embed, dict) else embed
    if reply_to:
        payload["message_reference"] = {"message_id": reply_to}

    result = _make_request("POST", f"/channels/{channel_id}/messages", json=payload)

    if result["success"]:
        msg = result["data"]
        return {
            "success": True,
            "action": "send_message",
            "message_id": msg["id"],
            "channel_id": msg["channel_id"],
            "content": msg.get("content", ""),
            "timestamp": msg["timestamp"],
            "author": msg["author"]["username"]
        }
    return result


def _action_read_messages(**kwargs) -> Dict[str, Any]:
    """Read messages from a channel."""
    channel_id = kwargs.get("channel_id")
    limit = kwargs.get("limit", 50)
    before = kwargs.get("before")
    after = kwargs.get("after")

    if not channel_id:
        return {"success": False, "error": "channel_id is required"}

    params = {"limit": min(limit, 100)}
    if before:
        params["before"] = before
    if after:
        params["after"] = after

    result = _make_request("GET", f"/channels/{channel_id}/messages", params=params)

    if result["success"]:
        messages = result["data"]
        return {
            "success": True,
            "action": "read_messages",
            "channel_id": channel_id,
            "count": len(messages),
            "messages": [
                {
                    "id": m["id"],
                    "content": m.get("content", ""),
                    "author": m["author"]["username"],
                    "author_id": m["author"]["id"],
                    "timestamp": m["timestamp"],
                    "attachments": len(m.get("attachments", [])),
                    "embeds": len(m.get("embeds", []))
                }
                for m in messages
            ]
        }
    return result


def _action_create_channel(**kwargs) -> Dict[str, Any]:
    """Create a new channel in a guild."""
    guild_id = kwargs.get("guild_id")
    name = kwargs.get("name")
    channel_type = kwargs.get("type", 0)
    topic = kwargs.get("topic")
    category_id = kwargs.get("category_id")

    if not guild_id:
        return {"success": False, "error": "guild_id is required"}
    if not name:
        return {"success": False, "error": "name is required"}

    payload = {
        "name": name,
        "type": channel_type
    }
    if topic:
        payload["topic"] = topic
    if category_id:
        payload["parent_id"] = category_id

    result = _make_request("POST", f"/guilds/{guild_id}/channels", json=payload)

    if result["success"]:
        channel = result["data"]
        return {
            "success": True,
            "action": "create_channel",
            "channel_id": channel["id"],
            "name": channel["name"],
            "type": channel["type"],
            "guild_id": channel["guild_id"],
            "topic": channel.get("topic"),
            "position": channel.get("position")
        }
    return result


def _action_delete_message(**kwargs) -> Dict[str, Any]:
    """Delete a message."""
    channel_id = kwargs.get("channel_id")
    message_id = kwargs.get("message_id")

    if not channel_id:
        return {"success": False, "error": "channel_id is required"}
    if not message_id:
        return {"success": False, "error": "message_id is required"}

    result = _make_request("DELETE", f"/channels/{channel_id}/messages/{message_id}")

    if result["success"]:
        return {
            "success": True,
            "action": "delete_message",
            "channel_id": channel_id,
            "message_id": message_id,
            "deleted": True
        }
    return result


def _action_add_reaction(**kwargs) -> Dict[str, Any]:
    """Add a reaction to a message."""
    channel_id = kwargs.get("channel_id")
    message_id = kwargs.get("message_id")
    emoji = kwargs.get("emoji")

    if not channel_id:
        return {"success": False, "error": "channel_id is required"}
    if not message_id:
        return {"success": False, "error": "message_id is required"}
    if not emoji:
        return {"success": False, "error": "emoji is required"}

    # URL encode the emoji for custom emojis or unicode
    encoded_emoji = quote(emoji, safe='')

    result = _make_request("PUT", f"/channels/{channel_id}/messages/{message_id}/reactions/{encoded_emoji}/@me")

    if result["success"]:
        return {
            "success": True,
            "action": "add_reaction",
            "channel_id": channel_id,
            "message_id": message_id,
            "emoji": emoji,
            "added": True
        }
    return result


def _action_get_guild_info(**kwargs) -> Dict[str, Any]:
    """Get guild (server) information."""
    guild_id = kwargs.get("guild_id")

    if not guild_id:
        return {"success": False, "error": "guild_id is required"}

    result = _make_request("GET", f"/guilds/{guild_id}")

    if result["success"]:
        guild = result["data"]
        return {
            "success": True,
            "action": "get_guild_info",
            "id": guild["id"],
            "name": guild["name"],
            "description": guild.get("description"),
            "icon": guild.get("icon"),
            "owner_id": guild["owner_id"],
            "member_count": guild.get("approximate_member_count"),
            "presence_count": guild.get("approximate_presence_count"),
            "premium_tier": guild.get("premium_tier"),
            "premium_subscription_count": guild.get("premium_subscription_count"),
            "verification_level": guild.get("verification_level"),
            "features": guild.get("features", [])
        }
    return result


def _action_list_channels(**kwargs) -> Dict[str, Any]:
    """List channels in a guild."""
    guild_id = kwargs.get("guild_id")
    type_filter = kwargs.get("type_filter")

    if not guild_id:
        return {"success": False, "error": "guild_id is required"}

    result = _make_request("GET", f"/guilds/{guild_id}/channels")

    if result["success"]:
        channels = result["data"]

        # Filter by type if specified
        if type_filter is not None:
            channels = [c for c in channels if c["type"] == type_filter]

        return {
            "success": True,
            "action": "list_channels",
            "guild_id": guild_id,
            "count": len(channels),
            "channels": [
                {
                    "id": c["id"],
                    "name": c["name"],
                    "type": c["type"],
                    "position": c.get("position"),
                    "topic": c.get("topic"),
                    "parent_id": c.get("parent_id")
                }
                for c in channels
            ]
        }
    return result


def _action_edit_message(**kwargs) -> Dict[str, Any]:
    """Edit a message."""
    channel_id = kwargs.get("channel_id")
    message_id = kwargs.get("message_id")
    content = kwargs.get("content")
    embed = kwargs.get("embed")

    if not channel_id:
        return {"success": False, "error": "channel_id is required"}
    if not message_id:
        return {"success": False, "error": "message_id is required"}
    if not content and not embed:
        return {"success": False, "error": "content or embed is required"}

    payload = {}
    if content:
        payload["content"] = content
    if embed:
        payload["embeds"] = [embed] if isinstance(embed, dict) else embed

    result = _make_request("PATCH", f"/channels/{channel_id}/messages/{message_id}", json=payload)

    if result["success"]:
        msg = result["data"]
        return {
            "success": True,
            "action": "edit_message",
            "message_id": msg["id"],
            "channel_id": msg["channel_id"],
            "content": msg.get("content", ""),
            "edited_timestamp": msg.get("edited_timestamp"),
            "author": msg["author"]["username"]
        }
    return result


def _action_create_thread(**kwargs) -> Dict[str, Any]:
    """Create a thread from a message or as a standalone thread."""
    channel_id = kwargs.get("channel_id")
    name = kwargs.get("name")
    message_id = kwargs.get("message_id")
    thread_type = kwargs.get("type", 11)  # 11 = PUBLIC_THREAD
    auto_archive_duration = kwargs.get("auto_archive_duration", 1440)  # 24 hours

    if not channel_id:
        return {"success": False, "error": "channel_id is required"}
    if not name:
        return {"success": False, "error": "name is required"}

    payload = {
        "name": name,
        "auto_archive_duration": auto_archive_duration
    }

    if message_id:
        # Create thread from a message
        endpoint = f"/channels/{channel_id}/messages/{message_id}/threads"
    else:
        # Create standalone thread (requires type)
        endpoint = f"/channels/{channel_id}/threads"
        payload["type"] = thread_type

    result = _make_request("POST", endpoint, json=payload)

    if result["success"]:
        thread = result["data"]
        return {
            "success": True,
            "action": "create_thread",
            "thread_id": thread["id"],
            "name": thread["name"],
            "parent_id": thread.get("parent_id"),
            "owner_id": thread.get("owner_id"),
            "type": thread["type"],
            "message_count": thread.get("message_count", 0),
            "member_count": thread.get("member_count", 0)
        }
    return result


def _action_list_threads(**kwargs) -> Dict[str, Any]:
    """List active threads in a guild."""
    guild_id = kwargs.get("guild_id")

    if not guild_id:
        return {"success": False, "error": "guild_id is required"}

    result = _make_request("GET", f"/guilds/{guild_id}/threads/active")

    if result["success"]:
        data = result["data"]
        threads = data.get("threads", [])
        return {
            "success": True,
            "action": "list_threads",
            "guild_id": guild_id,
            "count": len(threads),
            "threads": [
                {
                    "id": t["id"],
                    "name": t["name"],
                    "parent_id": t.get("parent_id"),
                    "owner_id": t.get("owner_id"),
                    "type": t["type"],
                    "message_count": t.get("message_count", 0),
                    "member_count": t.get("member_count", 0),
                    "archived": t.get("thread_metadata", {}).get("archived", False)
                }
                for t in threads
            ]
        }
    return result


def _action_list_members(**kwargs) -> Dict[str, Any]:
    """List members in a guild."""
    guild_id = kwargs.get("guild_id")
    limit = kwargs.get("limit", 100)
    after = kwargs.get("after")  # User ID to paginate after

    if not guild_id:
        return {"success": False, "error": "guild_id is required"}

    params = {"limit": min(limit, 1000)}
    if after:
        params["after"] = after

    result = _make_request("GET", f"/guilds/{guild_id}/members", params=params)

    if result["success"]:
        members = result["data"]
        return {
            "success": True,
            "action": "list_members",
            "guild_id": guild_id,
            "count": len(members),
            "members": [
                {
                    "id": m["user"]["id"],
                    "username": m["user"]["username"],
                    "display_name": m.get("nick") or m["user"].get("global_name") or m["user"]["username"],
                    "discriminator": m["user"].get("discriminator", "0"),
                    "bot": m["user"].get("bot", False),
                    "joined_at": m.get("joined_at"),
                    "roles": m.get("roles", []),
                    "mention": f"<@{m['user']['id']}>"
                }
                for m in members
            ]
        }
    return result


def _action_get_member(**kwargs) -> Dict[str, Any]:
    """Get information about a specific guild member."""
    guild_id = kwargs.get("guild_id")
    user_id = kwargs.get("user_id")

    if not guild_id:
        return {"success": False, "error": "guild_id is required"}
    if not user_id:
        return {"success": False, "error": "user_id is required"}

    result = _make_request("GET", f"/guilds/{guild_id}/members/{user_id}")

    if result["success"]:
        m = result["data"]
        return {
            "success": True,
            "action": "get_member",
            "id": m["user"]["id"],
            "username": m["user"]["username"],
            "display_name": m.get("nick") or m["user"].get("global_name") or m["user"]["username"],
            "discriminator": m["user"].get("discriminator", "0"),
            "bot": m["user"].get("bot", False),
            "avatar": m["user"].get("avatar"),
            "joined_at": m.get("joined_at"),
            "roles": m.get("roles", []),
            "mention": f"<@{m['user']['id']}>"
        }
    return result


def _action_search_members(**kwargs) -> Dict[str, Any]:
    """Search for guild members by username."""
    guild_id = kwargs.get("guild_id")
    query = kwargs.get("query")
    limit = kwargs.get("limit", 10)

    if not guild_id:
        return {"success": False, "error": "guild_id is required"}
    if not query:
        return {"success": False, "error": "query is required"}

    params = {"query": query, "limit": min(limit, 1000)}

    result = _make_request("GET", f"/guilds/{guild_id}/members/search", params=params)

    if result["success"]:
        members = result["data"]
        return {
            "success": True,
            "action": "search_members",
            "guild_id": guild_id,
            "query": query,
            "count": len(members),
            "members": [
                {
                    "id": m["user"]["id"],
                    "username": m["user"]["username"],
                    "display_name": m.get("nick") or m["user"].get("global_name") or m["user"]["username"],
                    "bot": m["user"].get("bot", False),
                    "mention": f"<@{m['user']['id']}>"
                }
                for m in members
            ]
        }
    return result


# Action dispatcher
_ACTIONS = {
    "send_message": _action_send_message,
    "read_messages": _action_read_messages,
    "create_channel": _action_create_channel,
    "create_thread": _action_create_thread,
    "list_threads": _action_list_threads,
    "list_members": _action_list_members,
    "get_member": _action_get_member,
    "search_members": _action_search_members,
    "delete_message": _action_delete_message,
    "add_reaction": _action_add_reaction,
    "get_guild_info": _action_get_guild_info,
    "list_channels": _action_list_channels,
    "edit_message": _action_edit_message,
}


@tool
def discord(
    action: str,
    # Common identifiers
    channel_id: Optional[str] = None,
    guild_id: Optional[str] = None,
    message_id: Optional[str] = None,
    user_id: Optional[str] = None,
    # Message content
    content: Optional[str] = None,
    embed: Optional[Dict[str, Any]] = None,
    tts: bool = False,
    reply_to: Optional[str] = None,
    # File attachments
    file_path: Optional[str] = None,
    file_paths: Optional[list] = None,
    # Channel/thread creation
    name: Optional[str] = None,
    topic: Optional[str] = None,
    category_id: Optional[str] = None,
    channel_type: int = 0,
    auto_archive_duration: int = 1440,
    # Pagination/filtering
    limit: int = 50,
    before: Optional[str] = None,
    after: Optional[str] = None,
    query: Optional[str] = None,
    type_filter: Optional[int] = None,
    # Reactions
    emoji: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Manage Discord channels and messages using the bot API.

    Args:
        action: The action to perform. One of:
            - send_message: Send message to channel
            - read_messages: Read messages from channel
            - create_channel: Create a new channel
            - create_thread: Create a thread
            - list_threads: List active threads
            - list_members: List guild members
            - get_member: Get member info
            - search_members: Search members by name
            - delete_message: Delete a message
            - add_reaction: Add reaction to message
            - get_guild_info: Get guild info
            - list_channels: List channels in guild
            - edit_message: Edit a message
        channel_id: Discord channel ID
        guild_id: Discord guild/server ID
        message_id: Message ID (for replies, reactions, edits, deletes)
        user_id: User ID (for get_member)
        content: Message content text
        embed: Embed object (dict with title, description, color, etc.)
        tts: Text-to-speech flag
        reply_to: Message ID to reply to
        file_path: Single file path to attach
        file_paths: List of file paths to attach
        name: Name for new channel/thread
        topic: Channel topic
        category_id: Parent category ID for new channel
        channel_type: Channel type (0=text, 2=voice, 4=category, 11=public_thread)
        auto_archive_duration: Thread auto-archive in minutes (default 1440 = 24h)
        limit: Max results for read/list operations (default 50)
        before: Pagination - get items before this ID
        after: Pagination - get items after this ID
        query: Search query (for search_members)
        type_filter: Filter channels by type
        emoji: Emoji for add_reaction (e.g., "👍" or custom emoji)

    Returns:
        dict with success status and action-specific data

    Examples:
        # Send a message
        discord(action="send_message", channel_id="123", content="Hello!")

        # Read messages
        discord(action="read_messages", channel_id="123", limit=10)

        # List channels (uses DISCORD_GUILD_ID if set)
        discord(action="list_channels", guild_id="456")

        # Mention a user
        discord(action="send_message", channel_id="123", content="Hey <@user_id>!")
    """
    if err := _check_requests():
        return err

    if not _get_token():
        return {
            "success": False,
            "error": "DISCORD_BOT_TOKEN environment variable not set",
            "hint": "Set DISCORD_BOT_TOKEN with your bot token"
        }

    if action not in _ACTIONS:
        return {
            "success": False,
            "error": f"Unknown action: {action}",
            "available_actions": list(_ACTIONS.keys())
        }

    # Build kwargs from explicit parameters
    kwargs: Dict[str, Any] = {
        "channel_id": channel_id,
        "guild_id": guild_id,
        "message_id": message_id,
        "user_id": user_id,
        "content": content,
        "embed": embed,
        "tts": tts,
        "reply_to": reply_to,
        "file_path": file_path,
        "file_paths": file_paths,
        "name": name,
        "topic": topic,
        "category_id": category_id,
        "type": channel_type,
        "auto_archive_duration": auto_archive_duration,
        "limit": limit,
        "before": before,
        "after": after,
        "query": query,
        "type_filter": type_filter,
        "emoji": emoji,
    }

    try:
        kwargs = _apply_env_defaults(action, kwargs)
        return _ACTIONS[action](**kwargs)
    except Exception as e:
        error_type = type(e).__name__
        return {
            "success": False,
            "action": action,
            "error": str(e),
            "error_type": error_type
        }
