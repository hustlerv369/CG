# claudegravity.space — what's actually running

This is the live reference for the deployment that went live on
**2026-05-09**. For the design rationale + alternatives (Cloudflare
Tunnel, VPS+API), see `DEPLOY.md`.

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  visitor's browser                                                   │
│         │                                                            │
│         ▼   https://claudegravity.space (or www.claudegravity.space) │
│  ┌─────────────────┐                                                 │
│  │  GoDaddy DNS    │                                                 │
│  │  A   @  →       │ 46.36.39.161  (TTL 1 h)                         │
│  │  CNAME www →    │ claudegravity.space                             │
│  └────────┬────────┘                                                 │
│           ▼                                                          │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │  hukot.net VPS  (46.36.39.161, Ubuntu 22.04, hackerznhustlerz)│   │
│  │                                                              │    │
│  │   Caddy :443 (Let's Encrypt prod, auto-renew)                │    │
│  │     │                                                        │    │
│  │     ├─ claudegravity.space, www.claudegravity.space {        │    │
│  │     │     reverse_proxy 127.0.0.1:7080                       │    │
│  │     │       flush_interval -1   (long-lived SSE)             │    │
│  │     │   }                                                    │    │
│  │     ▼                                                        │    │
│  │   sshd :7080  (bound 127.0.0.1 only — GatewayPorts off)      │    │
│  │     ▲                                                        │    │
│  │     │ reverse tunnel (started by PC, outbound port 22)       │    │
│  └─────│────────────────────────────────────────────────────────┘    │
│        │                                                             │
│  ┌─────┴────────────────────────────────────────────────────────┐    │
│  │ Hustler's Windows 11 PC                                      │    │
│  │                                                              │    │
│  │   Scheduled Task "ClaudeGravity-tunnel"                      │    │
│  │     ssh -N -R 7080:127.0.0.1:8765 root@46.36.39.161          │    │
│  │     (auto-restart on disconnect, runs as Hustler@login)      │    │
│  │                                                              │    │
│  │   python src/cg.py dashboard  (FastAPI on 127.0.0.1:8765)    │    │
│  │     - HTTP Basic auth via CG_AUTH_PASSWORD_HASH env var      │    │
│  │     - Conductor + 30 presets + replay + Mission Library      │    │
│  │     - Claude OAuth (Pro) + Gemini OAuth (Google) live here   │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

## Why SSH reverse tunnel instead of frp / cloudflared

- **frp ruled out:** the VPS provider firewalls inbound port 7000
  (the frp control channel default), so frpc on the PC couldn't
  connect. We tried; logs in `git log` reference the abandoned attempt.
- **cloudflared ruled out:** would have required adding the domain
  to a new Cloudflare account. Per `CLAUDE.md` the user explicitly
  avoids Cloudflare on this stack.
- **SSH wins:** outbound port 22 to hukot is already proven (every git
  push uses it). The same key + the same account handles the tunnel.
  GatewayPorts is OFF, so the tunneled port (7080) is bound to
  127.0.0.1 only — Caddy reaches it locally, the public never does.

## Files in this repo

| Path | Purpose |
|---|---|
| `src/auth.py` | PBKDF2-SHA256 password hashing, `cg auth init` backing |
| `src/dashboard.py` (middleware section) | HTTP Basic gate, opt-in via env |
| `deploy/vps/Caddyfile.snippet` | Block to append to `/etc/caddy/Caddyfile` |
| `deploy/windows/install-tunnel.ps1` | One-shot Scheduled Task installer |
| `deploy/windows/cg-tunnel.ps1` | Foreground tunnel loop (alt to install-tunnel) |
| `deploy/windows/frpc.toml.example` | frp config kept for reference (not in use) |
| `docs/DEPLOY.md` | Architecture + alternative deployment options |
| `docs/DEPLOY-LIVE.md` | This file — what's actually running |

## What was done on the VPS (one-time)

1. Appended `deploy/vps/Caddyfile.snippet` to `/etc/caddy/Caddyfile`.
2. `systemctl reload caddy` — Caddy obtains Let's Encrypt cert on first
   request to `https://claudegravity.space` (E8 issuer, 90-day cert,
   auto-renews).
3. `rm -rf /var/lib/caddy/.local/share/caddy/acme/acme-staging-v02.*`
   — there was stale staging-only state from older work that briefly
   prevented prod cert issuance.
4. No firewall changes — port 22 already open, port 7080 binds to
   127.0.0.1 (not visible to the internet anyway).

## What was done on the PC (one-time)

1. `python src/cg.py auth init --user hustler --url https://claudegravity.space`
   → password generated, hash printed, credentials saved to
   `C:\Users\Hustler\Desktop\claudegravity-login.txt`.
2. Set user-scope environment variables:
   - `CG_AUTH_USER=hustler`
   - `CG_AUTH_PASSWORD_HASH=pbkdf2_sha256$600000$...`
3. Restart the dashboard so it reads the new env vars.
4. `powershell -ExecutionPolicy Bypass -File deploy\windows\install-tunnel.ps1`
   — registers the Scheduled Task, starts it now, schedules at-login
   restart on every reboot.

## What was done at GoDaddy (one-time)

1. DNS Records → A `@` → set value to `46.36.39.161` (was a default
   GoDaddy WebsiteBuilder placeholder).
2. CNAME `www` → `claudegravity.space` was already in place.
3. Nameservers stayed on GoDaddy's `ns11.domaincontrol.com /
   ns12.domaincontrol.com` — no nameserver change required.

## Health checks

| Check | Command | Expected |
|---|---|---|
| Dashboard up | (on PC) `curl http://127.0.0.1:8765/api/agents -u hustler:<pw>` | `200` |
| Tunnel up | (on VPS) `ss -tln \| grep 7080` | `LISTEN ... 127.0.0.1:7080` |
| Cert valid | (on VPS) `echo \| openssl s_client -servername claudegravity.space -connect claudegravity.space:443 2>/dev/null \| openssl x509 -noout -dates` | `notBefore/notAfter` show prod cert |
| Public auth gate | (anywhere) `curl https://claudegravity.space/api/conductor/roles` | `401` |
| Public with auth | (anywhere) `curl -u hustler:<pw> https://claudegravity.space/api/conductor/roles` | `200` + JSON |
| End-to-end | (browser) open `https://claudegravity.space`, enter credentials | dashboard loads |

## Failure modes + recovery

| Symptom | Likely cause | Fix |
|---|---|---|
| Browser shows 502 from Caddy | tunnel down on PC | `Get-ScheduledTask "ClaudeGravity-tunnel"` → `Start-ScheduledTask`; check `cg-tunnel.log` |
| Browser shows 401, password rejected | env var on PC out of sync with the hash printed by `cg auth init` | re-run `cg auth init`, copy new hash to env, restart dashboard |
| Cert expired | Caddy auto-renew failed (rare; usually DNS or port issue) | `journalctl -u caddy -n 200`; rerun `systemctl reload caddy` |
| Tunnel disconnects often | flaky local internet, ServerAlive grace too short | bump `ServerAliveInterval` in `install-tunnel.ps1` to 60 |
| PC offline → site down | by design (BYOS architecture) | turn the PC on, the tunnel auto-reconnects within ~1 minute |

## Rotating the password

```powershell
cd D:\CG
python src/cg.py auth init --user hustler --url https://claudegravity.space
# Copy the new hash from the printed output. Then:
[Environment]::SetEnvironmentVariable("CG_AUTH_PASSWORD_HASH", "<new-hash>", "User")
# Restart the dashboard:
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -like '*cg.py*dashboard*' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
$env:CG_AUTH_PASSWORD_HASH = [Environment]::GetEnvironmentVariable("CG_AUTH_PASSWORD_HASH","User")
$env:CG_AUTH_USER = [Environment]::GetEnvironmentVariable("CG_AUTH_USER","User")
Start-Process python -ArgumentList "src\cg.py","dashboard"
```

The credentials file on the Desktop is overwritten by `auth init` —
no separate copy step required.

## Security posture

- **TLS:** Let's Encrypt prod cert, ECDSA, 90-day rotation handled by
  Caddy. TLS 1.2+ only.
- **Auth:** HTTP Basic over HTTPS, PBKDF2-SHA256 600k iterations,
  constant-time verify. No session cookies — every request re-checks.
- **Tunnel surface:** SSH key auth only, GatewayPorts off (tunnel
  port not visible publicly), no inbound port opened on the PC.
- **No persistent server-side state:** OAuth tokens for Claude / Gemini
  live ONLY on the PC. The VPS is a TLS terminator + tunnel endpoint;
  losing it would not leak any credentials.
- **Rate limiting:** none currently. If abuse becomes an issue, add a
  Caddy `rate_limit` directive to the site block.
- **Password leak response:** rotate password (above). Old hash stops
  validating the moment the new env var is set.
