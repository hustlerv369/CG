// CG Dashboard frontend — vanilla JS, no framework, no build step.

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

const state = {
  agents: [],
  presets: [],
  currentRun: null,    // { id, title, agents: [...] }
  panels: {},          // label -> {root, log, badges...}
  evtSource: null,
  history: [],
  viewMode: "raw",     // raw | md | diff
};

// ---------- bootstrap ----------

async function init() {
  try {
    const a = await fetch("/api/agents").then(r => r.json());
    state.agents = a.agents;
  } catch {
    setStatus("server unreachable", "err");
    return;
  }
  setStatus("connected", "ok");

  const p = await fetch("/api/presets").then(r => r.json());
  state.presets = p.presets;
  populatePresets();
  await populateWorkflows();
  await refreshHistory();
  ensureOneAgentRow();
  requestNotificationPermission();
  // CLI auto-load: cg dashboard --workflow <name>
  await autoLoadFromUrl();

  setInterval(refreshHistory, 5000);
}

// ---------- saved workflows in localStorage ----------

const WORKFLOW_KEY = "cg.workflows";

function loadWorkflows() {
  try {
    return JSON.parse(localStorage.getItem(WORKFLOW_KEY) || "[]");
  } catch { return []; }
}

function saveWorkflows(list) {
  localStorage.setItem(WORKFLOW_KEY, JSON.stringify(list));
}

async function populateWorkflows() {
  const sel = $("#workflow-select");
  if (!sel) return;
  const browser = loadWorkflows();
  let disk = [];
  try {
    const r = await fetch("/api/workflows");
    if (r.ok) disk = (await r.json()).workflows || [];
  } catch { /* offline mode */ }

  const browserOpts = browser.map((w, i) =>
    `<option value="local:${i}">🌐 ${escapeHtml(w.title || "(untitled)")}</option>`
  ).join("");
  const diskOpts = disk.map(w =>
    `<option value="disk:${escapeHtml(w.name)}">📁 ${escapeHtml(w.title)} (${w.agentCount})</option>`
  ).join("");

  sel.innerHTML = '<option value="">— load saved —</option>' +
    (browserOpts ? `<optgroup label="Browser (this device)">${browserOpts}</optgroup>` : "") +
    (diskOpts ? `<optgroup label="Disk (D:\\CG\\workflows\\)">${diskOpts}</optgroup>` : "");

  sel.onchange = async () => {
    const v = sel.value;
    if (!v) return;
    if (v.startsWith("local:")) {
      const i = parseInt(v.slice(6), 10);
      const w = loadWorkflows()[i];
      if (!w) return;
      loadSpecIntoDesigner(w);
    } else if (v.startsWith("disk:")) {
      const name = v.slice(5);
      try {
        const r = await fetch(`/api/workflows/${encodeURIComponent(name)}`);
        if (!r.ok) { alert("Failed to load workflow"); return; }
        loadSpecIntoDesigner(await r.json());
      } catch (e) { alert("Network error: " + e); }
    }
  };
}

function loadSpecIntoDesigner(w) {
  $("#run-title").value = w.title || "";
  $("#agent-rows").innerHTML = "";
  (w.spec || []).forEach(addAgentRow);
}

