"""
FFmpeg Tool

Video processing operations using FFmpeg.

Usage Examples:
    from strands import Agent
    from strands_pack import ffmpeg

    agent = Agent(tools=[ffmpeg])

    # Cut a video segment
    agent.tool.ffmpeg(action="cut", input_path="video.mp4", output_path="clip.mp4", start_time="00:01:30", duration="60")

    # Concatenate videos
    agent.tool.ffmpeg(action="concat", input_paths=["clip1.mp4", "clip2.mp4"], output_path="final.mp4")

    # Get video info
    agent.tool.ffmpeg(action="info", input_path="video.mp4")

    # Extract audio
    agent.tool.ffmpeg(action="extract_audio", input_path="video.mp4", output_path="audio.mp3")

Available Actions:
    - cut: Cut/trim a segment from a video
        Parameters: input_path, output_path, start_time, end_time OR duration
    - concat: Concatenate multiple videos
        Parameters: input_paths (list), output_path, reencode (bool)
    - info: Get video metadata
        Parameters: input_path
    - extract_audio: Extract audio track
        Parameters: input_path, output_path, format (mp3/wav/aac/flac)
    - resize: Scale video resolution (e.g., 1080p -> 720p)
        Parameters: input_path, output_path, width and/or height
    - convert: Change container/format (e.g., mp4 -> webm/mkv)
        Parameters: input_path, output_path, video_codec (optional), audio_codec (optional)
    - compress: Reduce file size using CRF quality
        Parameters: input_path, output_path, crf (optional), preset (optional)
    - add_audio: Add/replace an audio track in a video
        Parameters: input_path, audio_path, output_path, replace_audio (optional)
    - extract_frames: Export frames as images
        Parameters: input_path, output_dir, fps (optional), image_format (optional), pattern (optional)
    - create_gif: Convert video to GIF
        Parameters: input_path, output_path, fps (optional), width (optional)
    - thumbnail: Generate a thumbnail image
        Parameters: input_path, output_path, timestamp (optional)
    - rotate: Rotate video 90/180/270 degrees
        Parameters: input_path, output_path, degrees
    - speed: Change playback speed (e.g., 0.5x, 2x)
        Parameters: input_path, output_path, speed_factor
    - watermark: Add image/text overlay
        Parameters: input_path, output_path, watermark_image OR watermark_text, position (optional), opacity (optional)
    - remove_dead_space: Remove silent/dead-air segments from audio or video
        Parameters: input_path, output_path, threshold_db (optional), min_silence_duration (optional),
                    padding_ms (optional), mode ("audio"|"video"|"auto"), reencode (optional), max_segments (optional)

Requirements:
    ffmpeg must be installed on the system
    - macOS: brew install ffmpeg
    - Linux: apt install ffmpeg
    - Windows: https://ffmpeg.org/download.html
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Literal, Optional

from strands import tool


def _check_ffmpeg() -> bool:
    """Check if ffmpeg is available."""
    return shutil.which("ffmpeg") is not None


def _check_ffprobe() -> bool:
    """Check if ffprobe is available."""
    return shutil.which("ffprobe") is not None


def _run_ffmpeg(args: list[str], timeout: int = 300) -> tuple[bool, str]:
    """Run ffmpeg with given arguments."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-y"] + args,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        if result.returncode != 0:
            return False, result.stderr
        return True, "Success"
    except subprocess.TimeoutExpired:
        return False, f"Operation timed out after {timeout} seconds"
    except Exception as e:
        return False, str(e)


