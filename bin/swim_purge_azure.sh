#!/bin/bash
set -euo pipefail

# Safety: require explicit argument
if [[ "${1:-}" != "YES_PURGE" ]]; then
  echo "Refusing. Run with: YES_PURGE"
  exit 2
fi

# Optional: take a backup/export before purge (recommended)
# /usr/local/bin/swim_export_azure.sh

# Stop downloads first to prevent re-population mid-purge
sudo systemctl stop swimctl-download.service

# >>> REPLACE THIS with your actual purge logic <<<
# Examples could be:
# - az cosmosdb sql container delete / truncate style operation
# - SQL: delete from table ...
# - custom python: swimctl_admin.py --purge
echo "TODO: implement purge command here"
exit 1
