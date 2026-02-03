"""Tests for FFmpeg tool."""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Import helper functions for testing
from strands_pack.ffmpeg import (
    _check_ffmpeg,
    _parse_timestamp,
    _parse_silencedetect,
    _run_ffmpeg,
)


class TestCheckFfmpeg:
    """Tests for ffmpeg availability check."""

    def test_check_ffmpeg_available(self):
        """Test that _check_ffmpeg returns True when ffmpeg is available."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/ffmpeg"
            assert _check_ffmpeg() is True
            mock_which.assert_called_once_with("ffmpeg")

    def test_check_ffmpeg_not_available(self):
        """Test that _check_ffmpeg returns False when ffmpeg is not installed."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None
            assert _check_ffmpeg() is False
            mock_which.assert_called_once_with("ffmpeg")


class TestParseTimestamp:
    """Tests for timestamp parsing."""

    def test_parse_seconds_only(self):
        """Test parsing seconds-only format."""
        result = _parse_timestamp("30")
        assert result == "00:00:30.000"

    def test_parse_seconds_with_decimals(self):
        """Test parsing seconds with decimal places."""
        result = _parse_timestamp("45.5")
        assert result == "00:00:45.500"

    def test_parse_minutes_seconds(self):
        """Test parsing MM:SS format."""
        result = _parse_timestamp("1:30")
        assert result == "00:01:30.000"

    def test_parse_minutes_seconds_with_decimals(self):
        """Test parsing MM:SS.mmm format."""
        result = _parse_timestamp("2:15.5")
        assert result == "00:02:15.500"

    def test_parse_hours_minutes_seconds(self):
        """Test parsing HH:MM:SS format."""
        result = _parse_timestamp("1:30:45")
        assert result == "01:30:45.000"

    def test_parse_full_format_with_decimals(self):
        """Test parsing HH:MM:SS.mmm format."""
        result = _parse_timestamp("2:15:30.5")
        assert result == "02:15:30.500"

    def test_parse_with_whitespace(self):
        """Test that whitespace is stripped."""
        result = _parse_timestamp("  30  ")
        assert result == "00:00:30.000"

    def test_parse_zero_values(self):
        """Test parsing zero values."""
        result = _parse_timestamp("0")
        assert result == "00:00:00.000"

    def test_parse_large_values(self):
        """Test parsing large hour values."""
        result = _parse_timestamp("10:30:45")
        assert result == "10:30:45.000"


class TestRunFfmpeg:
    """Tests for _run_ffmpeg helper function."""

    def test_run_ffmpeg_success(self):
        """Test successful ffmpeg execution."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            success, msg = _run_ffmpeg(["-version"])
            assert success is True
            assert msg == "Success"

    def test_run_ffmpeg_failure(self):
        """Test ffmpeg execution with non-zero return code."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1, stderr="Error: Invalid input"
            )
            success, msg = _run_ffmpeg(["-i", "nonexistent.mp4"])
            assert success is False
            assert "Invalid input" in msg

    def test_run_ffmpeg_timeout(self):
        """Test ffmpeg execution timeout."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="ffmpeg", timeout=10)
            success, msg = _run_ffmpeg(["-i", "video.mp4"], timeout=10)
            assert success is False
            assert "timed out" in msg

    def test_run_ffmpeg_exception(self):
        """Test ffmpeg execution with unexpected exception."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = Exception("Unexpected error")
            success, msg = _run_ffmpeg(["-i", "video.mp4"])
            assert success is False
            assert "Unexpected error" in msg


class TestSilenceDetectParsing:
    def test_parse_silencedetect_intervals(self):
        stderr = """
[silencedetect @ 0x0] silence_start: 0.023
[silencedetect @ 0x0] silence_end: 1.234 | silence_duration: 1.211
[silencedetect @ 0x0] silence_start: 5.000
"""
        intervals = _parse_silencedetect(stderr)
        assert intervals[0] == (0.023, 1.234)
        assert intervals[1] == (5.0, None)


