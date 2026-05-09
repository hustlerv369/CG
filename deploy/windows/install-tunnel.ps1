# Install/refresh the ClaudeGravity-tunnel Scheduled Task.
#
# Idempotent — re-running this script unregisters the old task and
# registers a fresh copy. Reboots are not required; the task starts
# the SSH process immediately and the OS automatically respawns it
# on every login.
#
# Prereqs (one-time, not done by this script):
#   1. SSH key at $env:USERPROFILE\.ssh\id_hukot with VPS root access.
#   2. CG dashboard running on 127.0.0.1:8765 with CG_AUTH_*
#      environment variables set (see `python src/cg.py auth init`).
#   3. The VPS-side Caddy block + frps/SSH listener (see
#      deploy/vps/Caddyfile.snippet) configured.
#
# Edit $vpsHost below if your VPS IP differs.

[CmdletBinding()]
param(
    [string]$VpsHost = "46.36.39.161",
    [int]   $VpsPort = 22,
    [string]$VpsUser = "root",
    [int]   $LocalPort = 8765,
    [int]   $RemotePort = 7080,
    [string]$KeyPath = "$env:USERPROFILE\.ssh\id_hukot"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $KeyPath)) {
    Write-Error "SSH key not found at $KeyPath. Generate one + add to VPS authorized_keys first."
}

$taskName = "ClaudeGravity-tunnel"

# Lock down key file ACL so OpenSSH doesn't refuse it
& icacls $KeyPath /inheritance:r /grant:r "${env:USERNAME}:R" 2>&1 |
    Out-Null

# Drop any old task
Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue |
    Unregister-ScheduledTask -Confirm:$false

$sshArgs = "-i `"$KeyPath`" -p $VpsPort -N -R ${RemotePort}:127.0.0.1:${LocalPort} " +
           "-o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL " +
           "-o ServerAliveInterval=30 -o ServerAliveCountMax=3 " +
           "-o ExitOnForwardFailure=yes -o ConnectTimeout=10 ${VpsUser}@${VpsHost}"

$action    = New-ScheduledTaskAction `
                -Execute "C:\Windows\System32\OpenSSH\ssh.exe" `
                -Argument $sshArgs `
                -WorkingDirectory "$env:USERPROFILE"
$trigger   = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERNAME"
$settings  = New-ScheduledTaskSettingsSet `
                -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
                -StartWhenAvailable `
                -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
                -ExecutionTimeLimit (New-TimeSpan -Days 365) `
                -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal `
                -UserId "$env:USERNAME" `
                -LogonType Interactive `
                -RunLevel Limited

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "SSH reverse tunnel: 127.0.0.1:$LocalPort -> ${VpsHost}:$RemotePort -> https://claudegravity.space"

Start-ScheduledTask -TaskName $taskName
Start-Sleep -Seconds 4

$task = Get-ScheduledTask -TaskName $taskName
Write-Output ("Task: {0} | State: {1}" -f $task.TaskName, $task.State)

$ssh = Get-Process ssh -ErrorAction SilentlyContinue |
        Where-Object { $_.StartTime -gt (Get-Date).AddSeconds(-30) }
if ($ssh) {
    Write-Output ("SSH PID: {0} | started: {1}" -f $ssh.Id, $ssh.StartTime)
} else {
    Write-Warning "No fresh ssh.exe process detected. Check Event Viewer or run ssh manually with the same args to debug."
}
