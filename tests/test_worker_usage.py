import datetime
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import o2_on_demand_hack as worker
from runtime_status import RuntimeStatusStore


# Captured read-only from the real Huawei modem on 2026-07-31. This fixture is
# intentionally unpadded and contains the stale 45-hour counter that previously
# appeared in the UI as 65.536 GiB.
REAL_STALE_MONTH_STATS = {
    "CurrentMonthDownload": "66785634227",
    "CurrentMonthUpload": "3594365651",
    "MonthDuration": "162296",
    "MonthLastClearTime": "2026-7-30",
}

AFTER_RESET_MONTH_STATS = {
    "CurrentMonthDownload": "125000000",
    "CurrentMonthUpload": "25000000",
    "MonthDuration": "3",
    "MonthLastClearTime": "2026-7-31",
}

O2_EXHAUSTED_SMS = (
    "Du hast Dein aktiviertes Highspeed-Datenvolumen verbraucht. Ab jetzt surfst Du bis zum "
    "Ende des Tages mit reduzierter Geschwindigkeit. Du möchtest mit Highspeed weitersurfen? "
    "Dann einfach mit WEITER auf diese SMS antworten, um kostenlos weitere 2 GB "
    "Highspeed-Datenvolumen abzurufen. Dein o2 Team"
)

O2_80_PERCENT_SMS = (
    " Du hast 80% Deines aktivierten Highspeed-Datenvolumens verbraucht. Um kostenlos weitere "
    "2 GB Highspeed-Datenvolumen abzurufen, einfach mit WEITER auf diese SMS antworten. "
    "Dein o2 Team"
)


class FakeMonitoring:
    def __init__(self, responses):
        self.responses = list(responses)
        self.clear_calls = 0

    def month_statistics(self):
        if len(self.responses) > 1:
            return self.responses.pop(0)
        return self.responses[0]

    def set_clear_traffic(self):
        self.clear_calls += 1
        return "OK"


class FakeSms:
    def __init__(self):
        self.sent = []
        self.deleted = []

    def send_sms(self, recipients, message):
        self.sent.append((recipients, message))

    def delete_sms(self, index):
        self.deleted.append(str(index))


class FakeUser:
    def __init__(self):
        self.logout_calls = 0

    def logout(self):
        self.logout_calls += 1


class FakeClient:
    def __init__(self, responses):
        self.monitoring = FakeMonitoring(responses)
        self.sms = FakeSms()
        self.user = FakeUser()


class PagingSms(FakeSms):
    def __init__(self, sent_messages):
        super().__init__()
        self.sent_messages = sent_messages
        self.list_calls = []

    def get_sms_list(
        self,
        page,
        box_type,
        read_count,
        sort_type,
        ascending,
        unread_preferred,
    ):
        self.list_calls.append((box_type, page, read_count))
        messages = self.sent_messages if box_type == worker.BoxTypeEnum.LOCAL_SENT else []
        start = (page - 1) * read_count
        page_messages = messages[start:start + read_count]
        return {
            "Count": str(len(messages)),
            "Messages": {"Message": page_messages} if page_messages else None,
        }


