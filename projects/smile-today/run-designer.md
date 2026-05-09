## Logo
```xml
<svg viewBox="0 0 240 240" xmlns="http://www.w3.org/2000/svg">
  
<rect width="240" height="240" fill="#ffffff"/>
  <text x="120" y="105" font-family="sans-serif" font-size="42" font-weight="400" text-anchor="middle" fill="#0a
0a0a">Smile</text>
  <text x="120" y="155" font-family="sans-serif" font-size="42" font-weight="700" text-anchor="middle" fill="#0a0a0a">Today</
text>
  <path d="M 85 172 Q 120 165, 155 172" stroke="#ff5a4e" stroke-width="4" fill="none" stroke-linecap="round"/>
</svg>

```

## Color tokens
```css
:root {
  /* Core Palette */
  --bg: #ffffff;
  --fg: #0a0a0a;
  --accent: #ff5a4e;

  /* Neutrals & Supporting */
  --muted: rgba
(10, 10, 10, 0.55);
  --border: rgba(10, 10, 10, 0.1);
  --shadow: rgba(10, 10, 10, 0.08
);

  /* Spacing Scale */
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 32px;

  --space-xxl: 64px;

  /* Radius Scale */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 16px;
  --radius-full: 9999px;

}
```

## Typography pairing
```css
/* Google Fonts Import */
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,300;9..144,400&family
=Inter:wght@400;600&display=swap');

/* Base & Scale */
html {
  font-size: 62.5%; /* 1rem = 10px */
}

body {
  font-family: 'Inter', sans-serif
;
  font-size: 1.6rem; /* 16px */
  line-height: 1.6;
  color: var(--fg);
  background-color: var(--bg);
}

h1, .font-display {
  font-family
: 'Fraunces', serif;
  font-optical-sizing: auto;
  font-weight: 400;
  font-size: clamp(3.2rem, 5vw + 1rem, 4.8rem); /* Responsive sizing */
  line-height: 
1.1;
  letter-spacing: -0.02em;
}

h2, .font-quote {
  font-family: 'Fraunces', serif;
  font-optical-sizing: auto;
  font-weight: 300;
  font-size
: 2rem; /* 20px */
  line-height: 1.4;
}

.font-micro {
  font-size: 1.2rem; /* 12px */
  text-transform: uppercase;
  letter-spacing: 0
.05em;
  font-weight: 600;
  color: var(--muted);
}
```

## Layout — three key states

**STATE: First-open**
Purpose: To introduce the app's purpose and request notification permission only on user interaction. It's
 a calm, single-action entry point.
```xml
<svg viewBox="0 0 800 500" xmlns="http://www.w3.org/2000/svg">
  <rect width="800" height="500" fill="#ffffff
"/>
  <style>
    .headline { font: 400 48px 'Fraunces', serif; fill: #0a0a0a; }
    .subline { font: 300 24px 'Fraunces', serif; fill:
 #0a0a0a; }
    .button { font: 600 18px 'Inter', sans-serif; fill: #ffffff; }
  </style>
  <text x="400" y="180" text-anchor="middle"
 class="headline">Smile at someone today.</text>
  <text x="400" y="230" text-anchor="middle" class="subline">A small kindness, every hour.</text>
  
  <rect x="250" y="300" width
="300" height="60" rx="30" fill="#ff5a4e"/>
  <text x="400" y="338" text-anchor="middle" class="button">Allow gentle reminders</text>
</svg>
```

**STATE
: Active**
Purpose: This is the main state, showing the time until the next reminder. The prominent button allows the user to log a "smile", which resets the timer and provides quiet positive reinforcement.
```xml
<svg viewBox="0 0 800 500" xmlns="
http://www.w3.org/2000/svg">
  <rect width="800" height="500" fill="#ffffff"/>
  <style>
    .micro-label { font: 600 12px 'Inter', sans-serif
; fill: #888; text-transform: uppercase; letter-spacing: 0.05em; }
    .timer { font: 400 96px 'Fraunces', serif; fill: #0a0a0a; }
    .quote { font: 
300 20px 'Fraunces', serif; fill: #0a0a0a; }
    .button-text { font: 600 18px 'Inter', sans-serif; fill: #ff5a4e; }
  </style>

  
  <!-- Top Right: Streak Counter -->
  <text x="760" y="40" text-anchor="end" class="micro-label">3 days of smiling</text>
  
  <!-- Center Content -->
  <text x="400" y="160
" text-anchor="middle" class="micro-label">Next smile in</text>
  <text x="400" y="250" text-anchor="middle" class="timer">59:12</text>
  <text x="400" y="31
0" text-anchor="middle" class="quote">Look up. Someone near you needs to be seen.</text>

  <!-- Main Action Button -->
  <circle cx="400" cy="410" r="50" fill="#ffffff" stroke="#eee" stroke-width
="2"/>
  <circle cx="400" cy="410" r="44" fill="#ff5a4e" fill-opacity="0.1"/>
  <text x="400" y="416" text-anchor="middle" class="button-text
">I smiled</text>

  <!-- Bottom Left: Settings -->
  <path d="M32 458 a4,4 0 0,1 4,-4 h16 a4,4 0 0,1 0,8 h-16 a4
,4 0 0,1 -4,-4 z m0 -10 a4,4 0 0,1 4,-4 h16 a4,4 0 0,1 0,8 h-16 a4,4 0 0,1 -
4,-4 z m0 -10 a4,4 0 0,1 4,-4 h16 a4,4 0 0,1 0,8 h-16 a4,4 0 0,1 -4,-4 z" fill="#ccc"/>
</svg
>
```

