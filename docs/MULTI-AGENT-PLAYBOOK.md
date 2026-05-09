# Multi-agent runs — playbook

How to design specs that go through end-to-end every time, distilled
from the Smile Today builds on 2026-05-09 (one stalled run, one full
agent build that needed an engineer retry).

For full context (model picks, watchdog quirks, recovery) see
`docs/MODEL-LIMITS.md` and `docs/CONDUCTOR.md`.

## Five rules

1. **`continue_on_dep_failure: true` on every dependent step** unless
   it physically cannot run without the upstream output. One stuck
   agent must not freeze the whole pipeline.
2. **Big code-gen steps need `first_token_timeout: 300`.** Default
   90 s is fine for 1–3 KB spec / design / critique steps. It is not
   enough for Opus producing 30 KB of HTML+CSS+JS in one call —
   the provider queues 1–3 minutes before the first visible token.
3. **Cap `depends_on` chains at depth 2.** Architect → Engineer is
   fine. Architect → Designer → Engineer → Operator means any
   single failure stalls 3+ agents downstream. Prefer parallel
   fan-out + a final consolidator.
4. **Inline critical context** into engineer prompts when the result
   is huge. `{{architect}} + {{designer}}` chained substitutions
   produce 10+ KB of inlined text and visibly slow the provider's
   first-token. See `.smile-engineer-only.spec.json` for the
   self-contained pattern.
5. **`streaming: true` on every Claude / Gemini step.** Without it
   you get one blocking write at the end and the alive-pill stays
   "connecting" for the whole run. Streaming is the source of the
   alive heartbeat AND the activity ticker — non-streaming runs
   look frozen.

## Spec template

```json
{
  "title": "<short title>",
  "spec": [
    {
      "agent": "claude-opus-4-7", "label": "architect", "role": "Architect",
      "streaming": true,
      "prompt": "..."
    },
    {
      "agent": "gemini-pro", "label": "designer", "role": "Designer",
      "streaming": true,
      "prompt": "..."
    },
    {
      "agent": "claude-opus-4-7", "label": "engineer", "role": "Engineer",
      "streaming": true,
      "depends_on": ["architect", "designer"],
      "continue_on_dep_failure": true,
      "first_token_timeout": 300,
      "prompt": "..."
    },
    {
      "agent": "gemini-flash", "label": "operator", "role": "Operator",
      "streaming": true,
      "depends_on": ["engineer"],
      "continue_on_dep_failure": true,
      "prompt": "..."
    }
  ]
}
```

## Live observation: every panel always shows what it's doing

Three layers tell you something is happening:

1. **Status pill** — `queued` / `waiting` / `running` / `done` / `failed`.
2. **Alive pill** — bumps every second while running:
   - `connecting · 12s` (status=running, no stdout yet)
   - `connected · 25s` (got an init/heartbeat)
   - `streaming · 8s` (first visible token landed)
3. **Currently line** — under the panel header, updates on each
   filtered stream-json event AND each non-noise stderr line:
   - `session ready · abcd1234`
   - `calling tool · Read`
   - `thinking…`
   - `writing…`
   - `finalizing · success`
   - or any stderr line the CLI prints (Gemini's "Calling tool: search_web")

If a panel is "running" with `0 chars` AND no activity tick for 90 s,
the watchdog kills it. With `first_token_timeout: 300` the threshold
is 5 min instead. The downstream still runs if
`continue_on_dep_failure` is set.

## When a step fails: re-run procedure

1. **Don't cancel the run.** `continue_on_dep_failure` lets the
   downstream finish on its own.
2. **Look at the failed step's output:**
   ```bash
   cat outputs/dashboard-runs/<run_id>/<label>.out.md
   cat outputs/dashboard-runs/<run_id>/<label>.err.md
   ```
3. **Retry just that step** with a longer timeout via a single-agent
   spec (see `.smile-engineer-only.spec.json` as a template):
   ```json
   {
     "title": "<retry>",
     "spec": [{
       "agent": "claude-opus-4-7", "label": "engineer", "role": "Engineer",
       "streaming": true,
       "first_token_timeout": 300,
       "prompt": "<context inlined directly, no {{deps}}>"
     }]
   }
   ```
4. **Extract + deploy** with the project's extractor:
   ```bash
   python projects/<project>/extract-and-deploy.py <retry_run_id>
   ```

## Things never to do

- Set `streaming: false` on Claude / Gemini — kills all live feedback.
- Leave `continue_on_dep_failure` unset on a downstream step.
- Inline outputs >10 KB into a downstream prompt when a summary works.
- Use Gemini Flash for outputs >5 KB Markdown — `_recoverFromLoop`
  self-aborts. Flash for short summaries only.
- Cancel a run because one agent is "stuck" — check the alive pill +
  currently line first. If they're ticking, the agent is alive and
  the provider is probably queueing a big output.

## Failure-mode reference (what to watch for)

| Symptom | Likely cause | Action |
|---|---|---|
| Panel says `connecting · 200s+` | provider hasn't started streaming | wait until first_token_timeout, or kill manually |
| Panel says `connected · 200s+` (heartbeats arriving, no visible tokens) | model is in tool-loop or thinking | watchdog will fire on the visible-content threshold |
| Panel says `streaming · ...` then stops mid-block | output truncated at provider's per-call token limit | split the spec into smaller files (e.g. backend + frontend separately) |
| `currently:` line stuck on "calling tool · Bash" for >2 min | tool subshell hung (rare with `--print`) | cancel that step |
| All agents `running` for >5 min, all 0 chars | dashboard restart picked up unfinished runs | UI is showing stale state, refresh |

## Reference: where the fixes live

- `src/dashboard.py` — `_describe_stream_event`, `_run_one`,
  `_wait_for_deps`, `_substitute_prompt`, `AgentRunState`
- `src/dashboard_static/dashboard.js` — `handleAlive`, `handleActivity`,
  `handleStatus` (currently-line sync), `_tickAlivePills` (1 Hz)
- `src/dashboard_static/dashboard.css` — `.alive-pill`,
  `.agent-currently`, lifecycle states
- `tests/test_dashboard.py` — `test_continue_on_dep_failure_*`,
  `test_describe_stream_event_*`
