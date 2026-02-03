"""
Image Tool

Local image manipulation using Pillow.

Actions
-------
- resize: Resize image (width, height, maintain_aspect)
- crop: Crop image (box=[left, upper, right, lower])
- rotate: Rotate image (angle, expand, fill_color)
- convert: Convert format (format, mode)
- compress: Compress image (quality, optimize)
- get_info: Get image information
- add_text: Add text overlay (text, position, font_size, color)
- thumbnail: Create thumbnail (size=[width, height])
- flip: Flip image (direction: horizontal/vertical)
- blur: Apply gaussian blur (radius)
- grayscale: Convert to grayscale
- brightness: Adjust brightness (factor)
- contrast: Adjust contrast (factor)
- sharpen: Sharpen image (unsharp mask)

Requirements:
    pip install strands-pack[image]
"""

import os
from typing import Any, Dict, List, Optional

from strands import tool

try:
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False


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


def _check_pillow() -> Optional[Dict[str, Any]]:
    """Check if Pillow is installed."""
    if not HAS_PILLOW:
        return _err("Pillow not installed. Run: pip install strands-pack[image]", error_type="ImportError")
    return None


def _validate_input_path(input_path: Optional[str]) -> Optional[Dict[str, Any]]:
    """Validate input file exists."""
    if not input_path:
        return _err("input_path is required")
    if not os.path.exists(input_path):
        return _err(f"Input file not found: {input_path}", error_type="FileNotFoundError")
    return None


def _validate_output_path(output_path: Optional[str]) -> Optional[Dict[str, Any]]:
    """Validate output path."""
    if not output_path:
        return _err("output_path is required")
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        return _err(f"Output directory does not exist: {output_dir}", error_type="FileNotFoundError")
    return None


