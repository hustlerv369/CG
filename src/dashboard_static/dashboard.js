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
  // K5 — load active workspace's draft (replaces ensureOneAgentRow path
  // unless this is a brand-new browser, in which case the default
  // workspace's empty spec triggers the safety fallback inside applyDraft)
  initWorkspaces();
  ensureOneAgentRow();
  initVisualMode();
  requestNotificationPermission();
  // CLI auto-load: cg dashboard --workflow <name>
  await autoLoadFromUrl();

  setInterval(refreshHistory, 5000);
}

// ---------- K5: workspaces (parallel orchestrator drafts) ---------------
//
// A workspace is one independent draft of the workflow designer (title
// + agent rows). Saved to localStorage so each browser keeps its own
// set of parallel drafts. Switching a workspace captures the current
// draft into the previously-active one before loading the target.

const WS_KEY = "cg.workspaces";
const WS_ACTIVE_KEY = "cg.workspaces.active";

function loadWorkspaces() {
  try {
    const v = JSON.parse(localStorage.getItem(WS_KEY) || "null");
    if (Array.isArray(v) && v.length) return v;
  } catch { /* fall through */ }
  return [{ id: "ws-1", name: "Draft 1", draft: { title: "", spec: [] } }];
}
function saveWorkspaces(list) {
  localStorage.setItem(WS_KEY, JSON.stringify(list));
}
function getActiveWsId() {
  return localStorage.getItem(WS_ACTIVE_KEY) || "ws-1";
}
function setActiveWsId(id) {
  localStorage.setItem(WS_ACTIVE_KEY, id);
}

function captureCurrentDraft() {
  return {
    title: ($("#run-title")?.value || "").trim(),
    spec: readSpec(),
    positions: window.__visPositions || {},  // v16 — visual canvas layout
  };
}

function applyDraft(draft) {
  if (!draft) draft = { title: "", spec: [] };
  if ($("#run-title")) $("#run-title").value = draft.title || "";
  $("#agent-rows").innerHTML = "";
  (draft.spec || []).forEach(s => addAgentRow(s));
  if (($$(".agent-row") || []).length === 0) addAgentRow();
  // v16 — restore saved canvas positions for this workspace
  window.__visPositions = (draft.positions && typeof draft.positions === "object")
    ? { ...draft.positions } : {};
  if (typeof renderVisualCanvas === "function" &&
      $("#visual-pane")?.style.display !== "none") {
    renderVisualCanvas();
  }
}

function persistActiveDraft() {
  const list = loadWorkspaces();
  const id = getActiveWsId();
  const idx = list.findIndex(w => w.id === id);
  if (idx === -1) return;
  list[idx].draft = captureCurrentDraft();
  saveWorkspaces(list);
}

function switchWorkspace(id) {
  persistActiveDraft();
  setActiveWsId(id);
  const list = loadWorkspaces();
  const target = list.find(w => w.id === id) || list[0];
  applyDraft(target.draft);
  renderWorkspaceList();
}

function addWorkspace() {
  persistActiveDraft();
  const list = loadWorkspaces();
  const n = list.length + 1;
  const newWs = { id: `ws-${Date.now().toString(36)}`,
                   name: `Draft ${n}`,
                   draft: { title: "", spec: [] } };
  list.push(newWs);
  saveWorkspaces(list);
  setActiveWsId(newWs.id);
  applyDraft(newWs.draft);
  renderWorkspaceList();
}

function removeWorkspace(id) {
  let list = loadWorkspaces();
  if (list.length <= 1) {
    alert("Can't remove the last workspace.");
    return;
  }
  const ws = list.find(w => w.id === id);
  if (!ws) return;
  if (!confirm(`Delete workspace "${ws.name}"? Its draft will be lost.`)) return;
  list = list.filter(w => w.id !== id);
  saveWorkspaces(list);
  if (getActiveWsId() === id) {
    setActiveWsId(list[0].id);
    applyDraft(list[0].draft);
  }
  renderWorkspaceList();
}

function renameWorkspace(id) {
  const list = loadWorkspaces();
  const ws = list.find(w => w.id === id);
  if (!ws) return;
  const next = prompt("Rename workspace:", ws.name);
  if (next === null) return;
  ws.name = next.trim() || ws.name;
  saveWorkspaces(list);
  renderWorkspaceList();
}

function renderWorkspaceList() {
  const host = $("#ws-list");
  if (!host) return;
  const list = loadWorkspaces();
  const active = getActiveWsId();
  host.innerHTML = "";
  list.forEach(ws => {
    const card = document.createElement("div");
    card.className = "ws-card" + (ws.id === active ? " active" : "");
    card.title = ws.name + " — click to switch, double-click to rename";
    card.innerHTML = `
      <button class="ws-close" title="Delete">×</button>
      <span class="ws-name"></span>
    `;
    card.querySelector(".ws-name").textContent =
      ws.name.length > 8 ? ws.name.slice(0, 8) + "…" : ws.name;
    card.addEventListener("click", e => {
      if (e.target.classList.contains("ws-close")) return;
      if (ws.id !== active) switchWorkspace(ws.id);
    });
    card.addEventListener("dblclick", e => {
      e.preventDefault();
      renameWorkspace(ws.id);
    });
    card.querySelector(".ws-close").addEventListener("click", e => {
      e.stopPropagation();
      removeWorkspace(ws.id);
    });
    host.appendChild(card);
  });
}

function initWorkspaces() {
  // Ensure persistence on page-leave so a refresh keeps the active draft.
  window.addEventListener("beforeunload", persistActiveDraft);
  $("#ws-add-btn")?.addEventListener("click", addWorkspace);
  // Load active workspace's draft as the initial UI state. We do this
  // BEFORE ensureOneAgentRow() so the saved spec is honored.
  const list = loadWorkspaces();
  saveWorkspaces(list);  // self-heal default
  const active = list.find(w => w.id === getActiveWsId()) || list[0];
  if (!list.find(w => w.id === getActiveWsId())) setActiveWsId(active.id);
  applyDraft(active.draft);
  renderWorkspaceList();
}

// ---------- v16: visual canvas (n8n / make.com style) ------------------
//
// State model: the source of truth for the workflow remains the classic
// agent-rows DOM. Visual mode reads via readSpec(), writes back via
// addAgentRow / inline edit. Per-workspace node positions live on
// `window.__visPositions` (mirrored into draft.positions on persist).

const VIEW_MODE_KEY = "cg.viewMode";
const VIS_NODE_W = 200;
const VIS_NODE_H = 110;
const VIS_COL_GAP = 80;
const VIS_ROW_GAP = 40;

function getViewMode() {
  return localStorage.getItem(VIEW_MODE_KEY) || "classic";
}
function setViewMode(mode) {
  localStorage.setItem(VIEW_MODE_KEY, mode);
}

function familyEmoji(family) {
  return ({
    claude: "🅒", gemini: "🅖", browser: "🌐", subworkflow: "🔁",
    opencode: "🅞", deepseek: "🐳", moonshot: "🌙", glm: "🇿",
    qwen: "🅠", llama: "🦙", mistral: "🅼", custom: "🛠",
  }[family] || "•");
}

function topoLayout(spec) {
  // Layered topological layout: column = longest depends_on chain depth.
  const byLabel = Object.fromEntries(spec.map(s => [s.label, s]));
  const depth = {};
  function depthOf(label, seen = new Set()) {
    if (depth[label] !== undefined) return depth[label];
    if (seen.has(label)) return 0;  // cycle guard
    seen.add(label);
    const node = byLabel[label];
    if (!node || !node.depends_on || node.depends_on.length === 0) {
      depth[label] = 0; return 0;
    }
    const d = 1 + Math.max(...node.depends_on.map(d => depthOf(d, seen)));
    depth[label] = d; return d;
  }
  spec.forEach(s => depthOf(s.label));
  // Group by depth
  const cols = {};
  spec.forEach(s => {
    const d = depth[s.label] || 0;
    (cols[d] ||= []).push(s);
  });
  const positions = {};
  Object.keys(cols).sort((a, b) => +a - +b).forEach(d => {
    cols[d].forEach((s, i) => {
      positions[s.label] = {
        x: 30 + (+d) * (VIS_NODE_W + VIS_COL_GAP),
        y: 30 + i * (VIS_NODE_H + VIS_ROW_GAP),
      };
    });
  });
  return positions;
}

