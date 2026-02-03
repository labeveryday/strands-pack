"""
Gemini Music Tool

Generate music using Google's Lyria RealTime model.

Usage Examples:
    from strands import Agent
    from strands_pack import gemini_music

    agent = Agent(tools=[gemini_music])

    # Generate music
    agent.tool.gemini_music(
        action="generate",
        prompt="upbeat electronic dance track with synth leads",
        duration_seconds=30
    )

    # Generate music with weighted prompts
    agent.tool.gemini_music(
        action="generate_weighted",
        prompts=[
            {"text": "jazz piano", "weight": 0.7},
            {"text": "ambient synth", "weight": 0.3}
        ],
        duration_seconds=30
    )

Available Actions:
    - generate: Generate music using Lyria RealTime
        Parameters:
            prompt (str): Text description of the music to generate
            output_dir (str): Output directory (default: "output")
            duration_seconds (int): Duration 5-120 seconds (default: 30)

    - generate_weighted: Generate music with weighted style prompts
        Parameters:
            prompts (list): List of {"text": str, "weight": float} dicts (required)
            output_dir (str): Output directory (default: "output")
            duration_seconds (int): Duration 5-120 seconds (default: 30)

Environment Variables:
    GOOGLE_API_KEY: Google AI API key (required)

Requires: pip install strands-pack[gemini]

Note:
    Prompts referencing specific artists or copyrighted songs (e.g., "50 cent in the club")
    will cause the model to hang indefinitely due to content filtering. Describe the style
    instead (e.g., "early 2000s club hip hop, chopped and screwed, slowed tempo").
"""

import asyncio
import os
import wave
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from strands import tool

# Type aliases
Action = Literal["generate", "generate_weighted"]
MusicGenerationMode = Literal["QUALITY", "DIVERSITY", "VOCALIZATION"]


# -----------------------------------------------------------------------------
# Internal Helper Functions
# -----------------------------------------------------------------------------


def _get_client_alpha(api_key: str):
    """Get a Gemini client instance with v1alpha API version (for Lyria)."""
    try:
        from google import genai
    except ImportError:
        raise ImportError("google-genai not installed. Run: pip install strands-pack[gemini]") from None
    return genai.Client(api_key=api_key, http_options={'api_version': 'v1alpha'})


def _save_audio_to_wav(audio_data: bytes, file_path: str) -> None:
    """Save raw PCM audio data to WAV file (48kHz stereo 16-bit)."""
    with wave.open(file_path, 'wb') as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(48000)
        wav_file.writeframes(audio_data)


def _append_prompt_controls(
    text: str,
    bpm: Optional[int],
    scale: Optional[str],
    brightness: Optional[float],
    density: Optional[float],
    mute_bass: bool,
    mute_drums: bool,
    only_bass_and_drums: bool,
) -> str:
    """
    Add style controls to prompt text.

    Note: These are best-effort hints; the realtime music model may not strictly obey them.
    """
    parts: List[str] = []
    if bpm is not None:
        parts.append(f"Tempo: {bpm} BPM.")
    if scale:
        parts.append(f"Key/scale: {scale}.")
    if brightness is not None:
        parts.append(f"Tonal brightness: {brightness}.")
    if density is not None:
        parts.append(f"Density/busyness: {density}.")

    if only_bass_and_drums:
        parts.append("Only bass and drums/percussion. No melody, no vocals.")
    else:
        if mute_bass:
            parts.append("No bassline / muted bass.")
        if mute_drums:
            parts.append("No drums / no percussion.")

    if not parts:
        return text
    return f"{text.rstrip()}\n\n" + " ".join(parts)


def _coerce_weighted_prompts(
    types_mod: Any,
    prompts: list,
    bpm: Optional[int],
    scale: Optional[str],
    brightness: Optional[float],
    density: Optional[float],
    mute_bass: bool,
    mute_drums: bool,
    only_bass_and_drums: bool,
) -> list:
    """Convert mixed prompt inputs into WeightedPrompt objects, appending prompt-level controls."""
    weighted_prompts = []
    for p in prompts:
        if isinstance(p, dict):
            txt = _append_prompt_controls(
                text=p.get("text", ""),
                bpm=bpm,
                scale=scale,
                brightness=brightness,
                density=density,
                mute_bass=mute_bass,
                mute_drums=mute_drums,
                only_bass_and_drums=only_bass_and_drums,
            )
            weighted_prompts.append(types_mod.WeightedPrompt(text=txt, weight=p.get("weight", 1.0)))
        else:
            txt = _append_prompt_controls(
                text=str(p),
                bpm=bpm,
                scale=scale,
                brightness=brightness,
                density=density,
                mute_bass=mute_bass,
                mute_drums=mute_drums,
                only_bass_and_drums=only_bass_and_drums,
            )
            weighted_prompts.append(types_mod.WeightedPrompt(text=txt, weight=1.0))
    return weighted_prompts


