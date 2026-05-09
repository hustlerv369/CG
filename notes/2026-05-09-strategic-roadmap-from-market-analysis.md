# Strategic upgrade roadmap — driven by market analysis (2026-05-09)

**Source:** "ClaudeGravity: návrh ultra‑jednoduchého multiagentního automation systému"
(Hustler's market research MD, 339 lines, references CrewAI / LangGraph / AutoGen / OpenAI
Agents / Gumloop / Lindy / Make / n8n / Zapier).

**Baseline:** CG v45 @ master `ca7642f`. Multi-vendor agent orchestrator, 30 presets,
idea-to-app verified 4/7 end-to-end, 4-layer timeout reliability.

**Goal:** strategic positioning + missing killer features for the "idea → shipped project"
video demo. Not another UI tweak round.

---

## 🎯 W0 — The Conductor (THE killer feature)

> **Hustler's framing (2026-05-09):** *"Idea → Opus dostane to → vymyslí kompletní
> workflow → vytvoří sestavení modelů na daný projekt → spustí se kompletní automatizace
> → z nápadu se dostane k finálnímu produktu. FROM IDEA TO WORKING THING."*

This is **THE differentiator**. Every other tool in the analysis (Gumloop, Lindy, Zapier,
Make, n8n) ships **fixed templates** the user picks from. CG ships a **Conductor** —
Opus 4.7 reads your idea and *designs the team itself*, picking models per role based on
the same MODEL-LIMITS heuristics a human engineer would use.

### Why it leapfrogs the analysis itself

The analysis recommends "templated missions" (presets like `idea-to-app`). Conductor
makes that a fallback, not the headline. The headline becomes:

> *"You don't pick a template. You describe an idea. Conductor designs a custom team
> for that specific idea, in 30 seconds, using the models you already pay for."*

No competitor does this today. CrewAI / LangGraph make you *write* the agent definitions.
Gumloop / Lindy give you *fixed templates*. Conductor closes the gap.

### Feasibility — yes, ships in 1–2 sessions

| Capability needed | Already in CG | Risk / mitigation |
|---|---|---|
| JSON workflow schema (`spec[]` with agent/label/prompt/depends_on) | ✅ used by 30 presets + `📋 paste` flow | none |
| Strong structured-JSON generation | ✅ Opus 4.7 1M context, proven | invalid JSON → schema validator + 1 retry |
| Model selection heuristics knowledge | ✅ `docs/MODEL-LIMITS.md` rule-of-thumb table | feed it as system prompt |
| 30 example workflows as few-shot | ✅ `workflows/*.json` + builtin PRESETS | Opus pattern-matches directly |
| Engine that runs an arbitrary JSON spec | ✅ same path as preset runner | none |
| Model whitelist (no hallucinated names) | ⚠️ to add (5 lines) | hardcoded list in `dashboard.py` |
| Cycle detection in `depends_on` | ⚠️ to add | topological sort + raise on cycle |
| Soft cap on team size (≤12 agents) | ⚠️ to add | constraint in Conductor's prompt |

**Honest limits:**
- Opus may emit 8 KB JSON in 30–60 s. Fine.
- Vague ideas ("make me something cool") yield generic plans → Conductor's prompt
  forces a clarification round-trip if confidence is low.
- Quality varies → **2-phase generation** below mitigates.

### 2-phase generation (the trick that makes this reliable)

Splitting **thinking** from **structuring** dramatically raises hit rate:

**Phase 1 — Brief (creative, where Opus shines):**
- Input: raw user idea + constraints (time/budget/stack)
- Output: plain-Markdown **Project Brief** with predictable headings
  (Persona / Use-cases / Scope / Milestones / Recommended stack / Suggested pricing)
- Streams to UI in real time. User reads, edits, approves OR clicks 🔁 re-conduct.

