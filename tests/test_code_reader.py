"""Tests for code reader tool."""

import tempfile
from pathlib import Path


def test_grab_code_file_not_found():
    """Test error handling for missing file."""
    from strands_pack import grab_code

    result = grab_code("/nonexistent/path/to/file.py")
    assert "Error: file not found" in result


def test_grab_code_simple_file():
    """Test reading a simple file."""
    from strands_pack import grab_code

    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("def hello():\n")
        f.write("    print('Hello, World!')\n")
        f.write("\n")
        f.write("hello()\n")
        temp_path = f.name

    try:
        result = grab_code(temp_path)

        assert "File:" in result
        assert "Lines:" in result
        assert "def hello():" in result
        assert "print('Hello, World!')" in result
        assert "```python" in result
    finally:
        Path(temp_path).unlink()


def test_grab_code_with_line_range():
    """Test reading specific lines from a file."""
    from strands_pack import grab_code

    # Create a temporary file with multiple lines
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        for i in range(1, 11):
            f.write(f"line {i}\n")
        temp_path = f.name

    try:
        result = grab_code(temp_path, start_line=3, end_line=5)

        assert "line 3" in result
        assert "line 4" in result
        assert "line 5" in result
        assert "line 1" not in result
        assert "line 6" not in result
    finally:
        Path(temp_path).unlink()


def test_grab_code_without_line_numbers():
    """Test reading without line numbers."""
    from strands_pack import grab_code

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("test content\n")
        temp_path = f.name

    try:
        result = grab_code(temp_path, with_line_numbers=False)

        assert "test content" in result
        # Should not have the line number prefix format
        assert " | " not in result.split("```")[1]  # Check in the code block
    finally:
        Path(temp_path).unlink()


def test_grab_code_invalid_line_range():
    """Test error handling for invalid line range."""
    from strands_pack import grab_code

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("test\n")
        temp_path = f.name

    try:
        result = grab_code(temp_path, start_line=10, end_line=5)
        assert "Error" in result
        assert "end_line" in result
    finally:
        Path(temp_path).unlink()
