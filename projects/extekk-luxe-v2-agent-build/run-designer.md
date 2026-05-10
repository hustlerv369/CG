## Logo
```xml
<svg viewBox="0 0 
320 80" xmlns="http://www.w3.org/2000/svg">
  <!-- Stylized Terminal Cursor Accent -->
  <path d="M 10 25 L 10 55 L 25 55 L 25 
50 L 15 50 L 15 30 L 25 30 L 25 25 Z" fill="#FFFFFF"/>
  <path d="M 30 55 L 42 55 L 42 50 L 
35 50 L 35 30 L 42 30 L 42 25 L 30 25 Z" fill="#FFFFFF" transform="translate(5, 0)"/>

  <!-- Wordmark 'EXTEKK' -->
  <text x="7
5" y="58" font-family="monospace" font-size="42" font-weight="bold" fill="#FFFFFF" letter-spacing="-2">
    EXTEKK
  </text>
</svg>
```

## Color tokens
```css
:root {
  /*
 BACKGROUND */
  --bg-0: #000000;
  --bg-1: #0a0a0a;
  --bg-2: #141414;

  /* FOREGROUND */
  --fg-0: rgba(255
, 255, 255, 1);
  --fg-1: rgba(255, 255, 255, 0.7);
  --fg-2: rgba(255, 255, 255
, 0.45);
  --fg-3: rgba(255, 255, 255, 0.2);

  /* ACCENTS */
  --accent: #00FF94;
  --accent-glow: rgba(0,
 255, 148, 0.6);
  --alert: #FF3B5C;

  /* UI */
  --border: rgba(255, 255, 255, 0.08);
  --grid: rgba(0
, 255, 148, 0.04);

  /* RADIUS */
  --r-0: 0px;
  --r-pill: 999px;

  /* SPACING */
  --s-1: 4px;

  --s-2: 8px;
  --s-3: 16px;
  --s-4: 24px;
  --s-5: 32px;
  --s-6: 64px;
  --s-
7: 96px;
}
```

## Typography
```css
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,100..900&family=JetBrains+Mono
:wght@100..800&display=swap');

h1 {
  font-family: 'Fraunces', serif;
  font-size: clamp(72px, 11vw, 160px);
  line-height: 0.92;

  letter-spacing: -0.04em;
  font-weight: 600;
  font-optical-sizing: auto;
  font-variation-settings: "SOFT" 0;
}

h2 {
  font-family: 'Fraunces
', serif;
  font-size: clamp(40px, 5vw, 72px);
  line-height: 1.1;
  letter-spacing: -0.02em;
  font-weight: 500;
}

h3 {

  font-family: 'Fraunces', serif;
  font-size: 24px;
  line-height: 1.2;
  letter-spacing: -0.01em;
  font-weight: 500;
}

body {
  font-
family: 'Fraunces', serif;
  font-size: 17px;
  line-height: 1.6;
  font-weight: 400;
  font-optical-sizing: auto;
  font-variation-settings: "SOFT" 
100;
}

.mono {
  font-family: 'JetBrains Mono', monospace;
  font-size: 14px;
  line-height: 1.5;
  font-weight: 400;
}

.micro {
  
font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
```

## Layout sketches — three states

**ASYMMETRIC HERO**
The
 initial viewport establishes the brand's core tension: editorial confidence meets cold, hard execution. A massive, razor-sharp headline dominates the left, while a live terminal on the right proves the claims in real-time, all bathed in an atmospheric, non-decorative gradient haze.

