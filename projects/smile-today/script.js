/* ============================================================
   Smile Today — main page script.
   Mirrors the Architect spec verbatim:
     - localStorage keys named smile.*
     - Hourly default (60 min), range 15-240 min
     - 10 rotating quotes
     - Service Worker fallback for hidden-tab notifications
     - Streak counter, quiet-until-morning toggle
   ============================================================ */
(() => {
  'use strict';

  // ---------- constants -------------------------------------------------
  const KEY = {
    interval:    'smile.intervalMinutes',
    nextAt:      'smile.nextSmileAt',
    streak:      'smile.streakCount',
    lastDate:    'smile.lastSmileDate',
    quiet:       'smile.quietUntilMorning',
    sound:       'smile.soundEnabled',
    asked:       'smile.permissionAsked',
    lastQuote:   'smile.lastQuoteIndex',
    installed:   'smile.installedAt',
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

  const HOUR_MS = 60 * 60 * 1000;
  const MIN_MS = 60 * 1000;

  // ---------- storage helpers -------------------------------------------
  const lsGet = (k, d) => {
    try {
      const v = localStorage.getItem(k);
      if (v === null || v === undefined) return d;
      if (typeof d === 'number') return Number(v);
      if (typeof d === 'boolean') return v === 'true';
      return v;
    } catch { return d; }
  };
  const lsSet = (k, v) => { try { localStorage.setItem(k, String(v)); } catch {} };

  // First-install timestamp (so streak math has a baseline)
  if (!lsGet(KEY.installed, 0)) lsSet(KEY.installed, Date.now());

  // ---------- elements ---------------------------------------------------
  const $ = (id) => document.getElementById(id);
  const body = document.body;
  const els = {
    allow:        $('allow-btn'),
    skip:         $('skip-btn'),
    permNote:     $('permission-note'),
    timer:        $('timer'),
    quote:        $('quote'),
    smile:        $('smile-btn'),
    smileText:    $('smile-btn-text'),
    streak:       $('streak'),
    settingsBtn:  $('settings-btn'),
    panel:        $('settings-panel'),
    backdrop:     $('settings-backdrop'),
    panelClose:   $('settings-close'),
    intervalIn:   $('interval-input'),
    intervalVal:  $('interval-value'),
    quietIn:      $('quiet-input'),
    soundIn:      $('sound-input'),
    resetBtn:     $('reset-streak'),
    brandMark:    document.querySelector('.brand-mark'),
  };

  // ---------- state ------------------------------------------------------
  const state = {
    intervalMinutes: lsGet(KEY.interval, 60),
    nextSmileAt:     lsGet(KEY.nextAt, 0),
    streak:          lsGet(KEY.streak, 0),
    lastDate:        lsGet(KEY.lastDate, ''),
    quiet:           lsGet(KEY.quiet, false),
    sound:           lsGet(KEY.sound, true),
    asked:           lsGet(KEY.asked, false),
    lastQuoteIdx:    lsGet(KEY.lastQuote, -1),
  };

  function persist() {
    lsSet(KEY.interval,  state.intervalMinutes);
    lsSet(KEY.nextAt,    state.nextSmileAt);
    lsSet(KEY.streak,    state.streak);
    lsSet(KEY.lastDate,  state.lastDate);
    lsSet(KEY.quiet,     state.quiet);
    lsSet(KEY.sound,     state.sound);
    lsSet(KEY.asked,     state.asked);
    lsSet(KEY.lastQuote, state.lastQuoteIdx);
  }

  // ---------- service worker --------------------------------------------
  async function registerSW() {
    if (!('serviceWorker' in navigator)) return null;
    try {
      const reg = await navigator.serviceWorker.register('/sw.js');
      return reg;
    } catch (err) {
      console.warn('[smile-today] SW register failed', err);
      return null;
    }
  }
  function syncSWState() {
    if (!navigator.serviceWorker || !navigator.serviceWorker.controller) return;
    navigator.serviceWorker.controller.postMessage({
      type: 'sync',
      nextSmileAt: state.nextSmileAt,
      intervalMs: state.intervalMinutes * MIN_MS,
      quietUntilMorning: state.quiet,
      quotes: QUOTES,
      lastQuoteIndex: state.lastQuoteIdx,
    });
  }

  // ---------- quotes -----------------------------------------------------
  function pickNextQuoteIdx() {
    if (QUOTES.length <= 1) return 0;
    let idx;
    do { idx = Math.floor(Math.random() * QUOTES.length); }
    while (idx === state.lastQuoteIdx);
    return idx;
  }
  function showQuote(idx) {
    if (!els.quote) return;
    els.quote.classList.add('swap-out');
    setTimeout(() => {
      els.quote.textContent = QUOTES[idx];
      els.quote.classList.remove('swap-out');
    }, 220);
  }

  // ---------- streak -----------------------------------------------------
  function todayStr() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
  }
  function dayDiff(a, b) {
    if (!a || !b) return Infinity;
    return Math.round((Date.parse(b) - Date.parse(a)) / 86400000);
  }
  function bumpStreak() {
    const today = todayStr();
    if (state.lastDate === today) return; // already counted today
    if (dayDiff(state.lastDate, today) === 1) state.streak += 1;
    else state.streak = 1;
    state.lastDate = today;
    persist();
    renderStreak();
  }
  function renderStreak() {
    if (!els.streak) return;
    if (state.streak <= 0) { els.streak.hidden = true; return; }
    const word = state.streak === 1 ? 'day' : 'days';
    els.streak.textContent = `${state.streak} ${word} of smiling`;
    els.streak.hidden = false;
  }

  // ---------- timer ------------------------------------------------------
  function ensureNext() {
    if (!state.nextSmileAt || state.nextSmileAt <= Date.now()) {
      state.nextSmileAt = Date.now() + state.intervalMinutes * MIN_MS;
    }
  }
  function fmt(ms) {
    if (ms <= 0) return ['00', '00'];
    const totalSec = Math.floor(ms / 1000);
    const h = Math.floor(totalSec / 3600);
    const m = Math.floor((totalSec % 3600) / 60);
    const s = totalSec % 60;
    if (h > 0) return [String(h), String(m).padStart(2,'0')];
    return [String(m).padStart(2,'0'), String(s).padStart(2,'0')];
  }
  let tickHandle = null;
  function tick() {
    if (!els.timer) return;
    const remaining = state.nextSmileAt - Date.now();
    const [a, b] = fmt(remaining);
    els.timer.firstChild.nodeValue = a; // text node before colon span
    els.timer.lastChild.nodeValue  = b; // text node after colon span
    if (remaining <= 0) {
      // Foreground reminder — show notification if permitted.
      tryNotify();
      // Bump cycle.
      const idx = pickNextQuoteIdx();
      state.lastQuoteIdx = idx;
      showQuote(idx);
      state.nextSmileAt = Date.now() + state.intervalMinutes * MIN_MS;
      persist();
      syncSWState();
    }
  }
  function startTicking() {
    if (tickHandle) clearInterval(tickHandle);
    tick();
    tickHandle = setInterval(tick, 1000);
  }

  // ---------- notification ----------------------------------------------
  function inQuietHours() {
    if (!state.quiet) return false;
    const h = new Date().getHours();
    return h >= 22 || h < 7;
  }
  async function requestPermission() {
    state.asked = true;
    persist();
    if (!('Notification' in window)) {
      els.permNote.hidden = false;
      els.permNote.textContent = 'This browser does not support notifications.';
      return false;
    }
    try {
      const result = await Notification.requestPermission();
      if (result === 'granted') {
        els.brandMark.dataset.pulsed = 'true';
        setTimeout(() => { delete els.brandMark.dataset.pulsed; }, 700);
        return true;
      }
      els.permNote.hidden = false;
      els.permNote.textContent = result === 'denied'
        ? 'Notifications blocked — you can still use the app, just refresh and try again later.'
        : 'No permission yet — tap above when you’re ready.';
    } catch (e) {
      console.warn('[smile-today] permission error', e);
    }
    return false;
  }
  function tryNotify() {
    if (inQuietHours()) return;
    if (!('Notification' in window)) return;
    if (Notification.permission !== 'granted') return;
    const idx = pickNextQuoteIdx();
    state.lastQuoteIdx = idx;
    persist();
    if (navigator.serviceWorker && navigator.serviceWorker.controller) {
      navigator.serviceWorker.controller.postMessage({ type: 'notify-now', body: QUOTES[idx] });
    } else {
      try {
        new Notification('Smile Today', {
          body: QUOTES[idx],
          icon: '/logo.svg',
          tag: 'smile-today',
          silent: !state.sound,
        });
      } catch (e) { /* ignore */ }
    }
    if (state.sound) chime();
  }

  // ---------- soft chime (no audio file) --------------------------------
  let audioCtx = null;
  function chime() {
    try {
      audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
      const ctx = audioCtx;
      const now = ctx.currentTime;
      const o = ctx.createOscillator();
      const g = ctx.createGain();
      o.connect(g); g.connect(ctx.destination);
      o.type = 'sine';
      o.frequency.setValueAtTime(880, now);
      o.frequency.exponentialRampToValueAtTime(660, now + 0.4);
      g.gain.setValueAtTime(0.0001, now);
      g.gain.exponentialRampToValueAtTime(0.18, now + 0.05);
      g.gain.exponentialRampToValueAtTime(0.0001, now + 0.6);
      o.start(now);
      o.stop(now + 0.65);
    } catch (e) { /* user-gesture not yet — silent */ }
  }

  // ---------- view switch -----------------------------------------------
  function showState(name) {
    body.dataset.state = name;
    document.querySelectorAll('.state').forEach((el) => {
      el.hidden = el.dataset.showWhen !== name;
    });
  }
  function enterActive() {
    ensureNext();
    persist();
    showState('active');
    if (state.lastQuoteIdx < 0) state.lastQuoteIdx = pickNextQuoteIdx();
    showQuote(state.lastQuoteIdx);
    renderStreak();
    startTicking();
    syncSWState();
  }

  // ---------- settings panel --------------------------------------------
  function openPanel() {
    els.panel.hidden = false;
    els.backdrop.hidden = false;
    els.intervalIn.value = state.intervalMinutes;
    els.intervalVal.textContent = `${state.intervalMinutes} minutes`;
    els.quietIn.checked = state.quiet;
    els.soundIn.checked = state.sound;
  }
  function closePanel() {
    els.panel.hidden = true;
    els.backdrop.hidden = true;
  }

  // ---------- wire up ---------------------------------------------------
  els.allow?.addEventListener('click', async () => {
    const ok = await requestPermission();
    enterActive(); // either way, show the app — denial is OK
    if (ok) {
      // small ripple confirmation handled via brandMark pulse already
    }
  });
  els.skip?.addEventListener('click', () => {
    state.asked = true;
    persist();
    enterActive();
  });

  els.smile?.addEventListener('click', () => {
    bumpStreak();
    const idx = pickNextQuoteIdx();
    state.lastQuoteIdx = idx;
    showQuote(idx);
    state.nextSmileAt = Date.now() + state.intervalMinutes * MIN_MS;
    persist();
    syncSWState();
    // Post-tap micro feedback
    if (els.smileText) {
      els.smileText.textContent = 'Thank you.';
      setTimeout(() => { els.smileText.textContent = 'I smiled'; }, 1500);
    }
    els.smile.dataset.pulsed = 'true';
    setTimeout(() => { delete els.smile.dataset.pulsed; }, 850);
  });

  els.settingsBtn?.addEventListener('click', openPanel);
  els.panelClose?.addEventListener('click', closePanel);
  els.backdrop?.addEventListener('click', closePanel);
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !els.panel.hidden) closePanel();
  });

  els.intervalIn?.addEventListener('input', () => {
    const v = Math.max(15, Math.min(240, Number(els.intervalIn.value)));
    state.intervalMinutes = v;
    els.intervalVal.textContent = `${v} minutes`;
    // Don't reset the live countdown — apply on next reset.
    persist();
    syncSWState();
  });
  els.quietIn?.addEventListener('change', () => {
    state.quiet = els.quietIn.checked;
    persist();
    syncSWState();
  });
  els.soundIn?.addEventListener('change', () => {
    state.sound = els.soundIn.checked;
    persist();
  });
  els.resetBtn?.addEventListener('click', () => {
    state.streak = 0;
    state.lastDate = '';
    persist();
    renderStreak();
    closePanel();
  });

  // ---------- boot ------------------------------------------------------
  registerSW();

  if (state.asked || ('Notification' in window && Notification.permission === 'granted')) {
    enterActive();
  } else {
    showState('onboarding');
  }

  // Re-tick when tab regains focus (a hidden tab's setInterval is throttled).
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) {
      if (state.nextSmileAt && state.nextSmileAt <= Date.now()) {
        // Missed reminder while hidden — fire and reset.
        tryNotify();
        state.nextSmileAt = Date.now() + state.intervalMinutes * MIN_MS;
        persist();
      }
      if (body.dataset.state === 'active') startTicking();
      syncSWState();
    }
  });

})();