**Phase 2 — Workflow JSON (mechanical, where strict schema matters):**
- Input: approved Brief + MODEL-LIMITS heuristics + JSON schema + 3 best example presets
- Output: validated `spec[]` JSON with role-named labels (Visionary/Architect/Engineer/QA/...),
  model assignments, prompts, dependencies
- Schema validator catches errors → 1 auto-retry with the validation error fed back.

### UX flow (replaces the current `idea-to-app` preset as the hero)

```
Quick Start hero:
  ┌─────────────────────────────────────────────┐
  │  💡 What do you want to build today?         │
  │  ┌───────────────────────────────────────┐   │
  │  │ [your idea — 1-3 sentences]           │   │
  │  └───────────────────────────────────────┘   │
  │                                              │
  │  [✨ Conductor — design my team]             │
  │  [📋 Use template instead]                   │
  └─────────────────────────────────────────────┘

Click Conductor →
  ⏳ "Opus is designing your team..." (30-60 s)
  ↓
  📋 Project Brief (Markdown, editable inline):
     Persona / Use-cases / Scope / Milestones / Stack / Pricing
     [✅ Approve & generate workflow]  [✏️ Edit brief]  [🔁 Re-conduct]
  ↓
  🎯 "Here's the team Conductor built for you"
     Timeline preview — 6 role-badged agents, model assignments,
     dependencies visible, est. duration: ~18 min
     [▶ Run]  [✏️ Edit team before run]  [🔁 Re-conduct]
  ↓
  🚀 Mission Mode timeline (W3 below) — live execution
  ↓
  📦 Save project
```

### Implementation outline (concrete enough to ship)

1. **New endpoint `POST /api/conductor/brief`** — input `{idea, constraints?}` → streams
   Phase 1 Brief Markdown. Calls `claude --print` with `claude-opus-4-7` and a system
   prompt that loads `docs/MODEL-LIMITS.md` heuristics + a list of available models.
2. **New endpoint `POST /api/conductor/compose`** — input `{approved_brief}` → streams
   Phase 2 plan JSON. Same Opus, different system prompt that requires JSON Schema
   compliance + injects 3 best preset examples as few-shot.
3. **Schema validator** — JSON Schema for `{id, title, description, variables, spec[]}`,
   per-step required fields, model whitelist, no cycles in `depends_on`, ≤12 agents.
4. **Generated-workflow preview UI** — dashboard renders the proposed spec as a
   read-only timeline (reusing W3 components). Edit button drops user into Visual
   canvas with the spec preloaded.
5. **Run path** — identical to existing preset flow. Conductor-generated specs are
   "presets that didn't exist 60 s ago".

### Why this also strengthens W1–W5

- **W1 (Visionary intake):** Conductor's Phase 1 Brief **is** the Visionary intake.
  W0 absorbs W1 — they're not parallel work.
- **W2 (role rebranding):** Conductor's prompt instructs it to label agents with role
  names. W2 must ship first or alongside, so Conductor has a vocabulary to use.
- **W3 (Mission Mode timeline):** Conductor-generated workflows are dynamic, so the
  static-canvas Visual mode is the wrong default for them. Mission Mode is the correct
  default for any Conductor run.
- **W4 (replay-from-here):** unchanged — works the same on Conductor-generated specs
  because they're regular JSON specs.
- **W5 (Mission Library tiles):** becomes the **fallback** path. Quick Start hero
  shows "✨ Conductor" as primary, "📋 Use template" as secondary. Templates serve
  users who don't know what they want and need to browse.

### Demo line for the video

> *"Watch this. I type one sentence. Opus designs a 6-agent team — Visionary, Architect,
> Designer, Engineer, QA, Operator — picks Claude where reasoning matters, Gemini where
> creativity matters, and runs the whole thing on my own subscriptions. No credits, no
> templates, no node graph. From idea to working thing."*

---

## Where CG already wins (reuse the messaging in the demo)

The analysis prescribes these as differentiators. CG already has them — lean on this:

