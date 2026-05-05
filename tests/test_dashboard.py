"""Smoke tests for the dashboard FastAPI app.

These tests exercise the HTTP endpoints with a TestClient. The actual
agent subprocesses are NOT invoked — we patch the AGENT_KINDS commands
so each "agent" is just `python -c "print('mock'); ..."` returning
deterministic stdout. That keeps tests fast and offline (no Pro / Google
quota burned during CI).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import dashboard as dash  # noqa: E402


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(dash, "RUNS_DIR", tmp_path / "runs")
    dash.RUNS_DIR.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(dash, "INDEX_PATH", tmp_path / "index.json")

    # Replace claude/gemini with deterministic Python one-liners so tests
    # don't actually call the subscriptions.
    monkeypatch.setitem(
        dash.AGENT_KINDS, "claude",
        {
            "label": "Claude (mock)",
            "command": [sys.executable, "-c",
                         "import sys; print('CLAUDE-MOCK ' + sys.stdin.read().strip())"],
            "stdin_prompt": True,
            "env": {},
        },
    )
    monkeypatch.setitem(
        dash.AGENT_KINDS, "gemini",
        {
            "label": "Gemini (mock)",
            "command": [sys.executable, "-c",
                         "import sys; print('GEMINI-MOCK ' + sys.argv[1])"],
            "stdin_prompt": False,
            "env": {},
        },
    )

    app = dash.create_app()
    return TestClient(app)


def test_get_agents(client):
    r = client.get("/api/agents")
    assert r.status_code == 200
    body = r.json()
    ids = [a["id"] for a in body["agents"]]
    assert "claude" in ids and "gemini" in ids


def test_get_presets(client):
    r = client.get("/api/presets")
    assert r.status_code == 200
    body = r.json()
    assert len(body["presets"]) >= 1
    for p in body["presets"]:
        assert {"id", "title", "description", "spec"} <= set(p.keys())
        assert isinstance(p["spec"], list)


def test_post_run_then_get(client):
    payload = {
        "title": "test run",
        "spec": [
            {"agent": "claude", "label": "c1", "prompt": "hello-1"},
            {"agent": "gemini", "label": "g1", "prompt": "hello-2"},
        ],
    }
    r = client.post("/api/runs", json=payload)
    assert r.status_code == 200
    run_id = r.json()["id"]

    # Wait for completion (mock subprocesses finish in ms; poll briefly)
    import time
    for _ in range(40):  # up to ~4 seconds
        r = client.get(f"/api/runs/{run_id}")
        body = r.json()
        if all(a["status"] in {"done", "failed"} for a in body["agents"]):
            break
        time.sleep(0.1)

    assert all(a["status"] == "done" for a in body["agents"])
    assert all(a["exit_code"] == 0 for a in body["agents"])

    # Outputs
    r = client.get(f"/api/runs/{run_id}/output/c1")
    assert r.status_code == 200
    assert "CLAUDE-MOCK hello-1" in r.json()["log"]
    r = client.get(f"/api/runs/{run_id}/output/g1")
    assert r.status_code == 200
    assert "GEMINI-MOCK hello-2" in r.json()["log"]


def test_post_run_rejects_empty_spec(client):
    r = client.post("/api/runs", json={"title": "x", "spec": []})
    assert r.status_code == 400


def test_post_run_rejects_unknown_agent(client):
    r = client.post(
        "/api/runs",
        json={"title": "x", "spec": [
            {"agent": "ghost", "label": "g", "prompt": "x"}]},
    )
    assert r.status_code == 400


def test_get_run_404(client):
    r = client.get("/api/runs/nonexistent")
    assert r.status_code == 404


def test_list_runs(client):
    # Empty initially
    r = client.get("/api/runs")
    assert r.status_code == 200
    initial = len(r.json()["runs"])

    # Add one
    r = client.post("/api/runs", json={
        "title": "history-test",
        "spec": [{"agent": "claude", "label": "c", "prompt": "y"}],
    })
    assert r.status_code == 200

    r = client.get("/api/runs")
    runs = r.json()["runs"]
    assert len(runs) == initial + 1
    assert any(r["title"] == "history-test" for r in runs)


def test_root_serves_html(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "CG" in r.text
    assert "<html" in r.text.lower()


def test_static_assets(client):
    r = client.get("/static/dashboard.css")
    assert r.status_code == 200
    assert "agent-panel" in r.text
    r = client.get("/static/dashboard.js")
    assert r.status_code == 200
    assert "EventSource" in r.text
