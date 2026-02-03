"""Tests for OpenAI video tool (Videos API wrapper)."""

import tempfile
from pathlib import Path

import pytest

from strands_pack.openai_video import openai_video


class _FakeStream:
    def __init__(self, b: bytes):
        self._b = b

    def read(self) -> bytes:
        return self._b


class _FakeVideos:
    def __init__(self):
        self._id = "video_123"
        self._retrieve_calls = 0

    def create(self, **kwargs):
        # Mimic API: seconds is a string in request
        assert "prompt" in kwargs
        return {
            "id": self._id,
            "object": "video",
            "model": kwargs.get("model", "sora-2"),
            "status": "queued",
            "progress": 0,
            "created_at": 1712697600,
            "size": kwargs.get("size", "720x1280"),
            "seconds": kwargs.get("seconds", "4"),
            "quality": "standard",
        }

    def retrieve(self, video_id=None, **kwargs):
        vid = video_id or kwargs.get("video_id")
        assert vid == self._id
        self._retrieve_calls += 1
        status = "queued" if self._retrieve_calls < 2 else "completed"
        return {"id": self._id, "object": "video", "model": "sora-2", "status": status, "progress": 100 if status == "completed" else 0}

    def download_content(self, video_id=None, variant=None, **kwargs):
        vid = video_id or kwargs.get("video_id")
        assert vid == self._id
        _ = variant
        return _FakeStream(b"fake_mp4_bytes")

    def remix(self, video_id=None, prompt=None, **kwargs):
        vid = video_id or kwargs.get("video_id")
        p = prompt or kwargs.get("prompt")
        assert vid == self._id
        assert p
        return {"id": "video_456", "object": "video", "model": "sora-2", "status": "queued", "remixed_from_video_id": self._id}

    def list(self, **_kwargs):
        return type("Page", (), {"data": [{"id": self._id, "object": "video", "model": "sora-2", "status": "completed"}]})()

    def delete(self, video_id=None, **kwargs):
        vid = video_id or kwargs.get("video_id")
        return {"id": vid, "object": "video", "status": "deleted"}


class _FakeClient:
    def __init__(self):
        self.videos = _FakeVideos()


def test_generate_end_to_end_saves_file():
    client = _FakeClient()
    with tempfile.TemporaryDirectory() as td:
        res = openai_video(
            action="generate",
            prompt="A test video",
            client_override=client,
            output_dir=td,
            poll_interval_seconds=1,
            max_wait_seconds=5,
        )
        assert res["success"] is True
        assert res["action"] == "generate"
        assert res["video_id"] == "video_123"
        p = Path(res["file_path"])
        assert p.exists()
        assert p.read_bytes() == b"fake_mp4_bytes"


def test_wait_returns_error_on_failed_terminal_status():
    class FailVideos(_FakeVideos):
        def retrieve(self, video_id=None, **kwargs):
            vid = video_id or kwargs.get("video_id")
            assert vid == self._id
            return {
                "id": self._id,
                "object": "video",
                "model": "sora-2",
                "status": "failed",
                "error": {"code": "moderation_blocked", "message": "blocked"},
            }

    class FailClient:
        def __init__(self):
            self.videos = FailVideos()

    res = openai_video(action="wait", video_id="video_123", client_override=FailClient(), max_wait_seconds=1, poll_interval_seconds=1)
    assert res["success"] is False
    assert res["error_type"] == "JobFailed"
    assert res.get("status") == "failed"


def test_create_requires_prompt():
    client = _FakeClient()
    res = openai_video(action="create", prompt="", client_override=client)
    assert res["success"] is False
    assert "prompt" in res["error"]


def test_seconds_validation():
    client = _FakeClient()
    res = openai_video(action="create", prompt="x", seconds=7, client_override=client)
    assert res["success"] is False
    assert "seconds" in res["error"]


def test_input_reference_path_missing_file():
    client = _FakeClient()
    res = openai_video(action="create", prompt="x", input_reference_path="/nope/ref.png", client_override=client)
    assert res["success"] is False
    assert res["error_type"] == "FileNotFound"


def test_remix_requires_video_id_and_prompt():
    client = _FakeClient()
    res = openai_video(action="remix", video_id="", prompt="x", client_override=client)
    assert res["success"] is False
    res2 = openai_video(action="remix", video_id="video_123", prompt="", client_override=client)
    assert res2["success"] is False


def test_list_returns_items():
    client = _FakeClient()
    res = openai_video(action="list", client_override=client)
    assert res["success"] is True
    assert res["count"] == 1


def test_missing_videos_api_returns_helpful_error():
    class NoVideosClient:
        videos = None

    res = openai_video(action="list", client_override=NoVideosClient())
    assert res["success"] is False
    assert res["error_type"] == "UnsupportedClient"


@pytest.mark.parametrize("action", ["unknown", "bogus"])
def test_invalid_action(action):
    res = openai_video(action=action, client_override=_FakeClient())
    assert res["success"] is False
    assert res["error_type"] == "InvalidAction"


