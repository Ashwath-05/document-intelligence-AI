"""Recursive, structure-aware text chunking.

Tries to split on paragraph breaks first; falls back to sentences, then
words, then a hard token cut only as a genuine last resort -- respecting the
document's own structure as long as possible before cutting arbitrarily.
Same category of algorithm as LangChain's RecursiveCharacterTextSplitter,
hand-rolled here on purpose: Phase 16 covers when reaching for a framework
instead of this actually pays off, and that comparison only means something
if there's real hand-written code to compare it against.

tiktoken is OpenAI's tokenizer, not Llama's (what Groq actually runs) -- an
approximation, not an exact count. Fine for sizing chunks to fit a context
window; not precise enough for exact token billing.
"""

from functools import lru_cache

import tiktoken

# Priority order: try the coarsest, most meaning-preserving split first.
_SEPARATORS = ["\n\n", "\n", ". ", " "]


@lru_cache
def _get_encoding():
    """Lazily load and cache the tokenizer.

    Loaded on first use, not at import time -- same reasoning as
    get_engine() in database.py. Importing this module (and the app
    booting) shouldn't require a network call to fetch tiktoken's vocab
    file; only actually calling count_tokens()/chunk_text() should.
    """
    return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(_get_encoding().encode(text))


def _split_on_separator(text: str, separator: str) -> list[str]:
    parts = text.split(separator)
    # Re-attach the separator to all but the last piece, so re-joining later
    # reconstructs the original text's spacing rather than losing it.
    return [p + separator for p in parts[:-1]] + [parts[-1]]


def _recursive_split(text: str, chunk_size: int, separators: list[str]) -> list[str]:
    """Split text into pieces no larger than chunk_size tokens each."""
    if count_tokens(text) <= chunk_size:
        return [text] if text.strip() else []

    if not separators:
        # Nothing structural left to try -- hard-cut by raw token count.
        tokens = _get_encoding().encode(text)
        return [
            _get_encoding().decode(tokens[i : i + chunk_size])
            for i in range(0, len(tokens), chunk_size)
        ]

    sep, *rest = separators
    pieces = _split_on_separator(text, sep)

    result: list[str] = []
    buffer = ""
    for piece in pieces:
        candidate = buffer + piece
        if count_tokens(candidate) <= chunk_size:
            buffer = candidate
            continue
        if buffer.strip():
            result.append(buffer)
        if count_tokens(piece) > chunk_size:
            # Still too big even alone -- recurse with the next, finer separator.
            result.extend(_recursive_split(piece, chunk_size, rest))
            buffer = ""
        else:
            buffer = piece
    if buffer.strip():
        result.append(buffer)
    return result


def _add_overlap(pieces: list[str], overlap_tokens: int) -> list[str]:
    """Prepend the tail of each chunk to the next one, so context isn't lost
    right at a chunk boundary."""
    if overlap_tokens <= 0 or len(pieces) <= 1:
        return pieces

    overlapped = [pieces[0]]
    for i in range(1, len(pieces)):
        prev_tokens = _get_encoding().encode(pieces[i - 1])
        tail = _get_encoding().decode(prev_tokens[-overlap_tokens:])
        overlapped.append(tail + pieces[i])
    return overlapped


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 75) -> list[dict]:
    """Split text into overlapping, token-bounded chunks.

    Returns dicts ready to become Chunk rows: text, chunk_index, token_count.

    Splits to (chunk_size - overlap) first, THEN adds overlap on top -- not
    chunk_size directly. Overlap adds tokens to a piece that already exists;
    splitting at the full chunk_size and then adding more on top would push
    chunks past the limit you asked for. Splitting smaller first means every
    resulting chunk lands at or under chunk_size once overlap is added back.
    """
    effective_size = max(chunk_size - overlap, 1)
    pieces = _recursive_split(text, effective_size, _SEPARATORS)
    pieces = _add_overlap(pieces, overlap)

    return [
        {"text": piece, "chunk_index": i, "token_count": count_tokens(piece)}
        for i, piece in enumerate(pieces)
    ]
