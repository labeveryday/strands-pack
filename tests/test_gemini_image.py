"""Tests for Gemini image tool (image generation and editing)."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Check if google-genai is installed
try:
    import google.genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False


# ============================================================================
# GEMINI IMAGE HELPER TESTS
# ============================================================================

class TestGeminiImageHelpers:
    """Tests for helper functions in gemini_image module."""

    def test_get_mime_type_png(self):
        """Test MIME type detection for PNG files."""
        from strands_pack.gemini_image import _get_mime_type
        assert _get_mime_type(Path("image.png")) == "image/png"
        assert _get_mime_type(Path("image.PNG")) == "image/png"

    def test_get_mime_type_jpeg(self):
        """Test MIME type detection for JPEG files."""
        from strands_pack.gemini_image import _get_mime_type
        assert _get_mime_type(Path("image.jpg")) == "image/jpeg"
        assert _get_mime_type(Path("image.jpeg")) == "image/jpeg"
        assert _get_mime_type(Path("image.JPEG")) == "image/jpeg"

    def test_get_mime_type_webp(self):
        """Test MIME type detection for WebP files."""
        from strands_pack.gemini_image import _get_mime_type
        assert _get_mime_type(Path("image.webp")) == "image/webp"

    def test_get_mime_type_gif(self):
        """Test MIME type detection for GIF files."""
        from strands_pack.gemini_image import _get_mime_type
        assert _get_mime_type(Path("image.gif")) == "image/gif"

    def test_get_mime_type_unknown_defaults_to_png(self):
        """Test that unknown extensions default to PNG."""
        from strands_pack.gemini_image import _get_mime_type
        assert _get_mime_type(Path("image.bmp")) == "image/png"
        assert _get_mime_type(Path("image.tiff")) == "image/png"

    @pytest.mark.skipif(not HAS_GENAI, reason="google-genai not installed")
    def test_load_image_part_file_not_found(self):
        """Test error handling when image file doesn't exist."""
        from strands_pack.gemini_image import _load_image_part
        with pytest.raises(FileNotFoundError) as exc_info:
            _load_image_part("/nonexistent/path/image.png")
        assert "Image file not found" in str(exc_info.value)


# ============================================================================
# GENERATE IMAGE TESTS
# ============================================================================

