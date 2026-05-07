# Changelog

All notable changes to CG (the multi-agent orchestrator).

Format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning is the dashboard's `vN` tag in commit messages — there is no
separate semver release; the GitHub master branch is the source of truth.

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
