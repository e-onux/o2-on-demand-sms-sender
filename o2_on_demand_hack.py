import argparse
import datetime
import hashlib
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

from huawei_lte_api.Client import Client
from huawei_lte_api.AuthorizedConnection import AuthorizedConnection
from huawei_lte_api.exceptions import LoginErrorAlreadyLoginException
from huawei_lte_api.enums.sms import BoxTypeEnum
from dotenv import load_dotenv

import connection_watchdog as watchdog
from runtime_status import RuntimeStatusStore

load_dotenv()  # Load the .env file

username = os.getenv('API_USER')
password = os.getenv('API_PASSWORD')

# Enter your modem's IP address and, if necessary, the port number here.
# Accept values like "192.168.8.1", "192.168.8.1:8080", "http://192.168.8.1"
host = os.getenv("MODEM_HOST", "192.168.8.1")
host = host.replace("http://", "").replace("https://", "").rstrip("/")

port = os.getenv("MODEM_PORT")  # optional
netloc = f"{host}:{port}" if port else host

url = f"http://{netloc}/"  # base URL to your modem

app_dir = Path(__file__).resolve().parent
data_dir = Path(os.getenv("SMS_DATA_DIR", str(app_dir / "data")))
last_sms_info_path = data_dir / "last_sms_info.txt"
legacy_last_sms_info_path = app_dir / "last_sms_info.txt"
sms_threshold_gb = float(os.getenv("SMS_THRESHOLD_GB", "1.9"))
status_store = RuntimeStatusStore(data_dir)
watchdog_config = watchdog.WatchdogConfig.from_env()

MODEM_DATE_PATTERN = re.compile(r"^\s*(\d{4})-(\d{1,2})-(\d{1,2})")
PING_TIME_PATTERN = re.compile(r"time[=<]\s*([0-9]+(?:\.[0-9]+)?)\s*ms")
COUNTER_REFRESH_RETRIES = 4
COUNTER_REFRESH_DELAY_SECONDS = 0.5
SMS_RETENTION_COUNT = int(os.getenv("SMS_RETENTION_COUNT", "3"))