class TestGenerateImage:
    """Tests for the generate action."""

    def test_missing_api_key(self):
        """Test error when GOOGLE_API_KEY is not set."""
        from strands_pack import gemini_image

        with patch.dict(os.environ, {}, clear=True):
            # Ensure GOOGLE_API_KEY is not set
            os.environ.pop("GOOGLE_API_KEY", None)
            result = gemini_image(action="generate", prompt="A test image")

        assert result["success"] is False
        assert "GOOGLE_API_KEY" in result["error"]

    def test_image_size_not_supported_for_flash(self):
        """Test that image_size is rejected for Flash model."""
        from strands_pack import gemini_image

        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            result = gemini_image(
                action="generate",
                prompt="A test image",
                model="gemini-2.5-flash-image",
                image_size="2K"
            )

        assert result["success"] is False
        assert "image_size is only supported with gemini-3-pro-image-preview" in result["error"]

    def test_google_search_not_supported_for_flash(self):
        """Test that Google Search is rejected for Flash model."""
        from strands_pack import gemini_image

        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            result = gemini_image(
                action="generate",
                prompt="A test image",
                model="gemini-2.5-flash-image",
                use_google_search=True
            )

        assert result["success"] is False
        assert "Google Search grounding is only supported with gemini-3-pro-image-preview" in result["error"]

    def test_flash_max_reference_images_exceeded(self):
        """Test that Flash model rejects more than 3 reference images."""
        from strands_pack import gemini_image

        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            result = gemini_image(
                action="generate",
                prompt="A test image",
                model="gemini-2.5-flash-image",
                reference_images=["img1.png", "img2.png", "img3.png", "img4.png"]
            )

        assert result["success"] is False
        assert "gemini-2.5-flash-image supports up to 3 reference images" in result["error"]

    def test_max_reference_images_exceeded(self):
        """Test that Pro model rejects more than 14 reference images."""
        from strands_pack import gemini_image

        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            result = gemini_image(
                action="generate",
                prompt="A test image",
                model="gemini-3-pro-image-preview",
                reference_images=[f"img{i}.png" for i in range(15)]
            )

        assert result["success"] is False
        assert "Maximum 14 reference images supported" in result["error"]

    def test_reference_image_not_found(self):
        """Test error when a reference image file doesn't exist."""
        from strands_pack import gemini_image

        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            result = gemini_image(
                action="generate",
                prompt="A test image",
                reference_images=["/nonexistent/image.png"]
            )

        assert result["success"] is False
        assert "Image file not found" in result["error"]

    @pytest.mark.skipif(not HAS_GENAI, reason="google-genai not installed")
    def test_successful_generation(self):
        """Test successful image generation with mocked API."""
        from strands_pack import gemini_image

        # Set up mock response
        mock_client = MagicMock()

        mock_part = MagicMock()
        mock_part.thought = False
        mock_part.inline_data = MagicMock()
        mock_part.inline_data.data = b"fake_image_data"
        mock_part.text = None

        mock_candidate = MagicMock()
        mock_candidate.content.parts = [mock_part]

        mock_response = MagicMock()
        mock_response.parts = None  # Explicitly set to None so candidates path is used
        mock_response.candidates = [mock_candidate]

        mock_client.models.generate_content.return_value = mock_response

        with patch("strands_pack.gemini_image._get_client", return_value=mock_client):
            with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
                with tempfile.TemporaryDirectory() as tmp_dir:
                    result = gemini_image(
                        action="generate",
                        prompt="A beautiful sunset",
                        output_dir=tmp_dir
                    )

                    assert result["success"] is True
                    assert "file_path" in result
                    assert "file_paths" in result
                    assert isinstance(result["file_paths"], list)
                    assert result["model"] == "gemini-3-pro-image-preview"
                    assert Path(result["file_path"]).exists()

    @pytest.mark.skipif(not HAS_GENAI, reason="google-genai not installed")
    def test_output_filename_is_used(self):
        """Test that output_filename controls the saved file name."""
        from strands_pack import gemini_image

        mock_client = MagicMock()

        mock_part = MagicMock()
        mock_part.thought = False
        mock_part.inline_data = MagicMock()
        mock_part.inline_data.data = b"fake_image_data"
        mock_part.text = None

        mock_candidate = MagicMock()
        mock_candidate.content.parts = [mock_part]

        mock_response = MagicMock()
        mock_response.parts = None  # Explicitly set to None so candidates path is used
        mock_response.candidates = [mock_candidate]
        mock_client.models.generate_content.return_value = mock_response

        with patch("strands_pack.gemini_image._get_client", return_value=mock_client):
            with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
                with tempfile.TemporaryDirectory() as tmp_dir:
                    result = gemini_image(
                        action="generate",
                        prompt="A beautiful sunset",
                        output_dir=tmp_dir,
                        output_filename="my_image.png",
                    )

                    assert result["success"] is True
                    assert Path(result["file_path"]).name == "my_image.png"
                    assert Path(result["file_path"]).exists()

    @pytest.mark.skipif(not HAS_GENAI, reason="google-genai not installed")
    def test_num_images_saves_multiple_when_available(self):
        """Test that num_images saves multiple outputs when the API returns multiple images."""
        from strands_pack import gemini_image

        mock_client = MagicMock()

        def make_part(data: bytes):
            p = MagicMock()
            p.thought = False
            p.inline_data = MagicMock()
            p.inline_data.data = data
            p.text = None
            return p

        mock_candidate1 = MagicMock()
        mock_candidate1.content.parts = [make_part(b"img1")]
        mock_candidate2 = MagicMock()
        mock_candidate2.content.parts = [make_part(b"img2")]

        mock_response = MagicMock()
        mock_response.parts = None  # Explicitly set to None so candidates path is used
        mock_response.candidates = [mock_candidate1, mock_candidate2]
        mock_client.models.generate_content.return_value = mock_response

        with patch("strands_pack.gemini_image._get_client", return_value=mock_client):
            with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
                with tempfile.TemporaryDirectory() as tmp_dir:
                    result = gemini_image(
                        action="generate",
                        prompt="A thing",
                        output_dir=tmp_dir,
                        output_filename="multi.png",
                        num_images=2,
                    )

                    assert result["success"] is True
                    assert result["num_images_requested"] == 2
                    assert result["num_images_generated"] == 2
                    assert len(result["file_paths"]) == 2
                    assert Path(result["file_paths"][0]).name == "multi_1.png"
                    assert Path(result["file_paths"][1]).name == "multi_2.png"
                    assert Path(result["file_paths"][0]).exists()
                    assert Path(result["file_paths"][1]).exists()

    @pytest.mark.skipif(not HAS_GENAI, reason="google-genai not installed")
    def test_output_format_requires_pillow(self):
        """Test that requesting non-PNG output without Pillow returns a helpful error."""
        from strands_pack import gemini_image

        mock_client = MagicMock()

        mock_part = MagicMock()
        mock_part.thought = False
        mock_part.inline_data = MagicMock()
        mock_part.inline_data.data = b"fake_image_data"
        mock_part.text = None

        mock_candidate = MagicMock()
        mock_candidate.content.parts = [mock_part]

        mock_response = MagicMock()
        mock_response.parts = None  # Explicitly set to None so candidates path is used
        mock_response.candidates = [mock_candidate]
        mock_client.models.generate_content.return_value = mock_response

        def mock_save_image_bytes(*, image_bytes, file_path, output_format):
            if output_format != "png":
                raise ImportError(
                    "Pillow is required for output_format != 'png'. "
                    "Install with: pip install strands-pack[image]"
                )

        with patch("strands_pack.gemini_image._get_client", return_value=mock_client):
            with patch("strands_pack.gemini_image._save_image_bytes", side_effect=mock_save_image_bytes):
                with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
                    result = gemini_image(action="generate", prompt="A test image", output_format="webp")

                    assert result["success"] is False
                    assert "Pillow is required" in result["error"]

    @pytest.mark.skipif(not HAS_GENAI, reason="google-genai not installed")
    def test_no_image_in_response(self):
        """Test handling when API returns no image data."""
        from strands_pack import gemini_image

        mock_client = MagicMock()

        # Response with text but no image
        mock_part = MagicMock()
        mock_part.thought = False
        mock_part.inline_data = None
        mock_part.text = "I cannot generate that image"

        mock_candidate = MagicMock()
        mock_candidate.content.parts = [mock_part]

        mock_response = MagicMock()
        mock_response.parts = None  # Explicitly set to None so candidates path is used
        mock_response.candidates = [mock_candidate]

        mock_client.models.generate_content.return_value = mock_response

        with patch("strands_pack.gemini_image._get_client", return_value=mock_client):
            with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
                result = gemini_image(action="generate", prompt="A test image")

                assert result["success"] is False
                assert "No image data in response" in result["error"]
                assert result["text_response"] == "I cannot generate that image"

    @pytest.mark.skipif(not HAS_GENAI, reason="google-genai not installed")
    def test_parses_response_parts_when_present(self):
        """Some SDK versions expose response.parts directly; ensure we can parse that too."""
        from strands_pack import gemini_image

        mock_client = MagicMock()

        mock_inline = MagicMock()
        mock_inline.data = b"fake_image_data"

        mock_part_img = MagicMock()
        mock_part_img.thought = False
        mock_part_img.inline_data = mock_inline
        mock_part_img.text = None

        mock_part_txt = MagicMock()
        mock_part_txt.thought = False
        mock_part_txt.inline_data = None
        mock_part_txt.text = "hello"

        mock_response = MagicMock()
        mock_response.parts = [mock_part_txt, mock_part_img]
        mock_response.candidates = None
        mock_client.models.generate_content.return_value = mock_response

        with patch("strands_pack.gemini_image._get_client", return_value=mock_client):
            with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
                with tempfile.TemporaryDirectory() as tmp_dir:
                    result = gemini_image(action="generate", prompt="A test", output_dir=tmp_dir)

                    assert result["success"] is True
                    assert result["text_response"] == "hello"
                    assert Path(result["file_path"]).exists()


