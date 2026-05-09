## Concept
A quiet hourly nudge to lift your eyes from the screen and smile at someone real — the cashier, your partner, a stranger on the tram. One small ritual, repeated, until kindness stops being a decision and starts being a reflex.

## Features
- One full-screen card showing the next smile time and a soft countdown.
- A single circular button — *"I smiled"* — that resets the timer and logs the streak silently.
- Hourly desktop/mobile notifications, even when the tab is hidden.
- Adjustable interval slider (15 min → 4 h), remembered across sessions.
- A rotating one-line quote that changes with every reset.
- Quiet streak counter (days in a row you've checked in at least once).
- Pause-for-tonight toggle (resumes at 7:00 next morning).
- Installable as a PWA — works offline, lives on the home screen.

## File structure
```
smile-today/
├── index.html
├── style.css
├── script.js
├── logo.svg
├── manifest.json
└── sw.js
```

## Notification flow
1. **First load:** the page shows the headline and a single button *"Allow gentle reminders"*. No auto-prompt — permission is requested only after the user taps.
2. **Permission copy** (browser-rendered, preceded by an in-app sentence): *"Smile Today would like to send you a small reminder every hour. No tracking, no accounts — just a nudge."*
3. **Default interval:** 60 minutes. **Allowed range:** 15 min – 4 h, set via a slider in Settings.
4. **Scheduling:** on grant, `script.js` registers `sw.js` and stores `nextSmileAt = Date.now() + intervalMs` in localStorage. A `setTimeout` chain in the page handles foreground ticks; the Service Worker re-reads `nextSmileAt` on every `fetch`/`message` event and on `periodicsync` (where supported) to fire `self.registration.showNotification()` when the tab is hidden or closed.
5. **Notification payload:** title *"Smile Today"*, body = one of the 10 rotating quotes, icon `logo.svg`, `tag: "smile-today"` (so reminders replace, never stack), `requireInteraction: false`, `silent: false`.
6. **On click:** the notification closes, the app tab is focused (or opened if absent), `nextSmileAt` resets, and the open tab plays a 600 ms micro-animation — the red dot in the logo gently pulses outward once, like a held breath releasing.

## On-screen copy
- **Headline:** Smile at someone today.
- **Sub-headline:** A small kindness, every hour.
- **Timer label:** Next smile in
- **Primary button (idle):** I smiled
- **Primary button (post-tap, 1.5s):** Thank you.
- **Permission CTA:** Allow gentle reminders
- **Settings — Interval label:** Remind me every
- **Settings — Pause label:** Quiet until morning
- **Settings — Sound label:** Soft chime
- **Settings — Reset label:** Forget my streak
- **Streak label:** {n} days of smiling
- **Footer:** Made quietly. No accounts, no tracking.

**Rotating quotes (one shown per cycle):**
- A smile costs nothing and warms two people at once.
- Look up. Someone near you needs to be seen.
- The shortest distance between two strangers is a smile.
- Be the soft thing in someone's hard day.
- Your face is a gift. Give it freely.
- Kindness is a muscle. Use it now.
- Somewhere, someone is waiting to be smiled at.
- A real smile travels further than any word.
- You will never regret being the warm one.
- The world is quieter when you remember to smile.

## Color palette
- **Ink:** `#0a0a0a`
- **Paper:** `#ffffff`
- **Accent — Coral Pulse:** `#ff5a4e`

A muted coral-red rather than a pure fire-red — it carries warmth and heartbeat without aggression, the colour of a held breath rather than a stop sign.

## Type stack
- **Display:** Fraunces (variable, soft optical sizing)
- **Body:** Inter (clean, neutral, excellent at small sizes)

Fraunces brings a gentle, almost handwritten warmth to the headline and quotes — its softness reads as kindness, not formality. Inter underneath stays invisible and legible, so the timer and settings feel like infrastructure, never decoration. Warm voice on top, quiet plumbing below.

## Settings stored in localStorage
| Key | Type | Default |
|---|---|---|
| `smile.intervalMinutes` | number | `60` |
| `smile.nextSmileAt` | number (epoch ms) | `Date.now() + 3600000` |
| `smile.streakCount` | number | `0` |
| `smile.lastSmileDate` | string (`YYYY-MM-DD`) | `""` |
| `smile.quietUntilMorning` | boolean | `false` |
| `smile.soundEnabled` | boolean | `true` |
| `smile.permissionAsked` | boolean | `false` |
| `smile.lastQuoteIndex` | number | `-1` |
| `smile.installedAt` | number (epoch ms) | `Date.now()` on first load |
