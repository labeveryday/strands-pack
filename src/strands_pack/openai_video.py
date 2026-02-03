"""
OpenAI Video Tool

Generate videos using OpenAI's Videos API (e.g., Sora models).

This tool follows the same "single tool with an action parameter" pattern used across strands-pack.
It also supports `client_override` for unit tests / advanced usage to avoid network calls.

Requires:
    pip install "strands-pack[openai]"

Environment:
    - OPENAI_API_KEY (required unless you pass client_override)

Actions
-------
- generate
    Create a new video job, wait for completion, and download the MP4 (default).
    Parameters:
      - prompt (str, required)
      - model (str, default "sora-2")
      - seconds (int, default 4; allowed 4/8/12)
      - size (str, default "720x1280")
      - input_reference_path (str, optional): path to an image reference
      - output_dir (str, default "output")
      - output_filename (str, optional; without extension)
      - variant (str, optional): which asset to download; default None (MP4)
      - max_wait_seconds (int, default 600)
      - poll_interval_seconds (int, default 5)

- create
    Create a new video job (does not wait / download).

- wait
    Poll a video job until it reaches a terminal status.
    Parameters:
      - video_id (str, required)

- download
    Download video bytes (or variant) for a completed job and save to disk.
    Parameters:
      - video_id (str, required)

- remix
    Create a remix job from a completed video (does not wait / download by default).
    Parameters:
      - video_id (str, required)
      - prompt (str, required)

- retrieve / list / delete
    Thin wrappers around the API.
"""

from __future__ import annotations

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from strands import tool

try:
    from openai import OpenAI

    HAS_OPENAI = True
except ImportError:  # pragma: no cover
    OpenAI = None
    HAS_OPENAI = False


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


def _require_deps(client_override: Any) -> Optional[Dict[str, Any]]:
    if client_override is not None:
        return None
    if HAS_OPENAI:
        return None
    return _err(
        "Missing OpenAI dependency. Install with: pip install strands-pack[openai]",
        error_type="MissingDependency",
    )


def _get_client(client_override: Any):
    if client_override is not None:
        return client_override
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    return OpenAI(api_key=api_key)


def _require_videos_api(client: Any) -> Optional[Dict[str, Any]]:
    # Newer OpenAI python clients expose `client.videos`.
    if getattr(client, "videos", None) is None:
        return _err(
            "Your installed openai package does not expose `client.videos`. Upgrade with: pip install -U openai",
            error_type="UnsupportedClient",
        )
    return None


def _as_video_dict(video_obj: Any) -> Dict[str, Any]:
    """Best-effort conversion of OpenAI client objects to plain dicts."""
    if video_obj is None:
        return {}
    if isinstance(video_obj, dict):
        return dict(video_obj)
    # Common OpenAI response objects implement model_dump()
    dump = getattr(video_obj, "model_dump", None)
    if callable(dump):
        try:
            return dump()
        except Exception:  # pragma: no cover
            pass
    # Fallback: extract a few likely attributes
    keys = [
        "id",
        "object",
        "model",
        "status",
        "progress",
        "created_at",
        "completed_at",
        "expires_at",
        "size",
        "seconds",
        "quality",
        "prompt",
        "remixed_from_video_id",
        "error",
    ]
    out: Dict[str, Any] = {}
    for k in keys:
        if hasattr(video_obj, k):
            out[k] = getattr(video_obj, k)
    return out


def _open_reference_file(path: str):
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Reference file not found: {path}")
    return open(p, "rb")


def _save_video_bytes(video_bytes: bytes, output_dir: str, output_filename: Optional[str] = None) -> Path:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if output_filename:
        fname = f"{output_filename}.mp4" if not output_filename.lower().endswith(".mp4") else output_filename
        out_path = out_dir / fname
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = out_dir / f"openai_video_{ts}.mp4"
    out_path.write_bytes(video_bytes)
    return out_path


