"""CG Dashboard — web UI for multi-agent orchestration.

A single FastAPI app that lets you:

  1. Define a multi-agent workflow (a list of {agent, label, prompt}).
  2. Hit "Run" — every agent launches as its own subprocess in parallel.
  3. Watch each agent's stdout stream live in its own browser panel via
     Server-Sent Events.
  4. Keep run history, download outputs, replay runs.

Architecture
------------

- ``RunManager`` (in-process state): runs a list of agent subprocesses,
  captures stdout line-by-line into per-agent queues, and tracks status.
- ``GET  /``          → serves ``static/index.html``
- ``GET  /api/agents`` → list configured agent kinds (claude, gemini)
- ``GET  /api/presets``→ list bundled workflow presets
- ``POST /api/runs``   → start a run, returns ``run_id``
- ``GET  /api/runs``   → list run history
- ``GET  /api/runs/{id}`` → run metadata + agent statuses
- ``GET  /api/runs/{id}/stream`` → SSE stream of `{agent, type, data}` events
- ``GET  /api/runs/{id}/output/{label}`` → final captured stdout (text)

The dashboard is a single page (``static/index.html``); it talks to the
backend via fetch + EventSource. No build step, no node, no JS framework.

Start with::

    python -m uvicorn dashboard:app --host 127.0.0.1 --port 8765
or, more simply::

    python src/dashboard.py
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

# v48 W0: Conductor — Opus designs custom workflows from raw ideas
from conductor import (
    build_phase1_prompt,
    build_phase2_prompt,
    extract_json_block,
    validate_workflow_spec,
    CANONICAL_ROLES,
)
# Optional HTTP Basic auth — opt-in via CG_AUTH_PASSWORD_HASH env var.
# When unset (the local-dev default), middleware is a no-op.
import auth as _cg_auth


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "src" / "dashboard_static"
RUNS_DIR = ROOT / "outputs" / "dashboard-runs"
RUNS_DIR.mkdir(parents=True, exist_ok=True)
INDEX_PATH = ROOT / "tasks" / "_dashboard_runs.json"
WORKFLOWS_DIR = ROOT / "workflows"
WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)
NOTES_DIR = ROOT / "notes"
NOTES_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Agent invocations — same auth, same subscriptions as the rest of CG
# ---------------------------------------------------------------------------


def _resolve_executable(name: str) -> str:
    direct = shutil.which(name)
    if direct:
        return direct
    if sys.platform.startswith("win"):
        for ext in (".cmd", ".bat", ".exe"):
            cand = shutil.which(name + ext)
            if cand:
                return cand
    return name


try:  # Optional — only used when present
    import ftfy as _ftfy  # type: ignore
except ImportError:
    _ftfy = None  # type: ignore


def _recover_mojibake(text: str) -> str:
    """Best-effort fix for double-encoded UTF-8 strings that come out of
    some CLIs on Windows when their stdout is piped through a non-UTF-8
    code page. The classic symptom: an emoji like 🧠 (UTF-8 bytes
    f0 9f a7 a0) arrives as the four chars `đź§ ` after a
    Windows-1250 → UTF-8 round-trip and ruins downstream HTML.

    Uses ``ftfy.fix_text`` when installed (handles a wide matrix of
    legacy code pages and is well-tested). Falls back to a no-op
    when ftfy isn't available — the raw mojibake survives but nothing
    else breaks.
    """
    if not text or _ftfy is None or all(ord(c) < 128 for c in text):
        return text
    try:
        return _ftfy.fix_text(text)
    except Exception:
        return text


def _describe_stream_event(family: str, line: str) -> str:
    """Best-effort activity description for a filtered stream-json line.

    The visible-content parser ``_parse_stream_json_line`` returns ``[]``
    for non-text events (init, tool_use, hook, result, …) so the panel
    log stays clean. But the user still wants to SEE that the agent is
    active — like watching a CMUX terminal where something is always
    happening. This helper turns each filtered event into a short
    human-readable string the dashboard can show under "currently:".

    Returns an empty string when the line yields no useful description
    (so the caller can keep the previous activity line visible).
    """
    s = line.strip()
    if not s or s[0] not in "{[":
        return ""
    try:
        ev = json.loads(s)
    except (ValueError, TypeError):
        return ""
    if not isinstance(ev, dict):
        return ""
    ev_type = ev.get("type")

    if family == "claude":
        if ev_type == "system" and ev.get("subtype") == "init":
            sess = ev.get("session_id") or ""
            return f"session ready{' · ' + sess[:8] if sess else ''}"
        if ev_type == "assistant":
            msg = ev.get("message") or {}
            content = msg.get("content") or []
            if isinstance(content, list):
                for blk in content:
                    if not isinstance(blk, dict):
                        continue
                    btype = blk.get("type")
                    if btype == "tool_use":
                        name = blk.get("name") or "tool"
                        return f"calling tool · {name}"
                    if btype == "thinking":
                        return "thinking…"
                    if btype == "text":
                        # The visible-content parser handles these; we
                        # just acknowledge the activity for the panel.
                        return "writing…"
            return "writing…"
        if ev_type == "user":
            # Tool result echoed back to the model
            return "tool result returned"
        if ev_type == "result":
            status = ev.get("status") or ev.get("subtype") or ""
            return f"finalizing{' · ' + status if status else ''}"
        if ev_type:
            return str(ev_type)

    if family == "gemini":
        if ev_type == "init":
            return "session ready"
        if ev_type == "message" and ev.get("role") == "assistant":
            return "writing…"
        if ev_type == "tool_call" or ev_type == "tool_use":
            name = ev.get("name") or ev.get("tool") or "tool"
            return f"calling tool · {name}"
        if ev_type == "result":
            return "finalizing"
        if ev_type == "thinking":
            return "thinking…"
        if ev_type:
            return str(ev_type)

    return ""


def _parse_stream_json_line(family: str, line: str) -> list[str] | None:
    """K3 — extract assistant text deltas from a stream-json output line.

    Returns:
      * ``None`` if the line is not parseable JSON (caller should treat
        it as a raw log line).
      * ``[]`` if the line parsed as a system / hook / init / result
        event we want to filter out of the visible log.
      * a non-empty list of strings — each is one text delta the UI
        should append to the agent's stream.

    Claude shape (`--output-format stream-json --verbose`)::

        {"type":"system","subtype":"init", ...}
        {"type":"assistant","message":{"content":[{"type":"text","text":"H"}]}}
        {"type":"result", ...}

    Gemini shape (`--output-format stream-json`)::

        {"type":"init", ...}
        {"type":"message","role":"assistant","content":"H","delta":true}
        {"type":"result", ...}
    """
    line = line.strip()
    if not line or line[0] not in "{[":
        return None
    try:
        ev = json.loads(line)
    except (ValueError, TypeError):
        return None
    if not isinstance(ev, dict):
        return None

    out: list[str] = []
    ev_type = ev.get("type")

    if family == "claude":
        if ev_type == "assistant":
            msg = ev.get("message") or {}
            content = msg.get("content") or []
            if isinstance(content, list):
                for blk in content:
                    if isinstance(blk, dict) and blk.get("type") == "text":
                        text = blk.get("text") or ""
                        if text:
                            out.append(text)
            elif isinstance(content, str) and content:
                out.append(content)
            return out
        # Filter init / system / result / tool_use / hook events
        return []

    if family == "gemini":
        if ev_type == "message" and ev.get("role") == "assistant":
            content = ev.get("content")
            if isinstance(content, str) and content:
                out.append(content)
            elif isinstance(content, list):
                for blk in content:
                    if isinstance(blk, dict):
                        text = blk.get("text") or blk.get("content") or ""
                        if text:
                            out.append(text)
                    elif isinstance(blk, str):
                        out.append(blk)
            return out
        return []

    return None


# Each entry is one selectable model in the dashboard. The "family" lets
# the UI group Claude vs Gemini in the dropdown.
AGENT_KINDS: dict[str, dict[str, Any]] = {
    # ---- Claude (Claude Pro subscription via OAuth) -----------------------
    "claude-sonnet-4-6": {
        "label": "Claude Sonnet 4.6",
        "family": "claude",
        "summary": "fast, balanced — daily driver",
        "command": [_resolve_executable("claude"), "--print",
                     "--model", "claude-sonnet-4-6"],
        "stdin_prompt": True,
        "env": {},
    },
    "claude-opus-4-7": {
        "label": "Claude Opus 4.7 (1M context)",
        "family": "claude",
        "summary": "smartest, 1M tokens — for big refactors",
        "command": [_resolve_executable("claude"), "--print",
                     "--model", "claude-opus-4-7"],
        "stdin_prompt": True,
        "env": {},
    },
    "claude-opus-4-6": {
        "label": "Claude Opus 4.6",
        "family": "claude",
        "summary": "previous-gen Opus, still strong",
        "command": [_resolve_executable("claude"), "--print",
                     "--model", "claude-opus-4-6"],
        "stdin_prompt": True,
        "env": {},
    },
    # ---- Gemini (Google account via OAuth, GOOGLE_GENAI_USE_GCA=true) -----
    #
    # Model strings MUST match what the gemini-cli (@google/gemini-cli) accepts.
    # Discovered the hard way: shorthand "flash" / "pro" passed via -m get
    # routed by Google's gateway to gemini-3.1-pro-preview which has flaky
    # capacity (429 MODEL_CAPACITY_EXHAUSTED). Use explicit canonical names.
    # Gemini CLI quirk: -p needs a value; passing the whole prompt as
    # a single argv element fails on Windows for long prompts (escape /
    # length issues). Pattern that works: -p "" placeholder + stdin
    # carrying the actual text. The CLI's own help confirms this:
    # "Use -p/--prompt for non-interactive (headless) mode. Appended
    #  to input on stdin (if any)."
    "gemini-flash": {
        "label": "Gemini 2.5 Flash",
        "family": "gemini",
        "summary": "fastest Gemini — quick checks, drafts",
        "command": [_resolve_executable("gemini"), "--skip-trust",
                     "-m", "gemini-2.5-flash", "-p", ""],
        "stdin_prompt": True,
        "env": {"GOOGLE_GENAI_USE_GCA": "true"},
    },
    "gemini-pro": {
        "label": "Gemini 2.5 Pro",
        "family": "gemini",
        "summary": "default Gemini — balanced quality",
        "command": [_resolve_executable("gemini"), "--skip-trust",
                     "-m", "gemini-2.5-pro", "-p", ""],
        "stdin_prompt": True,
        "env": {"GOOGLE_GENAI_USE_GCA": "true"},
    },
    # ---- OpenCode (sst/opencode CLI — open-source local agent) -----------
    # https://github.com/sst/opencode — TUI/CLI similar to Claude Code,
    # supports any provider via config. Headless invocation: `opencode run`.
    # Subscription-friendly: bring-your-own provider keys, no per-token
    # markup over native pricing.
    "opencode": {
        "label": "OpenCode (open-source)",
        "family": "opencode",
        "summary": "sst/opencode CLI — bring your own model config",
        "command": [_resolve_executable("opencode"), "run"],
        "stdin_prompt": True,
        "env": {},
    },
    # ---- browser agent (built-in) ----------------------------------------
    "browser": {
        "label": "🌐 Browser (Playwright)",
        "family": "browser",
        "summary": "Headless Chromium with full action API — prompt is JSON",
        "runner": "browser",
    },
    # ---- subworkflow agent (built-in) ------------------------------------
    "subworkflow": {
        "label": "🔁 Sub-workflow",
        "family": "subworkflow",
        "summary": "Run a saved workflow as a step. Prompt is JSON {workflow, variables?}",
        "runner": "subworkflow",
    },
    # ---- browser pilot (v17 — autonomous Perplexity-Computer-style loop)
    "browser-pilot": {
        "label": "🤖 Browser Pilot (autonomous)",
        "family": "browser",
        "summary": "Goal-driven loop: page → LLM → next action → repeat. Prompt is plain English or JSON {goal, model?, max_steps?, start_url?}",
        "runner": "browser_pilot",
    },
}


# ---------------------------------------------------------------------------
# Optional HTTP-based providers (require user-supplied API keys, opt-in)
#
# NOT a subscription token reuse — each provider below is invoked through
# its OWN paid API with the user's own key. Anthropic and Google's recent
# ToS updates ban OAuth-token reuse from third-party tools; subprocess
# invocation of the official CLIs (the rest of AGENT_KINDS above) is the
# documented and supported path. This block is for users who want to add
# direct paid API access to additional providers (GLM via Z.ai, anything
# via OpenRouter, etc.) — the dashboard auto-detects which API keys are
# present in the environment and exposes only those models.
# ---------------------------------------------------------------------------


def _build_http_models() -> dict[str, dict[str, Any]]:
    """Detect which API keys are set in the environment and return a dict
    of new model entries to merge into AGENT_KINDS."""
    out: dict[str, dict[str, Any]] = {}

    # OpenRouter — any model, single API, ~no markup over native pricing
    if os.environ.get("OPENROUTER_API_KEY"):
        out.update({
            "or-glm-4.7": {
                "label": "GLM-4.7 via OpenRouter",
                "family": "glm",
                "summary": "$0.38/$1.74 per M tokens — strong + cheap",
                "runner": "http",
                "http": {
                    "endpoint": "https://openrouter.ai/api/v1/chat/completions",
                    "model": "z-ai/glm-4.7",
                    "api_key_env": "OPENROUTER_API_KEY",
                    "headers": {"HTTP-Referer": "https://github.com/hustlerv369/CG",
                                 "X-Title": "CG Dashboard"},
                },
            },
            "or-deepseek-v3": {
                "label": "DeepSeek V3 via OpenRouter",
                "family": "deepseek",
                "summary": "$0.27/$1.10 per M — strongest value coding model",
                "runner": "http",
                "http": {
                    "endpoint": "https://openrouter.ai/api/v1/chat/completions",
                    "model": "deepseek/deepseek-chat-v3",
                    "api_key_env": "OPENROUTER_API_KEY",
                    "headers": {"HTTP-Referer": "https://github.com/hustlerv369/CG",
                                 "X-Title": "CG Dashboard"},
                },
            },
            "or-qwen3-coder": {
                "label": "Qwen3 Coder via OpenRouter",
                "family": "qwen",
                "summary": "$0.15/$1.00 per M — agentic coding, 262k ctx",
                "runner": "http",
                "http": {
                    "endpoint": "https://openrouter.ai/api/v1/chat/completions",
                    "model": "qwen/qwen3-coder",
                    "api_key_env": "OPENROUTER_API_KEY",
                    "headers": {"HTTP-Referer": "https://github.com/hustlerv369/CG",
                                 "X-Title": "CG Dashboard"},
                },
            },
            "or-deepseek-r1": {
                "label": "DeepSeek R1 via OpenRouter",
                "family": "deepseek",
                "summary": "$0.55/$2.19 per M — strong reasoning model",
                "runner": "http",
                "http": {
                    "endpoint": "https://openrouter.ai/api/v1/chat/completions",
                    "model": "deepseek/deepseek-r1",
                    "api_key_env": "OPENROUTER_API_KEY",
                    "headers": {"HTTP-Referer": "https://github.com/hustlerv369/CG",
                                 "X-Title": "CG Dashboard"},
                },
            },
            "or-kimi-k2": {
                "label": "Kimi K2 via OpenRouter",
                "family": "moonshot",
                "summary": "$0.55/$2.19 per M — Moonshot 1T MoE, agentic",
                "runner": "http",
                "http": {
                    "endpoint": "https://openrouter.ai/api/v1/chat/completions",
                    "model": "moonshotai/kimi-k2",
                    "api_key_env": "OPENROUTER_API_KEY",
                    "headers": {"HTTP-Referer": "https://github.com/hustlerv369/CG",
                                 "X-Title": "CG Dashboard"},
                },
            },
            "or-llama-3.3": {
                "label": "Llama 3.3 70B via OpenRouter",
                "family": "llama",
                "summary": "$0.13/$0.39 per M — Meta open weights, fast",
                "runner": "http",
                "http": {
                    "endpoint": "https://openrouter.ai/api/v1/chat/completions",
                    "model": "meta-llama/llama-3.3-70b-instruct",
                    "api_key_env": "OPENROUTER_API_KEY",
                    "headers": {"HTTP-Referer": "https://github.com/hustlerv369/CG",
                                 "X-Title": "CG Dashboard"},
                },
            },
            "or-mistral-large": {
                "label": "Mistral Large via OpenRouter",
                "family": "mistral",
                "summary": "$2/$6 per M — Mistral flagship, strong code",
                "runner": "http",
                "http": {
                    "endpoint": "https://openrouter.ai/api/v1/chat/completions",
                    "model": "mistralai/mistral-large",
                    "api_key_env": "OPENROUTER_API_KEY",
                    "headers": {"HTTP-Referer": "https://github.com/hustlerv369/CG",
                                 "X-Title": "CG Dashboard"},
                },
            },
        })

    # DeepSeek API direct (cheapest path to DeepSeek if you have a key)
    if os.environ.get("DEEPSEEK_API_KEY"):
        out.update({
            "deepseek-chat": {
                "label": "DeepSeek Chat (direct API)",
                "family": "deepseek",
                "summary": "$0.27/$1.10 per M — cheapest robust coder",
                "runner": "http",
                "http": {
                    "endpoint": "https://api.deepseek.com/chat/completions",
                    "model": "deepseek-chat",
                    "api_key_env": "DEEPSEEK_API_KEY",
                    "headers": {},
                },
            },
            "deepseek-reasoner": {
                "label": "DeepSeek Reasoner (direct API)",
                "family": "deepseek",
                "summary": "$0.55/$2.19 per M — R1-class reasoning",
                "runner": "http",
                "http": {
                    "endpoint": "https://api.deepseek.com/chat/completions",
                    "model": "deepseek-reasoner",
                    "api_key_env": "DEEPSEEK_API_KEY",
                    "headers": {},
                },
            },
        })

    # Moonshot Kimi direct API
    if os.environ.get("MOONSHOT_API_KEY"):
        out["kimi-k2-direct"] = {
            "label": "Kimi K2 (Moonshot direct)",
            "family": "moonshot",
            "summary": "$0.60/$2.50 per M — Moonshot direct, China region",
            "runner": "http",
            "http": {
                "endpoint": "https://api.moonshot.cn/v1/chat/completions",
                "model": "moonshot-v1-128k",
                "api_key_env": "MOONSHOT_API_KEY",
                "headers": {},
            },
        }

    # Z.ai GLM direct
    if os.environ.get("ZHIPU_API_KEY") or os.environ.get("ZAI_API_KEY"):
        env_var = "ZHIPU_API_KEY" if os.environ.get("ZHIPU_API_KEY") else "ZAI_API_KEY"
        out.update({
            "glm-4.7": {
                "label": "GLM-4.7 (Z.ai direct)",
                "family": "glm",
                "summary": "$0.60/$2.20 per M — Z.ai flagship",
                "runner": "http",
                "http": {
                    "endpoint": "https://api.z.ai/api/paas/v4/chat/completions",
                    "model": "glm-4.7",
                    "api_key_env": env_var,
                    "headers": {},
                },
            },
            "glm-4.7-flash": {
                "label": "GLM-4.7 Flash (FREE tier)",
                "family": "glm",
                "summary": "Free tier — fastest GLM",
                "runner": "http",
                "http": {
                    "endpoint": "https://api.z.ai/api/paas/v4/chat/completions",
                    "model": "glm-4.7-flash",
                    "api_key_env": env_var,
                    "headers": {},
                },
            },
            "glm-4.7-flashx": {
                "label": "GLM-4.7 FlashX (ultra-cheap)",
                "family": "glm",
                "summary": "$0.07/$0.40 per M — cheapest paid GLM",
                "runner": "http",
                "http": {
                    "endpoint": "https://api.z.ai/api/paas/v4/chat/completions",
                    "model": "glm-4.7-flashx",
                    "api_key_env": env_var,
                    "headers": {},
                },
            },
        })

    # Anthropic API direct (separate billing — costs money outside Pro)
    if os.environ.get("ANTHROPIC_API_KEY"):
        out["claude-api-sonnet"] = {
            "label": "Claude Sonnet 4.6 (API)",
            "family": "claude",
            "summary": "API billing — independent of Claude Pro quota",
            "runner": "http",
            "http": {
                "endpoint": "https://api.anthropic.com/v1/messages",
                "model": "claude-sonnet-4-6",
                "api_key_env": "ANTHROPIC_API_KEY",
                "anthropic_native": True,  # different request shape
            },
        }

    # Google AI Studio (Gemini API direct)
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        env_var = "GEMINI_API_KEY" if os.environ.get("GEMINI_API_KEY") else "GOOGLE_API_KEY"
        out["gemini-api-pro"] = {
            "label": "Gemini Pro (API)",
            "family": "gemini",
            "summary": "API billing — independent of Google subscription",
            "runner": "http",
            "http": {
                "endpoint": "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent",
                "model": "gemini-pro",
                "api_key_env": env_var,
                "google_native": True,
            },
        }

    return out


# Merge HTTP-based models into AGENT_KINDS at startup so they appear in
# the dropdown. Re-evaluated each time get_agents is called so adding a
# new env var and refreshing /api/agents picks them up without restart.
AGENT_KINDS.update(_build_http_models())


# ---------------------------------------------------------------------------
# Custom HTTP "tool" agents — user-defined endpoints as workflow steps.
# Saved to D:\CG\custom_agents.json as a list of { id, label, family,
# summary, http: {endpoint, model, api_key_env, headers, format} }.
# Loaded on startup and merged into AGENT_KINDS.
# ---------------------------------------------------------------------------

CUSTOM_AGENTS_PATH = ROOT / "custom_agents.json"
SCHEDULES_PATH = ROOT / "schedules.json"
TUNNEL_DIR = ROOT / "tunnel"
TUNNEL_DIR.mkdir(parents=True, exist_ok=True)
NOTIFICATIONS_PATH = ROOT / "notifications.json"


def _load_custom_agents() -> dict[str, dict[str, Any]]:
    if not CUSTOM_AGENTS_PATH.exists():
        return {}
    try:
        raw = json.loads(CUSTOM_AGENTS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(raw, list):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        kid = entry.get("id")
        if not kid:
            continue
        # Normalize to AGENT_KINDS shape
        out[kid] = {
            "label": entry.get("label", kid),
            "family": entry.get("family", "custom"),
            "summary": entry.get("summary", "user-defined HTTP agent"),
            "runner": "http",
            "http": entry["http"],
        }
    return out


def _save_custom_agents(items: list[dict[str, Any]]) -> None:
    CUSTOM_AGENTS_PATH.write_text(
        json.dumps(items, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# Apply custom agents on startup
AGENT_KINDS.update(_load_custom_agents())


# ---------------------------------------------------------------------------
# Cloudflare Tunnel — auto-download + spawn (phone dispatch enabler)
# ---------------------------------------------------------------------------


_auth_session: dict[str, Any] = {
    "active": None,        # {slug, url, started_at} or None
    "save_event": None,    # threading.Event
    "cancel_event": None,  # threading.Event
    "thread": None,
    "result": None,
}


_tunnel_state: dict[str, Any] = {
    "running": False,
    "url": None,
    "pid": None,
    "started_at": None,
    "port": int(os.environ.get("CG_DASHBOARD_PORT", "8765")),
    "_proc": None,
    "binary": None,
}


def _ensure_cloudflared() -> str | None:
    r"""Find or auto-download a cloudflared binary. Returns absolute path
    or None on failure.

    Strategy:
      1. Check PATH (shutil.which)
      2. Check D:\CG\tunnel\cloudflared.exe (cached download)
      3. Try to download from GitHub releases (Windows amd64 default)
    """
    import shutil
    from urllib.request import urlretrieve

    cached = TUNNEL_DIR / ("cloudflared.exe" if sys.platform.startswith("win") else "cloudflared")
    if cached.exists() and cached.stat().st_size > 0:
        return str(cached)

    direct = shutil.which("cloudflared") or shutil.which("cloudflared.exe")
    if direct:
        return direct

    # Auto-download (Windows amd64 — most common)
    if sys.platform.startswith("win"):
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
    elif sys.platform == "darwin":
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-amd64.tgz"
        return None  # tgz needs extraction; user can install via brew
    else:
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"

    try:
        urlretrieve(url, cached)
        if not sys.platform.startswith("win"):
            cached.chmod(0o755)
        return str(cached)
    except Exception:
        return None


def _spawn_tunnel(binary_path: str, port: int) -> tuple[str | None, Any]:
    """Spawn cloudflared, parse output for the trycloudflare URL,
    return (url, proc)."""
    log_path = TUNNEL_DIR / "cloudflared.log"

    proc = subprocess.Popen(
        [binary_path, "tunnel", "--url", f"http://127.0.0.1:{port}",
         "--no-autoupdate"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        creationflags=(0x08000000 if sys.platform.startswith("win") else 0),
    )

    url_holder: dict[str, str] = {}

    def _scan_output() -> None:
        with open(log_path, "w", encoding="utf-8") as logfp:
            try:
                assert proc.stdout is not None
                for line in proc.stdout:
                    logfp.write(line)
                    logfp.flush()
                    # Look for: "https://<random>.trycloudflare.com"
                    if "trycloudflare.com" in line and "https://" in line:
                        m = _re.search(r"https://[a-zA-Z0-9.-]+\.trycloudflare\.com", line)
                        if m and "url" not in url_holder:
                            url_holder["url"] = m.group(0)
            except Exception:
                pass

    threading.Thread(target=_scan_output, daemon=True).start()

    # Wait up to 20 seconds for the URL to appear
    for _ in range(40):
        if "url" in url_holder:
            break
        time.sleep(0.5)

    return url_holder.get("url"), proc


# ---------------------------------------------------------------------------
# Run-finished webhook notifications
# ---------------------------------------------------------------------------


def _load_notifications() -> dict[str, Any]:
    if not NOTIFICATIONS_PATH.exists():
        return {"webhook_url": "", "kind": "ntfy",
                "on_complete": True, "on_failed": True}
    try:
        return json.loads(NOTIFICATIONS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"webhook_url": "", "kind": "ntfy",
                "on_complete": True, "on_failed": True}


def _send_notification(run: "RunState") -> None:
    cfg = _load_notifications()
    url = cfg.get("webhook_url", "").strip()
    if not url:
        return
    failed_count = sum(1 for a in run.agents.values() if a.status == "failed")
    if failed_count > 0 and not cfg.get("on_failed", True):
        return
    if failed_count == 0 and not cfg.get("on_complete", True):
        return

    title = f"CG run: {run.title}"
    body_parts = [f"Run {run.id} finished",
                    f"{len(run.agents)} agents — {failed_count} failed"]
    for a in run.agents.values():
        body_parts.append(
            f"  • {a.label} ({a.agent}): {a.status} (exit={a.exit_code})"
        )
    body = "\n".join(body_parts)
    kind = cfg.get("kind", "ntfy")

    import urllib.request

    try:
        if kind == "ntfy":
            # ntfy.sh expects PUT with title in header + plain body
            req = urllib.request.Request(
                url,
                data=body.encode("utf-8"),
                headers={"Title": title,
                         "Tags": "robot,fire" if failed_count else "robot,white_check_mark"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=10).read()
        elif kind == "discord":
            # Discord webhook expects {content: "..."}
            payload = {"content": f"**{title}**\n```\n{body}\n```"}
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=10).read()
        elif kind == "slack":
            # Slack incoming webhook expects {text: "..."}
            payload = {"text": f"*{title}*\n```{body}```"}
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=10).read()
        else:  # generic
            payload = {"title": title, "body": body, "run_id": run.id,
                       "failed": failed_count > 0}
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=10).read()
    except Exception:
        # Notifications are fire-and-forget — never crash the run
        pass


# ---------------------------------------------------------------------------
# Schedules (cron-style periodic runs)
# ---------------------------------------------------------------------------


def _load_schedules() -> list[dict[str, Any]]:
    if not SCHEDULES_PATH.exists():
        return []
    try:
        data = json.loads(SCHEDULES_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _start_scheduler(manager: "RunManager") -> None:
    """Background thread polling schedules.json every 30s and dispatching
    enabled schedules whose interval has elapsed since last run."""
    last_runs: dict[str, float] = {}

    def _tick() -> None:
        while True:
            try:
                schedules = _load_schedules()
                now = time.time()
                for s in schedules:
                    if not s.get("enabled"):
                        continue
                    workflow_name = s.get("workflow")
                    interval_min = int(s.get("interval_minutes", 0))
                    if not workflow_name or interval_min < 1:
                        continue
                    key = f"{workflow_name}::{interval_min}"
                    last = last_runs.get(key, 0)
                    if now - last < interval_min * 60:
                        continue
                    # Time to fire
                    path = WORKFLOWS_DIR / f"{_safe_workflow_name(workflow_name)}.json"
                    if not path.exists():
                        continue
                    try:
                        data = json.loads(path.read_text(encoding="utf-8"))
                        spec = data.get("spec") or []
                        if not spec:
                            continue
                        title = f"scheduled: {data.get('title', workflow_name)}"
                        variables = dict(data.get("variables", {}) or {})
                        variables.update(s.get("variables", {}) or {})
                        manager.start_run(title, spec, variables=variables)
                        last_runs[key] = now
                    except Exception:
                        pass
            except Exception:
                pass
            time.sleep(30)

    threading.Thread(target=_tick, daemon=True).start()


# Backward-compatible aliases for old presets / clients ("claude" → default
# Sonnet, "gemini" → default Pro)
AGENT_ALIASES = {
    "claude": "claude-sonnet-4-6",
    "gemini": "gemini-pro",
}


def _resolve_agent_kind(kind: str) -> str:
    """Map legacy aliases to current ids; passthrough otherwise."""
    return AGENT_ALIASES.get(kind, kind)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class AgentRunState:
    label: str
    agent: str
    depends_on: list[str] = field(default_factory=list)
    status: str = "queued"  # queued | waiting | running | done | failed | cancelled
    started: float | None = None
    finished: float | None = None
    exit_code: int | None = None
    log_lines: list[str] = field(default_factory=list)
    stderr_lines: list[str] = field(default_factory=list)
    process: Any = field(default=None, repr=False)  # subprocess.Popen
    # K3: opt-in streaming. When True and the agent family supports it
    # (claude / gemini), the underlying CLI is invoked with stream-json
    # output and each assistant text delta is emitted as its own log
    # event so the UI can show token-by-token output.
    streaming: bool = False
    # v46 W2: optional role tag (Visionary / Architect / Designer / Engineer
    # / QA / Critic / Operator / Researcher / Strategist). Pure display —
    # `label` stays the slug used in depends_on + {{label}} substitution.
    # Empty string = no badge rendered (backward compat for older presets).
    role: str = ""
    # v47.1 W0.2: refinement loop with another agent. When set, after
    # this step's first run, the engine optionally re-runs the partner
    # then this step again, up to max_rounds, with the partner's prompt
    # appended with this step's previous output as critique. Stops
    # early if the regex in accept_when matches this step's output.
    iterate_with: str = ""
    max_rounds: int = 1
    accept_when: str = ""
    rounds_completed: int = 0  # bumped each time this step finishes a round
    # v51 — opt-in fail-soft. When True, this step still runs even if
    # one or more `depends_on` agents failed. The failed dep's
    # {{label}} substitution falls back to a placeholder so prompts
    # don't crash. Default: False (existing strict behavior).
    continue_on_dep_failure: bool = False
    # v51 — liveness telemetry. `last_activity_at` is bumped on every
    # stdout line (visible OR filtered system/init events) so the UI
    # can render "connected, waiting Xs" instead of a frozen 0-chars
    # block. `first_visible_at` records when the first user-visible
    # text arrived (used by the v45 watchdog rebuild — fires on lack
    # of *visible* content, not lack of raw stdout).
    last_activity_at: float | None = None
    first_visible_at: float | None = None

    def to_public(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "agent": self.agent,
            "depends_on": self.depends_on,
            "status": self.status,
            "started": self.started,
            "finished": self.finished,
            "exit_code": self.exit_code,
            "log_chars": sum(len(l) for l in self.log_lines),
            "log_tail": "\n".join(self.log_lines[-200:]),
            "stderr_chars": sum(len(l) for l in self.stderr_lines),
            "streaming": self.streaming,
            "role": self.role,
            "iterate_with": self.iterate_with,
            "max_rounds": self.max_rounds,
            "rounds_completed": self.rounds_completed,
            "continue_on_dep_failure": self.continue_on_dep_failure,
            "last_activity_at": self.last_activity_at,
            "first_visible_at": self.first_visible_at,
        }


@dataclass
class RunState:
    id: str
    title: str
    created: float
    spec: list[dict[str, Any]]
    agents: dict[str, AgentRunState] = field(default_factory=dict)
    # v47.1 W0.2: track watcher thread refs so test teardown (and any
    # caller) can join them and ensure no _persist_index() fires after
    # the run is supposed to be quiescent.
    _watcher_threads: list[Any] = field(default_factory=list, repr=False)
    finished: bool = False
    # Per-run env overrides (e.g. API keys forwarded from browser
    # Settings) and ${VAR} substitutions for prompts.
    secrets: dict[str, str] = field(default_factory=dict)
    variables: dict[str, str] = field(default_factory=dict)
    # Per-agent bindings (browser agents put extracted data here, so
    # downstream agents can access them via {{label.field}})
    bindings: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "created": self.created,
            "finished": self.finished,
            "spec": self.spec,  # original prompts preserved for rerun
            "agents": [a.to_public() for a in self.agents.values()],
        }


# ---------------------------------------------------------------------------
# Run manager — runs subprocesses in threads, pumps lines into asyncio queues
# ---------------------------------------------------------------------------


class RunManager:
    def __init__(self) -> None:
        self.runs: dict[str, RunState] = {}
        # one asyncio.Queue per (run_id, label) for SSE consumers
        self.streams: dict[tuple[str, str], asyncio.Queue] = {}
        self.lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def _emit(self, run_id: str, label: str, event: dict[str, Any]) -> None:
        key = (run_id, label)
        q = self.streams.get(key)
        if q is None or self._loop is None:
            return
        # We are on a worker thread; bounce into the loop.
        try:
            asyncio.run_coroutine_threadsafe(q.put(event), self._loop)
        except RuntimeError:
            pass  # loop closed — ignore

    def _emit_run(self, run_id: str, event: dict[str, Any]) -> None:
        # Fan-out to all agent streams for this run (consumers can filter)
        with self.lock:
            keys = [k for k in self.streams if k[0] == run_id]
        for k in keys:
            q = self.streams.get(k)
            if q and self._loop:
                asyncio.run_coroutine_threadsafe(q.put(event), self._loop)

    def start_run(self, title: str, spec: list[dict[str, Any]],
                    secrets: dict[str, str] | None = None,
                    variables: dict[str, str] | None = None) -> RunState:
        run_id = uuid.uuid4().hex[:12]
        run = RunState(
            id=run_id,
            title=title or f"run-{run_id}",
            created=time.time(),
            spec=spec,
            secrets=secrets or {},
            variables=variables or {},
        )
        # Validate first
        labels_in_spec: set[str] = set()
        for i, item in enumerate(spec):
            label = item.get("label") or f"agent-{i+1}"
            raw_kind = item.get("agent")
            agent_kind = _resolve_agent_kind(raw_kind)
            if agent_kind not in AGENT_KINDS:
                raise HTTPException(400, f"unknown agent {raw_kind!r} for {label}")
            # Normalize spec to use canonical kind id everywhere downstream
            item["agent"] = agent_kind
            if label in labels_in_spec:
                raise HTTPException(400, f"duplicate label {label!r}")
            labels_in_spec.add(label)
        # Validate depends_on references
        for i, item in enumerate(spec):
            label = item.get("label") or f"agent-{i+1}"
            for dep in item.get("depends_on", []) or []:
                if dep not in labels_in_spec:
                    raise HTTPException(
                        400,
                        f"agent {label!r} depends on {dep!r} which is not in this run",
                    )
                if dep == label:
                    raise HTTPException(400, f"agent {label!r} cannot depend on itself")
        # v47.1 W0.2 — validate iterate_with references
        for i, item in enumerate(spec):
            label = item.get("label") or f"agent-{i+1}"
            iter_with = item.get("iterate_with")
            if not iter_with:
                continue
            if iter_with == label:
                raise HTTPException(
                    400,
                    f"agent {label!r} iterate_with cannot reference itself",
                )
            if iter_with not in labels_in_spec:
                raise HTTPException(
                    400,
                    f"agent {label!r} iterate_with {iter_with!r} which is not in this run",
                )
            mr = item.get("max_rounds", 1)
            if not isinstance(mr, int) or not (1 <= mr <= 10):
                raise HTTPException(
                    400,
                    f"agent {label!r} max_rounds must be int in [1, 10]",
                )
        # Build state
        for i, item in enumerate(spec):
            label = item.get("label") or f"agent-{i+1}"
            # v54 — streaming defaults to TRUE. Stream-json gives the
            # UI live token deltas + system/init + tool_use heartbeats
            # ("currently: thinking · 12s") instead of a silent
            # "connecting" until the buffered output dumps at the end.
            # Spec steps that explicitly set `streaming: false` opt out
            # (legacy non-streaming behavior — buffered output, no
            # heartbeat). Agents whose family doesn't support stream-
            # json (only claude/gemini do) get streaming=False applied
            # downstream in `_run_one` regardless of this flag.
            streaming_field = item.get("streaming")
            streaming_default = True
            streaming_value = (
                bool(streaming_field)
                if streaming_field is not None
                else streaming_default
            )
            run.agents[label] = AgentRunState(
                label=label,
                agent=item["agent"],
                depends_on=list(item.get("depends_on", []) or []),
                status="queued" if not item.get("depends_on") else "waiting",
                streaming=streaming_value,
                role=str(item.get("role", "") or ""),
                iterate_with=str(item.get("iterate_with", "") or ""),
                max_rounds=int(item.get("max_rounds", 1) or 1),
                accept_when=str(item.get("accept_when", "") or ""),
                continue_on_dep_failure=bool(
                    item.get("continue_on_dep_failure", False)
                ),
            )
        self.runs[run_id] = run
        self._persist_index()

        # Each agent runs in its own thread; the thread blocks on its
        # dependencies first via _wait_for_deps.
        for item in spec:
            label = item["label"] if "label" in item else None
            if not label:
                # backfill any missing labels
                for i2, it in enumerate(spec):
                    if it is item:
                        label = f"agent-{i2+1}"
                        break
            t = threading.Thread(
                target=self._run_one_with_deps,
                args=(run, label, item.get("agent"), item.get("prompt", "")),
                daemon=True,
            )
            t.start()
        # Watcher thread to mark run finished
        _wt = threading.Thread(target=self._watch_run, args=(run,), daemon=True)
        run._watcher_threads.append(_wt)
        _wt.start()
        return run

    def _wait_for_deps(self, run: RunState, agent_state: AgentRunState) -> bool:
        """Block until every dependency reaches a terminal status.

        Returns False if any dep failed/cancelled AND this agent does
        NOT have ``continue_on_dep_failure`` set (caller should mark
        the agent failed too). When fail-soft is on, returns True even
        with failed upstreams — `_substitute_prompt` will substitute
        a placeholder for missing `{{label}}` content.
        """
        if not agent_state.depends_on:
            return True
        agent_state.status = "waiting"
        self._emit(run.id, agent_state.label, {"event": "status", "data": {
            "label": agent_state.label, "status": "waiting"}})
        while True:
            statuses = [run.agents[d].status for d in agent_state.depends_on
                         if d in run.agents]
            terminal = {"done", "failed", "cancelled"}
            if all(s in terminal for s in statuses):
                # All deps reached a terminal state.
                if any(s in {"failed", "cancelled"} for s in statuses):
                    if agent_state.continue_on_dep_failure:
                        # Note in the log so the user understands why
                        # {{deplabel}} placeholders may be empty.
                        broken = [d for d in agent_state.depends_on
                                   if run.agents.get(d) and
                                   run.agents[d].status in {"failed", "cancelled"}]
                        msg = (f"[continue-on-dep-failure] proceeding without "
                               f"{', '.join(broken)} — placeholder substitution will fill in")
                        agent_state.log_lines.append(msg)
                        self._emit(run.id, agent_state.label, {"event": "log", "data": {
                            "label": agent_state.label, "line": msg}})
                        return True
                    return False
                return True
            time.sleep(0.5)

    def _substitute_prompt(self, run: RunState, prompt: str,
                            depends_on: list[str]) -> str:
        """Replace ``{{...}}`` and ``${VAR}`` placeholders.

        Order:
          1. ``${VAR}`` — run.variables (per-run user-supplied env)
          2. ``{{label}}`` — dependency outputs
          3. ``{{file:...}}`` / ``{{git:...}}`` / ``{{shell:...}}`` — context
        """
        result = prompt

        # ${VAR} substitution from run.variables (n8n-style env vars)
        if run.variables:
            for k, v in run.variables.items():
                result = result.replace("${" + k + "}", str(v))

        # Dependency outputs (and browser agent bindings)
        for dep in depends_on or []:
            agent = run.agents.get(dep)
            if agent is None:
                continue
            # First: {{dep.field}} from browser bindings (more specific)
            dep_bindings = (run.bindings or {}).get(dep, {})
            for field_name, field_val in dep_bindings.items():
                if isinstance(field_val, (list, dict)):
                    field_str = json.dumps(field_val, indent=2,
                                             ensure_ascii=False, default=str)
                else:
                    field_str = str(field_val) if field_val is not None else ""
                result = result.replace(
                    "{{" + dep + "." + field_name + "}}", field_str)
            # Then: bare {{dep}} = full agent output. v51 — if the dep
            # finished in a non-`done` terminal state and we're running
            # under continue_on_dep_failure, substitute a clear human-
            # readable placeholder so the agent's prompt still parses.
            if agent.status in {"failed", "cancelled"}:
                output = (f"[upstream agent '{dep}' did not complete "
                          f"(status={agent.status}) — proceed without it]")
            else:
                output = "\n".join(agent.log_lines)
            result = result.replace("{{" + dep + "}}", output)

        # File / git / shell placeholders, with project root override
        # available via run.secrets["CG_PROJECT_ROOT"] (forwarded from
        # the browser Settings tab).
        prev_root = os.environ.get("CG_PROJECT_ROOT")
        if "CG_PROJECT_ROOT" in run.secrets:
            os.environ["CG_PROJECT_ROOT"] = run.secrets["CG_PROJECT_ROOT"]
        try:
            result = _expand_context_placeholders(result)
        finally:
            if prev_root is None:
                os.environ.pop("CG_PROJECT_ROOT", None)
            else:
                os.environ["CG_PROJECT_ROOT"] = prev_root
        return result

    def _run_one_with_deps(self, run: RunState, label: str, agent: str, prompt: str) -> None:
        agent_state = run.agents[label]
        if not self._wait_for_deps(run, agent_state):
            agent_state.status = "failed"
            agent_state.exit_code = -1
            agent_state.finished = time.time()
            agent_state.log_lines.append(
                f"[skipped] dependency failed or was cancelled: {agent_state.depends_on}")
            self._emit(run.id, label, {"event": "log", "data": {
                "label": label, "line": agent_state.log_lines[-1]}})
            self._emit(run.id, label, {"event": "status", "data": {
                "label": label, "status": "failed", "exit_code": -1}})
            return
        # Substitute {{depLabel}} placeholders with the dependency's output
        rendered = self._substitute_prompt(run, prompt, agent_state.depends_on)

        # v47.1 W0.2 — if we'll iterate, mask the transient "done" status
        # _run_one will set after round 1 completes. Polling external
        # observers (UI, tests) must see status flip from "running"
        # (round 1) → "running" (round 2) → … → "done" (final round)
        # without ever seeing "done" mid-flight. We do this by lifting
        # the status flip out of round 1 and setting it ourselves only
        # after the iteration loop finishes.
        will_iterate = (agent_state.iterate_with
                         and agent_state.max_rounds > 1
                         and agent_state.iterate_with in run.agents)

        # v55 — auto-retry once on transient failure. Default 1 retry
        # for claude/gemini agents (provider queueing recovery, network
        # blips, OAuth token rotation). Spec steps can override with
        # `auto_retry: 0` (disable) or `auto_retry: N` (more retries).
        # Eligible exit codes: 1 (generic CLI failure), -9 (wall-clock
        # SIGKILL — usually means we underestimated the time budget,
        # second pass might fit). Exit 0 (success) and other codes
        # (auth failure, missing CLI, etc.) are NOT retried.
        spec_step = next(
            (s for s in run.spec if s.get("label") == label), {}
        )
        family_for_retry = ""
        try:
            family_for_retry = AGENT_KINDS.get(agent, {}).get("family", "")
        except Exception:
            pass
        default_retry = 1 if family_for_retry in ("claude", "gemini") else 0
        retry_field = spec_step.get("auto_retry")
        max_retries = int(retry_field) if retry_field is not None else default_retry
        retries_used = 0
        retry_eligible_codes = {1, -9}

        self._run_one(run, label, agent, rendered)
        while (
            agent_state.status == "failed"
            and agent_state.exit_code in retry_eligible_codes
            and retries_used < max_retries
        ):
            retries_used += 1
            msg = (
                f"[auto-retry] attempt {retries_used}/{max_retries} after "
                f"exit_code={agent_state.exit_code} — provider queueing or "
                f"transient CLI failure, retrying with fresh subprocess"
            )
            agent_state.log_lines.append(msg)
            self._emit(run.id, label, {"event": "log", "data": {
                "label": label, "line": msg}})
            self._emit(run.id, label, {"event": "activity", "data": {
                "label": label,
                "text": f"auto-retry · attempt {retries_used}/{max_retries}",
                "source": "retry",
            }})
            # Reset transient state for fresh attempt; keep depends_on,
            # streaming, role, max_rounds, etc.
            agent_state.status = "running"
            agent_state.started = None
            agent_state.finished = None
            agent_state.exit_code = None
            agent_state.first_visible_at = None
            agent_state.last_activity_at = None
            self._run_one(run, label, agent, rendered)
        agent_state.rounds_completed = max(1, agent_state.rounds_completed)

        if (will_iterate and agent_state.status == "done"):
            # Mask round-1 done — flip back to running before polling
            # can sample. Mirror for the partner whose round-1 thread
            # has already returned.
            partner = run.agents.get(agent_state.iterate_with)
            agent_state.status = "running"
            self._emit(run.id, label, {"event": "status", "data": {
                "label": label, "status": "running", "round": 1,
                "iterating": True}})
            if partner is not None:
                partner.status = "running"
                self._emit(run.id, partner.label, {
                    "event": "status", "data": {
                        "label": partner.label, "status": "running",
                        "round": 1, "iterating": True}})
            try:
                self._run_iteration_loop(run, label, agent, prompt)
            finally:
                # Loop body already sets status=done at the end of the
                # last round via _run_one. If it broke early on a
                # subprocess failure, status is failed/cancelled. If
                # status is still "running" for any reason, force done
                # so the run can settle.
                if agent_state.status == "running":
                    agent_state.status = "done"
                    self._emit(run.id, label, {"event": "status", "data": {
                        "label": label, "status": "done"}})
                if partner is not None and partner.status == "running":
                    partner.status = "done"
                    self._emit(run.id, partner.label, {
                        "event": "status", "data": {
                            "label": partner.label, "status": "done"}})

    def _run_iteration_loop(self, run: "RunState", label: str,
                              agent: str, prompt: str) -> None:
        """Repeatedly re-run (partner, self) for max_rounds rounds.

        Round 1 already happened in _run_one_with_deps. This method
        adds rounds 2..N. Each round:
          1. Inject this step's last output into partner's prompt as
             a "## CRITIQUE FROM <self>" appended block.
          2. Re-run partner.
          3. Re-run self (its prompt re-resolves {{partner}} from disk).
          4. Stop early if accept_when matches self's output OR if any
             subprocess fails.

        Notes:
          - The partner's normal thread already finished in round 1.
            We bypass it here and call _run_one directly.
          - We reset rolling state (log_lines, on-disk output) for each
            round so the UI shows a fresh stream per round, but we keep
            the AgentRunState instance (so status/exit_code/etc. flip
            in place — UI sees "designer running again, round 2").
          - This method assumes round 1 has already left both agents in
            status=done.
        """
        import re as _re
        agent_state = run.agents[label]
        partner_label = agent_state.iterate_with
        partner_state = run.agents.get(partner_label)
        if partner_state is None:
            return
        # Find the partner's spec entry for its prompt + agent kind
        partner_step = next(
            (s for s in run.spec if s.get("label") == partner_label), None)
        self_step = next(
            (s for s in run.spec if s.get("label") == label), None)
        if not partner_step or not self_step:
            return

        max_rounds = max(1, int(agent_state.max_rounds or 1))
        accept_re = None
        if agent_state.accept_when:
            try:
                accept_re = _re.compile(agent_state.accept_when, _re.MULTILINE)
            except Exception:
                accept_re = None

        run_dir = RUNS_DIR / run.id
        for round_n in range(2, max_rounds + 1):
            # Check accept signal in current self-output before next round
            if accept_re is not None:
                cur_out = "\n".join(agent_state.log_lines)
                if accept_re.search(cur_out):
                    self._emit(run.id, label, {"event": "log", "data": {
                        "label": label,
                        "line": f"[iterate] accepted in round "
                                f"{round_n - 1} (matched accept_when)",
                    }})
                    break

            # ---- Round N: re-run partner with critique injected --------
            critique = "\n".join(agent_state.log_lines)
            partner_prompt_base = partner_step.get("prompt", "")
            partner_prompt = (
                partner_prompt_base
                + f"\n\n## CRITIQUE FROM {label.upper()} (round {round_n - 1})\n"
                + critique.strip()
            )
            # Reset partner's rolling state for the new round
            partner_state.log_lines = []
            partner_state.stderr_lines = []
            partner_state.exit_code = None
            partner_state.started = None
            partner_state.finished = None
            partner_state.status = "running"
            self._emit(run.id, partner_label, {"event": "status", "data": {
                "label": partner_label, "status": "running",
                "round": round_n,
            }})
            # Delete the prior on-disk output so {{partner}} substitution
            # in self's prompt picks up the new round's content.
            try:
                old = run_dir / f"{partner_label}.out.md"
                if old.exists():
                    old.unlink()
            except Exception:
                pass
            partner_rendered = self._substitute_prompt(
                run, partner_prompt, partner_state.depends_on)
            self._run_one(run, partner_label,
                            partner_state.agent, partner_rendered)
            partner_state.rounds_completed = round_n
            if partner_state.status != "done":
                self._emit(run.id, label, {"event": "log", "data": {
                    "label": label,
                    "line": f"[iterate] partner {partner_label!r} did not "
                            f"finish round {round_n}; stopping loop",
                }})
                break

            # ---- Round N: re-run self with new partner output ----------
            agent_state.log_lines = []
            agent_state.stderr_lines = []
            agent_state.exit_code = None
            agent_state.started = None
            agent_state.finished = None
            agent_state.status = "running"
            self._emit(run.id, label, {"event": "status", "data": {
                "label": label, "status": "running",
                "round": round_n,
            }})
            try:
                old = run_dir / f"{label}.out.md"
                if old.exists():
                    old.unlink()
            except Exception:
                pass
            self_rendered = self._substitute_prompt(
                run, prompt, agent_state.depends_on)
            self._run_one(run, label, agent, self_rendered)
            agent_state.rounds_completed = round_n
            if agent_state.status != "done":
                break

    def _run_one(self, run: RunState, label: str, agent: str, prompt: str) -> None:
        cfg = AGENT_KINDS[agent]
        agent_state = run.agents[label]
        agent_state.status = "running"
        agent_state.started = time.time()
        self._emit(run.id, label, {"event": "status", "data": {
            "label": label, "status": "running"}})

        run_dir = RUNS_DIR / run.id
        run_dir.mkdir(parents=True, exist_ok=True)
        out_path = run_dir / f"{label}.out.md"
        out_fp = open(out_path, "w", encoding="utf-8", buffering=1)

        # HTTP-based provider runner — for OpenRouter, Z.ai, Anthropic
        # API, Google API. Stateless one-shot HTTP call, mirrored into
        # the same log/output channels as the subprocess runner.
        if cfg.get("runner") == "http":
            self._run_one_http(run, label, agent, prompt, cfg, out_fp)
            out_fp.close()
            return

        # Browser runner — Playwright headless Chromium driving a
        # JSON-defined script (see _run_browser_step for action set)
        if cfg.get("runner") == "browser":
            self._run_one_browser(run, label, agent, prompt, cfg, out_fp)
            out_fp.close()
            return

        # Sub-workflow runner — execute a saved workflow as a step,
        # exposing each sub-agent's output as a binding under this
        # parent label (so {{label.subagent}} works downstream).
        if cfg.get("runner") == "subworkflow":
            self._run_one_subworkflow(run, label, agent, prompt, cfg, out_fp)
            out_fp.close()
            return

        # v17 — Browser Pilot: autonomous goal-driven loop.
        # Each iteration: snapshot the page (text + visible elements) →
        # ask an LLM for the next action → execute via _run_browser_step
        # → repeat until the model emits {"action": "done", ...} or we
        # hit max_steps / timeout.
        if cfg.get("runner") == "browser_pilot":
            self._run_one_browser_pilot(run, label, agent, prompt, cfg, out_fp)
            out_fp.close()
            return

        cmd = list(cfg["command"])
        # K3: opt-in token-by-token streaming. We append the CLI's
        # stream-json output flag and parse each line as JSON in the
        # stdout loop below. Best-effort — if the CLI rejects the flag
        # the subprocess will fail, which is the correct signal.
        family = cfg.get("family", "")
        use_streaming = bool(agent_state.streaming) and family in ("claude", "gemini")
        if use_streaming:
            if family == "claude":
                # claude --print --output-format stream-json --verbose
                cmd = cmd + ["--output-format", "stream-json", "--verbose"]
            elif family == "gemini":
                # gemini -p ...   →  gemini --output-format stream-json -p ...
                cmd = cmd + ["--output-format", "stream-json"]

        # v44 — Gemini CLI runs an agentic loop with built-in tools
        # (write_file, run_shell_command, …). When our prompt asks for
        # text output ("write the spec" / "output Markdown"), Gemini
        # often tries to call write_file → tool not available in this
        # workspace → loops forever waiting for delegate-able sub-agent
        # → process hangs at ~1KB output.
        # Mitigation: prepend a global "TEXT ONLY, no tools" preamble
        # to every Gemini prompt. Claude --print is one-shot generative
        # already, so it doesn't need this preamble.
        if family == "gemini":
            preamble = (
                "OUTPUT MODE: TEXT ONLY. Do not call any tools — no "
                "write_file, no read_file, no run_shell_command, no "
                "grep_search, no sub-agent delegation. Respond with "
                "raw text in the format the user asks for. Nothing "
                "else.\n\n---\n\n"
            )
            prompt = preamble + prompt

        if cfg["stdin_prompt"]:
            stdin_input: str | None = prompt
        else:
            cmd = cmd + [prompt]
            stdin_input = None

        env = os.environ.copy()
        env.update(cfg.get("env", {}))
        # Per-run secrets (forwarded from browser Settings tab) take
        # precedence over shell env vars
        env.update(run.secrets)

        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE if stdin_input is not None else subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,  # capture separately, don't pollute log
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                env=env,
            )
        except FileNotFoundError as exc:
            agent_state.status = "failed"
            agent_state.exit_code = 127
            agent_state.finished = time.time()
            agent_state.log_lines.append(f"[error] command not found: {cmd[0]} ({exc})")
            self._emit(run.id, label, {"event": "log", "data": {
                "label": label, "line": agent_state.log_lines[-1]}})
            self._emit(run.id, label, {"event": "status", "data": {
                "label": label, "status": "failed", "exit_code": 127}})
            out_fp.close()
            return

        agent_state.process = proc

        if stdin_input is not None and proc.stdin is not None:
            try:
                proc.stdin.write(stdin_input)
                proc.stdin.close()
            except (BrokenPipeError, OSError):
                pass

        # Stderr reader on its own thread so it can't deadlock the stdout reader.
        # v52 — well-known noise we filter out of activity surfacing.
        # These lines arrive on stderr from CLI bootstrap and don't
        # represent the agent doing anything meaningful.
        STDERR_NOISE = (
            "256-color support not detected",
            "Ripgrep is not available",
            "deprecat",
        )

        def _drain_stderr():
            assert proc.stderr is not None
            for line in proc.stderr:
                clean = line.rstrip("\n")
                agent_state.stderr_lines.append(clean)
                # v52 — surface non-noise stderr as activity so the
                # user sees what the agent is doing (Gemini prints
                # "Calling tool: search_web" etc. to stderr).
                if clean.strip() and not any(n in clean for n in STDERR_NOISE):
                    agent_state.last_activity_at = time.time()
                    self._emit(run.id, label, {"event": "activity", "data": {
                        "label": label,
                        "text": clean[:160],
                        "source": "stderr",
                    }})
        stderr_thread = threading.Thread(target=_drain_stderr, daemon=True)
        stderr_thread.start()

        # v45 — first-token watchdog. If the subprocess accepts the
        # prompt but emits NOTHING for `first_token_timeout` seconds,
        # something is wrong (API queueing, frozen client, network
        # stall) — kill it fast instead of waiting the full 720 s
        # wall-clock timeout.
        # v51.1 — per-step override (`first_token_timeout`).
        # v53 — ADAPTIVE watchdog. The previous design slept naively for
        # `first_token_timeout` seconds and then killed, ignoring whether
        # the subprocess was alive. Reality: provider queueing on Opus
        # peak hours can take 3-8 minutes before any visible content,
        # but the subprocess IS alive — it streams `system/init`,
        # `tool_use`, `thinking` events to stdout the entire time. Those
        # update `agent_state.last_activity_at` even though they don't
        # satisfy `first_token_received` (which requires VISIBLE
        # content). The new watchdog uses both signals:
        #   1. If first-visible-content arrives → cancel (success).
        #   2. If subprocess is heartbeating (last_activity within
        #      HEARTBEAT_GRACE seconds) → extend deadline by another
        #      first_token_timeout chunk and keep watching.
        #   3. If both deadline AND heartbeat-grace are exceeded → kill.
        # Default first_token_timeout bumped 90 → 300s for the common
        # case (Opus producing 30+ KB of code under provider queueing).
        # Hard wall-clock `agent_timeout` (720s default) still bounds
        # total run time, so a truly stuck subprocess won't run forever.
        spec_step = next(
            (s for s in run.spec if s.get("label") == label), {}
        ) if run else {}
        first_token_timeout = float(
            spec_step.get("first_token_timeout")
            or cfg.get("first_token_timeout")
            or os.environ.get("CG_FIRST_TOKEN_TIMEOUT")
            or 300
        )
        # v53 — heartbeat grace window. If the subprocess emits ANY raw
        # stdout (stream-json init / tool_use / heartbeat) within this
        # many seconds, treat it as alive even past the deadline.
        heartbeat_grace = float(
            spec_step.get("heartbeat_grace")
            or cfg.get("heartbeat_grace")
            or os.environ.get("CG_HEARTBEAT_GRACE")
            or 75
        )
        watchdog_tick = 10.0  # how often we wake to re-evaluate
        first_token_received = threading.Event()
        watchdog_canceled = threading.Event()
        proc_started_at = time.time()

        def _first_token_watchdog():
            # v54.1 — first-token watchdog is now DISABLED for ALL
            # agents. Reasoning:
            #
            #   Even in streaming mode, Claude CLI does NOT emit a
            #   `system/init` event the moment the subprocess starts —
            #   it emits init only after the first API response from
            #   Anthropic. Provider queueing on Opus peak hours can
            #   delay that first response 3-5 minutes, during which
            #   the subprocess is alive but last_activity_at stays None.
            #   A heartbeat-based watchdog cannot tell "Opus queueing"
            #   from "subprocess truly frozen" without OS-level signals
            #   (CPU usage, network bytes, etc.) which we don't sample.
            #
            #   The hard wall-clock `agent_timeout` (1800s = 30 min) is
            #   a strictly stronger guarantee: bounds total runtime
            #   regardless of streaming/buffered/queued state. False-
            #   positive kills are gone.
            #
            #   For UI visibility, the parent emits periodic "alive"
            #   events with elapsed seconds so the user sees the agent
            #   is still alive even before any stream event arrives.
            watchdog_canceled.wait()
            return
            deadline = time.time() + first_token_timeout
            extensions = 0
            max_extensions = 8  # cap at ~8x first_token_timeout total adaptive runway
            announced_extension = False
            while True:
                # Wake every WATCHDOG_TICK seconds OR when canceled
                if watchdog_canceled.wait(timeout=watchdog_tick):
                    return
                if first_token_received.is_set():
                    return
                now = time.time()
                last_activity = agent_state.last_activity_at or proc_started_at
                idle = now - last_activity
                if now < deadline:
                    # Still inside initial deadline — keep waiting
                    continue
                # Past the deadline. Is the subprocess heartbeating?
                if idle < heartbeat_grace and extensions < max_extensions:
                    # Subprocess sent SOMETHING (stream-json init, tool
                    # call, etc.) within `heartbeat_grace` seconds — it's
                    # alive, provider is just queueing. Extend deadline.
                    extensions += 1
                    deadline = now + first_token_timeout
                    msg = (
                        f"[watchdog] {now - proc_started_at:.0f}s elapsed, "
                        f"last heartbeat {idle:.0f}s ago — subprocess alive, "
                        f"extending deadline (+{first_token_timeout:.0f}s, "
                        f"ext {extensions}/{max_extensions})"
                    )
                    agent_state.log_lines.append(msg)
                    self._emit(run.id, label, {"event": "log", "data": {
                        "label": label, "line": msg}})
                    if not announced_extension:
                        # Surface as activity so the UI shows it under the panel
                        self._emit(run.id, label, {"event": "activity", "data": {
                            "label": label,
                            "text": f"provider queueing — {now - proc_started_at:.0f}s",
                            "source": "watchdog",
                        }})
                        announced_extension = True
                    continue
                # Past deadline AND no heartbeat AND/OR extensions exhausted → kill
                if extensions >= max_extensions:
                    reason = (
                        f"max watchdog extensions exhausted "
                        f"({max_extensions} × {first_token_timeout:.0f}s)"
                    )
                else:
                    reason = (
                        f"no output in {first_token_timeout:.0f}s and "
                        f"no heartbeat for {idle:.0f}s "
                        f"(subprocess truly frozen — likely network/CLI hang)"
                    )
                agent_state.log_lines.append(
                    f"[error] {reason} — killing subprocess"
                )
                self._emit(run.id, label, {"event": "log", "data": {
                    "label": label, "line": agent_state.log_lines[-1]}})
                try:
                    proc.kill()
                except Exception:
                    pass
                return

        watchdog_thread = threading.Thread(target=_first_token_watchdog, daemon=True)
        watchdog_thread.start()

        # v54.1 — alive ticker. Emits a heartbeat event every 10s so
        # the UI can show "elapsed: 90s" even when the subprocess is
        # silent (provider queueing, big buffered output, etc.). This
        # is the user-visible replacement for the first-token watchdog
        # we just removed. The ticker stops when the subprocess exits.
        alive_ticker_canceled = threading.Event()

        def _alive_ticker():
            tick_interval = 10.0
            while not alive_ticker_canceled.wait(timeout=tick_interval):
                elapsed = time.time() - proc_started_at
                last_act = agent_state.last_activity_at
                if last_act:
                    quiet = time.time() - last_act
                    text = f"alive · elapsed {elapsed:.0f}s · last event {quiet:.0f}s ago"
                else:
                    text = (
                        f"alive · elapsed {elapsed:.0f}s · waiting for first event "
                        f"(provider queueing or buffered CLI)"
                    )
                self._emit(run.id, label, {"event": "alive", "data": {
                    "label": label, "kind": "ticker",
                    "elapsed": elapsed,
                    "text": text,
                }})

        alive_ticker_thread = threading.Thread(target=_alive_ticker, daemon=True)
        alive_ticker_thread.start()

        assert proc.stdout is not None
        for line in proc.stdout:
            # v51 — bump activity timestamp on EVERY raw stdout line so the
            # UI can show "connected, waiting Xs" before any visible
            # content arrives (Sonnet stream-json emits a system/init
            # event first that the parser correctly filters out — the
            # init line is not "first visible token" but it IS a sign of
            # life).
            agent_state.last_activity_at = time.time()

            # _recover_mojibake fixes the Windows-CLI double-encode case
            # (emoji like 🧠 arriving as đź§  through Windows-1250→UTF-8
            # round trips). It's a no-op on clean ASCII so it's free.
            line = _recover_mojibake(line)
            line_clean = line.rstrip("\n")
            visible_added = 0  # bytes of user-visible content this line yielded

            if use_streaming:
                deltas = _parse_stream_json_line(family, line_clean)
                if deltas is None:
                    # Not JSON / unexpected — fall through to raw emit
                    agent_state.log_lines.append(line_clean)
                    out_fp.write(line)
                    self._emit(run.id, label, {"event": "log", "data": {
                        "label": label, "line": line_clean}})
                    visible_added += len(line_clean)
                elif len(deltas) == 0:
                    # System / init / tool_use / hook / result — sign
                    # of life but no visible content. Emit a heartbeat
                    # AND a structured activity description so the UI
                    # can show "currently: calling tool · Read", etc.
                    # CMUX-style continuous activity: every filtered
                    # event becomes a labelled tick in the panel.
                    self._emit(run.id, label, {"event": "alive", "data": {
                        "label": label, "kind": "stream-init"}})
                    desc = _describe_stream_event(family, line_clean)
                    if desc:
                        self._emit(run.id, label, {"event": "activity", "data": {
                            "label": label, "text": desc,
                            "source": "stream-json"}})
                else:
                    # Filter ran — only assistant text deltas reach here
                    for delta in deltas:
                        delta = _recover_mojibake(delta)
                        agent_state.log_lines.append(delta)
                        out_fp.write(delta + "\n")
                        self._emit(run.id, label, {"event": "log", "data": {
                            "label": label, "line": delta,
                            "stream": True}})
                        visible_added += len(delta)
            else:
                agent_state.log_lines.append(line_clean)
                out_fp.write(line)
                self._emit(run.id, label, {"event": "log", "data": {
                    "label": label, "line": line_clean}})
                visible_added += len(line_clean)

            # v51 — watchdog cancels ONLY on first VISIBLE token. Stream-
            # json init events keep the subprocess alive in the dashboard
            # ("connected, 25s") but no longer satisfy the watchdog —
            # which is the bug that left Sonnet 9 min on 0 visible chars.
            if visible_added > 0 and not first_token_received.is_set():
                first_token_received.set()
                watchdog_canceled.set()
                agent_state.first_visible_at = time.time()
                self._emit(run.id, label, {"event": "alive", "data": {
                    "label": label, "kind": "first-visible"}})

        # v44 — hard wall-clock timeout per agent. Without it, an agent
        # CLI that hangs (e.g. Gemini stuck in a missing-tool loop, or
        # any subprocess waiting on stdin) blocks the run forever.
        # v54.1 — bumped 1200 → 1800s (30 min). Wall-clock is now the
        # ONLY safety net (first-token watchdog is fully disabled — see
        # `_first_token_watchdog` above). Realistic ceiling: Opus 1M
        # context generating a full-stack app spec under heavy provider
        # queueing has been measured at 18-22 min. 30 min gives ~30%
        # headroom. Truly frozen subprocesses still get reaped here.
        # Override per-step via env CG_AGENT_TIMEOUT or per-agent in
        # AGENT_KINDS cfg.
        agent_timeout = float(
            cfg.get("timeout")
            or os.environ.get("CG_AGENT_TIMEOUT")
            or 1800
        )
        try:
            proc.wait(timeout=agent_timeout)
        except subprocess.TimeoutExpired:
            alive_ticker_canceled.set()
            watchdog_canceled.set()
            agent_state.log_lines.append(
                f"[error] agent timed out after {agent_timeout:.0f}s — killing subprocess"
            )
            self._emit(run.id, label, {"event": "log", "data": {
                "label": label, "line": agent_state.log_lines[-1]}})
            try:
                proc.kill()
            except Exception:
                pass
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
            agent_state.exit_code = -9
            agent_state.status = "failed"
            agent_state.finished = time.time()
            stderr_thread.join(timeout=2)
            out_fp.close()
            self._emit(run.id, label, {"event": "status", "data": {
                "label": label, "status": "failed", "exit_code": -9}})
            return
        # v54.1 — subprocess exited normally; stop alive ticker & watchdog
        alive_ticker_canceled.set()
        watchdog_canceled.set()
        stderr_thread.join(timeout=2)
        agent_state.exit_code = proc.returncode
        if agent_state.status == "cancelled":
            pass  # leave as cancelled
        else:
            agent_state.status = "done" if proc.returncode == 0 else "failed"
        agent_state.finished = time.time()
        out_fp.close()
        # Persist stderr if any (cosmetic warnings etc.)
        if agent_state.stderr_lines:
            stderr_path = run_dir / f"{label}.err.md"
            stderr_path.write_text("\n".join(agent_state.stderr_lines),
                                    encoding="utf-8")
        self._emit(run.id, label, {"event": "status", "data": {
            "label": label, "status": agent_state.status,
            "exit_code": agent_state.exit_code}})

    def _run_one_http(self, run: "RunState", label: str, agent: str,
                       prompt: str, cfg: dict[str, Any], out_fp: Any) -> None:
        """HTTP runner for paid-API models (OpenRouter / Z.ai / Anthropic
        API / Google AI Studio). One non-streaming POST per call; the
        full response text is appended to the agent's log buffer in one
        chunk (we could stream later, but most providers' SSE shapes
        differ enough that batch-then-emit is simpler and reliable)."""
        import urllib.request
        import urllib.error

        agent_state = run.agents[label]
        http_cfg = cfg["http"]
        # Per-run secrets (browser Settings) take precedence over env vars
        api_key = run.secrets.get(http_cfg["api_key_env"]) \
            or os.environ.get(http_cfg["api_key_env"])
        if not api_key:
            agent_state.status = "failed"
            agent_state.exit_code = 401
            agent_state.finished = time.time()
            agent_state.log_lines.append(
                f"[error] env var {http_cfg['api_key_env']!r} is empty"
            )
            self._emit(run.id, label, {"event": "log", "data": {
                "label": label, "line": agent_state.log_lines[-1]}})
            self._emit(run.id, label, {"event": "status", "data": {
                "label": label, "status": "failed", "exit_code": 401}})
            return

        # Build provider-specific request
        if http_cfg.get("anthropic_native"):
            url = http_cfg["endpoint"]
            payload = {
                "model": http_cfg["model"],
                "max_tokens": 4096,
                "messages": [{"role": "user", "content": prompt}],
            }
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
        elif http_cfg.get("google_native"):
            url = f"{http_cfg['endpoint']}?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
            }
            headers = {"content-type": "application/json"}
        else:
            # OpenAI-compatible (OpenRouter, Z.ai, etc.)
            url = http_cfg["endpoint"]
            payload = {
                "model": http_cfg["model"],
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            }
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            for k, v in (http_cfg.get("headers") or {}).items():
                headers[k] = v

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                exit_code = 0 if resp.status < 300 else resp.status
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            exit_code = exc.code
        except Exception as exc:
            agent_state.status = "failed"
            agent_state.exit_code = 1
            agent_state.finished = time.time()
            agent_state.log_lines.append(f"[network error] {exc}")
            self._emit(run.id, label, {"event": "log", "data": {
                "label": label, "line": agent_state.log_lines[-1]}})
            self._emit(run.id, label, {"event": "status", "data": {
                "label": label, "status": "failed", "exit_code": 1}})
            return

        text = _extract_response_text(raw, http_cfg)
        for line in text.splitlines() or [""]:
            agent_state.log_lines.append(line)
            out_fp.write(line + "\n")
            self._emit(run.id, label, {"event": "log", "data": {
                "label": label, "line": line}})

        agent_state.exit_code = exit_code
        agent_state.status = "done" if exit_code == 0 else "failed"
        agent_state.finished = time.time()
        self._emit(run.id, label, {"event": "status", "data": {
            "label": label, "status": agent_state.status,
            "exit_code": exit_code}})

    def _run_one_subworkflow(self, run: "RunState", label: str, agent: str,
                                prompt: str, cfg: dict[str, Any],
                                out_fp: Any) -> None:
        """Sub-workflow runner — load a saved workflow JSON, execute its
        spec inside the parent run as a child run, then merge the
        child's per-agent outputs into parent's bindings[label] so
        downstream parent agents can {{label.subagent}} them.

        Prompt JSON shape::

            {"workflow": "name-or-path", "variables": {"K": "v"}}
        """
        agent_state = run.agents[label]

        def emit_line(s: str) -> None:
            agent_state.log_lines.append(s)
            out_fp.write(s + "\n")
            self._emit(run.id, label, {"event": "log",
                "data": {"label": label, "line": s}})

        try:
            spec_obj = json.loads(prompt)
        except json.JSONDecodeError as exc:
            agent_state.status = "failed"
            agent_state.exit_code = 2
            agent_state.finished = time.time()
            emit_line(f"[subworkflow: prompt is not valid JSON — {exc}]")
            self._emit(run.id, label, {"event": "status",
                "data": {"label": label, "status": "failed",
                         "exit_code": 2}})
            return

        wf_name = (spec_obj or {}).get("workflow")
        if not wf_name:
            agent_state.status = "failed"
            agent_state.exit_code = 2
            agent_state.finished = time.time()
            emit_line("[subworkflow: missing 'workflow' field]")
            self._emit(run.id, label, {"event": "status",
                "data": {"label": label, "status": "failed", "exit_code": 2}})
            return

        # Load the named workflow from disk
        wf_path = WORKFLOWS_DIR / f"{_safe_workflow_name(wf_name)}.json"
        if not wf_path.exists():
            agent_state.status = "failed"
            agent_state.exit_code = 1
            agent_state.finished = time.time()
            emit_line(f"[subworkflow: workflow {wf_name!r} not found at {wf_path}]")
            self._emit(run.id, label, {"event": "status",
                "data": {"label": label, "status": "failed", "exit_code": 1}})
            return

        try:
            wf_data = json.loads(wf_path.read_text(encoding="utf-8"))
        except Exception as exc:
            agent_state.status = "failed"
            agent_state.exit_code = 1
            agent_state.finished = time.time()
            emit_line(f"[subworkflow: failed to parse workflow JSON — {exc}]")
            self._emit(run.id, label, {"event": "status",
                "data": {"label": label, "status": "failed", "exit_code": 1}})
            return

        sub_spec = wf_data.get("spec") or []
        if not sub_spec:
            agent_state.status = "failed"
            agent_state.exit_code = 1
            agent_state.finished = time.time()
            emit_line(f"[subworkflow: workflow {wf_name!r} has empty spec]")
            self._emit(run.id, label, {"event": "status",
                "data": {"label": label, "status": "failed", "exit_code": 1}})
            return

        # Merge variables: workflow defaults < parent run vars < step overlay
        sub_vars: dict[str, str] = {}
        sub_vars.update(wf_data.get("variables", {}) or {})
        sub_vars.update(run.variables or {})
        sub_vars.update((spec_obj.get("variables", {}) or {}))

        # Spawn the child run synchronously here — block until done
        emit_line(f"[subworkflow] launching {wf_name!r} with "
                    f"{len(sub_spec)} agents, vars={list(sub_vars.keys())}")
        child = self.start_run(
            f"sub: {wf_data.get('title', wf_name)}",
            sub_spec,
            secrets=dict(run.secrets or {}),  # forward parent's secrets
            variables=sub_vars,
        )
        emit_line(f"[subworkflow] child run id: {child.id}")

        # Block on child completion (poll, since start_run is fire-and-forget)
        deadline = time.time() + int(spec_obj.get("timeout_seconds", 1800))
        while time.time() < deadline:
            if all(a.status in {"done", "failed", "cancelled"}
                    for a in child.agents.values()):
                break
            time.sleep(0.5)
        else:
            agent_state.status = "failed"
            agent_state.exit_code = 124
            agent_state.finished = time.time()
            emit_line("[subworkflow: timed out waiting for child]")
            self._emit(run.id, label, {"event": "status",
                "data": {"label": label, "status": "failed",
                         "exit_code": 124}})
            return

        # Collect child outputs into bindings[label]
        bindings: dict[str, Any] = {}
        any_failed = False
        for sub_label, sub_agent in child.agents.items():
            output_text = "\n".join(sub_agent.log_lines)
            bindings[sub_label] = output_text
            status_marker = "✓" if sub_agent.status == "done" else "✗"
            emit_line(f"  {status_marker} {sub_label} ({sub_agent.agent}): "
                        f"{sub_agent.status}, exit={sub_agent.exit_code}, "
                        f"chars={len(output_text)}")
            if sub_agent.status != "done":
                any_failed = True

        # Also expose child run id for traceability
        bindings["_child_run_id"] = child.id
        run.bindings = getattr(run, "bindings", {})
        run.bindings[label] = bindings
        emit_line("\n=== child bindings ===")
        emit_line(json.dumps({k: (v if not isinstance(v, str) or len(v) < 200
                                     else v[:200] + "…")
                               for k, v in bindings.items()},
                              indent=2, ensure_ascii=False, default=str))

        agent_state.exit_code = 0 if not any_failed else 1
        agent_state.status = "done" if not any_failed else "failed"
        agent_state.finished = time.time()
        self._emit(run.id, label, {"event": "status",
            "data": {"label": label, "status": agent_state.status,
                     "exit_code": agent_state.exit_code}})

    def _run_one_browser(self, run: "RunState", label: str, agent: str,
                          prompt: str, cfg: dict[str, Any], out_fp: Any) -> None:
        """Browser agent runner — parses prompt as JSON ``browser_steps``
        list, executes via Playwright, and stores per-step bindings into
        ``agent.log_lines`` so the {{label}} substitution exposes the
        full bindings dict to downstream agents.

        Bindings are also written to ``run.bindings[label]`` so a custom
        ``{{label.field}}`` placeholder can pull individual values
        without round-tripping through JSON parse in the prompt.
        """
        agent_state = run.agents[label]
        run_dir = RUNS_DIR / run.id

        # Parse prompt as JSON; if it's a list, treat as steps directly,
        # else expect {steps: [...], session: {...}}
        try:
            parsed = json.loads(prompt)
        except json.JSONDecodeError as exc:
            agent_state.status = "failed"
            agent_state.exit_code = 2
            agent_state.finished = time.time()
            msg = f"[browser: prompt is not valid JSON — {exc}]"
            agent_state.log_lines.append(msg)
            self._emit(run.id, label, {"event": "log",
                "data": {"label": label, "line": msg}})
            self._emit(run.id, label, {"event": "status",
                "data": {"label": label, "status": "failed",
                         "exit_code": 2}})
            return

        if isinstance(parsed, list):
            steps = parsed
            session = {}
        elif isinstance(parsed, dict):
            steps = parsed.get("steps") or parsed.get("browser_steps") or []
            session = parsed.get("session") or parsed.get("browser_session") or {}
        else:
            agent_state.status = "failed"
            agent_state.log_lines.append("[browser: spec must be array of steps OR {steps, session}]")
            self._emit(run.id, label, {"event": "status",
                "data": {"label": label, "status": "failed", "exit_code": 2}})
            return

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            agent_state.status = "failed"
            agent_state.exit_code = 127
            agent_state.finished = time.time()
            msg = ("[browser: playwright not installed. "
                    "pip install playwright && playwright install chromium]")
            agent_state.log_lines.append(msg)
            self._emit(run.id, label, {"event": "log",
                "data": {"label": label, "line": msg}})
            self._emit(run.id, label, {"event": "status",
                "data": {"label": label, "status": "failed",
                         "exit_code": 127}})
            return

        bindings: dict[str, Any] = {}

        def emit_line(s: str) -> None:
            agent_state.log_lines.append(s)
            out_fp.write(s + "\n")
            self._emit(run.id, label, {"event": "log",
                "data": {"label": label, "line": s}})

        # Per-run auth state directory
        auth_dir = run_dir / "auth"

        try:
            with sync_playwright() as p:
                headless = bool(session.get("headless", True))
                browser = p.chromium.launch(headless=headless)
                ctx_kwargs: dict[str, Any] = {}
                if session.get("viewport"):
                    vw, vh = session["viewport"]
                    ctx_kwargs["viewport"] = {"width": int(vw), "height": int(vh)}
                if session.get("user_agent"):
                    ctx_kwargs["user_agent"] = session["user_agent"]
                if session.get("locale"):
                    ctx_kwargs["locale"] = session["locale"]
                if session.get("timezone"):
                    ctx_kwargs["timezone_id"] = session["timezone"]
                # Load auth state if requested + file exists
                load_auth = session.get("load_auth_state")
                if load_auth:
                    auth_path = (NOTES_DIR.parent / "browser_auth"
                                   / f"{_safe_workflow_name(load_auth)}.json")
                    if auth_path.exists():
                        ctx_kwargs["storage_state"] = str(auth_path)
                        emit_line(f"[browser] loaded auth state: {load_auth}")

                ctx = browser.new_context(**ctx_kwargs)
                page = ctx.new_page()
                default_timeout = int(session.get("default_timeout_ms", 30000))
                page.set_default_timeout(default_timeout)
                emit_line(f"[browser] starting {len(steps)} steps "
                            f"(headless={headless})")

                for i, step in enumerate(steps):
                    if not isinstance(step, dict) or "action" not in step:
                        emit_line(f"[step {i+1}] SKIP — invalid step")
                        continue
                    action = step["action"]
                    bind_as = step.get("as")  # name to store output under
                    try:
                        result = _run_browser_step(page, ctx, browser, step,
                                                     run, label, bindings)
                        # Format result for log
                        if isinstance(result, str):
                            preview = result[:200].replace("\n", " ")
                            emit_line(f"[step {i+1}] {action}: {preview}")
                        elif isinstance(result, list):
                            emit_line(f"[step {i+1}] {action}: list({len(result)})")
                        elif result is None:
                            emit_line(f"[step {i+1}] {action}: ok")
                        else:
                            emit_line(f"[step {i+1}] {action}: {result}")
                        if bind_as:
                            bindings[bind_as] = result
                    except Exception as exc:
                        emit_line(f"[step {i+1}] {action}: ERROR {exc}")
                        if step.get("optional"):
                            continue
                        raise

                # Save auth state if requested
                save_auth = session.get("save_auth_state")
                if save_auth:
                    auth_dir = NOTES_DIR.parent / "browser_auth"
                    auth_dir.mkdir(parents=True, exist_ok=True)
                    auth_path = auth_dir / f"{_safe_workflow_name(save_auth)}.json"
                    ctx.storage_state(path=str(auth_path))
                    emit_line(f"[browser] saved auth state: {save_auth}")

                browser.close()

            # Persist bindings to run + emit final summary
            run.bindings = getattr(run, "bindings", {})
            run.bindings[label] = bindings
            agent_state.exit_code = 0
            agent_state.status = "done"
            agent_state.finished = time.time()
            # Final binding dump in JSON for {{label}} substitution
            emit_line("\n=== bindings ===")
            emit_line(json.dumps(bindings, indent=2, ensure_ascii=False, default=str))
            self._emit(run.id, label, {"event": "status",
                "data": {"label": label, "status": "done", "exit_code": 0}})
        except Exception as exc:
            agent_state.exit_code = 1
            agent_state.status = "failed"
            agent_state.finished = time.time()
            emit_line(f"[browser] error: {exc}")
            self._emit(run.id, label, {"event": "status",
                "data": {"label": label, "status": "failed", "exit_code": 1}})

    def _run_one_browser_pilot(self, run: "RunState", label: str, agent: str,
                                  prompt: str, cfg: dict[str, Any], out_fp: Any) -> None:
        """v17 — Autonomous Perplexity-Computer-style loop.

        Each iteration:
          1. Capture page state (visible text + interactive elements
             with stable selectors + screenshot path).
          2. Render history + current state + goal into a compact
             prompt and pipe it through the chosen LLM (default
             ``claude-sonnet-4-6``) with a JSON-only response contract.
          3. Parse the action and execute via _run_browser_step.
          4. Stop on ``done`` action, max_steps, or timeout.

        Prompt accepted formats:
          * Plain English string  → goal, defaults applied
          * JSON dict             → ``{goal, model?, max_steps?,
                                        start_url?, headless?}``
        """
        agent_state = run.agents[label]
        run_dir = RUNS_DIR / run.id
        bindings: dict[str, Any] = {"steps": [], "answer": None}

        def emit_line(s: str) -> None:
            agent_state.log_lines.append(s)
            out_fp.write(s + "\n"); out_fp.flush()
            self._emit(run.id, label, {"event": "log",
                "data": {"label": label, "line": s}})

        # Parse prompt — accept plain string OR dict
        cfg_obj: dict[str, Any] = {}
        prompt_stripped = (prompt or "").strip()
        if prompt_stripped.startswith("{"):
            try:
                cfg_obj = json.loads(prompt_stripped)
            except Exception as exc:
                emit_line(f"[pilot] failed to parse JSON config — {exc}; "
                          f"treating as plain goal")
        if not cfg_obj:
            cfg_obj = {"goal": prompt_stripped}

        goal = (cfg_obj.get("goal") or "").strip()
        if not goal:
            agent_state.status = "failed"; agent_state.exit_code = 2
            agent_state.finished = time.time()
            emit_line("[pilot] empty goal")
            self._emit(run.id, label, {"event": "status",
                "data": {"label": label, "status": "failed", "exit_code": 2}})
            return

        model_id = cfg_obj.get("model", "claude-sonnet-4-6")
        max_steps = int(cfg_obj.get("max_steps", 12))
        start_url = cfg_obj.get("start_url") or "about:blank"
        headless = bool(cfg_obj.get("headless", True))

        emit_line(f"[pilot] goal: {goal}")
        emit_line(f"[pilot] model={model_id} max_steps={max_steps} "
                  f"start_url={start_url} headless={headless}")

        if model_id not in AGENT_KINDS:
            agent_state.status = "failed"; agent_state.exit_code = 2
            agent_state.finished = time.time()
            emit_line(f"[pilot] unknown model {model_id!r}")
            self._emit(run.id, label, {"event": "status",
                "data": {"label": label, "status": "failed", "exit_code": 2}})
            return

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            agent_state.status = "failed"; agent_state.exit_code = 1
            agent_state.finished = time.time()
            emit_line("[pilot] playwright not installed — pip install playwright "
                      "&& playwright install chromium")
            self._emit(run.id, label, {"event": "status",
                "data": {"label": label, "status": "failed", "exit_code": 1}})
            return

        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

        # System prompt for the LLM. We constrain the response to a
        # single JSON object so parsing is deterministic.
        system = (
            "You are a browser-pilot agent. Your job is to reach the user's "
            "GOAL by emitting one browser action per turn.\n\n"
            "Allowed actions:\n"
            "  goto      {url}\n"
            "  click     {selector}\n"
            "  fill      {selector, value}\n"
            "  scroll    {to: 'top'|'bottom'|<int px>}\n"
            "  wait      {time_ms}\n"
            "  extract   {selector, attr?}   — returns text and shows it to you next turn\n"
            "  done      {answer}            — finishes the task with the final answer\n\n"
            "Respond with EXACTLY one JSON object: {\"reasoning\": \"...\", "
            "\"action\": \"<name>\", ...args}. Nothing else, no markdown fences. "
            "Prefer stable CSS selectors. If you cannot make progress, "
            "emit done with answer explaining why."
        )

        history: list[dict[str, Any]] = []

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=headless)
                ctx_kwargs: dict[str, Any] = {
                    "viewport": {"width": 1280, "height": 800},
                }
                ctx = browser.new_context(**ctx_kwargs)
                page = ctx.new_page()
                if start_url and start_url != "about:blank":
                    try:
                        page.goto(start_url, wait_until="domcontentloaded", timeout=30000)
                        try:
                            page.wait_for_load_state("networkidle", timeout=5000)
                        except Exception:
                            pass
                    except Exception as exc:
                        emit_line(f"[pilot] start_url failed: {exc}")

                for step_idx in range(1, max_steps + 1):
                    if agent_state.status == "cancelled":
                        emit_line("[pilot] cancelled by user")
                        break

                    # 1) Snapshot current page state
                    snapshot = self._pilot_capture_state(page, label, step_idx)
                    snap_path = run_dir / f"{label}.step-{step_idx}.snap.json"
                    snap_path.write_text(json.dumps(snapshot, indent=2,
                                                     ensure_ascii=False, default=str),
                                          encoding="utf-8")
                    emit_line(f"[pilot] step {step_idx}: at {snapshot['url']!r} "
                              f"(title={snapshot['title']!r}, screenshot={snapshot['screenshot']})")

                    # 2) Build LLM prompt
                    history_text = "\n".join(
                        f"  {i+1}. {h['action']}({json.dumps({k:v for k,v in h.items() if k not in ('action','reasoning','result')}, ensure_ascii=False)}) "
                        f"→ {str(h.get('result',''))[:120]}"
                        for i, h in enumerate(history[-6:])  # last 6 to keep ctx small
                    ) or "  (none)"
                    elements_text = "\n".join(
                        f"  - {e['tag']} {e['selector']}: {e['text'][:60]!r}"
                        for e in snapshot["elements"][:30]
                    )
                    page_text_excerpt = snapshot["page_text"][:1500]
                    user_msg = (
                        f"GOAL: {goal}\n\n"
                        f"STEP {step_idx}/{max_steps}\n"
                        f"URL: {snapshot['url']}\n"
                        f"TITLE: {snapshot['title']}\n\n"
                        f"VISIBLE INTERACTIVE ELEMENTS (top 30):\n{elements_text}\n\n"
                        f"PAGE TEXT (first 1500 chars):\n{page_text_excerpt}\n\n"
                        f"PREVIOUS ACTIONS (last 6):\n{history_text}\n\n"
                        f"What is your next action? Respond with EXACTLY one JSON object."
                    )
                    full_prompt = f"{system}\n\n---\n\n{user_msg}"

                    # 3) Call the LLM via subprocess
                    action = self._pilot_ask_llm(model_id, full_prompt, label, step_idx)
                    if action is None:
                        emit_line(f"[pilot] step {step_idx}: model returned no parseable JSON, stopping")
                        bindings["error"] = "model returned non-JSON"
                        break
                    emit_line(f"[pilot] step {step_idx}: → {action.get('action')} "
                              f"({(action.get('reasoning') or '')[:120]})")

                    # 4) Execute
                    if action.get("action") == "done":
                        bindings["answer"] = action.get("answer")
                        bindings["steps"].append({**action, "step": step_idx})
                        emit_line(f"[pilot] DONE — answer: {action.get('answer')}")
                        break
                    try:
                        result = _run_browser_step(page, ctx, browser,
                                                    action, run, label, {})
                        history.append({**action, "result": result})
                        bindings["steps"].append({**action, "step": step_idx,
                                                    "result": str(result)[:200]})
                    except Exception as exc:
                        history.append({**action, "result": f"ERROR: {exc}"})
                        bindings["steps"].append({**action, "step": step_idx,
                                                    "error": str(exc)})
                        emit_line(f"[pilot] step {step_idx}: action raised — {exc}")

                else:
                    emit_line(f"[pilot] hit max_steps={max_steps} without 'done'")
                    bindings["error"] = "max_steps reached"

                browser.close()

            run.bindings = getattr(run, "bindings", {})
            run.bindings[label] = bindings
            agent_state.exit_code = 0
            agent_state.status = "done"
            agent_state.finished = time.time()
            emit_line("\n=== bindings ===")
            emit_line(json.dumps(bindings, indent=2, ensure_ascii=False, default=str))
            self._emit(run.id, label, {"event": "status",
                "data": {"label": label, "status": "done", "exit_code": 0}})
        except Exception as exc:
            agent_state.exit_code = 1
            agent_state.status = "failed"
            agent_state.finished = time.time()
            emit_line(f"[pilot] error: {exc}")
            self._emit(run.id, label, {"event": "status",
                "data": {"label": label, "status": "failed", "exit_code": 1}})

    def _pilot_capture_state(self, page: Any, label: str,
                                step_idx: int) -> dict[str, Any]:
        """Snapshot the page: text, interactive elements, screenshot path."""
        import hashlib
        try:
            url = page.url or ""
        except Exception:
            url = ""
        try:
            title = page.title()
        except Exception:
            title = ""
        try:
            page_text = (page.inner_text("body") or "")[:6000]
        except Exception:
            page_text = ""

        # Visible interactive elements with selectors. We pick a small,
        # stable subset and synthesize a CSS selector for each.
        try:
            elements = page.evaluate(r"""() => {
              const out = [];
              const candidates = document.querySelectorAll(
                'a[href], button, input, textarea, select, [role="button"], [role="link"]');
              for (const el of candidates) {
                const r = el.getBoundingClientRect();
                if (r.width === 0 || r.height === 0) continue;
                if (r.bottom < 0 || r.top > window.innerHeight + 200) continue;
                let sel = el.tagName.toLowerCase();
                if (el.id) { sel = '#' + CSS.escape(el.id); }
                else if (el.getAttribute('name')) {
                  sel += `[name="${el.getAttribute('name')}"]`;
                }
                else if (el.getAttribute('aria-label')) {
                  sel += `[aria-label="${el.getAttribute('aria-label')}"]`;
                }
                else if (el.className && typeof el.className === 'string') {
                  const cls = el.className.split(/\s+/).filter(c =>
                    c && !/[\:\\\\\\/]/.test(c)).slice(0, 2);
                  if (cls.length) sel += '.' + cls.join('.');
                }
                let text = (el.innerText || el.value || el.placeholder ||
                              el.getAttribute('aria-label') || '').trim();
                out.push({ tag: el.tagName.toLowerCase(), selector: sel, text });
                if (out.length >= 60) break;
              }
              return out;
            }""")
        except Exception:
            elements = []

        # Screenshot
        digest = hashlib.sha1((url + str(step_idx)).encode("utf-8")).hexdigest()[:10]
        ss_path = SCREENSHOTS_DIR / f"pilot-{label}-step-{step_idx}-{digest}.png"
        try:
            page.screenshot(path=str(ss_path), full_page=False)
            ss_rel = f"outputs/screenshots/{ss_path.name}"
        except Exception:
            ss_rel = ""

        return {
            "url": url, "title": title,
            "page_text": page_text,
            "elements": elements or [],
            "screenshot": ss_rel,
        }

    def _pilot_ask_llm(self, model_id: str, full_prompt: str,
                         label: str, step_idx: int) -> dict[str, Any] | None:
        """Pipe a prompt through an AGENT_KINDS subprocess command and
        parse its stdout as JSON. Returns None on parse failure."""
        cfg = AGENT_KINDS.get(model_id)
        if not cfg or "command" not in cfg:
            return None
        cmd = list(cfg["command"])
        if cfg.get("stdin_prompt"):
            stdin_input: str | None = full_prompt
        else:
            cmd = cmd + [full_prompt]
            stdin_input = None
        env = os.environ.copy()
        env.update(cfg.get("env", {}))
        try:
            proc = subprocess.run(
                cmd,
                input=stdin_input,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                timeout=180,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            return {"action": "done", "answer": f"LLM call failed: {exc}",
                     "reasoning": "subprocess error"}
        raw = (proc.stdout or "").strip()
        # Best-effort JSON extraction — model may wrap it in fences
        if "```" in raw:
            # Strip code fence
            try:
                inner = raw.split("```", 2)[1]
                if inner.startswith(("json", "JSON")):
                    inner = inner.split("\n", 1)[1] if "\n" in inner else inner[4:]
                raw = inner.strip()
            except Exception:
                pass
        # Find first { and matching } for safety
        try:
            start = raw.index("{")
            depth = 0; end = -1
            for i in range(start, len(raw)):
                if raw[i] == "{": depth += 1
                elif raw[i] == "}":
                    depth -= 1
                    if depth == 0: end = i + 1; break
            if end > start:
                return json.loads(raw[start:end])
        except Exception:
            pass
        return None

    def cancel_run(self, run_id: str) -> bool:
        """Kill any in-flight subprocesses for this run."""
        run = self.runs.get(run_id)
        if not run:
            return False
        for agent_state in run.agents.values():
            if agent_state.status in {"running", "waiting", "queued"}:
                agent_state.status = "cancelled"
                if agent_state.process is not None:
                    try:
                        agent_state.process.kill()
                    except Exception:
                        pass
                self._emit(run.id, agent_state.label, {"event": "status", "data": {
                    "label": agent_state.label, "status": "cancelled"}})
        return True

    def _compute_downstream(self, run: "RunState", label: str) -> list[str]:
        """BFS over the depends_on graph (reversed) to find every agent
        whose result would be invalidated by re-running ``label``.

        Returns the labels in spec order (preserving the original execution
        order), with ``label`` itself first.
        """
        if label not in run.agents:
            return []
        # Map: dependent → set of labels it depends on
        deps_of: dict[str, set[str]] = {
            lbl: set(ag.depends_on) for lbl, ag in run.agents.items()
        }
        affected: set[str] = {label}
        changed = True
        while changed:
            changed = False
            for lbl, deps in deps_of.items():
                if lbl in affected:
                    continue
                if deps & affected:
                    affected.add(lbl)
                    changed = True
        # Preserve spec order
        ordered: list[str] = []
        seen: set[str] = set()
        for item in run.spec:
            lbl = item.get("label")
            if lbl in affected and lbl not in seen:
                ordered.append(lbl)
                seen.add(lbl)
        return ordered

    def replay_from(self, run_id: str, label: str) -> dict[str, Any]:
        """Reset ``label`` + every downstream dependent and re-spawn them.

        Prior steps' outputs are preserved on disk so ``{{label}}``
        substitution still works for upstream references. Kills any
        subprocess that's currently running for the affected steps.

        Returns ``{"replayed": [labels...], "preserved": [labels...]}``.
        """
        run = self.runs.get(run_id)
        if not run:
            raise HTTPException(404, f"run {run_id!r} not found")
        if label not in run.agents:
            raise HTTPException(404,
                f"agent {label!r} not in run {run_id!r}")

        downstream = self._compute_downstream(run, label)
        if not downstream:
            return {"replayed": [], "preserved": list(run.agents.keys())}

        run_dir = RUNS_DIR / run.id
        for lbl in downstream:
            ag = run.agents[lbl]
            # Kill running subprocess if any
            if ag.process is not None:
                try:
                    ag.process.kill()
                except Exception:
                    pass
                ag.process = None
            # Reset state — keep depends_on; flip status back per spec
            initial_status = "queued" if not ag.depends_on else "waiting"
            ag.status = initial_status
            ag.exit_code = None
            ag.started = None
            ag.finished = None
            ag.log_lines = []
            ag.stderr_lines = []
            # Delete prior on-disk output for this step (so {{lbl}}
            # references see the fresh content the re-run produces, not
            # the stale failed output).
            try:
                out_path = run_dir / f"{lbl}.out.md"
                if out_path.exists():
                    out_path.unlink()
            except Exception:
                pass
            self._emit(run.id, lbl, {"event": "status", "data": {
                "label": lbl, "status": initial_status,
                "replayed": True}})

        # Mark run as not-finished so /api/runs/<id> reflects in-flight state
        run.finished = False
        self._persist_index()

        # Re-spawn threads for the affected labels using the original spec
        downstream_set = set(downstream)
        for item in run.spec:
            lbl = item.get("label")
            if lbl in downstream_set:
                t = threading.Thread(
                    target=self._run_one_with_deps,
                    args=(run, lbl, item.get("agent"), item.get("prompt", "")),
                    daemon=True,
                )
                t.start()
        # Watcher to flip run.finished again when the replayed batch settles
        _wt = threading.Thread(target=self._watch_run, args=(run,), daemon=True)
        run._watcher_threads.append(_wt)
        _wt.start()

        preserved = [lbl for lbl in run.agents.keys()
                     if lbl not in downstream_set]
        return {"replayed": downstream, "preserved": preserved}

    def _watch_run(self, run: RunState) -> None:
        # Module-overridable poll interval. Production uses 500ms;
        # tests can lower it (e.g. 50ms) to make teardown joins fast.
        poll_s = float(globals().get("WATCH_RUN_POLL_S", 0.5))
        while True:
            time.sleep(poll_s)
            if all(a.status in {"done", "failed", "cancelled"}
                    for a in run.agents.values()):
                break
        run.finished = True
        self._persist_index()
        self._emit_run(run.id, {"event": "run-finished", "data": {"id": run.id}})
        # Fire run-finished webhook notifications (Discord/Slack/ntfy)
        try:
            _send_notification(run)
        except Exception:
            pass

    # SSE consumer registration
    def subscribe(self, run_id: str, label: str) -> asyncio.Queue:
        key = (run_id, label)
        q: asyncio.Queue = asyncio.Queue()
        self.streams[key] = q
        return q

    def unsubscribe(self, run_id: str, label: str) -> None:
        self.streams.pop((run_id, label), None)

    def _persist_index(self) -> None:
        index = [
            {
                "id": r.id, "title": r.title, "created": r.created,
                "finished": r.finished,
                "spec": r.spec,  # full spec — needed to rehydrate after restart
                "agents": [
                    {"label": a.label, "agent": a.agent,
                     "depends_on": a.depends_on,
                     "status": a.status, "exit_code": a.exit_code,
                     "started": a.started, "finished": a.finished,
                     "log_chars": sum(len(l) for l in a.log_lines),
                     "streaming": a.streaming}
                    for a in r.agents.values()
                ],
            }
            for r in sorted(self.runs.values(), key=lambda x: x.created, reverse=True)
        ]
        try:
            INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
            INDEX_PATH.write_text(
                json.dumps(index, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    def hydrate_from_disk(self) -> int:
        """Reload finished runs from INDEX_PATH on startup so the
        dashboard's history survives a restart. Best-effort — broken
        entries are skipped, never raised. Returns hydrated count."""
        if not INDEX_PATH.exists():
            return 0
        try:
            data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        except Exception:
            return 0
        if not isinstance(data, list):
            return 0
        loaded = 0
        for entry in data:
            try:
                if not isinstance(entry, dict):
                    continue
                rid = entry.get("id")
                if not rid or rid in self.runs:
                    continue
                run = RunState(
                    id=rid,
                    title=entry.get("title") or rid,
                    created=float(entry.get("created") or time.time()),
                    spec=entry.get("spec") or [],
                )
                run.finished = bool(entry.get("finished"))
                for a in entry.get("agents") or []:
                    label = a.get("label") or "agent"
                    agent_state = AgentRunState(
                        label=label,
                        agent=a.get("agent") or "claude-sonnet-4-6",
                        depends_on=list(a.get("depends_on") or []),
                        status=a.get("status") or "done",
                        started=a.get("started"),
                        finished=a.get("finished"),
                        exit_code=a.get("exit_code"),
                        streaming=bool(a.get("streaming", False)),
                        role=str(a.get("role", "") or ""),
                    )
                    # Refill log_lines from on-disk capture file
                    out_path = RUNS_DIR / rid / f"{label}.out.md"
                    if out_path.exists():
                        try:
                            agent_state.log_lines = out_path.read_text(
                                encoding="utf-8").splitlines()
                        except Exception:
                            pass
                    err_path = RUNS_DIR / rid / f"{label}.err.md"
                    if err_path.exists():
                        try:
                            agent_state.stderr_lines = err_path.read_text(
                                encoding="utf-8").splitlines()
                        except Exception:
                            pass
                    run.agents[label] = agent_state
                self.runs[rid] = run
                loaded += 1
            except Exception:
                continue
        return loaded


# ---------------------------------------------------------------------------
# Presets — bundled workflows
# ---------------------------------------------------------------------------


# v50 W5 — Mission Library categories. Five buckets the Quick Start
# advanced block surfaces as tiles. Each preset maps to ONE category via
# PRESET_CATEGORIES below; presets without a mapping fall through to
# "other" and only show in the flat dropdown.
MISSION_CATEGORIES: list[dict[str, str]] = [
    {"id": "app",       "icon": "🚀",
     "name": "App builder",
     "description": "Idea → working code. SaaS, tools, scripts."},
    {"id": "audit",     "icon": "🔍",
     "name": "Audit & research",
     "description": "Crawl, analyze, score. SEO, competitors, code review."},
    {"id": "content",   "icon": "🎨",
     "name": "Design & content factory",
     "description": "Blog, social, design, pitch deck, email, translation."},
    {"id": "automation","icon": "🤖",
     "name": "Automation hub",
     "description": "Pipelines, fan-outs, model comparisons."},
    {"id": "browser",   "icon": "🌐",
     "name": "Browser ops",
     "description": "Headless web — scrape, fill, screenshot, pilot."},
]

PRESET_CATEGORIES: dict[str, str] = {
    # App builder
    "idea-to-app":               "app",
    "file-refactor":             "app",
    "github-readme-from-code":   "app",
    "bug-investigation":         "app",
    "code-review":               "app",
    "code-pr-review":            "app",
    "github-pr-review":          "app",
    "git-pr-review":             "app",
    # Audit & research
    "seo-audit":                 "audit",
    "competitor-analysis":       "audit",
    "research-deep-dive":        "audit",
    # Design & content factory
    "idea-to-content-plan":      "content",
    "idea-to-pitch-deck":        "content",
    "design-brief-to-concepts":  "content",
    "blog-article-full":         "content",
    "blog-draft":                "content",
    "social-content-fanout":     "content",
    "email-drip-5":              "content",
    "product-description-3":     "content",
    "translate-cz-en":           "content",
    "meeting-to-actions":        "content",
    # Automation hub
    "compare":                   "automation",
    "pipeline":                  "automation",
    "pipeline-var":              "automation",
    "fanout":                    "automation",
    # Browser ops
    "browser-scrape-and-summarize": "browser",
    "browser-visual-regression":    "browser",
    "browser-form-test":            "browser",
    "browser-pilot-search":         "browser",
    "browser-pilot-summarize":      "browser",
}

PRESETS: list[dict[str, Any]] = [
    # ============================================================
    # v41 — FLAGSHIP "from idea" presets
    # The CG vision: type one idea, get a finished thing.
    # These three cover the highest-volume "I have an idea" use cases:
    # build a product, plan a content series, pitch a startup.
    # ============================================================
    {
        "id": "idea-to-app",
        "title": "💡 Idea → finished app (one prompt, multi-vendor team)",
        "description": "Type your idea once in ${IDEA}. A mixed team of Claude "
                       "AND Gemini agents collaborates: Opus directs + writes "
                       "the architecture and code (1M context for big specs), "
                       "Gemini Pro brings independent design + testing + market "
                       "perspective, Sonnet runs the code review, Gemini Flash "
                       "writes the docs. End result: a complete project you can "
                       "paste into a repo and run, built by AIs from two vendors "
                       "checking each other's work.",
        "variables": {
            "IDEA": "An app for solo freelancers to track billable hours and "
                    "auto-generate invoices in PDF. Mobile-first PWA. Stripe "
                    "for payments. Dark mode default. CZ + EN locales.",
        },
        "spec": [
            {
                "agent": "claude-opus-4-7", "label": "director", "role": "Visionary",
                "prompt": "You are the project director. Turn this idea into a "
                          "precise build spec a team can execute today. Output "
                          "Markdown with these sections, in order:\n\n"
                          "## Product\n2 sentences explaining what it does and for whom.\n\n"
                          "## Target user persona\nName + 1 paragraph.\n\n"
                          "## MVP scope\n5-7 must-have features as bullets. NO nice-to-haves.\n\n"
                          "## Tech stack\nConcrete picks (e.g. 'Next.js 15 App Router + Tailwind 4 + tRPC + Drizzle + Postgres + Stripe + Resend'). One-line rationale per choice.\n\n"
                          "## File tree\nEvery file the project needs, as a tree.\n\n"
                          "## Data model\nTables + columns + relations. SQL-DDL ready.\n\n"
                          "## API contract\nEvery endpoint: METHOD /path · request shape · response shape. JSON.\n\n"
                          "## Acceptance criteria\n5-10 testable bullets.\n\n"
                          "## Risks + mitigations\n3 bullets.\n\n"
                          "Be opinionated. No 'depends on requirements' hedging.\n\n"
                          "## Idea\n${IDEA}",
            },
            {
                "agent": "gemini-pro", "label": "designer", "role": "Designer",
                "depends_on": ["director"],
                "prompt": "OUTPUT MODE: TEXT ONLY. Do not call any tools. Do not "
                          "invoke write_file, read_file, run_shell_command, "
                          "or any sub-agent. Do not delegate. Respond with "
                          "raw text in the requested format — nothing else.\n\n"
                          "You are the lead designer (different vendor than the "
                          "director, so bring fresh visual judgment). From the spec, output:\n\n"
                          "## Design tokens\nCSS custom properties block — colors (hex), type scale, spacing scale, radii, shadows.\n\n"
                          "## Component inventory\n10-15 components needed (Button, Input, DataTable, …) with one-line spec each.\n\n"
                          "## Three key screens\nFor each: name, purpose, layout described in 6-10 bullets, then a self-contained inline SVG (≥800×500) showing the actual layout. NOT generic placeholders — real labels, real button text, real numbers.\n\n"
                          "## Mood\n3 sentences on the overall vibe.\n\n"
                          "## Spec\n{{director}}",
            },
            {
                "agent": "claude-opus-4-7", "label": "architect", "role": "Architect",
                "depends_on": ["director"],
                "prompt": "You are the architect. From the spec, output the "
                          "COMPLETE project scaffold:\n\n"
                          "## Package manifest\nFull `package.json` (or `pyproject.toml`) with concrete pinned versions.\n\n"
                          "## Folder structure\nEvery file with one-line purpose.\n\n"
                          "## Config files\n`.env.example`, `tsconfig.json`, `tailwind.config.ts`, `next.config.ts`, `drizzle.config.ts` etc. — full content for each.\n\n"
                          "## Setup commands\nFrom `git clone` to `localhost:3000` working — copy-pasteable shell block.\n\n"
                          "## Spec\n{{director}}",
            },
            {
                "agent": "claude-opus-4-7", "label": "implementation", "role": "Engineer",
                "depends_on": ["director", "architect", "designer"],
                "prompt": "You are the implementer. Write the FULL working "
                          "implementation. Output EVERY file as a fenced code "
                          "block whose first line is a comment with the file "
                          "path: `// path/to/file.ts` (or `# path/to/file.py`).\n\n"
                          "Cover, in order: data layer (schema + migrations), "
                          "API endpoints (every one in the contract), business "
                          "logic, auth (basic email + password OR OAuth — pick), "
                          "frontend pages (every screen the designer drew), "
                          "components (everything in the inventory), error "
                          "boundaries, loading states. Use the design tokens "
                          "from {{designer}} verbatim. Wire Stripe / Resend / "
                          "etc. with code that actually compiles, not stubs.\n\n"
                          "NO 'TODO' or 'implement later' comments. NO "
                          "placeholder strings. If you can't fit something, "
                          "state which file is partial at the bottom and why.\n\n"
                          "## Spec\n{{director}}\n\n## Scaffold\n{{architect}}\n\n"
                          "## Design tokens + components\n{{designer}}",
            },
            {
                # v45 — tests step now runs from SPEC ONLY, not full
                # implementation. Previous run had Sonnet hang at 0 B
                # for 6+ min when fed {{director}} (12.5 KB) +
                # {{implementation}} (117 KB) = 130 KB prompt — likely
                # API soft-limit / queueing. Spec alone has everything
                # tests need: API contract, acceptance criteria, file
                # tree. Reviewer step still reads both, so the loop
                # closes there.
                "agent": "claude-sonnet-4-6", "label": "tests", "role": "QA",
                "depends_on": ["director"],
                "prompt": "You are the test author. Write thorough tests for "
                          "the project described by the spec below. Cover:\n"
                          "- Happy path for every endpoint in the API contract\n"
                          "- Each acceptance-criterion bullet\n"
                          "- Edge cases (null/empty/zero/negative/overflow)\n"
                          "- Auth + authz boundaries\n"
                          "- Error responses\n\n"
                          "Match the stack from the spec (pytest for Python, "
                          "Vitest for TS, etc.). Output every test file as a "
                          "fenced code block with `# path/to/file.py` "
                          "(or `// path/to/file.ts`) as the first line. NO "
                          "explanation between blocks.\n\n"
                          "## Spec\n{{director}}",
            },
            {
                "agent": "claude-sonnet-4-6", "label": "reviewer", "role": "Critic",
                "depends_on": ["implementation", "tests"],
                "prompt": "You are the senior code reviewer. Find: bugs, "
                          "security issues (injection / authz / secrets / SSRF / "
                          "CSRF), missing acceptance criteria, missing error "
                          "handling, perf concerns (N+1, blocking I/O), "
                          "deployment risks. Markdown bullet list with "
                          "severity tag (CRIT / HIGH / MED / LOW), exact "
                          "file:line, and a one-sentence fix per finding.\n\n"
                          "End with: `Ship readiness: <0-10>` and one sentence "
                          "rationale. Be honest — if not ready, say so.\n\n"
                          "## Implementation\n{{implementation}}\n\n## Tests\n{{tests}}",
            },
            {
                # v45 — moved Gemini Flash → Sonnet 4.6. Gemini Flash
                # has its own internal _recoverFromLoop detector that
                # self-aborted on the previous run after generating ~6 KB
                # of README, even with our "TEXT ONLY no tools" preamble
                # (the loop detector watches the model's own output, not
                # tool calls). Sonnet 4.6 has no such detector, similar
                # speed for short Markdown, perfectly reliable.
                "agent": "claude-sonnet-4-6", "label": "readme-deploy", "role": "Operator",
                "depends_on": ["director", "architect", "implementation"],
                "prompt": "Write the project's complete README + deploy guide:\n\n"
                          "## README.md\n- Title + tagline (≤12 words)\n- Hero "
                          "screenshot placeholder\n- Feature list (from MVP "
                          "scope)\n- Quickstart (copy-pasteable)\n- Project "
                          "structure section\n- Env vars table\n- "
                          "Contributing\n- License (MIT)\n\n"
                          "## DEPLOY.md\nPick ONE cloud (Vercel + Neon for JS, "
                          "Fly.io + Postgres for Python, etc.) and give "
                          "step-by-step deploy instructions a beginner can "
                          "follow. Include cost estimate.\n\n"
                          "## Spec\n{{director}}\n\n## Scaffold\n{{architect}}",
            },
        ],
    },
    {
        "id": "idea-to-content-plan",
        "title": "💡 Idea → 90-day content plan (calendar + 3 sample pieces)",
        "description": "Type one ${TOPIC}. Strategist analyzes audience + "
                       "competitors. Editor builds 90-day content calendar "
                       "across blog / social / email. Three writers produce "
                       "a sample piece each (blog, X thread, email). Critic "
                       "scores the plan.",
        "variables": {
            "TOPIC": "Practical multi-agent AI for small dev teams that already "
                     "pay for Claude + Gemini and want to stop renting Make / "
                     "Zapier monthly.",
            "AUDIENCE": "Senior engineers + tech-savvy founders, 25-45, "
                        "subscribe to The Pragmatic Engineer / Latent Space.",
        },
        "spec": [
            {
                "agent": "claude-opus-4-7", "label": "strategy", "role": "Strategist",
                "prompt": "You are head of content. From the topic + audience, "
                          "output:\n\n"
                          "## Positioning\n2 sentences — what we own vs the rest.\n\n"
                          "## 5 content pillars\nName + 1-line intent each.\n\n"
                          "## 10 evergreen post hooks\nNumbered, each headline-ready (≤90 chars).\n\n"
                          "## Channel mix\n%-split across blog, X, LinkedIn, newsletter, video. Justify.\n\n"
                          "## North-star metric\nOne KPI + 90-day target.\n\n"
                          "## Topic\n${TOPIC}\n\n## Audience\n${AUDIENCE}",
            },
            {
                "agent": "claude-opus-4-7", "label": "calendar", "role": "Architect",
                "depends_on": ["strategy"],
                "prompt": "From the strategy, build a 90-day calendar. Output "
                          "Markdown table: `| Day | Channel | Format | Title | Pillar | KPI focus |`. "
                          "Aim for 3-4 posts/week, mixed channels, ladder up "
                          "to a flagship piece in week 8 and a recap in week "
                          "12.\n\n## Strategy\n{{strategy}}",
            },
            {
                "agent": "claude-sonnet-4-6", "label": "sample-blog", "role": "Writer",
                "depends_on": ["strategy", "calendar"],
                "prompt": "Pick the strongest blog headline from the calendar "
                          "and write the full 1500-word post. Tone: confident, "
                          "no fluff, one strong opinion. Add SEO title + meta "
                          "description.\n\n## Strategy\n{{strategy}}\n\n## Calendar\n{{calendar}}",
            },
            {
                "agent": "claude-sonnet-4-6", "label": "sample-thread", "role": "Writer",
                "depends_on": ["strategy", "calendar"],
                "prompt": "Pick the strongest X (Twitter) hook from the "
                          "calendar and write the full 8-tweet thread. Each "
                          "tweet ≤280 chars. End with a CTA.\n\n## Strategy\n{{strategy}}\n\n"
                          "## Calendar\n{{calendar}}",
            },
            {
                "agent": "gemini-pro", "label": "sample-email", "role": "Writer",
                "depends_on": ["strategy", "calendar"],
                "prompt": "Pick the strongest newsletter idea from the "
                          "calendar and write the full email (subject + "
                          "preheader + 350-450 words body + single CTA). "
                          "Conversational tone.\n\n## Strategy\n{{strategy}}\n\n"
                          "## Calendar\n{{calendar}}",
            },
            {
                "agent": "claude-sonnet-4-6", "label": "critic", "role": "Critic",
                "depends_on": ["strategy", "calendar", "sample-blog",
                               "sample-thread", "sample-email"],
                "prompt": "Critique the whole plan. Score 0-10 on: "
                          "Audience fit, Differentiation, Cadence realism, "
                          "Content quality, KPI achievability. Be honest. End "
                          "with 'Top fix: …' (one sentence).\n\n"
                          "## Strategy\n{{strategy}}\n\n## Calendar\n{{calendar}}\n\n"
                          "## Blog\n{{sample-blog}}\n\n## Thread\n{{sample-thread}}\n\n"
                          "## Email\n{{sample-email}}",
            },
        ],
    },
    {
        "id": "idea-to-pitch-deck",
        "title": "💡 Idea → pitch deck (10 slides + investor Q&A)",
        "description": "Type one ${IDEA}. Strategist sharpens the angle. "
                       "Three parallel agents draft Problem, Solution, "
                       "Market+Competition. Implementer writes 10 slides as "
                       "Markdown ready to paste into Slides / Pitch / "
                       "Beautiful.ai. Reviewer simulates 12 investor questions "
                       "with answers.",
        "variables": {
            "IDEA": "AI-native bookkeeping for solo freelancers — auto-imports "
                    "invoices from email, categorizes, files VAT in CZ + DE in "
                    "one click. Subscription €19/mo.",
            "STAGE": "Pre-seed, raising €500k for 12 months runway",
        },
        "spec": [
            {
                "agent": "claude-opus-4-7", "label": "angle", "role": "Strategist",
                "prompt": "You are a pitch coach. From the idea + stage, "
                          "sharpen the angle:\n\n"
                          "## One-line pitch\n≤14 words. Memorable.\n\n"
                          "## Why now\n3 bullets — what changed in the world that makes this possible/urgent.\n\n"
                          "## Why us\n3 bullets — unfair advantages.\n\n"
                          "## Founder narrative\n2 sentences — the personal story that makes investors believe.\n\n"
                          "## Idea\n${IDEA}\n\n## Stage\n${STAGE}",
            },
            {
                "agent": "claude-opus-4-7", "label": "problem", "role": "Researcher",
                "depends_on": ["angle"],
                "prompt": "Write the Problem section: 1 customer story (named "
                          "persona, real day-in-the-life), 3 quantified pain "
                          "points (numbers), and how today's solutions fall "
                          "short. ≤200 words.\n\n## Angle\n{{angle}}",
            },
            {
                "agent": "claude-opus-4-7", "label": "solution", "role": "Architect",
                "depends_on": ["angle"],
                "prompt": "Write the Solution section: 3-step user journey "
                          "(before/during/after), unique mechanism (the 'how'), "
                          "and one demo screenshot description (label-only "
                          "wireframe). ≤200 words.\n\n## Angle\n{{angle}}",
            },
            {
                "agent": "gemini-pro", "label": "market", "role": "Researcher",
                "depends_on": ["angle"],
                "prompt": "Write the Market + Competition section: TAM/SAM/SOM "
                          "with cited sources or 'estimate based on …', "
                          "competitor matrix (3-4 competitors × 4 attributes), "
                          "and your differentiator in one sentence. ≤200 words.\n\n"
                          "## Angle\n{{angle}}",
            },
            {
                "agent": "claude-opus-4-7", "label": "deck", "role": "Engineer",
                "depends_on": ["angle", "problem", "solution", "market"],
                "prompt": "Assemble the 10-slide deck as Markdown. Each slide "
                          "is a `## Slide N: Title` heading + 5-8 bullet "
                          "points. Order: 1 Cover · 2 Problem · 3 Solution · "
                          "4 Why now · 5 Market · 6 Product (screenshot stub) · "
                          "7 Business model · 8 Traction · 9 Team · 10 Ask. "
                          "End with one-line speaker note per slide.\n\n"
                          "## Angle\n{{angle}}\n\n## Problem\n{{problem}}\n\n"
                          "## Solution\n{{solution}}\n\n## Market\n{{market}}",
            },
            {
                "agent": "claude-sonnet-4-6", "label": "qa", "role": "Critic",
                "depends_on": ["deck"],
                "prompt": "Simulate 12 of the toughest questions a "
                          "${STAGE} investor will ask after seeing this deck. "
                          "For each: the question + your 3-sentence answer + "
                          "what NOT to say. Format as numbered list.\n\n"
                          "## Deck\n{{deck}}",
            },
        ],
    },
    {
        "id": "compare",
        "title": "Two-model compare (Sonnet × Gemini Pro)",
        "description": "Same task to Claude Sonnet 4.6 and Gemini Pro in parallel — diff the two answers.",
        "spec": [
            {
                "agent": "claude-sonnet-4-6", "label": "claude",
                "prompt": "Write a Python function `is_prime(n: int) -> bool` "
                          "that handles n<2 correctly. Output ONLY a fenced ```python code block."
            },
            {
                "agent": "gemini-pro", "label": "gemini",
                "prompt": "DO NOT ask questions. DO NOT propose a plan. "
                          "Write a Python function `is_prime(n: int) -> bool` "
                          "that handles n<2 correctly. "
                          "Output ONLY a fenced ```python code block. Nothing else."
            },
        ],
    },
    {
        "id": "pipeline",
        "title": "Design → Implement → Critique (Gemini Pro → Opus 4.7 → Sonnet 4.6)",
        "description": "Real sequential pipeline. Edit the 'design' agent's "
                        "prompt — replace the [PASTE YOUR TASK HERE] block with "
                        "your brief (one paragraph or a bullet list). The other "
                        "two agents auto-pick it up via {{design}} / {{implement}}. "
                        "Critique uses Sonnet (Pro subscription) to avoid Gemini "
                        "preview-model 429 capacity errors.",
        "spec": [
            {
                "agent": "gemini-pro", "label": "design",
                "prompt": "DO NOT ask questions. DO NOT propose a plan. Write a precise "
                          "Markdown spec for the task below. Cover: Signature / API, "
                          "Inputs, Outputs, Edge cases, and 2-3 concrete example "
                          "inputs+expected outputs. Output Markdown only.\n\n"
                          "## Task\n\n"
                          "[PASTE YOUR TASK HERE — e.g. \"Build a Python function "
                          "`is_prime(n: int) -> bool` that handles n<2.\" or "
                          "\"Design a React component for a sortable, filterable "
                          "data table with pagination.\" Replace this whole "
                          "bracketed block.]"
            },
            {
                "agent": "claude-opus-4-7", "label": "implement",
                "depends_on": ["design"],
                "prompt": "Implement the following spec exactly. Output ONLY a fenced "
                          "code block in the appropriate language, nothing before "
                          "or after.\n\n"
                          "# Spec\n\n{{design}}"
            },
            {
                "agent": "claude-sonnet-4-6", "label": "critique",
                "depends_on": ["design", "implement"],
                "prompt": "Critically review this implementation against its spec. List bugs, "
                          "missing edge cases, and concrete improvements as a Markdown bullet "
                          "list. Be terse. If the implementation is correct, say so in one line.\n\n"
                          "## Spec\n{{design}}\n\n## Implementation\n{{implement}}"
            },
        ],
    },
    {
        "id": "pipeline-var",
        "title": "Design → Implement → Critique (uses ${TASK} variable)",
        "description": "Same pipeline as 'Design → Implement → Critique', but "
                        "the brief lives in a single ${TASK} variable. Set it in "
                        "Settings → Variables (or workflow variables) once and "
                        "all 3 agents read it — no prompt editing needed.",
        "variables": {
            "TASK": "Build a Python function `is_prime(n: int) -> bool` that "
                    "handles n<2 correctly. Include an explanation in comments."
        },
        "spec": [
            {
                "agent": "gemini-pro", "label": "design",
                "prompt": "DO NOT ask questions. DO NOT propose a plan. Write a precise "
                          "Markdown spec for the task below. Cover: Signature / API, "
                          "Inputs, Outputs, Edge cases, and 2-3 concrete example "
                          "inputs+expected outputs. Output Markdown only.\n\n"
                          "## Task\n\n${TASK}"
            },
            {
                "agent": "claude-opus-4-7", "label": "implement",
                "depends_on": ["design"],
                "prompt": "Implement this spec exactly. Output ONLY a fenced code "
                          "block in the appropriate language, nothing else.\n\n"
                          "# Original task\n\n${TASK}\n\n# Spec\n\n{{design}}"
            },
            {
                "agent": "claude-sonnet-4-6", "label": "critique",
                "depends_on": ["design", "implement"],
                "prompt": "Critically review this implementation. List bugs, missing "
                          "edge cases, and concrete improvements as a Markdown "
                          "bullet list. Be terse.\n\n"
                          "## Original task\n${TASK}\n\n"
                          "## Spec\n{{design}}\n\n"
                          "## Implementation\n{{implement}}"
            },
        ],
    },
    {
        "id": "fanout",
        "title": "4-agent fan-out (creative diversity)",
        "description": "Same prompt to 4 different models in parallel — pick the best output.",
        "spec": [
            {"agent": "claude-sonnet-4-6", "label": "sonnet",
             "prompt": "Write a haiku about debugging. ASCII only."},
            {"agent": "claude-opus-4-6", "label": "opus-4-6",
             "prompt": "Write a haiku about debugging. ASCII only."},
            {"agent": "gemini-pro", "label": "gemini-pro",
             "prompt": "DO NOT add any prose. Output ONLY a haiku about debugging. "
                       "ASCII only. 3 lines."},
            {"agent": "gemini-flash", "label": "gemini-flash",
             "prompt": "DO NOT add any prose. Output ONLY a haiku about debugging. "
                       "ASCII only. 3 lines."},
        ],
    },
    {
        "id": "git-pr-review",
        "title": "Git diff review (auto-fetched current diff)",
        "description": "Reviews the CURRENT working-tree git diff with three "
                        "models in parallel. Uses {{git:diff}} placeholder so "
                        "you don't paste anything — just save your file and Run.",
        "spec": [
            {
                "agent": "claude-sonnet-4-6", "label": "style",
                "prompt": "Review this diff for style, readability, obvious "
                          "bugs, and missing tests. Output a Markdown bullet "
                          "list, max 10 items. If the diff is trivial say so "
                          "in one line.\n\n```diff\n{{git:diff}}\n```"
            },
            {
                "agent": "claude-opus-4-7", "label": "architecture",
                "prompt": "Review this diff at the architecture / design level "
                          "(coupling, abstractions, future maintainability). "
                          "Concrete concerns + suggested fixes as a Markdown "
                          "bullet list.\n\n```diff\n{{git:diff}}\n```"
            },
            {
                "agent": "gemini-pro", "label": "edge-cases",
                "prompt": "Adversarially review this diff. List 5+ specific "
                          "edge cases the author probably did not test. Be "
                          "concrete — exact inputs and likely-actual vs "
                          "expected behavior.\n\n```diff\n{{git:diff}}\n```"
            },
        ],
    },
    {
        "id": "file-refactor",
        "title": "File refactor (Sonnet drafts → Opus 4.7 reviews)",
        "description": "Sonnet 4.6 drafts a refactor of an explicit file path "
                        "(edit src/xyz.py inline in the prompt before Run), "
                        "then Opus 4.7 reviews the diff. Demonstrates {{file:}} "
                        "placeholder + sequential pipeline.",
        "spec": [
            {
                "agent": "claude-sonnet-4-6", "label": "draft",
                "prompt": "Refactor the following Python file. Make it cleaner "
                          "and add type hints where missing. Output ONLY a "
                          "fenced ```python code block with the FULL refactored "
                          "file content.\n\n--- src/cg.py ---\n{{file:src/cg.py}}"
            },
            {
                "agent": "claude-opus-4-7", "label": "review",
                "depends_on": ["draft"],
                "prompt": "Review this refactor against the original. Did it "
                          "preserve behaviour? Did it introduce regressions? "
                          "Markdown bullet list, terse.\n\n## Original\n"
                          "```python\n{{file:src/cg.py}}\n```\n\n## Refactor\n"
                          "{{draft}}"
            },
        ],
    },
    {
        "id": "browser-scrape-and-summarize",
        "title": "Browser scrape + AI summary (any URL)",
        "description": "Headless Chromium navigates to ${TARGET_URL}, extracts "
                        "the main heading + body + screenshot via the browser "
                        "agent's action API, then Claude summarizes the page "
                        "into 5 bullets. Demonstrates browser→LLM hand-off with "
                        "{{label.field}} binding access.",
        "spec": [
            {
                "agent": "browser",
                "label": "fetch",
                "prompt": "{\n  \"steps\": [\n"
                          "    {\"action\": \"goto\", \"url\": \"${TARGET_URL}\"},\n"
                          "    {\"action\": \"title\", \"as\": \"page_title\"},\n"
                          "    {\"action\": \"extract\", \"selector\": \"h1\", \"as\": \"heading\", \"optional\": true},\n"
                          "    {\"action\": \"extract\", \"selector\": \"body\", \"as\": \"body_text\"},\n"
                          "    {\"action\": \"extract_all\", \"selector\": \"a\", \"attr\": \"href\", \"as\": \"links\"},\n"
                          "    {\"action\": \"screenshot\", \"full_page\": true, \"as\": \"shot\"}\n"
                          "  ]\n}"
            },
            {
                "agent": "claude-sonnet-4-6",
                "label": "summary",
                "depends_on": ["fetch"],
                "prompt": "Summarize this page in exactly 5 bullets, then "
                          "list 3 quotable lines verbatim.\n\n"
                          "Title: {{fetch.page_title}}\n"
                          "Heading: {{fetch.heading}}\n"
                          "Screenshot: {{fetch.shot}}\n"
                          "Outbound link count: {{fetch.links}}\n\n"
                          "## Body\n\n{{fetch.body_text}}"
            },
        ],
    },
    {
        "id": "browser-visual-regression",
        "title": "Visual regression (live URL × 2 screenshots → AI diff)",
        "description": "Snapshots ${TARGET_URL} at two viewports (desktop + "
                        "mobile), Sonnet diffs the visible content, Gemini "
                        "spots layout regressions. Useful before/after a "
                        "deploy: change ${TARGET_URL} between runs.",
        "spec": [
            {
                "agent": "browser",
                "label": "shoot-desktop",
                "prompt": "{\n  \"session\": {\"viewport\": [1440, 900]},\n"
                          "  \"steps\": [\n"
                          "    {\"action\": \"goto\", \"url\": \"${TARGET_URL}\"},\n"
                          "    {\"action\": \"wait_for\", \"time_ms\": 1500},\n"
                          "    {\"action\": \"screenshot\", \"full_page\": true, \"as\": \"shot\"},\n"
                          "    {\"action\": \"extract\", \"selector\": \"body\", \"as\": \"body\"}\n"
                          "  ]\n}"
            },
            {
                "agent": "browser",
                "label": "shoot-mobile",
                "prompt": "{\n  \"session\": {\"viewport\": [390, 844], \"user_agent\": \"Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15\"},\n"
                          "  \"steps\": [\n"
                          "    {\"action\": \"goto\", \"url\": \"${TARGET_URL}\"},\n"
                          "    {\"action\": \"wait_for\", \"time_ms\": 1500},\n"
                          "    {\"action\": \"screenshot\", \"full_page\": true, \"as\": \"shot\"},\n"
                          "    {\"action\": \"extract\", \"selector\": \"body\", \"as\": \"body\"}\n"
                          "  ]\n}"
            },
            {
                "agent": "claude-sonnet-4-6",
                "label": "compare",
                "depends_on": ["shoot-desktop", "shoot-mobile"],
                "prompt": "Compare desktop vs mobile rendering of "
                          "${TARGET_URL}.\n\n## Desktop body\n"
                          "{{shoot-desktop.body}}\n\n## Mobile body\n"
                          "{{shoot-mobile.body}}\n\nList layout/content "
                          "differences as Markdown bullets. Are any "
                          "elements missing on mobile? Truncated? "
                          "Reordered awkwardly?\n\nScreenshots: "
                          "{{shoot-desktop.shot}} vs {{shoot-mobile.shot}}"
            },
        ],
    },
    {
        "id": "browser-form-test",
        "title": "Browser e2e form smoke test (fill, submit, verify)",
        "description": "Navigates to ${FORM_URL}, fills the input named "
                        "${INPUT_NAME} with ${INPUT_VALUE}, clicks submit, "
                        "captures the response page. Sonnet verifies the "
                        "expected confirmation text appeared. Edit the JSON "
                        "to match your form's actual selectors.",
        "spec": [
            {
                "agent": "browser",
                "label": "submit",
                "prompt": "{\n  \"steps\": [\n"
                          "    {\"action\": \"goto\", \"url\": \"${FORM_URL}\"},\n"
                          "    {\"action\": \"wait_for\", \"selector\": \"form\"},\n"
                          "    {\"action\": \"fill\", \"selector\": \"input[name='${INPUT_NAME}']\", \"value\": \"${INPUT_VALUE}\"},\n"
                          "    {\"action\": \"screenshot\", \"as\": \"before\"},\n"
                          "    {\"action\": \"click\", \"selector\": \"button[type='submit'], input[type='submit']\"},\n"
                          "    {\"action\": \"wait_for\", \"time_ms\": 2000},\n"
                          "    {\"action\": \"url\", \"as\": \"final_url\"},\n"
                          "    {\"action\": \"extract\", \"selector\": \"body\", \"as\": \"final_body\"},\n"
                          "    {\"action\": \"screenshot\", \"as\": \"after\"}\n"
                          "  ]\n}"
            },
            {
                "agent": "claude-sonnet-4-6",
                "label": "verify",
                "depends_on": ["submit"],
                "prompt": "I submitted a form. Verify whether the response "
                          "indicates success.\n\n"
                          "Final URL: {{submit.final_url}}\n"
                          "Before screenshot: {{submit.before}}\n"
                          "After screenshot: {{submit.after}}\n\n"
                          "## Final page body\n{{submit.final_body}}\n\n"
                          "Did the submit succeed? Quote the line in the "
                          "body that proves it (or the line that suggests "
                          "failure). Be terse."
            },
        ],
    },
    {
        "id": "seo-audit",
        "title": "SEO audit (live page → 3 angles → action plan)",
        "description": "Headless Chromium fetches the live URL (rendered JS), "
                        "three models analyze different angles, and Opus synthesizes "
                        "a prioritized action plan. Set ${TARGET_URL} in Settings.",
        "spec": [
            {
                "agent": "claude-sonnet-4-6", "label": "technical",
                "prompt": "SEO technical audit of ${TARGET_URL}.\n\n"
                          "## Page meta (machine-extracted)\n\n"
                          "{{web-meta:${TARGET_URL}}}\n\n"
                          "## Rendered body (innerText)\n\n"
                          "{{web:${TARGET_URL}}}\n\n"
                          "Identify: missing/weak meta tags, title issues, "
                          "OG/Twitter card problems, heading hierarchy, "
                          "thin content. Markdown bullet list, max 12 items, "
                          "ordered by impact."
            },
            {
                "agent": "gemini-pro", "label": "content",
                "prompt": "Content quality audit of ${TARGET_URL}.\n\n"
                          "## Rendered text\n\n{{web:${TARGET_URL}}}\n\n"
                          "Critique: keyword targeting, intent match, "
                          "E-E-A-T signals, readability, depth vs surface, "
                          "thin/duplicate sections. Concrete suggestions."
            },
            {
                "agent": "claude-opus-4-7", "label": "competitive",
                "prompt": "Identify the top 3 competitors for ${TARGET_URL} "
                          "and what they do better, based on the page content.\n\n"
                          "{{web:${TARGET_URL}}}\n\n"
                          "List competitors with one URL each + concrete deltas."
            },
            {
                "agent": "claude-opus-4-7", "label": "plan",
                "depends_on": ["technical", "content", "competitive"],
                "prompt": "Synthesize a 30-day SEO action plan from these "
                          "three audits. Group by week, prioritize by "
                          "impact/effort. Markdown.\n\n"
                          "## Technical\n{{technical}}\n\n"
                          "## Content\n{{content}}\n\n"
                          "## Competitive\n{{competitive}}"
            },
        ],
    },
    {
        "id": "competitor-analysis",
        "title": "Competitor analysis (live scrape → comparison table)",
        "description": "Pulls live content from your URL + competitor URLs, "
                        "Sonnet builds a feature comparison table, Opus suggests "
                        "positioning angles. Set ${OUR_URL} and ${COMP_URL} "
                        "(comma-separated for multiple competitors).",
        "spec": [
            {
                "agent": "claude-sonnet-4-6", "label": "compare",
                "prompt": "Build a feature comparison table from these pages:\n\n"
                          "## Us — ${OUR_URL}\n\n{{web:${OUR_URL}}}\n\n"
                          "## Competitor — ${COMP_URL}\n\n{{web:${COMP_URL}}}\n\n"
                          "Output a Markdown table: Feature | Us | Them. "
                          "Include only features where they differ meaningfully."
            },
            {
                "agent": "claude-opus-4-7", "label": "positioning",
                "depends_on": ["compare"],
                "prompt": "Based on this comparison, suggest 3 specific "
                          "positioning angles we could lean into where we "
                          "have an advantage, and 3 areas where we're behind "
                          "and should improve. Concrete + actionable.\n\n"
                          "{{compare}}"
            },
        ],
    },
    {
        "id": "github-pr-review",
        "title": "GitHub PR review (current diff → 3 models → save as note)",
        "description": "Reviews the current working-tree diff with three models and "
                        "saves the consolidated report as a CG note. Variables: "
                        "${PR_NUMBER}, ${REPO_URL}. Set them in Settings or POST a "
                        "trigger payload.",
        "spec": [
            {
                "agent": "claude-sonnet-4-6", "label": "style",
                "prompt": "Review the code style + readability + obvious bugs of "
                          "this PR. Output a Markdown bullet list, max 10 items.\n\n"
                          "## PR ${PR_NUMBER} on ${REPO_URL}\n\n"
                          "```diff\n{{git:diff}}\n```"
            },
            {
                "agent": "claude-opus-4-7", "label": "architecture",
                "prompt": "Review architecture / design (coupling, abstractions, "
                          "future maintainability) of this PR.\n\n"
                          "## PR ${PR_NUMBER}\n\n```diff\n{{git:diff}}\n```"
            },
            {
                "agent": "gemini-pro", "label": "edge-cases",
                "prompt": "Adversarially review this PR. List 5+ edge cases the "
                          "author probably did not test.\n\n```diff\n{{git:diff}}\n```"
            },
            {
                "agent": "claude-sonnet-4-6", "label": "summary",
                "depends_on": ["style", "architecture", "edge-cases"],
                "prompt": "Synthesize these three reviews into a single GitHub-PR "
                          "comment. Markdown formatted, with collapsible "
                          "<details> sections for each angle. Be terse.\n\n"
                          "## Style\n{{style}}\n\n## Architecture\n{{architecture}}\n\n"
                          "## Edge cases\n{{edge-cases}}"
            },
        ],
    },
    {
        "id": "blog-draft",
        "title": "Blog draft (research → outline → write → polish)",
        "description": "End-to-end blog post drafting pipeline. Set ${TOPIC} in "
                        "Settings, optionally ${AUDIENCE} (default: developers) and "
                        "${WORD_COUNT} (default: 1200).",
        "spec": [
            {
                "agent": "gemini-pro", "label": "research",
                "prompt": "Research the topic '${TOPIC}'. Output a Markdown brief "
                          "with: 5 specific angles, 3 contrarian takes, recent "
                          "stats/examples worth citing, common reader misconceptions."
            },
            {
                "agent": "claude-opus-4-7", "label": "outline",
                "depends_on": ["research"],
                "prompt": "Build a blog outline (H2 headings + 1-line abstracts) "
                          "for an audience of ${AUDIENCE} based on this research. "
                          "Aim for ${WORD_COUNT} words total. Optimize for "
                          "skimming.\n\n## Research\n{{research}}"
            },
            {
                "agent": "claude-opus-4-7", "label": "draft",
                "depends_on": ["outline"],
                "prompt": "Write the full blog post per this outline. ${WORD_COUNT} "
                          "words. Avoid AI-tells (em-dashes, 'delve', 'crucial'). "
                          "Concrete examples only, no fluff.\n\n## Outline\n{{outline}}"
            },
            {
                "agent": "gemini-pro", "label": "polish",
                "depends_on": ["draft"],
                "prompt": "Edit this blog draft. Cut 15%, sharpen leads, fix any "
                          "weak sections. Output the final polished post in "
                          "Markdown — no commentary, just the prose.\n\n{{draft}}"
            },
        ],
    },
    {
        "id": "bug-investigation",
        "title": "Bug investigation (file → 3 models → action plan)",
        "description": "Three models analyze the same file looking for the bug "
                        "described in ${BUG_DESCRIPTION}. Set ${TARGET_FILE} in "
                        "Settings. Best for production incidents.",
        "spec": [
            {
                "agent": "claude-opus-4-7", "label": "deep-read",
                "prompt": "Bug report: ${BUG_DESCRIPTION}\n\n"
                          "Walk through this file line-by-line, name every "
                          "potential cause that matches the symptom. Markdown "
                          "numbered list, ranked by likelihood.\n\n"
                          "```\n{{file:${TARGET_FILE}}}\n```"
            },
            {
                "agent": "gemini-pro", "label": "lateral",
                "prompt": "Bug: ${BUG_DESCRIPTION}\n\nThink laterally about this "
                          "file — what's NOT in it that should be? Defensive "
                          "checks, error handling, race conditions, config "
                          "issues. Markdown bullets.\n\n"
                          "```\n{{file:${TARGET_FILE}}}\n```"
            },
            {
                "agent": "claude-sonnet-4-6", "label": "git-context",
                "prompt": "Bug: ${BUG_DESCRIPTION}\n\nWhich recent commits "
                          "touched this file or related ones? Could any of them "
                          "be the regression?\n\n## Recent commits\n"
                          "{{git:log:20}}\n\n## Diff vs HEAD~5\n"
                          "{{git:diff:HEAD~5}}"
            },
            {
                "agent": "claude-opus-4-7", "label": "plan",
                "depends_on": ["deep-read", "lateral", "git-context"],
                "prompt": "Synthesize a concrete investigation plan from these "
                          "three angles. Specific commands to run, files to "
                          "check, hypotheses to verify. Order by fastest-to-"
                          "rule-out first.\n\n"
                          "## Deep read\n{{deep-read}}\n\n"
                          "## Lateral\n{{lateral}}\n\n"
                          "## Git context\n{{git-context}}"
            },
        ],
    },
    {
        "id": "code-review",
        "title": "Code review — 3 models cross-check",
        "description": "Three models review the same diff: Sonnet for style + bugs, "
                        "Opus 4.7 for architecture (1M context), Gemini Pro for "
                        "edge cases. Use {{diff}} placeholder by editing the prompts "
                        "and pasting the diff at the top of each.",
        "spec": [
            {
                "agent": "claude-sonnet-4-6", "label": "style",
                "prompt": "Review this code change. Focus on style, readability, "
                          "obvious bugs, and missing tests. Be concise — bullet list, "
                          "max 10 items.\n\n[paste diff here]"
            },
            {
                "agent": "claude-opus-4-7", "label": "architecture",
                "prompt": "Review this code change at the architecture level. "
                          "Coupling, abstractions, future maintainability. Bullet "
                          "list of concrete concerns + suggested fixes.\n\n"
                          "[paste diff here]"
            },
            {
                "agent": "gemini-pro", "label": "edge-cases",
                "prompt": "Adversarially review this code change. List 5+ specific "
                          "edge cases the author probably did not test. Be concrete: "
                          "exact inputs, expected vs likely actual behavior.\n\n"
                          "[paste diff here]"
            },
        ],
    },
    {
        "id": "browser-pilot-search",
        "title": "🤖 Browser Pilot — autonomous web search",
        "description": "Goal-driven Playwright loop. Pilot decides every "
                        "next action from a screenshot + page text + element list. "
                        "Single agent, prompt is JSON {goal, model?, max_steps?, start_url?}.",
        "spec": [
            {
                "agent": "browser-pilot", "label": "pilot",
                "prompt": json.dumps({
                    "goal": "Open DuckDuckGo, search for 'site:python.org pep 723' and tell me the title of the first result.",
                    "model": "claude-sonnet-4-6",
                    "max_steps": 8,
                    "start_url": "https://duckduckgo.com",
                    "headless": True,
                }, indent=2),
            },
        ],
    },
    {
        "id": "browser-pilot-summarize",
        "title": "🤖 Browser Pilot → Claude summary",
        "description": "Pilot navigates to a target URL and extracts the answer; "
                        "Claude turns the trace into a clean Markdown summary.",
        "spec": [
            {
                "agent": "browser-pilot", "label": "pilot",
                "prompt": json.dumps({
                    "goal": "Visit https://news.ycombinator.com and tell me the top 3 story titles with their points and comments count.",
                    "model": "claude-sonnet-4-6",
                    "max_steps": 6,
                    "start_url": "https://news.ycombinator.com",
                }, indent=2),
            },
            {
                "agent": "claude-sonnet-4-6", "label": "summary",
                "depends_on": ["pilot"],
                "prompt": "Format this browser-pilot trace as a clean Markdown "
                          "report with the final answer at the top and a short "
                          "step-by-step trace below.\n\n{{pilot}}",
            },
        ],
    },
    # ============================================================
    # v38 — Real-world workflow presets (Hustler practical pack)
    # Each one ships with sensible default ${VARS} you edit once in
    # Settings → Variables. Together they target the highest-volume
    # automations: content, design, research, code, comms, ops.
    # ============================================================
    {
        "id": "blog-article-full",
        "title": "📝 Blog article pipeline (research → outline → draft → SEO polish)",
        "description": "End-to-end blog post: web research → structured outline → "
                       "long-form draft → SEO-polished final. Set ${TOPIC}, ${TONE}, "
                       "${WORD_COUNT} once in Settings → Variables. Critique catches "
                       "weak claims and suggests internal-link anchors.",
        "variables": {
            "TOPIC": "Why open-source multi-agent orchestrators are eating Zapier",
            "TONE": "expert but readable — confident, no fluff, no AI clichés",
            "WORD_COUNT": "1400",
        },
        "spec": [
            {
                "agent": "gemini-pro", "label": "research",
                "prompt": "You are a research analyst. For the topic below, return a "
                          "Markdown brief with: 5-7 fact-checked talking points (each "
                          "with a credible source URL or a 'verify:' note if uncertain), "
                          "3 contrarian angles, 2 data points worth quoting, and 5 "
                          "long-tail keywords search-engines will reward. Output "
                          "Markdown only.\n\n## Topic\n${TOPIC}",
            },
            {
                "agent": "claude-sonnet-4-6", "label": "outline",
                "depends_on": ["research"],
                "prompt": "Write a tight outline for a ${WORD_COUNT}-word blog post on "
                          "'${TOPIC}'. Structure: H1, 4-6 H2 sections, hook, "
                          "objection-handling, CTA. Pull from the research brief. "
                          "Output Markdown only.\n\n## Research brief\n{{research}}",
            },
            {
                "agent": "claude-opus-4-7", "label": "draft",
                "depends_on": ["outline", "research"],
                "prompt": "Write the full blog post following the outline. Tone: ${TONE}. "
                          "Target ${WORD_COUNT} words. Use concrete examples from the "
                          "research brief. Add a punchy intro hook (≤2 sentences) and "
                          "a CTA at the end. No headings beyond H2/H3. No 'in this "
                          "post we will' filler. Output Markdown only.\n\n"
                          "## Outline\n{{outline}}\n\n## Research\n{{research}}",
            },
            {
                "agent": "claude-sonnet-4-6", "label": "seo-polish",
                "depends_on": ["draft"],
                "prompt": "Polish this draft for SEO + readability. Tasks: tighten "
                          "intro to 2 sentences, add 1 internal-link anchor placeholder "
                          "[INT: ...] per H2, replace passive voice, add meta title "
                          "(≤60 chars) + meta description (≤155 chars) at the top, "
                          "spell-check, and remove any AI cliché phrases. Output the "
                          "final polished post.\n\n{{draft}}",
            },
        ],
    },
    {
        "id": "social-content-fanout",
        "title": "📱 Social content fan-out (1 article → 5 platform posts)",
        "description": "Take one long-form piece and produce 5 platform-tuned posts: "
                       "X thread, LinkedIn, Instagram caption, TikTok hook, "
                       "Facebook. Each agent runs in parallel. Paste your source "
                       "into ${SOURCE} or use {{file:path/to/article.md}}.",
        "variables": {
            "SOURCE": "[Paste your article / blog / talk transcript here, or replace "
                      "with {{file:notes/post-2026-05-08.md}} to pull from disk.]",
        },
        "spec": [
            {
                "agent": "claude-sonnet-4-6", "label": "x-thread",
                "prompt": "Convert the source into an X (Twitter) thread of 6-9 posts. "
                          "Hook in post 1 (≤200 chars). Each post ≤280 chars. End "
                          "with a clear CTA. No emojis unless the source already had "
                          "them. Output as numbered list 1/ 2/ etc.\n\n## Source\n${SOURCE}",
            },
            {
                "agent": "claude-sonnet-4-6", "label": "linkedin",
                "prompt": "Write a LinkedIn post (1500-2200 chars) from the source. "
                          "Hook ≤2 lines. Use line breaks generously. End with one "
                          "thoughtful question to drive comments. No hashtags in body — "
                          "list 5 relevant hashtags below.\n\n## Source\n${SOURCE}",
            },
            {
                "agent": "claude-sonnet-4-6", "label": "instagram",
                "prompt": "Write an Instagram caption (≤2200 chars but aim for 800-1400). "
                          "Hook ≤125 chars (preview-safe). Bullet-style for scanability. "
                          "End with a soft CTA + 12-20 niche hashtags grouped at the "
                          "bottom.\n\n## Source\n${SOURCE}",
            },
            {
                "agent": "gemini-flash", "label": "tiktok-hook",
                "prompt": "Pull 3 TikTok script hooks from the source. Each hook ≤8 "
                          "seconds spoken (≈25 words). Format: \"HOOK: ... \" — make "
                          "them stop-the-scroll worthy. Output as a numbered list.\n\n"
                          "## Source\n${SOURCE}",
            },
            {
                "agent": "gemini-flash", "label": "facebook",
                "prompt": "Write a Facebook post (400-700 chars) from the source. "
                          "Conversational tone. End with an open-ended question. "
                          "No hashtags.\n\n## Source\n${SOURCE}",
            },
        ],
    },
    {
        "id": "design-brief-to-concepts",
        "title": "🎨 Design brief → 3 directions → critique",
        "description": "Turn a brief into 3 distinct design directions (mood, palette, "
                       "type stack, key components), then critique against the brief. "
                       "Pair with Stitch MCP to render screens for each direction, "
                       "or with Open Design MCP for a full prototype.",
        "variables": {
            "BRIEF": "Landing page for an indie developer-tool SaaS. Audience: senior "
                     "engineers. Vibe: confident, terminal-adjacent, premium. Must "
                     "feel different from Linear and Vercel.",
            "BRAND_COLORS": "(optional) coral #FF7A59, amber #FFB87A, cream #F5E6D3",
        },
        "spec": [
            {
                "agent": "claude-opus-4-7", "label": "direction-a",
                "prompt": "You are a senior brand designer. Given the brief, propose "
                          "Direction A. Output Markdown sections: Concept (2 sentences), "
                          "Mood (5 adjectives), Palette (4-6 hex codes with names + "
                          "rationale; respect ${BRAND_COLORS} if provided), Type stack "
                          "(display + body + mono), Key components (10 bullet points "
                          "with one-line spec each), Hero copy (headline + sub).\n\n"
                          "## Brief\n${BRIEF}\n\n## Brand colors\n${BRAND_COLORS}",
            },
            {
                "agent": "claude-opus-4-7", "label": "direction-b",
                "prompt": "Same brief as direction A. Propose a DIFFERENT direction B "
                          "(distinct mood + palette + type). Same Markdown structure. "
                          "Avoid duplicating direction A's choices.\n\n## Brief\n${BRIEF}\n\n"
                          "## Brand colors\n${BRAND_COLORS}",
            },
            {
                "agent": "gemini-pro", "label": "direction-c",
                "prompt": "Same brief as A and B. Propose direction C — go bolder, "
                          "more contrarian. Different mood + palette + type. Same "
                          "Markdown structure.\n\n## Brief\n${BRIEF}\n\n"
                          "## Brand colors\n${BRAND_COLORS}",
            },
            {
                "agent": "claude-sonnet-4-6", "label": "critique",
                "depends_on": ["direction-a", "direction-b", "direction-c"],
                "prompt": "Compare the 3 directions against the brief. Score each "
                          "0-10 on: Brief fit, Differentiation, Memorability, "
                          "Implementation cost. End with 'Recommendation: …' (one "
                          "paragraph). Be terse.\n\n## Brief\n${BRIEF}\n\n"
                          "## A\n{{direction-a}}\n\n## B\n{{direction-b}}\n\n"
                          "## C\n{{direction-c}}",
            },
        ],
    },
    {
        "id": "translate-cz-en",
        "title": "🌍 Translate CZ ↔ EN (draft → review → polish)",
        "description": "Two-pass translation with a different model on the second "
                       "pass for catch-anything-missed. Set ${SRC_LANG}, ${DST_LANG}, "
                       "${REGISTER}.",
        "variables": {
            "SRC_LANG": "Czech",
            "DST_LANG": "English",
            "REGISTER": "professional but warm — like a fluent native, not a robot",
            "SOURCE": "[Paste source text here, or use {{file:notes/text-cz.md}}.]",
        },
        "spec": [
            {
                "agent": "claude-sonnet-4-6", "label": "draft",
                "prompt": "Translate from ${SRC_LANG} to ${DST_LANG}. Register: "
                          "${REGISTER}. Preserve formatting (Markdown, code, lists, "
                          "links). Don't translate code identifiers or quoted brand "
                          "names. Don't add commentary. Output ONLY the translation.\n\n"
                          "## Source\n${SOURCE}",
            },
            {
                "agent": "claude-opus-4-7", "label": "review",
                "depends_on": ["draft"],
                "prompt": "Review this ${DST_LANG} translation. Find: literal/awkward "
                          "phrasing, missing nuance, wrong register, lost cultural "
                          "context. Output a Markdown bullet list of fixes (≤8 "
                          "bullets) with the specific phrase quoted. If perfect, "
                          "say so.\n\n## Source (${SRC_LANG})\n${SOURCE}\n\n"
                          "## Draft (${DST_LANG})\n{{draft}}",
            },
            {
                "agent": "claude-sonnet-4-6", "label": "final",
                "depends_on": ["draft", "review"],
                "prompt": "Apply the reviewer's fixes to the draft. Output ONLY the "
                          "final ${DST_LANG} text, no commentary, preserve original "
                          "formatting.\n\n## Draft\n{{draft}}\n\n## Reviewer fixes\n{{review}}",
            },
        ],
    },
    {
        "id": "email-drip-5",
        "title": "✉️ Email drip sequence (5-email value series)",
        "description": "Generate a 5-email nurture sequence. Each email lands a "
                       "different angle: welcome, problem, story, proof, CTA. Set "
                       "${PRODUCT}, ${PERSONA}, ${OUTCOME}.",
        "variables": {
            "PRODUCT": "CG — multi-agent orchestrator that runs Claude + Gemini in "
                       "parallel on subscription plans (no API keys)",
            "PERSONA": "Senior engineer at a 10-50 person startup who's already paying "
                       "for Claude Pro and Gemini Advanced and feels Zapier/Make are "
                       "too consumer-focused",
            "OUTCOME": "Replace 70% of their Make.com subscription cost with a self-hosted "
                       "agent pipeline they own end-to-end",
        },
        "spec": [
            {
                "agent": "claude-sonnet-4-6", "label": "email-1-welcome",
                "prompt": "Write email 1 of 5: WELCOME. Subject + preheader + body "
                          "(120-180 words). Tone: warm, no fluff. Set the stage. "
                          "Promise the next 4 emails. Single CTA: reply with their "
                          "biggest pain point. Product: ${PRODUCT}. Persona: ${PERSONA}.",
            },
            {
                "agent": "claude-sonnet-4-6", "label": "email-2-problem",
                "prompt": "Write email 2 of 5: PROBLEM AGITATION. Subject + preheader + "
                          "body (180-240 words). Open with a relatable pain story. "
                          "Quantify the cost. No solution yet. Product: ${PRODUCT}. "
                          "Persona: ${PERSONA}. Outcome they want: ${OUTCOME}.",
            },
            {
                "agent": "claude-sonnet-4-6", "label": "email-3-story",
                "prompt": "Write email 3 of 5: STORY/CASE. Subject + preheader + "
                          "body (200-300 words). Tell a believable customer-style "
                          "story (label as 'composite — based on real users'). Show "
                          "the before/after. Product: ${PRODUCT}.",
            },
            {
                "agent": "claude-sonnet-4-6", "label": "email-4-proof",
                "prompt": "Write email 4 of 5: PROOF. Subject + preheader + body "
                          "(160-220 words). Show 3 concrete proofs (numbers, "
                          "screenshots described in [SCREENSHOT: ...] tags, social "
                          "quotes). End with a soft CTA: book a 15-min walkthrough. "
                          "Product: ${PRODUCT}.",
            },
            {
                "agent": "claude-opus-4-7", "label": "email-5-cta",
                "prompt": "Write email 5 of 5: HARD CTA. Subject + preheader + body "
                          "(120-180 words). Recap the journey from emails 1-4 in 2 "
                          "sentences. Single clear CTA with urgency (free trial / "
                          "demo / first month at 50%). Product: ${PRODUCT}. Outcome: "
                          "${OUTCOME}.",
            },
        ],
    },
    {
        "id": "research-deep-dive",
        "title": "🔬 Research deep-dive (web crawl → synthesis → bullets)",
        "description": "Pulls fresh content from the web, synthesizes it through 3 "
                       "lenses, then a director compiles 10 bullets. Replace "
                       "${URLS} with comma-separated URLs to feed.",
        "variables": {
            "QUESTION": "What are the most useful self-hostable open-source alternatives "
                        "to Zapier in 2026? Compare on agent support, MCP compatibility, "
                        "and learning curve.",
            "URLS": "https://news.ycombinator.com,https://github.com/trending",
        },
        "spec": [
            {
                "agent": "claude-sonnet-4-6", "label": "lens-tech",
                "prompt": "From a TECHNICAL ARCHITECT lens, answer this question. "
                          "Use the web sources below as primary input. Cite by name "
                          "where possible. Output Markdown sections: Findings (5-8 "
                          "bullets), Strongest argument (one paragraph), Weakest "
                          "evidence (one paragraph).\n\n## Question\n${QUESTION}\n\n"
                          "## Sources\n{{web:${URLS}}}",
            },
            {
                "agent": "gemini-pro", "label": "lens-business",
                "prompt": "Same question, but from a BUSINESS OPERATOR lens — what "
                          "matters for cost, vendor risk, hiring. Same Markdown "
                          "structure as the tech lens.\n\n## Question\n${QUESTION}\n\n"
                          "## Sources\n{{web:${URLS}}}",
            },
            {
                "agent": "claude-sonnet-4-6", "label": "lens-user",
                "prompt": "Same question, but from a DAY-TO-DAY USER lens — onboarding, "
                          "ergonomics, debugging. Same structure.\n\n## Question\n"
                          "${QUESTION}\n\n## Sources\n{{web:${URLS}}}",
            },
            {
                "agent": "claude-opus-4-7", "label": "synthesis",
                "depends_on": ["lens-tech", "lens-business", "lens-user"],
                "prompt": "Synthesize the 3 lenses into 10 prioritized bullets that "
                          "directly answer the question. Each bullet ≤25 words. Group "
                          "by theme. End with 'TL;DR: …' (one sentence).\n\n"
                          "## Question\n${QUESTION}\n\n## Tech\n{{lens-tech}}\n\n"
                          "## Business\n{{lens-business}}\n\n## User\n{{lens-user}}",
            },
        ],
    },
    {
        "id": "meeting-to-actions",
        "title": "🎙 Meeting transcript → summary + action items",
        "description": "Turn a meeting transcript into: 2-paragraph summary, "
                       "decisions made, blockers, and a numbered list of action "
                       "items with [Owner / Due] tags. Paste transcript into "
                       "${TRANSCRIPT} or use {{file:transcripts/2026-05-08.txt}}.",
        "variables": {
            "TRANSCRIPT": "[Paste transcript here. Use ${PARTICIPANTS} as a hint to the "
                          "model so it gets owners right.]",
            "PARTICIPANTS": "Hustler (founder), Claude (engineer)",
        },
        "spec": [
            {
                "agent": "gemini-flash", "label": "summary",
                "prompt": "Summarize this meeting in EXACTLY 2 paragraphs. Paragraph 1: "
                          "context + main topics. Paragraph 2: outcomes + sentiment. "
                          "No bullet lists. ≤220 words total.\n\n## Participants\n"
                          "${PARTICIPANTS}\n\n## Transcript\n${TRANSCRIPT}",
            },
            {
                "agent": "claude-sonnet-4-6", "label": "decisions-blockers",
                "prompt": "Pull 'Decisions made' and 'Blockers/Risks' from this "
                          "transcript. Two Markdown sections. Quote the speaker who "
                          "owns each.\n\n## Participants\n${PARTICIPANTS}\n\n"
                          "## Transcript\n${TRANSCRIPT}",
            },
            {
                "agent": "claude-opus-4-7", "label": "action-items",
                "depends_on": ["decisions-blockers"],
                "prompt": "Extract action items as a numbered list. Format: "
                          "'1. [Owner / Due] task — context'. Owner from "
                          "${PARTICIPANTS}. Due defaults to 'this week' if not stated. "
                          "Be conservative — only include explicit asks, not vague "
                          "wishes.\n\n## Transcript\n${TRANSCRIPT}\n\n"
                          "## Decisions + blockers\n{{decisions-blockers}}",
            },
        ],
    },
    {
        "id": "code-pr-review",
        "title": "🔍 Code PR review (security + perf + readability)",
        "description": "Three reviewers each from a different angle, then a director "
                       "deduplicates. Inject the diff with {{git:diff}} or paste it "
                       "into ${DIFF}.",
        "variables": {
            "DIFF": "{{git:diff}}",
            "CONTEXT": "Python 3.12, FastAPI backend, PostgreSQL via Prisma. Hot path; "
                       "perf matters more than purity.",
        },
        "spec": [
            {
                "agent": "claude-opus-4-7", "label": "security",
                "prompt": "You are an OWASP-trained security auditor. Review THIS "
                          "DIFF for: injection (SQL/cmd/prompt), authn/authz holes, "
                          "missing input validation, secrets in code, insecure "
                          "deserialization, SSRF, XSS, CSRF. Output Markdown: severity "
                          "(Critical/High/Med/Low), CWE id, exact file:line, fix. "
                          "If clean, say so.\n\n## Context\n${CONTEXT}\n\n## Diff\n${DIFF}",
            },
            {
                "agent": "claude-sonnet-4-6", "label": "performance",
                "prompt": "Review for performance issues only: N+1 queries, blocking "
                          "I/O on async paths, unnecessary loops, allocations in hot "
                          "paths, missing indexes. Output Markdown bullets with "
                          "file:line refs. If clean, say so.\n\n## Context\n${CONTEXT}\n\n"
                          "## Diff\n${DIFF}",
            },
            {
                "agent": "gemini-pro", "label": "readability",
                "prompt": "Review for readability + maintainability: unclear naming, "
                          "missing tests, dead code, over-abstraction, missed comments. "
                          "Output ≤8 bullets. If clean, say so.\n\n## Context\n${CONTEXT}\n\n"
                          "## Diff\n${DIFF}",
            },
            {
                "agent": "claude-opus-4-7", "label": "verdict",
                "depends_on": ["security", "performance", "readability"],
                "prompt": "Merge the 3 reviews. Dedup overlapping findings. Order "
                          "by severity. End with a clear verdict: 'APPROVE' / "
                          "'APPROVE_WITH_NITS' / 'REQUEST_CHANGES'. One sentence "
                          "rationale.\n\n## Security\n{{security}}\n\n## Perf\n{{performance}}\n\n"
                          "## Readability\n{{readability}}",
            },
        ],
    },
    {
        "id": "product-description-3",
        "title": "🛍 Product description (3 angles + winner)",
        "description": "Generate 3 product descriptions targeting different buyer "
                       "motivations (status, savings, ease), then a critic picks "
                       "the strongest. Set ${PRODUCT}, ${AUDIENCE}, ${KEY_FEATURE}.",
        "variables": {
            "PRODUCT": "ergonomic split mechanical keyboard, 60% layout, hot-swap, RGB",
            "AUDIENCE": "developers + writers who type 6+ hours daily",
            "KEY_FEATURE": "modular thumb cluster you can rearrange in 30 seconds",
        },
        "spec": [
            {
                "agent": "claude-sonnet-4-6", "label": "status-angle",
                "prompt": "Write a product description (120-180 words) hooking on "
                          "STATUS and craft. Lead with 'For people who notice the "
                          "difference between …'. Hero feature: ${KEY_FEATURE}. "
                          "Audience: ${AUDIENCE}. Product: ${PRODUCT}.",
            },
            {
                "agent": "claude-sonnet-4-6", "label": "savings-angle",
                "prompt": "Same product, same length. Hook on SAVINGS / ROI: 'Pay "
                          "once, type for a decade'. Quantify the savings. Product: "
                          "${PRODUCT}. Audience: ${AUDIENCE}. Hero: ${KEY_FEATURE}.",
            },
            {
                "agent": "claude-sonnet-4-6", "label": "ease-angle",
                "prompt": "Same product, same length. Hook on EASE / ergonomics: "
                          "'Your hands will thank you in week 2'. Concrete physical "
                          "comfort claims. Product: ${PRODUCT}. Audience: ${AUDIENCE}. "
                          "Hero: ${KEY_FEATURE}.",
            },
            {
                "agent": "claude-opus-4-7", "label": "winner",
                "depends_on": ["status-angle", "savings-angle", "ease-angle"],
                "prompt": "Pick the strongest of the 3 angles for this product + "
                          "audience. Quote 2 lines from the winner that prove it. "
                          "Suggest 2 small edits to make it even better. End with "
                          "'WINNER: <angle> — because …' (one sentence).\n\n"
                          "## Status\n{{status-angle}}\n\n## Savings\n{{savings-angle}}\n\n"
                          "## Ease\n{{ease-angle}}",
            },
        ],
    },
    {
        "id": "github-readme-from-code",
        "title": "📚 GitHub README generator (from code base)",
        "description": "Reads your project files, drafts a README with badges, "
                       "install, quickstart, and feature highlights. Set ${PROJECT_NAME} "
                       "and ${KEY_FILES} (comma-separated paths).",
        "variables": {
            "PROJECT_NAME": "CG — multi-agent orchestrator",
            "KEY_FILES": "src/cg.py,README.md,CHANGELOG.md,pyproject.toml",
            "ONE_LINER": "Run Claude Code + Gemini in parallel on your subscriptions, "
                         "no API keys, n8n-style canvas in the browser.",
        },
        "spec": [
            {
                "agent": "claude-sonnet-4-6", "label": "scan",
                "prompt": "You are scanning a project to write its README. Read the "
                          "key files below. Output Markdown sections: Project type "
                          "(detected from files), Main entry-points, Public surface "
                          "(top-level symbols / commands), Notable libs in use, "
                          "Inferred audience.\n\n## Files\n{{file:${KEY_FILES}}}",
            },
            {
                "agent": "claude-opus-4-7", "label": "readme",
                "depends_on": ["scan"],
                "prompt": "Write a complete GitHub README for ${PROJECT_NAME}. "
                          "Sections in order: Title + 1-line tagline (use ${ONE_LINER}), "
                          "Status badges (placeholders [![...]]), 3-line elevator pitch, "
                          "Quickstart (copy-pasteable), Features (8-12 bullets, group "
                          "by area), Architecture (one diagram, ASCII or mermaid "
                          "fenced block), CLI reference, Contributing, License (MIT). "
                          "Use the scan output as ground truth.\n\n## Scan\n{{scan}}",
            },
        ],
    },
]


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Context placeholders for prompts: {{file:...}}, {{git:...}}, {{shell:...}}
# ---------------------------------------------------------------------------

import re as _re

_PLACEHOLDER_RE = _re.compile(r"\{\{([a-zA-Z][a-zA-Z0-9_-]*):([^{}\n]+)\}\}")
_ALLOW_SHELL = os.environ.get("CG_ALLOW_SHELL", "0") == "1"


def ROOT_PROJECT_FOR_FILES() -> "Path":
    """Project root used to resolve {{file:...}} placeholders.

    Defaults to the CG repo root, but can be overridden by setting the
    ``CG_PROJECT_ROOT`` env var so the same dashboard can pull files
    from a sibling project (e.g. TeamIDAS).
    """
    override = os.environ.get("CG_PROJECT_ROOT")
    if override:
        return Path(override).resolve()
    return ROOT


def _git_placeholder(arg: str) -> str:
    """Resolve ``{{git:...}}`` placeholders by shelling out to ``git``."""
    parts = [p.strip() for p in arg.split(":") if p.strip() != ""] or ["status"]
    op = parts[0].lower()
    ref_or_n = parts[1] if len(parts) > 1 else None

    project_root = ROOT_PROJECT_FOR_FILES()

    cmd: list[str]
    if op == "diff":
        cmd = ["git", "diff"] + ([ref_or_n] if ref_or_n else [])
    elif op == "log":
        n = ref_or_n or "10"
        cmd = ["git", "log", "--oneline", f"-n{n}"]
    elif op == "status":
        cmd = ["git", "status", "--short", "--branch"]
    elif op == "show":
        cmd = ["git", "show", ref_or_n or "HEAD", "--stat"]
    elif op == "branch":
        cmd = ["git", "branch", "--show-current"]
    else:
        return f"[git: unknown op {op!r}]"

    try:
        out = subprocess.run(
            cmd, cwd=str(project_root), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=15,
        )
        return (
            out.stdout
            if out.returncode == 0
            else f"[git error: {out.stderr.strip()[:200]}]"
        )
    except subprocess.TimeoutExpired:
        return "[git: timeout]"
    except FileNotFoundError:
        return "[git: not installed or not on PATH]"


def _shell_placeholder(cmd: str) -> str:
    """Resolve ``{{shell:...}}`` — disabled by default, opt-in via env var."""
    project_root = ROOT_PROJECT_FOR_FILES()
    try:
        out = subprocess.run(
            cmd, shell=True, cwd=str(project_root),
            capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=30,
        )
        return out.stdout + (
            ("\n[stderr]\n" + out.stderr) if out.stderr.strip() else ""
        )
    except subprocess.TimeoutExpired:
        return "[shell: timeout 30s]"


SCREENSHOTS_DIR = ROOT / "outputs" / "screenshots"
BROWSER_AUTH_DIR = ROOT / "browser_auth"


def _run_browser_step(page: Any, ctx: Any, browser: Any, step: dict,
                        run: "RunState", label: str,
                        bindings: dict) -> Any:
    """Execute a single Playwright step and return its result.

    Supported actions (the canonical list — see docs/browser-actions.md):

      goto         {url}                              navigate
      click        {selector}                         click element
      fill         {selector, value}                  text input
      type         {selector, text, delay?}           keyboard typing
      press        {selector?, key}                   key press (Enter, etc.)
      hover        {selector}                         mouse hover
      scroll       {to: 'top'|'bottom'|number}        scroll
      wait_for     {selector?, time_ms?, state?}      wait for element/time
      extract      {selector, attr?}                  innerText or attribute
      extract_all  {selector, attr?}                  array of innerText/attr
      screenshot   {full_page?, selector?}            saves PNG, returns path
      evaluate     {script}                           run JS, return result
      title        {}                                 page title
      content      {}                                 full HTML
      url          {}                                 current URL
      accept_dialog {}                                accept next dialog
      pdf          {}                                 save PDF (paid Chromium feature)
    """
    a = step["action"]

    # Variable interpolation in step values from bindings + run.variables
    def _resolve(v: Any) -> Any:
        if not isinstance(v, str):
            return v
        # ${VAR} from run.variables
        for k, val in (run.variables or {}).items():
            v = v.replace("${" + k + "}", str(val))
        # {{label.field}} from bindings collected so far
        for binding_name, binding_val in bindings.items():
            if isinstance(binding_val, dict):
                for fk, fv in binding_val.items():
                    v = v.replace("{{" + binding_name + "." + fk + "}}",
                                    str(fv))
            v = v.replace("{{" + binding_name + "}}", str(binding_val))
        return v

    if a == "goto":
        url = _resolve(step["url"])
        wait = step.get("wait_until", "domcontentloaded")
        page.goto(url, wait_until=wait, timeout=step.get("timeout_ms", 30000))
        try:
            page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            pass
        return f"loaded {url}"

    if a == "click":
        sel = _resolve(step["selector"])
        page.click(sel, timeout=step.get("timeout_ms", 10000))
        return f"clicked {sel}"

    if a == "fill":
        sel = _resolve(step["selector"])
        val = _resolve(step.get("value", ""))
        page.fill(sel, val, timeout=step.get("timeout_ms", 10000))
        return f"filled {sel}"

    if a == "type":
        sel = _resolve(step["selector"])
        text = _resolve(step["text"])
        delay = int(step.get("delay", 0))
        page.type(sel, text, delay=delay)
        return f"typed into {sel}"

    if a == "press":
        sel = _resolve(step.get("selector", "body"))
        key = step["key"]
        page.press(sel, key)
        return f"pressed {key}"

    if a == "hover":
        sel = _resolve(step["selector"])
        page.hover(sel)
        return f"hovered {sel}"

    if a == "scroll":
        to = step.get("to", "bottom")
        if to == "top":
            page.evaluate("window.scrollTo(0, 0)")
        elif to == "bottom":
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        elif isinstance(to, (int, float)):
            page.evaluate(f"window.scrollTo(0, {to})")
        return f"scrolled {to}"

    if a == "wait_for":
        sel = step.get("selector")
        time_ms = step.get("time_ms")
        state = step.get("state", "visible")
        if sel:
            page.wait_for_selector(_resolve(sel), state=state,
                                     timeout=step.get("timeout_ms", 10000))
            return f"waited for {sel}"
        if time_ms:
            page.wait_for_timeout(int(time_ms))
            return f"waited {time_ms}ms"
        return "wait_for: no-op"

    if a == "extract":
        sel = _resolve(step["selector"])
        attr = step.get("attr")
        elem = page.query_selector(sel)
        if elem is None:
            return None
        if attr:
            return elem.get_attribute(attr)
        return elem.inner_text()

    if a == "extract_all":
        sel = _resolve(step["selector"])
        attr = step.get("attr")
        elements = page.query_selector_all(sel)
        if attr:
            return [e.get_attribute(attr) for e in elements]
        return [e.inner_text() for e in elements]

    if a == "screenshot":
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        import hashlib
        digest = hashlib.sha1((page.url or "").encode("utf-8")).hexdigest()[:12]
        fname = f"{int(time.time())}-{digest}-{label}.png"
        out_path = SCREENSHOTS_DIR / fname
        kwargs: dict[str, Any] = {"path": str(out_path),
                                    "full_page": bool(step.get("full_page", True))}
        sel = step.get("selector")
        if sel:
            elem = page.query_selector(_resolve(sel))
            if elem is not None:
                elem.screenshot(path=str(out_path))
            else:
                page.screenshot(**kwargs)
        else:
            page.screenshot(**kwargs)
        return f"outputs/screenshots/{fname}"

    if a == "evaluate":
        return page.evaluate(_resolve(step["script"]))

    if a == "title":
        return page.title()

    if a == "content":
        return page.content()

    if a == "url":
        return page.url

    if a == "accept_dialog":
        page.once("dialog", lambda d: d.accept())
        return "next dialog will be accepted"

    if a == "pdf":
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        fname = f"{int(time.time())}-{label}.pdf"
        out_path = SCREENSHOTS_DIR / fname
        page.pdf(path=str(out_path))
        return f"outputs/screenshots/{fname}"

    return f"[unknown action: {a}]"


def _web_placeholder(kind: str, url: str) -> str:
    """Resolve ``{{web:URL}}`` family of placeholders by driving headless
    Chromium via Playwright. Lazy-imports playwright so the dashboard
    runs without it; returns an actionable error if missing.

    kind options:
      ``web``, ``web-text``    — innerText of body
      ``web-html``             — full rendered outerHTML
      ``web-shot``, ``web-screenshot`` — save PNG, return repo-relative path
      ``web-title``            — page <title>
      ``web-meta``             — meta tags + OG as JSON
    """
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        return ("[web: playwright not installed. "
                "pip install playwright; playwright install chromium]")

    if not (url.startswith("http://") or url.startswith("https://")):
        return f"[web: URL must start with http:// or https:// (got {url!r})]"

    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    from playwright.sync_api import sync_playwright

    timeout_ms = int(os.environ.get("CG_WEB_TIMEOUT_MS", "30000"))

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                ctx = browser.new_context(
                    user_agent=("Mozilla/5.0 (CG dashboard headless "
                                 "via Playwright Chromium)"),
                    viewport={"width": 1280, "height": 800},
                )
                page = ctx.new_page()
                page.goto(url, timeout=timeout_ms,
                            wait_until="domcontentloaded")
                # Brief settle wait for rendering — use load OR network idle,
                # whichever finishes first
                try:
                    page.wait_for_load_state("networkidle", timeout=5000)
                except Exception:
                    pass

                if kind in {"web", "web-text"}:
                    body = page.inner_text("body") or ""
                    return body.strip()

                if kind == "web-html":
                    return page.content() or ""

                if kind in {"web-shot", "web-screenshot"}:
                    import hashlib
                    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
                    safe_url = (
                        url.replace("https://", "").replace("http://", "")
                           .replace("/", "_").replace(":", "-")[:80]
                    )
                    fname = f"{int(time.time())}-{digest}-{safe_url}.png"
                    out_path = SCREENSHOTS_DIR / fname
                    page.screenshot(path=str(out_path), full_page=True)
                    return f"[screenshot saved] outputs/screenshots/{fname}"

                if kind == "web-title":
                    return page.title() or ""

                if kind == "web-meta":
                    meta = page.evaluate("""() => {
                        const out = { title: document.title || '',
                                       description: '', og: {}, twitter: {} };
                        document.querySelectorAll('meta').forEach(m => {
                            const name = m.getAttribute('name');
                            const prop = m.getAttribute('property');
                            const content = m.getAttribute('content') || '';
                            if (name === 'description') out.description = content;
                            if (prop && prop.startsWith('og:'))
                                out.og[prop.slice(3)] = content;
                            if (name && name.startsWith('twitter:'))
                                out.twitter[name.slice(8)] = content;
                        });
                        return out;
                    }""")
                    return json.dumps(meta, indent=2, ensure_ascii=False)

                return f"[web: unknown subkind {kind!r}]"
            finally:
                browser.close()
    except Exception as exc:
        return f"[web: error — {exc}]"


def _expand_context_placeholders(text: str) -> str:
    """Replace ``{{kind:arg}}`` patterns with their resolved values.

    Supports:
      ``{{file:path/to/file}}``     — repo-relative file content (UTF-8)
      ``{{git:diff}}``              — current git diff (working tree)
      ``{{git:diff:HEAD~1}}``       — git diff vs ref
      ``{{git:log:5}}``             — last N commits oneline
      ``{{git:status}}``            — git status --short --branch
      ``{{git:show:HEAD}}``         — git show with --stat
      ``{{git:branch}}``            — current branch name
      ``{{shell:cmd ...}}``         — disabled unless CG_ALLOW_SHELL=1
      ``{{web:URL}}``               — innerText of rendered page
      ``{{web-html:URL}}``          — full rendered HTML
      ``{{web-shot:URL}}``          — screenshot saved, returns relative path
      ``{{web-title:URL}}``         — <title> tag text
      ``{{web-meta:URL}}``          — meta tags + OpenGraph as JSON
    Unknown ``kind`` is left as-is so the agent can complain.
    """
    def replace_one(match: "_re.Match[str]") -> str:
        kind = match.group(1).lower()
        arg = match.group(2).strip()
        try:
            if kind == "file":
                p = (ROOT_PROJECT_FOR_FILES() / arg).resolve()
                root = ROOT_PROJECT_FOR_FILES()
                # safety: must stay under project root
                try:
                    p.relative_to(root)
                except ValueError:
                    return f"[file: refused — {arg} is outside the project root]"
                if not p.exists():
                    return f"[file: not found — {arg}]"
                return p.read_text(encoding="utf-8", errors="replace")

            if kind == "git":
                return _git_placeholder(arg)

            if kind == "shell":
                if not _ALLOW_SHELL:
                    return "[shell: disabled — set CG_ALLOW_SHELL=1 to enable]"
                return _shell_placeholder(arg)

            if kind in {"web", "web-text", "web-html", "web-shot",
                         "web-screenshot", "web-title", "web-meta"}:
                return _web_placeholder(kind, arg)
        except Exception as exc:
            return f"[{kind}: error — {exc}]"
        return match.group(0)

    return _PLACEHOLDER_RE.sub(replace_one, text)


# ---------------------------------------------------------------------------
# HTTP response text extraction (per-provider shape differences)
# ---------------------------------------------------------------------------


def _extract_response_text(raw: str, http_cfg: dict[str, Any]) -> str:
    """Pull plain text out of the JSON response, accounting for provider
    differences. Falls back to the raw body if parsing fails so the user
    still sees the error payload."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return raw

    # Provider-specific shapes
    if http_cfg.get("anthropic_native"):
        # {"content": [{"type":"text", "text":"..."}], ...}
        content = data.get("content") or []
        parts = [c.get("text", "") for c in content if c.get("type") == "text"]
        if parts:
            return "\n".join(parts)
        # Errors: {"error": {"type":"...", "message":"..."}}
        if "error" in data:
            return f"[anthropic error] {data['error']}"
        return raw

    if http_cfg.get("google_native"):
        # {"candidates": [{"content": {"parts": [{"text":"..."}]}}]}
        cands = data.get("candidates") or []
        if cands:
            content = cands[0].get("content", {})
            parts = content.get("parts", [])
            text_parts = [p.get("text", "") for p in parts if "text" in p]
            if text_parts:
                return "".join(text_parts)
        if "error" in data:
            return f"[google error] {data['error']}"
        return raw

    # OpenAI-compatible (OpenRouter / Z.ai / DeepSeek)
    # {"choices": [{"message": {"content": "..."}}], "usage": {...}}
    choices = data.get("choices") or []
    if choices:
        msg = choices[0].get("message", {})
        content = msg.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):  # multi-part content blocks
            return "".join(p.get("text", "") for p in content if isinstance(p, dict))
    if "error" in data:
        return f"[provider error] {data['error']}"
    return raw


