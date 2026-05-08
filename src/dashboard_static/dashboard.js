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
/* v36 — renamed from setViewMode to avoid collision with the
 * setViewMode() at line ~2209 (which controls the OUTPUT view:
 * raw / markdown / diff / preview). Same name = the later
 * declaration overrode this one, so persisting Classic↔Visual
 * to localStorage silently never happened. */
function persistVisualMode(mode) {
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

  // Draw connections first (under nodes).
  // v34 — endpoints match port positions (body edge ± 6) so the
  // bezier visually connects to the draggable port, not the body edge.
  spec.forEach(s => {
    (s.depends_on || []).forEach(dep => {
      const from = positions[dep], to = positions[s.label];
      if (!from || !to) return;
      const x1 = from.x + VIS_NODE_W + 6;  // out port
      const y1 = from.y + VIS_NODE_H / 2;
      const x2 = to.x - 6;                  // in port
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

  // Draw nodes (foreignObject so we get full HTML+CSS inside SVG).
  // v34 — ports moved AFTER node bodies (was before, foreignObjects
  // covered them and stole pointerdown). Drag-to-connect now works.
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
      // Account for current zoom: 1 px on screen = 1/zoom in canvas
      // coords (the .zoom-group transform handles the scaling).
      const z = (window.__visView && window.__visView.zoom) || 1;
      const newPos = {
        x: Math.max(0, dragState.origX + dx / z),
        y: Math.max(0, dragState.origY + dy / z),
      };
      positions[s.label] = newPos;
      fo.setAttribute("x", newPos.x);
      fo.setAttribute("y", newPos.y);
      // v34 — also move the ports that belong to this node
      const out = svg.querySelector(`.vis-port--out[data-label="${s.label}"]`);
      if (out) {
        out.setAttribute("cx", newPos.x + VIS_NODE_W + 6);
        out.setAttribute("cy", newPos.y + VIS_NODE_H / 2);
      }
      const inp = svg.querySelector(`.vis-port--in[data-label="${s.label}"]`);
      if (inp) {
        inp.setAttribute("cx", newPos.x - 6);
        inp.setAttribute("cy", newPos.y + VIS_NODE_H / 2);
      }
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

  // v34 — Drag-to-connect ports rendered LAST so they sit above
  // foreignObjects and receive pointer events. We position them
  // slightly outside node bounds (cx +/- 4) for unambiguous targeting.
  spec.forEach(s => {
    const pos = positions[s.label];
    if (!pos) return;
    const NS = "http://www.w3.org/2000/svg";

    const outPort = document.createElementNS(NS, "circle");
    outPort.setAttribute("cx", pos.x + VIS_NODE_W + 6);  // +6 outside body
    outPort.setAttribute("cy", pos.y + VIS_NODE_H / 2);
    outPort.setAttribute("r", 6);
    outPort.classList.add("vis-port", "vis-port--out");
    outPort.dataset.label = s.label;
    outPort.dataset.kind = "out";
    nodesLayer.appendChild(outPort);

    const inPort = document.createElementNS(NS, "circle");
    inPort.setAttribute("cx", pos.x - 6);  // -6 outside body
    inPort.setAttribute("cy", pos.y + VIS_NODE_H / 2);
    inPort.setAttribute("r", 6);
    inPort.classList.add("vis-port", "vis-port--in");
    inPort.dataset.label = s.label;
    inPort.dataset.kind = "in";
    nodesLayer.appendChild(inPort);
  });

  // Wire ports → drag-to-connect on the svg root (delegated, idempotent)
  attachWireDragHandlers(svg, spec, positions);

  // Re-apply current zoom/pan transform — we replaced layer children
  // but the .zoom-group itself survives renderVisualCanvas calls.
  if (typeof applyVisView === "function") applyVisView();
}

function drawConnectionsOnly(svg, spec, positions) {
  const layer = svg.querySelector(".connections-layer");
  layer.innerHTML = "";
  spec.forEach(s => {
    (s.depends_on || []).forEach(dep => {
      const from = positions[dep], to = positions[s.label];
      if (!from || !to) return;
      const x1 = from.x + VIS_NODE_W + 6;  // v34 — port-aligned
      const y1 = from.y + VIS_NODE_H / 2;
      const x2 = to.x - 6;
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
  persistVisualMode(mode);  // v36 — was setViewMode (collided with output renderer)
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

// ---------- Visual canvas zoom + pan + fullscreen ----------
window.__visView = window.__visView || { zoom: 1, panX: 0, panY: 0 };

function applyVisView() {
  const g = document.querySelector("#visual-canvas .zoom-group");
  if (!g) return;
  const { zoom, panX, panY } = window.__visView;
  g.setAttribute("transform",
    `translate(${panX} ${panY}) scale(${zoom})`);
  const readout = document.getElementById("zoom-readout");
  const resetBtn = document.getElementById("visual-zoom-reset");
  const pct = Math.round(zoom * 100) + "%";
  if (readout) readout.textContent = pct;
  if (resetBtn) resetBtn.textContent = pct;
}

function setVisZoom(nextZoom, anchorX, anchorY) {
  const wrap = document.getElementById("visual-canvas-wrap");
  if (!wrap) return;
  const v = window.__visView;
  const z = Math.max(0.2, Math.min(3, nextZoom));
  if (anchorX !== undefined && anchorY !== undefined) {
    const rect = wrap.getBoundingClientRect();
    const px = anchorX - rect.left;
    const py = anchorY - rect.top;
    v.panX = px - (px - v.panX) * (z / v.zoom);
    v.panY = py - (py - v.panY) * (z / v.zoom);
  }
  v.zoom = z;
  applyVisView();
}

function fitVisToViewport() {
  const wrap = document.getElementById("visual-canvas-wrap");
  const svg = document.getElementById("visual-canvas");
  if (!wrap || !svg) return;
  const nodes = svg.querySelectorAll(".nodes-layer foreignObject");
  if (!nodes.length) return;
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  nodes.forEach(fo => {
    const x = +fo.getAttribute("x"), y = +fo.getAttribute("y");
    const w = +fo.getAttribute("width"), h = +fo.getAttribute("height");
    minX = Math.min(minX, x); minY = Math.min(minY, y);
    maxX = Math.max(maxX, x + w); maxY = Math.max(maxY, y + h);
  });
  const margin = 40;
  const cw = wrap.clientWidth - margin * 2;
  const ch = wrap.clientHeight - margin * 2;
  const gw = maxX - minX, gh = maxY - minY;
  if (gw <= 0 || gh <= 0) return;
  const z = Math.min(cw / gw, ch / gh, 2);
  window.__visView = {
    zoom: z,
    panX: margin - minX * z + (cw - gw * z) / 2,
    panY: margin - minY * z + (ch - gh * z) / 2,
  };
  applyVisView();
}

function initVisualMode() {
  document.querySelectorAll(".view-mode-toggle .vm-seg").forEach(b => {
    b.addEventListener("click", () => applyViewMode(b.dataset.vm));
  });
  $("#visual-add-node")?.addEventListener("click", openNodePalette);
  $("#visual-auto-layout")?.addEventListener("click", () => {
    window.__visPositions = {};
    renderVisualCanvas();
  });

  $("#visual-zoom-in")?.addEventListener("click", () =>
    setVisZoom(window.__visView.zoom * 1.2));
  $("#visual-zoom-out")?.addEventListener("click", () =>
    setVisZoom(window.__visView.zoom / 1.2));
  $("#visual-zoom-reset")?.addEventListener("click", () => {
    window.__visView = { zoom: 1, panX: 0, panY: 0 };
    applyVisView();
  });
  $("#visual-fit")?.addEventListener("click", fitVisToViewport);
  $("#visual-fullscreen")?.addEventListener("click", () => {
    document.body.classList.toggle("visual-fullscreen");
    setTimeout(fitVisToViewport, 200);
  });

  // Ctrl+wheel = zoom around cursor; drag bg = pan
  const wrap = document.getElementById("visual-canvas-wrap");
  if (wrap) {
    wrap.addEventListener("wheel", (e) => {
      if (!e.ctrlKey && !e.metaKey) return;
      e.preventDefault();
      const delta = e.deltaY < 0 ? 1.1 : 1 / 1.1;
      setVisZoom(window.__visView.zoom * delta, e.clientX, e.clientY);
    }, { passive: false });

    let panState = null;
    wrap.addEventListener("pointerdown", (e) => {
      if (e.target.closest(".vis-node, button, input, select, textarea")) return;
      panState = {
        startX: e.clientX, startY: e.clientY,
        origPanX: window.__visView.panX, origPanY: window.__visView.panY,
      };
      wrap.classList.add("panning");
      wrap.setPointerCapture(e.pointerId);
    });
    wrap.addEventListener("pointermove", (e) => {
      if (!panState) return;
      window.__visView.panX = panState.origPanX + (e.clientX - panState.startX);
      window.__visView.panY = panState.origPanY + (e.clientY - panState.startY);
      applyVisView();
    });
    wrap.addEventListener("pointerup", () => {
      panState = null;
      wrap.classList.remove("panning");
    });
  }

  document.addEventListener("keydown", (e) => {
    if (!document.body.classList.contains("visual-mode-active")) return;
    if (e.target.matches("input, textarea, select, [contenteditable]")) return;
    if (e.key === "0") {
      window.__visView = { zoom: 1, panX: 0, panY: 0 };
      applyVisView(); e.preventDefault();
    } else if (e.key === "f" || e.key === "F") {
      document.body.classList.toggle("visual-fullscreen");
      setTimeout(fitVisToViewport, 200); e.preventDefault();
    } else if (e.key === "+" || e.key === "=") {
      setVisZoom(window.__visView.zoom * 1.2); e.preventDefault();
    } else if (e.key === "-" || e.key === "_") {
      setVisZoom(window.__visView.zoom / 1.2); e.preventDefault();
    }
  });

  applyViewMode(getViewMode());
  applyVisView();
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

/* ============================================================
 * v28 — Slash commands in prompt textareas
 * Type "/" in any .prompt or .vne-prompt to open a command picker.
 * Completions insert CG placeholder syntax ({{file:}}, {{git:diff}},
 * {{web:URL}}, ${VAR}) and personas (predefined system prompts).
 * ============================================================ */
const PERSONAS_KEY = "cg.personas.v1";

const PERSONAS_BUILTIN = [
  { id: "code-reviewer", icon: "🔍", name: "Senior code reviewer",
    body: "You are a senior staff engineer reviewing code. Look for: bugs, race conditions, off-by-one errors, security issues, performance problems, missing edge cases, unclear naming, and over-engineering. Quote the exact line. Be terse — bullet points, no preamble." },
  { id: "security-auditor", icon: "🛡", name: "Security auditor",
    body: "You are an OWASP-trained security auditor. Find injection (SQL, command, prompt), auth/authz holes, missing input validation, secrets in code, insecure deserialization, SSRF, XSS, and CSRF. Output: severity (Critical/High/Med/Low), CWE id, exact line, exploitation sketch, fix." },
  { id: "concise-summarizer", icon: "✦", name: "Concise summarizer",
    body: "Summarize the input in ≤5 bullets. No preamble, no closing remarks, no apologies. Each bullet ≤20 words. Pull out concrete numbers and names. Match the source language (CZ if Czech, EN otherwise)." },
  { id: "devils-advocate", icon: "⚔", name: "Devil's advocate critic",
    body: "You are the strongest critic of the proposal. Don't be polite — find every weakness, hidden assumption, scalability concern, and edge case. Steel-man your objections. End with: 'Strongest objection: …' (one sentence)." },
  { id: "pair-buddy", icon: "🤝", name: "Pair-programming buddy",
    body: "You are a pair-programming buddy. Don't write code unless asked — instead, ask probing questions, suggest test cases, point out tradeoffs, and propose simpler alternatives. Encourage thinking out loud. Match the developer's vibe (terse if they're terse)." },
  { id: "czech-translator", icon: "🇨🇿", name: "Czech translator",
    body: "Translate the input to natural, idiomatic Czech. Preserve formatting (markdown, code blocks, lists). Don't add commentary, don't translate code identifiers, don't translate quoted brand names. Match register (formal/casual) of the source." },
  { id: "test-writer", icon: "🧪", name: "Test writer",
    body: "Write thorough tests for the given code. Include: happy path, edge cases (null/empty/zero/negative/max), error paths, race conditions if relevant. Use the framework already present in the project. No prose — just the test file content." },
  { id: "rubber-duck", icon: "🦆", name: "Rubber duck",
    body: "Listen to the user describe their problem. Ask exactly 3 clarifying questions, one at a time. Don't propose solutions until they confirm you've understood. After 3 rounds, summarize what they actually need in 1 paragraph." },
];

function loadPersonas() {
  try {
    const raw = localStorage.getItem(PERSONAS_KEY);
    const custom = raw ? JSON.parse(raw) : [];
    return [...PERSONAS_BUILTIN, ...custom];
  } catch {
    return [...PERSONAS_BUILTIN];
  }
}
function saveCustomPersonas(custom) {
  try { localStorage.setItem(PERSONAS_KEY, JSON.stringify(custom || [])); } catch {}
}
function getCustomPersonas() {
  try {
    const raw = localStorage.getItem(PERSONAS_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch { return []; }
}

/* The slash-command catalog. Each entry can either insert text directly
 * (`insert`) or open a sub-picker (`open`: 'personas' | 'deps' | 'vars'). */
function slashCommands() {
  return [
    { key: "file",     icon: "📄", label: "/file",     hint: "Inline a file by path",
      insert: "{{file:PATH}}" },
    { key: "git-diff", icon: "↧",  label: "/git-diff", hint: "Inline current diff",
      insert: "{{git:diff}}" },
    { key: "git-log",  icon: "⏱",  label: "/git-log",  hint: "Last 5 commits",
      insert: "{{git:log:5}}" },
    { key: "web",      icon: "🌐", label: "/web",      hint: "Fetch a URL as markdown",
      insert: "{{web:URL}}" },
    { key: "web-shot", icon: "📸", label: "/web-shot", hint: "Screenshot a URL",
      insert: "{{web-shot:URL}}" },
    { key: "shell",    icon: ">",  label: "/shell",    hint: "Run a shell command, inline output",
      insert: "{{shell:CMD}}" },
    { key: "dep",      icon: "→",  label: "/dep",      hint: "Insert {{label}} from a previous agent",
      open: "deps" },
    { key: "var",      icon: "$",  label: "/var",      hint: "Insert ${VAR} from saved variables",
      open: "vars" },
    { key: "persona",  icon: "👤", label: "/persona",  hint: "Prepend a saved system-prompt persona",
      open: "personas" },
  ];
}

const _slashState = {
  el: null,        // DOM root
  active: 0,
  items: [],
  query: "",
  textarea: null,
  triggerStart: -1, // index of the "/" that opened it
  mode: "root",    // 'root' | 'personas' | 'deps' | 'vars'
};

function ensureSlashEl() {
  if (_slashState.el) return _slashState.el;
  const el = document.createElement("div");
  el.className = "slash-menu";
  el.setAttribute("role", "listbox");
  el.hidden = true;
  document.body.appendChild(el);
  _slashState.el = el;
  return el;
}

function placeSlashMenu(textarea) {
  const el = _slashState.el;
  if (!el) return;
  // Place the menu near the textarea — anchor under bottom-left corner
  const rect = textarea.getBoundingClientRect();
  el.style.left = `${Math.round(rect.left)}px`;
  el.style.top  = `${Math.round(rect.bottom + 6)}px`;
  el.style.minWidth = `${Math.max(280, Math.round(rect.width / 2))}px`;
}

function renderSlashMenu() {
  const el = ensureSlashEl();
  const items = _slashState.items;
  if (!items.length) {
    el.innerHTML = `<div class="slash-empty">No matches for <code>${escapeHtml(_slashState.query)}</code></div>`;
    return;
  }
  let html = `<div class="slash-head">${escapeHtml(headerForMode(_slashState.mode))}</div>`;
  items.forEach((it, i) => {
    const isActive = i === _slashState.active;
    html += `
      <div class="slash-item ${isActive ? "is-active" : ""}" data-idx="${i}">
        <span class="slash-icon">${escapeHtml(it.icon || "•")}</span>
        <span class="slash-body">
          <span class="slash-label">${escapeHtml(it.label)}</span>
          <span class="slash-hint">${escapeHtml(it.hint || "")}</span>
        </span>
      </div>`;
  });
  el.innerHTML = html;
  el.querySelectorAll(".slash-item").forEach(node => {
    node.addEventListener("mousedown", (e) => {
      e.preventDefault(); // keep textarea focused
      _slashState.active = Number(node.dataset.idx);
      pickSlashItem();
    });
  });
}
function headerForMode(mode) {
  switch (mode) {
    case "personas": return "PERSONAS — prepend system prompt";
    case "deps":     return "DEPENDS — labels of upstream agents";
    case "vars":     return "VARIABLES — saved ${VARS}";
    default:         return "SLASH COMMANDS — type to filter";
  }
}

function fuzzy(q, t) {
  if (!q) return 1;
  q = q.toLowerCase(); t = t.toLowerCase();
  if (t.includes(q)) return 100 - t.indexOf(q);
  let qi = 0;
  for (let i = 0; i < t.length && qi < q.length; i++) if (t[i] === q[qi]) qi++;
  return qi === q.length ? 30 : 0;
}

function refreshSlashItems() {
  const q = _slashState.query.toLowerCase();
  let pool = [];
  if (_slashState.mode === "root") {
    pool = slashCommands();
  } else if (_slashState.mode === "personas") {
    pool = loadPersonas().map(p => ({
      key: `persona:${p.id}`, icon: p.icon || "👤",
      label: p.name, hint: (p.body || "").slice(0, 60),
      insertPersona: p,
    }));
  } else if (_slashState.mode === "deps") {
    const labels = readSpec().map(s => s.label).filter(Boolean);
    pool = labels.map(l => ({
      key: `dep:${l}`, icon: "→", label: `{{${l}}}`,
      hint: `Insert reference to "${l}"`,
      insert: `{{${l}}}`,
    }));
    if (!pool.length) {
      pool = [{ key: "dep:none", icon: "—", label: "No upstream agents",
               hint: "Add other rows first to see them here", insert: "" }];
    }
  } else if (_slashState.mode === "vars") {
    const vars = (window.__cgVars && Array.isArray(window.__cgVars))
      ? window.__cgVars
      : (() => {
          try { return JSON.parse(localStorage.getItem("cg.vars") || "[]"); }
          catch { return []; }
        })();
    pool = (vars || []).map(v => ({
      key: `var:${v.key}`, icon: "$", label: `\${${v.key}}`,
      hint: String(v.value || "").slice(0, 60),
      insert: `\${${v.key}}`,
    }));
    if (!pool.length) {
      pool = [{ key: "var:none", icon: "—", label: "No variables saved",
               hint: "Add some in Settings → Workflow variables", insert: "" }];
    }
  }
  _slashState.items = pool
    .map(it => ({ it, score: fuzzy(q, it.label) + fuzzy(q, it.hint || "") * 0.4 }))
    .filter(x => x.score > 0)
    .sort((a, b) => b.score - a.score)
    .map(x => x.it)
    .slice(0, 12);
  if (_slashState.active >= _slashState.items.length) _slashState.active = 0;
}

function openSlashMenu(textarea, triggerStart) {
  _slashState.textarea = textarea;
  _slashState.triggerStart = triggerStart;
  _slashState.query = "";
  _slashState.active = 0;
  _slashState.mode = "root";
  refreshSlashItems();
  ensureSlashEl().hidden = false;
  placeSlashMenu(textarea);
  renderSlashMenu();
}
function closeSlashMenu() {
  if (_slashState.el) _slashState.el.hidden = true;
  _slashState.textarea = null;
  _slashState.triggerStart = -1;
  _slashState.mode = "root";
}

function pickSlashItem() {
  const it = _slashState.items[_slashState.active];
  const ta = _slashState.textarea;
  if (!it || !ta) return closeSlashMenu();

  // Sub-picker delegation
  if (it.key === "var" || it.key === "dep" || it.key === "persona") {
    _slashState.mode = it.key + (it.key === "var" ? "s" : "s"); // 'vars' / 'deps' / 'personas'
    _slashState.query = "";
    _slashState.active = 0;
    refreshSlashItems();
    renderSlashMenu();
    return;
  }

  // Persona application: prepend "[System: ...]\n\n" to current prompt
  if (it.insertPersona) {
    const p = it.insertPersona;
    const v = ta.value || "";
    const start = _slashState.triggerStart;
    const before = v.slice(0, start);
    const afterRaw = v.slice(start);
    // Drop the slash-trigger fragment up to caret
    const caretAfter = ta.selectionEnd;
    const after = v.slice(caretAfter);
    const personaBlock = `[System: ${p.name}]\n${p.body}\n\n`;
    ta.value = personaBlock + before + after;
    // Caret right after persona block + original text head
    const newCaret = personaBlock.length + before.length;
    ta.setSelectionRange(newCaret, newCaret);
    ta.dispatchEvent(new Event("input"));
    closeSlashMenu();
    if (typeof toast === "function") toast(`Persona applied: ${p.name}`, 1500);
    return;
  }

  // Plain insert: replace the "/<query>" trigger with the placeholder
  const v = ta.value || "";
  const triggerStart = _slashState.triggerStart;
  const caret = ta.selectionEnd;
  const before = v.slice(0, triggerStart);
  const after = v.slice(caret);
  const inserted = it.insert || "";
  ta.value = before + inserted + after;
  // Position caret inside the placeholder argument if it has one
  const argMatches = /:[A-Z][A-Z_]*\}\}|:URL\}\}|:CMD\}\}|:PATH\}\}/.exec(inserted);
  if (argMatches) {
    const start = before.length + argMatches.index + 1;
    const end = before.length + argMatches.index + argMatches[0].length - 2;
    ta.setSelectionRange(start, end);
  } else {
    const newCaret = before.length + inserted.length;
    ta.setSelectionRange(newCaret, newCaret);
  }
  ta.dispatchEvent(new Event("input"));
  closeSlashMenu();
}

function isPromptTextarea(t) {
  if (!t) return false;
  if (t.tagName !== "TEXTAREA") return false;
  return t.classList.contains("prompt") || t.classList.contains("vne-prompt");
}

function initSlashCommands() {
  // Delegate keydown on document so dynamically-added rows are covered
  document.addEventListener("keydown", (e) => {
    const ta = e.target;
    const open = !!_slashState.textarea;

    if (open) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        _slashState.active = Math.min(_slashState.active + 1,
          _slashState.items.length - 1);
        renderSlashMenu();
        return;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        _slashState.active = Math.max(_slashState.active - 1, 0);
        renderSlashMenu();
        return;
      }
      if (e.key === "Enter" || e.key === "Tab") {
        e.preventDefault();
        pickSlashItem();
        return;
      }
      if (e.key === "Escape") {
        e.preventDefault();
        closeSlashMenu();
        return;
      }
    }

    if (e.key === "/" && isPromptTextarea(ta) && !e.ctrlKey && !e.metaKey) {
      // Open menu after the slash is inserted (let default keypress through)
      setTimeout(() => {
        const caret = ta.selectionStart;
        const triggerStart = caret - 1;
        if (triggerStart < 0) return;
        if (ta.value[triggerStart] !== "/") return;
        openSlashMenu(ta, triggerStart);
      }, 0);
    }
  });

  // Update query as the user types after "/"
  document.addEventListener("input", (e) => {
    if (!_slashState.textarea || e.target !== _slashState.textarea) return;
    const ta = _slashState.textarea;
    const trigger = _slashState.triggerStart;
    const caret = ta.selectionEnd;
    if (caret <= trigger) return closeSlashMenu();
    const fragment = ta.value.slice(trigger + 1, caret);
    if (/[\s\n]/.test(fragment) || ta.value[trigger] !== "/") {
      return closeSlashMenu();
    }
    _slashState.query = fragment;
    refreshSlashItems();
    renderSlashMenu();
  });

  // Click-away closes
  document.addEventListener("mousedown", (e) => {
    if (!_slashState.textarea) return;
    if (e.target === _slashState.textarea) return;
    if (_slashState.el && _slashState.el.contains(e.target)) return;
    closeSlashMenu();
  });

  // Reposition on resize / scroll
  window.addEventListener("resize", () => {
    if (_slashState.textarea) placeSlashMenu(_slashState.textarea);
  });
}

// Tiny non-blocking toast (used by preset variable nudge).
// Styling lives in dashboard.css (.cg-toast) so it inherits design tokens.
function toast(msg, ms = 4500) {
  let el = document.getElementById("cg-toast");
  if (!el) {
    el = document.createElement("div");
    el.id = "cg-toast";
    el.className = "cg-toast";
    document.body.appendChild(el);
  }
  el.textContent = msg;
  el.classList.add("cg-toast--visible");
  clearTimeout(el._t);
  el._t = setTimeout(() => { el.classList.remove("cg-toast--visible"); }, ms);
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
  root.className = `agent-panel agent-panel--block status-${agent.status}`;
  const depsHtml = (agent.depends_on && agent.depends_on.length)
    ? `<span class="deps">← ${agent.depends_on.map(escapeHtml).join(", ")}</span>` : "";
  const fam = familyOf(agent.agent);
  const modelLabel = shortAgentLabel(agent.agent);
  root.innerHTML = `
    <div class="agent-panel-head">
      <div class="title">
        <span class="agent-family-dot agent-family-${fam}" aria-hidden="true"></span>
        <span class="agent-label">${escapeHtml(agent.label)}</span>
        ${depsHtml}
      </div>
      <div class="badges">
        <span class="badge ${fam}" title="${escapeHtml(agent.agent)}">${escapeHtml(modelLabel)}</span>
        <span class="badge status ${agent.status}">
          <span class="badge-dot" aria-hidden="true"></span>
          <span class="badge-text">${agent.status}</span>
        </span>
        <span class="agent-elapsed" data-elapsed hidden>--:--</span>
        <span class="agent-tokens" data-tokens hidden>0 tok</span>
      </div>
      <div class="agent-panel-actions" aria-label="Panel actions">
        <button class="ap-action ap-copy" title="Copy log (C)" aria-label="Copy log">
          <span class="ap-icon">⧉</span>
        </button>
        <button class="ap-action ap-fullscreen" title="Fullscreen (F)" aria-label="Fullscreen">
          <span class="ap-icon">⛶</span>
        </button>
      </div>
    </div>
    <div class="agent-panel-log" tabindex="0"></div>
    <div class="agent-panel-foot">
      <span class="bytes">0 chars</span>
      <span class="exit"></span>
    </div>
  `;
  const logEl = root.querySelector(".agent-panel-log");
  const elapsedEl = root.querySelector("[data-elapsed]");
  const tokensEl  = root.querySelector("[data-tokens]");

  // Action buttons
  root.querySelector(".ap-copy").onclick = () => {
    navigator.clipboard.writeText(logEl.textContent || "");
    if (typeof toast === "function") toast(`Copied ${agent.label}`, 1500);
  };
  root.querySelector(".ap-fullscreen").onclick = () => {
    root.classList.toggle("agent-panel--fullscreen");
  };

  // Sticky-bottom auto-scroll: pin to bottom while user hasn't scrolled up.
  // 32px threshold so accidental wheel movements don't unpin.
  const stickyState = { pinned: true };
  logEl.addEventListener("scroll", () => {
    const dist = logEl.scrollHeight - logEl.scrollTop - logEl.clientHeight;
    stickyState.pinned = dist < 32;
  });

  // Track elapsed time
  let elapsedStart = null;
  let elapsedTimer = null;
  function startElapsed() {
    if (elapsedTimer) return;
    elapsedStart = Date.now();
    elapsedEl.hidden = false;
    elapsedTimer = setInterval(() => {
      const s = Math.floor((Date.now() - elapsedStart) / 1000);
      const mm = String(Math.floor(s / 60)).padStart(2, "0");
      const ss = String(s % 60).padStart(2, "0");
      elapsedEl.textContent = `${mm}:${ss}`;
    }, 500);
  }
  function stopElapsed() {
    if (elapsedTimer) {
      clearInterval(elapsedTimer);
      elapsedTimer = null;
    }
  }
  if (agent.status === "running") startElapsed();

  return {
    root,
    log: logEl,
    statusBadge: root.querySelector(".badge.status"),
    bytesEl: root.querySelector(".bytes"),
    exitEl: root.querySelector(".exit"),
    elapsedEl,
    tokensEl,
    sticky: stickyState,
    startElapsed,
    stopElapsed,
  };
}

function handleStatus(d) {
  // v16 — also paint the visual canvas node
  if (typeof visualUpdateAgentStatus === "function") {
    visualUpdateAgentStatus(d.label, d.status);
  }
  const p = state.panels[d.label];
  if (!p) return;
  // Update badge: dot+text structure (v21)
  p.statusBadge.className = `badge status ${d.status}`;
  const txt = p.statusBadge.querySelector(".badge-text");
  if (txt) txt.textContent = d.status;
  else p.statusBadge.textContent = d.status;
  // Mirror status onto the panel root for state-driven styling
  if (p.root) {
    p.root.className = p.root.className.replace(/\bstatus-[a-z]+\b/g, "");
    p.root.classList.add(`status-${d.status}`);
  }
  // Drive elapsed timer lifecycle from real status events
  if (d.status === "running" && p.startElapsed) p.startElapsed();
  if ((d.status === "done" || d.status === "failed" || d.status === "cancelled")
      && p.stopElapsed) p.stopElapsed();
  if (d.exit_code !== null && d.exit_code !== undefined) {
    p.exitEl.textContent = `exit ${d.exit_code}`;
  }
  // v25 — refresh inspector if it's currently showing this agent
  if (typeof refreshInspectorIfShowing === "function") {
    refreshInspectorIfShowing(d.label);
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
  // v21 — token approximation surfaced in panel header (~4 chars per token)
  if (p.tokensEl) {
    const approxTok = Math.round(text.length / 4);
    if (approxTok > 0) {
      p.tokensEl.hidden = false;
      p.tokensEl.textContent = `~${formatCount(approxTok)} tok`;
    }
  }
  // v21 — sticky-bottom auto-scroll: defer to the panel's tracked state
  const stickToBottom = (p.sticky && p.sticky.pinned !== false);
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
    // v26 — ANSI escape parsing in raw mode for true terminal feel
    const html = ansiToHtml(text);
    if (html.hasAnsi) {
      p.log.classList.add("ansi-rendered");
      p.log.innerHTML = html.html;
    } else {
      p.log.classList.remove("ansi-rendered");
      p.log.textContent = text;
    }
  }
  if (stickToBottom) p.log.scrollTop = p.log.scrollHeight;
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
  // v34 — per-section "Save API keys" button with inline status feedback
  if ($("#ss-save-keys-btn")) $("#ss-save-keys-btn").onclick = () => {
    saveSettingsForm();
    const status = document.getElementById("ss-save-keys-status");
    if (status) {
      const keys = [
        $("#setting-openrouter").value,
        $("#setting-zhipu").value,
        $("#setting-anthropic").value,
        $("#setting-gemini").value,
      ].filter(Boolean).length;
      status.textContent = keys
        ? `✓ Saved · ${keys} key${keys === 1 ? "" : "s"} active`
        : "✓ Saved (no keys configured yet)";
      status.className = "ss-save-status ss-save-status--ok";
      setTimeout(() => { status.className = "ss-save-status"; status.textContent = ""; }, 4000);
    }
    if (typeof toast === "function") toast("API keys saved to browser storage", 2000);
  };
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

  /* ============================================================
   * v19 — Status bar live wiring + ⌘K command palette
   * v20 — Resizable layout gutters
   * ============================================================ */
  initStatusBar();
  initCommandPalette();
  initResizeGutters();
  initLayoutToggle();
  initHeaderPalette();
  initInspector();
  initSlashCommands();
  initThemeToggle();
  initKeyboardSheet();
  initDragDropUpload();
});

/* ----------------------------------------------------------
 * v30 — Keyboard shortcuts cheat sheet (toggle with "?")
 * ---------------------------------------------------------- */
const KEYBOARD_SHORTCUTS = [
  { section: "Global", items: [
    { keys: ["⌘K", "Ctrl+K"],     desc: "Open command palette" },
    { keys: ["?"],                 desc: "Toggle this cheat sheet" },
    { keys: ["Esc"],               desc: "Close any open overlay" },
    { keys: ["Ctrl+Shift+L"],      desc: "Toggle dark / light theme" },
    { keys: ["I"],                 desc: "Toggle inspector rail" },
  ]},
  { section: "Layout", items: [
    { keys: ["Ctrl+\\"],           desc: "Collapse / expand workspace rail" },
    { keys: ["Ctrl+Shift+\\"],     desc: "Collapse / expand designer" },
    { keys: ["double-click gutter"], desc: "Collapse adjacent column" },
    { keys: ["drag gutter"],       desc: "Resize columns (persisted)" },
  ]},
  { section: "Visual canvas", items: [
    { keys: ["F"],                 desc: "Toggle fullscreen canvas" },
    { keys: ["0"],                 desc: "Reset zoom to 100%" },
    { keys: ["Ctrl + wheel"],      desc: "Zoom in / out" },
    { keys: ["drag node"],         desc: "Reposition (persisted per workspace)" },
    { keys: ["drag port → port"],  desc: "Add depends_on edge" },
    { keys: ["click edge"],        desc: "Remove dependency" },
  ]},
  { section: "Editor", items: [
    { keys: ["Ctrl+S"],            desc: "Save current workflow / file / note" },
    { keys: ["/"],                 desc: "Slash commands in any prompt" },
    { keys: ["Tab / Enter"],       desc: "Pick slash item" },
  ]},
  { section: "Run / monitor", items: [
    { keys: ["click panel"],       desc: "Inspect agent in right rail" },
    { keys: ["⧉ button"],          desc: "Copy this agent's full output" },
    { keys: ["⛶ button"],          desc: "Fullscreen this panel" },
    { keys: ["drag file → row"],   desc: "Auto-insert {{file:path}} placeholder" },
  ]},
];

function initKeyboardSheet() {
  let overlay = null;
  const close = () => {
    if (overlay) { overlay.remove(); overlay = null; }
  };
  document.addEventListener("keydown", (e) => {
    // "?" key — but ignore when typing in inputs
    if (e.key !== "?") return;
    const t = e.target;
    if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" ||
              t.isContentEditable || t.closest(".CodeMirror"))) return;
    e.preventDefault();
    if (overlay) return close();

    overlay = document.createElement("div");
    overlay.className = "kbd-sheet-overlay";
    overlay.innerHTML = `
      <div class="kbd-sheet-backdrop" title="Click to close"></div>
      <div class="kbd-sheet" role="dialog" aria-modal="true" aria-label="Keyboard shortcuts">
        <header class="kbd-sheet-head">
          <h3>Keyboard shortcuts</h3>
          <div class="kbd-sheet-head-actions">
            <button type="button" class="kbd-hint-btn" title="Close (Esc)">esc</button>
            <button type="button" class="kbd-sheet-x" title="Close" aria-label="Close">×</button>
          </div>
        </header>
        <div class="kbd-sheet-body">
          ${KEYBOARD_SHORTCUTS.map(sec => `
            <section class="kbd-sec">
              <h4>${escapeHtml(sec.section)}</h4>
              <ul>
                ${sec.items.map(it => `
                  <li>
                    <span class="kbd-keys">${it.keys.map(k =>
                      `<kbd>${escapeHtml(k)}</kbd>`).join('<span class="kbd-or">/</span>')}</span>
                    <span class="kbd-desc">${escapeHtml(it.desc)}</span>
                  </li>`).join("")}
              </ul>
            </section>`).join("")}
        </div>
        <footer class="kbd-sheet-foot">
          Press <kbd>?</kbd> again, <kbd>esc</kbd>, or click outside to close
        </footer>
      </div>`;
    document.body.appendChild(overlay);
    // v33 — wire all close affordances
    overlay.querySelector(".kbd-sheet-backdrop").addEventListener("click", close);
    overlay.querySelector(".kbd-hint-btn").addEventListener("click", close);
    overlay.querySelector(".kbd-sheet-x").addEventListener("click", close);
    const esc = (ev) => {
      if (ev.key === "Escape" || ev.key === "?") {
        ev.preventDefault();
        close();
        document.removeEventListener("keydown", esc);
      }
    };
    document.addEventListener("keydown", esc);
  });
}

