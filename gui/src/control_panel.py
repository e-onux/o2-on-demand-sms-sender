#!/usr/bin/env python3
"""Desktop control panel for the O2 On-Demand SMS Docker service."""

from __future__ import annotations

import json
import os
import queue
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

import tkinter as tk
from tkinter import messagebox, ttk


def project_dir_argument(arguments: Sequence[str] | None = None) -> str | None:
    """Read --project-dir without taking ownership of the remaining arguments."""
    return argument_value("--project-dir", arguments)


def argument_value(
    name: str, arguments: Sequence[str] | None = None
) -> str | None:
    """Read a named command-line value without parsing unrelated arguments."""
    values = list(sys.argv[1:] if arguments is None else arguments)
    try:
        index = values.index(name)
        return values[index + 1]
    except (ValueError, IndexError):
        return None


def resolve_project_dir() -> Path:
    """Locate the repository from source or a packaged platform build."""
    explicit_path = project_dir_argument() or os.getenv("O2_SMS_PROJECT_DIR")
    candidates = [
        Path(explicit_path).expanduser() if explicit_path else None,
        Path.cwd(),
        Path(__file__).resolve().parent,
        Path(sys.executable).resolve().parent,
        Path("/Users/emironuk/Documents/Projeler/01_Kisisel_Projeler/o2-on-demand-sms-sender"),
    ]
    checked: set[Path] = set()
    for candidate in candidates:
        if candidate is None:
            continue
        for directory in (candidate, *candidate.parents):
            if directory in checked:
                continue
            checked.add(directory)
            if (directory / "docker-compose.yml").is_file() and (
                directory / "o2_on_demand_hack.py"
            ).is_file():
                return directory
    raise RuntimeError(
        "The O2 SMS project directory was not found. Set O2_SMS_PROJECT_DIR or use --project-dir."
    )


PROJECT_DIR = resolve_project_dir()
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from runtime_status import RuntimeStatusStore  # noqa: E402
from gui.src.i18n import LANGUAGES, translate  # noqa: E402
from gui.src.platform_integration import (  # noqa: E402
    enriched_subprocess_environment,
    load_settings,
    save_settings,
    set_start_at_login,
)

try:  # Pillow is optional for minimal source runs.
    from PIL import Image, ImageDraw
except ImportError:  # pragma: no cover - exercised by minimal source environments.
    Image = None
    ImageDraw = None

pystray: Any = None


DATA_DIR = PROJECT_DIR / "data"
STATUS_PATH = DATA_DIR / "status.json"
EVENTS_PATH = DATA_DIR / "events.jsonl"
MAX_GUI_LOG_LINES = 2000
CONTROL_PANEL_LOG_PATH = DATA_DIR / "control_panel.log"
MAX_CONTROL_PANEL_LOG_BYTES = 256 * 1024


def read_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def read_recent_events(path: Path, limit: int = 100) -> list[dict[str, Any]]:
    """Return the last valid JSONL events, newest first."""
    recent_lines: deque[str] = deque(maxlen=limit)
    try:
        with path.open("r", encoding="utf-8") as events_file:
            for line in events_file:
                if line.strip():
                    recent_lines.append(line)
    except OSError:
        return []

    events: list[dict[str, Any]] = []
    for line in reversed(recent_lines):
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def format_timestamp(
    value: Any,
    empty_text: str = "Not yet",
    *,
    multiline: bool = False,
) -> str:
    if not value:
        return empty_text
    try:
        timestamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if timestamp.tzinfo is not None:
            timestamp = timestamp.astimezone()
        pattern = "%d.%m.%Y\n%H:%M:%S" if multiline else "%d.%m.%Y %H:%M:%S"
        return timestamp.strftime(pattern)
    except ValueError:
        return str(value)


def format_decimal_gb_from_bytes(value: Any) -> str:
    try:
        return f"{int(value) / 1_000_000_000:.2f} GB"
    except (TypeError, ValueError):
        return "—"


def tray_icon_is_visible(icon: Any, platform: str | None = None) -> bool:
    """Return whether the tray backend and its native macOS item are visible."""
    if icon is None or not bool(getattr(icon, "visible", False)):
        return False
    if (platform or sys.platform) != "darwin":
        return True
    try:
        status_item = getattr(icon, "_status_item")
        button = status_item.button()
        return button is not None and not bool(button.isHidden())
    except (AttributeError, TypeError):
        return False


