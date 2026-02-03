"""
Gemini Image Tool

Generate and edit images using Google's Gemini image models (Nano Banana).

Usage Examples:
    from strands import Agent
    from strands_pack import gemini_image

    agent = Agent(tools=[gemini_image])

    # Generate an image
    agent.tool.gemini_image(
        action="generate",
        prompt="sunset over mountains",
        aspect_ratio="16:9"
    )

    # Edit an existing image
    agent.tool.gemini_image(
        action="edit",
        prompt="Add a wizard hat to the cat",
        image_path="cat.png"
    )

Available Actions:
    - generate: Generate images using Gemini models
        Parameters:
            prompt (str): Text description of the image to generate
            model (str): "gemini-2.5-flash-image" or "gemini-3-pro-image-preview" (default)
            aspect_ratio (str): "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"
            image_size (str): "1K", "2K", "4K" (Gemini 3 Pro only)
            use_google_search (bool): Enable Google Search grounding (Gemini 3 Pro only)
            reference_images (list): List of image paths for style/content reference
            output_dir (str): Output directory (default: "output")

    - edit: Edit an existing image
        Parameters:
            prompt (str): Text description of the edits to make
            image_path (str): Path to the image to edit (required)
            model (str): "gemini-2.5-flash-image" or "gemini-3-pro-image-preview" (default)
            aspect_ratio (str): Output aspect ratio
            image_size (str): "1K", "2K", "4K" (Gemini 3 Pro only)
            additional_images (list): Additional reference images
            output_dir (str): Output directory (default: "output")

    - chat: Multi-turn (conversational) image generation/editing
        Parameters:
            prompt (str): Message to send to the chat
            chat_id (str): Optional. If provided, continues an existing chat session.
            model (str): "gemini-2.5-flash-image" or "gemini-3-pro-image-preview" (default)
            aspect_ratio (str): Output aspect ratio
            image_size (str): "1K", "2K", "4K" (Gemini 3 Pro only)
            use_google_search (bool): Enable Google Search grounding (Gemini 3 Pro only)
            additional_images (list): Optional image paths to include with this message
            response_modalities (list[str]): e.g. ["IMAGE"] to suppress text
            output_dir/output_filename/output_format/num_images: Same as generate/edit

    - close_chat: Close a chat session
        Parameters:
            chat_id (str): Required

Environment Variables:
    GOOGLE_API_KEY: Google AI API key (required)

Requires: pip install strands-pack[gemini]
"""

import os
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

from strands import tool

# Type aliases
ImageModel = Literal["gemini-2.5-flash-image", "gemini-3-pro-image-preview"]
ImageAspectRatio = Literal["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"]
ImageSize = Literal["1K", "2K", "4K"]
ImageOutputFormat = Literal["png", "jpeg", "jpg", "webp"]
Action = Literal["generate", "edit", "chat", "close_chat"]

# In-memory chat sessions (per-process). The official SDK handles thought signatures inside chat objects.
_CHATS: Dict[str, Any] = {}
_MAX_CHATS = 25


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


def _normalize_output_format(fmt: Optional[str]) -> str:
    """Normalize output format (e.g., jpg -> jpeg)."""
    if not fmt:
        return "png"
    fmt_norm = fmt.strip().lower()
    if fmt_norm == "jpg":
        fmt_norm = "jpeg"
    return fmt_norm


def _infer_format_from_filename(filename: str) -> Optional[str]:
    suffix = Path(filename).suffix.lower().lstrip(".")
    if not suffix:
        return None
    if suffix == "jpg":
        return "jpeg"
    if suffix in {"png", "jpeg", "webp"}:
        return suffix
    return None


def _resolve_output_paths(
    *,
    output_dir: str,
    action: str,
    output_filename: Optional[str],
    output_format: str,
    count: int,
) -> List[Path]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    fmt = _normalize_output_format(output_format)
    if fmt not in {"png", "jpeg", "webp"}:
        raise ValueError("output_format must be one of: png, jpeg, webp")

    if output_filename:
        inferred = _infer_format_from_filename(output_filename)
        if inferred and inferred != fmt:
            raise ValueError(
                f"output_filename extension implies format '{inferred}', but output_format is '{fmt}'. "
                "Either align them or omit output_format."
            )

        base = Path(output_filename)
        if base.suffix:
            stem = base.stem
            suffix = base.suffix
        else:
            stem = base.name
            suffix = f".{fmt}"

        if count <= 1:
            return [out_dir / f"{stem}{suffix}"]
        return [out_dir / f"{stem}_{i+1}{suffix}" for i in range(count)]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if action == "edit":
        stem = f"gemini_edited_{timestamp}"
    else:
        stem = f"gemini_image_{timestamp}"
    suffix = f".{fmt}"

    if count <= 1:
        return [out_dir / f"{stem}{suffix}"]
    return [out_dir / f"{stem}_{i+1}{suffix}" for i in range(count)]


