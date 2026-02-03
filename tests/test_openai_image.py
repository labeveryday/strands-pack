"""Tests for GPT Image tool."""

import base64
import os
import tempfile
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def test_image_path():
    """Create a simple test image."""
    try:
        from PIL import Image
    except ImportError:
        pytest.skip("Pillow not installed")

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img = Image.new("RGB", (200, 200), color="blue")
        img.save(f.name)
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def output_dir():
    """Create a temp directory for output files."""
    with tempfile.TemporaryDirectory() as d:
        yield d


class TestGptImageHelpers:
    """Test helper functions."""

    def test_get_mime_type_png(self):
        from strands_pack.openai_image import _get_mime_type
        from pathlib import Path
        assert _get_mime_type(Path("test.png")) == "image/png"

    def test_get_mime_type_jpeg(self):
        from strands_pack.openai_image import _get_mime_type
        from pathlib import Path
        assert _get_mime_type(Path("test.jpg")) == "image/jpeg"
        assert _get_mime_type(Path("test.jpeg")) == "image/jpeg"

    def test_get_mime_type_webp(self):
        from strands_pack.openai_image import _get_mime_type
        from pathlib import Path
        assert _get_mime_type(Path("test.webp")) == "image/webp"

    def test_enhance_prompt_with_style(self):
        from strands_pack.openai_image import _enhance_prompt
        result = _enhance_prompt("a cat", "photorealistic")
        assert "photorealistic" in result
        assert "a cat" in result

    def test_enhance_prompt_no_style(self):
        from strands_pack.openai_image import _enhance_prompt
        result = _enhance_prompt("a cat", None)
        assert result == "a cat"

    def test_enhance_prompt_custom_style(self):
        from strands_pack.openai_image import _enhance_prompt
        result = _enhance_prompt("a cat", "my custom style")
        assert "my custom style" in result


class TestGenerateImage:
    """Test generate action."""

    def test_missing_api_key(self):
        from strands_pack import openai_image

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("OPENAI_API_KEY", None)
            result = openai_image(action="generate", prompt="test")
            assert result["success"] is False
            assert "OPENAI_API_KEY" in result["error"]

    def test_missing_prompt(self):
        from strands_pack import openai_image

        result = openai_image(action="generate")
        assert result["success"] is False
        assert "prompt" in result["error"]

    def test_invalid_num_images(self):
        from strands_pack import openai_image

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            result = openai_image(action="generate", prompt="test", num_images=5)
            assert result["success"] is False
            assert "num_images" in result["error"]

    @patch("strands_pack.openai_image._get_client")
    def test_successful_generation(self, mock_get_client, output_dir):
        from strands_pack import openai_image

        # Create mock response
        mock_image_data = MagicMock()
        mock_image_data.b64_json = base64.b64encode(b"fake image data").decode()
        mock_image_data.url = None

        mock_response = MagicMock()
        mock_response.data = [mock_image_data]

        mock_client = MagicMock()
        mock_client.images.generate.return_value = mock_response
        mock_get_client.return_value = mock_client

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            result = openai_image(
                action="generate",
                prompt="a sunset",
                output_dir=output_dir,
                output_filename="test_gen"
            )

        assert result["success"] is True
        assert result["action"] == "generate"
        assert "file_path" in result
        assert result["num_images_generated"] == 1


class TestEditImage:
    """Test edit action."""

    def test_missing_api_key(self, test_image_path):
        from strands_pack import openai_image

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("OPENAI_API_KEY", None)
            result = openai_image(action="edit", prompt="add hat", image_path=test_image_path)
            assert result["success"] is False
            assert "OPENAI_API_KEY" in result["error"]

    def test_missing_image_path(self):
        from strands_pack import openai_image

        result = openai_image(action="edit", prompt="add hat")
        assert result["success"] is False
        assert "image_path" in result["error"]

    def test_missing_prompt(self, test_image_path):
        from strands_pack import openai_image

        result = openai_image(action="edit", image_path=test_image_path)
        assert result["success"] is False
        assert "prompt" in result["error"]

    def test_image_not_found(self):
        from strands_pack import openai_image

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            result = openai_image(action="edit", prompt="test", image_path="/nonexistent/image.png")
            assert result["success"] is False
            assert "not found" in result["error"]


