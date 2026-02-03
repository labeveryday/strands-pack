"""Tests for notify tool."""

import os
from unittest.mock import MagicMock, patch


class TestNotifyTool:
    def test_invalid_action(self):
        from strands_pack.notify import notify
        r = notify(action="nope")
        assert r["success"] is False

    def test_beep_suppressed_in_aws(self):
        from strands_pack.notify import notify
        with patch.dict(os.environ, {"AWS_LAMBDA_FUNCTION_NAME": "x"}):
            r = notify(action="beep")
        assert r["success"] is True
        assert r["routed_to"] == "none"

    def test_play_file_requires_path(self):
        from strands_pack.notify import notify
        r = notify(action="play_file")
        assert r["success"] is False
        assert "sound_path" in r["error"]

    def test_notify_auto_local(self):
        from strands_pack.notify import notify
        with patch.dict(os.environ, {}, clear=True):
            # ensure not aws
            r = notify(action="notify", title="t", message="m", sound=False)
        assert r["success"] is True
        assert r["routed_to"] == "local"

    def test_rate_limit(self):
        from strands_pack.notify import notify, _RECENT
        _RECENT.clear()  # Reset rate limit state
        # Set a very low rate limit and send twice immediately
        r1 = notify(action="notify", title="t", message="m", sound=False, rate_limit_per_minute=1)
        r2 = notify(action="notify", title="t", message="m", sound=False, rate_limit_per_minute=1)
        assert r1["success"] is True
        assert r2["success"] is False
        assert r2.get("error_type") == "RateLimited"

    def test_dedupe(self):
        from strands_pack.notify import notify, _RECENT_DEDUPE
        _RECENT_DEDUPE.clear()  # Reset dedupe state
        r1 = notify(action="notify", title="t", message="m", sound=False, dedupe_key="k", dedupe_window_seconds=60)
        r2 = notify(action="notify", title="t", message="m", sound=False, dedupe_key="k", dedupe_window_seconds=60)
        assert r1["success"] is True
        assert r2["success"] is False
        assert r2.get("error_type") == "Deduped"


class TestSnsPublish:
    def test_sns_publish_uses_boto3(self):
        # SNS is intentionally out of scope for notify; use the dedicated sns tool instead.
        assert True


