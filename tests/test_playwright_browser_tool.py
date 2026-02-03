"""Tests for playwright_browser tool."""
import pytest


# Reusable mock fixtures
@pytest.fixture
def mock_playwright(monkeypatch):
    """Mock playwright for testing without browser."""
    import importlib
    mod = importlib.import_module("strands_pack.playwright_browser")

    # Clear any existing sessions
    mod._SESSIONS.clear()

    class FakeLocator:
        def __init__(self, page, selector):
            self.page = page
            self.selector = selector
        def inner_text(self, timeout=None):
            return "hello world"
        def type(self, text, timeout=None, delay=None):
            self.page.typed.append((self.selector, text, timeout, delay))

    class FakeKeyboard:
        def __init__(self, page):
            self.page = page
        def press(self, key):
            self.page.pressed.append(key)

    class FakePage:
        def __init__(self):
            self.url = None
            self.clicked = []
            self.filled = []
            self.typed = []
            self.waited = []
            self.evaluated = []
            self.pressed = []
            self.screenshots = []
            self.keyboard = FakeKeyboard(self)
        def goto(self, url, wait_until=None, timeout=None):
            self.url = url
        def locator(self, selector):
            return FakeLocator(self, selector)
        def click(self, selector, timeout=None):
            self.clicked.append((selector, timeout))
        def fill(self, selector, text, timeout=None):
            self.filled.append((selector, text, timeout))
        def wait_for_selector(self, selector, state=None, timeout=None):
            self.waited.append((selector, state, timeout))
        def evaluate(self, script):
            self.evaluated.append(script)
            return {"ok": True}
        def screenshot(self, path=None, full_page=None):
            self.screenshots.append({"path": path, "full_page": full_page})
            return None
        def inner_text(self, selector, timeout=None):
            return "page body text"
        def close(self):
            return None

    class FakeBrowser:
        def __init__(self, page):
            self._page = page
        def new_page(self):
            return self._page
        def close(self):
            return None

    class FakeChromium:
        def __init__(self, page):
            self._page = page
        def launch(self, headless=False):
            return FakeBrowser(self._page)

    class FakePlaywright:
        def __init__(self, page):
            self.chromium = FakeChromium(page)
        def stop(self):
            return None

    class FakeSyncPlaywright:
        def __init__(self, page):
            self._page = page
        def start(self):
            return FakePlaywright(self._page)

    fake_page = FakePage()
    monkeypatch.setattr(mod, "HAS_PLAYWRIGHT", True)
    monkeypatch.setattr(mod, "sync_playwright", lambda: FakeSyncPlaywright(fake_page))

    return {"mod": mod, "page": fake_page}


def test_playwright_browser_missing_url():
    """Test that missing URL returns error before starting browser."""
    from strands_pack.playwright_browser import playwright_browser

    res = playwright_browser(action="screenshot")
    assert res["success"] is False
    assert "url" in res["error"].lower() or "playwright" in res["error"].lower()


def test_playwright_browser_invalid_action():
    """Test that invalid action returns error."""
    from strands_pack.playwright_browser import playwright_browser

    res = playwright_browser(action="nope", url="https://example.com")
    assert res["success"] is False
    assert "Unknown action" in res["error"]
    assert "available_actions" in res


def test_playwright_browser_requires_url_without_session(monkeypatch):
    """Test that actions require URL when no session exists."""
    import importlib
    mod = importlib.import_module("strands_pack.playwright_browser")
    monkeypatch.setattr(mod, "HAS_PLAYWRIGHT", True)
    monkeypatch.setattr(mod, "sync_playwright", lambda: None)

    res = mod.playwright_browser(action="click", selector="#x")
    assert res["success"] is False
    assert "url is required" in res["error"]


def test_playwright_browser_navigate(mock_playwright):
    """Test navigate action."""
    mod = mock_playwright["mod"]
    page = mock_playwright["page"]

    res = mod.playwright_browser(action="navigate", url="https://example.com", headless=True)
    assert res["success"] is True
    assert res["action"] == "navigate"
    assert res["url"] == "https://example.com"
    assert page.url == "https://example.com"


def test_playwright_browser_screenshot_default_path(mock_playwright, tmp_path, monkeypatch):
    """Test screenshot saves to .playwright-strands/ by default."""
    mod = mock_playwright["mod"]
    page = mock_playwright["page"]

    # Change to tmp directory
    monkeypatch.chdir(tmp_path)

    res = mod.playwright_browser(action="screenshot", url="https://example.com", headless=True)
    assert res["success"] is True
    assert res["action"] == "screenshot"
    assert ".playwright-strands" in res["output_path"]
    assert "screenshot.png" in res["output_path"]


def test_playwright_browser_screenshot_custom_filename(mock_playwright, tmp_path, monkeypatch):
    """Test screenshot with custom filename goes to .playwright-strands/."""
    mod = mock_playwright["mod"]

    monkeypatch.chdir(tmp_path)

    res = mod.playwright_browser(
        action="screenshot",
        url="https://example.com",
        output_path="my-capture.png",
        headless=True
    )
    assert res["success"] is True
    assert ".playwright-strands/my-capture.png" in res["output_path"]


