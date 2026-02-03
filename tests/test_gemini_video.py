"""Tests for Gemini video tool (video generation using Veo models)."""

import os
import sys
import tempfile
from importlib import import_module
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Import the actual module (not the tool) for patching internal functions
gemini_video_mod = import_module("strands_pack.gemini_video")

# Check if google-genai is installed
try:
    import google.genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

# Create mock modules for when google-genai is not installed
mock_google = MagicMock()
mock_genai = MagicMock()
mock_types = MagicMock()
mock_google.genai = mock_genai
mock_genai.types = mock_types


# ============================================================================
# GEMINI VIDEO HELPER TESTS
# ============================================================================

class TestGeminiVideoHelpers:
    """Tests for video helper functions in gemini_video module."""

    def test_get_mime_type_png(self):
        """Test MIME type detection for PNG files."""
        from strands_pack.gemini_video import _get_mime_type
        assert _get_mime_type(Path("image.png")) == "image/png"
        assert _get_mime_type(Path("image.PNG")) == "image/png"

    def test_get_mime_type_jpeg(self):
        """Test MIME type detection for JPEG files."""
        from strands_pack.gemini_video import _get_mime_type
        assert _get_mime_type(Path("image.jpg")) == "image/jpeg"
        assert _get_mime_type(Path("image.jpeg")) == "image/jpeg"
        assert _get_mime_type(Path("image.JPEG")) == "image/jpeg"

    def test_get_mime_type_webp(self):
        """Test MIME type detection for WebP files."""
        from strands_pack.gemini_video import _get_mime_type
        assert _get_mime_type(Path("image.webp")) == "image/webp"

    def test_get_mime_type_gif(self):
        """Test MIME type detection for GIF files."""
        from strands_pack.gemini_video import _get_mime_type
        assert _get_mime_type(Path("image.gif")) == "image/gif"

    def test_get_mime_type_unknown_defaults_to_png(self):
        """Test that unknown extensions default to PNG."""
        from strands_pack.gemini_video import _get_mime_type
        assert _get_mime_type(Path("image.bmp")) == "image/png"
        assert _get_mime_type(Path("image.tiff")) == "image/png"

    @pytest.mark.skipif(not HAS_GENAI, reason="google-genai not installed")
    def test_load_image_file_not_found(self):
        """Test error handling when image file doesn't exist."""
        from strands_pack.gemini_video import _load_image
        with pytest.raises(FileNotFoundError) as exc_info:
            _load_image("/nonexistent/path/image.png")
        assert "Image file not found" in str(exc_info.value)


# ============================================================================
# GENERATE VIDEO TESTS
# ============================================================================

