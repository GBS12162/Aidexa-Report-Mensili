"""Console password input helpers with masked feedback."""

from __future__ import annotations

import sys
import getpass


def prompt_password_masked(prompt: str) -> str:
    """Read a password from terminal showing one '*' per typed character."""

    if not sys.stdin.isatty():
        return getpass.getpass(prompt)

    sys.stdout.write(prompt)
    sys.stdout.flush()

    if sys.platform.startswith("win"):
        return _prompt_windows()
    return _prompt_posix()


def _prompt_windows() -> str:
    import msvcrt  # pragma: no cover - windows-only

    chars: list[str] = []
    while True:
        key = msvcrt.getwch()

        if key in ("\r", "\n"):
            sys.stdout.write("\n")
            sys.stdout.flush()
            return "".join(chars)

        if key in ("\b", "\x08", "\x7f"):
            if chars:
                chars.pop()
                sys.stdout.write("\b \b")
                sys.stdout.flush()
            continue

        if key == "\x03":
            raise KeyboardInterrupt

        chars.append(key)
        sys.stdout.write("*")
        sys.stdout.flush()


def _prompt_posix() -> str:
    import termios
    import tty

    fd = sys.stdin.fileno()
    previous = termios.tcgetattr(fd)
    chars: list[str] = []

    try:
        tty.setraw(fd)
        while True:
            key = sys.stdin.read(1)

            if key in ("\r", "\n"):
                sys.stdout.write("\n")
                sys.stdout.flush()
                return "".join(chars)

            if key in ("\b", "\x08", "\x7f"):
                if chars:
                    chars.pop()
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
                continue

            if key == "\x03":
                raise KeyboardInterrupt

            chars.append(key)
            sys.stdout.write("*")
            sys.stdout.flush()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, previous)
