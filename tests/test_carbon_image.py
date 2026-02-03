"""Tests for carbon tool."""

import pytest


def test_list_carbon_themes():
    """Test listing available themes."""
    from strands_pack import carbon

    result = carbon(action="list_themes")

    assert result["success"] is True
    assert "themes" in result
    assert "recommended" in result
    assert "default" in result
    assert result["default"] == "seti"
    assert "dracula" in result["themes"]
    assert "monokai" in result["themes"]
    assert len(result["themes"]) > 20


def test_list_carbon_themes_categories():
    """Test that recommended themes have categories."""
    from strands_pack import carbon

    result = carbon(action="list_themes")

    assert result["success"] is True
    assert "dark_professional" in result["recommended"]
    assert "dark_vibrant" in result["recommended"]
    assert "light" in result["recommended"]
    assert "retro" in result["recommended"]
    assert "minimal" in result["recommended"]


def test_generate_missing_code():
    """Test that generate action requires code parameter."""
    from strands_pack import carbon

    result = carbon(action="generate")

    assert result["success"] is False
    assert "code" in result["error"].lower()


def test_generate_from_file_missing_path():
    """Test that generate_from_file action requires file_path parameter."""
    from strands_pack import carbon

    result = carbon(action="generate_from_file")

    assert result["success"] is False
    assert "file_path" in result["error"].lower()


def test_generate_from_file_not_found():
    """Test that generate_from_file returns error for non-existent file."""
    from strands_pack import carbon

    result = carbon(action="generate_from_file", file_path="/nonexistent/script.py")

    assert result["success"] is False
    assert "not found" in result["error"].lower()


def test_unknown_action():
    """Test that unknown action returns error."""
    from strands_pack import carbon

    result = carbon(action="unknown_action")

    assert result["success"] is False
    assert "unknown action" in result["error"].lower()


# Note: generate and generate_from_file tests require playwright to be installed
# These tests are marked as skipped by default

@pytest.mark.skip(reason="Requires playwright browser")
def test_generate_code_image():
    """Test generating a code image."""
    from strands_pack import carbon

    result = carbon(
        action="generate",
        code='print("Hello, World!")',
        language="python",
        output_dir="/tmp/test_carbon"
    )

    assert "success" in result
    # May fail if playwright not installed
    if result["success"]:
        assert "file_path" in result
        assert "url" in result
