# Run this AFTER closing all Antigravity windows and the Claude Code
# session that built D:\CG. It renames the old D:\CLAUDE\CLAUDEGRAVITY
# directory to D:\CLAUDE\CLAUDEGRAVITY.archive so:
#   - Antigravity stops auto-loading its poisoned workspace context
#   - The directory is preserved on disk in case anything is needed
#   - The repo on GitHub (hustlerv369/CLAUDEGRAVITY) is the canonical archive
#
# Usage (PowerShell):
#   powershell -ExecutionPolicy Bypass -File D:\CG\scripts\archive-old-claudegravity.ps1

$ErrorActionPreference = "Stop"

$old = "D:\CLAUDE\CLAUDEGRAVITY"
$archived = "D:\CLAUDE\CLAUDEGRAVITY.archive"

if (-not (Test-Path $old)) {
    Write-Host "Already archived (or missing): $old does not exist"
    exit 0
}

if (Test-Path $archived) {
    Write-Host "ERROR: $archived already exists. Move/delete it first or pick a different name." -ForegroundColor Red
    exit 1
}

# Pre-flight: make sure no process holds files inside the old dir.
$locked = Get-ChildItem -Path $old -Recurse -ErrorAction SilentlyContinue |
    Where-Object {
        try { [IO.File]::Open($_.FullName, "Open", "Read", "None").Close(); $false }
        catch { $true }
    } |
    Select-Object -First 5

if ($locked) {
    Write-Host "ERROR: some files are locked. Close Antigravity / Claude Code / VS Code first:" -ForegroundColor Red
    $locked | ForEach-Object { Write-Host "  $($_.FullName)" }
    exit 1
}

Write-Host "Renaming $old -> $archived ..."
Rename-Item -Path $old -NewName "CLAUDEGRAVITY.archive"
Write-Host "Done. The old workspace is now at $archived" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Open Antigravity, point it at D:\CG (new workspace, fresh memory)"
Write-Host "  2. From now on use 'python D:\CG\src\cg.py ...' for orchestrated work"
Write-Host "  3. If you ever want the old code back: cd D:\CLAUDE\CLAUDEGRAVITY.archive"
Write-Host "     or clone https://github.com/hustlerv369/CLAUDEGRAVITY"
