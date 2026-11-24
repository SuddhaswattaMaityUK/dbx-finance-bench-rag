"""Tests for cutting a PDF into parts. No Spark needed: run `pytest` from the repository root."""

import sys
from pathlib import Path

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


def test_a_pdf_that_cannot_be_read_is_one_part_with_its_bytes():
    assert split_pdf(b"not a pdf", 50) == [(1, 0, None, b"not a pdf")]
