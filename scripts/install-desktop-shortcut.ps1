# install-desktop-shortcut.ps1
# Creates a Windows desktop shortcut "CLAUDEGRAVITY" that launches the
# CG dashboard on http://127.0.0.1:8765 with the brutal Hustler icon.
#
# Run from PowerShell (no admin needed):
#     cd D:\CG
#     powershell -ExecutionPolicy Bypass -File scripts\install-desktop-shortcut.ps1
#
# Removes the previous "CG Dashboard" shortcut if present, then installs
# the new one. Idempotent - re-run any time you regenerate icons.

$ErrorActionPreference = "Stop"

$Repo       = (Resolve-Path "$PSScriptRoot\..").Path
$IconSource = Join-Path $Repo "src\dashboard_static\brand\cg-icon.ico"
$Desktop    = [Environment]::GetFolderPath("Desktop")
$NewLink    = Join-Path $Desktop "CLAUDEGRAVITY.lnk"
$OldLink    = Join-Path $Desktop "CG Dashboard.lnk"

Write-Host "CLAUDEGRAVITY desktop shortcut installer" -ForegroundColor Yellow
Write-Host "Repo:    $Repo"
Write-Host "Icon:    $IconSource"
Write-Host "Desktop: $Desktop"
Write-Host ""

if (-not (Test-Path $IconSource)) {
    Write-Host "Icon not found - generating now..." -ForegroundColor Yellow
    Push-Location $Repo
    python "scripts\make-icons.py"
    Pop-Location
}

# Find python.exe
$Python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $Python) {
    $Python = (Get-Command py -ErrorAction SilentlyContinue).Source
}
if (-not $Python) {
    Write-Error "python.exe not found in PATH. Install Python 3.11+ first."
    exit 1
}

$LauncherScript = Join-Path $Repo "src\cg.py"
if (-not (Test-Path $LauncherScript)) {
    Write-Error "Launcher not found at: $LauncherScript"
    exit 1
}

# Drop the old "CG Dashboard.lnk" if present
if (Test-Path $OldLink) {
    Remove-Item $OldLink -Force
    Write-Host "Removed old shortcut: CG Dashboard.lnk" -ForegroundColor DarkGray
}

# Build the new "CLAUDEGRAVITY.lnk"
$Wsh = New-Object -ComObject WScript.Shell
$sc  = $Wsh.CreateShortcut($NewLink)
$sc.TargetPath       = $Python
$sc.Arguments        = "`"$LauncherScript`" dashboard"
$sc.WorkingDirectory = $Repo
$sc.IconLocation     = "$IconSource,0"
$sc.Description      = "CLAUDEGRAVITY - Hustler multi-agent dashboard (http://127.0.0.1:8765)"
$sc.WindowStyle      = 7
$sc.Save()

Write-Host "Created: $NewLink" -ForegroundColor Green
Write-Host ""
Write-Host "Double-click the desktop icon to launch the dashboard." -ForegroundColor Cyan
Write-Host "If the icon does not refresh, right-click desktop > Refresh."
