```html
<!-- index.html -->
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#ff5a4e">
<meta name="description" content="A small kindness, every hour.">
<title>Smile Today</title>
<link rel="manifest" href="manifest.json">
<link rel="icon" type="image/svg+xml" href="logo.svg">
<link rel="apple-touch-icon" href="logo.svg">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@300;400;500&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="style.css">
</head>
<body>
<main class="app">
  <header class="hero">
    <img src="logo.svg" alt="Smile Today" class="logo" width="80" height="80">
    <h1 class="headline">Smile at someone today.</h1>
    <p class="subheadline">A small kindness, every hour.</p>
  </header>

  <section class="permission" id="permission" hidden>
    <p class="pre-prompt">Smile Today would like to send you a small reminder every hour. No tracking, no accounts — just a nudge.</p>
    <button class="btn btn-secondary" id="permission-cta" type="button">Allow gentle reminders</button>
  </section>

  <section class="timer" aria-label="Next smile timer">
    <p class="timer-label">Next smile in</p>
    <div class="countdown" id="countdown" aria-live="polite">
      <span id="cd-h">00</span><span class="colon">:</span><span id="cd-m">00</span><span class="colon">:</span><span id="cd-s">00</span>
    </div>
  </section>

  <section class="quote" id="quote-box">
    <blockquote id="quote-text"></blockquote>
  </section>

  <section class="action">
    <button class="btn btn-primary" id="smile-btn" type="button">
      <span class="ripple" id="ripple" aria-hidden="true"></span>
      <span class="btn-label" id="smile-label">I smiled</span>
    </button>
    <p class="streak" id="streak-text" aria-live="polite"></p>
  </section>

  <section class="settings" aria-label="Settings">
    <h2 class="settings-title">Settings</h2>
    <label class="setting">
      <span>Remind me every <strong id="interval-display">60 min</strong></span>
      <input type="range" id="interval-slider" min="15" max="240" step="5" value="60" aria-label="Reminder interval in minutes">
    </label>
    <label class="setting setting-toggle">
      <span>Quiet until morning</span>
      <input type="checkbox" id="quiet-toggle">
      <span class="switch" aria-hidden="true"></span>
    </label>
    <label class="setting setting-toggle">
      <span>Soft chime</span>
      <input type="checkbox" id="sound-toggle">
      <span class="switch" aria-hidden="true"></span>
    </label>
    <button class="btn-link" id="forget-btn" type="button">Forget my streak</button>
  </section>

  <footer class="footer">
    <p>Made quietly. No accounts, no tracking.</p>
  </footer>
</main>
<script src="script.js"></script>
</body>
</html>
```