1. **BYOS / BYOK (own subscriptions, no platform credits).** CG runs on Claude OAuth Pro +
   Gemini OAuth Google. Zero API-key billing. The analysis explicitly cites Warp Terminal
   as the reference — CG matches that and applies it to a *full* automation orchestrator,
   which Warp does not.
2. **Multi-agent as first class.** Subprocess Claude + Gemini paralelně, mixed in one run.
   Already shipped in v43.
3. **No platform credits / no per-task pricing.** Self-hosted, free, GPL.
4. **From idea to shipped is the hero.** Quick Start banner + 3 idea→ flagship presets
   (`idea-to-app`, `idea-to-content-plan`, `idea-to-pitch-deck`) since v40.
5. **Cross-vendor diversity by design.** v44 Gemini "TEXT ONLY" preamble + v45 first-token
   watchdog turn the previously unreliable "mix vendors" idea into a stable default.

**Demo line:** *"Není to AI wrapper. Je to router nad tvými existujícími předplatnými,
co řídí tým agentů místo tebe."*

---

## Where CG is leaving value on the table (the gaps)

| Analysis prescription | CG v45 reality | Gap severity |
|---|---|---|
| **Role-based mental model** — Visionary, Researcher, Architect, Designer, Engineer, QA, Operator | Agents named by *step* (director, designer, architect, implementation, tests, reviewer, readme-deploy). Function-first, not role-first. | **HIGH** |
| **Project Blueprint — idea becomes a structured brief the user reviews BEFORE execution** | `idea-to-app` jumps from raw prompt straight to director → architect. No intake brief. | **HIGH** |
| **Human-in-the-loop checkpoints as default** | Run is fire-and-forget. 7 steps, ~20 min, you watch passively. | **HIGH** |
| **Story mode (Level 1 UI) — timeline + checklist, no node graph visible** | Only Terminal & Visual modes — both show steps as nodes / linear rows. | **HIGH** |
| **Mission timeline + replay-from-here** | If step 5 fails, you re-run from step 1. v45 fixed reliability but not recoverability. | **MEDIUM** |
| **Mission Library — categorized tiles (App / Automation / Audit / Redesign / Content factory)** | 30 presets in a flat dropdown. Onboarding is "scroll and read titles". | **MEDIUM** |
| **Intelligence Source registry (Add Ollama / Perplexity / Groq, tag with capabilities)** | Models hardcoded per preset. | **LOW** (nice-to-have) |
| **Operator playbooks (uploadable desktop macros)** | Playwright browser agents already exist. Native desktop control out of scope. | **LOW** (post-video) |

---

## Top 5 wins, prioritized for the video demo

Each win is **scoped to ship in 1–2 sessions**, builds on existing v45 plumbing, and
directly improves "raw idea → finished project" storyline.

### 🥇 W1 — Visionary intake step + reviewable Project Brief
**Effort:** 1 session
**Demo impact:** ⭐⭐⭐⭐⭐ (the single biggest upgrade)
**Files:** `src/dashboard.py` (idea-to-app preset), new step `visionary` before `director`

**What changes:**
- Insert a new step #0 `visionary` (Claude Opus 4.7) into `idea-to-app`. Output is a
  structured **Project Brief**: target persona, 3 use-cases, scope (in/out), 5 milestones,
  recommended stack, suggested pricing tier — all in Markdown sections.
- After visionary completes, the run **pauses** until the user clicks **"✅ Approve & start
  team"** or edits the brief inline + clicks **"🔁 Re-run visionary"**.
- The brief's content becomes `${PROJECT_BRIEF}` available to all downstream agents (so
  director / architect / designer all read the same approved scope).

**Why it wins the demo:** turns "give it a 2-line prompt and pray" into "give it 2 lines,
get back a 1-page exec brief, edit a sentence, click go". This is the analysis's
"Idea → Project Blueprint" promise made concrete.