def env_bool(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().casefold() not in {"0", "false", "no", "off"}


def env_int(name, default):
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        print(f"Invalid integer for {name}={value!r}; using {default}.")
        return default


def normalize_host(value):
    host_value = str(value or "").replace("http://", "").replace("https://", "").strip().rstrip("/")
    if "/" in host_value:
        host_value = host_value.split("/", 1)[0]
    if ":" in host_value:
        host_value = host_value.split(":", 1)[0]
    return host_value


MODEM_LATENCY_WATCH_ENABLED = env_bool("MODEM_LATENCY_WATCH_ENABLED", True)
MODEM_LATENCY_HOST = normalize_host(os.getenv("MODEM_LATENCY_HOST") or host)
MODEM_LATENCY_THRESHOLD_MS = env_int("MODEM_LATENCY_THRESHOLD_MS", 800)
MODEM_LATENCY_PING_TIMEOUT_SECONDS = max(1, env_int("MODEM_LATENCY_PING_TIMEOUT_SECONDS", 2))
MODEM_LATENCY_BAD_WINDOW_SECONDS = max(30, env_int("MODEM_LATENCY_BAD_WINDOW_SECONDS", 300))
MODEM_LATENCY_REBOOT_AFTER_BAD_CHECKS = max(1, env_int("MODEM_LATENCY_REBOOT_AFTER_BAD_CHECKS", 3))
MODEM_LATENCY_REBOOT_COOLDOWN_SECONDS = max(60, env_int("MODEM_LATENCY_REBOOT_COOLDOWN_SECONDS", 300))
MODEM_LATENCY_HISTORY_LIMIT = max(10, env_int("MODEM_LATENCY_HISTORY_LIMIT", 180))
MODEM_RESTART_NOTIFY_ENABLED = env_bool("MODEM_RESTART_NOTIFY_ENABLED", True)
MODEM_RESTART_NOTIFY_TO = (
    os.getenv("MODEM_RESTART_NOTIFY_TO")
    or os.getenv("SMS_DEFAULT_TO")
    or ""
).strip()
MODEM_RESTART_NOTIFY_TEXT = os.getenv(
    "MODEM_RESTART_NOTIFY_TEXT",
    "Modem yeniden baslatiliyor.",
)

O2_TRIGGER_REASONS = {
    "highspeed_exhausted": "O2 yüksek hız veri hacmi tükendi SMS'i alındı.",
    "highspeed_80_percent": "O2 yüksek hız veri hacmi %80 SMS'i alındı.",
}

def attempt_login(max_retries=3):
    retries = 0
    while retries < max_retries:
        try:
            connection = AuthorizedConnection(url, username=username, password=password)
            client = Client(connection)
            print("Logged in!")
            return client
        except LoginErrorAlreadyLoginException:
            print("Already logged in, retrying after delay...")
            time.sleep(10)
            retries += 1
    raise Exception("Failed to login after several attempts.")

def read_last_sms_info():
    """Read the persistent baseline, migrating the legacy file when present."""
    for candidate in (last_sms_info_path, legacy_last_sms_info_path):
        try:
            last_data = candidate.read_text(encoding="utf-8").strip().split(',')
            last_byte = int(last_data[0])
            last_time = float(last_data[1])
            if candidate != last_sms_info_path:
                write_last_sms_info(last_byte, last_time)
            return last_byte, last_time
        except (FileNotFoundError, ValueError, IndexError, OSError):
            continue
    return 0, 0

def write_last_sms_info(total_data, timestamp=None):
    data_dir.mkdir(parents=True, exist_ok=True)
    temporary_path = last_sms_info_path.with_suffix(".txt.tmp")
    temporary_path.write_text(
        f"{total_data},{timestamp if timestamp is not None else time.time()}",
        encoding="utf-8",
    )
    os.replace(temporary_path, last_sms_info_path)


def normalize_sms_text(value):
    text = " ".join(str(value or "").casefold().split())
    return re.sub(r"\s*%\s*", "% ", text)


def classify_o2_data_trigger_sms(content):
    """Return a high-confidence trigger code for known O2 allowance messages."""
    text = normalize_sms_text(content)
    required_fragments = (
        "mit weiter auf diese sms antworten",
        "weitere 2 gb highspeed-datenvolumen",
        "dein o2 team",
    )
    if not all(fragment in text for fragment in required_fragments):
        return None
    if "du hast 80% deines aktivierten highspeed-datenvolumens verbraucht" in text:
        return "highspeed_80_percent"
    if "du hast dein aktiviertes highspeed-datenvolumen verbraucht" in text:
        return "highspeed_exhausted"
    return None


def sms_message_key(message):
    fingerprint_source = "|".join(
        str(message.get(field, ""))
        for field in ("_direction", "Index", "Date", "Phone", "Content")
    )
    return hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest()


def messages_from_sms_response(response, direction):
    if not isinstance(response, dict) or str(response.get("Count", "0")) == "0":
        return []
    messages_node = response.get("Messages") or {}
    messages = messages_node.get("Message", []) if isinstance(messages_node, dict) else []
    if isinstance(messages, dict):
        messages = [messages]
    result = []
    for message in messages if isinstance(messages, list) else []:
        if isinstance(message, dict):
            result.append({**message, "_direction": direction})
    return result


def read_all_sms_messages(client):
    """Read every page of the local and SIM inbox/sent folders."""
    box_definitions = (
        (BoxTypeEnum.LOCAL_INBOX, "inbox"),
        (BoxTypeEnum.LOCAL_SENT, "sent"),
        (BoxTypeEnum.SIM_INBOX, "inbox"),
        (BoxTypeEnum.SIM_SENT, "sent"),
    )
    messages = []
    seen = set()
    for box_type, direction in box_definitions:
        page = 1
        page_size = 20  # Huawei rejects oversized ReadCount values with 100005.
        while True:
            response = client.sms.get_sms_list(
                page=page,
                box_type=box_type,
                read_count=page_size,
                sort_type=0,
                ascending=0,
                unread_preferred=0,
            )
            page_messages = messages_from_sms_response(response, direction)
            for message in page_messages:
                identity = (str(message.get("Index")), direction)
                if identity not in seen:
                    seen.add(identity)
                    messages.append(message)

            try:
                total_count = int(response.get("Count", 0))
            except (AttributeError, TypeError, ValueError):
                total_count = 0
            if not page_messages or len(page_messages) < page_size or page * page_size >= total_count:
                break
            page += 1
    return messages


def find_o2_sms_trigger(messages):
    processed_keys = set(status_store.load().get("processed_trigger_message_keys", []))
    matches = []
    for message in messages:
        if message.get("_direction") != "inbox":
            continue
        trigger_code = classify_o2_data_trigger_sms(message.get("Content"))
        message_key = sms_message_key(message)
        if trigger_code and message_key not in processed_keys:
            matches.append((trigger_code, message_key))
    if not matches:
        return None

    trigger_codes = {code for code, _ in matches}
    primary_code = (
        "highspeed_exhausted"
        if "highspeed_exhausted" in trigger_codes
        else "highspeed_80_percent"
    )
    return {
        "code": primary_code,
        "reason": O2_TRIGGER_REASONS[primary_code],
        "message_keys": [message_key for _, message_key in matches],
    }


def parse_sms_datetime(value):
    try:
        return datetime.datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
    except ValueError as error:
        raise ValueError(f"Unsupported SMS date: {value!r}") from error


def retain_recent_sms(client, messages, keep_count=SMS_RETENTION_COUNT):
    """Keep the newest N incoming/sent messages combined and delete the rest."""
    if keep_count < 0:
        raise ValueError("SMS_RETENTION_COUNT cannot be negative")
    ordered_messages = sorted(
        messages,
        key=lambda message: (
            parse_sms_datetime(message.get("Date")),
            int(message.get("Index", 0)),
        ),
        reverse=True,
    )
    deleted_count = 0
    for message in ordered_messages[keep_count:]:
        client.sms.delete_sms(message['Index'])
        deleted_count += 1
        print(f"Old SMS deleted (index: {message['Index']}).")
    return deleted_count


def ping_command_for_host(hostname):
    ping_path = shutil.which("ping")
    if not ping_path:
        return None
    if sys.platform == "darwin":
        timeout_ms = MODEM_LATENCY_PING_TIMEOUT_SECONDS * 1000
        return [ping_path, "-n", "-c", "1", "-W", str(timeout_ms), hostname]
    return [
        ping_path,
        "-n",
        "-c",
        "1",
        "-W",
        str(MODEM_LATENCY_PING_TIMEOUT_SECONDS),
        hostname,
    ]


def measure_tcp_latency_ms(hostname, port_number=80):
    started_at = time.monotonic()
    try:
        with socket.create_connection(
            (hostname, port_number),
            timeout=MODEM_LATENCY_PING_TIMEOUT_SECONDS,
        ):
            pass
    except OSError as error:
        print(f"Modem TCP latency probe failed: {type(error).__name__}: {error}")
        return None
    return (time.monotonic() - started_at) * 1000


def measure_modem_latency_ms(hostname=MODEM_LATENCY_HOST):
    hostname = normalize_host(hostname)
    if not hostname:
        return None

    command = ping_command_for_host(hostname)
    if command:
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=MODEM_LATENCY_PING_TIMEOUT_SECONDS + 1,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            print(f"Modem ping probe failed: {type(error).__name__}: {error}")
        else:
            output = "\n".join(part for part in (result.stdout, result.stderr) if part)
            match = PING_TIME_PATTERN.search(output)
            if result.returncode == 0 and match:
                return float(match.group(1))
            print(f"Modem ping probe failed for {hostname}.")

    return measure_tcp_latency_ms(hostname)


def modem_latency_sample_is_bad(latency_ms, threshold_ms=MODEM_LATENCY_THRESHOLD_MS):
    return latency_ms is None or float(latency_ms) >= threshold_ms


def latency_history_from_status(status):
    history = status.get("modem_latency_history", [])
    if not isinstance(history, list):
        return []
    return [sample for sample in history if isinstance(sample, dict)]


def record_modem_latency_sample(latency_ms):
    if not MODEM_LATENCY_WATCH_ENABLED:
        return {"enabled": False, "should_reboot": False}

    observed_at = time.time()
    observed_at_iso = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    is_bad = modem_latency_sample_is_bad(latency_ms)

    status = status_store.load()
    last_reboot_epoch = float(status.get("last_modem_latency_reboot_epoch") or 0)
    window_start = max(
        observed_at - MODEM_LATENCY_BAD_WINDOW_SECONDS,
        last_reboot_epoch,
    )
    history = latency_history_from_status(status)
    sample = {
        "timestamp": observed_at_iso,
        "epoch": observed_at,
        "latency_ms": None if latency_ms is None else round(float(latency_ms), 1),
        "ok": not is_bad,
    }
    history.append(sample)
    history = history[-MODEM_LATENCY_HISTORY_LIMIT:]
    bad_samples = [
        item
        for item in history
        if not bool(item.get("ok", True)) and float(item.get("epoch") or 0) >= window_start
    ]
    bad_count = len(bad_samples)
    cooldown_remaining = max(
        0,
        int(MODEM_LATENCY_REBOOT_COOLDOWN_SECONDS - (observed_at - last_reboot_epoch)),
    )
    should_reboot = (
        bad_count >= MODEM_LATENCY_REBOOT_AFTER_BAD_CHECKS
        and cooldown_remaining == 0
    )

    status_store.update(
        modem_latency_watch_enabled=True,
        modem_latency_host=MODEM_LATENCY_HOST,
        modem_latency_last_ms=sample["latency_ms"],
        modem_latency_last_ok=sample["ok"],
        modem_latency_last_checked_at=observed_at_iso,
        modem_latency_threshold_ms=MODEM_LATENCY_THRESHOLD_MS,
        modem_latency_bad_window_seconds=MODEM_LATENCY_BAD_WINDOW_SECONDS,
        modem_latency_reboot_after_bad_checks=MODEM_LATENCY_REBOOT_AFTER_BAD_CHECKS,
        modem_latency_reboot_cooldown_seconds=MODEM_LATENCY_REBOOT_COOLDOWN_SECONDS,
        modem_latency_bad_count=bad_count,
        modem_latency_reboot_cooldown_remaining_seconds=cooldown_remaining,
        modem_latency_history=history,
    )

    if is_bad:
        latency_text = (
            "unreachable" if latency_ms is None else f"{float(latency_ms):.1f} ms"
        )
        status_store.append_event(
            "modem_latency_high",
            f"Modem latency is high ({latency_text}).",
            latency_ms=sample["latency_ms"],
            threshold_ms=MODEM_LATENCY_THRESHOLD_MS,
            bad_sample_count=bad_count,
            reboot_after_bad_checks=MODEM_LATENCY_REBOOT_AFTER_BAD_CHECKS,
            window_seconds=MODEM_LATENCY_BAD_WINDOW_SECONDS,
            cooldown_remaining_seconds=cooldown_remaining,
        )

    return {
        "enabled": True,
        "should_reboot": should_reboot,
        "latency_ms": sample["latency_ms"],
        "bad_count": bad_count,
        "cooldown_remaining": cooldown_remaining,
        "observed_at": observed_at,
        "observed_at_iso": observed_at_iso,
    }


def masked_phone_number(value):
    if not value:
        return ""
    if len(value) <= 4:
        return "****"
    return f"{'*' * max(0, len(value) - 4)}{value[-4:]}"


def read_modem_signal(client):
    """Return parsed RSRP/RSRQ/SINR, or None when the modem does not report them."""
    try:
        signal = watchdog.parse_signal(client.device.signal())
    except Exception as error:
        print(f"Reading modem signal failed: {type(error).__name__}: {error}")
        return None
    return signal if any(value is not None for value in signal.values()) else None


def weak_signal_note(signal):
    """ASCII text keeps the SMS in the GSM alphabet (one 160-character part)."""
    if not watchdog.signal_is_weak(signal, watchdog_config):
        return ""
    parts = [
        f"{label} {signal[key]:g} {unit}"
        for key, label, unit in (("rsrp", "RSRP", "dBm"), ("sinr", "SINR", "dB"))
        if signal.get(key) is not None
    ]
    return " 4G sinyal zayif: " + ", ".join(parts) + "."


def send_modem_restart_notification(client, reason):
    if not MODEM_RESTART_NOTIFY_ENABLED or not MODEM_RESTART_NOTIFY_TO:
        return False
    try:
        text = MODEM_RESTART_NOTIFY_TEXT + weak_signal_note(read_modem_signal(client))
        client.sms.send_sms([MODEM_RESTART_NOTIFY_TO], text)
        status_store.append_event(
            "modem_restart_notification_sent",
            "Modem restart SMS notification was sent.",
            reason=reason,
            recipient=masked_phone_number(MODEM_RESTART_NOTIFY_TO),
        )
        print("Modem restart SMS notification sent.")
        return True
    except Exception as error:
        status_store.append_event(
            "modem_restart_notification_failed",
            f"Modem restart SMS notification failed: {type(error).__name__}: {error}",
            reason=reason,
        )
        print(f"Modem restart SMS notification failed: {type(error).__name__}: {error}")
        return False


def restart_modem_for_latency(client, decision):
    notification_sent = send_modem_restart_notification(client, "modem_latency")
    client.device.reboot()
    restarted_at = time.time()
    restarted_at_iso = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    status_store.update(
        worker_state="idle",
        last_check_at=restarted_at_iso,
        last_check_status="ok",
        last_error=None,
        last_check_sms_sent=False,
        last_deleted_sms_count=0,
        last_modem_latency_reboot_at=restarted_at_iso,
        last_modem_latency_reboot_epoch=restarted_at,
        last_auto_modem_restart_reason="modem_latency",
        last_modem_restart_notification_sent=notification_sent,
        modem_latency_bad_count=0,
        modem_latency_reboot_cooldown_remaining_seconds=MODEM_LATENCY_REBOOT_COOLDOWN_SECONDS,
    )
    status_store.append_event(
        "modem_latency_reboot",
        "Modem restart was requested because latency stayed high.",
        latency_ms=decision.get("latency_ms"),
        bad_sample_count=decision.get("bad_count"),
        threshold_ms=MODEM_LATENCY_THRESHOLD_MS,
        window_seconds=MODEM_LATENCY_BAD_WINDOW_SECONDS,
        cooldown_seconds=MODEM_LATENCY_REBOOT_COOLDOWN_SECONDS,
        notification_sent=notification_sent,
    )
    print("Modem restart requested automatically because latency stayed high.")

def local_today():
    return datetime.datetime.now().astimezone().date()


def parse_modem_date(value):
    """Parse Huawei dates with padded or unpadded month/day components."""
    match = MODEM_DATE_PATTERN.match(str(value))
    if match is None:
        raise ValueError(f"Unsupported modem date: {value!r}")
    year, month, day = (int(part) for part in match.groups())
    return datetime.date(year, month, day)


def usage_bytes_from_month_stats(month_stats):
    try:
        download = int(month_stats['CurrentMonthDownload'])
        upload = int(month_stats['CurrentMonthUpload'])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"Invalid month statistics payload: {month_stats!r}") from error
    if download < 0 or upload < 0:
        raise ValueError(f"Negative traffic counter in payload: {month_stats!r}")
    return download + upload


