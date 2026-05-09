```markdown
<!-- README.md -->
# Smile Today
Daily positive affirmations delivered to your browser via web notifications
.

Smile Today delivers a daily dose of positivity directly to your browser. Receive uplifting messages through web notifications, designed to encourage and inspire. It's a small reminder to pause, reflect, and smile.

## Try it
Experience daily joy at https://claudegravity.online

## Run locally
To run
 Smile Today on your local machine, simply open `index.html` located in the `projects/smile-today/` directory in any modern web browser.

## Browser support
Requires Chrome, Edge, Firefox, or Safari 16+ for full Web Notification functionality.

## License
Licensed under the MIT License.


```bash
<!-- deploy.sh -->
#!/bin/bash
rsync -avz --delete projects/smile-today/ root@46.36.39.161:/var/www/smile-today/
ssh hukot 'systemctl reload caddy'
```
