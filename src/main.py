"""Main entry point for the Oracle onboarding error report generator."""

from __future__ import annotations

import argparse
import logging
import sys

# Ensure config-loading log messages (emitted at import time by other
# modules) are visible before setup_logging() reconfigures with the file handler.
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

import oracledb

from config import get_config, load_settings, load_test_settings
from src.db.oracle_connection import try_connect
from src.reporting.data_extractor import (
    EXPECTED_PRODUCT_FILTERS,
    apply_period_filter,
    apply_product_filter,
    count_product_filters,
    filter_by_period,
    load_mock_dataframe_from_excel,
    load_query_text,
    run_query,
)
from src.reporting.excel_formatter import export_report, export_workbook
from src.reporting.period import Period, ask_period
from src.reporting.pivot_generator import ReportModel, build_report
from src.reporting.validator import validate_against_reference
from src.security.credential_manager import (
    OracleCredentials,
    delete_saved_credentials,
    load_saved_credentials,
    save_credentials,
)
from src.utils.logger import setup_logging
from src.utils.masked_input import masked_input

LOGGER = logging.getLogger(__name__)


def _ask_credentials() -> OracleCredentials:
    print("Inserire le credenziali Oracle.")
    username = input("Username Oracle: ").strip()
    password = masked_input("Password Oracle: ")
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

    if save_credentials(credentials):
        LOGGER.info("Connessione Oracle riuscita, credenziali aggiornate")
    else:
        LOGGER.warning("Connessione Oracle riuscita, ma salvataggio credenziali non riuscito")
    return connection


def main() -> int:
    """Run the report generation workflow."""

    args = _parse_args()

    if args.generate_config:
        target = get_config().generate_example_file()
        print(f"File di configurazione generato: {target}")
        return 0

    if args.test_excel:
        return _run_test_excel_mode()

    if args.test_full:
        return _run_test_full_mode(args)

    settings = load_settings()
    setup_logging(settings.log_file)

    try:
        LOGGER.info("Avvio applicazione")
        query_text = load_query_text(settings.query_file)
        _check_product_filters(query_text)

        products = get_config().products
        sheets: list[tuple[str, ReportModel]] = []

        connection = _authenticate()
        try:
            period = ask_period(
                ask_month=get_config().require_month,
                ask_year=get_config().require_year,
            )
            print(f"Periodo analizzato: {period.label()}")

            for sheet_name, product_code in products:
                LOGGER.info("Generazione worksheet %s", sheet_name)
                LOGGER.info("Parametro prodotto: %s", product_code)

                product_query = apply_period_filter(
                    apply_product_filter(query_text, product_code), period
                )
                dataframe = run_query(connection, product_query)
                LOGGER.info("Query eseguita correttamente")

                dataframe = filter_by_period(dataframe, period)

                if dataframe.empty:
                    print(f"Attenzione: nessun dato per il prodotto {product_code} nel periodo selezionato.")
                    LOGGER.warning("Nessuna riga nel periodo selezionato (%s)", product_code)

                sheets.append(
                    (sheet_name, build_report(dataframe, product_query, dates=period.days()))
                )
                LOGGER.info("Worksheet %s completato", sheet_name)
        finally:
            connection.close()

        LOGGER.info("Generazione file Excel")
        export_workbook(sheets, settings.output_file)
        LOGGER.info("Workbook completato")

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


def _check_product_filters(query_text: str) -> None:
    """Log how many prdt_code filters the query contains before running it."""

    found = count_product_filters(query_text)
    if found == EXPECTED_PRODUCT_FILTERS:
        LOGGER.info("Occorrenze filtro prodotto trovate: %s", found)
    else:
        LOGGER.warning("Numero occorrenze filtro inatteso: %s", found)


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
    parser.add_argument(
        "--generate-config",
        action="store_true",
        help="Genera config.example.json con tutti i parametri disponibili ed esce.",
    )
    parser.add_argument(
        "--test-full",
        action="store_true",
        help=(
            "Simulazione completa offline: usa examples/caso1/input.xlsx come risultato "
            "della query per ogni prodotto configurato, applica la selezione del periodo "
            "e genera il workbook a due fogli. Nessuna connessione Oracle."
        ),
    )
    parser.add_argument("--month", type=int, help="Mese (1-12) da usare con --test-full, senza prompt.")
    parser.add_argument("--year", type=int, help="Anno (YYYY) da usare con --test-full, senza prompt.")
    return parser.parse_args()


def _run_test_full_mode(args: argparse.Namespace) -> int:
    """Offline end-to-end simulation: period selection + one sheet per product."""

    settings = load_settings()
    test_settings = load_test_settings()
    setup_logging(settings.log_file)

    try:
        LOGGER.info("Avvio simulazione completa (nessuna connessione Oracle)")
        print("Modalità test completa: nessuna connessione Oracle verrà effettuata.")

        query_text = load_query_text(settings.query_file)
        _check_product_filters(query_text)

        if args.month is not None and args.year is not None:
            period = Period(year=args.year, month=args.month)
            LOGGER.info("Mese selezionato: %s", period.month)
            LOGGER.info("Anno selezionato: %s", period.year)
            LOGGER.info("Periodo analizzato: %s", period.label())
        else:
            period = ask_period(
                ask_month=get_config().require_month,
                ask_year=get_config().require_year,
            )
        print(f"Periodo analizzato: {period.label()}")

        source = load_mock_dataframe_from_excel(test_settings.input_file)
        sheets: list[tuple[str, ReportModel]] = []

        for sheet_name, product_code in get_config().products:
            LOGGER.info("Generazione worksheet %s", sheet_name)
            LOGGER.info("Parametro prodotto: %s", product_code)

            product_query = apply_period_filter(
                apply_product_filter(query_text, product_code), period
            )
            dataframe = filter_by_period(source, period)
            sheets.append(
                (sheet_name, build_report(dataframe, product_query, dates=period.days()))
            )
            LOGGER.info("Worksheet %s completato", sheet_name)

        output_file = settings.output_file.with_name("report_test.xlsx")
        export_workbook(sheets, output_file)
        LOGGER.info("Workbook completato")
        print(f"File generato: {output_file}")
        return 0

    except FileNotFoundError as exc:
        _fail("File non trovato", exc)
    except ValueError as exc:
        _fail("Dati non validi", exc)
    except PermissionError as exc:
        _fail("File Excel bloccato o non scrivibile", exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        _fail("Errore inatteso durante la simulazione", exc)

    return 1


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
