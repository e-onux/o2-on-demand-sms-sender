#!/usr/bin/env python3
"""Explicit manual modem actions used by the desktop control panel.

Keeping this as a separate entry point makes manual buttons fail safely when an
older container image (without this file) is still running.
"""

import argparse

from o2_on_demand_hack import (
    clear_sms_inbox_manually,
    restart_modem_manually,
    send_manual_sms,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an explicit modem action")
    parser.add_argument(
        "action",
        choices=("send-sms", "clear-inbox", "restart-modem"),
    )
    arguments = parser.parse_args()

    if arguments.action == "send-sms":
        send_manual_sms()
    elif arguments.action == "clear-inbox":
        clear_sms_inbox_manually()
    else:
        restart_modem_manually()


if __name__ == "__main__":
    main()
