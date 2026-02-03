"""
Gemini Video Tool

Generate and manipulate videos using Google's Veo models.

Usage Examples:
    from strands import Agent
    from strands_pack import gemini_video

    agent = Agent(tools=[gemini_video])

    # Generate a video from text
    agent.tool.gemini_video(
        action="generate",
        prompt="A cinematic drone shot of mountains at sunrise",
        duration_seconds=8
    )

    # Generate a video from an image (image-to-video)
    agent.tool.gemini_video(
        action="image_to_video",
        prompt="The kitten wakes up and stretches",
        image_path="sleeping_kitten.png"
    )

    # Extend a previously generated video
    agent.tool.gemini_video(
        action="extend",
        prompt="The butterfly lands on an orange flower",
        video_path="butterfly.mp4"
    )

Available Actions:
    - generate: Generate video from text using Veo models
        Parameters:
            prompt (str): Text description of the video to generate
            model (str): Veo model (default: "veo-3.1-generate-preview")
            duration_seconds (int): 4, 5, 6, or 8 seconds (default: 8)
            aspect_ratio (str): "16:9" or "9:16"
            resolution (str): "720p" or "1080p" (1080p requires 8s duration)
            negative_prompt (str): What NOT to include
            reference_images (list): Reference images (Veo 3.1 only, max 3)
            number_of_videos (int): Generate multiple variations at once (default: 1)
            fps (int): Frame rate control (if supported by your installed google-genai SDK)
            seed (int): Reproducibility seed (if supported by your installed google-genai SDK)
            enhance_prompt (bool): Let the tool expand the prompt (default: False)
            generate_audio (bool): (Deprecated/ignored) Veo 3/3.1 generate audio natively; Veo 2 is silent.
            person_generation (str): "ALLOW_ALL" | "ALLOW_ADULT" | "BLOCK_ALL" (if supported)
            compression_quality (int): Compression quality (if supported)
            output_dir (str): Output directory (default: "output")
            max_wait_seconds (int): Timeout (default: 600)

    - image_to_video: Generate video from an image (first frame)
        Parameters:
            prompt (str): Text description of the video motion
            image_path (str): Path to the first frame image (required)
            model (str): Veo model (default: "veo-3.1-generate-preview")
            duration_seconds (int): 4, 5, 6, or 8 seconds (default: 8)
            aspect_ratio (str): "16:9" or "9:16"
            resolution (str): "720p" or "1080p"
            negative_prompt (str): What NOT to include
            last_frame_path (str): Path to last frame for interpolation (Veo 3.1 only)
            number_of_videos (int): Generate multiple variations at once (default: 1)
            fps (int): Frame rate control (if supported by your installed google-genai SDK)
            seed (int): Reproducibility seed (if supported by your installed google-genai SDK)
            enhance_prompt (bool): Let the tool expand the prompt (default: False)
            generate_audio (bool): (Deprecated/ignored) Veo 3/3.1 generate audio natively; Veo 2 is silent.
            person_generation (str): "ALLOW_ALL" | "ALLOW_ADULT" | "BLOCK_ALL" (if supported)
            compression_quality (int): Compression quality (if supported)
            output_dir (str): Output directory (default: "output")
            max_wait_seconds (int): Timeout (default: 600)

    - extend: Extend a Veo-generated video by 7 seconds
        Parameters:
            prompt (str): Description of what happens in the extension
            video_path (str): Path to the Veo video to extend (required)
            model (str): "veo-3.1-generate-preview" or "veo-3.1-fast-generate-preview"
            number_of_videos (int): Generate multiple variations at once (default: 1)
            fps (int): Frame rate control (if supported by your installed google-genai SDK)
            seed (int): Reproducibility seed (if supported by your installed google-genai SDK)
            enhance_prompt (bool): Let the tool expand the prompt (default: False)
            generate_audio (bool): (Deprecated/ignored) Veo 3/3.1 generate audio natively; Veo 2 is silent.
            person_generation (str): "ALLOW_ALL" | "ALLOW_ADULT" | "BLOCK_ALL" (if supported)
            compression_quality (int): Compression quality (if supported)
            output_dir (str): Output directory (default: "output")
            max_wait_seconds (int): Timeout (default: 600)

Environment Variables:
    GOOGLE_API_KEY: Google AI API key (required)

Requires: pip install strands-pack[gemini]
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from strands import tool

# Type aliases
VideoModel = Literal[
    "veo-3.1-generate-preview",
    "veo-3.1-fast-generate-preview",
    "veo-3.0-generate-001",
    "veo-3.0-fast-generate-001",
    "veo-2.0-generate-001",
]
VideoAspectRatio = Literal["16:9", "9:16"]
VideoResolution = Literal["720p", "1080p"]
VideoDuration = Literal[4, 5, 6, 8]
Action = Literal["generate", "image_to_video", "extend"]
PersonGeneration = Literal["ALLOW_ALL", "ALLOW_ADULT", "BLOCK_ALL"]


# -----------------------------------------------------------------------------
# Internal Helper Functions
# -----------------------------------------------------------------------------


def _get_client(api_key: str):
    """Get a Gemini client instance."""
    try:
        from google import genai
    except ImportError:
        raise ImportError("google-genai not installed. Run: pip install strands-pack[gemini]") from None
    return genai.Client(api_key=api_key)


def _get_mime_type(path: Path) -> str:
    """Get MIME type from file extension."""
    suffix = path.suffix.lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    return mime_map.get(suffix, "image/png")


def _load_image(image_path: str):
    """Load an image file and return an Image object (for video generation)."""
    try:
        from google.genai import types
    except ImportError:
        raise ImportError("google-genai not installed. Run: pip install strands-pack[gemini]") from None

    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    with open(path, "rb") as f:
        image_bytes = f.read()

    mime_type = _get_mime_type(path)
    return types.Image(image_bytes=image_bytes, mime_type=mime_type)


def _build_generate_videos_config(types_mod, config_kwargs: dict) -> tuple[object | None, list[str]]:
    """
    Build a google.genai.types.GenerateVideosConfig in a version-tolerant way.

    The google-genai SDK evolves quickly; older versions may not accept newer config
    fields (e.g., fps/seed/audio controls). We attempt to instantiate the config and
    drop unsupported kwargs if we detect them from TypeError messages.
    """
    if not config_kwargs:
        return None, []

    dropped: list[str] = []
    # Work on a copy so callers can still introspect their requested keys if needed.
    kwargs = dict(config_kwargs)

    while True:
        try:
            return types_mod.GenerateVideosConfig(**kwargs), dropped
        except TypeError as e:
            msg = str(e)
            # Common pattern: "__init__() got an unexpected keyword argument 'fps'"
            needle = "unexpected keyword argument"
            if needle in msg and "'" in msg:
                try:
                    field = msg.split(needle, 1)[1].split("'")[1]
                except Exception:
                    raise
                if field in kwargs:
                    kwargs.pop(field, None)
                    dropped.append(field)
                    if not kwargs:
                        return None, dropped
                    continue
            raise


def _poll_operation(client, operation, max_wait_seconds: int) -> dict:
    """Poll operation until complete or timeout."""
    start_time = time.time()
    while not operation.done:
        if time.time() - start_time > max_wait_seconds:
            return {"success": False, "error": f"Video generation timed out after {max_wait_seconds} seconds"}
        time.sleep(10)
        operation = client.operations.get(operation)

    if operation.error:
        return {"success": False, "error": f"Generation failed: {operation.error}"}

    if not operation.response or not operation.response.generated_videos:
        return {"success": False, "error": "No video generated"}

    return {"success": True, "operation": operation}


def _is_generate_audio_unsupported(err: str) -> bool:
    msg = (err or "").lower()
    return "generate_audio" in msg and "not supported" in msg


def _is_encoding_field_unsupported(err: str) -> bool:
    msg = (err or "").lower()
    # Common observed backend error:
    # "`encoding` isn't supported by this model. Please remove it ..."
    return "encoding" in msg and "isn't supported" in msg


def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def _extract_last_frame(video_path: str, out_png_path: str) -> tuple[bool, str]:
    """
    Extract a near-last frame from a video using ffmpeg.
    Uses -sseof to seek from end, which avoids needing ffprobe/duration.
    """
    if not _ffmpeg_available():
        return False, "ffmpeg is not installed (required for extend fallback)"
    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-sseof",
                "-0.1",
                "-i",
                str(Path(video_path).expanduser().resolve()),
                "-vframes",
                "1",
                str(Path(out_png_path).expanduser().resolve()),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            return False, (result.stderr or "").strip() or "ffmpeg failed"
        return True, ""
    except Exception as e:
        return False, str(e)


def _save_video(client, generated_video, output_dir: str, prefix: str, api_key: str) -> dict:
    """Save generated video to file."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.mp4"
    file_path = output_path / filename

    video_obj = generated_video.video if hasattr(generated_video, 'video') else None

    if video_obj:
        try:
            client.files.download(file=video_obj)
            video_obj.save(str(file_path))
            return {"success": True, "file_path": str(file_path), "video_uri": getattr(video_obj, "uri", None)}
        except Exception:
            pass

        if hasattr(video_obj, 'video_bytes') and video_obj.video_bytes:
            with open(file_path, "wb") as f:
                f.write(video_obj.video_bytes)
            return {"success": True, "file_path": str(file_path), "video_uri": getattr(video_obj, "uri", None)}

        if hasattr(video_obj, 'uri') and video_obj.uri:
            import requests
            separator = "&" if "?" in video_obj.uri else "?"
            url = f"{video_obj.uri}{separator}key={api_key}"
            response = requests.get(url, allow_redirects=True, timeout=60)
            if response.status_code == 200:
                with open(file_path, "wb") as f:
                    f.write(response.content)
                return {"success": True, "file_path": str(file_path), "video_uri": getattr(video_obj, "uri", None)}
            return {"success": False, "error": f"Failed to download video: HTTP {response.status_code}"}

    return {"success": False, "error": "No video data in response"}