async def _maybe_set_music_generation_config(
    session: Any,
    types_mod: Any,
    *,
    bpm: Optional[int],
    scale: Optional[str],
    brightness: Optional[float],
    density: Optional[float],
    seed: Optional[int],
    temperature: Optional[float],
    guidance: Optional[float],
    music_generation_mode: Optional[str],
) -> Dict[str, Any]:
    """
    Best-effort attempt to set generation config on the live music session.

    The google-genai realtime music API is evolving, so this function uses runtime feature
    detection. If config isn't supported, it returns success=False and includes a reason.
    """
    # Find a setter method on the session
    setter = None
    for name in ("set_music_generation_config", "set_generation_config", "set_config"):
        if hasattr(session, name):
            setter = getattr(session, name)
            break
    if setter is None:
        return {"success": False, "reason": "no_session_config_method"}

    payload: Dict[str, Any] = {}
    for k, v in (
        ("bpm", bpm),
        ("scale", scale),
        ("brightness", brightness),
        ("density", density),
        ("seed", seed),
        ("temperature", temperature),
        ("guidance", guidance),
        ("music_generation_mode", music_generation_mode),
    ):
        if v is not None:
            payload[k] = v

    if not payload:
        return {"success": False, "reason": "no_config_fields_provided"}

    # Try to construct a config object if available; otherwise pass a dict.
    cfg_obj = None
    for cls_name in ("MusicGenerationConfig", "LiveMusicGenerationConfig", "GenerationConfig"):
        cls = getattr(types_mod, cls_name, None)
        if cls is not None:
            try:
                cfg_obj = cls(**payload)
                break
            except TypeError:
                cfg_obj = None

    try:
        if cfg_obj is not None:
            await setter(cfg_obj)
            return {"success": True, "applied": list(payload.keys()), "via": type(cfg_obj).__name__}
        await setter(payload)
        return {"success": True, "applied": list(payload.keys()), "via": "dict"}
    except Exception as e:
        return {"success": False, "reason": "config_set_failed", "error": str(e), "attempted": list(payload.keys())}


