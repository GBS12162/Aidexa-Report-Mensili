"""Analysis period (month + year) selection and handling."""

from __future__ import annotations

import calendar
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime

LOGGER = logging.getLogger(__name__)

MONTH_NAMES: tuple[str, ...] = (
    "Gennaio",
    "Febbraio",
    "Marzo",
    "Aprile",
    "Maggio",
    "Giugno",
    "Luglio",
    "Agosto",
    "Settembre",
    "Ottobre",
    "Novembre",
    "Dicembre",
)

_YEAR_PATTERN = re.compile(r"^\d{4}$")


@dataclass(frozen=True)
class Period:
    """A full calendar month, leap years included."""

    year: int
    month: int

    def __post_init__(self) -> None:
        if not 1 <= self.month <= 12:
            raise ValueError(f"Mese non valido: {self.month}")
        if not 1000 <= self.year <= 9999:
            raise ValueError(f"Anno non valido: {self.year}")

    @property
    def start(self) -> date:
        return date(self.year, self.month, 1)

    @property
    def end(self) -> date:
        return date(self.year, self.month, calendar.monthrange(self.year, self.month)[1])

    @property
    def month_name(self) -> str:
        return MONTH_NAMES[self.month - 1]

    def days(self) -> list[datetime]:
        """Every day of the month, as midnight datetimes."""

        last_day = self.end.day
        return [datetime(self.year, self.month, day) for day in range(1, last_day + 1)]

    def label(self) -> str:
        return f"{self.start:%d/%m/%Y} - {self.end:%d/%m/%Y}"


def parse_month(raw: str) -> int:
    """Validate a month entered by the user (1-12)."""

    value = raw.strip()
    if not value:
        raise ValueError("Mese non inserito.\nInserire un numero da 1 a 12.")
    try:
        month = int(value)
    except ValueError as exc:
        raise ValueError("Mese non valido.\nInserire un numero da 1 a 12.") from exc
    if not 1 <= month <= 12:
        raise ValueError("Mese non valido.\nInserire un numero da 1 a 12.")
    return month


def parse_year(raw: str) -> int:
    """Validate a year entered by the user (four digits)."""

    value = raw.strip()
    if not value:
        raise ValueError("Anno non inserito.\nInserire un anno nel formato YYYY.")
    if not _YEAR_PATTERN.match(value):
        raise ValueError("Anno non valido.\nInserire un anno nel formato YYYY.")
    return int(value)


def print_month_menu() -> None:
    print()
    print("Seleziona il mese da analizzare:")
    print()
    for index, name in enumerate(MONTH_NAMES, start=1):
        print(f"{index:<2} - {name}")
    print()


def ask_period(ask_month: bool = True, ask_year: bool = True, default: Period | None = None) -> Period:
    """Prompt for month and year until both are valid.

    A prompt is skipped only when disabled AND a default period is available;
    the year is never inferred from the current date.
    """

    if ask_month or default is None:
        print_month_menu()
        month = _ask_value("Mese (1-12): ", parse_month)
    else:
        month = default.month

    if ask_year or default is None:
        year = _ask_value("Inserisci l'anno da analizzare: ", parse_year)
    else:
        year = default.year

    period = Period(year=year, month=month)
    LOGGER.info("Mese selezionato: %s", period.month)
    LOGGER.info("Anno selezionato: %s", period.year)
    LOGGER.info("Periodo analizzato: %s", period.label())
    return period


def _ask_value(prompt: str, parser: Callable[[str], int]) -> int:
    while True:
        try:
            return parser(input(prompt))
        except ValueError as exc:
            print(f"[ERRORE] {exc}")
