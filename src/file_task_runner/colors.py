"""ANSI color helpers shared by the runner and task scripts."""

from __future__ import annotations

import os
import sys

RESET = "\033[0m"
RED = "91"
GREEN = "92"
YELLOW = "93"
CYAN = "96"
GRAY = "90"

# Same character table and weights as the old ffprobe-simple.bat, so colors stay familiar.
HASH_CHARS = "abcdefghijklmnopqrstuvwxyz0123456789._ "
# Bright 91-96 followed by dark 31-36 (hard-to-read colors left out).
HASH_PALETTE = ("91", "92", "93", "94", "95", "96", "31", "32", "33", "34", "35", "36")

_enabled: bool | None = None


def enabled() -> bool:
    global _enabled
    if _enabled is None:
        _enabled = (
            "NO_COLOR" not in os.environ
            and sys.stdout.isatty()
            and _enable_vt_mode()
        )
    return _enabled


def _enable_vt_mode() -> bool:
    if sys.platform != "win32":
        return True
    import ctypes

    kernel32 = ctypes.windll.kernel32
    handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
    mode = ctypes.c_uint32()
    if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
        return False
    ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
    return bool(kernel32.SetConsoleMode(handle, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING))


def color(text: str, code: str) -> str:
    return f"\033[{code}m{text}{RESET}" if enabled() else text


def hash_value(text: str, chars: str = HASH_CHARS) -> int:
    """Each known character adds `index * 7 + 3`; unknown characters are ignored."""
    total = 0
    for c in text.lower():
        i = chars.find(c)
        if i >= 0:
            total += i * 7 + 3
    return total


def hash_color(text: str) -> str:
    """The same text always gets the same color."""
    return HASH_PALETTE[hash_value(text) % len(HASH_PALETTE)]
