"""Smoke tests for the dashboard FastAPI app.

These tests exercise the HTTP endpoints with a TestClient. The actual
agent subprocesses are NOT invoked — we patch the AGENT_KINDS commands
so each "agent" is just `python -c "print('mock'); ..."` returning
deterministic stdout. That keeps tests fast and offline (no Pro / Google
quota burned during CI).
"""

from __future__ import annotations

import json
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
    # Snapshot AGENT_KINDS so tests that mutate it (custom agents)
    # don't leak state into later tests in the same pytest session.
    snapshot = dict(dash.AGENT_KINDS)
    yield TestClient(app)
    dash.AGENT_KINDS.clear()
    dash.AGENT_KINDS.update(snapshot)


def test_get_agents(client):
    r = client.get("/api/agents")
    assert r.status_code == 200
    body = r.json()
    ids = [a["id"] for a in body["agents"]]
    # New specific model ids must all be present
    for kid in ("claude-sonnet-4-6", "claude-opus-4-7", "claude-opus-4-6",
                 "gemini-flash", "gemini-pro", "gemini-3-pro", "browser"):
        assert kid in ids, f"missing model id {kid!r} in {ids}"
    # Each entry has family + summary
    for a in body["agents"]:
        assert a["family"] in {"claude", "gemini", "browser", "other", "custom"}
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


# ---------------------------------------------------------------------------
# Context placeholders ({{file:...}}, {{git:...}}, {{shell:...}})
# ---------------------------------------------------------------------------


def test_browser_step_executor_runs_basic_actions(monkeypatch):
    """_run_browser_step should dispatch each action to the right
    Playwright method and return the right thing."""
    actions: list[tuple] = []

    class FakePage:
        url = "https://example.com/done"
        def goto(self, url, **kw):
            actions.append(("goto", url))
        def click(self, sel, **kw):
            actions.append(("click", sel))
        def fill(self, sel, val, **kw):
            actions.append(("fill", sel, val))
        def title(self): return "Mock Title"
        def content(self): return "<html>ok</html>"
        def wait_for_selector(self, sel, **kw):
            actions.append(("wait", sel))
        def wait_for_timeout(self, ms):
            actions.append(("wait_ms", ms))
        def query_selector(self, sel):
            class E:
                def inner_text(self): return f"text-of-{sel}"
                def get_attribute(self, a): return f"attr-{a}-of-{sel}"
                def screenshot(self, **kw): pass
            return E()
        def query_selector_all(self, sel):
            def _make(idx):
                class E:
                    def inner_text(self): return f"item-{idx}"
                    def get_attribute(self, a): return f"attr-{idx}"
                return E()
            return [_make(i) for i in range(3)]
        def screenshot(self, **kw):
            from pathlib import Path as _P
            _P(kw["path"]).parent.mkdir(parents=True, exist_ok=True)
            _P(kw["path"]).write_bytes(b"\x89PNG\r\n")
        def evaluate(self, js): return f"eval-result-of-{js[:20]}"
        def set_default_timeout(self, *a, **kw): pass
        def hover(self, sel): actions.append(("hover", sel))
        def type(self, sel, text, **kw): actions.append(("type", sel, text))
        def press(self, sel, key): actions.append(("press", sel, key))
        def pdf(self, path): pass
        def once(self, *a, **kw): pass

    page = FakePage()
    bindings: dict = {}
    run = dash.RunState(id="t", title="t", created=0, spec=[],
                          variables={"FOO": "bar"})

    # Test variable substitution + goto
    res = dash._run_browser_step(page, None, None,
        {"action": "goto", "url": "https://${FOO}.com"},
        run, "lbl", bindings)
    assert "https://bar.com" in str(res)
    assert actions[0] == ("goto", "https://bar.com")

    # extract
    res = dash._run_browser_step(page, None, None,
        {"action": "extract", "selector": "h1"},
        run, "lbl", bindings)
    assert res == "text-of-h1"

    # extract_all
    res = dash._run_browser_step(page, None, None,
        {"action": "extract_all", "selector": "li"},
        run, "lbl", bindings)
    assert res == ["item-0", "item-1", "item-2"]

    # fill
    res = dash._run_browser_step(page, None, None,
        {"action": "fill", "selector": "#x", "value": "y"},
        run, "lbl", bindings)
    assert ("fill", "#x", "y") in actions

    # title
    res = dash._run_browser_step(page, None, None,
        {"action": "title"}, run, "lbl", bindings)
    assert res == "Mock Title"


