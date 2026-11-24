"""Text -> pieces of a size in tokens, with LangChain's RecursiveCharacterTextSplitter.

The splitter tries the gentlest cut first: paragraph, line, sentence, word. Sizes are counted in tokens with
tiktoken, so a chunk always fits the embedding model.

tiktoken downloads its vocabulary on first use. Workers may have no internet access, so the notebooks point
`TIKTOKEN_CACHE_DIR` at a volume (see `use_cache`) that the driver fills once.

The caches are plain dicts, filled on first use in each process: the module is shipped to the workers by value
(cloudpickle), and an empty dict pickles cleanly.
"""

import os

ENCODING = "cl100k_base"
SEPARATORS = ["\n\n", "\n", ". ", " ", ""]
_CACHE = {}


def use_cache(path):
    """Read (and on the driver, write) tiktoken's vocabulary in `path`. Call before the first count_tokens."""
    os.environ["TIKTOKEN_CACHE_DIR"] = path


def _encoding():
    if "encoding" not in _CACHE:
        import tiktoken

        _CACHE["encoding"] = tiktoken.get_encoding(ENCODING)
    return _CACHE["encoding"]


def count_tokens(text):
    return len(_encoding().encode(text, disallowed_special=()))


def _length(text):
    return count_tokens(text)  # looked up on every call, so tests can replace count_tokens


def _splitter(size, overlap):
    """One splitter per size, built once per process (once per worker in a UDF)."""
    key = ("splitter", size, overlap)
    if key not in _CACHE:
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        _CACHE[key] = RecursiveCharacterTextSplitter(
            chunk_size=size, chunk_overlap=overlap, length_function=_length, separators=SEPARATORS,
            keep_separator="end",
        )
    return _CACHE[key]


def split_text(text, size, overlap):
    """Pieces of at most `size` tokens (unless one word is bigger), `overlap` tokens shared between neighbours."""
    return _splitter(size, overlap).split_text(text)


def split_with_offsets(text, size, overlap):
    """Like split_text, with the character offset where each piece starts: [(start, piece), ...].

    The pieces are in order, so each one is searched for after the start of the previous one. (LangChain's own
    add_start_index can answer -1 on repetitive text, which filings have plenty of.)"""
    out, start = [], -1
    for piece in split_text(text, size, overlap):
        found = text.find(piece, start + 1)
        start = found if found >= 0 else start + 1
        out.append((start, piece))
    return out
