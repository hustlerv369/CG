"""slugify v1 — Opus 4.7's original output from run bd1b5693d541.

Kept verbatim so we can prove (via tests) that Sonnet's critique was
correct: this version fails on the truncation edge case where the
window already ends on a word boundary (next char is a hyphen).
"""

import unicodedata
import re


def slugify(text: str, max_len: int = 80) -> str:
    if max_len < 1:
        raise ValueError("max_len must be >= 1")

    text = unicodedata.normalize("NFC", text)
    decomposed = unicodedata.normalize("NFD", text)
    stripped = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    ascii_text = stripped.encode("ascii", errors="ignore").decode("ascii")
    lowered = ascii_text.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered)
    slug = slug.strip("-")

    if len(slug) <= max_len:
        return slug

    window = slug[:max_len]
    last_hyphen = window.rfind("-")
    if last_hyphen == -1:
        return window
    return window[:last_hyphen].rstrip("-")
