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
  populateWorkflows();
  await refreshHistory();
  ensureOneAgentRow();
  requestNotificationPermission();

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

function populateWorkflows() {
  const sel = $("#workflow-select");
  if (!sel) return;
  const items = loadWorkflows();
  sel.innerHTML = '<option value="">— load saved —</option>' +
    items.map((w, i) =>
      `<option value="${i}">${escapeHtml(w.title || "(untitled)")}</option>`
    ).join("");
  sel.onchange = () => {
    const i = parseInt(sel.value, 10);
    if (isNaN(i)) return;
    const w = loadWorkflows()[i];
    if (!w) return;
    $("#run-title").value = w.title || "";
    $("#agent-rows").innerHTML = "";
    (w.spec || []).forEach(addAgentRow);
  };
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
    <button class="ghost" id="rerun-btn">↻ Reload into editor</button>
  `;
  tools.querySelector("#cancel-btn").onclick = async () => {
    if (!confirm("Cancel this run? Running agents will be killed.")) return;
    await fetch(`/api/runs/${meta.id}`, { method: "DELETE" });
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
  p.log.textContent = d.log;
  p.bytesEl.textContent = `${d.log.length} chars`;
  p.log.scrollTop = p.log.scrollHeight;
}

function handleLog(d) {
  const p = state.panels[d.label];
  if (!p) return;
  if (p.log.textContent && !p.log.textContent.endsWith("\n")) {
    p.log.textContent += "\n";
  }
  p.log.textContent += d.line;
  p.bytesEl.textContent = `${p.log.textContent.length} chars`;
  // Auto-scroll if user is near bottom
  const nearBottom = (p.log.scrollHeight - p.log.scrollTop - p.log.clientHeight) < 40;
  if (nearBottom) p.log.scrollTop = p.log.scrollHeight;
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

document.addEventListener("DOMContentLoaded", () => {
  $("#add-agent").onclick = () => addAgentRow();
  $("#run-btn").onclick = startRun;
  $("#clear-btn").onclick = () => {
    $("#agent-rows").innerHTML = "";
    $("#run-title").value = "";
    ensureOneAgentRow();
  };
  if ($("#save-workflow-btn")) {
    $("#save-workflow-btn").onclick = saveCurrentWorkflow;
  }
  if ($("#del-workflow-btn")) {
    $("#del-workflow-btn").onclick = deleteSelectedWorkflow;
  }

  // Keyboard shortcuts
  document.addEventListener("keydown", (e) => {
    // Ctrl/Cmd + Enter from anywhere = Run
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      startRun();
    }
    // Ctrl/Cmd + S = save workflow
    if ((e.ctrlKey || e.metaKey) && e.key === "s") {
      e.preventDefault();
      saveCurrentWorkflow();
    }
  });

  init();
});