function renderVisualCanvas() {
  const svg = document.getElementById("visual-canvas");
  if (!svg) return;
  const nodesLayer = svg.querySelector(".nodes-layer");
  const connsLayer = svg.querySelector(".connections-layer");
  nodesLayer.innerHTML = "";
  connsLayer.innerHTML = "";

  // Source of truth — when a run is open in the monitor, mirror ITS
  // spec (so all 5 agents from a multi-agent pipeline show up); else
  // fall back to the classic agent-rows draft. Without this, opening
  // a 5-agent run from history was leaving Visual showing the 1-row
  // draft on the left and confusing the user about what was running.
  let spec;
  if (state.currentRun && Array.isArray(state.currentRun.spec)
      && state.currentRun.spec.length) {
    // Reuse spec items but normalise to the shape readSpec() returns
    spec = state.currentRun.spec.map((s, i) => ({
      agent: s.agent,
      label: s.label || `agent-${i + 1}`,
      depends_on: Array.isArray(s.depends_on) ? s.depends_on : [],
      streaming: !!s.streaming,
      prompt: s.prompt || "",
    }));
  } else {
    spec = readSpec();
  }

  document.getElementById("visual-empty").style.display =
    spec.length === 0 ? "flex" : "none";
  if (spec.length === 0) return;

  // Resolve positions: saved > auto-layout fallback
  const auto = topoLayout(spec);
  const positions = window.__visPositions = window.__visPositions || {};
  spec.forEach(s => {
    if (!positions[s.label]) positions[s.label] = auto[s.label];
  });
  // Drop positions for labels that no longer exist
  Object.keys(positions).forEach(label => {
    if (!spec.find(s => s.label === label)) delete positions[label];
  });

  // Resize canvas to fit
  const maxX = Math.max(...spec.map(s => (positions[s.label]?.x || 0))) + VIS_NODE_W + 60;
  const maxY = Math.max(...spec.map(s => (positions[s.label]?.y || 0))) + VIS_NODE_H + 60;
  svg.setAttribute("viewBox", `0 0 ${Math.max(800, maxX)} ${Math.max(460, maxY)}`);
  svg.style.width = Math.max(800, maxX) + "px";
  svg.style.height = Math.max(460, maxY) + "px";

  // Draw connections first (under nodes)
  spec.forEach(s => {
    (s.depends_on || []).forEach(dep => {
      const from = positions[dep], to = positions[s.label];
      if (!from || !to) return;
      const x1 = from.x + VIS_NODE_W;
      const y1 = from.y + VIS_NODE_H / 2;
      const x2 = to.x;
      const y2 = to.y + VIS_NODE_H / 2;
      const dx = Math.max(40, (x2 - x1) / 2);
      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("d",
        `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`);
      path.setAttribute("marker-end", "url(#arrowhead)");
      path.dataset.from = dep;
      path.dataset.to = s.label;
      path.addEventListener("click", e => {
        if (!confirm(`Remove dependency ${dep} → ${s.label}?`)) return;
        // Remove dep from target's depends_on row
        const targetRow = $$(".agent-row").find((r, i) =>
          (r.querySelector(".label").value.trim() || `agent-${i + 1}`) === s.label);
        if (targetRow) {
          const dInp = targetRow.querySelector(".depends_on");
          dInp.value = (dInp.value || "")
            .split(",").map(x => x.trim()).filter(x => x && x !== dep)
            .join(",");
        }
        renderVisualCanvas();
      });
      connsLayer.appendChild(path);
    });
  });

  // Draw nodes (foreignObject so we get full HTML+CSS inside SVG)
  spec.forEach(s => {
    const pos = positions[s.label];
    if (!pos) return;
    const fo = document.createElementNS("http://www.w3.org/2000/svg", "foreignObject");
    fo.setAttribute("x", pos.x);
    fo.setAttribute("y", pos.y);
    fo.setAttribute("width", VIS_NODE_W);
    fo.setAttribute("height", VIS_NODE_H + 80);  // extra for edit panel
    fo.dataset.label = s.label;
    const node = document.createElement("div");
    node.className = "vis-node";
    node.dataset.label = s.label;
    const meta = state.agents.find(a => a.id === s.agent);
    node.innerHTML = `
      <div class="vis-node-head">
        <span class="vis-emoji">${familyEmoji(meta?.family)}</span>
        <span class="vis-label">${escapeHtml(s.label || "(unnamed)")}</span>
        <span class="vis-status">queued</span>
        <button class="vis-close" title="Remove">×</button>
      </div>
      <div class="vis-node-model">${escapeHtml(meta?.label || s.agent)}</div>
      <div class="vis-node-prompt">${escapeHtml((s.prompt || "").slice(0, 200))}</div>
      <div class="vis-node-log"></div>
      <div class="vis-node-edit">
        <select class="vne-agent">${buildAgentSelectOptions()}</select>
        <input type="text" class="vne-label" placeholder="label" />
        <input type="text" class="vne-deps" placeholder="depends_on (comma)" />
        <textarea class="vne-prompt" placeholder="prompt"></textarea>
        <div class="row">
          <button type="button" class="primary vne-save">Save</button>
          <button type="button" class="ghost vne-cancel">Cancel</button>
        </div>
      </div>
    `;
    // Set form values from the live spec entry
    node.querySelector(".vne-agent").value = s.agent;
    node.querySelector(".vne-label").value = s.label;
    node.querySelector(".vne-deps").value = (s.depends_on || []).join(",");
    node.querySelector(".vne-prompt").value = s.prompt || "";

    // Click body → toggle edit. Skip if drag started or button clicked.
    node.addEventListener("click", e => {
      if (node.dataset.dragged === "1") { node.dataset.dragged = "0"; return; }
      if (e.target.closest("button, select, input, textarea")) return;
      node.classList.toggle("editing");
    });

    // Edit panel buttons
    node.querySelector(".vne-cancel").onclick = () => node.classList.remove("editing");
    node.querySelector(".vne-save").onclick = () => {
      const newLabel = node.querySelector(".vne-label").value.trim() || s.label;
      const newAgent = node.querySelector(".vne-agent").value;
      const newDeps = node.querySelector(".vne-deps").value.trim();
      const newPrompt = node.querySelector(".vne-prompt").value;
      // Find the matching classic row by label and patch it in place
      const row = $$(".agent-row").find((r, i) =>
        (r.querySelector(".label").value.trim() || `agent-${i + 1}`) === s.label);
      if (row) {
        row.querySelector(".agent-select").value = newAgent;
        row.querySelector(".label").value = newLabel;
        row.querySelector(".depends_on").value = newDeps;
        row.querySelector(".prompt").value = newPrompt;
        // re-fire applyBrowserMode if needed
        if (typeof applyBrowserMode === "function") applyBrowserMode(row, { prompt: newPrompt });
      }
      // Carry position over if label was renamed
      if (newLabel !== s.label && positions[s.label]) {
        positions[newLabel] = positions[s.label];
        delete positions[s.label];
      }
      renderVisualCanvas();
    };

    // Remove
    node.querySelector(".vis-close").onclick = e => {
      e.stopPropagation();
      if (!confirm(`Remove node "${s.label}"?`)) return;
      const row = $$(".agent-row").find((r, i) =>
        (r.querySelector(".label").value.trim() || `agent-${i + 1}`) === s.label);
      if (row) row.remove();
      delete positions[s.label];
      renderVisualCanvas();
    };

    // Drag — pointer-based (works for mouse + touch)
    let dragState = null;
    node.addEventListener("pointerdown", e => {
      if (e.target.closest("button, select, input, textarea")) return;
      if (node.classList.contains("editing")) return;
      dragState = {
        startX: e.clientX, startY: e.clientY,
        origX: positions[s.label].x, origY: positions[s.label].y,
        moved: false,
      };
      node.classList.add("dragging");
      node.setPointerCapture(e.pointerId);
    });
    node.addEventListener("pointermove", e => {
      if (!dragState) return;
      const dx = e.clientX - dragState.startX;
      const dy = e.clientY - dragState.startY;
      if (Math.abs(dx) > 3 || Math.abs(dy) > 3) dragState.moved = true;
      // Scale coordinates by canvas viewport
      const svgRect = svg.getBoundingClientRect();
      const vb = svg.viewBox.baseVal;
      const sx = vb.width / svgRect.width;
      const sy = vb.height / svgRect.height;
      positions[s.label] = {
        x: Math.max(0, dragState.origX + dx * sx),
        y: Math.max(0, dragState.origY + dy * sy),
      };
      fo.setAttribute("x", positions[s.label].x);
      fo.setAttribute("y", positions[s.label].y);
      // Redraw connections live
      drawConnectionsOnly(svg, spec, positions);
    });
    node.addEventListener("pointerup", e => {
      if (dragState && dragState.moved) node.dataset.dragged = "1";
      dragState = null;
      node.classList.remove("dragging");
    });

    fo.appendChild(node);
    nodesLayer.appendChild(fo);
  });
}

