"""Cluster runner — multiple agents in parallel, each in its own visible pane.

Three rendering modes, picked automatically based on what is installed:

  1. ``wt`` (Windows Terminal) — single window, split into N vertical panes.
     Best UX. Install from Microsoft Store: "Windows Terminal".
  2. ``cmd start`` fallback — opens N separate cmd windows side by side.
     Always works on Windows. Less tidy but visible.
  3. ``.vscode/tasks.json`` generation — when launching from inside an
     IDE (Antigravity, VS Code, Cursor) you get N integrated-terminal
     tabs in the same IDE window, all in parallel.

The cluster file is JSON describing N agent invocations:

  [
    {"agent": "gemini", "label": "design", "prompt": "..."},
    {"agent": "claude", "label": "build",  "prompt": "..."},
    {"agent": "gemini", "label": "review", "prompt": "..."}
  ]
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import textwrap
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN_VISIBLE = ROOT / "scripts" / "run_visible.py"


def _wt_available() -> bool:
    return shutil.which("wt") is not None


def _emit_ps_runner(label: str, agent: str, prompt_path: Path,
                     output_path: Path) -> Path:
    """Write a small .ps1 that runs the agent and tees output to *output_path*.

    Returns the path to the generated .ps1.
    """
    invocation_map = {
        "claude": (
            "Get-Content -Raw -Encoding UTF8 '{p}' | claude --print"
        ),
        "gemini": (
            "$prompt = Get-Content -Raw -Encoding UTF8 '{p}'; "
            "$env:GOOGLE_GENAI_USE_GCA = 'true'; "
            "gemini --skip-trust -p $prompt"
        ),
    }
    if agent not in invocation_map:
        raise ValueError(f"unknown agent: {agent}")
    invocation = invocation_map[agent].format(p=prompt_path)

    ps = textwrap.dedent(f"""
        $Host.UI.RawUI.WindowTitle = '{label} ({agent})'
        Write-Host '== [{label}] {agent} starting ==' -ForegroundColor Cyan
        $start = Get-Date
        try {{
            {invocation} 2>&1 | Tee-Object -FilePath '{output_path}'
            $ec = $LASTEXITCODE
        }} catch {{
            Write-Host ('ERROR: ' + $_) -ForegroundColor Red
            $ec = 1
        }}
        $dur = (Get-Date) - $start
        Add-Content -Path '{output_path}' -Value ''
        Add-Content -Path '{output_path}' -Value ('__CG_DONE__ exit=' + $ec)
        Write-Host ''
        Write-Host ('== [{label}] done in ' + $dur.TotalSeconds.ToString('F1') + 's (exit=' + $ec + ') ==') -ForegroundColor Green
        Read-Host 'Press Enter to close'
    """).strip() + "\n"
    script_path = output_path.with_suffix(".ps1")
    script_path.write_text(ps, encoding="utf-8")
    return script_path


def run_cluster(cluster_spec: list[dict], cluster_dir: Path,
                 layout: str = "auto") -> int:
    """Launch each agent in *cluster_spec* in its own visible window.

    Args:
        cluster_spec: list of {"agent": str, "label": str, "prompt": str}.
        cluster_dir: where prompts and outputs go (created if missing).
        layout: "wt" (windows terminal), "cmd" (separate windows),
                "tasks-json" (write .vscode/tasks.json; do not launch),
                or "auto" (pick wt if available, else cmd).
    """
    cluster_dir.mkdir(parents=True, exist_ok=True)

    # Persist the cluster spec for replay
    (cluster_dir / "_spec.json").write_text(
        json.dumps(cluster_spec, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    runners = []
    for i, item in enumerate(cluster_spec):
        label = item.get("label") or f"step-{i+1}"
        agent = item["agent"]
        prompt = item["prompt"]
        prompt_path = cluster_dir / f"{i+1:02d}-{label}.prompt.txt"
        output_path = cluster_dir / f"{i+1:02d}-{label}.out.md"
        prompt_path.write_text(prompt, encoding="utf-8")
        output_path.write_text("", encoding="utf-8")
        ps = _emit_ps_runner(label, agent, prompt_path, output_path)
        runners.append({
            "label": label,
            "agent": agent,
            "ps_script": ps,
            "output": output_path,
        })

    if layout == "auto":
        layout = "wt" if _wt_available() else "cmd"

    if layout == "wt":
        return _launch_wt(runners)
    if layout == "cmd":
        return _launch_cmd(runners)
    if layout == "tasks-json":
        return _emit_tasks_json(runners, cluster_dir)
    print(f"error: unknown layout {layout!r}", file=sys.stderr)
    return 2


def _launch_wt(runners: list[dict]) -> int:
    """One Windows Terminal window, N vertical panes."""
    if not runners:
        return 0
    args = ["wt"]
    for i, r in enumerate(runners):
        if i == 0:
            args += ["new-tab", "--title", f"{r['label']} ({r['agent']})"]
        else:
            args += [";", "split-pane", "-V",
                     "--title", f"{r['label']} ({r['agent']})"]
        args += ["powershell.exe", "-NoExit", "-ExecutionPolicy", "Bypass",
                 "-File", str(r["ps_script"])]
    print(f"[cluster] launching wt with {len(runners)} panes")
    subprocess.Popen(args, shell=False)
    return 0


def _launch_cmd(runners: list[dict]) -> int:
    """Separate cmd windows, one per agent. Works without Windows Terminal."""
    print(f"[cluster] launching {len(runners)} separate console windows")
    for r in runners:
        subprocess.Popen(
            ["cmd.exe", "/c", "start", f"{r['label']} ({r['agent']})",
             "powershell.exe", "-NoExit", "-ExecutionPolicy", "Bypass",
             "-File", str(r["ps_script"])],
            shell=False,
        )
        time.sleep(0.2)  # tiny stagger so windows tile a bit
    return 0


def _emit_tasks_json(runners: list[dict], cluster_dir: Path) -> int:
    """Write a .vscode/tasks.json that runs all panes from inside the IDE."""
    tasks_dir = ROOT / ".vscode"
    tasks_dir.mkdir(exist_ok=True)
    tasks_path = tasks_dir / "tasks.json"

    tasks = []
    for r in runners:
        tasks.append({
            "label": f"agent: {r['label']}",
            "type": "shell",
            "command": "powershell.exe",
            "args": [
                "-NoExit", "-ExecutionPolicy", "Bypass",
                "-File", str(r["ps_script"]),
            ],
            "presentation": {
                "panel": "dedicated",
                "group": "agents",
                "reveal": "always",
            },
            "problemMatcher": [],
        })
    tasks.append({
        "label": "Run cluster",
        "dependsOn": [f"agent: {r['label']}" for r in runners],
        "dependsOrder": "parallel",
        "problemMatcher": [],
    })
    tasks_json = {"version": "2.0.0", "tasks": tasks}
    tasks_path.write_text(
        json.dumps(tasks_json, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"[cluster] wrote {tasks_path}")
    print("  In Antigravity / VS Code:  Ctrl+Shift+P → Tasks: Run Task → 'Run cluster'")
    print("  All N agents will open in parallel terminal tabs of the IDE.")
    return 0


def wait_for_cluster(cluster_dir: Path, *, timeout: int = 600) -> dict[str, int]:
    """Block until every output file in *cluster_dir* has the sentinel."""
    sentinel = "__CG_DONE__"
    spec_path = cluster_dir / "_spec.json"
    if not spec_path.exists():
        return {}
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    pending = {}
    for i, item in enumerate(spec):
        label = item.get("label") or f"step-{i+1}"
        pending[label] = cluster_dir / f"{i+1:02d}-{label}.out.md"
    results: dict[str, int] = {}
    start = time.time()
    while pending and time.time() - start < timeout:
        for label, path in list(pending.items()):
            if path.exists():
                tail = path.read_text(encoding="utf-8", errors="replace").splitlines()[-3:]
                for line in tail:
                    if line.startswith(sentinel):
                        try:
                            results[label] = int(line.split("=", 1)[1])
                        except (IndexError, ValueError):
                            results[label] = 0
                        del pending[label]
                        print(f"[cluster] {label}: done (exit={results[label]})")
                        break
        if pending:
            time.sleep(2)
    for label in pending:
        results[label] = 124  # timeout
    return results
