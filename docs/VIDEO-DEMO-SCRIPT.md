# Video demo script — "From idea to working thing"

**Target length:** 3 minutes.
**Tagline:** *"You don't pick a template. You describe an idea. Opus designs
a custom team. The team ships your project. On your own subscriptions."*

This script is meant to be performed in a single take with light editing.
Two takes recommended: one with full approval flow (manual) for the
"craftsmanship" angle, one with **Auto mode** for the "I just walk away"
angle.

---

## Pre-flight checklist (~5 min before recording)

```bash
cd D:\CG
git pull origin master                 # ensure on latest
python -m pytest tests/ -q --tb=no      # confirm 212+ green
python src/cg.py doctor                 # verify Claude + Gemini OAuth alive
```

Then:

- Stop any old dashboard, start fresh:
  ```powershell
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like '*cg.py*dashboard*' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
  Start-Process python -ArgumentList "src\cg.py","dashboard"
  ```
- Open `http://127.0.0.1:8765` in a fresh browser window. Maximize.
- Set browser zoom to 110% (text + role badges read clearly on YouTube).
- Clear the Quick Start textarea (no leftover idea).
- Settings → Workflow variables → make sure `IDEA` is empty.
- Run history sidebar: collapse it (less clutter on screen).
- Visual mode toggle: switch to **Terminal** (vertical agent panels — the
  Mission-Mode-ish view) so the role badges + replay buttons are
  immediately visible.

---

## Demo idea — choose one

Pick a real idea that:
- Maps to clear feature scope (not "build me Twitter")
- Doesn't need login/payment hookups for demo (those live in code, not
  in the demo)
- Short enough that Phase 1 brief reads in <30 s on screen

Suggested ideas (rotate per take):

> *"A web app for solo Czech freelancers to track billable hours and
> auto-generate Czech-format invoices in PDF. Mobile-first PWA, dark
> mode default, Stripe for payments later."*

> *"A simple landing page for a SaaS that turns long YouTube videos
> into structured 800-word blog posts. Hero, 3 features, FAQ, pricing,
> waitlist email capture."*

> *"A CLI tool for analyzing my git repo and printing the top 10 files
> by churn × line count over the last 90 days. Single Python file."*

The demo flow is the same for any of them — only the on-screen brief
content changes.

---

## Take 1 — Manual flow (≈3 min)

### Beat 1 — open shot (0:00–0:15)

**Visual:** dashboard hero, cursor at rest near the textarea.

**Voiceover:**

> "ClaudeGravity. Open-source multi-agent orchestrator. Runs on your own
> Claude and Gemini subscriptions — zero credits, zero per-task pricing.
> You don't pick a template. You describe an idea."

### Beat 2 — type the idea (0:15–0:35)

**Visual:** type the idea into the Quick Start textarea. Pause briefly
at the end so the viewer reads it.

**Voiceover:**

> "Watch this. One sentence — the kind of thing you'd type into ChatGPT
> if you wanted advice. Now I click Conductor."

### Beat 3 — Phase 1 streams (0:35–1:15)

**Action:** click **🎩 Conductor**.

**Visual:** the Phase 1 panel opens. Brief Markdown streams in
section by section. Persona, Use-cases, Scope, Milestones, Stack, Pricing,
Risks. ~30–60 s wall clock.

**Voiceover:**

> "Behind the scenes, Opus 4.7 — Anthropic's strongest model — is acting
> as the Visionary. Reading my idea and writing a tight one-page brief.
> Persona, scope, milestones, recommended stack — the questions a founder
> would ask before writing any code. **It's writing this live, on my own
> Pro subscription, no API keys.**"

When streaming finishes, point cursor at the **Approve & compose** button:

> "I read it. If I want to change a milestone or scope something out, I
> edit inline. Otherwise — approve."

Click **✅ Approve & compose workflow**.

### Beat 4 — Phase 2 streams (1:15–1:50)

**Visual:** Phase 2 panel opens. Opus emits a fenced JSON block. The
terminal-style streaming builds the spec line by line.

**Voiceover:**

> "Now Opus designs the actual team. Not pulling from a fixed template —
> writing one custom for *this* idea. Visionary, Architect, Designer,
> Engineer, QA, Critic, Operator. Each role gets the right model:
> Claude for reasoning and code, Gemini for design and creative
> diversity, Sonnet for review."