async function saveWorkflowToDisk() {
  const title = $("#run-title").value.trim();
  if (!title) { alert("Give the workflow a Title before saving."); return; }
  const spec = readSpec();
  if (!spec.length) { alert("Add at least one agent before saving."); return; }
  const safeName = title.toLowerCase()
    .replace(/[^a-z0-9._-]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80) || "workflow";
  try {
    const r = await fetch(`/api/workflows/${encodeURIComponent(safeName)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, spec }),
    });
    if (!r.ok) { alert("Save failed: " + (await r.text())); return; }
    setStatus(`saved 📁 ${safeName}.json`, "ok");
    setTimeout(() => setStatus("connected", "ok"), 2000);
    await populateWorkflows();
  } catch (e) {
    alert("Network error: " + e);
  }
}

async function importWorkflowFromPaste() {
  const text = prompt(
    "Paste workflow JSON here.\n\n" +
    'Schema: { "title": "...", "spec": [{ "agent": "claude-sonnet-4-6", ' +
    '"label": "...", "depends_on": [], "prompt": "..." }] }'
  );
  if (!text || !text.trim()) return;
  let data;
  try { data = JSON.parse(text); }
  catch (e) { alert("Not valid JSON: " + e); return; }
  await sendImport({ json: data });
}

async function importWorkflowFromFile(ev) {
  const file = ev.target.files && ev.target.files[0];
  if (!file) return;
  const text = await file.text();
  let data;
  try { data = JSON.parse(text); }
  catch (e) { alert("Not valid JSON: " + e); return; }
  await sendImport({ json: data });
  ev.target.value = "";  // allow re-import same file
}

async function sendImport(body) {
  try {
    const r = await fetch("/api/workflows/import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!r.ok) {
      const err = await r.text();
      alert("Import failed: " + err);
      return;
    }
    const data = await r.json();
    setStatus(`imported "${data.title}"`, "ok");
    setTimeout(() => setStatus("connected", "ok"), 2000);
    await populateWorkflows();
    loadSpecIntoDesigner({ title: data.title, spec: data.spec });
  } catch (e) { alert("Network error: " + e); }
}

async function autoLoadFromUrl() {
  // Support  /?workflow=<name>  for cg dashboard --workflow <name>
  const params = new URLSearchParams(window.location.search);
  const wf = params.get("workflow");
  if (!wf) return;
  try {
    let url;
    if (wf.endsWith(".json") || wf.includes("/") || wf.includes("\\")) {
      // Treat as path → ask backend to read it
      const r = await fetch("/api/workflows/import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: wf }),
      });
      if (r.ok) {
        const data = await r.json();
        loadSpecIntoDesigner({ title: data.title, spec: data.spec });
        await populateWorkflows();
        setStatus(`auto-loaded "${data.title}"`, "ok");
        setTimeout(() => setStatus("connected", "ok"), 2500);
      }
    } else {
      // Treat as saved workflow name
      const r = await fetch(`/api/workflows/${encodeURIComponent(wf)}`);
      if (r.ok) {
        loadSpecIntoDesigner(await r.json());
        setStatus(`auto-loaded "${wf}"`, "ok");
        setTimeout(() => setStatus("connected", "ok"), 2500);
      }
    }
  } catch (e) { /* ignore — no workflow auto-load */ }
}

async function deleteSelectedWorkflowEither() {
  const sel = $("#workflow-select");
  const v = sel.value;
  if (!v) { alert("Pick a saved workflow first."); return; }
  if (v.startsWith("local:")) {
    deleteSelectedWorkflow();
    return;
  }
  if (v.startsWith("disk:")) {
    const name = v.slice(5);
    if (!confirm(`Delete workflow "${name}" from disk?`)) return;
    try {
      const r = await fetch(`/api/workflows/${encodeURIComponent(name)}`, { method: "DELETE" });
      if (!r.ok) { alert("Delete failed"); return; }
      setStatus(`deleted 📁 ${name}`, "ok");
      setTimeout(() => setStatus("connected", "ok"), 1500);
      await populateWorkflows();
    } catch (e) { alert("Network error: " + e); }
  }
}

function saveCurrentWorkflow() {
  const title = $("#run-title").value.trim();
  if (!title) {
    alert("Give the workflow a Title before saving.");
    return;
  }
  const spec = readSpec();
  if (!spec.length) {
    alert("Add at least one agent before saving.");
    return;
  }
  const list = loadWorkflows();
  // upsert on title
  const existing = list.findIndex(w => w.title === title);
  const entry = { title, spec, savedAt: Date.now() };
  if (existing >= 0) list[existing] = entry; else list.push(entry);
  saveWorkflows(list);
  populateWorkflows();
  setStatus(`saved "${title}"`, "ok");
  setTimeout(() => setStatus("connected", "ok"), 1500);
}

function deleteSelectedWorkflow() {
  const sel = $("#workflow-select");
  const i = parseInt(sel.value, 10);
  if (isNaN(i)) {
    alert("Pick a saved workflow first.");
    return;
  }
  const list = loadWorkflows();
  const removed = list.splice(i, 1)[0];
  saveWorkflows(list);
  populateWorkflows();
  setStatus(`deleted "${removed.title}"`, "ok");
  setTimeout(() => setStatus("connected", "ok"), 1500);
}

// ---------- browser notifications ----------

function requestNotificationPermission() {
  if (!("Notification" in window)) return;
  if (Notification.permission === "default") {
    Notification.requestPermission();
  }
}

function notify(title, body) {
  if (!("Notification" in window)) return;
  if (Notification.permission !== "granted") return;
  if (document.hasFocus()) return;  // don't notify if user is looking
  try {
    new Notification(title, { body, silent: false });
  } catch { /* ignore */ }
}

function setStatus(msg, klass) {
  const el = $("#server-status");
  el.textContent = msg;
  el.className = `status ${klass || ""}`;
}

function populatePresets() {
  const sel = $("#preset-select");
  sel.innerHTML = '<option value="">— pick a preset —</option>' +
    state.presets.map(p =>
      `<option value="${p.id}">${escapeHtml(p.title)}</option>`
    ).join("");
  sel.onchange = () => {
    const preset = state.presets.find(p => p.id === sel.value);
    if (!preset) return;
    $("#run-title").value = preset.title;
    $("#agent-rows").innerHTML = "";
    preset.spec.forEach(addAgentRow);
  };
}

// ---------- agent row designer ----------

function buildAgentSelectOptions() {
  // Group models by family (claude, gemini, other) into <optgroup>s.
  const groups = {};
  state.agents.forEach(a => {
    const fam = a.family || "other";
    (groups[fam] = groups[fam] || []).push(a);
  });
  const familyLabels = {
    claude: "Claude (Pro)",
    gemini: "Gemini (Google)",
    other: "Other",
  };
  const order = ["claude", "gemini", "other"];
  return order
    .filter(f => groups[f])
    .map(f => `
      <optgroup label="${escapeHtml(familyLabels[f] || f)}">
        ${groups[f].map(a =>
          `<option value="${a.id}" title="${escapeHtml(a.summary || '')}">${escapeHtml(a.label)}</option>`
        ).join("")}
      </optgroup>
    `).join("");
}

function addAgentRow(spec = {}) {
  const tpl = document.createElement("div");
  tpl.className = "agent-row";
  tpl.innerHTML = `
    <div class="agent-row-head">
      <select class="agent-select" title="Pick a model">
        ${buildAgentSelectOptions()}
      </select>
      <input type="text" class="label" placeholder="label (e.g. design)" />
      <button type="button" class="remove" title="Remove">×</button>
    </div>
    <input type="text" class="depends_on" placeholder="depends_on (comma-separated labels)" />
    <textarea class="prompt" placeholder="Prompt — use {{label}} to inject a dependency's output"></textarea>
  `;
  const sel = tpl.querySelector(".agent-select");
  if (spec.agent) {
    // Tolerate legacy ids ("claude" / "gemini") by matching against options
    const opts = Array.from(sel.options).map(o => o.value);
    if (opts.includes(spec.agent)) sel.value = spec.agent;
    else if (spec.agent === "claude" && opts.includes("claude-sonnet-4-6")) sel.value = "claude-sonnet-4-6";
    else if (spec.agent === "gemini" && opts.includes("gemini-pro")) sel.value = "gemini-pro";
  }
  tpl.querySelector(".label").value = spec.label || "";
  tpl.querySelector(".prompt").value = spec.prompt || "";
  tpl.querySelector(".depends_on").value = (spec.depends_on || []).join(",");
  tpl.querySelector(".remove").onclick = () => tpl.remove();
  $("#agent-rows").appendChild(tpl);
}

function ensureOneAgentRow() {
  if ($$(".agent-row").length === 0) addAgentRow();
}

function readSpec() {
  return $$(".agent-row").map((row, i) => ({
    agent: row.querySelector(".agent-select").value,
    label: row.querySelector(".label").value.trim() || `agent-${i + 1}`,
    depends_on: (row.querySelector(".depends_on").value || "")
      .split(",").map(s => s.trim()).filter(Boolean),
    prompt: row.querySelector(".prompt").value,
  }));
}

// ---------- run lifecycle ----------

async function startRun() {
  const spec = readSpec().filter(s => s.prompt.trim().length > 0);
  if (spec.length === 0) {
    alert("Add at least one agent with a non-empty prompt.");
    return;
  }
  const title = $("#run-title").value.trim() || "untitled";
  const btn = $("#run-btn");
  btn.disabled = true;
  btn.textContent = "starting…";

  let runId;
  try {
    const r = await fetch("/api/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, spec }),
    });
    if (!r.ok) {
      const err = await r.text();
      alert(`Server error: ${err}`);
      return;
    }
    const data = await r.json();
    runId = data.id;
  } finally {
    btn.disabled = false;
    btn.textContent = "▶ Run";
  }

  await openRun(runId);
  await refreshHistory();
}

async function openRun(runId) {
  if (state.evtSource) {
    state.evtSource.close();
    state.evtSource = null;
  }
  const meta = await fetch(`/api/runs/${runId}`).then(r => r.json());
  state.currentRun = meta;

  $("#run-title-display").textContent = meta.title;
  $("#run-meta").textContent = `id ${meta.id} · ${meta.agents.length} agents · started ${formatTime(meta.created)}`;
  // Toolbar: cancel + re-run buttons
  let tools = $("#run-tools");
  if (!tools) {
    tools = document.createElement("div");
    tools.id = "run-tools";
    tools.className = "run-tools";
    $(".monitor-header").appendChild(tools);
  }
  const liveSpec = meta.agents.map(a => ({
    agent: a.agent, label: a.label,
    depends_on: a.depends_on || [],
    prompt: "" /* original prompt not exposed by API; rerun uses spec from storage */
  }));
  tools.innerHTML = `
    <button class="ghost" id="cancel-btn">⨯ Cancel</button>
    <button class="ghost" id="rerun-btn">↻ Reload</button>
    <button class="ghost" id="export-btn">⬇ Export .md</button>
  `;
  tools.querySelector("#cancel-btn").onclick = async () => {
    if (!confirm("Cancel this run? Running agents will be killed.")) return;
    await fetch(`/api/runs/${meta.id}`, { method: "DELETE" });
  };
  tools.querySelector("#export-btn").onclick = async () => {
    try {
      const r = await fetch(`/api/runs/${meta.id}/report`);
      if (!r.ok) { alert("Export failed"); return; }
      const data = await r.json();
      const blob = new Blob([data.markdown], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `cg-${data.id}-${(data.title || "run").replace(/[^a-z0-9]+/gi, "-").toLowerCase()}.md`;
      document.body.appendChild(a); a.click();
      setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 100);
    } catch (e) { alert("Network error: " + e); }
  };
  tools.querySelector("#rerun-btn").onclick = () => {
    // Reload this run's spec into the designer (prompts intact for editing)
    $("#run-title").value = meta.title + " (rerun)";
    $("#agent-rows").innerHTML = "";
    (meta.spec || []).forEach(a => addAgentRow({
      agent: a.agent, label: a.label,
      depends_on: a.depends_on || [],
      prompt: a.prompt || "",
    }));
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  // Build agent panels
  const grid = $("#agent-grid");
  grid.innerHTML = "";
  state.panels = {};
  meta.agents.forEach(a => {
    const panel = buildPanel(a);
    grid.appendChild(panel.root);
    state.panels[a.label] = panel;
  });

  // Highlight in history
  $$("#history li").forEach(li => li.classList.toggle("active", li.dataset.runId === runId));

  // Start SSE
  const es = new EventSource(`/api/runs/${runId}/stream`);
  state.evtSource = es;
  es.addEventListener("status", (e) => handleStatus(JSON.parse(e.data)));
  es.addEventListener("snapshot", (e) => handleSnapshot(JSON.parse(e.data)));
  es.addEventListener("log", (e) => handleLog(JSON.parse(e.data)));
  es.addEventListener("done", () => {
    es.close();
    state.evtSource = null;
    refreshHistory();
    // Browser notification when run completes (if user has tab in background)
    const failed = Object.values(state.panels)
      .filter(p => p.statusBadge.classList.contains("failed")).length;
    const total = Object.keys(state.panels).length;
    notify(
      failed === 0 ? "✅ CG run complete" : `⚠️ CG run finished (${failed}/${total} failed)`,
      meta.title
    );
  });
  es.onerror = () => { /* ignore — server may close stream when run done */ };
}

function familyOf(agentId) {
  const a = (state.agents || []).find(x => x.id === agentId);
  if (a && a.family) return a.family;
  if (typeof agentId === "string") {
    if (agentId.startsWith("claude")) return "claude";
    if (agentId.startsWith("gemini")) return "gemini";
  }
  return "other";
}

function shortAgentLabel(agentId) {
  const a = (state.agents || []).find(x => x.id === agentId);
  if (a) return a.label;
  return agentId;
}

function buildPanel(agent) {
  const root = document.createElement("div");
  root.className = "agent-panel";
  const depsHtml = (agent.depends_on && agent.depends_on.length)
    ? `<span class="deps">← ${agent.depends_on.map(escapeHtml).join(", ")}</span>` : "";
  const fam = familyOf(agent.agent);
  const modelLabel = shortAgentLabel(agent.agent);
  root.innerHTML = `
    <div class="agent-panel-head">
      <div class="title">${escapeHtml(agent.label)} ${depsHtml}</div>
      <div class="badges">
        <span class="badge ${fam}" title="${escapeHtml(agent.agent)}">${escapeHtml(modelLabel)}</span>
        <span class="badge status ${agent.status}">${agent.status}</span>
      </div>
    </div>
    <div class="agent-panel-log"></div>
    <div class="agent-panel-foot">
      <span class="bytes">0 chars</span>
      <button class="copy-btn" title="Copy log to clipboard">copy</button>
      <span class="exit"></span>
    </div>
  `;
  const logEl = root.querySelector(".agent-panel-log");
  root.querySelector(".copy-btn").onclick = () => {
    navigator.clipboard.writeText(logEl.textContent || "");
    const btn = root.querySelector(".copy-btn");
    btn.textContent = "✓"; setTimeout(() => btn.textContent = "copy", 1200);
  };
  return {
    root,
    log: logEl,
    statusBadge: root.querySelector(".badge.status"),
    bytesEl: root.querySelector(".bytes"),
    exitEl: root.querySelector(".exit"),
  };
}

function handleStatus(d) {
  const p = state.panels[d.label];
  if (!p) return;
  p.statusBadge.textContent = d.status;
  p.statusBadge.className = `badge status ${d.status}`;
  if (d.exit_code !== null && d.exit_code !== undefined) {
    p.exitEl.textContent = `exit ${d.exit_code}`;
  }
}

function handleSnapshot(d) {
  const p = state.panels[d.label];
  if (!p) return;
  p.rawBuffer = d.log;
  rerenderPanel(p);
}

function handleLog(d) {
  const p = state.panels[d.label];
  if (!p) return;
  // Append to the canonical raw buffer
  p.rawBuffer = (p.rawBuffer || "") + (p.rawBuffer ? "\n" : "") + d.line;
  rerenderPanel(p);
}

function rerenderPanel(p) {
  const text = p.rawBuffer || "";
  p.bytesEl.textContent = `${text.length} chars`;
  const nearBottom = (p.log.scrollHeight - p.log.scrollTop - p.log.clientHeight) < 40;
  if (state.viewMode === "md" && window.marked) {
    p.log.classList.add("md-rendered");
    p.log.classList.remove("diff-rendered");
    p.log.innerHTML = window.marked.parse(text);
    if (window.hljs) p.log.querySelectorAll("pre code").forEach(b => window.hljs.highlightElement(b));
  } else if (state.viewMode === "diff") {
    p.log.classList.add("diff-rendered");
    p.log.classList.remove("md-rendered");
    p.log.innerHTML = renderDiffPlaceholder(p.label, text);
  } else {
    p.log.classList.remove("md-rendered", "diff-rendered");
    p.log.textContent = text;
  }
  if (nearBottom) p.log.scrollTop = p.log.scrollHeight;
}

function renderDiffPlaceholder(label, text) {
  // Diff is meaningful only with 2 panels — actual diff is rendered
  // in renderDiffMode() at the grid level. Per-panel just shows text.
  return escapeHtml(text);
}

function setViewMode(mode) {
  state.viewMode = mode;
  document.querySelectorAll("#view-toggle .seg").forEach(b => {
    b.classList.toggle("active", b.dataset.view === mode);
  });
  const grid = $("#agent-grid");
  if (grid) grid.classList.toggle("diff-grid", mode === "diff" && Object.keys(state.panels).length === 2);

  // Re-render every panel
  Object.values(state.panels).forEach(rerenderPanel);

  // For diff mode with exactly 2 panels, run the diff and inject into both panels
  if (mode === "diff" && Object.keys(state.panels).length === 2) {
    const labels = Object.keys(state.panels);
    const a = state.panels[labels[0]].rawBuffer || "";
    const b = state.panels[labels[1]].rawBuffer || "";
    const diff = computeLineDiff(a, b);
    state.panels[labels[0]].log.innerHTML = diff.left;
    state.panels[labels[1]].log.innerHTML = diff.right;
  }
}

// Tiny LCS-based line diff — enough for two short markdown outputs.
function computeLineDiff(a, b) {
  const A = a.split("\n");
  const B = b.split("\n");
  const m = A.length, n = B.length;
  const dp = Array.from({ length: m + 1 }, () => new Int32Array(n + 1));
  for (let i = m - 1; i >= 0; i--) {
    for (let j = n - 1; j >= 0; j--) {
      if (A[i] === B[j]) dp[i][j] = dp[i + 1][j + 1] + 1;
      else dp[i][j] = Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }
  const left = [], right = [];
  let i = 0, j = 0;
  while (i < m && j < n) {
    if (A[i] === B[j]) {
      left.push(`<span class="diff-eq">  ${escapeHtml(A[i])}</span>`);
      right.push(`<span class="diff-eq">  ${escapeHtml(B[j])}</span>`);
      i++; j++;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      left.push(`<span class="diff-rem">- ${escapeHtml(A[i])}</span>`);
      right.push(`<span class="diff-eq">  </span>`);
      i++;
    } else {
      left.push(`<span class="diff-eq">  </span>`);
      right.push(`<span class="diff-add">+ ${escapeHtml(B[j])}</span>`);
      j++;
    }
  }
  while (i < m) { left.push(`<span class="diff-rem">- ${escapeHtml(A[i++])}</span>`); right.push(`<span class="diff-eq">  </span>`); }
  while (j < n) { left.push(`<span class="diff-eq">  </span>`); right.push(`<span class="diff-add">+ ${escapeHtml(B[j++])}</span>`); }
  return { left: left.join(""), right: right.join("") };
}

// ---------- history sidebar ----------

async function refreshHistory() {
  try {
    const data = await fetch("/api/runs").then(r => r.json());
    state.history = data.runs;
    const ul = $("#history");
    ul.innerHTML = state.history.map(r => `
      <li data-run-id="${r.id}" class="${state.currentRun && state.currentRun.id === r.id ? 'active' : ''}">
        <div class="h-title">${escapeHtml(r.title)}</div>
        <div class="h-meta">
          ${r.agents.length} agents · ${r.finished ? '✓ done' : '⋯ running'} ·
          ${formatTime(r.created)}
        </div>
      </li>
    `).join("") || '<li style="color: var(--fg-dim); cursor: default;">No runs yet.</li>';
    $$("#history li[data-run-id]").forEach(li => {
      li.onclick = () => openRun(li.dataset.runId);
    });
  } catch {
    /* ignore */
  }
}

// ---------- helpers ----------

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));
}

function formatTime(ts) {
  if (!ts) return "—";
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString();
}

// ---------- wire up buttons ----------

// ---------- editor tab (file tree + CodeMirror) ----------

const editorState = {
  cm: null,
  currentPath: null,
  originalContent: "",
  dirty: false,
  expandedDirs: new Set(),
};

function modeForPath(path) {
  const ext = (path.split(".").pop() || "").toLowerCase();
  return {
    "py": "python",
    "js": "javascript", "mjs": "javascript", "ts": "javascript",
    "tsx": "javascript", "jsx": "javascript",
    "md": "markdown",
    "html": "htmlmixed", "htm": "htmlmixed",
    "css": "css",
    "json": { name: "javascript", json: true },
    "xml": "xml", "svg": "xml",
  }[ext] || null;
}

function ensureCodeMirror() {
  if (editorState.cm) return editorState.cm;
  const host = $("#editor-host");
  $("#editor-empty").style.display = "none";
  editorState.cm = CodeMirror(host, {
    value: "",
    theme: "material-darker",
    lineNumbers: true,
    autoCloseBrackets: true,
    matchBrackets: true,
    indentUnit: 2,
    tabSize: 2,
    extraKeys: {
      "Ctrl-S": () => editorSave(),
      "Cmd-S":  () => editorSave(),
    },
  });
  editorState.cm.on("change", () => {
    const cur = editorState.cm.getValue();
    const dirty = cur !== editorState.originalContent;
    if (dirty !== editorState.dirty) {
      editorState.dirty = dirty;
      $("#editor-dirty").hidden = !dirty;
      $("#editor-save-btn").disabled = !dirty;
      $("#editor-revert-btn").disabled = !dirty;
    }
  });
  return editorState.cm;
}

async function loadFileTree(path = "") {
  try {
    const r = await fetch(`/api/files/tree?path=${encodeURIComponent(path)}`);
    if (!r.ok) {
      $("#file-tree").innerHTML =
        `<li style="color:var(--error);padding:8px 14px">${(await r.text()).slice(0, 200)}</li>`;
      return;
    }
    const data = await r.json();
    $("#editor-root-label").textContent = data.root.replace(/^.*[\\/]/, "");
    $("#editor-root-label").title = data.root;
    if ($("#editor-root-display")) $("#editor-root-display").textContent = data.root;

    const root = document.createDocumentFragment();
    data.entries.forEach(entry => root.appendChild(buildFileTreeNode(entry)));
    const ul = $("#file-tree");
    ul.innerHTML = "";
    ul.appendChild(root);
  } catch (e) {
    $("#file-tree").innerHTML =
      `<li style="color:var(--error);padding:8px 14px">network error: ${e}</li>`;
  }
}

function buildFileTreeNode(entry) {
  const li = document.createElement("li");
  li.className = entry.is_dir ? "dir" : "file";
  li.dataset.path = entry.path;
  const icon = entry.is_dir ? "▸" : "·";
  li.innerHTML = `<span class="icon">${icon}</span><span>${escapeHtml(entry.name)}</span>`;
  li.onclick = async (ev) => {
    ev.stopPropagation();
    if (entry.is_dir) {
      // toggle expand
      const existing = li.querySelector(":scope > .nested");
      if (existing) {
        existing.remove();
        li.querySelector(".icon").textContent = "▸";
        editorState.expandedDirs.delete(entry.path);
        return;
      }
      const r = await fetch(`/api/files/tree?path=${encodeURIComponent(entry.path)}`);
      if (!r.ok) return;
      const data = await r.json();
      const nested = document.createElement("ul");
      nested.className = "nested";
      data.entries.forEach(child => nested.appendChild(buildFileTreeNode(child)));
      li.appendChild(nested);
      li.querySelector(".icon").textContent = "▾";
      editorState.expandedDirs.add(entry.path);
    } else {
      await openFileInEditor(entry.path);
      document.querySelectorAll(".file-tree li.active")
        .forEach(x => x.classList.remove("active"));
      li.classList.add("active");
    }
  };
  return li;
}

async function openFileInEditor(path) {
  if (editorState.dirty) {
    if (!confirm("Discard unsaved changes?")) return;
  }
  try {
    const r = await fetch(`/api/files/content?path=${encodeURIComponent(path)}`);
    if (!r.ok) {
      alert(`Open failed: ${await r.text()}`);
      return;
    }
    const data = await r.json();
    const cm = ensureCodeMirror();
    cm.setValue(data.content);
    cm.setOption("mode", modeForPath(path));
    editorState.originalContent = data.content;
    editorState.currentPath = path;
    editorState.dirty = false;
    $("#editor-current-file").textContent = path;
    $("#editor-dirty").hidden = true;
    $("#editor-save-btn").disabled = true;
    $("#editor-revert-btn").disabled = true;
  } catch (e) { alert("Network error: " + e); }
}

async function editorSave() {
  if (!editorState.currentPath || !editorState.dirty || !editorState.cm) return;
  const content = editorState.cm.getValue();
  try {
    const r = await fetch("/api/files/content", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: editorState.currentPath, content }),
    });
    if (!r.ok) {
      alert(`Save failed: ${await r.text()}`);
      return;
    }
    editorState.originalContent = content;
    editorState.dirty = false;
    $("#editor-dirty").hidden = true;
    $("#editor-save-btn").disabled = true;
    $("#editor-revert-btn").disabled = true;
    setStatus(`saved ${editorState.currentPath}`, "ok");
    setTimeout(() => setStatus("connected", "ok"), 1500);
  } catch (e) { alert("Network error: " + e); }
}

function editorRevert() {
  if (!editorState.cm || !editorState.dirty) return;
  if (!confirm("Discard unsaved changes?")) return;
  editorState.cm.setValue(editorState.originalContent);
  editorState.dirty = false;
  $("#editor-dirty").hidden = true;
  $("#editor-save-btn").disabled = true;
  $("#editor-revert-btn").disabled = true;
}

function switchTab(tab) {
  document.querySelectorAll("nav.tabs .tab").forEach(b =>
    b.classList.toggle("active", b.dataset.tab === tab));
  document.querySelectorAll(".tab-pane").forEach(p =>
    p.classList.toggle("active", p.id === `tab-${tab}`));
  if (tab === "editor") {
    if (!$("#file-tree").firstChild) {
      loadFileTree("");
    }
    if (editorState.cm) {
      // CodeMirror needs a refresh after being shown
      setTimeout(() => editorState.cm.refresh(), 50);
    }
  }
}

document.addEventListener("DOMContentLoaded", () => {
  $("#add-agent").onclick = () => addAgentRow();
  $("#run-btn").onclick = startRun;
  // Tab switcher
  document.querySelectorAll("nav.tabs .tab").forEach(b => {
    b.addEventListener("click", () => switchTab(b.dataset.tab));
  });
  // Editor handlers
  if ($("#editor-refresh-btn")) {
    $("#editor-refresh-btn").onclick = () => loadFileTree("");
  }
  if ($("#editor-save-btn")) {
    $("#editor-save-btn").onclick = editorSave;
  }
  if ($("#editor-revert-btn")) {
    $("#editor-revert-btn").onclick = editorRevert;
  }
  $("#clear-btn").onclick = () => {
    $("#agent-rows").innerHTML = "";
    $("#run-title").value = "";
    ensureOneAgentRow();
  };
  if ($("#save-workflow-btn")) {
    $("#save-workflow-btn").onclick = saveCurrentWorkflow;
  }
  if ($("#del-workflow-btn")) {
    $("#del-workflow-btn").onclick = deleteSelectedWorkflowEither;
  }
  if ($("#save-disk-btn")) {
    $("#save-disk-btn").onclick = saveWorkflowToDisk;
  }
  if ($("#import-paste-btn")) {
    $("#import-paste-btn").onclick = importWorkflowFromPaste;
  }
  if ($("#import-file-btn")) {
    $("#import-file-btn").onclick = () => $("#import-file").click();
  }
  if ($("#import-file")) {
    $("#import-file").addEventListener("change", importWorkflowFromFile);
  }
  // View mode segmented control
  document.querySelectorAll("#view-toggle .seg").forEach(b => {
    b.addEventListener("click", () => setViewMode(b.dataset.view));
  });

  // Keyboard shortcuts
  document.addEventListener("keydown", (e) => {
    // Ctrl/Cmd + Enter from anywhere = Run
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      startRun();
    }
    // Ctrl/Cmd + S = context-aware save
    //   - if editor tab is open + a file is dirty: save the file
    //   - otherwise: save the current workflow to localStorage
    if ((e.ctrlKey || e.metaKey) && e.key === "s") {
      e.preventDefault();
      const editorActive = $("#tab-editor")?.classList.contains("active");
      if (editorActive && editorState.dirty) {
        editorSave();
      } else {
        saveCurrentWorkflow();
      }
    }
  });

  init();
});