def test_browser_step_unknown_action_returns_marker(monkeypatch):
    class FakePage:
        def set_default_timeout(self, *a, **kw): pass

    res = dash._run_browser_step(FakePage(), None, None,
        {"action": "frobnicate"},
        dash.RunState(id="t", title="t", created=0, spec=[]),
        "lbl", {})
    assert "[unknown action" in res


def test_browser_step_screenshot_writes_file(tmp_path, monkeypatch):
    monkeypatch.setattr(dash, "SCREENSHOTS_DIR", tmp_path)

    class FakePage:
        url = "https://example.com"
        def screenshot(self, **kw):
            from pathlib import Path as _P
            _P(kw["path"]).write_bytes(b"\x89PNG")
        def query_selector(self, sel): return None

    res = dash._run_browser_step(FakePage(), None, None,
        {"action": "screenshot", "full_page": True},
        dash.RunState(id="t", title="t", created=0, spec=[]),
        "shot", {})
    assert "outputs/screenshots/" in res
    assert any(p.suffix == ".png" for p in tmp_path.iterdir())


def test_browser_runner_handles_invalid_json_prompt(client):
    """If the prompt isn't valid JSON, browser agent should fail with
    a clear message rather than crash."""
    r = client.post("/api/runs", json={
        "title": "bad json",
        "spec": [{"agent": "browser", "label": "x",
                   "prompt": "this is not json"}],
    })
    assert r.status_code == 200
    run_id = r.json()["id"]
    import time
    for _ in range(40):
        body = client.get(f"/api/runs/{run_id}").json()
        if body["agents"][0]["status"] in {"done", "failed"}:
            break
        time.sleep(0.1)
    assert body["agents"][0]["status"] == "failed"
    log = client.get(f"/api/runs/{run_id}/output/x").json()["log"]
    assert "not valid JSON" in log or "browser:" in log


def test_label_field_substitution_from_bindings(monkeypatch):
    """{{label.field}} should pull from RunState.bindings."""
    mgr = dash.RunManager()
    run = dash.RunState(id="t", title="t", created=0, spec=[],
                          bindings={"scrape": {"title": "Hello", "count": 5}})
    # Add a fake agent for the dependency check
    run.agents["scrape"] = dash.AgentRunState(label="scrape", agent="browser",
                                                  log_lines=["full log"])
    out = mgr._substitute_prompt(run,
        "Title: {{scrape.title}} | Count: {{scrape.count}} | Full: {{scrape}}",
        depends_on=["scrape"])
    assert "Title: Hello" in out
    assert "Count: 5" in out
    assert "Full: full log" in out


def test_web_placeholder_rejects_non_http_url(monkeypatch):
    out = dash._expand_context_placeholders("{{web:not-a-url}}")
    assert "must start with http" in out


def test_web_placeholder_handles_missing_playwright(monkeypatch):
    """If playwright is not installed, the placeholder must return a
    helpful error string instead of raising."""
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *a, **kw):
        if name.startswith("playwright"):
            raise ImportError("simulated missing playwright")
        return real_import(name, *a, **kw)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    out = dash._expand_context_placeholders("{{web:https://example.com}}")
    assert "playwright not installed" in out
    assert "pip install playwright" in out


def test_web_placeholder_text_uses_inner_text(monkeypatch, tmp_path):
    """Mock the playwright stack to verify _web_placeholder calls
    page.inner_text('body') for the default 'web' kind."""
    calls = {"goto": None, "method": None}

    class FakePage:
        def goto(self, url, **kw):
            calls["goto"] = url
        def wait_for_load_state(self, *a, **kw):
            pass
        def inner_text(self, sel):
            calls["method"] = ("inner_text", sel)
            return "BODY TEXT FROM MOCK"
        def title(self):
            calls["method"] = ("title",)
            return "MOCK TITLE"
        def content(self):
            calls["method"] = ("content",)
            return "<html><body>MOCK</body></html>"
        def screenshot(self, path, **kw):
            calls["method"] = ("screenshot", path)
            from pathlib import Path as _P
            _P(path).write_bytes(b"\x89PNG\r\n\x1a\n")
        def evaluate(self, js):
            calls["method"] = ("evaluate",)
            return {"title": "T", "description": "D", "og": {}, "twitter": {}}

    class FakeContext:
        def new_page(self):
            return FakePage()
    class FakeBrowser:
        def new_context(self, **kw):
            return FakeContext()
        def close(self):
            pass
    class FakeChromium:
        def launch(self, **kw):
            return FakeBrowser()
    class FakeP:
        chromium = FakeChromium()

    class FakePW:
        def __enter__(self):
            return FakeP()
        def __exit__(self, *a):
            return False

    import playwright.sync_api as ps
    monkeypatch.setattr(ps, "sync_playwright", lambda: FakePW())

    out = dash._web_placeholder("web", "https://example.com")
    assert out == "BODY TEXT FROM MOCK"
    assert calls["goto"] == "https://example.com"
    assert calls["method"] == ("inner_text", "body")


