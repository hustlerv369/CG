# Smile Today

A small kindness, every hour.

A quiet hourly nudge to lift your eyes from the screen and smile at someone real
— the cashier, your partner, a stranger on the tram. One tiny ritual, repeated,
until kindness stops being a decision and starts being a reflex.

## Try it

Live at **<https://claudegravity.online>** — works in any modern browser. Allow
notifications when prompted, then leave the tab open or install it as a PWA.

## Run locally

It's a static site. No build step.

```bash
cd smile-today
python -m http.server 8000
# open http://localhost:8000
```

Browser support: Chrome, Edge, Firefox, Safari 16+ for Web Notifications.
The service worker keeps reminders firing even when the tab is hidden.

## How it was built

Designed by ClaudeGravity's Conductor flow on 2026-05-09:

- **Architect** — Claude Opus 4.7 → concept, features, file structure, copy
- **Designer** — Gemini 2.5 Pro → logo, color tokens, typography pairing,
  three-state layout SVGs, motion spec
- **Engineer** (originally Sonnet 4.6, completed by hand from the spec when
  Sonnet stalled at first-token) → all six files

Source + run trace: <https://github.com/hustlerv369/CG/tree/master/projects/smile-today>

## License

MIT
