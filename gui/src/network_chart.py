"""Modem ping, internet ping and download-speed chart on a plain Tk canvas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Sequence

import tkinter as tk
from tkinter import ttk

WINDOWS = {"1h": 3600, "6h": 6 * 3600, "24h": 24 * 3600}
MODEM_COLOR = "#f79009"
PING_COLOR = "#2563eb"
SPEED_COLOR = "#16a34a"
SLOW_COLOR = "#dc2626"
GRID_COLOR = "#d4d4d8"
TEXT_COLOR = "#52525b"
FAIR_COLOR = "#eab308"
MARGIN_LEFT, MARGIN_RIGHT, MARGIN_TOP, MARGIN_BOTTOM = 60, 72, 10, 36
SIGNAL_STRIP_HEIGHT = 8


def signal_quality(rsrp: Any, sinr: Any) -> str | None:
    """Common LTE bands: weak below -105 dBm RSRP or 0 dB SINR, fair below -95 / 10."""
    if not isinstance(rsrp, (int, float)) and not isinstance(sinr, (int, float)):
        return None
    if (isinstance(rsrp, (int, float)) and rsrp < -105) or (isinstance(sinr, (int, float)) and sinr < 0):
        return "weak"
    if (isinstance(rsrp, (int, float)) and rsrp < -95) or (isinstance(sinr, (int, float)) and sinr < 10):
        return "fair"
    return "good"


SIGNAL_COLORS = {"good": SPEED_COLOR, "fair": FAIR_COLOR, "weak": SLOW_COLOR}

def parse_timestamp(value: Any) -> float | None:
    try:
        return datetime.fromisoformat(str(value)).timestamp()
    except ValueError:
        return None


def nice_ceiling(value: float, minimum: float) -> float:
    """Round an axis maximum up to 1, 2 or 5 times a power of ten."""
    value = max(value, minimum)
    magnitude = 10 ** (len(str(int(value))) - 1)
    for step in (1, 2, 5, 10):
        if value <= step * magnitude:
            return float(step * magnitude)
    return float(10 * magnitude)


def chart_series(
    history: Sequence[dict[str, Any]],
    now: float,
    window_seconds: int,
    modem_history: Sequence[dict[str, Any]] = (),
) -> dict[str, list[Any]]:
    """Return (window-fraction, value) series; None values break a line.

    Modem ping comes from the network history ("modem_ms"). The latency
    watch's own short history fills in older samples recorded before that.
    """
    series: dict[str, list[Any]] = {"ping": [], "modem": [], "speed": [], "signal": []}

    def position_of(record: dict[str, Any]) -> float | None:
        timestamp = parse_timestamp(record.get("timestamp"))
        if timestamp is None or now - timestamp > window_seconds or timestamp > now + 60:
            return None
        return 1 - (now - timestamp) / window_seconds

    for record in history:
        position = position_of(record)
        if position is None:
            continue
        ping = record.get("ping_ms")
        if isinstance(ping, (int, float)):
            series["ping"].append((position, float(ping)))
        else:
            series["ping"].append((position, None))
        if "modem_ms" in record:
            modem = record.get("modem_ms")
            series["modem"].append((position, float(modem) if isinstance(modem, (int, float)) else None))
        speed = record.get("download_mbps")
        if record.get("speed_measured") and isinstance(speed, (int, float)):
            series["speed"].append((position, float(speed)))
        quality = signal_quality(record.get("rsrp"), record.get("sinr"))
        if quality:
            series["signal"].append((position, quality))

    first_modem = min((position for position, _ in series["modem"]), default=2.0)
    older_modem: list[tuple[float, float | None]] = []
    for record in modem_history:
        position = position_of(record)
        if position is None or position >= first_modem:
            continue
        latency = record.get("latency_ms")
        older_modem.append((position, float(latency) if isinstance(latency, (int, float)) else None))
    series["modem"] = sorted(older_modem) + series["modem"]
    return series


class NetworkChart(ttk.Frame):
    def __init__(self, parent: tk.Misc, translate: Callable[..., str]) -> None:
        super().__init__(parent)
        self.t = translate
        self._history: list[dict[str, Any]] = []
        self._modem_history: list[dict[str, Any]] = []
        self._modem_threshold_ms: float | None = None
        self._slow_mbps: float | None = None
        self.window_var = tk.StringVar(value="6h")

        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, pady=(0, 4))
        for color, key in (
            (MODEM_COLOR, "chart_legend_modem"),
            (PING_COLOR, "chart_legend_internet"),
            (SPEED_COLOR, "chart_legend_speed"),
            (FAIR_COLOR, "chart_legend_signal"),
        ):
            tk.Label(toolbar, text="● " + self.t(key), foreground=color).pack(side=tk.LEFT, padx=(0, 12))
        for key in reversed(tuple(WINDOWS)):
            ttk.Radiobutton(
                toolbar,
                text=self.t(f"chart_window_{key}"),
                value=key,
                variable=self.window_var,
                command=self.redraw,
            ).pack(side=tk.RIGHT, padx=(6, 0))

        self.canvas = tk.Canvas(self, height=140, background="white", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", lambda _event: self.redraw())

    def set_data(
        self,
        history: list[dict[str, Any]],
        modem_history: list[dict[str, Any]],
        modem_threshold_ms: float | None,
        slow_mbps: float | None,
    ) -> None:
        self._history = history
        self._modem_history = modem_history
        self._modem_threshold_ms = modem_threshold_ms
        self._slow_mbps = slow_mbps
        self.redraw()

    def summary_text(self) -> str:
        latest = self._history[-1] if self._history else {}
        ping = latest.get("ping_ms")
        speeds = [r for r in self._history if r.get("speed_measured")]
        speed = speeds[-1].get("download_mbps") if speeds else None
        text = self.t(
            "chart_summary",
            ping="-" if ping is None else f"{ping:.0f}",
            speed="-" if speed is None else f"{speed:.1f}",
        )
        signals = [r for r in self._history if signal_quality(r.get("rsrp"), r.get("sinr"))]
        if signals:
            latest_signal = signals[-1]
            rsrp, sinr = latest_signal.get("rsrp"), latest_signal.get("sinr")
            text += "\n" + self.t(
                "chart_signal_summary",
                rsrp="-" if rsrp is None else f"{rsrp:g}",
                sinr="-" if sinr is None else f"{sinr:g}",
                quality=self.t(f"signal_{signal_quality(rsrp, sinr)}"),
            )
        return text

    def redraw(self) -> None:
        canvas = self.canvas
        canvas.delete("all")
        width, height = canvas.winfo_width(), canvas.winfo_height()
        if width < 120 or height < 60:
            return
        window = WINDOWS.get(self.window_var.get(), WINDOWS["6h"])
        series = chart_series(
            self._history, datetime.now().timestamp(), window, self._modem_history
        )
        left, right = MARGIN_LEFT, width - MARGIN_RIGHT
        top, bottom = MARGIN_TOP, height - MARGIN_BOTTOM

        if not any(series.values()):
            canvas.create_text(width / 2, height / 2, text=self.t("chart_no_data"), fill=TEXT_COLOR)
            return

        pings = [v for _, v in series["ping"] + series["modem"] if v is not None]
        speeds = [v for _, v in series["speed"] if v is not None]
        ping_max = nice_ceiling(max(pings) * 1.1 if pings else 100, 50)
        speed_max = nice_ceiling(max(speeds + [self._slow_mbps or 0]) * 1.1 if speeds else 10, 5)

        def x_of(position: float) -> float:
            return left + position * (right - left)

        def y_of(value: float, maximum: float) -> float:
            return bottom - min(value, maximum) / maximum * (bottom - top)

        small = ("TkDefaultFont", 8)
        for fraction in (0, 0.5, 1):
            y = bottom - fraction * (bottom - top)
            canvas.create_line(left, y, right, y, fill=GRID_COLOR)
            ping_label = f"{ping_max * fraction:.0f}" + (" ms" if fraction == 1 else "")
            speed_label = f"{speed_max * fraction:.0f}" + (" Mbit/s" if fraction == 1 else "")
            canvas.create_text(left - 6, y, text=ping_label, anchor=tk.E, fill=TEXT_COLOR, font=small)
            canvas.create_text(right + 6, y, text=speed_label, anchor=tk.W, fill=SPEED_COLOR, font=small)
        strip_top = bottom + 5
        canvas.create_text(left - 6, strip_top + SIGNAL_STRIP_HEIGHT / 2, text="4G", anchor=tk.E, fill=TEXT_COLOR, font=small)
        signal_points = series["signal"]
        for index, (position, quality) in enumerate(signal_points):
            # Each sample colours the strip up to the next sample (at most 5 min).
            next_position = signal_points[index + 1][0] if index + 1 < len(signal_points) else 1.0
            end = min(next_position, position + 300 / window, 1.0)
            canvas.create_rectangle(
                x_of(position), strip_top, max(x_of(end), x_of(position) + 1), strip_top + SIGNAL_STRIP_HEIGHT,
                fill=SIGNAL_COLORS[quality], outline="",
            )
        canvas.create_text(left, height - 4, text=self.t(f"chart_window_{self.window_var.get()}"), anchor=tk.SW, fill=TEXT_COLOR, font=small)
        canvas.create_text(right, height - 4, text=self.t("chart_now"), anchor=tk.SE, fill=TEXT_COLOR, font=small)

        # Threshold lines only when they fall inside the visible range, so a
        # high reboot threshold does not flatten normal 20-50 ms values.
        if self._modem_threshold_ms and self._modem_threshold_ms <= ping_max:
            y = y_of(self._modem_threshold_ms, ping_max)
            canvas.create_line(left, y, right, y, fill=SLOW_COLOR, dash=(4, 3))
        if self._slow_mbps:
            y = y_of(self._slow_mbps, speed_max)
            canvas.create_line(left, y, right, y, fill=SPEED_COLOR, dash=(4, 3))

        for name, color in (("modem", MODEM_COLOR), ("ping", PING_COLOR)):
            segment: list[float] = []
            for position, value in series[name] + [(2.0, None)]:
                if value is None:
                    if len(segment) >= 4:
                        canvas.create_line(*segment, fill=color, width=1.5)
                    elif len(segment) == 2:
                        x, y = segment
                        canvas.create_oval(x - 2, y - 2, x + 2, y + 2, fill=color, outline="")
                    if position <= 1:
                        # A failed probe: short red tick on the baseline.
                        x = x_of(position)
                        canvas.create_line(x, bottom, x, bottom - 6, fill=SLOW_COLOR, width=2)
                    segment = []
                    continue
                segment += [x_of(position), y_of(value, ping_max)]

        for position, value in series["speed"]:
            x, y = x_of(position), y_of(value, speed_max)
            slow = self._slow_mbps is not None and value < self._slow_mbps
            color = SLOW_COLOR if slow else SPEED_COLOR
            canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill=color, outline="")
