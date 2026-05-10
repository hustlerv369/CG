## Concept
EXTEKK is the black-ops insurance policy for Discord servers — one keystroke rebuilds what attackers took an hour to destroy. It sells certainty disguised as software: the bot already saw the nuke coming, and the rollback is just paperwork.

Borrowing from **linear.app**: a single soft-cyan radial blob anchored behind the hero terminal, blurred to ~180px, layered under crisp Inter-grade type so depth reads as *atmosphere*, not decoration. Borrowing from **tailscale.com**: hacker credibility via JetBrains Mono inline-tags ("verified", "nuked → restored") sitting flush inside serif paragraphs — mono-meets-serif without any neon-rave aesthetic. Borrowing from **oxide.computer**: 0px border-radius across every surface — cards, buttons, pricing, terminals — plus monospace-as-display for stat numbers, so the page feels machined rather than designed.

## Tone
Surgical. Cold-confident. Receipts-over-promises.

## Information architecture
1. **Hero** — Tagline + live terminal + status pill above the fold.
2. **Watch-it-work** — 3-step heist sequence: detect → lockdown → restore.
3. **Live numbers** — 4 animating counters proving scale.
4. **Feature grid (bento)** — 6 capabilities in asymmetric layout.
5. **Terminal demo** — 3 parallel CLI blocks showing real commands.
6. **Sentinel section** — Auto-mod 24/7 patrol, scam-link interception montage.
7. **Testimonials** — 3 fixed quotes from server owners.
8. **Pricing** — Free vs Pro, transparent feature deltas.
9. **FAQ** — 5 real objections answered.
10. **Final CTA + Footer** — One-line invitation, hacker-tagline footer.

## Hero copy
- **Headline:** `Your server can't die anymore.`
- **Sub-headline:** EXTEKK rebuilds nuked Discord servers in under a second — channels, roles, members, vouches, intact.
- **Primary CTA:** `Add to Discord`
- **Secondary CTA:** `See it run`
- **Status pill:** `● SENTINEL ONLINE — 23,412 servers under watch`

The word **`die`** is the single acid-accented word in the headline.

## Watch-it-work — 3 steps
1. **Detect** — Sentinel flags mass-channel-delete pattern from a compromised admin token. → `0.000s`
2. **Lockdown** — Permissions frozen, raiders revoked, audit-log snapshot sealed. → `0.420s`
3. **Restore** — Categories, channels, roles, members, and vouch ledger redeployed from encrypted snapshot. → `1.000s`

Heist cadence: zero → almost-instant → done before they noticed.

## Live numbers — 4 cards
| Label | Final | Unit |
|---|---|---|
| Bot downloads | 23,412 | servers protected |
| Premium customers | 11,608 | paid seats |
| Mean restore time | 0.97 | seconds end-to-end |
| Sentinel uptime | 99.998 | % rolling 90-day |

All counters animate from 0 on viewport entry — `IntersectionObserver` + `requestAnimationFrame`, ease-out cubic, 1.6s.

## Feature grid — 6 cards (BENTO)

```
┌───────────────────────────────┬──────────────┐
│ HERO CELL (large)             │ MEDIUM       │
│ EXTEKK SENTINEL               │ RESTORE      │
├──────────────┬────────────────┤              │
│ MEDIUM       │ SMALL          │              │
│ LOCKDOWN     │ VOUCH VAULT    │              │
│              ├────────────────┼──────────────┤
│              │ SMALL          │ SMALL        │
│              │ TICKETS        │ BLACKLIST    │
└──────────────┴────────────────┴──────────────┘
```

1. **SENTINEL** *(hero, large)* — AI patrols every message 24/7, deletes phishing mid-keystroke, mutes spammers before mods wake up. *icon: radar*
2. **RESTORE** *(medium)* — OAuth2 member + structure rollback. One command, full server back. *icon: rewind*
3. **LOCKDOWN** *(medium)* — Aesthetic server builder doubles as panic button. Locks every channel in 200ms. *icon: lock*
4. **VOUCHES** *(small)* — Universal Vouch Vault syncs reputation across servers, immune to wipes. *icon: ledger*
5. **TICKETS** *(small)* — Pro ticket system with transcripts, role-routing, and tag-based triage. *icon: receipt*
6. **BLACKLIST** *(small)* — Global scammer database — 480k flagged IDs, auto-banned on join. *icon: skull*

## Terminal demo — copy for code blocks

Three side-by-side blocks, 0px radius, JetBrains Mono. **The leftmost (hero) terminal performs real letter-by-letter typing animation** — 22ms per char, blinking caret `▌`, then output streams in line-by-line with 80–140ms staggers. Tabs auto-cycle on a 12s loop; users can click to pause.

**Block 1 — `$ extekk restore`**
```
[14:02:11] ✓ snapshot loaded         12ms
[14:02:11] ✓ categories rebuilt      89ms
[14:02:11] ✓ 47 channels redeployed 312ms
[14:02:12] ✓ roles + perms restored 481ms
[14:02:12] ✓ 11,608 members rejoined 970ms
done in 0.97s
```

**Block 2 — `$ extekk lockdown`**
```
[14:02:11] ✓ admin tokens revoked    08ms
[14:02:11] ✓ all channels frozen     94ms
[14:02:11] ✓ raid pattern logged    142ms
[14:02:11] ✓ audit snapshot sealed  201ms
server is read-only.
```