**Carries through to W3 (checkpoints).**

---

### 🥈 W2 — Role rebranding (Visionary / Researcher / Architect / Designer / Engineer / QA / Operator)
**Effort:** 0.5 session
**Demo impact:** ⭐⭐⭐⭐ (mental-model upgrade visible everywhere)
**Files:** all `idea-to-*` presets, dashboard JS labels, MODEL-LIMITS.md heuristics table

**What changes:**
- Rename agent labels in **all flagship presets** (idea-to-app, idea-to-content-plan,
  idea-to-pitch-deck, design-brief-to-concepts, code-pr-review, research-deep-dive):
  - `director` → `Visionary` (idea-to-app) or `Strategist`
  - `architect` → `Architect` (already aligned)
  - `implementation` → `Engineer`
  - `designer` → `Designer` (already aligned)
  - `tests` → `QA`
  - `reviewer` → `Critic`
  - `readme-deploy` → `Operator`
- Add a **role badge** to each agent card in the dashboard: 🔭 Visionary, 🔬 Researcher,
  🏛 Architect, 🎨 Designer, 🛠 Engineer, 🧪 QA, 📡 Operator.
- The **model assignment** stays underneath as a "powered by Claude Opus / Gemini Pro"
  subtitle. User now thinks in *roles* (analysis principle), not in *which model is at step 4*.

**Why it wins the demo:** the analysis explicitly says *"the user should think in roles, not
nodes"*. This is a 30-minute refactor that aligns CG's vocabulary with how every modern
agent framework (CrewAI, OpenAI Agents) talks about itself — and how the demo voiceover
will sound natural ("Visionary defines the scope, Architect designs the system, Engineer
ships the code").

---

### 🥉 W3 — Mission Mode (Level 1 UI): timeline + approval gates, hide the graph
**Effort:** 1.5 sessions
**Demo impact:** ⭐⭐⭐⭐⭐ (THE story-mode promise)
**Files:** `src/dashboard_static/index.html`, `dashboard.css`, `dashboard.js`

**What changes:**
- New **Mission Mode** toggle in the top bar (default ON for idea→ presets). Hides the
  Terminal & Visual canvases entirely.
- Replaces them with a **vertical timeline**:
  - Phase header → role icon + role name + 1-line "what they do"
  - Status pill (Queued / Running / **⏸ Awaiting approval** / Done / Failed)
  - Live token count + ETA
  - Inline preview of the agent's last 200 chars (no full output dump)
  - **Per-step actions:** `🔁 Replay from here`, `📋 View output`, `✏️ Edit prompt & retry`
- "Show advanced graph" link in the corner reveals the existing Visual canvas for power users.
- The gates from W1 (Visionary brief) and W4 (post-Architect) render as full-width
  **approval cards** in the timeline — they block the run until the user acts.

**Why it wins the demo:** this is the screen you record. No nodes, no edges, no jargon —
just a clean "team is shipping your project" view. Matches the analysis's "Level 1 — Story
mode" prescription word-for-word.

**Reuses:** the existing run state machine + WebSocket stream from v44/v45. Just a new
view rendering the same data.

---

### 4️⃣ W4 — Replay-from-here on timeline (resume broken runs)
**Effort:** 0.5 session
**Demo impact:** ⭐⭐⭐ (reliability demo polish — *"step 5 failed? click here, done"*)
**Files:** `src/dashboard.py` (run engine), `dashboard.js` (timeline action handler)

**What changes:**
- Run engine already writes per-agent output to `outputs/dashboard-runs/<id>/<step>.out.md`.
  Add a `POST /api/runs/<id>/replay-from/<step>` endpoint that:
  1. Marks all steps from `<step>` onward as `queued` (resets their state)
  2. Keeps prior steps' outputs intact (they're already on disk)
  3. Re-spawns subprocesses for the queued ones, with `{{upstream}}` references resolving
     from the existing on-disk outputs