def read_daily_data_usage(client):
    """Return the verified daily byte counter, resetting a stale counter first."""
    month_stats = client.monitoring.month_statistics()
    last_clear_date = parse_modem_date(month_stats.get('MonthLastClearTime'))
    today = local_today()
    print(f"Last clear time: {last_clear_date}, Today: {today}")

    if last_clear_date == today:
        return usage_bytes_from_month_stats(month_stats), False

    client.monitoring.set_clear_traffic()
    write_last_sms_info(0)
    print("Data usage has been reset; verifying the modem counter.")
    status_store.append_event(
        "data_usage_reset",
        "Günlük veri sayacı sıfırlandı.",
        previous_clear_date=str(last_clear_date),
    )

    # Do not trust the pre-reset payload. Huawei firmware may apply the clear
    # asynchronously, so only return data after the reported clear date is today.
    for attempt in range(COUNTER_REFRESH_RETRIES):
        refreshed_stats = client.monitoring.month_statistics()
        refreshed_date = parse_modem_date(refreshed_stats.get('MonthLastClearTime'))
        if refreshed_date == today:
            return usage_bytes_from_month_stats(refreshed_stats), True
        if attempt + 1 < COUNTER_REFRESH_RETRIES:
            time.sleep(COUNTER_REFRESH_DELAY_SECONDS)

    raise RuntimeError(
        "Modem traffic counter did not report today's clear date after reset "
        f"(last value: {refreshed_stats.get('MonthLastClearTime')!r})."
    )

