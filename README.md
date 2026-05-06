# CG — multi-agent orchestrator on subscriptions

CG dispatches coding tasks to Claude Code and Google Gemini in parallel,
using the user's existing **Claude Pro** and **Google** subscriptions —
no API keys, no per-token billing.

This is the successor to CLAUDEGRAVITY (archived). The earlier design
assumed AI chat agents in IDEs (Antigravity, Claude Code chat) could be
treated as autonomous workers driven by a filesystem inbox/outbox
protocol. That assumption was wrong: chat agents don't loop, their
workspace context drifts, and protocol overhead drowned out any benefit.

CG replaces it with the simplest thing that works: **headless CLI
subprocesses, called in parallel from a Python orchestrator**.

```
┌─────────────────────────────────────────┐
│  Director (you, in Claude Code or chat) │
└────────┬────────────────────────────────┘
         ▼  python cg.py run task-001 --to both
┌─────────────────────────────────────────┐
│  Orchestrator (src/cg.py)               │
│  - reads task spec from tasks/_index.json│
│  - dispatches in parallel as subprocesses│
└────────┬────────────────┬───────────────┘
         │                │
         ▼                ▼
┌──────────────────┐  ┌──────────────────┐
│ claude --print   │  │ gemini -p        │
│ (Claude Pro OAuth│  │ (Google OAuth)   │
└──────┬───────────┘  └──────┬───────────┘
       ▼                     ▼
  outputs/task-001/      outputs/task-001/
    claude.md              gemini.md
```

## Why this works

- **Both CLIs use OAuth on subscriptions, not API keys.** No new charges.
- **Stateless workers.** Each subprocess invocation is a fresh process
  with no shared memory. No workspace context drift, no role-play
  priming, no stale-task pickup.
- **Parallel by default.** Both agents run at the same time; the
  orchestrator waits for whichever finishes last.
- **Auditable.** All outputs land on disk under `outputs/<task-id>/`
  and the per-task run log lives in `tasks/_index.json`.

## Prerequisites

You need both CLIs installed and authenticated:

```bash
# Claude Code (uses Claude Pro/Max subscription via OAuth)
# https://docs.claude.com/en/docs/claude-code
claude --version

# Google Gemini CLI (uses Google account via OAuth)
npm install -g @google/gemini-cli
gemini  # interactive first-run does the OAuth dance
```

Both tools accept first-run authentication via browser; after that the
session token is cached locally.

## Quickstart

```bash
# 1) verify both agents work
python src/cg.py doctor

# 2) create a task
python src/cg.py task add "Build CSV exporter" --spec "$(cat <<'EOF'
Write export_invoices_csv(invoices) -> bytes that produces RFC-4180 CSV.
Output ONLY a Python code block, no prose.
EOF
)"
# → created task-001

# 3) dispatch in parallel
python src/cg.py run task-001 --to both
# → outputs/task-001/claude.md
# → outputs/task-001/gemini.md

# 4) inspect
python src/cg.py task show task-001
diff outputs/task-001/claude.md outputs/task-001/gemini.md
```

## CLI reference

```
cg.py dashboard                          launch web dashboard (browser UI)
cg.py cluster <spec.json> --layout auto  launch N agents in N visible windows

cg.py task add <title> [--spec ... | --spec-file ... | stdin]
                       [--id task-NNN]   create a task
cg.py task list                          list tasks with run counts
cg.py task show <task-id>                show task spec + run history

cg.py run <task-id> --to claude|gemini|both
                    [--timeout 300]      dispatch (subprocesses, parallel)

cg.py doctor                             smoke-check both agent CLIs
```

## Task spec format

A task spec is just text. Anything you would have pasted into a chat
window. Best practice:

