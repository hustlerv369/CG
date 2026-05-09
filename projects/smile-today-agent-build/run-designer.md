## Logo
```xml
<svg viewBox="0 0 240 240" xmlns="http://www.w3.org/2000/svg">
    
<style>
        .st-text { font-family: sans-serif; font-weight: 700; font-size: 64px; fill: #0a0a0a; text-anchor: middle; }
        .st-accent { fill: none; stroke: #ff6f6
1; stroke-width: 8; stroke-linecap: round; }
    </style>
    <rect width="240" height="240" fill="#ffffff"/>
    <text x="120" y="100" class="st-text">Smile</text>
    <
text x="120" y="160" class="st-text">Today</text>
    <path d="M 100 180 q 20 15 40 0" class="st-accent" />
</svg>
```


## Color tokens
```css
:root {
    /* Palette */
    --bg: #ffffff;
    --fg: #0a0a0a;
    --accent: #ff6f61; /* Warm Coral Red */
    --muted: #6b6b6b;
    
--border: #e0e0e0;
    --shadow: rgba(10, 10, 10, 0.1);

    /* Radii */
    --radius-sm: 4px;
    --radius-md: 8px;
    --
radius-lg: 16px;
    --radius-full: 9999px;

    /* Spacing Scale (4px base) */
    --space-xs: 4px;
    --space-sm: 8px;
    --space-md:
 16px;
    --space-lg: 24px;
    --space-xl: 32px;
    --space-xxl: 64px;
}
```

## Typography
```css
@import url('https://fonts.googleapis.com
/css2?family=Montserrat:wght@500;700&family=Lora:ital@0;1&display=swap');

/*
    Display: 'Montserrat', sans-serif
    Body: 'Lora', serif
*/

body {
    font-family: 'Lora', serif;
    
font-size: 18px;
    line-height: 1.6;
    color: var(--fg);
    background-color: var(--bg);
}

h1, .countdown {
    font-family: 'Montserrat', sans-serif;
    font-weight: 70
0;
    font-size: 96px;
    line-height: 1.1;
}

.micro-label {
    font-family: 'Montserrat', sans-serif;
    font-size: 12px;
    letter-spacing: 0.5
px;
    text-transform: uppercase;
    color: var(--muted);
}
```

## Layout sketch (one screen)
```xml
<svg viewBox="0 0 800 500" xmlns="http://www.w3.org/2000/
svg">
    <style>
        .bg { fill: #ffffff; }
        .fg { fill: #0a0a0a; }
        .muted { fill: #6b6b6b; }
        .accent { stroke: #ff6f61;
 }

        .logo-text { font-family: sans-serif; font-weight: 700; font-size: 16px; }
        .streak-text { font-family: sans-serif; font-size: 14px; text-anchor: end
; }
        .micro-label { font-family: sans-serif; font-size: 12px; text-transform: uppercase; text-anchor: middle; letter-spacing: 0.5px; }
        .countdown-text { font-family: monospace; font-weight
: 700; font-size: 96px; text-anchor: middle; }
        .quote-text { font-family: serif; font-style: italic; font-size: 16px; text-anchor: middle; }
        .button-text { font-family: sans-
serif; font-size: 20px; font-weight: 500; text-anchor: middle; }
        .button-circle { stroke: #0a0a0a; stroke-width: 2; fill: none; }
    </style>
    <
rect width="800" height="500" class="bg" />

    <!-- Header -->
    <text x="32" y="44" class="logo-text fg">Smile Today</text>
    <path d="M 32 49 q 8 4
 16 0" class="accent" stroke-width="2" fill="none" />
    <text x="768" y="44" class="streak-text muted">Streak: 7 days</text>
    
    <!-- Main content -->
    <text x="4
00" y="150" class="micro-label muted">Next smile in</text>
    <text x="400" y="240" class="countdown-text fg">59:12</text>
    <text x="400" y="28
0" class="quote-text muted">The best time to smile was yesterday. The next best time is now.</text>

    <!-- Footer button -->
    <circle cx="400" cy="380" r="60" class="button-circle" />
    <text x="4
00" y="386" class="button-text fg">I smiled</text>
</svg>
```

## Motion
- **Element Fade-in:** `opacity` from 0 to 1, `transform` from `translateY(8px)` to `translateY(0
)`. Duration `450ms`. Easing: `cubic-bezier(0.22, 1, 0.36, 1)`. Applied to main content blocks on load.
- **Countdown Colon Pulse:** The colon character in the `59:12` countdown animates 
`opacity` from 1 to 0.4 and back. Duration `1000ms`. Iteration: `infinite`. Timing: `ease-in-out`.
- **Button Tap Ripple:** On click, a circle element scales up from the center of the 'I smiled' button. `transform` from `scale(0)
` to `scale(2.5)`, `opacity` from 0.5 to 0. Duration `800ms`. Easing: `cubic-bezier(0.19, 1, 0.22, 1)`. The ripple's fill is `var(--accent)`.
- **
Settings Panel Slide-up:** A settings panel slides up from the bottom of the viewport. `transform` from `translateY(100%)` to `translateY(0)`. Duration `380ms`. Easing: `cubic-bezier(0.4, 0, 0.2
, 1)`.
- **Logo Accent Pulse:** When a notification triggers a tab to be focused, the red accent curve in the logo briefly pulses. `transform` animates `scaleY` from 1 to 1.5 and back to 1. Duration `600ms`. Easing: 
`cubic-bezier(0.5, 0, 0.5, 2)`.

## Mood
It is a quiet space to pause and acknowledge a moment of peace. It is designed to feel like an exhale, a brief, intentional interaction. The experience is personal and reflective, a tool for mindfulness
, not a metric for happiness.
