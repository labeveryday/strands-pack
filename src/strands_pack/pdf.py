"""
PDF Tool

PDF manipulation using PyMuPDF (fitz).

Actions
-------
- extract_text: Extract text from PDF (pages, preserve_layout)
- extract_pages: Extract specific pages to new PDF (pages)
- delete_pages: Remove specific pages to new PDF (pages)
- merge: Merge multiple PDFs (input_paths)
- split: Split PDF into multiple files (pages_per_file)
- get_info: Get PDF metadata and info
- to_images: Convert pages to images (format, dpi, pages)
- rotate_pages: Rotate pages (angle, pages)
- add_watermark: Add text watermark (text, position, opacity, font_size)
- search_text: Search for text in PDF (query, case_sensitive)
- add_page_numbers: Add page numbers to PDF (position, font_size, format)

Requirements:
    pip install strands-pack[pdf]
"""

import os
from typing import Any, Dict, List, Optional

from strands import tool

try:
    import fitz  # PyMuPDF

    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False


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


def _check_pymupdf() -> Optional[Dict[str, Any]]:
    """Check if PyMuPDF is installed."""
    if not HAS_PYMUPDF:
        return _err("PyMuPDF not installed. Run: pip install strands-pack[pdf]", error_type="ImportError")
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


def _validate_output_dir(output_dir: Optional[str]) -> Optional[Dict[str, Any]]:
    """Validate output directory exists."""
    if not output_dir:
        return _err("output_dir is required")
    if not os.path.exists(output_dir):
        return _err(f"Output directory does not exist: {output_dir}", error_type="FileNotFoundError")
    return None