class TestCutAction:
    """Tests for ffmpeg cut action."""

    def test_cut_ffmpeg_not_installed(self):
        """Test cut when ffmpeg is not installed."""
        from strands_pack import ffmpeg

        with patch("strands_pack.ffmpeg._check_ffmpeg") as mock_check:
            mock_check.return_value = False
            result = ffmpeg(
                action="cut",
                input_path="/tmp/video.mp4",
                output_path="/tmp/output.mp4",
                start_time="0",
                end_time="10",
            )
            assert "Error" in result
            assert "ffmpeg is not installed" in result

    def test_cut_input_not_found(self):
        """Test cut with non-existent input file."""
        from strands_pack import ffmpeg

        with patch("strands_pack.ffmpeg._check_ffmpeg") as mock_check:
            mock_check.return_value = True
            result = ffmpeg(
                action="cut",
                input_path="/nonexistent/video.mp4",
                output_path="/tmp/output.mp4",
                start_time="0",
                end_time="10",
            )
            assert "Error" in result
            assert "not found" in result

    def test_cut_missing_end_and_duration(self):
        """Test cut when neither end_time nor duration is provided."""
        from strands_pack import ffmpeg

        with patch("strands_pack.ffmpeg._check_ffmpeg") as mock_check:
            mock_check.return_value = True
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
                temp_file = f.name
            try:
                result = ffmpeg(
                    action="cut",
                    input_path=temp_file,
                    output_path="/tmp/output.mp4",
                    start_time="0",
                )
                assert "Error" in result
                assert "Must provide either end_time or duration" in result
            finally:
                Path(temp_file).unlink(missing_ok=True)

    def test_cut_both_end_and_duration(self):
        """Test cut when both end_time and duration are provided."""
        from strands_pack import ffmpeg

        with patch("strands_pack.ffmpeg._check_ffmpeg") as mock_check:
            mock_check.return_value = True
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
                temp_file = f.name
            try:
                result = ffmpeg(
                    action="cut",
                    input_path=temp_file,
                    output_path="/tmp/output.mp4",
                    start_time="0",
                    end_time="10",
                    duration="5",
                )
                assert "Error" in result
                assert "Provide either end_time or duration, not both" in result
            finally:
                Path(temp_file).unlink(missing_ok=True)

    def test_cut_success_with_end_time(self):
        """Test successful cut with end_time."""
        from strands_pack import ffmpeg

        with patch("strands_pack.ffmpeg._check_ffmpeg") as mock_check, patch(
            "strands_pack.ffmpeg._run_ffmpeg"
        ) as mock_run:
            mock_check.return_value = True
            mock_run.return_value = (True, "Success")
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
                temp_file = f.name
            try:
                result = ffmpeg(
                    action="cut",
                    input_path=temp_file,
                    output_path="/tmp/output.mp4",
                    start_time="0:30",
                    end_time="1:30",
                )
                assert "successfully" in result
                mock_run.assert_called_once()
                args = mock_run.call_args[0][0]
                assert "-i" in args
                assert "-ss" in args
                assert "-to" in args
                assert "-c" in args
                assert "copy" in args
            finally:
                Path(temp_file).unlink(missing_ok=True)

    def test_cut_success_with_duration(self):
        """Test successful cut with duration."""
        from strands_pack import ffmpeg

        with patch("strands_pack.ffmpeg._check_ffmpeg") as mock_check, patch(
            "strands_pack.ffmpeg._run_ffmpeg"
        ) as mock_run:
            mock_check.return_value = True
            mock_run.return_value = (True, "Success")
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
                temp_file = f.name
            try:
                result = ffmpeg(
                    action="cut",
                    input_path=temp_file,
                    output_path="/tmp/output.mp4",
                    start_time="30",
                    duration="60",
                )
                assert "successfully" in result
                mock_run.assert_called_once()
                args = mock_run.call_args[0][0]
                assert "-t" in args
            finally:
                Path(temp_file).unlink(missing_ok=True)


