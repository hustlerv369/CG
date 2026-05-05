"""CG — minimal multi-agent orchestrator on subscriptions.

Two AI workers, both invoked as headless subprocesses on the user's
existing subscriptions (no API keys needed):

- ``claude --print``  — Claude Code headless, uses Claude Pro OAuth
- ``gemini -p``       — Google Gemini CLI, uses Google account OAuth
                        (set GOOGLE_GENAI_USE_GCA=true before first call)

The orchestrator:

1. Reads a task spec (Markdown with optional frontmatter or just text).
2. Sends it to one or both agents in parallel as subprocesses.
3. Captures stdout/stderr from each.
4. Writes per-agent outputs into ``outputs/<task-id>/<agent>.md``.
5. Optionally lets the human (or Claude) merge the outputs into a final
   deliverable.

Design principle: agents are stateless one-shot text-in / text-out
functions. No inbox, no heartbeats, no claims, no workspace memory.
Everything the agent needs is in the prompt; nothing it produces leaks
across invocations.

Usage::

    python cg.py run <task-id> --to claude
    python cg.py run <task-id> --to gemini
    python cg.py run <task-id> --to both
    python cg.py task add "<title>" --spec <path-or-stdin>
    python cg.py task list
    python cg.py task show <task-id>
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import json
import os
import re
import subprocess
import sys
import textwrap
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASKS_DIR = ROOT / "tasks"
OUTPUTS_DIR = ROOT / "outputs"
DB_PATH = ROOT / "tasks" / "_index.json"

DEFAULT_TIMEOUT = int(os.environ.get("CG_AGENT_TIMEOUT", "300"))  # seconds


# ---------------------------------------------------------------------------
# Task model
# ---------------------------------------------------------------------------


@dataclass
class Task:
    id: str
    title: str
    spec: str
    created_at: str
    runs: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _next_task_id() -> str:
    if not DB_PATH.exists():
        return "task-001"
    db = json.loads(DB_PATH.read_text(encoding="utf-8"))
    nums = [int(re.match(r"task-(\d+)", t["id"]).group(1)) for t in db.get("tasks", [])
            if re.match(r"task-(\d+)", t["id"])]
    return f"task-{(max(nums) if nums else 0) + 1:03d}"


def _load_db() -> dict:
    if not DB_PATH.exists():
        return {"tasks": []}
    return json.loads(DB_PATH.read_text(encoding="utf-8"))


def _save_db(db: dict) -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    DB_PATH.write_text(json.dumps(db, indent=2, ensure_ascii=False), encoding="utf-8")


def get_task(task_id: str) -> Task | None:
    db = _load_db()
    for t in db["tasks"]:
        if t["id"] == task_id:
            return Task(**t)
    return None


def save_task(task: Task) -> None:
    db = _load_db()
    found = False
    for i, t in enumerate(db["tasks"]):
        if t["id"] == task.id:
            db["tasks"][i] = task.to_dict()
            found = True
            break
    if not found:
        db["tasks"].append(task.to_dict())
    _save_db(db)


# ---------------------------------------------------------------------------
# Agent runners
# ---------------------------------------------------------------------------


def _resolve_executable(name: str) -> str:
    """Return a path Python's subprocess can launch directly.

    On Windows, npm-installed CLIs ship as ``<name>`` (POSIX shell shim),
    ``<name>.cmd`` (batch file), and sometimes ``<name>.ps1``. Python's
    ``subprocess.run`` does not auto-resolve these without ``shell=True``,
    so we walk PATH looking for a runnable extension explicitly.
    Returns the original name if no candidate is found, letting subprocess
    surface the FileNotFoundError as it normally would.
    """
    import shutil

    direct = shutil.which(name)
    if direct:
        return direct
    if sys.platform.startswith("win"):
        for ext in (".cmd", ".bat", ".exe"):
            cand = shutil.which(name + ext)
            if cand:
                return cand
    return name


def _run_subprocess(cmd: list[str], stdin_text: str | None = None,
                     env: dict | None = None, timeout: int = DEFAULT_TIMEOUT) -> tuple[int, str, str]:
    """Run *cmd* as a blocking subprocess, return (exit, stdout, stderr)."""
    proc_env = os.environ.copy()
    if env:
        proc_env.update(env)
    resolved = [_resolve_executable(cmd[0])] + list(cmd[1:])
    try:
        completed = subprocess.run(
            resolved,
            input=stdin_text,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=proc_env,
        )
        return completed.returncode, completed.stdout, completed.stderr
    except subprocess.TimeoutExpired as exc:
        return 124, exc.stdout or "", (exc.stderr or "") + f"\n[cg] TIMEOUT after {timeout}s"
    except FileNotFoundError as exc:
        return 127, "", f"[cg] command not found: {cmd[0]} ({exc})"


def run_claude(prompt: str, *, timeout: int = DEFAULT_TIMEOUT) -> tuple[int, str, str]:
    """Invoke Claude Code in headless print mode."""
    return _run_subprocess(
        ["claude", "--print"],
        stdin_text=prompt,
        timeout=timeout,
    )


def run_gemini(prompt: str, *, timeout: int = DEFAULT_TIMEOUT) -> tuple[int, str, str]:
    """Invoke Google Gemini CLI in headless mode.

    Uses ``--skip-trust`` to bypass the trust-this-folder interactive
    prompt (we are operating in headless mode, the human owns the repo).
    """
    return _run_subprocess(
        ["gemini", "--skip-trust", "-p", prompt],
        env={"GOOGLE_GENAI_USE_GCA": "true"},
        timeout=timeout,
    )


AGENT_RUNNERS = {
    "claude": run_claude,
    "gemini": run_gemini,
}


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


def dispatch(task: Task, agents: list[str], *, timeout: int = DEFAULT_TIMEOUT) -> dict[str, dict]:
    """Send *task.spec* to each agent in parallel. Return per-agent results."""
    out_dir = OUTPUTS_DIR / task.id
    out_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, dict] = {}
    started = _now_iso()

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(agents)) as pool:
        future_map = {
            pool.submit(AGENT_RUNNERS[a], task.spec, timeout=timeout): a
            for a in agents if a in AGENT_RUNNERS
        }
        unknown = [a for a in agents if a not in AGENT_RUNNERS]
        for u in unknown:
            print(f"[cg] WARN: unknown agent {u!r}, skipping", file=sys.stderr)
        for fut in concurrent.futures.as_completed(future_map):
            agent = future_map[fut]
            try:
                exit_code, stdout, stderr = fut.result()
            except Exception as exc:  # pragma: no cover - subprocess errors are caught upstream
                exit_code, stdout, stderr = 1, "", f"[cg] dispatcher error: {exc}"
            (out_dir / f"{agent}.md").write_text(stdout, encoding="utf-8")
            if stderr.strip():
                (out_dir / f"{agent}.stderr").write_text(stderr, encoding="utf-8")
            results[agent] = {
                "exit_code": exit_code,
                "stdout_path": str((out_dir / f"{agent}.md").relative_to(ROOT)),
                "stderr_path": (
                    str((out_dir / f"{agent}.stderr").relative_to(ROOT))
                    if stderr.strip() else None
                ),
                "stdout_chars": len(stdout),
            }
    finished = _now_iso()

    task.runs.append({
        "started": started,
        "finished": finished,
        "agents": agents,
        "results": results,
    })
    save_task(task)
    return results


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------


def cmd_task_add(args: argparse.Namespace) -> int:
    title = args.title
    if args.spec_file:
        spec = Path(args.spec_file).read_text(encoding="utf-8")
    elif args.spec_inline:
        spec = args.spec_inline
    elif not sys.stdin.isatty():
        spec = sys.stdin.read()
    else:
        spec = ""
    if not spec.strip():
        print("error: task spec is empty (use --spec-file, --spec, or pipe via stdin)",
              file=sys.stderr)
        return 2
    task = Task(
        id=args.task_id or _next_task_id(),
        title=title,
        spec=spec,
        created_at=_now_iso(),
    )
    save_task(task)
    print(f"created {task.id}: {task.title}")
    print(f"  spec chars: {len(spec)}")
    print(f"  to dispatch: python cg.py run {task.id} --to claude")
    print(f"            or python cg.py run {task.id} --to gemini")
    print(f"            or python cg.py run {task.id} --to both")
    return 0


def cmd_task_list(args: argparse.Namespace) -> int:
    db = _load_db()
    if not db["tasks"]:
        print("(no tasks)")
        return 0
    for t in db["tasks"]:
        runs = len(t.get("runs", []))
        print(f"{t['id']}  runs={runs}  {t['title']}")
    return 0


def cmd_task_show(args: argparse.Namespace) -> int:
    task = get_task(args.task_id)
    if task is None:
        print(f"error: task {args.task_id} not found", file=sys.stderr)
        return 1
    print(f"# {task.id} — {task.title}")
    print(f"created: {task.created_at}")
    print(f"spec ({len(task.spec)} chars):")
    print(textwrap.indent(task.spec, "  "))
    if task.runs:
        print("\nruns:")
        for r in task.runs:
            agents = ", ".join(r["agents"])
            print(f"  - {r['started']} -> {r['finished']}  [{agents}]")
            for a, info in r["results"].items():
                print(f"      {a}: exit={info['exit_code']} chars={info['stdout_chars']} -> {info['stdout_path']}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    task = get_task(args.task_id)
    if task is None:
        print(f"error: task {args.task_id} not found", file=sys.stderr)
        return 1
    if args.to == "both":
        agents = ["claude", "gemini"]
    else:
        agents = [args.to]
    print(f"[cg] dispatching {task.id} to {agents} (timeout={args.timeout}s)")
    results = dispatch(task, agents, timeout=args.timeout)
    for agent, info in results.items():
        marker = "OK" if info["exit_code"] == 0 else f"FAIL({info['exit_code']})"
        print(f"  {agent}: {marker}  -> {info['stdout_path']}  ({info['stdout_chars']} chars)")
        if info["stderr_path"]:
            print(f"    stderr: {info['stderr_path']}")
    return 0


def cmd_cluster(args: argparse.Namespace) -> int:
    """Launch a multi-agent cluster from a JSON spec.

    Spec format (a list of agent invocations)::

        [
          {"agent": "gemini", "label": "design",   "prompt": "..."},
          {"agent": "claude", "label": "build",    "prompt": "..."},
          {"agent": "gemini", "label": "review",   "prompt": "..."}
        ]

    With ``--layout tasks-json`` we instead write a ``.vscode/tasks.json``
    that the IDE (Antigravity / VS Code / Cursor) can run as a single
    "Run cluster" task — all panes appear inside the IDE window.
    """
    import cluster as cluster_mod

    spec_path = Path(args.spec).resolve()
    if not spec_path.exists():
        print(f"error: spec file {spec_path} not found", file=sys.stderr)
        return 1
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    if not isinstance(spec, list):
        print("error: spec must be a JSON array of agent invocations", file=sys.stderr)
        return 1

    cluster_dir = OUTPUTS_DIR / args.id
    rc = cluster_mod.run_cluster(spec, cluster_dir, layout=args.layout)
    if rc != 0:
        return rc
    if args.wait:
        results = cluster_mod.wait_for_cluster(cluster_dir, timeout=args.timeout)
        all_ok = all(v == 0 for v in results.values())
        for label, exit_code in results.items():
            print(f"  {label}: exit={exit_code}")
        return 0 if all_ok else 1
    return 0


def cmd_dashboard(args: argparse.Namespace) -> int:
    """Launch the web dashboard (FastAPI app) on a local port.

    Opens http://127.0.0.1:8765 in the default browser. The dashboard
    lets you define multi-agent workflows, run them in parallel, and
    watch each agent's stdout stream live in its own panel.
    """
    try:
        import uvicorn  # noqa: F401  (presence check)
    except ImportError:
        print("error: uvicorn not installed. Run: pip install fastapi 'uvicorn[standard]' sse-starlette",
              file=sys.stderr)
        return 1
    # We delegate to dashboard.main() so the CLI stays consistent.
    sys.argv = ["dashboard"]
    if args.host:
        sys.argv += ["--host", args.host]
    if args.port:
        sys.argv += ["--port", str(args.port)]
    if args.no_open:
        sys.argv += ["--no-open"]
    # Import here so we don't pay startup cost for other commands
    sys.path.insert(0, str(Path(__file__).parent))
    import dashboard
    dashboard.main()
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    """Smoke-check that both AI worker CLIs are present and authenticated."""
    print("[cg] doctor — checking agent CLIs")
    print("")

    print("claude --print …")
    code, out, err = run_claude("Reply with the single word PONG and nothing else.", timeout=60)
    print(f"  exit={code}  out={out.strip()[:80]!r}")
    if err.strip():
        print(f"  stderr={err.strip()[:200]!r}")

    print("\ngemini --skip-trust -p …")
    code, out, err = run_gemini("Reply with the single word PONG and nothing else.", timeout=60)
    print(f"  exit={code}  out={out.strip()[:80]!r}")
    if err.strip():
        # gemini emits warnings on stderr that are not fatal
        first_err = err.strip().splitlines()[0] if err.strip() else ""
        print(f"  stderr (first line)={first_err[:200]!r}")

    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cg",
                                 description="CG minimal multi-agent orchestrator (subscription-based).")
    sub = p.add_subparsers(dest="cmd", required=True)

    # task
    task = sub.add_parser("task", help="task CRUD")
    task_sub = task.add_subparsers(dest="task_cmd", required=True)

    add = task_sub.add_parser("add", help="create a new task")
    add.add_argument("title", help="short task title")
    add.add_argument("--spec", dest="spec_inline", default=None,
                     help="task spec inline (or use --spec-file / stdin)")
    add.add_argument("--spec-file", dest="spec_file", default=None,
                     help="path to a Markdown file containing the task spec")
    add.add_argument("--id", dest="task_id", default=None,
                     help="explicit task ID (default: auto-numbered)")
    add.set_defaults(func=cmd_task_add)

    lst = task_sub.add_parser("list", help="list tasks")
    lst.set_defaults(func=cmd_task_list)

    sh = task_sub.add_parser("show", help="show one task with run history")
    sh.add_argument("task_id")
    sh.set_defaults(func=cmd_task_show)

    # run
    run = sub.add_parser("run", help="dispatch a task to one or both agents")
    run.add_argument("task_id")
    run.add_argument("--to", choices=["claude", "gemini", "both"], required=True)
    run.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                     help=f"per-agent timeout in seconds (default: {DEFAULT_TIMEOUT})")
    run.set_defaults(func=cmd_run)

    # dashboard
    dash = sub.add_parser("dashboard",
                           help="launch the web dashboard (multi-agent UI in browser)")
    dash.add_argument("--host", default="127.0.0.1")
    dash.add_argument("--port", type=int, default=8765)
    dash.add_argument("--no-open", action="store_true",
                       help="do not auto-open browser")
    dash.set_defaults(func=cmd_dashboard)

    # cluster
    cl = sub.add_parser("cluster",
                         help="launch N agents in parallel, each in its own visible window")
    cl.add_argument("spec", help="path to JSON cluster spec (array of {agent,label,prompt})")
    cl.add_argument("--id", default="cluster", help="cluster id (used as outputs/<id>/ subdir)")
    cl.add_argument("--layout", choices=["auto", "wt", "cmd", "tasks-json"], default="auto",
                     help="window layout: wt=Windows Terminal split panes, "
                          "cmd=separate console windows, tasks-json=write .vscode/tasks.json "
                          "for the IDE, auto=pick wt if available else cmd")
    cl.add_argument("--wait", action=argparse.BooleanOptionalAction, default=True,
                     help="block until all agents finish (--no-wait to fire-and-forget)")
    cl.add_argument("--timeout", type=int, default=600,
                     help="cluster-wide timeout in seconds")
    cl.set_defaults(func=cmd_cluster)

    # doctor
    doc = sub.add_parser("doctor", help="smoke-check both AI worker CLIs")
    doc.set_defaults(func=cmd_doctor)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
