"""Tests for the gold chunker. No Spark and no network: tiktoken is replaced by a word count."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "gold"))

import text_split  # noqa: E402
from chunking import Settings, chunk, prefix  # noqa: E402
from elements import clean, doc_meta, heading_level  # noqa: E402
from sections import sections  # noqa: E402
from tables import pieces, render, table_rows  # noqa: E402


def words(text):
    return len(text.split())


@pytest.fixture(autouse=True)
def word_tokens(monkeypatch):
    monkeypatch.setattr(text_split, "count_tokens", words)


def el(page, type_, content):
    return {"page_no": page, "type": type_, "content": content}


def table(*rows, head="th"):
    cells = lambda r, tag: "".join(f"<{tag}>{c}</{tag}>" for c in r)  # noqa: E731
    first, *rest = rows
    return "<table><tr>" + cells(first, head) + "</tr>" + "".join(f"<tr>{cells(r, 'td')}</tr>" for r in rest) + "</table>"


INCOME = table(["", "2022", "2021"], ["Revenue", "66,608", "62,286"], ["Operating income", "(3,547)", "(2,902)"])


# --- elements ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("path, expected", [
    ("/Volumes/x/pdfs/BOEING_2022_10K.pdf", ("BOEING", "2022", "10K")),
    ("PEPSICO_2022Q1_10Q.pdf", ("PEPSICO", "2022Q1", "10Q")),
    ("JOHNSON_&_JOHNSON_2022_10K.pdf", ("JOHNSON & JOHNSON", "2022", "10K")),
    ("INTEL_2023_8K_dated-2023-02-10.pdf", ("INTEL", "2023", "8K")),
    ("AMCOR_2023Q4_EARNINGS.pdf", ("AMCOR", "2023Q4", "EARNINGS")),
    ("3M_2018_10K.pdf", ("3M", "2018", "10K")),
    ("ODD.pdf", ("ODD", "", "")),
])
def test_doc_meta(path, expected):
    assert doc_meta(path) == expected


def test_clean_drops_noise_and_empty_elements():
    out = clean([el(1, "page_header", "Boeing"), el(1, "text", "  Revenue grew.  "), el(1, "page_number", "17"),
                 el(1, "figure", "BOEING"), el(1, "text", "   "), el(2, "page_footer", "Annual report")])
    assert out == [el(1, "text", "Revenue grew.")]


@pytest.mark.parametrize("type_, text, level", [
    ("section_header", "PART II", 0), ("title", "Item 7. Management's Discussion", 1), ("section_header", "Item 1A.", 1),
    ("section_header", "Liquidity", 2), ("text", "Item 7 is discussed below", None),
    # the parser typed a short Item line as text (AmericanWaterWorks 2022): still an Item heading
    ("text", "ITEM 6. [RESERVED]", 1), ("text", "Item 9A. - Controls and Procedures", 1),
    # but a paragraph that starts like one is not a heading
    ("text", "Item 7. " + "The discussion that follows explains the results. " * 5, None),
])
def test_heading_level(type_, text, level):
    assert heading_level(el(1, type_, text)) == level


def test_clean_strips_the_html_the_parser_puts_around_headings():
    # CORNING 2020: the heading came as <u>Item 1. Business</u>, which a regex for "Item" at the start would miss
    out = clean([el(2, "section_header", "<u>Item 1. Business</u>"), el(2, "text", "Keep <b>tags</b> in text")])
    assert [e["content"] for e in out] == ["Item 1. Business", "Keep <b>tags</b> in text"]
    assert heading_level(out[0]) == 1


# --- tables -----------------------------------------------------------------------------------------------

def test_table_rows_and_colspan():
    rows = table_rows('<table><tr><th colspan="2">Years</th><th>Note</th></tr><tr><td>1<br>2</td><td>3</td><td></td></tr></table>')
    assert rows == [["Years", "", "Note"], ["1 2", "3", ""]]


def test_table_rows_of_text_that_is_not_html():
    assert table_rows("Revenue 100") == []


def test_render_puts_the_lead_on_top():
    text = render(table_rows(INCOME), "(in millions)")
    assert text.splitlines()[0] == "(in millions)"
    assert "| Operating income | (3,547) | (2,902) |" in text


def test_pieces_repeat_lead_and_header():
    rows = [["", "2022"]] + [[f"Line {i}", str(i)] for i in range(20)]
    out = pieces(rows, "(in millions)", 30, words)
    assert len(out) > 1
    for p in out:
        assert p.startswith("(in millions)\n|  | 2022 |")
    assert sum(p.count("| Line ") for p in out) == 20  # every row once


# --- sections ---------------------------------------------------------------------------------------------

def test_item_heading_always_starts_a_section_and_small_headings_merge():
    els = clean([
        el(1, "section_header", "PART II"), el(1, "section_header", "Item 7. MD&A"), el(1, "text", "Short intro."),
        el(1, "section_header", "Overview"), el(1, "text", "Also short."),
        el(2, "section_header", "Item 8. Financial Statements"), el(2, "text", "Statements follow."),
    ])
    out = sections(els, words, min_tokens=100)
    # "PART II" alone is no section: it is only in the heading path of what follows
    assert [s["heading_path"] for s in out] == ["PART II > Item 7. MD&A", "PART II > Item 8. Financial Statements"]
    assert [e["content"] for e in out[0]["elements"]] == ["Item 7. MD&A", "Short intro.", "Overview", "Also short."]


def test_small_heading_starts_a_section_when_the_current_one_is_big():
    els = clean([el(1, "section_header", "Item 7. MD&A"), el(1, "text", "word " * 150),
                 el(2, "section_header", "Liquidity"), el(2, "text", "Cash.")])
    out = sections(els, words, min_tokens=100)
    assert [s["heading_path"] for s in out] == ["Item 7. MD&A", "Item 7. MD&A > Liquidity"]


def test_table_is_alone_and_takes_its_units_line():
    els = clean([el(5, "section_header", "Item 8"), el(5, "text", "Long paragraph " * 20),
                 el(5, "text", "(in millions)"), el(5, "table", INCOME), el(5, "text", "After the table.")])
    out = sections(els, words)
    assert [s["kind"] for s in out] == ["text", "table", "text"]
    assert out[1]["lead"] == "(in millions)"
    assert out[1]["heading_path"] == "Item 8"
    assert all(e["content"] != "(in millions)" for e in out[0]["elements"])


def test_table_continued_on_the_next_page_is_merged():
    more = table(["", "2022", "2021"], ["Net income", "(5,053)", "(4,202)"])  # the header repeated on page 6
    els = clean([el(5, "table", INCOME), el(6, "page_header", "Boeing"), el(6, "table", more)])
    out = sections(els, words)
    assert len(out) == 1
    assert out[0]["pages"] == [5, 6]
    assert [r[0] for r in out[0]["rows"]] == ["", "Revenue", "Operating income", "Net income"]


def test_tables_with_text_between_are_not_merged():
    els = clean([el(5, "table", INCOME), el(6, "text", "Statement of cash flows"), el(6, "table", INCOME)])
    out = sections(els, words)
    assert [s["kind"] for s in out] == ["table", "table"]
    assert out[1]["lead"] == "Statement of cash flows" and out[1]["pages"] == [6]


# --- chunking ---------------------------------------------------------------------------------------------

PATH = "/Volumes/w/s/docs/pdfs/BOEING_2022_10K.pdf"


def filing():
    return [
        el(1, "page_header", "Boeing"), el(1, "section_header", "Item 7. MD&A"),
        el(1, "text", "Revenue increased because of deliveries. " * 40),
        el(2, "text", "Liquidity remained strong. " * 40),
        el(3, "section_header", "Item 8. Financial Statements"), el(3, "text", "(in millions)"), el(3, "table", INCOME),
    ]


def test_structured_children_point_to_parents_with_their_text():
    parents, children = chunk(PATH, filing(), "structured", Settings(parent_tokens=300, child_tokens=60, child_overlap=10))
    by_id = {p["parent_id"]: p for p in parents}
    assert children and all(c["parent_id"] in by_id for c in children)
    for c in children:
        assert c["parent_text"] == by_id[c["parent_id"]]["text"]
        assert c["embed_text"].startswith(prefix(("BOEING", "2022", "10K"), c["heading_path"]) + "\n\n")
        assert c["strategy"] == "structured"
    assert len({c["chunk_id"] for c in children}) == len(children)


def test_structured_parents_respect_the_budget_and_know_their_pages():
    parents, _ = chunk(PATH, filing(), "structured", Settings(parent_tokens=300))
    text = [p for p in parents if p["chunk_type"] == "text"]
    assert all(p["n_tokens"] <= 300 for p in text)
    assert (text[0]["page_start"], text[0]["page_end"]) == (1, 1)
    assert text[-1]["page_end"] == 2


def test_structured_table_is_one_parent_with_its_units():
    parents, children = chunk(PATH, filing(), "structured")
    tables = [p for p in parents if p["chunk_type"] == "table"]
    assert len(tables) == 1
    assert tables[0]["text"].startswith("(in millions)\n")
    assert tables[0]["heading_path"] == "Item 8. Financial Statements"
    assert (tables[0]["page_start"], tables[0]["page_end"]) == (3, 3)
    assert all("(3,547)" in c["parent_text"] for c in children if c["chunk_type"] == "table")


def test_fixed_has_no_parents_and_pages_per_chunk():
    parents, children = chunk(PATH, filing(), "fixed", Settings(fixed_tokens=150, fixed_overlap=10))
    assert parents == []
    assert len(children) > 1
    for c in children:
        assert c["parent_id"] is None and c["parent_text"] == c["text"] and c["strategy"] == "fixed"
        assert c["n_tokens"] <= 150
        assert 1 <= c["page_start"] <= c["page_end"] <= 3
    assert children[0]["page_start"] == 1 and children[-1]["page_end"] == 3
    assert "Boeing" not in " ".join(c["text"] for c in children)  # the page header is noise


def test_chunk_ids_are_stable_across_runs():
    assert [c["chunk_id"] for c in chunk(PATH, filing(), "structured")[1]] == \
           [c["chunk_id"] for c in chunk(PATH, filing(), "structured")[1]]


def test_empty_filing_and_unknown_strategy():
    assert chunk(PATH, [el(1, "page_number", "1")], "fixed") == ([], [])
    assert chunk(PATH, [], "structured") == ([], [])
    with pytest.raises(ValueError):
        chunk(PATH, filing(), "semantic")