/* ----------------------------------------------------------
 * v30 — Drag-and-drop file upload onto agent rows
 * Drag a file from your OS into any agent row → auto-inserts a
 * {{file:abs/path}} placeholder at the prompt caret. Also supports
 * dropping multiple files (joined with newlines).
 * ---------------------------------------------------------- */
function initDragDropUpload() {
  const isAgentRow = (el) =>
    el && el.closest && (el.closest(".agent-row") || el.closest(".vis-node"));

  document.addEventListener("dragover", (e) => {
    if (!isAgentRow(e.target)) return;
    if (!e.dataTransfer || !Array.from(e.dataTransfer.types || []).includes("Files")) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
    const row = isAgentRow(e.target);
    row.classList.add("drag-target");
  });

  document.addEventListener("dragleave", (e) => {
    const row = isAgentRow(e.target);
    if (row) row.classList.remove("drag-target");
  });

  document.addEventListener("drop", (e) => {
    const row = isAgentRow(e.target);
    if (!row) return;
    if (!e.dataTransfer || !e.dataTransfer.files || !e.dataTransfer.files.length) return;
    e.preventDefault();
    row.classList.remove("drag-target");

    const ta = row.querySelector(".prompt") || row.querySelector(".vne-prompt");
    if (!ta) return;
    const files = Array.from(e.dataTransfer.files);
    // We can't get full OS paths reliably (browser security) — files only
    // expose names. Insert a {{file:NAME}} placeholder which the user can
    // adjust. Nudge with a toast.
    const inserts = files.map(f => `{{file:${f.name}}}`).join("\n");
    const cur = ta.value || "";
    const at = ta.selectionEnd != null ? ta.selectionEnd : cur.length;
    ta.value = cur.slice(0, at) + inserts + cur.slice(at);
    ta.dispatchEvent(new Event("input"));
    if (typeof toast === "function") {
      toast(`Inserted ${files.length} file placeholder${files.length === 1 ? "" : "s"} — adjust the path if needed.`, 3000);
    }
  });
}