def check_data_usage_and_send_sms(client, trigger=None):
    total_data, was_reset = read_daily_data_usage(client)
    total_usage_gib = total_data / (1024**3)
    print(f"Current usage: {total_usage_gib:.2f} GiB")
    last_byte, last_time = read_last_sms_info()
    last_usage_gib = last_byte / (1024**3)
    age_text = f"{int((time.time() - last_time) / 60)} min ago" if last_time else "no baseline yet"
    print(f"Last usage: {last_usage_gib:.2f} GiB - {age_text}.")
    if was_reset or total_data < last_byte:  # Counter reset or stale state file.
        write_last_sms_info(0)
        last_byte = 0
        last_usage_gib = 0
        status_store.append_event(
            "sms_baseline_reset",
            "SMS veri eşiği başlangıç değeri sıfırlandı.",
            usage_bytes=total_data,
        )

    sms_sent = False
    if trigger is not None:
        client.sms.send_sms(['80112'], 'WEITER')
        write_last_sms_info(total_data)
        status_store.mark_sms_sent(
            reason=trigger["reason"],
            usage_bytes=total_data,
            threshold_gb=sms_threshold_gb,
            trigger_message_keys=trigger["message_keys"],
            trigger_code=trigger["code"],
        )
        sms_sent = True
        last_byte = total_data
        print(f"SMS sent due to O2 trigger: {trigger['code']}.")
    elif total_usage_gib >= last_usage_gib + sms_threshold_gb:
        client.sms.send_sms(['80112'], 'WEITER')
        write_last_sms_info(total_data)
        reason = f"{sms_threshold_gb:.2f} GiB yeni veri kullanım eşiği aşıldı."
        status_store.mark_sms_sent(
            reason=reason,
            usage_bytes=total_data,
            threshold_gb=sms_threshold_gb,
        )
        sms_sent = True
        last_byte = total_data
        print("SMS sent due to data usage threshold being exceeded.")

    return total_data, last_byte, sms_sent


