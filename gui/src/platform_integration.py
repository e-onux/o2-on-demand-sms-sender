"""Cross-platform process, settings, and startup integration helpers."""

from __future__ import annotations

import json
import os
import plistlib
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


APP_ID = "com.emironuk.o2-sms-control-panel"
WINDOWS_RUN_NAME = "O2SMSControlPanel"


def settings_path() -> Path:
    """Return a user-writable settings path outside the project checkout."""
    if sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support" / "O2SMSControlPanel"
    elif sys.platform == "win32":
        root = Path(os.getenv("APPDATA", str(Path.home() / "AppData" / "Roaming"))) / "O2SMSControlPanel"
    else:
        root = Path(os.getenv("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "o2-sms-control-panel"
    return root / "settings.json"


def load_settings() -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "language": "tr",
        "close_to_tray": True,
        "start_at_login": False,
    }
    try:
        value = json.loads(settings_path().read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return defaults
    if isinstance(value, dict):
        defaults.update(value)
    return defaults


def save_settings(settings: Mapping[str, Any]) -> None:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(f".json.{os.getpid()}.tmp")
    temporary_path.write_text(
        json.dumps(dict(settings), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary_path, path)


def enriched_subprocess_environment(source: Mapping[str, str] | None = None) -> dict[str, str]:
    """Add common CLI locations missing from Finder and desktop launchers."""
    environment = dict(source if source is not None else os.environ)
    candidates = [
        str(Path.home() / ".docker" / "bin"),
        "/usr/local/bin",
        "/opt/homebrew/bin",
        "/Applications/Docker.app/Contents/Resources/bin",
    ]
    if sys.platform == "win32":
        program_files = environment.get("ProgramFiles", r"C:\Program Files")
        candidates.append(str(Path(program_files) / "Docker" / "Docker" / "resources" / "bin"))
    existing = environment.get("PATH", "").split(os.pathsep)
    ordered = [entry for entry in (*candidates, *existing) if entry]
    environment["PATH"] = os.pathsep.join(dict.fromkeys(ordered))
    return environment


def launch_command(project_dir: Path, *, minimized: bool = False) -> list[str]:
    """Build a stable command for packaged and source-based launches."""
    if getattr(sys, "frozen", False):
        command = [sys.executable]
    else:
        executable = Path(sys.executable)
        if sys.platform == "win32" and executable.name.casefold() == "python.exe":
            pythonw = executable.with_name("pythonw.exe")
            if pythonw.is_file():
                executable = pythonw
        command = [str(executable), str(Path(__file__).with_name("control_panel.py"))]
    if minimized:
        command.append("--minimized")
    command.extend(("--project-dir", str(project_dir)))
    return command


def _quote_desktop_argument(value: str) -> str:
    return shlex.quote(value)


def set_start_at_login(enabled: bool, project_dir: Path) -> None:
    """Enable or disable per-user minimized startup for the current platform."""
    command = launch_command(project_dir, minimized=True)
    if sys.platform == "darwin":
        path = Path.home() / "Library" / "LaunchAgents" / f"{APP_ID}.plist"
        if not enabled:
            path.unlink(missing_ok=True)
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "Label": APP_ID,
            "ProgramArguments": command,
            "RunAtLoad": True,
            "KeepAlive": False,
            "WorkingDirectory": str(project_dir),
        }
        temporary_path = path.with_suffix(".plist.tmp")
        temporary_path.write_bytes(plistlib.dumps(payload, sort_keys=True))
        os.replace(temporary_path, path)
        return

    if sys.platform == "win32":
        import winreg

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
            if enabled:
                winreg.SetValueEx(key, WINDOWS_RUN_NAME, 0, winreg.REG_SZ, subprocess.list2cmdline(command))
            else:
                try:
                    winreg.DeleteValue(key, WINDOWS_RUN_NAME)
                except FileNotFoundError:
                    pass
        return

    path = Path(os.getenv("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "autostart" / "o2-sms-control-panel.desktop"
    if not enabled:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    executable = " ".join(_quote_desktop_argument(value) for value in command)
    content = "\n".join(
        (
            "[Desktop Entry]",
            "Type=Application",
            "Name=O2 SMS Control Panel",
            f"Exec={executable}",
            f"Path={project_dir}",
            "Terminal=false",
            "X-GNOME-Autostart-enabled=true",
            "",
        )
    )
    temporary_path = path.with_suffix(".desktop.tmp")
    temporary_path.write_text(content, encoding="utf-8")
    os.replace(temporary_path, path)
