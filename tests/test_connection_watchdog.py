import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import connection_watchdog as watchdog
import o2_on_demand_hack as worker
from runtime_status import RuntimeStatusStore
from tests.test_worker_usage import FakeClient

CONFIG = watchdog.WatchdogConfig()
MINUTE = 60
HOUR = 3600

SLOW = {"ping_ms": 35.0, "loss_percent": 0.0, "speed_measured": True, "download_mbps": 1.2}
FAST = {"ping_ms": 30.0, "loss_percent": 0.0, "speed_measured": True, "download_mbps": 40.0}
PING_ONLY = {"ping_ms": 30.0, "loss_percent": 0.0, "speed_measured": False}


def run(samples, start=0.0, step=MINUTE, state=None):
    """Feed samples one minute apart; return final state and (time, action) list."""
    actions = []
    now = start
    for sample in samples:
        state, action, _ = watchdog.decide(state, sample, now, CONFIG)
        if action:
            actions.append((now, action))
        now += step
    return state, actions


class EscalationTests(unittest.TestCase):
    def test_healthy_connection_never_acts(self):
        state, actions = run([FAST] * 120)
        self.assertEqual(actions, [])
        self.assertEqual(state["phase"], watchdog.PHASE_HEALTHY)

    def test_single_slow_probe_is_not_enough(self):
        state, actions = run([SLOW, FAST])
        self.assertEqual(actions, [])
        self.assertEqual(state["phase"], watchdog.PHASE_HEALTHY)

    def test_confirmed_slowness_sends_sms_first_then_restarts_after_two_minutes(self):
        _, actions = run([SLOW] * 5)
        self.assertEqual(
            actions,
            [(1 * MINUTE, watchdog.ACTION_SEND_SMS), (3 * MINUTE, watchdog.ACTION_RESTART_MODEM)],
        )

    def test_sms_that_fixes_the_connection_spends_no_restart(self):
        state, actions = run([SLOW, SLOW, FAST, FAST])
        self.assertEqual(actions, [(MINUTE, watchdog.ACTION_SEND_SMS)])
        self.assertEqual(state["phase"], watchdog.PHASE_HEALTHY)
        self.assertEqual(state["restart_times"], [])

    def test_rainy_day_restarts_follow_the_ladder_and_daily_cap(self):
        # Slow for 48 hours, measured every minute.
        _, actions = run([SLOW] * (48 * 60))
        restarts = [t for t, action in actions if action == watchdog.ACTION_RESTART_MODEM]
        sms = [t for t, action in actions if action == watchdog.ACTION_SEND_SMS]
        self.assertEqual(len(sms), 1)
        gaps = [later - earlier for earlier, later in zip(restarts, restarts[1:])]
        self.assertEqual(gaps[:3], [30 * MINUTE, 3 * HOUR, 6 * HOUR])
        for index, restart in enumerate(restarts):
            in_window = [t for t in restarts[: index + 1] if restart - t < 24 * HOUR]
            self.assertLessEqual(len(in_window), CONFIG.max_restarts_per_day)
        self.assertLessEqual(len(restarts), 8)

    def test_short_recovery_does_not_reset_the_ladder(self):
        state, actions = run([SLOW] * 4)  # SMS + first restart
        self.assertEqual(state["episode_restart_count"], 1)
        # Better for 20 minutes, then slow again: the next restart still waits
        # for the 30-minute step and counts as the second restart.
        state, _ = run([FAST] * 20, start=4 * MINUTE, state=state)
        state, actions = run([SLOW] * 30, start=24 * MINUTE, state=state)
        self.assertEqual(actions, [(33 * MINUTE, watchdog.ACTION_RESTART_MODEM)])
        self.assertEqual(state["episode_restart_count"], 2)
        self.assertEqual(state["next_action_at"], 33 * MINUTE + 3 * HOUR)

    def test_sustained_recovery_resets_the_ladder(self):
        state, _ = run([SLOW] * 4)
        state, _ = run([FAST] * 61, start=4 * MINUTE, state=state)
        self.assertEqual(state["phase"], watchdog.PHASE_HEALTHY)
        self.assertEqual(state["episode_restart_count"], 0)
        # A new episode starts again with SMS.
        _, actions = run([SLOW] * 2, start=70 * MINUTE, state=state)
        self.assertEqual(actions, [(71 * MINUTE, watchdog.ACTION_SEND_SMS)])

    def test_runs_without_speed_probe_do_not_change_the_episode(self):
        state, _ = run([SLOW])
        state, actions = run([PING_ONLY] * 10, start=MINUTE, state=state)
        self.assertEqual(actions, [])
        self.assertEqual(state["phase"], watchdog.PHASE_DEGRADED)

    def test_high_latency_alone_counts_as_slow(self):
        lag = {"ping_ms": 900.0, "loss_percent": 0.0, "speed_measured": False}
        self.assertEqual(watchdog.classify_sample(lag, watchdog.initial_state(), CONFIG), "slow")

    def test_failed_probes_never_trigger_actions(self):
        # Observed 2026-10-06: the worker container's own DNS failed while the
        # line was fine. Such failures must not restart the modem.
        broken = {"ping_ms": None, "loss_percent": 100.0, "speed_measured": True, "download_mbps": None}
        state, actions = run([broken] * 600)
        self.assertEqual(actions, [])
        self.assertEqual(state["phase"], watchdog.PHASE_HEALTHY)

    def test_threshold_follows_usual_speed_once_known(self):
        state = watchdog.initial_state()
        self.assertEqual(watchdog.slow_download_threshold(state, CONFIG), 5.0)
        state["speed_history"] = [50.0] * CONFIG.relative_min_samples
        self.assertAlmostEqual(watchdog.slow_download_threshold(state, CONFIG), 17.5)
        ten_mbps = dict(FAST, download_mbps=10.0)
        self.assertEqual(watchdog.classify_sample(ten_mbps, state, CONFIG), "slow")

    def test_speed_probe_schedule_saves_data_while_waiting(self):
        state = watchdog.initial_state()
        self.assertTrue(watchdog.needs_speed_probe(state, 0, CONFIG))
        state["last_speed_probe_at"] = 0
        self.assertFalse(watchdog.needs_speed_probe(state, 5 * MINUTE, CONFIG))
        self.assertTrue(watchdog.needs_speed_probe(state, 15 * MINUTE, CONFIG))
        state.update(phase=watchdog.PHASE_RESTART_WAIT, next_action_at=3 * HOUR, last_speed_probe_at=HOUR)
        self.assertFalse(watchdog.needs_speed_probe(state, HOUR + 60, CONFIG))
        self.assertTrue(watchdog.needs_speed_probe(state, 3 * HOUR, CONFIG))

    def test_corrupt_state_is_normalized(self):
        state, action, verdict = watchdog.decide({"phase": "???"}, FAST, 0, CONFIG)
        self.assertEqual(state["phase"], watchdog.PHASE_HEALTHY)
        self.assertIsNone(action)
        self.assertEqual(verdict, "ok")

    def test_backoff_list_from_environment(self):
        with patch.dict("os.environ", {"WATCHDOG_RESTART_BACKOFF_MINUTES": "10,60"}):
            self.assertEqual(watchdog.WatchdogConfig.from_env().restart_backoff_seconds, (600, 3600))
        with patch.dict("os.environ", {"WATCHDOG_RESTART_BACKOFF_MINUTES": "0"}):
            with self.assertRaises(ValueError):
                watchdog.WatchdogConfig.from_env()


