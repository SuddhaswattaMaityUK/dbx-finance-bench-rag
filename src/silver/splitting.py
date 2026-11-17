"""Cut a long PDF into parts of at most `size` pages, so the parser gets small requests."""

from io import BytesIO


def part_ranges(pages, size):
    """The parts of a PDF as (part_no, first page, end page), 0-based, end excluded. One part if it is short enough."""
    if not size or pages <= size:
        return [(1, 0, pages)]
    return [(i + 1, start, min(start + size, pages)) for i, start in enumerate(range(0, pages, size))]


def split_pdf(content, size):
    """Cut a PDF (bytes). Returns [(part_no, page_offset, pages, bytes)].

    A PDF that is short, or that cannot be read here, is one part with its original bytes: the parser then
    decides, and a failure is logged like any other.
    """
    from pypdf import PdfReader, PdfWriter  # outside the try: a missing library must fail, not look like a bad PDF

    try:
        reader = PdfReader(BytesIO(content))
        ranges = part_ranges(len(reader.pages), size)
        if len(ranges) == 1:
            return [(1, 0, ranges[0][2], content)]
        parts = []
        for part_no, start, end in ranges:
            writer = PdfWriter()
            for page in reader.pages[start:end]:
                writer.add_page(page)
            buffer = BytesIO()
            writer.write(buffer)
            parts.append((part_no, start, end - start, buffer.getvalue()))
        return parts
    except Exception:
        return [(1, 0, None, content)]
