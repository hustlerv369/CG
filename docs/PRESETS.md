# CG Presets — practical workflow library

CG ships **27 presets** that map to real automation needs. Each one is a
multi-agent pipeline you can pick from the **Preset** dropdown, edit any
prompt, and Run. Most use `${VARIABLES}` so you can configure once in
**Settings → Workflow variables** and reuse across runs.

The 10 presets prefixed with an emoji (`📝 📱 🎨 🌍 ✉️ 🔬 🎙 🔍 🛍 📚`) were
designed for the most common automation jobs: content, design, research,
code review, comms, product, docs.

---

## How to use a preset

1. Open the dashboard at `http://127.0.0.1:8765`
2. **Preset** dropdown → pick one
3. Open **Settings → Workflow variables** → fill in the `${VARS}` it asked for
4. Edit any prompt in the designer (Terminal mode = linear rows, Visual
   mode = node graph)
5. Click **▶ Run** — agents run in parallel where there's no `depends_on`,
   sequentially where there is

---

## Content & marketing

### 📝 Blog article pipeline
**ID:** `blog-article-full`
**Stages:** research (Gemini Pro) → outline (Sonnet 4.6) → draft (Opus 4.7) → SEO polish (Sonnet 4.6)
**Vars:** `${TOPIC}`, `${TONE}`, `${WORD_COUNT}`
**What it does:** end-to-end blog post. Research agent pulls 5-7 fact-checked
talking points + 3 contrarian angles + 5 long-tail keywords. Outline agent
structures the post. Draft writes the long-form. SEO polish tightens, adds
internal-link anchor placeholders, generates meta title + description.

### 📱 Social content fan-out
**ID:** `social-content-fanout`
**Stages:** 5 parallel agents (X thread, LinkedIn, Instagram, TikTok hook, Facebook)
**Vars:** `${SOURCE}` (paste article or use `{{file:notes/post.md}}`)
**What it does:** one source article → 5 platform-tuned posts. Each agent
respects platform constraints (X 280 chars/post, LinkedIn 1500-2200 chars,
Instagram caption 800-1400 + 12-20 hashtags, TikTok hook ≤8s spoken,
Facebook 400-700 chars).

### ✉️ Email drip sequence (5-email)
**ID:** `email-drip-5`
**Stages:** 5 sequential agents — welcome → problem → story → proof → CTA
**Vars:** `${PRODUCT}`, `${PERSONA}`, `${OUTCOME}`
**What it does:** full nurture sequence. Each email lands a different angle.
Subjects + preheaders + body. Final email has a hard CTA with urgency.

### 🛍 Product description (3 angles + winner)
**ID:** `product-description-3`
**Stages:** 3 parallel angles (status / savings / ease) → critic picks winner
**Vars:** `${PRODUCT}`, `${AUDIENCE}`, `${KEY_FEATURE}`
**What it does:** generates 3 distinct descriptions, then a critic (Opus)
quotes the winner's strongest 2 lines and suggests edits.

---

## Design

### 🎨 Design brief → 3 directions → critique
**ID:** `design-brief-to-concepts`
**Stages:** 3 parallel directions (Opus, Opus, Gemini Pro) → critique (Sonnet)
**Vars:** `${BRIEF}`, `${BRAND_COLORS}` (optional)
**What it does:** turn a brief into 3 distinct directions — concept,
mood, palette (4-6 hex codes), type stack, key components, hero copy.
Critic scores each on Brief fit / Differentiation / Memorability /
Implementation cost.

