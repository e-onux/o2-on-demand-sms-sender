"""Detect a slow mobile connection and decide on an escalating recovery step.

This module never talks to the modem. It measures the connection (HTTP request
latency and a small download probe) and turns the persisted watchdog state plus
the newest measurement into at most one action: ``send_sms`` or
``restart_modem``. The worker executes that action through its own modem
session, which keeps every Huawei operation inside the worker modules.

Recovery ladder for one slow episode:

1. slowness is confirmed by consecutive slow measurements
2. the WEITER SMS is sent once and the connection is re-measured after a short wait
3. if it is still slow the modem is restarted, then the next restart is only
   allowed after a growing delay (30 min, 3 h, 6 h, 12 h, 24 h by default)

The ladder resets only after the connection stayed healthy for a sustained
period, and a rolling 24-hour cap limits restarts, so a day of poor radio
conditions (rain) cannot cause a restart loop. Probes that fail outright (DNS
or routing errors, for example a broken container network) are "unknown", never
"slow": only completed measurements may lead to an action.
"""

import http.client
import os
import statistics
import time
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Sequence

PHASE_HEALTHY = "healthy"
PHASE_DEGRADED = "degraded"
PHASE_SMS_WAIT = "sms_wait"
PHASE_RESTART_WAIT = "restart_wait"

ACTION_SEND_SMS = "send_sms"
ACTION_RESTART_MODEM = "restart_modem"

DAY_SECONDS = 24 * 60 * 60


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return value.strip().casefold() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, "") or default)
    except ValueError:
        return default


def _parse_targets(value: str) -> tuple[tuple[str, str], ...]:
    targets = []
    for item in value.split(","):
        host, _, path = item.strip().partition("/")
        if host:
            targets.append((host, "/" + path))
    return tuple(targets)


def _parse_minutes(value: str) -> tuple[int, ...]:
    delays = tuple(int(float(part) * 60) for part in value.split(",") if part.strip())
    if not delays or any(delay <= 0 for delay in delays):
        raise ValueError(f"Invalid restart backoff list: {value!r}")
    return delays


@dataclass(frozen=True)
class WatchdogConfig:
    enabled: bool = True
    ping_targets: tuple[tuple[str, str], ...] = (
        ("cp.cloudflare.com", "/generate_204"),
        ("connectivitycheck.gstatic.com", "/generate_204"),
        ("www.msftconnecttest.com", "/connecttest.txt"),
    )
    ping_timeout_seconds: float = 5.0
    slow_ping_ms: float = 400.0
    speed_url: str = "https://speed.cloudflare.com/__down?bytes={bytes}"
    speed_bytes: int = 1_000_000
    speed_timeout_seconds: float = 25.0
    speed_interval_seconds: int = 15 * 60
    min_download_mbps: float = 5.0
    relative_slow_factor: float = 0.35
    relative_min_samples: int = 20
    confirm_count: int = 2
    sms_wait_seconds: int = 120
    restart_backoff_seconds: tuple[int, ...] = (30 * 60, 3 * 3600, 6 * 3600, 12 * 3600, 24 * 3600)
    recovery_seconds: int = 3600
    max_restarts_per_day: int = 4

    @classmethod
    def from_env(cls) -> "WatchdogConfig":
        defaults = cls()
        targets = _parse_targets(os.getenv("WATCHDOG_PING_TARGETS", "")) or defaults.ping_targets
        backoff_text = os.getenv("WATCHDOG_RESTART_BACKOFF_MINUTES", "").strip()
        return cls(
            enabled=_env_bool("WATCHDOG_ENABLED", defaults.enabled),
            ping_targets=targets,
            slow_ping_ms=_env_float("WATCHDOG_SLOW_PING_MS", defaults.slow_ping_ms),
            speed_url=os.getenv("WATCHDOG_SPEED_URL", "").strip() or defaults.speed_url,
            speed_bytes=int(_env_float("WATCHDOG_SPEED_BYTES", defaults.speed_bytes)),
            speed_interval_seconds=int(
                _env_float("WATCHDOG_SPEED_INTERVAL_SECONDS", defaults.speed_interval_seconds)
            ),
            min_download_mbps=_env_float("WATCHDOG_MIN_DOWNLOAD_MBPS", defaults.min_download_mbps),
            relative_slow_factor=_env_float(
                "WATCHDOG_RELATIVE_SLOW_FACTOR", defaults.relative_slow_factor
            ),
            confirm_count=max(1, int(_env_float("WATCHDOG_CONFIRM_COUNT", defaults.confirm_count))),
            sms_wait_seconds=int(_env_float("WATCHDOG_SMS_WAIT_SECONDS", defaults.sms_wait_seconds)),
            restart_backoff_seconds=(
                _parse_minutes(backoff_text) if backoff_text else defaults.restart_backoff_seconds
            ),
            recovery_seconds=int(_env_float("WATCHDOG_RECOVERY_SECONDS", defaults.recovery_seconds)),
            max_restarts_per_day=int(
                _env_float("WATCHDOG_MAX_RESTARTS_PER_DAY", defaults.max_restarts_per_day)
            ),
        )