```xml
<svg viewBox="0 0
 1280 720" xmlns="http://www.w3.org/2000/svg" font-family="sans-serif">
  <defs>
    <filter id="blur-1" x="-100%" y="-100%" width="3
00%" height="300%">
      <feGaussianBlur stdDeviation="140" />
    </filter>
    <filter id="blur-2" x="-100%" y="-100%" width="300%" height="300%">
      <feGaussianBlur
 stdDeviation="120" />
    </filter>
    <pattern id="noise" patternUnits="userSpaceOnUse" width="100" height="100">
        <image href="data:image/svg+xml,%3Csvg viewBox='0 0 100
 100' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch
'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E" x="0" y="0" width="1
00" height="100" opacity="0.2"/>
    </pattern>
  </defs>

  <rect width="1280" height="720" fill="#000000"/>
  <circle cx="950" cy="3
60" r="300" fill="#00FF94" opacity="0.15" filter="url(#blur-1)"/>
  <circle cx="300" cy="600" r="250" fill="#FFFFFF" opacity="0.05
" filter="url(#blur-2)"/>
  <rect width="1280" height="720" fill="url(#noise)" style="mix-blend-mode: overlay; opacity: 0.02;"/>

  <!-- Status Pill -->
  <rect x="
80" y="80" width="370" height="36" rx="18" ry="18" fill="rgba(255,255,255,0.05)" />
  <rect x="80" y="80"
 width="370" height="36" rx="18" ry="18" stroke="rgba(255,255,255,0.1)" stroke-width="1"/>
  <circle cx="100" cy="98" r="
4" fill="#00FF94"/>
  <text x="118" y="103" fill="rgba(255,255,255,0.7)" font-family="'JetBrains Mono', monospace" font-size="12" letter-spacing
="0.5">ALL SYSTEMS NOMINAL · 99.99% UPTIME</text>

  <!-- Headline -->
  <text x="80" y="280" fill="#FFFFFF" font-family="'Fraunces', serif" font-size="120" font-
weight="bold" letter-spacing="-6">Your server</text>
  <text x="80" y="380" fill="#FFFFFF" font-family="'Fraunces', serif" font-size="120" font-weight="bold" letter-spacing="-6">can
't <tspan fill="#00FF94">die</tspan> anymore.</text>
  
  <!-- Terminal Panel -->
  <rect x="780" y="150" width="420" height="420" fill="#0a0a
0a" stroke="rgba(255,255,255,0.08)" stroke-width="1"/>
  <rect x="780" y="150" width="420" height="30" fill="#14141
4"/>
  <circle cx="796" cy="165" r="6" fill="#FF3B5C"/>
  <circle cx="820" cy="165" r="6" fill="#FFC107"/>
  <circle cx="844
" cy="165" r="6" fill="#4CAF50"/>
  
  <text x="800" y="210" fill="rgba(255,255,255,0.7)" font-family="'JetBrains Mono', monospace" font
-size="14">
    $ extekk restore
  </text>
  <text x="800" y="240" fill="#00FF94" font-family="'JetBrains Mono', monospace" font-size="14">
    <tspan fill="#
FFFFFF" fill-opacity="0.4">[14:02:11]</tspan> ✓ snapshot loaded
  </text>
   <text x="800" y="260" fill="#00FF94" font-family="'JetBrains Mono', monospace" font-
size="14">
    <tspan fill="#FFFFFF" fill-opacity="0.4">[14:02:11]</tspan> ✓ 47 channels redeployed
  </text>
  <text x="800" y="280" fill="#00FF
94" font-family="'JetBrains Mono', monospace" font-size="14">
    <tspan fill="#FFFFFF" fill-opacity="0.4">[14:02:12]</tspan> ✓ roles + perms restored
  </text>
  <text
 x="800" y="300" fill="#00FF94" font-family="'JetBrains Mono', monospace" font-size="14">
    <tspan fill="#FFFFFF" fill-opacity="0.4">[14:02:12]</t
span> ✓ 11,608 members rejoined
  </text>
  <text x="800" y="330" fill="rgba(255,255,255,0.7)" font-family="'JetBrains Mono', monospace" font-size="
14">
    done in 0.97s<tspan fill="#00FF94" font-weight="bold">▌</tspan>
  </text>
</svg>
```

**WATCH IT WORK**
This section visualizes the speed and surgical precision of a
 server rollback. By breaking the grid and offsetting the middle card, the layout communicates a sense of controlled chaos and highlights the critical "lockdown" phase as a distinct, pivotal moment.

