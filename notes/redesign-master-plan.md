# CG Redesign — Master Plan

> Synthesis of the three sub-agent reports + user direction. This document
> drives implementation. Each phase is an atomic commit.

## Vision

**"Hustler Claude Gravity"** — a multi-agent orchestrator that feels like a
million-dollar product, not an experimental script. Free, customizable,
luxurious. User picks Terminal or Visual mode; both must be perfect.

## Design DNA

Three layers, blended:

| Layer | Pulled from | Manifestation |
|---|---|---|
| **Antigravity base** | true dark, code-first IDE feeling | `#0a0908` warm-black base, JetBrains Mono on agent output, hairline 1px dividers |
| **Claude warmth** | Anthropic's coral/cream palette | warm coral `#FF6B4A` primary accent, amber `#FFB87A` highlights, Tiempos-feel serif headers (optional), cream `#F5E6D3` glow tints |
| **Hustler premium** | Linear/Stripe/Vercel polish | Inter UI, 8px spacing grid, generous whitespace, glass blur on chrome, gradient accents, Cmd+K palette, status bar, micro-interactions |

## Layout — Hybrid C-on-A

(from `redesign-wireframe-spec.md` §6)

- **Default:** 3-zone shell — left rail (workspaces/runs) | center (workflow + monitor) | right inspector (selected agent details)
- **Run-active:** center morphs to CMUX-style tiled grid (1/2/4/N agents, each terminal-styled with header/body/footer)
- **Canvas (n8n):** ⌘G overlay or center-mode swap, NOT a top-level toggle
- **Kills:** Classic ↔ Visual top-level toggle; the four-tab navigation in current header (folds into ⌘K palette + sidebar sections)

## Hard constraints (audit §7 — don't break)

- API routes + SSE event names: `status` / `snapshot` / `log` / `done`
- Run hydrate shape: `meta.spec[].{agent,label,depends_on,streaming,prompt}`
- Phone-dispatch JSON body `{message, agent}`
- localStorage keys: `cg.workspaces`, `cg.workspaces.active`, `cg.viewMode`, draft positions
- Streaming flag valid only for claude/gemini families
- `?v={{CG_BUILD}}` cache-bust on `/static/` files

## Phases (each = 1 commit)

### v18 — Design tokens + typography (foundation)
- Replace `--accent` purple with Hustler coral + amber gradient
- Add `--space-1..8` scale (4 / 8 / 12 / 16 / 24 / 32 / 48 / 64)
- Consolidate purples (kill `#a78bfa` fallbacks)
- Replace hardcoded status hexes in Visual canvas with tokens
- Body background: coral radial instead of purple
- Fix duplicate `</main>` tag (index.html:154-156)

### v19 — Status bar + ⌘K command palette
- Bottom 32px status bar: backend dot · runs · queued · tunnel · tailnet · elapsed · build
- ⌘K palette modal: fuzzy search, sections (Run / Jump / Editor / Settings / Actions)
- Keyboard shortcut framework

### v20 — Resizable panels + 3-zone shell
- `react-resizable-panels`-style splits (vanilla JS implementation, no React dep)
- Left rail (220px, min 180, max 360)
- Right inspector (340px, min 280, max 520)
- Center vertical: workflow/grid + event log
- Persist all sizes to `localStorage[cg.layout.v1]`
- Double-click gutter = collapse, Ctrl+\ / Ctrl+Shift+\

### v21 — Block-style agent panes (Warp-inspired)
- `buildPanel()` rewrite: header (name · model · pulse-pill · elapsed · tokens) / body (terminal-styled) / footer (cost · tools)
- Status pill animation: dot pulse 1.2s ease-in-out
- Hover overlay: copy / fullscreen / kill
- Sticky-bottom auto-scroll with scroll-up release

### v22 — Center morph + CMUX grid mode
- When run is active and ≥2 agents: center column flips to tiled grid (1/2/4/N CSS-grid layouts)
- Single-agent view: large block, no split
- Layout selector in toolbar (1 | 2 | 4 | N)

### v23 — Inspector rail + Settings sectioning
- Right rail: contextual to selection (agent · run · workflow · file)
- Settings split into accordion sections instead of one scroll-wall
- Browser auth, Tunnel, Notifications get their own collapsibles

### v24 — Polish pass
- Micro-interactions (button press, badge appear, gutter hover)
- Empty states with art
- Loading skeletons
- Mobile-aware breakpoints (≤900px collapses inspector)

## Out of scope (future — not this redesign)

- Real xterm.js terminals per agent (currently styled `<pre>` is enough; xterm = next sprint)
- Light mode (dark-only first)
- Tailscale integration (separate big rock in ROADMAP)
- Drag-to-connect in canvas (still on roadmap, not blocked by redesign)

## File touch list

```
src/dashboard_static/dashboard.css   # design tokens, layout, all panes
src/dashboard_static/dashboard.js    # palette, resize, panel factory, keyboard
src/dashboard_static/index.html      # shell restructure, status bar, palette modal
src/dashboard.py                     # build version stamp, no logic change
docs/dashboard-guide.md              # update screenshots + section names
README.md                            # update Status list (v18+ entries)
CHANGELOG.md                         # v18-v24 entries with commit hashes
RESUME-FROM-NEW-SESSION.md           # bump pointer
```

---

**Authored:** 2026-05-08
**Drives:** v18 → v24
