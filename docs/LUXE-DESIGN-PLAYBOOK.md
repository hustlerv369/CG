# Luxe Design Playbook (2026)

What "top web design 2026" actually means in concrete CSS, motion, layout
and typography terms — distilled from three trend reports (ultraperfekt.ch,
fireart.studio, grauberg.co) and the reference galleries they cite
(Awwwards, Mobbin, Dark Mode Design, SiteInspire, Minimal Gallery, Dribbble,
Pageflows, Waveguide).

This is the **MUST-RESPECT block** every CG architect/designer/engineer
prompt has to inject when the brief says "luxurious", "Awwwards-tier",
"breathtaking", or any equivalent. Skip this and you ship 2024-tier flat
dark sites — exactly what failed on EXTEKK Luxe v1.

---

## The non-negotiable five

Any luxe site MUST hit at least four of these or it's not luxe:

1. **Typography is the architecture, not a decoration.** Edge-to-edge
   headlines, viewport units, variable-font weight/width modulation.
2. **One acid color against deep monochrome.** Not three brand colors
   in a soft pastel. Pick obsidian + ONE saturated accent and make it
   feel like a knife.
3. **Motion responds to the user, not to a timer.** Scroll-driven
   transforms beat any 3-second loop. Cursor-driven beats both.
4. **Texture, not flat.** Film grain / SVG noise / animated gradient
   blobs / scan lines — something that breaks the "AI-generated dark
   landing page" silhouette.
5. **Layout breaks the grid at least once.** Bento. Asymmetric hero.
   Off-center section that floats over a full-bleed gradient. The
   eye must land somewhere unexpected on first scroll.

---

## Visual aesthetic patterns

### Tactile Brutalism *(2026 dominant)*

- **Border radius: 0.** No rounded corners on cards, buttons, or sections.
  Reserve `border-radius: 999px` only for status pills.
- **Borders: `1px solid`** in the accent or stark white. No 2px, no
  dashed, no gradient borders.
- **Drop shadows: zero.** Depth comes from overlap and color contrast,
  not blur.
- **Overlapping grid lines** as background — `repeating-linear-gradient`
  at 1–2% accent opacity, 60–80px spacing. Lines visible up close,
  invisible at scale.

```css
:root { --grid: rgba(0, 255, 148, 0.04); }
body {
  background:
    repeating-linear-gradient(0deg, transparent 0 79px, var(--grid) 79px 80px),
    repeating-linear-gradient(90deg, transparent 0 79px, var(--grid) 79px 80px),
    var(--bg-0);
}
```

### Chromatic Extremes

- Deep cyber-monochrome: `#000000` → `#0a0a0a` → `#141414`. Nothing
  in between fades to gray-blue.
- ONE saturated acid: cyan `#00ffe0`, magenta `#ff2bd6`, chartreuse
  `#caff00`, electric mint `#00ff94`. Pick ONE.
- White `#ffffff` for primary text, then 70% / 45% / 20% steppes for
  secondary/tertiary/disabled. Never a colored gray.
- The acid only on: primary CTA, single hero word, status indicator,
  hover state. Saturating everywhere kills the contrast.

### CSS Noise / Film Grain

- An always-on full-viewport noise overlay at 4–8% opacity.
- Implementation: SVG turbulence (lightweight, scalable):

```css
.noise {
  position: fixed; inset: 0; z-index: 999; pointer-events: none;
  opacity: 0.06; mix-blend-mode: overlay;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='200' height='200' filter='url(%23n)' opacity='0.6'/%3E%3C/svg%3E");
}
```

- Animate by translating the overlay 5px in a 600ms loop for "alive"
  film-grain feel.

### Animated Gradient Backgrounds

- Kinetic blob meshes that drift slowly. NOT `linear-gradient` rotating.
  Real pseudo-elements with `filter: blur(120px)` doing slow translate
  loops over 20–40 seconds.

```css
.blob {
  position: absolute; border-radius: 50%;
  filter: blur(140px); opacity: 0.4; mix-blend-mode: screen;
}
.blob-1 { top: -20%; left: -10%; width: 60vw; height: 60vw;
          background: var(--accent);
          animation: drift1 32s ease-in-out infinite; }
@keyframes drift1 { 50% { transform: translate(40vw, 30vh) scale(1.2); } }
```

