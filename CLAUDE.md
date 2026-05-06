# CLAUDE.md — Onboarding pro novou Claude Code session

> **🚀 START HERE — pokud jsi nová Claude Code session v `D:\CG`, čti tohle PRVNÍ.**

## Kde jsi a co je CG

`D:\CG\` = **CG dashboard** — multi-agent automation platforma postavená přes 13 commitů během 2 dnů (2026-05-05 a 2026-05-06). User se jmenuje **Hustler**, mluví česky, projekt vyvíjíme my dva spolu.

GitHub: https://github.com/hustlerv369/CG

## ⚠️ Než cokoli uděláš, přečti tohle pořadí:

```
1. C:\Users\Hustler\.claude\projects\D--CG\memory\RESUME-FROM-NEW-SESSION.md
2. C:\Users\Hustler\.claude\projects\D--CG\memory\MEMORY.md
3. Latest session note: 2026-05-06-v11-subworkflows-auth-wizard.md
```

`RESUME-FROM-NEW-SESSION.md` je AUTORITATIVNÍ handoff — má kompletní stav projektu + přesné implementační plány pro K3, K4, K5 (zbývající fáze).

## Co jsme dělali a kde jsme skončili

Předchozí session (token limit) skončila na **commit `df3431b` — v11**. Hotové K1+K2:
- ✅ K1: Sub-workflows (`subworkflow` agent type, `{{parent.child}}` bindings)
- ✅ K2: Browser auth wizard (5 endpointů `/api/browser-auth/*`)

Zbývající (popsané v RESUME doc):
- ⏳ **K3**: Streaming JSON tokens (claude/gemini `--output-format stream-json`) — 1.5h
- ⏳ **K4**: UI builder pro browser steps (drag-drop místo JSON psaní) — 2h
- ⏳ **K5**: Workspace tabs (CMUX-style multi-draft Orchestrator) — 2h

## Co user pravděpodobně chce, když napíše "pokračuj"

Pokračovat v K3 → K4 → K5 podle RESUME doc. Konkrétně:

1. **Read** `C:\Users\Hustler\.claude\projects\D--CG\memory\RESUME-FROM-NEW-SESSION.md`
2. **Implement** K3 (streaming JSON tokens) — backend parsuje claude/gemini stream-json output, emituje tokens jako SSE events
3. **Test** — pytest tests/, očekávej 113+ passing
4. **Commit** s patternem `feat(dashboard): v12 — <feature>`
5. **Push** → github.com/hustlerv369/CG
6. **Update** Megamind (`~/.claude/projects/D--CG/memory/2026-MM-DD-vN-<slug>.md`) + Pinecone (`seokrates-context / cg`)
7. **Brief** — Google Doc + Calendar event 6:30 ráno
8. Pokračuj K4, K5 stejným patternem

## Kritické konvence projektu

- **Commit message:** `feat(dashboard): vN — <short summary>` + detailní body s důvody, implementací, testy
- **Memory file naming:** `2026-MM-DD-vN-<slug>.md` v `~/.claude/projects/D--CG/memory/`
- **Tests:** `python -m pytest tests/` — musí projít všechno (intermittent flake na `test_workflow_save_load_delete_cycle` je known, druhý run projde)
- **Test fixture pattern:** `client` v `tests/test_dashboard.py` snapshots+restores `AGENT_KINDS` aby custom-agent testy nesvinily ostatní
- **Mocked playwright:** všechny browser tests mockují `playwright.sync_api`, ne real browser
- **Memory tripleton:** GitHub + Megamind + Pinecone — vždy update všechny 3 po každém commitu
- **Calendar event:** vždy 6:30 Prague, color 10 (Basil zelená), 2 popup reminders (0 + 5 min)
- **Briefing v češtině** s pár anglickými technickými termíny (jak user píše)

## Quick start příkazy

```bash
# Z D:\CG dir:
python -m pytest tests/ -q       # 113 passing currently
python src/cg.py dashboard       # spustí na http://127.0.0.1:8765
git log --oneline -5             # vidět co jsme committed nedávno
git status -sb                   # uncommitted změny
```

## Stack po commitu df3431b

8 built-in agent kinds:
1. claude-sonnet-4-6, claude-opus-4-7, claude-opus-4-6 (Pro subscription)
2. gemini-flash, gemini-pro, gemini-3-pro (Google subscription)
3. browser (Playwright, 16 actions)
4. subworkflow (recursive workflow composition)

+ Opt-in HTTP providers (OpenRouter, Z.ai GLM, Anthropic API, Gemini API)
+ Custom HTTP agents přes API
+ 15 bundled presetů
+ 40+ REST endpointů
+ 4-tab UI (Orchestrator / Editor / Notes / Settings)
+ Phone Dispatch loop (Cloudflare Tunnel + iOS Shortcuts + ntfy push)
+ ToS-compliant subscription invocation

## Důležité nedělej

- ❌ Nezačínej znovu od začátku — všechno už existuje, jen pokračuj
- ❌ Neměň test fixture pattern — pečlivě řeší AGENT_KINDS state pollution
- ❌ Nezahazuj commits — vždy `git pull` first, pak commit
- ❌ Nepoužívej `cd D:\CG` v Bash toolu — workdir tam už je
- ❌ Nepokoušej se znovu opravit CLAUDEGRAVITY (starý projekt, archived). CG je nástupce.

## Memory souborů struktura

```
~/.claude/projects/D--CG/memory/
├─ MEMORY.md                                 ← index všech session notes
├─ 🚀 RESUME-FROM-NEW-SESSION.md             ← TENTO první
├─ 2026-05-05-genesis.md                     ← jak CG vznikl (po CLAUDEGRAVITY failu)
├─ 2026-05-05-dashboard.md                   ← v1
├─ 2026-05-05-final-state.md                 ← v2
├─ 2026-05-06-v3-model-selector.md
├─ 2026-05-06-v4-context-placeholders.md
├─ 2026-05-06-v5-multiprovider-editor.md
├─ 2026-05-06-v6-notes-settings.md
├─ 2026-05-06-v7-n8n-automation.md
├─ 2026-05-06-v8-playwright-web.md
├─ 2026-05-06-v9-browser-agent.md
├─ 2026-05-06-v10-tunnel-phone-notifications.md
└─ 2026-05-06-v11-subworkflows-auth-wizard.md   ← latest
```

Pinecone vector index: `seokrates-context`, namespace `cg`, query přes `mcp__pinecone__search-records`.

---

**Když user napíše "pokračuj" nebo "navaž odsud" — toto je tvůj checklist:**

- [ ] Read `C:\Users\Hustler\.claude\projects\D--CG\memory\RESUME-FROM-NEW-SESSION.md`
- [ ] Read `C:\Users\Hustler\.claude\projects\D--CG\memory\2026-05-06-v11-subworkflows-auth-wizard.md` (latest)
- [ ] Implement K3 (streaming JSON tokens) podle plánu v RESUME doc
- [ ] Test, commit, push, memory update, briefing
- [ ] Pokračuj K4, K5

Hodně štěstí! Užij si pokračování. 💚