def _download_content_bytes(client: Any, video_id: str, variant: Optional[str] = None) -> bytes:
    """Download video bytes using the OpenAI client, handling minor API/client variations."""
    dl = getattr(client.videos, "download_content", None)
    if not callable(dl):
        raise AttributeError("client.videos.download_content is not available in this OpenAI client")

    try:
        resp = dl(video_id=video_id, variant=variant) if variant else dl(video_id=video_id)
    except TypeError:
        # Older signature variants
        resp = dl(video_id, variant=variant) if variant else dl(video_id)

    if isinstance(resp, (bytes, bytearray)):
        return bytes(resp)
    read = getattr(resp, "read", None)
    if callable(read):
        data = read()
        if isinstance(data, (bytes, bytearray)):
            return bytes(data)
    # Some http clients expose .content
    content = getattr(resp, "content", None)
    if isinstance(content, (bytes, bytearray)):
        return bytes(content)
    raise ValueError("Unexpected download response; expected bytes or a stream-like object with .read()")


def _create_job(
    *,
    client: Any,
    prompt: str,
    model: str,
    seconds: int,
    size: str,
    input_reference_path: Optional[str],
) -> Dict[str, Any]:
    if not prompt or str(prompt).strip() == "":
        return _err("'prompt' is required", error_type="InvalidRequest")
    if seconds not in (4, 8, 12):
        return _err("seconds must be one of: 4, 8, 12", error_type="InvalidRequest")

    ref_file = None
    try:
        if input_reference_path:
            ref_file = _open_reference_file(input_reference_path)

        kwargs: Dict[str, Any] = {
            "prompt": prompt,
            "model": model,
            "seconds": str(seconds),
            "size": size,
        }
        if ref_file is not None:
            kwargs["input_reference"] = ref_file

        try:
            video = client.videos.create(**kwargs)
        finally:
            if ref_file is not None:
                try:
                    ref_file.close()
                except Exception:  # pragma: no cover
                    pass

        vdict = _as_video_dict(video)
        return _ok(action="create", video=vdict, video_id=vdict.get("id"))

    except FileNotFoundError as e:
        return _err(str(e), error_type="FileNotFound")
    except Exception as e:
        return _err(str(e), error_type=type(e).__name__)


def _retrieve_job(client: Any, video_id: str) -> Dict[str, Any]:
    if not video_id:
        return _err("'video_id' is required", error_type="InvalidRequest")
    try:
        try:
            video = client.videos.retrieve(video_id)
        except TypeError:
            video = client.videos.retrieve(video_id=video_id)
        vdict = _as_video_dict(video)
        return _ok(action="retrieve", video=vdict, video_id=vdict.get("id"))
    except Exception as e:
        return _err(str(e), error_type=type(e).__name__, action="retrieve", video_id=video_id)


def _wait_for_completion(
    client: Any,
    video_id: str,
    *,
    max_wait_seconds: int = 600,
    poll_interval_seconds: int = 5,
) -> Dict[str, Any]:
    start = time.time()
    last: Dict[str, Any] = {}
    while True:
        res = _retrieve_job(client, video_id)
        if not res.get("success"):
            return res
        last = res
        status = (res.get("video") or {}).get("status")
        if status in ("completed", "failed", "cancelled", "canceled", "expired"):
            if status == "completed":
                return _ok(action="wait", video=res.get("video"), video_id=video_id, status=status)
            # For non-completed terminal states, return a failure with full context.
            v = res.get("video") or {}
            err_payload = v.get("error")
            return _err(
                f"Video job finished with status '{status}'",
                error_type="JobFailed",
                action="wait",
                video_id=video_id,
                status=status,
                video=v,
                error=err_payload,
            )
        if time.time() - start > max_wait_seconds:
            return _err(
                f"Video job timed out after {max_wait_seconds} seconds",
                error_type="Timeout",
                action="wait",
                video_id=video_id,
                last_status=status,
                last_video=res.get("video"),
            )
        time.sleep(max(1, int(poll_interval_seconds)))


