"""The chunking strategies: one PDF's parsed elements -> parent and child rows for the gold tables.

- structured (main): sections by heading, whole tables. Parents (what the LLM reads) are sections up to
  `parent_tokens` or a whole table; children (what is searched) are small pieces of a parent, or row groups of a
  table that each repeat the header row.
- fixed (baseline): the whole text cut every `fixed_tokens`, headings and tables ignored. No parents: a chunk is
  what is searched and what the LLM reads.

Every child keeps `parent_text`, the text the LLM gets, so one search returns it (it is not embedded). Only
`embed_text` (a prefix line with the filing and section, then the child's text) is embedded.
"""

import bisect
import hashlib
from dataclasses import dataclass

import text_split
from elements import TABLE, clean, doc_meta
from sections import sections
from tables import pieces, render, table_rows

STRATEGIES = ("structured", "fixed")


@dataclass(frozen=True)
class Settings:
    parent_tokens: int = 900
    child_tokens: int = 200
    child_overlap: int = 30
    fixed_tokens: int = 600
    fixed_overlap: int = 60
    min_section_tokens: int = 100
    lead_tokens: int = 60


def _id(*parts):
    return hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()


def prefix(meta, heading_path):
    """The line put before a child's text in embed_text: BOEING 10K 2022 | Item 8 > Consolidated Statements..."""
    company, period, doc_type = meta
    head = " ".join(p for p in (company, doc_type, period) if p)
    return f"{head} | {heading_path}" if heading_path else head


def _text_parents(section, count, s):
    """A text section -> parents of at most parent_tokens, packed element by element, so each knows its pages.
    An element bigger than parent_tokens is cut with the splitter and keeps its own page."""
    out, group, size = [], [], 0

    def flush():
        nonlocal group, size
        if group:
            pages = [e["page_no"] for e in group]
            out.append(("\n\n".join(e["content"] for e in group), min(pages), max(pages)))
        group, size = [], 0

    for e in section["elements"]:
        n = count(e["content"])
        if n > s.parent_tokens:
            flush()
            out += [(t, e["page_no"], e["page_no"]) for t in text_split.split_text(e["content"], s.parent_tokens, 0)]
            continue
        if group and size + n > s.parent_tokens:
            flush()
        group.append(e)
        size += n
    flush()
    return out


def chunk_structured(path, elements, s=Settings()):
    meta, count = doc_meta(path), text_split.count_tokens
    parents, children = [], []
    for sec in sections(clean(elements), count, s.min_section_tokens, s.lead_tokens):
        if sec["kind"] == "table":
            groups = [(render(sec["rows"], sec["lead"]), min(sec["pages"]), max(sec["pages"]),
                       pieces(sec["rows"], sec["lead"], s.child_tokens, count))]
        else:
            groups = [(text, first, last, text_split.split_text(text, s.child_tokens, s.child_overlap))
                      for text, first, last in _text_parents(sec, count, s)]

        for text, first, last, kids in groups:
            pid = _id("structured", path, "parent", len(parents))
            common = {"path": path, "company": meta[0], "fiscal_period": meta[1], "doc_type": meta[2],
                      "chunk_type": sec["kind"], "heading_path": sec["heading_path"],
                      "page_start": first, "page_end": last}
            parents.append({"parent_id": pid, "parent_no": len(parents), **common, "text": text,
                            "n_tokens": count(text)})
            for kid in kids:
                children.append({"chunk_id": _id("structured", path, "child", len(children)), "strategy": "structured",
                                 "parent_id": pid, "chunk_no": len(children), **common, "text": kid,
                                 "embed_text": f"{prefix(meta, sec['heading_path'])}\n\n{kid}",
                                 "parent_text": text, "n_tokens": count(kid)})
    return parents, children


def chunk_fixed(path, elements, s=Settings()):
    """The baseline: all the text in reading order (tables rendered as rows), cut every fixed_tokens."""
    meta, count = doc_meta(path), text_split.count_tokens
    texts, starts, pages, pos = [], [], [], 0
    for e in clean(elements):
        rows = table_rows(e["content"]) if e["type"] == TABLE else []
        text = render(rows) if rows else e["content"]
        texts.append(text)
        starts.append(pos)
        pages.append(e["page_no"])
        pos += len(text) + 2  # the "\n\n" between elements
    if not texts:
        return [], []

    children = []
    for start, piece in text_split.split_with_offsets("\n\n".join(texts), s.fixed_tokens, s.fixed_overlap):
        first = bisect.bisect_right(starts, start) - 1
        last = bisect.bisect_right(starts, start + len(piece) - 1) - 1
        span = pages[first:last + 1]
        children.append({
            "chunk_id": _id("fixed", path, "child", len(children)), "strategy": "fixed", "parent_id": None,
            "chunk_no": len(children), "path": path, "company": meta[0], "fiscal_period": meta[1],
            "doc_type": meta[2], "chunk_type": "text", "heading_path": None,
            "page_start": min(span), "page_end": max(span), "text": piece,
            "embed_text": f"{prefix(meta, None)}\n\n{piece}", "parent_text": piece, "n_tokens": count(piece),
        })
    return [], children


def chunk(path, elements, strategy, s=Settings()):
    """One PDF -> (parents, children) for the strategy."""
    match strategy:
        case "structured":
            return chunk_structured(path, elements, s)
        case "fixed":
            return chunk_fixed(path, elements, s)
        case _:
            raise ValueError(f"unknown strategy: {strategy}")
