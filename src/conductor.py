"""Conductor — turns a raw user idea into a custom multi-agent workflow.

The Conductor is a meta-agent that uses Opus 4.7 to design a workflow
specification on the fly. The user types one idea; Conductor produces
(1) a Project Brief, (2) a validated workflow JSON spec; CG runs it.

This module is pure data + system prompts + a JSON Schema validator.
The actual subprocess execution is delegated to the existing run
engine (``RunManager.start_run``) — Conductor's two phases are
themselves single-agent runs that stream Markdown / JSON via the
already-shipping SSE infrastructure.

Reference: ``D:\\CG\\notes\\2026-05-09-strategic-roadmap-from-market-analysis.md``
section "W0 — The Conductor".
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


# ---------------------------------------------------------------------------
# Canonical roles + default model picks (the Conductor's lexicon)
# ---------------------------------------------------------------------------
# Mirrors docs/MODEL-LIMITS.md "Role vocabulary" section. Conductor tells
# Opus to label every step with one of these roles; the right column is
# the default model Opus should pick unless the role's job in this
# specific workflow argues for a different one.

CANONICAL_ROLES: dict[str, dict[str, str]] = {
    "Visionary":  {"icon": "🔭", "default_model": "claude-opus-4-7",
                   "purpose": "Defines scope and intent from a raw idea."},
    "Strategist": {"icon": "🧭", "default_model": "claude-opus-4-7",
                   "purpose": "Positioning, narrative, KPIs."},
    "Researcher": {"icon": "🔬", "default_model": "gemini-pro",
                   "purpose": "Broad reading, market lens, cross-checks."},
    "Architect":  {"icon": "🏛", "default_model": "claude-opus-4-7",
                   "purpose": "System design and large structured specs."},
    "Designer":   {"icon": "🎨", "default_model": "gemini-pro",
                   "purpose": "Independent creative eye, layouts, SVG."},
    "Engineer":   {"icon": "🛠", "default_model": "claude-opus-4-7",
                   "purpose": "Long code output without tool-loop hangs."},
    "Writer":     {"icon": "✍",  "default_model": "claude-sonnet-4-6",
                   "purpose": "Long-form prose, fast and cheap."},
    "QA":         {"icon": "🧪", "default_model": "claude-sonnet-4-6",
                   "purpose": "Tests written from spec only."},
    "Critic":     {"icon": "⚖",  "default_model": "claude-sonnet-4-6",
                   "purpose": "Code or content critique with tags + fixes."},
    "Operator":   {"icon": "📡", "default_model": "claude-sonnet-4-6",
                   "purpose": "Docs + deploy + runbooks (avoid Flash)."},
}


# ---------------------------------------------------------------------------
# Phase 1 — Brief
# ---------------------------------------------------------------------------

PHASE1_SYSTEM_PROMPT = """\
You are Conductor — the lead Visionary of CG (ClaudeGravity), a multi-agent
orchestrator. Your job in this phase is to read the user's raw idea and
produce a tight, opinionated Project Brief that a multi-agent team can
execute today.

Output ONLY the brief as Markdown with these EXACT section headings, in
this order. Be concrete. No "depends on requirements" hedging.

## Persona
Name + 1 paragraph (concrete person, not a generic segment).

## Use-cases
3-5 numbered, each ≤ 25 words. Real jobs the user does today.

## Scope (in / out)
**In:** 5-7 features that are MUST-HAVE for v1.
**Out:** 3-5 things explicitly deferred. (Saying no is the hard part.)

## Milestones
4-6 numbered milestones, each with a 1-line definition of "done".

## Recommended stack
Concrete picks (e.g. "Next.js 15 App Router + tRPC + Postgres + Stripe").
One-line rationale per pick.

## Pricing direction
1-2 sentences on revenue model + price anchor (free / freemium / $X/mo /
one-off / etc.). Justified by the persona.

## Risks
3 short bullets — top risks + a one-line mitigation each.

End the brief there. No "Conclusion" section, no signature, no notes
about the brief itself.
"""

PHASE1_USER_PROMPT_TEMPLATE = """\
The user typed this idea:

\"\"\"
{idea}
\"\"\"

{constraints_block}Write the Project Brief now.
"""


def build_phase1_prompt(idea: str, constraints: str = "") -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for Phase 1."""
    constraints_block = ""
    if constraints.strip():
        constraints_block = f"Additional constraints from the user:\n{constraints.strip()}\n\n"
    user = PHASE1_USER_PROMPT_TEMPLATE.format(
        idea=idea.strip() or "(no idea provided)",
        constraints_block=constraints_block,
    )
    return PHASE1_SYSTEM_PROMPT, user