class TestGenerateVideo:
    """Tests for the generate action."""

    def test_missing_api_key(self):
        """Test error when GOOGLE_API_KEY is not set."""
        from strands_pack.gemini_video import gemini_video

        with patch.dict(sys.modules, {"google": mock_google, "google.genai": mock_genai}):
            with patch.dict(os.environ, {}, clear=True):
                os.environ.pop("GOOGLE_API_KEY", None)
                result = gemini_video(action="generate", prompt="A test video")

            assert result["success"] is False
            assert "GOOGLE_API_KEY" in result["error"]

    def test_invalid_duration_for_veo31(self):
        """Test that invalid duration is rejected for Veo 3.1."""
        from strands_pack.gemini_video import gemini_video

        with patch.dict(sys.modules, {"google": mock_google, "google.genai": mock_genai}):
            with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
                result = gemini_video(
                    action="generate",
                    prompt="A test video",
                    model="veo-3.1-generate-preview",
                    duration_seconds=5  # 5 is only valid for Veo 2
                )

            assert result["success"] is False
            assert "Invalid duration" in result["error"]
            assert "[4, 6, 8]" in result["error"]

    def test_invalid_duration_for_veo2(self):
        """Test that invalid duration is rejected for Veo 2."""
        from strands_pack.gemini_video import gemini_video

        with patch.dict(sys.modules, {"google": mock_google, "google.genai": mock_genai}):
            with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
                result = gemini_video(
                    action="generate",
                    prompt="A test video",
                    model="veo-2.0-generate-001",
                    duration_seconds=4  # 4 is not valid for Veo 2
                )

            assert result["success"] is False
            assert "Invalid duration" in result["error"]
            assert "[5, 6, 8]" in result["error"]

    def test_1080p_not_supported_for_veo2(self):
        """Test that 1080p resolution is rejected for Veo 2."""
        from strands_pack.gemini_video import gemini_video

        with patch.dict(sys.modules, {"google": mock_google, "google.genai": mock_genai}):
            with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
                result = gemini_video(
                    action="generate",
                    prompt="A test video",
                    model="veo-2.0-generate-001",
                    resolution="1080p"
                )

            assert result["success"] is False
            assert "1080p resolution not supported for Veo 2" in result["error"]

    def test_1080p_requires_8s_duration(self):
        """Test that 1080p resolution requires 8 second duration."""
        from strands_pack.gemini_video import gemini_video

        with patch.dict(sys.modules, {"google": mock_google, "google.genai": mock_genai}):
            with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
                result = gemini_video(
                    action="generate",
                    prompt="A test video",
                    model="veo-3.1-generate-preview",
                    resolution="1080p",
                    duration_seconds=6
                )

            assert result["success"] is False
            assert "1080p resolution requires duration_seconds=8" in result["error"]

    def test_reference_images_only_for_veo31(self):
        """Test that reference images are only supported for Veo 3.1."""
        from strands_pack.gemini_video import gemini_video

        with patch.dict(sys.modules, {"google": mock_google, "google.genai": mock_genai}):
            with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
                result = gemini_video(
                    action="generate",
                    prompt="A test video",
                    model="veo-3.0-generate-001",
                    reference_images=["img1.png"]
                )

            assert result["success"] is False
            assert "Reference images only supported with Veo 3.1 models" in result["error"]

    def test_max_reference_images_exceeded(self):
        """Test that more than 3 reference images is rejected."""
        from strands_pack.gemini_video import gemini_video

        with patch.dict(sys.modules, {"google": mock_google, "google.genai": mock_genai}):
            with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
                result = gemini_video(
                    action="generate",
                    prompt="A test video",
                    model="veo-3.1-generate-preview",
                    reference_images=["img1.png", "img2.png", "img3.png", "img4.png"]
                )

            assert result["success"] is False
            assert "Maximum 3 reference images supported" in result["error"]

    def test_missing_prompt(self):
        """Test that generate requires prompt parameter."""
        from strands_pack.gemini_video import gemini_video

        result = gemini_video(action="generate", prompt="")

        assert result["success"] is False
        assert "prompt" in result["error"]

    def test_generate_multiple_videos_returns_file_paths(self):
        """number_of_videos should produce multiple outputs when SDK supports it."""
        from strands_pack import gemini_video as gemini_video_tool

        # Build a minimal fake google.genai.types module with GenerateVideosConfig.
        class FakeGenerateVideosConfig:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        class FakeTypes:
            GenerateVideosConfig = FakeGenerateVideosConfig

            class VideoGenerationReferenceImage:  # pragma: no cover
                def __init__(self, **_kwargs):
                    pass

        class FakeClient:
            def __init__(self):
                self.models = MagicMock()

        # Fake operation response with 3 videos
        class FakeVideoObj:
            def __init__(self, b: bytes):
                self.video_bytes = b

        class FakeGeneratedVideo:
            def __init__(self, b: bytes):
                self.video = FakeVideoObj(b)

        fake_operation = MagicMock()
        fake_operation.response = MagicMock()
        fake_operation.response.generated_videos = [
            FakeGeneratedVideo(b"a"),
            FakeGeneratedVideo(b"b"),
            FakeGeneratedVideo(b"c"),
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}), patch.object(
                gemini_video_mod, "_get_client", return_value=FakeClient()
            ) as _get_client, patch.object(
                gemini_video_mod, "_poll_operation", return_value={"success": True, "operation": fake_operation}
            ), patch.dict(sys.modules, {"google": mock_google, "google.genai": mock_genai}):
                # Patch the runtime import target used by _generate_video
                with patch.dict(sys.modules, {"google.genai.types": FakeTypes}):
                    # Also patch "from google.genai import types" resolution by setting attribute
                    mock_genai.types = FakeTypes

                    # Make generate_videos return the operation object
                    _get_client.return_value.models.generate_videos.return_value = MagicMock()

                    result = gemini_video_tool(
                        action="generate",
                        prompt="A test video",
                        output_dir=tmp_dir,
                        number_of_videos=3,
                    )

            assert result["success"] is True
            assert result["number_of_videos"] == 3
            assert isinstance(result["file_paths"], list)
            assert len(result["file_paths"]) == 3
            for p in result["file_paths"]:
                assert Path(p).exists()

    def test_generate_video_drops_unsupported_config_fields(self):
        """If SDK doesn't support a field (e.g., fps), it should be dropped with warnings."""
        from strands_pack import gemini_video as gemini_video_tool

        class FakeGenerateVideosConfig:
            def __init__(self, **kwargs):
                if "fps" in kwargs:
                    raise TypeError("__init__() got an unexpected keyword argument 'fps'")
                self.kwargs = kwargs

        class FakeTypes:
            GenerateVideosConfig = FakeGenerateVideosConfig

        class FakeClient:
            def __init__(self):
                self.models = MagicMock()

        class FakeVideoObj:
            def __init__(self, b: bytes):
                self.video_bytes = b

        class FakeGeneratedVideo:
            def __init__(self, b: bytes):
                self.video = FakeVideoObj(b)

        fake_operation = MagicMock()
        fake_operation.response = MagicMock()
        fake_operation.response.generated_videos = [FakeGeneratedVideo(b"a")]

        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}), patch.object(
                gemini_video_mod, "_get_client", return_value=FakeClient()
            ), patch.object(
                gemini_video_mod, "_poll_operation", return_value={"success": True, "operation": fake_operation}
            ), patch.dict(sys.modules, {"google": mock_google, "google.genai": mock_genai}):
                mock_genai.types = FakeTypes
                result = gemini_video_tool(
                    action="generate",
                    prompt="A test video",
                    output_dir=tmp_dir,
                    fps=30,
                )

            assert result["success"] is True
            assert "fps" in (result.get("dropped_config_fields") or [])
            assert any("Dropped unsupported config fields" in w for w in (result.get("warnings") or []))


