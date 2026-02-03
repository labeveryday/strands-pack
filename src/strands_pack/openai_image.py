"""
OpenAI Image Tool

Generate and edit images using OpenAI's GPT image models.

Usage Examples:
    from strands import Agent
    from strands_pack import openai_image

    agent = Agent(tools=[openai_image])

    # Generate an image
    agent.tool.openai_image(
        action="generate",
        prompt="A sunset over mountains",
        style="photorealistic"
    )

    # Edit an existing image
    agent.tool.openai_image(
        action="edit",
        prompt="Add a rainbow to the sky",
        image_path="photo.png"
    )

    # Analyze image effectiveness
    agent.tool.openai_image(
        action="analyze",
        image_path="thumbnail.png",
        platform="youtube"
    )

Available Actions:
    - generate: Generate images from text prompts
        Parameters:
            prompt (str): Text description of the image
            model (str): "gpt-image-1" (default) or "dall-e-3"
            size (str): "1024x1024", "1792x1024", "1024x1792", or "auto"
            quality (str): "auto", "low", "medium", "high"
            style (str): Style hint (photorealistic, illustration, etc.)
            num_images (int): Number of images to generate (1-4)

    - edit: Edit an existing image with a prompt
        Parameters:
            prompt (str): Description of the edits to make
            image_path (str): Path to the image to edit (required)
            model (str): "gpt-image-1" (default) or "dall-e-3"
            size (str): Output size
            quality (str): Output quality

    - analyze: Analyze image effectiveness using GPT-4o vision
        Parameters:
            image_path (str): Path to the image to analyze (required)
            platform (str): Target platform (youtube, instagram, twitter, blog)

    - optimize: Optimize image for a specific platform
        Parameters:
            image_path (str): Path to the image (required)
            platform (str): Target platform (required)
            enhance_contrast (bool): Apply contrast enhancement

    - variations: Generate variations of an existing image
        Parameters:
            image_path (str): Path to the source image (required)
            num_images (int): Number of variations (1-4)

Environment Variables:
    OPENAI_API_KEY: OpenAI API key (required)

Requires: pip install strands-pack[openai]
"""

import base64
import os
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from strands import tool

# Type aliases
ImageModel = Literal["gpt-image-1", "dall-e-3"]
ImageSize = Literal["1024x1024", "1792x1024", "1024x1792", "auto"]
ImageQuality = Literal["auto", "low", "medium", "high"]
Platform = Literal["youtube", "instagram", "twitter", "facebook", "blog"]

# Platform size presets
PLATFORM_SIZES = {
    "youtube": "1792x1024",
    "instagram": "1024x1024",
    "twitter": "1792x1024",
    "facebook": "1200x630",
    "blog": "1792x1024",
}


# -----------------------------------------------------------------------------
# Internal Helper Functions
# -----------------------------------------------------------------------------


def _get_client(api_key: str):
    """Get an OpenAI client instance."""
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("openai not installed. Run: pip install strands-pack[openai]") from None
    return OpenAI(api_key=api_key)


