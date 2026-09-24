"""Main entry point for the Oracle onboarding error report generator."""

from __future__ import annotations

import argparse
import getpass
import logging
import sys

import oracledb

from config import load_settings, load_test_settings
from src.db.oracle_connection import try_connect
from src.reporting.data_extractor import extract_report_data, load_mock_dataframe_from_excel, load_query_text
from src.reporting.excel_formatter import export_report
from src.reporting.pivot_generator import build_report
from src.reporting.validator import validate_against_reference
from src.security.credential_manager import (
    OracleCredentials,
    delete_saved_credentials,
    load_saved_credentials,
    save_credentials,
)
from src.utils.logger import setup_logging

LOGGER = logging.getLogger(__name__)


def _ask_credentials() -> OracleCredentials:
    print("Inserire le credenziali Oracle.")
    username = input("Username Oracle: ").strip()
    password = getpass.getpass("Password Oracle: ")
    return OracleCredentials(username=username, password=password)


def _authenticate() -> oracledb.Connection:
    """Authenticate against Oracle, retrying once with fresh credentials on failure."""

    saved = load_saved_credentials()
    if saved is not None:
        try:
            connection = try_connect(saved)
            LOGGER.info("Connessione Oracle riuscita con credenziali salvate")
            return connection
        except oracledb.DatabaseError as exc:
            LOGGER.warning("Credenziali salvate non valide, richiesta nuova autenticazione")
            delete_saved_credentials()

    credentials = _ask_credentials()
    try:
        connection = try_connect(credentials)
    except oracledb.DatabaseError as exc:
        LOGGER.error("Autenticazione Oracle fallita")
        raise RuntimeError("Impossibile autenticarsi su Oracle con le credenziali fornite") from exc

    save_credentials(credentials)
    LOGGER.info("Connessione Oracle riuscita, credenziali aggiornate")
    return connection


def main() -> int:
    """Run the report generation workflow."""

    args = _parse_args()

    if args.test_excel:
        return _run_test_excel_mode()

    settings = load_settings()
    setup_logging(settings.log_file)

    try:
        LOGGER.info("Avvio applicazione")
        query_text = load_query_text(settings.query_file)

        connection = _authenticate()
        try:
            LOGGER.info("Esecuzione query su Oracle")
            dataframe = extract_report_data(connection, settings.query_file)
        finally:
            connection.close()

        if dataframe.empty:
            print("Attenzione: la query non ha restituito alcun dato.")
            LOGGER.warning("Query eseguita senza righe restituite")

        model = build_report(dataframe, query_text)

        LOGGER.info("Generazione file Excel")
        export_report(model, settings.output_file)

        print(f"Report generato correttamente: {settings.output_file}")
        LOGGER.info("Processo completato con successo")
        return 0

    except FileNotFoundError as exc:
        _fail("File non trovato", exc)
    except RuntimeError as exc:
        _fail("Autenticazione non riuscita", exc)
    except oracledb.DatabaseError as exc:
        _fail("Connessione Oracle o query fallita", exc)
    except PermissionError as exc:
        _fail("File Excel bloccato o non scrivibile", exc)
    except ValueError as exc:
        _fail("Dati non validi", exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        _fail("Errore inatteso durante la generazione del report", exc)

    return 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generatore report Excel Aidexa")
    parser.add_argument(
        "--test-excel",
        action="store_true",
        help=(
            "Modalità offline: legge examples/caso1/input.xlsx al posto di Oracle, "
            "genera output_test.xlsx e lo confronta con examples/caso1/output_atteso.xlsx. "
            "Nessuna connessione, query o credenziale Oracle viene utilizzata."
        ),
    )
    return parser.parse_args()


def _run_test_excel_mode() -> int:
    """Offline mode: build the report from a static Excel dump instead of Oracle.

    Used to validate transformation logic and Excel formatting without any
    database access, credential prompt or query execution.
    """

    settings = load_test_settings()
    setup_logging(settings.log_file)

    try:
        LOGGER.info("Avvio modalità test Excel (nessuna connessione Oracle)")
        print("Modalità test: nessuna connessione Oracle verrà effettuata.")

        query_text = load_query_text(
            settings.reference_file.parent / "query.sql"
        )
        dataframe = load_mock_dataframe_from_excel(settings.input_file)

        if dataframe.empty:
            print("Attenzione: il file di input non contiene alcuna riga.")
            LOGGER.warning("Input di test senza righe")

        model = build_report(dataframe, query_text)

        LOGGER.info("Generazione file Excel di test")
        export_report(model, settings.output_file)
        print(f"File generato: {settings.output_file}")

        report = validate_against_reference(settings.output_file, settings.reference_file)
        print()
        print("=== Report differenze rispetto a output_atteso.xlsx ===")
        print(report.render())

        LOGGER.info("Modalità test Excel completata (identico=%s)", report.is_valid)
        return 0 if report.is_valid else 2

    except FileNotFoundError as exc:
        _fail("File non trovato", exc)
    except ValueError as exc:
        _fail("Dati non validi", exc)
    except PermissionError as exc:
        _fail("File Excel bloccato o non scrivibile", exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        _fail("Errore inatteso durante il test Excel", exc)

    return 1


def _fail(message: str, exc: Exception) -> None:
    logger = logging.getLogger(__name__)
    full_message = f"{message}: {exc}"
    if logging.getLogger().handlers:
        logger.error(full_message)
    print(full_message, file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
