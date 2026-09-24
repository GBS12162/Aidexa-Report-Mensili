"""Console password input that echoes '*' per character instead of hiding input."""

from __future__ import annotations

import sys

_BACKSPACE_CODES = {"\x08", "\x7f"}
_ENTER_CODES = {"\r", "\n"}


def masked_input(prompt: str = "") -> str:
    """Read a line from stdin, echoing '*' for each character typed.

    Supports Backspace and special characters. The real input is never
    written to stdout, logs, or error messages.
    """

    print(prompt, end="", flush=True)
    try:
        if sys.platform == "win32":
            password = _read_masked_windows()
        else:
            password = _read_masked_unix()
    except KeyboardInterrupt:
        print()
        raise
    print()
    return password


def _read_masked_windows() -> str:
    import msvcrt

    chars: list[str] = []
    while True:
        ch = msvcrt.getwch()
        if ch in _ENTER_CODES:
            break
        if ch == "\x03":
            raise KeyboardInterrupt
        if ch in _BACKSPACE_CODES:
            if chars:
                chars.pop()
                sys.stdout.write("\b \b")
                sys.stdout.flush()
            continue
        chars.append(ch)
        sys.stdout.write("*")
        sys.stdout.flush()
    return "".join(chars)


def _read_masked_unix() -> str:
    import termios
    import tty

    fd = sys.stdin.fileno()
    original_settings = termios.tcgetattr(fd)
    chars: list[str] = []
    try:
        tty.setraw(fd)
        while True:
            ch = sys.stdin.read(1)
            if ch in _ENTER_CODES:
                break
            if ch == "\x03":
                raise KeyboardInterrupt
            if ch in _BACKSPACE_CODES:
                if chars:
                    chars.pop()
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
                continue
            chars.append(ch)
            sys.stdout.write("*")
            sys.stdout.flush()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, original_settings)
    return "".join(chars)
