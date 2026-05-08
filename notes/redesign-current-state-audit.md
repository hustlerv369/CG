# CG Dashboard — Current-State Audit (pre-redesign)

Source files: `src/dashboard_static/index.html` (366), `dashboard.css` (1846), `dashboard.js` (2673), `src/dashboard.py` (4370).

## 1. Layout inventory

App shell is a single-page app with a fixed `<header>` (h1 + pill tab nav + status pill) and four `<main>` panes that swap via `.tab-pane.active` (`index.html:24-33`).

- **Orchestrator** (`#tab-orchestrator`, `index.html:35-154`) — 3-column grid `56px / 380px / 1fr` (`dashboard.css:188`):
  - Workspaces rail (`.workspaces-rail`, l.37-43) — vertical "WS" cards in localStorage, parallel orchestrator drafts.
  - Designer (`.designer`, l.46-133) — preset select, saved-workflow CRUD, JSON import, title input, **Classic / Visual** toggle (`.view-mode-toggle`, l.82-86), Classic = `#agent-rows`, Visual = SVG node graph (`#visual-canvas` with arrowhead defs, zoom/pan/fit/fullscreen toolbar, l.95-124), Run/Clear actions, History `<ul>`.
  - Monitor (`.monitor`, l.136-153) — title display, 4-way view toggle (raw / markdown / diff / preview), `#agent-grid` of agent panels.
  - In Visual mode, layout flips to `56px / 1fr / 1fr` (`dashboard.css:197`).
- **Editor** (`#tab-editor`, l.158-183) — `280px / 1fr`: file tree + CodeMirror host + dirty pill + save/revert.
- **Notes** (`#tab-notes`, l.185-220) — `280px / 1fr`: sidebar (search, list) + editor (title, tags, preview toggle, `[[wikilinks]]`, `#backlinks-pane`).
- **Settings** (`#tab-settings`, l.222-362) — single scrolling section: API keys (4 providers), project root override, defaults, vars list (`${VAR}` substitution), browser auth states, Cloudflare Tunnel for phone dispatch, run-finished webhook (ntfy/discord/slack/generic).

## 2. Styling system

Design tokens **do exist** (`dashboard.css:15-69`) — surfaces, borders, fg tiers, accents, status, family, fonts, radii, shadows, transition. Inter + JetBrains Mono via CDN (l.12-13). Palette: `--bg-base #0a0a0c`, accent `#8C77FF` (Revolut purple) with gradient to `#B8A4FF`, family accents `--claude #E5A572`, `--gemini #4285F4`, status `#30D158 / #FFD60A / #FF453A`. Radii `8/12/16`, transition `200ms cubic-bezier(0.4,0,0.2,1)`. **No spacing scale token** — paddings hardcoded throughout (e.g. `padding: 14px 24px` l.101, `12px 16px` l.1649, `9px 12px` l.832). Body 13px/1.5. Glass panels via `backdrop-filter: blur(20-24px) saturate(180%)`.

## 3. Multi-agent visualization

Two parallel views, both DOM/JS-driven:

- **Classic / Monitor grid** — `.agent-grid` is `repeat(auto-fit, minmax(420px, 1fr))` with `grid-auto-rows: minmax(240px, 1fr)` (`dashboard.css:1600-1608`). Each `.agent-panel` (built by `buildPanel()` in `dashboard.js:1532-1567`) has head (label + deps + family badge + status badge), `.agent-panel-log` (mono pre-wrap), and foot (char count + copy). Family badges color via `.badge.claude` / `.badge.gemini`.
- **Visual canvas** — single SVG with `<g class="zoom-group"><g class="connections-layer"/><g class="nodes-layer"/></g>` (`index.html:107-117`). Nodes are foreignObject `.vis-node` cards with edit-in-place (model select + prompt textarea), connections are bezier paths with arrow markers, zoom/pan via wheel + drag (state in `window.__visPositions` per workspace, persisted to localStorage).

## 4. Streaming / live data flow

Frontend opens `new EventSource('/api/runs/${runId}/stream')` (`dashboard.js:1495`) and listens for `status`, `snapshot`, `log`, `done` events. Backend uses `sse_starlette.EventSourceResponse` (`dashboard.py:54`); per-agent queues live in `RunManager.streams: dict[(run_id,label), Queue]` (`dashboard.py:917`); streaming families (claude/gemini) get `--output-format stream-json` and lines are parsed into deltas via `_parse_stream_json_line` (l.115, l.1218-1234). Running state shows as `.badge.running` with a pulsing `::before` dot (`dashboard.css:1705-1720`, `@keyframes pulse` l.1737). Visual canvas mirrors with `.vis-node.status-running` (`#38bdf8` glow, `vis-pulse` animation l.1067).

