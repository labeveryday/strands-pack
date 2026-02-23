#!/usr/bin/env python3
"""
Unicorn Video Workflow Agent (Gemini Veo + FFmpeg)

Takes a base image (first frame), generates a short 3-beat animation sequence, and stitches
the clips together into a single MP4 using the `ffmpeg` tool.

Sequence:
  1) image_to_video: unicorn comes alive and jumps over first balance beam
  2) extend: unicorn jumps over a second beam
  3) extend: magical glitter-rain + unicorn says "Myka you are awesome!"

Usage:
    python examples/unicorn_video_workflow_agent.py

Optional:
    python examples/unicorn_video_workflow_agent.py --image ./examples/output/unicorn.png --outdir ./examples/output

Environment:
    GOOGLE_API_KEY: Required - Google AI API key (Veo)

Notes:
  - This script loads `.env` via python-dotenv if present.
  - Ensure `ffmpeg` is installed locally (macOS: `brew install ffmpeg`).
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

from strands_pack import ffmpeg, gemini_video  # noqa: E402


def _now_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def run_workflow(*, image_path: str, output_dir: str) -> str:
    outdir = Path(output_dir).expanduser().resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    img = Path(image_path).expanduser().resolve()
    if not img.exists():
        raise FileNotFoundError(f"Image not found: {img}")

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


    # 1) Image-to-video
    r1 = gemini_video(
        action="image_to_video",
        prompt=prompt_1,
        image_path=str(img),
        model="veo-3.1-generate-preview",
        duration_seconds=8,
        aspect_ratio="16:9",
        # Use 720p so that the output can be extended (per Veo docs: extension is 720p-only).
        resolution="720p",
        enhance_prompt=True,
        output_dir=str(outdir),
        max_wait_seconds=900,
    )
    if not r1.get("success"):
        raise RuntimeError(f"Step 1 failed: {r1}")
    clip1 = r1["file_path"]
    segments = [clip1]
    current_video = clip1
    current_ref = r1.get("video_ref")

    # 2) Extend
    r2 = gemini_video(
        action="extend",
        prompt=prompt_2,
        video_path=current_video,
        video_ref=current_ref,
        model="veo-3.1-generate-preview",
        number_of_videos=1,
        enhance_prompt=True,
        output_dir=str(outdir),
        max_wait_seconds=900,
    )
    if not r2.get("success"):
        raise RuntimeError(f"Step 2 failed: {r2}")

    current_video = r2["file_path"]
    current_ref = r2.get("video_ref") or current_ref
    if r2.get("extend_mode") == "fallback_image_to_video":
        # Fallback produces a standalone clip; append it.
        segments.append(current_video)
    else:
        # True extend outputs a combined video; replace the last segment.
        segments[-1] = current_video

    # 3) Extend again (rain + spoken line)
    r3 = gemini_video(
        action="extend",
        prompt=prompt_3,
        video_path=current_video,
        video_ref=current_ref,
        model="veo-3.1-generate-preview",
        number_of_videos=1,
        enhance_prompt=True,
        output_dir=str(outdir),
        max_wait_seconds=900,
    )
    if not r3.get("success"):
        raise RuntimeError(f"Step 3 failed: {r3}")

    current_video = r3["file_path"]
    current_ref = r3.get("video_ref") or current_ref
    if r3.get("extend_mode") == "fallback_image_to_video":
        segments.append(current_video)
    else:
        segments[-1] = current_video

    # If we ended up with a single combined video (true-extend path), return it directly.
    if len(segments) == 1:
        return str(segments[0])

    # Otherwise stitch the independent clips.
    final_path = outdir / f"unicorn_workflow_{tag}.mp4"
    stitch_msg = ffmpeg(action="concat", input_paths=segments, output_path=str(final_path), reencode=True)
    if isinstance(stitch_msg, str) and stitch_msg.lower().startswith("error"):
        raise RuntimeError(f"Stitch failed: {stitch_msg}")
    return str(final_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a 3-beat unicorn video and stitch clips with ffmpeg.")
    parser.add_argument(
        "--image",
        default=str(Path(__file__).parent / "output" / "unicorn.png"),
        help="Path to the base image (first frame). Default: ./examples/output/unicorn.png",
    )
    parser.add_argument(
        "--outdir",
        default=str(Path(__file__).parent / "output"),
        help="Output directory for clips and final video. Default: ./examples/output",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Unicorn Video Workflow (Gemini Veo + FFmpeg)")
    print("=" * 60)
    print(f"Image:  {args.image}")
    print(f"Outdir: {args.outdir}")

    final_video = run_workflow(image_path=args.image, output_dir=args.outdir)
    print("\nDone.")
    print(f"Final video: {final_video}")


if __name__ == "__main__":
    main()


