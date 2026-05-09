# Luxe Design Playbook (2026)

What "top web design 2026" actually means in concrete CSS, motion, layout
and typography terms — distilled from:

**Trend reports**
- ultraperfekt.ch/en/insights/web-design-trends-2026
- fireart.studio/blog/the-best-web-design-trends/
- grauberg.co/resources/websites-ui

**Reference galleries** — Awwwards, Mobbin, Dark Mode Design, SiteInspire,
Minimal Gallery, Dribbble, Pageflows, Waveguide.

**Codified pattern libraries**
- `docs/design/brands/` — 73 brand DESIGN.md files with structured tokens
  (colors, type scale, spacing, radii) for Linear, Apple, Stripe, Vercel,
  Cohere, Notion, Figma, Tesla, BMW, Ferrari, Lamborghini, Sanity,
  Shopify, Airbnb, Spotify, Starbucks… cloned from
  github.com/ItsssssJack/power-design (forked from VoltAgent/awesome-design-md)
- `docs/design/principles/design-principles.md` — 20 codified rules with
  numeric thresholds (40% whitespace, 4.5:1 contrast, line-height 1.4-1.6,
  ratio-based type scale, 8-pt grid, F/Z attention pattern, etc.)
- Workflow patterns from garden-skills web-design-engineer
  (declare design system → v0 draft → full build → checklist)

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

---

# Part 2 — The named-pattern library

Every CG brief now selects from these named patterns instead of
re-deriving them from a vague brief. This is Hustler's taxonomy +
the integrated patterns from `power-design` and
`garden-skills/web-design-engineer`.

## The 9 named visual styles

### `style.glassmorphism_saas_v2` *(SaaS / fintech / dashboards)*

Modern soft frosted glass — refined, not the 2021 toxic version.

- **80% of the page is a clean simple background** (gradient or
  textured) — sklo je JEN na kartách, navbarech, side panelech.
- `backdrop-filter: blur(20-32px)` + `background: rgba(255,255,255,0.04)`
  on the dark variant; `rgba(0,0,0,0.04)` on light.
- **Text contrast first.** Always pair glass card with a slightly
  darker overlay behind it so body copy hits 4.5:1.
- Tiny border-radius (`8-16px`) on glass surfaces — no hard corners.
- Hairline `1px solid rgba(255,255,255,0.08)` border on every glass
  card. No drop shadow.
- **Aurora layer optional** — animated gradient blob mesh BEHIND
  the glass for depth. Slow drift, opacity 30-40%, mix-blend-mode
  screen.
- Fallback for browsers without `backdrop-filter`: solid 8% white
  surface, no blur.
- Verify contrast with `audit.accessibility_glass_v1` before shipping.

### `style.tactile_brutalism_enterprise` *(B2B, devtool, security)*

Sharp geometric, typography-led. The signature of EXTEKK Luxe v2.

- **0px border-radius everywhere except status pills.**
- 1px solid borders. Often the accent color, not white.
- ZERO drop shadows. Depth = overlap + 1px borders.
- High-contrast B&W base + 1-2 accent colors max.
- Typography is the hero — display set at `clamp(72-160px)`,
  edge-to-edge, no margin.
- Repeating-gradient grid lines as background (1-2% accent opacity,
  60-80px spacing).
- CSS noise / SVG turbulence overlay at 4-8% opacity.
- No stock photography — SVG illustrations or pure type.
- Per `power-design` brands matching this style: linear.app,
  oxide.computer-style, tailscale.com, vercel, supabase.

### `style.claymorphism_playful` *(consumer, kids, illustration sites)*

Plastic 3D shapes, soft shadows, "kneaded" cards. **Not for the
whole layout** — use for icons, CTAs, accent cards only.

- Border-radius `24-40px`.
- Layered soft shadows (BOTH directions): `box-shadow:
  inset 4px 4px 8px rgba(255,255,255,0.5),
  inset -4px -4px 8px rgba(0,0,0,0.1),
  4px 4px 12px rgba(0,0,0,0.1)`
