"""slugify v2 — fixed per Sonnet's critique (run bd1b5693d541).

Pipeline (matches the spec produced by `design` agent):
  1. NFC normalize
  2. NFD decompose, strip combining marks (Mn category), encode ASCII (ignore)
  3. Lowercase
  4. Replace non-alnum runs with single hyphen
  5. Strip leading/trailing hyphens
  6. Truncate to max_len without breaking a word

Bug fixed
---------
Critique pointed out that when ``len(slug) > max_len`` AND
``slug[max_len] == '-'`` the slice ``slug[:max_len]`` already ends on a
clean word boundary; the original implementation still searched for the
previous hyphen and truncated again, producing a slug shorter than
necessary (e.g. ``"hello-world-foo"`` with ``max_len=11`` returned
``"hello"`` instead of ``"hello-world"``).

Also subtly fixed: when the original window itself ends with a hyphen
(``slug[max_len-1] == '-'``) the previous logic could over-trim. The
new version normalizes both cases by stripping any trailing hyphens
from the window first, then deciding whether the natural truncation
already happens to end on a word boundary.
"""

import re
import unicodedata


def slugify(text: str, max_len: int = 80) -> str:
    if max_len < 1:
        raise ValueError("max_len must be >= 1")

    # 1. NFC, then NFD so combining marks are separable.
    text = unicodedata.normalize("NFC", text)
    decomposed = unicodedata.normalize("NFD", text)
    # 2. Strip combining marks (Czech diacritics → ASCII bases).
    stripped = "".join(c for c in decomposed
                       if unicodedata.category(c) != "Mn")
    ascii_text = stripped.encode("ascii", errors="ignore").decode("ascii")
    # 3. Lowercase.
    lowered = ascii_text.lower()
    # 4. Collapse non-alnum runs to single hyphen.
    slug = re.sub(r"[^a-z0-9]+", "-", lowered)
    # 5. Strip leading/trailing hyphens.
    slug = slug.strip("-")

    # 6. Truncation.
    if len(slug) <= max_len:
        return slug

    # FIX: if the next char outside the window is itself a separator,
    # the window already ends on a clean word boundary. Just take it
    # (after stripping any trailing hyphen from the window, in case
    # max_len landed exactly on the separator).
    window = slug[:max_len]
    if slug[max_len] == "-":
        return window.rstrip("-")

    # Otherwise back off to the last hyphen inside the window.
    last_hyphen = window.rfind("-")
    if last_hyphen == -1:
        # No safe break — hard-cut at max_len.
        return window
    return window[:last_hyphen].rstrip("-")
