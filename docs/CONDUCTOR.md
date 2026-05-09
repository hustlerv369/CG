# Conductor — Opus designs your team

**Status:** shipped in v48 (master `0235f51`). UI live in Quick Start
hero. Backend at `src/conductor.py`, endpoints under `/api/conductor/*`.

## What it does

Type a 1–3 sentence idea. Click **🎩 Conductor**. Opus 4.7 reads the
idea and designs a custom multi-agent workflow for *that specific
idea* — not a fixed template. Tick **🚀 Auto mode** to skip approval
gates and ship end-to-end.

No competitor in the analysis (Make, n8n, Zapier, CrewAI, LangGraph,
Gumloop, Lindy, Warp) auto-designs a team. Templates exist; design
doesn't.

## Two-phase flow

The trick that makes this reliable is **separating thinking from
structuring**. One Opus call to design freely (Markdown), one Opus
call to lock structure (validated JSON). Each call is small, focused,
and easy to validate.

```
┌──────────┐ idea ┌────────────┐ brief  ┌──────────────┐ JSON ┌──────────┐
│ Quick    ├─────▶│  Phase 1   ├───────▶│   Phase 2    ├─────▶│  Launch  │
│ Start    │      │  Brief     │ approve│   Compose    │valid.│  real    │
│  hero    │      │  (Opus)    │        │   (Opus JSON)│      │  run     │
└──────────┘      └────────────┘        └──────────────┘      └──────────┘
                  Markdown stream      JSON spec stream      Live timeline
```

### Phase 1 — Project Brief

Opus writes a 1-page Markdown brief with **fixed sections** so the
Phase 2 prompt has predictable anchors:

```
## Persona            (concrete person, not a segment)
## Use-cases          (3-5, real jobs)
## Scope (in / out)   (must-have features + explicit non-goals)
## Milestones         (4-6 with done-criteria)
## Recommended stack  (concrete picks + 1-line rationale)
## Pricing direction  (1-2 sentences)
## Risks              (3 bullets + mitigations)
```

**Endpoint:** `POST /api/conductor/brief` with `{idea, constraints?}`.
Returns a regular `run_id`. Stream via existing `/api/runs/<id>/stream`
SSE channel.

### Phase 2 — Workflow JSON

Opus emits one fenced ` ```json ` block matching CG's preset schema.
The system prompt includes:

- The full ALLOWED MODELS list (claude-* + gemini-* OAuth subset)
- The CANONICAL ROLES list (Visionary, Strategist, Researcher,
  Architect, Designer, Engineer, Writer, QA, Critic, Operator —
  see `docs/MODEL-LIMITS.md`)
- The approved Phase 1 brief as ground truth
- 4–12 agent cap, no cycles, no forward refs
- Cross-vendor pairing rules for refinement loops (`iterate_with`)

**Endpoint:** `POST /api/conductor/compose` with `{brief}`. Returns
`run_id`. Same SSE stream.

### Phase 3 — Validate + launch

Composer's output is read from disk (`composer.out.md` — v44 disk-path),
JSON block extracted, `validate_workflow_spec` checks:

| Check | Action on failure |
|---|---|
| valid JSON | 422 with parse error |
| has id / title / description / spec[] | 422 with missing fields |
| every `agent` ∈ allowed models | 422 with offending value |
| every `role` ∈ canonical roles | 422 with offending value |
| labels unique | 422 |
| `depends_on` points to earlier label | 422 |
| no self-deps | 422 |
| 4 ≤ len(spec) ≤ 12 | 422 |
| `iterate_with` exists if set | 422 |
| `max_rounds` ∈ [1, 10] | 422 |

If valid: `manager.start_run(spec)` spawns the actual run. Returns
`run_id` of the live workflow. UI navigates to it.

**Endpoint:** `POST /api/conductor/launch` with `{compose_run_id, auto_mode?, variables?}`.

## Auto mode (W0.3)

Tick the **🚀 Auto mode** checkbox before clicking Conductor. Effect:

- Phase 1 still streams to the UI (you can watch + Stop).
- Approval gates auto-fire after streaming ends.
- Phase 2 runs immediately. JSON validates. Spec auto-launches.
- Final run executes end-to-end.

Safety rails (planned for v51, currently rely on v45 watchdogs):
- 45-min wall-clock cap on the auto-run
- 2 M token cap
- 12-agent cap (already enforced by Conductor's prompt + validator)
- Per-agent first-token watchdog (90 s, already shipped)
- **Stop** button always visible at the top of the timeline

## Implementation map

| Concern | Lives in |
|---|---|
| System prompts | `src/conductor.py::PHASE1_SYSTEM_PROMPT`, `PHASE2_SYSTEM_PROMPT` |
| Role table | `src/conductor.py::CANONICAL_ROLES` |
| JSON extractor | `src/conductor.py::extract_json_block` |
| Validator | `src/conductor.py::validate_workflow_spec` |
| Endpoints | `src/dashboard.py::conductor_brief / compose / launch / roles` |
| Frontend flow | `src/dashboard_static/dashboard.js::runConductorFlow` |
| Frontend panel | `src/dashboard_static/index.html::#conductor-panel` |
| Tests | `tests/test_conductor.py` (23 cases) |

## What's NOT shipped yet

These are in the validator (so Conductor *can* generate them) but the
run engine doesn't execute them yet. Stripped before launch:

- **`iterate_with` refinement loops (W0.2)** — Designer ↔ Critic
  multi-round exchange. Engine plumbing planned.
- **`tool:<mcp-name>` agent kind (W0.1)** — Open Design / Stitch /
  Canva / Figma dispatched directly by orchestrator. Needs MCP client
  research.
- **Approval gates inside generated workflows** — currently every
  generated run is effectively auto-mode end-to-end (W3 timeline UI
  will surface gates).

When these ship, Conductor's prompt automatically uses them — the
prompt already mentions `iterate_with` + `max_rounds` and the validator
already checks them.

## Demo line

> "I type one sentence. Opus designs a 6-agent team — Visionary,
> Architect, Designer, Engineer, QA, Operator — picks Claude where
> reasoning matters, Gemini where creativity matters, runs the whole
> thing on my own subscriptions. No credits, no templates. From idea
> to working thing."