class MeasurementTests(unittest.TestCase):
    def test_ping_reports_median_and_loss(self):
        class FakeConnection:
            def __init__(self, host, port, timeout):
                self.host = host

            def connect(self):
                if self.host == "down":
                    raise OSError("Temporary failure in name resolution")

            def request(self, method, path, headers):
                self.path = path

            def getresponse(self):
                return io.BytesIO(b"")

            def close(self):
                pass

        result = watchdog.measure_ping([("a", "/x"), ("down", "/x")], 1.0, FakeConnection)
        self.assertEqual(result["loss_percent"], 50.0)
        self.assertIsNotNone(result["ping_ms"])
        self.assertIsNone(watchdog.measure_ping([("down", "/")], 1.0, FakeConnection)["ping_ms"])

    def test_ping_targets_from_environment(self):
        with patch.dict("os.environ", {"WATCHDOG_PING_TARGETS": "a.example/204, b.example"}):
            self.assertEqual(
                watchdog.WatchdogConfig.from_env().ping_targets,
                (("a.example", "/204"), ("b.example", "/")),
            )

    def test_download_failure_returns_none(self):
        def opener(request, timeout):
            raise OSError("timeout")

        self.assertIsNone(watchdog.measure_download_mbps("http://x/{bytes}", 10, 1.0, opener=opener))

    def test_download_stops_at_the_deadline_and_rates_what_arrived(self):
        class Crawling:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def read(self, size):
                return b"x" * 1000  # endless trickle

        clock = iter(range(100))
        with patch.object(watchdog.time, "monotonic", lambda: next(clock)):
            mbps = watchdog.measure_download_mbps("http://x/{bytes}", 10**9, 5.0, opener=lambda r, timeout: Crawling())
        self.assertAlmostEqual(mbps, 0.01)

    def test_signal_strings_are_parsed(self):
        signal = watchdog.parse_signal({"rsrp": "-87dBm", "rsrq": "-7dB", "sinr": ">=30dB"})
        self.assertEqual(signal, {"rsrp": -87.0, "rsrq": -7.0, "sinr": 30.0})
        self.assertEqual(watchdog.parse_signal(None), {"rsrp": None, "rsrq": None, "sinr": None})
        self.assertTrue(watchdog.signal_is_weak({"rsrp": -110.0, "sinr": 5.0}, CONFIG))
        self.assertTrue(watchdog.signal_is_weak({"rsrp": -90.0, "sinr": -1.0}, CONFIG))
        self.assertFalse(watchdog.signal_is_weak({"rsrp": -87.0, "sinr": 13.0}, CONFIG))

    def test_download_speed_is_positive(self):
        def opener(request, timeout):
            return io.BytesIO(b"x" * 300_000)

        self.assertGreater(watchdog.measure_download_mbps("http://x/{bytes}", 300_000, 1.0, opener=opener), 0)


class WorkerWatchdogTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        data_dir = Path(self.temporary_directory.name)
        self.store = RuntimeStatusStore(data_dir)
        self.patcher = patch.multiple(
            worker,
            data_dir=data_dir,
            last_sms_info_path=data_dir / "last_sms_info.txt",
            legacy_last_sms_info_path=data_dir / "legacy.txt",
            status_store=self.store,
            watchdog_config=CONFIG,
        )
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.temporary_directory.cleanup()

    def test_sms_then_restart_through_the_worker(self):
        client = FakeClient([{}])
        for minute in range(4):
            worker.run_connection_watchdog(client, SLOW, 1000, False, now=minute * MINUTE)
        self.assertEqual(client.sms.sent, [(["80112"], "WEITER")])
        self.assertEqual(client.device.reboot_calls, 1)
        status = self.store.load()
        self.assertEqual(status["today_sms_count"], 1)
        self.assertEqual(status["connection_watchdog"]["phase"], watchdog.PHASE_RESTART_WAIT)
        event_types = [line for line in self.store.events_path.read_text().splitlines()]
        self.assertTrue(any("modem_auto_restarted" in line for line in event_types))

    def test_sms_already_sent_this_run_is_not_duplicated(self):
        client = FakeClient([{}])
        worker.run_connection_watchdog(client, SLOW, 1000, False, now=0)
        worker.run_connection_watchdog(client, SLOW, 1000, True, now=MINUTE)
        self.assertEqual(client.sms.sent, [])

    def test_failing_reboot_is_not_retried_in_a_loop(self):
        client = FakeClient([{}])

        def broken_reboot():
            client.device.reboot_calls += 1
            raise ConnectionError("connection dropped during reboot")

        client.device.reboot = broken_reboot
        for minute in range(10):
            try:
                worker.run_connection_watchdog(client, SLOW, 1000, False, now=minute * MINUTE)
            except ConnectionError:
                pass
        self.assertEqual(client.device.reboot_calls, 1)

    def test_no_decision_right_after_a_latency_watch_reboot(self):
        client = FakeClient([{}])
        self.store.update(last_modem_latency_reboot_epoch=1000)
        for minute in range(9):
            worker.run_connection_watchdog(client, SLOW, 1000, False, now=1000 + minute * MINUTE)
        self.assertEqual(client.sms.sent, [])
        self.assertEqual(self.store.load()["connection_verdict"], "grace")

    def test_slow_connection_restart_starts_the_latency_watch_cooldown(self):
        client = FakeClient([{}])
        with patch.multiple(
            worker,
            MODEM_RESTART_NOTIFY_ENABLED=True,
            MODEM_RESTART_NOTIFY_TO="0123456789",
            MODEM_RESTART_NOTIFY_TEXT="Modem yeniden baslatiliyor.",
        ):
            for minute in range(4):
                worker.run_connection_watchdog(client, SLOW, 1000, True, now=minute * MINUTE)
        status = self.store.load()
        self.assertEqual(client.device.reboot_calls, 1)
        self.assertEqual(status["last_modem_latency_reboot_epoch"], 3 * MINUTE)
        self.assertEqual(status["last_auto_modem_restart_reason"], "slow_connection")
        self.assertEqual(client.sms.sent, [(["0123456789"], "Modem yeniden baslatiliyor.")])

    def test_modem_latency_is_stored_with_the_network_sample(self):
        with patch.object(worker.watchdog, "measure_ping", return_value={"ping_ms": 30.0, "loss_percent": 0.0}), \
                patch.object(worker.watchdog, "measure_download_mbps", return_value=40.0):
            sample = worker.measure_connection(now=0, modem_ms=2.345)
        self.assertEqual(sample["modem_ms"], 2.3)
        self.assertEqual(self.store.load_network_history()[-1]["modem_ms"], 2.3)

    def _notify(self, raw_signal):
        client = FakeClient([{}])
        client.device.signal = lambda: raw_signal
        with patch.multiple(
            worker,
            MODEM_RESTART_NOTIFY_ENABLED=True,
            MODEM_RESTART_NOTIFY_TO="0123456789",
            MODEM_RESTART_NOTIFY_TEXT="Modem yeniden baslatiliyor.",
        ):
            worker.send_modem_restart_notification(client, "slow_connection")
        return client.sms.sent[0][1]

    def test_restart_sms_mentions_weak_signal(self):
        text = self._notify({"rsrp": "-112dBm", "sinr": "-3dB"})
        self.assertEqual(text, "Modem yeniden baslatiliyor. 4G sinyal zayif: RSRP -112 dBm, SINR -3 dB.")
        self.assertLessEqual(len(text), 160)

    def test_restart_sms_is_unchanged_with_good_or_unknown_signal(self):
        self.assertEqual(self._notify({"rsrp": "-87dBm", "sinr": "13dB"}), "Modem yeniden baslatiliyor.")
        self.assertEqual(self._notify(None), "Modem yeniden baslatiliyor.")

    def test_signal_is_attached_to_the_latest_sample(self):
        self.store.append_network_sample({"ping_ms": 30.0})
        client = FakeClient([{}])
        client.device.signal = lambda: {"rsrp": "-87dBm", "sinr": "13dB"}
        worker.record_modem_signal(client)
        self.assertEqual(self.store.load_network_history()[-1]["rsrp"], -87.0)
        self.assertFalse(self.store.load()["modem_signal_weak"])

    def test_network_history_is_bounded(self):
        self.store.network_history_max_samples = 3
        for value in range(5):
            self.store.append_network_sample({"ping_ms": value})
        self.assertEqual([item["ping_ms"] for item in self.store.load_network_history()], [2, 3, 4])


