# CG roadmap — co dál

> Living document. Každá implementovaná položka přejde do CHANGELOG / RESUME.
> User přidává nové ad-hoc požadavky; Claude tady aktualizuje stav per session.

---

## Hot (právě řešíme)

### Vizuální vidět-že-se-něco-děje (in progress)
- ✅ K3 streaming hotový od `befc96a` (per-step opt-in stream-json)
- ✅ Default streaming ON pro nové claude/gemini rows (commit po `0b18c94`)
- ⏳ **TODO**: live "current LLM token" indikátor v monitor headeru — místo "running"
  ukázat třeba kolika znaků LLM napsal + spinner pulsing.
- ⏳ **TODO**: progress bar či dots animace ve `vis-node.status-running` ve Visual canvas
  (aktuálně jen pulse glow — chce explicit "živě generuji" feeling).

### Artifact preview (právě hotové)
- ✅ Nový `🎨 preview` segment v monitor toolbaru
- ✅ Sandboxed iframe pro HTML / SVG / JSX (Babel-standalone), `<img>` pro
  data:image / image-URL fallback
- ⏳ **TODO**: per-fence-block carousel (když output má víc fenced HTML/SVG/JSX,
  šipky ⟨ ⟩ pro přepínání mezi nimi)
- ⏳ **TODO**: copy-to-Editor button — vezme detected HTML/JSX a hodí ho do
  Editor tabu jako nový soubor
- ⏳ **TODO**: viewport-frame picker (mobile / tablet / desktop / browser-chrome)
  — inspired by Open Design's device frames

### Gemini model fix (právě hotové)
- ✅ AGENT_KINDS naopravěné na canonical model strings:
  `gemini-2.5-flash`, `gemini-2.5-pro` (ne shorthand "flash"/"pro" co se
  routovalo na `gemini-3.1-pro-preview` s 429 capacity issues)
- ✅ Smazaná `gemini-3-pro` entry (model name neexistuje v gemini-cli)
- ⏳ **TODO**: detekce `gemini` CLI version + warning pokud user má
  starou verzi co model strings nepřijímá
- ⏳ **TODO**: fallback chain — když gemini-2.5-pro vrátí 429, auto-retry
  s gemini-2.5-flash (graceful degradation místo full fail)

### Open Design integration (právě hotové, surface level)
- ✅ `POST /api/runs/<id>/export-to-open-design` — drops run report do
  `D:\CLAUDE\OPEN DESIGN\open-design\imports\cg-<id>-<title>.md`
- ✅ "🎨 Open in OD" button na monitor toolbaru
- ⏳ **TODO**: detekovat běžící OD daemon (port 7457) a zavolat skutečné
  import API místo file-drop (lepší UX, projekt se otevře přímo)
- ⏳ **TODO**: bidirectional — přidat OD's "Send to CG" button do OD launcher
  workflow tak, aby user mohl design v OD a pak ho z dispatch v CG

---

## Big rocks (návrhy s odhadem rozsahu)

### 1. CMUX/wmux-style multi-terminal spawning
**Inspirace:** [openwong2kim/wmux](https://github.com/openwong2kim/wmux),
ten že lze spustit klidně 50 separátních terminálů s agenty.

**Aktuální stav:** `src/cluster.py` umí spawnout N agent windows (Windows
Terminal tabs nebo `start cmd`), ale není napojen na dashboard.

**Plán implementace (~4h):**
1. Frontend: Visual mode → "Run as cluster" button vedle "▶ Run" → 
   spawne N OS terminálů, každý s jedním agent's CLI invocation.
2. Backend: nový endpoint `POST /api/runs/<id>/cluster-launch` — pro 
   každý agent v spec spustí Windows Terminal `wt -w 0 nt` s patřičným
   `claude --print` / `gemini -p` příkazem. Run se neexecutuje uvnitř
   FastAPI procesu, ale orchestruje OS-level.
3. Per-agent terminál streamuje stdout zpět do CG dashboardu přes pipe
   nebo named pipe (Windows) / socket (Linux).
4. Bonus: `tmux` adapter pro Linux/macOS — když `tmux` k dispozici,
   použít jeden window s N panes místo N samostatných terminálů.

**Use case:** 8 paralelních pilots na různá zadání, vidíš všech 8
v separate windows, můžeš každý zastavit nezávisle, žádný single-process
bottleneck.

### 2. Pilot vision
- Browser pilot teď vidí jen text + element list, ne obrázek.
- Plán: Claude Sonnet 4.6 vision přes Anthropic API multimodal payload
  (potřebuje `ANTHROPIC_API_KEY`) NEBO Gemini Pro vision přes gemini-cli
  (preview, capacity questionable).
- Implementace: `_pilot_ask_llm` + screenshot upload (base64 inline).
- Estimate: 2h.

### 3. Pilot skill caching
- Po dokončeném `done` action uložit sekvenci akcí jako "skill" 
  do Pinecone (vector embedding nad goal text).
- Při novém pilot run nejdřív vector search — pokud existuje similar
  skill, nabídnout ji jako baseline ("found 87% similar past run, use it
  as starting trace?").
- Estimate: 3h (Pinecone integration + skill lifecycle).

### 4. Drag-to-connect ve Visual canvas
- Aktuálně klik na connection smaže ji, ale nelze nakreslit novou.
- Implementace: pointer-down na pravý okraj nodu (output port) → drag →
  pointer-up na levý okraj target (input port) → vytvoří `depends_on`.
- Visual feedback: ghost line during drag.
- Estimate: 2h.

### 5. Pan/zoom ve Visual canvas
- SVG canvas teď scrolluje, ale chybí pinch-zoom + drag-pan.
- Použít d3-zoom nebo custom transform matrix.
- Estimate: 1.5h.

### 6. Workflow templates marketplace
- Sdílení JSON workflows přes GitHub gist nebo embed-in-dashboard browse.
- "Import from gist" + "Share to gist" buttons.
- Estimate: 2h.

### 7. Multi-pilot voter
- 3 pilots paralelně se stejným cílem ale různými strategy prompty 
  (greedy / cautious / explorer), voter agent vybere best answer.
- Estimate: 3h.

### 8. Pilot trigger UI
- Endpoint `/api/triggers/<workflow>` existuje (v7), ale UI pro generování
  secure tokenů + curl examples chybí.
- Estimate: 1h.

---

## Backlog (low-priority, nice-to-have)

- **Streaming-aware diff view** — diff mode aktualizuje v reálném čase jak
  oba agenti generují tokens
- **Agent-specific keyboard shortcuts** — Ctrl+1..9 selectne tab, Ctrl+R run, Ctrl+E export
- **Run replay** — krok-za-krokem přehrání minulého runu (jako video timeline)
- **Cost estimator** — když user vybere HTTP provider, ukázat $/M tokens × estimated tokens před Run
- **GitHub Actions integration** — `cg run` z `.github/workflows/`
- **Kubernetes deploy** — Helm chart pro self-hosted dashboard
- **Mobile-first dashboard skin** — current UI je desktop-first, mobile frnu lze improve
- **Import from Claude Design ZIP** — Open Design má `POST /api/import/claude-design`,
  obdobně přidat do CG abychom mohli pokračovat editaci Claude Design exportu

---

**Aktualizováno:** 2026-05-07 (po commitu zatím čeká na commit)
**Maintainer:** Claude Code session během práce.