**Pair with:** [Stitch MCP](https://stitch.io) to render screens for each
direction, or [Open Design](https://www.open-design.com) for full prototype
generation. Add MCPs in `~/.claude/mcp_servers.json`; CG passes through.

---

## Research

### 🔬 Research deep-dive
**ID:** `research-deep-dive`
**Stages:** 3 parallel lenses (tech / business / user) → synthesis (Opus)
**Vars:** `${QUESTION}`, `${URLS}` (comma-separated for `{{web:...}}`)
**What it does:** Playwright fetches the URLs, three agents read from
different lenses, director compiles 10 prioritized bullets + TL;DR.

### 🎙 Meeting transcript → action items
**ID:** `meeting-to-actions`
**Stages:** summary (Flash) → decisions+blockers (Sonnet) → action items (Opus)
**Vars:** `${TRANSCRIPT}`, `${PARTICIPANTS}`
**What it does:** turn transcript into 2-paragraph summary, separates
decisions/blockers, extracts numbered action items with `[Owner / Due]`
tags. Conservative — only explicit asks, not vague wishes.

---

## Translation

### 🌍 Translate CZ ↔ EN
**ID:** `translate-cz-en`
**Stages:** draft (Sonnet) → review (Opus) → polish (Sonnet)
**Vars:** `${SRC_LANG}`, `${DST_LANG}`, `${REGISTER}`, `${SOURCE}`
**What it does:** two-pass translation. Different model on second pass
catches nuance the first missed. Preserves Markdown / code / brand names.
Adjust register (formal / casual / technical / warm).

---

## Code

### 🔍 Code PR review (3 lenses)
**ID:** `code-pr-review`
**Stages:** 3 parallel lenses (security/Opus, performance/Sonnet,
readability/Gemini-Pro) → verdict (Opus)
**Vars:** `${DIFF}` (defaults to `{{git:diff}}`), `${CONTEXT}`
**What it does:** security uses OWASP/CWE framing, performance hunts N+1
+ blocking I/O + missed indexes, readability calls out naming + missing
tests. Director merges, dedups, ends with `APPROVE` / `APPROVE_WITH_NITS`
/ `REQUEST_CHANGES`.

### 📚 GitHub README generator
**ID:** `github-readme-from-code`
**Stages:** scan (Sonnet reads files) → readme (Opus writes)
**Vars:** `${PROJECT_NAME}`, `${KEY_FILES}` (comma-separated paths), `${ONE_LINER}`
**What it does:** reads your project files, drafts a complete GitHub
README with badges, quickstart, features, architecture diagram, CLI
reference, contributing.

---

## Pre-existing presets (kept from earlier versions)

| ID | Title | Use case |
|---|---|---|
| `compare` | Two-model compare | Same task → diff Claude × Gemini |
| `pipeline` | Design → Implement → Critique | Foundational sequential demo |
| `pipeline-var` | Same with `${TASK}` variable | Reuse without prompt edits |
| `fanout` | 4-agent fan-out | Creative diversity |
| `git-pr-review` | Quick git diff review | One-shot diff scan |
| `file-refactor` | Refactor with cross-review | Sonnet drafts, Opus reviews |
| `browser-scrape-and-summarize` | Headless scrape → summary | Article research |
| `browser-visual-regression` | URL × 2 screenshots → AI diff | Visual QA |
| `browser-form-test` | Headless form e2e | Smoke test |
| `seo-audit` | Live page SEO audit | 3 lenses + action plan |
| `competitor-analysis` | Live scrape → table | Quick competitor mapping |
| `github-pr-review` | 3-model GH PR review | Saves as note |
| `blog-draft` | Quick blog draft | Research-light alternative |
| `bug-investigation` | File → 3 models → plan | Root-cause hunt |
| `code-review` | 3-model code review | Cross-check |
| `browser-pilot-search` | Autonomous web search | Goal-driven Playwright |
| `browser-pilot-summarize` | Pilot trace → summary | Two-step pilot |

---

## Variable reference (works in all prompts)

| Pattern | Resolves to |
|---|---|
| `${VARNAME}` | from Settings → Workflow variables |
| `{{label}}` | output of upstream agent named "label" |
| `{{label.field}}` | structured field of upstream output (browser agent) |
| `{{file:path/to/file}}` | inline file contents |
| `{{git:diff}}` | current `git diff` |
| `{{git:log:5}}` | last 5 commits |
| `{{shell:cmd}}` | output of shell command |
| `{{web:URL[,URL2,...]}}` | headless-Chromium markdown of URLs |
| `{{web-shot:URL}}` | base64 screenshot of URL |

---

## Adding your own preset

Drop a JSON file into `D:\CG\workflows\` and it appears in the **Saved
workflows** dropdown. Or paste JSON via the **📋 paste** button. The
schema is the same as built-in presets:

```json
{
  "id": "my-preset",
  "title": "My custom workflow",
  "description": "What it does in one sentence.",
  "variables": { "VAR1": "default value" },
  "spec": [
    {
      "agent": "claude-sonnet-4-6",
      "label": "step1",
      "prompt": "Do something with ${VAR1}.",
      "streaming": true
    },
    {
      "agent": "gemini-pro",
      "label": "step2",
      "depends_on": ["step1"],
      "prompt": "Improve {{step1}}."
    }
  ]
}
```

---

## Roadmap (next presets to add)

- **Customer support reply** — issue → empathetic draft → final
- **Newsletter generator** — news items → curate → write → polish
- **Code migration helper** — analyze old → propose new → diff review
- **YouTube video script** — topic → outline → script → thumbnail copy
- **Cold outreach sequence** — prospect data → 5 personalized emails

Got an idea for a preset? Drop a JSON in `workflows/`, share it, or open
an issue at [github.com/hustlerv369/CG](https://github.com/hustlerv369/CG).
