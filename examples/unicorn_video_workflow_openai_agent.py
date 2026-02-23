#!/usr/bin/env python3
"""
Unicorn Video Workflow Agent (OpenAI Videos API + FFmpeg)

Takes a base image (reference), generates a short 3-beat animation sequence, and stitches
the clips together into a single MP4 using the `ffmpeg` tool.

Sequence (OpenAI Videos API):
  1) generate (with input_reference image): beat 1
  2) remix previous: beat 2
  3) remix previous: beat 3 (auto-retry with safer prompt if moderation blocks)

Usage:
    python examples/unicorn_video_workflow_openai_agent.py

Optional:
    python examples/unicorn_video_workflow_openai_agent.py --image ./examples/output/unicorn.png --outdir ./examples/output

Environment:
    OPENAI_API_KEY: Required - OpenAI API key

Notes:
  - This script loads `.env` via python-dotenv if present.
  - Ensure `ffmpeg` is installed locally (macOS: `brew install ffmpeg`).
  - OpenAI Videos API requires the reference image to match the requested `--size` exactly.
    This script will auto-resize into the output directory when needed (requires Pillow via strands-pack[image]).
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Load .env if present
load_dotenv()

# Add src to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from strands_pack import ffmpeg, image, openai_video  # noqa: E402


def _now_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _parse_size(size: str) -> tuple[int, int]:
    s = (size or "").strip().lower()
    if "x" not in s:
        raise ValueError("size must be formatted like WIDTHxHEIGHT (e.g. 1280x720)")
    w_s, h_s = s.split("x", 1)
    return int(w_s), int(h_s)


def _maybe_resize_reference_image(*, input_path: Path, output_dir: Path, target_size: str, tag: str) -> Path:
    """
    OpenAI Videos API requires reference image dimensions to exactly match `size`.
    We'll force-resize (no aspect preservation) into the output dir when needed.
    """
    info = image(action="get_info", input_path=str(input_path))
    if not info.get("success"):
        raise RuntimeError(
            "This workflow auto-resizes reference images to match OpenAI `size`, but Pillow isn't available. "
            "Install with: pip install strands-pack[image]\n"
            f"Details: {info}"
        )

    w, h = info.get("width"), info.get("height")
    tw, th = _parse_size(target_size)
    if isinstance(w, int) and isinstance(h, int) and w == tw and h == th:
        return input_path

    out_path = output_dir / f"unicorn_openai_ref_{tag}.png"
    res = image(
        action="resize",
        input_path=str(input_path),
        output_path=str(out_path),
        width=tw,
        height=th,
        maintain_aspect=False,
    )
    if not res.get("success"):
        raise RuntimeError(f"Failed to resize reference image for OpenAI (must match {target_size}): {res}")
    return out_path


def run_workflow(*, image_path: str, output_dir: str, size: str = "1280x720") -> str:
    outdir = Path(output_dir).expanduser().resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    img = Path(image_path).expanduser().resolve()
    if not img.exists():
        raise FileNotFoundError(f"Image not found: {img}")

    allowed_sizes = {"720x1280", "1280x720", "1024x1792", "1792x1024"}
    if size not in allowed_sizes:
        raise ValueError(f"--size must be one of {sorted(allowed_sizes)} (got: {size})")

    tag = _now_tag()

    # Keep prompts explicit for continuity across clips.
    prompt_1 = (
        "Use the provided image as the first frame. Keep the same illustration style, colors, and character design. "
        "The unicorn comes alive in a warm, dreamy gym. The unicorn performs a graceful gymnastics leap over the "
        "balance beam in the foreground, with sparkles trailing. Smooth motion, stable camera, no cuts."
    )
    prompt_2 = (
        "Continue seamlessly from the previous video. Same scene, same unicorn, same lighting and art style. "
        "The unicorn lands, trots forward, and jumps over a second balance beam. More sparkles, slight camera follow, "
        "no cuts, smooth and coherent motion."
    )
    prompt_3 = (
        "Continue seamlessly. The unicorn finishes the second jump and magical glitter-rain starts falling from the sky. "
        "The unicorn turns toward camera and clearly says (spoken in audio): 'Myka you are awesome!' "
        "Happy, warm tone. No text overlays or subtitles."
    )

    ref_img = _maybe_resize_reference_image(input_path=img, output_dir=outdir, target_size=size, tag=tag)

    segments: list[str] = []

    # Beat 1: generate (with image reference)
    r1 = openai_video(
        action="generate",
        prompt=prompt_1,
        input_reference_path=str(ref_img),
        model="sora-2",
        seconds=8,
        size=size,
        output_dir=str(outdir),
        output_filename=f"unicorn_openai_1_{tag}",
        max_wait_seconds=900,
        poll_interval_seconds=5,
    )
    if not r1.get("success"):
        raise RuntimeError(f"Step 1 failed: {r1}")
    segments.append(r1["file_path"])
    prev_id = r1.get("video_id")
    if not prev_id:
        raise RuntimeError(f"Step 1 did not return video_id: {r1}")

    # Beat 2: remix + wait + download
    r2 = openai_video(action="remix", video_id=prev_id, prompt=prompt_2)
    if not r2.get("success"):
        raise RuntimeError(f"Step 2 (remix) failed: {r2}")
    v2 = r2.get("video_id")
    if not v2:
        raise RuntimeError(f"Step 2 did not return video_id: {r2}")
    w2 = openai_video(action="wait", video_id=v2, max_wait_seconds=900, poll_interval_seconds=5)
    if not w2.get("success"):
        raise RuntimeError(f"Step 2 (wait) failed: {w2}")
    d2 = openai_video(action="download", video_id=v2, output_dir=str(outdir), output_filename=f"unicorn_openai_2_{tag}")
    if not d2.get("success"):
        raise RuntimeError(f"Step 2 (download) failed: {d2}")
    segments.append(d2["file_path"])
    prev_id = v2

    # Beat 3: remix + wait + download (retry on moderation_blocked)
    r3 = openai_video(action="remix", video_id=prev_id, prompt=prompt_3)
    if not r3.get("success"):
        raise RuntimeError(f"Step 3 (remix) failed: {r3}")
    v3 = r3.get("video_id")
    if not v3:
        raise RuntimeError(f"Step 3 did not return video_id: {r3}")
    w3 = openai_video(action="wait", video_id=v3, max_wait_seconds=900, poll_interval_seconds=5)
    if not w3.get("success"):
        err = (w3.get("error") or {})
        code = err.get("code") if isinstance(err, dict) else None
        if code == "moderation_blocked":
            prompt_3_safe = (
                "Continue seamlessly. The unicorn finishes the second jump and magical glitter-rain starts falling. "
                "The unicorn turns toward the camera, smiles, and gives a friendly, upbeat compliment. "
                "Warm, whimsical tone. Smooth motion. No text overlays."
            )
            r3b = openai_video(action="remix", video_id=prev_id, prompt=prompt_3_safe)
            if not r3b.get("success"):
                raise RuntimeError(f"Step 3 retry (remix) failed: {r3b}")
            v3b = r3b.get("video_id")
            if not v3b:
                raise RuntimeError(f"Step 3 retry did not return video_id: {r3b}")
            w3b = openai_video(action="wait", video_id=v3b, max_wait_seconds=900, poll_interval_seconds=5)
            if not w3b.get("success"):
                raise RuntimeError(f"Step 3 retry (wait) failed: {w3b}")
            v3 = v3b
        else:
            raise RuntimeError(f"Step 3 (wait) failed: {w3}")

    d3 = openai_video(action="download", video_id=v3, output_dir=str(outdir), output_filename=f"unicorn_openai_3_{tag}")
    if not d3.get("success"):
        raise RuntimeError(f"Step 3 (download) failed: {d3}")
    segments.append(d3["file_path"])

    final_path = outdir / f"unicorn_workflow_openai_{tag}.mp4"
    stitch_msg = ffmpeg(action="concat", input_paths=segments, output_path=str(final_path), reencode=True)
    if isinstance(stitch_msg, str) and stitch_msg.lower().startswith("error"):
        raise RuntimeError(f"Stitch failed: {stitch_msg}")
    return str(final_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a 3-beat unicorn video with OpenAI and stitch clips with ffmpeg.")
    parser.add_argument(
        "--image",
        default=str(Path(__file__).parent / "output" / "unicorn.png"),
        help="Path to the base image (reference). Default: ./examples/output/unicorn.png",
    )
    parser.add_argument(
        "--outdir",
        default=str(Path(__file__).parent / "output"),
        help="Output directory for clips and final video. Default: ./examples/output",
    )
    parser.add_argument(
        "--size",
        default="1280x720",
        choices=["720x1280", "1280x720", "1024x1792", "1792x1024"],
        help="OpenAI output size. Reference image will be resized to match. Default: 1280x720",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Unicorn Video Workflow (OpenAI Videos API + FFmpeg)")
    print("=" * 60)
    print(f"Image:  {args.image}")
    print(f"Outdir: {args.outdir}")
    print(f"Size:   {args.size}")

    final_video = run_workflow(image_path=args.image, output_dir=args.outdir, size=args.size)
    print("\nDone.")
    print(f"Final video: {final_video}")


if __name__ == "__main__":
    main()


