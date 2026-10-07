"""Persistent runtime status and event history for the SMS worker.

The worker runs inside Docker while the desktop control panel runs on the host.
Both processes communicate through small JSON files in the bind-mounted data
directory.  Writes to the status file are atomic so the GUI never sees a
partially-written document.
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import fcntl
except ImportError:  # Windows
    fcntl = None  # type: ignore[assignment]

try:
    import msvcrt
except ImportError:  # POSIX
    msvcrt = None  # type: ignore[assignment]


SCHEMA_VERSION = 1


def local_now() -> datetime:
    return datetime.now().astimezone()


def iso_now() -> str:
    return local_now().isoformat(timespec="seconds")


class RuntimeStatusStore:
    """Store the latest worker state plus an append-only event history."""

    def __init__(self, data_dir: str | os.PathLike[str]) -> None:
        self.data_dir = Path(data_dir)
        self.status_path = self.data_dir / "status.json"
        self.events_path = self.data_dir / "events.jsonl"
        self.lock_path = self.data_dir / ".runtime_status.lock"
        self.network_history_path = self.data_dir / "network_history.json"
        self.network_history_max_samples = int(os.getenv("NETWORK_HISTORY_MAX_SAMPLES", "1440"))
        self.event_history_max_bytes = int(os.getenv("EVENT_HISTORY_MAX_BYTES", "2000000"))
        self.event_history_keep_lines = int(os.getenv("EVENT_HISTORY_KEEP_LINES", "2000"))
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any]:
        try:
            value = json.loads(self.status_path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}

    def update(self, **fields: Any) -> dict[str, Any]:
        with self._locked():
            return self._update_unlocked(**fields)

    def _update_unlocked(self, **fields: Any) -> dict[str, Any]:
        status = self.load()
        today = local_now().date().isoformat()
        if status.get("statistics_day") != today:
            status["statistics_day"] = today
            status["today_sms_count"] = 0

        status.update(fields)
        status["schema_version"] = SCHEMA_VERSION
        status["updated_at"] = iso_now()
        self._write_atomic(status)
        return status

    def append_event(self, event_type: str, message: str, **fields: Any) -> dict[str, Any]:
        event = {
            "schema_version": SCHEMA_VERSION,
            "timestamp": iso_now(),
            "event_type": event_type,
            "message": message,
            **fields,
        }
        event_line = json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n"
        with self._locked():
            with self.events_path.open("a", encoding="utf-8") as event_file:
                event_file.write(event_line)
                event_file.flush()
                os.fsync(event_file.fileno())
            self._compact_events_unlocked()
        return event

    def mark_check_started(self) -> None:
        self.update(
            worker_state="checking",
            last_check_started_at=iso_now(),
            last_error=None,
        )

    def mark_sms_sent(
        self,
        *,
        reason: str,
        usage_bytes: int,
        threshold_gb: float,
        trigger_message_keys: list[str] | None = None,
        trigger_code: str | None = None,
    ) -> None:
        with self._locked():
            status = self.load()
            today = local_now().date().isoformat()
            today_count = int(status.get("today_sms_count", 0) or 0)
            if status.get("statistics_day") != today:
                today_count = 0

            total_count = int(status.get("total_sms_count", 0) or 0)
            processed_trigger_keys = list(status.get("processed_trigger_message_keys", []))
            for message_key in trigger_message_keys or []:
                if message_key not in processed_trigger_keys:
                    processed_trigger_keys.append(message_key)
            processed_trigger_keys = processed_trigger_keys[-200:]
            sent_at = iso_now()
            self._update_unlocked(
                statistics_day=today,
                today_sms_count=today_count + 1,
                total_sms_count=total_count + 1,
                last_sms_at=sent_at,
                last_sms_reason=reason,
                last_sms_usage_bytes=usage_bytes,
                last_sms_usage_gb=round(usage_bytes / (1024**3), 3),
                current_usage_bytes=usage_bytes,
                current_usage_gb=round(usage_bytes / (1024**3), 3),
                baseline_usage_bytes=usage_bytes,
                baseline_usage_gb=round(usage_bytes / (1024**3), 3),
                processed_trigger_message_keys=processed_trigger_keys,
                last_o2_trigger_code=trigger_code,
            )
        event_fields = {
            "usage_bytes": usage_bytes,
            "usage_gb": round(usage_bytes / (1024**3), 3),
            "threshold_gb": threshold_gb,
            "recipient": "80112",
        }
        if trigger_code:
            event_fields["trigger_code"] = trigger_code
            event_fields["trigger_message_count"] = len(trigger_message_keys or [])
        self.append_event(
            "sms_sent",
            reason,
            **event_fields,
        )

    def mark_check_completed(
        self,
        *,
        usage_bytes: int,
        baseline_bytes: int,
        threshold_gb: float,
        sms_sent: bool,
        deleted_sms_count: int,
    ) -> None:
        checked_at = iso_now()
        usage_gb = usage_bytes / (1024**3)
        baseline_gb = baseline_bytes / (1024**3)
        self.update(
            worker_state="idle",
            last_check_at=checked_at,
            last_check_status="ok",
            last_error=None,
            current_usage_bytes=usage_bytes,
            current_usage_gb=round(usage_gb, 3),
            baseline_usage_bytes=baseline_bytes,
            baseline_usage_gb=round(baseline_gb, 3),
            threshold_gb=threshold_gb,
            last_check_sms_sent=sms_sent,
            last_deleted_sms_count=deleted_sms_count,
        )
        self.append_event(
            "check_completed",
            "SMS gönderildi." if sms_sent else "SMS gönderme eşiğine henüz ulaşılmadı.",
            usage_bytes=usage_bytes,
            usage_gb=round(usage_gb, 3),
            baseline_usage_gb=round(baseline_gb, 3),
            threshold_gb=threshold_gb,
            sms_sent=sms_sent,
            deleted_sms_count=deleted_sms_count,
        )

    def mark_check_failed(self, error: BaseException) -> None:
        error_text = f"{type(error).__name__}: {error}"
        failed_at = iso_now()
        self.update(
            worker_state="error",
            last_check_at=failed_at,
            last_check_status="error",
            last_error=error_text,
        )
        self.append_event("check_failed", error_text)

    def mark_manual_action_completed(self, action: str) -> None:
        self.update(
            last_manual_action=action,
            last_manual_action_at=iso_now(),
            last_manual_action_status="ok",
            last_manual_action_error=None,
        )

    def mark_manual_action_failed(self, action: str, error: BaseException) -> None:
        error_text = f"{type(error).__name__}: {error}"
        self.update(
            last_manual_action=action,
            last_manual_action_at=iso_now(),
            last_manual_action_status="error",
            last_manual_action_error=error_text,
        )
        self.append_event(
            "manual_action_failed",
            error_text,
            action=action,
        )

    def load_network_history(self) -> list[dict[str, Any]]:
        try:
            value = json.loads(self.network_history_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return []
        return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []

    def append_network_sample(self, sample: dict[str, Any]) -> None:
        """Keep a bounded latency/speed history for the GUI chart (24 h at 1/min)."""
        record = {"timestamp": iso_now(), **sample}
        with self._locked():
            history = self.load_network_history()
            history.append(record)
            history = history[-self.network_history_max_samples:]
            self._write_network_history_unlocked(history)

    def annotate_last_network_sample(self, **fields: Any) -> None:
        """Add values measured later in the same run (modem signal) to the newest sample."""
        with self._locked():
            history = self.load_network_history()
            if not history:
                return
            history[-1].update(fields)
            self._write_network_history_unlocked(history)

    def _write_network_history_unlocked(self, history: list[dict[str, Any]]) -> None:
        temporary_path = self.network_history_path.with_suffix(f".json.{os.getpid()}.tmp")
        with temporary_path.open("w", encoding="utf-8") as history_file:
            json.dump(history, history_file, ensure_ascii=False, separators=(",", ":"))
            history_file.flush()
            os.fsync(history_file.fileno())
        os.replace(temporary_path, self.network_history_path)

    def clear_events(self) -> None:
        """Clear event history while excluding concurrent worker writes."""
        with self._locked():
            with self.events_path.open("w", encoding="utf-8") as event_file:
                event_file.flush()
                os.fsync(event_file.fileno())

    def _write_atomic(self, status: dict[str, Any]) -> None:
        temporary_path = self.status_path.with_suffix(f".json.{os.getpid()}.tmp")
        with temporary_path.open("w", encoding="utf-8") as status_file:
            json.dump(status, status_file, ensure_ascii=False, indent=2, sort_keys=True)
            status_file.write("\n")
            status_file.flush()
            os.fsync(status_file.fileno())
        os.replace(temporary_path, self.status_path)

    def _compact_events_unlocked(self) -> None:
        try:
            file_size = self.events_path.stat().st_size
        except OSError:
            return
        if file_size <= self.event_history_max_bytes:
            return

        with self.events_path.open("rb") as event_file:
            seek_position = max(0, file_size - self.event_history_max_bytes)
            event_file.seek(seek_position)
            if seek_position:
                event_file.readline()  # Discard a partial JSONL record.
            retained_lines = event_file.readlines()[-self.event_history_keep_lines:]

        temporary_path = self.events_path.with_suffix(f".jsonl.{os.getpid()}.tmp")
        with temporary_path.open("wb") as compacted_file:
            compacted_file.writelines(retained_lines)
            compacted_file.flush()
            os.fsync(compacted_file.fileno())
        os.replace(temporary_path, self.events_path)

    @contextmanager
    def _locked(self):
        with self.lock_path.open("a+b") as lock_file:
            if fcntl is not None:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            elif msvcrt is not None:
                # msvcrt locks a byte range; ensure that byte zero exists.
                lock_file.seek(0, os.SEEK_END)
                if lock_file.tell() == 0:
                    lock_file.write(b"\0")
                    lock_file.flush()
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
            else:  # pragma: no cover - every supported platform has one API.
                raise RuntimeError("Bu platformda desteklenen bir dosya kilidi bulunamadı.")
            try:
                yield
            finally:
                if fcntl is not None:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                elif msvcrt is not None:
                    lock_file.seek(0)
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