```xml
<svg viewBox="0 0 1280 720" xmlns="http://www.w3.
org/2000/svg" font-family="sans-serif">
  <rect width="1280" height="720" fill="#000000"/>
  
  <!-- Card 1: Detect -->
  <rect x="150" y
="290" width="280" height="140" fill="#0a0a0a" stroke="#222" stroke-width="1"/>
  <text x="170" y="320" fill="#FF3B5C" font-family="'
JetBrains Mono', monospace" font-size="12">DETECT</text>
  <text x="170" y="360" fill="rgba(255,255,255,0.7)" font-size="16" line-height="1
.4">
    <tspan x="170" dy="0">Sentinel flags mass-channel</tspan>
    <tspan x="170" dy="20">delete from compromised</tspan>
    <tspan x="170" dy="20">admin
 token.</tspan>
  </text>
  <rect x="330" y="300" width="80" height="24" rx="12" ry="12" fill="#141414"/>
  <text x="350"
 y="317" fill="rgba(255,255,255,0.7)" font-family="'JetBrains Mono', monospace" font-size="12">0.000s</text>

  <!-- Arrow 1 -->
  <path d="
M 440 360 L 500 360" stroke="#444" stroke-width="1" stroke-dasharray="4 4"/>
  
  <!-- Card 2: Lockdown (Off-center) -->
  <rect x="510"
 y="190" width="280" height="140" fill="#0a0a0a" stroke="#222" stroke-width="1"/>
  <text x="530" y="220" fill="#00FF94" font-family="'
JetBrains Mono', monospace" font-size="12">LOCKDOWN</text>
  <text x="530" y="260" fill="rgba(255,255,255,0.7)" font-size="16" line-height
="1.4">
    <tspan x="530" dy="0">Permissions frozen, raiders</tspan>
    <tspan x="530" dy="20">revoked, audit-log</tspan>
    <tspan x="53
0" dy="20">snapshot sealed.</tspan>
  </text>
  <rect x="690" y="200" width="80" height="24" rx="12" ry="12" fill="#141414"/>
  <
text x="710" y="217" fill="rgba(255,255,255,0.7)" font-family="'JetBrains Mono', monospace" font-size="12">0.420s</text>

  <!-- Arrow 
2 -->
  <path d="M 800 260 C 830 260, 830 420, 860 420" stroke="#444" stroke-width="1" fill="none" stroke-dasharray="
4 4"/>
  
  <!-- Card 3: Restore -->
  <rect x="870" y="350" width="280" height="140" fill="#0a0a0a" stroke="#222" stroke-width="1"/>

  <text x="890" y="380" fill="#00FF94" font-family="'JetBrains Mono', monospace" font-size="12">RESTORE</text>
  <text x="890" y="420" fill="rgba
(255,255,255,0.7)" font-size="16" line-height="1.4">
    <tspan x="890" dy="0">Channels, roles, members,</tspan>
    <tspan x="8
90" dy="20">and vouch ledger are</tspan>
    <tspan x="890" dy="20">redeployed.</tspan>
  </text>
  <rect x="1050" y="360" width="80
" height="24" rx="12" ry="12" fill="#141414"/>
  <text x="1070" y="377" fill="rgba(255,255,255,0.7)" font-
family="'JetBrains Mono', monospace" font-size="12">1.000s</text>
</svg>
```

**BENTO FEATURE GRID**
This is a high-density, high-value information layout that rejects cookie-cutter feature grids. The asymmetric sizing establishes a clear hierarchy of
 importance—Sentinel as the flagship—while the hard-edged, gapless structure feels architectural and robust.

