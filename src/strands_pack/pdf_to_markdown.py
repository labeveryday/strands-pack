"""
PDF to Markdown Tool

High-quality PDF-to-markdown conversion for LLM/RAG consumption.

Actions
-------
- convert: Convert local PDF to structured markdown (input_path, pages, output_path)
- from_arxiv: Fetch arxiv paper and convert to markdown (arxiv_id, output_path)

Requirements:
    pip install strands-pack[pdf_to_markdown]
"""

import os
import re
import tempfile
from typing import Any, Dict, List, Optional

from strands import tool

try:
    import pymupdf4llm

    HAS_PYMUPDF4LLM = True
except ImportError:
    HAS_PYMUPDF4LLM = False


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


def _check_pymupdf4llm() -> Optional[Dict[str, Any]]:
    if not HAS_PYMUPDF4LLM:
        return _err("pymupdf4llm not installed. Run: pip install strands-pack[pdf_to_markdown]", error_type="ImportError")
    return None


def _html_to_markdown(html: str) -> str:
    """Convert HTML article body to clean markdown using BeautifulSoup."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")

    # Try to find the main article body
    article = soup.find("article") or soup.find("main") or soup.find("div", class_="ltx_page_content") or soup.body or soup

    lines = []

    for element in article.descendants:
        if element.name is None:
            continue

        text = element.get_text(strip=True)
        if not text:
            continue

        if element.name in ("h1",):
            lines.append(f"\n# {text}\n")
        elif element.name in ("h2",):
            lines.append(f"\n## {text}\n")
        elif element.name in ("h3",):
            lines.append(f"\n### {text}\n")
        elif element.name in ("h4",):
            lines.append(f"\n#### {text}\n")
        elif element.name in ("h5", "h6"):
            lines.append(f"\n##### {text}\n")
        elif element.name == "p":
            lines.append(f"\n{text}\n")
        elif element.name == "li":
            lines.append(f"- {text}")
        elif element.name in ("pre", "code"):
            if element.parent and element.parent.name in ("pre", "code"):
                continue
            lines.append(f"\n```\n{text}\n```\n")
        elif element.name == "blockquote":
            lines.append(f"\n> {text}\n")
        elif element.name == "table":
            # Simple table extraction
            rows = element.find_all("tr")
            for i, row in enumerate(rows):
                cells = row.find_all(["th", "td"])
                cell_texts = [c.get_text(strip=True) for c in cells]
                lines.append("| " + " | ".join(cell_texts) + " |")
                if i == 0:
                    lines.append("| " + " | ".join(["---"] * len(cell_texts)) + " |")

    md = "\n".join(lines)
    # Clean up excessive blank lines
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip()


@tool
def pdf_to_markdown(
    action: str,
    input_path: Optional[str] = None,
    pages: Optional[List[int]] = None,
    output_path: Optional[str] = None,
    arxiv_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convert PDFs to high-quality markdown for LLM/RAG consumption.

    Args:
        action: The action to perform. One of:
            - "convert": Convert a local PDF file to markdown.
            - "from_arxiv": Fetch an arxiv paper and convert to markdown.
        input_path: Path to input PDF (required for convert action).
        pages: Optional list of page numbers (0-indexed) to convert. Defaults to all pages.
        output_path: Optional path to write the markdown output to a file.
        arxiv_id: Arxiv paper ID, e.g. "2005.11401" (required for from_arxiv action).

    Returns:
        dict with success status, markdown content, and metadata

    Examples:
        >>> pdf_to_markdown(action="convert", input_path="paper.pdf")
        >>> pdf_to_markdown(action="convert", input_path="paper.pdf", pages=[0, 1, 2])
        >>> pdf_to_markdown(action="from_arxiv", arxiv_id="2005.11401")
        >>> pdf_to_markdown(action="from_arxiv", arxiv_id="2005.11401", output_path="rag.md")
    """
    action = (action or "").strip().lower()

    try:
        if action == "convert":
            if err := _check_pymupdf4llm():
                return err
            if not input_path:
                return _err("input_path is required")
            if not os.path.exists(input_path):
                return _err(f"Input file not found: {input_path}", error_type="FileNotFoundError")

            kwargs: Dict[str, Any] = {}
            if pages is not None:
                kwargs["pages"] = pages

            md = pymupdf4llm.to_markdown(input_path, **kwargs)

            result = _ok(
                action="convert",
                input_path=input_path,
                markdown=md,
                char_count=len(md),
            )

            if output_path:
                output_dir = os.path.dirname(output_path)
                if output_dir and not os.path.exists(output_dir):
                    return _err(f"Output directory does not exist: {output_dir}", error_type="FileNotFoundError")
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(md)
                result["output_path"] = output_path

            return result

        if action == "from_arxiv":
            if not arxiv_id:
                return _err("arxiv_id is required (e.g. '2005.11401')")

            # Validate arxiv_id format (basic check)
            arxiv_id = arxiv_id.strip()
            if not re.match(r"^[\d.]+[vV]?\d*$", arxiv_id):
                return _err(f"Invalid arxiv_id format: {arxiv_id}. Expected format like '2005.11401' or '2005.11401v2'")

            import requests

            # Try ar5iv HTML first
            ar5iv_url = f"https://ar5iv.labs.arxiv.org/html/{arxiv_id}"
            md = None
            source = None

            try:
                resp = requests.get(ar5iv_url, timeout=30)
                if resp.status_code == 200 and len(resp.text) > 500:
                    md = _html_to_markdown(resp.text)
                    source = "ar5iv"
            except Exception:
                pass

            # Fallback to PDF download + convert
            if not md or len(md) < 100:
                if err := _check_pymupdf4llm():
                    return err

                pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
                try:
                    resp = requests.get(pdf_url, timeout=60)
                    if resp.status_code != 200:
                        return _err(f"Failed to download arxiv PDF: HTTP {resp.status_code}", error_type="DownloadError")
                except Exception as e:
                    return _err(f"Failed to download arxiv PDF: {e}", error_type="DownloadError")

                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    tmp.write(resp.content)
                    tmp_path = tmp.name

                try:
                    md = pymupdf4llm.to_markdown(tmp_path)
                    source = "pdf"
                finally:
                    os.unlink(tmp_path)

            result = _ok(
                action="from_arxiv",
                arxiv_id=arxiv_id,
                source=source,
                markdown=md,
                char_count=len(md),
            )

            if output_path:
                output_dir = os.path.dirname(output_path)
                if output_dir and not os.path.exists(output_dir):
                    return _err(f"Output directory does not exist: {output_dir}", error_type="FileNotFoundError")
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(md)
                result["output_path"] = output_path

            return result

        return _err(
            f"Unknown action: {action}",
            error_type="InvalidAction",
            available_actions=["convert", "from_arxiv"],
        )

    except Exception as e:
        return _err(str(e), error_type=type(e).__name__, action=action)
