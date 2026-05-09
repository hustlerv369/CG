# EXTEKK — Landing Page Spec

## Brand promise
EXTEKK rebuilds your nuked Discord server in one second and stops the next attack before it lands. Insurance for communities that can't afford to disappear.

## Tone
Surgical. Unbothered. Lethal.

## Information architecture
1. **Hero** — promise, status pill, dual CTA, ambient terminal background.
2. **Watch-it-work** — three-state cinematic showing attack → restore → rebuild.
3. **Live numbers** — four counters animating on scroll, social proof at a glance.
4. **Feature grid** — six capability cards explaining the arsenal.
5. **Terminal demo** — three live CLI blocks proving the bot is real software, not vapor.
6. **Testimonials** — three fixed verified quotes from server owners.
7. **Pricing** — two tiers, free vs Pro, single decision.
8. **FAQ** — five sharp answers to the only questions that block conversion.
9. **Final CTA** — one last invitation, oversized Discord button.
10. **Footer** — nav, social, legal, hacker-tagline.

## Hero copy
- **Headline:** Your server, restored in one second.
- **Sub-headline:** EXTEKK is the security bot that rebuilds nuked Discord servers and kills scammers before they post.
- **Primary CTA:** Add to Discord
- **Secondary CTA:** Watch demo
- **Status pill:** ● ALL SYSTEMS NOMINAL · 99.99% UPTIME

## Watch-it-work — 3 steps
1. **ATTACK DETECTED** — Sentinel flags a compromised admin token at 03:47:12 UTC. Channels start dropping.
2. **RESTORE INITIATED** — Snapshot loaded. Roles, categories, vouches, permissions queued for re-sync in parallel.
3. **SERVER REBUILT** — 1.04 seconds later your community is whole. Attacker logged, blacklisted, gone.

## Live numbers
- **Servers protected** · **23,400+** · communities online
- **Premium operators** · **11,600+** · trusted by
- **Threats neutralized** · **1.2M+** · scams auto-killed
- **Mean restore time** · **0.97s** · attack to rebuilt

## Feature grid — 6 cards
1. **OAUTH RESTORE** — Members and structure rebuilt from cryptographic snapshots. *Icon: shield*
2. **SENTINEL AI** — 24/7 patrol bot deletes phishing and mutes spammers in real time. *Icon: eye*
3. **AESTHETIC BUILDER** — One command spins up a production-grade server in seconds. *Icon: terminal*
4. **PRO TICKETS** — Encrypted support threads with audit trails and role gating. *Icon: ticket*
5. **VOUCH VAULT** — Universal reputation ledger that travels with your community. *Icon: badge*
6. **GLOBAL BLACKLIST** — Cross-server scammer graph updated every 30 seconds. *Icon: globe*

## Terminal demo — copy for code blocks

**Block 1 — Restore**
```
$ extekk restore --snapshot=latest
[03:47:13] ✓ snapshot loaded · 247 channels, 84 roles
[03:47:13] ✓ permissions reconciled
[03:47:14] ✓ vouches resynced · 11,832 entries
[03:47:14] ✓ rebuild complete · 1.04s
```

**Block 2 — Lockdown**
```
$ extekk lockdown --tier=critical
[03:47:15] ⚡ tier 3 lockdown engaged
[03:47:15] ✓ 312 members · read-only
[03:47:15] ✓ 4 admin tokens revoked · 0.31s
```

**Block 3 — Vouch sync**
```
$ extekk vouches sync --global
[03:47:16] → pulling vault · 1.2M records
[03:47:17] ✓ 8,431 reputations updated
[03:47:17] ✓ 12 scammers flagged · added to blacklist
[03:47:17] ✓ sync complete · 0.88s
```

## Testimonials — 3 fixed quotes

> "Got nuked at 4am by a rogue admin. EXTEKK had us back online before I finished my coffee. Insurance you didn't know you needed."
> **@volt** · Server owner · 12K members · ✓ verified purchase

> "Sentinel caught a phishing campaign my mods missed for two weeks. Banned 47 alts in an hour. Worth every cent of the trial."
> **@nyx_mod** · Head moderator · 38K community · ✓ verified purchase

> "Ran my whole launch off EXTEKK's builder. Roles, channels, vouches — production-ready in one command. No competitor comes close."
> **@kairo** · Project founder · 6K trading hub · ✓ verified purchase

## Pricing — 2 tiers

### FREE
*Everything you need to survive.*
- ✓ OAuth Member & Server Restore
- ✓ Aesthetic Server Builder
- ✓ Vouch Vault (community)
- ✓ Global Scammer Blacklist (read)
- ✗ Sentinel AI auto-mod
- ✗ Pro Ticket System

**CTA:** Add for free

### PRO — $19/mo · 14-day free trial
*Everything. No exceptions.*
- ✓ Sentinel AI · 24/7 patrol
- ✓ Pro Ticket System · encrypted
- ✓ Sub-second restore SLA
- ✓ Cross-server reputation sync
- ✓ Priority blacklist push
- ✓ 24/7 white-glove support

**CTA:** Start free trial

## FAQ — 5 questions

**Is it safe to give the bot OAuth?**
Yes. EXTEKK uses scoped Discord OAuth with read-mostly permissions. Snapshots are encrypted at rest and we never touch DMs.

**How fast is restore?**
Median 0.97 seconds for servers under 50K members. The clock starts the instant Sentinel detects the breach.

**What if Discord deletes my server?**
Snapshots live on our infrastructure, not Discord's. Spin up a new server, point EXTEKK at it, and your community is back.

**Do you log my server data?**
We store encrypted structural snapshots only. No message content, no DMs, no personal data. Audit log is open-source.

**Can I cancel anytime?**
One click in the dashboard. No retention call, no email gauntlet. Free tier stays active forever.

## Final CTA
**Stop hoping. Start insuring.** → **Add EXTEKK to Discord**

## Footer
- **Nav:** Features · Pricing · Demo · Docs · Status
- **Social:** Discord · GitHub
- **Legal:** Terms · Privacy · Refund Policy
- **Hacker-tagline:** Built by operators, for operators.
- © 2026 EXTEKK Systems

## Color palette
- **Obsidian background:** `#080808`
- **Electric accent:** `#7CFFB2` (refined mint — confident, not radioactive)
- **Discord blue:** `#5865F2` (reserved for the primary "Add to Discord" CTA only)
- **Breach red:** `#FF4D5E` (subdued crimson — used only for ATTACK DETECTED state and destructive actions)

## Type stack
- **Body:** Geist
- **Mono:** Geist Mono

One family, two cuts — Vercel's Geist gives surgical neutrality in the body and razor-precise terminal authenticity in the mono, so every section feels like it shipped from the same engineering team.
