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
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "src" / "dashboard_static"
RUNS_DIR = ROOT / "outputs" / "dashboard-runs"
RUNS_DIR.mkdir(parents=True, exist_ok=True)
INDEX_PATH = ROOT / "tasks" / "_dashboard_runs.json"


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
    "gemini-flash": {
        "label": "Gemini Flash",
        "family": "gemini",
        "summary": "fastest Gemini — quick checks, drafts",
        "command": [_resolve_executable("gemini"), "--skip-trust",
                     "-m", "flash", "-p"],
        "stdin_prompt": False,
        "env": {"GOOGLE_GENAI_USE_GCA": "true"},
    },
    "gemini-pro": {
        "label": "Gemini Pro",
        "family": "gemini",
        "summary": "default Gemini — balanced quality",
        "command": [_resolve_executable("gemini"), "--skip-trust",
                     "-m", "pro", "-p"],
        "stdin_prompt": False,
        "env": {"GOOGLE_GENAI_USE_GCA": "true"},
    },
    "gemini-3-pro": {
        "label": "Gemini 3 Pro (preview)",
        "family": "gemini",
        "summary": "latest Gemini 3 Pro — slow but strongest",
        "command": [_resolve_executable("gemini"), "--skip-trust",
                     "-m", "gemini-3-pro-preview", "-p"],
        "stdin_prompt": False,
        "env": {"GOOGLE_GENAI_USE_GCA": "true"},
    },
}


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
        }