class TestAnalyzeImage:
    """Test analyze action."""

    def test_missing_api_key(self, test_image_path):
        from strands_pack import openai_image

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("OPENAI_API_KEY", None)
            result = openai_image(action="analyze", image_path=test_image_path)
            assert result["success"] is False
            assert "OPENAI_API_KEY" in result["error"]

    def test_missing_image_path(self):
        from strands_pack import openai_image

        result = openai_image(action="analyze")
        assert result["success"] is False
        assert "image_path" in result["error"]

    def test_image_not_found(self):
        from strands_pack import openai_image

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            result = openai_image(action="analyze", image_path="/nonexistent/image.png")
            assert result["success"] is False
            assert "not found" in result["error"]

    @patch("strands_pack.openai_image._get_client")
    def test_successful_analysis(self, mock_get_client, test_image_path):
        from strands_pack import openai_image

        # Mock GPT-4o response
        mock_message = MagicMock()
        mock_message.content = "Effectiveness score: 7/10. This image has good contrast..."

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            result = openai_image(action="analyze", image_path=test_image_path, platform="youtube")

        assert result["success"] is True
        assert result["action"] == "analyze"
        assert "analysis" in result
        assert result["effectiveness_score"] == 7.0


class TestOptimizeImage:
    """Test optimize action."""

    def test_missing_image_path(self):
        from strands_pack import openai_image

        result = openai_image(action="optimize", platform="youtube")
        assert result["success"] is False
        assert "image_path" in result["error"]

    def test_image_not_found(self):
        from strands_pack import openai_image

        result = openai_image(action="optimize", image_path="/nonexistent/image.png", platform="youtube")
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_unknown_platform(self, test_image_path, output_dir):
        from strands_pack import openai_image

        result = openai_image(
            action="optimize",
            image_path=test_image_path,
            platform="unknown_platform",
            output_dir=output_dir
        )
        assert result["success"] is False
        assert "Unknown platform" in result["error"]

    def test_successful_optimization(self, test_image_path, output_dir):
        from strands_pack import openai_image

        result = openai_image(
            action="optimize",
            image_path=test_image_path,
            platform="youtube",
            output_dir=output_dir
        )

        assert result["success"] is True
        assert result["action"] == "optimize"
        assert result["platform"] == "youtube"
        assert result["size"] == "1792x1024"
        assert os.path.exists(result["file_path"])

    def test_optimization_instagram(self, test_image_path, output_dir):
        from strands_pack import openai_image

        result = openai_image(
            action="optimize",
            image_path=test_image_path,
            platform="instagram",
            output_dir=output_dir
        )

        assert result["success"] is True
        assert result["size"] == "1024x1024"


class TestVariations:
    """Test variations action."""

    def test_missing_image_path(self):
        from strands_pack import openai_image

        result = openai_image(action="variations")
        assert result["success"] is False
        assert "image_path" in result["error"]

    def test_missing_api_key(self, test_image_path):
        from strands_pack import openai_image

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("OPENAI_API_KEY", None)
            result = openai_image(action="variations", image_path=test_image_path)
            assert result["success"] is False
            assert "OPENAI_API_KEY" in result["error"]

    def test_invalid_num_images(self, test_image_path):
        from strands_pack import openai_image

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            result = openai_image(action="variations", image_path=test_image_path, num_images=5)
            assert result["success"] is False
            assert "num_images" in result["error"]


class TestUnknownAction:
    """Test unknown action handling."""

    def test_unknown_action(self):
        from strands_pack import openai_image

        result = openai_image(action="unknown_action")
        assert result["success"] is False
        assert "Unknown action" in result["error"]
        assert "available_actions" in result
