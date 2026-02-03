"""Tests for Gemini music tool (music generation using Lyria)."""

import asyncio
import os
import tempfile
import wave
from importlib import import_module
from pathlib import Path
from unittest.mock import patch

import pytest
import sys
import types as py_types

# Import the actual module (not the tool) for patching internal functions
gemini_music_mod = import_module("strands_pack.gemini_music")


# ============================================================================
# GEMINI MUSIC HELPER TESTS
# ============================================================================

class TestGeminiMusicHelpers:
    """Tests for music helper functions in gemini_music module."""

    def test_save_audio_to_wav(self):
        """Test saving raw PCM data to WAV file."""
        from strands_pack.gemini_music import _save_audio_to_wav

        # Create some fake audio data (48kHz, stereo, 16-bit)
        # 1 second of audio = 48000 samples * 2 channels * 2 bytes = 192000 bytes
        fake_audio = b"\x00" * 19200  # ~0.1 seconds

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name

        try:
            _save_audio_to_wav(fake_audio, temp_path)

            # Verify WAV file properties
            with wave.open(temp_path, 'rb') as wav_file:
                assert wav_file.getnchannels() == 2  # Stereo
                assert wav_file.getsampwidth() == 2  # 16-bit
                assert wav_file.getframerate() == 48000  # 48kHz
        finally:
            Path(temp_path).unlink()

    def test_generate_music_async_stops_by_bytes_not_chunk_count(self, monkeypatch):
        """Ensure duration is enforced by PCM byte count (avoids 2-min outputs)."""
        from strands_pack.gemini_music import _generate_music_async

        # Provide a minimal google.genai.types shim so the helper can build WeightedPrompt.
        class DummyWeightedPrompt:
            def __init__(self, text: str, weight: float = 1.0):
                self.text = text
                self.weight = weight

        class DummyMusicGenerationConfig:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        genai_mod = py_types.ModuleType("google.genai")
        genai_mod.types = py_types.SimpleNamespace(
            WeightedPrompt=DummyWeightedPrompt,
            MusicGenerationConfig=DummyMusicGenerationConfig,
        )

        google_mod = sys.modules.get("google")
        if google_mod is None:
            google_mod = py_types.ModuleType("google")
            monkeypatch.setitem(sys.modules, "google", google_mod)
        setattr(google_mod, "genai", genai_mod)
        monkeypatch.setitem(sys.modules, "google.genai", genai_mod)

        # Dummy streaming session that yields 3 seconds worth of PCM in 1s chunks.
        bytes_per_second = 48000 * 2 * 2

        class DummyAudioChunk:
            def __init__(self, data: bytes):
                self.data = data

        class DummyServerContent:
            def __init__(self, chunks):
                self.audio_chunks = chunks

        class DummyMsg:
            def __init__(self, chunks):
                self.server_content = DummyServerContent(chunks)

        captured = {"weighted_prompts": None, "config": None}

        class DummySession:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def set_weighted_prompts(self, _):
                captured["weighted_prompts"] = _
                return None

            async def set_music_generation_config(self, cfg):
                captured["config"] = cfg
                return None

            async def play(self):
                return None

            async def stop(self):
                return None

            async def receive(self):
                # 3 seconds available, but caller requests 2 seconds
                yield DummyMsg([DummyAudioChunk(b"\x00" * bytes_per_second)])
                yield DummyMsg([DummyAudioChunk(b"\x01" * bytes_per_second)])
                yield DummyMsg([DummyAudioChunk(b"\x02" * bytes_per_second)])

        class DummyConnect:
            def __call__(self, model: str):
                assert model == "lyria-realtime-exp"
                return DummySession()

        class DummyClient:
            def __init__(self):
                self.aio = py_types.SimpleNamespace(
                    live=py_types.SimpleNamespace(music=py_types.SimpleNamespace(connect=DummyConnect()))
                )

        monkeypatch.setattr(gemini_music_mod, "_get_client_alpha", lambda _: DummyClient())

        audio = asyncio.run(
            _generate_music_async(
                api_key="k",
                prompts=["x"],
                duration_seconds=2,
                bpm=120,
                scale="C minor",
                brightness=0.4,
                density=0.6,
                temperature=0.8,
                guidance=1.2,
                seed=123,
                music_generation_mode="QUALITY",
            )
        )

        assert isinstance(audio, (bytes, bytearray))
        assert len(audio) == 2 * bytes_per_second
        # Prompt-level controls should have been appended
        assert "Tempo: 120 BPM" in captured["weighted_prompts"][0].text
        assert "Key/scale: C minor" in captured["weighted_prompts"][0].text
        # Config should have been attempted via MusicGenerationConfig
        assert captured["config"] is not None
        assert getattr(captured["config"], "kwargs", {}).get("temperature") == 0.8
        assert getattr(captured["config"], "kwargs", {}).get("seed") == 123

    def test_generate_music_async_retries_on_unavailable(self, monkeypatch):
        """Retry logic should kick in for transient service-unavailable errors."""
        from strands_pack.gemini_music import _generate_music_async

        # Shim google.genai.types.WeightedPrompt
        class DummyWeightedPrompt:
            def __init__(self, text: str, weight: float = 1.0):
                self.text = text
                self.weight = weight

        class DummyMusicGenerationConfig:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        genai_mod = py_types.ModuleType("google.genai")
        genai_mod.types = py_types.SimpleNamespace(
            WeightedPrompt=DummyWeightedPrompt,
            MusicGenerationConfig=DummyMusicGenerationConfig,
        )
        google_mod = sys.modules.get("google")
        if google_mod is None:
            google_mod = py_types.ModuleType("google")
            monkeypatch.setitem(sys.modules, "google", google_mod)
        setattr(google_mod, "genai", genai_mod)
        monkeypatch.setitem(sys.modules, "google.genai", genai_mod)

        bytes_per_second = 48000 * 2 * 2

        class DummyAudioChunk:
            def __init__(self, data: bytes):
                self.data = data

        class DummyServerContent:
            def __init__(self, chunks):
                self.audio_chunks = chunks

        class DummyMsg:
            def __init__(self, chunks):
                self.server_content = DummyServerContent(chunks)

        class DummySession:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def set_weighted_prompts(self, _):
                return None

            async def play(self):
                return None

            async def stop(self):
                return None

            async def receive(self):
                yield DummyMsg([DummyAudioChunk(b"\x00" * bytes_per_second)])

        attempts = {"n": 0}

        class DummyConnect:
            def __call__(self, model: str):
                attempts["n"] += 1
                if attempts["n"] == 1:
                    raise RuntimeError("Service unavailable (503)")
                return DummySession()

        class DummyClient:
            def __init__(self):
                self.aio = py_types.SimpleNamespace(
                    live=py_types.SimpleNamespace(music=py_types.SimpleNamespace(connect=DummyConnect()))
                )

        monkeypatch.setattr(gemini_music_mod, "_get_client_alpha", lambda _: DummyClient())
        # Avoid real sleeping in the retry loop - patch the module's asyncio reference
        original_sleep = asyncio.sleep
        async def fast_sleep(*_args, **_kwargs):
            return await original_sleep(0)
        monkeypatch.setattr(asyncio, "sleep", fast_sleep)

        audio = asyncio.run(_generate_music_async(api_key="k", prompts=["x"], duration_seconds=1))
        assert attempts["n"] == 2
        assert len(audio) == bytes_per_second