def append_control_panel_diagnostic(message: str) -> None:
    """Append a bounded diagnostic entry for failures that occur without a window."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if (
            CONTROL_PANEL_LOG_PATH.exists()
            and CONTROL_PANEL_LOG_PATH.stat().st_size >= MAX_CONTROL_PANEL_LOG_BYTES
        ):
            os.replace(
                CONTROL_PANEL_LOG_PATH,
                CONTROL_PANEL_LOG_PATH.with_suffix(".log.1"),
            )
        timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
        with CONTROL_PANEL_LOG_PATH.open("a", encoding="utf-8") as log_file:
            log_file.write(f"{timestamp} {message.rstrip()}\n")
    except OSError:
        pass


def create_tray_image():
    """Create the cross-platform O2 tray image."""
    if Image is None or ImageDraw is None:
        return None
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((3, 8, 61, 52), radius=13, fill=(0, 96, 190, 255))
    draw.polygon(((17, 50), (13, 61), (29, 51)), fill=(0, 96, 190, 255))
    draw.text((20, 21), "O2", fill=(255, 255, 255, 255))
    return image


def process_is_alive(process_id: int) -> bool:
    """Return whether a process still exists without changing it."""
    try:
        os.kill(process_id, 0)
        return True
    except (ProcessLookupError, ValueError):
        return False
    except PermissionError:
        return True


def run_macos_tray_helper(
    parent_pid: int,
    ready_path: Path,
    language: str,
) -> int:
    """Run the macOS status item in its own native AppKit event loop."""
    if sys.platform != "darwin":
        return 2
    try:
        import AppKit
        import pystray as pystray_module
    except Exception as error:
        append_control_panel_diagnostic(
            f"Tray helper import failed: {type(error).__name__}: {error}"
        )
        return 3

    image = create_tray_image()
    if image is None:
        append_control_panel_diagnostic("Tray helper image support is unavailable.")
        return 3

    native_app = AppKit.NSApplication.sharedApplication()
    native_app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)
    icon: Any = None

    def signal_parent(signal_number: int) -> None:
        try:
            os.kill(parent_pid, signal_number)
        except ProcessLookupError:
            pass

    def show_window(_icon, _item) -> None:
        signal_parent(signal.SIGUSR1)

    def quit_application(_icon, _item) -> None:
        signal_parent(signal.SIGUSR2)
        _icon.stop()

    icon = pystray_module.Icon(
        "o2-sms-control-panel",
        image,
        translate(language, "app_title"),
        pystray_module.Menu(
            pystray_module.MenuItem(
                translate(language, "show_window"),
                show_window,
                default=True,
            ),
            pystray_module.MenuItem(
                translate(language, "quit"),
                quit_application,
            ),
        ),
    )

    # pystray normally changes AppKit visibility from its setup thread. This
    # helper owns the native event loop, so initialize the status item on the
    # main thread before entering that loop.
    icon.visible = True
    status_item = getattr(icon, "_status_item")
    button = status_item.button()
    if button is not None:
        button.setTitle_(" O₂")
    if not tray_icon_is_visible(icon, "darwin"):
        append_control_panel_diagnostic("Tray helper native status item stayed hidden.")
        return 4

    ready_path.parent.mkdir(parents=True, exist_ok=True)
    ready_path.write_text("ready\n", encoding="utf-8")
    append_control_panel_diagnostic("Tray helper is visible.")

    def monitor_parent() -> None:
        while process_is_alive(parent_pid):
            time.sleep(0.5)
        os._exit(0)

    threading.Thread(target=monitor_parent, daemon=True).start()
    icon._setup_thread = threading.current_thread()
    try:
        icon._run()
    finally:
        ready_path.unlink(missing_ok=True)
    return 0


def run_process(
    arguments: Sequence[str],
    *,
    timeout: int = 30,
    cwd: Path = PROJECT_DIR,
    language: str = "en",
) -> tuple[int, str]:
    try:
        result = subprocess.run(
            list(arguments),
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=enriched_subprocess_environment(),
        )
    except FileNotFoundError:
        return 127, translate(language, "command_not_found", command=arguments[0])
    except subprocess.TimeoutExpired:
        return 124, translate(language, "command_timeout", seconds=timeout)
    except OSError as error:
        return 1, translate(language, "command_failed", error=error)

    output_parts = [part.strip() for part in (result.stdout, result.stderr) if part.strip()]
    return result.returncode, "\n".join(output_parts)


def parse_compose_ps(output: str) -> list[dict[str, Any]]:
    if not output.strip():
        return []
    try:
        value = json.loads(output)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            return [value]
    except json.JSONDecodeError:
        pass

    items: list[dict[str, Any]] = []
    for line in output.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            items.append(value)
    return items


def collect_external_status(language: str = "en") -> dict[str, Any]:
    status: dict[str, Any] = {}

    branch_code, branch = run_process(
        ["git", "branch", "--show-current"], timeout=8, language=language
    )
    commit_code, commit = run_process(
        ["git", "rev-parse", "--short", "HEAD"], timeout=8, language=language
    )
    changes_code, changes = run_process(
        ["git", "status", "--porcelain", "--untracked-files=no"], timeout=8, language=language
    )
    if branch_code == commit_code == changes_code == 0:
        changed_count = len([line for line in changes.splitlines() if line.strip()])
        status["git"] = {
            "ok": True,
            "branch": branch or "(detached)",
            "commit": commit,
            "changed_count": changed_count,
        }
    else:
        status["git"] = {"ok": False, "error": branch or commit or changes}

    compose_code, compose_output = run_process(
        ["docker", "compose", "ps", "--all", "--format", "json"],
        timeout=12,
        language=language,
    )
    if compose_code != 0:
        status["docker"] = {"ok": False, "error": compose_output}
    else:
        containers = parse_compose_ps(compose_output)
        container = next(
            (
                item
                for item in containers
                if item.get("Service") == "o2-ondemand-sms"
                or item.get("Name") == "o2-ondemand-sms"
            ),
            containers[0] if containers else None,
        )
        status["docker"] = {"ok": True, "container": container}
    return status


def migrate_legacy_baseline() -> None:
    """Preserve the pre-GUI SMS threshold file on the first launch."""
    source = PROJECT_DIR / "last_sms_info.txt"
    destination = DATA_DIR / "last_sms_info.txt"
    if source.is_file() and not destination.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


class ControlPanel(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.settings = load_settings()
        self.language = str(self.settings.get("language", "tr"))
        if self.language not in LANGUAGES:
            self.language = "en"
        self.settings["language"] = self.language

        self.title(self.t("app_title"))
        self.geometry("1180x780")
        self.minsize(980, 680)
        self.protocol("WM_DELETE_WINDOW", self._request_close)
        if sys.platform == "darwin":
            self.createcommand("tk::mac::ReopenApplication", self._show_window)
            self.createcommand("tk::mac::Quit", self._quit_application)
            self.bind("<Unmap>", self._handle_window_unmap, add="+")

        self._closing = False
        self._command_running = False
        self._refresh_running = False
        self._messages: queue.Queue[tuple[str, Any]] = queue.Queue()
        self._action_buttons: list[ttk.Button] = []
        self._tray_icon: Any = None
        self._tray_process: subprocess.Popen[str] | None = None
        self._tray_ready_path: Path | None = None
        self._tray_available = False
        self.close_to_tray_var = tk.BooleanVar(
            value=bool(self.settings.get("close_to_tray", True))
        )
        self.start_at_login_var = tk.BooleanVar(
            value=bool(self.settings.get("start_at_login", False))
        )
        self.language_var = tk.StringVar(value=self.language)

        if sys.platform == "darwin":
            signal.signal(
                signal.SIGUSR1,
                lambda _number, _frame: self._messages.put(("tray_show", None)),
            )
            signal.signal(
                signal.SIGUSR2,
                lambda _number, _frame: self._messages.put(("tray_quit", None)),
            )

        self._configure_styles()
        self._build_menu()
        self._build_ui()
        self._start_tray_icon()
        self._refresh_local_data()
        self._start_external_refresh()
        self.after(100, self._drain_messages)
        self.after(5000, self._periodic_refresh)
        if "--minimized" in sys.argv:
            self.after(250, self._minimize_to_tray)

    def t(self, key: str, **values: Any) -> str:
        return translate(self.language, key, **values)

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        available_themes = style.theme_names()
        if "clam" in available_themes:
            style.theme_use("clam")
        style.configure("Header.TLabel", font=("TkDefaultFont", 20, "bold"))
        style.configure("Subtle.TLabel", foreground="#667085")
        style.configure("Running.TLabel", foreground="#15803d", font=("TkDefaultFont", 11, "bold"))
        style.configure("Stopped.TLabel", foreground="#b42318", font=("TkDefaultFont", 11, "bold"))
        style.configure("CardTitle.TLabel", foreground="#667085", font=("TkDefaultFont", 10))
        style.configure("CardValue.TLabel", font=("TkDefaultFont", 17, "bold"))
        style.configure("Action.TButton", padding=(12, 8))
        style.configure("Treeview", rowheight=26)

    def _build_menu(self) -> None:
        menu_bar = tk.Menu(self)
        settings_menu = tk.Menu(menu_bar, tearoff=False)
        language_menu = tk.Menu(settings_menu, tearoff=False)
        for code, label in LANGUAGES.items():
            language_menu.add_radiobutton(
                label=label,
                value=code,
                variable=self.language_var,
                command=lambda selected=code: self._set_language(selected),
            )
        settings_menu.add_cascade(label=self.t("language"), menu=language_menu)
        settings_menu.add_separator()
        settings_menu.add_checkbutton(
            label=self.t("close_to_tray"),
            variable=self.close_to_tray_var,
            command=self._toggle_close_to_tray,
        )
        settings_menu.add_checkbutton(
            label=self.t("start_at_login"),
            variable=self.start_at_login_var,
            command=self._toggle_start_at_login,
        )
        settings_menu.add_separator()
        settings_menu.add_command(
            label=self.t("minimize_to_tray"), command=self._minimize_to_tray
        )
        settings_menu.add_command(label=self.t("quit"), command=self._quit_application)
        menu_bar.add_cascade(label=self.t("settings"), menu=settings_menu)
        self.configure(menu=menu_bar)

    def _build_ui(self) -> None:
        self._action_buttons = []
        root = ttk.Frame(self, padding=18)
        self._root_frame = root
        root.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(root)
        header.pack(fill=tk.X, pady=(0, 14))
        ttk.Label(header, text=self.t("header_title"), style="Header.TLabel").pack(side=tk.LEFT)
        header_right = ttk.Frame(header)
        header_right.pack(side=tk.RIGHT)
        self.git_var = tk.StringVar(value=self.t("git_loading"))
        self.service_var = tk.StringVar(value=self.t("service_loading"))
        ttk.Label(header_right, textvariable=self.git_var, style="Subtle.TLabel").pack(anchor=tk.E)
        self.service_label = ttk.Label(
            header_right, textvariable=self.service_var, style="Stopped.TLabel"
        )
        self.service_label.pack(anchor=tk.E, pady=(3, 0))

        actions = ttk.LabelFrame(root, text=self.t("actions"), padding=10)
        actions.pack(fill=tk.X, pady=(0, 14))
        action_definitions = [
            (self.t("update_start"), self._update_and_start),
            (self.t("git_pull"), self._git_pull),
            (self.t("image_pull"), self._image_pull),
            (self.t("service_start"), self._start_service),
            (self.t("service_stop"), self._stop_service),
            (self.t("service_restart"), self._restart_service),
            (self.t("logs_refresh"), self._load_logs),
            (self.t("refresh_now"), self._manual_refresh),
        ]
        for column in range(4):
            actions.columnconfigure(column, weight=1, uniform="actions")
        for index, (label, callback) in enumerate(action_definitions):
            button = ttk.Button(actions, text=label, command=callback, style="Action.TButton")
            button.grid(
                row=index // 4,
                column=index % 4,
                sticky="ew",
                padx=(0, 7),
                pady=(0 if index < 4 else 7, 0),
            )
            self._action_buttons.append(button)

        modem_actions = ttk.LabelFrame(root, text=self.t("modem_actions"), padding=10)
        modem_actions.pack(fill=tk.X, pady=(0, 14))
        manual_sms_button = ttk.Button(
            modem_actions,
            text=self.t("manual_sms"),
            command=self._send_manual_sms,
            style="Action.TButton",
        )
        manual_sms_button.pack(side=tk.LEFT, padx=(0, 7))
        clear_inbox_button = ttk.Button(
            modem_actions,
            text=self.t("clear_inbox"),
            command=self._clear_sms_inbox,
            style="Action.TButton",
        )
        clear_inbox_button.pack(side=tk.LEFT, padx=(0, 12))
        ttk.Label(
            modem_actions,
            text=self.t("modem_note"),
            style="Subtle.TLabel",
            wraplength=650,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._action_buttons.extend((manual_sms_button, clear_inbox_button))

        cards = ttk.Frame(root)
        cards.pack(fill=tk.X, pady=(0, 14))
        for column in range(5):
            cards.columnconfigure(column, weight=1, uniform="stats")

        self.last_sms_var = self._create_card(cards, 0, self.t("last_sms"), self.t("never"))
        self.today_sms_var = self._create_card(cards, 1, self.t("today_sent"), "0")
        self.total_sms_var = self._create_card(cards, 2, self.t("total_sent"), "0")
        self.usage_var = self._create_card(cards, 3, self.t("today_usage"), "—")
        self.last_check_var = self._create_card(cards, 4, self.t("last_check"), self.t("never"))

        details = ttk.LabelFrame(root, text=self.t("current_details"), padding=10)
        details.pack(fill=tk.X, pady=(0, 14))
        details.columnconfigure(1, weight=1)
        self.reason_var = self._detail_row(details, 0, self.t("last_reason"))
        self.check_result_var = self._detail_row(details, 1, self.t("last_result"))
        self.threshold_var = self._detail_row(details, 2, self.t("threshold_status"))
        self.error_var = self._detail_row(details, 3, self.t("last_error"))

        panes = ttk.Panedwindow(root, orient=tk.VERTICAL)
        panes.pack(fill=tk.BOTH, expand=True)

        events_frame = ttk.LabelFrame(panes, text=self.t("recent_events"), padding=8)
        panes.add(events_frame, weight=3)
        events_frame.rowconfigure(1, weight=1)
        events_frame.columnconfigure(0, weight=1)

        events_toolbar = ttk.Frame(events_frame)
        events_toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 7))
        copy_events_button = ttk.Button(
            events_toolbar,
            text=self.t("copy_events"),
            command=self._copy_events,
        )
        copy_events_button.pack(side=tk.LEFT, padx=(0, 7))
        clear_events_button = ttk.Button(
            events_toolbar,
            text=self.t("clear_events"),
            command=self._clear_events,
        )
        clear_events_button.pack(side=tk.LEFT)
        self._action_buttons.extend((copy_events_button, clear_events_button))

        self.events_tree = ttk.Treeview(
            events_frame,
            columns=("time", "type", "description"),
            show="headings",
            height=8,
        )
        self.events_tree.heading("time", text=self.t("time"))
        self.events_tree.heading("type", text=self.t("event"))
        self.events_tree.heading("description", text=self.t("description"))
        self.events_tree.column("time", width=160, stretch=False)
        self.events_tree.column("type", width=150, stretch=False)
        self.events_tree.column("description", width=700)
        event_scroll = ttk.Scrollbar(events_frame, orient=tk.VERTICAL, command=self.events_tree.yview)
        self.events_tree.configure(yscrollcommand=event_scroll.set)
        self.events_tree.grid(row=1, column=0, sticky="nsew")
        event_scroll.grid(row=1, column=1, sticky="ns")

        log_frame = ttk.LabelFrame(panes, text=self.t("logs"), padding=8)
        panes.add(log_frame, weight=2)
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        self.log_text = tk.Text(
            log_frame,
            height=8,
            wrap=tk.WORD,
            font=("TkFixedFont", 10),
            state=tk.DISABLED,
        )
        log_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        log_scroll.grid(row=0, column=1, sticky="ns")

        self.footer_var = tk.StringVar(value=self.t("ready"))
        ttk.Label(root, textvariable=self.footer_var, style="Subtle.TLabel").pack(
            fill=tk.X, pady=(8, 0)
        )

    def _create_card(self, parent: ttk.Frame, column: int, title: str, value: str) -> tk.StringVar:
        card = ttk.LabelFrame(parent, padding=12)
        card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 5, 0))
        ttk.Label(card, text=title, style="CardTitle.TLabel").pack(anchor=tk.W)
        variable = tk.StringVar(value=value)
        ttk.Label(card, textvariable=variable, style="CardValue.TLabel").pack(
            anchor=tk.W, pady=(7, 0)
        )
        return variable

    def _detail_row(self, parent: ttk.LabelFrame, row: int, title: str) -> tk.StringVar:
        ttk.Label(parent, text=title, style="Subtle.TLabel").grid(
            row=row, column=0, sticky=tk.NW, padx=(0, 10), pady=2
        )
        variable = tk.StringVar(value="—")
        ttk.Label(parent, textvariable=variable, wraplength=900).grid(
            row=row, column=1, sticky=tk.W, pady=2
        )
        return variable

    def _refresh_local_data(self) -> None:
        status = read_json_object(STATUS_PATH)
        events = read_recent_events(EVENTS_PATH, limit=100)

        last_sms_at = status.get("last_sms_at")
        self.last_sms_var.set(
            format_timestamp(last_sms_at, self.t("never"), multiline=True)
        )

        today = datetime.now().astimezone().date().isoformat()
        today_count = status.get("today_sms_count", 0) if status.get("statistics_day") == today else 0
        self.today_sms_var.set(str(today_count))
        self.total_sms_var.set(str(status.get("total_sms_count", 0)))
        self.usage_var.set(format_decimal_gb_from_bytes(status.get("current_usage_bytes")))
        self.last_check_var.set(
            format_timestamp(
                status.get("last_check_at"), self.t("never"), multiline=True
            )
        )
        self.reason_var.set(self._localized_sms_reason(status))

        if status.get("last_check_status") == "ok":
            result = self.t("success")
            if status.get("last_check_sms_sent"):
                result += f" — {self.t('sms_sent_suffix')}"
            else:
                result += f" — {self.t('sms_not_needed')}"
        elif status.get("last_check_status") == "error":
            result = self.t("error")
        elif status.get("worker_state") == "checking":
            result = self.t("checking")
        else:
            result = self.t("no_check")
        self.check_result_var.set(result)

        baseline = status.get("baseline_usage_gb")
        threshold = status.get("threshold_gb")
        if baseline is None or threshold is None:
            self.threshold_var.set(self.t("no_initial_check"))
        else:
            next_threshold = float(baseline) + float(threshold)
            self.threshold_var.set(
                self.t(
                    "next_threshold",
                    baseline=float(baseline),
                    next_threshold=next_threshold,
                )
            )
        errors: list[str] = []
        if status.get("last_error"):
            errors.append(f"{self.t('check_prefix')}: {status['last_error']}")
        if status.get("last_manual_action_error"):
            errors.append(f"{self.t('manual_prefix')}: {status['last_manual_action_error']}")
        self.error_var.set(" | ".join(errors) if errors else self.t("none"))
        self._populate_events(events)

    def _localized_sms_reason(self, status: dict[str, Any]) -> str:
        reason = str(status.get("last_sms_reason") or "")
        if not reason:
            return self.t("no_sms_record")
        trigger_code = status.get("last_o2_trigger_code")
        if trigger_code == "highspeed_exhausted":
            return self.t("runtime_trigger_exhausted")
        if trigger_code == "highspeed_80_percent":
            return self.t("runtime_trigger_80")
        normalized = reason.casefold()
        if "manuel" in normalized or "manually" in normalized:
            return self.t("runtime_manual_sms")
        if "eşik" in normalized or "threshold" in normalized:
            return self.t("runtime_threshold", threshold=float(status.get("threshold_gb", 0)))
        return reason

    def _localized_event_message(self, event: dict[str, Any]) -> str:
        event_type = str(event.get("event_type", ""))
        if event_type == "check_completed":
            return self.t("runtime_check_sent" if event.get("sms_sent") else "runtime_check_no_sms")
        if event_type == "data_usage_reset":
            return self.t("runtime_counter_reset")
        if event_type == "sms_baseline_reset":
            return self.t("runtime_baseline_reset")
        if event_type == "sms_inbox_cleared":
            return self.t("runtime_inbox_cleared", count=int(event.get("deleted_sms_count", 0)))
        if event_type == "sms_sent":
            trigger_code = event.get("trigger_code")
            if trigger_code == "highspeed_exhausted":
                return self.t("runtime_trigger_exhausted")
            if trigger_code == "highspeed_80_percent":
                return self.t("runtime_trigger_80")
            message = str(event.get("message", ""))
            normalized = message.casefold()
            if "manuel" in normalized or "manually" in normalized:
                return self.t("runtime_manual_sms")
            if "eşik" in normalized or "threshold" in normalized:
                return self.t("runtime_threshold", threshold=float(event.get("threshold_gb", 0)))
        return str(event.get("message", ""))

    def _populate_events(self, events: list[dict[str, Any]]) -> None:
        self.events_tree.delete(*self.events_tree.get_children())
        labels = {
            "sms_sent": self.t("event_sms_sent"),
            "check_completed": self.t("event_check_completed"),
            "check_failed": self.t("event_check_failed"),
            "data_usage_reset": self.t("event_usage_reset"),
            "sms_baseline_reset": self.t("event_baseline_reset"),
            "sms_inbox_cleared": self.t("event_inbox_cleared"),
            "manual_action_failed": self.t("event_manual_failed"),
        }
        for event in events:
            event_type = str(event.get("event_type", self.t("event_unknown")))
            message = self._localized_event_message(event)
            if event_type == "check_completed" and event.get("usage_bytes") is not None:
                message = f"{message} " + self.t(
                    "event_usage",
                    usage=format_decimal_gb_from_bytes(event["usage_bytes"]),
                )
            self.events_tree.insert(
                "",
                tk.END,
                values=(
                    format_timestamp(event.get("timestamp"), self.t("never")),
                    labels.get(event_type, event_type),
                    message,
                ),
            )

    def _periodic_refresh(self) -> None:
        if self._closing:
            return
        self._refresh_local_data()
        self._start_external_refresh()
        self.after(5000, self._periodic_refresh)

    def _start_external_refresh(self) -> None:
        if self._refresh_running or self._closing:
            return
        self._refresh_running = True

        def worker() -> None:
            self._messages.put(("external_status", collect_external_status(self.language)))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_external_status(self, status: dict[str, Any]) -> None:
        self._refresh_running = False
        git = status.get("git", {})
        if git.get("ok"):
            changes = int(git.get("changed_count", 0))
            suffix = f" • {self.t('local_changes', count=changes)}" if changes else ""
            self.git_var.set(f"Git: {git.get('branch')} @ {git.get('commit')}{suffix}")
        else:
            self.git_var.set(self.t("git_unavailable"))

        docker = status.get("docker", {})
        if not docker.get("ok"):
            self.service_var.set(self.t("docker_unavailable"))
            self.service_label.configure(style="Stopped.TLabel")
            return
        container = docker.get("container")
        if not container:
            self.service_var.set(self.t("service_missing"))
            self.service_label.configure(style="Stopped.TLabel")
            return

        state = str(container.get("State", "unknown")).lower()
        health = str(container.get("Health", "")).lower()
        detail = str(container.get("Status", "")).strip()
        if state == "running":
            health_text = f" • {health}" if health else ""
            self.service_var.set(self.t("service_running", health=health_text, detail=detail))
            self.service_label.configure(style="Running.TLabel")
        else:
            self.service_var.set(self.t("service_state", state=state, detail=detail))
            self.service_label.configure(style="Stopped.TLabel")

    def _run_command_sequence(
        self,
        title: str,
        steps: Sequence[tuple[Sequence[str], int]],
    ) -> None:
        if self._command_running:
            messagebox.showinfo(self.t("app_title"), self.t("wait_for_command"))
            return
        self._command_running = True
        self._set_actions_enabled(False)
        self.footer_var.set(self.t("action_running", title=title))
        self._append_log(f"\n▶ {title}\n")

        def worker() -> None:
            all_output: list[str] = []
            final_code = 0
            for arguments, timeout in steps:
                command_label = " ".join(arguments)
                all_output.append(f"$ {command_label}")
                code, output = run_process(arguments, timeout=timeout, language=self.language)
                all_output.append(output or self.t("no_output"))
                if code != 0:
                    final_code = code
                    break
            self._messages.put(
                ("command_result", {"title": title, "code": final_code, "output": "\n".join(all_output)})
            )

        threading.Thread(target=worker, daemon=True).start()

    def _handle_command_result(self, result: dict[str, Any]) -> None:
        self._command_running = False
        self._set_actions_enabled(True)
        self._append_log(str(result.get("output", "")) + "\n")
        if result.get("code") == 0:
            self.footer_var.set(self.t("action_completed", title=result.get("title")))
        else:
            self.footer_var.set(
                self.t(
                    "action_failed",
                    title=result.get("title"),
                    code=result.get("code"),
                )
            )
        self._refresh_local_data()
        self._start_external_refresh()

    def _append_log(self, content: str) -> None:
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, content)
        line_count = int(self.log_text.index("end-1c").split(".")[0])
        if line_count > MAX_GUI_LOG_LINES:
            self.log_text.delete("1.0", f"{line_count - MAX_GUI_LOG_LINES}.0")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _set_actions_enabled(self, enabled: bool) -> None:
        state = tk.NORMAL if enabled else tk.DISABLED
        for button in self._action_buttons:
            button.configure(state=state)

    def _drain_messages(self) -> None:
        while True:
            try:
                message_type, payload = self._messages.get_nowait()
            except queue.Empty:
                break
            if message_type == "external_status":
                self._apply_external_status(payload)
            elif message_type == "command_result":
                self._handle_command_result(payload)
            elif message_type == "tray_show":
                self._show_window()
            elif message_type == "tray_quit":
                self._quit_application()
        if not self._closing:
            self.after(100, self._drain_messages)

    def _update_and_start(self) -> None:
        self._run_command_sequence(
            self.t("op_update_start"),
            [
                (["git", "pull", "--ff-only"], 180),
                (["docker", "compose", "up", "-d", "--build"], 1200),
            ],
        )

    def _git_pull(self) -> None:
        self._run_command_sequence(self.t("git_pull"), [(["git", "pull", "--ff-only"], 180)])

    def _image_pull(self) -> None:
        self._run_command_sequence(
            self.t("op_image_pull"),
            [(["docker", "compose", "pull", "o2-ondemand-sms"], 1200)],
        )

    def _start_service(self) -> None:
        self._run_command_sequence(
            self.t("op_start"), [(["docker", "compose", "up", "-d"], 300)]
        )

    def _stop_service(self) -> None:
        self._run_command_sequence(
            self.t("op_stop"), [(["docker", "compose", "stop"], 180)]
        )

    def _restart_service(self) -> None:
        self._run_command_sequence(
            self.t("op_restart"), [(["docker", "compose", "restart"], 180)]
        )

    def _load_logs(self) -> None:
        self._run_command_sequence(
            self.t("op_logs"),
            [(["docker", "compose", "logs", "--tail", "200", "o2-ondemand-sms"], 60)],
        )

    def _send_manual_sms(self) -> None:
        confirmed = messagebox.askyesno(
            self.t("manual_confirm_title"),
            self.t("manual_confirm"),
            icon="warning",
        )
        if not confirmed:
            return
        self._run_command_sequence(
            self.t("op_manual_sms"),
            [
                (
                    [
                        "docker",
                        "compose",
                        "exec",
                        "-T",
                        "o2-ondemand-sms",
                        "python",
                        "/app/modem_actions.py",
                        "send-sms",
                    ],
                    180,
                )
            ],
        )

    def _clear_sms_inbox(self) -> None:
        confirmed = messagebox.askyesno(
            self.t("clear_inbox_title"),
            self.t("clear_inbox_confirm"),
            icon="warning",
        )
        if not confirmed:
            return
        self._run_command_sequence(
            self.t("op_clear_inbox"),
            [
                (
                    [
                        "docker",
                        "compose",
                        "exec",
                        "-T",
                        "o2-ondemand-sms",
                        "python",
                        "/app/modem_actions.py",
                        "clear-inbox",
                    ],
                    180,
                )
            ],
        )

    def _copy_events(self) -> None:
        rows = [self.events_tree.item(item, "values") for item in self.events_tree.get_children()]
        if not rows:
            self.footer_var.set(self.t("no_events_to_copy"))
            return

        lines = [f"{self.t('time')}\t{self.t('event')}\t{self.t('description')}"]
        lines.extend("\t".join(str(value) for value in row) for row in rows)
        self.clipboard_clear()
        self.clipboard_append("\n".join(lines))
        self.update_idletasks()
        self.footer_var.set(self.t("events_copied", count=len(rows)))

    def _clear_events(self) -> None:
        confirmed = messagebox.askyesno(
            self.t("clear_events_title"),
            self.t("clear_events_confirm"),
            icon="warning",
        )
        if not confirmed:
            return

        try:
            RuntimeStatusStore(DATA_DIR).clear_events()
        except OSError:
            # Linux bind mounts may create root-owned files. In that case clear
            # the same mounted file from inside the running service container.
            self._run_command_sequence(
                self.t("op_clear_events"),
                [
                    (
                        [
                            "docker",
                            "compose",
                            "exec",
                            "-T",
                            "o2-ondemand-sms",
                            "python",
                            "-c",
                            (
                                "from runtime_status import RuntimeStatusStore; "
                                "RuntimeStatusStore('/app/data').clear_events()"
                            ),
                        ],
                        60,
                    )
                ],
            )
            return

        self._refresh_local_data()
        self.footer_var.set(self.t("events_cleared"))

    def _manual_refresh(self) -> None:
        self._refresh_local_data()
        self._start_external_refresh()
        self.footer_var.set(self.t("refreshed"))

    def _save_current_settings(self) -> None:
        self.settings.update(
            language=self.language,
            close_to_tray=bool(self.close_to_tray_var.get()),
            start_at_login=bool(self.start_at_login_var.get()),
        )
        save_settings(self.settings)

    def _set_language(self, language: str) -> None:
        if language not in LANGUAGES or language == self.language:
            return
        self.language = language
        self.language_var.set(language)
        self._save_current_settings()
        self.title(self.t("app_title"))
        self._root_frame.destroy()
        self._build_menu()
        self._build_ui()
        if self._command_running:
            self._set_actions_enabled(False)
        self._refresh_local_data()
        self._start_external_refresh()
        self._rebuild_tray_menu()

    def _toggle_close_to_tray(self) -> None:
        self._save_current_settings()

    def _toggle_start_at_login(self) -> None:
        enabled = bool(self.start_at_login_var.get())
        try:
            set_start_at_login(enabled, PROJECT_DIR)
            self._save_current_settings()
        except OSError as error:
            self.start_at_login_var.set(not enabled)
            messagebox.showerror(
                self.t("app_title"),
                self.t("autostart_failed", error=error),
            )

    def _create_tray_image(self):
        return create_tray_image()

    def _tray_menu(self):
        if pystray is None:
            return None
        return pystray.Menu(
            pystray.MenuItem(
                self.t("show_window"),
                lambda _icon, _item: self.after(0, self._show_window),
                default=True,
            ),
            pystray.MenuItem(
                self.t("quit"),
                lambda _icon, _item: self.after(0, self._quit_application),
            ),
        )

    def _start_tray_icon(self) -> None:
        global pystray
        if sys.platform == "darwin":
            self._start_macos_tray_helper()
            return
        try:
            if pystray is None:
                import pystray as pystray_module

                pystray = pystray_module
        except Exception as error:  # Headless Linux and missing optional dependencies.
            message = f"Tray initialization failed: {type(error).__name__}: {error}"
            self._append_log(message + "\n")
            append_control_panel_diagnostic(message)
            return
        try:
            image = self._create_tray_image()
            if image is None:
                raise RuntimeError("tray image support is unavailable")
            self._tray_icon = pystray.Icon(
                "o2-sms-control-panel",
                image,
                self.t("app_title"),
                self._tray_menu(),
            )
            self._tray_icon.run_detached()
            self.after(100, self._refresh_tray_availability)
        except Exception as error:  # A missing desktop backend must not stop the GUI.
            self._tray_icon = None
            self._tray_available = False
            message = f"Tray initialization failed: {type(error).__name__}: {error}"
            self._append_log(message + "\n")
            append_control_panel_diagnostic(message)

    def _start_macos_tray_helper(self) -> None:
        self._stop_macos_tray_helper()
        ready_path = Path(tempfile.gettempdir()) / f"o2-sms-tray-{os.getpid()}.ready"
        ready_path.unlink(missing_ok=True)
        self._tray_ready_path = ready_path
        if getattr(sys, "frozen", False):
            command = [sys.executable]
        else:
            command = [sys.executable, str(Path(__file__).resolve())]
        command.extend(
            (
                "--macos-tray-helper",
                "--parent-pid",
                str(os.getpid()),
                "--tray-ready-file",
                str(ready_path),
                "--tray-language",
                self.language,
                "--project-dir",
                str(PROJECT_DIR),
            )
        )
        try:
            self._tray_process = subprocess.Popen(
                command,
                cwd=PROJECT_DIR,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
                env=enriched_subprocess_environment(),
            )
            self.after(100, lambda: self._poll_macos_tray_helper(50))
        except OSError as error:
            self._tray_process = None
            message = f"Tray helper failed to start: {type(error).__name__}: {error}"
            self._append_log(message + "\n")
            append_control_panel_diagnostic(message)

    def _poll_macos_tray_helper(self, attempts_remaining: int) -> None:
        if self._closing:
            return
        process = self._tray_process
        ready_path = self._tray_ready_path
        if process is None or ready_path is None:
            self._tray_available = False
            return
        if ready_path.is_file() and process.poll() is None:
            if not self._tray_available:
                append_control_panel_diagnostic("Tray helper handshake completed.")
            self._tray_available = True
            return
        if process.poll() is not None:
            self._tray_available = False
            message = f"Tray helper exited with code {process.returncode}."
            self._append_log(message + "\n")
            append_control_panel_diagnostic(message)
            return
        if attempts_remaining > 0:
            self.after(
                100,
                lambda: self._poll_macos_tray_helper(attempts_remaining - 1),
            )
            return
        self._tray_available = False
        append_control_panel_diagnostic("Tray helper readiness timed out.")
        self._stop_macos_tray_helper()

    def _stop_macos_tray_helper(self) -> None:
        process = self._tray_process
        self._tray_process = None
        self._tray_available = False
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
        if self._tray_ready_path is not None:
            self._tray_ready_path.unlink(missing_ok=True)
        self._tray_ready_path = None

    def _refresh_tray_availability(self) -> None:
        if sys.platform == "darwin":
            process = self._tray_process
            ready_path = self._tray_ready_path
            self._tray_available = bool(
                process is not None
                and process.poll() is None
                and ready_path is not None
                and ready_path.is_file()
            )
            return
        self._tray_available = tray_icon_is_visible(self._tray_icon)

    def _rebuild_tray_menu(self) -> None:
        if sys.platform == "darwin":
            self._start_macos_tray_helper()
            return
        if self._tray_icon is None:
            return
        self._tray_icon.title = self.t("app_title")
        self._tray_icon.menu = self._tray_menu()
        self._tray_icon.update_menu()

    def _show_window(self) -> None:
        self._set_macos_dock_visible(True)
        self.deiconify()
        self.lift()
        self.focus_force()

    def _minimize_to_tray(self) -> None:
        self._refresh_tray_availability()
        if self._tray_available:
            self.withdraw()
            self._set_macos_dock_visible(False)
            return
        self.footer_var.set(self.t("tray_unavailable"))
        self.iconify()

    def _set_macos_dock_visible(self, visible: bool) -> None:
        if sys.platform != "darwin":
            return
        if not visible and not self._tray_available:
            return
        try:
            import AppKit

            native_app = AppKit.NSApplication.sharedApplication()
            policy = (
                AppKit.NSApplicationActivationPolicyRegular
                if visible
                else AppKit.NSApplicationActivationPolicyAccessory
            )
            native_app.setActivationPolicy_(policy)
            if visible:
                native_app.activateIgnoringOtherApps_(True)
        except Exception as error:
            message = f"Dock policy update failed: {type(error).__name__}: {error}"
            self._append_log(message + "\n")
            append_control_panel_diagnostic(message)

    def _handle_window_unmap(self, event: tk.Event) -> None:
        if (
            event.widget is self
            and not self._closing
            and self.close_to_tray_var.get()
            and self._tray_available
            and self.state() == "iconic"
        ):
            self.after_idle(self._minimize_to_tray)

    def _request_close(self) -> None:
        if self.close_to_tray_var.get():
            self._minimize_to_tray()
            return
        self._quit_application()

    def _quit_application(self) -> None:
        self._closing = True
        if sys.platform == "darwin":
            self._stop_macos_tray_helper()
        if self._tray_icon is not None:
            self._tray_icon.stop()
        self.destroy()


def packaged_smoke_test() -> int:
    """Validate the minimum runtime contract without opening a window."""
    required_paths = (
        PROJECT_DIR / "docker-compose.yml",
        PROJECT_DIR / "o2_on_demand_hack.py",
    )
    return 0 if all(path.is_file() for path in required_paths) else 1


def main() -> None:
    if "--macos-tray-helper" in sys.argv:
        try:
            parent_pid_value = argument_value("--parent-pid")
            ready_path_value = argument_value("--tray-ready-file")
            if parent_pid_value is None or ready_path_value is None:
                raise ValueError("missing tray helper argument")
            parent_pid = int(parent_pid_value)
            ready_path = Path(ready_path_value)
            language = argument_value("--tray-language") or "en"
        except (TypeError, ValueError):
            raise SystemExit(2)
        if language not in LANGUAGES:
            raise SystemExit(2)
        try:
            helper_exit_code = run_macos_tray_helper(parent_pid, ready_path, language)
        except Exception as error:
            append_control_panel_diagnostic(
                f"Tray helper crashed: {type(error).__name__}: {error}"
            )
            helper_exit_code = 5
        raise SystemExit(helper_exit_code)
    if "--smoke-test" in sys.argv:
        raise SystemExit(packaged_smoke_test())
    if "--docker-smoke-test" in sys.argv:
        docker_status = collect_external_status("en").get("docker", {})
        raise SystemExit(0 if docker_status.get("ok") else 2)
    try:
        migrate_legacy_baseline()
    except OSError as error:
        print(f"The legacy status file could not be migrated: {error}")
    app = ControlPanel()
    if "--tray-lifecycle-smoke-test" in sys.argv:
        lifecycle_exit_code = 3

        def finish_tray_restore(hidden_ok: bool) -> None:
            nonlocal lifecycle_exit_code
            app.update_idletasks()
            try:
                import AppKit

                dock_is_regular = (
                    AppKit.NSApplication.sharedApplication().activationPolicy()
                    == AppKit.NSApplicationActivationPolicyRegular
                )
            except Exception:
                dock_is_regular = False
            restored_ok = app.state() == "normal" and dock_is_regular
            lifecycle_exit_code = 0 if hidden_ok and restored_ok else 4
            marker = os.getenv("O2_SMS_GUI_SMOKE_MARKER")
            if lifecycle_exit_code == 0 and marker:
                Path(marker).write_text("ok\n", encoding="utf-8")
            app._quit_application()

        def exercise_tray_lifecycle(attempts_remaining: int = 100) -> None:
            app._refresh_tray_availability()
            if not app._tray_available and attempts_remaining > 0:
                app.after(
                    100,
                    lambda: exercise_tray_lifecycle(attempts_remaining - 1),
                )
                return
            if not app._tray_available:
                app._quit_application()
                return
            app._minimize_to_tray()
            app.update_idletasks()
            try:
                import AppKit

                dock_is_accessory = (
                    AppKit.NSApplication.sharedApplication().activationPolicy()
                    == AppKit.NSApplicationActivationPolicyAccessory
                )
            except Exception:
                dock_is_accessory = False
            helper_is_running = bool(
                app._tray_process is not None and app._tray_process.poll() is None
            )
            hidden_ok = (
                app.state() == "withdrawn"
                and dock_is_accessory
                and helper_is_running
            )
            os.kill(os.getpid(), signal.SIGUSR1)
            app.after(300, lambda: finish_tray_restore(hidden_ok))

        app.after(100, exercise_tray_lifecycle)
        app.mainloop()
        raise SystemExit(lifecycle_exit_code)
    if "--gui-smoke-test" in sys.argv:
        exit_code = 3

        def finish_gui_smoke_test(attempts_remaining: int = 100) -> None:
            nonlocal exit_code
            app._refresh_tray_availability()
            if not app._tray_available and attempts_remaining > 0:
                app.after(
                    100,
                    lambda: finish_gui_smoke_test(attempts_remaining - 1),
                )
                return
            exit_code = 0 if app._tray_available else 3
            marker = os.getenv("O2_SMS_GUI_SMOKE_MARKER")
            if exit_code == 0 and marker:
                Path(marker).write_text("ok\n", encoding="utf-8")
            app._quit_application()

        app.after(100, finish_gui_smoke_test)
        app.mainloop()
        raise SystemExit(exit_code)
    app.mainloop()


if __name__ == "__main__":
    main()
