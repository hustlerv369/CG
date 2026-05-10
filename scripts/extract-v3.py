#!/usr/bin/env python
"""Extract v3 artifacts. v3: line-based parser handling all wrapper styles."""
import json, pathlib, re

raw = pathlib.Path('C:/Users/Hustler/AppData/Local/Temp/v3-engineer.txt').read_text(encoding='utf-8', errors='replace')
try:
    log = json.loads(raw).get('log', raw)
except Exception:
    log = raw

out_dir = pathlib.Path("D:/CG/projects/extekk-luxe-v3-agent-build")
out_dir.mkdir(parents=True, exist_ok=True)

lines = log.split("\n")
i = 0
written = {}

def detect_filename(text):
    text = text.strip()
    for pat in [
        r"<!--\s*([^\s>]+\.[a-zA-Z0-9]+)\s*-->",
        r"/\*\s*([^\s*]+\.[a-zA-Z0-9]+)\s*\*/",
        r"//\s*([^\s/]+\.[a-zA-Z0-9]+)",
        r"^#\s*([^\s]+\.[a-zA-Z0-9]+)\s*$",
    ]:
        m = re.search(pat, text)
        if m:
            return m.group(1)
    return None

# Collect fence segments
segments = []  # list of (lang, body_lines, prev_line, first_line)
i = 0
while i < len(lines):
    m = re.match(r"^```([a-zA-Z0-9_+-]*)\s*$", lines[i])
    if m:
        lang = m.group(1)
        prev_line = lines[i-1] if i > 0 else ""
        body_lines = []
        i += 1
        while i < len(lines):
            if re.match(r"^```\s*$", lines[i]):
                break
            body_lines.append(lines[i])
            i += 1
        first_line = body_lines[0] if body_lines else ""
        segments.append((lang, body_lines, prev_line, first_line))
    i += 1

# For each segment, figure out the filename
EXT_TO_LANG = {"html": "html", "css": "css", "js": "js", "json": "json", "svg": "xml", "txt": ""}

for lang, body_lines, prev_line, first_line in segments:
    name = None
    # 1) prev line (e.g. "<!-- manifest.json -->")
    name = detect_filename(prev_line)
    body_offset = 0
    if name:
        # body starts from line 0
        body_offset = 0
    else:
        # 2) first line of body
        name = detect_filename(first_line)
        if name:
            body_offset = 1

    # 3) Heuristic from lang
    if not name:
        if lang == "xml" and body_lines and "<svg" in (body_lines[0] if body_lines else ""):
            name = "logo.svg"
            body_offset = 0

    # 4) robots.txt — prev line might be empty fence-no-lang
    if not name and lang == "" and any("User-agent" in l for l in body_lines[:5]):
        name = "robots.txt"
        body_offset = 0
        # Strip "# robots.txt" first line if present
        if body_lines and "robots.txt" in body_lines[0]:
            body_offset = 1

    # 5) three-matrix.js — js fence with `import * as THREE`
    if not name and lang == "js" and any("import" in l and "THREE" in l for l in body_lines[:10]):
        name = "three-matrix.js"
        body_offset = 0
        if body_lines and detect_filename(body_lines[0]):
            body_offset = 1

    if not name:
        continue

    content_lines = body_lines[body_offset:]
    content = "\n".join(content_lines).rstrip() + "\n"
    if name in written:
        # Don't overwrite a larger file with a smaller
        if len(content) <= written[name]:
            continue
    out_path = out_dir / name
    out_path.write_text(content, encoding='utf-8')
    written[name] = len(content)

print("Engineer output size:", len(log), "chars")
print("Files extracted:")
for f, s in sorted(written.items()):
    print("  ", f, ":", s, "bytes")

# Audit trails
for label in ("architect", "designer", "engineer", "operator"):
    src = pathlib.Path("C:/Users/Hustler/AppData/Local/Temp/v3-" + label + ".txt")
    if src.exists():
        dst = out_dir / ("run-" + label + ".txt")
        dst.write_text(src.read_text(encoding='utf-8', errors='replace'), encoding='utf-8')

print("Audit trails saved.")
