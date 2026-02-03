"""
YouTube Transcript Tool (Public)

Fetch transcripts for **public** YouTube videos when available.

Why this exists
--------------
YouTube "transcripts" are not consistently accessible via the official YouTube Data API v3
unless you have caption-owner access. For your *own* videos, use the official captions flow:
`youtube(action="list_captions" / "download_caption", auth_type="authorized_user", ...)`.

For public videos, this tool uses the community-maintained `youtube-transcript-api` package
to retrieve transcript segments when YouTube exposes them.

Install:
    pip install "strands-pack[youtube_transcript]"

Supported actions
-----------------
- get_transcript
    Parameters:
      - video_id (required)
      - languages (optional): list[str] or comma-separated string, e.g. ["en","en-US"]
      - preserve_formatting (bool, default False)
      - output_format (str, default "text"): "text" | "text_with_timestamps"
      - output_path (optional): if provided, writes transcript text to disk
      - include_segments (bool, default False): include raw segments list in output

Usage (Agent)
-------------
    from strands import Agent
    from strands_pack import youtube_transcript

    agent = Agent(tools=[youtube_transcript])

    # Fetch transcript text (best-effort)
    agent.tool.youtube_transcript(action="get_transcript", video_id="VIDEO_ID", languages=["en"])

    # Save transcript to disk
    agent.tool.youtube_transcript(
        action="get_transcript",
        video_id="VIDEO_ID",
        languages="en,en-US",
        output_format="text_with_timestamps",
        output_path="downloads/transcript.txt",
    )
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from strands import tool

try:
    from youtube_transcript_api import YouTubeTranscriptApi as _YTA

    HAS_YOUTUBE_TRANSCRIPT = True
except ImportError:  # pragma: no cover
    _YTA = None
    HAS_YOUTUBE_TRANSCRIPT = False


def _csv_list(value: Optional[Any]) -> Optional[List[str]]:
    if value is None:
        return None
    if isinstance(value, list):
        out = [str(v).strip() for v in value if str(v).strip()]
        return out or None
    if isinstance(value, str):
        out = [v.strip() for v in value.split(",") if v.strip()]
        return out or None
    return [str(value).strip()]


def _segments_to_text(segments: Sequence[Dict[str, Any]]) -> str:
    # youtube-transcript-api returns segments like: {"text": "...", "start": 12.34, "duration": 3.21}
    return "\n".join(str(s.get("text", "")).rstrip() for s in segments).strip()


def _format_ts(seconds: float) -> str:
    # Format as HH:MM:SS (no milliseconds) for readability in plain text.
    try:
        total = int(float(seconds))
    except Exception:
        total = 0
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def _segments_to_text_with_timestamps(segments: Sequence[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for seg in segments:
        ts = _format_ts(seg.get("start", 0.0))
        txt = str(seg.get("text", "")).rstrip()
        if not txt:
            continue
        lines.append(f"[{ts}] {txt}")
    return "\n".join(lines).strip()


@tool
def youtube_transcript(
    action: str,
    video_id: Optional[str] = None,
    languages: Optional[List[str]] = None,
    preserve_formatting: bool = False,
    output_format: str = "text",
    output_path: Optional[str] = None,
    include_segments: bool = False,
) -> Dict[str, Any]:
    """
    Fetch transcripts for public YouTube videos.

    Args:
        action: The operation to perform. One of:
            - "get_transcript": Fetch transcript for a video
        video_id: YouTube video ID (required for get_transcript)
        languages: Preferred languages as list, e.g. ["en", "en-US"]. Falls back if unavailable.
        preserve_formatting: Keep original formatting like line breaks (default False)
        output_format: Output format - "text" or "text_with_timestamps" (default "text")
        output_path: Optional file path to save transcript
        include_segments: Include raw segment data in response (default False)

    Returns:
        dict with:
            - success: bool
            - video_id: str
            - transcript_text: str
            - segments: list (if include_segments=True)
            - output_path: str (if output_path provided)

    Examples:
        # Get transcript as plain text
        youtube_transcript(action="get_transcript", video_id="dQw4w9WgXcQ")

        # Get transcript in English with timestamps
        youtube_transcript(
            action="get_transcript",
            video_id="dQw4w9WgXcQ",
            languages=["en", "en-US"],
            output_format="text_with_timestamps",
        )

        # Save transcript to file
        youtube_transcript(
            action="get_transcript",
            video_id="dQw4w9WgXcQ",
            output_path="transcripts/video.txt",
        )
    """
    valid_actions = ["get_transcript"]
    action = (action or "").strip()
    if action not in valid_actions:
        return {"success": False, "error": f"Unknown action: {action}", "available_actions": valid_actions}

    if action == "get_transcript":
        if not HAS_YOUTUBE_TRANSCRIPT:
            return {
                "success": False,
                "error": "Missing dependency: youtube-transcript-api. Install with: pip install strands-pack[youtube_transcript]",
                "error_type": "MissingDependency",
            }

        if not video_id:
            return {"success": False, "error": "video_id is required"}

        langs = _csv_list(languages) or ["en"]

        try:
            # youtube-transcript-api v1.x uses instance method .fetch()
            result = _YTA().fetch(video_id, languages=langs, preserve_formatting=preserve_formatting)
            # Convert FetchedTranscript to list of dicts for compatibility
            segments = [{"text": s.text, "start": s.start, "duration": s.duration} for s in result.snippets]
        except Exception as e:
            return {"success": False, "error": str(e), "video_id": video_id}

        if output_format == "text":
            text = _segments_to_text(segments)
        elif output_format == "text_with_timestamps":
            text = _segments_to_text_with_timestamps(segments)
        else:
            return {
                "success": False,
                "error": f"Unknown output_format: {output_format}. Valid: text, text_with_timestamps",
                "video_id": video_id,
            }

        result: Dict[str, Any] = {
            "success": True,
            "video_id": video_id,
            "output_format": output_format,
            "transcript_text": text,
        }

        if include_segments:
            result["segments"] = segments

        if output_path:
            p = Path(output_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
            result["output_path"] = str(p.absolute())

        return result

    return {"success": False, "error": f"Unhandled action: {action}"}