@tool
def pdf(
    action: str,
    input_path: Optional[str] = None,
    input_paths: Optional[List[str]] = None,
    output_path: Optional[str] = None,
    output_dir: Optional[str] = None,
    pages: Optional[List[int]] = None,
    preserve_layout: bool = False,
    pages_per_file: int = 1,
    output_format: str = "png",
    dpi: int = 150,
    angle: Optional[int] = None,
    text: Optional[str] = None,
    position: str = "center",
    opacity: float = 0.3,
    font_size: Optional[int] = None,
    query: Optional[str] = None,
    case_sensitive: bool = False,
    number_format: str = "Page {n}",
) -> Dict[str, Any]:
    """
    Manipulate PDF files using PyMuPDF.

    Args:
        action: The action to perform. One of:
            - "extract_text": Extract text from PDF.
            - "extract_pages": Extract specific pages to new PDF.
            - "delete_pages": Delete specific pages from PDF (write new PDF).
            - "merge": Merge multiple PDFs.
            - "split": Split PDF into multiple files.
            - "get_info": Get PDF metadata and info.
            - "to_images": Convert pages to images.
            - "rotate_pages": Rotate pages in PDF.
            - "add_watermark": Add text watermark.
            - "search_text": Search for text in PDF.
            - "add_page_numbers": Add page numbers to PDF.
        input_path: Path to input PDF (required for most actions).
        input_paths: List of PDF paths for merge action.
        output_path: Path to output PDF (required for most write actions).
        output_dir: Output directory for split/to_images actions.
        pages: List of page numbers (0-indexed) for page-specific actions.
        preserve_layout: Preserve text layout when extracting (default False).
        pages_per_file: Pages per file when splitting (default 1).
        output_format: Image format for to_images action (default "png").
        dpi: DPI for to_images action (default 150).
        angle: Rotation angle (90, 180, 270) for rotate_pages action.
        text: Watermark text for add_watermark action.
        position: Watermark position for add_watermark (default "center").
        opacity: Watermark opacity for add_watermark (default 0.3).
        font_size: Font size for watermark/page numbers (auto-calculated if not set).
        query: Search query for search_text action.
        case_sensitive: Case-sensitive search (default False).
        number_format: Page number format string with {n} placeholder (default "Page {n}").

    Returns:
        dict with success status and action-specific data

    Examples:
        >>> pdf(action="extract_text", input_path="document.pdf")
        >>> pdf(action="merge", input_paths=["a.pdf", "b.pdf"], output_path="merged.pdf")
        >>> pdf(action="get_info", input_path="document.pdf")
    """
    if err := _check_pymupdf():
        return err

    action = (action or "").strip().lower()

    try:
        if action == "extract_text":
            if err := _validate_input_path(input_path):
                return err

            doc = fitz.open(input_path)
            total_pages = len(doc)

            if pages is None:
                page_numbers = list(range(total_pages))
            else:
                page_numbers = [p for p in pages if 0 <= p < total_pages]

            extracted_text = []
            for page_num in page_numbers:
                page = doc[page_num]
                if preserve_layout:
                    txt = page.get_text("text", flags=fitz.TEXT_PRESERVE_WHITESPACE)
                else:
                    txt = page.get_text("text")
                extracted_text.append({"page": page_num, "text": txt.strip()})

            doc.close()

            return _ok(
                action="extract_text",
                input_path=input_path,
                total_pages=total_pages,
                pages_extracted=len(extracted_text),
                content=extracted_text,
            )

        if action == "extract_pages":
            if err := _validate_input_path(input_path):
                return err
            if err := _validate_output_path(output_path):
                return err
            if not pages:
                return _err("pages is required (list of page numbers)")

            doc = fitz.open(input_path)
            total_pages = len(doc)

            valid_pages = [p for p in pages if 0 <= p < total_pages]
            if not valid_pages:
                doc.close()
                return _err(f"No valid pages specified. PDF has {total_pages} pages (0-{total_pages - 1})")

            new_doc = fitz.open()
            for page_num in valid_pages:
                new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)

            new_doc.save(output_path)
            new_doc.close()
            doc.close()

            return _ok(
                action="extract_pages",
                input_path=input_path,
                output_path=output_path,
                original_pages=total_pages,
                extracted_pages=valid_pages,
                pages_count=len(valid_pages),
            )

        if action == "delete_pages":
            if err := _validate_input_path(input_path):
                return err
            if err := _validate_output_path(output_path):
                return err
            if not pages:
                return _err("pages is required (list of page numbers)")

            doc = fitz.open(input_path)
            total_pages = len(doc)

            delete_pages = sorted({p for p in pages if 0 <= p < total_pages})
            if not delete_pages:
                doc.close()
                return _err(f"No valid pages specified. PDF has {total_pages} pages (0-{total_pages - 1})")

            keep_pages = [p for p in range(total_pages) if p not in set(delete_pages)]
            if not keep_pages:
                doc.close()
                return _err("Refusing to delete all pages. At least one page must remain.", error_type="ValidationError")

            new_doc = fitz.open()
            for p in keep_pages:
                new_doc.insert_pdf(doc, from_page=p, to_page=p)

            new_doc.save(output_path)
            new_doc.close()
            doc.close()

            return _ok(
                action="delete_pages",
                input_path=input_path,
                output_path=output_path,
                original_pages=total_pages,
                deleted_pages=delete_pages,
                kept_pages=keep_pages,
                pages_deleted=len(delete_pages),
                pages_remaining=len(keep_pages),
            )

        if action == "merge":
            if not input_paths or not isinstance(input_paths, list):
                return _err("input_paths is required (list of PDF paths)")
            if err := _validate_output_path(output_path):
                return err

            for path in input_paths:
                if not os.path.exists(path):
                    return _err(f"Input file not found: {path}", error_type="FileNotFoundError")

            merged_doc = fitz.open()
            page_counts = []

            for path in input_paths:
                doc = fitz.open(path)
                page_counts.append({"file": path, "pages": len(doc)})
                merged_doc.insert_pdf(doc)
                doc.close()

            merged_doc.save(output_path)
            total_pages = len(merged_doc)
            merged_doc.close()

            return _ok(
                action="merge",
                input_paths=input_paths,
                output_path=output_path,
                files_merged=len(input_paths),
                page_counts=page_counts,
                total_pages=total_pages,
            )

        if action == "split":
            if err := _validate_input_path(input_path):
                return err
            if err := _validate_output_dir(output_dir):
                return err

            doc = fitz.open(input_path)
            total_pages = len(doc)
            base_name = os.path.splitext(os.path.basename(input_path))[0]

            output_files = []
            file_index = 1

            for start_page in range(0, total_pages, pages_per_file):
                end_page = min(start_page + pages_per_file, total_pages)

                new_doc = fitz.open()
                new_doc.insert_pdf(doc, from_page=start_page, to_page=end_page - 1)

                out_path = os.path.join(output_dir, f"{base_name}_part{file_index}.pdf")
                new_doc.save(out_path)
                new_doc.close()

                output_files.append({"file": out_path, "pages": list(range(start_page, end_page))})
                file_index += 1

            doc.close()

            return _ok(
                action="split",
                input_path=input_path,
                output_dir=output_dir,
                original_pages=total_pages,
                pages_per_file=pages_per_file,
                files_created=len(output_files),
                output_files=output_files,
            )

        if action == "get_info":
            if err := _validate_input_path(input_path):
                return err

            doc = fitz.open(input_path)
            metadata = doc.metadata

            info = {
                "page_count": len(doc),
                "file_size_bytes": os.path.getsize(input_path),
                "metadata": {
                    "title": metadata.get("title", ""),
                    "author": metadata.get("author", ""),
                    "subject": metadata.get("subject", ""),
                    "creator": metadata.get("creator", ""),
                    "producer": metadata.get("producer", ""),
                    "creation_date": metadata.get("creationDate", ""),
                    "modification_date": metadata.get("modDate", ""),
                },
                "is_encrypted": doc.is_encrypted,
                "permissions": doc.permissions if not doc.is_encrypted else None,
            }

            if len(doc) > 0:
                first_page = doc[0]
                rect = first_page.rect
                info["page_dimensions"] = {"width": rect.width, "height": rect.height, "unit": "points"}

            doc.close()

            return _ok(action="get_info", input_path=input_path, **info)

        if action == "to_images":
            if err := _validate_input_path(input_path):
                return err
            if err := _validate_output_dir(output_dir):
                return err

            doc = fitz.open(input_path)
            total_pages = len(doc)
            base_name = os.path.splitext(os.path.basename(input_path))[0]

            if pages is None:
                page_numbers = list(range(total_pages))
            else:
                page_numbers = [p for p in pages if 0 <= p < total_pages]

            zoom = dpi / 72.0
            matrix = fitz.Matrix(zoom, zoom)

            output_files = []
            for page_num in page_numbers:
                page = doc[page_num]
                pix = page.get_pixmap(matrix=matrix)

                out_path = os.path.join(output_dir, f"{base_name}_page{page_num + 1}.{output_format}")
                pix.save(out_path)

                output_files.append({"file": out_path, "page": page_num, "width": pix.width, "height": pix.height})

            doc.close()

            return _ok(
                action="to_images",
                input_path=input_path,
                output_dir=output_dir,
                format=output_format,
                dpi=dpi,
                pages_converted=len(output_files),
                output_files=output_files,
            )

        if action == "rotate_pages":
            if err := _validate_input_path(input_path):
                return err
            if err := _validate_output_path(output_path):
                return err
            if angle is None:
                return _err("angle is required (90, 180, or 270)")
            if angle not in (90, 180, 270, -90, -180, -270):
                return _err("angle must be 90, 180, or 270 (or negative)")

            doc = fitz.open(input_path)
            total_pages = len(doc)

            if pages is None:
                page_numbers = list(range(total_pages))
            else:
                page_numbers = [p for p in pages if 0 <= p < total_pages]

            for page_num in page_numbers:
                page = doc[page_num]
                page.set_rotation(page.rotation + angle)

            doc.save(output_path)
            doc.close()

            return _ok(
                action="rotate_pages",
                input_path=input_path,
                output_path=output_path,
                angle=angle,
                pages_rotated=page_numbers,
                total_pages=total_pages,
            )

        if action == "add_watermark":
            if err := _validate_input_path(input_path):
                return err
            if err := _validate_output_path(output_path):
                return err
            if not text:
                return _err("text is required")

            doc = fitz.open(input_path)

            for page in doc:
                rect = page.rect

                if position == "center":
                    x = rect.width / 2
                    y = rect.height / 2
                elif position == "top-left":
                    x = 50
                    y = 50
                elif position == "top-right":
                    x = rect.width - 50
                    y = 50
                elif position == "bottom-left":
                    x = 50
                    y = rect.height - 50
                elif position == "bottom-right":
                    x = rect.width - 50
                    y = rect.height - 50
                else:
                    x = rect.width / 2
                    y = rect.height / 2

                fs = font_size if font_size else min(rect.width, rect.height) / 10

                page.insert_text((x, y), text, fontsize=fs, color=(0.5, 0.5, 0.5), overlay=True)

            doc.save(output_path)
            pages_watermarked = len(doc)
            doc.close()

            return _ok(
                action="add_watermark",
                input_path=input_path,
                output_path=output_path,
                text=text,
                position=position,
                opacity=opacity,
                pages_watermarked=pages_watermarked,
            )

        if action == "search_text":
            if err := _validate_input_path(input_path):
                return err
            if not query:
                return _err("query is required")

            doc = fitz.open(input_path)
            results = []

            for page_num, page in enumerate(doc):
                if case_sensitive:
                    instances = page.search_for(query)
                else:
                    instances = page.search_for(query, quads=False)

                if instances:
                    results.append({"page": page_num, "occurrences": len(instances), "rects": [[r.x0, r.y0, r.x1, r.y1] for r in instances]})

            doc.close()

            return _ok(
                action="search_text",
                input_path=input_path,
                query=query,
                case_sensitive=case_sensitive,
                pages_with_matches=len(results),
                total_matches=sum(r["occurrences"] for r in results),
                results=results,
            )

        if action == "add_page_numbers":
            if err := _validate_input_path(input_path):
                return err
            if err := _validate_output_path(output_path):
                return err

            doc = fitz.open(input_path)
            total_pages = len(doc)

            for page_num, page in enumerate(doc):
                rect = page.rect
                fs = font_size if font_size else 12

                number_text = number_format.replace("{n}", str(page_num + 1)).replace("{total}", str(total_pages))

                if position == "bottom-center":
                    x = rect.width / 2
                    y = rect.height - 30
                elif position == "bottom-right":
                    x = rect.width - 50
                    y = rect.height - 30
                elif position == "bottom-left":
                    x = 50
                    y = rect.height - 30
                elif position == "top-center":
                    x = rect.width / 2
                    y = 30
                else:
                    x = rect.width / 2
                    y = rect.height - 30

                page.insert_text((x, y), number_text, fontsize=fs, color=(0, 0, 0), overlay=True)

            doc.save(output_path)
            doc.close()

            return _ok(
                action="add_page_numbers",
                input_path=input_path,
                output_path=output_path,
                position=position,
                format=number_format,
                pages_numbered=total_pages,
            )

        return _err(
            f"Unknown action: {action}",
            error_type="InvalidAction",
            available_actions=[
                "extract_text",
                "extract_pages",
                "delete_pages",
                "merge",
                "split",
                "get_info",
                "to_images",
                "rotate_pages",
                "add_watermark",
                "search_text",
                "add_page_numbers",
            ],
        )

    except Exception as e:
        return _err(str(e), error_type=type(e).__name__, action=action)
