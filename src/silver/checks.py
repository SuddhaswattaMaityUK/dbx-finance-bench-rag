"""Checks on parser output.

Plain Python, no Spark: easy to read, and tested in tests/test_checks.py.
"""

import re

# Parser errors that retrying cannot fix.
PERMANENT = re.compile(r"exceeds the limit|conversion failed", re.I)


def page_id(element):
    """0-based PDF page of a parsed element (page 0 if it has no box)."""
    boxes = element.get("bbox") or [{"page_id": 0}]
    return boxes[0]["page_id"]


def content_pages(doc):
    """Number of PDF pages that have at least one parsed element."""
    return len({page_id(e) for e in doc["document"]["elements"]})


def check_parse(doc):
    """Is the parse of a PDF complete? Returns None if so, else (reason, retryable)."""
    errors = doc.get("error_status") or []
    if not doc["document"]["elements"]:
        reason = errors[0]["error_message"] if errors else "no elements"
        return reason, not PERMANENT.search(reason)
    if errors:
        return f"{len(errors)} pages failed: {errors[0]['error_message']}", True
    return None