- Saturated pastel colors. NOT washed-out — bright, kid-toy hues.
- 3D-feel illustration treatment — Notion-doodle / Memoji style.
- Combine with `style.glassmorphism_saas_v2` if you want a softer
  variant of the SaaS look.

### `style.aurora_liquid_glass` *(luxury, immersive, premium)*

Glass + aurora gradients fused. Apple-tier marketing pages.

- Animated multi-stop gradient mesh background (CSS conic-gradient
  or SVG `feGaussianBlur` over multiple paths).
- Glass surfaces float on top with backdrop-filter saturate(180%)
  blur(28px).
- Reflections — subtle horizontal `linear-gradient` on glass top
  edges to fake light.
- Dark base, mid-pastel aurora (cyan / magenta / orange), white
  glass surfaces.
- Slow drift on the aurora (32-60s) — never fast, never repeats
  visibly.

### `style.kinetic_typography_editorial` *(editorial, portfolio, story)*

Text IS the design. Apple landing-page tier.

- Hero h1 at `clamp(80-200px)`, edge-to-edge, line-height 0.92.
- Variable font with scroll-driven `wght` modulation (700 → 300
  as user scrolls).
- Letter-by-letter SVG path-draw on first paint.
- Marquee scroll on tagline tickers.
- Neo-serif × monospace pairing required.
- One sentence per scroll section — text revealed word by word
  on viewport entry.

### `style.dark_first_oled` *(default for everything 2026)*

True `#000000` background. OLED-friendly. Default starting point
unless brief explicitly demands light.

- See "Dark-First (#000000)" earlier in this doc. Combine with any
  other style.

### `style.neon_cyber_minimal` *(hacker, security, web3)*

Refined version of the toxic-neon-on-grey trend.

- Pure obsidian + ONE acid color (electric mint / cyan / chartreuse).
- Mono-everywhere typography, no sans pairing.
- ASCII-art accents (boxes drawn with U+2500 dashes, not images).
- Scan-line overlay (`repeating-linear-gradient` at 0.5deg, 4px lines).
- Terminal panel UI everywhere — even non-terminal content lives in
  macOS-chrome panels.

### `style.editorial_neoserif` *(media, journalism, books)*

Magazine-tier editorial. Whitespace as material.

- Neo-serif (Fraunces, Playfair, IBM Plex Serif) for ALL headlines.
- Generous line-height (1.6+ on body), narrow column (max 60ch).
- Pull-quotes at 4-6× body size with hairline rules.
- Two-column or asymmetric layout. NEVER 3-equal column.
- B&W photography only, no color photography unless intentional.
- Color reserved for the single accent — drop cap, link underline.

### `style.industrial_motion` *(automotive, hardware, fashion)*

For brands like Tesla, BMW, Bugatti, Nike. Cinematic precision.

- Full-bleed video / hero image.
- Type stacked at the bottom-left in a thin display sans (Helvetica
  Neue ultra-thin, Geist 100 weight).
- Slow horizontal scroll between scenes, or scroll-driven camera.
- Hairline icons (Lucide stroke-only at 1px, not 2px).
- Aggressive negative space, almost broadcast-tier.

---

## The 4 named layout patterns

### `layout.bento_dashboard_v1`

Modular bento grid. Apple-product-page style.

- Max **6-8 cards per viewport**.
- Card priorities by business goal: ONE hero cell (2x2), TWO
  medium cells (2x1), THREE small cells (1x1). Never 6 equal.
- Each card has its own micro-feature — interactive demo, animated
  number, sparkline, etc. Static cards = wasted space.
- Hover = subtle scale + cursor-following glow.
- 1px border between cells (use `gap: 1px; background: var(--border)`).

```css
.bento {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  grid-template-rows: 280px 280px;
  gap: 1px;
  background: var(--border);
}
.bento > :nth-child(1) { grid-column: span 2; grid-row: span 2; } /* hero 2x2 */
.bento > :nth-child(2) { grid-column: span 2; }                    /* med 2x1 */
.bento > :nth-child(3) { grid-column: span 2; }                    /* med 2x1 */
.bento > :nth-child(4),
.bento > :nth-child(5),
.bento > :nth-child(6) { grid-column: span 1; }                    /* small 1x1 */
```

