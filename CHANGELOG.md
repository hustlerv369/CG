# Changelog

All notable changes to CG (the multi-agent orchestrator).

Format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning is the dashboard's `vN` tag in commit messages — there is no
separate semver release; the GitHub master branch is the source of truth.

## v18–v27 — 2026-05-08 — Hustler Claude Gravity redesign

### v27 — 2026-05-08 — Drag-to-connect (`14b07b8`)
- SVG ports on each Visual canvas node (output right · input left)
- Wire-drag from output port → ghost bezier with marching dashed line +
  drop-shadow follows cursor (correct under any zoom/pan)
- Drop on input port adds `depends_on` in classic designer (source of
  truth), idempotent, with toast confirmation
- Esc + pointerup-elsewhere cancel cleanly; self-loops blocked
- Closes the last n8n-parity gap (could only delete connections before)

### v26 — 2026-05-08 — ANSI parser + Terminal/Visual rebrand (`d1b3845`)
- New `ansiToHtml()` handles SGR escape sequences in raw view mode:
  8 base colors + bright variants (FG + BG), bold, dim, underline,
  256-color palette, true-color (rgb), proper reset, non-SGR CSI strip
- ANSI palette tuned for warm-black background (bright-red is
  Hustler coral — errors pop in brand color)
- Auto-applied per panel: zero overhead for clean streams (quick reject
  on missing 0x1B), `.ansi-rendered` class swap when colors detected
- 📋 Classic toggle renamed to ⌨ Terminal (matches user mental model);
  active segment now uses full accent gradient with depth shadow
- ◇ Visual gets cleaner mark; toggle widened with monospace icons



A six-commit shell redesign that takes the dashboard from "experimental
custom" to a unified premium product. No backend or API contract changes
— pure UI/UX upgrade across `index.html`, `dashboard.css`, `dashboard.js`.

Driving documents (sub-agent research):
- `notes/redesign-competitor-analysis.md` — CMUX, Claude Squad, n8n,
  Linear, Mac, Warp, Charm — patterns to steal
- `notes/redesign-current-state-audit.md` — 7-section inventory + pain
  points + reusable bones + hard constraints
- `notes/redesign-wireframe-spec.md` — 3 layout proposals + recommendation
- `notes/redesign-master-plan.md` — implementation roadmap

### v25 — 2026-05-08 — Inspector rail (`066e602`)
- New 340px right rail (toggle-able): contextual panel for selected agent
- Click any agent panel → populates inspector + opens; selected panel
  gets accent ring
- Three sections: Agent (label, model, family, depends, streaming) ·
  Live state (status pill, elapsed, output size, token estimate) · Prompt
  (full text, monospace box, 280px max-height + scroll)
- Three actions: Copy prompt · Copy output · Jump to designer row
  (target row flashes coral for 1.1s)
- Live-refreshes on SSE status events for the focused agent
- Toolbar button "⌖ inspector" + keyboard "i" + double-click right
  gutter to close; visibility persisted in localStorage
- Grid extends from 5 to 7 columns when shown (rail | g | designer |
  g | monitor | g | inspector); --cg-col-3 width persisted

### v24 — 2026-05-08 — Workspace rail polish + docs (`9ce5c95`)
- Workspace cards: warm-tinted hover, accent-gradient stripe on active,
  red close-button on hover, smoother motion + token-aligned spacing
- `+ new workspace` button: dashed accent border, fills with coral on hover
- README / CHANGELOG / RESUME-FROM-NEW-SESSION refreshed for v18-v24

### v23 — 2026-05-08 — Brand header + Settings accordion (`3a1e397`)
- Inline-SVG brand mark (gradient orbital atom), wordmark + sub-line
- Header search-bar opens ⌘K palette
- Settings split into 8 native `<details>` accordion sections — kills
  the scrollwall flagged by the audit
- History list cards + monitor empty state polish

### v22 — 2026-05-08 — CMUX-style grid layout selector (`a938d68`)
- 5-position layout toggle in monitor toolbar:
  ⊞ auto · ▢ single · ⊟ 2-col · ⊠ 2×2 · ▦ compact
- Persists choice to `localStorage[cg.layoutMode.v1]`
- Single mode hides siblings beyond the first agent (focus mode)

### v21 — 2026-05-08 — Warp-style block agent panes (`8ce8e1c`)
- 3px state-driven left border per status (queued / waiting / running /
  done / failed / cancelled), coral side-glow when running
