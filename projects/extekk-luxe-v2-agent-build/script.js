(() => {
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ─── 1. HERO TYPING + STREAM ─────────────────────────────
  function bootHeroTerminal() {
    const cmd = document.querySelector('.terminal-hero .t-cmd');
    if (!cmd) return;
    const target = cmd.dataset.typed || '';
    if (reduced) {
      cmd.textContent = target;
      streamRows();
      return;
    }
    let i = 0;
    cmd.textContent = '';
    const tick = () => {
      if (i <= target.length) {
        cmd.textContent = target.slice(0, i);
        i++;
        setTimeout(tick, 22);
      } else {
        setTimeout(streamRows, 240);
      }
    };
    tick();

    function streamRows() {
      const wrap = document.querySelector('.terminal-hero .t-out');
      if (!wrap) return;
      let data = [];
      try { data = JSON.parse(wrap.dataset.stream || '[]'); } catch {}
      wrap.innerHTML = '';
      data.forEach((row, idx) => {
        const el = document.createElement('div');
        el.className = 't-row';
        el.innerHTML = `<span class="t-time">${row.t}</span><span class="acid">${row.m.includes('✓') ? '' : ''}</span><span>${row.m}</span><span class="t-ms">${row.ms}</span>`;
        wrap.appendChild(el);
        const delay = reduced ? 0 : 80 + Math.random() * 60 + idx * 90;
        setTimeout(() => el.classList.add('in'), delay);
      });
      const done = document.querySelector('.terminal-hero .t-done');
      if (done) done.style.opacity = '0';
      setTimeout(() => { if (done) { done.style.transition = 'opacity 400ms cubic-bezier(0.22,1,0.36,1)'; done.style.opacity = '1'; } }, 1200);
    }
  }

  // ─── 2. SCROLL-DRIVEN VAR-FONT MODULATION ────────────────
  function bootScrollWeight() {
    if (reduced) return;
    const root = document.documentElement;
    let ticking = false;
    const onScroll = () => {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(() => {
        const y = window.scrollY;
        const max = window.innerHeight;
        const p = Math.min(1, Math.max(0, y / max));
        // wght 400 → 800, SOFT 100 → 0 (hardens as user commits)
        const wght = Math.round(400 + p * 400);
        const soft = Math.round(100 - p * 100);
        root.style.setProperty('--hero-wght', wght);
        root.style.setProperty('--hero-soft', soft);
        ticking = false;
      });
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  // ─── 3. INTERSECTION OBSERVERS (reveal + counters + watch-timing) ─
  function bootIO() {
    const reveal = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.classList.add('in');
          reveal.unobserve(e.target);
        }
      });
    }, { threshold: 0.18 });
    document.querySelectorAll('.cell, .watch-card').forEach((el) => reveal.observe(el));

    // Counters
    const fmt = (v, mode) => {
      if (mode === 'int') return Math.floor(v).toLocaleString('en-US');
      if (mode === 'dec2') return v.toFixed(2);
      if (mode === 'dec3') return v.toFixed(3);
      return Math.floor(v).toString();
    };
    const easeOutCubic = (t) => 1 - Math.pow(1 - t, 3);
    const counter = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (!e.isIntersecting) return;
        const el = e.target;
        const target = parseFloat(el.dataset.count || '0');
        const mode = el.dataset.format || 'int';
        if (reduced) { el.textContent = fmt(target, mode); counter.unobserve(el); return; }
        const dur = 1600;
        const start = performance.now();
        const step = (now) => {
          const t = Math.min(1, (now - start) / dur);
          const v = target * easeOutCubic(t);
          el.textContent = fmt(v, mode);
          if (t < 1) requestAnimationFrame(step);
          else el.textContent = fmt(target, mode);
        };
        requestAnimationFrame(step);
        counter.unobserve(el);
      });
    }, { threshold: 0.4 });
    document.querySelectorAll('.num-value').forEach((el) => counter.observe(el));

    // Watch timing pills
    const watchT = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (!e.isIntersecting) return;
        const el = e.target;
        const target = parseFloat(el.dataset.target || '0');
        if (reduced) { el.textContent = target.toFixed(3) + 's'; watchT.unobserve(el); return; }
        const dur = 1200;
        const start = performance.now();
        const step = (now) => {
          const t = Math.min(1, (now - start) / dur);
          const v = target * easeOutCubic(t);
          el.textContent = v.toFixed(3) + 's';
          if (t < 1) requestAnimationFrame(step);
          else el.textContent = target.toFixed(3) + 's';
        };
        requestAnimationFrame(step);
        watchT.unobserve(el);
      });
    }, { threshold: 0.5 });
    document.querySelectorAll('.watch-time').forEach((el) => watchT.observe(el));
  }

  // ─── 4. CURSOR GLOW (mousemove → --mx, --my) ─────────────
  function bootCursorGlow() {
    if (reduced) return;
    const cards = document.querySelectorAll('.glow-card');
    let raf = 0;
    const onMove = (e) => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        cards.forEach((card) => {
          const r = card.getBoundingClientRect();
          if (e.clientX < r.left - 100 || e.clientX > r.right + 100 ||
              e.clientY < r.top - 100 || e.clientY > r.bottom + 100) return;
          const x = ((e.clientX - r.left) / r.width) * 100;
          const y = ((e.clientY - r.top) / r.height) * 100;
          card.style.setProperty('--mx', x + '%');
          card.style.setProperty('--my', y + '%');
        });
      });
    };
    window.addEventListener('mousemove', onMove, { passive: true });
  }

  // ─── 5. NAV BURGER ───────────────────────────────────────
  function bootBurger() {
    const burger = document.querySelector('.nav-burger');
    const links = document.querySelector('.nav-links');
    if (!burger || !links) return;
    burger.addEventListener('click', () => {
      const open = links.style.display === 'flex';
      links.style.display = open ? '' : 'flex';
      links.style.position = 'absolute';
      links.style.top = '60px';
      links.style.left = '0';
      links.style.right = '0';
      links.style.flexDirection = 'column';
      links.style.background = 'var(--bg-0)';
      links.style.padding = 'var(--s-4)';
      links.style.borderBottom = '1px solid var(--border)';
      burger.setAttribute('aria-expanded', open ? 'false' : 'true');
    });
  }

  // ─── BOOT ────────────────────────────────────────────────
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      bootHeroTerminal();
      bootScrollWeight();
      bootIO();
      bootCursorGlow();
      bootBurger();
    });
  } else {
    bootHeroTerminal();
    bootScrollWeight();
    bootIO();
    bootCursorGlow();
    bootBurger();
  }
})();