```xml
<svg viewBox="0 0 1280 720" xmlns="http://www.w3.org/2000/svg" font-family="
sans-serif">
  <rect width="1280" height="720" fill="#000000"/>
  <g transform="translate(100, 100)" stroke="rgba(255,255,255,0.08
)" stroke-width="1" fill="none">
    
    <!-- Large Hero Cell -->
    <rect x="0" y="0" width="600" height="250" fill="#0a0a0a"/>
    <text x="30" y="
50" fill="#FFFFFF" font-size="24" font-family="'Fraunces', serif" font-weight="bold">EXTEKK SENTINEL</text>
    <text x="30" y="80" fill="rgba(255,255,
255,0.7)" font-size="16">AI patrols every message 24/7, deletes phishing mid-keystroke, mutes spammers before mods wake up.</text>

    <!-- Medium Cell (Restore) -->
    <rect x="600" y="
0" width="480" height="250" fill="#0a0a0a"/>
    <text x="630" y="50" fill="#FFFFFF" font-size="24" font-family="'Fraunces', serif" font-weight="bold">RESTORE
</text>
    <text x="630" y="80" fill="rgba(255,255,255,0.7)" font-size="16">OAuth2 member + structure rollback. One command, full server back.</text>

    <!--
 Medium Cell (Lockdown) -->
    <rect x="0" y="250" width="300" height="270" fill="#0a0a0a"/>
    <text x="30" y="290" fill="#FFFFFF" font-size="2
4" font-family="'Fraunces', serif" font-weight="bold">LOCKDOWN</text>
    <text x="30" y="320" fill="rgba(255,255,255,0.7)" font-size="16
">Aesthetic server builder doubles as panic button. Locks every channel in 200ms.</text>

    <!-- Small Cell (Vouch Vault) -->
    <rect x="300" y="250" width="480" height="135" fill="#0
a0a0a"/>
    <text x="330" y="290" fill="#FFFFFF" font-size="24" font-family="'Fraunces', serif" font-weight="bold">VOUCH VAULT</text>
    <text x="3
30" y="320" fill="rgba(255,255,255,0.7)" font-size="16">Universal sync for reputation, immune to wipes.</text>
    
    <!-- Small Cell (Tickets) -->
    <rect x="3
00" y="385" width="480" height="135" fill="#0a0a0a"/>
    <text x="330" y="425" fill="#FFFFFF" font-size="24" font-family="'Fraunces
', serif" font-weight="bold">TICKETS</text>
    <text x="330" y="455" fill="rgba(255,255,255,0.7)" font-size="16">Pro system with transcripts and role-routing
.</text>

    <!-- Small Cell (Blacklist) -->
    <rect x="780" y="250" width="300" height="270" fill="#0a0a0a"/>
    <text x="810" y="29
0" fill="#FFFFFF" font-size="24" font-family="'Fraunces', serif" font-weight="bold">BLACKLIST</text>
    <text x="810" y="320" fill="rgba(255,255,255
,0.7)" font-size="16">Global scammer database—480k flagged IDs, auto-banned on join.</text>
  </g>
</svg>
```

## Motion
- **Hero Terminal Typing:** `0.06s` per character,
 linear easing (`cubic-bezier(0, 0, 1, 1)`), simulating mechanical output.
- **Scroll-driven Font Modulation:** `wght` 700 to 300 from `scrollY: 0` to `window.innerHeight`, driven by a scroll listener, no
 fixed duration.
- **Blob Mesh Drift:** `32s` duration, `cubic-bezier(0.42, 0, 0.58, 1)` `infinite alternate`, applied to two pseudo-elements with `filter: blur(140px)`.
- **SVG Noise Translation
:** `600ms` duration, `cubic-bezier(0.42, 0, 0.58, 1)` `infinite alternate`, translating a `<pattern>` element `5px` on X and Y axes.
- **Number Counter Roll-up:** `1200ms
` duration, `cubic-bezier(0.22, 1, 0.36, 1)`, triggered once on viewport intersection.
- **Card Glow Follow:** No duration, `requestAnimationFrame` on `mousemove` to update CSS custom properties `--mx` and `--my`, with a `cubic-bezier
(0.25, 1, 0.5, 1)` transition on the gradient's position for smoothing.

## Mood
Confident, precise, and inevitable. The visual system of a premium utility that has already solved the problem before you knew you had it. This is hacker-couture:
 a machined, architectural aesthetic that makes security feel less like a defense and more like a law of physics.