def clear_sms_inbox(client):
    sms_list = client.sms.get_sms_list()
    if not isinstance(sms_list, dict) or str(sms_list.get('Count', '0')) == '0':
        print("No SMS messages to delete or error retrieving SMS list.")
        return 0

    messages = sms_list.get('Messages', {}).get('Message', [])
    if isinstance(messages, dict):
        messages = [messages]

    deleted_count = 0
    for sms in messages:
        client.sms.delete_sms(sms['Index'])
        deleted_count += 1
        # Do not print message content or sender details into Docker logs.
        print(f"SMS deleted (index: {sms['Index']}).")
    return deleted_count


def logout(client):
    if client is None:
        return
    try:
        client.user.logout()
        print("Successfully logged out.")
    except Exception as error:
        print(f"Error during logout: {error}")


def send_manual_sms():
    """Send WEITER on demand and move the automatic-send baseline forward."""
    client = None
    try:
        client = attempt_login()
        # Manual and automatic sends must use the exact same verified daily
        # counter path. Never label an unchecked month payload as daily usage.
        total_data, _ = read_daily_data_usage(client)
        client.sms.send_sms(['80112'], 'WEITER')

        # Treat a manual SMS like an automatic one so the next periodic check
        # does not immediately send another message for the same usage.
        write_last_sms_info(total_data)
        reason = "Kontrol panelinden manuel olarak gönderildi."
        status_store.mark_sms_sent(
            reason=reason,
            usage_bytes=total_data,
            threshold_gb=sms_threshold_gb,
        )
        status_store.update(
            current_usage_bytes=total_data,
            current_usage_gb=round(total_data / (1024**3), 3),
            baseline_usage_bytes=total_data,
            baseline_usage_gb=round(total_data / (1024**3), 3),
            threshold_gb=sms_threshold_gb,
        )
        status_store.mark_manual_action_completed("send_sms")
        print("Manual WEITER SMS sent successfully.")
    except Exception as error:
        status_store.mark_manual_action_failed("send_sms", error)
        print(f"Manual SMS failed: {type(error).__name__}: {error}")
        raise
    finally:
        logout(client)


