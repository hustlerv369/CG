## Concept

Smile Today is a quiet browser tab that taps you on the shoulder once an hour and asks one thing: smile at a real person nearby. It is not meditation, not therapy, not a streak — just a gentle pulse that pulls you back into the room you are already in.

## Features

- A single full-screen countdown to your next smile
- One tap to mark "done" and reset the hour
- Adjustable interval slider (15 min – 4 h)
- Hourly desktop notification with a rotating one-line prompt
- Works offline and keeps reminding when the tab is hidden (Service Worker)
- Installable as a PWA on phone and desktop
- A soft pulse animation on the logo when a reminder fires

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

1. On first load, show inline button: **"Allow gentle reminders"** → triggers `Notification.requestPermission()`.
2. Permission copy in the button's helper text: *"One soft ping every hour. Nothing else, ever."*
3. Default interval: **60 minutes**.
4. Allowed range: **15 minutes – 4 hours**, set via slider in settings.
5. Foreground tab: `setTimeout` drives the countdown and fires `new Notification(...)`.
6. Hidden tab / closed window fallback: `sw.js` registers a periodic check; on `visibilitychange === 'hidden'` the page hands off the next-fire timestamp via `postMessage`, and the Service Worker calls `self.registration.showNotification(...)` at the right moment.
7. Notification click → `clients.matchAll()` → focus existing tab (or open `/`) → dispatch `smile:reset` event → countdown restarts from full interval.
8. Manual "I smiled" button does the same reset, no notification needed.

## On-screen copy

- **Headline:** Smile Today
- **Sub-headline:** One smile, every hour, at someone real.
- **Timer label:** Next smile in
- **Primary button:** I smiled
- **Permission button:** Allow gentle reminders
- **Permission helper:** One soft ping every hour. Nothing else, ever.
- **Settings — section title:** Rhythm
- **Settings — interval label:** Remind me every
- **Settings — interval unit:** minutes
- **Settings — sound label:** Soft chime
- **Settings — pulse label:** Pulse the logo
- **Settings — reset link:** Start the hour over
- **Footer:** Made quietly. No accounts. No tracking.

**Rotating prompts (one per reminder):**

```
Smile at the next person you see.
A stranger's day is one second from changing.
Look up. Find a face. Smile.
Be the warm thing in someone's afternoon.
The cashier counts too.
Smile first. Don't wait to be smiled at.
Eyes up, corners up.
Someone nearby needs this more than you know.
Give it away. You'll get it back.
A smile costs nothing and lands like sunlight.
```

## Color palette

- **Ink** `#0a0a0a` — backgrounds, text
- **Paper** `#ffffff` — surfaces, text on ink
- **Coral** `#FF5A4E` — single accent (timer ring, button, logo pulse)

`#FF5A4E` is a warm sunrise coral — saturated enough to feel alive against pure black, soft enough to never feel like a notification badge or an error state.

## Type stack

- **Display:** Fraunces (variable, soft optical sizing) — for headline and timer digits
- **Body:** Inter — for everything else

Fraunces brings a hand-drawn warmth that keeps a one-word headline from feeling clinical; Inter underneath stays out of the way and renders perfectly at the small sizes used for settings and helper text. Serif feeling + sans clarity = warm but legible.

## Settings stored in localStorage

| Key | Type | Default |
|---|---|---|
| `smile.intervalMinutes` | number | `60` |
| `smile.soundEnabled` | boolean | `true` |
| `smile.pulseEnabled` | boolean | `true` |
| `smile.permissionAsked` | boolean | `false` |
| `smile.nextFireAt` | number (epoch ms) | `Date.now() + 3600000` |
| `smile.lastSmiledAt` | number (epoch ms) \| `null` | `null` |
| `smile.quoteIndex` | number | `0` |
| `smile.installed` | boolean | `false` |
