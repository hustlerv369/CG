<!-- index.html -->
```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>EXTEKK — Your server, restored in one second.</title>
<meta name="description" content="EXTEKK is the security bot that rebuilds nuked Discord servers and kills scammers before they post. Insurance for communities that can't afford to disappear." />
<meta name="theme-color" content="#7CFFB2" />
<meta property="og:title" content="EXTEKK — Your server, restored in one second." />
<meta property="og:description" content="The security bot that rebuilds nuked Discord servers and kills scammers before they post." />
<meta property="og:type" content="website" />
<meta property="og:image" content="/logo.svg" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="EXTEKK — Your server, restored in one second." />
<meta name="twitter:description" content="The security bot that rebuilds nuked Discord servers and kills scammers before they post." />
<link rel="manifest" href="/manifest.json" />
<link rel="icon" type="image/svg+xml" href="/logo.svg" />
<link rel="stylesheet" href="/style.css" />
</head>
<body>

<!-- ============= NAV ============= -->
<header class="nav" id="nav">
  <div class="nav__inner">
    <a class="nav__logo" href="#top" aria-label="EXTEKK home">
      <svg viewBox="0 0 320 80" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        <path d="M24 10 L10 24 L10 56 L24 70 L40 70 L54 56 L54 24 L40 10 Z M32 20 L44 20 L44 30 L32 42 Z" fill="#7CFFB2"/>
        <text x="70" y="60" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Geist', 'Roboto', sans-serif" font-size="56" fill="white" font-weight="500" letter-spacing="-0.02em">EXTEKK</text>
      </svg>
    </a>
    <nav class="nav__links" aria-label="Primary">
      <a href="#features">Features</a>
      <a href="#demo">Demo</a>
      <a href="#pricing">Pricing</a>
      <a href="#faq">FAQ</a>
    </nav>
    <a class="btn btn--primary nav__cta" href="#cta-final">Add to Discord</a>
    <button class="nav__burger" aria-label="Toggle menu" aria-expanded="false" id="navBurger">
      <span></span><span></span><span></span>
    </button>
  </div>
  <div class="nav__mobile" id="navMobile">
    <a href="#features">Features</a>
    <a href="#demo">Demo</a>
    <a href="#pricing">Pricing</a>
    <a href="#faq">FAQ</a>
    <a class="btn btn--primary" href="#cta-final">Add to Discord</a>
  </div>
</header>

<main id="top">

<!-- ============= HERO ============= -->
<section class="hero">
  <div class="hero__grid" aria-hidden="true"></div>
  <div class="container hero__inner">
    <div class="hero__copy">
      <div class="pill">
        <span class="pill__dot" aria-hidden="true"></span>
        <span class="micro">ALL SYSTEMS NOMINAL · 99.99% UPTIME</span>
      </div>
      <h1 class="hero__headline">Your server, restored<br/>in one second.</h1>
      <p class="hero__sub">EXTEKK is the security bot that rebuilds nuked Discord servers and kills scammers before they post.</p>
      <div class="hero__ctas">
        <a class="btn btn--primary" href="#cta-final">Add to Discord</a>
        <a class="btn btn--secondary" href="#watch">Watch demo</a>
      </div>
    </div>

    <div class="hero__terminal" aria-hidden="false">
      <div class="terminal">
        <div class="terminal__chrome">
          <span class="dot dot--r"></span>
          <span class="dot dot--y"></span>
          <span class="dot dot--g"></span>
          <span class="terminal__title mono">extekk@ops</span>
        </div>
        <pre class="terminal__body mono" id="heroTerminal" aria-label="Live terminal feed"></pre>
      </div>
    </div>
  </div>
</section>

<!-- ============= WATCH-IT-WORK ============= -->
<section class="watch" id="watch">
  <div class="container">
    <p class="micro section__eyebrow">Watch it work</p>
    <h2 class="section__title">Attack to rebuilt in 1.04 seconds.</h2>
    <div class="watch__row">
      <article class="watch__card watch__card--alert" data-step="0">
        <span class="watch__pill watch__pill--alert mono" data-target="0.000">0.000s</span>
        <h3 class="watch__title watch__title--alert">ATTACK DETECTED</h3>
        <p class="watch__desc">Sentinel flags a compromised admin token at 03:47:12 UTC. Channels start dropping.</p>
      </article>
      <svg class="watch__arrow" viewBox="0 0 60 24" aria-hidden="true"><path d="M0 12 L52 12 M46 6 L52 12 L46 18" fill="none" stroke="rgba(255,255,255,0.2)" stroke-width="1.5"/></svg>
      <article class="watch__card" data-step="1">
        <span class="watch__pill mono" data-target="0.420">0.000s</span>
        <h3 class="watch__title watch__title--accent">RESTORE INITIATED</h3>
        <p class="watch__desc">Snapshot loaded. Roles, categories, vouches, permissions queued for re-sync in parallel.</p>
      </article>
      <svg class="watch__arrow" viewBox="0 0 60 24" aria-hidden="true"><path d="M0 12 L52 12 M46 6 L52 12 L46 18" fill="none" stroke="rgba(255,255,255,0.2)" stroke-width="1.5"/></svg>
      <article class="watch__card" data-step="2">
        <span class="watch__pill mono" data-target="1.000">0.000s</span>
        <h3 class="watch__title watch__title--accent">SERVER REBUILT</h3>
        <p class="watch__desc">1.04 seconds later your community is whole. Attacker logged, blacklisted, gone.</p>
      </article>
    </div>
  </div>
</section>

<!-- ============= LIVE NUMBERS ============= -->
<section class="numbers">
  <div class="container">
    <div class="numbers__grid">
      <div class="numbers__card">
        <div class="numbers__value" data-count="23400" data-suffix="+">0</div>
        <p class="micro">Servers protected</p>
        <p class="numbers__hint">communities online</p>
      </div>
      <div class="numbers__card">
        <div class="numbers__value" data-count="11600" data-suffix="+">0</div>
        <p class="micro">Premium operators</p>
        <p class="numbers__hint">trusted by</p>
      </div>
      <div class="numbers__card">
        <div class="numbers__value" data-count="1.2" data-suffix="M+" data-decimals="1">0</div>
        <p class="micro">Threats neutralized</p>
        <p class="numbers__hint">scams auto-killed</p>
      </div>
      <div class="numbers__card">
        <div class="numbers__value" data-count="0.97" data-suffix="s" data-decimals="2">0</div>
        <p class="micro">Mean restore time</p>
        <p class="numbers__hint">attack to rebuilt</p>
      </div>
    </div>
  </div>
</section>

<!-- ============= FEATURE GRID ============= -->
<section class="features" id="features">
  <div class="container">
    <p class="micro section__eyebrow">The arsenal</p>
    <h2 class="section__title">Six capabilities. One bot.</h2>
    <div class="features__grid">
      <article class="feature">
        <div class="feature__icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
        </div>
        <h3 class="feature__title">OAUTH RESTORE</h3>
        <p class="feature__desc">Members and structure rebuilt from cryptographic snapshots.</p>
      </article>
      <article class="feature">
        <div class="feature__icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z"/><circle cx="12" cy="12" r="3"/></svg>
        </div>
        <h3 class="feature__title">SENTINEL AI</h3>
        <p class="feature__desc">24/7 patrol bot deletes phishing and mutes spammers in real time.</p>
      </article>
      <article class="feature">
        <div class="feature__icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>
        </div>
        <h3 class="feature__title">AESTHETIC BUILDER</h3>
        <p class="feature__desc">One command spins up a production-grade server in seconds.</p>
      </article>
      <article class="feature">
        <div class="feature__icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 8a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v2a2 2 0 1 0 0 4v2a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-2a2 2 0 1 0 0-4V8z"/><line x1="13" y1="6" x2="13" y2="18" stroke-dasharray="2 2"/></svg>
        </div>
        <h3 class="feature__title">PRO TICKETS</h3>
        <p class="feature__desc">Encrypted support threads with audit trails and role gating.</p>
      </article>
      <article class="feature">
        <div class="feature__icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="9" r="6"/><polyline points="9 13 7 22 12 19 17 22 15 13"/></svg>
        </div>
        <h3 class="feature__title">VOUCH VAULT</h3>
        <p class="feature__desc">Universal reputation ledger that travels with your community.</p>
      </article>
      <article class="feature">
        <div class="feature__icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
        </div>
        <h3 class="feature__title">GLOBAL BLACKLIST</h3>
        <p class="feature__desc">Cross-server scammer graph updated every 30 seconds.</p>
      </article>
    </div>
  </div>
</section>

<!-- ============= TERMINAL DEMO ============= -->
<section class="demo" id="demo">
  <div class="container">
    <p class="micro section__eyebrow">Real software</p>
    <h2 class="section__title">Three commands. Three outcomes.</h2>
    <div class="demo__grid">
      <div class="terminal">
        <div class="terminal__chrome">
          <span class="dot dot--r"></span><span class="dot dot--y"></span><span class="dot dot--g"></span>
          <span class="terminal__title mono">restore</span>
        </div>
<pre class="terminal__body mono"><span class="prompt">$</span> extekk restore --snapshot=latest
<span class="ts">[03:47:13]</span> <span class="ok">&#10003;</span> snapshot loaded · 247 channels, 84 roles
<span class="ts">[03:47:13]</span> <span class="ok">&#10003;</span> permissions reconciled
<span class="ts">[03:47:14]</span> <span class="ok">&#10003;</span> vouches resynced · 11,832 entries
<span class="ts">[03:47:14]</span> <span class="ok">&#10003;</span> rebuild complete · 1.04s</pre>
      </div>

      <div class="terminal">
        <div class="terminal__chrome">
          <span class="dot dot--r"></span><span class="dot dot--y"></span><span class="dot dot--g"></span>
          <span class="terminal__title mono">lockdown</span>
        </div>
<pre class="terminal__body mono"><span class="prompt">$</span> extekk lockdown --tier=critical
<span class="ts">[03:47:15]</span> <span class="bolt">&#9889;</span> tier 3 lockdown engaged
<span class="ts">[03:47:15]</span> <span class="ok">&#10003;</span> 312 members · read-only
<span class="ts">[03:47:15]</span> <span class="ok">&#10003;</span> 4 admin tokens revoked · 0.31s</pre>
      </div>

      <div class="terminal">
        <div class="terminal__chrome">
          <span class="dot dot--r"></span><span class="dot dot--y"></span><span class="dot dot--g"></span>
          <span class="terminal__title mono">vouches</span>
        </div>
<pre class="terminal__body mono"><span class="prompt">$</span> extekk vouches sync --global
<span class="ts">[03:47:16]</span> <span class="arrow">&rarr;</span> pulling vault · 1.2M records
<span class="ts">[03:47:17]</span> <span class="ok">&#10003;</span> 8,431 reputations updated
<span class="ts">[03:47:17]</span> <span class="ok">&#10003;</span> 12 scammers flagged · added to blacklist
<span class="ts">[03:47:17]</span> <span class="ok">&#10003;</span> sync complete · 0.88s</pre>
      </div>
    </div>
  </div>
</section>

<!-- ============= TESTIMONIALS ============= -->
<section class="testimonials">
  <div class="container">
    <p class="micro section__eyebrow">Operators</p>
    <h2 class="section__title">Trusted under fire.</h2>
    <div class="testimonials__grid">
      <figure class="testimonial">
        <blockquote>"Got nuked at 4am by a rogue admin. EXTEKK had us back online before I finished my coffee. Insurance you didn't know you needed."</blockquote>
        <figcaption>
          <strong>@volt</strong>
          <span>Server owner · 12K members</span>
          <span class="verified"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3 8 L7 12 L13 4" fill="none" stroke="currentColor" stroke-width="2"/></svg> verified purchase</span>
        </figcaption>
      </figure>
      <figure class="testimonial">
        <blockquote>"Sentinel caught a phishing campaign my mods missed for two weeks. Banned 47 alts in an hour. Worth every cent of the trial."</blockquote>
        <figcaption>
          <strong>@nyx_mod</strong>
          <span>Head moderator · 38K community</span>
          <span class="verified"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3 8 L7 12 L13 4" fill="none" stroke="currentColor" stroke-width="2"/></svg> verified purchase</span>
        </figcaption>
      </figure>
      <figure class="testimonial">
        <blockquote>"Ran my whole launch off EXTEKK's builder. Roles, channels, vouches — production-ready in one command. No competitor comes close."</blockquote>
        <figcaption>
          <strong>@kairo</strong>
          <span>Project founder · 6K trading hub</span>
          <span class="verified"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3 8 L7 12 L13 4" fill="none" stroke="currentColor" stroke-width="2"/></svg> verified purchase</span>
        </figcaption>
      </figure>
    </div>
  </div>
</section>

<!-- ============= PRICING ============= -->
<section class="pricing" id="pricing">
  <div class="container">
    <p class="micro section__eyebrow">Pricing</p>
    <h2 class="section__title">Two tiers. One decision.</h2>
    <div class="pricing__grid">
      <article class="plan">
        <header class="plan__head">
          <h3 class="plan__name">FREE</h3>
          <p class="plan__sub">Everything you need to survive.</p>
        </header>
        <ul class="plan__features">
          <li><span class="check">&#10003;</span> OAuth Member &amp; Server Restore</li>
          <li><span class="check">&#10003;</span> Aesthetic Server Builder</li>
          <li><span class="check">&#10003;</span> Vouch Vault (community)</li>
          <li><span class="check">&#10003;</span> Global Scammer Blacklist (read)</li>
          <li class="muted"><span class="cross">&#10007;</span> Sentinel AI auto-mod</li>
          <li class="muted"><span class="cross">&#10007;</span> Pro Ticket System</li>
        </ul>
        <a class="btn btn--secondary btn--block" href="#cta-final">Add for free</a>
      </article>

      <article class="plan plan--pro">
        <span class="plan__tag">MOST POPULAR</span>
        <header class="plan__head">
          <h3 class="plan__name">PRO</h3>
          <p class="plan__price"><span class="plan__amount">$19</span><span class="plan__period">/mo</span> · 14-day free trial</p>
          <p class="plan__sub">Everything. No exceptions.</p>
        </header>
        <ul class="plan__features">
          <li><span class="check">&#10003;</span> Sentinel AI · 24/7 patrol</li>
          <li><span class="check">&#10003;</span> Pro Ticket System · encrypted</li>
          <li><span class="check">&#10003;</span> Sub-second restore SLA</li>
          <li><span class="check">&#10003;</span> Cross-server reputation sync</li>
          <li><span class="check">&#10003;</span> Priority blacklist push</li>
          <li><span class="check">&#10003;</span> 24/7 white-glove support</li>
        </ul>
        <a class="btn btn--accent btn--block" href="#cta-final">Start free trial</a>
      </article>
    </div>
  </div>
</section>

<!-- ============= FAQ ============= -->
<section class="faq" id="faq">
  <div class="container container--narrow">
    <p class="micro section__eyebrow">FAQ</p>
    <h2 class="section__title">Sharp answers.</h2>
    <div class="faq__list">
      <details open>
        <summary>Is it safe to give the bot OAuth?</summary>
        <p>Yes. EXTEKK uses scoped Discord OAuth with read-mostly permissions. Snapshots are encrypted at rest and we never touch DMs.</p>
      </details>
      <details>
        <summary>How fast is restore?</summary>
        <p>Median 0.97 seconds for servers under 50K members. The clock starts the instant Sentinel detects the breach.</p>
      </details>
      <details>
        <summary>What if Discord deletes my server?</summary>
        <p>Snapshots live on our infrastructure, not Discord's. Spin up a new server, point EXTEKK at it, and your community is back.</p>
      </details>
      <details>
        <summary>Do you log my server data?</summary>
        <p>We store encrypted structural snapshots only. No message content, no DMs, no personal data. Audit log is open-source.</p>
      </details>
      <details>
        <summary>Can I cancel anytime?</summary>
        <p>One click in the dashboard. No retention call, no email gauntlet. Free tier stays active forever.</p>
      </details>
    </div>
  </div>
</section>

<!-- ============= FINAL CTA ============= -->
<section class="cta-final" id="cta-final">
  <div class="container">
    <h2 class="cta-final__title">Stop hoping.<br/>Start insuring.</h2>
    <a class="btn btn--primary btn--xl" href="https://discord.com/oauth2/authorize">Add EXTEKK to Discord</a>
  </div>
</section>

</main>

<!-- ============= FOOTER ============= -->
<footer class="footer">
  <div class="container footer__inner">
    <div class="footer__brand">
      <svg class="footer__logo" viewBox="0 0 320 80" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        <path d="M24 10 L10 24 L10 56 L24 70 L40 70 L54 56 L54 24 L40 10 Z M32 20 L44 20 L44 30 L32 42 Z" fill="#7CFFB2"/>
        <text x="70" y="60" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Geist', 'Roboto', sans-serif" font-size="56" fill="white" font-weight="500" letter-spacing="-0.02em">EXTEKK</text>
      </svg>
      <p class="footer__tag micro">Built by operators, for operators.</p>
    </div>
    <div class="footer__cols">
      <div>
        <p class="micro footer__col-title">Product</p>
        <a href="#features">Features</a>
        <a href="#pricing">Pricing</a>
        <a href="#demo">Demo</a>
        <a href="#">Docs</a>
        <a href="#">Status</a>
      </div>
      <div>
        <p class="micro footer__col-title">Social</p>
        <a href="#">Discord</a>
        <a href="#">GitHub</a>
      </div>
      <div>
        <p class="micro footer__col-title">Legal</p>
        <a href="#">Terms</a>
        <a href="#">Privacy</a>
        <a href="#">Refund Policy</a>
      </div>
    </div>
  </div>
  <div class="container footer__bottom">
    <p class="micro">© 2026 EXTEKK Systems</p>
  </div>
</footer>

<script src="/script.js"></script>
</body>
</html>
```