### `layout.split_screen_diagonal`

Two-column with diagonal divider, one-page premium feel.

- 50/50 vertical split with `clip-path: polygon(0 0, 60% 0, 40% 100%, 0 100%)`
- Left side: brand statement, dark
- Right side: product demo or video, light
- Animated on scroll — divider angle changes from 70° to 90°.

### `layout.asymmetric_hero`

Default for any luxe site (replaces centered stack).

- Headline floats LEFT, terminal/visual floats RIGHT.
- ONE element BREAKS the gutter (CTA overlapping both columns,
  scroll indicator off-center, image bleeding into headline column).
- The break is the design move.

### `layout.scrollytelling_narrative`

One-page story. Each scroll section reveals new text + visual,
synchronized.

- Sticky-position visual on right, text scrolls on left.
- IntersectionObserver triggers state changes on the visual.
- Always a progress indicator (top bar OR side dots).
- Maximum 5-7 sections — longer becomes tedious.

---

## The 4 named motion patterns

### `motion.micro_interactions_pack`

Library rules — apply to EVERY interactive element.

- Duration: **150-300ms**, default 220ms.
- Easing: `cubic-bezier(0.22, 1, 0.36, 1)` for entrances,
  `cubic-bezier(0.65, 0, 0.35, 1)` for exits. NEVER `ease`.
- Every hover = state change (color shift, scale, translate, glow).
  No random wobble or pulsing without reason.
- No full-screen transitions that block users.
- Focus state must be visible — 2px outline at accent color, 3px offset.
- Loading states: skeleton shimmer, NOT spinner.
- Form feedback inline, not toast (toast for system events only).

### `motion.scrollytelling_narrative`

See layout pattern. Pair with text reveal.

- Word-by-word fade-in with 60ms stagger on viewport entry.
- Horizontal lock — sticky text region holds while user scrolls
  through the visual states.
- Always anchor (heading or progress dot) so user doesn't get lost.

### `motion.3d_hero_lightweight`

WebGL/Three.js — but used CHEAPLY.

- **Max 1 WebGL canvas per page.** Hero only.
- 3D element MUST relate to product (rotating product model, animated
  data orb, geographic globe). NEVER generic blob spinning.
- Polygon budget: < 50k for hero, < 10k for cards.
- Lazy-load `three.module.js` — don't bundle into main JS.
- Static `<img>` fallback for browsers without WebGL.
- **Always pause when tab is hidden** (`document.visibilityState`).

### `motion.kinetic_typography`

See `style.kinetic_typography_editorial`.

- Variable font scroll modulation (wght / wdth axes).
- Letter-by-letter SVG draw on first paint.
- Marquee tickers ≤ 3 per page.
- Word-by-word reveal on intersection.

---

## The 2 named UX patterns

### `ux.dynamic_layouts_v1` *(adaptive interfaces)*

Component blocks reorder based on user signal.

- Module types: `promo`, `education`, `power_user_tools`,
  `social_proof`, `trust_signals`.
- Each module has a `priority` integer the engine reorders by.
- For new visitor: `social_proof + education + promo`.
- For returning user: `power_user_tools + promo + education`.
- For high-intent (clicked CTA before): `promo + trust_signals`.
- Visual consistency stays — only ORDER changes.

### `ux.adaptive_intent_routing` *(content per traffic source)*

Detect referrer/UTM and serve different hero copy.

- Twitter/X traffic → casual, emoji-heavy hero.
- LinkedIn traffic → enterprise framing, ROI numbers.
- Direct/SEO → balanced default.
- Implementation: small JS that reads `document.referrer` + URL
  params, sets `data-source="..."` on `<body>`, CSS swaps copy via
  `[data-source="x"] .hero h1::after { content: "..." }` OR JS
  swaps innerText of pre-defined targets.

---

## The 2 named system skills

### `system.design_tokens_generator`

Given style choice, generate complete tokens.

- Outputs a CSS `:root` block with every token the rest of the
  site references.
