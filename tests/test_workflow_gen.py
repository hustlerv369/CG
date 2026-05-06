"""Tests for workflow_gen — the helper used by an orchestrating Claude
Code session to produce CG-compatible workflow JSON."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import workflow_gen as wg  # noqa: E402


def test_build_workflow_simple():
    flow = wg.build_workflow(
        title="Hello",
        steps=[
            ("a", "claude-sonnet-4-6", "do something"),
        ],
    )
    assert flow["title"] == "Hello"
    assert len(flow["spec"]) == 1
    assert flow["spec"][0]["agent"] == "claude-sonnet-4-6"
    assert "depends_on" not in flow["spec"][0]


def test_build_workflow_with_dependencies():
    flow = wg.build_workflow(
        title="Pipeline",
        steps=[
            ("design",   "gemini-pro", "make a spec"),
            ("build",    "claude-opus-4-7", "from spec: {{design}}", ["design"]),
            ("review",   "gemini-pro", "review: {{build}}", ["design", "build"]),
        ],
    )
    assert len(flow["spec"]) == 3
    assert flow["spec"][1]["depends_on"] == ["design"]
    assert flow["spec"][2]["depends_on"] == ["design", "build"]


def test_validate_rejects_missing_title():
    with pytest.raises(ValueError, match="title"):
        wg.validate_workflow({"spec": [{"agent": "claude-sonnet-4-6",
                                          "label": "x", "prompt": "y"}]})


def test_validate_rejects_empty_spec():
    with pytest.raises(ValueError, match="non-empty"):
        wg.validate_workflow({"title": "x", "spec": []})


def test_validate_rejects_unknown_agent():
    with pytest.raises(ValueError, match="KNOWN_AGENTS"):
        wg.validate_workflow({
            "title": "x",
            "spec": [{"agent": "unknown-foo", "label": "a", "prompt": "z"}],
        })


def test_validate_rejects_duplicate_label():
    with pytest.raises(ValueError, match="duplicate label"):
        wg.validate_workflow({
            "title": "x",
            "spec": [
                {"agent": "claude-sonnet-4-6", "label": "a", "prompt": "p1"},
                {"agent": "gemini-pro",        "label": "a", "prompt": "p2"},
            ],
        })


def test_validate_rejects_self_dep():
    with pytest.raises(ValueError, match="itself"):
        wg.validate_workflow({
            "title": "x",
            "spec": [{
                "agent": "claude-sonnet-4-6", "label": "loop",
                "depends_on": ["loop"], "prompt": "p"
            }],
        })


def test_validate_rejects_unknown_dep():
    with pytest.raises(ValueError, match="unknown label"):
        wg.validate_workflow({
            "title": "x",
            "spec": [{
                "agent": "claude-sonnet-4-6", "label": "a",
                "depends_on": ["does-not-exist"], "prompt": "p"
            }],
        })


def test_legacy_alias_accepted():
    """The legacy 'claude' / 'gemini' aliases must validate so old
    workflows still load."""
    flow = wg.build_workflow(
        title="legacy",
        steps=[
            ("a", "claude", "x"),
            ("b", "gemini", "y", ["a"]),
        ],
    )
    assert flow["spec"][0]["agent"] == "claude"


def test_write_workflow_persists_and_round_trips(tmp_path):
    flow = wg.build_workflow(
        title="Disk test",
        steps=[("a", "claude-sonnet-4-6", "p")],
    )
    path = wg.write_workflow(flow, name="disk-test", workflows_dir=tmp_path)
    assert path.exists()
    parsed = json.loads(path.read_text(encoding="utf-8"))
    assert parsed["title"] == "Disk test"

    fresh = wg.read_workflow(path)
    assert fresh == parsed


def test_safe_filename_blocks_path_separators():
    assert "/" not in wg.safe_filename("foo/bar/baz")
    assert "\\" not in wg.safe_filename("foo\\bar")
    assert wg.safe_filename(" spaces & cruft! ") == "spaces-cruft"