function drawConnectionsOnly(svg, spec, positions) {
  const layer = svg.querySelector(".connections-layer");
  layer.innerHTML = "";
  spec.forEach(s => {
    (s.depends_on || []).forEach(dep => {
      const from = positions[dep], to = positions[s.label];
      if (!from || !to) return;
      const x1 = from.x + VIS_NODE_W;
      const y1 = from.y + VIS_NODE_H / 2;
      const x2 = to.x;
      const y2 = to.y + VIS_NODE_H / 2;
      const dx = Math.max(40, (x2 - x1) / 2);
      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("d",
        `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`);
      path.setAttribute("marker-end", "url(#arrowhead)");
      path.dataset.from = dep;
      path.dataset.to = s.label;
      layer.appendChild(path);
    });
  });
}

function visualUpdateAgentStatus(label, status, lastLine) {
  const node = document.querySelector(
    `#visual-pane .vis-node[data-label="${CSS.escape(label)}"]`);
  if (!node) return;
  ["queued", "waiting", "running", "done", "failed", "cancelled"].forEach(s =>
    node.classList.remove("status-" + s));
  if (status) node.classList.add("status-" + status);
  const badge = node.querySelector(".vis-status");
  if (badge && status) badge.textContent = status;
  if (lastLine) {
    const log = node.querySelector(".vis-node-log");
    if (log) log.textContent = lastLine.slice(0, 80);
  }
  // Pulse the connection FROM each completed dep TO this node when running
  if (status === "running") {
    document.querySelectorAll(
      `.connections-layer path[data-to="${CSS.escape(label)}"]`
    ).forEach(p => p.classList.add("flowing"));
  }
  if (status === "done" || status === "failed" || status === "cancelled") {
    document.querySelectorAll(
      `.connections-layer path[data-from="${CSS.escape(label)}"]`
    ).forEach(p => p.classList.remove("flowing"));
  }
}

function openNodePalette() {
  const back = document.createElement("div");
  back.className = "vis-palette-backdrop";
  const palette = document.createElement("div");
  palette.className = "vis-palette";
  palette.innerHTML = `
    <h3>Add a node</h3>
    <div class="vis-palette-list"></div>
    <div class="vis-palette-actions">
      <button class="ghost vp-cancel">Cancel</button>
    </div>
  `;
  const list = palette.querySelector(".vis-palette-list");
  state.agents.forEach(a => {
    const card = document.createElement("div");
    card.className = "vis-palette-card";
    card.innerHTML = `
      <div class="name">${familyEmoji(a.family)} ${escapeHtml(a.label)}</div>
      <div class="meta">${escapeHtml(a.summary || a.id)}</div>
    `;
    card.onclick = () => {
      // Compute a default label based on existing count
      const spec = readSpec();
      const base = a.family || "agent";
      let i = 1, label = base;
      while (spec.find(s => s.label === label)) { i++; label = `${base}-${i}`; }
      addAgentRow({ agent: a.id, label, prompt: "" });
      back.remove();
      renderVisualCanvas();
    };
    list.appendChild(card);
  });
  palette.querySelector(".vp-cancel").onclick = () => back.remove();
  back.addEventListener("click", e => { if (e.target === back) back.remove(); });
  back.appendChild(palette);
  document.body.appendChild(back);
}

function applyViewMode(mode) {
  setViewMode(mode);
  document.querySelectorAll(".view-mode-toggle .vm-seg").forEach(b =>
    b.classList.toggle("active", b.dataset.vm === mode));
  $("#classic-pane").style.display = mode === "classic" ? "" : "none";
  $("#visual-pane").style.display = mode === "visual" ? "flex" : "none";
  // v16/visual: a body-class lets the orchestrator main grid widen
  // its first content column to 1fr so the canvas isn't trapped in
  // the 380px designer slot. CSS handles the rest.
  document.body.classList.toggle("visual-mode-active", mode === "visual");
  if (mode === "visual") renderVisualCanvas();
}

function initVisualMode() {
  document.querySelectorAll(".view-mode-toggle .vm-seg").forEach(b => {
    b.addEventListener("click", () => applyViewMode(b.dataset.vm));
  });
  $("#visual-add-node")?.addEventListener("click", openNodePalette);
  $("#visual-auto-layout")?.addEventListener("click", () => {
    window.__visPositions = {};  // forget saved
    renderVisualCanvas();
  });
  applyViewMode(getViewMode());
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
    // If preset ships default variables (e.g. ${TASK} pipeline), merge
    // them into Settings → Variables so the user can edit in one place
    // and any ${VAR} substitution in prompts resolves.
    if (preset.variables && typeof preset.variables === "object") {
      const settings = loadSettings();
      settings.variables = settings.variables || {};
      let added = 0;
      for (const [k, v] of Object.entries(preset.variables)) {
        if (!(k in settings.variables)) {
          settings.variables[k] = v;
          added++;
        }
      }
      if (added > 0) {
        saveSettings(settings);
        if (typeof renderVariables === "function") renderVariables();
        // Friendly nudge in the run title hint
        const ks = Object.keys(preset.variables).join(", ");
        toast(`Preset added ${added} variable(s): ${ks}. Edit them in Settings → Variables before Run.`);
      }
    }
    // Repaint visual canvas if active
    if (typeof renderVisualCanvas === "function" &&
        $("#visual-pane")?.style.display !== "none") {
      renderVisualCanvas();
    }
  };
}

// Tiny non-blocking toast (used by preset variable nudge)
function toast(msg, ms = 4500) {
  let el = document.getElementById("cg-toast");
  if (!el) {
    el = document.createElement("div");
    el.id = "cg-toast";
    el.style.cssText = "position:fixed;bottom:20px;right:20px;z-index:2000;" +
      "background:rgba(20,20,24,0.95);color:#fff;padding:10px 14px;" +
      "border-radius:8px;border:1px solid #a78bfa;font-size:12px;" +
      "max-width:380px;box-shadow:0 8px 24px rgba(0,0,0,0.5);" +
      "transition:opacity 0.25s;";
    document.body.appendChild(el);
  }
  el.textContent = msg;
  el.style.opacity = "1";
  clearTimeout(el._t);
  el._t = setTimeout(() => { el.style.opacity = "0"; }, ms);
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
    deepseek: "DeepSeek (cheap & strong)",
    moonshot: "Moonshot (Kimi)",
    glm: "GLM (Z.ai)",
    qwen: "Qwen",
    llama: "Llama (Meta)",
    mistral: "Mistral",
    opencode: "OpenCode (open-source CLI)",
    browser: "Browser / Pilot (Playwright)",
    subworkflow: "Sub-workflow",
    custom: "Custom (your own HTTP)",
    other: "Other",
  };
  const order = ["claude", "gemini", "deepseek", "moonshot", "glm",
                  "qwen", "llama", "mistral", "opencode",
                  "browser", "subworkflow", "custom", "other"];
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