When the JSON finishes:

> "Validated against my installed models. No cycles, no forward
> references, hard cap of twelve agents. If anything's malformed
> Conductor retries. Looks good — let's run it."

Click **▶ Launch this team**.

### Beat 5 — Phase 3 timeline (1:50–2:30)

**Visual:** Page jumps to the live run. Agent panels appear with role
badges (🔭 Visionary, 🏛 Architect, etc.). Status pills flip from queued
→ running → done. Token counters tick. Output streams under each panel.

**Voiceover:**

> "The team is shipping. Architect first — designing the system, picking
> tables, defining the API contract. Then Designer — Gemini, different
> vendor, different visual judgment. Engineer ships the code on Claude
> Opus 1-million context, no token limit drama. QA writes tests. Critic
> reviews everything. Operator writes the README and the deploy guide."

Hover over the **🔁 round** badge if a refinement loop is configured:

> "And if there's a refinement loop in the spec — Designer iterates with
> Critic for three rounds across two vendors — you watch the round
> counter climb. Real cross-vendor collaboration."

### Beat 6 — save the project (2:30–2:55)

**Visual:** scroll to the run header, click **📦 Save project**.
File explorer opens (or path is shown). Open it briefly to show real
files on disk: `package.json`, `src/`, tests, README, deploy guide.

**Voiceover:**

> "When the team's done, click Save. The Operator's on-disk output
> becomes a real folder of real files I can git-init and ship. The
> whole thing — from one sentence to a working project — ran on my
> Pro subscription. No platform credits. No per-task pricing. No
> templates I had to pick from."

### Beat 7 — closing card (2:55–3:00)

**Visual:** dashboard with the completed run visible. Overlay the repo
URL.

**Voiceover:**

> "ClaudeGravity. Open source. github.com/hustlerv369/CG. Bring your own
> subscriptions."

---

## Take 2 — Auto mode (≈90 s)

Same setup, but tick **🚀 Auto mode** before clicking Conductor. Then:

> "Same thing again, but I'll tick Auto mode this time."

(click Auto, click Conductor)

> "Brief streams. No approval. Compose runs immediately. Validates,
> launches. Coffee."

(let it run; cut footage to ~20 s of timeline action)

(when done, save project)

> "Idea in, working thing out. Three minutes of model time, zero clicks."

---

## Editing notes

- **Cut** any 2+ second pause where the user is just waiting for stream.
  Speed those up 4× with a small clock overlay.
- **Highlight** the role badges with a subtle red ring on first
  appearance.
- **Caption** every action in lower-third (e.g. "Click Conductor",
  "Approve brief", "Launch team") — viewers on mute should still
  follow.
- **Show** the github URL throughout the lower-third in subtle gray.
- **End card** at 3:00: repo URL + license (GPL) + "no API keys
  required".

---

## What NOT to show

- The internal `/api/conductor/*` HTTP calls (boring for non-devs).
- The MODEL-LIMITS.md docs (they're for builders, not viewers).
- Any preset dropdown — Conductor IS the demo. Templates are the
  fallback path, not the headline.
- Errors / retries — if Phase 1 hangs, cut and re-shoot. Don't show
  the timeout watchdog firing in a marketing video.

---

## Recovery if something goes wrong mid-take

| Problem | Quick recover |
|---|---|
| Phase 1 streams nothing for >60 s | Stop run, restart dashboard, re-shoot |
| Phase 2 emits invalid JSON | The 422 response shows in the panel — say *"Conductor caught a malformed spec, retrying"* and re-conduct. Or cut. |
| An agent in Phase 3 hangs | Click **🔁 Replay** on that step. Real demo of the v49 W4 feature. |
| Dashboard reloads mid-take | Stop, fix env, re-shoot. |

---

## Equipment

- 1080p (or 4K downscaled to 1080p) screen capture, 60 fps.
- External mic — phone built-in or Yeti is fine, no AirPods (compression
  artifacts).
- Quiet room, no fan/keyboard noise. Use a quiet keyboard for typing
  beats.
- Dual monitors: dashboard on the recording monitor, this script on the
  other.

---

**Final check before you hit record:** read the script through once
out loud at presenting pace. If it doesn't fit in 3 minutes, cut Beat
2 down or speed-edit Beat 4 in post.
