# CG Redesign — Competitor Analysis

Research notes for upgrading the CG dashboard (FastAPI + vanilla JS) from "experimental" to "professional." Sources at end.

## 1. CMUX (coder/cmux + wmux fork)
- **Steal:** Sub-agent panes that auto-spawn from a primary, report status into a sidebar, and auto-close when their task completes — pane lifecycle is task-bound, not user-managed.
- **Visual:** Native macOS via libghostty (Ghostty's renderer); Unix-domain socket for ultra-low-latency status; built-in WebKit panel beside the terminal, not a tab.
- **Avoid:** Mac-only and CLI-spawn-only mentality — don't make CG depend on a native shell to feel polished.

## 2. Claude Squad (smtg-ai)
- **Steal:** One agent = one git worktree + one tmux session — strict isolation eliminates merge chaos. CG should keep visual + state isolation per agent.
- **Visual:** Bubbletea TUI; agent list on the left, live preview pane on the right, attach/detach hotkeys. Minimal chrome, dense info.
- **Avoid:** No persistent web/visual layer — purely TUI. CG's web layer is a strength; don't apologize for it.

## 3. n8n editor canvas
- **Steal:** Node = self-contained card with input/output handles; edges color-coded by execution state (idle / running / success / error); click-to-execute with live status pulses on the canvas.
- **Visual:** Gray dotted-grid canvas, modular node cards with rounded corners, progressive disclosure (configure-in-place without leaving canvas in the new editor).
- **Avoid:** Cluttered side panel that pops over the canvas — the new n8n is moving inline. CG should edit nodes in place, not in modals.

## 4. Linear
- **Steal:** Command palette as the primary navigation (Cmd+K), keyboard-first everything, 3-token theme generation (base / accent / contrast in LCH).
- **Visual:** Inter UI font; ~12px headers (600 weight), ~20px body (400, 31px line-height); dark-mode-first; subtle gradients + glassmorphism; 361 brand colors from a tiny token primitive set.
- **Avoid:** Over-soft contrast in light mode — Linear leans dark; force a single high-contrast dark theme first, add light later.

## 5. Mac (Finder, Activity Monitor, Xcode)
- **Steal:** Full-height sidebar with `sidebarTrackingSeparator` alignment; toolbar groupings (left/center/right zones); inspector panel pattern (right rail, contextual to selection); sheet dialogs instead of modal overlays.
- **Visual:** NSVisualEffectView vibrancy on titlebar/toolbar; SF Pro / system font; tight 8/16/24 px spacing rhythm; hairline 1px dividers on translucent panels.
- **Avoid:** Vibrancy alone won't save bad hierarchy — Mac apps work because of disciplined zones, not blur.

## 6. Warp terminal
- **Steal:** Block-based output — every command + output is a discrete copyable unit with exit code, duration, timestamp. Apply to CG agent turns (block per LLM turn, with token count + latency on the block chrome).
- **Visual:** GPU-accelerated rendering; Cmd+P palette searches actions, settings, and recent commands in one index; "Active AI" banner over current shell context.
- **Avoid:** Heavy AI prompts overlaying the terminal — keep AI suggestions as opt-in banners, not auto-modals.

## 7. Charm / Bubbletea / Crush (2026)
- **Steal:** Composed components (10+ in Crush): list + viewport + spinner + dialog overlay, all reactive to one model. Lipgloss-style declarative styling. Smooth animation transitions (Bubbletea v2 / Mode 2026 sync output).
- **Visual:** Pastel-on-dark palette, rounded ASCII borders, generous padding, monospaced everything but proportional spacing rules.
- **Avoid:** ASCII-borders-everywhere look — copy the *rhythm* and *animation*, not the borders, on a web canvas.

## Synthesis — patterns CG should adopt

1. **Three-zone shell (Mac + CMUX):** Left sidebar = agent/workspace tree; center = canvas OR block view (toggle); right inspector = selected node/agent details. Full-height sidebar with vibrancy/blur on the chrome.
2. **Block-based agent turns (Warp + Linear):** Each LLM turn renders as a Warp-style block — collapsible, copyable, with chips for tokens / latency / model / cost; edges between blocks show data flow when in canvas mode.
3. **3-token LCH theme system (Linear):** Define `--base`, `--accent`, `--contrast`; generate the rest. Inter font, 12/14/20 px scale, 8 px spacing grid, 6 px radius.
4. **Cmd+K palette (Linear + Warp):** One palette for spawn-agent, switch-workspace, run-task, jump-to-block, settings. Keyboard-first; mouse is the fallback.
5. **Per-agent worktree isolation made visible (Claude Squad + n8n):** Each agent's pane shows branch + diff badge in the header; canvas edges are colored by execution state (idle/running/success/error) with subtle pulse animation, not heavy modal overlays.

Sources:
- [cmux.com](https://cmux.com/)
- [Better Stack: cmux native macOS terminal](https://betterstack.com/community/guides/ai/cmux-terminal/)
- [wmux fork](https://github.com/amirlehmam/wmux)
- [claude-squad GitHub](https://github.com/smtg-ai/claude-squad)
- [Claude Squad tmux integration](https://deepwiki.com/smtg-ai/claude-squad/4.2-tmux-integration)
- [n8n canvas docs](https://deepwiki.com/n8n-io/n8n/6.2-workflow-canvas-and-node-management)
- [n8n UX deep dive](https://n8n.spot/n8n-ui-ux-deep-dive-how-thoughtful-design-streamlines-visual-automation/)
- [Linear brand](https://linear.app/brand)
- [Linear UI redesign](https://linear.app/now/how-we-redesigned-the-linear-ui)
- [FontOfWeb: Linear tokens](https://fontofweb.com/tokens/linear.app)
- [Typ.io: Inter UI on Linear](https://typ.io/s/2jmp)
- [Warp blocks docs](https://docs.warp.dev/terminal/blocks/block-basics/)
- [Warp 2026 changelog](https://docs.warp.dev/changelog/2026/)
- [Bubbletea framework](https://github.com/charmbracelet/bubbletea)
- [Bubbletea 2026 features](https://www.glukhov.org/post/2026/02/tui-frameworks-bubbletea-go-vs-ratatui-rust/)
- [NSWindowStyles / NSToolbar showcase](https://github.com/lukakerr/NSWindowStyles)
- [Apple inspectorTrackingSeparator forum](https://developer.apple.com/forums/thread/718569)