# --- measurement -----------------------------------------------------------


def measure_ping(
    targets: Sequence[tuple[str, str]],
    timeout: float,
    connection_factory: Callable[..., Any] = http.client.HTTPConnection,
) -> dict[str, Any]:
    """Time one small HTTP request on an already open connection.

    Connect time is excluded on purpose: Docker Desktop proxies outbound
    connections and can add seconds there, while the request itself still
    shows the real round trip. No ICMP privileges or ping binary are needed.
    """
    latencies = []
    for host, path in targets:
        connection = connection_factory(host, 80, timeout=timeout)
        try:
            connection.connect()
            started = time.monotonic()
            connection.request("GET", path, headers={"User-Agent": "o2-ondemand-sms-watchdog"})
            connection.getresponse().read()
            latencies.append((time.monotonic() - started) * 1000)
        except (OSError, http.client.HTTPException):
            continue
        finally:
            connection.close()
    loss_percent = 100.0 * (len(targets) - len(latencies)) / len(targets) if targets else 100.0
    return {
        "ping_ms": round(statistics.median(latencies), 1) if latencies else None,
        "loss_percent": round(loss_percent, 1),
    }


def measure_download_mbps(
    url: str,
    byte_count: int,
    timeout: float,
    opener: Callable[..., Any] = urllib.request.urlopen,
) -> float | None:
    """Download a small test file and return Mbit/s measured after the first byte."""
    request = urllib.request.Request(
        url.format(bytes=byte_count), headers={"User-Agent": "o2-ondemand-sms-watchdog"}
    )
    try:
        with opener(request, timeout=timeout) as response:
            first_chunk = response.read(16 * 1024)
            started = time.monotonic()
            received = 0
            while chunk := response.read(64 * 1024):
                received += len(chunk)
            elapsed = time.monotonic() - started
    except (OSError, ValueError):
        return None
    if not first_chunk or received <= 0 or elapsed <= 0:
        return None
    return round(received * 8 / elapsed / 1_000_000, 2)


# --- decision --------------------------------------------------------------


def initial_state() -> dict[str, Any]:
    return {
        "phase": PHASE_HEALTHY,
        "slow_streak": 0,
        "healthy_since": None,
        "episode_restart_count": 0,
        "restart_times": [],
        "next_action_at": None,
        "last_speed_probe_at": None,
        "speed_history": [],
    }


def normalized_state(state: dict[str, Any] | None) -> dict[str, Any]:
    result = initial_state()
    if isinstance(state, dict):
        result.update({key: state[key] for key in result if key in state})
    if result["phase"] not in (PHASE_HEALTHY, PHASE_DEGRADED, PHASE_SMS_WAIT, PHASE_RESTART_WAIT):
        result["phase"] = PHASE_HEALTHY
    return result


