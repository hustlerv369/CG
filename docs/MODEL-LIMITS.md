# Model limits & operational quirks

What each agent CLI / API can and can't do, learned from real CG runs.
Update when you hit new failure modes — this is the ground truth that
drives preset design (which model goes where).

---

## Claude Code CLI (`claude --print`)

**Mode:** one-shot generative. Takes prompt → returns text. Does NOT
run an agentic loop in `--print` mode (no tool calls in the output by
default). This is exactly what CG wants.

| Agent | Stable token range | Notes |
|---|---|---|
| `claude-opus-4-7` (1M ctx) | up to ~64k output tokens / call | Best for long code generation. Ran fine for 6 min producing 136 KB output in one call. |
| `claude-opus-4-6` | similar | Older Opus, similar profile. |
| `claude-sonnet-4-6` | up to ~32k output tokens | Faster + cheaper than Opus. Best for review / critique / focused tasks. |
| `claude-haiku-4-5` | up to ~32k output tokens | Cheapest. Use for trivial summaries / classification. Don't use for code generation. |

**Quirks:**
- Subprocess exits cleanly when generation is done. Stream-json output is reliable.
- 1M context Opus genuinely accepts huge input, but generation slows down past ~30 KB output. Plan for 5–10 min wall-clock for big code outputs.
- No tool-loop hangs observed.

**Recommendation:** Use Claude wherever you need a long, structured text
output (code, specs, README) you can trust to come back as text.

---

## Gemini CLI (`gemini -p`)

**Mode:** agentic loop. Has built-in tools (`write_file`, `read_file`,
`run_shell_command`, `grep_search`, sub-agent delegation). When the
model decides a tool call would help, it tries to invoke one.

**The trap:** if the workspace doesn't have the tool the model wants
(or the tool errors), Gemini retries, then tries to delegate to a
sub-agent (`generalist`), which often also doesn't exist → process
hangs forever waiting for a response that will never come.

Real example, run `dd51a4845f01`, tests step:

```
"the run_shell_command tool is not available in my current environment,
 preventing me from creating the necessary directories and files for
 the test suite. To proceed, I will delegate this file creation task
 to the generalist sub-agent..."
```

→ subprocess never exits, agent stuck "running" indefinitely.

**Mitigations applied in CG (v44):**

1. **Hard subprocess timeout** (`CG_AGENT_TIMEOUT`, default 720 s) —
   any agent that runs longer than this is killed and marked failed.
   The downstream agents that depend on it stop waiting.

2. **Auto-prepended "TEXT ONLY, no tools" preamble** to every Gemini
   prompt. The orchestrator now injects, before user prompt:

   ```
   OUTPUT MODE: TEXT ONLY. Do not call any tools — no
   write_file, no read_file, no run_shell_command, no
   grep_search, no sub-agent delegation. Respond with
   raw text in the format the user asks for. Nothing
   else.
   ```

   Empirically reduces tool-loop hangs to near zero.

| Agent | Stable token range | Notes |
|---|---|---|
| `gemini-2.5-pro` | up to ~32k output, ~2M input | Strong on creative + structured output. Auto-stops at ~20 KB output for one observed run. |
| `gemini-2.5-flash` | up to ~16k output, ~1M input | Fast (sub-30 s for a 1.6 KB README). Best for short, well-bounded tasks. |
| `gemini-3-pro` (preview) | unknown | Capacity-limited (429s observed). Avoid for now. |

**Quirks:**
- Output streaming chunk size is irregular; some short responses arrive
  in one frame, others byte-by-byte.
- Even with the preamble, Gemini occasionally writes a 1–2 line
  meta-comment ("I will now…") before the actual content — usually
  harmless, the parser scans for fenced blocks anyway.
- 256-color and Ripgrep warnings on `stderr` are cosmetic, ignore them.
- **`_recoverFromLoop` self-abort (v45 finding):** Gemini Flash has
  its own internal generation-loop detector that watches the model's
  own output for repetition. If it fires, the CLI throws
  `AbortError: The user aborted a request. at GeminiClient._recoverFromLoop`
  and exits with non-zero. Observed when generating long Markdown
  documents (README + DEPLOY in one go). Mitigation: don't use Flash
  for tasks > ~5 KB output; prefer Sonnet for docs.

**Recommendation:** Use Gemini for:
- Independent design / creative tasks (Gemini Pro produces solid SVG
  mockups + design tokens)
- Short summaries / reformatting (Gemini Flash is genuinely fast)
- Cross-vendor critique (catches things Claude missed)

**Avoid Gemini for:**
- Tasks where the prompt asks the model to "write files" or "run
  commands" (it will try to use tools)
- Very large outputs (>15 KB) — risk of mid-stream cutoff
- Tasks where you need deterministic completion within a tight budget

---

## OpenCode CLI (`opencode run`)

Bring-your-own-provider headless mode. Variable-quality, depends on
the provider config. Use only for users who've configured it
themselves.

---

## HTTP-API agents (OpenRouter, Z.ai, Anthropic API direct, …)

Token limits match the underlying model. No agentic loop, no tool
hangs. Reliable, but billed per-token. Use as fallback when CLI
subscription quota is exhausted.

---

## CG orchestrator failure modes & their fixes

### 1. Subprocess hangs forever
**Symptom:** agent status stays `running` indefinitely; output file
mtime stops advancing; subprocess PID still alive.