**STATE: Settings panel**
Purpose: Provides access to non-essential controls without cluttering the main interface. It allows users to adjust the app's behavior to fit their personal rhythm.
```xml
<svg viewBox="0 0 800 500" xmlns="http
://www.w3.org/2000/svg">
  <rect width="800" height="500" fill="#f0f0f0"/>
  <rect x="200" y="50" width="400" height="400
" rx="16" fill="#ffffff" stroke="#eee" stroke-width="1"/>
  <style>
    .label { font: 400 16px 'Inter', sans-serif; fill: #0a0a0a; }
    .value { font: 6
00 16px 'Inter', sans-serif; fill: #0a0a0a; }
    .reset { font: 400 14px 'Inter', sans-serif; fill: #ff5a4e; }
    .close { font: 
600 24px 'Inter', sans-serif; fill: #aaa; }
  </style>

  <!-- Close Button -->
  <text x="570" y="80" text-anchor="middle" class="close">×</text>
  
  <!--
 Interval Slider -->
  <text x="240" y="120" class="label">Remind me every</text>
  <text x="560" y="120" text-anchor="end" class="value">60 minutes</text>
  
<rect x="240" y="140" width="320" height="4" rx="2" fill="#eee"/>
  <rect x="240" y="140" width="80" height="4" rx="2" fill="#ff5a4
e"/>
  <circle cx="320" cy="142" r="8" fill="#ff5a4e" stroke="#fff" stroke-width="2"/>

  <!-- Toggles -->
  <line x1="240" y1="190" x2
="560" y2="190" stroke="#eee" stroke-width="1"/>
  <text x="240" y="225" class="label">Quiet until morning</text>
  <rect x="510" y="212" width="5
0" height="26" rx="13" fill="#ff5a4e"/>
  <circle cx="537" cy="225" r="10" fill="#fff"/>

  <line x1="240" y1="260" x2
="560" y2="260" stroke="#eee" stroke-width="1"/>
  <text x="240" y="295" class="label">Soft chime</text>
  <rect x="510" y="282" width
="50" height="26" rx="13" fill="#ccc"/>
  <circle cx="523" cy="295" r="10" fill="#fff"/>
  
  <!-- Reset -->
  <line x1="240" y1="33
0" x2="560" y2="330" stroke="#eee" stroke-width="1"/>
  <text x="400" y="380" text-anchor="middle" class="reset">Forget my streak</text>
</svg>

```

## Motion
- **Element Fade-in/out:** Used for quotes and the "Thank you" button state. `transition: opacity 450ms cubic-bezier(0.22, 1, 0.36, 1);`
- **Countdown Pulse:** A subtle
 'beat' on the timer's colon every second. `animation: pulse 1s infinite cubic-bezier(0.5, 0, 0.5, 1); @keyframes pulse { 50% { opacity: 0.3; } }`
- **Permission Ripple:** A radial
 gradient expands from the button on permission grant. `animation: ripple 800ms cubic-bezier(0.25, 0.46, 0.45, 0.94);`
- **Settings Panel Slide-in:** Panel animates from bottom to top on open
. `transform: translateY(100%); transition: transform 400ms cubic-bezier(0.22, 1, 0.36, 1);`
- **Logo Dot Pulse:** On app open after notification click, the red underline animates. `animation: dot-
pulse 600ms cubic-bezier(0.4, 0, 0.2, 1); @keyframes dot-pulse { 50% { transform: scaleX(1.4); stroke-width: 5px; } }`
- **Toggle Switch:** The circle
 inside the toggle slider. `transition: transform 250ms cubic-bezier(0.25, 0.46, 0.45, 0.94);`

## Mood
This experience is a quiet space to breathe, not another app demanding your attention. Its design is intentionally calm
 and minimal, using ample white space to feel like a held breath. The interactions are soft and subtle, creating a sense of personal ritual rather than a digital task.