async def _generate_music_async(
    api_key: str,
    prompts: list,
    duration_seconds: int,
    *,
    bpm: Optional[int] = None,
    scale: Optional[str] = None,
    brightness: Optional[float] = None,
    density: Optional[float] = None,
    seed: Optional[int] = None,
    temperature: Optional[float] = None,
    guidance: Optional[float] = None,
    music_generation_mode: Optional[str] = None,
    mute_bass: bool = False,
    mute_drums: bool = False,
    only_bass_and_drums: bool = False,
) -> bytes:
    """Async music generation using Lyria RealTime WebSocket."""
    try:
        from google.genai import types
    except ImportError:
        raise ImportError("google-genai not installed. Run: pip install strands-pack[gemini]") from None

    client = _get_client_alpha(api_key)

    weighted_prompts = _coerce_weighted_prompts(
        types_mod=types,
        prompts=prompts,
        bpm=bpm,
        scale=scale,
        brightness=brightness,
        density=density,
        mute_bass=mute_bass,
        mute_drums=mute_drums,
        only_bass_and_drums=only_bass_and_drums,
    )

    # We receive raw PCM chunks. To get a deterministic duration, stop once we've
    # collected enough bytes for the target duration (48kHz stereo 16-bit).
    bytes_per_second = 48000 * 2 * 2  # sample_rate * channels * bytes_per_sample
    bytes_needed = duration_seconds * bytes_per_second
    frame_size = 2 * 2  # channels * bytes_per_sample (4 bytes per stereo frame)

    audio_chunks: List[bytes] = []
    bytes_collected = 0

    # Transient errors (503/unavailable) happen with realtime models; retry a couple times.
    last_err: Optional[Exception] = None
    for attempt in range(3):
        try:
            async with client.aio.live.music.connect(model='lyria-realtime-exp') as session:
                await session.set_weighted_prompts(weighted_prompts)
                # Best-effort: set structured controls if supported by the client/session.
                await _maybe_set_music_generation_config(
                    session,
                    types,
                    bpm=bpm,
                    scale=scale,
                    brightness=brightness,
                    density=density,
                    seed=seed,
                    temperature=temperature,
                    guidance=guidance,
                    music_generation_mode=music_generation_mode,
                )
                await session.play()

                async for msg in session.receive():
                    if msg.server_content and msg.server_content.audio_chunks:
                        for audio_chunk in msg.server_content.audio_chunks:
                            if audio_chunk.data:
                                remaining = bytes_needed - bytes_collected
                                if remaining <= 0:
                                    break

                                data = audio_chunk.data
                                if len(data) > remaining:
                                    # Trim to an even number of frames to keep WAV sane.
                                    trimmed = data[:remaining]
                                    trimmed = trimmed[: (len(trimmed) // frame_size) * frame_size]
                                    if trimmed:
                                        audio_chunks.append(trimmed)
                                        bytes_collected += len(trimmed)
                                    break

                                audio_chunks.append(data)
                                bytes_collected += len(data)

                    if bytes_collected >= bytes_needed:
                        break

                await session.stop()

            return b"".join(audio_chunks)
        except Exception as e:
            last_err = e
            msg = str(e).lower()
            retryable = ("503" in msg) or ("unavailable" in msg) or ("temporar" in msg) or ("resource" in msg)
            if (attempt < 2) and retryable:
                await asyncio.sleep(2 * (attempt + 1))
                continue
            raise

    # Should be unreachable, but keeps type-checkers happy.
    if last_err:
        raise last_err

    return b"".join(audio_chunks)


def _ok(**data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": True}
    out.update(data)
    return out


def _err(message: str, **data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": False, "error": message}
    out.update(data)
    return out


# -----------------------------------------------------------------------------
# Main Tool Function
# -----------------------------------------------------------------------------


@tool
def gemini_music(
    action: str,
    prompt: Optional[str] = None,
    prompts: Optional[List[Dict[str, Any]]] = None,
    duration_seconds: int = 30,
    output_dir: str = "output",
    max_retries: int = 2,
    bpm: Optional[int] = None,
    scale: Optional[str] = None,
    brightness: Optional[float] = None,
    density: Optional[float] = None,
    seed: Optional[int] = None,
    temperature: Optional[float] = None,
    guidance: Optional[float] = None,
    mute_bass: bool = False,
    mute_drums: bool = False,
    only_bass_and_drums: bool = False,
    music_generation_mode: Optional[MusicGenerationMode] = None,
) -> Dict[str, Any]:
    """
    Generate music using Google's Lyria RealTime model.

    Args:
        action: The action to perform. One of:
            - "generate": Generate music from a text prompt
            - "generate_weighted": Generate music with weighted style prompts
        prompt: Text description of the music to generate (required for "generate" action)
        prompts: List of {"text": str, "weight": float} dicts (required for "generate_weighted" action)
        duration_seconds: Duration of the music in seconds (5-120, default: 30)
        output_dir: Directory to save the output file (default: "output")
        max_retries: Retries for transient service failures (default: 2)
        bpm: Tempo control (best-effort; may be enforced by model or treated as a hint)
        scale: Musical key/scale, e.g. "C minor" (best-effort)
        brightness: Tonal brightness (best-effort; typically 0.0-1.0, but model-dependent)
        density: Arrangement density/busyness (best-effort; typically 0.0-1.0, but model-dependent)
        seed: Reproducibility seed (if supported by the client/session)
        temperature: Randomness/creativity (if supported by the client/session)
        guidance: How strongly to follow the prompt (if supported by the client/session)
        mute_bass: Best-effort "no bass" hint (not true stem muting)
        mute_drums: Best-effort "no drums" hint (not true stem muting)
        only_bass_and_drums: Best-effort rhythm-section-only hint
        music_generation_mode: "QUALITY", "DIVERSITY", or "VOCALIZATION" (if supported)

    Returns:
        dict with keys:
            - success: bool indicating if the operation succeeded
            - file_path: path to saved WAV file (if successful)
            - message: status message
            - action: the action that was performed
            - duration: the duration in seconds
            - error: error message (if failed)
            - num_prompts: number of prompts used (for generate_weighted)

    Examples:
        >>> gemini_music(action="generate", prompt="upbeat jazz", duration_seconds=30)
        >>> gemini_music(action="generate_weighted", prompts=[{"text": "jazz", "weight": 0.7}])

    Note:
        Prompts referencing specific artists or copyrighted songs will cause the model
        to hang indefinitely due to content filtering. Describe the style instead
        (e.g., "early 2000s club hip hop chopped and screwed" instead of "50 cent in the club").
    """
    # Validate action
    valid_actions = ["generate", "generate_weighted"]
    action = (action or "").strip()
    if action not in valid_actions:
        return _err(f"Invalid action '{action}'. Must be one of: {valid_actions}")

    # Validate duration
    if duration_seconds < 5 or duration_seconds > 120:
        return _err("duration_seconds must be between 5 and 120")

    # Validate controls
    if bpm is not None and (bpm < 20 or bpm > 300):
        return _err("bpm must be between 20 and 300")
    if brightness is not None and (brightness < 0 or brightness > 1):
        return _err("brightness must be between 0.0 and 1.0")
    if density is not None and (density < 0 or density > 1):
        return _err("density must be between 0.0 and 1.0")
    if temperature is not None and (temperature < 0 or temperature > 2):
        return _err("temperature must be between 0.0 and 2.0")
    if guidance is not None and guidance < 0:
        return _err("guidance must be >= 0")
    if only_bass_and_drums and (mute_bass or mute_drums):
        return _err("only_bass_and_drums cannot be combined with mute_bass or mute_drums")

    # Validate required parameters based on action
    if action == "generate":
        if not prompt:
            return _err("'prompt' is required for action 'generate'")

    if action == "generate_weighted":
        if prompts is None:
            return _err("'prompts' is required for action 'generate_weighted'")
        if not prompts:
            return _err("At least one prompt is required")

    # Check API key
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return _err("GOOGLE_API_KEY environment variable not set")

    try:
        # Prepare prompts list for the async function
        if action == "generate":
            prompt_list = [prompt]
        else:
            prompt_list = prompts

        # Generate music
        # _generate_music_async retries internally; max_retries is kept for API compatibility/future tuning.
        _ = max_retries
        audio_data = asyncio.run(
            _generate_music_async(
                api_key=api_key,
                prompts=prompt_list,
                duration_seconds=duration_seconds,
                bpm=bpm,
                scale=scale,
                brightness=brightness,
                density=density,
                seed=seed,
                temperature=temperature,
                guidance=guidance,
                music_generation_mode=music_generation_mode,
                mute_bass=mute_bass,
                mute_drums=mute_drums,
                only_bass_and_drums=only_bass_and_drums,
            )
        )

        if not audio_data:
            return _err("No audio data generated")

        # Save output
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if action == "generate":
            filename = f"gemini_music_{timestamp}.wav"
        else:
            filename = f"gemini_music_weighted_{timestamp}.wav"
        file_path = output_path / filename

        _save_audio_to_wav(audio_data, str(file_path))

        result = {
            "file_path": str(file_path),
            "message": f"Music saved to {file_path}",
            "duration": duration_seconds,
            "action": action,
            "controls": {
                "bpm": bpm,
                "scale": scale,
                "brightness": brightness,
                "density": density,
                "seed": seed,
                "temperature": temperature,
                "guidance": guidance,
                "mute_bass": mute_bass,
                "mute_drums": mute_drums,
                "only_bass_and_drums": only_bass_and_drums,
                "music_generation_mode": music_generation_mode,
            },
        }

        if action == "generate_weighted":
            result["num_prompts"] = len(prompts)

        return _ok(**result)

    except ImportError as e:
        return _err(str(e))
    except Exception as e:
        msg = str(e)
        lower = msg.lower()
        hint = None
        if ("503" in lower) or ("unavailable" in lower) or ("temporar" in lower):
            hint = "The realtime music service appears temporarily unavailable. Try again in a minute or two."
        return _err(msg, hint=hint)
