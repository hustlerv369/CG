# CG Dashboard — user guide

The dashboard is a small FastAPI web app that lets you run multiple AI
agents (Claude + Gemini) in parallel and watch their output live in
your browser. Think n8n / Make, but for AI workers, running entirely
on your local machine and your existing **Claude Pro + Google
subscriptions** (no API keys, no per-token cost).

![architecture](dashboard-architecture.txt)

## Starting it

Three equivalent ways:

```bash
# 1) Desktop launcher
double-click  C:\Users\<you>\Desktop\CG Dashboard.bat

# 2) cg CLI
cd D:\CG
python src\cg.py dashboard
# → http://127.0.0.1:8765 opens automatically

# 3) directly with uvicorn
cd D:\CG\src
python -m uvicorn dashboard:app --host 127.0.0.1 --port 8765
```

The browser opens at `http://127.0.0.1:8765`. The page is the entire
app — no login, no accounts, runs locally.

## Anatomy of the page

```
┌─────────────────────────────────────────────────────────────────┐
│ CG — multi-agent                                  connected     │
├──────────────┬──────────────────────────────────────────────────┤
│ WORKFLOW     │  no run yet                                      │
│              ├──────────────────────────────────────────────────┤
│ Preset: ▼    │  ┌────────────┐  ┌────────────┐                 │
│ Title: ____  │  │ design     │  │ build      │   ← agent       │
│              │  │ [gemini]   │  │ [claude]   │     panels       │
│ ┌─ agent 1 ┐ │  │ running ●  │  │ done       │   (live SSE     │
│ │ Gemini ▼ │ │  │            │  │            │    streaming)   │
│ │ design   │ │  │ < live     │  │ < final    │                 │
│ │ prompt:  │ │  │   stdout   │  │   output > │                 │
│ │ [.....]  │ │  │            │  │            │                 │
│ └──────────┘ │  └────────────┘  └────────────┘                 │
│ + add agent  │                                                  │
│ [▶ Run]      │                                                  │
│              │                                                  │
│ HISTORY      │                                                  │
│ • run abc12  │                                                  │
│ • run def34  │                                                  │
└──────────────┴──────────────────────────────────────────────────┘
```

**Left** — workflow designer:

- **Preset** dropdown — three bundled workflows to get started:
  - *Two-model compare* — same task, both models, side-by-side
  - *Design → Implement* — Gemini designs spec, Claude implements
  - *4-agent fan-out* — same prompt to 4 agents for diversity
- **Title** — name your run (shows in history)
- **Agents** — one row per agent. Pick agent kind (Claude / Gemini),
  give it a label (`design`, `build`, `review` — anything), write the
  prompt.
- **+ add agent** — add as many as you want, each runs in parallel
- **Run** — fire all agents at once
- **History** — clickable list of past runs

**Right** — live monitor:

- One panel per agent
- Status badge: `queued` → `running ●` (animated) → `done` / `failed`
- Live stdout stream, auto-scroll
- Char counter and exit code in footer

## Three real-world workflows

### 1. Quick diff — same task, two models, compare

Pick the *Two-model compare* preset. Both agents get the same prompt;
you see two answers side-by-side. Useful for:

- Tricky bugs where you want a second opinion
- Generating idea variants (haiku, ad copy, alternatives)
- Spotting blind spots — when one model misses something the other catches

### 2. Pipeline — design then implement

Pick the *Design → Implement* preset. Two agents run in parallel; in
practice this works because the prompts are independent enough. For
true sequential dependency (Claude waits for Gemini's output), today
you'd run two separate runs and copy between them; a `dependsOn`
field on agent rows is on the roadmap.

### 3. Fan-out — diversity for creative tasks

Pick the *4-agent fan-out* preset. Same prompt, 4 agents (2× Claude,
2× Gemini) — each returns a different answer. You pick the best one.
Surprisingly effective for short creative outputs.

## Custom workflows

Click **Clear**, then build from scratch:

1. Set a title (e.g. *"Exporters for the invoicing module"*)
2. Add 3 agent rows:
   - `design` (Gemini) → *"Design the public API for export_invoices_csv"*
   - `impl` (Claude) → *"Implement export_invoices_csv per the spec…"*
   - `tests` (Claude) → *"Write pytest tests covering empty / 100-row / weird-encoding inputs"*
3. Click **Run**
4. Watch each panel as it streams output
5. Pick / merge / commit

## Output files

Every run also writes plain markdown files to disk:

```
D:\CG\outputs\dashboard-runs\<run-id>\<label>.out.md
```

These survive after you close the browser. The dashboard's history
shows the most recent runs; the run index lives at
`D:\CG\tasks\_dashboard_runs.json`.

## How fast is it?

Per request, the latency is the slowest agent. Typical numbers in
practice:

| | Claude | Gemini |
|---|---|---|
| Short reply (1 line) | ~10s | ~15s |
| Code block (50 lines) | ~25s | ~40s |
| Detailed spec / design | ~45s | ~60s |

Two agents in parallel finish in roughly the slower one's time, not
the sum.

## Limits / caveats

- **Subscriptions, not API.** Both CLIs use OAuth to your Pro / Google
  accounts. If your subscription quota runs out, you'll see exit ≠ 0
  in the panels with the rate-limit message in the log.
- **No agent-to-agent dependency yet.** All agents in a run start at
  the same time. For a true pipeline (B's prompt depends on A's
  output) chain two runs manually for now.
- **Runs live in process memory.** Restart the dashboard → the
  in-memory list resets. Run output files on disk persist.
- **Local only.** Server binds to `127.0.0.1` by default — not exposed
  to your network. Override with `--host 0.0.0.0` if you really want
  to (and add auth!).

## Stopping it

- `Ctrl+C` in the launcher window.
- Or close the launcher window.
- Or `taskkill /F /IM python.exe` if it gets stuck.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `connecting…` in header forever | server died or wrong port | Check launcher window for crash; restart |
| Agent panel says `failed exit=127` | CLI not on PATH | Run `python src/cg.py doctor` to confirm both CLIs are reachable |
| Gemini output starts with Windows warnings | `gemini-cli` always logs them | Cosmetic only; the actual response follows |
| `command not found: claude` | Claude Code not installed or not in PATH | Reinstall Claude Code, add `~/.local/bin` to PATH |
| Empty output, exit 0 | Model returned empty (rare) | Re-run; if persistent, sharpen the prompt |