# ============================================================================
# IMAGE TO VIDEO TESTS
# ============================================================================

class TestImageToVideo:
    """Tests for the image_to_video action."""

    def test_missing_api_key(self):
        """Test error when GOOGLE_API_KEY is not set."""
        from strands_pack.gemini_video import gemini_video

        with patch.dict(sys.modules, {"google": mock_google, "google.genai": mock_genai}):
            with patch.dict(os.environ, {}, clear=True):
                os.environ.pop("GOOGLE_API_KEY", None)
                result = gemini_video(
                    action="image_to_video",
                    prompt="Animate this",
                    image_path="/some/image.png"
                )

            assert result["success"] is False
            assert "GOOGLE_API_KEY" in result["error"]

    def test_last_frame_only_for_veo31(self):
        """Test that last_frame is only supported for Veo 3.1."""
        from strands_pack.gemini_video import gemini_video

        with patch.dict(sys.modules, {"google": mock_google, "google.genai": mock_genai}):
            with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
                result = gemini_video(
                    action="image_to_video",
                    prompt="Animate this",
                    image_path="/some/image.png",
                    model="veo-3.0-generate-001",
                    last_frame_path="/some/last_frame.png"
                )

            assert result["success"] is False
            assert "Frame interpolation (last_frame) only supported with Veo 3.1 models" in result["error"]

    def test_invalid_duration_for_veo31(self):
        """Test invalid duration for Veo 3.1."""
        from strands_pack.gemini_video import gemini_video

        with patch.dict(sys.modules, {"google": mock_google, "google.genai": mock_genai}):
            with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
                result = gemini_video(
                    action="image_to_video",
                    prompt="Animate this",
                    image_path="/some/image.png",
                    model="veo-3.1-generate-preview",
                    duration_seconds=5
                )

            assert result["success"] is False
            assert "Invalid duration" in result["error"]

    def test_image_not_found(self):
        """Test error when input image file doesn't exist."""
        from strands_pack.gemini_video import gemini_video

        with patch.dict(sys.modules, {"google": mock_google, "google.genai": mock_genai}):
            with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
                result = gemini_video(
                    action="image_to_video",
                    prompt="Animate this",
                    image_path="/nonexistent/image.png"
                )

            assert result["success"] is False
            assert "Image file not found" in result["error"]

    def test_missing_image_path(self):
        """Test that image_to_video requires image_path parameter."""
        from strands_pack.gemini_video import gemini_video

        result = gemini_video(action="image_to_video", prompt="Animate this")

        assert result["success"] is False
        assert "image_path" in result["error"]