// ---------- K4: browser step builder ------------------------------------
//
// Each entry describes one Playwright action and which form fields the
// builder UI exposes for it. `fields` are rendered in order. The schema
// matches the action set in dashboard.py::_run_browser_step exactly.
const BROWSER_ACTIONS = [
  { id: "goto",          fields: [["url",      "text", "https://…"]] },
  { id: "click",         fields: [["selector", "text", "CSS selector"]] },
  { id: "fill",          fields: [["selector", "text", "CSS selector"],
                                   ["value",    "text", "value"]] },
  { id: "type",          fields: [["selector", "text", "CSS selector"],
                                   ["text",     "text", "text to type"],
                                   ["delay",    "num",  "delay ms (0)"]] },
  { id: "press",         fields: [["selector", "text", "selector (default body)"],
                                   ["key",      "text", "Enter / Tab / …"]] },
  { id: "hover",         fields: [["selector", "text", "CSS selector"]] },
  { id: "scroll",        fields: [["to",       "text", "top | bottom | <px>"]] },
  { id: "wait_for",      fields: [["selector", "text", "selector (optional)"],
                                   ["time_ms",  "num",  "or wait N ms"],
                                   ["state",    "text", "visible / attached / hidden"]] },
  { id: "extract",       fields: [["selector", "text", "CSS selector"],
                                   ["attr",     "text", "attribute (optional)"]] },
  { id: "extract_all",   fields: [["selector", "text", "CSS selector"],
                                   ["attr",     "text", "attribute (optional)"]] },
  { id: "screenshot",    fields: [["selector",  "text", "selector (optional)"],
                                   ["full_page", "bool", "full page (default true)"]] },
  { id: "evaluate",      fields: [["script",   "ta",   "JavaScript expression"]] },
  { id: "title",         fields: [] },
  { id: "content",       fields: [] },
  { id: "url",           fields: [] },
  { id: "accept_dialog", fields: [] },
  { id: "pdf",           fields: [] },
];

function browserActionMeta(id) {
  return BROWSER_ACTIONS.find(a => a.id === id) || BROWSER_ACTIONS[0];
}

function renderBrowserStepCard(stepData = { action: "goto" }) {
  const card = document.createElement("div");
  card.className = "browser-step";
  card.innerHTML = `
    <div class="browser-step-head">
      <span class="drag-handle" title="Reorder">⋮⋮</span>
      <select class="step-action">
        ${BROWSER_ACTIONS.map(a => `<option value="${a.id}">${a.id}</option>`).join("")}
      </select>
      <input type="text" class="step-bind-as" placeholder="bind_as (optional)" />
      <button type="button" class="step-up"  title="Move up">↑</button>
      <button type="button" class="step-down" title="Move down">↓</button>
      <button type="button" class="step-remove" title="Remove">×</button>
    </div>
    <div class="browser-step-fields"></div>
  `;
  const actionSel = card.querySelector(".step-action");
  actionSel.value = stepData.action || "goto";
  card.querySelector(".step-bind-as").value = stepData.bind_as || "";

  function rebuildFields() {
    const meta = browserActionMeta(actionSel.value);
    const wrap = card.querySelector(".browser-step-fields");
    wrap.innerHTML = "";
    if (meta.fields.length === 0) {
      const note = document.createElement("div");
      note.className = "step-empty";
      note.textContent = "(no parameters)";
      wrap.appendChild(note);
      return;
    }
    for (const [name, type, placeholder] of meta.fields) {
      const fieldId = `f-${name}`;
      let el;
      if (type === "ta") {
        el = document.createElement("textarea");
      } else if (type === "bool") {
        const lab = document.createElement("label");
        lab.className = "step-bool";
        const cb = document.createElement("input");
        cb.type = "checkbox";
        cb.className = "step-field";
        cb.dataset.field = name;
        cb.dataset.kind = "bool";
        if (stepData[name] !== undefined) cb.checked = !!stepData[name];
        else cb.checked = name === "full_page";  // default true for screenshot
        lab.appendChild(cb);
        lab.appendChild(document.createTextNode(" " + (placeholder || name)));
        wrap.appendChild(lab);
        continue;
      } else {
        el = document.createElement("input");
        el.type = type === "num" ? "number" : "text";
      }
      el.className = "step-field";
      el.dataset.field = name;
      el.dataset.kind = type;
      el.placeholder = placeholder || name;
      const v = stepData[name];
      if (v !== undefined && v !== null) el.value = String(v);
      wrap.appendChild(el);
    }
  }
  actionSel.addEventListener("change", rebuildFields);
  rebuildFields();

  card.querySelector(".step-remove").onclick = () => card.remove();
  card.querySelector(".step-up").onclick = () => {
    const prev = card.previousElementSibling;
    if (prev && prev.classList.contains("browser-step")) {
      card.parentNode.insertBefore(card, prev);
    }
  };
  card.querySelector(".step-down").onclick = () => {
    const next = card.nextElementSibling;
    if (next && next.classList.contains("browser-step")) {
      card.parentNode.insertBefore(next, card);
    }
  };
  return card;
}

function readBrowserBuilderSteps(builder) {
  return Array.from(builder.querySelectorAll(".browser-step")).map(card => {
    const out = { action: card.querySelector(".step-action").value };
    const bindAs = card.querySelector(".step-bind-as").value.trim();
    if (bindAs) out.bind_as = bindAs;
    for (const fld of card.querySelectorAll(".step-field")) {
      const name = fld.dataset.field;
      const kind = fld.dataset.kind;
      if (kind === "bool") {
        out[name] = !!fld.checked;
      } else if (kind === "num") {
        if (fld.value !== "") out[name] = Number(fld.value);
      } else {
        if (fld.value !== "") out[name] = fld.value;
      }
    }
    return out;
  });
}

function renderBrowserBuilder(row, spec) {
  const builder = document.createElement("div");
  builder.className = "browser-builder";
  builder.innerHTML = `
    <div class="browser-builder-head">
      <span class="builder-title">🌐 Browser steps</span>
      <button type="button" class="ghost browser-builder-toggle"
              title="Switch to raw JSON for this step">{ } JSON</button>
      <button type="button" class="ghost browser-add-step">+ add step</button>
    </div>
    <div class="browser-steps"></div>
  `;
  const stepsHost = builder.querySelector(".browser-steps");
  const addBtn = builder.querySelector(".browser-add-step");
  const toggleBtn = builder.querySelector(".browser-builder-toggle");

  // Seed steps from incoming spec.prompt (best-effort JSON parse)
  let initial = [];
  try {
    const parsed = JSON.parse(spec.prompt || "{}");
    initial = parsed.steps || parsed.browser_steps || [];
  } catch (e) { /* fall through, empty list */ }
  if (initial.length === 0) initial = [{ action: "goto", url: "" }];
  initial.forEach(s => stepsHost.appendChild(renderBrowserStepCard(s)));

  addBtn.onclick = () => stepsHost.appendChild(renderBrowserStepCard());

  // Toggle to raw JSON edit (rare escape hatch — preserves builder state)
  toggleBtn.onclick = () => {
    const ta = row.querySelector(".prompt");
    const steps = readBrowserBuilderSteps(builder);
    ta.value = JSON.stringify({ steps }, null, 2);
    builder.style.display = "none";
    ta.style.display = "block";
    ta.dataset.builderHidden = "1";
  };

  return builder;
}

function applyBrowserMode(row, spec = {}) {
  const isBrowser = row.querySelector(".agent-select").value === "browser";
  const ta = row.querySelector(".prompt");
  const deps = row.querySelector(".depends_on");
  const streamLabel = row.querySelector(".streaming-toggle");
  let builder = row.querySelector(".browser-builder");

  if (isBrowser) {
    if (!builder) {
      builder = renderBrowserBuilder(row, spec);
      row.appendChild(builder);
    }
    // Builder visible → hide plain prompt unless user opted into raw JSON.
    if (!ta.dataset.builderHidden) {
      ta.style.display = "none";
    }
    deps.placeholder = "depends_on (comma-separated, optional for browser)";
    if (streamLabel) streamLabel.style.display = "none";  // streaming N/A
  } else {
    if (builder) builder.remove();
    ta.style.display = "block";
    delete ta.dataset.builderHidden;
    deps.placeholder = "depends_on (comma-separated labels)";
    if (streamLabel) streamLabel.style.display = "";
  }
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
      <label class="streaming-toggle" title="Stream token-by-token (claude/gemini stream-json)">
        <input type="checkbox" class="streaming" /> stream
      </label>
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
  // Default streaming ON for claude/gemini so the user sees token-by-token
  // output in the live monitor instead of a long "running" stall.
  const agentValue = tpl.querySelector(".agent-select").value;
  const family = (state.agents.find(a => a.id === agentValue) || {}).family;
  const streamDefault = (family === "claude" || family === "gemini");
  tpl.querySelector(".streaming").checked = (spec.streaming !== undefined)
    ? !!spec.streaming
    : streamDefault;
  tpl.querySelector(".remove").onclick = () => tpl.remove();
  $("#agent-rows").appendChild(tpl);

  // K4 — toggle step builder on agent change + on initial render
  applyBrowserMode(tpl, spec);
  sel.addEventListener("change", () => applyBrowserMode(tpl, { prompt: tpl.querySelector(".prompt").value }));
}

