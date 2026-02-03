"""
Audio Tool

Manipulate audio files using pydub.

Requires:
    pip install strands-pack[audio]
    FFmpeg must be installed on the system for non-WAV formats

Supported actions
-----------------
- get_info: Get audio file information
- convert: Convert audio to a different format
- trim: Trim audio to a specific time range
- concat: Concatenate multiple audio files
- adjust_volume: Adjust audio volume by dB
- normalize: Normalize audio volume to 0 dBFS
- fade: Apply fade in/out effects
- split: Split audio into segments
- overlay: Overlay one audio file on top of another
- extract_segment: Extract a segment of specified duration

Notes:
  - FFmpeg must be installed for non-WAV formats (mp3, ogg, flac, etc.)
  - All time values are in milliseconds
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from strands import tool

# Lazy import for pydub
_pydub = None


def _get_pydub():
    global _pydub
    if _pydub is None:
        try:
            from pydub import AudioSegment
            _pydub = AudioSegment
        except ImportError:
            raise ImportError("pydub not installed. Run: pip install strands-pack[audio]") from None
    return _pydub


def _ok(**data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": True}
    out.update(data)
    return out


def _err(message: str, *, error_type: Optional[str] = None, **data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": False, "error": message}
    if error_type:
        out["error_type"] = error_type
    out.update(data)
    return out


def _load_audio(input_path: str):
    """Load audio from file, auto-detecting format."""
    AudioSegment = _get_pydub()
    path = Path(input_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {input_path}")

    # Try to determine format from extension
    ext = path.suffix.lower().lstrip(".")
    if ext in ("mp3", "wav", "ogg", "flac", "m4a", "aac", "wma"):
        return AudioSegment.from_file(str(path), format=ext)
    else:
        # Let pydub/ffmpeg figure it out
        return AudioSegment.from_file(str(path))


def _save_audio(audio, output_path: str, format: Optional[str] = None,
                bitrate: Optional[str] = None):
    """Save audio to file."""
    path = Path(output_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)

    # Determine format from extension if not specified
    if not format:
        format = path.suffix.lower().lstrip(".") or "mp3"

    export_params = {}
    if bitrate:
        export_params["bitrate"] = bitrate

    audio.export(str(path), format=format, **export_params)
    return str(path)


@tool
def audio(
    action: str,
    # get_info, convert, trim, adjust_volume, normalize, fade, split, overlay, extract_segment
    input_path: Optional[str] = None,
    # convert, trim, adjust_volume, normalize, fade, overlay, extract_segment
    output_path: Optional[str] = None,
    # convert
    format: Optional[str] = None,
    bitrate: Optional[str] = None,
    # trim
    start_ms: Optional[int] = None,
    end_ms: Optional[int] = None,
    # concat
    input_paths: Optional[List[str]] = None,
    crossfade_ms: Optional[int] = None,
    # adjust_volume
    db: Optional[float] = None,
    # fade
    fade_in_ms: Optional[int] = None,
    fade_out_ms: Optional[int] = None,
    # split
    output_dir: Optional[str] = None,
    segment_ms: Optional[int] = None,
    # overlay
    overlay_path: Optional[str] = None,
    position_ms: int = 0,
    volume_db: Optional[float] = None,
    # extract_segment
    duration_ms: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Manipulate audio files using pydub.

    Args:
        action: The action to perform. One of:
            - "get_info": Get audio file information
            - "convert": Convert audio to a different format
            - "trim": Trim audio to a specific time range
            - "concat": Concatenate multiple audio files
            - "adjust_volume": Adjust audio volume by dB
            - "normalize": Normalize audio volume to 0 dBFS
            - "fade": Apply fade in/out effects
            - "split": Split audio into segments
            - "overlay": Overlay one audio file on top of another
            - "extract_segment": Extract a segment of specified duration
        input_path: Path to input audio file (required for most actions)
        output_path: Path to save output audio file (required for convert, trim, etc.)
        format: Output format for convert (e.g., "mp3", "wav", "ogg")
        bitrate: Output bitrate for convert (e.g., "192k", "320k")
        start_ms: Start time in milliseconds (for trim, extract_segment)
        end_ms: End time in milliseconds (for trim)
        input_paths: List of audio file paths to concatenate (for concat)
        crossfade_ms: Crossfade duration in milliseconds (for concat)
        db: Volume adjustment in decibels, positive or negative (for adjust_volume)
        fade_in_ms: Fade in duration in milliseconds (for fade)
        fade_out_ms: Fade out duration in milliseconds (for fade)
        output_dir: Output directory for split segments (for split)
        segment_ms: Segment duration in milliseconds (for split)
        overlay_path: Path to overlay audio file (for overlay)
        position_ms: Position to start overlay in milliseconds (for overlay, default 0)
        volume_db: Volume adjustment for overlay in dB (for overlay)
        duration_ms: Duration in milliseconds (for extract_segment)

    Returns:
        dict with success status and action-specific data

    Examples:
        # Get audio info
        audio(action="get_info", input_path="song.mp3")

        # Convert to WAV
        audio(action="convert", input_path="song.mp3", output_path="song.wav")

        # Trim first 30 seconds
        audio(action="trim", input_path="song.mp3", output_path="intro.mp3", start_ms=0, end_ms=30000)

        # Concatenate files
        audio(action="concat", input_paths=["part1.mp3", "part2.mp3"], output_path="full.mp3")

        # Increase volume by 3dB
        audio(action="adjust_volume", input_path="quiet.mp3", output_path="louder.mp3", db=3)

        # Normalize volume
        audio(action="normalize", input_path="song.mp3", output_path="normalized.mp3")

        # Add fade in/out
        audio(action="fade", input_path="song.mp3", output_path="faded.mp3", fade_in_ms=2000, fade_out_ms=3000)

        # Split into 30-second segments
        audio(action="split", input_path="podcast.mp3", output_dir="segments/", segment_ms=30000)

        # Overlay background music
        audio(action="overlay", input_path="speech.mp3", overlay_path="music.mp3", output_path="mixed.mp3", volume_db=-10)

        # Extract 10-second segment starting at 1 minute
        audio(action="extract_segment", input_path="song.mp3", output_path="clip.mp3", start_ms=60000, duration_ms=10000)

    Note:
        FFmpeg must be installed for non-WAV formats.
    """
    valid_actions = [
        "get_info",
        "convert",
        "trim",
        "concat",
        "adjust_volume",
        "normalize",
        "fade",
        "split",
        "overlay",
        "extract_segment",
    ]

    action = (action or "").strip().lower()

    if action not in valid_actions:
        return _err(
            f"Unknown action: {action}",
            error_type="InvalidAction",
            available_actions=valid_actions,
        )

    try:
        # get_info
        if action == "get_info":
            if not input_path:
                return _err("input_path is required for get_info")
            try:
                audio_seg = _load_audio(input_path)
            except FileNotFoundError as e:
                return _err(str(e), error_type="FileNotFoundError")
            return _ok(
                action="get_info",
                input_path=input_path,
                duration_ms=len(audio_seg),
                duration_seconds=len(audio_seg) / 1000.0,
                channels=audio_seg.channels,
                sample_width=audio_seg.sample_width,
                frame_rate=audio_seg.frame_rate,
                frame_width=audio_seg.frame_width,
                rms=audio_seg.rms,
                max_possible_amplitude=audio_seg.max_possible_amplitude,
                dBFS=round(audio_seg.dBFS, 2) if audio_seg.dBFS != float("-inf") else None,
            )

        # convert
        if action == "convert":
            if not input_path:
                return _err("input_path is required for convert")
            if not output_path:
                return _err("output_path is required for convert")
            try:
                audio_seg = _load_audio(input_path)
            except FileNotFoundError as e:
                return _err(str(e), error_type="FileNotFoundError")
            saved_path = _save_audio(audio_seg, output_path, format=format, bitrate=bitrate)
            return _ok(
                action="convert",
                input_path=input_path,
                output_path=saved_path,
                format=format or Path(output_path).suffix.lower().lstrip("."),
                bitrate=bitrate,
                duration_ms=len(audio_seg),
            )

        # trim
        if action == "trim":
            if not input_path:
                return _err("input_path is required for trim")
            if not output_path:
                return _err("output_path is required for trim")
            if start_ms is None:
                return _err("start_ms is required for trim")
            if end_ms is None:
                return _err("end_ms is required for trim")
            start_ms = int(start_ms)
            end_ms = int(end_ms)
            if start_ms < 0:
                return _err("start_ms must be non-negative")
            if end_ms <= start_ms:
                return _err("end_ms must be greater than start_ms")
            try:
                audio_seg = _load_audio(input_path)
            except FileNotFoundError as e:
                return _err(str(e), error_type="FileNotFoundError")
            if start_ms > len(audio_seg):
                return _err(f"start_ms ({start_ms}) exceeds audio duration ({len(audio_seg)}ms)")
            end_ms = min(end_ms, len(audio_seg))
            trimmed = audio_seg[start_ms:end_ms]
            saved_path = _save_audio(trimmed, output_path)
            return _ok(
                action="trim",
                input_path=input_path,
                output_path=saved_path,
                start_ms=start_ms,
                end_ms=end_ms,
                original_duration_ms=len(audio_seg),
                new_duration_ms=len(trimmed),
            )

        # concat
        if action == "concat":
            if not input_paths:
                return _err("input_paths is required for concat (list of file paths)")
            if not output_path:
                return _err("output_path is required for concat")
            if len(input_paths) < 2:
                return _err("At least 2 input files are required for concatenation")
            _get_pydub()
            try:
                audios = [_load_audio(p) for p in input_paths]
            except FileNotFoundError as e:
                return _err(str(e), error_type="FileNotFoundError")
            result = audios[0]
            for audio_seg in audios[1:]:
                if crossfade_ms and crossfade_ms > 0:
                    result = result.append(audio_seg, crossfade=crossfade_ms)
                else:
                    result = result + audio_seg
            saved_path = _save_audio(result, output_path)
            return _ok(
                action="concat",
                input_paths=input_paths,
                output_path=saved_path,
                crossfade_ms=crossfade_ms,
                input_count=len(input_paths),
                total_duration_ms=len(result),
            )

        # adjust_volume
        if action == "adjust_volume":
            if not input_path:
                return _err("input_path is required for adjust_volume")
            if not output_path:
                return _err("output_path is required for adjust_volume")
            if db is None:
                return _err("db is required for adjust_volume (positive to increase, negative to decrease)")
            db = float(db)
            try:
                audio_seg = _load_audio(input_path)
            except FileNotFoundError as e:
                return _err(str(e), error_type="FileNotFoundError")
            adjusted = audio_seg + db
            saved_path = _save_audio(adjusted, output_path)
            return _ok(
                action="adjust_volume",
                input_path=input_path,
                output_path=saved_path,
                db_change=db,
                original_dBFS=round(audio_seg.dBFS, 2) if audio_seg.dBFS != float("-inf") else None,
                new_dBFS=round(adjusted.dBFS, 2) if adjusted.dBFS != float("-inf") else None,
            )

        # normalize
        if action == "normalize":
            if not input_path:
                return _err("input_path is required for normalize")
            if not output_path:
                return _err("output_path is required for normalize")
            try:
                audio_seg = _load_audio(input_path)
            except FileNotFoundError as e:
                return _err(str(e), error_type="FileNotFoundError")
            from pydub.effects import normalize as pydub_normalize
            normalized = pydub_normalize(audio_seg)
            saved_path = _save_audio(normalized, output_path)
            return _ok(
                action="normalize",
                input_path=input_path,
                output_path=saved_path,
                original_dBFS=round(audio_seg.dBFS, 2) if audio_seg.dBFS != float("-inf") else None,
                normalized_dBFS=round(normalized.dBFS, 2) if normalized.dBFS != float("-inf") else None,
            )

        # fade
        if action == "fade":
            if not input_path:
                return _err("input_path is required for fade")
            if not output_path:
                return _err("output_path is required for fade")
            if not fade_in_ms and not fade_out_ms:
                return _err("At least one of fade_in_ms or fade_out_ms is required for fade")
            try:
                audio_seg = _load_audio(input_path)
            except FileNotFoundError as e:
                return _err(str(e), error_type="FileNotFoundError")
            result = audio_seg
            if fade_in_ms and fade_in_ms > 0:
                result = result.fade_in(int(fade_in_ms))
            if fade_out_ms and fade_out_ms > 0:
                result = result.fade_out(int(fade_out_ms))
            saved_path = _save_audio(result, output_path)
            return _ok(
                action="fade",
                input_path=input_path,
                output_path=saved_path,
                fade_in_ms=fade_in_ms,
                fade_out_ms=fade_out_ms,
                duration_ms=len(result),
            )

        # split
        if action == "split":
            if not input_path:
                return _err("input_path is required for split")
            if not output_dir:
                return _err("output_dir is required for split")
            if not segment_ms:
                return _err("segment_ms is required for split")
            segment_ms = int(segment_ms)
            if segment_ms <= 0:
                return _err("segment_ms must be positive")
            try:
                audio_seg = _load_audio(input_path)
            except FileNotFoundError as e:
                return _err(str(e), error_type="FileNotFoundError")
            out_dir = Path(output_dir).expanduser()
            out_dir.mkdir(parents=True, exist_ok=True)
            input_ext = Path(input_path).suffix or ".mp3"
            base_name = Path(input_path).stem
            segments = []
            segment_num = 0
            pos = 0
            while pos < len(audio_seg):
                segment = audio_seg[pos:pos + segment_ms]
                segment_path = out_dir / f"{base_name}_{segment_num:04d}{input_ext}"
                _save_audio(segment, str(segment_path))
                segments.append({
                    "path": str(segment_path),
                    "start_ms": pos,
                    "end_ms": min(pos + segment_ms, len(audio_seg)),
                    "duration_ms": len(segment),
                })
                pos += segment_ms
                segment_num += 1
            return _ok(
                action="split",
                input_path=input_path,
                output_dir=str(out_dir),
                segment_ms=segment_ms,
                original_duration_ms=len(audio_seg),
                segment_count=len(segments),
                segments=segments,
            )

        # overlay
        if action == "overlay":
            if not input_path:
                return _err("input_path is required for overlay")
            if not overlay_path:
                return _err("overlay_path is required for overlay")
            if not output_path:
                return _err("output_path is required for overlay")
            position_ms_val = int(position_ms or 0)
            try:
                base = _load_audio(input_path)
                overlay_audio = _load_audio(overlay_path)
            except FileNotFoundError as e:
                return _err(str(e), error_type="FileNotFoundError")
            if volume_db is not None:
                overlay_audio = overlay_audio + float(volume_db)
            result = base.overlay(overlay_audio, position=position_ms_val)
            saved_path = _save_audio(result, output_path)
            return _ok(
                action="overlay",
                input_path=input_path,
                overlay_path=overlay_path,
                output_path=saved_path,
                position_ms=position_ms_val,
                volume_db=volume_db,
                base_duration_ms=len(base),
                overlay_duration_ms=len(overlay_audio),
                result_duration_ms=len(result),
            )

        # extract_segment
        if action == "extract_segment":
            if not input_path:
                return _err("input_path is required for extract_segment")
            if not output_path:
                return _err("output_path is required for extract_segment")
            if start_ms is None:
                return _err("start_ms is required for extract_segment")
            if duration_ms is None:
                return _err("duration_ms is required for extract_segment")
            start_ms = int(start_ms)
            duration_ms = int(duration_ms)
            if start_ms < 0:
                return _err("start_ms must be non-negative")
            if duration_ms <= 0:
                return _err("duration_ms must be positive")
            try:
                audio_seg = _load_audio(input_path)
            except FileNotFoundError as e:
                return _err(str(e), error_type="FileNotFoundError")
            if start_ms > len(audio_seg):
                return _err(f"start_ms ({start_ms}) exceeds audio duration ({len(audio_seg)}ms)")
            end_ms = min(start_ms + duration_ms, len(audio_seg))
            segment = audio_seg[start_ms:end_ms]
            saved_path = _save_audio(segment, output_path)
            return _ok(
                action="extract_segment",
                input_path=input_path,
                output_path=saved_path,
                start_ms=start_ms,
                requested_duration_ms=duration_ms,
                actual_duration_ms=len(segment),
                original_duration_ms=len(audio_seg),
            )

    except ImportError as e:
        return _err(str(e), error_type="ImportError")
    except Exception as e:
        return _err(str(e), error_type=type(e).__name__, action=action)

    return _err(f"Unhandled action: {action}")