- Two or three blobs at most. The viewer should sense breathing, not
  recognize a loop.

### Dark-First (`#000000`)

- True black, not `#0f1115`. OLED hardware draws zero power on
  unlit pixels.
- Skip `prefers-color-scheme` light variant for marketing landings —
  the brand IS the dark mode.

### SVG over Photography

- Hero illustrations: SVG. Inline. Animatable. Recolorable.
- Logo: SVG. Always.
- Decorations: SVG. Customer photos / product shots stay raster.

---

## Typography patterns

### Typography as architecture

- Hero headline at `clamp(72px, 11vw, 160px)`. Edge-to-edge. No padding.
- Letter-spacing tight: `-0.04em` to `-0.06em` on display weights.
- Line-height `0.92` for max impact. Not `1`.

### Variable-font scroll-driven modulation

Modern variable fonts (Inter, Geist, Roboto Flex, IBM Plex Sans) expose
weight (`wght`) and width (`wdth`) axes. Map them to scroll progress.

```js
const headline = document.querySelector('.hero h1');
addEventListener('scroll', () => {
  const p = Math.min(1, scrollY / window.innerHeight);
  const wght = 700 - 400 * p;        // 700 → 300 as user scrolls
  const wdth = 100 - 30 * p;          // 100 → 70 (compresses)
  headline.style.fontVariationSettings =
    `"wght" ${wght}, "wdth" ${wdth}`;
});
```

### Neo-Serif × Monospace pairing

Editorial headings in a neo-serif (Fraunces, Playfair Display, IBM
Plex Serif). Functional metadata in mono (JetBrains Mono, Geist Mono,
IBM Plex Mono). NEVER both sans. The contrast is the design.

### Animated text reveal

- Marquee scrolls for tagline tickers (`@keyframes` translate -100%).
- Letter-by-letter SVG path-draw for hero brand at first paint.
- Word-by-word fade-in with 60ms stagger on viewport intersection.

---

## Layout patterns

### Bento grid

- Modular block layout for feature sections / dashboards / portfolios.
- CSS Grid with `grid-template-areas` for hand-tuned compositions, OR
  `grid-template-rows: masonry` (Firefox-only currently, fall back to
  CSS Grid Lanes).
- Each cell has its own purpose: one large hero cell, two medium,
  several small. Never six equal cells.

```css
.bento {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  grid-template-rows: 280px 280px;
  gap: 1px;
  background: var(--border);
}
.bento > :nth-child(1) { grid-column: span 2; grid-row: span 2; } /* hero */
.bento > :nth-child(2) { grid-column: span 2; }                    /* wide */
.bento > :nth-child(3),
.bento > :nth-child(4) { grid-column: span 1; }                    /* small */
```

### Asymmetric hero

- Headline floats LEFT, terminal/visual floats RIGHT, with ONE element
  breaking the gutter (a CTA button overlapping both columns, or a
  scroll-down indicator off-center).
- Reject the `[hero centered] / [features 3-column]` template.

### Just-in-time interface

- UI elements appear only on scroll/hover. The site looks empty at
  load and reveals itself. Inverse of "everything visible".

---

## Motion patterns

### Scroll-driven, not time-driven

- Use `IntersectionObserver` for triggers, not `setTimeout`.
- Use `scroll-timeline` (Chrome 115+) for native CSS scroll animations:

```css
@keyframes appear { from { opacity: 0; transform: translateY(40px); }
                       to { opacity: 1; transform: none; } }
.section {
  animation: appear linear both;
  animation-timeline: view();
  animation-range: entry 0% cover 30%;
}
```

### Cursor-driven micro-interactions

- Buttons that tilt 4° toward the cursor on hover (`mousemove` →
  `transform: rotate(...)`).
- Cards with a subtle glow that follows the cursor across the surface
  (`background: radial-gradient(at var(--mx) var(--my), accent 0%, transparent 40%)`).
- Custom cursor on premium sites — a small mint dot replacing the
  arrow, expanding on link hover.

### Lightweight & purposeful