def _ok(**data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": True}
    out.update(data)
    return out


def _err(message: str, **data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": False, "error": message}
    out.update(data)
    return out


def _load_image_bytes(image_path: str) -> bytes:
    """Load image file as bytes."""
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")
    with open(path, "rb") as f:
        return f.read()


def _load_image_base64(image_path: str) -> str:
    """Load image file as base64 string."""
    image_bytes = _load_image_bytes(image_path)
    return base64.b64encode(image_bytes).decode("utf-8")


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


def _save_image(
    image_data: bytes,
    output_dir: str,
    filename: Optional[str],
    output_format: str,
    index: int = 0,
) -> Path:
    """Save image bytes to file."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    ext = output_format.lower()
    if ext == "jpeg":
        ext = "jpg"

    if filename:
        if index > 0:
            file_path = output_path / f"{filename}_{index + 1}.{ext}"
        else:
            file_path = output_path / f"{filename}.{ext}"
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if index > 0:
            file_path = output_path / f"openai_image_{timestamp}_{index + 1}.{ext}"
        else:
            file_path = output_path / f"openai_image_{timestamp}.{ext}"

    # Convert format if needed
    if output_format.lower() in ("jpeg", "jpg", "webp") and output_format.lower() != "png":
        try:
            from PIL import Image
            img = Image.open(BytesIO(image_data))
            if img.mode == "RGBA" and output_format.lower() in ("jpeg", "jpg"):
                img = img.convert("RGB")
            buffer = BytesIO()
            save_format = "JPEG" if output_format.lower() in ("jpeg", "jpg") else output_format.upper()
            img.save(buffer, format=save_format, quality=95)
            image_data = buffer.getvalue()
        except ImportError:
            pass  # Save as-is if Pillow not available

    with open(file_path, "wb") as f:
        f.write(image_data)

    return file_path


def _enhance_prompt(prompt: str, style: Optional[str] = None) -> str:
    """Enhance prompt with style hints."""
    if not style:
        return prompt

    style_hints = {
        "photorealistic": "photorealistic, highly detailed, professional photography",
        "illustration": "digital illustration, artistic, stylized",
        "cartoon": "cartoon style, vibrant colors, playful",
        "minimalist": "minimalist design, clean, simple, modern",
        "dramatic": "dramatic lighting, high contrast, cinematic",
        "professional": "professional, polished, corporate quality",
        "vintage": "vintage style, retro aesthetic, nostalgic",
        "watercolor": "watercolor painting style, soft edges, artistic",
        "3d": "3D rendered, volumetric lighting, detailed textures",
    }

    hint = style_hints.get(style.lower(), style)
    return f"{prompt}, {hint}"


def _resize_if_needed(image_bytes: bytes, max_size_mb: float = 4.0) -> bytes:
    """Resize image if it exceeds max size."""
    if len(image_bytes) <= max_size_mb * 1024 * 1024:
        return image_bytes

    try:
        from PIL import Image
        img = Image.open(BytesIO(image_bytes))

        # Reduce dimensions by 50% iteratively until under size limit
        while len(image_bytes) > max_size_mb * 1024 * 1024:
            new_size = (img.width // 2, img.height // 2)
            if new_size[0] < 64 or new_size[1] < 64:
                break
            img = img.resize(new_size, Image.LANCZOS)
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            image_bytes = buffer.getvalue()

        return image_bytes
    except ImportError:
        return image_bytes  # Return original if Pillow not available


# -----------------------------------------------------------------------------
# Action Implementations
# -----------------------------------------------------------------------------


def _generate_image(
    prompt: str,
    model: str = "gpt-image-1",
    size: str = "auto",
    quality: str = "auto",
    style: Optional[str] = None,
    num_images: int = 1,
    output_dir: str = "output",
    output_filename: Optional[str] = None,
    output_format: str = "png",
) -> Dict[str, Any]:
    """Generate images using OpenAI's image models."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _err("OPENAI_API_KEY environment variable not set")

    if num_images < 1 or num_images > 4:
        return _err("num_images must be between 1 and 4")

    # Resolve auto size
    actual_size = "1024x1024" if size == "auto" else size

    # Enhance prompt with style
    enhanced_prompt = _enhance_prompt(prompt, style)

    try:
        client = _get_client(api_key)

        # Build generation params
        gen_params = {
            "model": model,
            "prompt": enhanced_prompt,
            "n": num_images,
            "size": actual_size,
        }

        if quality != "auto":
            gen_params["quality"] = quality

        response = client.images.generate(**gen_params)

        # Extract image data
        file_paths = []
        for i, image_data in enumerate(response.data):
            if hasattr(image_data, "b64_json") and image_data.b64_json:
                img_bytes = base64.b64decode(image_data.b64_json)
            elif hasattr(image_data, "url") and image_data.url:
                # Download from URL
                import urllib.request
                with urllib.request.urlopen(image_data.url) as resp:
                    img_bytes = resp.read()
            else:
                continue

            file_path = _save_image(img_bytes, output_dir, output_filename, output_format, i)
            file_paths.append(file_path)

        if not file_paths:
            return _err("No images returned from API")

        return _ok(
            action="generate",
            file_path=str(file_paths[0]),
            file_paths=[str(p) for p in file_paths],
            message=f"Generated {len(file_paths)} image(s)",
            model=model,
            size=actual_size,
            prompt=enhanced_prompt,
            num_images_generated=len(file_paths),
        )

    except Exception as e:
        # Try fallback to dall-e-3 if gpt-image-1 fails
        if model == "gpt-image-1":
            try:
                return _generate_image(
                    prompt=prompt,
                    model="dall-e-3",
                    size=size,
                    quality=quality,
                    style=style,
                    num_images=min(num_images, 1),  # DALL-E 3 only supports n=1
                    output_dir=output_dir,
                    output_filename=output_filename,
                    output_format=output_format,
                )
            except Exception:
                pass
        return _err(str(e))


def _edit_image(
    prompt: str,
    image_path: str,
    model: str = "gpt-image-1",
    size: str = "auto",
    quality: str = "auto",
    output_dir: str = "output",
    output_filename: Optional[str] = None,
    output_format: str = "png",
) -> Dict[str, Any]:
    """Edit an existing image using OpenAI's image edit API."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _err("OPENAI_API_KEY environment variable not set")

    try:
        image_bytes = _load_image_bytes(image_path)
    except FileNotFoundError as e:
        return _err(str(e))

    # Resize if needed
    image_bytes = _resize_if_needed(image_bytes)

    # Resolve auto size
    actual_size = "1024x1024" if size == "auto" else size

    try:
        client = _get_client(api_key)

        # Use images.edit endpoint
        edit_params = {
            "model": model,
            "image": BytesIO(image_bytes),
            "prompt": prompt,
            "size": actual_size,
        }

        response = client.images.edit(**edit_params)

        # Extract image data
        if response.data and len(response.data) > 0:
            image_data = response.data[0]
            if hasattr(image_data, "b64_json") and image_data.b64_json:
                img_bytes = base64.b64decode(image_data.b64_json)
            elif hasattr(image_data, "url") and image_data.url:
                import urllib.request
                with urllib.request.urlopen(image_data.url) as resp:
                    img_bytes = resp.read()
            else:
                return _err("No image data in response")

            file_path = _save_image(img_bytes, output_dir, output_filename, output_format)

            return _ok(
                action="edit",
                file_path=str(file_path),
                message=f"Edited image saved to {file_path}",
                model=model,
                size=actual_size,
                source_image=image_path,
            )
        else:
            return _err("No image returned from API")

    except Exception as e:
        return _err(str(e))


def _analyze_image(
    image_path: str,
    platform: str = "youtube",
) -> Dict[str, Any]:
    """Analyze image effectiveness using GPT-4o vision."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _err("OPENAI_API_KEY environment variable not set")

    try:
        image_base64 = _load_image_base64(image_path)
    except FileNotFoundError as e:
        return _err(str(e))

    mime_type = _get_mime_type(Path(image_path))

    # Platform-specific analysis prompts
    platform_prompts = {
        "youtube": "Analyze this YouTube thumbnail for effectiveness. Consider: visual impact in 0.3 seconds, face visibility, text readability, color contrast, clickthrough potential, emotional appeal.",
        "instagram": "Analyze this Instagram image for effectiveness. Consider: square format optimization, mobile-first design, feed aesthetics, engagement potential, brand consistency.",
        "twitter": "Analyze this Twitter/X image for effectiveness. Consider: timeline visibility, text clarity, visual impact, shareability, brand recognition.",
        "facebook": "Analyze this Facebook image for effectiveness. Consider: news feed visibility, engagement potential, mobile display, text-to-image ratio.",
        "blog": "Analyze this blog image for effectiveness. Consider: professional appearance, topic relevance, web optimization, SEO potential, reader engagement.",
    }

    analysis_prompt = platform_prompts.get(platform, platform_prompts["youtube"])

    try:
        client = _get_client(api_key)

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert image analyst specializing in digital marketing and content optimization. Provide a numerical effectiveness score (0-10) and detailed analysis with actionable suggestions.",
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": analysis_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_base64}"
                            },
                        },
                    ],
                },
            ],
            max_tokens=1000,
        )

        analysis_text = response.choices[0].message.content

        # Try to extract score from response
        score = None
        import re
        score_match = re.search(r"(\d+(?:\.\d+)?)\s*/\s*10|score[:\s]+(\d+(?:\.\d+)?)", analysis_text.lower())
        if score_match:
            score = float(score_match.group(1) or score_match.group(2))

        return _ok(
            action="analyze",
            image_path=image_path,
            platform=platform,
            analysis=analysis_text,
            effectiveness_score=score,
            message="Analysis complete",
        )

    except Exception as e:
        return _err(str(e))


