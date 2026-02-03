"""
Utility Tools

A collection of general-purpose utility tools for common operations.

Available Tools:
    validate_email      - Validate email address format
    count_lines_in_file - Count lines in a text file
    divide_numbers      - Safely divide two numbers
    save_json           - Save data to JSON file
    load_json           - Load data from JSON file
    get_env_variable    - Get environment variable value
    format_timestamp    - Format timestamps
    extract_urls        - Extract URLs from text
    word_count          - Count words and characters

Usage Examples:
    from strands import Agent
    from strands_pack import validate_email, word_count, save_json

    agent = Agent(tools=[validate_email, word_count, save_json])

    # Validate an email
    agent.tool.validate_email(email="user@example.com")

    # Count words
    agent.tool.word_count(text="Hello world", include_details=True)

    # Save JSON
    agent.tool.save_json(data={"key": "value"}, file_path="output.json")
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path

from strands import tool


@tool
def validate_email(email: str) -> dict:
    """
    Validate an email address format.

    Args:
        email: The email address to validate.

    Returns:
        dict with validation result and details.
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    is_valid = bool(re.match(pattern, email))

    result = {
        "email": email,
        "is_valid": is_valid,
    }

    if is_valid:
        parts = email.split("@")
        result["local_part"] = parts[0]
        result["domain"] = parts[1]
    else:
        result["error"] = "Invalid email format"

    return result


@tool
def count_lines_in_file(file_path: str) -> dict:
    """
    Count lines in a text file.

    Args:
        file_path: Path to the file.

    Returns:
        dict with line count and file info.
    """
    try:
        path = Path(file_path)

        if not path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}

        if not path.is_file():
            return {"success": False, "error": f"Not a file: {file_path}"}

        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        non_empty_lines = [l for l in lines if l.strip()]

        return {
            "success": True,
            "file_path": str(path.absolute()),
            "total_lines": len(lines),
            "non_empty_lines": len(non_empty_lines),
            "empty_lines": len(lines) - len(non_empty_lines),
            "file_size_bytes": path.stat().st_size,
        }

    except UnicodeDecodeError:
        return {"success": False, "error": "File is not a text file"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def divide_numbers(numerator: float, denominator: float) -> dict:
    """
    Safely divide two numbers with error handling.

    Args:
        numerator: The number to be divided.
        denominator: The number to divide by.

    Returns:
        dict with result and details.
    """
    if denominator == 0:
        return {
            "success": False,
            "error": "Division by zero is not allowed",
            "numerator": numerator,
            "denominator": denominator,
        }

    result = numerator / denominator

    return {
        "success": True,
        "result": result,
        "numerator": numerator,
        "denominator": denominator,
        "is_integer": result == int(result),
    }


@tool
def save_json(data: dict, file_path: str, pretty: bool = True) -> dict:
    """
    Save data to a JSON file.

    Args:
        data: Dictionary data to save.
        file_path: Output file path.
        pretty: Whether to format JSON with indentation.

    Returns:
        dict with success status and file info.
    """
    try:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            if pretty:
                json.dump(data, f, indent=2, ensure_ascii=False)
            else:
                json.dump(data, f, ensure_ascii=False)

        return {
            "success": True,
            "file_path": str(path.absolute()),
            "size_bytes": path.stat().st_size,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def load_json(file_path: str) -> dict:
    """
    Load data from a JSON file.

    Args:
        file_path: Path to JSON file.

    Returns:
        dict with success status and loaded data.
    """
    try:
        path = Path(file_path)

        if not path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return {
            "success": True,
            "file_path": str(path.absolute()),
            "data": data,
        }

    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid JSON: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def get_env_variable(name: str, default: str = None) -> dict:
    """
    Get an environment variable value.

    Args:
        name: Name of the environment variable.
        default: Default value if not found.

    Returns:
        dict with variable name and value.
    """
    value = os.environ.get(name, default)

    return {
        "name": name,
        "value": value,
        "is_set": name in os.environ,
        "using_default": name not in os.environ and default is not None,
    }


@tool
def format_timestamp(
    timestamp: str = None,
    input_format: str = None,
    output_format: str = "%Y-%m-%d %H:%M:%S",
) -> dict:
    """
    Format a timestamp or get the current time.

    Args:
        timestamp: Input timestamp string (None for current time).
        input_format: Format of input timestamp (auto-detect if None).
        output_format: Desired output format.

    Returns:
        dict with formatted timestamp and details.
    """
    try:
        if timestamp is None:
            dt = datetime.now()
        else:
            if input_format:
                dt = datetime.strptime(timestamp, input_format)
            else:
                # Try common formats
                formats = [
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%dT%H:%M:%SZ",
                    "%Y-%m-%d",
                    "%d/%m/%Y",
                    "%m/%d/%Y",
                ]
                dt = None
                for fmt in formats:
                    try:
                        dt = datetime.strptime(timestamp, fmt)
                        break
                    except ValueError:
                        continue

                if dt is None:
                    return {
                        "success": False,
                        "error": f"Could not parse timestamp: {timestamp}",
                    }

        formatted = dt.strftime(output_format)

        return {
            "success": True,
            "formatted": formatted,
            "iso": dt.isoformat(),
            "timestamp": dt.timestamp(),
            "year": dt.year,
            "month": dt.month,
            "day": dt.day,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def extract_urls(text: str) -> dict:
    """
    Extract all URLs from a text string.

    Args:
        text: Text containing URLs.

    Returns:
        dict with list of found URLs.
    """
    # URL pattern matching http, https, and www
    pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'

    urls = re.findall(pattern, text)

    # Clean up URLs (remove trailing punctuation)
    cleaned = []
    for url in urls:
        while url and url[-1] in ".,;:!?)":
            url = url[:-1]
        if url:
            cleaned.append(url)

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for url in cleaned:
        if url not in seen:
            seen.add(url)
            unique.append(url)

    return {
        "success": True,
        "urls": unique,
        "count": len(unique),
    }


@tool
def word_count(text: str, include_details: bool = False) -> dict:
    """
    Count words, characters, and sentences in text.

    Args:
        text: Text to analyze.
        include_details: Whether to include detailed breakdown.

    Returns:
        dict with word count and optional details.
    """
    words = text.split()
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    result = {
        "word_count": len(words),
        "character_count": len(text),
        "character_count_no_spaces": len(text.replace(" ", "")),
        "sentence_count": len(sentences),
    }

    if include_details:
        # Word frequency
        word_freq = {}
        for word in words:
            word_lower = word.lower().strip(".,!?;:")
            if word_lower:
                word_freq[word_lower] = word_freq.get(word_lower, 0) + 1

        # Top 10 words
        top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]

        result["avg_word_length"] = sum(len(w) for w in words) / len(words) if words else 0
        result["avg_sentence_length"] = len(words) / len(sentences) if sentences else 0
        result["top_words"] = dict(top_words)

    return result
