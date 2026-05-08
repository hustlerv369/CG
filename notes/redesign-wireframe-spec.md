# CG Dashboard Redesign — Wireframe Spec

Goal: ditch the "custom unpolished" feel of tabs + Classic/Visual toggle. Aim for Mac Console + n8n + CMUX/Warp polish. Live multi-agent visibility is the headline feature.

---

## 1. Top-level layout — three proposals

### Proposal A — "Mac Console-style" (3-column)

```
+--------+----------------------------------------+-----------+
| RUNS   | RUN: Spawn 4 agents - title here       | INSPECTOR |
|        +----------------------------------------+           |
| > Run1 |  [agent-1 stream] [agent-2 stream]     | Agent 2   |
|   Run2 |                                        | claude-4  |
|   Run3 |  [agent-3 stream] [agent-4 stream]     | tokens 8k |
|        |                                        | cost $.03 |
| + new  |  -- event log timeline --              | tools: rg |
+--------+----------------------------------------+-----------+
| status: connected | 2 runs | 5 queued | tunnel: on | 03:14  |
+-------------------------------------------------------------+
```

Pros: familiar (Console.app, Xcode, Linear), clean separation, browse history while a run is live.
Cons: less canvas-feeling for graph-style workflow design; 3 columns can crowd at 13".
Best for: power users running many runs, debugging, history review.

### Proposal B — "n8n canvas-first"

```
+-------------------------------------------------------------+
|  toolbar: [Run] [Cluster] [Save] [Import]  [pan] [zoom]     |
+-------------------------------------------------------------+
|                                                             |
|   (○ claude)----+---->(○ pilot)---->(○ gemini)              |
|                 \                       |                   |
|                  +----->(○ vision)<-----+                   |
|                                                             |
+-------------------------------------------------------------+
| [agent-1 mini-term] [agent-2 mini-term] [agent-3] [+]   ⤢   |
+-------------------------------------------------------------+
| status: connected | 2 runs | 5 queued | tunnel | 03:14      |
+-------------------------------------------------------------+
```

Pros: workflow design is a first-class citizen; matches existing Visual canvas investment; striking "wow" moment.
Cons: terminal strip cramped at 4+ agents; secondary functions hidden behind collapsibles.
Best for: visual designers, demo-heavy use, single-run focus.

### Proposal C — "CMUX-style grid"

```
+-------------------------------------------------------------+
| [Run] [+ split] [layout: 1 | 2 | 4 | N] [maximize] [⌘K]     |
+-----------------------------+-------------------------------+
| agent-1 claude    running   | agent-2 gemini    running     |
| > generating tokens here    | > another stream live...      |
|                             |                               |
+-----------------------------+-------------------------------+
| agent-3 pilot     done      | agent-4 vision    queued      |
|                             |                               |
+-----------------------------+-------------------------------+
| event log ▸ run-42 step-3 emitted "ok" (3 entries collapsed)|
+-------------------------------------------------------------+
| status: connected | 2 runs | 5 queued | tunnel | 03:14      |
+-------------------------------------------------------------+
```

Pros: maximum agent visibility — every pane equal real estate. Closest to user's "see everything live" goal.
Cons: workflow design moved to modal/sheet; history hidden; weak for >9 agents.
Best for: live-cluster users, simultaneous-stream watching, the headline scenario.

---

## 2. Resizable splits (react-resizable-panels)

- Outer horizontal: left rail (220px, min 180, max 360) | center (flex) | right inspector (340px, min 280, max 520).
- Center vertical: canvas/grid (flex) | event log strip (160px default, min 80, max 50% of parent).
- Per-agent grid: pure CSS grid for 1/2/4 layouts; `Panel`s only at column-pair level for N-grid.
- All sizes persisted to `localStorage[cg.layout.v1]` keyed by panel id.
- Double-click a gutter → collapse the smaller side (toggles between collapsed/last-size). Visual handle on hover (4px → 6px, accent color).
- Keyboard: Ctrl+\ collapse left rail, Ctrl+Shift+\ collapse right inspector.

---

## 3. Multi-agent live pane

```
┌─ agent-2 · gemini-2.5-pro · ● running · 00:12 · 8.4k tok ──┐
│ > tool_use: read_file("D:/CG/src/cluster.py")              │
│ > assistant: Looking at the cluster spawning logic...      │
│ ▌                                                          │
│ in $0.012  out $0.031  tools: read,grep                    │
└─[ copy ][ ⤢ fullscreen ][ ⏹ kill ]──────────────────────────┘
```

- Header row: agent name, model badge, status pill (queued grey / running amber pulse / done green / failed red), elapsed `mm:ss`, token count.
- Body: terminal-style, `JetBrains Mono → SF Mono → IBM Plex Mono → ui-monospace`, 13px, line-height 1.45, ANSI colors honored, blinking caret while streaming, auto-scroll with sticky-bottom that releases on user scroll-up.
- Footer: `in $X · out $Y · tools: a,b,c` muted text.
- Hover overlay (top-right): copy-output, expand-fullscreen (modal w/ Esc), kill (red, confirms).
- Status pill animation: amber → uses dot pulse (1.2s ease-in-out), not just glow — addresses ROADMAP "explicit živě generuji feeling".

---

## 4. Command palette (⌘K / Ctrl+K)

Linear/Warp-style, fuzzy search, sections:
- **Run** — workflow names + "Re-run last", "Cluster-launch", "Open dispatch"
- **Jump to** — active runs, then agents within selected run
- **Editor** — recent files
- **Settings** — toggle Tunnel, Tailscale, Theme, Streaming
- **Actions** — kill all, export run, copy share link
Recents pinned at top. Keyboard: ↑↓ navigate, Enter execute, Tab to scope. Backdrop blur, 640px width centered, rounded-12.

---

## 5. Status bar (bottom, 24px)

`● connected · backend :8765   |   2 runs · 5 queued   |   tunnel ✓ (cf-1234.trycloudflare)   |   tailnet 100.x.y.z   |   ⏱ run-42 03:14   |   v0.7.3`

Click segments = jump (runs → palette filtered, tunnel → settings, elapsed → current run). Color: connected green / degraded amber / offline red. Single horizontal strip, no wrap; overflow → ellipsis with tooltip.

---

## 6. Recommendation — Hybrid C-on-A

Default layout is **A** (3-column), with the center column able to morph into **C's grid** when a run is selected and contains ≥2 agents. Canvas (B) becomes a Ctrl+G overlay over the center, not a top-level mode.

Rationale:
- A's left rail solves history/parallel-runs (the "WS rail" already exists), keeping current users oriented.
- C's grid inside the center column delivers the headline "watch all agents live" promise — directly serves ROADMAP "vidět-že-se-něco-děje".
- B-as-overlay preserves the canvas investment without forcing users into design-mode every session; pan/zoom work stays useful.

This kills the Classic↔Visual toggle (one of the "unpolished" complaints), unifies into one shell, and the polish budget goes into the agent pane (typography, pulse, palette) where users actually look.
