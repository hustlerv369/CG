(function () {
  'use strict';

  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ============= NAV BURGER =============
  const burger = document.getElementById('navBurger');
  const mobile = document.getElementById('navMobile');
  if (burger && mobile) {
    burger.addEventListener('click', () => {
      const open = burger.getAttribute('aria-expanded') === 'true';
      burger.setAttribute('aria-expanded', String(!open));
      mobile.classList.toggle('is-open', !open);
    });
    mobile.querySelectorAll('a').forEach(a => {
      a.addEventListener('click', () => {
        burger.setAttribute('aria-expanded', 'false');
        mobile.classList.remove('is-open');
      });
    });
  }

  // ============= HERO TERMINAL TYPING =============
  const heroTerm = document.getElementById('heroTerminal');
  const lines = [
    { html: '<span class="prompt">$</span> extekk restore --snapshot=latest' },
    { html: '<span class="ts">[03:47:13]</span> <span class="ok">\u2713</span> snapshot loaded \u00b7 247 channels, 84 roles' },
    { html: '<span class="ts">[03:47:13]</span> <span class="ok">\u2713</span> permissions reconciled' },
    { html: '<span class="ts">[03:47:14]</span> <span class="ok">\u2713</span> vouches resynced \u00b7 11,832 entries' },
    { html: '<span class="ts">[03:47:14]</span> <span class="ok">\u2713</span> rebuild complete \u00b7 1.04s' },
    { html: '' },
    { html: '<span class="prompt">$</span> extekk lockdown --tier=critical' },
    { html: '<span class="ts">[03:47:15]</span> <span class="bolt">\u26a1</span> tier 3 lockdown engaged' },
    { html: '<span class="ts">[03:47:15]</span> <span class="ok">\u2713</span> 312 members \u00b7 read-only' },
    { html: '<span class="ts">[03:47:15]</span> <span class="ok">\u2713</span> 4 admin tokens revoked \u00b7 0.31s' }
  ];

  function renderFinalTerminal() {
    if (!heroTerm) return;
    heroTerm.innerHTML = lines.map(l => l.html).join('\n') + '<span class="cursor"></span>';
  }

  function typeTerminal() {
    if (!heroTerm) return;
    if (reduced) { renderFinalTerminal(); return; }

    // Strategy: type each line char-by-char while keeping HTML coloring intact.
    // We build the visible string up to N raw chars and re-render by chunking lines.
    // To keep it lightweight: type plain text, then swap to HTML-rendered version when line ends.

    const plain = lines.map(l => stripHTML(l.html));
    let li = 0;          // line index
    let ci = 0;          // char index within current line
    const buffer = [];   // already-completed rendered lines (HTML)
    const charDelay = 14; // ~0.06s per char would feel slow over many lines; tuned for impact

    function stripHTML(s) {
      const tmp = document.createElement('div');
      tmp.innerHTML = s;
      return tmp.textContent || '';
    }

    function step() {
      if (li >= lines.length) {
        heroTerm.innerHTML = buffer.join('\n') + '<span class="cursor"></span>';
        return;
      }
      const currentPlain = plain[li];
      if (ci < currentPlain.length) {
        const partial = currentPlain.slice(0, ci + 1);
        const html = buffer.concat([escapeHtml(partial)]).join('\n');
        heroTerm.innerHTML = html + '<span class="cursor"></span>';
        ci++;
        setTimeout(step, charDelay);
      } else {
        // commit fully rendered HTML for this line
        buffer.push(lines[li].html);
        li++; ci = 0;
        setTimeout(step, li === 6 ? 380 : 60); // pause before second command
      }
    }

    function escapeHtml(s) {
      return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    // Start typing once hero is in view (or immediately, since it's at top)
    setTimeout(step, 220);
  }

  typeTerminal();

  // ============= COUNTERS =============
  const counters = document.querySelectorAll('.numbers__value');
  const animateCounter = (el) => {
    const target = parseFloat(el.dataset.count);
    const decimals = parseInt(el.dataset.decimals || '0', 10);
    const suffix = el.dataset.suffix || '';
    if (reduced) {
      el.textContent = format(target, decimals) + suffix;
      return;
    }
    const duration = 1200;
    const start = performance.now();
    const ease = (t) => 1 - Math.pow(1 - t, 3); // approximate cubic-bezier(0.22, 1, 0.36, 1)

    function tick(now) {
      const t = Math.min(1, (now - start) / duration);
      const value = target * ease(t);
      el.textContent = format(value, decimals) + (t === 1 ? suffix : '');
      if (t < 1) requestAnimationFrame(tick);
      else el.textContent = format(target, decimals) + suffix;
    }
    requestAnimationFrame(tick);
  };
  function format(n, decimals) {
    if (decimals > 0) return n.toFixed(decimals);
    return Math.round(n).toLocaleString('en-US');
  }

  // ============= WATCH CARDS + COUNTER PILLS =============
  const watchCards = document.querySelectorAll('.watch__card');
  const animatePill = (el) => {
    const target = parseFloat(el.dataset.target);
    if (reduced) { el.textContent = target.toFixed(3) + 's'; return; }
    const duration = 1000;
    const start = performance.now();
    const ease = (t) => 1 - Math.pow(1 - t, 3);
    function tick(now) {
      const t = Math.min(1, (now - start) / duration);
      el.textContent = (target * ease(t)).toFixed(3) + 's';
      if (t < 1) requestAnimationFrame(tick);
      else el.textContent = target.toFixed(3) + 's';
    }
    requestAnimationFrame(tick);
  };

  // ============= INTERSECTION OBSERVER =============
  if ('IntersectionObserver' in window) {
    const numIo = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          animateCounter(entry.target);
          numIo.unobserve(entry.target);
        }
      });
    }, { threshold: 0.4 });
    counters.forEach(c => numIo.observe(c));

    const watchIo = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const card = entry.target;
          const idx = parseInt(card.dataset.step || '0', 10);
          setTimeout(() => {
            card.classList.add('is-visible');
            const pill = card.querySelector('.watch__pill');
            if (pill) animatePill(pill);
          }, idx * 150);
          watchIo.unobserve(card);
        }
      });
    }, { threshold: 0.3 });
    watchCards.forEach(c => watchIo.observe(c));
  } else {
    // Fallback: just show everything
    counters.forEach(animateCounter);
    watchCards.forEach(c => {
      c.classList.add('is-visible');
      const pill = c.querySelector('.watch__pill');
      if (pill) animatePill(pill);
    });
  }
})();
