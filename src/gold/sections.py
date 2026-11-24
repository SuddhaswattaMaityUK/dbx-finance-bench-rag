"""Cleaned elements -> sections (text under one heading) and tables, each with its heading path and pages."""

from elements import TABLE, heading_level, is_major
from tables import table_rows


def heading_path(stack):
    return " > ".join(text for _, text in stack)


def push_heading(stack, level, text):
    """A heading replaces the headings at its level or below: Item 8 replaces Item 7 and its subheadings."""
    while stack and stack[-1][0] >= level:
        stack.pop()
    stack.append((level, text[:150]))


def sections(elements, count, min_tokens=100, lead_tokens=60):
    """Group cleaned elements, in reading order, into a list of:

    - {"kind": "text", "heading_path", "elements"}: the elements of one section, heading included
    - {"kind": "table", "heading_path", "lead", "rows", "pages"}: one table, never mixed with prose

    A PART or Item heading always starts a new section. A smaller heading starts one only when the current section
    has at least `min_tokens`, so tiny sections are merged instead of becoming tiny chunks. The short element just
    before a table (its title or units, such as "(in millions)") moves into the table as its `lead`. A table that
    continues on the next page (nothing in between, same number of columns) is merged into the previous one.
    """
    out, stack, buf = [], [], []
    buf_path = ""

    def flush():
        nonlocal buf
        if any(heading_level(x) is None for x in buf):  # headings alone are not a section: they are in heading_path
            out.append({"kind": "text", "heading_path": buf_path, "elements": buf})
        buf = []

    def add(e):
        nonlocal buf_path
        if not buf:
            buf_path = heading_path(stack)
        buf.append(e)

    for e in elements:
        level = heading_level(e)
        if level is not None:
            if is_major(level) or sum(count(x["content"]) for x in buf) >= min_tokens:
                flush()
            push_heading(stack, level, e["content"])
            add(e)
            continue

        rows = table_rows(e["content"]) if e["type"] == TABLE else []
        if not rows:  # prose, or a "table" that is not HTML: kept as text
            add(e)
            continue

        prev = out[-1] if out else None
        if (not buf and prev and prev["kind"] == "table" and e["page_no"] == prev["pages"][-1] + 1
                and max(map(len, rows)) == max(map(len, prev["rows"]))):
            prev["rows"].extend(rows[1:] if rows[0] == prev["rows"][0] else rows)  # drop the repeated header
            prev["pages"].append(e["page_no"])
            continue

        lead = ""
        if buf and buf[-1]["type"] != TABLE and count(buf[-1]["content"]) <= lead_tokens:
            lead = buf.pop()["content"]
        flush()
        out.append({"kind": "table", "heading_path": heading_path(stack), "lead": lead, "rows": rows,
                    "pages": [e["page_no"]]})
    flush()
    return out
