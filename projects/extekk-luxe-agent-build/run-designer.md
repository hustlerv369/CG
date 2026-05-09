## Logo
```xml
<svg viewBox='0 0 320 80' xmlns='http://www.w3.
org/2000/svg'>
  <defs>
    <style>
      .wordmark { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Geist", "Roboto", "Oxygen", "Ubuntu", "Cantarell", "Fira
 Sans", "Droid Sans", "Helvetica Neue", sans-serif; font-size: 56px; fill: white; font-weight: 500; letter-spacing: -0.02em; }
    </style>
  </defs>
  <path d='
M24 10 L10 24 L10 56 L24 70 L40 70 L54 56 L54 24 L40 10 Z M32 20 L44 20 L44
 30 L32 42 Z' fill='#7CFFB2'/>
  <text x='70' y='60' class='wordmark'>EXTEKK</text>
</svg>
```

## Color tokens
```css
:root {
  /* Palette
 */
  --bg-0: #080808;
  --bg-1: #111111;
  --bg-2: #1A1A1A;
  --fg-0: #FFFFFF;
  --fg-1: rgba(
255, 255, 255, 0.75);
  --fg-2: rgba(255, 255, 255, 0.45);
  --accent: #7CFFB2;
  --
accent-glow: rgba(124, 255, 178, 0.6);
  --discord: #5865F2;
  --alert: #FF4D5E;
  --border: rgba(255, 25
5, 255, 0.08);
  --grid: rgba(124, 255, 178, 0.04);

  /* Radius */
  --r-1: 4px;
  --r-2: 
8px;
  --r-3: 12px;
  --r-4: 16px;
  --r-pill: 999px;

  /* Spacing */
  --s-1: 4px;
  --s-2:
 8px;
  --s-3: 12px;
  --s-4: 16px;
  --s-5: 24px;
  --s-6: 48px;
  --s-7: 96px;

}
```

## Typography
```css
@import url('https://fonts.googleapis.com/css2?family=Geist+Sans:wght@400;500&family=Geist+Mono&display=swap');

:root {
  --font-body: '
Geist Sans', sans-serif;
  --font-mono: 'Geist Mono', monospace;
}

body {
  font-family: var(--font-body);
  font-size: 17px;
  line-height: 1.6;
  color
: var(--fg-1);
}

h1, h2, h3 {
  font-weight: 500;
  line-height: 1.2;
  letter-spacing: -0.02em;
  color: var(--fg-0);

}

h1 {
  font-size: clamp(3.5rem, 8vw, 7rem); /* 56px -> 112px */
}

h2 {
  font-size: 2.25rem; /* 36px */

}

h3 {
  font-size: 1.5rem; /* 24px */
}

.mono {
  font-family: var(--font-mono);
  font-size: 14px;
  line-height: 1.5;

  color: var(--fg-1);
}

.micro {
  font-size: 12px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--
fg-2);
}
```

## Layout sketches — three states

**HERO**
The hero introduces the core promise with maximum impact. A stark headline is flanked by clear calls-to-action and a live terminal feed, creating an atmosphere of calm, lethal competence against a subtle grid backdrop.