def test_web_placeholder_screenshot_returns_path(monkeypatch, tmp_path):
    """{{web-shot:URL}} should write a PNG into outputs/screenshots/
    and return its repo-relative path."""
    monkeypatch.setattr(dash, "SCREENSHOTS_DIR", tmp_path)

    class FakePage:
        def goto(self, url, **kw): pass
        def wait_for_load_state(self, *a, **kw): pass
        def screenshot(self, path, **kw):
            from pathlib import Path as _P
            _P(path).write_bytes(b"\x89PNG\r\n")
        def inner_text(self, sel): return ""
        def title(self): return ""
        def content(self): return ""
        def evaluate(self, js): return {}
    class FakeBrowser:
        def new_context(self, **kw):
            class C:
                def new_page(s2): return FakePage()
            return C()
        def close(self): pass
    class FakePW:
        def __enter__(self):
            class P:
                chromium = type("Cr", (), {"launch": lambda s, **k: FakeBrowser()})()
            return P()
        def __exit__(self, *a): return False

    import playwright.sync_api as ps
    monkeypatch.setattr(ps, "sync_playwright", lambda: FakePW())

    out = dash._web_placeholder("web-shot", "https://example.com")
    assert "screenshot saved" in out
    assert "outputs/screenshots/" in out
    # Confirm a PNG was actually written
    files = list(tmp_path.glob("*.png"))
    assert len(files) == 1


def test_placeholder_unknown_kind_left_intact(monkeypatch):
    out = dash._expand_context_placeholders("hello {{foo:bar}} world")
    assert out == "hello {{foo:bar}} world"


def test_placeholder_file_reads_existing_file(tmp_path, monkeypatch):
    monkeypatch.setenv("CG_PROJECT_ROOT", str(tmp_path))
    (tmp_path / "spec.md").write_text("# spec\nhello", encoding="utf-8")
    out = dash._expand_context_placeholders("read: {{file:spec.md}}")
    assert "# spec" in out and "hello" in out


def test_placeholder_file_missing_renders_marker(tmp_path, monkeypatch):
    monkeypatch.setenv("CG_PROJECT_ROOT", str(tmp_path))
    out = dash._expand_context_placeholders("{{file:does-not-exist.txt}}")
    assert "[file: not found" in out


def test_placeholder_file_path_traversal_refused(tmp_path, monkeypatch):
    monkeypatch.setenv("CG_PROJECT_ROOT", str(tmp_path))
    out = dash._expand_context_placeholders("{{file:../etc/passwd}}")
    # Must NOT contain typical /etc/passwd content; refusal marker present
    assert "refused" in out or "not found" in out


def test_placeholder_shell_disabled_by_default(monkeypatch):
    monkeypatch.setattr(dash, "_ALLOW_SHELL", False)
    out = dash._expand_context_placeholders("{{shell:echo hi}}")
    assert "disabled" in out


def test_placeholder_multiple_in_one_prompt(tmp_path, monkeypatch):
    monkeypatch.setenv("CG_PROJECT_ROOT", str(tmp_path))
    (tmp_path / "a.txt").write_text("AAA", encoding="utf-8")
    (tmp_path / "b.txt").write_text("BBB", encoding="utf-8")
    out = dash._expand_context_placeholders(
        "first: {{file:a.txt}} -- second: {{file:b.txt}}"
    )
    assert "AAA" in out and "BBB" in out


# ---------------------------------------------------------------------------
# Notes / knowledge base
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# G-phase: variables, secret forwarding, custom agents, webhooks, schedules
# ---------------------------------------------------------------------------


def test_variables_passed_to_run_via_post_body(client, monkeypatch):
    """The `variables` field on POST /api/runs must reach run.variables."""
    captured: list[dict] = []
    real_start = dash.RunManager.start_run

    def spy(self, title, spec, secrets=None, variables=None):
        captured.append(variables or {})
        return real_start(self, title, spec, secrets=secrets, variables=variables)

    monkeypatch.setattr(dash.RunManager, "start_run", spy)
    r = client.post("/api/runs", json={
        "title": "vars",
        "spec": [{"agent": "claude", "label": "x", "prompt": "y"}],
        "variables": {"FOO": "bar", "BAZ": "qux"},
    })
    assert r.status_code == 200
    assert captured[-1] == {"FOO": "bar", "BAZ": "qux"}