/* ----------------------------------------------------------
 * v29 — Theme toggle (dark / light)
 * Persists to localStorage[cg.theme]; default = dark.
 * Exposed via the ⌘K palette and Ctrl+Shift+L shortcut.
 * ---------------------------------------------------------- */
const CG_THEME_KEY = "cg.theme";

function applyTheme(theme) {
  if (theme === "light") {
    document.body.setAttribute("data-theme", "light");
  } else {
    document.body.removeAttribute("data-theme");
  }
}
function getTheme() {
  try { return localStorage.getItem(CG_THEME_KEY) || "dark"; }
  catch { return "dark"; }
}
function setTheme(theme) {
  applyTheme(theme);
  try { localStorage.setItem(CG_THEME_KEY, theme); } catch {}
  if (typeof toast === "function") {
    toast(`Theme: ${theme}`, 1200);
  }
}
function toggleTheme() {
  const cur = getTheme();
  setTheme(cur === "light" ? "dark" : "light");
}

function initThemeToggle() {
  applyTheme(getTheme());
  // Ctrl+Shift+L (Windows/Linux) and Cmd+Shift+L (Mac)
  document.addEventListener("keydown", (e) => {
    const isMac = navigator.platform.toUpperCase().includes("MAC");
    const mod = isMac ? e.metaKey : e.ctrlKey;
    if (mod && e.shiftKey && (e.key === "L" || e.key === "l")) {
      e.preventDefault();
      toggleTheme();
    }
  });
}

