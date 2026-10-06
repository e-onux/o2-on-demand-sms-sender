"""Latency and download-speed chart drawn on a plain Tk canvas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Sequence

import tkinter as tk
from tkinter import ttk

WINDOWS = {"1h": 3600, "6h": 6 * 3600, "24h": 24 * 3600}
PING_COLOR = "#2563eb"
SPEED_COLOR = "#16a34a"
SLOW_COLOR = "#dc2626"
GRID_COLOR = "#d4d4d8"
TEXT_COLOR = "#52525b"
MARGIN_LEFT, MARGIN_RIGHT, MARGIN_TOP, MARGIN_BOTTOM = 60, 72, 10, 22


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
    history: Sequence[dict[str, Any]], now: float, window_seconds: int
) -> dict[str, list[tuple[float, float | None]]]:
    """Return (age-fraction, value) series for ping, loss and download in the window."""
    series: dict[str, list[tuple[float, float | None]]] = {"ping": [], "lost": [], "speed": []}
    for record in history:
        timestamp = parse_timestamp(record.get("timestamp"))
        if timestamp is None or now - timestamp > window_seconds or timestamp > now + 60:
            continue
        position = 1 - (now - timestamp) / window_seconds
        ping = record.get("ping_ms")
        if isinstance(ping, (int, float)):
            series["ping"].append((position, float(ping)))
        else:
            series["ping"].append((position, None))  # break the line on total loss
            series["lost"].append((position, None))
        speed = record.get("download_mbps")
        if record.get("speed_measured") and isinstance(speed, (int, float)):
            series["speed"].append((position, float(speed)))
        elif record.get("speed_measured"):
            series["lost"].append((position, None))
    return series


class NetworkChart(ttk.Frame):
    def __init__(self, parent: tk.Misc, translate: Callable[..., str]) -> None:
        super().__init__(parent)
        self.t = translate
        self._history: list[dict[str, Any]] = []
        self._slow_ping_ms: float | None = None
        self._slow_mbps: float | None = None
        self.window_var = tk.StringVar(value="6h")

        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, pady=(0, 4))
        self.summary_var = tk.StringVar(value="")
        ttk.Label(toolbar, textvariable=self.summary_var).pack(side=tk.LEFT)
        for key in reversed(tuple(WINDOWS)):
            ttk.Radiobutton(
                toolbar,
                text=self.t(f"chart_window_{key}"),
                value=key,
                variable=self.window_var,
                command=self.redraw,
            ).pack(side=tk.RIGHT, padx=(6, 0))

        self.canvas = tk.Canvas(self, height=150, background="white", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", lambda _event: self.redraw())

    def set_data(
        self,
        history: list[dict[str, Any]],
        slow_ping_ms: float | None,
        slow_mbps: float | None,
    ) -> None:
        self._history = history
        self._slow_ping_ms = slow_ping_ms
        self._slow_mbps = slow_mbps
        latest = history[-1] if history else {}
        ping = latest.get("ping_ms")
        speeds = [r for r in history if r.get("speed_measured")]
        speed = speeds[-1].get("download_mbps") if speeds else None
        self.summary_var.set(
            self.t(
                "chart_summary",
                ping="-" if ping is None else f"{ping:.0f}",
                speed="-" if speed is None else f"{speed:.1f}",
            )
        )
        self.redraw()

    def redraw(self) -> None:
        canvas = self.canvas
        canvas.delete("all")
        width, height = canvas.winfo_width(), canvas.winfo_height()
        if width < 120 or height < 60:
            return
        window = WINDOWS.get(self.window_var.get(), WINDOWS["6h"])
        series = chart_series(self._history, datetime.now().timestamp(), window)
        left, right = MARGIN_LEFT, width - MARGIN_RIGHT
        top, bottom = MARGIN_TOP, height - MARGIN_BOTTOM

        if not series["ping"] and not series["speed"]:
            canvas.create_text(width / 2, height / 2, text=self.t("chart_no_data"), fill=TEXT_COLOR)
            return

        pings = [value for _, value in series["ping"] if value is not None]
        speeds = [value for _, value in series["speed"]]
        ping_max = nice_ceiling(max(pings + [self._slow_ping_ms or 0]) * 1.1 if pings else 100, 50)
        speed_max = nice_ceiling(max(speeds + [self._slow_mbps or 0]) * 1.1 if speeds else 10, 5)

        def x_of(position: float) -> float:
            return left + position * (right - left)

        def y_of(value: float, maximum: float) -> float:
            return bottom - min(value, maximum) / maximum * (bottom - top)

        for fraction in (0, 0.5, 1):
            y = bottom - fraction * (bottom - top)
            canvas.create_line(left, y, right, y, fill=GRID_COLOR)
            ping_label = f"{ping_max * fraction:.0f}" + (" ms" if fraction == 1 else "")
            speed_label = f"{speed_max * fraction:.0f}" + (" Mbit/s" if fraction == 1 else "")
            canvas.create_text(left - 6, y, text=ping_label, anchor=tk.E, fill=PING_COLOR, font=("TkDefaultFont", 8))
            canvas.create_text(right + 6, y, text=speed_label, anchor=tk.W, fill=SPEED_COLOR, font=("TkDefaultFont", 8))
        canvas.create_text(left, height - 4, text=self.t(f"chart_window_{self.window_var.get()}"), anchor=tk.SW, fill=TEXT_COLOR, font=("TkDefaultFont", 8))
        canvas.create_text(right, height - 4, text=self.t("chart_now"), anchor=tk.SE, fill=TEXT_COLOR, font=("TkDefaultFont", 8))

        if self._slow_mbps:
            y = y_of(self._slow_mbps, speed_max)
            canvas.create_line(left, y, right, y, fill=SPEED_COLOR, dash=(4, 3))

        segment: list[float] = []
        for position, value in series["ping"]:
            if value is None:
                if len(segment) >= 4:
                    canvas.create_line(*segment, fill=PING_COLOR, width=1.5)
                segment = []
                continue
            segment += [x_of(position), y_of(value, ping_max)]
        if len(segment) >= 4:
            canvas.create_line(*segment, fill=PING_COLOR, width=1.5)
        elif len(segment) == 2:
            canvas.create_oval(segment[0] - 2, segment[1] - 2, segment[0] + 2, segment[1] + 2, fill=PING_COLOR, outline="")

        for position, value in series["speed"]:
            x, y = x_of(position), y_of(value, speed_max)
            slow = self._slow_mbps is not None and value < self._slow_mbps
            color = SLOW_COLOR if slow else SPEED_COLOR
            canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill=color, outline="")
        for position, _ in series["lost"]:
            x = x_of(position)
            canvas.create_line(x, bottom, x, bottom - 6, fill=SLOW_COLOR, width=2)