# ---------------------------------------------------------------------------
# Notes (Obsidian-inspired knowledge base)
# ---------------------------------------------------------------------------


def _iso_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())


def _safe_note_name(raw: str) -> str:
    safe = _re.sub(r"[^a-zA-Z0-9._\- ]+", "-", raw.strip()) or "note"
    safe = _re.sub(r"\s+", "-", safe)
    return safe[:120].strip("-").lower()


def _note_path(name: str) -> Path:
    return NOTES_DIR / f"{_safe_note_name(name)}.md"


_FM_RE = _re.compile(r"^---\s*\n(.*?)\n---\s*\n", _re.DOTALL)


def _parse_note(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    frontmatter: dict[str, Any] = {}
    body = raw
    m = _FM_RE.match(raw)
    if m:
        body = raw[m.end():]
        for line in m.group(1).splitlines():
            if ":" not in line:
                continue
            k, _, v = line.partition(":")
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                inner = v[1:-1].strip()
                frontmatter[k.strip()] = (
                    [item.strip().strip('"\'') for item in inner.split(",")
                     if item.strip()]
                    if inner else []
                )
            else:
                frontmatter[k.strip()] = v.strip('"\'')
    name = path.stem
    return {
        "name": name,
        "title": frontmatter.get("title") or name,
        "tags": frontmatter.get("tags") or [],
        "created": frontmatter.get("created"),
        "updated": frontmatter.get("updated"),
        "run_id": frontmatter.get("run_id"),
        "content": body.lstrip("\n"),
    }


def _render_note(frontmatter: dict[str, Any], body: str) -> str:
    lines = ["---"]
    for k, v in frontmatter.items():
        if v is None:
            continue
        if isinstance(v, list):
            arr = ", ".join(f'"{item}"' for item in v)
            lines.append(f"{k}: [{arr}]")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append("")
    lines.append(body.rstrip())
    lines.append("")
    return "\n".join(lines)


def _list_notes() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for p in sorted(NOTES_DIR.glob("*.md"), key=lambda x: x.stat().st_mtime,
                    reverse=True):
        try:
            note = _parse_note(p)
        except Exception:
            continue
        out.append({
            "name": note["name"],
            "title": note["title"],
            "tags": note["tags"],
            "updated": note["updated"],
            "size": p.stat().st_size,
        })
    return out


_WIKILINK_RE = _re.compile(r"\[\[([^\]\|]+)(?:\|[^\]]+)?\]\]")


def _find_backlinks(target_name: str) -> list[dict[str, Any]]:
    """Return notes whose body links to *target_name* via [[wikilink]]."""
    target = _safe_note_name(target_name)
    out: list[dict[str, Any]] = []
    for p in NOTES_DIR.glob("*.md"):
        if p.stem == target:
            continue
        try:
            note = _parse_note(p)
        except Exception:
            continue
        body = note["content"]
        links = [_safe_note_name(m) for m in _WIKILINK_RE.findall(body)]
        if target in links:
            # Extract a 200-char excerpt around the first match
            for m in _WIKILINK_RE.finditer(body):
                if _safe_note_name(m.group(1)) == target:
                    start = max(0, m.start() - 80)
                    end = min(len(body), m.end() + 80)
                    excerpt = body[start:end].replace("\n", " ")
                    out.append({
                        "name": note["name"],
                        "title": note["title"],
                        "excerpt": ("…" if start > 0 else "") + excerpt
                                    + ("…" if end < len(body) else ""),
                    })
                    break
    return out


def _search_notes(query: str) -> list[dict[str, Any]]:
    """Naive substring search across title + body. Good enough at this
    scale; can be replaced with a proper indexer later."""
    q = query.lower()
    out: list[dict[str, Any]] = []
    for p in NOTES_DIR.glob("*.md"):
        try:
            note = _parse_note(p)
        except Exception:
            continue
        haystack = (note["title"] + "\n" + note["content"]).lower()
        if q in haystack:
            idx = haystack.find(q)
            start = max(0, idx - 60)
            end = min(len(haystack), idx + len(q) + 80)
            excerpt = haystack[start:end].replace("\n", " ")
            out.append({
                "name": note["name"],
                "title": note["title"],
                "excerpt": ("…" if start > 0 else "") + excerpt
                            + ("…" if end < len(haystack) else ""),
            })
    return out


# ---------------------------------------------------------------------------
# Workflow filesystem helpers
# ---------------------------------------------------------------------------


def _safe_workflow_name(raw: str) -> str:
    """Sanitize a workflow name to a safe filesystem slug."""
    safe = _re.sub(r"[^a-zA-Z0-9._-]+", "-", raw.strip()) or "workflow"
    return safe[:80]


def _workflow_path(name: str) -> Path:
    return WORKFLOWS_DIR / f"{_safe_workflow_name(name)}.json"


def _name_of(path: Path) -> str:
    return path.stem


def _list_workflow_files() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for p in sorted(WORKFLOWS_DIR.glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict):
            # Tolerate non-dict workflow files (corrupt / hand-edited)
            continue
        spec = data.get("spec")
        if not isinstance(spec, list):
            spec = []
        out.append({
            "name": _name_of(p),
            "title": data.get("title") or _name_of(p),
            "agentCount": len(spec),
            "savedAt": data.get("savedAt"),
        })
    return out


# ---------------------------------------------------------------------------
# Run report renderer (single Markdown bundle)
# ---------------------------------------------------------------------------


def _render_run_report(run: "RunState") -> str:
    """Format a run as one self-contained Markdown document."""
    lines: list[str] = []
    lines.append(f"# CG run report — {run.title}")
    lines.append("")
    lines.append(f"- **id**: `{run.id}`")
    lines.append(f"- **created**: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(run.created))}")
    lines.append(f"- **agents**: {len(run.agents)}")
    if run.finished:
        lines.append(f"- **status**: finished")
    else:
        lines.append(f"- **status**: in progress")
    lines.append("")

    spec_by_label = {item.get("label", f"agent-{i+1}"): item
                      for i, item in enumerate(run.spec)}

    for label, agent in run.agents.items():
        lines.append("---")
        lines.append("")
        lines.append(f"## {label} — {agent.agent}")
        lines.append("")
        meta = []
        if agent.depends_on:
            meta.append(f"depends_on: `{', '.join(agent.depends_on)}`")
        meta.append(f"status: **{agent.status}**")
        if agent.exit_code is not None:
            meta.append(f"exit: `{agent.exit_code}`")
        if agent.started and agent.finished:
            dur = agent.finished - agent.started
            meta.append(f"duration: `{dur:.1f}s`")
        lines.append(" · ".join(meta))
        lines.append("")

        # Prompt
        prompt = (spec_by_label.get(label, {}) or {}).get("prompt", "")
        if prompt:
            lines.append("### Prompt")
            lines.append("")
            lines.append("```")
            lines.append(prompt.rstrip())
            lines.append("```")
            lines.append("")

        # Output
        lines.append("### Output")
        lines.append("")
        output = "\n".join(agent.log_lines).rstrip()
        if output:
            lines.append(output)
        else:
            lines.append("_(empty)_")
        lines.append("")

        # Stderr (if any)
        if agent.stderr_lines:
            lines.append("### stderr")
            lines.append("")
            lines.append("```")
            lines.append("\n".join(agent.stderr_lines).rstrip())
            lines.append("```")
            lines.append("")

    return "\n".join(lines)


def create_app() -> FastAPI:
    from contextlib import asynccontextmanager

    manager = RunManager()
    # Reload finished runs from on-disk index so dashboard history
    # survives a restart. Best-effort.
    hydrated = manager.hydrate_from_disk()
    if hydrated:
        print(f"[CG] Hydrated {hydrated} run(s) from disk")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        manager.bind_loop(asyncio.get_running_loop())
        _start_scheduler(manager)
        yield

    app = FastAPI(title="CG Dashboard", version="0.1", lifespan=lifespan)
    # Expose manager on app.state so tests can cancel pending runs in
    # teardown without leaking `_watch_run` threads (which would later
    # write to the next test's monkeypatched INDEX_PATH).
    app.state.cg_manager = manager

    # ---- Optional HTTP Basic auth ----------------------------------------
    # Disabled by default (env var unset) so local dev keeps working
    # without a password. Enable for any public deployment.
    @app.middleware("http")
    async def _basic_auth_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        if not _cg_auth.auth_enabled():
            return await call_next(request)
        # Allow unauthenticated GETs of static assets only — the index
        # page itself is gated, since it boots the SPA that hits /api.
        # (Browsers automatically resend the Authorization header for
        # subdocument requests once the user has typed the password
        # into the Basic-Auth dialog.)
        path = request.url.path
        if path.startswith("/static/") or path == "/favicon.ico":
            return await call_next(request)
        hdr = request.headers.get("authorization", "")
        if hdr.lower().startswith("basic "):
            try:
                import base64 as _b64
                decoded = _b64.b64decode(hdr[6:]).decode("utf-8")
                if ":" in decoded:
                    user, pw = decoded.split(":", 1)
                    if _cg_auth.check_credentials(user, pw):
                        return await call_next(request)
            except Exception:
                pass
        return Response(
            status_code=401,
            content="Authentication required.",
            headers={"WWW-Authenticate": 'Basic realm="ClaudeGravity"'},
        )

    @app.get("/", include_in_schema=False)
    async def root() -> Any:
        index = STATIC_DIR / "index.html"
        if not index.exists():
            return JSONResponse({"error": "frontend not built", "looked_for": str(index)},
                                status_code=500)
        # Render with cache-busting build stamp so browsers always
        # re-fetch dashboard.js / dashboard.css after a deploy. We use
        # the script's mtime so it only changes when the file changes.
        try:
            html = index.read_text(encoding="utf-8")
            js_mtime = int((STATIC_DIR / "dashboard.js").stat().st_mtime)
            css_mtime = int((STATIC_DIR / "dashboard.css").stat().st_mtime)
            stamp = f"{js_mtime}-{css_mtime}"
            html = html.replace("{{CG_BUILD}}", stamp)
            return HTMLResponse(html)
        except Exception:
            return FileResponse(index)

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/api/agents")
    async def get_agents() -> Any:
        return {
            "agents": [
                {
                    "id": k,
                    "label": v["label"],
                    "family": v.get("family", "other"),
                    "summary": v.get("summary", ""),
                }
                for k, v in AGENT_KINDS.items()
            ]
        }

    @app.get("/api/custom-agents")
    async def list_custom_agents() -> Any:
        if not CUSTOM_AGENTS_PATH.exists():
            return {"agents": []}
        try:
            return {"agents": json.loads(CUSTOM_AGENTS_PATH.read_text(encoding="utf-8"))}
        except Exception:
            return {"agents": []}

    @app.put("/api/custom-agents")
    async def save_custom_agents(body: dict[str, Any]) -> Any:
        items = body.get("agents")
        if not isinstance(items, list):
            raise HTTPException(400, "body.agents must be an array")
        # Light validation
        normalized: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        for entry in items:
            if not isinstance(entry, dict):
                continue
            kid = entry.get("id")
            if not kid or not _re.match(r"^[a-zA-Z][a-zA-Z0-9._-]*$", kid):
                raise HTTPException(400, f"agent id {kid!r} must be alnum/._-, start with letter")
            if kid in AGENT_KINDS and kid not in _load_custom_agents():
                raise HTTPException(409, f"id {kid!r} clashes with built-in agent")
            if kid in seen_ids:
                raise HTTPException(400, f"duplicate id {kid!r}")
            seen_ids.add(kid)
            http = entry.get("http") or {}
            if not http.get("endpoint") or not http.get("model"):
                raise HTTPException(400, f"agent {kid!r} needs http.endpoint and http.model")
            normalized.append({
                "id": kid,
                "label": entry.get("label", kid),
                "family": entry.get("family", "custom"),
                "summary": entry.get("summary", ""),
                "http": {
                    "endpoint": http["endpoint"],
                    "model": http["model"],
                    "api_key_env": http.get("api_key_env", ""),
                    "headers": http.get("headers", {}),
                    "anthropic_native": bool(http.get("anthropic_native", False)),
                    "google_native": bool(http.get("google_native", False)),
                },
            })
        _save_custom_agents(normalized)
        # Reload into AGENT_KINDS — first remove old custom entries
        for old_id in list(AGENT_KINDS.keys()):
            if AGENT_KINDS[old_id].get("family") == "custom":
                del AGENT_KINDS[old_id]
        AGENT_KINDS.update(_load_custom_agents())
        return {"saved": len(normalized)}

    @app.get("/api/presets")
    async def get_presets() -> Any:
        # v50 W5 — enrich each preset with its category for the Mission
        # Library tile UI. The map below is the only place to edit when
        # categorizing presets — adding `category: "..."` to 30 dict
        # literals would be brittle and easy to drift out of sync.
        out = []
        for p in PRESETS:
            entry = dict(p)
            entry["category"] = PRESET_CATEGORIES.get(p.get("id"), "other")
            out.append(entry)
        return {
            "presets": out,
            "categories": MISSION_CATEGORIES,
        }

    # v55 — pre-flight ${VAR} validator. Scans every step's prompt for
    # `${NAME}` placeholders and reports the set of variables that the
    # supplied `variables` dict does NOT cover. Used by both the dispatch
    # endpoint (returns 400 with missing list, frontend prompts user)
    # and a standalone `/api/spec/missing-vars` endpoint (used to peek
    # before submitting). Pattern matches uppercase A-Z, 0-9, underscore;
    # bracket form `${ ... }` only — `$VAR` shell-style is intentionally
    # NOT matched, since prompts often contain literal `$variable` text
    # in code examples.
    _VAR_RE = _re.compile(r"\$\{([A-Z][A-Z0-9_]*)\}")

    def _scan_unsubstituted_vars(spec_list: list[dict[str, Any]],
                                  variables: dict[str, Any]) -> list[str]:
        provided = set((variables or {}).keys())
        missing: set[str] = set()
        for step in spec_list or []:
            prompt = (step or {}).get("prompt") or ""
            for m in _VAR_RE.finditer(prompt):
                name = m.group(1)
                if name not in provided:
                    missing.add(name)
        return sorted(missing)

    @app.post("/api/spec/missing-vars")
    async def spec_missing_vars(body: dict[str, Any]) -> Any:
        spec = body.get("spec") or []
        variables = body.get("variables") or {}
        return {"missing": _scan_unsubstituted_vars(spec, variables)}

    @app.post("/api/runs")
    async def post_run(body: dict[str, Any], request: Request) -> Any:
        title = body.get("title") or "untitled"
        spec = body.get("spec") or []
        if not isinstance(spec, list) or not spec:
            raise HTTPException(400, "spec must be a non-empty array")
        # v55 — pre-flight validator: refuse runs where prompts contain
        # `${VAR}` placeholders that no variable covers. Old behavior
        # silently substituted nothing → director got literal `${IDEA}`
        # in its prompt and (correctly) refused to invent an idea, but
        # all 6 downstream agents still ran for 5+ minutes on garbage
        # before the user noticed. New behavior fails fast with a
        # structured response the frontend turns into a "Fill in: ..."
        # modal. To bypass (e.g. when the variable is supplied via
        # another mechanism), pass `?skip_var_check=1` as a query param.
        skip_var_check = request.query_params.get("skip_var_check") in (
            "1", "true", "yes",
        )
        body_vars = body.get("variables") or {}
        if not skip_var_check:
            missing = _scan_unsubstituted_vars(spec, body_vars)
            if missing:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "missing_variables",
                        "variables": missing,
                        "message": (
                            f"Run requires variable(s): {', '.join(missing)}. "
                            "Pass them in the request body's `variables` "
                            "dict, or append `?skip_var_check=1` to skip "
                            "this check."
                        ),
                    },
                )
        # Browser-supplied secrets (Settings tab) come in via headers so
        # they live only in localStorage + a single request body, never
        # on disk. Each runner reads its key by env var name; we set
        # those env vars on the run's session via a per-run "secrets"
        # dict, applied only when the runner spawns its subprocess.
        secrets: dict[str, str] = {}
        header_to_env = {
            "x-cg-openrouter-key": "OPENROUTER_API_KEY",
            "x-cg-zhipu-key": "ZHIPU_API_KEY",
            "x-cg-anthropic-key": "ANTHROPIC_API_KEY",
            "x-cg-gemini-key": "GEMINI_API_KEY",
            "x-cg-project-root": "CG_PROJECT_ROOT",
        }
        for header, env_name in header_to_env.items():
            v = request.headers.get(header)
            if v and v.strip():
                secrets[env_name] = v.strip()
        # Variables (`${VAR}` substitution in prompts) come in the body
        variables = body.get("variables") or {}
        run = manager.start_run(title, spec, secrets=secrets, variables=variables)
        return {"id": run.id, "title": run.title}

    @app.get("/api/runs")
    async def list_runs() -> Any:
        return {
            "runs": [r.to_public()
                     for r in sorted(manager.runs.values(),
                                      key=lambda x: x.created,
                                      reverse=True)]
        }

    @app.get("/api/runs/{run_id}")
    async def get_run(run_id: str) -> Any:
        run = manager.runs.get(run_id)
        if not run:
            raise HTTPException(404, "run not found")
        return run.to_public()

    @app.delete("/api/runs/{run_id}")
    async def cancel_run_ep(run_id: str) -> Any:
        if run_id not in manager.runs:
            raise HTTPException(404, "run not found")
        manager.cancel_run(run_id)
        return {"id": run_id, "cancelled": True}

    # v49 W4 — Replay-from-here. Re-runs `<label>` + every downstream
    # dependent. Prior steps' outputs stay on disk so upstream {{label}}
    # references still resolve. Kills any in-flight subprocess for the
    # affected steps before re-spawning.
    @app.post("/api/runs/{run_id}/replay-from/{label}")
    async def replay_from_ep(run_id: str, label: str) -> Any:
        if run_id not in manager.runs:
            raise HTTPException(404, "run not found")
        return {
            "id": run_id,
            "from": label,
            **manager.replay_from(run_id, label),
        }

    @app.get("/api/runs/{run_id}/output/{label}")
    async def get_output(run_id: str, label: str) -> Any:
        run = manager.runs.get(run_id)
        if not run:
            raise HTTPException(404, "run not found")
        if label not in run.agents:
            raise HTTPException(404, "label not found")
        return {"label": label, "log": "\n".join(run.agents[label].log_lines)}

    @app.get("/api/runs/{run_id}/report")
    async def get_run_report(run_id: str) -> Any:
        """Render a single Markdown report bundling every agent's
        prompt, output, and exit code — useful for archiving or
        sharing the result of a multi-agent run."""
        run = manager.runs.get(run_id)
        if not run:
            raise HTTPException(404, "run not found")
        return {
            "title": run.title,
            "id": run.id,
            "markdown": _render_run_report(run),
        }

    @app.get("/api/runs/{run_id}/preview")
    async def preview_run_first_renderable(run_id: str) -> Any:
        """Find the first agent in this run whose output contains a
        renderable HTML/SVG fence and serve it. Useful when a 5-agent
        pipeline is open and the renderable artifact is buried in (e.g.)
        the `polish` agent at the end — the UI doesn't have to know
        which one, the backend picks the LAST agent with a hit so the
        most-refined version wins.
        """
        run = manager.runs.get(run_id)
        if not run:
            raise HTTPException(404, "run not found")

        import re as _re
        # Iterate in reverse — the last agent with a renderable artifact
        # is typically the polish/final step, which is what we want to
        # show.
        labels = list(run.agents.keys())
        for label in reversed(labels):
            agent_state = run.agents.get(label)
            if not agent_state:
                continue
            text = "\n".join(agent_state.log_lines)
            if (_re.search(r"```\s*html?\s*\n", text, _re.IGNORECASE)
                or _re.search(r"```\s*svg\s*\n", text, _re.IGNORECASE)
                or _re.search(r"<html[\s\S]*?</html>", text, _re.IGNORECASE)
                or _re.search(r"<svg[\s\S]*?</svg>", text, _re.IGNORECASE)):
                return await preview_run_artifact(run_id, label)
        raise HTTPException(404,
            "no renderable HTML/SVG found in any agent of this run")

    @app.get("/api/runs/{run_id}/preview/{label}")
    async def preview_run_artifact(run_id: str, label: str) -> Any:
        """Serve the first renderable HTML/SVG fence from an agent's
        output as a real top-level page. Used by the dashboard's
        "open in new tab" button so the design renders in a full
        browser window (with working scroll, scroll-snap, hover, etc.)
        instead of a sandboxed iframe inside the monitor panel.

        Detection priority mirrors the in-panel preview:
          1. `````html`` fenced block
          2. `````svg`` fenced block (wrapped in a centering page)
          3. raw ``<html>...</html>`` chunk in the buffer
          4. raw ``<svg>...</svg>`` chunk
        Returns 404 if nothing renderable is found, so the UI can show
        a clear message instead of a blank page.
        """
        run = manager.runs.get(run_id)
        if not run:
            raise HTTPException(404, "run not found")
        agent_state = run.agents.get(label)
        if not agent_state:
            raise HTTPException(404, f"agent {label!r} not found in run")
        text = "\n".join(agent_state.log_lines)

        import re as _re
        html_match = _re.search(r"```\s*html?\s*\n([\s\S]*?)```",
                                  text, _re.IGNORECASE)
        svg_match = _re.search(r"```\s*svg\s*\n([\s\S]*?)```",
                                 text, _re.IGNORECASE)

        if html_match:
            return HTMLResponse(html_match.group(1))
        if svg_match:
            page = (
                "<!doctype html><meta charset='utf-8'>"
                "<title>SVG preview</title>"
                "<style>html,body{margin:0;background:#fff;display:flex;"
                "align-items:center;justify-content:center;min-height:100vh;"
                "font-family:system-ui}svg{max-width:100%;max-height:100vh}"
                "</style>" + svg_match.group(1)
            )
            return HTMLResponse(page)

        raw_html = _re.search(r"<html[\s\S]*?</html>", text, _re.IGNORECASE)
        if raw_html:
            return HTMLResponse(raw_html.group(0))
        raw_svg = _re.search(r"<svg[\s\S]*?</svg>", text, _re.IGNORECASE)
        if raw_svg:
            page = (
                "<!doctype html><meta charset='utf-8'>"
                "<title>SVG preview</title>"
                "<style>html,body{margin:0;background:#fff;display:flex;"
                "align-items:center;justify-content:center;min-height:100vh;"
                "font-family:system-ui}svg{max-width:100%;max-height:100vh}"
                "</style>" + raw_svg.group(0)
            )
            return HTMLResponse(page)

        raise HTTPException(404,
            "no renderable HTML/SVG found in this agent's output")

    @app.post("/api/runs/{run_id}/export-project")
    async def export_project(run_id: str) -> Any:
        """v42.1 — scan a finished run's outputs for fenced code blocks
        whose first line is a comment with a file path, and write them
        as real files under outputs/<run_id>/project/.

        Closes the "Idea → finished" loop: agents output code blocks,
        we materialize them into a working project folder the user can
        cd into, run, and ship.

        Recognized path comments (case-insensitive, leading `// # /* <!--`):
          // path/to/file.ts      → JS / TS / Java / C / Go / Rust
          # path/to/file.py        → Python / shell / YAML / Make
          /* path/to/file.css */  → CSS / SCSS
          <!-- path/to/file.html -->  → HTML / XML / JSX-as-text

        Returns: {written: int, files: [...absolute paths...], skipped: int}
        """
        run = manager.runs.get(run_id)
        if not run:
            raise HTTPException(404, "run not found")

        # v44 — read each agent's full output from disk instead of
        # in-memory log_lines. Files are authoritative (full content),
        # log_lines may be partial after cancellation or filtered for
        # streaming. Process each file separately so a fenced block in
        # one agent's output never accidentally consumes a closing
        # fence from another agent's output.
        agent_texts: list[str] = []
        run_dir = RUNS_DIR / run.id
        for label in run.agents:
            out_md = run_dir / f"{label}.out.md"
            if out_md.exists():
                try:
                    agent_texts.append(out_md.read_text(encoding="utf-8", errors="replace"))
                except (OSError, UnicodeError):
                    pass

        # Find every ``` ... ``` fenced block
        # Then peel off a path-comment first line if present.
        import re
        fence_re = re.compile(
            r"```[a-zA-Z0-9_+\-]*\n(.*?)\n```",
            re.DOTALL,
        )
        # Match 1st-line path comments. Path can contain letters, digits,
        # underscores, dashes, dots, slashes, spaces. We trust the agent
        # gave us a sane relative path. Reject anything with ".." or
        # absolute paths for safety.
        path_re = re.compile(
            r"""
            ^
            (?:
              //\s*(?P<a>[\w./\- ]+\.[\w]+)        # // path/to.ext
              | \#\s*(?P<b>[\w./\- ]+\.[\w]+)       # # path/to.ext
              | /\*\s*(?P<c>[\w./\- ]+\.[\w]+)\s*\*/  # /* ... */
              | <!--\s*(?P<d>[\w./\- ]+\.[\w]+)\s*-->  # <!-- ... -->
            )
            \s*$
            """,
            re.VERBOSE,
        )

        project_dir = RUNS_DIR / run.id / "project"
        project_dir.mkdir(parents=True, exist_ok=True)

        written: list[str] = []
        skipped = 0
        seen_paths: set[str] = set()

        for full_text in agent_texts:
            for m in fence_re.finditer(full_text):
                body = m.group(1)
                if not body.strip():
                    continue
                first_nl = body.find("\n")
                if first_nl == -1:
                    continue
                first_line = body[:first_nl].strip()
                pm = path_re.match(first_line)
                if not pm:
                    skipped += 1
                    continue
                rel_path = (
                    pm.group("a") or pm.group("b")
                    or pm.group("c") or pm.group("d") or ""
                ).strip()
                # Safety: reject absolute, parent-traversal, or empty
                if (not rel_path
                        or rel_path.startswith("/")
                        or rel_path.startswith("\\")
                        or ".." in Path(rel_path).parts
                        or len(rel_path) > 240):
                    skipped += 1
                    continue
                # Last writer wins if multiple agents emit the same path
                content = body[first_nl + 1:]
                target = project_dir / rel_path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                key = str(target)
                if key not in seen_paths:
                    seen_paths.add(key)
                    written.append(key)

        return {
            "written": len(written),
            "files": written,
            "skipped": skipped,
            "project_dir": str(project_dir),
        }

    # v55 — Output hub: download the materialized project as a ZIP. Runs
    # export-project first if the project folder doesn't exist yet, so
    # one click closes the loop "agents finished → I have a working
    # codebase on disk". Returns the ZIP as a streaming response.
    @app.get("/api/runs/{run_id}/export-zip")
    async def export_zip(run_id: str) -> Any:
        run = manager.runs.get(run_id)
        if not run:
            raise HTTPException(404, "run not found")
        project_dir = RUNS_DIR / run.id / "project"
        if not project_dir.exists() or not any(project_dir.rglob("*")):
            # Auto-trigger export-project to materialize files first
            await export_project(run_id)
        if not project_dir.exists() or not any(project_dir.rglob("*")):
            raise HTTPException(
                404,
                "no exportable files — agents didn't emit fenced code "
                "blocks with file-path comments",
            )
        # Build ZIP in memory (small projects only — 99% of runs < 500 KB)
        import io as _io
        import zipfile as _zip
        buf = _io.BytesIO()
        with _zip.ZipFile(buf, "w", _zip.ZIP_DEFLATED) as zf:
            for path in project_dir.rglob("*"):
                if path.is_file():
                    arc = path.relative_to(project_dir).as_posix()
                    try:
                        zf.write(path, arc)
                    except OSError:
                        pass
        buf.seek(0)
        safe_title = "".join(
            c if c.isalnum() or c in "-_" else "-"
            for c in (run.title or run.id)
        )[:60].strip("-") or run.id
        filename = f"{safe_title}-{run.id[:8]}.zip"
        return Response(
            content=buf.getvalue(),
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(buf.getvalue())),
            },
        )

    @app.post("/api/runs/{run_id}/export-to-open-design")
    async def export_to_open_design(run_id: str) -> Any:
        """Drop a Markdown bundle of this run into Open Design's
        ``imports/`` folder so the user can pick it up there.
        Best-effort handoff — no daemon API call, just a shared file
        location both apps can see. Returns the absolute path so the
        UI can show it (and a hint to launch OD if it's not already
        running).

        OD path resolution order:
          1. ``CG_OPEN_DESIGN_DIR`` env override
          2. ``D:\\CLAUDE\\OPEN DESIGN\\open-design`` (the install path
             we know about from this user's machine)
          3. ``~/Open Design`` and ``~/open-design`` fallbacks
        """
        run = manager.runs.get(run_id)
        if not run:
            raise HTTPException(404, "run not found")

        candidates: list[Path] = []
        env_dir = os.environ.get("CG_OPEN_DESIGN_DIR")
        if env_dir:
            candidates.append(Path(env_dir))
        candidates.extend([
            Path(r"D:\CLAUDE\OPEN DESIGN\open-design"),
            Path.home() / "Open Design",
            Path.home() / "open-design",
        ])
        od_dir: Path | None = next(
            (c for c in candidates if c.exists() and c.is_dir()), None)
        if od_dir is None:
            raise HTTPException(404,
                "Open Design install not found. Set CG_OPEN_DESIGN_DIR "
                "env var or install OD at D:\\CLAUDE\\OPEN DESIGN\\open-design.")

        imports_dir = od_dir / "imports"
        imports_dir.mkdir(parents=True, exist_ok=True)
        safe_title = "".join(c if c.isalnum() or c in "-_" else "-"
                              for c in (run.title or "run").lower())[:60]
        out_path = imports_dir / f"cg-{run.id}-{safe_title}.md"
        out_path.write_text(_render_run_report(run), encoding="utf-8")
        return {
            "saved": True,
            "path": str(out_path),
            "open_design_dir": str(od_dir),
            "hint": ("Run launch.cmd in the Open Design folder (or click "
                      "the desktop shortcut) to see this file under imports/."),
        }

    # ---- v48 W0: Conductor — idea → custom team → live workflow -----------
    #
    # Three endpoints implement the two-phase Conductor flow:
    #   POST /api/conductor/brief    — Phase 1: streams a Markdown
    #                                   Project Brief from Opus 4.7.
    #                                   Returns a regular run_id; client
    #                                   reads it via /api/runs/<id>/stream.
    #   POST /api/conductor/compose  — Phase 2: takes the approved brief,
    #                                   asks Opus to emit a JSON workflow
    #                                   spec. Also a regular run_id.
    #   POST /api/conductor/launch   — Reads a Phase-2 run's output, parses
    #                                   + validates the JSON, then starts
    #                                   the actual workflow run as a normal
    #                                   manager.start_run. Returns the new
    #                                   run_id (the "real" one).
    # All three reuse the existing run engine, SSE streaming, timeout
    # watchdog, and on-disk output capture. No new infrastructure.

    def _allowed_models_for_conductor() -> list[str]:
        """Subset of AGENT_KINDS Conductor is allowed to assign.

        Excludes browser/sub-workflow/pilot pseudo-agents (those need
        special inputs Conductor can't realistically produce). Excludes
        third-party API agents that may not be configured (OpenRouter
        etc.) — keeps generated specs runnable on a fresh CG install
        with just Claude + Gemini OAuth.
        """
        good_prefixes = ("claude-", "gemini-")
        out = []
        for kind in AGENT_KINDS:
            if not isinstance(kind, str):
                continue
            if not kind.startswith(good_prefixes):
                continue
            # Skip preview / 3-pro etc. that have known capacity issues
            if "preview" in kind or kind.endswith("-3-pro"):
                continue
            out.append(kind)
        return out

    @app.post("/api/conductor/brief")
    async def conductor_brief(body: dict[str, Any], request: Request) -> Any:
        """Start Phase 1: Visionary writes a Markdown Project Brief."""
        idea = (body.get("idea") or "").strip()
        if not idea:
            raise HTTPException(400, "idea must be a non-empty string")
        constraints = (body.get("constraints") or "").strip()
        sys_prompt, user_prompt = build_phase1_prompt(idea, constraints)
        # Combine system + user into one stdin payload — claude --print
        # has no separate --system flag in CG's invocation; the prompt
        # leads with the role, then the actual task.
        full_prompt = f"{sys_prompt}\n\n---\n\n{user_prompt}"
        spec = [{
            "agent": "claude-opus-4-7",
            "label": "visionary",
            "role": "Visionary",
            "prompt": full_prompt,
            "streaming": True,
        }]
        # Forward the same secret headers as /api/runs
        secrets: dict[str, str] = {}
        header_to_env = {
            "x-cg-openrouter-key": "OPENROUTER_API_KEY",
            "x-cg-zhipu-key": "ZHIPU_API_KEY",
            "x-cg-anthropic-key": "ANTHROPIC_API_KEY",
            "x-cg-gemini-key": "GEMINI_API_KEY",
        }
        for header, env_name in header_to_env.items():
            v = request.headers.get(header)
            if v and v.strip():
                secrets[env_name] = v.strip()
        run = manager.start_run(
            title=f"Conductor brief: {idea[:60]}",
            spec=spec,
            secrets=secrets,
            variables={},
        )
        return {
            "phase": 1,
            "run_id": run.id,
            "title": run.title,
            "label": "visionary",
        }

    @app.post("/api/conductor/compose")
    async def conductor_compose(body: dict[str, Any], request: Request) -> Any:
        """Start Phase 2: Conductor emits a fenced JSON workflow spec."""
        brief = (body.get("brief") or "").strip()
        if not brief:
            raise HTTPException(400, "brief must be a non-empty string")
        allowed = _allowed_models_for_conductor()
        sys_prompt, _ = build_phase2_prompt(brief, allowed)
        spec = [{
            "agent": "claude-opus-4-7",
            "label": "composer",
            "role": "Architect",
            "prompt": sys_prompt,
            "streaming": True,
        }]
        secrets: dict[str, str] = {}
        for header, env_name in {
            "x-cg-anthropic-key": "ANTHROPIC_API_KEY",
        }.items():
            v = request.headers.get(header)
            if v and v.strip():
                secrets[env_name] = v.strip()
        run = manager.start_run(
            title="Conductor compose: workflow JSON",
            spec=spec,
            secrets=secrets,
            variables={},
        )
        return {
            "phase": 2,
            "run_id": run.id,
            "title": run.title,
            "label": "composer",
            "allowed_models": allowed,
        }

    @app.post("/api/conductor/launch")
    async def conductor_launch(body: dict[str, Any], request: Request) -> Any:
        """Parse + validate a Phase-2 output, then launch the real run.

        Body:
          - compose_run_id: id of the Phase 2 run whose output is the JSON
          - variables: optional dict of ${VAR} overrides for the launched run
          - title: optional title override
          - auto_mode: bool — currently informational; kept for symmetry
            with W0.3 (run engine has no approval gates yet anyway, so
            today every Conductor run is effectively auto-mode end-to-end
            until W3 ships explicit gates).
        """
        compose_run_id = body.get("compose_run_id") or ""
        if not compose_run_id:
            raise HTTPException(400, "compose_run_id is required")
        compose_run = manager.runs.get(compose_run_id)
        if not compose_run:
            raise HTTPException(404, f"compose run {compose_run_id!r} not found")
        composer = compose_run.agents.get("composer")
        if not composer:
            raise HTTPException(400, "compose run has no 'composer' agent")
        # Read the composer's full output. Prefer on-disk output (v44 path)
        # over in-memory log_lines so we get the post-cancel-safe view.
        composer_text = ""
        try:
            run_dir = RUNS_DIR / compose_run_id
            for candidate in (run_dir / "composer.out.md", run_dir / "composer.txt"):
                if candidate.exists():
                    composer_text = candidate.read_text(encoding="utf-8", errors="replace")
                    break
        except Exception:
            pass
        if not composer_text:
            composer_text = "\n".join(composer.log_lines)
        if not composer_text.strip():
            raise HTTPException(
                400,
                "compose run has no output yet — wait for status=done before launching",
            )

        json_str = extract_json_block(composer_text)
        if not json_str:
            raise HTTPException(
                422,
                "could not find a JSON block in the composer output",
            )

        allowed = set(_allowed_models_for_conductor())
        result = validate_workflow_spec(json_str, allowed)
        if not result.ok or not result.spec:
            raise HTTPException(
                422,
                {"error": "workflow validation failed",
                 "details": result.errors},
            )

        # Apply user variable overrides on top of the generated defaults
        merged_vars = dict(result.spec.get("variables") or {})
        merged_vars.update(body.get("variables") or {})

        # Forward secret headers to the launched run
        secrets: dict[str, str] = {}
        header_to_env = {
            "x-cg-openrouter-key": "OPENROUTER_API_KEY",
            "x-cg-zhipu-key": "ZHIPU_API_KEY",
            "x-cg-anthropic-key": "ANTHROPIC_API_KEY",
            "x-cg-gemini-key": "GEMINI_API_KEY",
            "x-cg-project-root": "CG_PROJECT_ROOT",
        }
        for header, env_name in header_to_env.items():
            v = request.headers.get(header)
            if v and v.strip():
                secrets[env_name] = v.strip()

        title = body.get("title") or result.spec.get("title") or "Conductor run"
        # v47.1: iterate_with / max_rounds are now honored by the engine.
        # Pass them through verbatim — start_run validates them.

        run = manager.start_run(
            title=title,
            spec=result.spec["spec"],
            secrets=secrets,
            variables=merged_vars,
        )
        warnings: list[str] = []
        if any(s.get("iterate_with") for s in result.spec["spec"]):
            warnings.append(
                "Conductor scheduled refinement loops (iterate_with). "
                "Rounds 2+ will fire after round 1 completes."
            )
        return {
            "phase": 3,
            "run_id": run.id,
            "title": run.title,
            "agents": [s.get("label") for s in result.spec["spec"]],
            "auto_mode": bool(body.get("auto_mode")),
            "warnings": warnings,
        }

    @app.get("/api/conductor/roles")
    async def conductor_roles() -> Any:
        """Expose the canonical roles + default models to the UI."""
        return {
            "roles": [
                {"name": name, **meta}
                for name, meta in CANONICAL_ROLES.items()
            ],
            "allowed_models": _allowed_models_for_conductor(),
        }

    # ---- workflows on disk -------------------------------------------------

    @app.get("/api/workflows")
    async def list_workflows() -> Any:
        return {"workflows": _list_workflow_files()}

    @app.get("/api/workflows/{name}")
    async def get_workflow(name: str) -> Any:
        path = _workflow_path(name)
        if not path.exists():
            raise HTTPException(404, "workflow not found")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise HTTPException(500, f"invalid workflow JSON: {exc}")
        return data

    @app.put("/api/workflows/{name}")
    async def save_workflow(name: str, body: dict[str, Any]) -> Any:
        path = _workflow_path(name)
        if not isinstance(body, dict):
            raise HTTPException(400, "body must be a JSON object")
        if "spec" not in body or not isinstance(body["spec"], list):
            raise HTTPException(400, "body.spec is required and must be an array")
        body.setdefault("title", name)
        body.setdefault("savedAt", time.time())
        path.write_text(
            json.dumps(body, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return {"name": _name_of(path), "saved": True}

    @app.delete("/api/workflows/{name}")
    async def delete_workflow(name: str) -> Any:
        path = _workflow_path(name)
        if not path.exists():
            raise HTTPException(404, "workflow not found")
        path.unlink()
        return {"name": name, "deleted": True}

    # ---- schedules (cron-style periodic runs) -----------------------------

    @app.get("/api/schedules")
    async def list_schedules() -> Any:
        return {"schedules": _load_schedules()}

    @app.put("/api/schedules")
    async def save_schedules(body: dict[str, Any]) -> Any:
        items = body.get("schedules")
        if not isinstance(items, list):
            raise HTTPException(400, "body.schedules must be an array")
        for s in items:
            if not isinstance(s, dict):
                raise HTTPException(400, "each schedule must be an object")
            if not s.get("workflow"):
                raise HTTPException(400, "schedule.workflow is required")
            interval = s.get("interval_minutes")
            if not isinstance(interval, int) or interval < 1:
                raise HTTPException(400, "schedule.interval_minutes must be a positive integer")
            s["enabled"] = bool(s.get("enabled", True))
            s.setdefault("variables", {})
        SCHEDULES_PATH.write_text(
            json.dumps(items, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return {"saved": len(items)}

    # ---- Browser auth wizard (headed login → save storage_state) --------

    @app.get("/api/browser-auth")
    async def list_browser_auths() -> Any:
        """List saved browser_auth/<slug>.json files."""
        BROWSER_AUTH_DIR.mkdir(parents=True, exist_ok=True)
        out = []
        for p in sorted(BROWSER_AUTH_DIR.glob("*.json")):
            stat = p.stat()
            out.append({
                "slug": p.stem,
                "size": stat.st_size,
                "modified": time.strftime("%Y-%m-%dT%H:%M:%S",
                                            time.localtime(stat.st_mtime)),
            })
        return {"auths": out, "active": _auth_session.get("active")}

    @app.post("/api/browser-auth/start")
    async def start_browser_auth(body: dict[str, Any]) -> Any:
        """Spawn a headed Chromium for user-driven login. The browser
        stays open until POST /api/browser-auth/save (success) or
        /api/browser-auth/cancel (abort)."""
        slug = body.get("slug") or ""
        url = body.get("url") or "about:blank"
        if not _re.match(r"^[a-zA-Z0-9._-]+$", slug):
            raise HTTPException(400, "slug must be alphanumeric/dash/dot/underscore")

        if _auth_session.get("active"):
            raise HTTPException(409, "another auth session is in progress; "
                                       "save or cancel it first")

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise HTTPException(500,
                "playwright not installed. pip install playwright && playwright install chromium")

        # Run the auth session in a background thread so this endpoint
        # can return immediately. The thread keeps the browser context
        # alive and waits for save/cancel signals.
        BROWSER_AUTH_DIR.mkdir(parents=True, exist_ok=True)

        ready_event = threading.Event()
        save_event = threading.Event()
        cancel_event = threading.Event()
        result_holder: dict[str, Any] = {}

        def _run() -> None:
            try:
                from playwright.sync_api import sync_playwright as _sp
                with _sp() as p:
                    browser = p.chromium.launch(headless=False)
                    ctx = browser.new_context()
                    page = ctx.new_page()
                    page.goto(url, timeout=60000)
                    ready_event.set()

                    # Spin until either save or cancel fires
                    while not save_event.is_set() and not cancel_event.is_set():
                        time.sleep(0.5)

                    if save_event.is_set():
                        out_path = BROWSER_AUTH_DIR / f"{slug}.json"
                        ctx.storage_state(path=str(out_path))
                        result_holder["path"] = str(out_path)
                        result_holder["status"] = "saved"
                    else:
                        result_holder["status"] = "cancelled"

                    browser.close()
            except Exception as exc:
                result_holder["status"] = "error"
                result_holder["error"] = str(exc)
                ready_event.set()
            finally:
                _auth_session["active"] = None
                _auth_session["save_event"] = None
                _auth_session["cancel_event"] = None
                _auth_session["result"] = result_holder

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        # Wait briefly for browser to spawn
        ready_event.wait(timeout=15)

        _auth_session["active"] = {
            "slug": slug, "url": url,
            "started_at": _iso_now(),
        }
        _auth_session["save_event"] = save_event
        _auth_session["cancel_event"] = cancel_event
        _auth_session["thread"] = thread

        return {"slug": slug, "url": url, "status": "started",
                "instructions": ("A Chromium window has opened. Sign in to "
                                 "the target site there, complete any 2FA, "
                                 "then click 'Save & Close' here in the "
                                 "dashboard to persist the storage_state.")}

    @app.post("/api/browser-auth/save")
    async def save_browser_auth() -> Any:
        save_event = _auth_session.get("save_event")
        if save_event is None:
            raise HTTPException(409, "no auth session in progress")
        save_event.set()
        # Wait briefly for the thread to finish saving
        thread = _auth_session.get("thread")
        if thread is not None:
            thread.join(timeout=10)
        result = _auth_session.get("result", {})
        return {"status": result.get("status", "unknown"),
                "path": result.get("path")}

    @app.post("/api/browser-auth/cancel")
    async def cancel_browser_auth() -> Any:
        cancel_event = _auth_session.get("cancel_event")
        if cancel_event is None:
            return {"status": "no-op"}
        cancel_event.set()
        thread = _auth_session.get("thread")
        if thread is not None:
            thread.join(timeout=10)
        return {"status": "cancelled"}

    @app.delete("/api/browser-auth/{slug}")
    async def delete_browser_auth(slug: str) -> Any:
        if not _re.match(r"^[a-zA-Z0-9._-]+$", slug):
            raise HTTPException(400, "invalid slug")
        path = BROWSER_AUTH_DIR / f"{slug}.json"
        if not path.exists():
            raise HTTPException(404, "auth state not found")
        path.unlink()
        return {"slug": slug, "deleted": True}

    # ---- Cloudflare Tunnel (phone dispatch enabler) ----------------------

    @app.get("/api/tunnel/status")
    async def tunnel_status() -> Any:
        # Hide internal _proc reference from public API
        return {k: v for k, v in _tunnel_state.items() if not k.startswith("_")}

    @app.post("/api/tunnel/start")
    async def tunnel_start() -> Any:
        if _tunnel_state.get("running"):
            return _tunnel_state.copy()
        path = _ensure_cloudflared()
        if not path:
            raise HTTPException(500,
                "cloudflared not found and auto-download failed. "
                "Install manually: https://github.com/cloudflare/cloudflared/releases")
        port = _tunnel_state.get("port", 8765)
        url, proc = _spawn_tunnel(path, port)
        _tunnel_state.update({
            "running": True,
            "url": url,
            "started_at": _iso_now(),
            "pid": proc.pid,
            "_proc": proc,
            "binary": path,
        })
        return {k: v for k, v in _tunnel_state.items() if not k.startswith("_")}

    @app.post("/api/tunnel/stop")
    async def tunnel_stop() -> Any:
        proc = _tunnel_state.get("_proc")
        if proc is not None:
            try:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
            except Exception:
                pass
        _tunnel_state.update({
            "running": False, "url": None, "_proc": None,
            "started_at": None, "pid": None,
        })
        return _tunnel_state.copy()

    # ---- Phone dispatch (mobile-friendly entry point) --------------------

    @app.post("/api/phone-dispatch")
    async def phone_dispatch(body: dict[str, Any], request: Request) -> Any:
        """Mobile-friendly entry point. Body: {message: str, agent?: str,
        workflow?: str}. If workflow is specified, fires that saved
        workflow with body.message overlayed as ${MESSAGE} variable.
        Otherwise dispatches a single agent (default: gemini-flash) with
        the message as the prompt.
        """
        message = body.get("message") or body.get("prompt") or body.get("text")
        if not message:
            raise HTTPException(400, "body.message is required")

        # Per-run secrets from headers (so phone can pass GEMINI_API_KEY)
        secrets: dict[str, str] = {}
        for header, env_name in [
            ("x-cg-openrouter-key", "OPENROUTER_API_KEY"),
            ("x-cg-zhipu-key", "ZHIPU_API_KEY"),
            ("x-cg-anthropic-key", "ANTHROPIC_API_KEY"),
            ("x-cg-gemini-key", "GEMINI_API_KEY"),
        ]:
            v = request.headers.get(header)
            if v and v.strip():
                secrets[env_name] = v.strip()

        workflow = body.get("workflow")
        if workflow:
            path = _workflow_path(workflow)
            if not path.exists():
                raise HTTPException(404, f"workflow {workflow!r} not found")
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise HTTPException(500, f"workflow JSON broken: {exc}")
            spec = data.get("spec") or []
            variables = dict(data.get("variables", {}) or {})
            variables["MESSAGE"] = message
            variables.update(body.get("variables", {}) or {})
            run = manager.start_run(
                f"phone: {workflow}", spec, secrets=secrets, variables=variables)
            return {"id": run.id, "title": run.title, "workflow": workflow,
                    "tunnel": _tunnel_state.get("url")}

        agent = body.get("agent") or "gemini-flash"
        run = manager.start_run(
            f"phone: {message[:60]}",
            [{"agent": agent, "label": "reply", "prompt": message}],
            secrets=secrets,
        )
        return {"id": run.id, "title": run.title, "agent": agent,
                "tunnel": _tunnel_state.get("url")}

    # ---- Run-finished notifications --------------------------------------

    @app.get("/api/notifications")
    async def get_notifications() -> Any:
        return _load_notifications()

    @app.put("/api/notifications")
    async def save_notifications_ep(body: dict[str, Any]) -> Any:
        config = body.get("config") or {}
        webhook_url = config.get("webhook_url", "").strip()
        webhook_kind = config.get("kind", "ntfy")
        if webhook_kind not in {"ntfy", "discord", "slack", "generic"}:
            raise HTTPException(400, f"unknown kind {webhook_kind!r}")
        on_complete = bool(config.get("on_complete", True))
        on_failed = bool(config.get("on_failed", True))
        out = {
            "webhook_url": webhook_url,
            "kind": webhook_kind,
            "on_complete": on_complete,
            "on_failed": on_failed,
        }
        NOTIFICATIONS_PATH.write_text(
            json.dumps(out, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return out

    @app.post("/api/triggers/{workflow_name}")
    async def trigger_workflow(workflow_name: str, body: dict[str, Any] | None = None) -> Any:
        """Webhook trigger — POST here from any external service to
        run a saved workflow. Optional body.variables overlay
        per-trigger ${VAR} substitution; useful when GitHub etc.
        forwards payload (issue title, sender, etc.) to be injected
        into prompts."""
        path = _workflow_path(workflow_name)
        if not path.exists():
            raise HTTPException(404, f"workflow {workflow_name!r} not found")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise HTTPException(500, f"workflow JSON broken: {exc}")
        spec = data.get("spec") or []
        if not spec:
            raise HTTPException(500, "workflow has empty spec")
        title = (body or {}).get("title") or f"trigger: {data.get('title', workflow_name)}"
        # Merge variables: workflow defaults < body overlay
        variables: dict[str, str] = {}
        variables.update(data.get("variables", {}) or {})
        variables.update((body or {}).get("variables", {}) or {})
        run = manager.start_run(title, spec, variables=variables)
        return {"id": run.id, "title": run.title, "workflow": workflow_name,
                "triggered_at": _iso_now()}

    # ---- notes (Obsidian-inspired knowledge base in D:\CG\notes\) ---------

    @app.get("/api/notes")
    async def list_notes() -> Any:
        """List every .md note with metadata for the sidebar."""
        return {"notes": _list_notes()}

    @app.get("/api/notes/{name}")
    async def get_note(name: str) -> Any:
        path = _note_path(name)
        if not path.exists():
            raise HTTPException(404, "note not found")
        return _parse_note(path)

    @app.put("/api/notes/{name}")
    async def save_note(name: str, body: dict[str, Any]) -> Any:
        if "content" not in body or not isinstance(body["content"], str):
            raise HTTPException(400, "body.content must be a string")
        title = body.get("title") or _safe_note_name(name)
        tags = body.get("tags") or []
        if not isinstance(tags, list):
            tags = []
        path = _note_path(name)
        existing = _parse_note(path) if path.exists() else None
        now = _iso_now()
        created = (existing or {}).get("created") or now
        frontmatter = {
            "title": title,
            "tags": tags,
            "created": created,
            "updated": now,
        }
        path.write_text(_render_note(frontmatter, body["content"]),
                          encoding="utf-8")
        return _parse_note(path)

    @app.delete("/api/notes/{name}")
    async def delete_note(name: str) -> Any:
        path = _note_path(name)
        if not path.exists():
            raise HTTPException(404, "note not found")
        path.unlink()
        return {"name": name, "deleted": True}

    @app.get("/api/notes/{name}/backlinks")
    async def note_backlinks(name: str) -> Any:
        target = _safe_note_name(name)
        return {"name": target, "backlinks": _find_backlinks(target)}

    @app.get("/api/notes-search")
    async def notes_search(q: str = "") -> Any:
        if not q.strip():
            return {"results": []}
        return {"results": _search_notes(q.strip())}

    @app.post("/api/notes/from-run")
    async def note_from_run(body: dict[str, Any]) -> Any:
        """Save a CG run as a Markdown note for later reference."""
        run_id = body.get("run_id")
        run = manager.runs.get(run_id) if run_id else None
        if not run:
            raise HTTPException(404, "run not found")
        slug = _safe_note_name(f"run-{run.id}-{run.title}")
        body_md = _render_run_report(run)
        frontmatter = {
            "title": f"Run: {run.title}",
            "tags": ["run"] + [a.agent for a in run.agents.values()],
            "created": _iso_now(),
            "updated": _iso_now(),
            "run_id": run.id,
        }
        path = _note_path(slug)
        path.write_text(_render_note(frontmatter, body_md), encoding="utf-8")
        return _parse_note(path)

    # ---- file tree + editor (read/write within CG_PROJECT_ROOT) -----------

    @app.get("/api/files/tree")
    async def files_tree(path: str = "") -> Any:
        """List files & directories under the project root. Used by the
        inline editor to render a tree on the left of the editor pane.
        Returns a single level (not recursive); the UI lazy-loads
        subdirs on click.
        """
        root = ROOT_PROJECT_FOR_FILES()
        target = (root / path).resolve() if path else root
        try:
            target.relative_to(root)
        except ValueError:
            raise HTTPException(403, "path escapes project root")
        if not target.exists():
            raise HTTPException(404, "not found")
        if not target.is_dir():
            raise HTTPException(400, "not a directory")
        entries = []
        for child in sorted(target.iterdir(),
                              key=lambda p: (not p.is_dir(), p.name.lower())):
            # Skip noisy / private dirs by default
            if child.name in {".git", "__pycache__", "node_modules",
                                ".pytest_cache", ".venv", ".vscode"}:
                continue
            rel = str(child.relative_to(root)).replace("\\", "/")
            entries.append({
                "name": child.name,
                "path": rel,
                "is_dir": child.is_dir(),
                "size": child.stat().st_size if child.is_file() else None,
            })
        return {
            "root": str(root),
            "path": str(target.relative_to(root)).replace("\\", "/") if target != root else "",
            "entries": entries,
        }

    @app.get("/api/files/content")
    async def file_content(path: str) -> Any:
        """Read a UTF-8 text file from within the project root."""
        root = ROOT_PROJECT_FOR_FILES()
        p = (root / path).resolve()
        try:
            p.relative_to(root)
        except ValueError:
            raise HTTPException(403, "path escapes project root")
        if not p.exists() or not p.is_file():
            raise HTTPException(404, "not found")
        size = p.stat().st_size
        if size > 2_000_000:
            raise HTTPException(413, f"file too large ({size} bytes)")
        try:
            content = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raise HTTPException(415, "not a UTF-8 text file")
        return {"path": path, "content": content, "size": size}

    @app.put("/api/files/content")
    async def file_save(body: dict[str, Any]) -> Any:
        """Write a UTF-8 text file within the project root.

        Editing only — must already exist (use the same UI gesture as
        opening). Creating new files via this endpoint is a separate
        future feature (would need explicit confirmation UI).
        """
        path = body.get("path") or ""
        content = body.get("content")
        if content is None or not isinstance(content, str):
            raise HTTPException(400, "body.content must be a string")
        root = ROOT_PROJECT_FOR_FILES()
        p = (root / path).resolve()
        try:
            p.relative_to(root)
        except ValueError:
            raise HTTPException(403, "path escapes project root")
        if not p.exists() or not p.is_file():
            raise HTTPException(404, "not found (this endpoint edits, not creates)")
        # Atomic write via temp + replace, so a crashed write doesn't
        # leave a half-written source file
        tmp = p.with_suffix(p.suffix + ".cg-tmp")
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(p)
        return {"path": path, "size": len(content.encode("utf-8"))}

    @app.post("/api/workflows/import")
    async def import_workflow(body: dict[str, Any]) -> Any:
        """Import a workflow JSON either from inline body or by reading
        a path on disk. Body shape::

            { "json": { "title": "...", "spec": [...] } }
            or
            { "path": "absolute/or/cg-relative/path/to/workflow.json" }

        On success, persists the workflow into ``D:\\CG\\workflows\\``
        and returns the saved name plus the parsed spec so the frontend
        can populate the designer immediately.
        """
        if "json" in body:
            data = body["json"]
        elif "path" in body:
            p = Path(body["path"])
            if not p.is_absolute():
                p = (ROOT / p).resolve()
            if not p.exists():
                raise HTTPException(404, f"file not found: {p}")
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise HTTPException(400, f"not valid JSON: {exc}")
        else:
            raise HTTPException(400, "body must contain either 'json' or 'path'")

        if not isinstance(data, dict):
            raise HTTPException(400, "imported workflow must be a JSON object")
        if not isinstance(data.get("spec"), list) or not data["spec"]:
            raise HTTPException(400, "workflow.spec must be a non-empty array")
        title = data.get("title") or "imported"
        save_name = _safe_workflow_name(title)
        save_path = _workflow_path(save_name)
        data.setdefault("title", title)
        data["importedAt"] = time.time()
        save_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return {"name": save_name, "title": title, "spec": data["spec"]}

    @app.get("/api/runs/{run_id}/stream")
    async def stream(run_id: str, request: Request) -> Any:
        run = manager.runs.get(run_id)
        if not run:
            raise HTTPException(404, "run not found")
        # subscribe to ALL agents in this run
        queues = {label: manager.subscribe(run_id, label) for label in run.agents}

        async def event_generator():
            # First, replay current state so newly-connecting clients see history
            for label, agent in run.agents.items():
                yield {"event": "status", "data": json.dumps({
                    "label": label, "status": agent.status,
                    "exit_code": agent.exit_code,
                })}
                if agent.log_lines:
                    yield {"event": "snapshot", "data": json.dumps({
                        "label": label, "log": "\n".join(agent.log_lines),
                    })}
            try:
                while True:
                    if await request.is_disconnected():
                        break
                    # Round-robin over queues, non-blocking-ish
                    delivered = False
                    for label, q in queues.items():
                        try:
                            ev = q.get_nowait()
                            delivered = True
                            yield {
                                "event": ev["event"],
                                "data": json.dumps(ev["data"]),
                            }
                        except asyncio.QueueEmpty:
                            pass
                    if not delivered:
                        await asyncio.sleep(0.1)
                    if run.finished:
                        # Drain
                        for label, q in queues.items():
                            while not q.empty():
                                ev = q.get_nowait()
                                yield {"event": ev["event"], "data": json.dumps(ev["data"])}
                        yield {"event": "done", "data": json.dumps({"id": run_id})}
                        break
            finally:
                for label in queues:
                    manager.unsubscribe(run_id, label)

        return EventSourceResponse(event_generator())

    return app


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

app = create_app()


def main() -> None:
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="CG Dashboard server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-open", action="store_true",
                         help="do not open browser automatically")
    parser.add_argument("--workflow", default=None,
                         help="auto-load this workflow on startup. Pass a "
                              "name (looks up D:\\CG\\workflows\\<name>.json) "
                              "or an absolute path to any .json file.")
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}"
    if args.workflow:
        # The dashboard frontend reads ?workflow=<name> from the URL
        # at boot time and POSTs to /api/workflows/import, which both
        # persists it and returns the spec for the designer.
        url = f"{url}/?workflow={args.workflow}"

    if not args.no_open:
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception:
            pass
    print(f"\n  CG Dashboard at {url}\n")
    uvicorn.run("dashboard:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