def needs_speed_probe(state: dict[str, Any], now: float, config: WatchdogConfig) -> bool:
    """Probe often only while an episode needs evidence; otherwise save data volume."""
    phase = state["phase"]
    if phase == PHASE_DEGRADED:
        return True
    next_action_at = state.get("next_action_at")
    if next_action_at is not None and now >= next_action_at:
        return True
    if phase == PHASE_SMS_WAIT:
        return False
    last_probe = state.get("last_speed_probe_at")
    return last_probe is None or now - last_probe >= config.speed_interval_seconds


def slow_download_threshold(state: dict[str, Any], config: WatchdogConfig) -> float:
    """Absolute minimum, raised to a fraction of this line's usual speed once known."""
    history = [value for value in state.get("speed_history", []) if isinstance(value, (int, float))]
    if len(history) < config.relative_min_samples:
        return config.min_download_mbps
    return max(config.min_download_mbps, statistics.median(history) * config.relative_slow_factor)


def classify_sample(
    sample: dict[str, Any], state: dict[str, Any], config: WatchdogConfig
) -> str | None:
    """Return "slow", "ok" or None when this run did not produce enough evidence.

    Failed probes give no evidence: an unreachable endpoint may be a local
    network problem that a modem restart cannot fix.
    """
    ping_ms = sample.get("ping_ms")
    if ping_ms is not None and ping_ms >= config.slow_ping_ms:
        return "slow"
    download = sample.get("download_mbps")
    if not sample.get("speed_measured") or download is None:
        return None
    if download < slow_download_threshold(state, config):
        return "slow"
    return "ok"


def decide(
    state: dict[str, Any] | None,
    sample: dict[str, Any],
    now: float,
    config: WatchdogConfig,
) -> tuple[dict[str, Any], str | None, str]:
    """Advance the watchdog state machine and return (state, action, verdict)."""
    state = normalized_state(state)
    verdict = classify_sample(sample, state, config)
    state["restart_times"] = [t for t in state["restart_times"] if now - t < DAY_SECONDS]

    if sample.get("speed_measured"):
        state["last_speed_probe_at"] = now
        download = sample.get("download_mbps")
        if verdict == "ok" and download is not None:
            # Only healthy probes define "usual speed", so a slow day cannot
            # drag the relative threshold down with it.
            state["speed_history"] = (state["speed_history"] + [download])[-96:]

    if verdict is None:
        return state, None, "unknown"

    phase = state["phase"]
    if verdict == "ok":
        state["slow_streak"] = 0
        if state["healthy_since"] is None:
            state["healthy_since"] = now
        if phase in (PHASE_DEGRADED, PHASE_SMS_WAIT):
            # Either a short blip or the SMS fixed it: no restart was spent.
            state.update(phase=PHASE_HEALTHY, next_action_at=None, episode_restart_count=0)
        elif phase == PHASE_RESTART_WAIT and now - state["healthy_since"] >= config.recovery_seconds:
            state.update(phase=PHASE_HEALTHY, next_action_at=None, episode_restart_count=0)
        return state, None, verdict

    state["healthy_since"] = None
    state["slow_streak"] += 1

    if phase == PHASE_HEALTHY:
        phase = state["phase"] = PHASE_DEGRADED
    if phase == PHASE_DEGRADED:
        if state["slow_streak"] < config.confirm_count:
            return state, None, verdict
        state.update(phase=PHASE_SMS_WAIT, next_action_at=now + config.sms_wait_seconds)
        return state, ACTION_SEND_SMS, verdict

    if now < (state["next_action_at"] or 0):
        return state, None, verdict
    if len(state["restart_times"]) >= config.max_restarts_per_day:
        state.update(phase=PHASE_RESTART_WAIT, next_action_at=min(state["restart_times"]) + DAY_SECONDS)
        return state, None, verdict

    restart_index = min(state["episode_restart_count"], len(config.restart_backoff_seconds) - 1)
    state["episode_restart_count"] += 1
    state["restart_times"].append(now)
    state.update(
        phase=PHASE_RESTART_WAIT,
        next_action_at=now + config.restart_backoff_seconds[restart_index],
    )
    return state, ACTION_RESTART_MODEM, verdict
