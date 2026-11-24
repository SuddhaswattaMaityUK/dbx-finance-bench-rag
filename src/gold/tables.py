"""Tables: the parser's HTML -> rows -> text. No model is involved, so every number stays exactly as parsed."""

from html.parser import HTMLParser


class _Rows(HTMLParser):
    """Collects the text of each cell, row by row. A cell with colspan=n is padded with n-1 empty cells."""

    def __init__(self):
        super().__init__()
        self.rows, self._row, self._cell, self._span = [], None, None, 1

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._end_row()
            self._row = []
        elif tag in ("td", "th"):
            self._end_cell()
            self._cell = []
            try:
                self._span = max(1, int(dict(attrs).get("colspan") or 1))
            except ValueError:
                self._span = 1
        elif tag == "br" and self._cell is not None:
            self._cell.append(" ")

    def handle_endtag(self, tag):
        if tag in ("td", "th"):
            self._end_cell()
        elif tag in ("tr", "table"):
            self._end_row()

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)

    def _end_cell(self):
        if self._cell is None:
            return
        if self._row is None:
            self._row = []
        self._row.append(" ".join("".join(self._cell).split()))
        self._row.extend([""] * (self._span - 1))
        self._cell = None

    def _end_row(self):
        self._end_cell()
        if self._row and any(self._row):
            self.rows.append(self._row)
        self._row = None

    def close(self):
        super().close()
        self._end_row()


def table_rows(html):
    """HTML table -> list of rows, each a list of cell texts. Empty rows are dropped. [] if it is not an HTML table."""
    parser = _Rows()
    parser.feed(html or "")
    parser.close()
    return parser.rows


def render(rows, lead=""):
    """Rows -> a pipe table, with the lead line (the table's title or units, such as "(in millions)") on top."""
    lines = ["| " + " | ".join(r) + " |" for r in rows]
    if len(lines) > 1:
        lines.insert(1, "|" + " --- |" * len(rows[0]))
    return "\n".join(([lead] if lead else []) + lines)


def pieces(rows, lead, size, count):
    """A table cut into row groups of at most `size` tokens. Every group repeats the lead line and the header row,
    so a piece on its own still says what its columns and units are. A single row bigger than `size` is its own piece."""
    header, body = rows[:1], rows[1:]
    if not body:
        return [render(rows, lead)]
    out, group = [], []
    for row in body:
        if group and count(render(header + group + [row], lead)) > size:
            out.append(render(header + group, lead))
            group = []
        group.append(row)
    out.append(render(header + group, lead))
    return out
