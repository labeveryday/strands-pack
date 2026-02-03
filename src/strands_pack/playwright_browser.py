"""
Playwright Browser Tool

Lightweight browser automation using Playwright (Chromium).

Requires:
    pip install strands-pack[playwright]
    playwright install chromium

Supported actions
-----------------
- navigate
    Parameters: url (required unless session already has a page), timeout_ms (default 15000)

- screenshot
    Parameters: url (optional if session already navigated), output_path (optional), full_page (default True),
                timeout_ms (default 15000)

- extract_text
    Parameters: url (optional if session already navigated), selector (optional), timeout_ms (default 15000),
                max_chars (default 20000)

- click
    Parameters: selector (required), timeout_ms (default 15000)

- fill
    Parameters: selector (required), text (required), timeout_ms (default 15000)

- type
    Parameters: selector (required), text (required), timeout_ms (default 15000), delay_ms (optional), press_enter (optional)

- wait
    Wait for an element.
    Parameters: selector (required), state (optional: "attached"|"detached"|"visible"|"hidden", default "visible"),
                timeout_ms (default 15000)

- evaluate
    Run JavaScript in the page context.
    Parameters: script (required), timeout_ms (default 15000)

- close_session
    Close a persisted browser session.
    Parameters: session_id (required)

Notes
-----
This is meant for simple agent workflows: capture a screenshot or extract visible text.
For complex multi-step browsing, consider an interactive browser tool.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from strands import tool

try:
    from playwright.sync_api import sync_playwright

    HAS_PLAYWRIGHT = True
except ImportError:  # pragma: no cover
    sync_playwright = None
    HAS_PLAYWRIGHT = False

_SESSIONS: Dict[str, Dict[str, Any]] = {}


def _ok(**data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": True}
    out.update(data)
    return out


def _err(message: str, *, error_type: Optional[str] = None, **data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": False, "error": message}
    if error_type:
        out["error_type"] = error_type
    out.update(data)
    return out


def _require_playwright() -> Optional[Dict[str, Any]]:
    if HAS_PLAYWRIGHT:
        return None
    return _err(
        "Missing Playwright dependency. Install with: pip install strands-pack[playwright] && playwright install chromium",
        error_type="MissingDependency",
    )

def _start_playwright():
    # sync_playwright() returns a context manager that also supports .start()/.stop()
    return sync_playwright().start()


def _get_or_create_session(session_id: str, *, headless: bool) -> Dict[str, Any]:
    if session_id in _SESSIONS:
        return _SESSIONS[session_id]
    p = _start_playwright()
    browser = p.chromium.launch(headless=headless)
    page = browser.new_page()
    sess = {"playwright": p, "browser": browser, "page": page, "headless": headless}
    _SESSIONS[session_id] = sess
    return sess


def _close_session(session_id: str) -> Dict[str, Any]:
    sess = _SESSIONS.pop(session_id, None)
    if not sess:
        return _err(f"Unknown session_id: {session_id}", error_type="NotFound")
    try:
        try:
            sess["page"].close()
        except Exception:
            pass
        try:
            sess["browser"].close()
        except Exception:
            pass
        try:
            sess["playwright"].stop()
        except Exception:
            pass
        return _ok(action="close_session", session_id=session_id, closed=True)
    except Exception as e:
        return _err(str(e), error_type=type(e).__name__, action="close_session", session_id=session_id)


def _with_page(*, session_id: Optional[str], headless: bool):
    """
    Returns (page, cleanup_fn|None).
    If session_id is provided, the page is persisted and cleanup_fn is None.
    """
    if session_id:
        sess = _get_or_create_session(session_id, headless=headless)
        return sess["page"], None
    # one-shot
    p = _start_playwright()
    browser = p.chromium.launch(headless=headless)
    page = browser.new_page()

    def _cleanup():
        try:
            page.close()
        except Exception:
            pass
        try:
            browser.close()
        except Exception:
            pass
        try:
            p.stop()
        except Exception:
            pass

    return page, _cleanup


@tool
def playwright_browser(
    action: str,
    url: Optional[str] = None,
    output_path: Optional[str] = None,
    full_page: bool = True,
    timeout_ms: int = 15000,
    selector: Optional[str] = None,
    max_chars: int = 20000,
    headless: bool = False,
    # new actions
    text: Optional[str] = None,
    delay_ms: Optional[int] = None,
    press_enter: bool = False,
    state: str = "visible",
    script: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Lightweight browser automation using Playwright (Chromium).

    Args:
        action: The action to perform. One of:
            - "navigate": Navigate to a URL.
            - "screenshot": Capture a screenshot of the page.
            - "extract_text": Extract visible text from the page.
            - "click": Click an element.
            - "fill": Fill an input/textarea element.
            - "type": Type into an element.
            - "wait": Wait for an element state.
            - "evaluate": Execute JavaScript and return the result.
            - "close_session": Close a persisted session.
        url: The URL to navigate to. Required for "navigate", and required for other actions
            unless you use `session_id` and have already navigated.
        output_path: Filename or path for the screenshot (screenshot action only).
            Filenames are saved to .playwright-strands/. Full paths are used as-is.
            Defaults to ".playwright-strands/screenshot.png".
        full_page: Whether to capture the full scrollable page (screenshot action only).
            Defaults to True.
        timeout_ms: Navigation and element timeout in milliseconds.
            Defaults to 15000.
        selector: CSS selector to extract text from (extract_text action only).
            If not provided, extracts text from the entire body.
        max_chars: Maximum characters to return for extract_text (default 20000).
            Text beyond this limit is truncated.
        headless: Run browser in headless mode (default False).
            Set to True to hide the browser window.
        text: Text to fill/type (fill/type actions).
        delay_ms: Per-character delay when typing (type action).
        press_enter: Whether to press Enter after typing (type action).
        state: Element state for wait (default "visible").
        script: JavaScript to evaluate (evaluate action).
        session_id: If provided, keeps the browser/page open between calls.

    Returns:
        dict with success status and action-specific data:
            - navigate: url, final_url
            - screenshot: url, output_path, full_page
            - extract_text: url, selector, text, truncated
            - click/fill/type/wait/evaluate: action-specific response
            - close_session: session_id, closed

    Examples:
        >>> playwright_browser(action="navigate", url="https://example.com")
        >>> playwright_browser(action="screenshot", url="https://example.com")
        >>> playwright_browser(action="screenshot", url="https://example.com", output_path="./page.png", full_page=False)
        >>> playwright_browser(action="extract_text", url="https://example.com")
        >>> playwright_browser(action="extract_text", url="https://example.com", selector="h1")
        >>> playwright_browser(action="click", session_id="s1", selector="text=Sign in")
        >>> playwright_browser(action="fill", session_id="s1", selector="input[name=email]", text="me@example.com")
        >>> playwright_browser(action="type", session_id="s1", selector="input[name=password]", text="...", press_enter=True)
        >>> playwright_browser(action="close_session", session_id="s1")
    """
    action = (action or "").strip()
    missing = _require_playwright()
    if missing is not None:
        return missing

    available_actions = [
        "navigate",
        "screenshot",
        "extract_text",
        "click",
        "fill",
        "type",
        "wait",
        "evaluate",
        "close_session",
    ]
    if action not in available_actions:
        return _err(
            f"Unknown action: {action}",
            error_type="InvalidAction",
            available_actions=available_actions,
        )

    if action == "close_session":
        if not session_id:
            return _err("session_id is required for close_session")
        return _close_session(session_id)

    # Validate url requirement before starting browser
    if not url and not session_id:
        return _err("url is required (or use session_id and call navigate first)")

    try:
        page, cleanup = _with_page(session_id=session_id, headless=headless)
        try:
            # navigate if requested, or if a url is supplied for other actions
            if action == "navigate":
                if not url:
                    return _err("url is required for navigate")
                page.goto(url, wait_until="networkidle", timeout=timeout_ms)
                return _ok(action="navigate", url=url, final_url=getattr(page, "url", None), session_id=session_id)

            if url:
                page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            elif action in ("screenshot", "extract_text", "click", "fill", "type", "wait", "evaluate"):
                # If you don't provide a url, you must be using a session that already navigated.
                if not session_id:
                    return _err("url is required (or use session_id and call navigate first)")

            if action == "screenshot":
                screenshot_dir = Path(".playwright-strands")
                if output_path:
                    p = Path(output_path).expanduser()
                    # If just a filename, put in .playwright-strands/
                    if p.parent == Path(".") or str(p.parent) == "":
                        out = screenshot_dir / p.name
                    else:
                        out = p
                else:
                    out = screenshot_dir / "screenshot.png"
                out.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(out), full_page=full_page)
                return _ok(action="screenshot", url=url or getattr(page, "url", None), output_path=str(out), full_page=full_page, session_id=session_id)

            if action == "extract_text":
                if selector:
                    loc = page.locator(selector)
                    extracted = loc.inner_text(timeout=timeout_ms)
                else:
                    extracted = page.inner_text("body", timeout=timeout_ms)
                extracted = (extracted or "").strip()
                truncated = len(extracted) > max_chars
                if truncated:
                    extracted = extracted[:max_chars]
                return _ok(action="extract_text", url=url or getattr(page, "url", None), selector=selector, text=extracted, truncated=truncated, session_id=session_id)

            if action == "click":
                if not selector:
                    return _err("selector is required for click")
                page.click(selector, timeout=timeout_ms)
                return _ok(action="click", selector=selector, url=url or getattr(page, "url", None), session_id=session_id)

            if action == "fill":
                if not selector:
                    return _err("selector is required for fill")
                if text is None:
                    return _err("text is required for fill")
                page.fill(selector, text, timeout=timeout_ms)
                return _ok(action="fill", selector=selector, url=url or getattr(page, "url", None), session_id=session_id)

            if action == "type":
                if not selector:
                    return _err("selector is required for type")
                if text is None:
                    return _err("text is required for type")
                # Prefer locator.type so it focuses the element
                loc = page.locator(selector)
                type_kwargs: Dict[str, Any] = {"timeout": timeout_ms}
                if delay_ms is not None:
                    type_kwargs["delay"] = int(delay_ms)
                loc.type(text, **type_kwargs)
                if press_enter:
                    page.keyboard.press("Enter")
                return _ok(action="type", selector=selector, url=url or getattr(page, "url", None), session_id=session_id)

            if action == "wait":
                if not selector:
                    return _err("selector is required for wait")
                if state not in ("attached", "detached", "visible", "hidden"):
                    return _err("state must be one of: attached, detached, visible, hidden")
                page.wait_for_selector(selector, state=state, timeout=timeout_ms)
                return _ok(action="wait", selector=selector, state=state, url=url or getattr(page, "url", None), session_id=session_id)

            if action == "evaluate":
                if not script:
                    return _err("script is required for evaluate")
                result = page.evaluate(script)
                return _ok(action="evaluate", url=url or getattr(page, "url", None), session_id=session_id, result=result)

            return _err(f"Unhandled action: {action}", error_type="InvalidAction")
        finally:
            if cleanup:
                cleanup()
    except Exception as e:
        return _err(str(e), error_type=type(e).__name__, action=action)