class ChartTests(unittest.TestCase):
    def test_series_keeps_window_and_marks_losses(self):
        from datetime import datetime, timezone

        from gui.src.network_chart import chart_series, nice_ceiling

        def at(seconds):
            return datetime.fromtimestamp(seconds, timezone.utc).isoformat()

        history = [
            {"timestamp": at(0), "ping_ms": 20.0},  # outside a 1 h window
            {"timestamp": at(5000), "ping_ms": 30.0, "speed_measured": True, "download_mbps": 12.0},
            {"timestamp": at(6000), "ping_ms": None, "loss_percent": 100.0},
            {"timestamp": at(7200), "ping_ms": 40.0, "speed_measured": True, "download_mbps": None},
        ]
        history[1]["modem_ms"] = 3.0
        history[3]["modem_ms"] = None
        older_modem = [
            {"timestamp": at(4000), "latency_ms": 2.0},
            {"timestamp": at(6000), "latency_ms": 9.0},  # already covered by the history
        ]
        series = chart_series(history, 7200, 3600, older_modem)
        self.assertEqual([value for _, value in series["ping"]], [30.0, None, 40.0])
        self.assertEqual(series["speed"], [(1 - 2200 / 3600, 12.0)])
        self.assertEqual([value for _, value in series["modem"]], [2.0, 3.0, None])
        self.assertEqual(nice_ceiling(130, 50), 200.0)
        self.assertEqual(nice_ceiling(3, 5), 5.0)

    def test_signal_quality_bands_feed_the_strip(self):
        from datetime import datetime, timezone

        from gui.src.network_chart import chart_series, signal_quality

        self.assertEqual(signal_quality(-87, 13), "good")
        self.assertEqual(signal_quality(-100, 13), "fair")
        self.assertEqual(signal_quality(-87, -2), "weak")
        self.assertIsNone(signal_quality(None, None))
        stamp = datetime.fromtimestamp(3000, timezone.utc).isoformat()
        series = chart_series([{"timestamp": stamp, "ping_ms": 30.0, "rsrp": -110, "sinr": 5}], 3600, 3600)
        self.assertEqual(series["signal"], [(1 - 600 / 3600, "weak")])

    def test_connection_status_text_is_localized(self):
        from gui.src.control_panel import connection_status_text
        from gui.src.i18n import translate

        def t(key, **values):
            return translate("en", key, **values)

        self.assertEqual(connection_status_text({}, t), "Not evaluated yet.")
        unreachable = {"connection_probe_ok": False, "connection_watchdog": {"phase": "healthy"}}
        self.assertIn("Cannot measure", connection_status_text(unreachable, t))
        status = {"connection_watchdog": {"phase": "restart_wait", "episode_restart_count": 2, "next_action_at": 0}}
        self.assertIn("2 automatic restarts", connection_status_text(status, t))


if __name__ == "__main__":
    unittest.main()
