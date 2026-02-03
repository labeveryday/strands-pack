"""
QR Code Tool

Generate and decode QR codes and barcodes.

Usage Examples:
    from strands import Agent
    from strands_pack import qrcode_tool

    agent = Agent(tools=[qrcode_tool])

    # Generate a QR code
    agent.tool.qrcode_tool(action="generate", data="https://example.com", output_path="qr.png")

    # Generate styled QR code with custom colors
    agent.tool.qrcode_tool(action="generate_styled", data="Hello", output_path="styled.png",
                           fill_color="blue", back_color="yellow")

    # Decode a QR code from an image
    agent.tool.qrcode_tool(action="decode", input_path="qr.png")

Available Actions:
    - generate: Create a QR code image
        Parameters: data (required), output_path (required), size, error_correction, border
    - generate_styled: Create a styled QR code with custom colors/logo
        Parameters: data (required), output_path (required), fill_color, back_color, logo_path, size, border
    - decode: Decode the first QR code in an image
        Parameters: input_path (required)
    - decode_all: Decode all QR codes in an image
        Parameters: input_path (required)
    - generate_svg: Create a QR code as SVG
        Parameters: data (required), output_path (required), size, border
    - generate_barcode: Create a barcode (code128, code39, ean13, etc.)
        Parameters: data (required), output_path (required), barcode_type (required), width, height
    - decode_barcode: Decode barcodes from an image
        Parameters: input_path (required)
    - get_info: Get information about QR codes in an image
        Parameters: input_path (required)

Notes:
    - pyzbar on Windows may require Visual C++ Redistributable 2013
    - Error correction levels: L (7%), M (15%), Q (25%), H (30%)

Requires: pip install strands-pack[qrcode]
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from strands import tool

# Lazy imports for optional dependencies
_qrcode = None
_pyzbar = None
_PIL = None


def _get_qrcode():
    global _qrcode
    if _qrcode is None:
        try:
            import qrcode
            _qrcode = qrcode
        except ImportError:
            raise ImportError("qrcode not installed. Run: pip install strands-pack[qrcode]") from None
    return _qrcode


def _get_pyzbar():
    global _pyzbar
    if _pyzbar is None:
        try:
            from pyzbar import pyzbar
            _pyzbar = pyzbar
        except ImportError:
            raise ImportError("pyzbar not installed. Run: pip install strands-pack[qrcode]") from None
    return _pyzbar


def _get_pil():
    global _PIL
    if _PIL is None:
        try:
            from PIL import Image
            _PIL = Image
        except ImportError:
            raise ImportError("Pillow not installed. Run: pip install strands-pack[qrcode]") from None
    return _PIL


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


def _generate(data: str, output_path: str, size: int = 10,
              error_correction: str = "M", border: int = 4) -> Dict[str, Any]:
    """Generate a QR code."""
    if not data:
        return _err("data is required")
    if not output_path:
        return _err("output_path is required")

    qrcode = _get_qrcode()

    # Map error correction level
    ec_map = {
        "L": qrcode.constants.ERROR_CORRECT_L,
        "M": qrcode.constants.ERROR_CORRECT_M,
        "Q": qrcode.constants.ERROR_CORRECT_Q,
        "H": qrcode.constants.ERROR_CORRECT_H,
    }
    ec_level = ec_map.get(error_correction.upper(), qrcode.constants.ERROR_CORRECT_M)

    qr = qrcode.QRCode(
        version=1,
        error_correction=ec_level,
        box_size=size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    path = Path(output_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(path))

    return _ok(
        action="generate",
        output_path=str(path),
        data_length=len(data),
        size=size,
        error_correction=error_correction.upper(),
        border=border,
    )


def _generate_styled(data: str, output_path: str, fill_color: str = "black",
                     back_color: str = "white", logo_path: Optional[str] = None,
                     size: int = 10, border: int = 4) -> Dict[str, Any]:
    """Generate a styled QR code with custom colors and optional logo."""
    if not data:
        return _err("data is required")
    if not output_path:
        return _err("output_path is required")

    qrcode = _get_qrcode()
    Image = _get_pil()

    # Use higher error correction if adding a logo
    ec_level = qrcode.constants.ERROR_CORRECT_H if logo_path else qrcode.constants.ERROR_CORRECT_M

    qr = qrcode.QRCode(
        version=1,
        error_correction=ec_level,
        box_size=size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color=fill_color, back_color=back_color).convert("RGBA")

    # Add logo if provided
    if logo_path:
        logo_p = Path(logo_path).expanduser()
        if not logo_p.exists():
            return _err(f"Logo file not found: {logo_path}", error_type="FileNotFoundError")

        logo = Image.open(str(logo_p)).convert("RGBA")

        # Resize logo to fit in center (about 20% of QR code size)
        qr_width, qr_height = img.size
        logo_max_size = int(min(qr_width, qr_height) * 0.2)
        logo.thumbnail((logo_max_size, logo_max_size), Image.Resampling.LANCZOS)

        # Calculate position to center the logo
        logo_pos = (
            (qr_width - logo.width) // 2,
            (qr_height - logo.height) // 2,
        )

        # Paste logo onto QR code
        img.paste(logo, logo_pos, logo)

    path = Path(output_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(path))

    return _ok(
        action="generate_styled",
        output_path=str(path),
        data_length=len(data),
        fill_color=fill_color,
        back_color=back_color,
        has_logo=logo_path is not None,
    )


def _decode(input_path: str) -> Dict[str, Any]:
    """Decode the first QR code found in an image."""
    if not input_path:
        return _err("input_path is required")

    path = Path(input_path).expanduser()
    if not path.exists():
        return _err(f"File not found: {input_path}", error_type="FileNotFoundError")

    Image = _get_pil()
    pyzbar = _get_pyzbar()

    img = Image.open(str(path))
    decoded = pyzbar.decode(img)

    if not decoded:
        return _ok(action="decode", found=False, data=None, input_path=str(path))

    first = decoded[0]
    return _ok(
        action="decode",
        found=True,
        data=first.data.decode("utf-8", errors="replace"),
        type=first.type,
        input_path=str(path),
    )


def _decode_all(input_path: str) -> Dict[str, Any]:
    """Decode all QR codes found in an image."""
    if not input_path:
        return _err("input_path is required")

    path = Path(input_path).expanduser()
    if not path.exists():
        return _err(f"File not found: {input_path}", error_type="FileNotFoundError")

    Image = _get_pil()
    pyzbar = _get_pyzbar()

    img = Image.open(str(path))
    decoded = pyzbar.decode(img)

    results: List[Dict[str, Any]] = []
    for item in decoded:
        results.append({
            "data": item.data.decode("utf-8", errors="replace"),
            "type": item.type,
            "rect": {
                "left": item.rect.left,
                "top": item.rect.top,
                "width": item.rect.width,
                "height": item.rect.height,
            },
        })

    return _ok(
        action="decode_all",
        input_path=str(path),
        count=len(results),
        codes=results,
    )


def _generate_svg(data: str, output_path: str, size: int = 10,
                  border: int = 4) -> Dict[str, Any]:
    """Generate a QR code as SVG."""
    if not data:
        return _err("data is required")
    if not output_path:
        return _err("output_path is required")

    qrcode = _get_qrcode()
    import qrcode.image.svg

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)

    # Generate SVG
    factory = qrcode.image.svg.SvgImage
    img = qr.make_image(image_factory=factory)

    path = Path(output_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(path))

    return _ok(
        action="generate_svg",
        output_path=str(path),
        data_length=len(data),
        size=size,
        border=border,
    )


def _generate_barcode(data: str, output_path: str, barcode_type: str,
                      width: Optional[int] = None, height: Optional[int] = None) -> Dict[str, Any]:
    """Generate a barcode."""
    if not data:
        return _err("data is required")
    if not output_path:
        return _err("output_path is required")
    if not barcode_type:
        return _err("barcode_type is required (e.g., 'code128', 'code39', 'ean13')")

    try:
        import barcode
        from barcode.writer import ImageWriter
    except ImportError:
        return _err("python-barcode not installed. Run: pip install python-barcode")

    barcode_type = barcode_type.lower()

    try:
        barcode_class = barcode.get_barcode_class(barcode_type)
    except barcode.errors.BarcodeNotFoundError:
        available = list(barcode.PROVIDED_BARCODES)
        return _err(
            f"Unknown barcode type: {barcode_type}",
            error_type="InvalidBarcodeType",
            available_types=available,
        )

    writer = ImageWriter()
    options = {}
    if width:
        options["module_width"] = width / 100.0  # Convert to mm
    if height:
        options["module_height"] = height

    bc = barcode_class(data, writer=writer)

    path = Path(output_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)

    # barcode.save() adds extension automatically, so we handle that
    saved_path = bc.save(str(path.with_suffix("")), options=options)

    return _ok(
        action="generate_barcode",
        output_path=saved_path,
        barcode_type=barcode_type,
        data=data,
    )


def _decode_barcode(input_path: str) -> Dict[str, Any]:
    """Decode barcodes from an image."""
    if not input_path:
        return _err("input_path is required")

    path = Path(input_path).expanduser()
    if not path.exists():
        return _err(f"File not found: {input_path}", error_type="FileNotFoundError")

    Image = _get_pil()
    pyzbar = _get_pyzbar()

    img = Image.open(str(path))
    decoded = pyzbar.decode(img)

    results: List[Dict[str, Any]] = []
    for item in decoded:
        results.append({
            "data": item.data.decode("utf-8", errors="replace"),
            "type": item.type,
            "rect": {
                "left": item.rect.left,
                "top": item.rect.top,
                "width": item.rect.width,
                "height": item.rect.height,
            },
        })

    return _ok(
        action="decode_barcode",
        input_path=str(path),
        count=len(results),
        codes=results,
    )


def _get_info(input_path: str) -> Dict[str, Any]:
    """Get information about QR codes in an image."""
    if not input_path:
        return _err("input_path is required")

    path = Path(input_path).expanduser()
    if not path.exists():
        return _err(f"File not found: {input_path}", error_type="FileNotFoundError")

    Image = _get_pil()
    pyzbar = _get_pyzbar()

    img = Image.open(str(path))
    decoded = pyzbar.decode(img)

    codes_info: List[Dict[str, Any]] = []
    for item in decoded:
        codes_info.append({
            "type": item.type,
            "data_length": len(item.data),
            "data_preview": item.data.decode("utf-8", errors="replace")[:50],
            "position": {
                "left": item.rect.left,
                "top": item.rect.top,
                "width": item.rect.width,
                "height": item.rect.height,
            },
        })

    return _ok(
        action="get_info",
        input_path=str(path),
        image_size=[img.width, img.height],
        image_format=img.format,
        codes_found=len(codes_info),
        codes=codes_info,
    )


@tool
def qrcode_tool(
    action: str,
    data: Optional[str] = None,
    input_path: Optional[str] = None,
    output_path: Optional[str] = None,
    size: int = 10,
    border: int = 4,
    error_correction: str = "M",
    fill_color: str = "black",
    back_color: str = "white",
    logo_path: Optional[str] = None,
    barcode_type: Optional[str] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Generate and decode QR codes and barcodes.

    Args:
        action: The action to perform. One of:
                - "generate": Create a QR code image
                - "generate_styled": Create styled QR with custom colors/logo
                - "decode": Decode first QR code in an image
                - "decode_all": Decode all QR codes in an image
                - "generate_svg": Create a QR code as SVG
                - "generate_barcode": Create a barcode
                - "decode_barcode": Decode barcodes from an image
                - "get_info": Get info about QR codes in an image
        data: The data to encode (required for generate actions).
        input_path: Path to image file (required for decode actions).
        output_path: Path for output file (required for generate actions).
        size: Box size in pixels (default: 10).
        border: Border size in boxes (default: 4).
        error_correction: Error correction level - L, M, Q, H (default: "M").
        fill_color: QR code color (default: "black").
        back_color: Background color (default: "white").
        logo_path: Path to logo image for center (optional).
        barcode_type: Type of barcode - code128, code39, ean13, etc.
        width: Barcode module width (optional).
        height: Barcode module height (optional).

    Returns:
        dict with keys:
            - success: bool indicating if operation succeeded
            - action: the action performed
            - output_path: path to generated file (for generate actions)
            - data: decoded data (for decode actions)
            - error: error message (if failed)

    Examples:
        >>> qrcode_tool(action="generate", data="https://example.com", output_path="qr.png")
        >>> qrcode_tool(action="generate_styled", data="Hello", output_path="styled.png",
        ...             fill_color="blue", back_color="yellow")
        >>> qrcode_tool(action="decode", input_path="qr.png")
        >>> qrcode_tool(action="generate_barcode", data="123456789", output_path="barcode.png",
        ...             barcode_type="code128")
    """
    valid_actions = [
        "generate", "generate_styled", "decode", "decode_all",
        "generate_svg", "generate_barcode", "decode_barcode", "get_info"
    ]

    action = (action or "").strip().lower()

    if action not in valid_actions:
        return _err(
            f"Unknown action: {action}",
            error_type="InvalidAction",
            available_actions=valid_actions,
        )

    try:
        if action == "generate":
            return _generate(data or "", output_path or "", size, error_correction, border)
        elif action == "generate_styled":
            return _generate_styled(data or "", output_path or "", fill_color, back_color,
                                    logo_path, size, border)
        elif action == "decode":
            return _decode(input_path or "")
        elif action == "decode_all":
            return _decode_all(input_path or "")
        elif action == "generate_svg":
            return _generate_svg(data or "", output_path or "", size, border)
        elif action == "generate_barcode":
            return _generate_barcode(data or "", output_path or "", barcode_type or "", width, height)
        elif action == "decode_barcode":
            return _decode_barcode(input_path or "")
        elif action == "get_info":
            return _get_info(input_path or "")
        else:
            return _err(f"Unhandled action: {action}")
    except ImportError as e:
        return _err(str(e), error_type="ImportError")
    except Exception as e:
        return _err(str(e), error_type=type(e).__name__, action=action)