# ============================================================================
# EDIT IMAGE TESTS
# ============================================================================

class TestEditImage:
    """Tests for the edit action."""

    def test_missing_api_key(self):
        """Test error when GOOGLE_API_KEY is not set."""
        from strands_pack import gemini_image

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GOOGLE_API_KEY", None)
            result = gemini_image(
                action="edit",
                prompt="Add a hat",
                image_path="/some/image.png"
            )

        assert result["success"] is False
        assert "GOOGLE_API_KEY" in result["error"]

    def test_image_size_not_supported_for_flash(self):
        """Test that image_size is rejected for Flash model."""
        from strands_pack import gemini_image

        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            result = gemini_image(
                action="edit",
                prompt="Add a hat",
                image_path="/some/image.png",
                model="gemini-2.5-flash-image",
                image_size="4K"
            )

        assert result["success"] is False
        assert "image_size is only supported with gemini-3-pro-image-preview" in result["error"]

    def test_primary_image_not_found(self):
        """Test error when primary image file doesn't exist."""
        from strands_pack import gemini_image

        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            result = gemini_image(
                action="edit",
                prompt="Add a hat",
                image_path="/nonexistent/image.png"
            )

        assert result["success"] is False
        assert "Image file not found" in result["error"]

    def test_missing_image_path(self):
        """Test that edit action requires image_path parameter."""
        from strands_pack import gemini_image

        result = gemini_image(action="edit", prompt="Add a hat")

        assert result["success"] is False
        assert "image_path" in result["error"]

    @pytest.mark.skipif(not HAS_GENAI, reason="google-genai not installed")
    def test_edit_num_images_saves_multiple_when_available(self):
        """Test that edit supports saving multiple outputs when available."""
        from strands_pack import gemini_image

        mock_client = MagicMock()

        def make_part(data: bytes):
            p = MagicMock()
            p.thought = False
            p.inline_data = MagicMock()
            p.inline_data.data = data
            p.text = None
            return p

        mock_candidate1 = MagicMock()
        mock_candidate1.content.parts = [make_part(b"img1")]
        mock_candidate2 = MagicMock()
        mock_candidate2.content.parts = [make_part(b"img2")]

        mock_response = MagicMock()
        mock_response.parts = None  # Explicitly set to None so candidates path is used
        mock_response.candidates = [mock_candidate1, mock_candidate2]
        mock_client.models.generate_content.return_value = mock_response

        with patch("strands_pack.gemini_image._get_client", return_value=mock_client):
            with patch("strands_pack.gemini_image._load_image_part", return_value="IMAGE_PART"):
                with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
                    with tempfile.TemporaryDirectory() as tmp_dir:
                        result = gemini_image(
                            action="edit",
                            prompt="Add a hat",
                            image_path="/some/image.png",
                            output_dir=tmp_dir,
                            output_filename="edit.png",
                            num_images=2,
                        )

                        assert result["success"] is True
                        assert result["num_images_requested"] == 2
                        assert result["num_images_generated"] == 2
                        assert Path(result["file_paths"][0]).name == "edit_1.png"
                        assert Path(result["file_paths"][1]).name == "edit_2.png"