def _download_to_file(
    client: Any,
    video_id: str,
    *,
    variant: Optional[str],
    output_dir: str,
    output_filename: Optional[str],
) -> Dict[str, Any]:
    if not video_id:
        return _err("'video_id' is required", error_type="InvalidRequest")
    try:
        data = _download_content_bytes(client, video_id, variant=variant)
        path = _save_video_bytes(data, output_dir=output_dir, output_filename=output_filename)
        return _ok(action="download", video_id=video_id, file_path=str(path), variant=variant, bytes=len(data))
    except Exception as e:
        return _err(str(e), error_type=type(e).__name__, action="download", video_id=video_id)


def _remix_job(client: Any, video_id: str, prompt: str) -> Dict[str, Any]:
    if not video_id:
        return _err("'video_id' is required", error_type="InvalidRequest")
    if not prompt or str(prompt).strip() == "":
        return _err("'prompt' is required", error_type="InvalidRequest")
    try:
        # Typical signature per docs: client.videos.remix(video_id="...", prompt="...")
        remix = client.videos.remix(video_id=video_id, prompt=prompt)
        vdict = _as_video_dict(remix)
        return _ok(action="remix", video=vdict, video_id=vdict.get("id"), remixed_from_video_id=video_id)
    except TypeError:
        # Alternate signature
        try:
            remix = client.videos.remix(video_id, prompt=prompt)
            vdict = _as_video_dict(remix)
            return _ok(action="remix", video=vdict, video_id=vdict.get("id"), remixed_from_video_id=video_id)
        except Exception as e:  # pragma: no cover
            return _err(str(e), error_type=type(e).__name__, action="remix", video_id=video_id)
    except Exception as e:
        return _err(str(e), error_type=type(e).__name__, action="remix", video_id=video_id)


def _list_jobs(client: Any, *, after: Optional[str] = None, limit: Optional[int] = None, order: Optional[str] = None) -> Dict[str, Any]:
    try:
        kwargs: Dict[str, Any] = {}
        if after:
            kwargs["after"] = after
        if limit is not None:
            kwargs["limit"] = int(limit)
        if order:
            kwargs["order"] = order
        page = client.videos.list(**kwargs) if kwargs else client.videos.list()
        data = getattr(page, "data", None) or []
        items = [_as_video_dict(v) for v in data]
        return _ok(action="list", count=len(items), videos=items)
    except Exception as e:
        return _err(str(e), error_type=type(e).__name__, action="list")


def _delete_job(client: Any, video_id: str) -> Dict[str, Any]:
    if not video_id:
        return _err("'video_id' is required", error_type="InvalidRequest")
    try:
        try:
            res = client.videos.delete(video_id)
        except TypeError:
            res = client.videos.delete(video_id=video_id)
        vdict = _as_video_dict(res)
        return _ok(action="delete", video=vdict, video_id=video_id)
    except Exception as e:
        return _err(str(e), error_type=type(e).__name__, action="delete", video_id=video_id)


