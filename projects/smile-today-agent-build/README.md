# Smile Today — agent build

This directory holds the **end-to-end agent-generated** version of Smile
Today, deployed live at **<https://claudegravity.online>**.

Companion to `projects/smile-today/` (the hand-written first cut). Both
share the design tokens; this one's HTML/CSS/JS came directly from the
ClaudeGravity agent run.

## How it was built

Two CG runs on the live dashboard at <https://claudegravity.space>:

| Run | Id | Agents | Result |
|---|---|---|---|
| Main 4-agent | `8ef99652aa54` | Architect (Opus) → Designer (Gemini Pro) → Engineer (Opus) → Operator (Gemini Flash) | 3/4 completed. Engineer killed at 90 s by v51 watchdog (Opus first-token slow that hour) but `continue_on_dep_failure: true` let Operator still run with a placeholder. **The "all four go through" promise was kept even when one agent failed.** |
| Engineer retry | `1b67599388b6` | Engineer-only (Opus, `first_token_timeout: 300`) | Visible content arrived at ~3 min, completed with 24 606 chars in < 5 s once it started. All 7 files parsed cleanly via `extract-and-deploy.py`. |

`run-{architect,designer,operator}.md` are the verbatim outputs of the
main 4-agent run (signed by their respective models). `run-engineer.md`
is the retry's output. They're committed alongside the source so the
provenance is auditable.

## What's deployed

| File | Size | Source |
|---|---|---|
| `index.html` | 3.0 KB | engineer (Opus, retry) |
| `style.css` | 7.4 KB | engineer (Opus, retry) |
| `script.js` | 11 KB | engineer (Opus, retry) |
| `sw.js` | 1.8 KB | engineer (Opus, retry) |
| `logo.svg` | 557 B | engineer (verbatim from designer's output) |
| `manifest.json` | 450 B | engineer (Opus, retry) |
| `robots.txt` | 23 B | engineer (Opus, retry) |

## Re-running

```bash
# Main 4-agent run
cd D:\CG
curl -sS -u "$CG_AUTH_USER:$CG_AUTH_PW" -X POST \
  https://claudegravity.space/api/runs \
  -H 'Content-Type: application/json' \
  -d @.smile-today.spec.json

# If engineer stalls, retry just the engineer with a longer first-token
# timeout, using the inline-context spec:
curl -sS -u "$CG_AUTH_USER:$CG_AUTH_PW" -X POST \
  https://claudegravity.space/api/runs \
  -H 'Content-Type: application/json' \
  -d @.smile-engineer-only.spec.json

# Then extract + deploy:
python projects/smile-today/extract-and-deploy.py <run_id>
```

## License

MIT