def _run_ffmpeg_capture_stderr(args: list[str], timeout: int = 300) -> tuple[bool, str]:
    """
    Run ffmpeg and always return stderr (used for analyzers like silencedetect).
    """
    try:
        result = subprocess.run(
            ["ffmpeg", "-y"] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode == 0, result.stderr or ""
    except subprocess.TimeoutExpired:
        return False, f"Operation timed out after {timeout} seconds"
    except Exception as e:
        return False, str(e)


def _run_ffprobe_capture(args: list[str], timeout: int = 30) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["ffprobe"] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            return False, result.stderr or ""
        return True, (result.stdout or "").strip()
    except subprocess.TimeoutExpired:
        return False, f"Operation timed out after {timeout} seconds"
    except Exception as e:
        return False, str(e)


def _get_duration_seconds(input_file: Path) -> tuple[bool, float | None, str]:
    if not _check_ffprobe():
        return False, None, "ffprobe is not installed (required for remove_dead_space)"
    ok, out = _run_ffprobe_capture(
        ["-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(input_file)]
    )
    if not ok:
        return False, None, out
    try:
        return True, float(out), ""
    except Exception:
        return False, None, f"Could not parse duration from ffprobe output: {out!r}"


def _parse_silencedetect(stderr: str) -> list[tuple[float, float | None]]:
    """
    Parse ffmpeg silencedetect output into a list of (start, end|None) intervals.
    """
    starts: list[float] = []
    intervals: list[tuple[float, float | None]] = []

    for line in (stderr or "").splitlines():
        if "silence_start:" in line:
            m = re.search(r"silence_start:\s*([0-9.]+)", line)
            if m:
                starts.append(float(m.group(1)))
        elif "silence_end:" in line:
            m = re.search(r"silence_end:\s*([0-9.]+)", line)
            if m and starts:
                s = starts.pop(0)
                intervals.append((s, float(m.group(1))))

    # Any unmatched starts become open-ended silence to EOF.
    for s in starts:
        intervals.append((s, None))
    return intervals


def _invert_silence_to_segments(
    silence: list[tuple[float, float | None]],
    duration: float,
    padding_ms: int,
    max_segments: int,
) -> list[tuple[float, float]]:
    """
    Convert silence intervals to non-silent segments [start,end], applying padding.
    """
    pad = max(0, int(padding_ms)) / 1000.0
    # Normalize
    intervals: list[tuple[float, float]] = []
    for s, e in silence:
        ss = max(0.0, float(s))
        ee = float(e) if e is not None else float(duration)
        ee = min(float(duration), max(ss, ee))
        intervals.append((ss, ee))
    intervals.sort(key=lambda x: x[0])

    # Merge overlaps
    merged: list[tuple[float, float]] = []
    for s, e in intervals:
        if not merged or s > merged[-1][1]:
            merged.append((s, e))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))

    segments: list[tuple[float, float]] = []
    cur = 0.0
    for s, e in merged:
        if s > cur:
            seg_start = max(0.0, cur - pad)
            seg_end = min(float(duration), s + pad)
            if seg_end > seg_start:
                segments.append((seg_start, seg_end))
        cur = max(cur, e)
    if cur < duration:
        seg_start = max(0.0, cur - pad)
        seg_end = float(duration)
        if seg_end > seg_start:
            segments.append((seg_start, seg_end))

    # Safety cap
    if len(segments) > int(max_segments):
        raise ValueError(f"Too many segments ({len(segments)}) exceeds max_segments={int(max_segments)}")

    # Remove tiny segments
    segments = [(s, e) for (s, e) in segments if (e - s) >= 0.05]
    return segments


def _audio_codec_args_for_output(output_file: Path) -> list[str]:
    ext = output_file.suffix.lower().lstrip(".")
    if ext in ("wav", "wave"):
        return ["-c:a", "pcm_s16le"]
    if ext in ("mp3",):
        return ["-c:a", "libmp3lame", "-q:a", "2"]
    if ext in ("flac",):
        return ["-c:a", "flac"]
    if ext in ("m4a", "mp4", "mov"):
        return ["-c:a", "aac", "-b:a", "192k"]
    # Best-effort default
    return ["-c:a", "aac", "-b:a", "192k"]


def _remove_dead_space(
    input_path: str,
    output_path: str,
    threshold_db: float = -45.0,
    min_silence_duration: float = 0.35,
    padding_ms: int = 120,
    mode: str = "auto",
    reencode: bool = True,
    max_segments: int = 200,
) -> str:
    """
    Remove silent/dead-air segments by detecting audio silence and cutting/concatenating non-silent regions.
    """
    if not _check_ffmpeg():
        return "Error: ffmpeg is not installed."

    input_file = Path(input_path).expanduser().resolve()
    output_file = Path(output_path).expanduser().resolve()
    if not input_file.exists():
        return f"Error: Input file not found: {input_path}"

    ok, duration, msg = _get_duration_seconds(input_file)
    if not ok or duration is None:
        return f"Error: {msg}"

    noise = f"{float(threshold_db)}dB"
    d = max(0.0, float(min_silence_duration))
    sd_args = ["-i", str(input_file), "-af", f"silencedetect=noise={noise}:d={d}", "-f", "null", "-"]
    ok, stderr = _run_ffmpeg_capture_stderr(sd_args, timeout=600)
    if not ok:
        return f"Error detecting silence: {stderr}"

    silences = _parse_silencedetect(stderr)
    try:
        segments = _invert_silence_to_segments(silences, duration=float(duration), padding_ms=padding_ms, max_segments=max_segments)
    except Exception as e:
        return f"Error computing segments: {e}"

    if not segments:
        return "No non-silent segments found (check threshold_db/min_silence_duration)."

    m = (mode or "auto").strip().lower()
    is_video = input_file.suffix.lower() in (".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v")
    if m == "auto":
        m = "video" if is_video else "audio"
    if m not in ("audio", "video"):
        return "Error: mode must be one of: audio, video, auto"

    with tempfile.TemporaryDirectory(prefix="strands_ffmpeg_trim_") as td:
        tmpdir = Path(td)
        parts: list[Path] = []

        for idx, (s, e) in enumerate(segments):
            part = tmpdir / f"part_{idx:04d}{output_file.suffix}"
            args = ["-ss", f"{s:.3f}", "-to", f"{e:.3f}", "-i", str(input_file)]
            if m == "video":
                if reencode:
                    args += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac", "-b:a", "192k"]
                else:
                    args += ["-c", "copy"]
            else:
                args += _audio_codec_args_for_output(output_file)
            args += [str(part)]
            success, msg = _run_ffmpeg(args, timeout=1200)
            if not success:
                return f"Error cutting segment {idx}: {msg}"
            parts.append(part)

        list_file = tmpdir / "concat.txt"
        with list_file.open("w", encoding="utf-8") as f:
            for p in parts:
                f.write(f"file '{p.as_posix()}'\n")

        concat_args = ["-f", "concat", "-safe", "0", "-i", str(list_file)]
        if m == "video":
            concat_args += ["-c", "copy"]
        else:
            concat_args += _audio_codec_args_for_output(output_file)
        concat_args += [str(output_file)]

        success, msg = _run_ffmpeg(concat_args, timeout=1200)
        if success:
            return f"Dead space removed successfully: {output_file}"
        return f"Error concatenating trimmed segments: {msg}"

