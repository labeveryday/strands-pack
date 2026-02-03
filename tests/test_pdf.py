"""Tests for PDF tool."""

import os
import tempfile

import pytest


@pytest.fixture
def test_pdf_path():
    """Create a simple test PDF."""
    try:
        import fitz
    except ImportError:
        pytest.skip("PyMuPDF not installed")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        doc = fitz.open()
        # Add 3 pages with text
        for i in range(3):
            page = doc.new_page()
            page.insert_text((50, 50), f"Page {i + 1} content")
        doc.save(f.name)
        doc.close()
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def test_pdf_path_2():
    """Create a second test PDF for merge tests."""
    try:
        import fitz
    except ImportError:
        pytest.skip("PyMuPDF not installed")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        doc = fitz.open()
        for i in range(2):
            page = doc.new_page()
            page.insert_text((50, 50), f"Doc 2 Page {i + 1}")
        doc.save(f.name)
        doc.close()
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def output_dir():
    """Create a temp directory for output files."""
    with tempfile.TemporaryDirectory() as d:
        yield d


def test_pdf_get_info(test_pdf_path):
    """Test getting PDF info."""
    from strands_pack import pdf

    result = pdf(action="get_info", input_path=test_pdf_path)

    assert result["success"] is True
    assert result["action"] == "get_info"
    assert result["page_count"] == 3
    assert "file_size_bytes" in result
    assert "metadata" in result
    assert "page_dimensions" in result


def test_pdf_extract_text(test_pdf_path):
    """Test extracting text from PDF."""
    from strands_pack import pdf

    result = pdf(action="extract_text", input_path=test_pdf_path)

    assert result["success"] is True
    assert result["action"] == "extract_text"
    assert result["total_pages"] == 3
    assert result["pages_extracted"] == 3
    assert len(result["content"]) == 3
    assert "Page 1 content" in result["content"][0]["text"]


def test_pdf_extract_text_specific_pages(test_pdf_path):
    """Test extracting text from specific pages."""
    from strands_pack import pdf

    result = pdf(action="extract_text", input_path=test_pdf_path, pages=[0, 2])

    assert result["success"] is True
    assert result["pages_extracted"] == 2
    assert result["content"][0]["page"] == 0
    assert result["content"][1]["page"] == 2


def test_pdf_extract_pages(test_pdf_path, output_dir):
    """Test extracting pages to new PDF."""
    from strands_pack import pdf

    output_path = os.path.join(output_dir, "extracted.pdf")
    result = pdf(
        action="extract_pages",
        input_path=test_pdf_path,
        output_path=output_path,
        pages=[0, 2]
    )

    assert result["success"] is True
    assert result["action"] == "extract_pages"
    assert result["pages_count"] == 2
    assert os.path.exists(output_path)


def test_pdf_delete_pages(test_pdf_path, output_dir):
    """Test deleting pages from PDF."""
    from strands_pack import pdf

    output_path = os.path.join(output_dir, "deleted.pdf")
    result = pdf(
        action="delete_pages",
        input_path=test_pdf_path,
        output_path=output_path,
        pages=[1],  # remove middle page
    )

    assert result["success"] is True
    assert result["action"] == "delete_pages"
    assert result["pages_deleted"] == 1
    assert result["pages_remaining"] == 2
    assert os.path.exists(output_path)

    # Verify output has 2 pages
    try:
        import fitz
    except ImportError:
        pytest.skip("PyMuPDF not installed")
    doc = fitz.open(output_path)
    assert len(doc) == 2
    doc.close()


def test_pdf_merge(test_pdf_path, test_pdf_path_2, output_dir):
    """Test merging PDFs."""
    from strands_pack import pdf

    output_path = os.path.join(output_dir, "merged.pdf")
    result = pdf(
        action="merge",
        input_paths=[test_pdf_path, test_pdf_path_2],
        output_path=output_path
    )

    assert result["success"] is True
    assert result["action"] == "merge"
    assert result["files_merged"] == 2
    assert result["total_pages"] == 5  # 3 + 2
    assert os.path.exists(output_path)


def test_pdf_split(test_pdf_path, output_dir):
    """Test splitting PDF into individual pages."""
    from strands_pack import pdf

    result = pdf(
        action="split",
        input_path=test_pdf_path,
        output_dir=output_dir,
        pages_per_file=1
    )

    assert result["success"] is True
    assert result["action"] == "split"
    assert result["files_created"] == 3
    assert len(result["output_files"]) == 3


def test_pdf_split_multiple_pages_per_file(test_pdf_path, output_dir):
    """Test splitting with multiple pages per file."""
    from strands_pack import pdf

    result = pdf(
        action="split",
        input_path=test_pdf_path,
        output_dir=output_dir,
        pages_per_file=2
    )

    assert result["success"] is True
    assert result["files_created"] == 2  # 3 pages / 2 = 2 files


def test_pdf_rotate_pages(test_pdf_path, output_dir):
    """Test rotating pages."""
    from strands_pack import pdf

    output_path = os.path.join(output_dir, "rotated.pdf")
    result = pdf(
        action="rotate_pages",
        input_path=test_pdf_path,
        output_path=output_path,
        angle=90
    )

    assert result["success"] is True
    assert result["action"] == "rotate_pages"
    assert result["angle"] == 90
    assert len(result["pages_rotated"]) == 3
    assert os.path.exists(output_path)