# ---------------------------------------------------------------------------
# Phase 2 — Workflow JSON compose
# ---------------------------------------------------------------------------

PHASE2_SYSTEM_PROMPT = """\
You are Conductor in the workflow-compose phase. The user's Project Brief
is approved. Now design a multi-agent workflow that will execute the
brief end-to-end.

OUTPUT FORMAT — STRICT:
Output ONE fenced ```json code block containing a single JSON object
matching this schema:

```
{
  "id": "conductor-<short-slug>",
  "title": "<One-line title for this run>",
  "description": "<One paragraph: what the team will produce.>",
  "variables": { "<NAME>": "<default value>" },
  "spec": [
    {
      "agent": "<one of the allowed model ids>",
      "label": "<unique snake-or-kebab slug>",
      "role":  "<one of the canonical roles>",
      "prompt": "<full prompt for this agent>",
      "depends_on": ["<other label>", "..."],   // optional
      "iterate_with": "<other label>",           // optional, see loops
      "max_rounds": 3                            // optional, default 3
    }
  ]
}
```

NO PROSE before or after the fenced block. No "Here is the JSON:"
preamble. The first character of your response is a backtick.

CONSTRAINTS:
- Choose 4-9 agents. Hard cap 12.
- Every label must be unique within the spec.
- Every `depends_on` reference must point to a label earlier in the
  array — no forward references, no cycles.
- Every `agent` must be from the ALLOWED MODELS list below.
- Every `role` must be from the CANONICAL ROLES list below.
- Every prompt must be self-contained text the receiving agent can
  execute without further questions. Use `{{label}}` placeholders to
  inject upstream agent outputs (e.g. `{{visionary}}`).
- Match role to model per the heuristic table — Architect/Engineer
  prefer Opus, Critic/QA/Operator prefer Sonnet, Designer/Researcher
  prefer Gemini Pro for cross-vendor diversity.
- Cross-vendor by design: at least ONE Gemini step in any team of 5+.
- Use `iterate_with` for refinement loops where it adds value:
  Designer ↔ Critic, Engineer ↔ Reviewer. Cap with `max_rounds`.

ALLOWED MODELS (must use one of these exact strings):
{allowed_models}

CANONICAL ROLES (must use one of these exact strings):
{canonical_roles}

THE BRIEF (treat as ground truth — your spec implements this):
---
{brief}
---

Compose the workflow now. Remember: ONE fenced ```json block, nothing
else.
"""