- 8px family-coded dot in title (claude / gemini / browser / opencode)
- Inline `MM:SS` elapsed timer, ticks live during running, freezes on done
- `~Nk tok` token-count chip estimated from log buffer length
- Hover-revealed action buttons: ⧉ copy log · ⛶ fullscreen mode
- Sticky-bottom auto-scroll with user scroll-up release
- Status badge gets explicit DOM dot (replaces ::before) for flex-safety

### v20 — 2026-05-08 — Resizable layout gutters (`aabd7c0`)
- Two draggable 5px gutters between workspaces rail | designer | monitor
- Drag to resize, double-click to collapse, persist to
  `localStorage[cg.layout.v1]`
- Keyboard: Ctrl+\\ collapses rail, Ctrl+Shift+\\ collapses designer
- Bounded sizes (col1 0–240px, col2 240–720px clipped to window)

### v19 — 2026-05-08 — Status bar + ⌘K command palette (`075221f`)
- Bottom 28px status bar: backend dot · runs · queued · tunnel · build
- Live elapsed timer for active run; click-to-jump segments
- Linear/Warp-style command palette: fuzzy search across tabs, presets,
  saved workflows, recent runs, settings actions
- Keyboard: ⌘K / Ctrl+K open, ↑↓ navigate, Enter execute, Esc close

### v18 — 2026-05-08 — Hustler Claude Gravity design tokens (`cbf6192`)
- Replace Revolut purple with Hustler coral (`#FF7A59`) + amber gradient
- Full `--space-1..8` (4-64px) and `--fs-micro..3xl` type scales
- Motion tokens (`--motion-micro/fast/slow/spring`) and z-index scale
- Body radial glow: coral + amber instead of purple/blue
- Visual canvas status colors unified with tokens (running uses --accent)
- Drop 10x `var(--accent, #a78bfa)` fallbacks → clean `var(--accent)`
- Move toast() inline cssText to `.cg-toast` utility class
- Universal accent focus ring; family accents extended (browser /
  opencode / custom gold)
- Bug fix: stray duplicate `</main>` at index.html:154-156

## v17 — 2026-05-07 — Autonomous browser pilot (`c04f991`)

### Added
- **`browser-pilot` agent type.** A goal-driven loop closing the gap
  between a Playwright session and an LLM. One natural-language goal
  drives a real browser through up to N steps without further human
  input.
- **Per-iteration snapshot.** `_pilot_capture_state()` captures URL,
  title, ~6 KB of body text, the first 60 visible interactive elements
  with synthesized stable selectors, and a viewport screenshot saved
  under `outputs/screenshots/`.
- **LLM in the loop.** Snapshot + last 6 actions + goal are rendered
  into a compact prompt with a JSON-only response contract and piped
  through any subprocess-based AGENT_KINDS entry (defaults to
  `claude-sonnet-4-6`, so the Pro subscription drives it).
