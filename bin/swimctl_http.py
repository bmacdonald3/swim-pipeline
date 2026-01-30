#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import os, json, subprocess, time

import psutil

HOST = "0.0.0.0"
PORT = 8129
SERVICE = "swim-receiver.service"

def sh(cmd):
    return subprocess.run(cmd, shell=False, capture_output=True, text=True)

def require_token(handler, qs):
    token = qs.get("token", [""])[0]
    expect = os.environ.get("SWIMCTL_TOKEN", "")
    if not expect or token != expect:
        handler.send_response(403)
        handler.send_header("Content-Type", "text/plain; charset=utf-8")
        handler.end_headers()
        handler.wfile.write(b"forbidden")
        return False
    return True

def systemd_is_active():
    r = sh(["/bin/systemctl", "is-active", SERVICE])
    return (r.stdout.strip() or r.stderr.strip()).strip()

def systemd_action(action):
    r = sh(["/bin/systemctl", action, SERVICE])
    ok = (r.returncode == 0)
    return ok, (r.stdout.strip() or r.stderr.strip()).strip()

def azure_health():
    try:
        import pyodbc
        server = os.environ["AZURE_SQL_SERVER"]
        db = os.environ["AZURE_SQL_DATABASE"]
        uid = os.environ["AZURE_SQL_USER"]
        pwd = os.environ["AZURE_SQL_PASSWORD"]

        cs = (
            "DRIVER={ODBC Driver 18 for SQL Server};"
            f"SERVER=tcp:{server},1433;"
            f"DATABASE={db};UID={uid};PWD={pwd};"
            "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=10;"
        )
        cn = pyodbc.connect(cs)
        cur = cn.cursor()
        cur.execute("SELECT COUNT(*) FROM dbo.flights")
        total = int(cur.fetchone()[0])
        cur.execute("SELECT MAX([timestamp]) FROM dbo.flights")
        last_ts = cur.fetchone()[0]
        cn.close()
        return {"ok": True, "rowcount": total, "last_timestamp": str(last_ts) if last_ts else None}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def pi_metrics():
    vm = psutil.virtual_memory()
    du = psutil.disk_usage("/")
    load1, load5, load15 = os.getloadavg()
    return {
        "time": int(time.time()),
        "cpu_percent": psutil.cpu_percent(interval=0.2),
        "load1": load1,
        "mem_percent": vm.percent,
        "mem_available_mb": int(vm.available / (1024*1024)),
        "disk_percent": du.percent,
        "disk_free_gb": round(du.free / (1024**3), 2),
        "service_state": systemd_is_active(),
        "swim_log_bytes": int(os.path.getsize("/home/bmacdonald3/flight_stream_live.log")) if os.path.exists("/home/bmacdonald3/flight_stream_live.log") else 0,
    }

class Handler(BaseHTTPRequestHandler):
    def _json(self, obj, code=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        qs = parse_qs(u.query)

        if u.path == "/status":
            self._json({"service": SERVICE, "state": systemd_is_active()})
            return

        if u.path == "/metrics":
            self._json(pi_metrics())
            return

        if u.path == "/azure":
            self._json(azure_health())
            return

        if u.path in ("/start", "/stop", "/restart"):
            if not require_token(self, qs):
                return
            action = "start" if u.path == "/start" else "stop" if u.path == "/stop" else "restart"
            ok, msg = systemd_action(action)
            self._json({"ok": ok, "action": action, "message": msg}, code=200 if ok else 500)
            return

        self._json({"error": "not found"}, code=404)

    def log_message(self, format, *args):
        return

if __name__ == "__main__":
    HTTPServer((HOST, PORT), Handler).serve_forever()