class TestConcatAction:
    """Tests for ffmpeg concat action."""

    def test_concat_ffmpeg_not_installed(self):
        """Test concat when ffmpeg is not installed."""
        from strands_pack import ffmpeg

        with patch("strands_pack.ffmpeg._check_ffmpeg") as mock_check:
            mock_check.return_value = False
            result = ffmpeg(
                action="concat",
                input_paths=["/tmp/v1.mp4", "/tmp/v2.mp4"],
                output_path="/tmp/output.mp4",
            )
            assert "Error" in result
            assert "ffmpeg is not installed" in result


class TestRemoveDeadSpaceAction:
    def test_remove_dead_space_requires_paths(self):
        from strands_pack import ffmpeg

        res = ffmpeg(action="remove_dead_space", input_path=None, output_path="/tmp/out.mp4")
        assert "input_path" in res

    def test_remove_dead_space_calls_ffmpeg(self):
        from strands_pack import ffmpeg

        # Fake files
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            inp = f.name
        outp = inp + ".out.mp3"

        try:
            with patch("strands_pack.ffmpeg._check_ffmpeg", return_value=True), patch(
                "strands_pack.ffmpeg._check_ffprobe", return_value=True
            ), patch("strands_pack.ffmpeg._run_ffprobe_capture", return_value=(True, "10.0")), patch(
                "strands_pack.ffmpeg._run_ffmpeg_capture_stderr",
                return_value=(True, "[silencedetect] silence_start: 0.0\n[silencedetect] silence_end: 1.0\n"),
            ), patch("strands_pack.ffmpeg._run_ffmpeg", return_value=(True, "Success")) as mock_run:
                res = ffmpeg(
                    action="remove_dead_space",
                    input_path=inp,
                    output_path=outp,
                    mode="audio",
                    threshold_db=-40.0,
                    min_silence_duration=0.3,
                    padding_ms=100,
                    max_segments=50,
                )
                assert "successfully" in res.lower()
                assert mock_run.call_count >= 2  # at least one cut + concat
        finally:
            Path(inp).unlink(missing_ok=True)
            Path(outp).unlink(missing_ok=True)


