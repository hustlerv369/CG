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
