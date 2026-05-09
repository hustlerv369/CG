# SSH reverse tunnel — exposes Hustler's local CG dashboard at
# 127.0.0.1:7080 on hukot.net, where Caddy reverse-proxies it to
# https://claudegravity.space.
#
# Why SSH instead of frp: the VPS provider firewalls inbound port 7000.
# Outbound 22 to the VPS already works (proven by the existing CG
# project's git pushes), so SSH reverse tunnel reuses that path.
#
# Run via the ClaudeGravity-tunnel Scheduled Task. Logs to the same
# folder as this script.

$ErrorActionPreference = "Continue"
$logPath  = "$PSScriptRoot\cg-tunnel.log"
$keyPath  = "$env:USERPROFILE\.ssh\id_hukot"
$vpsUser  = "root"
$vpsHost  = "46.36.39.161"
$vpsPort  = 22
# Local CG dashboard port (must match what the dashboard binds to)
$localPort  = 8765
# Remote port that Caddy's reverse_proxy block forwards to
$remotePort = 7080

function Log($m) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$ts $m" | Out-File -Append -Encoding utf8 $logPath
}

Log "tunnel starting: 127.0.0.1:$localPort -> $vpsHost:$remotePort"

# Loop forever — if ssh exits for any reason, wait 5s and reconnect.
while ($true) {
    & ssh `
        -i $keyPath `
        -p $vpsPort `
        -N `
        -R "$($remotePort):127.0.0.1:$localPort" `
        -o StrictHostKeyChecking=no `
        -o UserKnownHostsFile=NUL `
        -o ServerAliveInterval=30 `
        -o ServerAliveCountMax=3 `
        -o ExitOnForwardFailure=yes `
        -o ConnectTimeout=10 `
        "$vpsUser@$vpsHost" 2>&1 |
        ForEach-Object { Log "[ssh] $_" }
    Log "ssh exited (code $LASTEXITCODE) — restarting in 5s"
    Start-Sleep -Seconds 5
}