/* v23 — header search-bar opens the ⌘K palette */
function initHeaderPalette() {
  const btn = document.getElementById("header-palette-btn");
  if (btn) btn.addEventListener("click", openPalette);
}

/* ----------------------------------------------------------
 * v25 — Inspector rail
 * Right-side contextual panel; opens on agent click or via
 * toolbar toggle / keyboard "I". Persists visibility.
 * ---------------------------------------------------------- */
const CG_INSPECTOR_KEY = "cg.inspector.shown";
let _inspectorState = { agentLabel: null };

function initInspector() {
  const toggleBtn = document.getElementById("inspector-toggle-btn");
  const closeBtn  = document.getElementById("inspector-close-btn");
  const grid      = document.getElementById("agent-grid");

  // Restore visibility
  const stored = localStorage.getItem(CG_INSPECTOR_KEY) === "1";
  if (stored) document.body.classList.add("cg-inspector-shown");

  // Init col-3 width from layout state
  const layout = cgLoadLayout();
  if (layout.col3) {
    document.documentElement.style.setProperty("--cg-col-3", `${layout.col3}px`);
  }

  if (toggleBtn) toggleBtn.addEventListener("click", () => toggleInspector());
  if (closeBtn)  closeBtn.addEventListener("click", () => setInspectorShown(false));

  // Click any agent panel → populate inspector + show
  if (grid) {
    grid.addEventListener("click", (e) => {
      const panel = e.target.closest(".agent-panel");
      if (!panel) return;
      // Don't capture clicks on action buttons
      if (e.target.closest(".ap-action") || e.target.closest("button")) return;
      const label = findAgentLabelFromPanel(panel);
      if (label) {
        renderInspector(label);
        setInspectorShown(true);
        // Highlight selected
        grid.querySelectorAll(".agent-panel.is-selected")
            .forEach(p => p.classList.remove("is-selected"));
        panel.classList.add("is-selected");
      }
    });
  }

  // Keyboard "i" toggles inspector (when not typing in an input)
  document.addEventListener("keydown", (e) => {
    if (e.key !== "i" && e.key !== "I") return;
    const t = e.target;
    if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" ||
              t.isContentEditable || t.closest(".CodeMirror"))) return;
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    e.preventDefault();
    toggleInspector();
  });
}

