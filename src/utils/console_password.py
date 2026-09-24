"""Console password input helpers with masked feedback."""

from __future__ import annotations

import getpass
import sys
from typing import TextIO


def prompt_password_masked(prompt: str) -> str:
    """Read a password from terminal showing one '*' per typed character."""

    input_stream = _pick_tty_input_stream()
    output_stream = _pick_tty_output_stream()
    tty_stream = None

    if (input_stream is None or output_stream is None) and not sys.platform.startswith("win"):
        tty_stream = _open_posix_tty()
        if tty_stream is not None:
            input_stream = tty_stream
            output_stream = tty_stream

    if input_stream is None or output_stream is None:
        return getpass.getpass(prompt)

    output_stream.write(prompt)
    output_stream.flush()

    try:
        if sys.platform.startswith("win"):
            return _prompt_windows(output_stream)
        return _prompt_posix(input_stream, output_stream)
    finally:
        if tty_stream is not None:
            tty_stream.close()


def _pick_tty_input_stream() -> TextIO | None:
    for stream in (sys.stdin, sys.__stdin__):
        if stream is not None and stream.isatty():
            return stream
    return None


def _pick_tty_output_stream() -> TextIO | None:
    for stream in (sys.stdout, sys.__stdout__):
        if stream is not None and stream.isatty():
            return stream
    return None


def _open_posix_tty() -> TextIO | None:
    try:
        return open("/dev/tty", "r+", encoding="utf-8", buffering=1)
    except OSError:
        return None


def _prompt_windows(output_stream: TextIO) -> str:
    import msvcrt  # pragma: no cover - windows-only

    chars: list[str] = []
    while True:
        key = msvcrt.getwch()

        if key in ("\r", "\n"):
            output_stream.write("\n")
            output_stream.flush()
            return "".join(chars)

        if key in ("\b", "\x08", "\x7f"):
            if chars:
                chars.pop()
                output_stream.write("\b \b")
                output_stream.flush()
            continue

        if key == "\x03":
            raise KeyboardInterrupt

        chars.append(key)
        output_stream.write("*")
        output_stream.flush()


def _prompt_posix(input_stream: TextIO, output_stream: TextIO) -> str:
    import termios
    import tty

    fd = input_stream.fileno()
    previous = termios.tcgetattr(fd)
    chars: list[str] = []

    try:
        tty.setraw(fd)
        while True:
            key = input_stream.read(1)

            if key in ("\r", "\n"):
                output_stream.write("\n")
                output_stream.flush()
                return "".join(chars)

            if key in ("\b", "\x08", "\x7f"):
                if chars:
                    chars.pop()
                    output_stream.write("\b \b")
                    output_stream.flush()
                continue

            if key == "\x03":
                raise KeyboardInterrupt

            chars.append(key)
            output_stream.write("*")
            output_stream.flush()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, previous)