class TestGeminiImageChat:
    """Tests for chat/close_chat actions."""

    def test_chat_requires_prompt(self):
        from strands_pack import gemini_image
        result = gemini_image(action="chat")
        assert result["success"] is False
        assert "prompt" in result["error"]

    def test_close_chat_requires_chat_id(self):
        from strands_pack import gemini_image
        result = gemini_image(action="close_chat")
        assert result["success"] is False
        assert "chat_id" in result["error"]

    @pytest.mark.skipif(not HAS_GENAI, reason="google-genai not installed")
    def test_chat_and_close_chat_success(self):
        import importlib
        from strands_pack import gemini_image

        # Get the actual module (not the decorated tool)
        gi_module = importlib.import_module('strands_pack.gemini_image')

        # Clear any existing chats
        gi_module._CHATS.clear()

        # Arrange fake genai chat
        mock_client = MagicMock()

        # chat.send_message returns a response with candidates[0].content.parts
        mock_inline = MagicMock()
        mock_inline.data = b"fake_image_data"
        mock_part = MagicMock()
        mock_part.thought = False
        mock_part.inline_data = mock_inline
        mock_part.text = None

        mock_candidate = MagicMock()
        mock_candidate.content.parts = [mock_part]

        mock_response = MagicMock()
        mock_response.parts = None
        mock_response.candidates = [mock_candidate]

        mock_chat = MagicMock()
        mock_chat.send_message.return_value = mock_response
        mock_client.chats.create.return_value = mock_chat

        with patch("strands_pack.gemini_image._get_client", return_value=mock_client):
            with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
                with tempfile.TemporaryDirectory() as tmp_dir:
                    r1 = gemini_image(action="chat", prompt="make an infographic", output_dir=tmp_dir, output_filename="c.png")
                    assert r1["success"] is True
                    assert r1["action"] == "chat"
                    assert r1["chat_id"]

                    r2 = gemini_image(action="close_chat", chat_id=r1["chat_id"])
                    assert r2["success"] is True
                    assert r2["closed"] is True


# ============================================================================
# UNKNOWN ACTION TEST
# ============================================================================

class TestUnknownAction:
    """Tests for unknown action handling."""

    def test_unknown_action(self):
        """Test that unknown action returns error."""
        from strands_pack import gemini_image

        result = gemini_image(action="unknown_action", prompt="test")

        assert result["success"] is False
        assert "Invalid action" in result["error"]


# ============================================================================
# INTEGRATION TESTS (Require actual API key)
# ============================================================================

@pytest.mark.skip(reason="Requires actual Google API key and network access")
class TestGeminiImageIntegration:
    """Integration tests that require actual API access."""

    def test_generate_simple_image(self):
        """Test generating a simple image with the API."""
        from strands_pack import gemini_image

        with tempfile.TemporaryDirectory() as tmp_dir:
            result = gemini_image(
                action="generate",
                prompt="A simple red circle on a white background",
                output_dir=tmp_dir,
                aspect_ratio="1:1"
            )

            assert result["success"] is True
            assert Path(result["file_path"]).exists()
            assert result["file_path"].endswith(".png")