def clear_sms_inbox_manually():
    client = None
    try:
        client = attempt_login()
        deleted_count = clear_sms_inbox(client)
        status_store.mark_manual_action_completed("clear_inbox")
        status_store.append_event(
            "sms_inbox_cleared",
            f"SMS kutusu temizlendi; {deleted_count} mesaj silindi.",
            deleted_sms_count=deleted_count,
        )
        print(f"SMS inbox cleared successfully ({deleted_count} deleted).")
    except Exception as error:
        status_store.mark_manual_action_failed("clear_inbox", error)
        print(f"Clearing SMS inbox failed: {type(error).__name__}: {error}")
        raise
    finally:
        logout(client)


def restart_modem_manually():
    """Request a modem reboot after confirmation in the desktop control panel."""
    client = None
    try:
        client = attempt_login()
        notification_sent = send_modem_restart_notification(client, "manual")
        client.device.reboot()
        status_store.mark_manual_action_completed("restart_modem")
        status_store.update(last_modem_restart_notification_sent=notification_sent)
        status_store.append_event(
            "modem_restarted",
            "Modem restart was requested from the control panel.",
            notification_sent=notification_sent,
        )
        print("Modem restart requested successfully.")
    except Exception as error:
        status_store.mark_manual_action_failed("restart_modem", error)
        print(f"Modem restart failed: {type(error).__name__}: {error}")
        raise
    finally:
        logout(client)