def _ok(**data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": True}
    out.update(data)
    return out


def _err(message: str, **data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": False, "error": message}
    out.update(data)
    return out


# -----------------------------------------------------------------------------
# Action Implementations
# -----------------------------------------------------------------------------


def _generate_video(
    prompt: str,
    model: str,
    duration_seconds: int,
    aspect_ratio: Optional[str],
    resolution: Optional[str],
    negative_prompt: Optional[str],
    reference_images: Optional[List[str]],
    number_of_videos: int,
    fps: Optional[int],
    seed: Optional[int],
    enhance_prompt: bool,
    generate_audio: Optional[bool],
    person_generation: Optional[str],
    compression_quality: Optional[int],
    output_dir: str,
    max_wait_seconds: int,
) -> dict:
    """Generate a video using Veo models (text-to-video)."""
    try:
        from google.genai import types
    except ImportError:
        return _err("google-genai not installed. Run: pip install strands-pack[gemini]")

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return _err("GOOGLE_API_KEY environment variable not set")

    is_veo31 = model.startswith("veo-3.1")
    is_veo2 = model.startswith("veo-2")

    if is_veo2:
        valid_durations = [5, 6, 8]
    else:
        valid_durations = [4, 6, 8]

    if duration_seconds not in valid_durations:
        return _err(f"Invalid duration for {model}. Must be one of: {valid_durations}")

    if resolution == "1080p":
        if is_veo2:
            return _err("1080p resolution not supported for Veo 2")
        if duration_seconds != 8:
            return _err("1080p resolution requires duration_seconds=8")

    if reference_images:
        if not is_veo31:
            return _err("Reference images only supported with Veo 3.1 models")
        if len(reference_images) > 3:
            return _err("Maximum 3 reference images supported")

    try:
        client = _get_client(api_key)

        if enhance_prompt:
            # Best-effort: nudge the model to expand/upgrade the prompt without extra API calls.
            prompt = (
                f"{prompt.rstrip()}\n\n"
                "Enhance and expand this prompt with coherent cinematic details (camera, lighting, scene), "
                "while staying faithful to the intent."
            )

        config_kwargs = {}
        if duration_seconds:
            config_kwargs["duration_seconds"] = duration_seconds
        if aspect_ratio:
            config_kwargs["aspect_ratio"] = aspect_ratio
        if resolution:
            config_kwargs["resolution"] = resolution
        if negative_prompt:
            config_kwargs["negative_prompt"] = negative_prompt
        if number_of_videos:
            config_kwargs["number_of_videos"] = number_of_videos
        if fps is not None:
            config_kwargs["fps"] = fps
        if seed is not None:
            config_kwargs["seed"] = seed
        # Veo 3/3.1 generate audio natively; Veo 2 is silent. Some backends reject a generate_audio parameter.
        # Keep the argument for compatibility but do not send it to the API.
        if person_generation is not None:
            config_kwargs["person_generation"] = person_generation
        if compression_quality is not None:
            config_kwargs["compression_quality"] = compression_quality

        if reference_images:
            refs = []
            for img_path in reference_images:
                try:
                    img = _load_image(img_path)
                    refs.append(types.VideoGenerationReferenceImage(
                        image=img,
                        reference_type="asset"
                    ))
                except FileNotFoundError as e:
                    return _err(str(e))
            config_kwargs["reference_images"] = refs

        config, dropped_fields = _build_generate_videos_config(types, config_kwargs)

        try:
            operation = client.models.generate_videos(
                model=model,
                prompt=prompt,
                config=config,
            )
        except Exception as e:
            # generate_audio isn't sent; just re-raise.
            raise

        result = _poll_operation(client, operation, max_wait_seconds)
        if not result["success"]:
            return result

        generated_videos = list(result["operation"].response.generated_videos or [])
        if not generated_videos:
            return _err("No video generated")

        file_paths: list[str] = []
        video_uris: list[str] = []
        for idx, gv in enumerate(generated_videos, start=1):
            save_result = _save_video(client, gv, output_dir, f"gemini_video_{idx}", api_key)
            if not save_result["success"]:
                return save_result
            file_paths.append(save_result["file_path"])
            if save_result.get("video_uri"):
                video_uris.append(save_result["video_uri"])

        warnings: list[str] = []
        if dropped_fields:
            warnings.append(
                f"Dropped unsupported config fields for your installed google-genai version: {sorted(dropped_fields)}"
            )
        if fps is not None and "fps" in dropped_fields:
            warnings.append("fps control is not supported by your installed google-genai SDK; re-encode via ffmpeg if needed.")
        if compression_quality is not None and "compression_quality" in dropped_fields:
            warnings.append("compression_quality is not supported by your installed google-genai SDK; re-encode via ffmpeg if needed.")

        return _ok(
            file_path=file_paths[0],
            file_paths=file_paths,
            message=f"Saved {len(file_paths)} video(s) to {output_dir}",
            model=model,
            duration=duration_seconds,
            has_audio=not is_veo2,
            number_of_videos=len(file_paths),
            video_uris=video_uris,
            # For extension, Gemini expects a Veo-generated server-side video reference, not an arbitrary local MP4.
            video_ref={"uri": video_uris[0], "mime_type": "video/mp4"} if video_uris else None,
            dropped_config_fields=dropped_fields,
            warnings=warnings,
            action="generate",
        )

    except Exception as e:
        return _err(str(e))


def _image_to_video(
    prompt: str,
    image_path: str,
    model: str,
    duration_seconds: int,
    aspect_ratio: Optional[str],
    resolution: Optional[str],
    negative_prompt: Optional[str],
    last_frame_path: Optional[str],
    number_of_videos: int,
    fps: Optional[int],
    seed: Optional[int],
    enhance_prompt: bool,
    generate_audio: Optional[bool],
    person_generation: Optional[str],
    compression_quality: Optional[int],
    output_dir: str,
    max_wait_seconds: int,
) -> dict:
    """Generate a video from an image using Veo models (image-to-video)."""
    try:
        from google.genai import types
    except ImportError:
        return _err("google-genai not installed. Run: pip install strands-pack[gemini]")

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return _err("GOOGLE_API_KEY environment variable not set")

    is_veo31 = model.startswith("veo-3.1")
    is_veo2 = model.startswith("veo-2")

    if last_frame_path and not is_veo31:
        return _err("Frame interpolation (last_frame) only supported with Veo 3.1 models")

    if is_veo2:
        valid_durations = [5, 6, 8]
    else:
        valid_durations = [4, 6, 8]

    if duration_seconds not in valid_durations:
        return _err(f"Invalid duration for {model}. Must be one of: {valid_durations}")

    if resolution == "1080p":
        if is_veo2:
            return _err("1080p resolution not supported for Veo 2")
        if duration_seconds != 8:
            return _err("1080p resolution requires duration_seconds=8")

    try:
        first_image = _load_image(image_path)
    except FileNotFoundError as e:
        return _err(str(e))

    try:
        client = _get_client(api_key)

        if enhance_prompt:
            prompt = (
                f"{prompt.rstrip()}\n\n"
                "Enhance and expand this prompt with coherent cinematic motion details, "
                "while staying faithful to the intent."
            )

        config_kwargs = {}
        if duration_seconds:
            config_kwargs["duration_seconds"] = duration_seconds
        if aspect_ratio:
            config_kwargs["aspect_ratio"] = aspect_ratio
        if resolution:
            config_kwargs["resolution"] = resolution
        if negative_prompt:
            config_kwargs["negative_prompt"] = negative_prompt
        if number_of_videos:
            config_kwargs["number_of_videos"] = number_of_videos
        if fps is not None:
            config_kwargs["fps"] = fps
        if seed is not None:
            config_kwargs["seed"] = seed
        # Veo 3/3.1 generate audio natively; Veo 2 is silent. Do not send generate_audio to API.
        if person_generation is not None:
            config_kwargs["person_generation"] = person_generation
        if compression_quality is not None:
            config_kwargs["compression_quality"] = compression_quality

        if last_frame_path:
            try:
                last_image = _load_image(last_frame_path)
                config_kwargs["last_frame"] = last_image
            except FileNotFoundError as e:
                return _err(str(e))

        config, dropped_fields = _build_generate_videos_config(types, config_kwargs)

        try:
            operation = client.models.generate_videos(
                model=model,
                prompt=prompt,
                image=first_image,
                config=config,
            )
        except Exception as e:
            raise

        result = _poll_operation(client, operation, max_wait_seconds)
        if not result["success"]:
            return result

        generated_videos = list(result["operation"].response.generated_videos or [])
        if not generated_videos:
            return _err("No video generated")
        prefix = "gemini_video_interpolation" if last_frame_path else "gemini_video_i2v"
        file_paths: list[str] = []
        video_uris: list[str] = []
        for idx, gv in enumerate(generated_videos, start=1):
            save_result = _save_video(client, gv, output_dir, f"{prefix}_{idx}", api_key)
            if not save_result["success"]:
                return save_result
            file_paths.append(save_result["file_path"])
            if save_result.get("video_uri"):
                video_uris.append(save_result["video_uri"])

        warnings: list[str] = []
        if dropped_fields:
            warnings.append(
                f"Dropped unsupported config fields for your installed google-genai version: {sorted(dropped_fields)}"
            )

        return _ok(
            file_path=file_paths[0],
            file_paths=file_paths,
            message=f"Saved {len(file_paths)} video(s) to {output_dir}",
            model=model,
            source_image=image_path,
            last_frame=last_frame_path,
            duration=duration_seconds,
            has_audio=not is_veo2,
            number_of_videos=len(file_paths),
            video_uris=video_uris,
            video_ref={"uri": video_uris[0], "mime_type": "video/mp4"} if video_uris else None,
            dropped_config_fields=dropped_fields,
            warnings=warnings,
            action="image_to_video",
        )

    except Exception as e:
        return _err(str(e))


def _extend_video(
    prompt: str,
    video_path: str,
    model: str,
    number_of_videos: int,
    fps: Optional[int],
    seed: Optional[int],
    enhance_prompt: bool,
    generate_audio: Optional[bool],
    person_generation: Optional[str],
    compression_quality: Optional[int],
    aspect_ratio: Optional[str],
    resolution: Optional[str],
    video_ref: Optional[dict],
    output_dir: str,
    max_wait_seconds: int,
) -> dict:
    """Extend a previously generated Veo video by 7 seconds (Veo 3.1 only)."""
    try:
        from google.genai import types
    except ImportError:
        return _err("google-genai not installed. Run: pip install strands-pack[gemini]")

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return _err("GOOGLE_API_KEY environment variable not set")

    video_file = Path(video_path)
    if not video_file.exists():
        return _err(f"Video file not found: {video_path}")

    try:
        client = _get_client(api_key)

        # IMPORTANT (per docs): extension expects a Veo-generated Video reference from a previous generation
        # (server-side), not an arbitrary local MP4. Prefer URI-based refs when available.
        video = None
        if isinstance(video_ref, dict) and video_ref.get("uri"):
            # Best effort: construct a Video from a URI.
            video = types.Video(uri=str(video_ref["uri"]), mime_type=str(video_ref.get("mime_type") or "video/mp4"))
        else:
            # Fallback: send local bytes. This often fails on some backends; we still try.
            with open(video_file, "rb") as f:
                video_bytes = f.read()
            video = types.Video(video_bytes=video_bytes, mime_type="video/mp4")

        if enhance_prompt:
            prompt = (
                f"{prompt.rstrip()}\n\n"
                "Enhance and expand this prompt with coherent cinematic continuation details, "
                "while staying faithful to the intent."
            )

        config_kwargs: Dict[str, Any] = {
            "number_of_videos": number_of_videos or 1,
        }
        # Per docs: extension is limited to 720p. Enforce 720p regardless of requested resolution.
        config_kwargs["resolution"] = "720p"
        if aspect_ratio:
            config_kwargs["aspect_ratio"] = aspect_ratio
        if fps is not None:
            config_kwargs["fps"] = fps
        if seed is not None:
            config_kwargs["seed"] = seed
        # Do not send generate_audio.
        if person_generation is not None:
            config_kwargs["person_generation"] = person_generation
        if compression_quality is not None:
            config_kwargs["compression_quality"] = compression_quality

        config, dropped_fields = _build_generate_videos_config(types, config_kwargs)

        try:
            operation = client.models.generate_videos(
                model=model,
                prompt=prompt,
                video=video,
                config=config,
            )
        except Exception as e:
            msg = str(e)
            # Some backends reject extend video input with "`encoding` isn't supported by this model".
            # In that case, fall back to chaining via image_to_video using the last frame of the previous clip.
            if _is_encoding_field_unsupported(msg):
                with tempfile.TemporaryDirectory(prefix="strands_gemini_video_extend_") as td:
                    frame_path = str(Path(td) / "last_frame.png")
                    ok, emsg = _extract_last_frame(video_path, frame_path)
                    if not ok:
                        return _err(
                            msg,
                            hint=(
                                "Your Gemini backend rejected 'extend' with an encoding/schema error. "
                                f"Automatic fallback requires ffmpeg to extract a last frame. ({emsg})"
                            ),
                        )
                    # Use image_to_video for continuation; keep the action as 'extend' but note the fallback mode.
                    cont = _image_to_video(
                        prompt=prompt,
                        image_path=frame_path,
                        model=model,
                        duration_seconds=8,
                        aspect_ratio=aspect_ratio,
                        resolution=resolution,
                        negative_prompt=None,
                        last_frame_path=None,
                        number_of_videos=number_of_videos or 1,
                        fps=fps,
                        seed=seed,
                        enhance_prompt=enhance_prompt,
                        generate_audio=generate_audio,
                        person_generation=person_generation,
                        compression_quality=compression_quality,
                        output_dir=output_dir,
                        max_wait_seconds=max_wait_seconds,
                    )
                    if cont.get("success"):
                        cont["action"] = "extend"
                        cont["extend_mode"] = "fallback_image_to_video"
                        cont["source_video"] = video_path
                    return cont
            raise

        result = _poll_operation(client, operation, max_wait_seconds)
        if not result["success"]:
            return result

        generated_videos = list(result["operation"].response.generated_videos or [])
        if not generated_videos:
            return _err("No video generated")

        file_paths: list[str] = []
        video_uris: list[str] = []
        for idx, gv in enumerate(generated_videos, start=1):
            save_result = _save_video(client, gv, output_dir, f"gemini_video_extended_{idx}", api_key)
            if not save_result["success"]:
                return save_result
            file_paths.append(save_result["file_path"])
            if save_result.get("video_uri"):
                video_uris.append(save_result["video_uri"])

        return _ok(
            file_path=file_paths[0],
            file_paths=file_paths,
            message=f"Saved {len(file_paths)} extended video(s) to {output_dir}",
            model=model,
            source_video=video_path,
            number_of_videos=len(file_paths),
            video_uris=video_uris,
            video_ref={"uri": video_uris[0], "mime_type": "video/mp4"} if video_uris else None,
            dropped_config_fields=dropped_fields,
            action="extend",
        )

    except Exception as e:
        msg = str(e)
        lower = msg.lower()
        hint = None
        if any(k in lower for k in ["codec", "unsupported", "invalidargument", "decode", "format", "container"]):
            hint = (
                "Veo 'extend' is picky about input encoding and often only accepts Veo-generated MP4s. "
                "If you hit an encoding/compatibility error, re-encode to a standard H.264/AAC MP4 and try again. "
                "Example: ffmpeg -i input.mp4 -c:v libx264 -pix_fmt yuv420p -profile:v baseline -level 3.1 "
                "-c:a aac -b:a 128k output.mp4"
            )
        return _err(msg, hint=hint)


# -----------------------------------------------------------------------------
# Main Tool Function
# -----------------------------------------------------------------------------


@tool
def gemini_video(
    action: str,
    prompt: str,
    image_path: Optional[str] = None,
    video_path: Optional[str] = None,
    model: str = "veo-3.1-generate-preview",
    duration_seconds: int = 8,
    aspect_ratio: Optional[str] = None,
    resolution: Optional[str] = None,
    negative_prompt: Optional[str] = None,
    reference_images: Optional[List[str]] = None,
    last_frame_path: Optional[str] = None,
    video_ref: Optional[dict] = None,
    number_of_videos: int = 1,
    fps: Optional[int] = None,
    seed: Optional[int] = None,
    enhance_prompt: bool = False,
    generate_audio: Optional[bool] = None,
    person_generation: Optional[PersonGeneration] = None,
    compression_quality: Optional[int] = None,
    output_dir: str = "output",
    max_wait_seconds: int = 600,
) -> Dict[str, Any]:
    """
    Generate and manipulate videos using Google's Veo models.

    Args:
        action: The action to perform. One of:
                - "generate": Generate video from text
                - "image_to_video": Generate video from an image (first frame)
                - "extend": Extend a Veo-generated video
        prompt: Text description for generation (required for all actions).
        image_path: Path to the first frame image (required for image_to_video).
        video_path: Path to the Veo video to extend (required for extend).
        model: Veo model to use. Options:
               - "veo-3.1-generate-preview" (default)
               - "veo-3.1-fast-generate-preview"
               - "veo-3.0-generate-001"
               - "veo-3.0-fast-generate-001"
               - "veo-2.0-generate-001"
        duration_seconds: Video duration (4, 5, 6, or 8 seconds). Default: 8.
                         Note: 5 is only valid for Veo 2; 4 is not valid for Veo 2.
        aspect_ratio: Output aspect ratio ("16:9" or "9:16").
        resolution: Output resolution ("720p" or "1080p"). 1080p requires 8s duration.
        negative_prompt: What NOT to include in the video.
        reference_images: List of image paths for reference (Veo 3.1 only, max 3).
        last_frame_path: Path to last frame for interpolation (Veo 3.1 only, image_to_video).
        number_of_videos: Generate multiple variations at once (default: 1).
        fps: Frame rate control (if supported by your installed google-genai SDK).
        seed: Reproducibility seed (if supported by your installed google-genai SDK).
        enhance_prompt: Let the tool enhance/expand the prompt before calling Veo (default: False).
        generate_audio: Toggle audio generation on/off (if supported). Note: Veo 2 has no audio.
        person_generation: People generation policy (best-effort; if supported). One of: "ALLOW_ALL", "ALLOW_ADULT", "BLOCK_ALL".
        compression_quality: Compression quality (if supported). If unsupported, re-encode via ffmpeg.
        output_dir: Directory to save output files. Default: "output".
        max_wait_seconds: Maximum time to wait for generation. Default: 600.

    Returns:
        dict with keys:
            - success: bool indicating if the operation succeeded
            - file_path: path to saved video (if successful)
            - message: status message
            - action: the action that was performed
            - error: error message (if failed)
            - Additional keys depending on action (model, duration, has_audio, etc.)

    Examples:
        >>> gemini_video(action="generate", prompt="A drone shot of mountains")
        >>> gemini_video(action="image_to_video", prompt="The cat wakes up", image_path="cat.png")
        >>> gemini_video(action="extend", prompt="The butterfly lands", video_path="video.mp4")
    """
    valid_actions = ["generate", "image_to_video", "extend"]

    if action not in valid_actions:
        return _err(f"Invalid action '{action}'. Must be one of: {valid_actions}")

    if not prompt:
        return _err(f"'prompt' is required for action '{action}'")

    # Validate required parameters for specific actions
    if action == "image_to_video" and not image_path:
        return _err("'image_path' is required for action 'image_to_video'")

    if action == "extend" and not video_path:
        return _err("'video_path' is required for action 'extend'")

    if number_of_videos < 1 or number_of_videos > 8:
        return _err("number_of_videos must be between 1 and 8")
    if fps is not None and (fps < 1 or fps > 120):
        return _err("fps must be between 1 and 120")
    if compression_quality is not None and (compression_quality < 1 or compression_quality > 100):
        return _err("compression_quality must be between 1 and 100")

    # Dispatch to appropriate handler
    if action == "generate":
        return _generate_video(
            prompt=prompt,
            model=model,
            duration_seconds=duration_seconds,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            negative_prompt=negative_prompt,
            reference_images=reference_images,
            number_of_videos=number_of_videos,
            fps=fps,
            seed=seed,
            enhance_prompt=enhance_prompt,
            generate_audio=generate_audio,
            person_generation=person_generation,
            compression_quality=compression_quality,
            output_dir=output_dir,
            max_wait_seconds=max_wait_seconds,
        )
    elif action == "image_to_video":
        return _image_to_video(
            prompt=prompt,
            image_path=image_path,  # type: ignore
            model=model,
            duration_seconds=duration_seconds,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            negative_prompt=negative_prompt,
            last_frame_path=last_frame_path,
            number_of_videos=number_of_videos,
            fps=fps,
            seed=seed,
            enhance_prompt=enhance_prompt,
            generate_audio=generate_audio,
            person_generation=person_generation,
            compression_quality=compression_quality,
            output_dir=output_dir,
            max_wait_seconds=max_wait_seconds,
        )
    elif action == "extend":
        return _extend_video(
            prompt=prompt,
            video_path=video_path,  # type: ignore
            model=model,
            number_of_videos=number_of_videos,
            fps=fps,
            seed=seed,
            enhance_prompt=enhance_prompt,
            generate_audio=generate_audio,
            person_generation=person_generation,
            compression_quality=compression_quality,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            video_ref=video_ref,
            output_dir=output_dir,
            max_wait_seconds=max_wait_seconds,
        )

    return _err(f"Unhandled action: {action}")