function findAgentLabelFromPanel(panel) {
  if (!panel || !state || !state.panels) return null;
  for (const [label, p] of Object.entries(state.panels)) {
    if (p && p.root === panel) return label;
  }
  // Fallback: read .agent-label text
  const labelEl = panel.querySelector(".agent-label");
  return labelEl ? labelEl.textContent.trim() : null;
}

function toggleInspector() {
  setInspectorShown(!document.body.classList.contains("cg-inspector-shown"));
}
function setInspectorShown(show) {
  document.body.classList.toggle("cg-inspector-shown", !!show);
  try { localStorage.setItem(CG_INSPECTOR_KEY, show ? "1" : "0"); } catch {}
}

function renderInspector(agentLabel) {
  const body = document.getElementById("inspector-body");
  if (!body) return;
  _inspectorState.agentLabel = agentLabel;

  // Find agent spec from current state.spec or panels
  const spec = (state.spec && Array.isArray(state.spec))
    ? state.spec.find(a => a.label === agentLabel)
    : null;
  const panel = state.panels && state.panels[agentLabel];

  if (!spec && !panel) {
    body.innerHTML = `<div class="inspector-empty">
      <span class="inspector-empty-glyph">?</span>
      <p>Couldn't find spec for <strong>${escapeHtml(agentLabel)}</strong>.</p>
    </div>`;
    return;
  }

  const fam = spec ? familyOf(spec.agent) : "other";
  const model = spec ? spec.agent : "(unknown)";
  const status = panel
    ? (panel.statusBadge.querySelector(".badge-text")?.textContent || "queued")
    : "queued";
  const buf = (panel && panel.rawBuffer) || "";
  const charCount = buf.length;
  const tokApprox = Math.round(charCount / 4);
  const elapsedTxt = panel && panel.elapsedEl
    ? (panel.elapsedEl.textContent || "--:--") : "--:--";
  const deps = (spec && spec.depends_on && spec.depends_on.length)
    ? spec.depends_on.join(", ") : "—";
  const streaming = spec && spec.streaming ? "yes" : "—";
  const promptText = spec ? (spec.prompt || "") : "";

  body.innerHTML = `
    <section class="ins-section">
      <span class="ins-section-title">Agent</span>
      <div class="ins-row">
        <span class="ins-row-label">Label</span>
        <span class="ins-row-value">${escapeHtml(agentLabel)}</span>
      </div>
      <div class="ins-row">
        <span class="ins-row-label">Model</span>
        <span class="ins-row-value">
          <span class="badge ${fam}">${escapeHtml(shortAgentLabel(model))}</span>
        </span>
      </div>
      <div class="ins-row">
        <span class="ins-row-label">Family</span>
        <span class="ins-row-value">${escapeHtml(fam)}</span>
      </div>
      <div class="ins-row">
        <span class="ins-row-label">Depends</span>
        <span class="ins-row-value">${escapeHtml(deps)}</span>
      </div>
      <div class="ins-row">
        <span class="ins-row-label">Streaming</span>
        <span class="ins-row-value">${escapeHtml(streaming)}</span>
      </div>
    </section>

    <section class="ins-section">
      <span class="ins-section-title">Live state</span>
      <div class="ins-row">
        <span class="ins-row-label">Status</span>
        <span class="ins-row-value">
          <span class="badge status ${escapeHtml(status)}">
            <span class="badge-dot"></span>
            <span class="badge-text">${escapeHtml(status)}</span>
          </span>
        </span>
      </div>
      <div class="ins-row">
        <span class="ins-row-label">Elapsed</span>
        <span class="ins-row-value">${escapeHtml(elapsedTxt)}</span>
      </div>
      <div class="ins-row">
        <span class="ins-row-label">Output</span>
        <span class="ins-row-value">
          ${formatCount(charCount)} chars · ~${formatCount(tokApprox)} tok
        </span>
      </div>
    </section>

    <section class="ins-section">
      <span class="ins-section-title">Prompt</span>
      <div class="ins-prompt" id="ins-prompt-box">${escapeHtml(promptText) || '<em>(empty)</em>'}</div>
      <div class="ins-actions">
        <button class="ghost" id="ins-copy-prompt">Copy prompt</button>
        <button class="ghost" id="ins-copy-output">Copy output</button>
        <button class="ghost" id="ins-jump-row">Jump to designer row</button>
      </div>
    </section>
  `;

  document.getElementById("ins-copy-prompt").onclick = () => {
    navigator.clipboard.writeText(promptText || "");
    if (typeof toast === "function") toast("Prompt copied", 1200);
  };
  document.getElementById("ins-copy-output").onclick = () => {
    navigator.clipboard.writeText(buf || "");
    if (typeof toast === "function") toast(`Output copied (${formatCount(charCount)} chars)`, 1200);
  };
  document.getElementById("ins-jump-row").onclick = () => {
    const rows = document.querySelectorAll("#agent-rows .agent-row");
    rows.forEach(r => {
      const labelInput = r.querySelector('input[name="label"]');
      if (labelInput && labelInput.value === agentLabel) {
        r.scrollIntoView({ behavior: "smooth", block: "center" });
        r.classList.add("is-flash");
        setTimeout(() => r.classList.remove("is-flash"), 1200);
      }
    });
  };
}

/* Refresh inspector when status events flow in (live update) */
function refreshInspectorIfShowing(label) {
  if (!_inspectorState.agentLabel || _inspectorState.agentLabel !== label) return;
  if (!document.body.classList.contains("cg-inspector-shown")) return;
  renderInspector(label);
}

/* ----------------------------------------------------------
 * v22 — Agent grid layout selector (CMUX-style tiled mode)
 * Modes: auto (default) | 1 (single) | 2 (cols) | 4 (2x2) | n (compact)
 * ---------------------------------------------------------- */
const CG_LAYOUT_MODE_KEY = "cg.layoutMode.v1";

function initLayoutToggle() {
  const toggle = document.getElementById("layout-toggle");
  const grid   = document.getElementById("agent-grid");
  if (!toggle || !grid) return;

  const stored = (() => {
    try { return localStorage.getItem(CG_LAYOUT_MODE_KEY) || "auto"; }
    catch { return "auto"; }
  })();

  const apply = (mode) => {
    grid.classList.remove("layout-auto", "layout-1", "layout-2", "layout-4", "layout-n");
    if (mode && mode !== "auto") grid.classList.add(`layout-${mode}`);
    toggle.querySelectorAll(".seg").forEach(b => {
      b.classList.toggle("active", b.dataset.layout === mode);
    });
    try { localStorage.setItem(CG_LAYOUT_MODE_KEY, mode); } catch {}
  };

  toggle.querySelectorAll(".seg").forEach(btn => {
    btn.addEventListener("click", () => apply(btn.dataset.layout));
  });

  apply(stored);
}

/* ----------------------------------------------------------
 * v20 — Resizable layout gutters
 * Drag to resize columns, double-click to collapse, persist to
 * localStorage[cg.layout.v1]. Keyboard: Ctrl+\ collapses rail,
 * Ctrl+Shift+\ collapses designer.
 * ---------------------------------------------------------- */
const CG_LAYOUT_KEY = "cg.layout.v1";
const CG_LAYOUT_DEFAULTS = {
  col1: 56,    // workspaces rail (px)
  col2: 380,   // designer (px)
  col2v: null, // designer in visual mode (null = 1fr)
  col3: 340,   // inspector (px) — only visible when shown
  railCollapsed: false,
  designerCollapsed: false,
};
const CG_LAYOUT_BOUNDS = {
  col1: { min: 0, max: 240, snap: 56 },
  col2: { min: 240, max: 720, snap: 380 },
  col3: { min: 240, max: 560, snap: 340 },
};

function cgLoadLayout() {
  try {
    const raw = localStorage.getItem(CG_LAYOUT_KEY);
    if (!raw) return { ...CG_LAYOUT_DEFAULTS };
    return { ...CG_LAYOUT_DEFAULTS, ...JSON.parse(raw) };
  } catch {
    return { ...CG_LAYOUT_DEFAULTS };
  }
}
function cgSaveLayout(layout) {
  try {
    localStorage.setItem(CG_LAYOUT_KEY, JSON.stringify(layout));
  } catch {}
}
function cgApplyLayout(layout) {
  const root = document.documentElement;
  root.style.setProperty("--cg-col-1", `${layout.col1}px`);
  root.style.setProperty("--cg-col-2", `${layout.col2}px`);
  if (layout.col3) {
    root.style.setProperty("--cg-col-3", `${layout.col3}px`);
  }
  if (layout.col2v != null) {
    root.style.setProperty("--cg-col-2-visual", `${layout.col2v}px`);
  } else {
    root.style.setProperty("--cg-col-2-visual", "1fr");
  }
  document.body.classList.toggle("cg-rail-collapsed", !!layout.railCollapsed);
  document.body.classList.toggle("cg-designer-collapsed", !!layout.designerCollapsed);
}