function ensureOneAgentRow() {
  if ($$(".agent-row").length === 0) addAgentRow();
}

function readSpec() {
  return $$(".agent-row").map((row, i) => {
    const agent = row.querySelector(".agent-select").value;
    let prompt = row.querySelector(".prompt").value;
    // K4 — when the browser builder is active, serialize cards → JSON
    // and use that as the prompt the backend's browser runner consumes.
    const builder = row.querySelector(".browser-builder");
    if (agent === "browser" && builder && builder.style.display !== "none") {
      const steps = readBrowserBuilderSteps(builder);
      prompt = JSON.stringify({ steps }, null, 2);
    }
    return {
      agent,
      label: row.querySelector(".label").value.trim() || `agent-${i + 1}`,
      depends_on: (row.querySelector(".depends_on").value || "")
        .split(",").map(s => s.trim()).filter(Boolean),
      streaming: !!row.querySelector(".streaming")?.checked,
      prompt,
    };
  });
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

  // Forward Settings (browser-stored API keys, project root, custom
  // variables) to the backend so the run actually uses them.
  const settings = loadSettings();
  const headers = { "Content-Type": "application/json" };
  if (settings.openrouter) headers["X-CG-OpenRouter-Key"] = settings.openrouter;
  if (settings.zhipu)      headers["X-CG-Zhipu-Key"] = settings.zhipu;
  if (settings.anthropic)  headers["X-CG-Anthropic-Key"] = settings.anthropic;
  if (settings.gemini)     headers["X-CG-Gemini-Key"] = settings.gemini;
  if (settings.projectRoot) headers["X-CG-Project-Root"] = settings.projectRoot;

  const variables = settings.variables || {};

  let runId;
  try {
    const r = await fetch("/api/runs", {
      method: "POST",
      headers,
      body: JSON.stringify({ title, spec, variables }),
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

  // Repaint Visual canvas with the active run's spec — so a 5-agent
  // pipeline opened from history shows all 5 nodes, not just the
  // leftover draft from agent-rows.
  if (typeof renderVisualCanvas === "function" &&
      $("#visual-pane")?.style.display !== "none") {
    renderVisualCanvas();
  }

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
  // "Open full page" button is ALWAYS shown when a run exists. The
  // backend (/api/runs/<id>/preview) picks the LAST agent with a
  // renderable artifact — perfect for multi-agent pipelines where
  // the polished output lives in the final agent and the UI doesn't
  // know which one upfront. Returns 404 with a friendly message if
  // nothing renderable was produced.
  tools.innerHTML = `
    <button class="ghost" id="cancel-btn">⨯ Cancel</button>
    <button class="ghost" id="rerun-btn">↻ Reload</button>
    <button class="ghost" id="export-btn">⬇ Export .md</button>
    <button class="ghost" id="full-page-btn"
       title="Open the rendered HTML/SVG in a new tab (full window — scroll, hover, scroll-snap all work). Picks the LAST agent with a renderable artifact (polish wins over implement).">↗ Open full page</button>
    <button class="ghost" id="open-design-btn" title="Drop this run's report into Open Design's imports/ folder">🎨 Open in OD</button>
  `;
  tools.querySelector("#full-page-btn").onclick = async () => {
    // Sniff the endpoint with a small Range GET so we can show a
    // friendly toast when nothing renderable was produced, rather
    // than dropping the user on a JSON 404 in a fresh tab.
    try {
      const r = await fetch(`/api/runs/${meta.id}/preview`,
                              { headers: { Range: "bytes=0-4" } });
      if (r.status === 404) {
        toast("No renderable HTML/SVG in this run yet — agents probably finished with Markdown only. Try the 'preview' tab.", 6000);
        return;
      }
    } catch (e) { /* fall through, let the browser show the error */ }
    window.open(`/api/runs/${meta.id}/preview`, "_blank", "noopener");
  };
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
  tools.querySelector("#open-design-btn").onclick = async () => {
    try {
      const r = await fetch(`/api/runs/${meta.id}/export-to-open-design`,
                              { method: "POST" });
      if (!r.ok) {
        const err = await r.text();
        alert("Open Design export failed:\n" + err);
        return;
      }
      const data = await r.json();
      toast(`Exported to Open Design: ${data.path}\n${data.hint}`, 9000);
    } catch (e) { alert("Network error: " + e); }
  };
  tools.querySelector("#rerun-btn").onclick = () => {
    // Reload this run's spec into the designer (prompts intact for editing)
    $("#run-title").value = meta.title + " (rerun)";
    $("#agent-rows").innerHTML = "";
    (meta.spec || []).forEach(a => addAgentRow({
      agent: a.agent, label: a.label,
      depends_on: a.depends_on || [],
      streaming: !!a.streaming,
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
  // v16 — also paint the visual canvas node
  if (typeof visualUpdateAgentStatus === "function") {
    visualUpdateAgentStatus(d.label, d.status);
  }
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
  // v16 — surface the latest line in the visual canvas node
  if (typeof visualUpdateAgentStatus === "function") {
    visualUpdateAgentStatus(d.label, null, d.line);
  }
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
    p.log.classList.remove("diff-rendered", "preview-rendered");
    p.log.innerHTML = window.marked.parse(text);
    if (window.hljs) p.log.querySelectorAll("pre code").forEach(b => window.hljs.highlightElement(b));
  } else if (state.viewMode === "diff") {
    p.log.classList.add("diff-rendered");
    p.log.classList.remove("md-rendered", "preview-rendered");
    p.log.innerHTML = renderDiffPlaceholder(p.label, text);
  } else if (state.viewMode === "preview") {
    p.log.classList.add("preview-rendered");
    p.log.classList.remove("md-rendered", "diff-rendered");
    p.log.innerHTML = "";
    p.log.appendChild(renderArtifactPreview(text));
  } else {
    p.log.classList.remove("md-rendered", "diff-rendered", "preview-rendered");
    p.log.textContent = text;
  }
  if (nearBottom) p.log.scrollTop = p.log.scrollHeight;
}

// Artifact-style preview — pulls the most useful renderable chunk from
// the agent's output and shows it in a sandboxed iframe (HTML / SVG /
// React-via-Babel) or img tag (data:image, png/jpg URL).
//
// Detection priority:
//   1. ```html ... ```  fenced block
//   2. ```svg  ... ```
//   3. ```jsx | tsx | react``` (wrapped in a Babel-standalone shell)
//   4. raw <html>/<svg> in the buffer
//   5. data:image/... or image-URL hits
// Otherwise → friendly empty-state hint.
function renderArtifactPreview(text) {
  const wrap = document.createElement("div");
  wrap.className = "artifact-host";

  function fenced(lang) {
    // Match ```<lang> ... ``` with a forgiving lang matcher
    const re = new RegExp("```\\s*(" + lang + ")\\s*\\n([\\s\\S]*?)```", "i");
    const m = text.match(re);
    return m ? m[2] : null;
  }

  let html = fenced("html|htm");
  let svg = fenced("svg");
  let jsx = fenced("jsx|tsx|react");

  if (!html) {
    const m = text.match(/<html[\s\S]*?<\/html>/i);
    if (m) html = m[0];
  }
  if (!svg) {
    const m = text.match(/<svg[\s\S]*?<\/svg>/i);
    if (m) svg = m[0];
  }

  if (html || svg || jsx) {
    const iframe = document.createElement("iframe");
    iframe.className = "artifact-iframe";
    iframe.setAttribute("sandbox", "allow-scripts");
    iframe.setAttribute("title", "preview");
    let doc;
    if (html) {
      doc = html;
    } else if (svg) {
      doc = `<!doctype html><meta charset="utf-8"><style>html,body{margin:0;background:#fff;display:flex;align-items:center;justify-content:center;min-height:100vh;font-family:system-ui}svg{max-width:100%;max-height:100vh}</style>${svg}`;
    } else {
      // jsx/tsx — wrap in a Babel-standalone host.
      // (text/babel script runs inside the sandbox; React UMD is loaded
      // from a CDN.)
      const safeJsx = jsx.replace(/<\/script/g, "<\\/script");
      doc =
        `<!doctype html><meta charset="utf-8">` +
        `<style>body{margin:0;font-family:system-ui;background:#fff}#root{padding:16px}</style>` +
        `<script crossorigin src="https://unpkg.com/react@18/umd/react.development.js"></script>` +
        `<script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>` +
        `<script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>` +
        `<div id="root"></div>` +
        `<script type="text/babel" data-presets="env,react,typescript">` +
        safeJsx +
        `\n;(function(){const e=window.App||window.Default||(typeof App!=='undefined'?App:null)||(typeof Component!=='undefined'?Component:null);` +
        `if(e){ReactDOM.createRoot(document.getElementById('root')).render(React.createElement(e));}else{document.getElementById('root').textContent='No component named App / Component / Default exported from the snippet.';}` +
        `})();</script>`;
    }
    iframe.srcdoc = doc;
    wrap.appendChild(iframe);
    return wrap;
  }

  // Image fallback
  const imgUrl = text.match(/(https?:\/\/\S+\.(?:png|jpe?g|gif|webp|svg))/i)
    || text.match(/(data:image\/[a-zA-Z+.-]+;base64,[A-Za-z0-9+/=]+)/);
  if (imgUrl) {
    const img = document.createElement("img");
    img.src = imgUrl[1];
    img.alt = "preview";
    img.className = "artifact-img";
    wrap.appendChild(img);
    return wrap;
  }

  const empty = document.createElement("div");
  empty.className = "artifact-empty";
  empty.innerHTML = "Preview shows when the output contains a renderable chunk: " +
    "<code>```html</code>, <code>```svg</code>, <code>```jsx</code>, raw " +
    "<code>&lt;html&gt;</code> / <code>&lt;svg&gt;</code>, or an image URL. " +
    "Use <strong>raw</strong> / <strong>markdown</strong> to inspect the full output.";
  wrap.appendChild(empty);
  return wrap;
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

// ============================================================
// Notes (Obsidian-inspired knowledge base)
// ============================================================

const notesState = {
  cm: null,
  list: [],
  currentName: null,
  originalContent: "",
  dirty: false,
  previewMode: false,
};

function ensureNotesEditor() {
  if (notesState.cm) return notesState.cm;
  const host = $("#notes-host");
  $("#notes-empty").style.display = "none";
  notesState.cm = CodeMirror(host, {
    value: "",
    mode: "markdown",
    theme: "material-darker",
    lineNumbers: false,
    lineWrapping: true,
    autoCloseBrackets: true,
    extraKeys: {
      "Ctrl-S": () => saveNote(),
      "Cmd-S":  () => saveNote(),
    },
  });
  notesState.cm.on("change", () => {
    const cur = notesState.cm.getValue();
    const dirty = cur !== notesState.originalContent;
    if (dirty !== notesState.dirty) {
      notesState.dirty = dirty;
      $("#note-dirty").hidden = !dirty;
      $("#note-save-btn").disabled = !dirty;
    }
  });
  return notesState.cm;
}

async function refreshNotesList(searchQuery = "") {
  try {
    let items;
    if (searchQuery && searchQuery.trim()) {
      const r = await fetch(`/api/notes-search?q=${encodeURIComponent(searchQuery)}`);
      const data = await r.json();
      items = (data.results || []).map(it => ({
        name: it.name, title: it.title,
        excerpt: it.excerpt, tags: [], updated: null,
      }));
    } else {
      const r = await fetch("/api/notes");
      const data = await r.json();
      items = data.notes || [];
    }
    notesState.list = items;
    const ul = $("#notes-list");
    if (!items.length) {
      ul.innerHTML = '<li style="color: var(--fg-tertiary); cursor: default; font-size: 12px;">No notes yet. Click + new.</li>';
      return;
    }
    ul.innerHTML = items.map(n => `
      <li data-name="${escapeHtml(n.name)}" class="${notesState.currentName === n.name ? 'active' : ''}">
        <div class="nl-title">${escapeHtml(n.title)}</div>
        <div class="nl-meta">
          ${(n.tags || []).slice(0, 3).map(t => `<span class="nl-tag">${escapeHtml(t)}</span>`).join("")}
          ${n.updated ? `<span>${escapeHtml(n.updated.slice(0, 10))}</span>` : ""}
        </div>
        ${n.excerpt ? `<div class="nl-excerpt">${escapeHtml(n.excerpt)}</div>` : ""}
      </li>
    `).join("");
    ul.querySelectorAll("li[data-name]").forEach(li => {
      li.onclick = () => openNote(li.dataset.name);
    });
  } catch (e) {
    $("#notes-list").innerHTML =
      `<li style="color:var(--error)">load failed: ${escapeHtml(String(e))}</li>`;
  }
}

async function openNote(name) {
  if (notesState.dirty) {
    if (!confirm("Discard unsaved changes?")) return;
  }
  try {
    const r = await fetch(`/api/notes/${encodeURIComponent(name)}`);
    if (!r.ok) { alert("Open failed: " + await r.text()); return; }
    const note = await r.json();
    const cm = ensureNotesEditor();
    cm.setValue(note.content);
    notesState.originalContent = note.content;
    notesState.currentName = note.name;
    notesState.dirty = false;
    $("#note-title").value = note.title;
    $("#note-tags").value = (note.tags || []).join(", ");
    $("#note-meta").textContent = note.updated ? `updated ${note.updated}` : "";
    $("#note-dirty").hidden = true;
    $("#note-save-btn").disabled = true;
    $("#note-delete-btn").disabled = false;
    document.querySelectorAll(".notes-list li.active")
      .forEach(x => x.classList.remove("active"));
    document.querySelector(`.notes-list li[data-name="${name}"]`)?.classList.add("active");
    await refreshBacklinks(note.name);
    if (notesState.previewMode) renderNotePreview();
  } catch (e) {
    alert("Network error: " + e);
  }
}

async function newNote() {
  if (notesState.dirty) {
    if (!confirm("Discard unsaved changes?")) return;
  }
  const slug = "note-" + Date.now();
  const cm = ensureNotesEditor();
  cm.setValue("# Untitled\n\nStart writing…\n\nLink other notes with [[note-name]].\n");
  notesState.originalContent = "";
  notesState.currentName = slug;
  notesState.dirty = true;
  $("#note-title").value = "Untitled";
  $("#note-tags").value = "";
  $("#note-meta").textContent = "(unsaved)";
  $("#note-dirty").hidden = false;
  $("#note-save-btn").disabled = false;
  $("#note-delete-btn").disabled = false;
  cm.focus();
  if (notesState.previewMode) renderNotePreview();
}

async function saveNote() {
  if (!notesState.currentName) return;
  const content = notesState.cm.getValue();
  const title = $("#note-title").value.trim() || "Untitled";
  const tags = $("#note-tags").value.split(",").map(s => s.trim()).filter(Boolean);
  try {
    const r = await fetch(`/api/notes/${encodeURIComponent(notesState.currentName)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, tags, content }),
    });
    if (!r.ok) { alert("Save failed: " + await r.text()); return; }
    const saved = await r.json();
    notesState.originalContent = content;
    notesState.dirty = false;
    notesState.currentName = saved.name;
    $("#note-meta").textContent = `updated ${saved.updated}`;
    $("#note-dirty").hidden = true;
    $("#note-save-btn").disabled = true;
    setStatus("note saved", "ok");
    setTimeout(() => setStatus("connected", "ok"), 1500);
    await refreshNotesList($("#notes-search").value);
    await refreshBacklinks(saved.name);
  } catch (e) { alert("Network error: " + e); }
}

async function deleteNote() {
  if (!notesState.currentName) return;
  if (!confirm("Delete this note?")) return;
  try {
    const r = await fetch(`/api/notes/${encodeURIComponent(notesState.currentName)}`,
                          { method: "DELETE" });
    if (!r.ok) { alert("Delete failed"); return; }
    notesState.currentName = null;
    notesState.dirty = false;
    if (notesState.cm) notesState.cm.setValue("");
    $("#note-title").value = "";
    $("#note-tags").value = "";
    $("#note-meta").textContent = "";
    $("#note-save-btn").disabled = true;
    $("#note-delete-btn").disabled = true;
    await refreshNotesList($("#notes-search").value);
  } catch (e) { alert("Network error: " + e); }
}

async function refreshBacklinks(name) {
  try {
    const r = await fetch(`/api/notes/${encodeURIComponent(name)}/backlinks`);
    if (!r.ok) {
      $("#backlinks-pane").hidden = true;
      return;
    }
    const data = await r.json();
    const ul = $("#backlinks-list");
    if (!data.backlinks.length) {
      $("#backlinks-pane").hidden = true;
      return;
    }
    $("#backlinks-pane").hidden = false;
    ul.innerHTML = data.backlinks.map(b => `
      <li data-name="${escapeHtml(b.name)}">
        <div class="bl-title">${escapeHtml(b.title)}</div>
        <div class="bl-excerpt">${escapeHtml(b.excerpt)}</div>
      </li>
    `).join("");
    ul.querySelectorAll("li[data-name]").forEach(li => {
      li.onclick = () => openNote(li.dataset.name);
    });
  } catch { /* ignore */ }
}

function renderNotePreview() {
  if (!notesState.cm) return;
  const md = notesState.cm.getValue();
  // Substitute [[wikilinks]] before passing to marked
  const withLinks = md.replace(
    /\[\[([^\]\|]+)(?:\|([^\]]+))?\]\]/g,
    (m, name, alt) => {
      const slug = name.toLowerCase().replace(/[^a-z0-9._\- ]+/g, "-")
                         .replace(/\s+/g, "-").trim().slice(0, 120);
      return `[${alt || name}](javascript:cgOpenNote("${slug}"))`;
    }
  );
  const host = notesState.cm.getWrapperElement();
  let preview = host.parentElement.querySelector(".markdown-preview");
  if (!preview) {
    preview = document.createElement("div");
    preview.className = "markdown-preview";
    host.parentElement.appendChild(preview);
  }
  host.style.display = "none";
  preview.style.display = "block";
  preview.innerHTML = (window.marked ? window.marked.parse(withLinks) : escapeHtml(withLinks));
  preview.querySelectorAll('a[href^="javascript:cgOpenNote"]').forEach(a => {
    const m = a.href.match(/cgOpenNote\("([^"]+)"\)/);
    if (m) {
      a.classList.add("wikilink");
      a.href = "#";
      a.onclick = (ev) => { ev.preventDefault(); openNote(m[1]); };
    }
  });
}

function exitPreview() {
  if (!notesState.cm) return;
  const host = notesState.cm.getWrapperElement();
  const preview = host.parentElement.querySelector(".markdown-preview");
  if (preview) preview.style.display = "none";
  host.style.display = "";
  notesState.cm.refresh();
}

function toggleNotePreview() {
  notesState.previewMode = !notesState.previewMode;
  const btn = $("#note-preview-btn");
  if (notesState.previewMode) {
    btn.textContent = "✏ edit";
    btn.dataset.mode = "preview";
    renderNotePreview();
  } else {
    btn.textContent = "👁 preview";
    btn.dataset.mode = "edit";
    exitPreview();
  }
}

window.cgOpenNote = openNote;  // for inline anchors in preview

// ============================================================
// Settings (localStorage + send via headers)
// ============================================================

const SETTINGS_KEY = "cg.settings";

function loadSettings() {
  try {
    return JSON.parse(localStorage.getItem(SETTINGS_KEY) || "{}");
  } catch { return {}; }
}
function persistSettings(s) {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(s));
}
function paintSettingsForm() {
  const s = loadSettings();
  $("#setting-openrouter").value = s.openrouter || "";
  $("#setting-zhipu").value = s.zhipu || "";
  $("#setting-anthropic").value = s.anthropic || "";
  $("#setting-gemini").value = s.gemini || "";
  $("#setting-project-root").value = s.projectRoot || "";
  if ($("#setting-default-view")) $("#setting-default-view").value = s.defaultView || "raw";

  // Variables list
  const vars = s.variables || {};
  const ul = $("#vars-list");
  if (ul) {
    const keys = Object.keys(vars);
    if (!keys.length) {
      ul.innerHTML = '<li style="color:var(--fg-tertiary); justify-content:center;"><em>(no variables yet)</em></li>';
    } else {
      ul.innerHTML = keys.sort().map(k =>
        `<li><span class="vk">\${${escapeHtml(k)}}</span><span class="vv">${escapeHtml(vars[k])}</span><button class="vrm" data-k="${escapeHtml(k)}">remove</button></li>`
      ).join("");
      ul.querySelectorAll(".vrm").forEach(b => {
        b.onclick = () => {
          const cur = loadSettings();
          delete (cur.variables || {})[b.dataset.k];
          persistSettings(cur);
          paintSettingsForm();
        };
      });
    }
  }

  const items = [
    ["OpenRouter", s.openrouter],
    ["Z.ai / Zhipu", s.zhipu],
    ["Anthropic API", s.anthropic],
    ["Gemini API", s.gemini],
    ["Project root", s.projectRoot],
    ["Variables", Object.keys(vars).length ? `${Object.keys(vars).length} defined` : ""],
  ];
  $("#settings-active").innerHTML = items.map(([name, v]) =>
    `<li class="${v ? 'ok' : 'off'}">${v ? '✓' : '○'} ${escapeHtml(name)}: ${v ? '<em>' + escapeHtml(v === true ? '(set)' : v) + '</em>' : '<em>not set</em>'}</li>`
  ).join("");
}

function addVariable() {
  const k = ($("#var-key-input").value || "").trim().toUpperCase();
  const v = ($("#var-value-input").value || "").trim();
  if (!/^[A-Z][A-Z0-9_]*$/.test(k)) {
    alert("Variable name must be UPPER_SNAKE_CASE starting with a letter.");
    return;
  }
  if (!v) { alert("Variable value cannot be empty."); return; }
  const s = loadSettings();
  s.variables = s.variables || {};
  s.variables[k] = v;
  persistSettings(s);
  $("#var-key-input").value = "";
  $("#var-value-input").value = "";
  paintSettingsForm();
}
function saveSettingsForm() {
  const s = {
    openrouter: $("#setting-openrouter").value.trim(),
    zhipu: $("#setting-zhipu").value.trim(),
    anthropic: $("#setting-anthropic").value.trim(),
    gemini: $("#setting-gemini").value.trim(),
    projectRoot: $("#setting-project-root").value.trim(),
    defaultView: $("#setting-default-view").value,
  };
  persistSettings(s);
  paintSettingsForm();
  setStatus("settings saved", "ok");
  setTimeout(() => setStatus("connected", "ok"), 1500);
  // Apply default view immediately
  if (s.defaultView) {
    state.viewMode = s.defaultView;
    document.querySelectorAll("#view-toggle .seg")
      .forEach(b => b.classList.toggle("active", b.dataset.view === s.defaultView));
  }
}
// ============================================================
// Cloudflare Tunnel + Notifications (Settings tab additions)
// ============================================================

// Browser auth wizard
async function refreshAuthList() {
  try {
    const r = await fetch("/api/browser-auth");
    if (!r.ok) return;
    const data = await r.json();
    const ul = $("#auth-list");
    if (!ul) return;
    if (!data.auths.length) {
      ul.innerHTML = '<li style="color: var(--fg-tertiary); justify-content: center;"><em>(no auth states yet)</em></li>';
    } else {
      ul.innerHTML = data.auths.map(a =>
        `<li><span class="vk">${escapeHtml(a.slug)}</span><span class="vv">${escapeHtml(a.modified)} · ${a.size} bytes</span><button class="vrm" data-slug="${escapeHtml(a.slug)}">delete</button></li>`
      ).join("");
      ul.querySelectorAll(".vrm").forEach(b => {
        b.onclick = async () => {
          if (!confirm(`Delete auth "${b.dataset.slug}"?`)) return;
          await fetch(`/api/browser-auth/${encodeURIComponent(b.dataset.slug)}`,
                       { method: "DELETE" });
          refreshAuthList();
        };
      });
    }
    if (data.active) {
      $("#auth-active-row").hidden = false;
      $("#auth-active-msg").textContent =
        `Chromium is open at ${data.active.url} as "${data.active.slug}". Sign in there, then click Save & Close.`;
    } else {
      $("#auth-active-row").hidden = true;
    }
  } catch { /* ignore */ }
}

async function startBrowserAuth() {
  const slug = $("#auth-slug-input").value.trim();
  const url = $("#auth-url-input").value.trim() || "about:blank";
  if (!/^[a-zA-Z0-9._-]+$/.test(slug)) {
    alert("Slug must be alphanumeric/dot/underscore/dash.");
    return;
  }
  const r = await fetch("/api/browser-auth/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ slug, url }),
  });
  if (!r.ok) {
    alert(`Start failed: ${await r.text()}`);
    return;
  }
  $("#auth-slug-input").value = "";
  $("#auth-url-input").value = "";
  refreshAuthList();
}

async function saveBrowserAuth() {
  const r = await fetch("/api/browser-auth/save", { method: "POST" });
  if (r.ok) {
    setStatus("auth state saved", "ok");
    setTimeout(() => setStatus("connected", "ok"), 2000);
  }
  refreshAuthList();
}

async function cancelBrowserAuth() {
  await fetch("/api/browser-auth/cancel", { method: "POST" });
  refreshAuthList();
}

async function refreshTunnelStatus() {
  try {
    const r = await fetch("/api/tunnel/status");
    const data = await r.json();
    const status = $("#tunnel-status");
    if (!status) return;
    if (data.running && data.url) {
      status.textContent = "running";
      status.className = "tunnel-status running";
      $("#tunnel-url-row").hidden = false;
      $("#tunnel-url-display").value = data.url;
      $("#tunnel-shortcut").hidden = false;
      $("#tunnel-shortcut-url").textContent = `${data.url}/api/phone-dispatch`;
    } else {
      status.textContent = "stopped";
      status.className = "tunnel-status";
      $("#tunnel-url-row").hidden = true;
      $("#tunnel-shortcut").hidden = true;
    }
  } catch { /* ignore */ }
}

async function startTunnel() {
  const status = $("#tunnel-status");
  status.textContent = "starting…";
  status.className = "tunnel-status starting";
  try {
    const r = await fetch("/api/tunnel/start", { method: "POST" });
    if (!r.ok) {
      const err = await r.text();
      alert(`Failed to start tunnel: ${err}`);
      status.textContent = "stopped";
      status.className = "tunnel-status";
      return;
    }
    await refreshTunnelStatus();
  } catch (e) {
    alert(`Network error: ${e}`);
    status.textContent = "stopped";
    status.className = "tunnel-status";
  }
}

async function stopTunnel() {
  await fetch("/api/tunnel/stop", { method: "POST" });
  await refreshTunnelStatus();
}

async function copyTunnelUrl() {
  const url = $("#tunnel-url-display").value;
  if (!url) return;
  await navigator.clipboard.writeText(url);
  const btn = $("#tunnel-copy-btn");
  btn.textContent = "✓"; setTimeout(() => btn.textContent = "📋", 1200);
}

async function loadNotificationsConfig() {
  try {
    const r = await fetch("/api/notifications");
    const cfg = await r.json();
    if ($("#notif-url"))         $("#notif-url").value = cfg.webhook_url || "";
    if ($("#notif-kind"))        $("#notif-kind").value = cfg.kind || "ntfy";
    if ($("#notif-on-complete")) $("#notif-on-complete").checked = !!cfg.on_complete;
    if ($("#notif-on-failed"))   $("#notif-on-failed").checked = !!cfg.on_failed;
  } catch { /* ignore */ }
}

async function saveNotificationsConfig() {
  const config = {
    webhook_url: $("#notif-url").value.trim(),
    kind: $("#notif-kind").value,
    on_complete: $("#notif-on-complete").checked,
    on_failed: $("#notif-on-failed").checked,
  };
  const r = await fetch("/api/notifications", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ config }),
  });
  if (r.ok) {
    setStatus("notifications saved", "ok");
    setTimeout(() => setStatus("connected", "ok"), 1500);
  } else {
    alert("Save failed: " + (await r.text()));
  }
}

async function sendTestNotification() {
  // Just trigger a fake "run-finished" by saving + start a dummy run
  const url = $("#notif-url").value.trim();
  if (!url) { alert("Set a webhook URL first."); return; }
  await saveNotificationsConfig();
  // Start a tiny mock run that finishes immediately so notification fires
  const r = await fetch("/api/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title: "🔔 notification test",
      spec: [{
        agent: "browser",
        label: "ping",
        prompt: '{"steps": []}',
      }],
    }),
  });
  if (r.ok) {
    setStatus("test ping fired — check your phone/Discord/Slack", "ok");
    setTimeout(() => setStatus("connected", "ok"), 4000);
  } else {
    alert("Test failed: " + (await r.text()));
  }
}

function clearSettings() {
  if (!confirm("Clear all settings from this browser?")) return;
  localStorage.removeItem(SETTINGS_KEY);
  paintSettingsForm();
  setStatus("settings cleared", "ok");
  setTimeout(() => setStatus("connected", "ok"), 1500);
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
      setTimeout(() => editorState.cm.refresh(), 50);
    }
  }
  if (tab === "notes") {
    refreshNotesList();
    if (notesState.cm) {
      setTimeout(() => notesState.cm.refresh(), 50);
    }
  }
  if (tab === "settings") {
    paintSettingsForm();
    refreshTunnelStatus();
    loadNotificationsConfig();
    refreshAuthList();
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
  // Notes handlers
  if ($("#note-new-btn")) $("#note-new-btn").onclick = newNote;
  if ($("#note-refresh-btn")) $("#note-refresh-btn").onclick = () => refreshNotesList($("#notes-search").value);
  if ($("#note-save-btn")) $("#note-save-btn").onclick = saveNote;
  if ($("#note-delete-btn")) $("#note-delete-btn").onclick = deleteNote;
  if ($("#note-preview-btn")) $("#note-preview-btn").onclick = toggleNotePreview;
  if ($("#note-title")) $("#note-title").addEventListener("input", () => {
    if (notesState.currentName && !notesState.dirty) {
      notesState.dirty = true;
      $("#note-dirty").hidden = false;
      $("#note-save-btn").disabled = false;
    }
  });
  if ($("#note-tags")) $("#note-tags").addEventListener("input", () => {
    if (notesState.currentName && !notesState.dirty) {
      notesState.dirty = true;
      $("#note-dirty").hidden = false;
      $("#note-save-btn").disabled = false;
    }
  });
  if ($("#notes-search")) {
    let searchT = null;
    $("#notes-search").addEventListener("input", () => {
      clearTimeout(searchT);
      searchT = setTimeout(() => refreshNotesList($("#notes-search").value), 200);
    });
  }
  // Settings handlers
  if ($("#settings-save-btn")) $("#settings-save-btn").onclick = saveSettingsForm;
  if ($("#settings-clear-btn")) $("#settings-clear-btn").onclick = clearSettings;
  if ($("#var-add-btn")) $("#var-add-btn").onclick = addVariable;
  // Tunnel + notifications
  if ($("#auth-start-btn")) $("#auth-start-btn").onclick = startBrowserAuth;
  if ($("#auth-save-btn")) $("#auth-save-btn").onclick = saveBrowserAuth;
  if ($("#auth-cancel-btn")) $("#auth-cancel-btn").onclick = cancelBrowserAuth;
  if ($("#tunnel-start-btn")) $("#tunnel-start-btn").onclick = startTunnel;
  if ($("#tunnel-stop-btn")) $("#tunnel-stop-btn").onclick = stopTunnel;
  if ($("#tunnel-copy-btn")) $("#tunnel-copy-btn").onclick = copyTunnelUrl;
  if ($("#notif-save-btn")) $("#notif-save-btn").onclick = saveNotificationsConfig;
  if ($("#notif-test-btn")) $("#notif-test-btn").onclick = sendTestNotification;
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
    //   - editor tab + dirty file → save file
    //   - notes tab + dirty note → save note
    //   - otherwise → save current workflow to localStorage
    if ((e.ctrlKey || e.metaKey) && e.key === "s") {
      e.preventDefault();
      const editorActive = $("#tab-editor")?.classList.contains("active");
      const notesActive = $("#tab-notes")?.classList.contains("active");
      if (editorActive && editorState.dirty) {
        editorSave();
      } else if (notesActive && notesState.dirty) {
        saveNote();
      } else {
        saveCurrentWorkflow();
      }
    }
  });

  init();
});