- Wire the **"🔁 Replay from here"** button on each timeline step to call this endpoint.

**Why it wins the demo:** if your idea-to-app run crashes at step 6/7 (Reviewer hung,
Operator API quota), you don't lose the 117 KB of code Engineer already produced. One
click and Reviewer reruns from the on-disk Engineer output. v45 reliability story
becomes a "even when it breaks, you don't restart" story.

**Cross-checked vs MODEL-LIMITS.md:** the v44 disk-based export endpoint already proved
that on-disk outputs are authoritative — same pattern reused.

---

### 5️⃣ W5 — Mission Library: 5 category tiles instead of flat preset dropdown
**Effort:** 0.5 session
**Demo impact:** ⭐⭐⭐ (onboarding clarity for first-time viewers of the video)
**Files:** `src/dashboard.py` (PRESETS metadata), `dashboard.css`, `dashboard.js`,
`docs/PRESETS.md`

**What changes:**
- Add a `category` field to each of the 30 presets. Five buckets:
  - **🚀 App builder** — idea-to-app, file-refactor, github-readme-from-code, code-migration-helper (future)
  - **🤖 Automation hub** — pipeline, pipeline-var, fanout, compare, browser-form-test
  - **🔍 Audit & research** — seo-audit, competitor-analysis, research-deep-dive, browser-visual-regression, code-pr-review, github-pr-review, bug-investigation
  - **🎨 Design & content factory** — design-brief-to-concepts, blog-article-full, blog-draft, social-content-fanout, email-drip-5, product-description-3, meeting-to-actions, translate-cz-en, idea-to-content-plan, idea-to-pitch-deck
  - **🌐 Browser ops** — browser-scrape-and-summarize, browser-pilot-search, browser-pilot-summarize
- The Quick Start hero shows **5 category tiles** (large, icon-first). Click → expands a
  panel of 3-7 mission cards in that category. Each card has icon + 2-line description +
  "Start mission" CTA.
- Flat dropdown stays as a "Browse all 30" link for power users.

**Why it wins the demo:** when Hustler records "this is what CG does", the opening shot
is 5 clean tiles, not a 30-item dropdown. Matches the analysis's progressive-disclosure
principle and "templated missions / playbooks" prescription.

---

## What we deliberately defer (post-video)

These came up in the analysis but don't move the demo needle and would dilute the v46 sprint:

- **Intelligence Source registry UI** (add Ollama / Perplexity / Groq via UI). Today the
  user edits the JSON preset to swap models — fine for power users, who are CG's audience
  this quarter. Build the UI when there's actual demand.
- **Native desktop Operator** (computer-use playbooks beyond browser). Playwright agents
  already cover the common case. Native macOS/Windows automation is a separate research
  arc.
- **Granular per-mission billing & team roles.** Single-user tool; multi-tenant work
  would be Q3 if ever.
- **Custom DSL.** Analysis explicitly warns against this. Already aligned.
- **Full Make/Zapier connector parity.** The `{{shell:...}}`, `{{web:...}}`,
  `{{file:...}}` resolvers + `subprocess` agents already cover 90% of integrations.

---

## Implementation order (revised v46-v49 sprint, W0 added)

```
v46 (0.5 sess.) — W2 role rebranding (must precede W0 — Conductor needs the vocabulary)
                  → rename labels in flagship presets, add role badges, MODEL-LIMITS heuristics

v47 (1.5 sess.) — W0 Conductor: Phase 1 Brief endpoint + Phase 2 JSON compose endpoint
                  + schema validator + retry loop + model whitelist + cycle check
                  → THE killer feature; absorbs W1 (Visionary intake)

v48 (1 sess.)   — W3 Mission Mode timeline UI (default view for Conductor runs)
                  + W4 replay-from-here (same backend touch points)
                  → THIS is the video-demo screen

v49 (0.5 sess.) — W5 Mission Library tiles as the secondary "Use template instead" path
                  → polish + onboarding clarity for users who don't know what they want
```