```css
/* style.css */
:root {
  --bg: #ffffff; --fg: #0a0a0a; --accent: #ff5a4e;
  --muted: rgba(10,10,10,.55); --border: rgba(10,10,10,.08); --shadow: rgba(10,10,10,.08);
  --space-xs: 4px; --space-sm: 8px; --space-md: 16px; --space-lg: 24px; --space-xl: 32px;
  --radius-sm: 4px; --radius-md: 8px; --radius-lg: 16px; --radius-full: 9999px;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; }
body {
  background: var(--bg);
  color: var(--fg);
  font-family: 'Inter', system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
  font-weight: 400;
  line-height: 1.5;
  min-height: 100vh;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.app {
  max-width: 560px;
  margin: 0 auto;
  padding: var(--space-xl) var(--space-lg);
  display: flex;
  flex-direction: column;
  gap: var(--space-xl);
  animation: fade-in 800ms ease-out both;
}

@keyframes fade-in {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

.hero { text-align: center; display: flex; flex-direction: column; align-items: center; gap: var(--space-md); }
.logo { width: 80px; height: 80px; }
.headline {
  font-family: 'Fraunces', Georgia, serif;
  font-weight: 500;
  font-size: clamp(1.75rem, 5vw, 2.4rem);
  line-height: 1.1;
  letter-spacing: -0.02em;
}
.subheadline { color: var(--muted); font-size: 1rem; }

.permission {
  background: rgba(255,90,78,0.06);
  border: 1px solid rgba(255,90,78,0.18);
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
  animation: fade-in 600ms ease-out both;
}
.pre-prompt { color: var(--fg); font-size: 0.95rem; line-height: 1.6; }

.timer { text-align: center; }
.timer-label {
  color: var(--muted);
  font-size: 0.875rem;
  margin-bottom: var(--space-sm);
  letter-spacing: 0.02em;
}
.countdown {
  font-family: 'Fraunces', Georgia, serif;
  font-weight: 300;
  font-size: clamp(2.4rem, 9vw, 3.2rem);
  letter-spacing: 0.02em;
  font-variant-numeric: tabular-nums;
}
.colon { display: inline-block; animation: pulse 1s ease-in-out infinite; }
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50%      { opacity: 0.35; }
}

.quote {
  text-align: center;
  padding: 0 var(--space-md);
  min-height: 4em;
  display: flex;
  align-items: center;
  justify-content: center;
}
.quote blockquote {
  font-family: 'Fraunces', Georgia, serif;
  font-weight: 400;
  font-style: italic;
  font-size: 1.15rem;
  color: var(--fg);
  max-width: 38ch;
  line-height: 1.55;
  animation: fade-in 600ms ease-out both;
}

.action { display: flex; flex-direction: column; align-items: center; gap: var(--space-md); }

.btn {
  font-family: inherit;
  font-weight: 500;
  font-size: 1rem;
  padding: var(--space-md) var(--space-xl);
  border: 0;
  border-radius: var(--radius-full);
  cursor: pointer;
  transition: transform 200ms ease, box-shadow 200ms ease, background 250ms ease, color 250ms ease;
  position: relative;
  overflow: hidden;
  user-select: none;
}
.btn:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }

.btn-primary {
  background: var(--fg);
  color: var(--bg);
  min-width: 220px;
  box-shadow: 0 4px 14px var(--shadow);
}
.btn-primary:hover { transform: translateY(-1px); box-shadow: 0 8px 22px var(--shadow); }
.btn-primary:active { transform: translateY(0); }
.btn-primary.thanked { background: var(--accent); color: #fff; }

.btn-secondary {
  background: var(--accent);
  color: #fff;
  box-shadow: 0 4px 14px rgba(255,90,78,0.25);
}
.btn-secondary:hover { transform: translateY(-1px); box-shadow: 0 8px 22px rgba(255,90,78,0.3); }

.btn-label { position: relative; z-index: 2; }

.ripple {
  position: absolute;
  top: 50%; left: 50%;
  width: 24px; height: 24px;
  margin: -12px 0 0 -12px;
  border-radius: 50%;
  background: rgba(255,255,255,0.45);
  transform: scale(0);
  opacity: 0;
  pointer-events: none;
  z-index: 1;
}
.ripple.active { animation: ripple 800ms ease-out; }
@keyframes ripple {
  0%   { transform: scale(0);  opacity: 0.65; }
  100% { transform: scale(12); opacity: 0; }
}

.streak {
  color: var(--muted);
  font-size: 0.875rem;
  min-height: 1.2em;
  letter-spacing: 0.02em;
}

.settings {
  border-top: 1px solid var(--border);
  padding-top: var(--space-lg);
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}
.settings-title {
  font-family: 'Fraunces', Georgia, serif;
  font-weight: 400;
  font-size: 1.25rem;
  margin-bottom: var(--space-sm);
}
.setting {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  font-size: 0.95rem;
  color: var(--fg);
}
.setting strong { color: var(--accent); font-weight: 500; }

input[type=range] {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 4px;
  background: var(--border);
  border-radius: var(--radius-full);
  outline: none;
}
input[type=range]::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 22px; height: 22px;
  background: var(--accent);
  border-radius: 50%;
  cursor: pointer;
  box-shadow: 0 2px 6px var(--shadow);
  transition: transform 150ms ease;
}
input[type=range]::-webkit-slider-thumb:hover { transform: scale(1.1); }
input[type=range]::-moz-range-thumb {
  width: 22px; height: 22px;
  background: var(--accent);
  border-radius: 50%;
  cursor: pointer;
  border: 0;
  box-shadow: 0 2px 6px var(--shadow);
}

.setting-toggle {
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  position: relative;
}
.setting-toggle input[type=checkbox] {
  position: absolute;
  opacity: 0;
  pointer-events: none;
  width: 1px; height: 1px;
}
.switch {
  width: 44px; height: 26px;
  background: var(--border);
  border-radius: var(--radius-full);
  position: relative;
  transition: background 220ms ease;
  flex-shrink: 0;
}
.switch::after {
  content: '';
  position: absolute;
  top: 3px; left: 3px;
  width: 20px; height: 20px;
  background: #fff;
  border-radius: 50%;
  box-shadow: 0 1px 3px var(--shadow);
  transition: transform 220ms ease;
}
.setting-toggle input[type=checkbox]:checked + .switch { background: var(--accent); }
.setting-toggle input[type=checkbox]:checked + .switch::after { transform: translateX(18px); }
.setting-toggle input[type=checkbox]:focus-visible + .switch {
  box-shadow: 0 0 0 3px rgba(255,90,78,0.3);
}

.btn-link {
  background: none;
  border: 0;
  color: var(--muted);
  font-family: inherit;
  font-size: 0.875rem;
  cursor: pointer;
  padding: var(--space-sm) 0;
  align-self: flex-start;
  text-decoration: underline;
  text-underline-offset: 3px;
  transition: color 200ms ease;
}
.btn-link:hover { color: var(--accent); }
.btn-link:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: var(--radius-sm); }

.footer {
  text-align: center;
  padding-top: var(--space-lg);
  border-top: 1px solid var(--border);
  color: var(--muted);
  font-size: 0.8125rem;
}

@media (max-width: 480px) {
  .app { padding: var(--space-lg) var(--space-md); gap: var(--space-lg); }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 1ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 1ms !important;
  }
  .colon { animation: none !important; opacity: 1 !important; }
  .ripple { display: none !important; }
}
```

