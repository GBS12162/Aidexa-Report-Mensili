"""Data extraction logic for the Oracle onboarding error report."""

from __future__ import annotations

import logging
import re
from pathlib import Path

import pandas as pd
import oracledb
from openpyxl import load_workbook

from config import get_config
from src.reporting.period import Period

LOGGER = logging.getLogger(__name__)

# Column layout of examples/caso1/query.sql (last two columns have no alias).
COLUMNS = get_config().query_columns

# Header labels expected on row 1 of examples/*/input.xlsx (order-independent lookup).
_INPUT_HEADER_NAMES = get_config().input_header_names

# Matches `pr.prdt_code IN ('SOME_CODE')` (any case/spacing) capturing the code.
_PRODUCT_FILTER_PATTERN = re.compile(
    r"(prdt_code\s+IN\s*\(\s*')([^']+)('\s*\))", re.IGNORECASE
)

EXPECTED_PRODUCT_FILTERS = 2

# Matches the date part of the TO_TIMESTAMP bounds of the query; the time part
# tells whether it is the lower (00:00:00.000000) or upper (23:59:59.999999) bound.
_PERIOD_BOUND_PATTERN = re.compile(
    r"'(\d{2}/\d{2}/\d{4}) (00:00:00\.000000|23:59:59\.999999)'"
)


def count_product_filters(query_text: str) -> int:
    """Return how many prdt_code IN (...) filters the query contains."""

    return len(_PRODUCT_FILTER_PATTERN.findall(query_text))


def apply_product_filter(query_text: str, product_code: str) -> str:
    """Return the query with every prdt_code filter set to product_code."""

    if "'" in product_code:
        raise ValueError(f"Codice prodotto non valido: {product_code}")

    replaced, count = _PRODUCT_FILTER_PATTERN.subn(
        lambda match: f"{match.group(1)}{product_code}{match.group(3)}", query_text
    )
    if count == 0:
        raise ValueError("Nessun filtro prdt_code trovato nella query")
    return replaced


def apply_period_filter(query_text: str, period: Period) -> str:
    """Return the query with every TO_TIMESTAMP bound moved to the given period."""

    def _replace(match: re.Match[str]) -> str:
        time_part = match.group(2)
        day = period.start if time_part.startswith("00:") else period.end
        return f"'{day:%d/%m/%Y} {time_part}'"

    replaced, count = _PERIOD_BOUND_PATTERN.subn(_replace, query_text)
    if count == 0:
        raise ValueError("Nessun intervallo temporale TO_TIMESTAMP trovato nella query")
    LOGGER.info("Limiti temporali aggiornati nella query: %s", count)
    return replaced


def filter_by_period(dataframe: pd.DataFrame, period: Period) -> pd.DataFrame:
    """Keep only the rows whose DATAA falls inside the selected month/year."""

    LOGGER.info("Applicazione filtro temporale")
    LOGGER.info("Record recuperati: %s", len(dataframe))
    if dataframe.empty:
        LOGGER.info("Record dopo filtro: 0")
        return dataframe

    dates = pd.to_datetime(dataframe["DATAA"], errors="coerce")
    mask = (dates.dt.year == period.year) & (dates.dt.month == period.month)
    filtered = dataframe.loc[mask].copy()
    LOGGER.info("Record dopo filtro: %s", len(filtered))
    return filtered


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


def extract_report_data(connection: oracledb.Connection, query_file: Path) -> pd.DataFrame:
    """Execute the fixed SQL query and return the full result set as a DataFrame."""

    return run_query(connection, load_query_text(query_file))


def run_query(connection: oracledb.Connection, query_text: str) -> pd.DataFrame:
    """Execute an already-prepared SQL text and return the result set."""

    with connection.cursor() as cursor:
        cursor.execute(query_text)
        rows = cursor.fetchall()

    dataframe = pd.DataFrame(rows, columns=COLUMNS)
    LOGGER.info("Estratte %s righe da Oracle", len(dataframe))
    return dataframe


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