```css
/* style.css */
:root {
  /* Palette */
  --bg-0: #080808;
  --bg-1: #111111;
  --bg-2: #1A1A1A;
  --fg-0: #FFFFFF;
  --fg-1: rgba(255, 255, 255, 0.75);
  --fg-2: rgba(255, 255, 255, 0.45);
  --accent: #7CFFB2;
  --accent-glow: rgba(124, 255, 178, 0.6);
  --discord: #5865F2;
  --alert: #FF4D5E;
  --border: rgba(255, 255, 255, 0.08);
  --grid: rgba(124, 255, 178, 0.04);

  /* Radius */
  --r-1: 4px;
  --r-2: 8px;
  --r-3: 12px;
  --r-4: 16px;
  --r-pill: 999px;

  /* Spacing */
  --s-1: 4px;
  --s-2: 8px;
  --s-3: 12px;
  --s-4: 16px;
  --s-5: 24px;
  --s-6: 48px;
  --s-7: 96px;
}

@import url('https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600&family=Geist+Mono&display=swap');

:root {
  --font-body: 'Geist', -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", sans-serif;
  --font-mono: 'Geist Mono', ui-monospace, "SFMono-Regular", monospace;
}

*, *::before, *::after { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  font-family: var(--font-body);
  font-size: 17px;
  line-height: 1.6;
  color: var(--fg-1);
  background: var(--bg-0);
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}

h1, h2, h3 {
  font-weight: 500;
  line-height: 1.2;
  letter-spacing: -0.02em;
  color: var(--fg-0);
  margin: 0;
}
h1 { font-size: clamp(3.5rem, 8vw, 7rem); }
h2 { font-size: clamp(2rem, 4vw, 2.75rem); }
h3 { font-size: 1.5rem; }
p { margin: 0; }
a { color: inherit; text-decoration: none; transition: color 180ms ease; }
a:hover { color: var(--fg-0); }

img, svg { display: block; max-width: 100%; }

button { font: inherit; }

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
  color: var(--fg-2);
}

/* Focus rings */
:where(a, button, summary, [tabindex]):focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 3px;
  border-radius: var(--r-1);
}

/* Containers */
.container {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 var(--s-5);
}
.container--narrow { max-width: 820px; }

/* Section heading helpers */
.section__eyebrow { color: var(--accent); margin-bottom: var(--s-3); }
.section__title { margin-bottom: var(--s-6); max-width: 720px; }

/* ============= BUTTONS ============= */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--s-2);
  padding: 14px 22px;
  border-radius: var(--r-2);
  font-size: 16px;
  font-weight: 500;
  font-family: var(--font-body);
  cursor: pointer;
  border: 1px solid transparent;
  transition: transform 180ms ease, background 180ms ease, box-shadow 260ms cubic-bezier(0.33, 1, 0.68, 1), color 180ms ease;
  white-space: nowrap;
}
.btn--primary {
  background: var(--discord);
  color: #fff;
}
.btn--primary:hover {
  background: #4752c4;
  color: #fff;
  transform: translateY(-1px);
}
.btn--secondary {
  background: transparent;
  color: var(--fg-0);
  border-color: rgba(255, 255, 255, 0.2);
}
.btn--secondary:hover {
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(255, 255, 255, 0.4);
  color: var(--fg-0);
}
.btn--accent {
  background: var(--accent);
  color: var(--bg-0);
}
.btn--accent:hover {
  background: #92ffc1;
  color: var(--bg-0);
  box-shadow: 0 0 32px var(--accent-glow);
  transform: translateY(-1px);
}
.btn--block { width: 100%; }
.btn--xl {
  padding: 22px 36px;
  font-size: 19px;
  border-radius: var(--r-3);
}

/* ============= NAV ============= */
.nav {
  position: sticky;
  top: 0;
  z-index: 50;
  background: rgba(8, 8, 8, 0.7);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-bottom: 1px solid var(--border);
}
.nav__inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 14px var(--s-5);
  display: flex;
  align-items: center;
  gap: var(--s-5);
}
.nav__logo svg { height: 28px; width: auto; }
.nav__links {
  display: flex;
  gap: var(--s-5);
  margin-left: auto;
}
.nav__links a {
  font-size: 14px;
  color: var(--fg-1);
  font-weight: 500;
}
.nav__cta { padding: 10px 18px; font-size: 14px; }
.nav__burger {
  display: none;
  background: transparent;
  border: 0;
  width: 36px;
  height: 36px;
  cursor: pointer;
  position: relative;
  margin-left: auto;
}
.nav__burger span {
  display: block;
  width: 22px;
  height: 1.5px;
  background: var(--fg-0);
  margin: 4px auto;
  transition: transform 200ms ease, opacity 200ms ease;
}
.nav__burger[aria-expanded="true"] span:nth-child(1) { transform: translateY(5.5px) rotate(45deg); }
.nav__burger[aria-expanded="true"] span:nth-child(2) { opacity: 0; }
.nav__burger[aria-expanded="true"] span:nth-child(3) { transform: translateY(-5.5px) rotate(-45deg); }

.nav__mobile {
  display: none;
  flex-direction: column;
  padding: var(--s-4) var(--s-5);
  gap: var(--s-4);
  border-top: 1px solid var(--border);
}
.nav__mobile.is-open { display: flex; }
.nav__mobile a { font-size: 17px; }

@media (max-width: 768px) {
  .nav__links, .nav__cta { display: none; }
  .nav__burger { display: block; }
}

/* ============= HERO ============= */
.hero {
  position: relative;
  padding: clamp(72px, 12vw, 140px) 0 clamp(72px, 12vw, 140px);
  overflow: hidden;
}
.hero__grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(to right, var(--grid) 1px, transparent 1px),
    linear-gradient(to bottom, var(--grid) 1px, transparent 1px);
  background-size: 40px 40px;
  mask-image: radial-gradient(ellipse 80% 60% at 50% 40%, #000 50%, transparent 100%);
  -webkit-mask-image: radial-gradient(ellipse 80% 60% at 50% 40%, #000 50%, transparent 100%);
  animation: grid-pulse 4s ease-in-out infinite;
  pointer-events: none;
}
@keyframes grid-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}
.hero__inner {
  position: relative;
  display: grid;
  grid-template-columns: 1.05fr 0.95fr;
  gap: var(--s-7);
  align-items: center;
}
.hero__copy { max-width: 600px; }
.hero__headline {
  margin: var(--s-5) 0 var(--s-5);
  background: linear-gradient(180deg, #fff 0%, rgba(255,255,255,0.7) 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}
.hero__sub {
  font-size: clamp(17px, 1.4vw, 20px);
  color: var(--fg-1);
  max-width: 520px;
  margin-bottom: var(--s-6);
}
.hero__ctas { display: flex; gap: var(--s-3); flex-wrap: wrap; }

.pill {
  display: inline-flex;
  align-items: center;
  gap: var(--s-2);
  padding: 8px 14px;
  background: rgba(124, 255, 178, 0.06);
  border: 1px solid rgba(124, 255, 178, 0.2);
  border-radius: var(--r-pill);
}
.pill__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 12px var(--accent-glow);
  animation: pill-pulse 2.4s ease-in-out infinite;
}
@keyframes pill-pulse {
  0%, 100% { box-shadow: 0 0 4px var(--accent-glow); }
  50%      { box-shadow: 0 0 16px var(--accent-glow); }
}

@media (max-width: 960px) {
  .hero__inner { grid-template-columns: 1fr; gap: var(--s-6); }
}

/* ============= TERMINAL ============= */
.terminal {
  background: var(--bg-1);
  border: 1px solid var(--border);
  border-radius: var(--r-3);
  overflow: hidden;
  box-shadow: 0 30px 80px -30px rgba(0,0,0,0.6);
}
.terminal__chrome {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 14px;
  background: rgba(255, 255, 255, 0.02);
  border-bottom: 1px solid var(--border);
}
.dot {
  width: 11px; height: 11px; border-radius: 50%;
  display: inline-block;
}
.dot--r { background: #FF5F57; }
.dot--y { background: #FEBC2E; }
.dot--g { background: #28C840; }
.terminal__title {
  margin-left: auto;
  color: var(--fg-2);
  font-size: 12px;
}
.terminal__body {
  margin: 0;
  padding: var(--s-5);
  font-family: var(--font-mono);
  font-size: 13.5px;
  line-height: 1.65;
  color: var(--fg-1);
  white-space: pre-wrap;
  word-break: break-word;
  min-height: 380px;
}
.terminal__body .prompt { color: var(--accent); }
.terminal__body .ts { color: var(--accent); }
.terminal__body .ok { color: var(--accent); }
.terminal__body .bolt { color: var(--accent); }
.terminal__body .arrow { color: var(--accent); }
.cursor {
  display: inline-block;
  width: 9px;
  height: 16px;
  background: var(--accent);
  vertical-align: -2px;
  margin-left: 2px;
  animation: cursor-blink 1s steps(1) infinite;
}
@keyframes cursor-blink {
  50% { opacity: 0; }
}

/* ============= WATCH-IT-WORK ============= */
.watch { padding: var(--s-7) 0; border-top: 1px solid var(--border); }
.watch__row {
  display: grid;
  grid-template-columns: 1fr auto 1fr auto 1fr;
  gap: var(--s-4);
  align-items: stretch;
}
.watch__card {
  background: var(--bg-1);
  border: 1px solid var(--border);
  border-radius: var(--r-3);
  padding: var(--s-5);
  opacity: 0;
  transform: translateY(16px);
  transition: opacity 450ms cubic-bezier(0.22, 1, 0.36, 1), transform 450ms cubic-bezier(0.22, 1, 0.36, 1), border-color 260ms ease, box-shadow 260ms ease;
}
.watch__card.is-visible { opacity: 1; transform: translateY(0); }
.watch__card--alert { border-color: var(--alert); }
.watch__pill {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: var(--r-pill);
  background: var(--accent);
  color: var(--bg-0);
  font-size: 13px;
  font-weight: 500;
}
.watch__pill--alert {
  background: var(--alert);
  color: #fff;
  animation: alert-pulse 1.2s ease-in-out infinite;
}
@keyframes alert-pulse {
  0%, 100% { box-shadow: 0 0 0 rgba(255, 77, 94, 0.6); }
  50%      { box-shadow: 0 0 20px rgba(255, 77, 94, 0.6); }
}
.watch__title { margin: var(--s-4) 0 var(--s-2); font-size: 16px; letter-spacing: 0.05em; text-transform: uppercase; }
.watch__title--alert { color: var(--alert); }
.watch__title--accent { color: var(--accent); }
.watch__desc { color: var(--fg-1); font-size: 15px; }
.watch__arrow { width: 60px; height: 24px; align-self: center; }

@media (max-width: 900px) {
  .watch__row { grid-template-columns: 1fr; }
  .watch__arrow { transform: rotate(90deg); margin: 0 auto; }
}

/* ============= LIVE NUMBERS ============= */
.numbers { padding: var(--s-7) 0; border-top: 1px solid var(--border); }
.numbers__grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--s-4);
}
.numbers__card {
  background: var(--bg-1);
  border: 1px solid var(--border);
  border-radius: var(--r-3);
  padding: var(--s-5);
}
.numbers__value {
  font-family: var(--font-mono);
  font-size: clamp(2rem, 4vw, 2.75rem);
  font-weight: 500;
  color: var(--accent);
  letter-spacing: -0.02em;
  margin-bottom: var(--s-3);
}
.numbers__hint { color: var(--fg-2); font-size: 14px; margin-top: 4px; }

@media (max-width: 768px) {
  .numbers__grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 480px) {
  .numbers__grid { grid-template-columns: 1fr; }
}

/* ============= FEATURES ============= */
.features { padding: var(--s-7) 0; border-top: 1px solid var(--border); }
.features__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--s-4);
}
.feature {
  background: var(--bg-1);
  border: 1px solid var(--border);
  border-radius: var(--r-3);
  padding: var(--s-5);
  transition: box-shadow 260ms cubic-bezier(0.33, 1, 0.68, 1), border-color 260ms ease, transform 260ms ease;
}
.feature:hover {
  border-color: rgba(124, 255, 178, 0.25);
  box-shadow: 0 0 0 1px rgba(124, 255, 178, 0.08), 0 24px 80px -30px var(--accent-glow);
  transform: translateY(-2px);
}
.feature__icon {
  width: 44px; height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--r-2);
  background: rgba(124, 255, 178, 0.06);
  color: var(--accent);
  margin-bottom: var(--s-4);
}
.feature__icon svg { width: 22px; height: 22px; }
.feature__title {
  font-size: 15px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--fg-0);
  margin-bottom: var(--s-2);
}
.feature__desc { color: var(--fg-1); font-size: 15px; }

@media (max-width: 900px) { .features__grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 600px) { .features__grid { grid-template-columns: 1fr; } }

/* ============= DEMO ============= */
.demo { padding: var(--s-7) 0; border-top: 1px solid var(--border); }
.demo__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--s-4);
}
.demo .terminal__body { min-height: 220px; }
@media (max-width: 1000px) { .demo__grid { grid-template-columns: 1fr; } }

/* ============= TESTIMONIALS ============= */
.testimonials { padding: var(--s-7) 0; border-top: 1px solid var(--border); }
.testimonials__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--s-4);
}
.testimonial {
  margin: 0;
  background: var(--bg-1);
  border: 1px solid var(--border);
  border-radius: var(--r-3);
  padding: var(--s-5);
}
.testimonial blockquote {
  margin: 0 0 var(--s-5);
  color: var(--fg-0);
  font-size: 17px;
  line-height: 1.55;
  letter-spacing: -0.01em;
}
.testimonial figcaption {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 14px;
  color: var(--fg-2);
}
.testimonial strong { color: var(--fg-0); font-weight: 500; }
.testimonial .verified {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--accent);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-top: 4px;
}
.testimonial .verified svg { width: 14px; height: 14px; }
@media (max-width: 900px) { .testimonials__grid { grid-template-columns: 1fr; } }

/* ============= PRICING ============= */
.pricing { padding: var(--s-7) 0; border-top: 1px solid var(--border); }
.pricing__grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--s-4);
  max-width: 880px;
  margin: 0 auto;
}
.plan {
  position: relative;
  background: var(--bg-1);
  border: 1px solid var(--border);
  border-radius: var(--r-3);
  padding: var(--s-6);
  display: flex;
  flex-direction: column;
}
.plan--pro {
  border-color: var(--accent);
  box-shadow: 0 24px 80px -30px var(--accent-glow);
}
.plan__tag {
  position: absolute;
  top: -12px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--accent);
  color: var(--bg-0);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  padding: 6px 12px;
  border-radius: var(--r-pill);
}
.plan__head { margin-bottom: var(--s-5); }
.plan__name { font-size: 22px; letter-spacing: 0.02em; color: var(--fg-0); margin-bottom: var(--s-2); }
.plan__price { color: var(--accent); font-size: 15px; margin-bottom: var(--s-2); }
.plan__amount { font-size: 32px; font-weight: 500; color: var(--fg-0); margin-right: 2px; }
.plan__period { color: var(--fg-2); font-size: 16px; }
.plan__sub { color: var(--fg-2); font-size: 15px; }
.plan__features {
  list-style: none;
  padding: 0;
  margin: 0 0 var(--s-6);
  display: flex;
  flex-direction: column;
  gap: var(--s-3);
  flex: 1;
}
.plan__features li {
  display: flex;
  align-items: center;
  gap: var(--s-3);
  font-size: 15px;
  color: var(--fg-1);
}
.plan__features li.muted { color: var(--fg-2); }
.check { color: var(--accent); font-weight: 700; }
.cross { color: var(--fg-2); font-weight: 700; }

@media (max-width: 800px) {
  .pricing__grid { grid-template-columns: 1fr; }
}

/* ============= FAQ ============= */
.faq { padding: var(--s-7) 0; border-top: 1px solid var(--border); }
.faq__list { display: flex; flex-direction: column; gap: var(--s-3); }
.faq details {
  background: var(--bg-1);
  border: 1px solid var(--border);
  border-radius: var(--r-3);
  padding: var(--s-4) var(--s-5);
  transition: border-color 200ms ease;
}
.faq details[open] { border-color: rgba(124, 255, 178, 0.2); }
.faq summary {
  cursor: pointer;
  list-style: none;
  font-size: 17px;
  font-weight: 500;
  color: var(--fg-0);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--s-3);
}
.faq summary::-webkit-details-marker { display: none; }
.faq summary::after {
  content: "+";
  color: var(--accent);
  font-size: 24px;
  font-weight: 300;
  transition: transform 200ms ease;
  line-height: 1;
}
.faq details[open] summary::after { content: "−"; }
.faq p {
  margin-top: var(--s-3);
  color: var(--fg-1);
  font-size: 16px;
}

/* ============= FINAL CTA ============= */
.cta-final {
  padding: clamp(80px, 12vw, 140px) 0;
  border-top: 1px solid var(--border);
  text-align: center;
  background:
    radial-gradient(ellipse 60% 50% at 50% 50%, rgba(124, 255, 178, 0.08), transparent 70%),
    var(--bg-0);
}
.cta-final__title {
  font-size: clamp(2.5rem, 7vw, 5.5rem);
  margin-bottom: var(--s-6);
  background: linear-gradient(180deg, #fff 0%, rgba(255,255,255,0.7) 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

/* ============= FOOTER ============= */
.footer {
  border-top: 1px solid var(--border);
  padding: var(--s-7) 0 var(--s-5);
  background: var(--bg-0);
}
.footer__inner {
  display: grid;
  grid-template-columns: 1.2fr 2fr;
  gap: var(--s-6);
  align-items: start;
}
.footer__logo { height: 28px; width: auto; margin-bottom: var(--s-3); }
.footer__tag { color: var(--fg-2); }
.footer__cols {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--s-5);
}
.footer__cols div { display: flex; flex-direction: column; gap: var(--s-3); }
.footer__col-title { color: var(--fg-2); margin-bottom: 4px; }
.footer__cols a { font-size: 14px; color: var(--fg-1); }
.footer__cols a:hover { color: var(--fg-0); }
.footer__bottom {
  margin-top: var(--s-6);
  padding-top: var(--s-5);
  border-top: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  color: var(--fg-2);
}
@media (max-width: 768px) {
  .footer__inner { grid-template-columns: 1fr; gap: var(--s-5); }
  .footer__cols { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 480px) {
  .footer__cols { grid-template-columns: 1fr 1fr; }
}

/* ============= MOTION REDUCTION ============= */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
  .hero__grid, .pill__dot, .watch__pill--alert, .cursor { animation: none !important; }
  .watch__card { opacity: 1; transform: none; }
}
```

