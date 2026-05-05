"""Run a single agent (claude or gemini) in a NEW visible PowerShell window
so the user can watch the live output. Mirror to a file for the orchestrator.

Usage::

    python scripts/run_visible.py <agent> <prompt-file> <output-file>

The agent's stdout/stderr stream into the new console *and* into
``output-file``, courtesy of PowerShell's ``Tee-Object``. The new window
stays open at the end (Read-Host) so the user can read the full
transcript at leisure.

The orchestrator decides "agent finished" by polling ``output-file`` —
we write a sentinel ``__DONE__`` line to it as the last action of the
PowerShell script.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


SENTINEL = "__CG_DONE__"


AGENT_INVOCATIONS = {
    # Each entry says how to *invoke* the agent inside PowerShell so that
    # it reads the prompt from a file and writes its response to stdout.
    "claude": (
        "Get-Content -Raw -Encoding UTF8 '{prompt_file}' | "
        "claude --print"
    ),
    "gemini": (
        # gemini -p reads the prompt from -p arg, not stdin; pass file content
        "$prompt = Get-Content -Raw -Encoding UTF8 '{prompt_file}'; "
        "$env:GOOGLE_GENAI_USE_GCA = 'true'; "
        "gemini --skip-trust -p $prompt"
    ),
}


def main() -> int:
    if len(sys.argv) != 4:
        print("usage: run_visible.py <agent> <prompt-file> <output-file>",
              file=sys.stderr)
        return 2
    agent, prompt_file, output_file = sys.argv[1], sys.argv[2], sys.argv[3]
    if agent not in AGENT_INVOCATIONS:
        print(f"error: unknown agent {agent!r}", file=sys.stderr)
        return 2

    prompt_file = str(Path(prompt_file).resolve())
    output_file = str(Path(output_file).resolve())
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    # Reset output file so caller can poll it without seeing stale data.
    Path(output_file).write_text("", encoding="utf-8")

    invocation = AGENT_INVOCATIONS[agent].format(prompt_file=prompt_file)

    ps = f"""
$Host.UI.RawUI.WindowTitle = '{agent.upper()} — live'
Write-Host '== {agent.upper()} working ==' -ForegroundColor Cyan
Write-Host 'Prompt file: {prompt_file}'
Write-Host 'Output file: {output_file}'
Write-Host ''
try {{
    {invocation} 2>&1 | Tee-Object -FilePath '{output_file}'
    $ec = $LASTEXITCODE
}} catch {{
    Write-Host ('ERROR: ' + $_) -ForegroundColor Red
    $ec = 1
}}
Add-Content -Path '{output_file}' -Value ''
Add-Content -Path '{output_file}' -Value ('{SENTINEL} exit=' + $ec)
Write-Host ''
Write-Host ('== {agent.upper()} done (exit=' + $ec + ') ==') -ForegroundColor Green
Write-Host 'Window will stay open. Close it whenever.'
Read-Host 'Press Enter to close'
"""
    # Save the script — PowerShell parses it cleanly when given as -File.
    script_path = Path(output_file).with_suffix(".ps1")
    script_path.write_text(ps, encoding="utf-8")

    # Spawn detached PowerShell window
    subprocess.Popen(
        ["cmd.exe", "/c", "start", f'{agent.upper()} live',
         "powershell.exe", "-NoExit",
         "-ExecutionPolicy", "Bypass",
         "-File", str(script_path)],
    )
    print(f"[run_visible] launched {agent} window; tailing {output_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
