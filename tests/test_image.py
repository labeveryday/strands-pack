"""Tests for image tool."""

import os
import tempfile

import pytest


@pytest.fixture
def test_image_path():
    """Create a simple test image."""
    try:
        from PIL import Image
    except ImportError:
        pytest.skip("Pillow not installed")

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img = Image.new("RGB", (200, 100), color="red")
        img.save(f.name)
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def output_dir():
    """Create a temp directory for output files."""
    with tempfile.TemporaryDirectory() as d:
        yield d


def test_image_get_info(test_image_path):
    """Test getting image info."""
    from strands_pack import image

    result = image(action="get_info", input_path=test_image_path)

    assert result["success"] is True
    assert result["action"] == "get_info"
    assert result["width"] == 200
    assert result["height"] == 100
    assert result["format"] == "PNG"
    assert result["mode"] == "RGB"


def test_image_resize(test_image_path, output_dir):
    """Test resizing an image."""
    from strands_pack import image

    output_path = os.path.join(output_dir, "resized.png")
    result = image(
        action="resize",
        input_path=test_image_path,
        output_path=output_path,
        width=100,
        maintain_aspect=True
    )

    assert result["success"] is True
    assert result["action"] == "resize"
    assert os.path.exists(output_path)
    assert result["new_size"][0] == 100
    # Aspect ratio maintained: 100/200 * 100 = 50
    assert result["new_size"][1] == 50


def test_image_resize_no_aspect(test_image_path, output_dir):
    """Test resizing without maintaining aspect ratio."""
    from strands_pack import image

    output_path = os.path.join(output_dir, "resized.png")
    result = image(
        action="resize",
        input_path=test_image_path,
        output_path=output_path,
        width=150,
        height=150,
        maintain_aspect=False
    )

    assert result["success"] is True
    assert result["new_size"] == [150, 150]


def test_image_crop(test_image_path, output_dir):
    """Test cropping an image."""
    from strands_pack import image

    output_path = os.path.join(output_dir, "cropped.png")
    result = image(
        action="crop",
        input_path=test_image_path,
        output_path=output_path,
        box=[10, 10, 110, 60]
    )

    assert result["success"] is True
    assert result["action"] == "crop"
    assert os.path.exists(output_path)
    assert result["new_size"] == [100, 50]


def test_image_rotate(test_image_path, output_dir):
    """Test rotating an image."""
    from strands_pack import image

    output_path = os.path.join(output_dir, "rotated.png")
    result = image(
        action="rotate",
        input_path=test_image_path,
        output_path=output_path,
        angle=90,
        expand=True
    )

    assert result["success"] is True
    assert result["action"] == "rotate"
    assert os.path.exists(output_path)
    # After 90 degree rotation with expand, dimensions swap
    assert result["new_size"][0] == 100
    assert result["new_size"][1] == 200


def test_image_flip(test_image_path, output_dir):
    """Test flipping an image."""
    from strands_pack import image

    output_path = os.path.join(output_dir, "flipped.png")
    result = image(
        action="flip",
        input_path=test_image_path,
        output_path=output_path,
        direction="horizontal"
    )

    assert result["success"] is True
    assert result["action"] == "flip"
    assert result["direction"] == "horizontal"
    assert os.path.exists(output_path)


def test_image_blur(test_image_path, output_dir):
    """Test blurring an image."""
    from strands_pack import image

    output_path = os.path.join(output_dir, "blurred.png")
    result = image(
        action="blur",
        input_path=test_image_path,
        output_path=output_path,
        radius=5
    )

    assert result["success"] is True
    assert result["action"] == "blur"
    assert result["radius"] == 5
    assert os.path.exists(output_path)


def test_image_thumbnail(test_image_path, output_dir):
    """Test creating a thumbnail."""
    from strands_pack import image

    output_path = os.path.join(output_dir, "thumb.png")
    result = image(
        action="thumbnail",
        input_path=test_image_path,
        output_path=output_path,
        size=[50, 50]
    )

    assert result["success"] is True
    assert result["action"] == "thumbnail"
    assert os.path.exists(output_path)
    # Thumbnail maintains aspect ratio, so won't be exactly 50x50
    assert result["new_size"][0] <= 50
    assert result["new_size"][1] <= 50