- Required tokens: bg-0/1/2, fg-0/1/2/3, accent, accent-glow,
  border, grid, radius scale (only `--r-0 0px` and `--r-pill 999px`
  for tactile brutalism; full 4/8/12/16 for glassmorphism), spacing
  scale (4-96px ladder), motion easing curves.
- For brand-specific work: pull from `docs/design/brands/<name>/brand-style.md`
  VERBATIM — those are professionally extracted tokens.
- Forbid components from hardcoding values outside this block. Audit
  with regex `(?<!var\()(#[0-9a-fA-F]{3,8}|rgba?\([^)]+\))` on
  built CSS.

### `system.design_principles_compliance`

Run the 20 principles from `docs/design/principles/design-principles.md`
as a final check.

Concrete numeric checks:
- Whitespace ratio ≥ 40% (≥60% on hero) — count colored pixels.
- Text contrast ≥ 4.5:1 body, ≥ 3:1 large text.
- Type scale uses ONE ratio (1.25/1.333/1.414/1.5/1.618).
- ≤ 4 type sizes per page section.
- Body ≥ 17px on screen, ≥ 24px for projected/slide use.
- Line-height 1.4-1.6 body, 1.05-1.2 display.
- Line length ≤ 60 characters body.
- 60-30-10 color split (60 neutral + 30 secondary + 10 accent).
- ONE accent per section (multiple = none).
- 8-pt spacing grid (4-pt allowed for icon-tight work).
- F-pattern: headline + key visual top-left to top-right.

---

## The 2 named audit skills

### `audit.performance_2026`

After generation, walk the component tree and propose:

1. JS animations → CSS where possible (`transform` + `opacity` only,
   GPU-accelerated, never layout properties).
2. Reduce blur/shadow filters — they kill rendering on mobile
   (each blur is a paint pass).
3. Replace any `<img>` over 100KB with WebP or AVIF.
4. Check for hidden network — third-party scripts, fonts not
   subset, video preloads.
5. Lighthouse target: ≥95 LCP/CLS/INP.
6. Carbon footprint: ≤0.5g CO₂ per visit (websitecarbon.com).
7. Semantic HTML check — count `<div>` vs semantic tags. If `<div>`
   ratio > 60%, refactor.
8. Machine Experience: H1-H6 hierarchy correct, ARIA labels on
   interactive elements, structured data (JSON-LD) on key sections.

### `audit.accessibility_glass_v1`

Specific to glassmorphism + neo-brutal styles.

1. Every glass card body text contrast ≥ 4.5:1 against the
   *underlying* background (not just the glass tint).
2. Focus rings visible on all interactive elements — 2px outline
   at accent color, 3px offset.
3. No interactive element below 44×44px touch target.
4. Keyboard navigation works — Tab through every link/button,
   visible state at each step.
5. Reduced-motion media query disables ALL kinetic animations.
6. `aria-label` on icon-only buttons.
7. Form labels visible (not just placeholder).
8. Heading hierarchy correct (no h3 before h2).
9. Skip-to-content link in nav.
10. Alt text on every meaningful image.

---

# Part 3 — Workflow (from garden-skills web-design-engineer)

For ANY luxe build, follow this 6-step workflow strictly.

## Step 1 — Understand the requirements

Don't fire 20 questions. Decide based on context:

| Scenario | Ask? |
|---|---|
| "Make a landing page" (no PRD, no audience) | YES — audience, tone, brand, variants |
| "Build a clone of <URL> better" | NO — fetch the URL, extract patterns, propose |
| "Use this PRD to build…" | NO — PRD has the info |
| "Recreate this Figma" | NO — read the design tokens directly |
| "Design onboarding for my app" | YES — users, flows, brand, key moments |

Probe areas (pick as needed):
- Product context: what / users / existing system / competitors
- Output type: landing / dashboard / prototype / slide deck — fidelity?
- Variation dimensions: layout / color / interaction / copy?
- Constraints: responsive / dark-light / accessibility / fixed dimensions?

## Step 2 — Gather design context (priority order)

1. **User-provided resources** (screenshots, Figma, codebase, UI Kit)
   → read thoroughly, extract tokens.