def test_pdf_rotate_specific_pages(test_pdf_path, output_dir):
    """Test rotating specific pages."""
    from strands_pack import pdf

    output_path = os.path.join(output_dir, "rotated.pdf")
    result = pdf(
        action="rotate_pages",
        input_path=test_pdf_path,
        output_path=output_path,
        angle=180,
        pages=[0, 2]
    )

    assert result["success"] is True
    assert result["pages_rotated"] == [0, 2]


def test_pdf_to_images(test_pdf_path, output_dir):
    """Test converting pages to images."""
    from strands_pack import pdf

    result = pdf(
        action="to_images",
        input_path=test_pdf_path,
        output_dir=output_dir,
        output_format="png",
        dpi=72
    )

    assert result["success"] is True
    assert result["action"] == "to_images"
    assert result["pages_converted"] == 3
    assert len(result["output_files"]) == 3
    # Check files exist
    for file_info in result["output_files"]:
        assert os.path.exists(file_info["file"])


def test_pdf_to_images_specific_pages(test_pdf_path, output_dir):
    """Test converting specific pages to images."""
    from strands_pack import pdf

    result = pdf(
        action="to_images",
        input_path=test_pdf_path,
        output_dir=output_dir,
        pages=[0, 2]
    )

    assert result["success"] is True
    assert result["pages_converted"] == 2


def test_pdf_add_watermark(test_pdf_path, output_dir):
    """Test adding watermark."""
    from strands_pack import pdf

    output_path = os.path.join(output_dir, "watermarked.pdf")
    result = pdf(
        action="add_watermark",
        input_path=test_pdf_path,
        output_path=output_path,
        text="CONFIDENTIAL",
        position="center"
    )

    assert result["success"] is True
    assert result["action"] == "add_watermark"
    assert result["text"] == "CONFIDENTIAL"
    assert result["pages_watermarked"] == 3
    assert os.path.exists(output_path)


def test_pdf_missing_input():
    """Test error when input file is missing."""
    from strands_pack import pdf

    result = pdf(action="get_info", input_path="/nonexistent/file.pdf")

    assert result["success"] is False
    assert "not found" in result["error"]


def test_pdf_unknown_action():
    """Test error for unknown action."""
    from strands_pack import pdf

    result = pdf(action="unknown_action")

    assert result["success"] is False
    assert "Unknown action" in result["error"]
    assert "available_actions" in result


def test_pdf_extract_pages_missing_pages(test_pdf_path, output_dir):
    """Test error when pages param is missing."""
    from strands_pack import pdf

    output_path = os.path.join(output_dir, "extracted.pdf")
    result = pdf(
        action="extract_pages",
        input_path=test_pdf_path,
        output_path=output_path
    )

    assert result["success"] is False
    assert "pages" in result["error"]


def test_pdf_merge_missing_input_paths(output_dir):
    """Test error when input_paths is missing."""
    from strands_pack import pdf

    output_path = os.path.join(output_dir, "merged.pdf")
    result = pdf(action="merge", output_path=output_path)

    assert result["success"] is False
    assert "input_paths" in result["error"]


def test_pdf_rotate_invalid_angle(test_pdf_path, output_dir):
    """Test error for invalid rotation angle."""
    from strands_pack import pdf

    output_path = os.path.join(output_dir, "rotated.pdf")
    result = pdf(
        action="rotate_pages",
        input_path=test_pdf_path,
        output_path=output_path,
        angle=45
    )

    assert result["success"] is False
    assert "angle" in result["error"]


def test_pdf_add_watermark_missing_text(test_pdf_path, output_dir):
    """Test error when watermark text is missing."""
    from strands_pack import pdf

    output_path = os.path.join(output_dir, "watermarked.pdf")
    result = pdf(
        action="add_watermark",
        input_path=test_pdf_path,
        output_path=output_path
    )

    assert result["success"] is False
    assert "text" in result["error"]


def test_pdf_search_text(test_pdf_path):
    """Test searching for text in PDF."""
    from strands_pack import pdf

    result = pdf(action="search_text", input_path=test_pdf_path, query="Page")

    assert result["success"] is True
    assert result["action"] == "search_text"
    assert result["query"] == "Page"
    assert result["pages_with_matches"] == 3
    assert result["total_matches"] == 3


def test_pdf_search_text_no_results(test_pdf_path):
    """Test searching for text not in PDF."""
    from strands_pack import pdf

    result = pdf(action="search_text", input_path=test_pdf_path, query="nonexistent")

    assert result["success"] is True
    assert result["total_matches"] == 0


def test_pdf_add_page_numbers(test_pdf_path, output_dir):
    """Test adding page numbers to PDF."""
    from strands_pack import pdf

    output_path = os.path.join(output_dir, "numbered.pdf")
    result = pdf(
        action="add_page_numbers",
        input_path=test_pdf_path,
        output_path=output_path,
        position="bottom-center"
    )

    assert result["success"] is True
    assert result["action"] == "add_page_numbers"
    assert result["pages_numbered"] == 3
    assert os.path.exists(output_path)
