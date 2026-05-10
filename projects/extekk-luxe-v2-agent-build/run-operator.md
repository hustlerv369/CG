```markdown
<!-- README.md -->
# EXTEKK Luxe v2

_Hacker-couture for
 2026: tactile brutalism meets chromatic extremes._

This is EXTEKK Luxe v2, a re-imagined digital experience. Its design language embodies 2026 trends with tactile brutalism, chromatic extremes, and scroll-driven typography. The entire project, from concept to code, was built using the Claude
Gravity 4-agent pipeline, meticulously adhering to the `LUXE-DESIGN-PLAYBOOK`.

## Live
[claudegravity.site](https://claudegravity.site)
[claudegravity.online](https://claudegravity.online)

## Run locally
Open `index.
html` in any modern web browser.

**Browser Support:** Optimized for modern Chromium, Firefox, and Safari 16+ (variable fonts required).

## Source provenance
This is a re-imagined version of extekk.mysellauth.com. The design and code were generated end-to
-end through ClaudeGravity, with the design language strictly enforced by `docs/LUXE-DESIGN-PLAYBOOK.md`.

## License
MIT License.
```

```bash
<!-- deploy.sh -->
#!/bin/bash
rsync -avz --delete ./projects/extekk-l
uxe-agent-build/ root@46.36.39.161:/var/www/extekk-luxe/ && ssh hukot 'systemctl reload caddy'
```
