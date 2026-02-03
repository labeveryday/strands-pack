"""Tests for QR code tool."""

import os
import tempfile

import pytest


@pytest.fixture
def output_dir():
    """Create a temp directory for output files."""
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def sample_qr_path(output_dir):
    """Create a sample QR code for testing decode operations."""
    try:
        import qrcode
    except ImportError:
        pytest.skip("qrcode not installed")

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data("https://example.com")
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    path = os.path.join(output_dir, "sample_qr.png")
    img.save(path)
    return path


def test_qrcode_generate(output_dir):
    """Test generating a QR code."""
    from strands_pack import qrcode_tool

    output_path = os.path.join(output_dir, "test_qr.png")
    result = qrcode_tool(
        action="generate",
        data="Hello, World!",
        output_path=output_path,
    )

    assert result["success"] is True
    assert result["action"] == "generate"
    assert os.path.exists(output_path)
    assert result["data_length"] == len("Hello, World!")


def test_qrcode_generate_with_options(output_dir):
    """Test generating a QR code with custom options."""
    from strands_pack import qrcode_tool

    output_path = os.path.join(output_dir, "test_qr_custom.png")
    result = qrcode_tool(
        action="generate",
        data="Test data",
        output_path=output_path,
        size=15,
        error_correction="H",
        border=2,
    )

    assert result["success"] is True
    assert result["size"] == 15
    assert result["error_correction"] == "H"
    assert result["border"] == 2


def test_qrcode_generate_styled(output_dir):
    """Test generating a styled QR code."""
    from strands_pack import qrcode_tool

    output_path = os.path.join(output_dir, "styled_qr.png")
    result = qrcode_tool(
        action="generate_styled",
        data="Styled QR",
        output_path=output_path,
        fill_color="blue",
        back_color="yellow",
    )

    assert result["success"] is True
    assert result["action"] == "generate_styled"
    assert result["fill_color"] == "blue"
    assert result["back_color"] == "yellow"
    assert result["has_logo"] is False


def test_qrcode_decode(sample_qr_path):
    """Test decoding a QR code."""
    try:
        from pyzbar import pyzbar
    except ImportError:
        pytest.skip("pyzbar not installed")

    from strands_pack import qrcode_tool

    result = qrcode_tool(action="decode", input_path=sample_qr_path)

    assert result["success"] is True
    assert result["action"] == "decode"
    assert result["found"] is True
    assert result["data"] == "https://example.com"
    assert result["type"] == "QRCODE"


def test_qrcode_decode_all(sample_qr_path):
    """Test decoding all QR codes in an image."""
    try:
        from pyzbar import pyzbar
    except ImportError:
        pytest.skip("pyzbar not installed")

    from strands_pack import qrcode_tool

    result = qrcode_tool(action="decode_all", input_path=sample_qr_path)

    assert result["success"] is True
    assert result["action"] == "decode_all"
    assert result["count"] >= 1
    assert len(result["codes"]) >= 1


def test_qrcode_generate_svg(output_dir):
    """Test generating a QR code as SVG."""
    from strands_pack import qrcode_tool

    output_path = os.path.join(output_dir, "test_qr.svg")
    result = qrcode_tool(
        action="generate_svg",
        data="SVG QR Code",
        output_path=output_path,
    )

    assert result["success"] is True
    assert result["action"] == "generate_svg"
    assert os.path.exists(output_path)


def test_qrcode_get_info(sample_qr_path):
    """Test getting QR code info."""
    try:
        from pyzbar import pyzbar
    except ImportError:
        pytest.skip("pyzbar not installed")

    from strands_pack import qrcode_tool

    result = qrcode_tool(action="get_info", input_path=sample_qr_path)

    assert result["success"] is True
    assert result["action"] == "get_info"
    assert "image_size" in result
    assert "codes_found" in result


def test_qrcode_missing_data(output_dir):
    """Test error when data is missing."""
    from strands_pack import qrcode_tool

    output_path = os.path.join(output_dir, "test.png")
    result = qrcode_tool(action="generate", output_path=output_path)

    assert result["success"] is False
    assert "data" in result["error"]


def test_qrcode_missing_input_path():
    """Test error when input path is missing for decode."""
    from strands_pack import qrcode_tool

    result = qrcode_tool(action="decode")

    assert result["success"] is False
    assert "input_path" in result["error"]


def test_qrcode_file_not_found():
    """Test error when input file doesn't exist."""
    from strands_pack import qrcode_tool

    result = qrcode_tool(action="decode", input_path="/nonexistent/file.png")

    assert result["success"] is False
    assert "not found" in result["error"].lower()


def test_qrcode_unknown_action():
    """Test error for unknown action."""
    from strands_pack import qrcode_tool

    result = qrcode_tool(action="unknown_action")

    assert result["success"] is False
    assert "Unknown action" in result["error"]
    assert "available_actions" in result