## 5. Pain points

- **Two clashing purples.** Token is `#8C77FF` (l.35) but fallback `#a78bfa` is hardcoded ~10 times (`dashboard.css:229,230,268,271,955,1034,1052,1120,1187` etc.) — different hue. Pick one.
- **Hardcoded status hexes in Visual canvas** (`dashboard.css:1060,1064,1065,1066`) — `#38bdf8 / #22c55e / #ef4444 / #71717a` ignore the existing `--success/--warning/--error` tokens.
- **No spacing scale.** `--radius-*` exists but no `--space-*`; every padding is a magic number.
- **Inline styles in JS toast** (`dashboard.js:1003-1005`) — backgrounds, borders, shadows hardcoded outside the token system.
- **Inline `style="display:none"`** scattered through `index.html` (l.72,95,271,290,297) and toggled imperatively in JS (`dashboard.js:91,293,312,568,569,1225,1226,1247,1250,1253,1390,1846,2006,2210` — 19 spots). Brittle for redesign.
- **27 `!important` rules** in CSS — layout fragility (e.g. `display:none !important` on l.201 for visual mode).
- **Body is 13px sans, monitor log is mono only** — labels and deps in the panel head are sans, while the running stream below is mono; hierarchy ok but font-size ladder is inconsistent (10/10.5/11/11.5/12/12.5/13/14/15/17 px all appear).
- **No resize handles** between designer / monitor / rail — fixed 56/380/1fr; user can't widen monitor without entering Visual mode.
- **Settings is one giant scrollwall** (`index.html:222-362`) — no sub-sections, no save-state per group.
- **Agent grid is auto-fit min 420px** — on narrow windows you get one column with 240px-tall logs that scroll independently; no overview.
- **Two `</main>` close tags** at `index.html:154` and `156` (stray duplicate; visible HTML smell).

## 6. Reusable bones

- **SSE plumbing** (backend queues + per-event-type listeners) is solid and decoupled from UI — keep contract intact.
- **Token system** in `:root` is already 80% there — extend with spacing scale and consolidate purples.
- **Visual canvas SVG approach** with foreignObject nodes + `zoom-group` transform is the right pattern; positions persisted per workspace.
- **Workspace rail localStorage** (`WS_KEY`, `WS_ACTIVE_KEY`, `persistActiveDraft` on `beforeunload`, l.49-191) — parallel drafts work.
- **buildPanel() factory + family-badge mapping** is clean enough to keep with markup tweaks.
- **CodeMirror, marked, highlight.js CDN-loaded** — Editor, Notes, markdown view, diff view all share libs.
- **Family-specific accents** (`--claude`, `--gemini`) — extend rather than replace.
- **Glassmorphism layer** (backdrop-filter blur+saturate on header/designer/sidebars) is consistent and looks current.

## 7. Hard constraints

- **API contract frozen**: `POST/GET/DELETE /api/runs`, `/api/runs/{id}/stream` SSE event names (`status`, `snapshot`, `log`, `done`), `/output/{label}`, `/report`, `/preview`, `/preview/{label}`, `/export-to-open-design`, `/api/workflows`, `/api/schedules`, `/api/browser-auth/*`, `/api/tunnel/*`, `/api/phone-dispatch`, `/api/notifications`, `/api/agents`, `/api/custom-agents`, `/api/presets` (`dashboard.py:3411-4021`).
- **Run history hydrate**: clicking history item rebuilds the spec into agent rows (`dashboard.js:1470-1478`) — `meta.spec[].{agent,label,depends_on,streaming,prompt}` shape must stay.
- **Phone dispatch** via Cloudflare Tunnel + `POST /api/phone-dispatch` body `{message, agent}` is documented to iOS Shortcuts users — don't break.
- **gh-pages landing** referenced separately; this audit is dashboard-only but redesign must not affect `/static/` static-mount path or `?v={{CG_BUILD}}` cache-busting.
- **Workspaces localStorage keys** (`WS_KEY`, `WS_ACTIVE_KEY`, `VIEW_MODE_KEY`, draft positions) — migrate, don't drop.
- **CDN deps** (Inter, JetBrains Mono, marked, highlight.js github-dark, CodeMirror + 6 modes + 2 addons) are load-bearing for Editor/Notes/markdown.
- **Streaming flag per agent** — only valid for claude/gemini (`dashboard.py:1149`); UI hides toggle for others (`dashboard.js:1250`).
