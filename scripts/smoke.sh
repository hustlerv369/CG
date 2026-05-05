#!/usr/bin/env bash
# End-to-end smoke test: doctor → create task → dispatch to both → verify.
# Run from repo root: bash scripts/smoke.sh
set -euo pipefail

cd "$(dirname "$0")/.."

echo "[smoke] doctor"
python src/cg.py doctor

echo ""
echo "[smoke] add task"
TASK_ID=$(python src/cg.py task add "Smoke greet" --spec \
  "Reply with exactly one fenced python block:
\`\`\`python
def greet(n: str) -> str:
    return f'Hi, {n}!'
\`\`\`
No prose. Just the block." 2>&1 | head -1 | awk '{print $2}' | sed 's/://')

echo "[smoke] task id: $TASK_ID"

echo "[smoke] dispatch to both"
python src/cg.py run "$TASK_ID" --to both --timeout 120

echo ""
echo "[smoke] outputs:"
ls -la "outputs/$TASK_ID/"

echo ""
echo "[smoke] claude head:"
head -10 "outputs/$TASK_ID/claude.md"
echo ""
echo "[smoke] gemini head:"
head -10 "outputs/$TASK_ID/gemini.md"

echo ""
echo "[smoke] PASS"