def test_substitute_prompt_method_directly(monkeypatch, tmp_path):
    """Direct unit test of RunManager._substitute_prompt with variables."""
    mgr = dash.RunManager()
    run = dash.RunState(
        id="t", title="t", created=0,
        spec=[],
        variables={"FOO": "bar", "URL": "https://example.com"},
    )
    out = mgr._substitute_prompt(run,
        "Visit ${URL} and look for ${FOO}", depends_on=[])
    assert out == "Visit https://example.com and look for bar"


def test_secrets_forwarded_via_headers(client, monkeypatch):
    """X-CG-OpenRouter-Key header → run.secrets['OPENROUTER_API_KEY']."""
    captured_secrets: list[dict] = []

    real_start = dash.RunManager.start_run

    def spy_start(self, title, spec, secrets=None, variables=None):
        captured_secrets.append(dict(secrets or {}))
        # Don't actually run anything — return a fake run
        return real_start(self, title, spec, secrets=secrets, variables=variables)

    monkeypatch.setattr(dash.RunManager, "start_run", spy_start)

    r = client.post(
        "/api/runs",
        headers={
            "Content-Type": "application/json",
            "X-CG-OpenRouter-Key": "sk-or-supersecret",
            "X-CG-Project-Root": "C:/some/path",
        },
        json={
            "title": "secrets test",
            "spec": [{"agent": "claude", "label": "x", "prompt": "y"}],
        },
    )
    assert r.status_code == 200
    assert captured_secrets[-1]["OPENROUTER_API_KEY"] == "sk-or-supersecret"
    assert captured_secrets[-1]["CG_PROJECT_ROOT"] == "C:/some/path"


def test_custom_agents_save_and_load(client, tmp_path, monkeypatch):
    """PUT /api/custom-agents → file written → next GET reflects it."""
    monkeypatch.setattr(dash, "CUSTOM_AGENTS_PATH", tmp_path / "custom_agents.json")
    body = {"agents": [{
        "id": "my-cohere",
        "label": "Cohere Command R+",
        "family": "custom",
        "summary": "Cohere flagship",
        "http": {
            "endpoint": "https://api.cohere.com/v1/chat",
            "model": "command-r-plus",
            "api_key_env": "COHERE_API_KEY",
            "headers": {"X-My-Header": "yes"},
        },
    }]}
    r = client.put("/api/custom-agents", json=body)
    assert r.status_code == 200
    assert r.json()["saved"] == 1

    r = client.get("/api/custom-agents")
    saved = r.json()["agents"]
    assert len(saved) == 1
    assert saved[0]["id"] == "my-cohere"


def test_custom_agents_rejects_invalid(client, tmp_path, monkeypatch):
    monkeypatch.setattr(dash, "CUSTOM_AGENTS_PATH", tmp_path / "ca.json")
    # Missing http
    r = client.put("/api/custom-agents", json={"agents": [{"id": "x"}]})
    assert r.status_code == 400
    # Bad id
    r = client.put("/api/custom-agents", json={"agents": [{
        "id": "../evil", "http": {"endpoint": "https://x", "model": "y"},
    }]})
    assert r.status_code == 400
    # Clash with built-in
    r = client.put("/api/custom-agents", json={"agents": [{
        "id": "claude-sonnet-4-6", "http": {"endpoint": "https://x", "model": "y"},
    }]})
    assert r.status_code == 409


def test_webhook_trigger_runs_workflow(client, tmp_path, monkeypatch):
    monkeypatch.setattr(dash, "WORKFLOWS_DIR", tmp_path)
    # Save a workflow
    client.put("/api/workflows/auto-flow", json={
        "title": "Auto",
        "spec": [{"agent": "claude", "label": "x", "prompt": "Hi ${WHO}"}],
        "variables": {"WHO": "default"},
    })
    # Trigger it with overlay vars
    r = client.post("/api/triggers/auto-flow",
                     json={"variables": {"WHO": "TeamIDAS"}})
    assert r.status_code == 200
    body = r.json()
    assert body["workflow"] == "auto-flow"
    assert body["id"]


def test_webhook_trigger_404_for_missing(client, tmp_path, monkeypatch):
    monkeypatch.setattr(dash, "WORKFLOWS_DIR", tmp_path)
    r = client.post("/api/triggers/nonexistent", json={})
    assert r.status_code == 404


def test_schedules_save_and_load(client, tmp_path, monkeypatch):
    monkeypatch.setattr(dash, "SCHEDULES_PATH", tmp_path / "schedules.json")
    body = {"schedules": [{
        "workflow": "morning-brief",
        "interval_minutes": 60,
        "enabled": True,
        "variables": {"TOPIC": "today"},
    }]}
    r = client.put("/api/schedules", json=body)
    assert r.status_code == 200
    assert r.json()["saved"] == 1
    r = client.get("/api/schedules")
    items = r.json()["schedules"]
    assert items[0]["workflow"] == "morning-brief"