**Block 3 — `$ extekk vouches sync`**
```
[14:02:11] ✓ vault handshake         44ms
[14:02:11] ✓ 8,412 vouches verified 380ms
[14:02:11] ✓ 12 forgeries rejected  391ms
[14:02:11] ✓ ledger broadcast       522ms
reputation: portable.
```

## Testimonials — 3 fixed quotes

> "Got nuked Tuesday at 3am by a compromised mod. Server was back before the raid screenshots hit Twitter. EXTEKK is the only reason I still own this community."
> **`@vyx`** · Owner, 84k-member trading server · ✓ verified purchase

> "Sentinel caught a phishing wave we didn't even know was running. 312 messages auto-deleted, 19 accounts muted, zero tickets opened. It just handled it."
> **`@nullroute`** · Head Mod, indie game guild · ✓ verified purchase

> "I sell Discord services. Vouch Vault means my reputation survives every server my buyers run. That alone pays for Pro ten times over."
> **`@kasimir`** · Reseller, 4.9★ across 6 servers · ✓ verified purchase

## Pricing — 2 tiers

### FREE — `Add to Discord`
- ✓ OAuth2 member restore (up to 1,000)
- ✓ Server structure restore (channels/roles)
- ✓ Basic Sentinel auto-mod
- ✓ Global scammer blacklist
- ✗ Vouch Vault sync
- ✗ Pro Ticket System

### PRO — `$19/mo` · *most popular* · `Start 14-day trial`
- ✓ Unlimited member restore
- ✓ Sub-second restore SLA
- ✓ Sentinel AI (full model, 24/7)
- ✓ Universal Vouch Vault & Reputation
- ✓ Pro Ticket System + transcripts
- ✓ 1-click Aesthetic Builder & Lockdown

## FAQ — 5 questions

<details><summary>Does EXTEKK actually need admin permissions?</summary>Yes — restore and lockdown require Manage Server, Manage Channels, and Manage Roles. Permissions are scoped, audited, and revocable in one click.</details>

<details><summary>What if EXTEKK itself gets removed during a nuke?</summary>Snapshots are stored off-Discord on encrypted infrastructure. Re-add the bot, run `extekk restore`, and the server returns from the last snapshot — even if EXTEKK was kicked first.</details>

<details><summary>How does Sentinel avoid false-positive bans?</summary>Sentinel uses a confidence threshold; below 0.92 it mutes and flags for human review, never bans. Every action is logged with the matching pattern.</details>

<details><summary>Is the Vouch Vault tamper-proof?</summary>Each vouch is signed and broadcast to a shared ledger. Forged or duplicate entries fail verification at sync and are rejected — see the live counter above.</details>

<details><summary>Can I cancel Pro anytime?</summary>Yes. Cancel mid-cycle, keep Pro until the period ends, drop to Free with no data loss. Trial cancels with one click and never charges.</details>

## Final CTA
**Headline:** `One command stands between your server and zero.`
**Button:** `Add to Discord`

## Footer
**Tagline (ALL CAPS, mono):** `WE DON'T PREVENT THE NUKE. WE MAKE IT IRRELEVANT.`

- **Nav:** Features · Pricing · Docs · Status · Changelog
- **Social:** Discord · GitHub
- **Legal:** Terms · Privacy
- **Copyright:** `© 2026 EXTEKK SYSTEMS — BUILT FOR THE 4AM RAID`

## Color palette — STRICT
- **Background:** `#000000` pure obsidian. No off-black, no `#0f1115`.
- **Foreground:** `rgba(255,255,255,1.00 / 0.70 / 0.45 / 0.20)` — pure white only, no warm grays, no cool grays.
- **Acid accent:** `#00FF94` mint. **Justification:** mint reads as *terminal-success-tick*, not rave neon — it carries the "✓ done" semantic into every CTA, so the brand color and the product action are the same gesture.
- **Acid usage:** Primary CTA fill, the word `die` in the headline, status pill dot, link hover underline. Nothing else gets it.
- **Breach red:** `#FF3B5C` — used exclusively for the "raid detected" indicator and the ✗ marks in pricing.

## Type stack — STRICT
- **Display:** **Fraunces** (Google Fonts, variable: `wght 100–900`, `opsz 9–144`, `SOFT 0–100`).
- **Mono:** **JetBrains Mono** (Google Fonts, variable: `wght 100–800`).

**Justification:** Fraunces' high-contrast modern serif with `opsz` axis carries editorial gravity at hero scale (`opsz 144`, `wght 600`, `SOFT 0` — sharp, almost weaponized) while collapsing gracefully to body. JetBrains Mono is the de-facto hacker terminal face — pairing the two creates the exact "dossier-meets-shell" tension the brand promises, with no third typeface ever needed.

**Variable-font scroll modulation:** Fraunces' `wght` axis modulates from `400 → 800` as the hero scrolls into pinned view; `SOFT` axis simultaneously eases from `100 → 0`, so the headline literally hardens as the user commits to the page. JetBrains Mono `wght` axis ticks from `400 → 600` on each terminal `✓` line as it streams in — type weight becomes the success animation.