function initResizeGutters() {
  const layout = cgLoadLayout();
  cgApplyLayout(layout);

  const gutters = document.querySelectorAll(".resize-gutter");
  if (!gutters.length) return;

  let drag = null;

  gutters.forEach(g => {
    g.addEventListener("pointerdown", (e) => {
      e.preventDefault();
      g.setPointerCapture(e.pointerId);
      g.classList.add("is-dragging");
      document.body.classList.add("cg-resizing");
      const which = g.dataset.gutter;
      const startX = e.clientX;
      const startLayout = cgLoadLayout();
      drag = { which, startX, startLayout, gutter: g };
    });

    g.addEventListener("pointermove", (e) => {
      if (!drag || drag.gutter !== g) return;
      const dx = e.clientX - drag.startX;
      const layout = { ...drag.startLayout };
      const visualMode = document.body.classList.contains("visual-mode-active");

      if (drag.which === "ws-designer") {
        const next = drag.startLayout.col1 + dx;
        const b = CG_LAYOUT_BOUNDS.col1;
        layout.col1 = Math.max(b.min, Math.min(b.max, next));
        layout.railCollapsed = layout.col1 < 12;
      } else if (drag.which === "designer-monitor") {
        const next = drag.startLayout.col2 + dx;
        const b = CG_LAYOUT_BOUNDS.col2;
        const max = window.innerWidth - drag.startLayout.col1 - 280;
        layout.col2 = Math.max(b.min, Math.min(Math.min(b.max, max), next));
        // In visual mode also drive col2v (proportional designer pane)
        if (visualMode) {
          layout.col2v = layout.col2;
        }
      } else if (drag.which === "monitor-inspector") {
        // Drag right gutter → invert dx (drag left = wider inspector)
        const next = drag.startLayout.col3 - dx;
        const b = CG_LAYOUT_BOUNDS.col3;
        layout.col3 = Math.max(b.min, Math.min(b.max, next));
      }
      cgApplyLayout(layout);
      drag.startLayout._latest = layout;
    });

    const finishDrag = (e) => {
      if (!drag || drag.gutter !== g) return;
      g.classList.remove("is-dragging");
      document.body.classList.remove("cg-resizing");
      try { g.releasePointerCapture(e.pointerId); } catch {}
      const final = drag.startLayout._latest || drag.startLayout;
      cgSaveLayout(final);
      drag = null;
    };
    g.addEventListener("pointerup", finishDrag);
    g.addEventListener("pointercancel", finishDrag);

    // Double-click — toggle collapse of the column on the appropriate side.
    g.addEventListener("dblclick", () => {
      const layout = cgLoadLayout();
      if (g.dataset.gutter === "ws-designer") {
        layout.railCollapsed = !layout.railCollapsed;
        if (!layout.railCollapsed && layout.col1 < 12) {
          layout.col1 = CG_LAYOUT_BOUNDS.col1.snap;
        }
      } else if (g.dataset.gutter === "designer-monitor") {
        layout.designerCollapsed = !layout.designerCollapsed;
        if (!layout.designerCollapsed && layout.col2 < 240) {
          layout.col2 = CG_LAYOUT_BOUNDS.col2.snap;
        }
      } else if (g.dataset.gutter === "monitor-inspector") {
        // Double-click on inspector gutter closes the inspector
        document.body.classList.remove("cg-inspector-shown");
        try { localStorage.setItem("cg.inspector.shown", "0"); } catch {}
      }
      cgApplyLayout(layout);
      cgSaveLayout(layout);
    });
  });

  // Keyboard shortcuts: Ctrl+\ / Ctrl+Shift+\
  document.addEventListener("keydown", (e) => {
    if (e.ctrlKey && e.key === "\\") {
      e.preventDefault();
      const layout = cgLoadLayout();
      if (e.shiftKey) {
        layout.designerCollapsed = !layout.designerCollapsed;
      } else {
        layout.railCollapsed = !layout.railCollapsed;
      }
      cgApplyLayout(layout);
      cgSaveLayout(layout);
    }
  });
}

/* ----------------------------------------------------------
 * Status bar — backend connection + live run/queue counters
 * ---------------------------------------------------------- */
function initStatusBar() {
  const dot     = document.getElementById("sb-backend-dot");
  const lbl     = document.getElementById("sb-backend-label");
  const runsEl  = document.getElementById("sb-runs");
  const qEl     = document.getElementById("sb-queued");
  const tDot    = document.getElementById("sb-tunnel-dot");
  const tLbl    = document.getElementById("sb-tunnel-label");
  const elapsedBtn = document.getElementById("sb-elapsed-btn");
  const elapsedEl  = document.getElementById("sb-elapsed");
  const elapsedLbl = document.getElementById("sb-elapsed-label");
  if (!dot) return;

  // Hide redundant header status pill — status-bar is the source of truth now
  const headerStatus = document.getElementById("server-status");
  if (headerStatus) headerStatus.style.display = "none";

  const setBackend = (state, text) => {
    dot.className = "sb-dot sb-dot--" + state;
    lbl.textContent = text;
  };
  setBackend("connecting", "connecting…");

  // Click-to-jump segments
  document.querySelectorAll(".status-bar .sb-seg[data-target]").forEach(btn => {
    btn.addEventListener("click", () => {
      const target = btn.dataset.target;
      if (target === "tunnel") activateTab("settings");
      else if (target === "palette") openPalette();
      else if (target === "runs") activateTab("orchestrator");
      else if (target === "elapsed") {
        // Scroll to live monitor
        const grid = document.getElementById("agent-grid");
        if (grid) grid.scrollIntoView({ behavior: "smooth" });
      }
    });
  });

  // Poll backend state every 4s
  let elapsedStart = null;
  let elapsedTimer = null;

  async function poll() {
    try {
      const r = await fetch("/api/runs?limit=20", { cache: "no-store" });
      if (!r.ok) throw new Error(r.status);
      const j = await r.json();
      const runs = (j.runs || []);
      const running = runs.filter(x => x.state === "running").length;
      const queued  = runs.filter(x => x.state === "queued" || x.state === "pending").length;
      setBackend("connected", "online");
      runsEl.textContent = `${running} run${running === 1 ? "" : "s"}`;
      qEl.textContent = `· ${queued} queued`;

      // Active-run elapsed timer
      const activeRun = runs.find(x => x.state === "running");
      if (activeRun) {
        const startMs = activeRun.started_at
          ? Date.parse(activeRun.started_at)
          : Date.now();
        if (elapsedStart !== startMs) {
          elapsedStart = startMs;
          if (elapsedLbl) elapsedLbl.textContent = activeRun.title || activeRun.id || "";
          if (elapsedTimer) clearInterval(elapsedTimer);
          elapsedTimer = setInterval(() => {
            if (!elapsedStart) return;
            const s = Math.floor((Date.now() - elapsedStart) / 1000);
            const mm = String(Math.floor(s / 60)).padStart(2, "0");
            const ss = String(s % 60).padStart(2, "0");
            elapsedEl.textContent = `${mm}:${ss}`;
          }, 1000);
        }
        elapsedBtn.hidden = false;
      } else {
        elapsedStart = null;
        if (elapsedTimer) clearInterval(elapsedTimer);
        elapsedTimer = null;
        elapsedBtn.hidden = true;
      }

      // Tunnel state (best-effort; endpoint may not be ready)
      try {
        const tr = await fetch("/api/tunnel/status", { cache: "no-store" });
        if (tr.ok) {
          const tj = await tr.json();
          if (tj.running) {
            tDot.className = "sb-dot sb-dot--connected";
            tLbl.textContent = "tunnel ✓";
          } else {
            tDot.className = "sb-dot";
            tLbl.textContent = "tunnel";
          }
        }
      } catch {}
    } catch (e) {
      setBackend("error", "offline");
    }
  }

  poll();
  setInterval(poll, 4000);
}

/* ----------------------------------------------------------
 * ⌘K Command palette — fuzzy launcher
 * ---------------------------------------------------------- */
let _paletteState = {
  open: false,
  items: [],
  filtered: [],
  active: 0,
  query: "",
};

function initCommandPalette() {
  const backdrop = document.getElementById("palette-backdrop");
  const palette  = document.getElementById("palette");
  const input    = document.getElementById("palette-input");
  const results  = document.getElementById("palette-results");
  if (!palette || !input) return;

  // Global keyboard shortcut ⌘K / Ctrl+K
  document.addEventListener("keydown", (e) => {
    const isMac = navigator.platform.toUpperCase().includes("MAC");
    const mod = isMac ? e.metaKey : e.ctrlKey;
    if (mod && (e.key === "k" || e.key === "K")) {
      e.preventDefault();
      if (_paletteState.open) closePalette();
      else openPalette();
    } else if (e.key === "Escape" && _paletteState.open) {
      e.preventDefault();
      closePalette();
    }
  });

  backdrop.addEventListener("click", closePalette);

  // v32 + v33 — explicit close affordances (4 buttons + capture Esc)
  ["palette-esc-btn", "palette-close-btn", "palette-x-big"].forEach(id => {
    const btn = document.getElementById(id);
    if (btn) btn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      closePalette();
    });
  });

  // v33 — drag the palette by its titlebar; double-click = recenter
  const titlebar = document.getElementById("palette-titlebar");
  if (titlebar) {
    let drag = null;
    titlebar.addEventListener("pointerdown", (e) => {
      // Don't start drag from the × button
      if (e.target.closest(".palette-titlebar-x")) return;
      e.preventDefault();
      titlebar.setPointerCapture(e.pointerId);
      const rect = palette.getBoundingClientRect();
      drag = {
        startX: e.clientX,
        startY: e.clientY,
        origLeft: rect.left,
        origTop:  rect.top,
        pointerId: e.pointerId,
      };
      palette.classList.add("is-dragging");
    });
    titlebar.addEventListener("pointermove", (e) => {
      if (!drag) return;
      const dx = e.clientX - drag.startX;
      const dy = e.clientY - drag.startY;
      const newLeft = Math.max(0, Math.min(window.innerWidth - 320, drag.origLeft + dx));
      const newTop  = Math.max(0, Math.min(window.innerHeight - 100, drag.origTop + dy));
      palette.style.left = `${newLeft}px`;
      palette.style.top = `${newTop}px`;
      palette.style.transform = "none";
    });
    const endDrag = (e) => {
      if (!drag) return;
      try { titlebar.releasePointerCapture(drag.pointerId); } catch {}
      drag = null;
      palette.classList.remove("is-dragging");
    };
    titlebar.addEventListener("pointerup", endDrag);
    titlebar.addEventListener("pointercancel", endDrag);
    titlebar.addEventListener("dblclick", (e) => {
      if (e.target.closest(".palette-titlebar-x")) return;
      // Recenter
      palette.style.left = "";
      palette.style.top = "";
      palette.style.transform = "";
    });
  }

  input.addEventListener("input", () => {
    _paletteState.query = input.value;
    _paletteState.active = 0;
    renderPalette();
  });

  input.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      _paletteState.active = Math.min(
        _paletteState.active + 1,
        _paletteState.filtered.length - 1
      );
      renderPalette({ keepFiltered: true });
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      _paletteState.active = Math.max(_paletteState.active - 1, 0);
      renderPalette({ keepFiltered: true });
    } else if (e.key === "Enter") {
      e.preventDefault();
      const item = _paletteState.filtered[_paletteState.active];
      if (item) executePaletteItem(item);
    } else if (e.key === "Escape") {
      // v32 — belt-and-suspenders: also close from input directly
      e.preventDefault();
      e.stopPropagation();
      closePalette();
    }
  });
}