class TestNewActions:
    """Smoke tests for newly added ffmpeg actions (argument building via mocks)."""

    def test_resize_calls_ffmpeg_with_scale_filter(self):
        from strands_pack import ffmpeg

        with patch("strands_pack.ffmpeg._check_ffmpeg", return_value=True), patch(
            "strands_pack.ffmpeg._run_ffmpeg", return_value=(True, "Success")
        ) as mock_run:
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
                input_path = f.name
            try:
                out = ffmpeg(action="resize", input_path=input_path, output_path="/tmp/out.mp4", width=1280, height=720)
                assert "resized successfully" in out
                args = mock_run.call_args[0][0]
                assert "-vf" in args
                assert any("scale=1280:720" in s for s in args)
            finally:
                Path(input_path).unlink(missing_ok=True)

    def test_compress_includes_crf_and_preset(self):
        from strands_pack import ffmpeg

        with patch("strands_pack.ffmpeg._check_ffmpeg", return_value=True), patch(
            "strands_pack.ffmpeg._run_ffmpeg", return_value=(True, "Success")
        ) as mock_run:
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
                input_path = f.name
            try:
                out = ffmpeg(action="compress", input_path=input_path, output_path="/tmp/out.mp4", crf=28, preset="fast")
                assert "compressed successfully" in out
                args = mock_run.call_args[0][0]
                assert "-crf" in args and "28" in args
                assert "-preset" in args and "fast" in args
            finally:
                Path(input_path).unlink(missing_ok=True)

    def test_thumbnail_includes_ss_and_frames(self):
        from strands_pack import ffmpeg

        with patch("strands_pack.ffmpeg._check_ffmpeg", return_value=True), patch(
            "strands_pack.ffmpeg._run_ffmpeg", return_value=(True, "Success")
        ) as mock_run:
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
                input_path = f.name
            try:
                out = ffmpeg(action="thumbnail", input_path=input_path, output_path="/tmp/thumb.jpg", timestamp="3.5")
                assert "Thumbnail created successfully" in out
                args = mock_run.call_args[0][0]
                assert "-ss" in args
                assert "-frames:v" in args
            finally:
                Path(input_path).unlink(missing_ok=True)

    def test_watermark_requires_text_or_image(self):
        from strands_pack import ffmpeg

        with patch("strands_pack.ffmpeg._check_ffmpeg", return_value=True):
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
                input_path = f.name
            try:
                out = ffmpeg(action="watermark", input_path=input_path, output_path="/tmp/out.mp4")
                assert "Must provide watermark_image or watermark_text" in out
            finally:
                Path(input_path).unlink(missing_ok=True)

    def test_concat_less_than_two_inputs(self):
        """Test concat with less than 2 input files."""
        from strands_pack import ffmpeg

        with patch("strands_pack.ffmpeg._check_ffmpeg") as mock_check:
            mock_check.return_value = True
            result = ffmpeg(
                action="concat",
                input_paths=["/tmp/v1.mp4"],
                output_path="/tmp/output.mp4",
            )
            assert "Error" in result
            assert "Need at least 2 videos" in result

    def test_concat_input_not_found(self):
        """Test concat with non-existent input file."""
        from strands_pack import ffmpeg

        with patch("strands_pack.ffmpeg._check_ffmpeg") as mock_check:
            mock_check.return_value = True
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
                existing_file = f.name
            try:
                result = ffmpeg(
                    action="concat",
                    input_paths=[existing_file, "/nonexistent/video.mp4"],
                    output_path="/tmp/output.mp4",
                )
                assert "Error" in result
                assert "not found" in result
            finally:
                Path(existing_file).unlink(missing_ok=True)

    def test_concat_success_no_reencode(self):
        """Test successful concat without re-encoding."""
        from strands_pack import ffmpeg

        with patch("strands_pack.ffmpeg._check_ffmpeg") as mock_check, patch(
            "strands_pack.ffmpeg._run_ffmpeg"
        ) as mock_run:
            mock_check.return_value = True
            mock_run.return_value = (True, "Success")
            temp_files = []
            try:
                for _ in range(3):
                    with tempfile.NamedTemporaryFile(
                        suffix=".mp4", delete=False
                    ) as f:
                        temp_files.append(f.name)
                result = ffmpeg(
                    action="concat",
                    input_paths=temp_files,
                    output_path="/tmp/output.mp4",
                    reencode=False,
                )
                assert "successfully" in result
                mock_run.assert_called_once()
                args = mock_run.call_args[0][0]
                assert "-f" in args
                assert "concat" in args
                assert "-c" in args
                assert "copy" in args
            finally:
                for f in temp_files:
                    Path(f).unlink(missing_ok=True)


class TestInfoAction:
    """Tests for ffmpeg info action."""

    def test_info_ffprobe_not_installed(self):
        """Test info when ffprobe is not installed."""
        from strands_pack import ffmpeg

        with patch("shutil.which") as mock_which:
            mock_which.return_value = None
            result = ffmpeg(action="info", input_path="/tmp/video.mp4")
            assert "Error" in result
            assert "ffprobe is not installed" in result

    def test_info_file_not_found(self):
        """Test info with non-existent file."""
        from strands_pack import ffmpeg

        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/ffprobe"
            result = ffmpeg(action="info", input_path="/nonexistent/video.mp4")
            assert "Error" in result
            assert "not found" in result

    def test_info_success(self):
        """Test successful info retrieval."""
        from strands_pack import ffmpeg

        mock_output = {
            "format": {
                "duration": "125.5",
                "size": "10485760",
            },
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                    "r_frame_rate": "30/1",
                },
                {
                    "codec_type": "audio",
                    "codec_name": "aac",
                    "sample_rate": "48000",
                    "channels": 2,
                },
            ],
        }
        with patch("shutil.which") as mock_which, patch(
            "subprocess.run"
        ) as mock_run:
            mock_which.return_value = "/usr/bin/ffprobe"
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=__import__("json").dumps(mock_output),
                stderr="",
            )
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
                temp_file = f.name
            try:
                result = ffmpeg(action="info", input_path=temp_file)
                assert "Duration:" in result
                assert "Size:" in result
                assert "Video:" in result
                assert "h264" in result
                assert "1920x1080" in result
                assert "Audio:" in result
                assert "aac" in result
            finally:
                Path(temp_file).unlink(missing_ok=True)