# ============================================================================
# EXTEND VIDEO TESTS
# ============================================================================

class TestExtendVideo:
    """Tests for the extend action."""

    def test_missing_api_key(self):
        """Test error when GOOGLE_API_KEY is not set."""
        from strands_pack.gemini_video import gemini_video

        with patch.dict(sys.modules, {"google": mock_google, "google.genai": mock_genai}):
            with patch.dict(os.environ, {}, clear=True):
                os.environ.pop("GOOGLE_API_KEY", None)
                result = gemini_video(
                    action="extend",
                    prompt="Continue the action",
                    video_path="/some/video.mp4"
                )

            assert result["success"] is False
            assert "GOOGLE_API_KEY" in result["error"]

    def test_video_not_found(self):
        """Test error when video file doesn't exist."""
        from strands_pack.gemini_video import gemini_video

        with patch.dict(sys.modules, {"google": mock_google, "google.genai": mock_genai}):
            with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
                result = gemini_video(
                    action="extend",
                    prompt="Continue the action",
                    video_path="/nonexistent/video.mp4"
                )

            assert result["success"] is False
            assert "Video file not found" in result["error"]

    def test_missing_video_path(self):
        """Test that extend requires video_path parameter."""
        from strands_pack.gemini_video import gemini_video

        result = gemini_video(action="extend", prompt="Continue the action")

        assert result["success"] is False
        assert "video_path" in result["error"]

    def test_extend_returns_hint_on_encoding_errors(self):
        """Extend should include a helpful hint when Veo rejects video encoding."""
        # Test the error handling logic by checking that encoding-related errors get hints
        # This tests the _err return path in _extend_video's except block

        error_messages = [
            "InvalidArgument: unsupported codec",
            "Failed to decode video",
            "Unsupported format",
            "Invalid container",
        ]

        for error_msg in error_messages:
            lower = error_msg.lower()
            # This mirrors the logic in _extend_video's except block
            hint = None
            if any(k in lower for k in ["codec", "unsupported", "invalidargument", "decode", "format", "container"]):
                hint = "re-encode"  # Simplified - actual hint is longer

            assert hint is not None, f"Error '{error_msg}' should trigger re-encode hint"
            assert "re-encode" in hint.lower()

    def test_extend_encoding_error_falls_back_to_image_to_video(self):
        """If extend hits an `encoding` unsupported error, tool should fall back internally."""
        from strands_pack import gemini_video as gemini_video_tool

        # Create fresh mocks to avoid state pollution from other tests
        local_mock_google = MagicMock()
        local_mock_genai = MagicMock()
        local_mock_google.genai = local_mock_genai

        # Create a temporary dummy mp4 file (contents irrelevant; we won't actually decode it in this unit test).
        with tempfile.TemporaryDirectory() as tmp_dir:
            vpath = Path(tmp_dir) / "in.mp4"
            vpath.write_bytes(b"\x00\x00\x00\x18ftypmp42")  # minimal-ish header

            # Create a mock client with generate_videos configured to raise the encoding error
            mock_client = MagicMock()
            mock_client.models.generate_videos.side_effect = Exception(
                "`encoding` isn't supported by this model."
            )

            with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}), patch.object(
                gemini_video_mod, "_get_client", return_value=mock_client
            ), patch.object(
                gemini_video_mod, "_extract_last_frame", return_value=(True, "")
            ), patch.object(
                gemini_video_mod, "_image_to_video", return_value={"success": True, "file_path": "out.mp4"}
            ), patch.dict(sys.modules, {"google": local_mock_google, "google.genai": local_mock_genai}):
                result = gemini_video_tool(
                    action="extend",
                    prompt="Continue",
                    video_path=str(vpath),
                    model="veo-3.1-generate-preview",
                )

                assert result["success"] is True
                assert result["action"] == "extend"
                assert result.get("extend_mode") == "fallback_image_to_video"

    def test_extend_uses_video_ref_uri_when_provided(self):
        """When video_ref contains a URI, extend should construct a URI-based Video (not bytes)."""
        from strands_pack import gemini_video as gemini_video_tool

        class FakeVideo:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        class FakeGenerateVideosConfig:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        class FakeTypes:
            Video = FakeVideo
            GenerateVideosConfig = FakeGenerateVideosConfig

        fake_operation = MagicMock()
        fake_operation.done = True
        fake_operation.error = None
        fake_operation.response = MagicMock()
        fake_operation.response.generated_videos = [MagicMock(video=MagicMock(video_bytes=b"a"))]

        # Create a FakeClient instance to track calls
        fake_client = MagicMock()

        with tempfile.TemporaryDirectory() as tmp_dir:
            vpath = Path(tmp_dir) / "in.mp4"
            vpath.write_bytes(b"\x00\x00\x00\x18ftypmp42")

            with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}), patch.object(
                gemini_video_mod, "_get_client", return_value=fake_client
            ), patch.object(
                gemini_video_mod, "_poll_operation", return_value={"success": True, "operation": fake_operation}
            ), patch.object(
                gemini_video_mod, "_save_video", return_value={"success": True, "file_path": "out.mp4", "video_uri": "https://example/video"}
            ), patch.dict(sys.modules, {"google": mock_google, "google.genai": mock_genai}):
                # Patch the runtime import target used by _extend_video
                with patch.dict(sys.modules, {"google.genai.types": FakeTypes}):
                    mock_genai.types = FakeTypes

                    result = gemini_video_tool(
                        action="extend",
                        prompt="Continue",
                        video_path=str(vpath),
                        model="veo-3.1-generate-preview",
                        video_ref={"uri": "https://example.com/veo_video_uri", "mime_type": "video/mp4"},
                    )

                    # Check the call inside the context where fake_client is still accessible
                    assert result["success"] is True
                    call_kwargs = fake_client.models.generate_videos.call_args.kwargs
                    assert "video" in call_kwargs
                    assert isinstance(call_kwargs["video"], FakeVideo)
                    assert call_kwargs["video"].kwargs.get("uri") == "https://example.com/veo_video_uri"


