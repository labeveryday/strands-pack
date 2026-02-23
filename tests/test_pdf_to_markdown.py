"""Tests for pdf_to_markdown tool."""

import os
import tempfile

import pytest

try:
    import fitz  # PyMuPDF

    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    import pymupdf4llm

    HAS_PYMUPDF4LLM = True
except ImportError:
    HAS_PYMUPDF4LLM = False


@pytest.fixture
def test_pdf(tmp_path):
    """Create a multi-page test PDF with headers and paragraphs."""
    if not HAS_PYMUPDF:
        pytest.skip("pymupdf not installed")

    pdf_path = str(tmp_path / "test.pdf")
    doc = fitz.open()

    # Page 1
    page1 = doc.new_page()
    page1.insert_text((72, 72), "Introduction", fontsize=20)
    page1.insert_text((72, 120), "This is the first paragraph of the test document.", fontsize=12)
    page1.insert_text((72, 140), "It contains multiple lines of text for testing.", fontsize=12)

    # Page 2
    page2 = doc.new_page()
    page2.insert_text((72, 72), "Methods", fontsize=20)
    page2.insert_text((72, 120), "This section describes the methodology used.", fontsize=12)
    page2.insert_text((72, 140), "We applied BM25 keyword search for retrieval.", fontsize=12)

    # Page 3
    page3 = doc.new_page()
    page3.insert_text((72, 72), "Results", fontsize=20)
    page3.insert_text((72, 120), "The results show significant improvement.", fontsize=12)

    doc.save(pdf_path)
    doc.close()
    return pdf_path


def test_convert_basic(test_pdf):
    """Test basic PDF to markdown conversion."""
    if not HAS_PYMUPDF4LLM:
        pytest.skip("pymupdf4llm not installed")

    from strands_pack.pdf_to_markdown import pdf_to_markdown

    result = pdf_to_markdown(action="convert", input_path=test_pdf)

    assert result["success"] is True
    assert result["action"] == "convert"
    assert "markdown" in result
    assert result["char_count"] > 0
    assert "Introduction" in result["markdown"]
    assert "first paragraph" in result["markdown"]


def test_convert_specific_pages(test_pdf):
    """Test converting only specific pages."""
    if not HAS_PYMUPDF4LLM:
        pytest.skip("pymupdf4llm not installed")

    from strands_pack.pdf_to_markdown import pdf_to_markdown

    result = pdf_to_markdown(action="convert", input_path=test_pdf, pages=[0])

    assert result["success"] is True
    assert "Introduction" in result["markdown"]
    # Page 2 content should not be present
    assert "Methods" not in result["markdown"]


def test_convert_output_to_file(test_pdf, tmp_path):
    """Test writing markdown output to a file."""
    if not HAS_PYMUPDF4LLM:
        pytest.skip("pymupdf4llm not installed")

    from strands_pack.pdf_to_markdown import pdf_to_markdown

    output_file = str(tmp_path / "output.md")
    result = pdf_to_markdown(action="convert", input_path=test_pdf, output_path=output_file)

    assert result["success"] is True
    assert result["output_path"] == output_file
    assert os.path.exists(output_file)
    with open(output_file, "r") as f:
        content = f.read()
    assert "Introduction" in content


def test_convert_missing_file():
    """Test error when input file doesn't exist."""
    if not HAS_PYMUPDF4LLM:
        pytest.skip("pymupdf4llm not installed")

    from strands_pack.pdf_to_markdown import pdf_to_markdown

    result = pdf_to_markdown(action="convert", input_path="/nonexistent/file.pdf")

    assert result["success"] is False
    assert "not found" in result["error"].lower() or "FileNotFoundError" in result.get("error_type", "")


def test_convert_missing_input_path():
    """Test error when input_path not provided."""
    from strands_pack.pdf_to_markdown import pdf_to_markdown

    result = pdf_to_markdown(action="convert")

    assert result["success"] is False
    assert "input_path" in result["error"]


def test_from_arxiv_success(monkeypatch):
    """Test from_arxiv with mocked ar5iv response."""
    import requests as requests_mod

    from strands_pack.pdf_to_markdown import pdf_to_markdown

    mock_html = """
    <html><body>
    <article>
        <h1>Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks</h1>
        <p>We explore a general-purpose fine-tuning recipe for retrieval-augmented generation (RAG)
        models. We combine pre-trained parametric and non-parametric memory for language generation.</p>
        <h2>Introduction</h2>
        <p>Large pre-trained language models have been shown to store factual knowledge in their
        parameters and achieve state-of-the-art results when fine-tuned on downstream NLP tasks.
        However, their ability to access and precisely manipulate knowledge is still limited.</p>
        <h2>Methods</h2>
        <p>Our approach combines a pre-trained sequence-to-sequence model with a dense retrieval
        component that provides access to a non-parametric external knowledge source.</p>
    </article>
    </body></html>
    """

    class MockResponse:
        status_code = 200
        text = mock_html

    def mock_get(url, timeout=None):
        return MockResponse()

    monkeypatch.setattr(requests_mod, "get", mock_get)

    result = pdf_to_markdown(action="from_arxiv", arxiv_id="2005.11401")

    assert result["success"] is True, f"Expected success but got: {result}"
    assert result["action"] == "from_arxiv"
    assert result["source"] == "ar5iv"
    assert "markdown" in result
    assert result["char_count"] > 0
    assert "Retrieval" in result["markdown"]


def test_from_arxiv_fallback(monkeypatch, tmp_path):
    """Test from_arxiv falls back to PDF when ar5iv returns 404."""
    if not HAS_PYMUPDF4LLM:
        pytest.skip("pymupdf4llm not installed")
    if not HAS_PYMUPDF:
        pytest.skip("pymupdf not installed")

    from strands_pack.pdf_to_markdown import pdf_to_markdown

    # Create a real PDF for fallback
    pdf_path = str(tmp_path / "fake_arxiv.pdf")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Fallback PDF Content", fontsize=16)
    doc.save(pdf_path)
    doc.close()
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    call_count = {"n": 0}

    class Mock404:
        status_code = 404
        text = ""

    class MockPDF:
        status_code = 200
        content = pdf_bytes

    def mock_get(url, timeout=None):
        call_count["n"] += 1
        if "ar5iv" in url:
            return Mock404()
        return MockPDF()

    import requests
    monkeypatch.setattr(requests, "get", mock_get)

    result = pdf_to_markdown(action="from_arxiv", arxiv_id="2005.11401")

    assert result["success"] is True
    assert result["source"] == "pdf"
    assert "markdown" in result
    assert result["char_count"] > 0


def test_from_arxiv_invalid_id():
    """Test error for invalid arxiv ID."""
    from strands_pack.pdf_to_markdown import pdf_to_markdown

    result = pdf_to_markdown(action="from_arxiv", arxiv_id="not-a-valid-id!")

    assert result["success"] is False
    assert "invalid" in result["error"].lower() or "format" in result["error"].lower()


def test_from_arxiv_missing_id():
    """Test error when arxiv_id not provided."""
    from strands_pack.pdf_to_markdown import pdf_to_markdown

    result = pdf_to_markdown(action="from_arxiv")

    assert result["success"] is False
    assert "arxiv_id" in result["error"]


def test_unknown_action():
    """Test error for unknown action."""
    from strands_pack.pdf_to_markdown import pdf_to_markdown

    result = pdf_to_markdown(action="unknown_action")

    assert result["success"] is False
    assert "Unknown action" in result["error"]
    assert "available_actions" in result
