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

    # Replace each real model with a deterministic Python one-liner so
    # tests don't actually call the subscriptions.
    claude_mock = {
        "label": "Claude (mock)",
        "family": "claude",
        "summary": "mock",
        "command": [sys.executable, "-c",
                     "import sys; print('CLAUDE-MOCK ' + sys.stdin.read().strip())"],
        "stdin_prompt": True,
        "env": {},
    }
    gemini_mock = {
        "label": "Gemini (mock)",
        "family": "gemini",
        "summary": "mock",
        "command": [sys.executable, "-c",
                     "import sys; print('GEMINI-MOCK ' + sys.argv[1])"],
        "stdin_prompt": False,
        "env": {},
    }
    # Mock both legacy aliases AND the new specific model ids
    for kid in ("claude", "claude-sonnet-4-6", "claude-opus-4-7", "claude-opus-4-6"):
        monkeypatch.setitem(dash.AGENT_KINDS, kid, claude_mock)
    for kid in ("gemini", "gemini-flash", "gemini-pro", "gemini-3-pro"):
        monkeypatch.setitem(dash.AGENT_KINDS, kid, gemini_mock)

    app = dash.create_app()
    return TestClient(app)


def test_get_agents(client):
    r = client.get("/api/agents")
    assert r.status_code == 200
    body = r.json()
    ids = [a["id"] for a in body["agents"]]
    # New specific model ids must all be present
    for kid in ("claude-sonnet-4-6", "claude-opus-4-7", "claude-opus-4-6",
                 "gemini-flash", "gemini-pro", "gemini-3-pro"):
        assert kid in ids, f"missing model id {kid!r} in {ids}"
    # Each entry has family + summary
    for a in body["agents"]:
        assert a["family"] in {"claude", "gemini", "other"}
        assert "summary" in a


def test_legacy_alias_still_works(client):
    """Old presets / clients using `agent: claude` should still resolve."""
    r = client.post("/api/runs", json={
        "title": "alias",
        "spec": [{"agent": "claude", "label": "c", "prompt": "x"}],
    })
    assert r.status_code == 200
    run_id = r.json()["id"]
    import time
    for _ in range(40):
        body = client.get(f"/api/runs/{run_id}").json()
        if all(a["status"] in {"done", "failed"} for a in body["agents"]):
            break
        time.sleep(0.1)
    assert body["agents"][0]["status"] == "done"
    # The agent kind should have been normalized to the canonical id
    assert body["agents"][0]["agent"] == "claude-sonnet-4-6"


def test_specific_model_ids_dispatch(client):
    """Each specific Claude/Gemini model id must be invokable."""
    payload = {
        "title": "all-models",
        "spec": [
            {"agent": "claude-sonnet-4-6", "label": "s46", "prompt": "x"},
            {"agent": "claude-opus-4-7",   "label": "o47", "prompt": "y"},
            {"agent": "gemini-flash",      "label": "gf",  "prompt": "z"},
            {"agent": "gemini-3-pro",      "label": "g3",  "prompt": "w"},
        ],
    }
    r = client.post("/api/runs", json=payload)
    assert r.status_code == 200
    run_id = r.json()["id"]
    import time
    for _ in range(60):
        body = client.get(f"/api/runs/{run_id}").json()
        if all(a["status"] in {"done", "failed"} for a in body["agents"]):
            break
        time.sleep(0.1)
    assert all(a["status"] == "done" for a in body["agents"])


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


def test_depends_on_runs_after_predecessor(client):
    """A→B with depends_on should run sequentially with substitution."""
    payload = {
        "title": "deps test",
        "spec": [
            {"agent": "claude", "label": "first", "prompt": "step-A"},
            {"agent": "gemini", "label": "second",
             "depends_on": ["first"],
             "prompt": "got: {{first}}"},
        ],
    }
    r = client.post("/api/runs", json=payload)
    assert r.status_code == 200
    run_id = r.json()["id"]

    import time
    for _ in range(60):
        r = client.get(f"/api/runs/{run_id}")
        body = r.json()
        if all(a["status"] in {"done", "failed"} for a in body["agents"]):
            break
        time.sleep(0.1)

    assert all(a["status"] == "done" for a in body["agents"]), \
        f"agents did not all reach done: {[a['status'] for a in body['agents']]}"

    # The 'second' agent should have received the first agent's output
    # via the {{first}} substitution. Our mock claude prints
    # "CLAUDE-MOCK <stdin>" so first.output = "CLAUDE-MOCK step-A".
    # Mock gemini prints "GEMINI-MOCK <argv[1]>" so second.output should
    # contain "got: CLAUDE-MOCK step-A".
    r = client.get(f"/api/runs/{run_id}/output/second")
    log = r.json()["log"]
    assert "CLAUDE-MOCK step-A" in log, (
        f"substitution failed; second's log was: {log!r}")


def test_depends_on_propagates_failure(client, monkeypatch):
    """If a dependency fails, dependents must be marked failed without running."""
    # Force the canonical claude model id to fail (legacy "claude" alias
    # resolves to "claude-sonnet-4-6", so we must override that one).
    fail_mock = {
        "label": "Claude (mock-fail)",
        "family": "claude",
        "summary": "fail mock",
        "command": [sys.executable, "-c",
                     "import sys; print('FAILED'); sys.exit(1)"],
        "stdin_prompt": True,
        "env": {},
    }
    for kid in ("claude", "claude-sonnet-4-6"):
        monkeypatch.setitem(dash.AGENT_KINDS, kid, fail_mock)
    payload = {
        "title": "deps failure test",
        "spec": [
            {"agent": "claude", "label": "first", "prompt": "x"},
            {"agent": "gemini", "label": "second",
             "depends_on": ["first"], "prompt": "y"},
        ],
    }
    r = client.post("/api/runs", json=payload)
    assert r.status_code == 200
    run_id = r.json()["id"]

    import time
    for _ in range(60):
        r = client.get(f"/api/runs/{run_id}")
        body = r.json()
        if all(a["status"] in {"done", "failed", "cancelled"} for a in body["agents"]):
            break
        time.sleep(0.1)

    statuses = {a["label"]: a["status"] for a in body["agents"]}
    assert statuses["first"] == "failed"
    assert statuses["second"] == "failed"


def test_depends_on_unknown_label_is_400(client):
    r = client.post("/api/runs", json={
        "title": "bad deps",
        "spec": [
            {"agent": "claude", "label": "a", "depends_on": ["nonexistent"],
             "prompt": "x"},
        ],
    })
    assert r.status_code == 400


def test_depends_on_self_is_400(client):
    r = client.post("/api/runs", json={
        "title": "self dep",
        "spec": [
            {"agent": "claude", "label": "loop", "depends_on": ["loop"],
             "prompt": "x"},
        ],
    })
    assert r.status_code == 400


def test_duplicate_label_is_400(client):
    r = client.post("/api/runs", json={
        "title": "dupes",
        "spec": [
            {"agent": "claude", "label": "x", "prompt": "a"},
            {"agent": "claude", "label": "x", "prompt": "b"},
        ],
    })
    assert r.status_code == 400


def test_cancel_endpoint(client):
    r = client.post("/api/runs", json={
        "title": "cancel test",
        "spec": [{"agent": "claude", "label": "c", "prompt": "x"}],
    })
    run_id = r.json()["id"]
    r = client.delete(f"/api/runs/{run_id}")
    assert r.status_code == 200
    assert r.json()["cancelled"] is True


def test_cancel_unknown_run_404(client):
    r = client.delete("/api/runs/does-not-exist")
    assert r.status_code == 404