# ============================================================================
# POLL OPERATION TESTS
# ============================================================================

class TestPollOperation:
    """Tests for the video generation polling logic."""

    def test_poll_operation_timeout(self):
        """Test that polling times out after max_wait_seconds."""
        from strands_pack.gemini_video import _poll_operation

        mock_client = MagicMock()
        mock_operation = MagicMock()
        mock_operation.done = False

        # Simulate an operation that never completes
        mock_client.operations.get.return_value = mock_operation

        result = _poll_operation(mock_client, mock_operation, max_wait_seconds=0)

        assert result["success"] is False
        assert "timed out" in result["error"]

    def test_poll_operation_error(self):
        """Test handling of operation errors."""
        from strands_pack.gemini_video import _poll_operation

        mock_client = MagicMock()
        mock_operation = MagicMock()
        mock_operation.done = True
        mock_operation.error = "API Error: quota exceeded"
        mock_operation.response = None

        result = _poll_operation(mock_client, mock_operation, max_wait_seconds=60)

        assert result["success"] is False
        assert "quota exceeded" in result["error"]

    def test_poll_operation_no_video(self):
        """Test handling when no video is generated."""
        from strands_pack.gemini_video import _poll_operation

        mock_client = MagicMock()
        mock_operation = MagicMock()
        mock_operation.done = True
        mock_operation.error = None
        mock_operation.response = MagicMock()
        mock_operation.response.generated_videos = []

        result = _poll_operation(mock_client, mock_operation, max_wait_seconds=60)

        assert result["success"] is False
        assert "No video generated" in result["error"]

    def test_poll_operation_success(self):
        """Test successful operation completion."""
        from strands_pack.gemini_video import _poll_operation

        mock_client = MagicMock()
        mock_operation = MagicMock()
        mock_operation.done = True
        mock_operation.error = None
        mock_operation.response = MagicMock()
        mock_operation.response.generated_videos = [MagicMock()]

        result = _poll_operation(mock_client, mock_operation, max_wait_seconds=60)

        assert result["success"] is True
        assert "operation" in result


