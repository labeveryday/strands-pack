"""
Code Reader Tool.

Tools for reading code from files with safety constraints.
Limits output size to keep tool responses manageable.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from strands import tool

_DEFAULT_MAX_BYTES = 250_000  # ~250KB
_DEFAULT_MAX_LINES = 400
_HARD_MAX_FILE_BYTES_WITHOUT_RANGE = 5_000_000  # 5MB


def _guess_language(path: Path) -> str:
    """Guess language from file extension."""
    ext = path.suffix.lower().lstrip(".")
    return {
        "py": "python",
        "js": "javascript",
        "ts": "typescript",
        "tsx": "tsx",
        "jsx": "jsx",
        "json": "json",
        "yaml": "yaml",
        "yml": "yaml",
        "toml": "toml",
        "md": "markdown",
        "sh": "bash",
        "bash": "bash",
        "zsh": "bash",
        "html": "html",
        "css": "css",
        "sql": "sql",
        "txt": "",
        "go": "go",
        "rs": "rust",
        "java": "java",
        "cpp": "cpp",
        "c": "c",
        "h": "c",
        "hpp": "cpp",
        "rb": "ruby",
        "php": "php",
    }.get(ext, "")


@tool
def grab_code(
    path: str,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
    max_lines: int = _DEFAULT_MAX_LINES,
    max_bytes: int = _DEFAULT_MAX_BYTES,
    with_line_numbers: bool = True,
) -> str:
    """
    Read code from a file so you don't have to paste it.

    This tool limits output size to keep tool responses manageable.

    Args:
        path: File path to read. Can be relative or absolute.
        start_line: 1-based starting line (inclusive). Defaults to start of file.
        end_line: 1-based ending line (inclusive). Defaults to end of file.
        max_lines: Maximum number of lines to return (even if a larger range is requested).
        max_bytes: Maximum bytes to read from disk.
        with_line_numbers: If true, prefixes each line with its line number.

    Returns:
        A markdown code block containing the requested file contents.

    Examples:
        >>> grab_code("src/main.py")
        >>> grab_code("src/models/models.py", start_line=120, end_line=220)
    """
    requested = Path(path).expanduser()
    full_path = requested.resolve()

    if not full_path.exists():
        return f"Error: file not found: {path}"
    if not full_path.is_file():
        return f"Error: not a file: {path}"

    s = 1 if start_line is None else max(1, int(start_line))
    e_req = None if end_line is None else max(1, int(end_line))
    if e_req is not None and e_req < s:
        return f"Error: end_line ({e_req}) must be >= start_line ({s})."

    try:
        file_size = full_path.stat().st_size
    except Exception:
        file_size = None

    # If the file is large, require an explicit range to avoid slow accidental reads.
    if file_size is not None and file_size > _HARD_MAX_FILE_BYTES_WITHOUT_RANGE and end_line is None:
        return (
            "Error: file is large; please provide an explicit line range.\n"
            f"File: {full_path}\n"
            f"Size: {file_size} bytes\n"
            "Example: grab_code(path, start_line=1, end_line=200)"
        )

    # Stream read so big files can still be sampled safely (bounded by max_lines/max_bytes).
    collected: list[tuple[int, str]] = []
    total_lines = 0
    approx_bytes = 0
    hit_byte_limit = False

    try:
        with full_path.open("r", encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f, start=1):
                total_lines = i
                if i < s:
                    continue
                if e_req is not None and i > e_req:
                    break

                line = line.rstrip("\n")
                collected.append((i, line))

                approx_bytes += len(line.encode("utf-8", errors="replace")) + 1
                if len(collected) >= max_lines:
                    break
                if approx_bytes >= max_bytes:
                    hit_byte_limit = True
                    break
    except Exception as e:
        return f"Error: failed reading file: {full_path} ({type(e).__name__}: {e})"

    if total_lines == 0:
        return f"Error: file appears to be empty: {full_path}"

    if collected:
        s_out = collected[0][0]
        e_out = collected[-1][0]
    else:
        s_out = s
        e_out = s - 1

    if with_line_numbers:
        width = max(4, len(str(e_out if e_out >= s_out else s_out)))
        snippet_text = "\n".join(f"{i:>{width}} | {line}" for i, line in collected)
    else:
        snippet_text = "\n".join(line for _, line in collected)

    lang = _guess_language(full_path)
    fence = f"```{lang}".rstrip()

    truncated_bits: list[str] = []
    if e_req is None and len(collected) >= max_lines:
        truncated_bits.append(f"Truncated to {max_lines} lines.")
    if hit_byte_limit:
        truncated_bits.append(f"Hit max_bytes={max_bytes}.")

    truncated_note = ""
    if truncated_bits:
        truncated_note = "\n\n(" + " ".join(truncated_bits) + " Use start_line/end_line to narrow further.)"

    return (
        f"File: {full_path}\n"
        f"Lines: {s_out}-{e_out} (of {total_lines})\n\n"
        f"{fence}\n"
        f"{snippet_text}\n"
        "```"
        f"{truncated_note}"
    )