def test_schedules_rejects_invalid(client, tmp_path, monkeypatch):
    monkeypatch.setattr(dash, "SCHEDULES_PATH", tmp_path / "s.json")
    # No interval
    r = client.put("/api/schedules", json={"schedules": [{"workflow": "x"}]})
    assert r.status_code == 400
    # Negative interval
    r = client.put("/api/schedules", json={"schedules": [{
        "workflow": "x", "interval_minutes": 0,
    }]})
    assert r.status_code == 400


def test_note_save_and_load(client, tmp_path, monkeypatch):
    monkeypatch.setattr(dash, "NOTES_DIR", tmp_path)
    r = client.put("/api/notes/hello", json={
        "title": "Hello",
        "tags": ["a", "b"],
        "content": "# Body\n\nLink: [[other]]",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "hello"
    assert body["title"] == "Hello"
    assert body["tags"] == ["a", "b"]
    assert "Body" in body["content"]

    r = client.get("/api/notes/hello")
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "Hello"
    assert body["created"]
    assert body["updated"]


def test_note_list_returns_recent_first(client, tmp_path, monkeypatch):
    monkeypatch.setattr(dash, "NOTES_DIR", tmp_path)
    client.put("/api/notes/first", json={"title": "First", "content": "1"})
    import time
    time.sleep(0.05)
    client.put("/api/notes/second", json={"title": "Second", "content": "2"})
    r = client.get("/api/notes")
    names = [n["name"] for n in r.json()["notes"]]
    assert "first" in names and "second" in names


def test_note_delete(client, tmp_path, monkeypatch):
    monkeypatch.setattr(dash, "NOTES_DIR", tmp_path)
    client.put("/api/notes/doomed", json={"title": "x", "content": "y"})
    r = client.delete("/api/notes/doomed")
    assert r.status_code == 200
    r = client.get("/api/notes/doomed")
    assert r.status_code == 404


def test_note_backlinks_finds_wikilinks(client, tmp_path, monkeypatch):
    monkeypatch.setattr(dash, "NOTES_DIR", tmp_path)
    client.put("/api/notes/source-1", json={
        "title": "Source 1",
        "content": "Mentions [[target]] in passing.",
    })
    client.put("/api/notes/source-2", json={
        "title": "Source 2",
        "content": "Also mentions [[target]] over here.",
    })
    client.put("/api/notes/target", json={
        "title": "Target",
        "content": "I am the target.",
    })
    r = client.get("/api/notes/target/backlinks")
    assert r.status_code == 200
    backlinks = r.json()["backlinks"]
    names = sorted(b["name"] for b in backlinks)
    assert names == ["source-1", "source-2"]
    # Each has an excerpt
    assert all("target" in b["excerpt"] for b in backlinks)


def test_note_search_substring(client, tmp_path, monkeypatch):
    monkeypatch.setattr(dash, "NOTES_DIR", tmp_path)
    client.put("/api/notes/a", json={"title": "Alpha", "content": "the quick brown fox"})
    client.put("/api/notes/b", json={"title": "Beta", "content": "lazy dog"})
    r = client.get("/api/notes-search?q=brown")
    assert r.status_code == 200
    hits = [h["name"] for h in r.json()["results"]]
    assert "a" in hits and "b" not in hits


def test_note_save_round_trips_frontmatter(tmp_path, monkeypatch):
    """Saving + loading preserves title, tags, created."""
    monkeypatch.setattr(dash, "NOTES_DIR", tmp_path)
    fm = {"title": "Name", "tags": ["x"], "created": "2026-01-01T10:00:00",
          "updated": "2026-01-02T10:00:00"}
    body = "Content here"
    rendered = dash._render_note(fm, body)
    p = tmp_path / "name.md"
    p.write_text(rendered, encoding="utf-8")
    parsed = dash._parse_note(p)
    assert parsed["title"] == "Name"
    assert parsed["tags"] == ["x"]
    assert parsed["created"] == "2026-01-01T10:00:00"
    assert parsed["content"].strip() == "Content here"


def test_note_name_sanitization(client, tmp_path, monkeypatch):
    monkeypatch.setattr(dash, "NOTES_DIR", tmp_path)
    r = client.put("/api/notes/A Note With Spaces & symbols!", json={
        "title": "Test", "content": "z",
    })
    assert r.status_code == 200
    files = list(tmp_path.glob("*.md"))
    assert len(files) == 1
    assert " " not in files[0].name and "!" not in files[0].name


def test_note_from_run(client, tmp_path, monkeypatch):
    """POST /api/notes/from-run should turn a run into a note."""
    monkeypatch.setattr(dash, "NOTES_DIR", tmp_path)
    # Create a run
    r = client.post("/api/runs", json={
        "title": "saved as note",
        "spec": [{"agent": "claude", "label": "x", "prompt": "y"}],
    })
    run_id = r.json()["id"]
    import time
    for _ in range(40):
        body = client.get(f"/api/runs/{run_id}").json()
        if all(a["status"] in {"done", "failed"} for a in body["agents"]):
            break
        time.sleep(0.1)
    r = client.post("/api/notes/from-run", json={"run_id": run_id})
    assert r.status_code == 200
    note = r.json()
    assert "Run:" in note["title"]
    assert "saved as note" in note["title"]
    assert "run" in note["tags"]


def test_files_tree_lists_root(client, tmp_path, monkeypatch):
    monkeypatch.setenv("CG_PROJECT_ROOT", str(tmp_path))
    (tmp_path / "a.txt").write_text("A", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.py").write_text("B", encoding="utf-8")
    r = client.get("/api/files/tree")
    assert r.status_code == 200
    data = r.json()
    names = [e["name"] for e in data["entries"]]
    assert "a.txt" in names
    assert "sub" in names


def test_files_tree_blocks_traversal(client, tmp_path, monkeypatch):
    monkeypatch.setenv("CG_PROJECT_ROOT", str(tmp_path))
    r = client.get("/api/files/tree?path=../..")
    assert r.status_code == 403


def test_files_content_read(client, tmp_path, monkeypatch):
    monkeypatch.setenv("CG_PROJECT_ROOT", str(tmp_path))
    (tmp_path / "hello.md").write_text("# hi\n", encoding="utf-8")
    r = client.get("/api/files/content?path=hello.md")
    assert r.status_code == 200
    assert r.json()["content"] == "# hi\n"


def test_files_content_blocks_traversal(client, tmp_path, monkeypatch):
    monkeypatch.setenv("CG_PROJECT_ROOT", str(tmp_path))
    r = client.get("/api/files/content?path=../etc/passwd")
    assert r.status_code in {403, 404}


def test_files_save_round_trip(client, tmp_path, monkeypatch):
    monkeypatch.setenv("CG_PROJECT_ROOT", str(tmp_path))
    p = tmp_path / "edit-me.txt"
    p.write_text("original", encoding="utf-8")
    r = client.put("/api/files/content",
                     json={"path": "edit-me.txt", "content": "updated"})
    assert r.status_code == 200
    assert p.read_text(encoding="utf-8") == "updated"


def test_files_save_blocks_creating_new_file(client, tmp_path, monkeypatch):
    """Save endpoint edits only — creating new files needs a separate
    explicit gesture."""
    monkeypatch.setenv("CG_PROJECT_ROOT", str(tmp_path))
    r = client.put("/api/files/content",
                     json={"path": "brand-new.txt", "content": "nope"})
    assert r.status_code == 404


def test_files_save_blocks_traversal(client, tmp_path, monkeypatch):
    monkeypatch.setenv("CG_PROJECT_ROOT", str(tmp_path))
    r = client.put("/api/files/content",
                     json={"path": "../escape.txt", "content": "x"})
    assert r.status_code == 403


def test_workflow_import_inline_json(client, tmp_path, monkeypatch):
    """POST /api/workflows/import with body.json saves + returns spec."""
    monkeypatch.setattr(dash, "WORKFLOWS_DIR", tmp_path)
    payload = {"json": {
        "title": "Imported flow",
        "spec": [{"agent": "claude", "label": "x", "prompt": "hi"}],
    }}
    r = client.post("/api/workflows/import", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "Imported flow"
    assert len(body["spec"]) == 1
    # Saved on disk under sanitized name
    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1


def test_workflow_import_from_path(client, tmp_path, monkeypatch):
    monkeypatch.setattr(dash, "WORKFLOWS_DIR", tmp_path)
    src = tmp_path / "ext.json"
    src.write_text(json.dumps({
        "title": "From file",
        "spec": [{"agent": "gemini", "label": "g", "prompt": "yo"}],
    }), encoding="utf-8")
    r = client.post("/api/workflows/import", json={"path": str(src)})
    assert r.status_code == 200
    assert r.json()["title"] == "From file"


def test_workflow_import_rejects_invalid(client, tmp_path, monkeypatch):
    monkeypatch.setattr(dash, "WORKFLOWS_DIR", tmp_path)
    # No json or path
    r = client.post("/api/workflows/import", json={})
    assert r.status_code == 400
    # Empty spec
    r = client.post("/api/workflows/import",
                     json={"json": {"title": "x", "spec": []}})
    assert r.status_code == 400
    # Non-existent path
    r = client.post("/api/workflows/import",
                     json={"path": str(tmp_path / "nope.json")})
    assert r.status_code == 404


def test_workflow_save_load_delete_cycle(client, tmp_path, monkeypatch):
    """End-to-end: PUT a workflow, GET it back, list it, DELETE it."""
    monkeypatch.setattr(dash, "WORKFLOWS_DIR", tmp_path)

    body = {"title": "smoke flow", "spec": [
        {"agent": "claude", "label": "a", "prompt": "x"}
    ]}
    r = client.put("/api/workflows/smoke-flow", json=body)
    assert r.status_code == 200
    assert r.json()["saved"] is True

    r = client.get("/api/workflows")
    assert r.status_code == 200
    listing = r.json()["workflows"]
    assert any(w["name"] == "smoke-flow" for w in listing)

    r = client.get("/api/workflows/smoke-flow")
    assert r.status_code == 200
    fetched = r.json()
    assert fetched["title"] == "smoke flow"
    assert fetched["spec"][0]["agent"] == "claude"

    r = client.delete("/api/workflows/smoke-flow")
    assert r.status_code == 200
    assert r.json()["deleted"] is True

    r = client.get("/api/workflows/smoke-flow")
    assert r.status_code == 404


def test_workflow_put_rejects_bad_body(client, tmp_path, monkeypatch):
    monkeypatch.setattr(dash, "WORKFLOWS_DIR", tmp_path)
    r = client.put("/api/workflows/bad", json={"title": "x"})
    assert r.status_code == 400
    r = client.put("/api/workflows/bad", json={"spec": "not-an-array"})
    assert r.status_code == 400


def test_workflow_name_sanitization(client, tmp_path, monkeypatch):
    """Slashes, spaces, etc. in the name must not escape WORKFLOWS_DIR."""
    monkeypatch.setattr(dash, "WORKFLOWS_DIR", tmp_path)
    body = {"title": "x", "spec": [{"agent": "claude", "label": "a", "prompt": "y"}]}
    r = client.put("/api/workflows/has spaces & special!chars", json=body)
    assert r.status_code == 200
    # Ensure a sanitized file exists (one containing the slugged stem)
    matching = [p for p in tmp_path.glob("*.json") if "spaces" in p.name and "&" not in p.name]
    assert matching, f"no sanitized workflow file found; got {list(tmp_path.glob('*.json'))}"
    assert " " not in matching[0].name
    assert "&" not in matching[0].name


def test_extract_openai_compatible_response():
    raw = json.dumps({
        "choices": [{"message": {"content": "hello world"}}],
        "usage": {"total_tokens": 12},
    })
    out = dash._extract_response_text(raw, {})
    assert out == "hello world"


def test_extract_anthropic_native_response():
    raw = json.dumps({
        "content": [
            {"type": "text", "text": "first part"},
            {"type": "text", "text": "second part"},
        ],
        "model": "claude-sonnet-4-6",
    })
    out = dash._extract_response_text(raw, {"anthropic_native": True})
    assert out == "first part\nsecond part"


def test_extract_google_native_response():
    raw = json.dumps({
        "candidates": [{
            "content": {"parts": [{"text": "from gemini api"}]},
        }],
    })
    out = dash._extract_response_text(raw, {"google_native": True})
    assert out == "from gemini api"


def test_extract_handles_error_payload():
    raw = json.dumps({"error": {"type": "rate_limit", "message": "slow down"}})
    out = dash._extract_response_text(raw, {"anthropic_native": True})
    assert "anthropic error" in out
    assert "rate_limit" in out


def test_extract_falls_back_to_raw_on_invalid_json():
    raw = "not actually json {oops"
    out = dash._extract_response_text(raw, {})
    assert out == raw


def test_http_runner_missing_api_key_marks_failed(client, monkeypatch):
    """If the env var named in http.api_key_env is empty, the agent
    should mark itself failed with exit_code 401 — not crash."""
    monkeypatch.setitem(dash.AGENT_KINDS, "test-http", {
        "label": "test http", "family": "glm", "summary": "test",
        "runner": "http",
        "http": {
            "endpoint": "https://example.invalid/v1",
            "model": "test",
            "api_key_env": "DEFINITELY_NOT_SET_TEST_VAR",
            "headers": {},
        },
    })
    monkeypatch.delenv("DEFINITELY_NOT_SET_TEST_VAR", raising=False)
    r = client.post("/api/runs", json={
        "title": "no key",
        "spec": [{"agent": "test-http", "label": "x", "prompt": "y"}],
    })
    assert r.status_code == 200
    run_id = r.json()["id"]
    import time
    for _ in range(40):
        body = client.get(f"/api/runs/{run_id}").json()
        if all(a["status"] in {"done", "failed"} for a in body["agents"]):
            break
        time.sleep(0.1)
    assert body["agents"][0]["status"] == "failed"
    assert body["agents"][0]["exit_code"] == 401


def test_http_runner_calls_provider_endpoint(client, monkeypatch):
    """Mock urllib.request.urlopen and verify the runner builds an
    OpenAI-compatible request with the right headers + body, then
    parses the response correctly."""
    captured: dict[str, Any] = {}

    class _MockResp:
        status = 200
        def __init__(self, body: bytes):
            self._body = body
        def read(self) -> bytes:
            return self._body
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    def mock_urlopen(req, timeout=180):
        captured["url"] = req.full_url
        captured["headers"] = dict(req.header_items())
        captured["body"] = req.data.decode("utf-8")
        body = json.dumps({"choices": [{"message": {"content": "PROVIDER PONG"}}]})
        return _MockResp(body.encode("utf-8"))

    monkeypatch.setenv("MOCK_PROVIDER_KEY", "sk-test-12345")
    monkeypatch.setitem(dash.AGENT_KINDS, "mock-provider", {
        "label": "mock", "family": "glm", "summary": "test",
        "runner": "http",
        "http": {
            "endpoint": "https://mock-provider.example/v1/chat/completions",
            "model": "mock-model-1",
            "api_key_env": "MOCK_PROVIDER_KEY",
            "headers": {"X-Custom": "yes"},
        },
    })

    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    r = client.post("/api/runs", json={
        "title": "mock provider run",
        "spec": [{"agent": "mock-provider", "label": "p", "prompt": "say hi"}],
    })
    run_id = r.json()["id"]
    import time
    for _ in range(40):
        body = client.get(f"/api/runs/{run_id}").json()
        if all(a["status"] in {"done", "failed"} for a in body["agents"]):
            break
        time.sleep(0.1)

    assert body["agents"][0]["status"] == "done"
    log = client.get(f"/api/runs/{run_id}/output/p").json()["log"]
    assert "PROVIDER PONG" in log
    # Verify the runner shaped the request correctly
    assert captured["url"] == "https://mock-provider.example/v1/chat/completions"
    auth = next(v for k, v in captured["headers"].items() if k.lower() == "authorization")
    assert auth == "Bearer sk-test-12345"
    custom = next(v for k, v in captured["headers"].items() if k.lower() == "x-custom")
    assert custom == "yes"
    body_json = json.loads(captured["body"])
    assert body_json["model"] == "mock-model-1"
    assert body_json["messages"][0]["content"] == "say hi"


def test_run_report_renders_markdown(client):
    """Run a 2-agent workflow then GET /report — must include both labels."""
    r = client.post("/api/runs", json={
        "title": "report test",
        "spec": [
            {"agent": "claude", "label": "alpha", "prompt": "p1"},
            {"agent": "gemini", "label": "beta",  "prompt": "p2"},
        ],
    })
    run_id = r.json()["id"]
    import time
    for _ in range(40):
        body = client.get(f"/api/runs/{run_id}").json()
        if all(a["status"] in {"done", "failed"} for a in body["agents"]):
            break
        time.sleep(0.1)

    r = client.get(f"/api/runs/{run_id}/report")
    assert r.status_code == 200
    md = r.json()["markdown"]
    assert "# CG run report" in md
    assert "## alpha" in md
    assert "## beta" in md
    assert "p1" in md  # prompt embedded
    assert "p2" in md
    assert "CLAUDE-MOCK p1" in md  # output embedded
    assert "GEMINI-MOCK p2" in md


def test_dependency_substitution_combined_with_file_placeholder(client, tmp_path, monkeypatch):
    """A pipeline can mix {{depLabel}} substitution with {{file:...}}."""
    monkeypatch.setenv("CG_PROJECT_ROOT", str(tmp_path))
    (tmp_path / "ctx.md").write_text("EXTERNAL_CONTEXT", encoding="utf-8")
    payload = {
        "title": "combined",
        "spec": [
            {"agent": "claude", "label": "first", "prompt": "step-A"},
            {"agent": "gemini", "label": "second",
             "depends_on": ["first"],
             "prompt": "dep={{first}} ctx={{file:ctx.md}}"},
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

    log = client.get(f"/api/runs/{run_id}/output/second").json()["log"]
    assert "CLAUDE-MOCK step-A" in log  # dep label substituted
    assert "EXTERNAL_CONTEXT" in log    # file placeholder expanded
