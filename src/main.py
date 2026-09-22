"""Main entry point for Oracle report generation."""

from __future__ import annotations

import logging
from pathlib import Path
import sys

import oracledb

from config import load_settings
from src.db.oracle_connection import get_connection
from src.reporting.data_extractor import extract_sales_data
from src.reporting.excel_formatter import export_report
from src.reporting.pivot_generator import create_sales_pivot
from src.utils.logger import setup_logging


LOGGER = logging.getLogger(__name__)
DEFAULT_LOG_FILE = Path("logs/report.log")


def main() -> int:
    """Run the report generation workflow."""

    setup_logging(DEFAULT_LOG_FILE)

    try:
        settings = load_settings()
        if settings.log_file != DEFAULT_LOG_FILE:
            setup_logging(settings.log_file)
        LOGGER.info("Avvio generazione report vendite")

        with get_connection(settings.oracle) as connection:
            dataframe = extract_sales_data(connection, settings.query)

        pivot = create_sales_pivot(dataframe)
        export_report(dataframe, pivot, settings.output_file)
        LOGGER.info("Processo completato con successo")
        return 0
    except ValueError as exc:
        _log_and_print("Configurazione non valida", exc)
    except oracledb.DatabaseError as exc:
        _log_and_print("Connessione Oracle o query fallita", exc)
    except PermissionError as exc:
        _log_and_print("File Excel bloccato o non scrivibile", exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        _log_and_print("Errore inatteso durante la generazione del report", exc)

    return 1


def _log_and_print(message: str, exc: Exception) -> None:
    logger = logging.getLogger(__name__)
    if logging.getLogger().handlers:
        logger.error("%s: %s", message, exc)
    else:
        print(f"{message}: {exc}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