def _parse_timestamp(ts: str) -> str:
    """Validate and return timestamp in HH:MM:SS or HH:MM:SS.mmm format."""
    ts = ts.strip()
    parts = ts.split(":")
    if len(parts) == 1:
        # Just seconds
        return f"00:00:{float(parts[0]):06.3f}"
    elif len(parts) == 2:
        # MM:SS
        return f"00:{int(parts[0]):02d}:{float(parts[1]):06.3f}"
    elif len(parts) == 3:
        # HH:MM:SS
        return f"{int(parts[0]):02d}:{int(parts[1]):02d}:{float(parts[2]):06.3f}"
    return ts


def _cut_video(
    input_path: str,
    output_path: str,
    start_time: str,
    end_time: str | None = None,
    duration: str | None = None,
) -> str:
    """Cut/trim a segment from a video file."""
    if not _check_ffmpeg():
        return "Error: ffmpeg is not installed. Install it with: brew install ffmpeg (macOS) or apt install ffmpeg (Linux)"

    input_file = Path(input_path).expanduser().resolve()
    output_file = Path(output_path).expanduser().resolve()

    if not input_file.exists():
        return f"Error: Input file not found: {input_path}"

    if end_time is None and duration is None:
        return "Error: Must provide either end_time or duration"

    if end_time is not None and duration is not None:
        return "Error: Provide either end_time or duration, not both"

    # Build ffmpeg command
    # Place -ss before -i for input seeking (faster and works with -c copy)
    args = ["-ss", _parse_timestamp(start_time), "-i", str(input_file)]

    if end_time:
        args.extend(["-to", _parse_timestamp(end_time)])
    else:
        args.extend(["-t", _parse_timestamp(duration)])

    # Copy codecs for speed (no re-encoding)
    args.extend(["-c", "copy", "-avoid_negative_ts", "make_zero", str(output_file)])

    success, msg = _run_ffmpeg(args)
    if success:
        return f"Video cut successfully: {output_file}"
    return f"Error cutting video: {msg}"


def _concat_videos(
    input_paths: list[str],
    output_path: str,
    reencode: bool = False,
) -> str:
    """Concatenate multiple video clips into a single video."""
    if not _check_ffmpeg():
        return "Error: ffmpeg is not installed. Install it with: brew install ffmpeg (macOS) or apt install ffmpeg (Linux)"

    if len(input_paths) < 2:
        return "Error: Need at least 2 videos to concatenate"

    # Resolve all input paths
    resolved_inputs = []
    for p in input_paths:
        input_file = Path(p).expanduser().resolve()
        if not input_file.exists():
            return f"Error: Input file not found: {p}"
        resolved_inputs.append(input_file)

    output_file = Path(output_path).expanduser().resolve()

    if reencode:
        # Use filter_complex for re-encoding (handles different formats)
        filter_inputs = "".join(f"[{i}:v][{i}:a]" for i in range(len(resolved_inputs)))
        filter_complex = f"{filter_inputs}concat=n={len(resolved_inputs)}:v=1:a=1[outv][outa]"

        args = []
        for f in resolved_inputs:
            args.extend(["-i", str(f)])
        args.extend([
            "-filter_complex", filter_complex,
            "-map", "[outv]", "-map", "[outa]",
            str(output_file)
        ])
    else:
        # Use concat demuxer (fast, no re-encoding)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            for input_file in resolved_inputs:
                f.write(f"file '{input_file}'\n")
            concat_list = f.name

        args = [
            "-f", "concat", "-safe", "0",
            "-i", concat_list,
            "-c", "copy",
            str(output_file)
        ]

    success, msg = _run_ffmpeg(args, timeout=600)
    if success:
        return f"Videos concatenated successfully: {output_file}"
    return f"Error concatenating videos: {msg}"