def test_image_convert(test_image_path, output_dir):
    """Test converting image format."""
    from strands_pack import image

    output_path = os.path.join(output_dir, "converted.jpg")
    result = image(
        action="convert",
        input_path=test_image_path,
        output_path=output_path
    )

    assert result["success"] is True
    assert result["action"] == "convert"
    assert os.path.exists(output_path)


def test_image_compress(test_image_path, output_dir):
    """Test compressing an image."""
    from strands_pack import image

    output_path = os.path.join(output_dir, "compressed.jpg")
    result = image(
        action="compress",
        input_path=test_image_path,
        output_path=output_path,
        quality=50
    )

    assert result["success"] is True
    assert result["action"] == "compress"
    assert result["quality"] == 50
    assert os.path.exists(output_path)


def test_image_add_text(test_image_path, output_dir):
    """Test adding text to an image."""
    from strands_pack import image

    output_path = os.path.join(output_dir, "text.png")
    result = image(
        action="add_text",
        input_path=test_image_path,
        output_path=output_path,
        text="Hello",
        position=[10, 10],
        color="white"
    )

    assert result["success"] is True
    assert result["action"] == "add_text"
    assert result["text"] == "Hello"
    assert os.path.exists(output_path)


def test_image_missing_input():
    """Test error when input file is missing."""
    from strands_pack import image

    result = image(action="get_info", input_path="/nonexistent/file.png")

    assert result["success"] is False
    assert "not found" in result["error"]


def test_image_missing_action_param():
    """Test error when required params are missing."""
    from strands_pack import image

    result = image(action="resize", input_path="test.png")

    assert result["success"] is False
    assert "not found" in result["error"] or "required" in result["error"]


def test_image_unknown_action():
    """Test error for unknown action."""
    from strands_pack import image

    result = image(action="unknown_action")

    assert result["success"] is False
    assert "Unknown action" in result["error"]
    assert "available_actions" in result


def test_image_flip_invalid_direction(test_image_path, output_dir):
    """Test error for invalid flip direction."""
    from strands_pack import image

    output_path = os.path.join(output_dir, "flipped.png")
    result = image(
        action="flip",
        input_path=test_image_path,
        output_path=output_path,
        direction="diagonal"
    )

    assert result["success"] is False
    assert "horizontal" in result["error"] or "vertical" in result["error"]


def test_image_crop_missing_box(test_image_path, output_dir):
    """Test error when crop box is missing."""
    from strands_pack import image

    output_path = os.path.join(output_dir, "cropped.png")
    result = image(
        action="crop",
        input_path=test_image_path,
        output_path=output_path
    )

    assert result["success"] is False
    assert "box" in result["error"]


def test_image_grayscale(test_image_path, output_dir):
    """Test converting to grayscale."""
    from strands_pack import image

    output_path = os.path.join(output_dir, "gray.png")
    result = image(action="grayscale", input_path=test_image_path, output_path=output_path)

    assert result["success"] is True
    assert result["action"] == "grayscale"
    assert os.path.exists(output_path)


def test_image_brightness(test_image_path, output_dir):
    """Test adjusting brightness."""
    from strands_pack import image

    output_path = os.path.join(output_dir, "bright.png")
    result = image(action="brightness", input_path=test_image_path, output_path=output_path, factor=1.5)

    assert result["success"] is True
    assert result["action"] == "brightness"
    assert result["factor"] == 1.5
    assert os.path.exists(output_path)


def test_image_contrast(test_image_path, output_dir):
    """Test adjusting contrast."""
    from strands_pack import image

    output_path = os.path.join(output_dir, "contrast.png")
    result = image(action="contrast", input_path=test_image_path, output_path=output_path, factor=1.25)

    assert result["success"] is True
    assert result["action"] == "contrast"
    assert result["factor"] == 1.25
    assert os.path.exists(output_path)


def test_image_sharpen(test_image_path, output_dir):
    """Test sharpening an image."""
    from strands_pack import image

    output_path = os.path.join(output_dir, "sharpen.png")
    result = image(action="sharpen", input_path=test_image_path, output_path=output_path, sharpen_radius=2.0)

    assert result["success"] is True
    assert result["action"] == "sharpen"
    assert os.path.exists(output_path)
