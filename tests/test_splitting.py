"""Tests for cutting a PDF into parts. No Spark needed: run `pytest` from the repository root."""

import sys
from io import BytesIO
from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "bronze"))

from splitting import part_ranges, split_pdf  # noqa: E402


# --- splitting -------------------------------------------------------------------------------------------

def test_a_short_pdf_is_one_part():
    assert part_ranges(50, 50) == [(1, 0, 50)]
    assert part_ranges(3, 50) == [(1, 0, 3)]


def test_a_long_pdf_is_cut_into_parts_of_the_size():
    assert part_ranges(155, 50) == [(1, 0, 50), (2, 50, 100), (3, 100, 150), (4, 150, 155)]


def test_the_parts_cover_every_page_once():
    for pages in (1, 49, 50, 51, 100, 101, 667):
        ranges = part_ranges(pages, 50)
        assert ranges[0][1] == 0 and ranges[-1][2] == pages
        assert all(a[2] == b[1] for a, b in zip(ranges, ranges[1:]))
        assert all(end - start <= 50 for _, start, end in ranges)


def test_no_size_means_one_part():
    assert part_ranges(667, None) == [(1, 0, 667)]
    assert part_ranges(667, 0) == [(1, 0, 667)]


def blank_pdf(pages):
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=72, height=72)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_a_short_pdf_is_one_part_with_its_own_bytes():
    content = blank_pdf(3)
    assert split_pdf(content, 50) == [(1, 0, 3, content)]


def test_a_long_pdf_is_cut_into_readable_parts():
    parts = split_pdf(blank_pdf(7), 3)
    assert [(n, offset, pages) for n, offset, pages, _ in parts] == [(1, 0, 3), (2, 3, 3), (3, 6, 1)]
    assert [len(PdfReader(BytesIO(b)).pages) for *_, b in parts] == [3, 3, 1]


def test_a_pdf_that_cannot_be_read_fails():
    with pytest.raises(Exception):
        split_pdf(b"not a pdf", 50)