# ============================================================================
# GENERATE MUSIC TESTS
# ============================================================================

class TestGenerateMusic:
    """Tests for the generate action."""

    def test_missing_api_key(self):
        """Test error when GOOGLE_API_KEY is not set."""
        from strands_pack import gemini_music

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GOOGLE_API_KEY", None)
            result = gemini_music(action="generate", prompt="A calm piano melody")

        assert result["success"] is False
        assert "GOOGLE_API_KEY" in result["error"]

    def test_missing_prompt(self):
        """Test error when prompt is not provided for generate action."""
        from strands_pack import gemini_music

        result = gemini_music(action="generate")

        assert result["success"] is False
        assert "prompt" in result["error"]

    def test_duration_too_short(self):
        """Test error when duration is less than 5 seconds."""
        from strands_pack import gemini_music

        result = gemini_music(
            action="generate",
            prompt="A calm piano melody",
            duration_seconds=3
        )

        assert result["success"] is False
        assert "duration_seconds must be between 5 and 120" in result["error"]

    def test_duration_too_long(self):
        """Test error when duration exceeds 120 seconds."""
        from strands_pack import gemini_music

        result = gemini_music(
            action="generate",
            prompt="A calm piano melody",
            duration_seconds=150
        )

        assert result["success"] is False
        assert "duration_seconds must be between 5 and 120" in result["error"]

    def test_valid_duration_boundaries(self):
        """Test that boundary durations are validated correctly."""
        from strands_pack import gemini_music

        # Test that 5 seconds is valid (but will fail due to missing API key)
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GOOGLE_API_KEY", None)
            result = gemini_music(action="generate", prompt="Test", duration_seconds=5)
            # Should fail for API key, not duration
            assert "duration_seconds" not in result.get("error", "")

        # Test that 120 seconds is valid
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GOOGLE_API_KEY", None)
            result = gemini_music(action="generate", prompt="Test", duration_seconds=120)
            assert "duration_seconds" not in result.get("error", "")


