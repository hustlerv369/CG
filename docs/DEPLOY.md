# Deploying CG to claudegravity.space (or any custom domain)

CG was built BYOS — Bring Your Own Subscription. Claude Pro OAuth and
Google OAuth tokens for Gemini live on the host that runs `claude --print`
and `gemini -p`. That has implications for production deployment.

This doc walks through the three real options, recommends the one
that matches CG's architecture, and lists exactly what to change on
the dashboard host + DNS provider.

## TL;DR

The OAuth-on-subscriptions model means CG works best as a **personal
service tunneled to a public domain**, not as a multi-tenant SaaS
behind a VPS. For a single-user setup like Hustler's, the right path
is option 1 below.

| Option | When to pick | Cost |
|---|---|---|
| **1. Local PC + tunnel + DNS** ⭐ | You're the only user. PC is on most of the day. | Free (Cloudflare Tunnel) or ~$0.50/mo (ngrok) |
| 2. VPS + API keys | Need 24/7 uptime, multiple users, OK to pay per-token | ~$5/mo VPS + token billing per agent call |
| 3. VPS + copied OAuth tokens | Want "free" 24/7. Fragile, against TOS. | $5/mo VPS, will silently break |

This doc covers option 1 in full. Options 2 and 3 are summarised at
the bottom.

---

## Option 1 — Local PC + Cloudflare Tunnel + GoDaddy DNS

Architecture:

```
   ┌──────────────────────────────────────────────────────────────┐
   │                                                              │
   │   visitor's browser                                          │
   │           │                                                  │
   │           ▼                                                  │
   │   https://claudegravity.space                                │
   │           │                                                  │
   │   ┌───────┴────────┐                                         │
   │   │  GoDaddy DNS   │  (CNAME claudegravity.space →           │
   │   │                │   <tunnel-id>.cfargotunnel.com)         │
   │   └───────┬────────┘                                         │
   │           ▼                                                  │
   │   ┌──────────────────┐                                       │
   │   │ Cloudflare edge  │  (terminates TLS, runs WAF rules)     │
   │   └────────┬─────────┘                                       │
   │            │  outbound-only mTLS tunnel                       │
   │            ▼                                                 │
   │   ┌─────────────────────┐                                    │
   │   │ Hustler's Win 11 PC │                                    │
   │   │  - cloudflared svc  │                                    │
   │   │  - cg dashboard:8765│  ← HTTP Basic auth (CG_AUTH_*)     │
   │   │  - claude OAuth     │                                    │
   │   │  - gemini OAuth     │                                    │
   │   └─────────────────────┘                                    │
   │                                                              │
   └──────────────────────────────────────────────────────────────┘
```

Why this is the right shape:

- **Claude / Gemini OAuth never leaves your machine.** No credential
  copy, no TOS friction, no token expiry on a remote box.
- **No inbound port** opened on your PC — cloudflared makes only
  outbound connections to Cloudflare's edge. No router config, no
  firewall holes.
- **TLS handled by Cloudflare** — you get `https://claudegravity.space`
  with a real cert, no Let's Encrypt cron, no certbot.
- **Auth happens twice** — once at the Cloudflare edge (optional, via
  Cloudflare Access if you want IdP-style login) and once at CG's HTTP
  Basic layer. The Basic layer alone is enough for a single-user
  setup.
- **Free tier** is fine for personal use. ~5 GB/month bandwidth, plenty.

### Prerequisites

