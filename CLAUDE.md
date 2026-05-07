# CLAUDE.md — Onboarding pro novou Claude Code session

> **🚀 START HERE — pokud jsi nová Claude Code (nebo phone-dispatch) session v `D:\CG`, čti tohle PRVNÍ.**

## Kde jsi a co je CG

`D:\CG\` = **CG dashboard** — multi-agent automation platforma postavená přes 22 commitů (2026-05-05 → 2026-05-07). User se jmenuje **Hustler**, mluví česky, projekt vyvíjíme my dva spolu.

GitHub: https://github.com/hustlerv369/CG

## ⚠️ Než cokoli uděláš, čti tohle pořadí (přesně v tomto):

```
1. D:\CG\RESUME-FROM-NEW-SESSION.md          ← STAV PROJEKTU (in-repo, dispatch-friendly)
2. D:\CG\CHANGELOG.md                         ← celá historie verzí v0 → v17
3. D:\CG\README.md                            ← features list + quickstart
```

Pokud máš přístup k Megamind / Pinecone (lokální Claude Code session), navíc:

```
4. C:\Users\Hustler\.claude\projects\D--CG\memory\MEMORY.md     ← session index
5. C:\Users\Hustler\.claude\projects\D--CG\memory\2026-05-07-v15-v16-v17-models-canvas-pilot.md (latest)
```

> **Phone-dispatch session:** zůstaň u kroků 1–3. Megamind/Pinecone nejsou v repu.

## Aktuální stav (k commitu `5dcb16b`, v17 + docs)

**HOTOVO:**
- ✅ K1-K5 z původního RESUME doc (sub-workflows, browser auth, streaming, step builder, workspace tabs)
- ✅ v15 cheap models (DeepSeek R1, Kimi K2, Llama 3.3, Mistral, OpenCode CLI, direct DeepSeek/Moonshot APIs)
- ✅ v16 visual workflow canvas (n8n-style toggle Classic/Visual + drag-edit + live status overlays)
- ✅ v17 autonomous browser pilot (vlastní Perplexity Computer MVP s LLM-in-loop Playwright)
- ✅ 126/126 testů passing
- ✅ 22 commitů na origin master

**NIC KRITICKÉHO NEZBÝVÁ.** RESUME doc je celý odbavený. Další iterace = nový plánovací cyklus s userem.

## Co user pravděpodobně chce, když napíše "pokračuj"

- **Možnost A** — přidává nové features. Vyžádej si specifikaci, pak implementuj v `feat(dashboard): vN` patternu.
- **Možnost B** — sanity check existujícího. Spusť dashboard, ověř že běží.
- **Možnost C** — bug fix. `git log --oneline -10` + reprodukuj + fix.

**NEPŘEDPOKLÁDEJ že "pokračuj" = K3/K4/K5/v15/v16/v17.** Ty jsou všechny hotové. Vždy ověř aktuální git stav před implementací.

## Workflow per-feature (KAŽDÁ změna)

```
1. Implement
2. python -m pytest tests/      → musí projít
3. node -e "..."                 → JS syntax check pro frontend změny
4. git add -A
5. git commit -m "feat(dashboard): vN — <summary>"  (HEREDOC pro multi-line body)
6. git push origin master        ← DŮLEŽITÉ: dispatch sleduje origin
7. Update CHANGELOG.md           ← per release
8. Update README.md status list
9. Update D:\CG\RESUME-FROM-NEW-SESSION.md  ← stav v repu pro dispatch
10. Megamind file                ← jen pokud máš přístup
11. Pinecone upsert              ← jen pokud máš MCP
12. Calendar 6:30 + Drive briefing  ← na konci sessions
```

## Kritické konvence projektu

- **Commit message:** `feat(dashboard): vN — <short summary>` + detailní body
- **Memory file naming:** `2026-MM-DD-vN-<slug>.md` v `~/.claude/projects/D--CG/memory/`
- **Tests:** `python -m pytest tests/` — 126/126 passing currently. Žádný flake by nemněl být.
- **Test fixture pattern:** `client` v `tests/test_dashboard.py` snapshots+restores `AGENT_KINDS`
- **Mocked playwright:** všechny `browser` agent tests mockují `playwright.sync_api`. v17 pilot tests mockují přes subprocess, ne playwright.
- **Memory tripleton:** GitHub + Megamind + Pinecone — vždy update všechny 3 po každém commitu (pokud máš přístup)
- **In-repo handoff:** `D:\CG\RESUME-FROM-NEW-SESSION.md` MUSÍ být aktuální pro dispatch session
- **Calendar event:** vždy 6:30 Prague, color 10 (Basil zelená), 2 popup reminders (0 + 30 min)
- **Briefing v češtině** s pár anglickými technickými termíny

## Quick start

```bash
# Z D:\CG dir (workdir je tam):
python -m pytest tests/ -q       # 126 passing
python src/cg.py dashboard       # http://127.0.0.1:8765
git log --oneline -10            # nedávné commity
git status -sb                   # uncommitted změny
```

## Stack po commitu `5dcb16b` (v17)

**10 built-in agent kinds:**
1. claude-sonnet-4-6, claude-opus-4-7, claude-opus-4-6 (Pro subscription)
2. gemini-flash, gemini-pro, gemini-3-pro (Google subscription)
3. browser (Playwright, 16 actions)
4. browser-pilot (autonomous LLM-in-loop, v17)
5. subworkflow (recursive workflow composition)
6. opencode (sst/opencode CLI, BYO provider config)

**+ Opt-in HTTP providers** (každý za env var):
- OpenRouter: GLM-4.7, DeepSeek V3/R1, Qwen3 Coder, Kimi K2, Llama 3.3, Mistral Large
- Z.ai direct: GLM-4.7 / Flash / FlashX
- DeepSeek direct: chat / reasoner
- Moonshot direct: kimi-k2-direct
- Anthropic API direct
- Google AI Studio direct

**+ Custom HTTP agents přes API** (n8n-style)
**+ 17 bundled presetů** (vč. 2 Browser Pilot presetů z v17)
**+ 40+ REST endpointů**
**+ Dual UI modes:**
  - 📋 Classic (linear agent rows)
  - 🌐 Visual (n8n-style node canvas s drag-edit a live status)
**+ 4-tab UI** (Orchestrator / Editor / Notes / Settings)
**+ Workspace tabs** (CMUX-style parallel drafts)
**+ Phone Dispatch loop** (Cloudflare Tunnel + iOS Shortcuts + ntfy push)
**+ ToS-compliant subscription invocation**

## Důležité nedělej

- ❌ Nezačínej znovu od začátku — všechno už existuje
- ❌ Neměň test fixture pattern v `tests/test_dashboard.py`
- ❌ Nezahazuj commits — vždy `git pull` first, pak commit
- ❌ Nepoužívej `cd D:\CG` v Bash (workdir tam už je)
- ❌ Nepokoušej se opravit CLAUDEGRAVITY (archived legacy)
- ❌ NEPŘEDPOKLÁDEJ že K3-K5 nebo v15-v17 jsou todo — jsou hotové

## Memory souborů struktura

```
D:\CG\                                       ← in-repo, dostupné dispatch session
├─ RESUME-FROM-NEW-SESSION.md                ← AUTORITATIVNÍ stav
├─ CLAUDE.md                                 ← TENTO soubor
├─ CHANGELOG.md                              ← v0 → v17 history
├─ README.md
└─ docs/dashboard-guide.md                   ← user tour všech features

~/.claude/projects/D--CG/memory/             ← Megamind, jen lokální session
├─ MEMORY.md                                 ← index
├─ RESUME-FROM-NEW-SESSION.md                ← starý (původní K3-K5 plán, zachováno historicky)
├─ 2026-05-06-v12-v13-v14-streaming-builder-workspaces.md
└─ 2026-05-07-v15-v16-v17-models-canvas-pilot.md  ← latest
```

Pinecone vector index: `seokrates-context`, namespace `cg`. Záznamy: cg-v12 / cg-v13 / cg-v14 / cg-v15 / cg-v16 / cg-v17 / cg-docs-* / cg-resume-doc-completed.

---

**Když user napíše "pokračuj" / "navaž odsud" — checklist:**

- [ ] Read `D:\CG\RESUME-FROM-NEW-SESSION.md`
- [ ] `git log --oneline -5` — vidět co je nejnovější
- [ ] Pokud user řekne konkrétní task → implementuj. Jinak se zeptej.
- [ ] Per-change: implement → test → commit → push → update RESUME → (Megamind/Pinecone pokud máš)
- [ ] Konec sessions: Calendar 6:30 + Drive briefing
