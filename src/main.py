"""Main entry point for Oracle report generation."""

from __future__ import annotations

from dataclasses import replace
import logging
import sys

import oracledb

from config import AppSettings, load_log_file, load_settings
from src.db.oracle_connection import get_connection
from src.reporting.data_extractor import extract_sales_data
from src.reporting.excel_formatter import export_report
from src.reporting.pivot_generator import create_sales_pivot
from src.utils.console_password import prompt_password_masked
from src.utils.logger import setup_logging

LOGGER = logging.getLogger(__name__)


def main() -> int:
    """Run the report generation workflow."""

    setup_logging(load_log_file())

    try:
        settings = load_settings()
        LOGGER.info("Avvio generazione report vendite")

        dataframe = _extract_with_retry(settings)

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


def _extract_with_retry(settings: AppSettings):
    current_settings = settings
    retried = False

    while True:
        try:
            with get_connection(current_settings.oracle) as connection:
                return extract_sales_data(connection, current_settings.query)
        except oracledb.DatabaseError as exc:
            if retried or not _is_authentication_error(exc):
                raise
            print("Autenticazione Oracle fallita. Reinserire la password.")
            new_secret = prompt_password_masked("Inserisci password Oracle: ")
            current_settings = replace(
                current_settings,
                oracle=replace(current_settings.oracle, **{"password": new_secret}),
            )
            retried = True


def _is_authentication_error(exc: oracledb.DatabaseError) -> bool:
    error = exc.args[0] if exc.args else None
    return getattr(error, "code", None) == 1017 or "ORA-01017" in str(exc).upper()


if __name__ == "__main__":
    raise SystemExit(main())
