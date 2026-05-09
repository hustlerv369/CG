# Luxe spec — drop-in prompt blocks

Paste these blocks into any CG spec where the brief is "luxe" /
"Awwwards-tier" / "breathtaking". Reference: `docs/LUXE-DESIGN-PLAYBOOK.md`.

---

## ARCHITECT block — append to architect prompt

```
## Required design references (MUST acknowledge in your ## Concept)
You MUST emulate the visual signature of these specific sites:
  1. linear.app — depth via blur + gradient blobs, refined Inter pairing
  2. tailscale.com — hacker-credibility without toxic neon, mono-meets-serif
  3. oxide.computer — tactile brutalism, 0px radius, monospace-as-display
Read each. Reference at least one named visual move from each in your
## Concept section (one sentence per reference).

## Color palette — STRICT
- Background: pure obsidian (#000000 or #0a0a0a — not #0f1115)
- Foreground hierarchy: white at 100% / 70% / 45% / 20% — NEVER colored gray
- Acid accent: pick ONE of [#00ffe0 cyan, #ff2bd6 magenta, #caff00 chartreuse, #00ff94 mint]
- Acid usage: primary CTA, ONE hero word, status dot, hover state — nothing else
- NO pastel gradient. NO purple-blue brand palette. NO three brand colors.
```

---

## DESIGNER block — append to designer prompt

```
## STRICT DO-NOTs (fail the spec if violated)
- DO NOT use border-radius > 0px on cards, buttons, or sections.
  ONLY status pills get border-radius: 999px.
- DO NOT use box-shadow for depth. Depth comes from overlap + 1px borders.
- DO NOT use pastel gradients in the hero.
- DO NOT use a 3-equal-column "features" grid with identical icons.
- DO NOT use a "trusted by" logo wall directly under the hero.
- DO NOT use border-radius: 12px (or any non-zero radius) on more than
  3 elements site-wide.

## Required visual moves (cover at least 6 of these in the layouts)
- [ ] Hero headline edge-to-edge at clamp(72px, 11vw, 160px)
- [ ] Variable-font modulation hint (specify the wght / wdth axes you'd map to scroll)
- [ ] Background = animated gradient blobs (2-3 max, filter: blur 120-160px)
- [ ] SVG noise / film-grain overlay specced (turbulence baseFrequency, opacity)
- [ ] At least one bento or asymmetric layout section
- [ ] Tactile brutalism: 0px radius cards, 1px solid borders, no shadows
- [ ] One section that breaks the grid intentionally
- [ ] Cursor-driven micro-interaction (tilt, glow, follow)

## Type stack — required
Pair an editorial or display font (Fraunces, Playfair Display, IBM
Plex Serif, Geist, Anton) with a monospace (JetBrains Mono, Geist
Mono, IBM Plex Mono). NEVER pair two sans-serifs. Justify the
contrast in one sentence.
```

---

## ENGINEER block — append to engineer prompt verbatim

```
## NON-NEGOTIABLE 12-POINT CHECKLIST — ALL REQUIRED OR DO NOT SUBMIT

The output MUST satisfy ALL twelve. Self-audit before emitting any
file. If you cannot honestly tick all 12, state which are missing
at the bottom.

[1]  Hero headline ≥ clamp(72px, 11vw, 160px) font-size
[2]  At least one variable-font axis modulation (wght / wdth / slnt)
     responsive to scroll progress via JS `scroll` listener OR CSS
     `scroll-timeline`
[3]  At least one scroll-driven section transformation using
     `IntersectionObserver` or `scroll-timeline` (CSS) — NOT a setTimeout
[4]  At least one cursor-driven micro-interaction (mousemove → tilt /
     glow / radial-gradient that follows cursor)
[5]  Animated noise / film-grain overlay using SVG `feTurbulence` data
     URI, position: fixed, mix-blend-mode: overlay, opacity 4-8%
[6]  At least one bento section OR asymmetric hero (NOT a centered
     stack with 3-column features below)
[7]  At least 2 animated gradient blobs in the hero
     (filter: blur 120-160px, slow drift via @keyframes 24-40s)
[8]  border-radius: 0 on all cards/buttons. Only status pills may use
     border-radius: 999px.
[9]  No box-shadow for depth. Use overlap and 1px borders.
[10] Single accent color with ≥ 3 white-tint steppes (100/70/45/20).
     No colored grays.
[11] All animations use cubic-bezier(0.22, 1, 0.36, 1) or
     cubic-bezier(0.65, 0, 0.35, 1). Never `ease`, `ease-in`, etc.
[12] @media (prefers-reduced-motion: reduce) disables ALL kinetic
     animations (typing, blob drift, noise translate, scroll triggers).

## Anti-patterns (instant rejection)
- Glass-morphism panels with backdrop-filter: blur(...) AND a soft
  white tint AND rounded corners — this is 2021–22.
- Stock photography for any non-product image
- Drop shadows for card depth
- Border-radius 12px on more than 3 elements site-wide
- "Features" section as 3 equal columns with same icon size
- "Trusted by" logo wall placed directly under the hero
```

---

## How to wire into a CG spec JSON

In your `.spec.json`, the architect/designer/engineer prompts should
each end with `\n\n---\n\n` followed by the matching block above.
Example for the engineer:

```json
"prompt": "Implement <project> as a static site...\n\n## Spec\n{{architect}}\n\n## Design\n{{designer}}\n\n---\n\n## NON-NEGOTIABLE 12-POINT CHECKLIST — ALL REQUIRED OR DO NOT SUBMIT\n\n[1]  Hero headline ≥ clamp(72px, 11vw, 160px)..."
```
