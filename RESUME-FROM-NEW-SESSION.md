# 🚀 RESUME FROM NEW SESSION — pokračuj odsud

> **In-repo handoff dokument.** Phone-dispatch i Claude Code session ho vidí. Vždy aktualizovaný před každým push.

---

## Stav projektu (k commitu `ba9c5c8`, 5-agent pipeline live-verified)

- **38 commitů** na https://github.com/hustlerv369/CG (origin master synced)
- **167 / 167 testů** passing
- ✅ Skutečný multi-agent collaboration prokázaný end-to-end (5 agentů, 4 dependency edges, 61KB total output, 6+ minut wall time)
- ✅ Gemini model resolution opravený (canonical `gemini-2.5-pro` / `gemini-2.5-flash` místo shorthand routovaných na vadný `gemini-3.1-pro-preview`)
- ✅ Streaming default ON pro nové claude/gemini rows
- ✅ Artifact-style preview tab (sandboxed iframe pro HTML/SVG/JSX, img pro data:URLs)
- ✅ Open Design export — `POST /api/runs/<id>/export-to-open-design` + "🎨 Open in OD" button
- ✅ ROADMAP.md s návrhy (CMUX/wmux multi-terminal, pilot vision, drag-to-connect, …)
- **10 built-in agent kinds + opt-in HTTP providers + custom HTTP agents**
- **18 bundled presetů** (vč. "Design → Implement → Critique (uses ${TASK} variable)" + Sonnet default critique)
- **Live-tested pipeline** — `examples/slugify.py` + `tests/test_slugify.py` (20 cases) prokazují že Sonnet critique našel reálný bug v Opus implementaci a fix funguje
- **Dual UI:** 📋 Classic ↔ 🌐 Visual canvas
- **Phone Dispatch** funguje přes Cloudflare Tunnel + `POST /api/phone-dispatch`

## Co je hotové

### Předchozí sprint (K1–K5, prior sessions)

| Tag | Commit | Feature |
|---|---|---|
| v9 | `f9bedd7` | `browser` agent (Playwright, 16 actions, JSON-defined steps) |
| v10 | `73b40d3` | Cloudflare Tunnel + Phone Dispatch + ntfy/Discord/Slack webhooks |
| v11 | `df3431b` | Sub-workflows (recursive composition) + Browser Auth Wizard |
| v12 | `befc96a` | K3 — Token-by-token streaming (claude/gemini stream-json) |
| v13 | `be7b2fb` | K4 — Browser step builder UI (drag-free visual editor) |
| v14 | `e7ef570` | K5 — Workspace tabs (CMUX-style parallel drafts, localStorage) |

### Aktuální sprint (v15–v17, 2026-05-07)

| Tag | Commit | Feature |
|---|---|---|
| v15 | `ba93b1a` | Cheap models — DeepSeek R1, Kimi K2, Llama 3.3, Mistral, OpenCode CLI, direct DeepSeek/Moonshot APIs |
| v16 | `14f3827` | **Visual workflow canvas** — n8n/make-style toggle Classic↔Visual, drag-edit, live status overlays during runs |
| v17 | `c04f991` | **Autonomous browser pilot** — vlastní Perplexity Computer MVP (LLM-in-loop Playwright). Default: Claude Sonnet 4.6 driver. |
| docs | `5dcb16b` | README + CHANGELOG + dashboard-guide refresh |
| docs | `ef72e0a` | In-repo handoff (CLAUDE.md refresh + RESUME-FROM-NEW-SESSION.md) |
| v18 | `a0ab42a` | Clearer Design→Implement→Critique preset + ${TASK} variable variant + toast() helper |
| chore | `c1d5ff1` | gitignore tunnel binary + local config (cleanup) |
| docs | `13e9e2a` | RESUME bump |
| fix | `51814ae` | Pipeline preset critique → Claude Sonnet 4.6 (Gemini Pro 429 capacity issue) |
| test | `9cb0e99` | examples/slugify.py + tests/test_slugify.py — proves Pipeline-1 critique found a real Opus bug |
| docs | `f7c12f7` | RESUME bump |
| test | `0b18c94` | examples/retry_decorator.py + tests/test_retry_decorator.py — Pipeline-2 critique "impl is correct" verdict survived 18 adversarial tests |
| docs | `d340dc6` | RESUME bump |
| feat | `0c50493` | artifact preview + OD export + Gemini canonical model strings + streaming default |
| docs | `010ea33` | RESUME bump |
| fix | `da1f4a3` | cache-bust /static/dashboard.{js,css} via mtime stamp (browser was holding stale JS after deploys) |
| docs | `c6af8cd` | RESUME bump |
| feat | `55926a4` | full-page preview endpoint + "↗ Open full page" button + Tailscale roadmap |
| fix | `ebe7250` | Windows-CLI emoji mojibake recovery via ftfy (🧠 was arriving as đź§) |
| docs | `28d98f4` | RESUME bump |
| fix | `90e447c` | Gemini CLI: pass prompt via stdin not argv (`-p ""` placeholder + stdin) |
| demo | `ba9c5c8` | 5-agent pipeline (strategy → visual → impl → critique → polish) on HustlerV — Gemini fix verified live |

