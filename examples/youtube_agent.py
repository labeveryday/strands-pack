#!/usr/bin/env python3
"""
YouTube Agent Example

Demonstrates all YouTube tools:
- youtube_read: Search and get video/channel metadata (API key only)
- youtube_write: Update video metadata and playlist membership (OAuth)
- youtube_analytics: Query channel analytics (OAuth)
- youtube_transcript: Fetch public video transcripts (no auth)

Usage:
    python examples/youtube_agent.py

Requirements:
    pip install strands-pack[youtube,youtube_transcript]

Environment:
    YOUTUBE_API_KEY - Required for youtube_read (search, get_videos, etc.)
    YOUTUBE_CHANNEL_ID - Optional default channel
    YOUTUBE_UPLOADS_PLAYLIST_ID - Optional default uploads playlist
    OAuth credentials - Required for youtube_write and youtube_analytics
"""

import os
import sys

from pathlib import Path

# Get repo root (parent of examples/)
_repo_root = Path(__file__).resolve().parent.parent

# Change to repo root so secrets/ is found
os.chdir(_repo_root)

# Add src to path for local development
sys.path.insert(0, str(_repo_root / "src"))

from dotenv import load_dotenv

load_dotenv()

from strands import Agent
from strands_pack import youtube_read, youtube_transcript, youtube_write, google_auth


def main():
    """Run the YouTube agent."""
    agent = Agent(tools=[youtube_read, youtube_write, youtube_transcript, google_auth])

    print("=" * 60)
    print("YouTube Agent")
    print("=" * 60)
    print("\nThis agent searches YouTube and fetches video information.")
    print("\nAvailable tools:")
    print("\n  youtube_read (6 actions) - API key only:")
    print("    search              - Search for videos, channels, playlists")
    print("    get_videos          - Get video details by ID")
    print("    get_channels        - Get channel details")
    print("    list_playlists      - List playlists for a channel")
    print("    list_playlist_items - List videos in a playlist")
    print("    get_comments        - List comments for a video")
    print("\n  youtube_write (10 actions) - OAuth required:")
    print("    update_video_metadata      - Update title/description/tags")
    print("    add_video_to_playlist      - Add video to a playlist")
    print("    remove_video_from_playlist - Remove from playlist")
    print("    create_playlist            - Create new playlist")
    print("    update_playlist            - Update playlist metadata")
    print("    delete_playlist            - Delete playlist (confirm required)")
    print("    delete_video               - Delete video (confirm required)")
    print("    delete_video_if_private    - Delete only if private (confirm)")
    print("    set_thumbnail              - Upload custom thumbnail")
    print("    set_video_privacy          - Set public/unlisted/private (confirm)")
    print("\n  youtube_transcript (1 action) - No auth:")
    print("    get_transcript      - Fetch public video transcript")
    print("\nExample queries:")
    print("  - Search YouTube for 'python tutorial'")
    print("  - Search for short HD videos about 'lofi beats'")
    print("  - Get details for video dQw4w9WgXcQ")
    print("  - Get the transcript for video dQw4w9WgXcQ")
    print("  - List playlists for channel UC_x5XG1OV2P6uZZ5FSM9Ttw")
    print("\nType 'quit' or 'exit' to end.\n")

    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q"):
                print("Goodbye!")
                break

            response = agent(user_input)
            print(f"\nAgent: {response}\n")

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
