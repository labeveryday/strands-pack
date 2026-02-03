"""Tests for audio tool."""

import os
import tempfile

import pytest


@pytest.fixture
def output_dir():
    """Create a temp directory for output files."""
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def sample_audio_path(output_dir):
    """Create a sample audio file for testing."""
    try:
        from pydub import AudioSegment
        from pydub.generators import Sine
    except ImportError:
        pytest.skip("pydub not installed")

    # Generate a simple sine wave tone (1 second, 440 Hz)
    tone = Sine(440).to_audio_segment(duration=1000)

    path = os.path.join(output_dir, "sample.wav")
    tone.export(path, format="wav")
    return path


@pytest.fixture
def second_audio_path(output_dir):
    """Create a second audio file for concat testing."""
    try:
        from pydub import AudioSegment
        from pydub.generators import Sine
    except ImportError:
        pytest.skip("pydub not installed")

    # Generate a different tone (500 Hz)
    tone = Sine(500).to_audio_segment(duration=500)

    path = os.path.join(output_dir, "second.wav")
    tone.export(path, format="wav")
    return path


def test_audio_get_info(sample_audio_path):
    """Test getting audio file info."""
    from strands_pack import audio

    result = audio(action="get_info", input_path=sample_audio_path)

    assert result["success"] is True
    assert result["action"] == "get_info"
    assert result["duration_ms"] == 1000
    assert result["channels"] >= 1
    assert "frame_rate" in result


def test_audio_convert(sample_audio_path, output_dir):
    """Test converting audio format."""
    from strands_pack import audio

    output_path = os.path.join(output_dir, "converted.wav")
    result = audio(
        action="convert",
        input_path=sample_audio_path,
        output_path=output_path,
    )

    assert result["success"] is True
    assert result["action"] == "convert"
    assert os.path.exists(output_path)


def test_audio_trim(sample_audio_path, output_dir):
    """Test trimming audio."""
    from strands_pack import audio

    output_path = os.path.join(output_dir, "trimmed.wav")
    result = audio(
        action="trim",
        input_path=sample_audio_path,
        output_path=output_path,
        start_ms=100,
        end_ms=500,
    )

    assert result["success"] is True
    assert result["action"] == "trim"
    assert result["new_duration_ms"] == 400
    assert os.path.exists(output_path)


def test_audio_trim_invalid_range(sample_audio_path, output_dir):
    """Test error with invalid trim range."""
    from strands_pack import audio

    output_path = os.path.join(output_dir, "trimmed.wav")
    result = audio(
        action="trim",
        input_path=sample_audio_path,
        output_path=output_path,
        start_ms=500,
        end_ms=100,
    )

    assert result["success"] is False
    assert "end_ms" in result["error"]


def test_audio_concat(sample_audio_path, second_audio_path, output_dir):
    """Test concatenating audio files."""
    from strands_pack import audio

    output_path = os.path.join(output_dir, "concat.wav")
    result = audio(
        action="concat",
        input_paths=[sample_audio_path, second_audio_path],
        output_path=output_path,
    )

    assert result["success"] is True
    assert result["action"] == "concat"
    assert result["input_count"] == 2
    assert result["total_duration_ms"] == 1500  # 1000 + 500
    assert os.path.exists(output_path)


def test_audio_concat_single_file(sample_audio_path, output_dir):
    """Test error when concatenating single file."""
    from strands_pack import audio

    output_path = os.path.join(output_dir, "concat.wav")
    result = audio(
        action="concat",
        input_paths=[sample_audio_path],
        output_path=output_path,
    )

    assert result["success"] is False
    assert "2 input files" in result["error"]


def test_audio_adjust_volume(sample_audio_path, output_dir):
    """Test adjusting volume."""
    from strands_pack import audio

    output_path = os.path.join(output_dir, "louder.wav")
    result = audio(
        action="adjust_volume",
        input_path=sample_audio_path,
        output_path=output_path,
        db=3,
    )

    assert result["success"] is True
    assert result["action"] == "adjust_volume"
    assert result["db_change"] == 3
    assert os.path.exists(output_path)


def test_audio_normalize(sample_audio_path, output_dir):
    """Test normalizing audio."""
    from strands_pack import audio

    output_path = os.path.join(output_dir, "normalized.wav")
    result = audio(
        action="normalize",
        input_path=sample_audio_path,
        output_path=output_path,
    )

    assert result["success"] is True
    assert result["action"] == "normalize"
    assert os.path.exists(output_path)


def test_audio_fade(sample_audio_path, output_dir):
    """Test applying fade effects."""
    from strands_pack import audio

    output_path = os.path.join(output_dir, "faded.wav")
    result = audio(
        action="fade",
        input_path=sample_audio_path,
        output_path=output_path,
        fade_in_ms=100,
        fade_out_ms=100,
    )

    assert result["success"] is True
    assert result["action"] == "fade"
    assert result["fade_in_ms"] == 100
    assert result["fade_out_ms"] == 100


def test_audio_fade_missing_params(sample_audio_path, output_dir):
    """Test error when no fade params provided."""
    from strands_pack import audio

    output_path = os.path.join(output_dir, "faded.wav")
    result = audio(
        action="fade",
        input_path=sample_audio_path,
        output_path=output_path,
    )

    assert result["success"] is False
    assert "fade_in_ms" in result["error"] or "fade_out_ms" in result["error"]


def test_audio_split(sample_audio_path, output_dir):
    """Test splitting audio into segments."""
    from strands_pack import audio

    split_dir = os.path.join(output_dir, "splits")
    result = audio(
        action="split",
        input_path=sample_audio_path,
        output_dir=split_dir,
        segment_ms=300,
    )

    assert result["success"] is True
    assert result["action"] == "split"
    assert result["segment_count"] >= 3  # 1000ms / 300ms = ~4 segments


def test_audio_overlay(sample_audio_path, second_audio_path, output_dir):
    """Test overlaying audio."""
    from strands_pack import audio

    output_path = os.path.join(output_dir, "overlay.wav")
    result = audio(
        action="overlay",
        input_path=sample_audio_path,
        overlay_path=second_audio_path,
        output_path=output_path,
        position_ms=200,
    )

    assert result["success"] is True
    assert result["action"] == "overlay"
    assert result["position_ms"] == 200


def test_audio_extract_segment(sample_audio_path, output_dir):
    """Test extracting a segment."""
    from strands_pack import audio

    output_path = os.path.join(output_dir, "segment.wav")
    result = audio(
        action="extract_segment",
        input_path=sample_audio_path,
        output_path=output_path,
        start_ms=200,
        duration_ms=300,
    )

    assert result["success"] is True
    assert result["action"] == "extract_segment"
    assert result["actual_duration_ms"] == 300


def test_audio_file_not_found(sample_audio_path):
    """Test error when file doesn't exist."""
    from strands_pack import audio

    result = audio(action="get_info", input_path="/nonexistent/file.wav")

    assert result["success"] is False
    # May fail with import error if pydub not installed, or file not found
    assert "not found" in result["error"].lower() or "not installed" in result["error"].lower()


def test_audio_missing_input_path():
    """Test error when input path is missing."""
    from strands_pack import audio

    result = audio(action="get_info")

    assert result["success"] is False
    assert "input_path" in result["error"]


def test_audio_unknown_action():
    """Test error for unknown action."""
    from strands_pack import audio

    result = audio(action="unknown_action")

    assert result["success"] is False
    assert "Unknown action" in result["error"]
    assert "available_actions" in result
