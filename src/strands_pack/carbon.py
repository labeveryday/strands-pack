"""
Carbon Tool

Generate beautiful code screenshots using Carbon.now.sh.

Usage Examples:
    from strands import Agent
    from strands_pack import carbon

    agent = Agent(tools=[carbon])

    # Generate code image from string
    agent.tool.carbon(action="generate", code='print("Hello")', language="python", theme="dracula")

    # Generate from file
    agent.tool.carbon(action="generate_from_file", file_path="script.py", theme="monokai")

    # List available themes
    agent.tool.carbon(action="list_themes")

Available Actions:
    - generate: Generate code screenshot from string
        Parameters:
            code (str): The source code to render (required)
            language (str): Programming language for syntax highlighting (default: "auto")
            theme (str): Color theme (default: "seti")
            background_color (str): Background color in rgba format
            window_theme (str): Window chrome style - "none", "sharp", "bw", "boxy"
            padding (int): Padding around the code in pixels (default: 56)
            line_numbers (bool): Show line numbers (default: False)
            font_family (str): Font for code (default: "Fira Code")
            font_size (int): Font size in pixels (default: 14)
            output_dir (str): Directory to save the image (default: "output")

    - generate_from_file: Generate from source file
        Parameters:
            file_path (str): Path to the source file (required)
            start_line (int): 1-based start line, inclusive (optional)
            end_line (int): 1-based end line, inclusive (optional)
            language (str): Language for highlighting (default: "auto")
            theme (str): Color theme (default: "seti")
            + all parameters from generate action
            max_lines (int): Max lines to include (default: 250)
            max_bytes (int): Max bytes to read (default: 250000)

    - list_themes: List available Carbon themes
        Parameters: none

Requirements:
    pip install strands-pack[carbon]
    playwright install chromium
"""

import asyncio
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Literal, Optional

from strands import tool

# Carbon configuration types
Theme = Literal[
    "3024-night", "a11y-dark", "blackboard", "base16-dark", "base16-light",
    "cobalt", "dracula", "duotone-dark", "hopscotch", "lucario", "material",
    "monokai", "night-owl", "nord", "oceanic-next", "one-light", "one-dark",
    "panda-syntax", "paraiso-dark", "seti", "shades-of-purple", "solarized-dark",
    "solarized-light", "synthwave-84", "twilight", "verminal", "vscode",
    "yeti", "zenburn"
]

WindowTheme = Literal["none", "sharp", "bw", "boxy"]
ExportSize = Literal["1x", "2x", "4x"]

# List of all available themes
CARBON_THEMES = [
    "3024-night", "a11y-dark", "blackboard", "base16-dark", "base16-light",
    "cobalt", "dracula", "duotone-dark", "hopscotch", "lucario", "material",
    "monokai", "night-owl", "nord", "oceanic-next", "one-light", "one-dark",
    "panda-syntax", "paraiso-dark", "seti", "shades-of-purple", "solarized-dark",
    "solarized-light", "synthwave-84", "twilight", "verminal", "vscode",
    "yeti", "zenburn"
]

# Recommended themes by category
RECOMMENDED_THEMES = {
    "dark_professional": ["seti", "vscode", "one-dark", "material"],
    "dark_vibrant": ["dracula", "synthwave-84", "shades-of-purple", "night-owl"],
    "light": ["one-light", "solarized-light", "base16-light", "yeti"],
    "retro": ["monokai", "zenburn", "twilight", "cobalt"],
    "minimal": ["nord", "oceanic-next", "panda-syntax"],
}

# File extension to language mapping
EXTENSION_TO_LANGUAGE = {
    "py": "python",
    "js": "javascript",
    "ts": "typescript",
    "tsx": "typescript",
    "jsx": "javascript",
    "go": "go",
    "rs": "rust",
    "java": "java",
    "kt": "kotlin",
    "swift": "swift",
    "cpp": "cpp",
    "cc": "cpp",
    "cxx": "cpp",
    "c": "c",
    "h": "cpp",
    "hpp": "cpp",
    "cs": "csharp",
    "rb": "ruby",
    "php": "php",
    "sh": "bash",
    "bash": "bash",
    "zsh": "bash",
    "sql": "sql",
    "json": "json",
    "yaml": "yaml",
    "yml": "yaml",
    "toml": "toml",
    "md": "markdown",
}