- ≤ 6 unique animations per page. More than that = noise.
- Easing: `cubic-bezier(0.22, 1, 0.36, 1)` for entrances,
  `cubic-bezier(0.65, 0, 0.35, 1)` for exits. Never `ease`.
- Duration: 280–520ms for UI, 800–1200ms for hero entrances.

---

## Per-genre cookbook

### Hacker / security / Discord-bot

- Tactile brutalism + chromatic extremes (mint or cyan accent).
- Mono pairing for both display and body, OR neo-serif × mono.
- Hero terminal panel TYPING in real time, not pre-rendered.
- Scan-line overlay, animated noise.
- Status pills with live dots, "[OPERATIONAL]" all-caps mono.
- Footer reads like a `/etc/motd` banner.

### SaaS / B2B / dashboard

- Bento grid for feature sections.
- Less acid color, more refined gradient mesh.
- Variable-font scroll modulation on the hero.
- One animated SVG product mock running real-feel data.

### Editorial / portfolio

- Neo-serif × mono pairing strict.
- Asymmetric layout with negative space as a feature.
- Scroll-driven typography reveal letter-by-letter.
- Photography full-bleed only when essential.

### Luxury / lifestyle

- Reserve acid color, lean into deep monochrome + film grain.
- Custom cursor.
- Slow blob mesh background, never abrasive.
- Whitespace as material.

---

## Hard "must" checklist for the engineer prompt

When the brief says "luxe / breathtaking / Awwwards-tier", the engineer
prompt MUST require:

- [ ] Hero headline ≥ `clamp(72px, 11vw, 160px)` font-size
- [ ] At least one variable-font axis modulation (weight, width, or slant)
- [ ] At least one scroll-driven transformation using
      `IntersectionObserver` or `scroll-timeline`
- [ ] At least one cursor-driven micro-interaction (tilt, glow, follow)
- [ ] Animated noise / film grain overlay (SVG turbulence)
- [ ] At least one bento or asymmetric layout section
- [ ] At least 2 animated gradient blobs in the hero (filter: blur)
- [ ] Border-radius: 0 on all cards/buttons EXCEPT status pills
- [ ] No drop shadows for depth — overlap + 1px borders only
- [ ] Single accent color with ≥ 3 muted-white tints for hierarchy
- [ ] All animations use `cubic-bezier(...)` not `ease`
- [ ] `prefers-reduced-motion` respected (disable all kinetic)

If the engineer ships without 8/12 of these, the result will look
2024-tier. Reject and re-run with stricter prompt.

---

## Reference sites to study (per-genre)

When building a brief, paste 2-3 of these into the architect prompt as
"emulate the visual signature of":

| Genre | Reference site |
|---|---|
| SaaS landing | linear.app, vercel.com, runway.com |
| Bento grid | apple.com (homepage), notion.so/product |
| Variable typography | typespiration.com, monotype.com |
| Hacker/security | tailscale.com, plausible.io, oxide.computer |
| Editorial | nytimes.com/interactive/, theverge.com (some) |
| Awwwards SOTD | awwwards.com/websites/ — the front page |

---

## Anti-patterns (= 2024 tier, instantly date a site)

- Glass-morphism EVERYWHERE (was 2021–22).
- Soft pastel gradient hero with a centered CTA.
- 3-column "features" with identical icon cards.
- Drop shadows on cards (`box-shadow: 0 8px 32px rgba(0,0,0,.4)`).
- "Trusted by" logo wall directly under the hero.
- Stock photos.
- A purple-blue brand palette with two purples and one blue.
- Border-radius 12px on EVERYTHING.

---

## How CG injects this

Every CG run that targets a luxe site MUST inject a copy of this
playbook (or its hard checklist) into:

1. **Architect prompt** — under "## Color palette" tell the architect
   to pick ONE accent + obsidian + tints, no exceptions.
2. **Designer prompt** — paste the entire "## Hard 'must' checklist"
   as a final required section.
3. **Engineer prompt** — paste the engineer checklist verbatim with
   "ALL TWELVE ITEMS REQUIRED OR DO NOT SUBMIT".

`.cg-luxe-design.spec-include.json` ships a JSON snippet that any
spec can `$ref` to inherit these requirements. See
`scripts/build-luxe-spec.py` for the wiring.
