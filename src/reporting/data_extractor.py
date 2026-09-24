"""Data extraction logic for the Oracle onboarding error report."""

from __future__ import annotations

import logging
from calendar import monthrange
from datetime import datetime
from pathlib import Path
from time import perf_counter

import pandas as pd
import oracledb
from openpyxl import load_workbook

LOGGER = logging.getLogger(__name__)

# Column layout of examples/caso1/query.sql (last two columns have no alias).
COLUMNS = ["URLL", "DATAA", "STATOO", "TIPO_ERRORE", "CONTEGGIO", "CONTEGGIO_RAW"]

# Header labels expected on row 1 of examples/*/input.xlsx (order-independent lookup).
_INPUT_HEADER_NAMES = ["URLL", "DATAA", "STATOO", "TIPO_ERRORE"]

MONTH_NAMES = (
    "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
    "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre",
)


def load_query_text(query_file: Path) -> str:
    """Read the SQL query text from disk."""

    if not query_file.is_file():
        raise FileNotFoundError(f"File query non trovato: {query_file}")

    text = query_file.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"Il file query è vuoto: {query_file}")
    if text.endswith(";"):
        text = text[:-1].rstrip()
    return text


def extract_report_data(
    connection: oracledb.Connection,
    query_file: Path,
    selected_month: int,
) -> pd.DataFrame:
    """Execute the query for the selected month in Oracle's current year."""

    if not 1 <= selected_month <= 12:
        raise ValueError("Il mese deve essere compreso tra 1 e 12.")

    query_text = load_query_text(query_file)
    LOGGER.info("File query Oracle: %s", query_file)
    LOGGER.info("Bind Oracle: selected_month=%s", selected_month)
    LOGGER.info("Query Oracle in esecuzione:\n%s", query_text)

    start = perf_counter()
    try:
        with connection.cursor() as cursor:
            cursor.execute(query_text, selected_month=selected_month)
            column_names = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
    except oracledb.DatabaseError:
        LOGGER.exception("Esecuzione query Oracle fallita. Query eseguita:\n%s", query_text)
        raise

    dataframe = pd.DataFrame(rows, columns=COLUMNS)
    elapsed_ms = round((perf_counter() - start) * 1000)
    LOGGER.info("Query Oracle completata in %s ms", elapsed_ms)
    LOGGER.info("Colonne restituite da Oracle: %s", ", ".join(column_names))
    LOGGER.info("Record recuperati da Oracle: %s", len(dataframe))
    _log_result_summary(dataframe)
    return dataframe


def available_years(dataframe: pd.DataFrame) -> list[int]:
    """Return sorted years available in the report date column."""

    dates = _parse_report_dates(dataframe)
    return sorted(dates.dt.year.unique().tolist())


def filter_report_data(dataframe: pd.DataFrame, month: int, year: int) -> pd.DataFrame:
    """Keep only records belonging to the selected calendar month and year."""

    if not 1 <= month <= 12:
        raise ValueError("Il mese deve essere compreso tra 1 e 12.")

    dates = _parse_report_dates(dataframe)
    filtered = dataframe.loc[(dates.dt.month == month) & (dates.dt.year == year)].copy()
    filtered["DATAA"] = pd.to_datetime(filtered["DATAA"]).dt.normalize()
    LOGGER.info(
        "Filtro applicato su DATAA: anno=%s, mese=%s, record=%s",
        year,
        month,
        len(filtered),
    )
    return filtered


def month_dates(month: int, year: int) -> list[datetime]:
    """Return every day in a month, including days with no database records."""

    if not 1 <= month <= 12:
        raise ValueError("Il mese deve essere compreso tra 1 e 12.")
    return [datetime(year, month, day) for day in range(1, monthrange(year, month)[1] + 1)]


def _parse_report_dates(dataframe: pd.DataFrame) -> pd.Series:
    """Parse DATAA and reject missing or invalid values before period filtering."""

    if "DATAA" not in dataframe:
        raise ValueError("Colonna data 'DATAA' non presente nei dati estratti.")

    dates = pd.to_datetime(dataframe["DATAA"], errors="coerce")
    if dates.isna().any():
        raise ValueError("La colonna data 'DATAA' contiene valori nulli o non validi.")
    return dates


def _log_result_summary(dataframe: pd.DataFrame) -> None:
    """Log result-set diagnostics without recording credentials or row contents."""

    if dataframe.empty:
        LOGGER.warning("La query Oracle non ha restituito record.")
        return

    dates = _parse_report_dates(dataframe)
    LOGGER.info(
        "Intervallo DATAA restituito: %s - %s; giorni distinti=%s",
        dates.min().strftime("%d/%m/%Y"),
        dates.max().strftime("%d/%m/%Y"),
        dates.dt.normalize().nunique(),
    )
    LOGGER.info("Record per TIPO_ERRORE: %s", dataframe["TIPO_ERRORE"].value_counts().to_dict())
    LOGGER.info("URL distinti: %s; STATOO distinti: %s", dataframe["URLL"].nunique(), sorted(dataframe["STATOO"].dropna().astype(str).unique()))


def load_mock_dataframe_from_excel(input_file: Path) -> pd.DataFrame:
    """Load a DataFrame with the same shape as extract_report_data(), but read
    from an Excel dump of a query result set (used by the --test-excel mode
    to simulate the Oracle extraction without any database access)."""

    if not input_file.is_file():
        raise FileNotFoundError(f"File di input non trovato: {input_file}")

    workbook = load_workbook(input_file, data_only=True)
    worksheet = workbook[workbook.sheetnames[0]]

    header_row = [worksheet.cell(row=1, column=col).value for col in range(1, worksheet.max_column + 1)]
    column_positions = {}
    for name in _INPUT_HEADER_NAMES:
        try:
            column_positions[name] = header_row.index(name) + 1
        except ValueError as exc:
            raise ValueError(f"Colonna '{name}' non trovata in {input_file}") from exc

    # The value column ("NVL(...)") has no stable alias: it is positioned
    # right after TIPO_ERRORE, followed by the unused raw conteggio column.
    value_col = column_positions["TIPO_ERRORE"] + 1

    rows = []
    for row_index in range(2, worksheet.max_row + 1):
        url = worksheet.cell(row=row_index, column=column_positions["URLL"]).value
        if url is None:
            continue
        rows.append(
            (
                url,
                worksheet.cell(row=row_index, column=column_positions["DATAA"]).value,
                worksheet.cell(row=row_index, column=column_positions["STATOO"]).value,
                worksheet.cell(row=row_index, column=column_positions["TIPO_ERRORE"]).value,
                worksheet.cell(row=row_index, column=value_col).value or 0,
                None,
            )
        )

    dataframe = pd.DataFrame(rows, columns=COLUMNS)
    LOGGER.info("Caricate %s righe da %s (modalità test, nessuna connessione Oracle)", len(dataframe), input_file)
    return dataframe

