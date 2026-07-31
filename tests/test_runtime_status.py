import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from gui.src.control_panel import (
    format_decimal_gb_from_bytes,
    parse_compose_ps,
    project_dir_argument,
    read_recent_events,
)
from gui.src.i18n import LANGUAGES, translate, validate_translations
from gui.src.platform_integration import enriched_subprocess_environment, set_start_at_login
from runtime_status import RuntimeStatusStore


class RuntimeStatusStoreTests(unittest.TestCase):
    def test_sms_counts_and_day_rollover(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            store = RuntimeStatusStore(temporary_directory)
            first_day = datetime(2026, 7, 31, 10, 0, tzinfo=timezone.utc)
            with patch("runtime_status.local_now", return_value=first_day):
                store.mark_sms_sent(
                    reason="Eşik aşıldı.",
                    usage_bytes=2 * 1024**3,
                    threshold_gb=1.9,
                )
                store.mark_sms_sent(
                    reason="Eşik tekrar aşıldı.",
                    usage_bytes=4 * 1024**3,
                    threshold_gb=1.9,
                )

            status = store.load()
            self.assertEqual(status["today_sms_count"], 2)
            self.assertEqual(status["total_sms_count"], 2)

            next_day = datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc)
            with patch("runtime_status.local_now", return_value=next_day):
                store.update(worker_state="idle")

            status = store.load()
            self.assertEqual(status["today_sms_count"], 0)
            self.assertEqual(status["total_sms_count"], 2)

    def test_status_and_events_are_valid_json(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            store = RuntimeStatusStore(temporary_directory)
            store.mark_check_completed(
                usage_bytes=1024**3,
                baseline_bytes=0,
                threshold_gb=1.9,
                sms_sent=False,
                deleted_sms_count=0,
            )
            status = json.loads(store.status_path.read_text(encoding="utf-8"))
            self.assertEqual(status["last_check_status"], "ok")
            events = read_recent_events(store.events_path)
            self.assertEqual(events[0]["event_type"], "check_completed")

    def test_clear_events_keeps_file_valid_and_empty(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            store = RuntimeStatusStore(temporary_directory)
            store.append_event("sample", "Sample event")
            store.clear_events()
            self.assertEqual(store.events_path.read_text(encoding="utf-8"), "")
            self.assertEqual(read_recent_events(store.events_path), [])

    def test_event_history_is_compacted_for_long_running_service(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            store = RuntimeStatusStore(temporary_directory)
            store.event_history_max_bytes = 600
            store.event_history_keep_lines = 2
            for index in range(30):
                store.append_event("sample", f"event-{index}-" + ("x" * 80))

            events = read_recent_events(store.events_path, limit=100)
            messages = [event["message"] for event in events]
            self.assertTrue(messages[0].startswith("event-29-"))
            self.assertFalse(any(message.startswith("event-0-") for message in messages))
            self.assertLessEqual(store.events_path.stat().st_size, 600)


class ControlPanelParsingTests(unittest.TestCase):
    def test_daily_usage_uses_decimal_gb_from_canonical_bytes(self):
        self.assertEqual(format_decimal_gb_from_bytes(70379999878), "70.38 GB")

    def test_parse_compose_ps_supports_array_and_json_lines(self):
        first = {"Service": "o2-ondemand-sms", "State": "running"}
        second = {"Service": "other", "State": "exited"}
        self.assertEqual(parse_compose_ps(json.dumps([first, second])), [first, second])
        json_lines = f"{json.dumps(first)}\n{json.dumps(second)}\n"
        self.assertEqual(parse_compose_ps(json_lines), [first, second])

    def test_recent_events_ignores_invalid_lines_and_returns_newest_first(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            event_path = Path(temporary_directory) / "events.jsonl"
            event_path.write_text(
                '{"event_type":"first"}\nnot-json\n{"event_type":"last"}\n',
                encoding="utf-8",
            )
            events = read_recent_events(event_path)
            self.assertEqual([event["event_type"] for event in events], ["last", "first"])

    def test_all_gui_translations_are_complete(self):
        self.assertEqual(validate_translations(), [])
        for language in LANGUAGES:
            self.assertNotEqual(translate(language, "settings"), "settings")

    def test_project_directory_argument(self):
        self.assertEqual(
            project_dir_argument(["--minimized", "--project-dir", "/tmp/project"]),
            "/tmp/project",
        )
        self.assertIsNone(project_dir_argument(["--minimized"]))

    def test_desktop_environment_includes_common_docker_cli_path(self):
        environment = enriched_subprocess_environment({"PATH": "/usr/bin:/bin"})
        self.assertIn("/usr/local/bin", environment["PATH"].split(os.pathsep))

    def test_linux_autostart_entry_launches_minimized_with_project_path(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            config_root = Path(temporary_directory)
            project_dir = config_root / "project with spaces"
            with patch("gui.src.platform_integration.sys.platform", "linux"), patch.dict(
                os.environ, {"XDG_CONFIG_HOME": str(config_root)}, clear=False
            ):
                set_start_at_login(True, project_dir)
                entry_path = config_root / "autostart" / "o2-sms-control-panel.desktop"
                content = entry_path.read_text(encoding="utf-8")
                self.assertIn("--minimized", content)
                self.assertIn("--project-dir", content)
                self.assertIn(str(project_dir), content)
                set_start_at_login(False, project_dir)
                self.assertFalse(entry_path.exists())


if __name__ == "__main__":
    unittest.main()