```js
// script.js
(function () {
  'use strict';

  const KEY = {
    intervalMinutes:    'smile.intervalMinutes',
    nextSmileAt:        'smile.nextSmileAt',
    streakCount:        'smile.streakCount',
    lastSmileDate:      'smile.lastSmileDate',
    quietUntilMorning:  'smile.quietUntilMorning',
    soundEnabled:       'smile.soundEnabled',
    permissionAsked:    'smile.permissionAsked',
    lastQuoteIndex:     'smile.lastQuoteIndex',
    installedAt:        'smile.installedAt',
  };

  const QUOTES = [
    'A smile costs nothing and warms two people at once.',
    'Look up. Someone near you needs to be seen.',
    'The shortest distance between two strangers is a smile.',
    "Be the soft thing in someone's hard day.",
    'Your face is a gift. Give it freely.',
    'Kindness is a muscle. Use it now.',
    'Somewhere, someone is waiting to be smiled at.',
    'A real smile travels further than any word.',
    'You will never regret being the warm one.',
    'The world is quieter when you remember to smile.',
  ];

  // --- storage ---
  function get(key, fallback) {
    const raw = localStorage.getItem(key);
    if (raw === null) return fallback;
    try { return JSON.parse(raw); } catch (e) { return fallback; }
  }
  function set(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) {}
  }

  // --- defaults on first load ---
  if (get(KEY.installedAt, null) === null) {
    set(KEY.installedAt,        Date.now());
    set(KEY.intervalMinutes,    60);
    set(KEY.nextSmileAt,        Date.now() + 3600000);
    set(KEY.streakCount,        0);
    set(KEY.lastSmileDate,      '');
    set(KEY.quietUntilMorning,  false);
    set(KEY.soundEnabled,       true);
    set(KEY.permissionAsked,    false);
    set(KEY.lastQuoteIndex,     -1);
  }

  // --- elements ---
  const el = {
    countdown:       document.getElementById('countdown'),
    h:               document.getElementById('cd-h'),
    m:               document.getElementById('cd-m'),
    s:               document.getElementById('cd-s'),
    quoteText:       document.getElementById('quote-text'),
    smileBtn:        document.getElementById('smile-btn'),
    smileLabel:      document.getElementById('smile-label'),
    ripple:          document.getElementById('ripple'),
    streakText:      document.getElementById('streak-text'),
    intervalSlider:  document.getElementById('interval-slider'),
    intervalDisplay: document.getElementById('interval-display'),
    quietToggle:     document.getElementById('quiet-toggle'),
    soundToggle:     document.getElementById('sound-toggle'),
    forgetBtn:       document.getElementById('forget-btn'),
    permission:      document.getElementById('permission'),
    permissionCta:   document.getElementById('permission-cta'),
  };

  // --- date helpers ---
  function dateStr(d) {
    return d.getFullYear() + '-' +
           String(d.getMonth() + 1).padStart(2, '0') + '-' +
           String(d.getDate()).padStart(2, '0');
  }
  function todayStr()     { return dateStr(new Date()); }
  function yesterdayStr() { const d = new Date(); d.setDate(d.getDate() - 1); return dateStr(d); }
  function pad2(n)        { return String(n).padStart(2, '0'); }

  function formatInterval(min) {
    if (min < 60) return `${min} min`;
    const h = Math.floor(min / 60);
    const r = min % 60;
    if (r === 0) return h === 1 ? '1 hour' : `${h} hours`;
    return `${h}h ${r}m`;
  }

  function isQuietHour() {
    if (!get(KEY.quietUntilMorning, false)) return false;
    const h = new Date().getHours();
    return h >= 22 || h < 7;
  }

  // --- audio chime ---
  let audioCtx = null;
  function ensureAudio() {
    if (audioCtx) return audioCtx;
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return null;
    audioCtx = new Ctx();
    return audioCtx;
  }
  function playChime() {
    if (!get(KEY.soundEnabled, true)) return;
    const ctx = ensureAudio();
    if (!ctx) return;
    try {
      if (ctx.state === 'suspended') ctx.resume();
      const now = ctx.currentTime;
      const tones = [
        { f: 880,    t: 0.00, d: 0.55 },
        { f: 1318.5, t: 0.18, d: 0.70 },
      ];
      tones.forEach(({ f, t, d }) => {
        const osc  = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'sine';
        osc.frequency.value = f;
        gain.gain.setValueAtTime(0, now + t);
        gain.gain.linearRampToValueAtTime(0.12, now + t + 0.04);
        gain.gain.exponentialRampToValueAtTime(0.0001, now + t + d);
        osc.connect(gain).connect(ctx.destination);
        osc.start(now + t);
        osc.stop(now + t + d + 0.05);
      });
    } catch (e) { /* silent */ }
  }

  // --- quotes ---
  function pickQuoteIndex() {
    const last = get(KEY.lastQuoteIndex, -1);
    if (QUOTES.length <= 1) return 0;
    let next;
    do { next = Math.floor(Math.random() * QUOTES.length); } while (next === last);
    set(KEY.lastQuoteIndex, next);
    return next;
  }
  function showQuoteByIndex(idx) {
    el.quoteText.textContent = QUOTES[idx];
    el.quoteText.style.animation = 'none';
    void el.quoteText.offsetWidth;
    el.quoteText.style.animation = '';
  }
  function showCurrentOrNewQuote() {
    let idx = get(KEY.lastQuoteIndex, -1);
    if (idx < 0 || idx >= QUOTES.length) idx = pickQuoteIndex();
    showQuoteByIndex(idx);
  }

  // --- countdown ---
  let cycleFiringLock = false;
  function renderCountdown() {
    const now  = Date.now();
    const next = get(KEY.nextSmileAt, now);
    let diff = Math.max(0, next - now);
    const hours = Math.floor(diff / 3600000); diff -= hours * 3600000;
    const mins  = Math.floor(diff / 60000);   diff -= mins  * 60000;
    const secs  = Math.floor(diff / 1000);
    el.h.textContent = pad2(hours);
    el.m.textContent = pad2(mins);
    el.s.textContent = pad2(secs);

    if (next <= now && !cycleFiringLock) {
      cycleFiringLock = true;
      onCycleElapsed();
      setTimeout(() => { cycleFiringLock = false; }, 1000);
    }
  }

  function rescheduleNext() {
    const min = get(KEY.intervalMinutes, 60);
    set(KEY.nextSmileAt, Date.now() + min * 60000);
  }

  function onCycleElapsed() {
    rescheduleNext();
    const idx = pickQuoteIndex();
    showQuoteByIndex(idx);
    if (!isQuietHour()) {
      playChime();
      sendNotification(QUOTES[idx]);
    }
  }

  // --- notifications ---
  function notificationSupported() { return 'Notification' in window; }

  function shouldShowPermissionCard() {
    if (!notificationSupported()) return false;
    if (Notification.permission === 'granted') return false;
    if (Notification.permission === 'denied')  return false;
    return true;
  }
  function refreshPermissionUI() {
    el.permission.hidden = !shouldShowPermissionCard();
  }

  function sendNotification(body) {
    if (!notificationSupported() || Notification.permission !== 'granted') return;
    const text = body || QUOTES[get(KEY.lastQuoteIndex, 0)] || 'Smile at someone today.';
    const opts = {
      body: text,
      icon: 'logo.svg',
      badge: 'logo.svg',
      tag: 'smile-today',
      silent: !get(KEY.soundEnabled, true),
    };
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.ready
        .then(reg => reg.showNotification('Smile Today', opts))
        .catch(() => { try { new Notification('Smile Today', opts); } catch (e) {} });
    } else {
      try { new Notification('Smile Today', opts); } catch (e) {}
    }
  }

  el.permissionCta.addEventListener('click', () => {
    if (!notificationSupported()) { el.permission.hidden = true; return; }
    set(KEY.permissionAsked, true);
    Notification.requestPermission().then(refreshPermissionUI).catch(refreshPermissionUI);
  });

  // --- streak ---
  function updateStreakOnSmile() {
    const today = todayStr();
    const last  = get(KEY.lastSmileDate, '');
    let streak  = get(KEY.streakCount, 0);
    if (last === today) {
      // already counted today
    } else if (last === yesterdayStr()) {
      streak += 1;
    } else {
      streak = 1;
    }
    set(KEY.streakCount, streak);
    set(KEY.lastSmileDate, today);
    renderStreak();
  }
  function renderStreak() {
    const last   = get(KEY.lastSmileDate, '');
    const streak = get(KEY.streakCount, 0);
    if (!streak || !last || (last !== todayStr() && last !== yesterdayStr())) {
      el.streakText.textContent = '';
      return;
    }
    el.streakText.textContent = streak === 1 ? '1 day streak' : `${streak} day streak`;
  }

  // --- smile button ---
  el.smileBtn.addEventListener('click', () => {
    ensureAudio();
    updateStreakOnSmile();
    rescheduleNext();
    const idx = pickQuoteIndex();
    showQuoteByIndex(idx);
    playChime();

    el.smileLabel.textContent = 'Thank you.';
    el.smileBtn.classList.add('thanked');

    el.ripple.classList.remove('active');
    void el.ripple.offsetWidth;
    el.ripple.classList.add('active');

    setTimeout(() => {
      el.smileLabel.textContent = 'I smiled';
      el.smileBtn.classList.remove('thanked');
    }, 1500);
  });

  // --- settings wiring ---
  function syncSettingsUI() {
    const min = get(KEY.intervalMinutes, 60);
    el.intervalSlider.value = String(min);
    el.intervalDisplay.textContent = formatInterval(min);
    el.quietToggle.checked = !!get(KEY.quietUntilMorning, false);
    el.soundToggle.checked = !!get(KEY.soundEnabled, true);
  }

  el.intervalSlider.addEventListener('input', () => {
    const min = parseInt(el.intervalSlider.value, 10);
    el.intervalDisplay.textContent = formatInterval(min);
  });
  el.intervalSlider.addEventListener('change', () => {
    const min = parseInt(el.intervalSlider.value, 10);
    set(KEY.intervalMinutes, min);
    set(KEY.nextSmileAt, Date.now() + min * 60000);
  });
  el.quietToggle.addEventListener('change', () => {
    set(KEY.quietUntilMorning, el.quietToggle.checked);
  });
  el.soundToggle.addEventListener('change', () => {
    set(KEY.soundEnabled, el.soundToggle.checked);
    if (el.soundToggle.checked) ensureAudio();
  });
  el.forgetBtn.addEventListener('click', () => {
    set(KEY.streakCount, 0);
    set(KEY.lastSmileDate, '');
    renderStreak();
  });

  // --- service worker ---
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('sw.js').catch(() => {});
    });
  }

  // --- visibility refresh ---
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) renderCountdown();
  });

  // --- boot ---
  syncSettingsUI();
  showCurrentOrNewQuote();
  renderCountdown();
  renderStreak();
  refreshPermissionUI();

  // 1s tick for countdown + colon pulse already handled in CSS
  setInterval(renderCountdown, 1000);

  // hourly scheduler safety net (handles tab-resume cases)
  setInterval(() => {
    const now  = Date.now();
    const next = get(KEY.nextSmileAt, now);
    if (next <= now && !cycleFiringLock) {
      cycleFiringLock = true;
      onCycleElapsed();
      setTimeout(() => { cycleFiringLock = false; }, 1000);
    }
  }, 30000);
})();
```