```xml

<svg viewBox="0 0 1280 720" xmlns="http://www.w3.org/2000/svg">
  <style>
    .bg { fill: #080808; }
    .grid { stroke: rgba(1
24, 255, 178, 0.04); stroke-width: 1; }
    .h1 { font: 500 80px 'Geist Sans', sans-serif; fill: white; letter-spacing: -0.02em;
 }
    .sub { font: 400 22px 'Geist Sans', sans-serif; fill: rgba(255,255,255,0.75); }
    .pill-text { font: 500 12px
 'Geist Sans', sans-serif; fill: rgba(255,255,255,0.45); text-transform: uppercase; letter-spacing: 0.05em; }
    .btn-p-txt { font: 500 1
6px 'Geist Sans', sans-serif; fill: white; }
    .btn-s-txt { font: 500 16px 'Geist Sans', sans-serif; fill: #FFFFFF; }
    .term-bg { fill: rgba(22, 22
, 22, 0.5); stroke: rgba(255,255,255,0.08); stroke-width: 1; }
    .term-txt { font: 400 14px 'Geist Mono', monospace; fill: rgba
(255,255,255,0.75); }
    .term-prompt { fill: #7CFFB2; }
  </style>
  <rect width="1280" height="720" class="bg"/>
  <defs
>
    <pattern id="gridPattern" width="40" height="40" patternUnits="userSpaceOnUse">
      <path d="M 40 0 L 0 0 0 40" fill="none" class="grid"/>
    </pattern>

  </defs>
  <rect width="1280" height="720" fill="url(#gridPattern)"/>

  <!-- Left Content -->
  <rect x="120" y="180" width="10" height="10" rx="5
" fill="#7CFFB2"/>
  <text x="138" y="189" class="pill-text">ALL SYSTEMS NOMINAL · 99.99% UPTIME</text>
  <text x="120" y="280" class
="h1">Your server, restored</text>
  <text x="120" y="360" class="h1">in one second.</text>
  <text x="120" y="430" class="sub" width="500">

    <tspan x="120" dy="0">EXTEKK is the security bot that rebuilds nuked Discord</tspan>
    <tspan x="120" dy="1.4em">servers and kills scammers before they post.</tspan>
  </text>
  
<rect x="120" y="500" width="180" height="52" rx="8" fill="#5865F2"/>
  <text x="156" y="533" class="btn-p-txt">Add to
 Discord</text>
  <rect x="320" y="500" width="160" height="52" rx="8" fill="transparent" stroke="rgba(255,255,255,0.2)" stroke-width="1"/>

  <text x="354" y="533" class="btn-s-txt">Watch demo</text>

  <!-- Right Terminal -->
  <rect x="720" y="160" width="440" height="400" rx="12"
 class="term-bg"/>
  <text class="term-txt" x="740" y="200">
    <tspan fill="#7CFFB2">$</tspan><tspan dx="5">extekk restore --snapshot=latest</tspan>

    <tspan x="740" dy="1.8em"><tspan class="term-prompt">[03:47:13]</tspan> ✓ snapshot loaded · 247 channels, 84 roles</tspan>
    <tspan x="740" dy
="1.8em"><tspan class="term-prompt">[03:47:13]</tspan> ✓ permissions reconciled</tspan>
    <tspan x="740" dy="1.8em"><tspan class="term-prompt">[03:47
:14]</tspan> ✓ vouches resynced · 11,832 entries</tspan>
    <tspan x="740" dy="1.8em"><tspan class="term-prompt">[03:47:14]</tspan>
 ✓ rebuild complete · 1.04s</tspan>
    <tspan x="740" dy="3.6em"><tspan fill="#7CFFB2">$</tspan><tspan dx="5">extekk lockdown --tier=critical</tspan>
    <
tspan x="740" dy="1.8em"><tspan class="term-prompt">[03:47:15]</tspan> ⚡ tier 3 lockdown engaged</tspan>
    <tspan x="740" dy="1.8em"><
tspan class="term-prompt">[03:47:15]</tspan> ✓ 312 members · read-only</tspan>
    <tspan x="740" dy="1.8em"><tspan class="term-prompt">[03:47:
15]</tspan> ✓ 4 admin tokens revoked · 0.31s<tspan fill="#7CFFB2" dy="1.5em">▋</tspan></tspan>
  </text>
</svg>
```

**WATCH-IT-WORK**
This
 cinematic sequence visualizes the speed and efficiency of the restore process. It breaks down a high-stakes event into three clear, digestible steps, turning a moment of chaos into a demonstration of control.