@tool
def openai_video(
    action: str,
    prompt: Optional[str] = None,
    model: str = "sora-2",
    seconds: int = 4,
    size: str = "720x1280",
    input_reference_path: Optional[str] = None,
    video_id: Optional[str] = None,
    variant: Optional[str] = None,
    output_dir: str = "output",
    output_filename: Optional[str] = None,
    max_wait_seconds: int = 600,
    poll_interval_seconds: int = 5,
    after: Optional[str] = None,
    limit: Optional[int] = None,
    order: Optional[str] = None,
    client_override: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    OpenAI Videos API wrapper.

    For most users, `action="generate"` is the easiest end-to-end flow.

    Args:
        action: The action to perform. One of: "generate", "create", "wait",
            "download", "remix", "retrieve", "list", "delete".
        prompt: Text prompt describing the video to generate. Required for
            "generate", "create", and "remix" actions.
        model: The model to use for video generation. Default is "sora-2".
        seconds: Duration of the video in seconds. Must be 4, 8, or 12. Default is 4.
        size: Video dimensions as "WxH" (e.g., "720x1280"). Default is "720x1280".
        input_reference_path: Optional path to an image file to use as a reference
            for video generation.
        video_id: The ID of an existing video job. Required for "wait", "download",
            "remix", "retrieve", and "delete" actions.
        variant: Optional variant to download (e.g., for different formats).
        output_dir: Directory to save downloaded videos. Default is "output".
        output_filename: Optional filename for the downloaded video (without extension).
        max_wait_seconds: Maximum time to wait for video completion in seconds.
            Default is 600.
        poll_interval_seconds: Interval between status checks in seconds. Default is 5.
        after: Pagination cursor for "list" action.
        limit: Maximum number of items to return for "list" action.
        order: Sort order for "list" action.
        client_override: Optional OpenAI client instance for testing or custom configuration.

    Returns:
        A dictionary with "success" (bool) and action-specific data or error information.
    """

    action = (action or "").strip().lower()
    valid_actions = ("generate", "create", "wait", "download", "remix", "retrieve", "list", "delete")
    if action not in valid_actions:
        return _err("Unknown action", error_type="InvalidAction", available_actions=list(valid_actions), action=action)

    if err := _require_deps(client_override):
        return err

    try:
        client = _get_client(client_override)
        if verr := _require_videos_api(client):
            return verr

        if action == "create":
            return _create_job(
                client=client,
                prompt=str(prompt or ""),
                model=str(model),
                seconds=int(seconds),
                size=str(size),
                input_reference_path=str(input_reference_path) if input_reference_path else None,
            )

        if action == "retrieve":
            return _retrieve_job(client, str(video_id or ""))

        if action == "list":
            return _list_jobs(
                client,
                after=after,
                limit=limit,
                order=order,
            )

        if action == "delete":
            return _delete_job(client, str(video_id or ""))

        if action == "remix":
            return _remix_job(client, str(video_id or ""), str(prompt or ""))

        if action == "wait":
            return _wait_for_completion(
                client,
                str(video_id or ""),
                max_wait_seconds=int(max_wait_seconds),
                poll_interval_seconds=int(poll_interval_seconds),
            )

        if action == "download":
            return _download_to_file(
                client,
                str(video_id or ""),
                variant=str(variant) if variant else None,
                output_dir=str(output_dir),
                output_filename=str(output_filename) if output_filename else None,
            )

        # action == "generate"
        create_res = _create_job(
            client=client,
            prompt=str(prompt or ""),
            model=str(model),
            seconds=int(seconds),
            size=str(size),
            input_reference_path=str(input_reference_path) if input_reference_path else None,
        )
        if not create_res.get("success"):
            create_res["action"] = "generate"
            return create_res

        created_id = create_res.get("video_id") or (create_res.get("video") or {}).get("id")
        if not created_id:
            return _err("Create succeeded but no video_id was returned", error_type="UnexpectedResponse", action="generate", create=create_res)

        wait_res = _wait_for_completion(
            client,
            str(created_id),
            max_wait_seconds=int(max_wait_seconds),
            poll_interval_seconds=int(poll_interval_seconds),
        )
        if not wait_res.get("success"):
            wait_res["action"] = "generate"
            wait_res["video_id"] = str(created_id)
            return wait_res

        status = wait_res.get("status")
        if status != "completed":
            return _err(
                f"Video job finished with status '{status}'",
                error_type="JobNotCompleted",
                action="generate",
                video_id=str(created_id),
                video=wait_res.get("video"),
            )

        dl_res = _download_to_file(
            client,
            str(created_id),
            variant=str(variant) if variant else None,
            output_dir=str(output_dir),
            output_filename=str(output_filename) if output_filename else None,
        )
        if not dl_res.get("success"):
            dl_res["action"] = "generate"
            dl_res["video_id"] = str(created_id)
            dl_res["video"] = wait_res.get("video")
            return dl_res

        return _ok(
            action="generate",
            video_id=str(created_id),
            status="completed",
            video=wait_res.get("video"),
            file_path=dl_res.get("file_path"),
            variant=dl_res.get("variant"),
            output_dir=str(output_dir),
        )

    except Exception as e:
        return _err(str(e), error_type=type(e).__name__, action=action)