function buildPaletteItems() {
  const items = [];

  // Tabs / navigation
  ["orchestrator", "editor", "notes", "settings"].forEach(t => {
    items.push({
      section: "Jump to",
      icon: { orchestrator: "▶", editor: "✎", notes: "✦", settings: "⚙" }[t] || "•",
      label: t.charAt(0).toUpperCase() + t.slice(1),
      hint: `Switch to ${t} tab`,
      meta: "TAB",
      run: () => activateTab(t),
    });
  });

  // Presets
  const presetSelect = document.getElementById("preset-select");
  if (presetSelect) {
    Array.from(presetSelect.options).forEach(opt => {
      if (!opt.value) return;
      items.push({
        section: "Run",
        icon: "▶",
        label: opt.textContent,
        hint: `Load preset and run`,
        meta: "PRESET",
        run: () => {
          presetSelect.value = opt.value;
          presetSelect.dispatchEvent(new Event("change"));
          const runBtn = document.getElementById("run-btn");
          if (runBtn) setTimeout(() => runBtn.click(), 300);
        },
      });
    });
  }

  // Saved workflows
  const wfSelect = document.getElementById("workflow-select");
  if (wfSelect) {
    Array.from(wfSelect.options).forEach(opt => {
      if (!opt.value) return;
      items.push({
        section: "Run",
        icon: "📁",
        label: opt.textContent,
        hint: `Load saved workflow`,
        meta: "WORKFLOW",
        run: () => {
          wfSelect.value = opt.value;
          wfSelect.dispatchEvent(new Event("change"));
          activateTab("orchestrator");
        },
      });
    });
  }

  // Active runs
  const histList = document.getElementById("history");
  if (histList) {
    Array.from(histList.querySelectorAll("li")).slice(0, 12).forEach((li, i) => {
      const txt = (li.textContent || "").trim().slice(0, 70);
      if (!txt) return;
      items.push({
        section: "Recent runs",
        icon: "⏱",
        label: txt,
        hint: "Open this run",
        meta: "RUN",
        run: () => {
          li.click();
          activateTab("orchestrator");
        },
      });
    });
  }

  // Settings actions
  items.push({
    section: "Help",
    icon: "?",
    label: "Keyboard shortcuts",
    hint: "Open the cheat sheet (?)",
    meta: "HELP",
    run: () => {
      // Synthesize a "?" keypress so initKeyboardSheet handles it
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "?" }));
    },
  });
  items.push({
    section: "Settings",
    icon: "🌓",
    label: getTheme() === "light" ? "Switch to dark mode" : "Switch to light mode",
    hint: "Ctrl+Shift+L · cream paper ↔ warm-black",
    meta: "THEME",
    run: () => toggleTheme(),
  });
  items.push({
    section: "Settings",
    icon: "🌐",
    label: "Toggle Cloudflare Tunnel",
    hint: "Phone dispatch on/off",
    meta: "ACTION",
    run: () => {
      activateTab("settings");
      setTimeout(() => {
        const btn = document.getElementById("tunnel-start-btn");
        if (btn) btn.scrollIntoView({ behavior: "smooth", block: "center" });
      }, 100);
    },
  });
  items.push({
    section: "Settings",
    icon: "🔑",
    label: "API keys",
    hint: "Configure provider credentials",
    meta: "ACTION",
    run: () => {
      activateTab("settings");
      setTimeout(() => {
        const el = document.getElementById("setting-openrouter");
        if (el) el.focus();
      }, 100);
    },
  });
  items.push({
    section: "Actions",
    icon: "↻",
    label: "Re-run last workflow",
    hint: "Runs whatever is currently in the designer",
    meta: "ACTION",
    run: () => {
      activateTab("orchestrator");
      const btn = document.getElementById("run-btn");
      if (btn) btn.click();
    },
  });
  items.push({
    section: "Actions",
    icon: "💾",
    label: "Save current workflow",
    hint: "Ctrl+S",
    meta: "ACTION",
    run: () => {
      const btn = document.getElementById("save-workflow-btn");
      if (btn) btn.click();
    },
  });

  return items;
}

function fuzzyScore(query, text) {
  if (!query) return 1;
  const q = query.toLowerCase();
  const t = text.toLowerCase();
  if (t.includes(q)) return 100 - t.indexOf(q);
  // letter-skip fuzzy
  let qi = 0;
  for (let i = 0; i < t.length && qi < q.length; i++) {
    if (t[i] === q[qi]) qi++;
  }
  return qi === q.length ? 50 - (t.length - q.length) * 0.1 : 0;
}

function renderPalette(opts = {}) {
  const results = document.getElementById("palette-results");
  if (!results) return;

  if (!opts.keepFiltered) {
    const q = _paletteState.query;
    _paletteState.filtered = _paletteState.items
      .map(item => ({
        item,
        score: fuzzyScore(q, item.label) + fuzzyScore(q, item.hint || "") * 0.3,
      }))
      .filter(x => x.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, 30)
      .map(x => x.item);

    if (_paletteState.active >= _paletteState.filtered.length) {
      _paletteState.active = 0;
    }
  }

  if (_paletteState.filtered.length === 0) {
    const q = escapeHtml(_paletteState.query || "");
    results.innerHTML = `
      <div class="palette-empty">
        <div class="palette-empty-glyph">⌖</div>
        <p class="palette-empty-msg">
          No matches for <code>${q}</code>.
        </p>
        <p class="palette-empty-hint">
          Try a different keyword, or close to dismiss.
        </p>
        <div class="palette-empty-actions">
          <button type="button" class="ghost" id="pe-clear">Clear search</button>
          <button type="button" class="primary" id="pe-close">Close palette</button>
        </div>
      </div>`;
    const clearBtn = document.getElementById("pe-clear");
    const closeBtn2 = document.getElementById("pe-close");
    if (clearBtn) clearBtn.onclick = () => {
      const inp = document.getElementById("palette-input");
      if (inp) { inp.value = ""; inp.focus(); }
      _paletteState.query = "";
      _paletteState.active = 0;
      renderPalette();
    };
    if (closeBtn2) closeBtn2.onclick = closePalette;
    return;
  }

  // Group by section, preserve relative order
  const sections = [];
  const seen = new Set();
  _paletteState.filtered.forEach(it => {
    if (!seen.has(it.section)) {
      sections.push({ name: it.section, items: [] });
      seen.add(it.section);
    }
    sections.find(s => s.name === it.section).items.push(it);
  });

  let html = "";
  let absIdx = 0;
  sections.forEach(sec => {
    html += `<div class="palette-section-head">${escapeHtml(sec.name)}</div>`;
    sec.items.forEach(it => {
      const isActive = absIdx === _paletteState.active;
      html += `
        <div class="palette-item ${isActive ? "is-active" : ""}"
             data-idx="${absIdx}">
          <span class="palette-item-icon">${escapeHtml(it.icon || "•")}</span>
          <div class="palette-item-body">
            <div class="palette-item-label">${escapeHtml(it.label)}</div>
            ${it.hint ? `<div class="palette-item-hint">${escapeHtml(it.hint)}</div>` : ""}
          </div>
          <span class="palette-item-meta">${escapeHtml(it.meta || "")}</span>
        </div>`;
      absIdx++;
    });
  });
  results.innerHTML = html;

  // Wire click handlers
  results.querySelectorAll(".palette-item").forEach(el => {
    el.addEventListener("click", () => {
      const idx = Number(el.dataset.idx);
      const it = _paletteState.filtered[idx];
      if (it) executePaletteItem(it);
    });
  });

  // Scroll active into view
  const activeEl = results.querySelector(".palette-item.is-active");
  if (activeEl) {
    activeEl.scrollIntoView({ block: "nearest" });
  }
}

function executePaletteItem(item) {
  closePalette();
  try { item.run(); }
  catch (e) {
    if (typeof toast === "function") toast(`Failed: ${e.message || e}`);
  }
}

function openPalette() {
  if (_paletteState.open) return;
  _paletteState.open = true;
  _paletteState.items = buildPaletteItems();
  _paletteState.filtered = _paletteState.items;
  _paletteState.active = 0;
  _paletteState.query = "";
  const backdrop = document.getElementById("palette-backdrop");
  const palette  = document.getElementById("palette");
  const input    = document.getElementById("palette-input");
  if (!palette) return;
  // Reset position to center if previously dragged
  palette.style.left = "";
  palette.style.top = "";
  palette.style.transform = "";
  backdrop.hidden = false;
  palette.hidden = false;
  input.value = "";
  renderPalette();
  setTimeout(() => input.focus(), 30);
}

/* v33 — bullet-proof close: force-hide regardless of state flag.
 * Previously an out-of-sync _paletteState.open could early-return here
 * and leave the palette stuck visible. */
function closePalette() {
  _paletteState.open = false;
  const bd = document.getElementById("palette-backdrop");
  const p  = document.getElementById("palette");
  if (bd) bd.hidden = true;
  if (p)  { p.hidden = true; p.style.left = ""; p.style.top = ""; p.style.transform = ""; }
}

/* v33 — capture-phase Esc listener. Runs BEFORE any other keydown
 * handler, so even if some component swallows Escape it still closes
 * any open overlay. */
window.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  const bd = document.getElementById("palette-backdrop");
  if (bd && !bd.hidden) {
    e.preventDefault();
    closePalette();
  }
}, true);