def build_phase2_prompt(brief: str,
                          allowed_models: list[str]) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for Phase 2.

    user_prompt is the same string as system_prompt here — Conductor's
    Phase 2 is a single instruction; we put it all in stdin since
    `claude --print` doesn't take a separate system prompt at the CLI
    level (the role split is enforced by the prompt structure itself).
    """
    allowed_block = "\n".join(f"  - {m}" for m in allowed_models)
    roles_block = "\n".join(
        f"  - {r}  ({meta['icon']}, {meta['purpose']})"
        for r, meta in CANONICAL_ROLES.items()
    )
    # Avoid str.format here — the JSON example in PHASE2_SYSTEM_PROMPT
    # contains literal `{` `}` chars that would collide with format slots.
    sys = (PHASE2_SYSTEM_PROMPT
           .replace("{allowed_models}", allowed_block)
           .replace("{canonical_roles}", roles_block)
           .replace("{brief}", brief.strip() or "(no brief provided)"))
    return sys, sys


# ---------------------------------------------------------------------------
# Phase 2 output parsing + validation
# ---------------------------------------------------------------------------

_FENCED_JSON_RE = re.compile(
    r"```(?:json|JSON)?\s*\n(.*?)\n```",
    re.DOTALL,
)


def extract_json_block(text: str) -> str | None:
    """Extract the first fenced JSON code block from text.

    Returns the inner JSON string, or None if no fenced block found.
    Falls back to "first `{` to last `}`" if no fence is present —
    Opus occasionally drops the fence when its output is the JSON
    itself with no surrounding prose.
    """
    m = _FENCED_JSON_RE.search(text)
    if m:
        return m.group(1).strip()
    s = text.strip()
    if s.startswith("{") and s.endswith("}"):
        return s
    # Last-ditch: find {...} substring
    first = s.find("{")
    last = s.rfind("}")
    if first != -1 and last != -1 and last > first:
        return s[first : last + 1]
    return None


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str]
    spec: dict[str, Any] | None  # parsed + normalized when ok=True


def validate_workflow_spec(raw: dict[str, Any] | str,
                              allowed_models: set[str],
                              max_agents: int = 12) -> ValidationResult:
    """Validate a Conductor-generated workflow spec.

    Checks:
      - top-level shape (id, title, description, variables, spec)
      - per-step: agent in allowed_models, label unique, role known,
        prompt non-empty, depends_on points to earlier labels, no cycles
      - hard cap on agent count
      - iterate_with target exists if set; max_rounds is 1..10

    Returns a ValidationResult. If ok=True, spec is normalized (defaults
    filled, depends_on always a list) and ready to feed to start_run.
    """
    errors: list[str] = []
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            return ValidationResult(False, [f"invalid JSON: {e}"], None)
    else:
        data = raw

    if not isinstance(data, dict):
        return ValidationResult(False, ["top-level must be a JSON object"], None)

    # Top-level fields
    for k in ("id", "title", "description"):
        if not isinstance(data.get(k), str) or not data.get(k).strip():
            errors.append(f"missing or empty top-level field {k!r}")
    spec = data.get("spec")
    if not isinstance(spec, list) or not spec:
        return ValidationResult(False,
                                 errors + ["missing or empty 'spec' array"],
                                 None)
    if len(spec) > max_agents:
        errors.append(f"too many agents: {len(spec)} > cap {max_agents}")

    valid_roles = set(CANONICAL_ROLES.keys())
    seen_labels: set[str] = set()
    normalized_spec: list[dict[str, Any]] = []
    for i, step in enumerate(spec):
        if not isinstance(step, dict):
            errors.append(f"spec[{i}] is not an object")
            continue
        label = step.get("label")
        if not isinstance(label, str) or not label.strip():
            errors.append(f"spec[{i}] missing/empty 'label'")
            label = f"agent-{i+1}"
        if label in seen_labels:
            errors.append(f"spec[{i}] duplicate label {label!r}")
            label = f"{label}-{i+1}"
        seen_labels.add(label)

        agent_kind = step.get("agent")
        if not isinstance(agent_kind, str) or agent_kind not in allowed_models:
            errors.append(
                f"spec[{i}] '{label}' has unknown agent {agent_kind!r}; "
                f"allowed: {sorted(allowed_models)}"
            )

        role = step.get("role", "")
        if role and role not in valid_roles:
            errors.append(
                f"spec[{i}] '{label}' has unknown role {role!r}; "
                f"allowed: {sorted(valid_roles)}"
            )

        prompt = step.get("prompt", "")
        if not isinstance(prompt, str) or not prompt.strip():
            errors.append(f"spec[{i}] '{label}' has empty prompt")

        deps = step.get("depends_on", []) or []
        if not isinstance(deps, list):
            errors.append(f"spec[{i}] '{label}' depends_on must be a list")
            deps = []
        for dep in deps:
            if dep == label:
                errors.append(f"spec[{i}] '{label}' depends on itself")
            elif dep not in seen_labels:
                errors.append(
                    f"spec[{i}] '{label}' depends on {dep!r} which is not "
                    f"declared earlier in the spec"
                )

        iterate_with = step.get("iterate_with")
        if iterate_with:
            if iterate_with == label:
                errors.append(f"spec[{i}] '{label}' iterate_with itself")
            elif iterate_with not in seen_labels and iterate_with not in {
                s.get("label") for s in spec
            }:
                errors.append(
                    f"spec[{i}] '{label}' iterate_with {iterate_with!r} "
                    f"which does not exist in spec"
                )

        max_rounds = step.get("max_rounds", 3)
        if not isinstance(max_rounds, int) or not (1 <= max_rounds <= 10):
            errors.append(
                f"spec[{i}] '{label}' max_rounds must be int in [1, 10]"
            )
            max_rounds = 3

        normalized = {
            "agent": agent_kind,
            "label": label,
            "role": role or "",
            "prompt": prompt,
            "depends_on": list(deps),
        }
        if iterate_with:
            normalized["iterate_with"] = iterate_with
            normalized["max_rounds"] = max_rounds
        if step.get("streaming"):
            normalized["streaming"] = True
        normalized_spec.append(normalized)

    if errors:
        return ValidationResult(False, errors, None)

    out = {
        "id": data["id"],
        "title": data["title"],
        "description": data["description"],
        "variables": data.get("variables") or {},
        "spec": normalized_spec,
    }
    return ValidationResult(True, [], out)
