#!/usr/bin/env python3
import os
import sys
import time
from datetime import datetime

def load_env(path):
    if not os.path.exists(path):
        print(f"[ERROR] Env file not found: {path}", file=sys.stderr)
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)

def main():
    env_path = "/home/bmacdonald3/.swimctl_env"
    load_env(env_path)

    print("[INFO] swimctl_download starting")
    print(f"[INFO] Time: {datetime.utcnow().isoformat()}Z")
    print(f"[INFO] Running as UID={os.getuid()}")

    # Sanity checks for expected env vars (adjust names if needed)
    expected = [
        "AZURE_SQL_SERVER",
        "AZURE_SQL_DATABASE",
        "AZURE_SQL_USER",
    ]
    missing = [k for k in expected if k not in os.environ]
    if missing:
        print(f"[WARN] Missing env vars: {missing}", file=sys.stderr)

    # Placeholder for real SWIM/FAA logic
    print("[INFO] Placeholder downloader ran successfully")

    # Write a last-success marker for HA
    try:
        with open("/home/bmacdonald3/.swimctl_last_success", "w") as f:
            f.write(datetime.utcnow().isoformat() + "Z\n")
    except Exception as e:
        print(f"[WARN] Could not write last success file: {e}", file=sys.stderr)

    print("[INFO] swimctl_download finished OK")
    return 0

if __name__ == "__main__":
    sys.exit(main())