**Cause:** Gemini tool loop, or any subprocess waiting on never-coming
input.

**Fix (v44):** hard timeout per agent; subprocess.kill() on expiry;
agent marked `failed` with exit code -9.

**Recovery for the user:** click `× Cancel` in the run header, or
let the timeout fire (default 12 min).

### 1b. Subprocess accepts prompt then emits zero bytes for minutes
**Symptom:** agent status `running`; output file is 0 bytes; no
stderr output; PID alive but never produces a single token.

**Cause:** Anthropic / Google API queueing under heavy load, frozen
client, network stall, or oversized prompt hitting a soft-limit.

**Fix (v45):** per-agent **first-token watchdog** (default 90 s,
configurable via `CG_FIRST_TOKEN_TIMEOUT` or `cfg.first_token_timeout`).
If the subprocess emits NOTHING within 90 s of accepting stdin, kill
it. Much faster than waiting the full 720 s wall-clock.

### 1c. Oversized prompts (>100 KB context)
**Symptom:** when an agent step's prompt embeds another step's full
output (`{{implementation}}` = 117 KB), Sonnet/Opus may queue/stall.

**Fix (v45 preset):** tests step now reads SPEC ONLY (`{{director}}`),
not full implementation. Reviewer still sees both, so cross-checking
loop is preserved. Same pattern recommended for any new step that
needs implementation knowledge — pass spec or summary, not full code.

### 2. Implementation truncates mid-block
**Symptom:** last fenced code block in `implementation.out.md` ends
mid-line.

**Cause:** model hit per-call output token limit (e.g. Opus 4.7 cuts
at ~64k tokens regardless of the 1M context).

**Fix:** split spec across multiple agents (e.g. `implementation-be`
backend + `implementation-fe` frontend) so each call stays under the
limit. Future preset upgrade.

### 3. Export endpoint missed files
**Symptom:** `📦 save project` writes fewer files than the
implementation output contains.

**Cause (v42.1 bug, fixed in v44):** endpoint scanned in-memory
`log_lines` which can drop bytes on cancel. Fixed to read from
`*.out.md` files on disk (authoritative), per-agent (no fence
collision across agent boundaries).

---

## Heuristics for picking a model in a new preset

```
need     | concrete pick                     | why
─────────┼───────────────────────────────────┼─────────────────────────
spec     | claude-opus-4-7                   | strongest reasoning
design   | gemini-pro                        | independent creative eye
code     | claude-opus-4-7 (1M)              | huge output, no tool hang
review   | claude-sonnet-4-6                 | best at code critique
tests    | claude-sonnet-4-6                 | from spec only (no full code)
docs     | claude-sonnet-4-6 (was Flash)     | Flash hits _recoverFromLoop on long Markdown
summary  | claude-haiku-4-5                  | bounded short output, cheap
critic   | gemini-pro                        | cross-vendor diversity (small input)
parallel | mix vendors                       | catch each other's blind spots
```

---

## v46 W2 — Role vocabulary (the Conductor's lexicon)

CG specs now accept an optional `role` field per step. Pure display — the
`label` slug stays the machine identifier used in `depends_on` and
`{{label}}` substitution. When Conductor (W0) generates a workflow, it
labels each step with one of these canonical roles so the user reads a
coherent team narrative ("Visionary defines scope → Architect designs
the system → Engineer ships the code") instead of step-function jargon.

Conductor's heuristic: **role drives model pick.** This table is the
default model assignment Conductor follows when composing a spec:

```
role         | icon | default model            | why
─────────────┼──────┼──────────────────────────┼────────────────────────────────
Visionary    |  🔭  | claude-opus-4-7          | scope + intent → strongest reasoning
Strategist   |  🧭  | claude-opus-4-7          | positioning, narrative, KPIs
Researcher   |  🔬  | gemini-pro               | broad reading, market lens, cross-check
Architect    |  🏛  | claude-opus-4-7 (1M)     | system design + huge specs
Designer     |  🎨  | gemini-pro               | independent creative eye, SVG output
Engineer     |  🛠  | claude-opus-4-7 (1M)     | huge code output, no tool-loop hangs
Writer       |  ✍   | claude-sonnet-4-6        | long-form prose, fast, cheap
QA           |  🧪  | claude-sonnet-4-6        | tests from spec, focused
Critic       |  ⚖   | claude-sonnet-4-6        | code critique excellence
Operator     |  📡  | claude-sonnet-4-6        | docs + deploy + runbooks (no Flash — _recoverFromLoop)
```

**Cross-vendor pairing rules for Conductor refinement loops (W0.2):**
- Designer (gemini) ↔ Critic (claude) — visual judgment vs structural rigor
- Engineer (claude) ↔ Reviewer (gemini) — implementation vs alternative pattern
- Researcher (gemini) ↔ Architect (claude) — breadth vs synthesis

When `iterate_with` is set in a Conductor-generated spec, prefer pairing
across vendors — the diversity is the whole point.

> **Rule of thumb:** if the agent's job is to OUTPUT TEXT WITH FENCED
> CODE BLOCKS containing actual file content (and the next agent will
> parse those blocks), prefer Claude. Gemini will sometimes try to
> write the files itself.

---

## Telemetry to add (future)

- Per-agent timing histogram saved to `outputs/dashboard-runs/<id>/timing.json`
- Output token estimate from char count → cost calculation
- Auto-flag runs with > 1 timeout for the user