# ============================================================================
# GENERATE WEIGHTED TESTS
# ============================================================================

class TestGenerateMusicWeighted:
    """Tests for the generate_weighted action."""

    def test_missing_api_key(self):
        """Test error when GOOGLE_API_KEY is not set."""
        from strands_pack import gemini_music

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GOOGLE_API_KEY", None)
            result = gemini_music(
                action="generate_weighted",
                prompts=[{"text": "jazz piano", "weight": 0.7}]
            )

        assert result["success"] is False
        assert "GOOGLE_API_KEY" in result["error"]

    def test_empty_prompts(self):
        """Test error when prompts list is empty."""
        from strands_pack import gemini_music

        result = gemini_music(action="generate_weighted", prompts=[])

        assert result["success"] is False
        assert "At least one prompt is required" in result["error"]

    def test_missing_prompts(self):
        """Test that generate_weighted requires prompts parameter."""
        from strands_pack import gemini_music

        result = gemini_music(action="generate_weighted")

        assert result["success"] is False
        assert "prompts" in result["error"]

    def test_duration_too_short(self):
        """Test error when duration is less than 5 seconds."""
        from strands_pack import gemini_music

        result = gemini_music(
            action="generate_weighted",
            prompts=[{"text": "jazz", "weight": 1.0}],
            duration_seconds=2
        )

        assert result["success"] is False
        assert "duration_seconds must be between 5 and 120" in result["error"]

    def test_duration_too_long(self):
        """Test error when duration exceeds 120 seconds."""
        from strands_pack import gemini_music

        result = gemini_music(
            action="generate_weighted",
            prompts=[{"text": "jazz", "weight": 1.0}],
            duration_seconds=200
        )

        assert result["success"] is False
        assert "duration_seconds must be between 5 and 120" in result["error"]


# ============================================================================
# UNKNOWN ACTION TESTS
# ============================================================================

class TestUnknownAction:
    """Tests for unknown action handling."""

    def test_unknown_action(self):
        """Test that unknown action returns error."""
        from strands_pack import gemini_music

        result = gemini_music(action="unknown_action", prompt="test")

        assert result["success"] is False
        assert "Invalid action" in result["error"]

    def test_empty_action(self):
        """Test that empty action returns error."""
        from strands_pack import gemini_music

        result = gemini_music(action="", prompt="test")

        assert result["success"] is False
        assert "Invalid action" in result["error"]


# ============================================================================
# INTEGRATION TESTS (Require actual API key)
# ============================================================================

@pytest.mark.skip(reason="Requires actual Google API key and network access")
class TestGeminiMusicIntegration:
    """Integration tests that require actual API access."""

    def test_generate_simple_music(self):
        """Test generating simple music with the API."""
        from strands_pack import gemini_music

        with tempfile.TemporaryDirectory() as tmp_dir:
            result = gemini_music(
                action="generate",
                prompt="A calm ambient melody",
                output_dir=tmp_dir,
                duration_seconds=5  # Minimum duration
            )

            assert result["success"] is True
            assert Path(result["file_path"]).exists()
            assert result["file_path"].endswith(".wav")

    def test_generate_weighted_music(self):
        """Test generating weighted music with the API."""
        from strands_pack import gemini_music

        with tempfile.TemporaryDirectory() as tmp_dir:
            result = gemini_music(
                action="generate_weighted",
                prompts=[
                    {"text": "jazz piano", "weight": 0.7},
                    {"text": "ambient synth", "weight": 0.3}
                ],
                output_dir=tmp_dir,
                duration_seconds=5
            )

            assert result["success"] is True
            assert Path(result["file_path"]).exists()
            assert result["file_path"].endswith(".wav")
            assert result["num_prompts"] == 2