2. **Existing pages of user's product** → ask if you can review them.
3. **Industry best practices** → ask which brands/products to reference.
4. **From scratch** → tell user "no reference may impact final quality"
   AND establish a temp system using `docs/design/brands/<name>/brand-style.md`.

> **Code ≫ Screenshots** — if you have both, invest effort in reading
> source code, not guessing from screenshots.

## Step 3 — Declare design system in Markdown BEFORE coding

```
Design Decisions:
- Color palette:    [primary / secondary / neutral / accent — hex codes]
- Typography:       [heading font / body font / mono font + scale ratio]
- Spacing system:   [base unit and multiples]
- Border-radius:    [strategy: 0px tactile / 8-16px glass / 24-40px clay]
- Shadow hierarchy: [none / inset only / 5-level elevation]
- Motion style:     [easing curves / duration ranges / triggers]
- Pattern picks:    [style.X, layout.Y, motion.Z from playbook]
```

Wait for user OK before proceeding.

## Step 4 — Show v0 draft EARLY

Don't hold back a perfect-v1. Ship a placeholder skeleton:
- Core structure + tokens + module placeholders (`[image]`, `[icon]`)
- Explicit list of design assumptions
- NOT: content details, full component library, all states, motion

A v0 with assumptions beats a "perfect v1" 3x slower. If direction
is wrong, you only redo 30 minutes of work.

## Step 5 — Full build

Follow declared system + patterns. If a major decision arises mid-build,
PAUSE and confirm. Don't silently push through.

## Step 6 — Verification (pre-delivery checklist)

Run `audit.performance_2026` AND `audit.accessibility_glass_v1` AND
the 20-principles compliance check. Fix everything that fails before
shipping.

---

# Part 4 — Brand library reference (`docs/design/brands/`)

73 brand DESIGN.md files. Each contains:
- Color tokens (primary, on-primary, ink scales, surface scales,
  hairline, semantic-success/error)
- Typography scale (12-15 named sizes with font-family, font-size,
  weight, line-height, letter-spacing)
- Border-radius scale
- Voice / tone notes

Quick reference table:

| Brand | Style match |
|---|---|
| `linear.app` | tactile_brutalism + dark_first |
| `apple` | aurora_liquid_glass + kinetic_typography |
| `stripe` | glassmorphism_saas_v2 + asymmetric_hero |
| `vercel` | tactile_brutalism + dark_first |
| `cursor` | tactile_brutalism + neon_cyber |
| `notion` | claymorphism (icons) + glassmorphism (cards) |
| `figma` | playful + bento |
| `tesla` | industrial_motion |
| `bmw`, `bmw-m`, `ferrari`, `lamborghini`, `bugatti` | industrial_motion |
| `nike` | industrial_motion + kinetic_typography |
| `spotify` | dark_first + claymorphism (album art) |
| `starbucks` | editorial_neoserif |
| `webflow` | bento + asymmetric_hero |
| `framer` | aurora_liquid_glass |
| `runwayml`, `glaido`, `minimax` | aurora + 3d_hero_lightweight |

When the brief mentions a brand name OR an industry, look up the
matching brand file and inject its tokens into the architect's
`## Color palette` and designer's `## Color tokens` sections
VERBATIM. Don't paraphrase the hex codes.

---

# Part 5 — How to use this in CG specs

For every architect/designer/engineer prompt:

1. **Architect prompt** — at the top of the prompt, include:
   ```
   ## Pattern selections (REQUIRED — pick from docs/LUXE-DESIGN-PLAYBOOK.md)
   - Visual style: <style.X>
   - Layout: <layout.Y>
   - Motion: <motion.Z>
   - Brand reference: <docs/design/brands/<name>/brand-style.md> (use tokens VERBATIM)
   ```

2. **Designer prompt** — append the matching pattern's "STRICT DO-NOTs"
   from this playbook + the brand's color/type tokens.

3. **Engineer prompt** — append the 12-point checklist + the audit
   triggers (`audit.performance_2026` + `audit.accessibility_glass_v1`)
   with "RUN BEFORE SUBMITTING."

4. **After build** — run the principles compliance check on the
   generated CSS. Reject if any of the 20 numeric thresholds fails.
