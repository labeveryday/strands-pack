"""
DEPRECATED MODULE (compat shim)

The implementation for the YouTube Data API read tool lives in `strands_pack.youtube_read`.
This file remains to avoid breaking older imports like:

    from strands_pack.youtube import youtube_read, youtube
"""

from __future__ import annotations

from strands_pack.youtube_read import youtube, youtube_read

__all__ = ["youtube_read", "youtube"]
