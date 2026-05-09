# Strategic upgrade roadmap — driven by market analysis (2026-05-09)

**Source:** "ClaudeGravity: návrh ultra‑jednoduchého multiagentního automation systému"
(Hustler's market research MD, 339 lines, references CrewAI / LangGraph / AutoGen / OpenAI
Agents / Gumloop / Lindy / Make / n8n / Zapier).

**Baseline:** CG v45 @ master `ca7642f`. Multi-vendor agent orchestrator, 30 presets,
idea-to-app verified 4/7 end-to-end, 4-layer timeout reliability.

**Goal:** strategic positioning + missing killer features for the "idea → shipped project"
video demo. Not another UI tweak round.

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

## Implementation order (proposed v46-v48 sprint)

```
v46 (1 session)  — W2 role rebranding + W5 mission library tiles
                   → ships visible polish first, low risk

v47 (1 session)  — W1 Visionary intake + W4 replay-from-here
                   → backend engine work, both touch run state machine

v48 (1.5 sess.)  — W3 Mission Mode timeline UI
                   → frontend rewrite of the run view, builds on v47 data shape
                   → THIS is the video-demo screen
```

End state by v48: idea-to-app demo flow becomes:

1. User clicks **🚀 App builder** tile → picks **Idea → full app**.
2. Types 2 sentences. Clicks Run.
3. Visionary returns a 1-page Project Brief in 30 s. Timeline pauses on
   **⏸ Awaiting approval**. User reads, edits one bullet, clicks **✅ Approve**.
4. Architect → Designer → Engineer → QA → Critic → Operator run as a live timeline.
   No nodes visible. Replay-from-here on every step.
5. Click **📦 Save project**. Files on disk. Done.

That's the video.

---

## Open questions for Hustler before v46 kicks off

1. **Role naming in CZ vs EN.** Visionary or Vizionář? Engineer or Engineer? Analysis
   uses CZ in places. Suggest: keep EN role names (international audience) but CZ
   tooltip/description. Confirm?
2. **Visionary brief format — fixed Markdown sections or free-form?** Suggest fixed
   sections (Persona / Use-cases / Scope / Milestones / Stack / Pricing) so downstream
   agents can parse predictable headings.
3. **Approval gates default ON or OFF for idea→ presets?** Suggest ON for `idea-to-app`
   only; the content/pitch-deck variants run shorter and approval-fatigue would hurt.
4. **Mission Library tile order.** Suggest "App builder" first (matches video focus).
5. **Replay-from-here cancel semantics.** When user clicks replay on step N, do we kill
   running step N+1? Suggest yes (no point producing output that depends on stale data).

---

## Cross-references

- Source analysis: `C:\Users\Hustler\Downloads\ClaudeGravity návrh ultra‑jednoduchého multiagentního automation systému nové generace.md`
- Memory handoff: `~/.claude/projects/D--CLAUDE-CLAUDEGRAVITY/memory/2026-05-09-cg-v45-handoff.md`
- Current state: `D:\CG\docs\MODEL-LIMITS.md`, `D:\CG\docs\PRESETS.md`
- Test run baseline: `D:\CG\notes\test-runs\2026-05-09-test-run-1.md`
- Previous redesign docs (still valid): `D:\CG\notes\redesign-master-plan.md`