```javascript
// script.js
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
```

```xml
<!-- logo.svg -->
<svg viewBox='0 0 320 80' xmlns='http://www.w3.org/2000/svg'>
  <defs>
    <style>
      .wordmark { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Geist", "Roboto", "Oxygen", "Ubuntu", "Cantarell", "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif; font-size: 56px; fill: white; font-weight: 500; letter-spacing: -0.02em; }
    </style>
  </defs>
  <path d='M24 10 L10 24 L10 56 L24 70 L40 70 L54 56 L54 24 L40 10 Z M32 20 L44 20 L44 30 L32 42 Z' fill='#7CFFB2'/>
  <text x='70' y='60' class='wordmark'>EXTEKK</text>
</svg>
```

<!-- manifest.json -->
```json
{
  "name": "EXTEKK",
  "short_name": "EXTEKK",
  "description": "The security bot that rebuilds nuked Discord servers and kills scammers before they post.",
  "start_url": "/",
  "display": "standalone",
  "theme_color": "#7CFFB2",
  "background_color": "#080808",
  "icons": [
    {
      "src": "/logo.svg",
      "sizes": "any",
      "type": "image/svg+xml",
      "purpose": "any"
    }
  ]
}
```

```text
# robots.txt
User-agent: *
Allow: /

Sitemap: /sitemap.xml
```