def test_playwright_browser_screenshot_full_path(mock_playwright, tmp_path):
    """Test screenshot with full path uses that path."""
    mod = mock_playwright["mod"]

    full_path = str(tmp_path / "custom" / "shot.png")
    res = mod.playwright_browser(
        action="screenshot",
        url="https://example.com",
        output_path=full_path,
        headless=True
    )
    assert res["success"] is True
    assert res["output_path"] == full_path


def test_playwright_browser_extract_text(mock_playwright):
    """Test extract_text action."""
    mod = mock_playwright["mod"]

    res = mod.playwright_browser(
        action="extract_text",
        url="https://example.com",
        headless=True
    )
    assert res["success"] is True
    assert res["action"] == "extract_text"
    assert "text" in res


def test_playwright_browser_extract_text_with_selector(mock_playwright):
    """Test extract_text with selector."""
    mod = mock_playwright["mod"]

    res = mod.playwright_browser(
        action="extract_text",
        url="https://example.com",
        selector="h1",
        headless=True
    )
    assert res["success"] is True
    assert res["text"] == "hello world"  # From FakeLocator


def test_playwright_browser_click(mock_playwright):
    """Test click action."""
    mod = mock_playwright["mod"]
    page = mock_playwright["page"]

    res = mod.playwright_browser(
        action="click",
        url="https://example.com",
        selector="#submit-btn",
        headless=True
    )
    assert res["success"] is True
    assert res["action"] == "click"
    assert len(page.clicked) == 1
    assert page.clicked[0][0] == "#submit-btn"


def test_playwright_browser_fill(mock_playwright):
    """Test fill action."""
    mod = mock_playwright["mod"]
    page = mock_playwright["page"]

    res = mod.playwright_browser(
        action="fill",
        url="https://example.com",
        selector="input[name=email]",
        text="test@example.com",
        headless=True
    )
    assert res["success"] is True
    assert res["action"] == "fill"
    assert ("input[name=email]", "test@example.com", 15000) in page.filled


def test_playwright_browser_type(mock_playwright):
    """Test type action with press_enter."""
    mod = mock_playwright["mod"]
    page = mock_playwright["page"]

    res = mod.playwright_browser(
        action="type",
        url="https://example.com",
        selector="input[name=search]",
        text="hello",
        press_enter=True,
        headless=True
    )
    assert res["success"] is True
    assert res["action"] == "type"
    assert "Enter" in page.pressed


def test_playwright_browser_wait(mock_playwright):
    """Test wait action."""
    mod = mock_playwright["mod"]
    page = mock_playwright["page"]

    res = mod.playwright_browser(
        action="wait",
        url="https://example.com",
        selector=".loading",
        state="hidden",
        headless=True
    )
    assert res["success"] is True
    assert res["action"] == "wait"
    assert (".loading", "hidden", 15000) in page.waited


def test_playwright_browser_evaluate(mock_playwright):
    """Test evaluate action."""
    mod = mock_playwright["mod"]

    res = mod.playwright_browser(
        action="evaluate",
        url="https://example.com",
        script="() => document.title",
        headless=True
    )
    assert res["success"] is True
    assert res["action"] == "evaluate"
    assert res["result"]["ok"] is True


def test_playwright_browser_session_persistence(mock_playwright):
    """Test session persistence across multiple calls."""
    mod = mock_playwright["mod"]

    # Start session
    sid = "test-session"
    res = mod.playwright_browser(
        action="navigate",
        url="https://example.com",
        session_id=sid,
        headless=True
    )
    assert res["success"] is True
    assert res["session_id"] == sid

    # Use session without URL
    res = mod.playwright_browser(action="click", session_id=sid, selector="#btn")
    assert res["success"] is True

    # Close session
    res = mod.playwright_browser(action="close_session", session_id=sid)
    assert res["success"] is True
    assert res["closed"] is True


def test_playwright_browser_close_session_unknown(mock_playwright):
    """Test close_session with unknown session ID."""
    mod = mock_playwright["mod"]

    res = mod.playwright_browser(action="close_session", session_id="nonexistent")
    assert res["success"] is False
    assert "Unknown session_id" in res["error"]


def test_playwright_browser_missing_required_params(mock_playwright):
    """Test that missing required params return errors."""
    mod = mock_playwright["mod"]

    # click without selector
    res = mod.playwright_browser(action="click", url="https://example.com", headless=True)
    assert res["success"] is False
    assert "selector" in res["error"]

    # fill without text
    res = mod.playwright_browser(action="fill", url="https://example.com", selector="input", headless=True)
    assert res["success"] is False
    assert "text" in res["error"]

    # evaluate without script
    res = mod.playwright_browser(action="evaluate", url="https://example.com", headless=True)
    assert res["success"] is False
    assert "script" in res["error"]

    # wait with invalid state
    res = mod.playwright_browser(action="wait", url="https://example.com", selector="div", state="invalid", headless=True)
    assert res["success"] is False
    assert "state" in res["error"]
