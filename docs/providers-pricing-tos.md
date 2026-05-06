# CG — provider pricing & ToS compliance (May 2026)

CG dashboard v5 supports two classes of agent runners:

1. **Subscription-driven** (default) — invoke the official CLI as a
   subprocess. The user's **own interactive** Claude Pro / Google login
   does the auth. No tokens leave the user's machine. **Fully
   ToS-compliant.**

2. **Direct API** (opt-in) — when the user supplies an API key as an
   environment variable, the dashboard exposes additional models that
   call the provider's REST API directly, billed to the user's API
   account. **Independent of any subscription.**

---

## Subscription path — current 6 models

These are the default models in the dropdown. They cost nothing extra
on top of your Claude Pro and Google subscriptions.

| Model | Family | CLI | Notes |
|---|---|---|---|
| `claude-sonnet-4-6` | Claude | `claude --model claude-sonnet-4-6 --print` | Daily driver |
| `claude-opus-4-7` | Claude | `claude --model claude-opus-4-7 --print` | 1M context — big refactors |
| `claude-opus-4-6` | Claude | `claude --model claude-opus-4-6 --print` | Previous-gen Opus |
| `gemini-flash` | Gemini | `gemini -m flash -p` | Fastest |
| `gemini-pro` | Gemini | `gemini -m pro -p` | Default |
| `gemini-3-pro` | Gemini | `gemini -m gemini-3-pro-preview -p` | Slowest, strongest |

### ToS — what's allowed and what's not (May 2026)

**Anthropic** ([source](https://www.theregister.com/2026/02/20/anthropic_clarifies_ban_third_party_claude_access)):

> "The use of OAuth tokens obtained via Claude Free, Pro, or Max
> accounts in any other product, tool, or service is not permitted."

The ban explicitly targets **third-party harnesses** (OpenClaw,
NanoClaw, etc.) that extract OAuth tokens from `~/.claude/` and call
the API directly with subscription credentials. **CG does NOT do
this.** CG invokes the official `claude --print` binary as a
subprocess, which is the documented headless mode. The subscription
auth is owned by Claude Code, never seen by CG.

**Google Gemini CLI** ([source](https://geminicli.com/docs/resources/tos-privacy/)):

> "Directly accessing the services powering Gemini CLI using
> third-party software, tools, or services (for example, using
> OpenClaw with Gemini CLI OAuth) is a violation of applicable terms
> and policies."

Same pattern — CG calls `gemini -p` (the official CLI), not the
backend API with stolen tokens. ToS-compliant.

### What CG explicitly does NOT do (and never will)

- Read `~/.claude/oauth.json` or any subscription credential file
- Make HTTP requests to `api.anthropic.com` / `cloudcode-pa.googleapis.com`
  with credentials we extracted ourselves
- Resell Claude or Gemini access to a third party
- Run as a hosted multi-user service on subscription credentials

This is what makes CG fundamentally different from OpenClaw-style
projects that got banned.

---

## API path — opt-in via API keys

If the user sets an env var with their own API key, the dashboard
auto-detects it on startup and adds matching models to the dropdown.

### OpenRouter — set `OPENROUTER_API_KEY`

OpenRouter is a model aggregator that pays providers directly. Pricing
is roughly pass-through (no major markup). One key, hundreds of models.

| Model id | Label | Price (input / output per 1M) | Why |
|---|---|---|---|
| `or-glm-4.7` | GLM-4.7 via OpenRouter | $0.38 / $1.74 | Strong + cheap |
| `or-deepseek-v3` | DeepSeek V3 | $0.27 / $1.10 | Best value coding model |
| `or-qwen3-coder` | Qwen3 Coder | $0.15 / $1.00 | Agentic, 262k ctx |

Sign up: https://openrouter.ai/keys

### Z.ai (GLM) direct — set `ZHIPU_API_KEY`

Zhipu's own platform. Slightly different pricing than OpenRouter
(no aggregator markup, but no aggregator convenience either).

| Model id | Label | Price (input / output per 1M) | Why |
|---|---|---|---|
| `glm-4.7` | GLM-4.7 (Z.ai direct) | $0.60 / $2.20 | Z.ai flagship |
| `glm-4.7-flash` | GLM-4.7 Flash (FREE tier) | free | Daily quota |
| `glm-4.7-flashx` | GLM-4.7 FlashX | $0.07 / $0.40 | Cheapest paid |

Sign up: https://docs.z.ai/guides/overview/pricing

### Anthropic API direct — set `ANTHROPIC_API_KEY`

For when you've maxed your Claude Pro quota and want to keep going.
This is **API billing**, not subscription. Costs add up.

| Model id | Label | Notes |
|---|---|---|
| `claude-api-sonnet` | Claude Sonnet 4.6 (API) | ~$3 / $15 per 1M |

### Google AI Studio — set `GEMINI_API_KEY` (or `GOOGLE_API_KEY`)

Direct Gemini API. Free tier on most models if you stay under
60 RPM / 1000 RPD on Flash.

| Model id | Label | Notes |
|---|---|---|
| `gemini-api-pro` | Gemini Pro (API) | Free tier eligible |

---

## Recommended cost-optimized matrix

For each task type, the cheapest model that's likely to do it well:

| Task | Subscription pick | API pick (if subs maxed) |
|---|---|---|
| Quick syntax/format check | gemini-flash (subs) | or-qwen3-coder ($0.15/$1.00) |
| Daily implementation | claude-sonnet-4-6 (subs) | or-glm-4.7 ($0.38/$1.74) |
| Big refactor (multi-file) | claude-opus-4-7 (subs, 1M ctx) | or-glm-4.7 (200k ctx, much cheaper) |
| Brainstorm / fan-out | All 4 subscription models | + or-deepseek-v3 for diversity |
| Code review (3 angles) | sonnet + opus + gemini-pro | swap one for or-qwen3-coder for 5th opinion |
| Long doc summarize | gemini-3-pro (subs) | gemini-api-pro (free tier) |

---

## How to enable API path

```bash
# In your terminal before launching CG dashboard:
set OPENROUTER_API_KEY=sk-or-...
set ZHIPU_API_KEY=...
# (Optional but rarely needed):
set ANTHROPIC_API_KEY=sk-ant-...
set GEMINI_API_KEY=...

# Then start as usual:
python D:\CG\src\cg.py dashboard
```

Or persist in a `.env` file at `D:\CG\.env` (not committed to git;
already in `.gitignore`).

The dashboard's `/api/agents` endpoint will reflect your active keys.
Check **Tab → Editor → File tree** for a sanity check.

---

## Privacy note

When you use the **API path**, prompts go to the third-party provider
(OpenRouter, Z.ai, etc.). Their privacy policies apply. The
**subscription path** still uses Anthropic / Google but through their
own consumer pipeline (same as if you typed in claude.ai / Gemini
chat).

CG itself never phones home. The dashboard binds to `127.0.0.1` only
by default; nothing leaves your machine except outbound calls to the
provider you explicitly invoked.
