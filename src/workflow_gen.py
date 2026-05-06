"""Workflow generator helpers — produce CG dashboard workflow JSON
from a higher-level brief.

This module is meant to be imported by another Claude Code session
(or any orchestrator) that wants to *generate* a workflow JSON file
that the dashboard can then auto-load via:

    cg dashboard --workflow workflows/my-flow.json

The CG workflow JSON schema is documented in ``WORKFLOW_SCHEMA``.
``validate_workflow`` raises ``ValueError`` on invalid input,
``write_workflow`` persists a validated workflow to disk under
``D:\\CG\\workflows\\<name>.json``.

The generator pattern used by Claude Code session::

    from workflow_gen import build_workflow, write_workflow

    flow = build_workflow(
        title="Refactor TeamIDAS auth",
        steps=[
            ("design",    "gemini-pro",        "Analyze: {{file:src/auth.ts}}\\n..."),
            ("implement", "claude-opus-4-7",   "Per spec: {{design}}",  ["design"]),
            ("review",    "gemini-pro",        "Critique: {{implement}}", ["design","implement"]),
        ],
    )
    write_workflow(flow, name="teamidas-auth-refactor")
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = ROOT / "workflows"

KNOWN_AGENTS = {
    # Subscription-driven (default — no extra cost on top of Pro/Google sub)
    "claude-sonnet-4-6", "claude-opus-4-7", "claude-opus-4-6",
    "gemini-flash", "gemini-pro", "gemini-3-pro",
    # OpenRouter (require OPENROUTER_API_KEY)
    "or-glm-4.7", "or-deepseek-v3", "or-qwen3-coder",
    # Z.ai direct (require ZHIPU_API_KEY)
    "glm-4.7", "glm-4.7-flash", "glm-4.7-flashx",
    # Direct API (require ANTHROPIC_API_KEY / GEMINI_API_KEY)
    "claude-api-sonnet", "gemini-api-pro",
    # Legacy aliases — accepted, normalized to canonical at dispatch
    "claude", "gemini",
}


WORKFLOW_SCHEMA = """
{
  "title": "<short human-readable name>",
  "description": "<optional one-liner>",
  "spec": [
    {
      "agent": "<one of KNOWN_AGENTS>",
      "label": "<unique-label-in-this-flow>",
      "depends_on": ["<labels of agents whose output this prompt needs>"],
      "prompt": "<the prompt text — may include placeholders>"
    }
  ]
}

Placeholder tokens supported in 'prompt':
  {{label}}                     -> output of dependency 'label'
  {{file:src/foo.py}}           -> contents of a file (project-rooted)
  {{git:diff}}                  -> current git diff
  {{git:diff:HEAD~1}}           -> diff vs ref
  {{git:log:N}}                 -> last N commits oneline
  {{git:status}}                -> git status --short --branch
  {{git:show:HEAD}}             -> git show --stat
  {{git:branch}}                -> current branch
  {{shell:cmd}}                 -> command output (env CG_ALLOW_SHELL=1 required)

Project root for {{file:}} defaults to D:\\CG; override via env
CG_PROJECT_ROOT=<absolute path>.
""".strip()


def build_workflow(
    *,
    title: str,
    description: str | None = None,
    steps: list[tuple] | None = None,
) -> dict:
    """Construct a workflow dict from a list of step tuples.

    Each step is a 3- or 4-tuple::

        (label, agent, prompt)
        (label, agent, prompt, depends_on_list)

    Returns the raw dict ready for :func:`write_workflow`.
    """
    spec = []
    for s in steps or []:
        if len(s) == 3:
            label, agent, prompt = s
            deps = []
        elif len(s) == 4:
            label, agent, prompt, deps = s
        else:
            raise ValueError(f"step must be 3- or 4-tuple, got: {s!r}")
        entry = {"agent": agent, "label": label, "prompt": prompt}
        if deps:
            entry["depends_on"] = list(deps)
        spec.append(entry)

    flow = {"title": title, "spec": spec}
    if description:
        flow["description"] = description
    validate_workflow(flow)
    return flow


def validate_workflow(flow: dict) -> None:
    """Raise ValueError if *flow* is not a valid CG workflow."""
    if not isinstance(flow, dict):
        raise ValueError("workflow must be a JSON object")
    if not flow.get("title"):
        raise ValueError("workflow.title is required")
    spec = flow.get("spec")
    if not isinstance(spec, list) or not spec:
        raise ValueError("workflow.spec must be a non-empty array")

    labels: set[str] = set()
    for i, item in enumerate(spec):
        if not isinstance(item, dict):
            raise ValueError(f"spec[{i}] must be an object")
        for key in ("agent", "label", "prompt"):
            if not item.get(key):
                raise ValueError(f"spec[{i}].{key} is required")
        agent = item["agent"]
        if agent not in KNOWN_AGENTS:
            # Soft warning via ValueError — caller can decide to ignore
            raise ValueError(
                f"spec[{i}].agent {agent!r} is not in KNOWN_AGENTS. "
                f"Allowed (subscription-driven): claude-sonnet-4-6, "
                f"claude-opus-4-7, claude-opus-4-6, gemini-flash, "
                f"gemini-pro, gemini-3-pro. (Or pass through with custom "
                f"AGENT_KINDS at runtime.)"
            )
        label = item["label"]
        if label in labels:
            raise ValueError(f"duplicate label: {label!r}")
        labels.add(label)
        for dep in item.get("depends_on", []) or []:
            if dep == label:
                raise ValueError(f"spec[{i}] depends on itself: {label!r}")
            if dep not in labels:
                # depends_on must reference an EARLIER label (we don't
                # require strict topological order, but we do require
                # the label to exist *somewhere* in the spec). We do a
                # second pass below to confirm.
                pass

    # Second pass — verify every depends_on entry exists
    for i, item in enumerate(spec):
        for dep in item.get("depends_on", []) or []:
            if dep not in labels:
                raise ValueError(
                    f"spec[{i}].depends_on references unknown label "
                    f"{dep!r}; available: {sorted(labels)}"
                )


def safe_filename(raw: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "-", raw.strip()) or "workflow"
    return safe[:80].strip("-")


def write_workflow(flow: dict, *, name: str | None = None,
                    workflows_dir: Path | None = None) -> Path:
    """Persist *flow* under ``workflows_dir/<name>.json``. Returns path."""
    validate_workflow(flow)
    workflows_dir = (workflows_dir or WORKFLOWS_DIR)
    workflows_dir.mkdir(parents=True, exist_ok=True)
    fname = safe_filename(name or flow.get("title", "workflow")) + ".json"
    path = workflows_dir / fname
    path.write_text(
        json.dumps(flow, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def read_workflow(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    validate_workflow(data)
    return data
