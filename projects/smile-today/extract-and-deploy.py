"""Extract files from a CG agent run + deploy to /var/www/smile-today/.

Reads outputs/dashboard-runs/<run_id>/engineer.out.md and operator.out.md,
parses fenced code blocks with file-path first-line comments, writes the
files to a temp dir, then rsync to the VPS.

Usage:
    python extract-and-deploy.py <run_id>

The fenced-block format the engineer agent was instructed to emit:

    <!-- index.html -->
    ```html
    <!DOCTYPE html>...
    ```

    /* style.css */
    ```css
    :root { --bg: #fff; ...
    ```

    // script.js
    ```javascript
    (() => { 'use strict'; ...
    ```

We only care about the path + body; the language hint is ignored.
"""

from __future__ import annotations

import re
import sys
import shutil
import subprocess
from pathlib import Path

# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

# A path-comment line looks like:
#   <!-- index.html -->
#   <!-- logo.svg -->
#   /* style.css */
#   // script.js
# Captures the file name (everything between the marker tokens, trimmed).
PATH_PATTERNS = [
    re.compile(r"^\s*<!--\s*([\w./\-]+\.\w+)\s*-->\s*$"),
    re.compile(r"^\s*/\*\s*([\w./\-]+\.\w+)\s*\*/\s*$"),
    re.compile(r"^\s*//\s*([\w./\-]+\.\w+)\s*$"),
    re.compile(r"^\s*#\s*([\w./\-]+\.\w+)\s*$"),
]

FENCE = re.compile(r"^```[\w-]*$")


def extract_blocks(markdown_text: str) -> dict[str, str]:
    """Return {file_path: content} for every fenced block preceded by a
    path-comment line.

    Robust to the common LLM output variations:
      - blank lines between the path comment and the fence
      - the path comment INSIDE the fenced block as the first line (some
        models emit it that way)
    """
    out: dict[str, str] = {}
    lines = markdown_text.splitlines()
    i = 0
    pending_path: str | None = None

    def match_path(line: str) -> str | None:
        for pat in PATH_PATTERNS:
            m = pat.match(line)
            if m:
                return m.group(1).strip()
        return None

    while i < len(lines):
        line = lines[i]
        # Path comment OUTSIDE any fence?
        if FENCE.match(line):
            # Start of a fenced block. We may not have a path yet —
            # check the very first non-empty line inside for an
            # in-fence path comment.
            j = i + 1
            block: list[str] = []
            in_fence_path = pending_path
            while j < len(lines) and not FENCE.match(lines[j]):
                if in_fence_path is None and lines[j].strip():
                    p = match_path(lines[j])
                    if p:
                        in_fence_path = p
                        j += 1
                        continue
                block.append(lines[j])
                j += 1
            if in_fence_path:
                # Some models leave a leading blank line — strip it
                while block and not block[0].strip():
                    block.pop(0)
                # … and trailing blank lines
                while block and not block[-1].strip():
                    block.pop()
                out[in_fence_path] = "\n".join(block) + "\n"
            pending_path = None
            i = j + 1
            continue
        p = match_path(line)
        if p is not None:
            pending_path = p
            i += 1
            continue
        # Non-fence, non-path line — clear pending path so a later
        # fence doesn't inherit a stale one.
        if line.strip():
            pending_path = None
        i += 1
    return out


# ---------------------------------------------------------------------------
# Deploy
# ---------------------------------------------------------------------------

REQUIRED = ["index.html", "style.css", "script.js", "logo.svg",
              "manifest.json", "sw.js"]


def main(run_id: str) -> int:
    repo_root = Path(__file__).resolve().parents[2]
    run_dir = repo_root / "outputs" / "dashboard-runs" / run_id
    if not run_dir.exists():
        print(f"error: run dir not found at {run_dir}", file=sys.stderr)
        return 1

    blocks: dict[str, str] = {}
    for src_label in ("engineer", "operator", "designer", "architect"):
        out_md = run_dir / f"{src_label}.out.md"
        if not out_md.exists():
            print(f"  [skip] {src_label}: no output (probably failed)")
            continue
        text = out_md.read_text(encoding="utf-8", errors="replace")
        new = extract_blocks(text)
        for k, v in new.items():
            # First writer wins (engineer first, then operator, etc.)
            blocks.setdefault(k, v)
        if new:
            print(f"  [{src_label}] {len(new)} files: {sorted(new)}")

    missing = [f for f in REQUIRED if f not in blocks]
    if missing:
        print(f"error: missing required files {missing}", file=sys.stderr)
        return 2

    # Write to a fresh staging dir
    stage = repo_root / "projects" / "smile-today-agent-build"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    for path, content in blocks.items():
        target = stage / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")
        print(f"  wrote {target.relative_to(repo_root)} ({len(content)} bytes)")

    # rsync to VPS
    print("\n[deploy] rsync to hukot:/var/www/smile-today/")
    rc = subprocess.run([
        "rsync", "-az", "--delete",
        f"{stage}/",
        "hukot:/var/www/smile-today/",
    ]).returncode
    if rc != 0:
        print(f"error: rsync failed with {rc}", file=sys.stderr)
        return 3

    subprocess.run(["ssh", "hukot",
                     "chown -R caddy:caddy /var/www/smile-today/"], check=False)
    subprocess.run(["ssh", "hukot",
                     "systemctl reload caddy"], check=False)
    print("[deploy] done — check https://claudegravity.online/")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: extract-and-deploy.py <run_id>", file=sys.stderr)
        sys.exit(1)
    sys.exit(main(sys.argv[1]))
