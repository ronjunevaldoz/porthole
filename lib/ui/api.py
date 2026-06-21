import contextlib
import io
import json
import re
import types
from http.server import BaseHTTPRequestHandler
from pathlib import Path

from ..core import load_env, load_services, LOCAL_ENV, VPS_ENV
from ..deploy import port_open
from ..commands import cmd_sync, cmd_add, cmd_remove

_UI_PATH = Path(__file__).parent.parent.parent / "ui" / "index.html"


def _capture(fn, fn_args):
    buf = io.StringIO()
    ok  = True
    try:
        with contextlib.redirect_stdout(buf):
            fn(fn_args)
    except SystemExit as e:
        ok = e.code == 0
    except Exception as e:
        buf.write(str(e))
        ok = False
    out = re.sub(r"\033\[[0-9;]*m", "", buf.getvalue()).strip()
    return out, ok


class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            body = _UI_PATH.read_bytes()
            self._send(200, "text/html", body)
        elif self.path == "/api/config":
            env = {**load_env(LOCAL_ENV), **load_env(VPS_ENV)}
            from ..core import _DEFAULT_SSH_KEY
            key = Path(env.get("SSH_KEY", str(_DEFAULT_SSH_KEY))).expanduser()
            self._json({
                "vps_host":      env.get("VPS_HOST", ""),
                "domain":        env.get("DOMAIN", ""),
                "email":         env.get("EMAIL", ""),
                "frp_token":     bool(env.get("FRP_TOKEN")),
                "duckdns_token": bool(env.get("DUCKDNS_TOKEN")),
                "ssh_key_ok":    key.exists(),
            })
        elif self.path == "/api/services":
            self._json([
                {"name": s.name, "local_port": s.local_port,
                 "remote_port": s.remote_port, "local_host": s.local_host}
                for s in load_services()
            ])
        else:
            self._send(404, "text/plain", b"not found")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body   = json.loads(self.rfile.read(length)) if length else {}

        if self.path == "/api/sync":
            out, ok = _capture(cmd_sync, None)
            self._json({"ok": ok, "output": out})

        elif self.path == "/api/status":
            env  = {**load_env(LOCAL_ENV), **load_env(VPS_ENV)}
            vps  = env.get("VPS_HOST", "")
            svcs = load_services()
            rows = [{"name": s.name, "up": port_open(vps, s.remote_port)} for s in svcs]
            lines = "\n".join(f"{'✓' if r['up'] else '✗'}  {r['name']}" for r in rows)
            self._json({"ok": True, "output": lines or "No services.", "services": rows})

        elif self.path == "/api/add":
            a   = types.SimpleNamespace(
                name=body["name"], local_port=body["local_port"],
                remote_port=body["remote_port"], docker=None, no_sync=False,
            )
            out, ok = _capture(cmd_add, a)
            self._json({"ok": ok, "output": out})

        elif self.path == "/api/remove":
            a   = types.SimpleNamespace(name=body["name"], no_sync=False)
            out, ok = _capture(cmd_remove, a)
            self._json({"ok": ok, "output": out})

        else:
            self._send(404, "text/plain", b"not found")

    def _send(self, code, ctype, body):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, data):
        self._send(200, "application/json", json.dumps(data).encode())

    def log_message(self, *_):
        pass
