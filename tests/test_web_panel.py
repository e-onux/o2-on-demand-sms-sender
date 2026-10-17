import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path

import web_panel


class WebPanelTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        data_dir = Path(self.temporary_directory.name)
        (data_dir / "status.json").write_text(json.dumps({"today_sms_count": 2}), encoding="utf-8")
        (data_dir / "network_history.json").write_text(json.dumps([{"ping_ms": 30.0}]), encoding="utf-8")
        (data_dir / "events.jsonl").write_text(
            '{"event_type":"sms_sent","message":"a"}\nnot json\n{"event_type":"check_completed","message":"b"}\n',
            encoding="utf-8",
        )
        self.actions = []
        self.clock = [1000.0]
        self.state = web_panel.PanelState(
            data_dir, "s3cret", action_runner=self._run, clock=lambda: self.clock[0]
        )
        self.server = web_panel.build_server("127.0.0.1", 0, self.state)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.temporary_directory.cleanup()

    def _run(self, action):
        self.actions.append(action)
        return True

    def request(self, method, path, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=5)
        connection.request(method, path, headers=headers or {})
        response = connection.getresponse()
        body = response.read()
        connection.close()
        return response, body

    def post_action(self, action="restart-modem", password="s3cret"):
        headers = {} if password is None else {"X-Panel-Password": password}
        response, body = self.request("POST", f"/api/actions/{action}", headers)
        return response.status, json.loads(body)

    def test_page_and_read_only_api_need_no_password(self):
        response, body = self.request("GET", "/")
        self.assertEqual(response.status, 200)
        self.assertIn(b'data-i18n="app_title"', body)
        self.assertIn("script-src 'self'", response.getheader("Content-Security-Policy"))
        self.assertEqual(response.getheader("X-Frame-Options"), "DENY")
        status = json.loads(self.request("GET", "/api/status")[1])
        self.assertEqual(status["today_sms_count"], 2)
        self.assertTrue(status["web_actions_enabled"])
        self.assertEqual(json.loads(self.request("GET", "/api/history")[1]), [{"ping_ms": 30.0}])
        events = json.loads(self.request("GET", "/api/events")[1])
        self.assertEqual([e["event_type"] for e in events], ["check_completed", "sms_sent"])

    def test_translations_follow_the_requested_language(self):
        bundle = json.loads(self.request("GET", "/api/i18n?lang=de")[1])
        self.assertEqual(bundle["language"], "de")
        self.assertEqual(bundle["strings"]["chart_legend_internet"], "Internet-Ping")
        self.assertEqual(set(bundle["languages"]), {"tr", "en", "de", "pl", "ru"})
        fallback = json.loads(self.request("GET", "/api/i18n?lang=xx")[1])
        self.assertEqual(fallback["language"], "en")

    def test_every_key_used_by_the_page_exists_in_every_language(self):
        import re

        from gui.src.i18n import LANGUAGES, TRANSLATIONS

        web = Path(web_panel.STATIC_DIR)
        html = (web / "index.html").read_text(encoding="utf-8")
        script = (web / "app.js").read_text(encoding="utf-8")
        keys = set(re.findall(r'data-(?:i18n|i18n-placeholder|confirm-key|done-key)="([a-z0-9_]+)"', html))
        keys |= set(re.findall(r'\bt\("([a-z0-9_]+)"', script))
        keys |= set(re.findall(r'"((?:event|runtime|web)_[a-z0-9_]+)"', script))
        keys |= {f"chart_window_{w}" for w in ("1h", "6h", "24h")}
        keys |= {f"signal_{q}" for q in ("good", "fair", "weak")}
        self.assertGreater(len(keys), 50)
        for key in sorted(keys):
            self.assertIn(key, TRANSLATIONS, key)
            for language in LANGUAGES:
                self.assertTrue(TRANSLATIONS[key].get(language), f"{key}:{language}")

    def test_unknown_and_traversal_paths_are_not_served(self):
        for path in ("/../web_panel.py", "/web/../web_panel.py", "/status.json", "/%2e%2e/etc/passwd"):
            self.assertEqual(self.request("GET", path)[0].status, 404, path)

    def test_correct_password_runs_the_action_once(self):
        self.assertEqual(self.post_action(), (200, {"ok": True, "action": "restart-modem"}))
        self.assertEqual(self.actions, ["restart-modem"])

    def test_cross_site_request_without_the_header_is_rejected(self):
        self.assertEqual(self.post_action(password=None)[0], 403)
        self.assertEqual(self.actions, [])

    def test_wrong_password_locks_out_and_unlocks_later(self):
        for _ in range(web_panel.MAX_FAILED_LOGINS):
            self.assertEqual(self.post_action(password="nope")[0], 401)
        self.assertEqual(self.post_action()[0], 429)  # even the right password is refused now
        self.clock[0] += web_panel.LOCKOUT_SECONDS
        self.assertEqual(self.post_action()[0], 200)
        self.assertEqual(self.actions, ["restart-modem"])

    def test_old_failures_expire(self):
        for _ in range(web_panel.MAX_FAILED_LOGINS - 1):
            self.post_action(password="nope")
        self.clock[0] += web_panel.LOCKOUT_SECONDS
        self.assertEqual(self.post_action(password="nope")[0], 401)
        self.assertEqual(self.post_action()[0], 200)

    def test_actions_are_disabled_without_a_password(self):
        self.state.password = ""
        self.assertEqual(self.post_action(password=""), (403, {"error": "actions_disabled"}))
        self.assertFalse(json.loads(self.request("GET", "/api/status")[1])["web_actions_enabled"])
        self.assertEqual(self.actions, [])

    def test_unknown_action_and_parallel_action_are_refused(self):
        self.assertEqual(self.post_action(action="rm-rf")[0], 404)
        self.state.action_lock.acquire()
        try:
            self.assertEqual(self.post_action(), (409, {"error": "busy"}))
        finally:
            self.state.action_lock.release()
        self.assertEqual(self.actions, [])

    def test_failed_action_is_reported(self):
        self.state.action_runner = lambda action: False
        self.assertEqual(self.post_action(action="send-sms"), (502, {"ok": False, "action": "send-sms"}))


if __name__ == "__main__":
    unittest.main()
