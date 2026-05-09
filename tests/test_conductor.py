"""Tests for src/conductor.py — Phase 2 JSON validator + extractor."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from conductor import (  # noqa: E402
    CANONICAL_ROLES,
    build_phase1_prompt,
    build_phase2_prompt,
    extract_json_block,
    validate_workflow_spec,
)


ALLOWED = {"claude-opus-4-7", "claude-sonnet-4-6", "gemini-pro", "gemini-flash"}


# ---------------------------------------------------------------------------
# Phase 1 prompt builder
# ---------------------------------------------------------------------------

def test_phase1_includes_idea():
    sys, user = build_phase1_prompt("a SaaS for cat photos")
    assert "Project Brief" in sys
    assert "Persona" in sys
    assert "a SaaS for cat photos" in user


def test_phase1_constraints_block():
    _, user = build_phase1_prompt("idea", constraints="must be in CZ + EN")
    assert "must be in CZ + EN" in user


def test_phase1_no_constraints_no_block():
    _, user = build_phase1_prompt("idea", constraints="")
    assert "Additional constraints" not in user


# ---------------------------------------------------------------------------
# Phase 2 prompt builder
# ---------------------------------------------------------------------------

def test_phase2_includes_brief_and_models():
    sys, user = build_phase2_prompt(
        "## Persona\nAlex.",
        ["claude-opus-4-7", "gemini-pro"],
    )
    assert sys == user  # same prompt — single instruction
    assert "claude-opus-4-7" in sys
    assert "gemini-pro" in sys
    assert "## Persona\nAlex." in sys
    # All canonical roles must be listed
    for role in CANONICAL_ROLES:
        assert role in sys


# ---------------------------------------------------------------------------
# JSON block extractor
# ---------------------------------------------------------------------------

def test_extract_fenced_json():
    text = "Here you go:\n```json\n{\"a\": 1}\n```\nDone."
    assert extract_json_block(text) == '{"a": 1}'


def test_extract_fenced_no_lang():
    text = "```\n{\"a\": 1}\n```"
    assert extract_json_block(text) == '{"a": 1}'


def test_extract_naked_json():
    text = '   {"a": 1}   '
    assert extract_json_block(text) == '{"a": 1}'


def test_extract_json_with_prose_around():
    text = 'Here:\n{"a": 1}\nThanks.'
    out = extract_json_block(text)
    # Falls back to first { ... last } substring
    assert out == '{"a": 1}'


def test_extract_no_json():
    assert extract_json_block("plain text only") is None


# ---------------------------------------------------------------------------
# Validator — happy paths
# ---------------------------------------------------------------------------

def _good_spec() -> dict:
    return {
        "id": "conductor-foo",
        "title": "Build a thing",
        "description": "Multi-agent team builds the thing.",
        "variables": {"IDEA": "a thing"},
        "spec": [
            {
                "agent": "claude-opus-4-7",
                "label": "visionary",
                "role": "Visionary",
                "prompt": "Define scope for ${IDEA}.",
            },
            {
                "agent": "gemini-pro",
                "label": "designer",
                "role": "Designer",
                "prompt": "Design from {{visionary}}.",
                "depends_on": ["visionary"],
            },
            {
                "agent": "claude-opus-4-7",
                "label": "engineer",
                "role": "Engineer",
                "prompt": "Build from {{visionary}} and {{designer}}.",
                "depends_on": ["visionary", "designer"],
            },
        ],
    }


def test_validate_accepts_good_spec():
    res = validate_workflow_spec(_good_spec(), ALLOWED)
    assert res.ok, res.errors
    assert res.spec is not None
    assert len(res.spec["spec"]) == 3
    # Normalized fields
    assert res.spec["spec"][0]["depends_on"] == []
    assert res.spec["spec"][1]["depends_on"] == ["visionary"]


def test_validate_accepts_iterate_with():
    spec = _good_spec()
    spec["spec"].append({
        "agent": "claude-sonnet-4-6",
        "label": "critic",
        "role": "Critic",
        "prompt": "Critique {{designer}}.",
        "depends_on": ["designer"],
        "iterate_with": "designer",
        "max_rounds": 2,
    })
    res = validate_workflow_spec(spec, ALLOWED)
    assert res.ok, res.errors
    assert res.spec["spec"][-1]["iterate_with"] == "designer"
    assert res.spec["spec"][-1]["max_rounds"] == 2


def test_validate_accepts_string_input():
    res = validate_workflow_spec(json.dumps(_good_spec()), ALLOWED)
    assert res.ok, res.errors


# ---------------------------------------------------------------------------
# Validator — failure modes
# ---------------------------------------------------------------------------

def test_validate_rejects_invalid_json_string():
    res = validate_workflow_spec("{not json", ALLOWED)
    assert not res.ok
    assert any("invalid JSON" in e for e in res.errors)


def test_validate_rejects_missing_top_fields():
    res = validate_workflow_spec({"spec": []}, ALLOWED)
    assert not res.ok
    assert any("'id'" in e for e in res.errors)
    assert any("spec" in e for e in res.errors)


def test_validate_rejects_unknown_model():
    spec = _good_spec()
    spec["spec"][0]["agent"] = "gpt-7-superduper"
    res = validate_workflow_spec(spec, ALLOWED)
    assert not res.ok
    assert any("gpt-7-superduper" in e for e in res.errors)


def test_validate_rejects_unknown_role():
    spec = _good_spec()
    spec["spec"][0]["role"] = "Wizard"
    res = validate_workflow_spec(spec, ALLOWED)
    assert not res.ok
    assert any("Wizard" in e for e in res.errors)


def test_validate_rejects_duplicate_labels():
    spec = _good_spec()
    spec["spec"][1]["label"] = "visionary"
    res = validate_workflow_spec(spec, ALLOWED)
    assert not res.ok
    assert any("duplicate" in e for e in res.errors)


def test_validate_rejects_forward_reference():
    spec = _good_spec()
    # designer depends on engineer (which is later)
    spec["spec"][1]["depends_on"] = ["engineer"]
    res = validate_workflow_spec(spec, ALLOWED)
    assert not res.ok


def test_validate_rejects_self_dependency():
    spec = _good_spec()
    spec["spec"][0]["depends_on"] = ["visionary"]
    res = validate_workflow_spec(spec, ALLOWED)
    assert not res.ok
    assert any("itself" in e for e in res.errors)


def test_validate_rejects_empty_prompt():
    spec = _good_spec()
    spec["spec"][0]["prompt"] = ""
    res = validate_workflow_spec(spec, ALLOWED)
    assert not res.ok


def test_validate_rejects_too_many_agents():
    spec = _good_spec()
    base = spec["spec"][0]
    spec["spec"] = [
        {**base, "label": f"a{i}", "depends_on": []}
        for i in range(15)
    ]
    res = validate_workflow_spec(spec, ALLOWED, max_agents=12)
    assert not res.ok
    assert any("too many" in e for e in res.errors)


def test_validate_rejects_invalid_max_rounds():
    spec = _good_spec()
    spec["spec"][2]["iterate_with"] = "designer"
    spec["spec"][2]["max_rounds"] = 99
    res = validate_workflow_spec(spec, ALLOWED)
    assert not res.ok
    assert any("max_rounds" in e for e in res.errors)


def test_canonical_roles_table_complete():
    # Sanity: every role has icon, default_model, purpose
    for role, meta in CANONICAL_ROLES.items():
        assert "icon" in meta and meta["icon"]
        assert "default_model" in meta and meta["default_model"]
        assert "purpose" in meta and meta["purpose"]
