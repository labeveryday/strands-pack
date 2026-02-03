"""Tests for utility tools."""

import tempfile
from pathlib import Path


def test_validate_email_valid():
    """Test validating a valid email."""
    from strands_pack import validate_email

    result = validate_email("test@example.com")

    assert result["is_valid"] is True
    assert result["local_part"] == "test"
    assert result["domain"] == "example.com"


def test_validate_email_invalid():
    """Test validating an invalid email."""
    from strands_pack import validate_email

    result = validate_email("invalid-email")

    assert result["is_valid"] is False
    assert "error" in result


def test_validate_email_complex():
    """Test validating complex email formats."""
    from strands_pack import validate_email

    # Valid complex email
    result = validate_email("user.name+tag@subdomain.example.com")
    assert result["is_valid"] is True

    # Invalid - missing @
    result = validate_email("userexample.com")
    assert result["is_valid"] is False


def test_count_lines_in_file():
    """Test counting lines in a file."""
    from strands_pack import count_lines_in_file

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Line 1\n")
        f.write("Line 2\n")
        f.write("\n")
        f.write("Line 4\n")
        temp_path = f.name

    try:
        result = count_lines_in_file(temp_path)

        assert result["success"] is True
        assert result["total_lines"] == 4
        assert result["non_empty_lines"] == 3
        assert result["empty_lines"] == 1
    finally:
        Path(temp_path).unlink()


def test_count_lines_file_not_found():
    """Test counting lines in non-existent file."""
    from strands_pack import count_lines_in_file

    result = count_lines_in_file("/nonexistent/file.txt")

    assert result["success"] is False
    assert "error" in result


def test_divide_numbers():
    """Test dividing numbers."""
    from strands_pack import divide_numbers

    result = divide_numbers(10, 2)

    assert result["success"] is True
    assert result["result"] == 5.0
    assert result["is_integer"] is True


def test_divide_numbers_decimal():
    """Test dividing with decimal result."""
    from strands_pack import divide_numbers

    result = divide_numbers(10, 3)

    assert result["success"] is True
    assert result["is_integer"] is False


def test_divide_by_zero():
    """Test division by zero."""
    from strands_pack import divide_numbers

    result = divide_numbers(10, 0)

    assert result["success"] is False
    assert "error" in result


def test_save_and_load_json():
    """Test saving and loading JSON."""
    from strands_pack import load_json, save_json

    with tempfile.TemporaryDirectory() as tmpdir:
        data = {
            "name": "test",
            "values": [1, 2, 3],
            "nested": {"key": "value"},
        }

        file_path = f"{tmpdir}/test.json"

        # Save
        save_result = save_json(data=data, file_path=file_path)
        assert save_result["success"] is True

        # Load
        load_result = load_json(file_path)
        assert load_result["success"] is True
        assert load_result["data"] == data


def test_load_json_not_found():
    """Test loading non-existent JSON."""
    from strands_pack import load_json

    result = load_json("/nonexistent/file.json")

    assert result["success"] is False


def test_load_json_invalid():
    """Test loading invalid JSON."""
    from strands_pack import load_json

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("this is not json")
        temp_path = f.name

    try:
        result = load_json(temp_path)
        assert result["success"] is False
        assert "Invalid JSON" in result["error"]
    finally:
        Path(temp_path).unlink()


def test_get_env_variable():
    """Test getting environment variables."""
    import os

    from strands_pack import get_env_variable

    # Set a test variable
    os.environ["TEST_VAR_XYZ"] = "test_value"

    try:
        result = get_env_variable("TEST_VAR_XYZ")
        assert result["value"] == "test_value"
        assert result["is_set"] is True
    finally:
        del os.environ["TEST_VAR_XYZ"]


def test_get_env_variable_default():
    """Test getting env variable with default."""
    from strands_pack import get_env_variable

    result = get_env_variable("DEFINITELY_NOT_SET_123", default="default_value")

    assert result["value"] == "default_value"
    assert result["is_set"] is False
    assert result["using_default"] is True


def test_format_timestamp_current():
    """Test formatting current timestamp."""
    from strands_pack import format_timestamp

    result = format_timestamp()

    assert result["success"] is True
    assert "formatted" in result
    assert "iso" in result
    assert result["year"] > 2020


def test_format_timestamp_parse():
    """Test parsing a timestamp."""
    from strands_pack import format_timestamp

    result = format_timestamp(
        timestamp="2024-06-15",
        output_format="%B %d, %Y",
    )

    assert result["success"] is True
    assert result["formatted"] == "June 15, 2024"


def test_format_timestamp_invalid():
    """Test parsing invalid timestamp."""
    from strands_pack import format_timestamp

    result = format_timestamp(timestamp="not-a-date")

    assert result["success"] is False


def test_extract_urls():
    """Test extracting URLs from text."""
    from strands_pack import extract_urls

    text = """
    Check out https://example.com and http://test.org/page for more info.
    Also visit https://github.com/user/repo. That's all!
    """

    result = extract_urls(text)

    assert result["success"] is True
    assert result["count"] == 3
    assert "https://example.com" in result["urls"]
    assert "https://github.com/user/repo" in result["urls"]


def test_extract_urls_empty():
    """Test extracting URLs from text without URLs."""
    from strands_pack import extract_urls

    result = extract_urls("No URLs here at all")

    assert result["success"] is True
    assert result["count"] == 0


def test_word_count_basic():
    """Test basic word count."""
    from strands_pack import word_count

    text = "This is a simple test sentence."

    result = word_count(text)

    assert result["word_count"] == 6
    assert result["sentence_count"] == 1
    assert result["character_count"] == len(text)


def test_word_count_detailed():
    """Test word count with details."""
    from strands_pack import word_count

    text = "The quick brown fox jumps. The fox is fast."

    result = word_count(text, include_details=True)

    assert result["word_count"] == 9
    assert result["sentence_count"] == 2
    assert "avg_word_length" in result
    assert "top_words" in result
    assert result["top_words"]["the"] == 2
    assert result["top_words"]["fox"] == 2
