"""Optional web panel: a browser alternative to the desktop control panel.

Runs next to the worker (supervisord program ``web-panel``) and serves the same
runtime files the desktop GUI reads. Viewing is open on the LAN; modem actions
need WEB_PANEL_PASSWORD and are disabled while it is empty. Modem mutations go
through ``modem_actions.py`` exactly like the desktop GUI, so this module never
opens a modem session itself.

Security notes for a LAN-only, plain-HTTP service:
- the password travels in a custom header that browsers only send from this
  page's own script, so another website cannot trigger an action (CSRF);
- repeated wrong passwords lock actions for that client for a while;
- only one modem action runs at a time;
- responses carry a strict Content-Security-Policy and no-frame headers.
"""

import hmac
import json
import os
import subprocess
import sys
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from gui.src.i18n import LANGUAGES, TRANSLATIONS

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "web"
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
}
ACTIONS = ("send-sms", "clear-inbox", "restart-modem")
EVENT_LIMIT = 100
MAX_FAILED_LOGINS = 5
LOCKOUT_SECONDS = 300
ACTION_TIMEOUT_SECONDS = 180
SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
        "img-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
    ),
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}


def read_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def read_recent_events(path, limit=EVENT_LIMIT):
    """Newest-first events; the file is bounded by RuntimeStatusStore."""
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()[-limit:]
    except OSError:
        return []
    events = []
    for line in reversed(lines):
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def translation_bundle(language):
    """All UI strings for one language (English fallback), shared with the desktop panel."""
    if language not in LANGUAGES:
        language = "en"
    return {
        "language": language,
        "languages": LANGUAGES,
        "strings": {key: choices.get(language, choices["en"]) for key, choices in TRANSLATIONS.items()},
    }


def run_modem_action(action):
    """Same subprocess boundary the desktop GUI uses for modem mutations."""
    result = subprocess.run(
        [sys.executable, str(APP_DIR / "modem_actions.py"), action],
        capture_output=True,
        text=True,
        timeout=ACTION_TIMEOUT_SECONDS,
        check=False,
    )
    return result.returncode == 0


class PanelState:
    """Shared, thread-safe server state: login throttling and the action lock."""

    def __init__(self, data_dir, password, action_runner=run_modem_action, clock=time.monotonic):
        self.data_dir = Path(data_dir)
        self.password = password or ""
        self.action_runner = action_runner
        self.clock = clock
        self.action_lock = threading.Lock()
        self._failures = {}
        self._failures_lock = threading.Lock()

    @property
    def actions_enabled(self):
        return bool(self.password)

    def locked_out(self, client):
        with self._failures_lock:
            count, since = self._failures.get(client, (0, 0.0))
            if count >= MAX_FAILED_LOGINS and self.clock() - since < LOCKOUT_SECONDS:
                return True
            if count >= MAX_FAILED_LOGINS:
                self._failures.pop(client, None)
            return False

    def check_password(self, client, supplied):
        ok = hmac.compare_digest(supplied.encode("utf-8"), self.password.encode("utf-8"))
        with self._failures_lock:
            if ok:
                self._failures.pop(client, None)
            else:
                count, since = self._failures.get(client, (0, 0.0))
                if self.clock() - since >= LOCKOUT_SECONDS:
                    count = 0  # an old typo should not count toward a lockout
                self._failures[client] = (count + 1, self.clock())
        return ok


class PanelHandler(BaseHTTPRequestHandler):
    server_version = "O2WebPanel"
    sys_version = ""
    state: PanelState

    def log_message(self, format, *args):  # noqa: A002 - signature from the base class
        # Never log headers; they carry the action password.
        sys.stderr.write(f"web-panel {self.client_address[0]} {format % args}\n")

    def _send(self, status, body, content_type="application/json; charset=utf-8"):
        payload = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        for name, value in SECURITY_HEADERS.items():
            self.send_header(name, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(payload)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        state = self.state
        if path in STATIC_FILES:
            name, content_type = STATIC_FILES[path]
            try:
                self._send(HTTPStatus.OK, (STATIC_DIR / name).read_bytes(), content_type)
            except OSError:
                self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})
        elif path == "/api/status":
            status = read_json(state.data_dir / "status.json", {})
            status = status if isinstance(status, dict) else {}
            status["web_actions_enabled"] = state.actions_enabled
            self._send(HTTPStatus.OK, status)
        elif path == "/api/history":
            history = read_json(state.data_dir / "network_history.json", [])
            self._send(HTTPStatus.OK, history if isinstance(history, list) else [])
        elif path == "/api/i18n":
            language = parse_qs(urlsplit(self.path).query).get("lang", [""])[0]
            self._send(HTTPStatus.OK, translation_bundle(language))
        elif path == "/api/events":
            self._send(HTTPStatus.OK, read_recent_events(state.data_dir / "events.jsonl"))
        else:
            self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    do_HEAD = do_GET

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        prefix = "/api/actions/"
        action = path[len(prefix):] if path.startswith(prefix) else ""
        state = self.state
        client = self.client_address[0]
        if action not in ACTIONS:
            return self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})
        if not state.actions_enabled:
            return self._send(HTTPStatus.FORBIDDEN, {"error": "actions_disabled"})
        supplied = self.headers.get("X-Panel-Password")
        if supplied is None:
            # Browsers only add custom headers from this page's own script.
            return self._send(HTTPStatus.FORBIDDEN, {"error": "missing_header"})
        if state.locked_out(client):
            return self._send(HTTPStatus.TOO_MANY_REQUESTS, {"error": "locked_out"})
        if not state.check_password(client, supplied):
            return self._send(HTTPStatus.UNAUTHORIZED, {"error": "wrong_password"})
        if not state.action_lock.acquire(blocking=False):
            return self._send(HTTPStatus.CONFLICT, {"error": "busy"})
        try:
            ok = state.action_runner(action)
        except subprocess.TimeoutExpired:
            ok = False
        finally:
            state.action_lock.release()
        self.log_message("action %s %s", action, "ok" if ok else "failed")
        status = HTTPStatus.OK if ok else HTTPStatus.BAD_GATEWAY
        self._send(status, {"ok": ok, "action": action})


def build_server(host, port, state):
    handler = type("BoundPanelHandler", (PanelHandler,), {"state": state})
    return ThreadingHTTPServer((host, port), handler)


def main():
    if os.getenv("WEB_PANEL_ENABLED", "").strip().casefold() not in {"1", "true", "yes", "on"}:
        print("Web panel disabled (set WEB_PANEL_ENABLED=true to enable).")
        return
    data_dir = Path(os.getenv("SMS_DATA_DIR", str(APP_DIR / "data")))
    host = os.getenv("WEB_PANEL_HOST", "0.0.0.0")
    port = int(os.getenv("WEB_PANEL_PORT", "8095"))
    state = PanelState(data_dir, os.getenv("WEB_PANEL_PASSWORD", ""))
    server = build_server(host, port, state)
    mode = "with actions" if state.actions_enabled else "read-only (no WEB_PANEL_PASSWORD)"
    print(f"Web panel listening on {host}:{port}, {mode}.")
    server.serve_forever()


if __name__ == "__main__":
    main()