@tool
def image(
    action: str,
    input_path: Optional[str] = None,
    output_path: Optional[str] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    maintain_aspect: bool = True,
    box: Optional[List[int]] = None,
    angle: Optional[int] = None,
    expand: bool = True,
    fill_color: str = "white",
    output_format: Optional[str] = None,
    mode: Optional[str] = None,
    quality: int = 85,
    optimize: bool = True,
    text: Optional[str] = None,
    position: Optional[List[int]] = None,
    font_size: int = 24,
    color: str = "white",
    size: Optional[List[int]] = None,
    direction: str = "horizontal",
    radius: int = 2,
    factor: float = 1.0,
    # sharpen params (unsharp mask)
    sharpen_radius: float = 2.0,
    sharpen_percent: int = 150,
    sharpen_threshold: int = 3,
) -> Dict[str, Any]:
    """
    Manipulate images using Pillow.

    Args:
        action: The action to perform. One of:
            - "resize": Resize image.
            - "crop": Crop image.
            - "rotate": Rotate image.
            - "convert": Convert format.
            - "compress": Compress image.
            - "get_info": Get image information.
            - "add_text": Add text overlay.
            - "thumbnail": Create thumbnail.
            - "flip": Flip image.
            - "blur": Apply gaussian blur.
            - "grayscale": Convert to grayscale.
            - "brightness": Adjust brightness.
            - "contrast": Adjust contrast.
            - "sharpen": Sharpen image (unsharp mask).
        input_path: Path to input image (required for all actions).
        output_path: Path to output image (required for most actions).
        width: Target width for resize.
        height: Target height for resize.
        maintain_aspect: Maintain aspect ratio when resizing (default True).
        box: Crop box as [left, upper, right, lower] for crop action.
        angle: Rotation angle in degrees for rotate action.
        expand: Expand image to fit rotated content (default True).
        fill_color: Fill color for rotation padding (default "white").
        output_format: Output format for convert action (e.g., "JPEG", "PNG").
        mode: Color mode for convert action (e.g., "RGB", "L", "RGBA").
        quality: Compression quality 1-100 for compress action (default 85).
        optimize: Optimize compression (default True).
        text: Text to add for add_text action.
        position: Text position as [x, y] for add_text action (default [10, 10]).
        font_size: Font size for add_text action (default 24).
        color: Text color for add_text action (default "white").
        size: Thumbnail size as [width, height] for thumbnail action (default [128, 128]).
        direction: Flip direction "horizontal" or "vertical" (default "horizontal").
        radius: Blur radius for blur action (default 2).
        factor: Brightness factor for brightness action (default 1.0, >1 brighter, <1 darker).
        sharpen_radius: Unsharp mask radius for sharpen action (default 2.0).
        sharpen_percent: Unsharp mask percent for sharpen action (default 150).
        sharpen_threshold: Unsharp mask threshold for sharpen action (default 3).

    Returns:
        dict with success status and action-specific data

    Examples:
        >>> image(action="resize", input_path="photo.jpg", output_path="small.jpg", width=400)
        >>> image(action="get_info", input_path="photo.jpg")
        >>> image(action="blur", input_path="photo.jpg", output_path="blurred.jpg", radius=5)
    """
    if err := _check_pillow():
        return err

    action = (action or "").strip().lower()

    try:
        if action == "resize":
            if err := _validate_input_path(input_path):
                return err
            if err := _validate_output_path(output_path):
                return err
            if not width and not height:
                return _err("At least one of width or height is required")

            with Image.open(input_path) as img:
                original_size = img.size
                if maintain_aspect:
                    img.thumbnail((width or img.width, height or img.height), Image.Resampling.LANCZOS)
                    new_size = img.size
                else:
                    new_width = width or img.width
                    new_height = height or img.height
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    new_size = (new_width, new_height)
                img.save(output_path)

            return _ok(
                action="resize",
                input_path=input_path,
                output_path=output_path,
                original_size=list(original_size),
                new_size=list(new_size),
                maintain_aspect=maintain_aspect,
            )

        if action == "crop":
            if err := _validate_input_path(input_path):
                return err
            if err := _validate_output_path(output_path):
                return err
            if not box or len(box) != 4:
                return _err("box is required as [left, upper, right, lower]")

            with Image.open(input_path) as img:
                original_size = img.size
                cropped = img.crop(tuple(box))
                cropped.save(output_path)
                new_size = cropped.size

            return _ok(
                action="crop",
                input_path=input_path,
                output_path=output_path,
                original_size=list(original_size),
                crop_box=box,
                new_size=list(new_size),
            )

        if action == "rotate":
            if err := _validate_input_path(input_path):
                return err
            if err := _validate_output_path(output_path):
                return err
            if angle is None:
                return _err("angle is required")

            with Image.open(input_path) as img:
                original_size = img.size
                rotated = img.rotate(angle, expand=expand, fillcolor=fill_color)
                rotated.save(output_path)
                new_size = rotated.size

            return _ok(
                action="rotate",
                input_path=input_path,
                output_path=output_path,
                angle=angle,
                expand=expand,
                original_size=list(original_size),
                new_size=list(new_size),
            )

        if action == "convert":
            if err := _validate_input_path(input_path):
                return err
            if err := _validate_output_path(output_path):
                return err

            with Image.open(input_path) as img:
                original_format = img.format
                original_mode = img.mode

                if mode:
                    img = img.convert(mode)

                # Handle RGBA to RGB conversion for JPEG
                if output_path.lower().endswith((".jpg", ".jpeg")) and img.mode == "RGBA":
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3])
                    img = background

                save_kwargs = {}
                if output_format:
                    save_kwargs["format"] = output_format

                img.save(output_path, **save_kwargs)
                final_format = output_format or os.path.splitext(output_path)[1][1:].upper()

            return _ok(
                action="convert",
                input_path=input_path,
                output_path=output_path,
                original_format=original_format,
                new_format=final_format,
                original_mode=original_mode,
                new_mode=mode or original_mode,
            )

        if action == "compress":
            if err := _validate_input_path(input_path):
                return err
            if err := _validate_output_path(output_path):
                return err

            original_size_bytes = os.path.getsize(input_path)

            with Image.open(input_path) as img:
                # Handle RGBA for JPEG
                if output_path.lower().endswith((".jpg", ".jpeg")) and img.mode == "RGBA":
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3])
                    img = background
                img.save(output_path, quality=quality, optimize=optimize)

            new_size_bytes = os.path.getsize(output_path)
            compression_ratio = round((1 - new_size_bytes / original_size_bytes) * 100, 2) if original_size_bytes > 0 else 0

            return _ok(
                action="compress",
                input_path=input_path,
                output_path=output_path,
                quality=quality,
                optimize=optimize,
                original_size_bytes=original_size_bytes,
                new_size_bytes=new_size_bytes,
                compression_percent=compression_ratio,
            )

        if action == "get_info":
            if err := _validate_input_path(input_path):
                return err

            file_size = os.path.getsize(input_path)

            with Image.open(input_path) as img:
                info = {
                    "format": img.format,
                    "mode": img.mode,
                    "width": img.width,
                    "height": img.height,
                    "size": [img.width, img.height],
                    "file_size_bytes": file_size,
                }

                if img.info:
                    safe_info = {}
                    for k, v in img.info.items():
                        if isinstance(v, (str, int, float, bool, list, dict)):
                            safe_info[k] = v
                        elif isinstance(v, tuple):
                            safe_info[k] = list(v)
                    if safe_info:
                        info["metadata"] = safe_info

            return _ok(action="get_info", input_path=input_path, **info)

        if action == "add_text":
            if err := _validate_input_path(input_path):
                return err
            if err := _validate_output_path(output_path):
                return err
            if not text:
                return _err("text is required")

            pos = position or [10, 10]

            with Image.open(input_path) as img:
                if img.mode != "RGBA":
                    img = img.convert("RGBA")

                draw = ImageDraw.Draw(img)

                # Try to use a default font, fall back to default
                try:
                    font = ImageFont.truetype("arial.ttf", font_size)
                except (OSError, IOError):
                    try:
                        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
                    except (OSError, IOError):
                        font = ImageFont.load_default()

                draw.text(tuple(pos), text, fill=color, font=font)

                if output_path.lower().endswith((".jpg", ".jpeg")):
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3])
                    img = background

                img.save(output_path)

            return _ok(
                action="add_text",
                input_path=input_path,
                output_path=output_path,
                text=text,
                position=pos,
                font_size=font_size,
                color=color,
            )

        if action == "thumbnail":
            if err := _validate_input_path(input_path):
                return err
            if err := _validate_output_path(output_path):
                return err

            thumb_size = size or [128, 128]
            if len(thumb_size) != 2:
                return _err("size must be [width, height]")

            with Image.open(input_path) as img:
                original_size = img.size
                img.thumbnail(tuple(thumb_size), Image.Resampling.LANCZOS)
                img.save(output_path)
                new_size = img.size

            return _ok(
                action="thumbnail",
                input_path=input_path,
                output_path=output_path,
                requested_size=thumb_size,
                original_size=list(original_size),
                new_size=list(new_size),
            )

        if action == "flip":
            if err := _validate_input_path(input_path):
                return err
            if err := _validate_output_path(output_path):
                return err

            if direction not in ("horizontal", "vertical"):
                return _err("direction must be 'horizontal' or 'vertical'")

            with Image.open(input_path) as img:
                if direction == "horizontal":
                    flipped = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                else:
                    flipped = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
                flipped.save(output_path)

            return _ok(action="flip", input_path=input_path, output_path=output_path, direction=direction)

        if action == "blur":
            if err := _validate_input_path(input_path):
                return err
            if err := _validate_output_path(output_path):
                return err

            with Image.open(input_path) as img:
                blurred = img.filter(ImageFilter.GaussianBlur(radius=radius))
                blurred.save(output_path)

            return _ok(action="blur", input_path=input_path, output_path=output_path, radius=radius)

        if action == "grayscale":
            if err := _validate_input_path(input_path):
                return err
            if err := _validate_output_path(output_path):
                return err

            with Image.open(input_path) as img:
                gray = img.convert("L")
                gray.save(output_path)

            return _ok(action="grayscale", input_path=input_path, output_path=output_path)

        if action == "brightness":
            if err := _validate_input_path(input_path):
                return err
            if err := _validate_output_path(output_path):
                return err

            with Image.open(input_path) as img:
                enhancer = ImageEnhance.Brightness(img)
                brightened = enhancer.enhance(factor)
                brightened.save(output_path)

            return _ok(action="brightness", input_path=input_path, output_path=output_path, factor=factor)

        if action == "contrast":
            if err := _validate_input_path(input_path):
                return err
            if err := _validate_output_path(output_path):
                return err

            with Image.open(input_path) as img:
                enhancer = ImageEnhance.Contrast(img)
                out_img = enhancer.enhance(factor)
                out_img.save(output_path)

            return _ok(action="contrast", input_path=input_path, output_path=output_path, factor=factor)

        if action == "sharpen":
            if err := _validate_input_path(input_path):
                return err
            if err := _validate_output_path(output_path):
                return err

            # Clamp to sane values
            sr = max(0.0, float(sharpen_radius))
            sp = int(sharpen_percent)
            st = int(sharpen_threshold)
            sp = max(0, min(500, sp))
            st = max(0, min(255, st))

            with Image.open(input_path) as img:
                sharpened = img.filter(ImageFilter.UnsharpMask(radius=sr, percent=sp, threshold=st))
                sharpened.save(output_path)

            return _ok(
                action="sharpen",
                input_path=input_path,
                output_path=output_path,
                sharpen_radius=sr,
                sharpen_percent=sp,
                sharpen_threshold=st,
            )

        return _err(
            f"Unknown action: {action}",
            error_type="InvalidAction",
            available_actions=[
                "resize",
                "crop",
                "rotate",
                "convert",
                "compress",
                "get_info",
                "add_text",
                "thumbnail",
                "flip",
                "blur",
                "grayscale",
                "brightness",
                "contrast",
                "sharpen",
            ],
        )

    except Exception as e:
        return _err(str(e), error_type=type(e).__name__, action=action)