- Be explicit about the **output format** ("Output ONLY a Python code
  block, no prose"). Both agents lean toward verbosity by default.
- State the **acceptance criteria** as bullets the agent can self-check.
- If the task touches files in the local repo, mention which files —
  but remember each subprocess runs in this directory and can read/write
  the project tree.

## Output format

Each `cg run` writes:

- `outputs/<task-id>/claude.md` — Claude's stdout (the response)
- `outputs/<task-id>/claude.stderr` — Claude's stderr (only if non-empty)
- `outputs/<task-id>/gemini.md` — Gemini's stdout
- `outputs/<task-id>/gemini.stderr` — Gemini's stderr

The Director (you, or another Claude Code session) merges or compares
the two outputs and decides which to commit. CG itself does not pick a
winner — the human (or a third agent) does.

## Why not autonomous?

A previous design tried "agent fleet": multiple chat agents claiming
tasks from a queue, sending heartbeats, handing off work. It failed
because IDE chat agents are not daemons — they only act when the user
types. Without API access, there is no way to wake an idle chat agent.

CG accepts this constraint: **the human director is the scheduler**,
the headless CLI is the worker. One round trip per task, parallel when
useful, no shared state, no drift.

If you later want true autonomous parallel agents, the path is paid API
access (Anthropic + Gemini API keys). Until then, this is the most
honest architecture that fits the constraints.

## Layout

```
D:\CG\
├─ src/
│  └─ cg.py             single-file orchestrator
├─ tasks/
│  └─ _index.json       SQLite-equivalent: task store + run history
├─ outputs/
│  └─ <task-id>/        per-agent stdout/stderr per run
├─ tests/
│  └─ test_cg.py        pytest tests for the orchestrator
├─ scripts/
│  └─ smoke.sh          end-to-end smoke test
└─ docs/
   └─ design-notes.md   why this was rebuilt
```

## Web dashboard 🆕

A FastAPI + vanilla-JS web app at `http://127.0.0.1:8765` that lets you
define multi-agent workflows in the browser, hit Run, and watch each
agent's stdout stream live in its own panel. n8n-style mission
control, but for AI workers, all on your subscriptions.

```bash
# Start it
python src/cg.py dashboard
# or double-click "CG Dashboard.bat" on your desktop

# → opens http://127.0.0.1:8765 with:
#    - 3 bundled presets (compare / pipeline / fan-out)
#    - per-agent live SSE panels
#    - run history sidebar
```

Full guide: [docs/dashboard-guide.md](docs/dashboard-guide.md).

## Status

- ✅ End-to-end smoke test passes (claude + gemini in parallel)
- ✅ Doctor passes
- ✅ Task store + run history
- ✅ Web dashboard with live SSE streaming
- ✅ 6 model selector (Sonnet 4.6 / Opus 4.7 / Opus 4.6 / Flash / Pro / 3 Pro)
- ✅ Apple + Revolut dark redesign (glassmorphism, purple accent)
- ✅ Sequential pipelines (`depends_on` + `{{label}}` substitution)
- ✅ Context placeholders (`{{file:path}}`, `{{git:diff}}`, `{{git:log:5}}`, etc.)
- ✅ Workflow files on disk (`D:\CG\workflows\*.json`) — share via git
- ✅ Markdown / diff render view-toggle (raw / md / diff segmented control)
- ✅ Run report export (single Markdown bundle of any run)
- ✅ Cancel / save / browser notifications / keyboard shortcuts
- ✅ 44 pytest tests passing (15 cg + 29 dashboard)
- ✅ Git remote (https://github.com/hustlerv369/CG)

## Migrating from CLAUDEGRAVITY

If you came from the old `D:\CLAUDE\CLAUDEGRAVITY` directory:

1. Close every Antigravity window and the Claude Code session that
   built CG (so no file locks remain).
2. Run the archive script in PowerShell:

   ```powershell
   powershell -ExecutionPolicy Bypass -File D:\CG\scripts\archive-old-claudegravity.ps1
   ```

   It renames `D:\CLAUDE\CLAUDEGRAVITY` to `D:\CLAUDE\CLAUDEGRAVITY.archive`.
   Antigravity stops auto-loading the poisoned workspace context, but the
   files are still recoverable on disk.

3. From now on, open Antigravity (or any IDE) at `D:\CG`. Brand new
   workspace memory in Antigravity = no Stripe ghost.

The full GitHub history of the old project lives at
`hustlerv369/CLAUDEGRAVITY` (master + the v2.0 backup at
`claude/sharp-cray-3be33e`).
