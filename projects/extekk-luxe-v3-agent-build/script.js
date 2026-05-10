(function () {
  'use strict';

  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const isMobile = window.matchMedia('(max-width: 900px)').matches;
  if (reduced) document.documentElement.classList.add('reduced');

  /* ---------- custom cursor ---------- */
  if (!isMobile && !reduced) {
    const dot = document.querySelector('[data-cursor]');
    const ring = document.querySelector('[data-cursor-ring]');
    let mx = innerWidth / 2, my = innerHeight / 2;
    let rx = mx, ry = my;
    addEventListener('mousemove', (e) => {
      mx = e.clientX; my = e.clientY;
      dot.style.transform = `translate(${mx}px, ${my}px) translate(-50%,-50%)`;
    }, { passive: true });
    function ringLoop() {
      rx += (mx - rx) * 0.18;
      ry += (my - ry) * 0.18;
      ring.style.transform = `translate(${rx}px, ${ry}px) translate(-50%,-50%)`;
      requestAnimationFrame(ringLoop);
    }
    ringLoop();
    document.addEventListener('mouseover', (e) => {
      if (e.target.closest('a, button, [data-magnetic], summary')) {
        dot.classList.add('is-link');
        ring.classList.add('is-link');
      }
    });
    document.addEventListener('mouseout', (e) => {
      if (e.target.closest('a, button, [data-magnetic], summary')) {
        dot.classList.remove('is-link');
        ring.classList.remove('is-link');
      }
    });
  }

  /* ---------- magnetic CTAs ---------- */
  if (!isMobile && !reduced) {
    document.querySelectorAll('[data-magnetic]').forEach(el => {
      addEventListener('mousemove', (e) => {
        const r = el.getBoundingClientRect();
        const cx = r.left + r.width / 2;
        const cy = r.top + r.height / 2;
        const dx = e.clientX - cx;
        const dy = e.clientY - cy;
        const dist = Math.hypot(dx, dy);
        if (dist < 80) {
          const f = (1 - dist / 80) * 8;
          el.style.transform = `translate(${(dx/80) * f}px, ${(dy/80) * f}px)`;
        } else {
          el.style.transform = '';
        }
      }, { passive: true });
      el.addE
```js
// script.js (continued)
      el.addEventListener('mouseleave', () => { el.style.transform = ''; });
    });
  }

  /* ---------- 3D card tilt + radial glow ---------- */
  if (!isMobile && !reduced) {
    document.querySelectorAll('[data-tilt], [data-glow]').forEach(card => {
      card.addEventListener('mousemove', (e) => {
        const r = card.getBoundingClientRect();
        const x = (e.clientX - r.left) / r.width;
        const y = (e.clientY - r.top) / r.height;
        card.style.setProperty('--mx', (x * 100) + '%');
        card.style.setProperty('--my', (y * 100) + '%');
        if (card.hasAttribute('data-tilt')) {
          const ry = (x - 0.5) * 8;
          const rx = (0.5 - y) * 8;
          card.style.transform = `perspective(1000px) rotateX(${rx}deg) rotateY(${ry}deg)`;
        }
      }, { passive: true });
      card.addEventListener('mouseleave', () => {
        card.style.transform = '';
      });
    });
  }

  /* ---------- variable font weight on hero h1 driven by scroll ---------- */
  if (!reduced) {
    const h1 = document.querySelector('[data-scroll-wght]');
    if (h1) {
      const max = innerHeight;
      addEventListener('scroll', () => {
        const p = Math.min(1, Math.max(0, scrollY / max));
        const w = 700 - p * 400;
        h1.style.fontVariationSettings = `'wght' ${w}`;
      }, { passive: true });
    }
  }

  /* ---------- terminal typing ---------- */
  (function () {
    const out = document.getElementById('terminal-out');
    if (!out) return;
    const lines = [
      { t: '$ extekk restore --target=#general', cls: 'cmd' },
      { t: '⠧ verifying audit log integrity…', cls: 'muted' },
      { t: '✓ pre-breach state restored (12.4MB)', cls: 'ok' },
      { t: '[09:41:18] [WARN] port scan from 192.168.1.10', cls: 'warn' },
      { t: '[09:41:19] [CRIT] sqli on /api/v3/users', cls: 'crit' },
      { t: '[09:41:19] [INFO] vector blacklisted globally', cls: 'ok' },
      { t: '$ sentinel --watch', cls: 'cmd' },
      { t: 'streaming events… 218 nodes online', cls: 'muted' }
    ];

    if (reduced) {
      out.innerHTML = lines.map(l => renderLine(l)).join('\n');
      return;
    }

    let li = 0, ci = 0;
    let buf = '';
    function renderLine(l) {
      if (l.cls === 'cmd') return `<span class="prompt">$</span> ${escapeHtml(l.t.slice(2))}`;
      if (l.cls === 'ok')   return `<span class="ok">${escapeHtml(l.t)}</span>`;
      if (l.cls === 'warn') return `<span class="warn">${escapeHtml(l.t)}</span>`;
      if (l.cls === 'crit') return `<span class="crit">${escapeHtml(l.t)}</span>`;
      if (l.cls === 'muted')return `<span class="muted">${escapeHtml(l.t)}</span>`;
      return escapeHtml(l.t);
    }
    function escapeHtml(s) { return s.replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])); }

    function tick() {
      if (li >= lines.length) {
        setTimeout(() => { li = 0; buf = ''; out.innerHTML = ''; tick(); }, 4000);
        return;
      }
      const l = lines[li];
      if (ci === 0 && l.cls === 'cmd') {
        out.innerHTML = buf + `<span class="prompt">$</span> `;
      }
      ci++;
      const partial = l.t.slice(0, ci);
      const partialLine = { t: partial, cls: l.cls };
      out.innerHTML = buf + renderLine(partialLine);
      if (ci >= l.t.length) {
        buf += renderLine(l) + '\n';
        out.innerHTML = buf;
        li++; ci = 0;
        const delay = l.cls === 'cmd' ? 600 : 250;
        setTimeout(tick, delay);
      } else {
        const delay = l.cls === 'cmd' ? 60 : 8;
        setTimeout(tick, delay);
      }
    }
    tick();
  })();

  /* ---------- live number counters ---------- */
  (function () {
    const els = document.querySelectorAll('[data-counter]');
    if (!els.length) return;
    const io = new IntersectionObserver((entries) => {
      entries.forEach(en => {
        if (!en.isIntersecting) return;
        const el = en.target;
        const to = parseFloat(el.dataset.to);
        const suffix = el.dataset.suffix || '';
        const decimals = parseInt(el.dataset.decimals || '0', 10);
        const start = performance.now();
        const dur = 1200;
        const ease = (t) => {
          // cubic-bezier(0.22, 1, 0.36, 1) approx
          return 1 - Math.pow(1 - t, 3);
        };
        function step(now) {
          const t = Math.min(1, (now - start) / dur);
          const v = (to * ease(t)).toFixed(decimals);
          el.innerHTML = v + `<span>${suffix}</span>`;
          if (t < 1) requestAnimationFrame(step);
        }
        if (reduced) {
          el.innerHTML = to.toFixed(decimals) + `<span>${suffix}</span>`;
        } else {
          requestAnimationFrame(step);
        }
        io.unobserve(el);
      });
    }, { threshold: 0.4 });
    els.forEach(el => io.observe(el));
  })();

  /* ---------- scrollytelling state observer ---------- */
  (function () {
    const states = document.querySelectorAll('.state');
    const shield = document.querySelector('[data-shield]');
    const dots = document.querySelectorAll('[data-dot]');
    if (!states.length) return;

    const io = new IntersectionObserver((entries) => {
      entries.forEach(en => {
        if (!en.isIntersecting) return;
        const idx = en.target.dataset.state;
        states.forEach(s => s.classList.remove('is-active'));
        en.target.classList.add('is-active');
        if (shield) shield.dataset.state = idx;
        dots.forEach(d => d.classList.toggle('is-active', d.dataset.dot === idx));
      });
    }, { threshold: 0.55, rootMargin: '-20% 0px -20% 0px' });
    states.forEach(s => io.observe(s));
  })();

  /* ---------- nav burger ---------- */
  (function () {
    const burger = document.querySelector('.nav__burger');
    const links = document.querySelector('.nav__links');
    if (!burger || !links) return;
    burger.addEventListener('click', () => {
      const open = links.classList.toggle('is-open');
      burger.setAttribute('aria-expanded', String(open));
      links.style.display = open ? 'flex' : '';
      if (open) {
        Object.assign(links.style, {
          position: 'fixed',
          inset: '72px 16px auto 16px',
          background: 'rgba(0,0,0,0.85)',
          backdropFilter: 'blur(28px) saturate(180%)',
          border: '1px solid var(--border)',
          borderRadius: '14px',
          padding: '20px',
          flexDirection: 'column',
          gap: '14px',
          alignItems: 'flex-start',
          zIndex: 99
        });
      }
    });
  })();

  /* ---------- WebGL detection + Three.js lazy load ---------- */
  function hasWebGL() {
    try {
      const c = document.createElement('canvas');
      return !!(window.WebGLRenderingContext && (c.getContext('webgl2') || c.getContext('webgl')));
    } catch (e) { return false; }
  }
  if (!hasWebGL()) {
    document.documentElement.classList.add('no-webgl');
  } else if (!reduced) {
    const canvas = document.getElementById('matrix-canvas');
    if (canvas) {
      const boot = () => {
        import('/three-matrix.js').then(({ initMatrixRain }) => {
          const ctl = initMatrixRain(canvas);
          document.addEventListener('visibilitychange', () => {
            if (document.hidden) ctl.pause(); else ctl.resume();
          });
          addEventListener('resize', () => ctl.resize(), { passive: true });
        }).catch(() => {
          document.documentElement.classList.add('no-webgl');
        });
      };
      if ('requestIdleCallback' in window) {
        requestIdleCallback(boot, { timeout: 1500 });
      } else {
        setTimeout(boot, 600);
      }
    }
  }
})();