def measure_connection(now=None, modem_ms=None):
    """Measure latency every run and download speed only when the watchdog needs it."""
    now = time.time() if now is None else now
    state = watchdog.normalized_state(status_store.load().get("connection_watchdog"))
    sample = watchdog.measure_ping(
        watchdog_config.ping_targets, watchdog_config.ping_timeout_seconds
    )
    # Stored with the sample so the GUI can chart modem and internet ping on one time axis.
    sample["modem_ms"] = None if modem_ms is None else round(float(modem_ms), 1)
    sample["speed_measured"] = watchdog.needs_speed_probe(state, now, watchdog_config)
    if sample["speed_measured"]:
        sample["download_mbps"] = watchdog.measure_download_mbps(
            watchdog_config.speed_url,
            watchdog_config.speed_bytes,
            watchdog_config.speed_timeout_seconds,
        )
    status_store.append_network_sample(sample)
    status_store.update(connection_probe_ok=sample["ping_ms"] is not None)
    return sample


WATCHDOG_RESTART_GRACE_SECONDS = 600


def record_modem_signal(client):
    """Attach this run's 4G signal to the network sample for the GUI chart."""
    signal = read_modem_signal(client)
    if signal is None:
        return None
    status_store.annotate_last_network_sample(rsrp=signal["rsrp"], sinr=signal["sinr"])
    status_store.update(
        modem_signal=signal,
        modem_signal_weak=watchdog.signal_is_weak(signal, watchdog_config),
    )
    return signal

WATCHDOG_EVENT_MESSAGES = {
    "connection_slow_sms": "Bağlantı yavaş; önce WEITER SMS'i gönderildi.",
    "modem_auto_restarted": "Bağlantı SMS'ten sonra da yavaş; modem otomatik yeniden başlatıldı.",
    "connection_recovered": "Bağlantı yeniden normal hızda.",
    "restart_limit_reached": "Günlük otomatik yeniden başlatma sınırına ulaşıldı; bekleniyor.",
}