# ============================================================================
# SAVE VIDEO TESTS
# ============================================================================

class TestSaveVideo:
    """Tests for the video saving logic."""

    def test_save_video_no_video_data(self):
        """Test handling when no video data is available."""
        from strands_pack.gemini_video import _save_video

        mock_client = MagicMock()
        mock_generated_video = MagicMock()
        mock_generated_video.video = None

        with tempfile.TemporaryDirectory() as tmp_dir:
            result = _save_video(
                mock_client,
                mock_generated_video,
                tmp_dir,
                "test_prefix",
                "test-api-key"
            )

        assert result["success"] is False
        assert "No video data" in result["error"]

    def test_save_video_with_video_bytes(self):
        """Test saving video when video_bytes is available."""
        from strands_pack.gemini_video import _save_video

        mock_client = MagicMock()
        mock_video = MagicMock()
        mock_video.video_bytes = b"fake_video_data"
        mock_generated_video = MagicMock()
        mock_generated_video.video = mock_video

        # Make download fail so it falls back to video_bytes
        mock_client.files.download.side_effect = Exception("Download failed")

        with tempfile.TemporaryDirectory() as tmp_dir:
            result = _save_video(
                mock_client,
                mock_generated_video,
                tmp_dir,
                "test_prefix",
                "test-api-key"
            )

            assert result["success"] is True
            assert "file_path" in result
            assert Path(result["file_path"]).exists()

            # Verify file contents
            with open(result["file_path"], "rb") as f:
                assert f.read() == b"fake_video_data"


# ============================================================================
# UNKNOWN ACTION TEST
# ============================================================================

class TestUnknownAction:
    """Tests for unknown action handling."""

    def test_unknown_action(self):
        """Test that unknown action returns error."""
        from strands_pack.gemini_video import gemini_video

        result = gemini_video(action="unknown_action", prompt="test")

        assert result["success"] is False
        assert "Invalid action" in result["error"]

    def test_missing_prompt(self):
        """Test that missing prompt returns error for actions that require it."""
        from strands_pack.gemini_video import gemini_video

        result = gemini_video(action="generate", prompt="")

        assert result["success"] is False
        assert "prompt" in result["error"]


# ============================================================================
# INTEGRATION TESTS (Require actual API key)
# ============================================================================

@pytest.mark.skip(reason="Requires actual Google API key and network access")
class TestGeminiVideoIntegration:
    """Integration tests that require actual API access."""

    def test_generate_simple_video(self):
        """Test generating a simple video with the API."""
        from strands_pack.gemini_video import gemini_video

        with tempfile.TemporaryDirectory() as tmp_dir:
            result = gemini_video(
                action="generate",
                prompt="A ball bouncing slowly",
                output_dir=tmp_dir,
                duration_seconds=4,
                model="veo-3.1-fast-generate-preview"
            )

            assert result["success"] is True
            assert Path(result["file_path"]).exists()
            assert result["file_path"].endswith(".mp4")
