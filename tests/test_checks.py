"""Tests for the checks on parser and model output. No Spark needed: run `pytest` from the repository root."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "silver"))

from checks import check_parse, clean_page, content_pages, page_id  # noqa: E402


def element(page, content="text"):
    return {"type": "text", "content": content, "bbox": [{"page_id": page, "coord": [0, 0, 1, 1]}]}


def doc(elements, errors=None, pages=3):
    return {"document": {"elements": elements, "pages": [{}] * pages}, "error_status": errors}


# --- check_parse -----------------------------------------------------------------------------------------

def test_complete_parse_is_good():
    assert check_parse(doc([element(0), element(1)])) is None


def test_empty_error_list_is_good():
    assert check_parse(doc([element(0)], errors=[])) is None


def test_page_errors_make_the_parse_bad_and_retryable():
    errors = [{"error_message": "Request rate limit exceeded. Please try again later.", "page_id": 1}] * 3
    reason, retryable = check_parse(doc([element(0)], errors=errors))
    assert retryable
    assert reason.startswith("3 pages failed")
    assert "rate limit" in reason


def test_internal_error_is_retryable():
    _, retryable = check_parse(doc([element(0)], errors=[{"error_message": "Internal error.", "page_id": 2}]))
    assert retryable


def test_pdf_over_the_page_limit_is_not_retryable():
    errors = [{"error_message": "Document has 549 pages, which exceeds the limit of 500.", "page_id": 0}]
    reason, retryable = check_parse(doc([], errors=errors))
    assert not retryable
    assert "549 pages" in reason


def test_failed_conversion_is_not_retryable():
    _, retryable = check_parse(doc([], errors=[{"error_message": "Document conversion failed.", "page_id": 0}]))
    assert not retryable


def test_no_elements_and_no_error_is_retryable():
    reason, retryable = check_parse(doc([]))
    assert reason == "no elements"
    assert retryable


# --- pages -----------------------------------------------------------------------------------------------

def test_page_id_defaults_to_page_zero_without_a_box():
    assert page_id({"type": "figure", "content": "logo"}) == 0
    assert page_id(element(4)) == 4


def test_content_pages_counts_distinct_pages():
    assert content_pages(doc([element(0), element(0), element(2), element(5)])) == 3


# --- clean_page ------------------------------------------------------------------------------------------

def test_clean_page_removes_a_page_marker_the_model_wrote():
    assert clean_page("<!-- page 16 -->\n# Credit\n\ntext\n\n<!-- page 17 -->") == "# Credit\n\ntext"


def test_clean_page_keeps_normal_text_and_tables():
    text = "# Title\n\n| a | b |\n| --- | --- |\n| 1 | 2 |"
    assert clean_page(text) == text


def test_clean_page_of_nothing_is_empty():
    assert clean_page(None) == ""
    assert clean_page("   \n ") == ""
    assert clean_page("<!-- page 3 -->") == ""