def _get_video_info(input_path: str) -> str:
    """Get information about a video file."""
    if not _check_ffprobe():
        return "Error: ffprobe is not installed. Install ffmpeg which includes ffprobe."

    input_file = Path(input_path).expanduser().resolve()
    if not input_file.exists():
        return f"Error: File not found: {input_path}"

    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format", "-show_streams",
                str(input_file)
            ],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return f"Error: {result.stderr}"

        data = json.loads(result.stdout)

        # Extract key info
        fmt = data.get("format", {})
        duration = float(fmt.get("duration", 0))
        size_mb = int(fmt.get("size", 0)) / (1024 * 1024)

        video_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
        audio_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), None)

        info = [
            f"File: {input_file.name}",
            f"Duration: {int(duration // 60)}:{int(duration % 60):02d} ({duration:.2f}s)",
            f"Size: {size_mb:.2f} MB",
        ]

        if video_stream:
            fps_str = video_stream.get('r_frame_rate', '0/1')
            try:
                num, den = fps_str.split('/')
                fps = float(num) / float(den) if float(den) != 0 else 0
            except (ValueError, ZeroDivisionError):
                fps = 0
            info.append(f"Video: {video_stream.get('codec_name', 'unknown')} "
                       f"{video_stream.get('width', '?')}x{video_stream.get('height', '?')} "
                       f"@ {fps:.2f} fps")

        if audio_stream:
            info.append(f"Audio: {audio_stream.get('codec_name', 'unknown')} "
                       f"{audio_stream.get('sample_rate', '?')} Hz "
                       f"{audio_stream.get('channels', '?')} channels")

        return "\n".join(info)

    except Exception as e:
        return f"Error getting video info: {e}"


def _extract_audio(
    input_path: str,
    output_path: str,
    format: str = "mp3",
) -> str:
    """Extract audio track from a video file."""
    if not _check_ffmpeg():
        return "Error: ffmpeg is not installed."

    input_file = Path(input_path).expanduser().resolve()
    output_file = Path(output_path).expanduser().resolve()

    if not input_file.exists():
        return f"Error: Input file not found: {input_path}"

    codec_map = {
        "mp3": "libmp3lame",
        "aac": "aac",
        "wav": "pcm_s16le",
        "flac": "flac",
    }

    codec = codec_map.get(format.lower(), "libmp3lame")

    args = [
        "-i", str(input_file),
        "-vn",  # No video
        "-acodec", codec,
        str(output_file)
    ]

    success, msg = _run_ffmpeg(args)
    if success:
        return f"Audio extracted successfully: {output_file}"
    return f"Error extracting audio: {msg}"


