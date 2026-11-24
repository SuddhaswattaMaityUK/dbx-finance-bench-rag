"""The parser's elements of one PDF, cleaned for chunking. Plain Python, tested in tests/test_gold.py.

An element is a dict with `page_no` (the real PDF page, 1-based), `type` and `content`, in reading order.
The notebook reads them from `silver_parsed` (one row per element, see `chunk_documents.ipynb`).
"""

import re

# Repeat on every page and say nothing about the filing: they only pollute the embeddings.
NOISE = {"page_header", "page_footer", "page_number", "figure"}
HEADINGS = {"title", "section_header"}
TABLE = "table"

PART = re.compile(r"^\s*part\s+[ivx]+\b", re.I)            # PART II
ITEM = re.compile(r"^\s*item\s+\d+[a-z]?\b", re.I)         # Item 7, Item 1A
ITEM_LINE = re.compile(r"^\s*item\s+\d+[a-c]?\s*[.\-–—:]", re.I)  # "Item 6. [RESERVED]": an Item line, not a sentence
PERIOD = re.compile(r"\d{4}(Q[1-4])?")                     # 2022, 2023Q2
TAGS = re.compile(r"<[^>]+>")                              # the parser wraps some headings: <u>Item 1. Business</u>
MAX_ITEM_LINE = 150                                        # longer text that starts with "Item 7." is a paragraph


def doc_meta(path):
    """File name -> (company, fiscal_period, doc_type). BOEING_2022_10K.pdf -> ('BOEING', '2022', '10K')."""
    name = path.rsplit("/", 1)[-1]
    name = name[:-4] if name.lower().endswith(".pdf") else name
    parts = name.split("_")
    i = next((k for k, p in enumerate(parts) if PERIOD.fullmatch(p)), None)
    if i is None:
        return name, "", ""
    return " ".join(parts[:i]), parts[i], (parts[i + 1] if i + 1 < len(parts) else "")


def clean(elements):
    """Drop the noise and the empty elements, and strip the text. Keeps the order.

    The text of a heading loses the HTML tags the parser sometimes puts around it (checked against the PDFs:
    19 of 176 Item headings were `<u>Item 1. Business</u>`), so the PART / Item rules and heading_path see plain text."""
    out = []
    for e in elements:
        text = (e.get("content") or "").strip()
        if e.get("type") in HEADINGS:
            text = " ".join(TAGS.sub(" ", text).split())
        if e.get("type") in NOISE or not text:
            continue
        out.append({"page_no": e["page_no"], "type": e.get("type") or "text", "content": text})
    return out


def heading_level(element):
    """0 for PART, 1 for Item, 2 for any other heading, None if the element is not a heading.

    A short `text` element that is an Item line ("ITEM 6. [RESERVED]") is an Item heading too: the parser typed 4 of
    176 Item headings as text. A sentence that only starts with the word ("Item 7 is discussed below") is not."""
    text = element["content"]
    if element["type"] == "text":
        return 1 if len(text) <= MAX_ITEM_LINE and ITEM_LINE.match(text) else None
    if element["type"] not in HEADINGS:
        return None
    if PART.match(text):
        return 0
    if ITEM.match(text):
        return 1
    return 2


def is_major(level):
    """PART and Item headings always start a new section."""
    return level is not None and level <= 1