## Co NENÍ hotové (žádný okamžitý todo)

Sprint je čistý — **žádný explicit todo nezbývá**. Pokud user napíše "pokračuj":
- Zeptej se na konkrétní task **NEBO**
- Nabídni návrhy z "Co dál" sekce dole

## Workflow pro každou změnu

```bash
# 1. Implement změny v src/
# 2. Test
python -m pytest tests/ -q          # MUSÍ projít všech 126

# 3. JS syntax check (pokud frontend)
node -e "const c=require('fs').readFileSync('src/dashboard_static/dashboard.js','utf8'); new Function(c)"

# 4. Commit + push
git add -A
git commit -m "feat(dashboard): vN — <summary>"  # multi-line body přes HEREDOC
git push origin master

# 5. Aktualizuj v repu (DŮLEŽITÉ pro dispatch):
#    - CHANGELOG.md     (nová entry navrch)
#    - README.md        (Status list)
#    - RESUME-FROM-NEW-SESSION.md (tento soubor — bump commit hash + tabulka)

# 6. Pokud máš lokální Claude Code session, navíc:
#    - Megamind file:  ~/.claude/projects/D--CG/memory/2026-MM-DD-vN-<slug>.md
#    - MEMORY.md index update
#    - Pinecone upsert: seokrates-context / cg namespace
#    - Calendar event 6:30 Prague + Drive briefing (na konci sessions)
```

## Quick start

```bash
cd D:\CG
python -m pytest tests/ -q       # 126 passing
python src/cg.py dashboard       # http://127.0.0.1:8765
git log --oneline -10            # nedávné commity
git status -sb                   # uncommitted změny
```

## Stack snapshot

**Built-in agents:**
- `claude-sonnet-4-6`, `claude-opus-4-7`, `claude-opus-4-6` (Pro)
- `gemini-flash`, `gemini-pro`, `gemini-3-pro` (Google)
- `browser` (Playwright, JSON-defined steps)
- `browser-pilot` (autonomous LLM-in-loop, v17)
- `subworkflow` (recursive composition)
- `opencode` (sst/opencode CLI, BYO provider config)

**Opt-in HTTP providers (per env var):**
- `OPENROUTER_API_KEY` → GLM-4.7, DeepSeek V3/R1, Qwen3 Coder, Kimi K2, Llama 3.3, Mistral Large
- `ZHIPU_API_KEY` / `ZAI_API_KEY` → GLM-4.7 / Flash / FlashX
- `DEEPSEEK_API_KEY` → deepseek-chat, deepseek-reasoner
- `MOONSHOT_API_KEY` → kimi-k2-direct
- `ANTHROPIC_API_KEY` → claude-api-sonnet (paid, separate from Pro)
- `GEMINI_API_KEY` / `GOOGLE_API_KEY` → gemini-api-pro