def _resize_video(
    input_path: str,
    output_path: str,
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> str:
    """Resize/scale a video to a target width/height (keeping aspect ratio when one dim is omitted)."""
    if not _check_ffmpeg():
        return "Error: ffmpeg is not installed."

    if width is None and height is None:
        return "Error: Must provide width and/or height for resize"

    input_file = Path(input_path).expanduser().resolve()
    output_file = Path(output_path).expanduser().resolve()
    if not input_file.exists():
        return f"Error: Input file not found: {input_path}"

    w = str(width) if width is not None else "-2"
    h = str(height) if height is not None else "-2"

    args = [
        "-i",
        str(input_file),
        "-vf",
        f"scale={w}:{h}",
        "-c:a",
        "copy",
        str(output_file),
    ]
    success, msg = _run_ffmpeg(args, timeout=600)
    if success:
        return f"Video resized successfully: {output_file}"
    return f"Error resizing video: {msg}"


def _convert_video(
    input_path: str,
    output_path: str,
    video_codec: Optional[str] = None,
    audio_codec: Optional[str] = None,
) -> str:
    """Convert a video to another container/format, optionally specifying codecs."""
    if not _check_ffmpeg():
        return "Error: ffmpeg is not installed."

    input_file = Path(input_path).expanduser().resolve()
    output_file = Path(output_path).expanduser().resolve()
    if not input_file.exists():
        return f"Error: Input file not found: {input_path}"

    args = ["-i", str(input_file)]
    if video_codec:
        args += ["-c:v", video_codec]
    if audio_codec:
        args += ["-c:a", audio_codec]
    args += [str(output_file)]

    success, msg = _run_ffmpeg(args, timeout=600)
    if success:
        return f"Video converted successfully: {output_file}"
    return f"Error converting video: {msg}"


def _compress_video(
    input_path: str,
    output_path: str,
    crf: int = 23,
    preset: str = "medium",
    video_codec: str = "libx264",
    audio_codec: str = "aac",
    audio_bitrate: str = "128k",
) -> str:
    """Compress/re-encode a video using CRF quality (lower CRF = higher quality/bigger files)."""
    if not _check_ffmpeg():
        return "Error: ffmpeg is not installed."

    input_file = Path(input_path).expanduser().resolve()
    output_file = Path(output_path).expanduser().resolve()
    if not input_file.exists():
        return f"Error: Input file not found: {input_path}"

    if crf < 0 or crf > 51:
        return "Error: crf must be between 0 and 51"

    args = [
        "-i",
        str(input_file),
        "-c:v",
        video_codec,
        "-crf",
        str(crf),
        "-preset",
        preset,
        "-c:a",
        audio_codec,
        "-b:a",
        audio_bitrate,
        str(output_file),
    ]
    success, msg = _run_ffmpeg(args, timeout=1200)
    if success:
        return f"Video compressed successfully: {output_file}"
    return f"Error compressing video: {msg}"


def _add_audio(
    input_path: str,
    audio_path: str,
    output_path: str,
    replace_audio: bool = True,
    audio_codec: str = "aac",
) -> str:
    """Add or replace an audio track in a video."""
    if not _check_ffmpeg():
        return "Error: ffmpeg is not installed."

    input_file = Path(input_path).expanduser().resolve()
    audio_file = Path(audio_path).expanduser().resolve()
    output_file = Path(output_path).expanduser().resolve()
    if not input_file.exists():
        return f"Error: Input file not found: {input_path}"
    if not audio_file.exists():
        return f"Error: Audio file not found: {audio_path}"

    # Map video from input 0 and audio from input 1. Use -shortest to stop when the shorter stream ends.
    args = [
        "-i",
        str(input_file),
        "-i",
        str(audio_file),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "copy",
        "-c:a",
        audio_codec,
        "-shortest",
    ]
    if not replace_audio:
        # If not replacing, keep original audio too (optional)
        args = [
            "-i",
            str(input_file),
            "-i",
            str(audio_file),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            audio_codec,
            "-shortest",
        ]
    args.append(str(output_file))

    success, msg = _run_ffmpeg(args, timeout=1200)
    if success:
        return f"Audio added successfully: {output_file}"
    return f"Error adding audio: {msg}"


def _extract_frames(
    input_path: str,
    output_dir: str,
    fps: Optional[int] = None,
    image_format: str = "png",
    pattern: str = "frame_%06d",
) -> str:
    """Extract frames from a video as images."""
    if not _check_ffmpeg():
        return "Error: ffmpeg is not installed."

    input_file = Path(input_path).expanduser().resolve()
    out_dir = Path(output_dir).expanduser().resolve()
    if not input_file.exists():
        return f"Error: Input file not found: {input_path}"
    out_dir.mkdir(parents=True, exist_ok=True)

    if fps is not None and (fps < 1 or fps > 120):
        return "Error: fps must be between 1 and 120"

    output_pattern = out_dir / f"{pattern}.{image_format}"
    args = ["-i", str(input_file)]
    if fps is not None:
        args += ["-vf", f"fps={fps}"]
    args += [str(output_pattern)]

    success, msg = _run_ffmpeg(args, timeout=1200)
    if success:
        return f"Frames extracted successfully: {out_dir}"
    return f"Error extracting frames: {msg}"


def _create_gif(
    input_path: str,
    output_path: str,
    fps: int = 12,
    width: Optional[int] = 480,
) -> str:
    """Create an animated GIF from a video (two-pass palette for quality)."""
    if not _check_ffmpeg():
        return "Error: ffmpeg is not installed."

    input_file = Path(input_path).expanduser().resolve()
    output_file = Path(output_path).expanduser().resolve()
    if not input_file.exists():
        return f"Error: Input file not found: {input_path}"

    if fps < 1 or fps > 60:
        return "Error: fps must be between 1 and 60"

    scale = f"scale={width}:-1:flags=lanczos" if width else "scale=iw:ih"
    vf = f"fps={fps},{scale}"

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        palette_path = Path(tmp.name)

    try:
        # Pass 1: generate palette
        success, msg = _run_ffmpeg(
            [
                "-i",
                str(input_file),
                "-vf",
                f"{vf},palettegen",
                str(palette_path),
            ],
            timeout=1200,
        )
        if not success:
            return f"Error creating GIF palette: {msg}"

        # Pass 2: use palette
        success, msg = _run_ffmpeg(
            [
                "-i",
                str(input_file),
                "-i",
                str(palette_path),
                "-lavfi",
                f"{vf}[x];[x][1:v]paletteuse",
                str(output_file),
            ],
            timeout=1200,
        )
        if success:
            return f"GIF created successfully: {output_file}"
        return f"Error creating GIF: {msg}"
    finally:
        palette_path.unlink(missing_ok=True)


def _thumbnail(
    input_path: str,
    output_path: str,
    timestamp: str = "1",
) -> str:
    """Generate a thumbnail image from a video at a given timestamp."""
    if not _check_ffmpeg():
        return "Error: ffmpeg is not installed."

    input_file = Path(input_path).expanduser().resolve()
    output_file = Path(output_path).expanduser().resolve()
    if not input_file.exists():
        return f"Error: Input file not found: {input_path}"

    args = [
        "-ss",
        _parse_timestamp(timestamp),
        "-i",
        str(input_file),
        "-frames:v",
        "1",
        "-q:v",
        "2",
        str(output_file),
    ]
    success, msg = _run_ffmpeg(args, timeout=600)
    if success:
        return f"Thumbnail created successfully: {output_file}"
    return f"Error creating thumbnail: {msg}"


def _rotate(
    input_path: str,
    output_path: str,
    degrees: int,
) -> str:
    """Rotate a video by 90/180/270 degrees."""
    if not _check_ffmpeg():
        return "Error: ffmpeg is not installed."

    if degrees not in (90, 180, 270):
        return "Error: degrees must be one of 90, 180, 270"

    input_file = Path(input_path).expanduser().resolve()
    output_file = Path(output_path).expanduser().resolve()
    if not input_file.exists():
        return f"Error: Input file not found: {input_path}"

    if degrees == 90:
        vf = "transpose=1"
    elif degrees == 270:
        vf = "transpose=2"
    else:
        vf = "transpose=1,transpose=1"

    args = ["-i", str(input_file), "-vf", vf, "-c:a", "copy", str(output_file)]
    success, msg = _run_ffmpeg(args, timeout=1200)
    if success:
        return f"Video rotated successfully: {output_file}"
    return f"Error rotating video: {msg}"


def _atempo_filter(speed_factor: float) -> str:
    """Build an atempo filter chain for arbitrary speed factors (ffmpeg supports 0.5-2.0 per filter)."""
    if speed_factor <= 0:
        return "atempo=1.0"
    factors: list[float] = []
    remaining = speed_factor
    while remaining > 2.0:
        factors.append(2.0)
        remaining /= 2.0
    while remaining < 0.5:
        factors.append(0.5)
        remaining /= 0.5
    factors.append(remaining)
    return ",".join([f"atempo={f:.5f}" for f in factors])


def _speed(
    input_path: str,
    output_path: str,
    speed_factor: float,
) -> str:
    """Change playback speed (affects video PTS and audio tempo)."""
    if not _check_ffmpeg():
        return "Error: ffmpeg is not installed."

    if speed_factor <= 0:
        return "Error: speed_factor must be > 0"

    input_file = Path(input_path).expanduser().resolve()
    output_file = Path(output_path).expanduser().resolve()
    if not input_file.exists():
        return f"Error: Input file not found: {input_path}"

    # setpts speeds video by factor; atempo speeds audio by factor. Use optional audio map.
    atempo = _atempo_filter(speed_factor)
    args = [
        "-i",
        str(input_file),
        "-filter_complex",
        f"[0:v]setpts=PTS/{speed_factor}[v];[0:a]{atempo}[a]",
        "-map",
        "[v]",
        "-map",
        "[a]?",
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        str(output_file),
    ]
    success, msg = _run_ffmpeg(args, timeout=1200)
    if success:
        return f"Speed changed successfully: {output_file}"
    return f"Error changing speed: {msg}"


def _watermark(
    input_path: str,
    output_path: str,
    watermark_image: Optional[str] = None,
    watermark_text: Optional[str] = None,
    position: str = "top-right",
    opacity: float = 0.7,
) -> str:
    """Add an image or text watermark overlay."""
    if not _check_ffmpeg():
        return "Error: ffmpeg is not installed."

    input_file = Path(input_path).expanduser().resolve()
    output_file = Path(output_path).expanduser().resolve()
    if not input_file.exists():
        return f"Error: Input file not found: {input_path}"

    if watermark_image is None and watermark_text is None:
        return "Error: Must provide watermark_image or watermark_text"

    if opacity < 0 or opacity > 1:
        return "Error: opacity must be between 0.0 and 1.0"

    pos_map = {
        "top-left": ("10", "10"),
        "top-right": ("W-w-10", "10"),
        "bottom-left": ("10", "H-h-10"),
        "bottom-right": ("W-w-10", "H-h-10"),
        "center": ("(W-w)/2", "(H-h)/2"),
    }
    x, y = pos_map.get(position, pos_map["top-right"])

    if watermark_image:
        wm_file = Path(watermark_image).expanduser().resolve()
        if not wm_file.exists():
            return f"Error: Watermark image not found: {watermark_image}"
        args = [
            "-i",
            str(input_file),
            "-i",
            str(wm_file),
            "-filter_complex",
            f"[1:v]format=rgba,colorchannelmixer=aa={opacity}[wm];[0:v][wm]overlay={x}:{y}",
            "-c:a",
            "copy",
            str(output_file),
        ]
        success, msg = _run_ffmpeg(args, timeout=1200)
        if success:
            return f"Watermark applied successfully: {output_file}"
        return f"Error applying watermark: {msg}"

    # Text watermark (best-effort; relies on ffmpeg drawtext + system fonts)
    safe_text = (watermark_text or "").replace(":", r"\:")
    args = [
        "-i",
        str(input_file),
        "-vf",
        f"drawtext=text='{safe_text}':x={x}:y={y}:fontsize=24:fontcolor=white@{opacity}",
        "-c:a",
        "copy",
        str(output_file),
    ]
    success, msg = _run_ffmpeg(args, timeout=1200)
    if success:
        return f"Watermark applied successfully: {output_file}"
    return f"Error applying watermark: {msg}"


@tool
def ffmpeg(
    action: Literal[
        "cut",
        "concat",
        "info",
        "extract_audio",
        "resize",
        "convert",
        "compress",
        "add_audio",
        "extract_frames",
        "create_gif",
        "thumbnail",
        "rotate",
        "speed",
        "watermark",
        "remove_dead_space",
    ],
    input_path: str | None = None,
    output_path: str | None = None,
    input_paths: list[str] | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    duration: str | None = None,
    reencode: bool = False,
    format: str = "mp3",
    # New action params
    width: int | None = None,
    height: int | None = None,
    video_codec: str | None = None,
    audio_codec: str | None = None,
    crf: int = 23,
    preset: str = "medium",
    audio_path: str | None = None,
    replace_audio: bool = True,
    fps: int | None = None,
    image_format: str = "png",
    pattern: str = "frame_%06d",
    timestamp: str = "1",
    degrees: int | None = None,
    speed_factor: float | None = None,
    watermark_image: str | None = None,
    watermark_text: str | None = None,
    position: str = "top-right",
    opacity: float = 0.7,
    threshold_db: float = -45.0,
    min_silence_duration: float = 0.35,
    padding_ms: int = 120,
    mode: str = "auto",
    max_segments: int = 200,
) -> str:
    """
    Perform video processing operations using FFmpeg.

    Args:
        action: The operation to perform. One of:
            - "cut": Cut/trim a segment from a video.
            - "concat": Concatenate multiple videos.
            - "info": Get video metadata.
            - "extract_audio": Extract audio track from video.
        input_path: Path to the input video file (for cut, info, extract_audio).
        output_path: Path for the output file (for cut, concat, extract_audio).
        input_paths: List of video paths to concatenate (for concat action).
        start_time: Start timestamp for cutting (e.g., "00:01:30" or "90").
        end_time: End timestamp for cutting. Provide end_time OR duration, not both.
        duration: Duration to cut in seconds or timestamp format. Provide end_time OR duration, not both.
        reencode: Whether to re-encode when concatenating (default False, uses stream copy).
        format: Audio format for extraction (mp3/wav/aac/flac, default mp3).
        width/height: Resize target dimensions (resize action).
        video_codec/audio_codec: Optional codec overrides (convert/compress/add_audio).
        crf/preset: Compression settings (compress action).
        audio_path/replace_audio: Add/replace audio track (add_audio action).
        fps/image_format/pattern: Frame extraction / GIF creation controls.
        timestamp: Thumbnail timestamp (seconds or HH:MM:SS[.mmm]).
        degrees: Rotation degrees (90/180/270).
        speed_factor: Playback speed multiplier (e.g., 0.5 or 2.0).
        watermark_image/watermark_text/position/opacity: Watermark controls.
        threshold_db: Silence threshold in dB for remove_dead_space (default -45).
        min_silence_duration: Minimum silence duration in seconds (default 0.35).
        padding_ms: Padding added around non-silent segments (default 120ms).
        mode: "audio", "video", or "auto" (default auto).
        max_segments: Safety cap on segments (default 200).

    Returns:
        Result message or video information string.

    Examples:
        >>> ffmpeg(action="cut", input_path="video.mp4", output_path="clip.mp4", start_time="00:01:30", duration="60")
        >>> ffmpeg(action="concat", input_paths=["clip1.mp4", "clip2.mp4"], output_path="final.mp4")
        >>> ffmpeg(action="info", input_path="video.mp4")
        >>> ffmpeg(action="extract_audio", input_path="video.mp4", output_path="audio.mp3", format="mp3")
        >>> ffmpeg(action="compress", input_path="video.mp4", output_path="small.mp4", crf=28)
        >>> ffmpeg(action="thumbnail", input_path="video.mp4", output_path="thumb.jpg", timestamp="3.5")
    """
    if action == "cut":
        if not input_path:
            return "Error: 'input_path' is required for action 'cut'"
        if not output_path:
            return "Error: 'output_path' is required for action 'cut'"
        if not start_time:
            return "Error: 'start_time' is required for action 'cut'"
        return _cut_video(
            input_path=input_path,
            output_path=output_path,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
        )

    elif action == "concat":
        if input_paths is None:
            return "Error: 'input_paths' is required for action 'concat'"
        if not output_path:
            return "Error: 'output_path' is required for action 'concat'"
        return _concat_videos(
            input_paths=input_paths,
            output_path=output_path,
            reencode=reencode,
        )

    elif action == "info":
        if not input_path:
            return "Error: 'input_path' is required for action 'info'"
        return _get_video_info(input_path=input_path)

    elif action == "extract_audio":
        if not input_path:
            return "Error: 'input_path' is required for action 'extract_audio'"
        if not output_path:
            return "Error: 'output_path' is required for action 'extract_audio'"
        return _extract_audio(
            input_path=input_path,
            output_path=output_path,
            format=format,
        )

    elif action == "resize":
        if not input_path:
            return "Error: 'input_path' is required for action 'resize'"
        if not output_path:
            return "Error: 'output_path' is required for action 'resize'"
        return _resize_video(input_path=input_path, output_path=output_path, width=width, height=height)

    elif action == "convert":
        if not input_path:
            return "Error: 'input_path' is required for action 'convert'"
        if not output_path:
            return "Error: 'output_path' is required for action 'convert'"
        return _convert_video(
            input_path=input_path,
            output_path=output_path,
            video_codec=video_codec,
            audio_codec=audio_codec,
        )

    elif action == "compress":
        if not input_path:
            return "Error: 'input_path' is required for action 'compress'"
        if not output_path:
            return "Error: 'output_path' is required for action 'compress'"
        return _compress_video(
            input_path=input_path,
            output_path=output_path,
            crf=crf,
            preset=preset,
            video_codec=video_codec or "libx264",
            audio_codec=audio_codec or "aac",
        )

    elif action == "add_audio":
        if not input_path:
            return "Error: 'input_path' is required for action 'add_audio'"
        if not audio_path:
            return "Error: 'audio_path' is required for action 'add_audio'"
        if not output_path:
            return "Error: 'output_path' is required for action 'add_audio'"
        return _add_audio(
            input_path=input_path,
            audio_path=audio_path,
            output_path=output_path,
            replace_audio=replace_audio,
            audio_codec=audio_codec or "aac",
        )

    elif action == "extract_frames":
        if not input_path:
            return "Error: 'input_path' is required for action 'extract_frames'"
        # output_path is treated as a directory here for backward-compat
        out_dir = output_path or ""
        if not out_dir:
            return "Error: 'output_path' (directory) is required for action 'extract_frames'"
        return _extract_frames(
            input_path=input_path,
            output_dir=out_dir,
            fps=fps,
            image_format=image_format,
            pattern=pattern,
        )

    elif action == "create_gif":
        if not input_path:
            return "Error: 'input_path' is required for action 'create_gif'"
        if not output_path:
            return "Error: 'output_path' is required for action 'create_gif'"
        return _create_gif(
            input_path=input_path,
            output_path=output_path,
            fps=fps or 12,
            width=width if width is not None else 480,
        )

    elif action == "thumbnail":
        if not input_path:
            return "Error: 'input_path' is required for action 'thumbnail'"
        if not output_path:
            return "Error: 'output_path' is required for action 'thumbnail'"
        return _thumbnail(input_path=input_path, output_path=output_path, timestamp=timestamp)

    elif action == "rotate":
        if not input_path:
            return "Error: 'input_path' is required for action 'rotate'"
        if not output_path:
            return "Error: 'output_path' is required for action 'rotate'"
        if degrees is None:
            return "Error: 'degrees' is required for action 'rotate'"
        return _rotate(input_path=input_path, output_path=output_path, degrees=degrees)

    elif action == "speed":
        if not input_path:
            return "Error: 'input_path' is required for action 'speed'"
        if not output_path:
            return "Error: 'output_path' is required for action 'speed'"
        if speed_factor is None:
            return "Error: 'speed_factor' is required for action 'speed'"
        return _speed(input_path=input_path, output_path=output_path, speed_factor=speed_factor)

    elif action == "watermark":
        if not input_path:
            return "Error: 'input_path' is required for action 'watermark'"
        if not output_path:
            return "Error: 'output_path' is required for action 'watermark'"
        return _watermark(
            input_path=input_path,
            output_path=output_path,
            watermark_image=watermark_image,
            watermark_text=watermark_text,
            position=position,
            opacity=opacity,
        )

    elif action == "remove_dead_space":
        if not input_path:
            return "Error: 'input_path' is required for action 'remove_dead_space'"
        if not output_path:
            return "Error: 'output_path' is required for action 'remove_dead_space'"
        return _remove_dead_space(
            input_path=input_path,
            output_path=output_path,
            threshold_db=threshold_db,
            min_silence_duration=min_silence_duration,
            padding_ms=padding_ms,
            mode=mode,
            reencode=reencode,
            max_segments=max_segments,
        )

    else:
        return (
            f"Error: Unknown action '{action}'. Valid actions: "
            "cut, concat, info, extract_audio, resize, convert, compress, add_audio, extract_frames, "
            "create_gif, thumbnail, rotate, speed, watermark, remove_dead_space"
        )