function activateTab(name) {
  const tab = document.querySelector(`.tab[data-tab="${name}"]`);
  if (tab) tab.click();
}

/* v36 — duplicate escapeHtml() removed; the canonical one at line
 * ~2291 also escapes single quotes (XSS-safer). This duplicate was
 * overriding it via JS declaration hoisting, leaving rendered output
 * vulnerable to ' in user-supplied strings. */

/* ============================================================
 * v26 — ANSI escape sequence parser (raw mode → colored HTML)
 * Supports SGR (\x1b[...m) for 8 colors + bright + bold + underline +
 * 256-color fg/bg + reset. Strips other CSI sequences (cursor moves
 * etc.) so they don't render as garbage.
 * ============================================================ */
const ANSI_BASE_FG = {
  30: "ansi-black",   31: "ansi-red",    32: "ansi-green",  33: "ansi-yellow",
  34: "ansi-blue",    35: "ansi-magenta",36: "ansi-cyan",   37: "ansi-white",
  90: "ansi-br-black",91: "ansi-br-red", 92: "ansi-br-green",93: "ansi-br-yellow",
  94: "ansi-br-blue", 95: "ansi-br-magenta",96: "ansi-br-cyan",97: "ansi-br-white",
};
const ANSI_BASE_BG = {
  40: "ansi-bg-black",   41: "ansi-bg-red",    42: "ansi-bg-green",
  43: "ansi-bg-yellow",  44: "ansi-bg-blue",   45: "ansi-bg-magenta",
  46: "ansi-bg-cyan",    47: "ansi-bg-white",
  100:"ansi-bg-br-black",101:"ansi-bg-br-red", 102:"ansi-bg-br-green",
  103:"ansi-bg-br-yellow",104:"ansi-bg-br-blue",105:"ansi-bg-br-magenta",
  106:"ansi-bg-br-cyan", 107:"ansi-bg-br-white",
};

/* ============================================================
 * v27 — Drag-to-connect for the Visual canvas
 * Pointerdown on a node's output port (right circle) → drag a ghost
 * bezier to cursor → pointerup over another node's input port creates
 * a depends_on edge in the spec. Cancel on Escape or release elsewhere.
 * ============================================================ */
function attachWireDragHandlers(svg, spec, positions) {
  // Attach once per render — clear handlers from prior render via dataset flag
  if (svg.__cgWireBound) return;
  svg.__cgWireBound = true;

  const NS = "http://www.w3.org/2000/svg";
  let drag = null;

  const screenToCanvas = (clientX, clientY) => {
    const pt = svg.createSVGPoint();
    pt.x = clientX; pt.y = clientY;
    const ctm = svg.getScreenCTM();
    if (!ctm) return { x: 0, y: 0 };
    const m = ctm.inverse();
    const local = pt.matrixTransform(m);
    return { x: local.x, y: local.y };
  };

  svg.addEventListener("pointerdown", (e) => {
    const port = e.target.closest(".vis-port--out");
    if (!port) return;
    e.preventDefault();
    e.stopPropagation();

    const fromLabel = port.dataset.label;
    const startX = Number(port.getAttribute("cx"));
    const startY = Number(port.getAttribute("cy"));

    const ghost = document.createElementNS(NS, "path");
    ghost.classList.add("vis-wire-ghost");
    ghost.setAttribute("d", `M ${startX} ${startY} L ${startX} ${startY}`);
    ghost.setAttribute("marker-end", "url(#arrowhead)");
    svg.querySelector(".connections-layer").appendChild(ghost);

    drag = { fromLabel, startX, startY, ghost, pointerId: e.pointerId };
    svg.setPointerCapture(e.pointerId);
    svg.classList.add("wire-dragging");
  });

  svg.addEventListener("pointermove", (e) => {
    if (!drag) return;
    const { x, y } = screenToCanvas(e.clientX, e.clientY);
    const dx = Math.max(40, (x - drag.startX) / 2);
    drag.ghost.setAttribute("d",
      `M ${drag.startX} ${drag.startY} ` +
      `C ${drag.startX + dx} ${drag.startY}, ` +
      `${x - dx} ${y}, ` +
      `${x} ${y}`);
    // Highlight any input port under cursor
    svg.querySelectorAll(".vis-port--in").forEach(p => p.classList.remove("vis-port--target"));
    const under = document.elementFromPoint(e.clientX, e.clientY);
    if (under && under.classList && under.classList.contains("vis-port--in")
        && under.dataset.label !== drag.fromLabel) {
      under.classList.add("vis-port--target");
    }
  });

  const endDrag = (e) => {
    if (!drag) return;
    let dropped = false;
    const under = document.elementFromPoint(e.clientX, e.clientY);
    if (under && under.classList && under.classList.contains("vis-port--in")) {
      const toLabel = under.dataset.label;
      if (toLabel && toLabel !== drag.fromLabel) {
        addDepInDesigner(toLabel, drag.fromLabel);
        dropped = true;
      }
    }
    drag.ghost.remove();
    svg.querySelectorAll(".vis-port--target").forEach(p => p.classList.remove("vis-port--target"));
    svg.classList.remove("wire-dragging");
    try { svg.releasePointerCapture(drag.pointerId); } catch {}
    drag = null;
    if (dropped) renderVisualCanvas();
  };
  svg.addEventListener("pointerup", endDrag);
  svg.addEventListener("pointercancel", endDrag);

  // Esc cancels
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && drag) {
      drag.ghost.remove();
      svg.classList.remove("wire-dragging");
      svg.querySelectorAll(".vis-port--target").forEach(p => p.classList.remove("vis-port--target"));
      drag = null;
    }
  });
}

/* Patch a depends_on entry into the classic agent-row designer.
 * Used by drag-to-connect. Idempotent — won't add duplicates. */
function addDepInDesigner(targetLabel, depLabel) {
  const rows = document.querySelectorAll("#agent-rows .agent-row");
  let target = null;
  rows.forEach((row, i) => {
    const labelInput = row.querySelector(".label");
    const rowLabel = (labelInput && labelInput.value.trim()) || `agent-${i + 1}`;
    if (rowLabel === targetLabel) target = row;
  });
  if (!target) return;
  const dInp = target.querySelector(".depends_on");
  if (!dInp) return;
  const existing = (dInp.value || "").split(",").map(x => x.trim()).filter(Boolean);
  if (existing.includes(depLabel)) return;
  existing.push(depLabel);
  dInp.value = existing.join(",");
  dInp.dispatchEvent(new Event("change"));
  if (typeof toast === "function") toast(`Connected: ${depLabel} → ${targetLabel}`, 1500);
}

function ansiToHtml(input) {
  if (!input) return { html: "", hasAnsi: false };
  // Quick reject: no escape char
  if (input.indexOf("\x1b") === -1) return { html: "", hasAnsi: false };

  let out = "";
  let openSpans = 0;
  let cur = { fg: null, bg: null, bold: false, underline: false, dim: false };
  let hasAnsi = false;

  const closeAll = () => {
    while (openSpans > 0) { out += "</span>"; openSpans--; }
  };
  const openCurrent = () => {
    const cls = [];
    if (cur.fg) cls.push(cur.fg);
    if (cur.bg) cls.push(cur.bg);
    if (cur.bold) cls.push("ansi-bold");
    if (cur.underline) cls.push("ansi-underline");
    if (cur.dim) cls.push("ansi-dim");
    if (cls.length === 0) return;
    out += `<span class="${cls.join(" ")}">`;
    openSpans++;
  };

  // Match: ESC[..m for SGR; or ESC[..<other-letter> to strip
  const re = /\x1b\[([0-9;]*)([A-Za-z])/g;
  let last = 0;
  let m;
  while ((m = re.exec(input)) !== null) {
    // Append plain text before this escape
    out += escapeHtml(input.slice(last, m.index));
    last = re.lastIndex;
    hasAnsi = true;
    const params = m[1];
    const final = m[2];
    if (final !== "m") continue; // strip non-SGR sequences

    closeAll();
    const codes = params.length === 0 ? [0] : params.split(";").map(Number);
    for (let i = 0; i < codes.length; i++) {
      const c = codes[i];
      if (c === 0) {
        cur = { fg: null, bg: null, bold: false, underline: false, dim: false };
      } else if (c === 1) cur.bold = true;
      else if (c === 2) cur.dim = true;
      else if (c === 4) cur.underline = true;
      else if (c === 22) { cur.bold = false; cur.dim = false; }
      else if (c === 24) cur.underline = false;
      else if (c === 39) cur.fg = null;
      else if (c === 49) cur.bg = null;
      else if (ANSI_BASE_FG[c]) cur.fg = ANSI_BASE_FG[c];
      else if (ANSI_BASE_BG[c]) cur.bg = ANSI_BASE_BG[c];
      else if (c === 38 && codes[i + 1] === 5 && codes[i + 2] != null) {
        // 256-color FG: ESC[38;5;Nm
        cur.fg = `ansi-256-fg-${codes[i + 2]}`;
        i += 2;
      } else if (c === 48 && codes[i + 1] === 5 && codes[i + 2] != null) {
        cur.bg = `ansi-256-bg-${codes[i + 2]}`;
        i += 2;
      }
      // 38;2;R;G;B and 48;2;R;G;B (true color) — fall back to inline style
      else if (c === 38 && codes[i + 1] === 2 && codes[i + 4] != null) {
        cur.fg = `style:color:rgb(${codes[i+2]},${codes[i+3]},${codes[i+4]})`;
        i += 4;
      } else if (c === 48 && codes[i + 1] === 2 && codes[i + 4] != null) {
        cur.bg = `style:bg:rgb(${codes[i+2]},${codes[i+3]},${codes[i+4]})`;
        i += 4;
      }
    }
    openCurrent();
  }
  // Trailing tail
  out += escapeHtml(input.slice(last));
  closeAll();
  return { html: out, hasAnsi };
}

/* v21 — compact integer formatter (1234 → 1.2k, 1234567 → 1.2M) */
function formatCount(n) {
  if (n == null || isNaN(n)) return "0";
  n = Math.abs(Number(n));
  if (n < 1000) return String(Math.round(n));
  if (n < 1_000_000) return (n / 1000).toFixed(n >= 9999 ? 0 : 1).replace(/\.0$/, "") + "k";
  return (n / 1_000_000).toFixed(n >= 9_999_999 ? 0 : 1).replace(/\.0$/, "") + "M";
}
