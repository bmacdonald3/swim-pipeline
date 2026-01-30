#!/bin/bash
set -euo pipefail

REPO="$HOME/swim-pipeline"

mkdir -p "$REPO/bin" "$REPO/systemd"

sudo cp -a /usr/local/bin/swimctl_download.sh "$REPO/bin/" || true
sudo cp -a /usr/local/bin/swimctl_download.py "$REPO/bin/" || true
sudo cp -a /usr/local/bin/swimctl_http.py     "$REPO/bin/" || true
sudo cp -a /usr/local/bin/swim_purge_azure.sh "$REPO/bin/" || true

sudo cp -a /etc/systemd/system/swimctl-download.service "$REPO/systemd/" 2>/dev/null || true
sudo cp -a /etc/systemd/system/swimctl-http.service     "$REPO/systemd/" 2>/dev/null || true
sudo cp -a /etc/systemd/system/swim-receiver.service    "$REPO/systemd/" 2>/dev/null || true

sudo chown -R "$USER:$USER" "$REPO/bin" "$REPO/systemd" || true
chmod +x "$REPO/bin"/*.sh "$REPO/bin"/*.py 2>/dev/null || true

cd "$REPO"
git add -A
if ! git diff --cached --quiet; then
  git commit -m "Backup from Pi: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  git push
else
  echo "No changes to commit."
fi