- **Tolerant parser.** `_pilot_ask_llm()` recovers the action JSON
  from ```json fences and surrounding prose by extracting the first
  balanced `{...}` block.
- **Unified action set.** Actions dispatch through the existing
  `_run_browser_step` so everything in v9's browser agent is reusable
  (goto / click / fill / extract / scroll / wait), plus a `done`
  action that ends the loop with a final answer.
- **Bindings.** `run.bindings[label] = {steps, answer, error?}` so a
  follow-up agent can post-process the trace.

### Frontend
- Agent dropdown gains explicit family labels and ordering (Claude,
  Gemini, DeepSeek, Moonshot, GLM, Qwen, Llama, Mistral, OpenCode,
  Browser, Sub-workflow, Custom).
- Two new presets ship: **🤖 Browser Pilot — autonomous web search**
  and **🤖 Browser Pilot → Claude summary**.

### Tests
- +4 (parser happy path, fenced JSON, garbage output, registration).
- 122 → 126 passing.

## v16 — 2026-05-07 — Visual workflow canvas (`14f3827`)

### Added
- **Toggle Classic ↔ Visual** at the top of the workflow designer.
  Classic remains the source of truth — visual mode reads via
  `readSpec()` and writes back via inline edit / palette / row patches.
- **SVG node graph.** Auto-laid-out by topological depth; Bezier
  connection lines with arrow markers; grid background; auto-resizing
  viewBox.
- **Drag-to-reposition.** Pointer-based dragging on each node with
  positions persisted per workspace in `draft.positions`.
- **Inline node edit.** Click a node body to toggle an edit panel
  (model dropdown / label / depends_on / prompt). Saving patches the
  matching classic row.
- **Add / remove.** `+ node` opens a palette modal listing every
  agent kind with family emoji + summary. `×` on a node removes it.
- **Connection editing.** Click a Bezier path to remove that
  `depends_on`.
- **Live status overlays.** SSE handlers also call
  `visualUpdateAgentStatus()` so during a run each node shows the
  status pill, color border (queued / running / done / failed), pulse
  glow when running, and the latest log line in muted accent.
  Connections feeding a running node mark themselves "flowing".
- **`auto-layout` button** forgets saved positions and re-runs
  topological layout.

### Bug fix found during testing
- `_list_workflow_files()` no longer crashes when a workflow file on
  disk is corrupt / non-dict (defensive `isinstance` + `spec=[]`
  fallback).

### Tests
- 121 → 122 (front-end change; coverage unchanged for the new code).

## v15 — 2026-05-07 — More models (`ba93b1a`)

### Added
- **OpenRouter (`OPENROUTER_API_KEY`):** `or-deepseek-r1`,
  `or-kimi-k2`, `or-llama-3.3`, `or-mistral-large`.
- **DeepSeek API direct (`DEEPSEEK_API_KEY`):** `deepseek-chat`,
  `deepseek-reasoner` (R1-class).
- **Moonshot direct (`MOONSHOT_API_KEY`):** `kimi-k2-direct`.
- **OpenCode CLI** (sst/opencode) — subscription-style entry running
  `opencode run` headless. Bring your own provider config; no API key
  charged by CG.

### Tests
- +3 (each new key surfaces its model ids; family allowlist extended
  for new families: deepseek / moonshot / llama / mistral / qwen /
  glm / opencode). 120 → 122 passing.

## v14 — 2026-05-07 — Workspace tabs (`e7ef570`)

### Added
- **CMUX-style workspace tabs.** A 56px vertical rail on the far-left of
  the Orchestrator tab lists every workspace as a stacked card. Each
  workspace is one independent draft of the workflow designer (title +
  agent rows). State persists per-browser in `localStorage` under
  `cg.workspaces` and `cg.workspaces.active`.
- **Workspace UX.** `+` creates a new workspace and switches to it.
  Click switches (auto-persisting the current draft into the previously
  active workspace first). Double-click renames. Hover and `×` deletes
  with confirm. The last remaining workspace cannot be removed.
- **Refresh-safe.** A `beforeunload` listener persists the active draft
  on page unload so reloads keep edits.
- **Responsive.** ≤1080px → 48px+320px+1fr; ≤720px → row-stacks the rail
  above the designer.

### Internal
- New `initWorkspaces()` runs after agents/presets load and applies the
  active workspace's draft, replacing the default "one empty row" seed
  when a saved draft exists.
- Layout uses the `main#tab-orchestrator.tab-pane.active` selector so
  only the orchestrator tab grows the third column — Editor / Notes /
  Settings are unchanged.

## v13 — 2026-05-07 — Browser step builder (`be7b2fb`)

### Added
- **Drag-free visual builder for the `browser` agent.** Selecting
  `🌐 Browser` from the agent dropdown swaps the plain prompt textarea
  for a sortable list of step cards.
- **Full action coverage.** Builder exposes all 16 actions matching
  `dashboard.py::_run_browser_step`: goto, click, fill, type, press,
  hover, scroll, wait_for, extract, extract_all, screenshot, evaluate,
  title, content, url, accept_dialog, pdf.
- **Per-action fields.** Each card dynamically renders the parameters
  its action expects (text / number / textarea / checkbox), plus an
  optional `bind_as` for downstream `{{label.field}}` references.
- **Reorder / remove controls.** ↑ / ↓ buttons on each card, × removes.
- **Escape hatch.** A `{ } JSON` toggle flips the row into raw-JSON
  mode for power use beyond the form schema.

### Internal
- `BROWSER_ACTIONS` JS array is the single source of truth for the form
  schema and stays in lock-step with the backend runner.
- `readSpec()` serializes cards to `{"steps": [...]}` JSON when the
  builder is active, so the backend payload is identical to the one it
  has always accepted.
- Existing presets and saved workflows that ship raw JSON are seeded
  back into cards via best-effort `JSON.parse`.

### Notes
- Frontend-only change. No backend modifications. 120 tests still pass.

## v12 — 2026-05-07 — Token-by-token streaming (`befc96a`)

### Added
- **Per-step opt-in streaming** for `claude` and `gemini` agents. A
  `stream` checkbox on each agent row, persisted through workflow
  save/load and run rerun.
- **Stream-json passthrough.** When enabled, the dashboard appends
  `--output-format stream-json --verbose` (claude) or
  `--output-format stream-json` (gemini) to the underlying CLI command.
- **Live token deltas.** Each NDJSON line is parsed in the stdout loop;
  assistant text content is emitted as its own log event so the existing
  SSE channel renders tokens as they arrive. `{event: "log", data: {…,
  stream: true}}` lets the UI mark stream-mode lines if it wants to.