class WorkerUsageTests(unittest.TestCase):
    def test_exact_user_supplied_o2_messages_are_triggers(self):
        self.assertEqual(
            worker.classify_o2_data_trigger_sms(O2_EXHAUSTED_SMS),
            "highspeed_exhausted",
        )
        self.assertEqual(
            worker.classify_o2_data_trigger_sms(O2_80_PERCENT_SMS),
            "highspeed_80_percent",
        )
        self.assertIsNone(worker.classify_o2_data_trigger_sms("Bitte mit WEITER antworten"))

    def test_parse_modem_date_accepts_real_unpadded_format(self):
        expected = datetime.date(2026, 7, 30)
        self.assertEqual(worker.parse_modem_date("2026-7-30"), expected)
        self.assertEqual(worker.parse_modem_date("2026-07-30"), expected)
        self.assertEqual(worker.parse_modem_date("2026-7-30 12:34:56"), expected)

    def test_stale_real_counter_is_never_returned_as_daily_usage(self):
        client = FakeClient([REAL_STALE_MONTH_STATS, AFTER_RESET_MONTH_STATS])
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            with patch.multiple(
                worker,
                data_dir=data_dir,
                last_sms_info_path=data_dir / "last_sms_info.txt",
                legacy_last_sms_info_path=data_dir / "missing.txt",
                status_store=RuntimeStatusStore(data_dir),
                local_today=lambda: datetime.date(2026, 7, 31),
            ):
                usage_bytes, was_reset = worker.read_daily_data_usage(client)

        self.assertTrue(was_reset)
        self.assertEqual(client.monitoring.clear_calls, 1)
        self.assertEqual(usage_bytes, 150000000)
        self.assertNotEqual(usage_bytes, 70379999878)

    def test_manual_sms_uses_verified_post_reset_counter(self):
        client = FakeClient([REAL_STALE_MONTH_STATS, AFTER_RESET_MONTH_STATS])
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            store = RuntimeStatusStore(data_dir)
            with patch.multiple(
                worker,
                data_dir=data_dir,
                last_sms_info_path=data_dir / "last_sms_info.txt",
                legacy_last_sms_info_path=data_dir / "missing.txt",
                status_store=store,
                attempt_login=lambda: client,
                local_today=lambda: datetime.date(2026, 7, 31),
            ):
                worker.send_manual_sms()

            status = store.load()

        self.assertEqual(client.sms.sent, [(["80112"], "WEITER")])
        self.assertEqual(client.monitoring.clear_calls, 1)
        self.assertEqual(status["current_usage_bytes"], 150000000)
        self.assertEqual(status["baseline_usage_bytes"], 150000000)
        self.assertEqual(status["last_sms_usage_bytes"], 150000000)

    def test_no_sms_when_reset_cannot_be_verified(self):
        client = FakeClient([REAL_STALE_MONTH_STATS] * 5)
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            with patch.multiple(
                worker,
                data_dir=data_dir,
                last_sms_info_path=data_dir / "last_sms_info.txt",
                legacy_last_sms_info_path=data_dir / "missing.txt",
                status_store=RuntimeStatusStore(data_dir),
                local_today=lambda: datetime.date(2026, 7, 31),
            ), patch.object(worker.time, "sleep", return_value=None):
                with self.assertRaises(RuntimeError):
                    worker.check_data_usage_and_send_sms(client)

        self.assertEqual(client.sms.sent, [])

    def test_o2_trigger_sends_once_resets_baseline_and_is_idempotent(self):
        current_stats = {
            "CurrentMonthDownload": str(3 * 1024**3),
            "CurrentMonthUpload": "0",
            "MonthLastClearTime": "2026-7-31",
        }
        client = FakeClient([current_stats])
        messages = [
            {
                "Index": "101",
                "Date": "2026-07-31 21:10:00",
                "Phone": "O2",
                "Content": O2_80_PERCENT_SMS,
                "_direction": "inbox",
            },
            {
                "Index": "102",
                "Date": "2026-07-31 21:11:00",
                "Phone": "O2",
                "Content": O2_EXHAUSTED_SMS,
                "_direction": "inbox",
            },
        ]
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            store = RuntimeStatusStore(data_dir)
            with patch.multiple(
                worker,
                data_dir=data_dir,
                last_sms_info_path=data_dir / "last_sms_info.txt",
                legacy_last_sms_info_path=data_dir / "missing.txt",
                status_store=store,
                local_today=lambda: datetime.date(2026, 7, 31),
            ):
                trigger = worker.find_o2_sms_trigger(messages)
                usage_bytes, baseline_bytes, sms_sent = worker.check_data_usage_and_send_sms(
                    client, trigger
                )
                replayed_trigger = worker.find_o2_sms_trigger(messages)

            status = store.load()

        self.assertTrue(sms_sent)
        self.assertEqual(len(client.sms.sent), 1)
        self.assertEqual(usage_bytes, 3 * 1024**3)
        self.assertEqual(baseline_bytes, usage_bytes)
        self.assertEqual(status["baseline_usage_bytes"], usage_bytes)
        self.assertEqual(status["last_o2_trigger_code"], "highspeed_exhausted")
        self.assertEqual(len(status["processed_trigger_message_keys"]), 2)
        self.assertIsNone(replayed_trigger)

    def test_retention_keeps_newest_three_incoming_and_sent_combined(self):
        client = FakeClient([AFTER_RESET_MONTH_STATS])
        messages = [
            {"Index": str(index), "Date": f"2026-07-31 20:0{index}:00", "_direction": direction}
            for index, direction in (
                (1, "inbox"),
                (2, "sent"),
                (3, "inbox"),
                (4, "sent"),
                (5, "inbox"),
            )
        ]
        deleted_count = worker.retain_recent_sms(client, messages, keep_count=3)
        self.assertEqual(deleted_count, 2)
        self.assertEqual(client.sms.deleted, ["2", "1"])

    def test_sms_reader_uses_supported_twenty_item_pagination(self):
        sent_messages = [
            {
                "Index": str(index),
                "Date": f"2026-07-31 20:{index:02d}:00",
                "Content": "WEITER",
            }
            for index in range(25)
        ]
        client = FakeClient([AFTER_RESET_MONTH_STATS])
        client.sms = PagingSms(sent_messages)

        messages = worker.read_all_sms_messages(client)

        self.assertEqual(len(messages), 25)
        sent_calls = [
            (page, read_count)
            for box_type, page, read_count in client.sms.list_calls
            if box_type == worker.BoxTypeEnum.LOCAL_SENT
        ]
        self.assertEqual(sent_calls, [(1, 20), (2, 20)])
        self.assertTrue(all(call[2] == 20 for call in client.sms.list_calls))


if __name__ == "__main__":
    unittest.main()
