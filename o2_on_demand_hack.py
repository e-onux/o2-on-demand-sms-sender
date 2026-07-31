import argparse
import datetime
import hashlib
import os
import re
import time
from pathlib import Path

from huawei_lte_api.Client import Client
from huawei_lte_api.AuthorizedConnection import AuthorizedConnection
from huawei_lte_api.exceptions import LoginErrorAlreadyLoginException
from huawei_lte_api.enums.sms import BoxTypeEnum
from dotenv import load_dotenv

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

MODEM_DATE_PATTERN = re.compile(r"^\s*(\d{4})-(\d{1,2})-(\d{1,2})")
COUNTER_REFRESH_RETRIES = 4
COUNTER_REFRESH_DELAY_SECONDS = 0.5
SMS_RETENTION_COUNT = int(os.getenv("SMS_RETENTION_COUNT", "3"))

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


def main():
    client = None
    status_store.mark_check_started()
    try:
        client = attempt_login()
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
        raise
    finally:
        logout(client)


def cli():
    parser = argparse.ArgumentParser(description="O2 On-Demand SMS modem worker")
    parser.add_argument(
        "action",
        nargs="?",
        default="run",
        choices=("run", "send-sms", "clear-inbox"),
        help="run the scheduled check or execute a manual modem action",
    )
    arguments = parser.parse_args()

    if arguments.action == "send-sms":
        send_manual_sms()
    elif arguments.action == "clear-inbox":
        clear_sms_inbox_manually()
    else:
        main()


if __name__ == "__main__":
    cli()
