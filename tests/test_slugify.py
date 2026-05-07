"""Verifies Sonnet's critique against Opus's original output AND that
the v2 fix passes everything.

Test data
=========
Every spec example from `design.out.md` is a parametrized case. Plus a
"buggy fixture" that runs the SAME assertions against the original Opus
implementation to prove the critique was real (not LLM hallucination).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from examples.slugify import slugify as slugify_fixed
from examples.slugify_v1_opus_original import slugify as slugify_buggy


# Each tuple: (input, max_len, expected, source)
# `source` is just a tag for debug; "spec" = from design.out.md, the
# rest are extra cases I derived while reviewing the implementation.
SPEC_CASES = [
    # ---- spec edge-cases table ------------------------------------
    ("",                                              80, "",                            "spec"),
    ("   ---   ",                                     80, "",                            "spec"),
    ("superlongwordthatexceedslimit",                 10, "superlongw",                  "spec"),
    ("hello world",                                   80, "hello-world",                 "spec"),
    ("Příliš žluťoučký kůň",                          80, "prilis-zlutoucky-kun",        "spec"),
    ("foo & bar (baz)!",                              80, "foo-bar-baz",                 "spec"),
    ("hello-world-foo",                               11, "hello-world",                 "spec"),  # critique bug case
    ("hello-world-foo",                                5, "hello",                       "spec"),
    ("v1.2.3 release",                                80, "v1-2-3-release",              "spec"),
    # ---- spec concrete examples -----------------------------------
    ("Příliš žluťoučký kůň úpěl ďábelské ódy",        25, "prilis-zlutoucky-kun-upel",   "spec"),
    ("  Hello, World!  (2024) -- v1.0  ",             80, "hello-world-2024-v1-0",       "spec"),
    ("Discontinuousword",                             10, "discontinu",                  "spec"),
    # ---- extra edge cases I derived during review ----------------
    ("中文",                                           80, "",                            "extra"),  # all non-ASCII stripped
    ("abc-def",                                        7, "abc-def",                     "extra"),  # exactly fits
    ("abc-def",                                        4, "abc",                         "extra"),  # window has hyphen INSIDE
    ("abc-def",                                        3, "abc",                         "extra"),  # window has no hyphen
    ("hello-world-foo-bar",                           12, "hello-world",                 "extra"),  # window ends ON hyphen
]


@pytest.mark.parametrize("text,max_len,expected,source", SPEC_CASES)
def test_slugify_fixed_matches_spec(text, max_len, expected, source):
    """The fixed v2 must satisfy every spec assertion."""
    assert slugify_fixed(text, max_len=max_len) == expected, source


def test_slugify_fixed_rejects_invalid_max_len():
    with pytest.raises(ValueError):
        slugify_fixed("anything", max_len=0)
    with pytest.raises(ValueError):
        slugify_fixed("anything", max_len=-5)


# ---- proof Sonnet's critique was real ----------------------------


CRITIQUE_BUG_CASES = [
    # Both cases Sonnet pointed at explicitly. Original Opus impl
    # FAILS these; our v2 fix passes them.
    ("hello-world-foo",                              11, "hello-world"),
    ("Příliš žluťoučký kůň úpěl ďábelské ódy",       25, "prilis-zlutoucky-kun-upel"),
]


@pytest.mark.parametrize("text,max_len,expected", CRITIQUE_BUG_CASES)
def test_opus_v1_actually_has_the_bug_critique_described(text, max_len, expected):
    """If this passes, Sonnet's critique was NOT a hallucination —
    Opus's original implementation really did return the wrong slug
    on these inputs. The v2 fix flips them green."""
    actual = slugify_buggy(text, max_len=max_len)
    assert actual != expected, (
        f"Critique would have been a false positive — Opus actually "
        f"returned {expected!r} for {text!r}, which means there was "
        f"no bug. (Got {actual!r} via the buggy path.)"
    )
    # And confirm the fixed version corrects it.
    assert slugify_fixed(text, max_len=max_len) == expected