```xml
<svg viewBox="0 0 1280 720" xmlns="http://www.
w3.org/2000/svg">
  <style>
    .bg { fill: #080808; }
    .card { fill: #111111; stroke: rgba(255,255,255,
0.08); stroke-width: 1; }
    .title { font: 500 16px 'Geist Sans', sans-serif; letter-spacing: 0.05em; text-transform: uppercase; }
    .desc { font: 400
 15px 'Geist Sans', sans-serif; fill: rgba(255,255,255,0.75); }
    .pill { font: 500 14px 'Geist Mono', monospace; fill: #08080
8; }
    .arrow { fill: none; stroke: rgba(255,255,255,0.2); stroke-width: 1.5; }
  </style>
  <rect width="1280" height="720"
 class="bg"/>

  <!-- Step 1: Attack -->
  <rect x="120" y="280" width="300" height="160" rx="12" class="card" style="stroke: #FF4D5E;"/>
  <rect x
="136" y="296" width="80" height="28" rx="14" fill="#FF4D5E" />
  <text x="153" y="316" class="pill">0.000s</text>

  <text x="136" y="356" class="title" fill="#FF4D5E">ATTACK DETECTED</text>
  <text class="desc" x="136" y="380">
    <tspan>Sentinel flags a compromised
</tspan>
    <tspan x="136" dy="1.4em">admin token. Channels drop.</tspan>
  </text>

  <!-- Arrow 1 -->
  <path class="arrow" d="M 440 360 L 4
80 360" />
  <path class="arrow" d="M 475 355 L 480 360 L 475 365" />

  <!-- Step 2: Restore -->
  <rect x="490" y
="280" width="300" height="160" rx="12" class="card"/>
  <rect x="506" y="296" width="80" height="28" rx="14" fill="#7CFFB2
" />
  <text x="523" y="316" class="pill">0.420s</text>
  <text x="506" y="356" class="title" fill="#7CFFB2">RESTORE INITIATED
</text>
  <text class="desc" x="506" y="380">
    <tspan>Snapshot loaded. Roles,</tspan>
    <tspan x="506" dy="1.4em">categories, perms queued.</tspan>
  
</text>

  <!-- Arrow 2 -->
  <path class="arrow" d="M 810 360 L 850 360" />
  <path class="arrow" d="M 845 355 L 850
 360 L 845 365" />
  
  <!-- Step 3: Rebuilt -->
  <rect x="860" y="280" width="300" height="160" rx="12" class="card"/>

  <rect x="876" y="296" width="80" height="28" rx="14" fill="#7CFFB2" />
  <text x="893" y="316" class="pill">1.00
0s</text>
  <text x="876" y="356" class="title" fill="#7CFFB2">SERVER REBUILT</text>
  <text class="desc" x="876" y="380">
    <t
span>Community is whole. Attacker</tspan>
    <tspan x="876" dy="1.4em">logged, blacklisted, gone.</tspan>
  </text>
</svg>
```

**PRICING**
The pricing section presents a clear, binary
 choice between a robust free tier and an all-in pro plan. The Pro card is visually emphasized with an accent border and a stronger call-to-action to guide the user's decision.