def _ok(**data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": True}
    out.update(data)
    return out


def _err(message: str, **data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": False, "error": message}
    out.update(data)
    return out


def _guess_language_from_path(path: Path) -> str:
    """Guess Carbon language from file extension."""
    ext = path.suffix.lower().lstrip(".")
    return EXTENSION_TO_LANGUAGE.get(ext, "auto")


def _build_carbon_url(
    code: str,
    language: str = "auto",
    theme: str = "seti",
    background_color: str = "rgba(171,184,195,1)",
    window_theme: str = "none",
    padding_vertical: int = 56,
    padding_horizontal: int = 56,
    line_numbers: bool = False,
    font_family: str = "Fira Code",
    font_size: int = 14,
) -> str:
    """Build Carbon URL with configuration parameters."""
    params = {
        "code": code,
        "l": language,
        "t": theme,
        "bg": background_color,
        "wt": window_theme,
        "pv": str(padding_vertical) + "px",
        "ph": str(padding_horizontal) + "px",
        "ln": str(line_numbers).lower(),
        "fm": font_family,
        "fs": str(font_size) + "px",
        "lh": "133%",
        "wc": "true",  # auto-adjust width
        "ds": "true",  # drop shadow
        "dsyoff": "20px",
        "dsblur": "68px",
        "wa": "true",  # width adjustment
        "es": "2x",  # export size
    }

    query_string = urllib.parse.urlencode(params)
    return f"https://carbon.now.sh/?{query_string}"


async def _capture_carbon_screenshot(
    url: str,
    output_path: Path,
    wait_time: float = 3.0,
    headless: bool = True,
) -> dict:
    """Capture screenshot of Carbon page using local Playwright."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return _err("Missing playwright. Install with: pip install strands-pack[carbon] && playwright install chromium")

    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=headless)
            page = await browser.new_page()

            try:
                # Navigate to Carbon with our configuration
                await page.goto(url, wait_until="networkidle")

                # Wait for the code to render
                await asyncio.sleep(wait_time)

                # Find the export container (the code window)
                export_container = await page.query_selector(".export-container")

                if export_container:
                    # Screenshot just the code window
                    await export_container.screenshot(path=str(output_path))
                else:
                    # Fallback: screenshot the main container
                    container = await page.query_selector("#__next")
                    if container:
                        await container.screenshot(path=str(output_path))
                    else:
                        # Last resort: full page
                        await page.screenshot(path=str(output_path))

                return _ok(file_path=str(output_path))

            finally:
                await page.close()
                await browser.close()

    except Exception as e:
        return _err(str(e))


def _generate_code_image(
    code: str,
    language: str = "auto",
    theme: str = "seti",
    background_color: str = "rgba(171,184,195,1)",
    window_theme: str = "none",
    padding: int = 56,
    line_numbers: bool = False,
    font_family: str = "Fira Code",
    font_size: int = 14,
    output_dir: str = "output",
) -> dict:
    """Generate a beautiful code screenshot using Carbon."""
    # Build Carbon URL
    carbon_url = _build_carbon_url(
        code=code,
        language=language,
        theme=theme,
        background_color=background_color,
        window_theme=window_theme,
        padding_vertical=padding,
        padding_horizontal=padding,
        line_numbers=line_numbers,
        font_family=font_family,
        font_size=font_size,
    )

    # Ensure output directory exists
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"carbon_code_{timestamp}.png"
    file_path = output_path / filename

    # Run async capture
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    result = loop.run_until_complete(
        _capture_carbon_screenshot(
            url=carbon_url,
            output_path=file_path,
        )
    )

    # Add metadata to result
    result["action"] = "generate"
    result["url"] = carbon_url
    result["theme"] = theme
    result["language"] = language

    if result["success"]:
        result["message"] = f"Code image saved to {file_path}"

    return result


def _generate_code_image_from_file(
    file_path: str,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
    language: str = "auto",
    theme: str = "seti",
    background_color: str = "rgba(171,184,195,1)",
    window_theme: str = "none",
    padding: int = 56,
    line_numbers: bool = False,
    font_family: str = "Fira Code",
    font_size: int = 14,
    output_dir: str = "output",
    max_lines: int = 250,
    max_bytes: int = 250_000,
) -> dict:
    """Generate a Carbon code screenshot by reading code directly from a file."""
    path = Path(file_path).expanduser().resolve()

    if not path.exists():
        return _err(f"File not found: {file_path}")
    if not path.is_file():
        return _err(f"Not a file: {file_path}")

    s = 1 if start_line is None else max(1, int(start_line))
    e_req = None if end_line is None else max(1, int(end_line))
    if e_req is not None and e_req < s:
        return _err(f"end_line ({e_req}) must be >= start_line ({s}).")

    # Stream read up to limits
    collected: list[tuple[int, str]] = []
    total_lines = 0
    approx_bytes = 0
    hit_limit = False

    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f, start=1):
                total_lines = i
                if i < s:
                    continue
                if e_req is not None and i > e_req:
                    break

                line = line.rstrip("\n")
                collected.append((i, line))

                approx_bytes += len(line.encode("utf-8", errors="replace")) + 1
                if len(collected) >= max_lines or approx_bytes >= max_bytes:
                    hit_limit = True
                    break
    except Exception as ex:
        return _err(f"Failed reading file: {type(ex).__name__}: {ex}")

    if total_lines == 0:
        return _err(f"File is empty: {file_path}")
    if not collected:
        return _err(f"No lines collected. Check start_line/end_line for {file_path}.")

    s_out = collected[0][0]
    e_out = collected[-1][0]
    code = "\n".join(line for _, line in collected)

    lang = language if language != "auto" else _guess_language_from_path(path)

    result = _generate_code_image(
        code=code,
        language=lang,
        theme=theme,
        background_color=background_color,
        window_theme=window_theme,
        padding=padding,
        line_numbers=line_numbers,
        font_family=font_family,
        font_size=font_size,
        output_dir=output_dir,
    )

    # Update action and add source metadata
    result["action"] = "generate_from_file"
    result["source_file"] = str(path)
    result["source_lines"] = f"{s_out}-{e_out}"
    if hit_limit:
        result["note"] = "Input snippet was truncated due to max_lines/max_bytes. Use start_line/end_line to narrow."

    return result


def _list_themes() -> dict:
    """List all available Carbon themes for code screenshots."""
    return _ok(
        action="list_themes",
        themes=CARBON_THEMES,
        recommended=RECOMMENDED_THEMES,
        default="seti",
    )


@tool
def carbon(
    action: str,
    code: Optional[str] = None,
    file_path: Optional[str] = None,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
    language: str = "auto",
    theme: str = "seti",
    background_color: str = "rgba(171,184,195,1)",
    window_theme: str = "none",
    padding: int = 56,
    line_numbers: bool = False,
    font_family: str = "Fira Code",
    font_size: int = 14,
    output_dir: str = "output",
    max_lines: int = 250,
    max_bytes: int = 250_000,
) -> dict:
    """
    Generate beautiful code screenshots using Carbon (carbon.now.sh).

    Args:
        action: The action to perform. One of:
                - "generate": Create screenshot from code string
                - "generate_from_file": Create screenshot from file
                - "list_themes": List available themes
        code: Source code to render (required for "generate").
        file_path: Path to source file (required for "generate_from_file").
        start_line: 1-based start line for file extraction (optional).
        end_line: 1-based end line for file extraction (optional).
        language: Programming language for syntax highlighting (default: "auto").
        theme: Color theme - dracula, monokai, seti, nord, etc. (default: "seti").
        background_color: Background color in rgba format.
        window_theme: Window style - "none", "sharp", "bw", "boxy" (default: "none").
        padding: Padding around code in pixels (default: 56).
        line_numbers: Show line numbers (default: False).
        font_family: Font for code (default: "Fira Code").
        font_size: Font size in pixels (default: 14).
        output_dir: Directory to save image (default: "output").
        max_lines: Max lines to include from file (default: 250).
        max_bytes: Max bytes to read from file (default: 250000).

    Returns:
        dict with keys:
            - success: bool indicating if operation succeeded
            - action: the action performed
            - file_path: path to saved image (for generate actions)
            - url: Carbon URL used (for debugging)
            - themes: list of themes (for list_themes)
            - error: error message (if failed)

    Examples:
        >>> carbon(action="generate", code='print("Hello")', language="python", theme="dracula")
        >>> carbon(action="generate_from_file", file_path="src/main.py", theme="monokai")
        >>> carbon(action="generate_from_file", file_path="app.js", start_line=10, end_line=50)
        >>> carbon(action="list_themes")
    """
    valid_actions = ["generate", "generate_from_file", "list_themes"]
    action = (action or "").lower().strip()

    if action not in valid_actions:
        return _err(f"Unknown action '{action}'. Valid actions are: {valid_actions}")

    if action == "generate":
        if not code:
            return _err("Missing required parameter 'code' for action 'generate'.")

        return _generate_code_image(
            code=code,
            language=language,
            theme=theme,
            background_color=background_color,
            window_theme=window_theme,
            padding=padding,
            line_numbers=line_numbers,
            font_family=font_family,
            font_size=font_size,
            output_dir=output_dir,
        )

    elif action == "generate_from_file":
        if not file_path:
            return _err("Missing required parameter 'file_path' for action 'generate_from_file'.")

        return _generate_code_image_from_file(
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            language=language,
            theme=theme,
            background_color=background_color,
            window_theme=window_theme,
            padding=padding,
            line_numbers=line_numbers,
            font_family=font_family,
            font_size=font_size,
            output_dir=output_dir,
            max_lines=max_lines,
            max_bytes=max_bytes,
        )

    elif action == "list_themes":
        return _list_themes()

    return _err(f"Unhandled action: {action}")