**Sprint cadence:** ~3.5 sessions to video-ready. W0 is the longest single piece because
it's net-new infrastructure (two new endpoints + schema + few-shot construction), but it
reuses the existing run engine end-to-end.

### End-state demo flow (after v49)

1. Open dashboard → Quick Start hero **"💡 What do you want to build today?"**
2. Type 2 sentences. Click **✨ Conductor — design my team**.
3. ⏳ Opus designs the team (30–60 s). Brief streams in.
4. Read 1-page Project Brief. Edit one bullet. Click **✅ Approve & generate workflow**.
5. Phase 2 runs — generated JSON spec appears as a Mission Mode timeline preview:
   "Visionary → Architect → Designer → Engineer → QA → Critic → Operator", model
   assignments visible, est. duration ~18 min.
6. Click **▶ Run**. Live timeline executes. No nodes visible. Replay-from-here on every step.
7. Click **📦 Save project**. Files on disk. Done.

That's the video. ~3 minutes of footage, end-to-end.

### Fallback path (the "📋 Use template" branch)

Users who can't articulate an idea still get a path:

1. Quick Start → **📋 Use template instead** → Mission Library opens
2. 5 category tiles → 30 curated presets (the existing library, just better organized)
3. Same timeline + replay UX as Conductor runs

Both paths converge on Mission Mode timeline. One UI to maintain.

---

## Open questions for Hustler before v46 kicks off

1. **Role naming in CZ vs EN.** Visionary or Vizionář? Engineer or Engineer? Analysis
   uses CZ in places. Suggest: keep EN role names (international audience, also matches
   Conductor's natural output language) but CZ tooltip/description. Confirm?
2. **Conductor failure-mode UX.** If Phase 2 schema validation fails twice, what do
   we show? Suggest: surface the raw JSON in an editor with the validation error
   inline, let user fix-and-run OR click 🔁 re-conduct.
3. **Conductor Phase 1 streaming partial-trust.** If the user tries to click Approve
   before Phase 1 finishes streaming, do we block or wait? Suggest block until streaming
   ends + 1 s grace, then auto-enable Approve.
4. **Brief format — fixed Markdown sections or free-form?** Suggest fixed sections so
   the JSON-compose phase has predictable anchors. Schema: `## Persona / ## Use-cases /
   ## Scope (in/out) / ## Milestones / ## Recommended stack / ## Pricing direction`.
5. **Approval gate after Phase 2 (workflow preview) — always ON or skippable?** Suggest
   ON by default; user can flip "Skip preview, run immediately" in Settings for
   subsequent runs once they trust Conductor.
6. **Mission Library tile order.** Suggest "App builder" first (matches video focus),
   then Automation / Audit / Design / Browser ops.
7. **Replay-from-here cancel semantics.** When user clicks replay on step N, do we kill
   running step N+1? Suggest yes (no point producing output that depends on stale data).
8. **Conductor model — always Opus 4.7, or fall back to Sonnet on capacity errors?**
   Suggest Opus only for design (Phase 1 + 2 both); if Opus is queued >2 min, surface
   "Conductor is queued, retry?" rather than silently downgrading quality.

---

## Cross-references

- Source analysis: `C:\Users\Hustler\Downloads\ClaudeGravity návrh ultra‑jednoduchého multiagentního automation systému nové generace.md`
- Memory handoff: `~/.claude/projects/D--CLAUDE-CLAUDEGRAVITY/memory/2026-05-09-cg-v45-handoff.md`
- Current state: `D:\CG\docs\MODEL-LIMITS.md`, `D:\CG\docs\PRESETS.md`
- Test run baseline: `D:\CG\notes\test-runs\2026-05-09-test-run-1.md`
- Previous redesign docs (still valid): `D:\CG\notes\redesign-master-plan.md`