**UI features:**
- 4 taby (Orchestrator / Editor / Notes / Settings)
- View toggle: Classic (linear rows) ↔ Visual (n8n canvas)
- Workspace tabs (parallel drafts, per-browser localStorage)
- Token-by-token streaming opt-in checkbox per agent
- Browser step builder (visual JSON editor) when agent = `browser`
- 17 presetů včetně Browser Pilot examples

## Sanity checklist (po čerstvém clone / dispatch wakeup)

```bash
git pull origin master
python -m pytest tests/ -q              # → 126 passed
python -c "import sys; sys.path.insert(0, 'src'); import dashboard"  # → no error
ls outputs/screenshots/ | head          # → kde se ukládají v17 pilot screenshoty
```

Pokud `pytest` nezelená:
- `git log --oneline -3` — opravdu jsi na `5dcb16b` nebo novějším?
- Test `test_workflow_save_load_delete_cycle` může být občas flaky (defenzivní fix v `_list_workflow_files` aplikován v v16, ale jistota nikdy není 100%) — druhý run vyřeší.

## Co dál (návrhy, nic z toho není zadané)

Pokud user řekne "pokračuj" bez specifikace, můžeš nabídnout:

1. **Vision pro Browser Pilot** — současný v17 pilot vidí jen text + element list, ne obrázek. Claude Sonnet 4.6 vision (přes screenshot upload v Anthropic API) nebo Gemini Pro vision by dramaticky zlepšil rozhodování. Vyžaduje runtime přepnutí na HTTP runner s multimodal payloadem.
2. **Drag-to-connect ve Visual canvas** — aktuálně lze klikem smazat connection, ale ne nakreslit novou. Implementace: pointer-down na pravý okraj nodu → drag → pointer-up na levý okraj target → vytvoří depends_on.
3. **Workflow templates marketplace** — sdílení JSON workflow přes GitHub gist nebo embed-in-dashboard browser tab.
4. **Pilot recall / skill caching** — po dokončeném `done` action uložit sekvenci akcí jako "skill" a nabídnout ji při podobných goal patternech (vector search přes Pinecone nad goal embedding).
5. **Multi-pilot voter** — 3 pilots paralelně na stejný goal s různými strategiemi, voter agent vybere best answer.
6. **Pan/zoom v Visual canvas** — aktuálně canvas scrolluje, ale chybí pinch-zoom + drag-pan.
7. **Webhook → workflow trigger UI** — endpoint `/api/triggers/<workflow>` existuje (v7), ale UI pro generování bezpečných tokenů + curl examples chybí.

## Důležité nedělej

- ❌ Nezačínej znovu — všechno už existuje (K1-K5, v15-v17 hotové)
- ❌ Neměň test fixture pattern v `tests/test_dashboard.py`
- ❌ Nezahazuj commits — vždy `git pull` před commitem
- ❌ Nepoužívej `cd D:\CG` v Bash (workdir tam už je)
- ❌ Nepokoušej se opravit CLAUDEGRAVITY (archived)
- ❌ NEPŘEDPOKLÁDEJ že K3-K5 / v15-v17 jsou todo — jsou hotové, viz tabulky výše

## Notes pro phone-dispatch session specificky

Pokud čteš tohle z phone-dispatch (přes Cloudflare Tunnel `POST /api/phone-dispatch`):

- Nemáš přístup k Megamind ani Pinecone — vystačíš si s tímto souborem
- Workdir je `D:\CG`
- Můžeš spouštět workflows přes `POST /api/phone-dispatch` s body `{workflow: "<name>"}` (viz `workflows/`)
- Pro stav nedávných runs: `GET /api/runs?limit=10`
- Live SSE feed: `GET /api/runs/<id>/stream`

---

**Aktualizováno:** 2026-05-07 (po commitu `ba9c5c8` — 5-agent pipeline ověřen live, multi-agent automation hotová)
**Maintainer:** ten Claude Code session co právě commituje. Vždy bumpni datum + commit hash při každém pushi.