```xml
<svg viewBox="0 0 1280 720" xmlns="http://www
.w3.org/2000/svg">
  <style>
    .bg { fill: #080808; }
    .card-free { fill: #111111; stroke: rgba(255,255,2
55,0.08); }
    .card-pro { fill: #111111; stroke: #7CFFB2; }
    .title { font: 500 24px 'Geist Sans', sans-serif; fill: white; }

    .subtitle { font: 400 16px 'Geist Sans', sans-serif; fill: rgba(255,255,255,0.75); }
    .price { font: 500 16px 'Geist
 Sans', sans-serif; fill: #7CFFB2; }
    .feature { font: 400 15px 'Geist Sans', sans-serif; fill: rgba(255,255,255,0.75); }
    .check {
 fill: #7CFFB2; font-size: 20px; font-weight: bold; }
    .cross { fill: rgba(255,255,255,0.45); font-size: 20px; font-weight: bold; }

    .btn-free-txt { font: 500 15px 'Geist Sans', sans-serif; fill: white; }
    .btn-pro-txt { font: 500 15px 'Geist Sans', sans-serif; fill: #
080808; }
  </style>
  <rect width="1280" height="720" class="bg"/>

  <!-- Free Card -->
  <rect x="260" y="150" width="360" height="
420" rx="12" class="card-free" stroke-width="1"/>
  <text x="290" y="200" class="title">FREE</text>
  <text x="290" y="230" class="subtitle">
Everything you need to survive.</text>
  <path d="M 290 260 H 590" stroke="rgba(255,255,255,0.08)" stroke-width="1"/>
  <text y="300" class
="check"><tspan x="290">✓</tspan></text><text y="300" class="feature"><tspan x="320">OAuth Member &amp; Server Restore</tspan></text>
  <text y="330" class="check"><
tspan x="290">✓</tspan></text><text y="330" class="feature"><tspan x="320">Aesthetic Server Builder</tspan></text>
  <text y="360" class="check"><tspan x="29
0">✓</tspan></text><text y="360" class="feature"><tspan x="320">Vouch Vault (community)</tspan></text>
  <text y="390" class="check"><tspan x="290">✓</t
span></text><text y="390" class="feature"><tspan x="320">Global Scammer Blacklist (read)</tspan></text>
  <text y="420" class="cross"><tspan x="290">✗</tspan></text
><text y="420" class="feature"><tspan x="320">Sentinel AI auto-mod</tspan></text>
  <text y="450" class="cross"><tspan x="290">✗</tspan></text><text y="4
50" class="feature"><tspan x="320">Pro Ticket System</tspan></text>
  <rect x="290" y="500" width="290" height="44" rx="8" fill="transparent" stroke="rgba(255
,255,255,0.2)" stroke-width="1"/>
  <text x="390" y="528" class="btn-free-txt">Add for free</text>

  <!-- Pro Card -->
  <rect x="660
" y="150" width="360" height="420" rx="12" class="card-pro" stroke-width="1.5"/>
  <text x="690" y="200" class="title">PRO</text>
  
<text x="750" y="200" class="price">$19/mo · 14-day free trial</text>
  <text x="690" y="230" class="subtitle">Everything. No exceptions.</text>
  <path d="
M 690 260 H 990" stroke="rgba(255,255,255,0.08)" stroke-width="1"/>
  <text y="300" class="check"><tspan x="690">
✓</tspan></text><text y="300" class="feature"><tspan x="720">Sentinel AI · 24/7 patrol</tspan></text>
  <text y="330" class="check"><tspan x="690">✓
</tspan></text><text y="330" class="feature"><tspan x="720">Pro Ticket System · encrypted</tspan></text>
  <text y="360" class="check"><tspan x="690">✓</tspan></text
><text y="360" class="feature"><tspan x="720">Sub-second restore SLA</tspan></text>
  <text y="390" class="check"><tspan x="690">✓</tspan></text><text y="3
90" class="feature"><tspan x="720">Cross-server reputation sync</tspan></text>
  <text y="420" class="check"><tspan x="690">✓</tspan></text><text y="420" class="
feature"><tspan x="720">Priority blacklist push</tspan></text>
  <text y="450" class="check"><tspan x="690">✓</tspan></text><text y="450" class="feature"><tspan x="7
20">24/7 white-glove support</tspan></text>
  <rect x="690" y="500" width="290" height="44" rx="8" fill="#7CFFB2"/>
  <text x="7
78" y="528" class="btn-pro-txt">Start free trial</text>
</svg>
```

## Motion
*   **hero terminal typing:** 0.06s per character, `steps(1, end)` (linear).
*   **hero grid pulse:**
 4s `ease-in-out` infinite, animating `opacity` from 1 to 0.7 and back.
*   **number counter roll-up:** 1.2s `cubic-bezier(0.22, 1, 0.36, 1)` on viewport entry
.
*   **feature card glow-on-hover:** 260ms `cubic-bezier(0.33, 1, 0.68, 1)` on a radial gradient or box-shadow.
*   **watch-it-work step transition:** 450ms
 `cubic-bezier(0.22, 1, 0.36, 1)` staggered by 150ms on card `transform` and `opacity`.
*   **alert pulse on breach indicator:** 1.2s `ease-in-out` infinite, pulsing the `fill
` or `box-shadow` of the red status element.

## Mood
Confident, premium, hacker-couture — the visual equivalent of a tailored bulletproof vest. It is surgical and refined, not noisy or choked with toxic-green neon. This is the calm lethality of apex predator software.