def run_connection_watchdog(client, sample, total_data, sms_already_sent, now=None):
    """Apply one escalation step. The new state is saved before acting, so a
    failing or connection-dropping action can never be retried in a tight loop."""
    now = time.time() if now is None else now
    status = status_store.load()
    last_latency_reboot = float(status.get("last_modem_latency_reboot_epoch") or 0)
    if last_latency_reboot and 0 <= now - last_latency_reboot < WATCHDOG_RESTART_GRACE_SECONDS:
        # Right after any automatic restart everything looks slow while the
        # modem boots; deciding now would stack a second restart on the first.
        state = watchdog.normalized_state(status.get("connection_watchdog"))
        if sample.get("speed_measured"):
            state["last_speed_probe_at"] = now  # keep the 15-minute probe schedule
        status_store.update(connection_watchdog=state, connection_verdict="grace")
        return None
    previous = watchdog.normalized_state(status.get("connection_watchdog"))
    state, action, verdict = watchdog.decide(previous, sample, now, watchdog_config)
    status_store.update(
        connection_watchdog=state,
        connection_verdict=verdict,
        connection_slow_threshold_mbps=round(
            watchdog.slow_download_threshold(state, watchdog_config), 2
        ),
    )
    details = {
        "ping_ms": sample.get("ping_ms"),
        "loss_percent": sample.get("loss_percent"),
        "download_mbps": sample.get("download_mbps"),
    }

    if previous["phase"] != watchdog.PHASE_HEALTHY and state["phase"] == watchdog.PHASE_HEALTHY:
        status_store.append_event(
            "connection_recovered", WATCHDOG_EVENT_MESSAGES["connection_recovered"], **details
        )
    elif (
        action is None
        and state["phase"] == watchdog.PHASE_RESTART_WAIT
        and len(state["restart_times"]) >= watchdog_config.max_restarts_per_day
        and previous.get("next_action_at") != state.get("next_action_at")
    ):
        status_store.append_event(
            "restart_limit_reached", WATCHDOG_EVENT_MESSAGES["restart_limit_reached"], **details
        )

    if action == watchdog.ACTION_SEND_SMS:
        reason = WATCHDOG_EVENT_MESSAGES["connection_slow_sms"]
        if not sms_already_sent:
            client.sms.send_sms(['80112'], 'WEITER')
            write_last_sms_info(total_data)
            status_store.mark_sms_sent(
                reason=reason, usage_bytes=total_data, threshold_gb=sms_threshold_gb
            )
        status_store.append_event("connection_slow_sms", reason, **details)
        print("Connection slow: WEITER SMS sent, re-checking shortly.")
    elif action == watchdog.ACTION_RESTART_MODEM:
        status_store.append_event(
            "modem_auto_restarted",
            WATCHDOG_EVENT_MESSAGES["modem_auto_restarted"],
            restart_number=state["episode_restart_count"],
            next_allowed_at=datetime.datetime.fromtimestamp(state["next_action_at"])
            .astimezone()
            .isoformat(timespec="seconds"),
            **details,
        )
        print(f"Connection still slow: restarting modem (#{state['episode_restart_count']}).")
        notification_sent = send_modem_restart_notification(client, "slow_connection")
        # Shares the latency watch's reboot marker so its cooldown and bad-sample
        # window restart too, and it does not reboot the booting modem again.
        status_store.update(
            last_modem_latency_reboot_epoch=now,
            last_auto_modem_restart_reason="slow_connection",
            last_modem_restart_notification_sent=notification_sent,
        )
        client.device.reboot()
    return action


def main():
    client = None
    sample = None
    status_store.mark_check_started()
    try:
        modem_latency_ms = measure_modem_latency_ms()
        latency_decision = record_modem_latency_sample(modem_latency_ms)
        if watchdog_config.enabled:
            try:
                sample = measure_connection(modem_ms=modem_latency_ms)
            except Exception as error:  # Measurement must never block the SMS check.
                print(f"Connection measurement failed: {type(error).__name__}: {error}")
        client = attempt_login()
        if watchdog_config.enabled:
            record_modem_signal(client)
        if latency_decision.get("should_reboot"):
            restart_modem_for_latency(client, latency_decision)
            return

        sms_messages = read_all_sms_messages(client)
        trigger = find_o2_sms_trigger(sms_messages)
        total_data, baseline_bytes, sms_sent = check_data_usage_and_send_sms(client, trigger)
        deleted_count = retain_recent_sms(client, sms_messages)
        status_store.mark_check_completed(
            usage_bytes=total_data,
            baseline_bytes=baseline_bytes,
            threshold_gb=sms_threshold_gb,
            sms_sent=sms_sent,
            deleted_sms_count=deleted_count,
        )
    except Exception as error:
        status_store.mark_check_failed(error)
        print(f"Worker failed: {type(error).__name__}: {error}")
        logout(client)
        raise

    try:
        if sample is not None:
            action = run_connection_watchdog(client, sample, total_data, sms_sent)
            if action == watchdog.ACTION_RESTART_MODEM:
                return  # The session dies with the reboot; logout would only fail.
    except Exception as error:
        status_store.append_event("watchdog_failed", f"{type(error).__name__}: {error}")
        print(f"Connection watchdog failed: {type(error).__name__}: {error}")
    logout(client)


def cli():
    parser = argparse.ArgumentParser(description="O2 On-Demand SMS modem worker")
    parser.add_argument(
        "action",
        nargs="?",
        default="run",
        choices=("run", "send-sms", "clear-inbox", "restart-modem"),
        help="run the scheduled check or execute a manual modem action",
    )
    arguments = parser.parse_args()

    if arguments.action == "send-sms":
        send_manual_sms()
    elif arguments.action == "clear-inbox":
        clear_sms_inbox_manually()
    elif arguments.action == "restart-modem":
        restart_modem_manually()
    else:
        main()


if __name__ == "__main__":
    cli()