@dataclass
class RunState:
    id: str
    title: str
    created: float
    spec: list[dict[str, Any]]
    agents: dict[str, AgentRunState] = field(default_factory=dict)
    finished: bool = False

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

    def start_run(self, title: str, spec: list[dict[str, Any]]) -> RunState:
        run_id = uuid.uuid4().hex[:12]
        run = RunState(
            id=run_id,
            title=title or f"run-{run_id}",
            created=time.time(),
            spec=spec,
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
        # Build state
        for i, item in enumerate(spec):
            label = item.get("label") or f"agent-{i+1}"
            run.agents[label] = AgentRunState(
                label=label,
                agent=item["agent"],
                depends_on=list(item.get("depends_on", []) or []),
                status="queued" if not item.get("depends_on") else "waiting",
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
        threading.Thread(target=self._watch_run, args=(run,), daemon=True).start()
        return run

    def _wait_for_deps(self, run: RunState, agent_state: AgentRunState) -> bool:
        """Block until every dependency is done. Returns False if any dep
        failed or was cancelled (caller should mark this agent failed too)."""
        if not agent_state.depends_on:
            return True
        agent_state.status = "waiting"
        self._emit(run.id, agent_state.label, {"event": "status", "data": {
            "label": agent_state.label, "status": "waiting"}})
        while True:
            statuses = [run.agents[d].status for d in agent_state.depends_on
                         if d in run.agents]
            if any(s in {"failed", "cancelled"} for s in statuses):
                return False
            if all(s == "done" for s in statuses):
                return True
            time.sleep(0.5)

    def _substitute_prompt(self, run: RunState, prompt: str,
                            depends_on: list[str]) -> str:
        """Replace ``{{label}}`` placeholders with that dependency's output."""
        if not depends_on:
            return prompt
        result = prompt
        for dep in depends_on:
            agent = run.agents.get(dep)
            if agent is None:
                continue
            output = "\n".join(agent.log_lines)
            placeholder = "{{" + dep + "}}"
            result = result.replace(placeholder, output)
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
        self._run_one(run, label, agent, rendered)

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

        cmd = list(cfg["command"])
        if cfg["stdin_prompt"]:
            stdin_input: str | None = prompt
        else:
            cmd = cmd + [prompt]
            stdin_input = None

        env = os.environ.copy()
        env.update(cfg.get("env", {}))

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
        def _drain_stderr():
            assert proc.stderr is not None
            for line in proc.stderr:
                agent_state.stderr_lines.append(line.rstrip("\n"))
        stderr_thread = threading.Thread(target=_drain_stderr, daemon=True)
        stderr_thread.start()

        assert proc.stdout is not None
        for line in proc.stdout:
            line_clean = line.rstrip("\n")
            agent_state.log_lines.append(line_clean)
            out_fp.write(line)
            self._emit(run.id, label, {"event": "log", "data": {
                "label": label, "line": line_clean}})

        proc.wait()
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

    def _watch_run(self, run: RunState) -> None:
        while True:
            time.sleep(0.5)
            if all(a.status in {"done", "failed"} for a in run.agents.values()):
                break
        run.finished = True
        self._persist_index()
        self._emit_run(run.id, {"event": "run-finished", "data": {"id": run.id}})

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
                "agents": [
                    {"label": a.label, "agent": a.agent, "status": a.status,
                     "exit_code": a.exit_code}
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


# ---------------------------------------------------------------------------
# Presets — bundled workflows
# ---------------------------------------------------------------------------


PRESETS: list[dict[str, Any]] = [
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
        "title": "Design → Implement → Critique (Gemini Pro → Opus 4.7 → Gemini Pro)",
        "description": "Real sequential pipeline. Gemini Pro writes the spec, "
                        "Opus 4.7 implements it (1M context — handles big specs), "
                        "Gemini Pro reviews both. Uses depends_on + {{label}} substitution.",
        "spec": [
            {
                "agent": "gemini-pro", "label": "design",
                "prompt": "DO NOT ask questions. DO NOT propose a plan. Output a precise Markdown "
                          "spec for a Python function `fizzbuzz(n: int) -> list[str]` that returns "
                          "the first n FizzBuzz values. Cover sections: Signature, Inputs, "
                          "Outputs, Edge cases (n<=0), Three concrete example outputs. Output "
                          "Markdown only."
            },
            {
                "agent": "claude-opus-4-7", "label": "implement",
                "depends_on": ["design"],
                "prompt": "Implement the following spec exactly. Output ONLY a fenced "
                          "```python code block, nothing before or after.\n\n"
                          "# Spec\n\n{{design}}"
            },
            {
                "agent": "gemini-pro", "label": "critique",
                "depends_on": ["design", "implement"],
                "prompt": "Critically review this implementation against its spec. List bugs, "
                          "missing edge cases, and concrete improvements as a Markdown bullet "
                          "list. Be terse. If the implementation is correct, say so in one line.\n\n"
                          "## Spec\n{{design}}\n\n## Implementation\n{{implement}}"
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
]


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    from contextlib import asynccontextmanager

    manager = RunManager()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        manager.bind_loop(asyncio.get_running_loop())
        yield

    app = FastAPI(title="CG Dashboard", version="0.1", lifespan=lifespan)

    @app.get("/", include_in_schema=False)
    async def root() -> Any:
        index = STATIC_DIR / "index.html"
        if not index.exists():
            return JSONResponse({"error": "frontend not built", "looked_for": str(index)},
                                status_code=500)
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

    @app.get("/api/presets")
    async def get_presets() -> Any:
        return {"presets": PRESETS}

    @app.post("/api/runs")
    async def post_run(body: dict[str, Any]) -> Any:
        title = body.get("title") or "untitled"
        spec = body.get("spec") or []
        if not isinstance(spec, list) or not spec:
            raise HTTPException(400, "spec must be a non-empty array")
        run = manager.start_run(title, spec)
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

    @app.get("/api/runs/{run_id}/output/{label}")
    async def get_output(run_id: str, label: str) -> Any:
        run = manager.runs.get(run_id)
        if not run:
            raise HTTPException(404, "run not found")
        if label not in run.agents:
            raise HTTPException(404, "label not found")
        return {"label": label, "log": "\n".join(run.agents[label].log_lines)}

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
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}"
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