def _save_image_bytes(*, image_bytes: bytes, file_path: Path, output_format: str) -> None:
    """Save image bytes to disk, converting formats if needed.

    Note: Gemini may return PNG bytes even if a different output format is requested.
    For non-PNG output, we convert via Pillow if available.
    """
    fmt = _normalize_output_format(output_format)
    if fmt == "png":
        with open(file_path, "wb") as f:
            f.write(image_bytes)
        return

    try:
        from PIL import Image
    except ImportError:
        raise ImportError(
            "Pillow is required for output_format != 'png'. "
            "Install with: pip install strands-pack[image] (or pip install Pillow)"
        ) from None

    img = Image.open(BytesIO(image_bytes))
    # Ensure compatible mode for JPEG
    if fmt == "jpeg" and img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGB")
    img.save(file_path, format=fmt.upper())


def _extract_images_and_text(response: Any) -> Tuple[List[bytes], Optional[str]]:
    """Extract image bytes and text response from a Gemini response.

    Supports both:
    - response.parts (some SDK versions)
    - response.candidates[0].content.parts (common structure)
    """
    images: List[bytes] = []
    text_response: Optional[str] = None

    parts = getattr(response, "parts", None)
    if parts:
        for part in parts:
            if getattr(part, "thought", False):
                continue
            inline = getattr(part, "inline_data", None)
            if inline is not None:
                data = getattr(inline, "data", None)
                if data:
                    images.append(data)
                    continue
            txt = getattr(part, "text", None)
            if txt and text_response is None:
                text_response = txt
        return images, text_response

    candidates = getattr(response, "candidates", None) or []
    for cand in candidates:
        content = getattr(cand, "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            if getattr(part, "thought", False):
                continue
            inline = getattr(part, "inline_data", None)
            if inline is not None:
                data = getattr(inline, "data", None)
                if data:
                    images.append(data)
                    continue
            txt = getattr(part, "text", None)
            if txt and text_response is None:
                text_response = txt

    return images, text_response


def _load_image_part(image_path: str):
    """Load an image file and return a Part object (for image generation)."""
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
    return types.Part.from_bytes(data=image_bytes, mime_type=mime_type)


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


def _generate_image(
    prompt: str,
    model: str = "gemini-3-pro-image-preview",
    aspect_ratio: Optional[str] = None,
    image_size: Optional[str] = None,
    use_google_search: bool = False,
    reference_images: Optional[List[str]] = None,
    output_dir: str = "output",
    output_filename: Optional[str] = None,
    output_format: str = "png",
    num_images: int = 1,
    response_modalities: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Generate an image using Gemini image models."""
    try:
        from google.genai import types
    except ImportError:
        return _err("google-genai not installed. Run: pip install strands-pack[gemini]")

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return _err("GOOGLE_API_KEY environment variable not set")

    if model == "gemini-2.5-flash-image":
        if image_size:
            return _err("image_size is only supported with gemini-3-pro-image-preview")
        if use_google_search:
            return _err("Google Search grounding is only supported with gemini-3-pro-image-preview")
        if reference_images and len(reference_images) > 3:
            return _err("gemini-2.5-flash-image supports up to 3 reference images")

    if reference_images and len(reference_images) > 14:
        return _err("Maximum 14 reference images supported")

    if num_images < 1:
        return _err("num_images must be >= 1")
    if num_images > 8:
        return _err("num_images is capped at 8 for safety")

    try:
        client = _get_client(api_key)

        contents = []

        if reference_images:
            for img_path in reference_images:
                try:
                    contents.append(_load_image_part(img_path))
                except FileNotFoundError as e:
                    return _err(str(e))

        contents.append(prompt)

        image_config = {}
        if aspect_ratio:
            image_config["aspect_ratio"] = aspect_ratio
        if image_size and model == "gemini-3-pro-image-preview":
            image_config["image_size"] = image_size

        config_kwargs = {
            "response_modalities": response_modalities or ["TEXT", "IMAGE"],
        }
        if image_config:
            config_kwargs["image_config"] = types.ImageConfig(**image_config)

        if use_google_search and model == "gemini-3-pro-image-preview":
            config_kwargs["tools"] = [{"google_search": {}}]

        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(**config_kwargs),
        )

        images, text_response = _extract_images_and_text(response)
        if not images:
            return _err("No image data in response", text_response=text_response)

        to_write = images[:num_images]
        try:
            file_paths = _resolve_output_paths(
                output_dir=output_dir,
                action="generate",
                output_filename=output_filename,
                output_format=output_format,
                count=len(to_write),
            )
        except Exception as e:
            return _err(str(e))

        try:
            for img_bytes, path in zip(to_write, file_paths):
                _save_image_bytes(image_bytes=img_bytes, file_path=path, output_format=output_format)
        except Exception as e:
            return _err(str(e))

        warnings: List[str] = []
        if len(images) < num_images:
            warnings.append(f"Only {len(images)} image(s) returned by the API; requested {num_images}.")

        return _ok(
            file_path=str(file_paths[0]),
            file_paths=[str(p) for p in file_paths],
            message=f"Saved {len(file_paths)} image(s) to {Path(output_dir)}",
            model=model,
            text_response=text_response,
            action="generate",
            output_format=_normalize_output_format(output_format),
            num_images_requested=num_images,
            num_images_generated=len(file_paths),
            warnings=warnings or None,
        )

    except Exception as e:
        return _err(str(e))


def _edit_image(
    prompt: str,
    image_path: str,
    model: str = "gemini-3-pro-image-preview",
    aspect_ratio: Optional[str] = None,
    image_size: Optional[str] = None,
    additional_images: Optional[List[str]] = None,
    output_dir: str = "output",
    output_filename: Optional[str] = None,
    output_format: str = "png",
    num_images: int = 1,
    response_modalities: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Edit an existing image using Gemini image models."""
    try:
        from google.genai import types
    except ImportError:
        return _err("google-genai not installed. Run: pip install strands-pack[gemini]")

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return _err("GOOGLE_API_KEY environment variable not set")

    if model == "gemini-2.5-flash-image":
        if image_size:
            return _err("image_size is only supported with gemini-3-pro-image-preview")

    if num_images < 1:
        return _err("num_images must be >= 1")
    if num_images > 8:
        return _err("num_images is capped at 8 for safety")

    try:
        client = _get_client(api_key)

        contents = []

        try:
            contents.append(_load_image_part(image_path))
        except FileNotFoundError as e:
            return _err(str(e))

        if additional_images:
            for img_path in additional_images:
                try:
                    contents.append(_load_image_part(img_path))
                except FileNotFoundError as e:
                    return _err(str(e))

        contents.append(prompt)

        image_config = {}
        if aspect_ratio:
            image_config["aspect_ratio"] = aspect_ratio
        if image_size and model == "gemini-3-pro-image-preview":
            image_config["image_size"] = image_size

        config_kwargs = {
            "response_modalities": response_modalities or ["TEXT", "IMAGE"],
        }
        if image_config:
            config_kwargs["image_config"] = types.ImageConfig(**image_config)

        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(**config_kwargs),
        )

        images, text_response = _extract_images_and_text(response)
        if not images:
            return _err("No image data in response", text_response=text_response)

        to_write = images[:num_images]
        try:
            file_paths = _resolve_output_paths(
                output_dir=output_dir,
                action="edit",
                output_filename=output_filename,
                output_format=output_format,
                count=len(to_write),
            )
        except Exception as e:
            return _err(str(e))

        try:
            for img_bytes, path in zip(to_write, file_paths):
                _save_image_bytes(image_bytes=img_bytes, file_path=path, output_format=output_format)
        except Exception as e:
            return _err(str(e))

        warnings: List[str] = []
        if len(images) < num_images:
            warnings.append(f"Only {len(images)} image(s) returned by the API; requested {num_images}.")

        return _ok(
            file_path=str(file_paths[0]),
            file_paths=[str(p) for p in file_paths],
            message=f"Saved {len(file_paths)} image(s) to {Path(output_dir)}",
            model=model,
            text_response=text_response,
            action="edit",
            output_format=_normalize_output_format(output_format),
            num_images_requested=num_images,
            num_images_generated=len(file_paths),
            warnings=warnings or None,
        )

    except Exception as e:
        return _err(str(e))


def _chat(
    *,
    prompt: str,
    model: str = "gemini-3-pro-image-preview",
    chat_id: Optional[str] = None,
    aspect_ratio: Optional[str] = None,
    image_size: Optional[str] = None,
    use_google_search: bool = False,
    additional_images: Optional[List[str]] = None,
    response_modalities: Optional[List[str]] = None,
    output_dir: str = "output",
    output_filename: Optional[str] = None,
    output_format: str = "png",
    num_images: int = 1,
) -> Dict[str, Any]:
    """Multi-turn image generation/editing using Gemini chat sessions."""
    try:
        from google.genai import types
    except ImportError:
        return _err("google-genai not installed. Run: pip install strands-pack[gemini]")

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return _err("GOOGLE_API_KEY environment variable not set")

    if num_images < 1:
        return _err("num_images must be >= 1")
    if num_images > 8:
        return _err("num_images is capped at 8 for safety")

    if model == "gemini-2.5-flash-image":
        if image_size:
            return _err("image_size is only supported with gemini-3-pro-image-preview")
        if use_google_search:
            return _err("Google Search grounding is only supported with gemini-3-pro-image-preview")

    try:
        client = _get_client(api_key)

        if not chat_id:
            if len(_CHATS) >= _MAX_CHATS:
                return _err("Too many active chats. Close old chats or restart the process.")
            chat_id = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

            config_kwargs: Dict[str, Any] = {
                "response_modalities": response_modalities or ["TEXT", "IMAGE"],
            }
            image_config = {}
            if aspect_ratio:
                image_config["aspect_ratio"] = aspect_ratio
            if image_size and model == "gemini-3-pro-image-preview":
                image_config["image_size"] = image_size
            if image_config:
                config_kwargs["image_config"] = types.ImageConfig(**image_config)
            if use_google_search and model == "gemini-3-pro-image-preview":
                config_kwargs["tools"] = [{"google_search": {}}]

            chat = client.chats.create(model=model, config=types.GenerateContentConfig(**config_kwargs))
            _CHATS[chat_id] = chat
        else:
            chat = _CHATS.get(chat_id)
            if not chat:
                return _err("Unknown chat_id", chat_id=chat_id)

        message_parts: List[Any] = []
        if additional_images:
            for img_path in additional_images:
                try:
                    message_parts.append(_load_image_part(img_path))
                except FileNotFoundError as e:
                    return _err(str(e))
        message_parts.append(prompt)

        response = chat.send_message(message_parts)
        images, text_response = _extract_images_and_text(response)
        if not images:
            return _err("No image data in response", text_response=text_response, chat_id=chat_id)

        to_write = images[:num_images]
        try:
            file_paths = _resolve_output_paths(
                output_dir=output_dir,
                action="chat",
                output_filename=output_filename,
                output_format=output_format,
                count=len(to_write),
            )
        except Exception as e:
            return _err(str(e), chat_id=chat_id)

        try:
            for img_bytes, path in zip(to_write, file_paths):
                _save_image_bytes(image_bytes=img_bytes, file_path=path, output_format=output_format)
        except Exception as e:
            return _err(str(e), chat_id=chat_id)

        return _ok(
            action="chat",
            chat_id=chat_id,
            file_path=str(file_paths[0]),
            file_paths=[str(p) for p in file_paths],
            message=f"Saved {len(file_paths)} image(s) to {Path(output_dir)}",
            model=model,
            text_response=text_response,
            output_format=_normalize_output_format(output_format),
            num_images_requested=num_images,
            num_images_generated=len(file_paths),
        )
    except Exception as e:
        return _err(str(e))


def _close_chat(*, chat_id: str) -> Dict[str, Any]:
    if not chat_id:
        return _err("'chat_id' is required for action 'close_chat'")
    existed = chat_id in _CHATS
    _CHATS.pop(chat_id, None)
    return _ok(action="close_chat", chat_id=chat_id, closed=existed)


# -----------------------------------------------------------------------------
# Main Tool Function
# -----------------------------------------------------------------------------


@tool
def gemini_image(
    action: str,
    prompt: Optional[str] = None,
    image_path: Optional[str] = None,
    model: str = "gemini-3-pro-image-preview",
    aspect_ratio: Optional[str] = None,
    image_size: Optional[str] = None,
    use_google_search: bool = False,
    reference_images: Optional[List[str]] = None,
    additional_images: Optional[List[str]] = None,
    output_dir: str = "output",
    output_filename: Optional[str] = None,
    output_format: str = "png",
    num_images: int = 1,
    response_modalities: Optional[List[str]] = None,
    chat_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate and edit images using Google's Gemini image models.

    Args:
        action: The action to perform. One of:
                - "generate": Generate an image from text
                - "edit": Edit an existing image
                - "chat": Multi-turn conversational generation/editing (recommended for iteration)
                - "close_chat": Close a chat session created by "chat"
        prompt: Text description for generation or editing.
        image_path: Path to the image to edit (required for "edit" action).
        model: The Gemini model to use. One of:
               - "gemini-3-pro-image-preview" (default): Higher quality, supports more features
               - "gemini-2.5-flash-image": Faster, limited features
        aspect_ratio: Output aspect ratio. One of:
                      "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"
        image_size: Output image size (Gemini 3 Pro only). One of: "1K", "2K", "4K"
        use_google_search: Enable Google Search grounding (Gemini 3 Pro only).
        reference_images: List of image paths for style/content reference (for "generate" action).
                         Gemini 3 Pro supports up to 14, Flash supports up to 3.
        additional_images: Additional reference images (for "edit" action).
        output_dir: Directory to save generated images (default: "output").
        output_filename: Optional filename for saved output (within output_dir). If num_images > 1,
                         an index suffix will be added (e.g., my_image_1.png).
        output_format: Output file format: "png" (default), "jpeg"/"jpg", or "webp".
                       Note: non-PNG formats require Pillow (strands-pack[image]).
        num_images: Number of variations to save (default: 1). If the API returns fewer images, only those
                    will be saved. Capped at 8 for safety.
        response_modalities: Optional list like ["IMAGE"] or ["TEXT","IMAGE"]. Defaults to ["TEXT","IMAGE"].
        chat_id: For action="chat", continue an existing session when provided.

    Returns:
        dict with keys:
            - success: bool indicating if the operation succeeded
            - file_path: path to saved image file (if successful)
            - message: status message
            - model: the model that was used
            - action: the action that was performed
            - text_response: any text from the model response
            - error: error message (if failed)

    Examples:
        >>> gemini_image(action="generate", prompt="A sunset over mountains")
        >>> gemini_image(action="generate", prompt="A cat", aspect_ratio="16:9", image_size="2K")
        >>> gemini_image(action="edit", prompt="Add a hat", image_path="photo.png")
        >>> gemini_image(action="edit", prompt="Change background to beach", image_path="portrait.png")
        >>> gemini_image(action="generate", prompt="A logo", output_filename="logo.png")
        >>> gemini_image(action="generate", prompt="A logo", output_filename="logo", output_format="webp")
        >>> gemini_image(action="generate", prompt="A logo", output_filename="logo", num_images=3)
    """
    valid_actions = ["generate", "edit", "chat", "close_chat"]

    if action not in valid_actions:
        return _err(f"Invalid action '{action}'. Must be one of: {valid_actions}")

    if action in ("generate", "edit", "chat") and not prompt:
        return _err(f"'prompt' is required for action '{action}'")

    if action == "edit" and not image_path:
        return _err("'image_path' is required for action 'edit'")
    if action == "close_chat" and not chat_id:
        return _err("'chat_id' is required for action 'close_chat'")

    if action == "generate":
        return _generate_image(
            prompt=prompt,
            model=model,
            aspect_ratio=aspect_ratio,
            image_size=image_size,
            use_google_search=use_google_search,
            reference_images=reference_images,
            output_dir=output_dir,
            output_filename=output_filename,
            output_format=output_format,
            num_images=num_images,
            response_modalities=response_modalities,
        )
    elif action == "edit":
        return _edit_image(
            prompt=prompt,
            image_path=image_path,
            model=model,
            aspect_ratio=aspect_ratio,
            image_size=image_size,
            additional_images=additional_images,
            output_dir=output_dir,
            output_filename=output_filename,
            output_format=output_format,
            num_images=num_images,
            response_modalities=response_modalities,
        )
    elif action == "chat":
        return _chat(
            prompt=prompt,
            model=model,
            chat_id=chat_id,
            aspect_ratio=aspect_ratio,
            image_size=image_size,
            use_google_search=use_google_search,
            additional_images=additional_images,
            response_modalities=response_modalities,
            output_dir=output_dir,
            output_filename=output_filename,
            output_format=output_format,
            num_images=num_images,
        )
    elif action == "close_chat":
        return _close_chat(chat_id=chat_id)

    return _err(f"Unhandled action: {action}")