You'll need:
- A free Cloudflare account (sign up at https://dash.cloudflare.com)
- The `claudegravity.space` domain owned at GoDaddy (you have this)
- The CG dashboard already running locally on port 8765 (`cg dashboard`)
- The auth credentials generated (`python src/cg.py auth init`,
  saved to `C:\Users\Hustler\Desktop\claudegravity-login.txt`)

### Step 1 — Add `claudegravity.space` to Cloudflare

1. https://dash.cloudflare.com → "Add a site" → enter
   `claudegravity.space` → choose Free plan.
2. Cloudflare gives you 2 nameservers (e.g. `lara.ns.cloudflare.com`
   + `nathan.ns.cloudflare.com`). Copy them.
3. Open GoDaddy → My Products → claudegravity.space → DNS → "Change
   Nameservers" → enter Cloudflare's pair.
4. Wait 5-30 min for propagation. `dig +short NS claudegravity.space`
   should return the Cloudflare names.

### Step 2 — Install + configure cloudflared on the Windows PC

1. Install:
   ```powershell
   winget install --id Cloudflare.cloudflared
   ```
2. Login (opens a browser window once):
   ```powershell
   cloudflared tunnel login
   ```
3. Create the tunnel:
   ```powershell
   cloudflared tunnel create claudegravity
   ```
   Note the tunnel ID it prints — UUID like `a1b2c3d4-...-...`.
4. Create `C:\Users\Hustler\.cloudflared\config.yml`:
   ```yaml
   tunnel: <tunnel-id-from-step-3>
   credentials-file: C:\Users\Hustler\.cloudflared\<tunnel-id>.json
   ingress:
     - hostname: claudegravity.space
       service: http://127.0.0.1:8765
     - service: http_status:404
   ```
5. Route the DNS:
   ```powershell
   cloudflared tunnel route dns claudegravity claudegravity.space
   ```
6. Run as a Windows service (so it starts on boot):
   ```powershell
   cloudflared service install
   ```
7. Verify it's running:
   ```powershell
   Get-Service cloudflared
   ```

### Step 3 — Enable auth on the dashboard

The credentials file already exists on the Desktop. Pull the
`CG_AUTH_*` lines from it.

```powershell
[Environment]::SetEnvironmentVariable("CG_AUTH_USER", "hustler", "User")
[Environment]::SetEnvironmentVariable(
  "CG_AUTH_PASSWORD_HASH",
  "pbkdf2_sha256$600000$...",  # paste from credentials file
  "User"
)
```

Restart the dashboard so it picks up the env vars:

```powershell
# stop existing
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -like '*cg.py*dashboard*' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
# restart
Start-Process python -ArgumentList "src\cg.py","dashboard"
```

Verify locally:

```powershell
curl http://127.0.0.1:8765/api/agents              # → 401 Unauthorized
curl -u hustler:<password> http://127.0.0.1:8765/api/agents   # → 200 OK
```

### Step 4 — Verify end-to-end

Open `https://claudegravity.space` in an **incognito window**. The
browser shows a Basic-auth dialog. Enter the username + password from
the credentials file. The dashboard loads.

Repeat in your normal browser to check session persistence (browsers
remember the Basic auth for the session).

### Step 5 — Optional hardening

The Basic auth above is sufficient for a single-user setup. For more
defense in depth:

- **Cloudflare Access** (free tier): adds an SSO-style login at the
  edge. Configure under Cloudflare Zero Trust → Access → Applications.
  Pick Email OTP if you don't have an IdP. CG's Basic auth still
  fires after Access — two-factor effectively.
- **Cloudflare Rules**: block all countries except CZ + US (or
  wherever you actually use it from) with a Custom Rule:
  *"(ip.geoip.country ne 'CZ' and ip.geoip.country ne 'US') → block"*.
- **Rate limiting**: 30 req/min per IP under Cloudflare → Security →
  WAF → Rate limiting rules.

### What to do when the password leaks (or you want to rotate it)

Run `python src/cg.py auth init` again. It generates a new password,
overwrites `claudegravity-login.txt` on the Desktop, and prints a new
hash. Update the `CG_AUTH_PASSWORD_HASH` env var with the new value
and restart the dashboard. Old sessions invalidate the moment the
hash changes.

---

## Option 2 — VPS + API keys (no OAuth)

If you want 24/7 uptime even when your PC is off:

1. Provision a VPS (Hetzner CX22 €4.51/mo is fine).
2. Install Python, git, clone the repo.
3. Get an Anthropic API key + a Gemini API key.
4. Switch CG's `AGENT_KINDS` config to use the API-direct entries
   (`claude-sonnet-4-6-api`, `gemini-pro-api`) instead of the OAuth
   CLI ones. Existing entries are in `src/dashboard.py`.
5. Set up auth via this same `CG_AUTH_*` env var pattern.
6. Reverse-proxy to claudegravity.space via Caddy or Nginx + Let's
   Encrypt.

**Cost:** ~$5/mo VPS + Anthropic/Google billing per agent call. A
single Conductor `idea-to-app` run can use 1-2 M tokens at Opus rates,
so $1-3 per run. Not bad if you're shipping demos; expensive if you
want unmetered usage.

## Option 3 — VPS + copied OAuth tokens

Don't. Tokens expire, refresh flows assume the original device,
copying them to a VPS violates the terms of service for both Claude
and Google. If you go this route despite the warning, the OAuth state
files are at:

- Claude:  `~/.config/claude-code/credentials.json` (or `%APPDATA%\Claude\` on Windows)
- Gemini:  `~/.config/google/auth/credentials.json`

You'll be re-logging in every few weeks at best. Not recommended.

---

## What CG itself contributes vs what's outside its scope

CG ships:
- HTTP Basic auth middleware (off by default, opt-in via env var)
- `cg auth init` CLI for credential generation + Desktop file drop
- Constant-time password verification (PBKDF2-SHA256, 600k rounds)
- 232/232 tests including auth-enabled coverage

CG does NOT ship:
- DNS automation (you do GoDaddy/Cloudflare manually — it's a
  one-time, 5-minute setup)
- TLS termination (Cloudflare or your reverse proxy handles it)
- Multi-user accounts or RBAC (single-user by design — change `auth.py`
  if you outgrow that)

For a single-user personal deployment, the workflow is:
1. `python src/cg.py auth init` (one time)
2. Set the env vars from the credentials file
3. Pick option 1, 2, or 3 above
4. Done