class TestExtractAudioAction:
    """Tests for ffmpeg extract_audio action."""

    def test_extract_audio_ffmpeg_not_installed(self):
        """Test extract_audio when ffmpeg is not installed."""
        from strands_pack import ffmpeg

        with patch("strands_pack.ffmpeg._check_ffmpeg") as mock_check:
            mock_check.return_value = False
            result = ffmpeg(
                action="extract_audio",
                input_path="/tmp/video.mp4",
                output_path="/tmp/audio.mp3",
            )
            assert "Error" in result
            assert "ffmpeg is not installed" in result

    def test_extract_audio_input_not_found(self):
        """Test extract_audio with non-existent input file."""
        from strands_pack import ffmpeg

        with patch("strands_pack.ffmpeg._check_ffmpeg") as mock_check:
            mock_check.return_value = True
            result = ffmpeg(
                action="extract_audio",
                input_path="/nonexistent/video.mp4",
                output_path="/tmp/audio.mp3",
            )
            assert "Error" in result
            assert "not found" in result

    def test_extract_audio_success_default_format(self):
        """Test successful extract_audio with default mp3 format."""
        from strands_pack import ffmpeg

        with patch("strands_pack.ffmpeg._check_ffmpeg") as mock_check, patch(
            "strands_pack.ffmpeg._run_ffmpeg"
        ) as mock_run:
            mock_check.return_value = True
            mock_run.return_value = (True, "Success")
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
                temp_file = f.name
            try:
                result = ffmpeg(
                    action="extract_audio",
                    input_path=temp_file,
                    output_path="/tmp/audio.mp3",
                )
                assert "successfully" in result
                mock_run.assert_called_once()
                args = mock_run.call_args[0][0]
                assert "-vn" in args
                assert "-acodec" in args
                assert "libmp3lame" in args
            finally:
                Path(temp_file).unlink(missing_ok=True)

    def test_extract_audio_wav_format(self):
        """Test extract_audio with wav format."""
        from strands_pack import ffmpeg

        with patch("strands_pack.ffmpeg._check_ffmpeg") as mock_check, patch(
            "strands_pack.ffmpeg._run_ffmpeg"
        ) as mock_run:
            mock_check.return_value = True
            mock_run.return_value = (True, "Success")
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
                temp_file = f.name
            try:
                result = ffmpeg(
                    action="extract_audio",
                    input_path=temp_file,
                    output_path="/tmp/audio.wav",
                    format="wav",
                )
                assert "successfully" in result
                args = mock_run.call_args[0][0]
                assert "pcm_s16le" in args
            finally:
                Path(temp_file).unlink(missing_ok=True)


class TestUnknownAction:
    """Tests for unknown action."""

    def test_unknown_action(self):
        """Test that unknown action returns error."""
        from strands_pack import ffmpeg

        result = ffmpeg(action="unknown_action")
        assert "Error" in result
        assert "Unknown action" in result


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_parse_timestamp_empty_string(self):
        """Test parsing empty string timestamp."""
        # Empty string will result in ValueError when converting to float
        with pytest.raises(ValueError):
            _parse_timestamp("")

    def test_concat_empty_list(self):
        """Test concat with empty list."""
        from strands_pack import ffmpeg

        with patch("strands_pack.ffmpeg._check_ffmpeg") as mock_check:
            mock_check.return_value = True
            result = ffmpeg(
                action="concat",
                input_paths=[],
                output_path="/tmp/output.mp4",
            )
            assert "Error" in result
            assert "Need at least 2 videos" in result