def _optimize_image(
    image_path: str,
    platform: str,
    enhance_contrast: bool = True,
    output_dir: str = "output",
    output_filename: Optional[str] = None,
    output_format: str = "png",
) -> Dict[str, Any]:
    """Optimize image for a specific platform."""
    try:
        from PIL import Image, ImageEnhance
    except ImportError:
        return _err("Pillow not installed. Run: pip install Pillow")

    try:
        img = Image.open(image_path)
    except FileNotFoundError:
        return _err(f"Image file not found: {image_path}")
    except Exception as e:
        return _err(f"Failed to open image: {e}")

    # Get target size for platform
    target_size = PLATFORM_SIZES.get(platform)
    if not target_size:
        return _err(f"Unknown platform: {platform}. Valid: {list(PLATFORM_SIZES.keys())}")

    target_width, target_height = map(int, target_size.split("x"))

    # Resize to target dimensions
    img = img.resize((target_width, target_height), Image.LANCZOS)

    # Enhance contrast if requested
    if enhance_contrast:
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.2)

    # Convert mode if needed for JPEG
    if output_format.lower() in ("jpeg", "jpg") and img.mode == "RGBA":
        img = img.convert("RGB")

    # Save
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    ext = "jpg" if output_format.lower() == "jpeg" else output_format.lower()
    if output_filename:
        file_path = output_path / f"{output_filename}.{ext}"
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = output_path / f"optimized_{platform}_{timestamp}.{ext}"

    save_format = "JPEG" if ext == "jpg" else ext.upper()
    img.save(file_path, format=save_format, quality=95)

    return _ok(
        action="optimize",
        file_path=str(file_path),
        platform=platform,
        size=target_size,
        contrast_enhanced=enhance_contrast,
        message=f"Optimized for {platform}: {file_path}",
    )