```svg
<!-- logo.svg -->
<svg viewBox="0 0 240 240" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Smile Today">
  <rect width="240" height="240" fill="#ffffff"/>
  <text x="120" y="105" font-family="Fraunces, Georgia, serif" font-size="42" font-weight="400" text-anchor="middle" fill="#0a0a0a">Smile</text>
  <text x="120" y="155" font-family="Fraunces, Georgia, serif" font-size="42" font-weight="700" text-anchor="middle" fill="#0a0a0a">Today</text>
  <path d="M 85 172 Q 120 165, 155 172" stroke="#ff5a4e" stroke-width="4" fill="none" stroke-linecap="round"/>
</svg>
```

```json
<!-- manifest.json -->
{
  "name": "Smile Today",
  "short_name": "Smile",
  "description": "A small kindness, every hour.",
  "start_url": "/",
  "scope": "/",
  "display": "standalone",
  "orientation": "portrait",
  "theme_color": "#ff5a4e",
  "background_color": "#ffffff",
  "icons": [
    { "src": "logo.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any" },
    { "src": "logo.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "maskable" }
  ]
}
```

```js
// sw.js
const CACHE = 'smile-today-v1';
const ASSETS = [
  './',
  './index.html',
  './style.css',
  './script.js',
  './logo.svg',
  './manifest.json',
];

self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE).then(cache => cache.addAll(ASSETS).catch(() => {}))
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  event.respondWith(
    caches.match(req).then(cached => {
      const network = fetch(req).then(resp => {
        if (resp && resp.status === 200 && resp.type === 'basic') {
          const clone = resp.clone();
          caches.open(CACHE).then(c => c.put(req, clone)).catch(() => {});
        }
        return resp;
      }).catch(() => cached);
      return cached || network;
    })
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
      for (const c of list) {
        if ('focus' in c) return c.focus();
      }
      if (self.clients.openWindow) return self.clients.openWindow('./');
    })
  );
});

self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'smile-notify') {
    const body = event.data.body || 'Smile at someone today.';
    self.registration.showNotification('Smile Today', {
      body,
      icon: 'logo.svg',
      badge: 'logo.svg',
      tag: 'smile-today',
    });
  }
});
```

```
# robots.txt
User-agent: *
Allow: /
```
