"""Demo: 3-phase collaborative pipeline.

  1. Gemini designs the formal spec.
  2. Claude implements based on Gemini's design.
  3. The orchestrator (this script, called from a Claude Code session)
     verifies, runs tests, and writes a final consolidated artefact.

Each step opens in a separate visible PowerShell window via
``run_visible.py``. The orchestrator polls the output file for a
sentinel line written by ``run_visible.py`` to know when the step is
done.

Usage::

    python scripts/demo_pipeline.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN_VISIBLE = ROOT / "scripts" / "run_visible.py"
SENTINEL = "__CG_DONE__"
PIPELINE_DIR = ROOT / "outputs" / "demo-pipeline"


def wait_for_done(output_file: Path, timeout: int = 300) -> int:
    """Poll output_file every second until SENTINEL appears, or timeout."""
    start = time.time()
    while time.time() - start < timeout:
        if output_file.exists():
            text = output_file.read_text(encoding="utf-8", errors="replace")
            for line in text.splitlines()[-3:]:
                if line.startswith(SENTINEL):
                    # parse "__CG_DONE__ exit=0"
                    try:
                        return int(line.split("=", 1)[1])
                    except (IndexError, ValueError):
                        return 0
        time.sleep(1)
    print(f"[pipeline] timeout waiting for {output_file}", file=sys.stderr)
    return 124


def strip_sentinel(output_file: Path) -> str:
    """Return the contents of *output_file* without the sentinel line."""
    text = output_file.read_text(encoding="utf-8", errors="replace")
    return "\n".join(
        line for line in text.splitlines()
        if not line.startswith(SENTINEL)
    ).strip()


def launch_visible(agent: str, prompt_file: Path, output_file: Path) -> None:
    subprocess.run(
        [sys.executable, str(RUN_VISIBLE), agent, str(prompt_file), str(output_file)],
        check=True,
    )


def main() -> int:
    if PIPELINE_DIR.exists():
        shutil.rmtree(PIPELINE_DIR)
    PIPELINE_DIR.mkdir(parents=True)

    # ------------------------------------------------------------------
    # Phase 1 — Gemini: design phase
    # ------------------------------------------------------------------
    print("\n=== Phase 1: Gemini designs the spec ===")
    design_prompt = (PIPELINE_DIR / "01-design-prompt.txt")
    design_prompt.write_text(
        """DO NOT ask questions. DO NOT propose a plan. Just write the spec.

Write a precise specification for a Python function that validates a Czech IČO
(8-digit business identifier with modulo-11 checksum).

Background reminder of the algorithm:
  - IČO is exactly 8 digits, may have leading zeros
  - The 8th digit is a checksum
  - Compute c = sum_{i=0..6}(digit[i] * weight[i]) where weights are [8,7,6,5,4,3,2]
  - r = c mod 11
  - if r == 0: checksum digit must be 1
  - if r == 1: checksum digit must be 0
  - else:      checksum digit must be 11 - r

Output a Markdown document with these sections, in this order:

  ## Function signature
  Single Python signature line, e.g. `def validate_ico(s: str) -> bool:`

  ## Inputs
  Describe what the function accepts (string, length, allowed chars).

  ## Outputs
  Describe the return value and what True/False mean.

  ## Edge cases (must be enumerated)
  - empty string
  - whitespace
  - non-digit characters
  - wrong length
  - leading zeros (must be allowed)

  ## Algorithm steps
  Numbered list of exactly the steps to compute the checksum.

  ## Three concrete test cases
  Two valid IČOs and one invalid one with one-line reasons.

Output ONLY this Markdown. No greeting, no closing remarks.
""",
        encoding="utf-8",
    )
    design_out = PIPELINE_DIR / "01-design.md"
    launch_visible("gemini", design_prompt, design_out)
    rc = wait_for_done(design_out)
    print(f"[pipeline] phase 1 finished (exit={rc})")
    design = strip_sentinel(design_out)
    if not design.strip():
        print("[pipeline] phase 1 empty output, aborting", file=sys.stderr)
        return 1
    print(f"[pipeline] design captured ({len(design)} chars)")

    # ------------------------------------------------------------------
    # Phase 2 — Claude: implementation phase, given the design
    # ------------------------------------------------------------------
    print("\n=== Phase 2: Claude implements following the design ===")
    impl_prompt = (PIPELINE_DIR / "02-impl-prompt.txt")
    impl_prompt.write_text(
        f"""You are implementing a function whose specification was just written
by a teammate. Your job is to produce a runnable Python module that
satisfies the spec exactly.

# Spec from teammate

{design}

# Your output

Output ONLY a single fenced ```python code block containing:
  - the function definition
  - any helper imports it needs (stdlib only)
  - NO test cases, NO main block, NO prose

Match the function signature in the spec. Implement every edge case
listed in the spec — empty string, whitespace, non-digit characters,
wrong length must all return False without raising.
""",
        encoding="utf-8",
    )
    impl_out = PIPELINE_DIR / "02-implementation.md"
    launch_visible("claude", impl_prompt, impl_out)
    rc = wait_for_done(impl_out)
    print(f"[pipeline] phase 2 finished (exit={rc})")
    impl = strip_sentinel(impl_out)
    print(f"[pipeline] implementation captured ({len(impl)} chars)")

    # ------------------------------------------------------------------
    # Phase 3 — orchestrator: synthesize, verify, write final artefact
    # ------------------------------------------------------------------
    print("\n=== Phase 3: Orchestrator verifies and writes final artefact ===")
    final_path = PIPELINE_DIR / "03-final.md"
    final_path.write_text(
        "# Pipeline result\n\n"
        f"## Phase 1 — Gemini design ({len(design)} chars)\n\n"
        f"{design}\n\n"
        f"## Phase 2 — Claude implementation ({len(impl)} chars)\n\n"
        f"{impl}\n\n"
        "## Phase 3 — Orchestrator handoff\n\n"
        "The orchestrator (your Claude Code session) now:\n"
        "  - extracts the python code block from phase 2\n"
        "  - writes it to `validate_ico.py`\n"
        "  - runs the spec's test cases against it\n"
        "  - reports pass/fail to the human\n",
        encoding="utf-8",
    )

    print(f"\n[pipeline] DONE. Artefacts in {PIPELINE_DIR}")
    print(f"  - {design_out.name}")
    print(f"  - {impl_out.name}")
    print(f"  - {final_path.name}")
    print()
    print("Next: orchestrator extracts code from phase 2 and runs the test cases.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
