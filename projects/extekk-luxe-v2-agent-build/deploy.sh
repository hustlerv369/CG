#!/bin/bash
rsync -avz --delete ./projects/extekk-l
uxe-agent-build/ root@46.36.39.161:/var/www/extekk-luxe/ && ssh hukot 'systemctl reload caddy'
