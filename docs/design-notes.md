# Design notes — why CG looks the way it does

## Background

CG is the third architecture for the same goal: get a fleet of AI agents
to collaborate on coding tasks using the user's existing subscriptions.

The two prior attempts:

1. **CLAUDEGRAVITY v1** (filesystem inbox + heartbeats + handoffs).
   Modeled the agents as autonomous daemons that would scan a queue,
   claim work, send heartbeats, and hand off to peers.

2. **CLAUDEGRAVITY 2.0 — pull-based dispatch** (commit 883b71c).
   Replaced autoscan with `cg dispatch` generating a self-contained
   prompt for the human to paste into a fresh chat.

Both failed in practice because of a shared assumption that turns out
to be wrong.

## The wrong assumption

We assumed an Antigravity (or Claude Code) **chat window** could be an
agent endpoint. It can't, for three reasons:

1. **No persistent loop.** Chat agents react to user input. They don't
   tick. There is no way to "wake" them from outside the chat UI.
2. **Workspace memory.** Antigravity stores per-workspace conversation
   trajectories. Every chat in a given workspace inherits the prior
   chats as context. So a "fresh chat" still sees the last week of
   history. Even after a clean repo, the IDE remembered.
3. **No reliable trigger.** The orchestrator can produce a prompt, but
   Claude Code on the Director PC cannot programmatically send it to
   the Gemini chat. The human has to copy-paste.

So the agents weren't really agents — they were chat windows we kept
*calling* agents.

## What actually works

Both Claude and Gemini ship as **headless command-line tools** that
authenticate via the user's existing subscription:

| Tool | Auth | Subscription |
|---|---|---|
| `claude --print "..."` | OAuth to Claude.ai | Claude Pro / Max |
| `gemini -p "..."` | OAuth to Google account | Google account / Cloud |

A subprocess is a real worker. It:

- Returns when done (no human in the loop).
- Has no shared state between invocations.
- Can be parallelized (Python's `concurrent.futures.ThreadPoolExecutor`).
- Reads/writes files in the directory it's launched from.

This collapses the entire CLAUDEGRAVITY protocol — claim, heartbeat,
handoff, lease, sweep — down to "fork two processes, wait for both,
write outputs to disk".

## The CG architecture

```
┌─────────────────────────────────────────┐
│  Director (you)                         │
│  python src/cg.py task add "..."        │
│  python src/cg.py run task-001 --to both│
└────────┬────────────────────────────────┘
         ▼
┌─────────────────────────────────────────┐
│  src/cg.py — single-file orchestrator   │
│                                         │
│  Task store: tasks/_index.json          │
│  Run history: per-task field            │
│  Outputs: outputs/<task-id>/<agent>.md  │
└────────┬────────────────┬───────────────┘
         │                │
         ▼                ▼
┌──────────────────┐  ┌──────────────────┐
│ subprocess       │  │ subprocess       │
│ claude --print   │  │ gemini -p        │
└──────────────────┘  └──────────────────┘
```

Total: ~350 lines of Python, 15 tests, zero infrastructure.

## What we kept from CLAUDEGRAVITY

- The idea of structured tasks with titles and specs.
- Per-task output directories.
- A run history for audit.

## What we threw away

- Inbox/outbox/orchestrator/protocol message types
- Claim arbitration, lease sweeping, heartbeats
- AGENTS.md as a per-workspace identity contract
- Antigravity bootstrap prompts
- Multi-agent state machine
- VPS relay / FastAPI / Redis / Telegram bot
- NotebookLM auto-sync
- Knowledge graph
- All the feature cards from the README's "What you get" list

The prior design was a heroic attempt to compensate for the fact that
chat windows aren't agents. Removing that compensation made the entire
edifice collapse — gloriously, by ~95%.

## Trade-offs

What CG **doesn't** do that CLAUDEGRAVITY tried to do:

- "Send a goal from your phone, agents work overnight while you sleep."
  Not possible without paid API keys; a subprocess needs a launching
  process.
- "Director Opus orchestrates a fleet of Sonnet builders + Haiku batch."
  Possible but unhelpful: at this scale, one Claude Code session can
  drive everything sequentially.
- "Reviewer Opus #2 cross-model reviews critical-path handoffs."
  Easily emulated: dispatch the same task with `--to both` and diff
  the outputs.

What CG **does** that CLAUDEGRAVITY couldn't reliably:

- Actually finish a task without human chat-paste-paste.
- Run two model perspectives in parallel for free.
- Survive cold-start (no daemon, no state.db, no inbox watcher).
- Be understood end-to-end from one Python file.

## Where to take it next

Nice incremental wins, in order of value-to-effort:

1. **Merge step.** A `cg merge <task-id>` that takes both outputs and
   asks Claude to pick the better version (or synthesize). Cheap, useful.
2. **Verifier.** A `cg verify <task-id>` that runs tests / lint / build
   on each agent's output and flags which produced runnable code.
3. **Templates.** A `cg task add --template <name>` that pre-fills the
   spec format ("output ONLY a code block", acceptance criteria, etc.).
4. **Re-dispatch on failure.** Auto-retry with a sharper prompt when an
   agent's output fails verification.
5. **Streaming output.** Claude/Gemini both support stream-json output;
   the orchestrator could surface partial progress instead of waiting
   for the full response.

Each of these is a few hundred lines max. None require new infrastructure.