def _generate_variations(
    image_path: str,
    num_images: int = 2,
    size: str = "auto",
    output_dir: str = "output",
    output_filename: Optional[str] = None,
    output_format: str = "png",
) -> Dict[str, Any]:
    """Generate variations of an existing image."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _err("OPENAI_API_KEY environment variable not set")

    if num_images < 1 or num_images > 4:
        return _err("num_images must be between 1 and 4")

    try:
        image_bytes = _load_image_bytes(image_path)
    except FileNotFoundError as e:
        return _err(str(e))

    # Resize if needed
    image_bytes = _resize_if_needed(image_bytes)

    # Resolve auto size
    actual_size = "1024x1024" if size == "auto" else size

    try:
        client = _get_client(api_key)

        response = client.images.create_variation(
            image=BytesIO(image_bytes),
            n=num_images,
            size=actual_size,
        )

        # Extract image data
        file_paths = []
        for i, image_data in enumerate(response.data):
            if hasattr(image_data, "b64_json") and image_data.b64_json:
                img_bytes = base64.b64decode(image_data.b64_json)
            elif hasattr(image_data, "url") and image_data.url:
                import urllib.request
                with urllib.request.urlopen(image_data.url) as resp:
                    img_bytes = resp.read()
            else:
                continue

            file_path = _save_image(img_bytes, output_dir, output_filename, output_format, i)
            file_paths.append(file_path)

        if not file_paths:
            return _err("No variations returned from API")

        return _ok(
            action="variations",
            file_path=str(file_paths[0]),
            file_paths=[str(p) for p in file_paths],
            message=f"Generated {len(file_paths)} variation(s)",
            source_image=image_path,
            num_variations_generated=len(file_paths),
        )

    except Exception as e:
        return _err(str(e))


# -----------------------------------------------------------------------------
# Main Tool Function
# -----------------------------------------------------------------------------


@tool
def openai_image(
    action: str,
    prompt: Optional[str] = None,
    image_path: Optional[str] = None,
    model: str = "gpt-image-1",
    size: str = "auto",
    quality: str = "auto",
    style: Optional[str] = None,
    platform: str = "youtube",
    num_images: int = 1,
    enhance_contrast: bool = True,
    output_dir: str = "output",
    output_filename: Optional[str] = None,
    output_format: str = "png",
) -> Dict[str, Any]:
    """
    Generate and edit images using OpenAI's GPT image models.

    Args:
        action: The action to perform. One of:
                - "generate": Generate images from text prompt
                - "edit": Edit existing image with prompt
                - "analyze": Analyze image effectiveness
                - "optimize": Optimize image for platform
                - "variations": Generate variations of image
        prompt: Text description for generation or editing.
        image_path: Path to input image (required for edit, analyze, optimize, variations).
        model: Image model to use: "gpt-image-1" (default) or "dall-e-3".
        size: Output size: "1024x1024", "1792x1024", "1024x1792", or "auto".
        quality: Image quality: "auto", "low", "medium", "high".
        style: Style hint for generation (photorealistic, illustration, cartoon,
               minimalist, dramatic, professional, vintage, watercolor, 3d).
        platform: Target platform for analyze/optimize (youtube, instagram,
                  twitter, facebook, blog).
        num_images: Number of images to generate (1-4).
        enhance_contrast: Apply contrast enhancement for optimize action.
        output_dir: Directory to save output images (default: "output").
        output_filename: Custom filename (without extension).
        output_format: Output format: "png", "jpeg", "webp".

    Returns:
        dict with keys:
            - success: bool indicating if operation succeeded
            - action: the action performed
            - file_path: path to saved image (if applicable)
            - file_paths: list of paths (if multiple images)
            - message: status message
            - error: error message (if failed)

    Examples:
        >>> openai_image(action="generate", prompt="A sunset over mountains")
        >>> openai_image(action="generate", prompt="A cat", style="watercolor", num_images=2)
        >>> openai_image(action="edit", prompt="Add a hat", image_path="photo.png")
        >>> openai_image(action="analyze", image_path="thumbnail.png", platform="youtube")
        >>> openai_image(action="optimize", image_path="image.png", platform="instagram")
        >>> openai_image(action="variations", image_path="logo.png", num_images=3)
    """
    valid_actions = ["generate", "edit", "analyze", "optimize", "variations"]

    if action not in valid_actions:
        return _err(f"Unknown action '{action}'", available_actions=valid_actions)

    # Validate required params per action
    if action == "generate" and not prompt:
        return _err("'prompt' is required for action 'generate'")
    if action == "edit" and not image_path:
        return _err("'image_path' is required for action 'edit'")
    if action == "edit" and not prompt:
        return _err("'prompt' is required for action 'edit'")
    if action == "analyze" and not image_path:
        return _err("'image_path' is required for action 'analyze'")
    if action == "optimize" and not image_path:
        return _err("'image_path' is required for action 'optimize'")
    if action == "variations" and not image_path:
        return _err("'image_path' is required for action 'variations'")
    if action == "generate":
        return _generate_image(
            prompt=prompt,
            model=model,
            size=size,
            quality=quality,
            style=style,
            num_images=num_images,
            output_dir=output_dir,
            output_filename=output_filename,
            output_format=output_format,
        )
    elif action == "edit":
        return _edit_image(
            prompt=prompt,
            image_path=image_path,
            model=model,
            size=size,
            quality=quality,
            output_dir=output_dir,
            output_filename=output_filename,
            output_format=output_format,
        )
    elif action == "analyze":
        return _analyze_image(
            image_path=image_path,
            platform=platform,
        )
    elif action == "optimize":
        return _optimize_image(
            image_path=image_path,
            platform=platform,
            enhance_contrast=enhance_contrast,
            output_dir=output_dir,
            output_filename=output_filename,
            output_format=output_format,
        )
    elif action == "variations":
        return _generate_variations(
            image_path=image_path,
            num_images=num_images,
            size=size,
            output_dir=output_dir,
            output_filename=output_filename,
            output_format=output_format,
        )

    return _err(f"Unhandled action: {action}")