- **Filtered noise.** `system / init / result / tool_use / hook` events
  are filtered out of the visible log.

### Changed
- `AgentRunState` gains a `streaming: bool` field (round-tripped through
  the public API as `streaming` on each agent record).

### Internal
- New helper `_parse_stream_json_line(family, line)` returns:
  - `None` for non-JSON (caller falls back to the raw-emit path)
  - `[]` for filtered system events
  - a list of text deltas for assistant message content
- Tolerates unknown families and bad JSON — non-JSON lines reach the log
  verbatim, so streaming never silently swallows output.

### Tests
- +7 tests: 5 parser unit (claude/gemini happy path, filter, non-JSON,
  unknown family) + 2 end-to-end (streaming flag round-trip + assistant
  deltas reach the log via mock NDJSON script).
- Total: 113 → 120 passing.

## v11 — 2026-05-06 — Sub-workflows + browser auth wizard (`df3431b`)

### Added
- **`subworkflow` agent type** — one workflow can call another saved
  workflow as a step; child outputs surface as `{{label.subagent}}` for
  the parent.
- **Browser auth wizard.** 5 endpoints under `/api/browser-auth/*` for a
  headed Chromium login flow that saves `storage_state` to disk for
  later authenticated scraping.

## v10 — 2026-05-06 — Tunnel + phone dispatch + notifications (`73b40d3`)

### Added
- Cloudflare Tunnel auto-launch (auto-downloads `cloudflared`)
- `POST /api/phone-dispatch` — mobile-friendly entry point (iOS
  Shortcuts ready)
- Run-finished webhooks: ntfy.sh / Discord / Slack / generic JSON POST

## v9 — 2026-05-06 — `browser` agent type (`f9bedd7`)

### Added
- `runner: "browser"` Playwright agent with 16 actions
  (goto/click/fill/extract/screenshot/evaluate/…), cross-step bindings
  via `{{label.field}}`.

## v8 — 2026-05-06 — Playwright web placeholders (`b9dd46b`)

### Added
- `{{web:URL}}`, `{{web-shot:URL}}` placeholders backed by headless
  Chromium. SEO + competitor presets.

## v7 — 2026-05-06 — n8n-grade automation (`307e308`)

### Added
- Custom HTTP tool agents (any OpenAI-compatible endpoint)
- Webhook triggers: `POST /api/triggers/<workflow>`
- Cron-style scheduler for periodic runs
- `${VAR}` substitution per project

## v6 — 2026-05-06 — Notes + Settings tabs (`24f2d05`)

### Added
- Obsidian-style notes with `[[wikilinks]]`, backlinks, search
- Settings panel for API keys + per-project defaults
  (browser-localStorage, forwarded to backend on each run)

## v5 — 2026-05-06 — Multi-provider + inline editor + workflow gen (`15d532f`)

### Added
- OpenRouter / Z.ai / Anthropic API / Gemini API opt-in HTTP runners
- Inline file editor (CodeMirror) with file tree + atomic save
- `workflow_gen.py` helper for orchestrating Claude Code sessions
- ToS doc

## v4 — 2026-05-06 — Context placeholders + workflows on disk (`6dc3cb2`)

### Added
- `{{file:path}}` / `{{git:diff}}` / `{{git:log:5}}` / `{{shell:…}}`
- Workflow JSON files on disk (`D:\CG\workflows\*.json`)
- Markdown / diff render view-toggle
- Run report export (single Markdown bundle)

## v3 — 2026-05-06 — Model selector + Apple/Revolut UI (`564c320`)

### Added
- 6 subscription models (Claude Sonnet 4.6, Opus 4.7, Opus 4.6, Gemini
  Flash / Pro / 3 Pro)
- Apple + Revolut dark redesign (glassmorphism, purple accent)

## v2 — 2026-05-06 — Sequential pipelines + dashboard groundwork

### Added
- `depends_on` + `{{label}}` substitution for sequential pipelines
- Cancel / save / browser notifications / keyboard shortcuts

## v1 — 2026-05-05 — Web dashboard (`07134cb`)

### Added
- FastAPI + vanilla-JS web app at `http://127.0.0.1:8765`
- 3 bundled presets (compare / pipeline / fan-out)
- Per-agent live SSE panels
- Run history sidebar

## v0 — 2026-05-05 — Genesis (`de2d730`)

### Added
- Single-file orchestrator (`src/cg.py`)
- Headless `claude --print` + `gemini -p` parallel subprocess dispatch
- Task store + run history (`tasks/_index.json`)
- End-to-end smoke test
