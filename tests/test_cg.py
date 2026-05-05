"""Tests for the CG orchestrator.

These tests cover:

- Task model serialization (round-trip through JSON)
- Task ID auto-numbering
- Subprocess fan-out + result aggregation
- Windows-safe executable resolution

The agent runners (claude, gemini) are *not* invoked; instead each test
patches ``AGENT_RUNNERS`` to deterministic stubs so tests run offline,
fast, and without consuming subscription quota.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Make src/ importable without installing the package.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import cg  # noqa: E402  (import after sys.path tweak)


@pytest.fixture
def tmp_repo(tmp_path, monkeypatch):
    """Redirect ROOT/TASKS_DIR/OUTPUTS_DIR/DB_PATH at a tmp dir per test."""
    monkeypatch.setattr(cg, "ROOT", tmp_path)
    monkeypatch.setattr(cg, "TASKS_DIR", tmp_path / "tasks")
    monkeypatch.setattr(cg, "OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.setattr(cg, "DB_PATH", tmp_path / "tasks" / "_index.json")
    return tmp_path


def test_next_task_id_starts_at_001(tmp_repo):
    assert cg._next_task_id() == "task-001"


def test_next_task_id_increments(tmp_repo):
    cg.save_task(cg.Task(id="task-001", title="A", spec="", created_at=cg._now_iso()))
    cg.save_task(cg.Task(id="task-002", title="B", spec="", created_at=cg._now_iso()))
    cg.save_task(cg.Task(id="task-005", title="E", spec="", created_at=cg._now_iso()))
    assert cg._next_task_id() == "task-006"


def test_task_save_and_get_round_trip(tmp_repo):
    t = cg.Task(id="task-001", title="A", spec="hello", created_at=cg._now_iso())
    cg.save_task(t)
    fetched = cg.get_task("task-001")
    assert fetched is not None
    assert fetched.title == "A"
    assert fetched.spec == "hello"


def test_task_save_overwrites_existing(tmp_repo):
    t = cg.Task(id="task-001", title="orig", spec="x", created_at=cg._now_iso())
    cg.save_task(t)
    t.title = "updated"
    cg.save_task(t)
    fetched = cg.get_task("task-001")
    assert fetched.title == "updated"
    db = json.loads((tmp_repo / "tasks" / "_index.json").read_text(encoding="utf-8"))
    assert len(db["tasks"]) == 1


def test_get_task_missing_returns_none(tmp_repo):
    assert cg.get_task("task-999") is None


def test_dispatch_calls_each_agent_in_parallel(tmp_repo, monkeypatch):
    calls: list[str] = []

    def fake_claude(prompt, *, timeout=cg.DEFAULT_TIMEOUT):
        calls.append("claude")
        return 0, f"claude got: {prompt}", ""

    def fake_gemini(prompt, *, timeout=cg.DEFAULT_TIMEOUT):
        calls.append("gemini")
        return 0, f"gemini got: {prompt}", ""

    monkeypatch.setitem(cg.AGENT_RUNNERS, "claude", fake_claude)
    monkeypatch.setitem(cg.AGENT_RUNNERS, "gemini", fake_gemini)

    task = cg.Task(id="task-001", title="X", spec="say hi",
                    created_at=cg._now_iso())
    cg.save_task(task)
    results = cg.dispatch(task, ["claude", "gemini"], timeout=10)

    assert set(results.keys()) == {"claude", "gemini"}
    assert results["claude"]["exit_code"] == 0
    assert results["gemini"]["exit_code"] == 0
    assert sorted(calls) == ["claude", "gemini"]
    out_dir = tmp_repo / "outputs" / "task-001"
    assert (out_dir / "claude.md").read_text(encoding="utf-8") == "claude got: say hi"
    assert (out_dir / "gemini.md").read_text(encoding="utf-8") == "gemini got: say hi"


def test_dispatch_records_run_in_task_history(tmp_repo, monkeypatch):
    monkeypatch.setitem(
        cg.AGENT_RUNNERS, "claude",
        lambda p, **_: (0, "out", "")
    )
    task = cg.Task(id="task-007", title="X", spec="x", created_at=cg._now_iso())
    cg.save_task(task)
    cg.dispatch(task, ["claude"], timeout=10)
    refreshed = cg.get_task("task-007")
    assert len(refreshed.runs) == 1
    assert refreshed.runs[0]["agents"] == ["claude"]


def test_dispatch_writes_stderr_only_when_nonempty(tmp_repo, monkeypatch):
    monkeypatch.setitem(
        cg.AGENT_RUNNERS, "claude",
        lambda p, **_: (0, "out", "warning here")
    )
    monkeypatch.setitem(
        cg.AGENT_RUNNERS, "gemini",
        lambda p, **_: (0, "out", "")
    )
    task = cg.Task(id="task-001", title="X", spec="x", created_at=cg._now_iso())
    cg.save_task(task)
    cg.dispatch(task, ["claude", "gemini"], timeout=10)
    out_dir = tmp_repo / "outputs" / "task-001"
    assert (out_dir / "claude.stderr").exists()
    assert not (out_dir / "gemini.stderr").exists()


def test_dispatch_handles_failure(tmp_repo, monkeypatch):
    monkeypatch.setitem(
        cg.AGENT_RUNNERS, "claude",
        lambda p, **_: (1, "", "boom")
    )
    task = cg.Task(id="task-001", title="X", spec="x", created_at=cg._now_iso())
    cg.save_task(task)
    results = cg.dispatch(task, ["claude"], timeout=10)
    assert results["claude"]["exit_code"] == 1


def test_dispatch_skips_unknown_agent(tmp_repo, monkeypatch, capsys):
    monkeypatch.setitem(
        cg.AGENT_RUNNERS, "claude",
        lambda p, **_: (0, "out", "")
    )
    task = cg.Task(id="task-001", title="X", spec="x", created_at=cg._now_iso())
    cg.save_task(task)
    results = cg.dispatch(task, ["claude", "ghost"], timeout=10)
    assert "claude" in results
    assert "ghost" not in results
    captured = capsys.readouterr()
    assert "unknown agent 'ghost'" in captured.err


def test_resolve_executable_returns_string(tmp_repo):
    # On Windows the resolver looks for .cmd / .bat / .exe; on Linux it
    # falls back to the original name. Either way it returns a string.
    out = cg._resolve_executable("python")
    assert isinstance(out, str)


def test_load_db_when_missing_returns_empty(tmp_repo):
    assert cg._load_db() == {"tasks": []}


def test_save_db_creates_parent(tmp_repo):
    db_path = tmp_repo / "tasks" / "_index.json"
    assert not db_path.exists()
    cg._save_db({"tasks": []})
    assert db_path.exists()


# CLI smoke (lightweight — checks parser doesn't crash and dispatches funcs)


def test_cli_task_add_then_list(tmp_repo, monkeypatch, capsys):
    parser = cg.build_parser()

    args = parser.parse_args(["task", "add", "Test title", "--spec", "do thing"])
    rc = args.func(args)
    assert rc == 0
    captured = capsys.readouterr()
    assert "task-001" in captured.out

    args = parser.parse_args(["task", "list"])
    rc = args.func(args)
    assert rc == 0
    captured = capsys.readouterr()
    assert "task-001" in captured.out
    assert "Test title" in captured.out


def test_cli_run_unknown_task_exits_nonzero(tmp_repo, capsys):
    parser = cg.build_parser()
    args = parser.parse_args(["run", "task-999", "--to", "claude"])
    rc = args.func(args)
    assert rc == 1
    captured = capsys.readouterr()
    assert "not found" in captured.err
