"""Main entry point for the Oracle onboarding error report generator."""

from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import datetime

import oracledb
import pandas as pd

from config import load_settings, load_test_settings
from src.db.oracle_connection import (
    ThickModeUnavailableError,
    TnsPingToolMissingError,
    resolve_tns_admin,
    run_tnsping,
    try_connect,
    try_connect_dsn,
)
from src.reporting.data_extractor import (
    MONTH_NAMES,
    available_years,
    extract_report_data,
    filter_report_data,
    load_mock_dataframe_from_excel,
    load_query_text,
    month_dates,
)
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
        LOGGER.error("Autenticazione Oracle fallita: %s", str(exc).splitlines()[0])
        raise RuntimeError(
            f"Impossibile autenticarsi su Oracle con le credenziali fornite ({str(exc).splitlines()[0]})"
        ) from exc

    if save_credentials(credentials):
        LOGGER.info("Connessione Oracle riuscita, credenziali aggiornate")
    else:
        LOGGER.warning("Connessione Oracle riuscita, ma salvataggio credenziali non riuscito")
    return connection


def main() -> int:
    """Run the report generation workflow."""

    args = _parse_args()

    if args.test_excel:
        return _run_test_excel_mode()

    if args.test_month:
        return _run_test_month_mode()

    if args.test_db:
        return _run_test_db_mode()

    settings = load_settings()
    setup_logging(settings.log_file)

    try:
        LOGGER.info("Avvio applicazione")
        query_text = load_query_text(settings.query_file)

        connection = _authenticate()
        LOGGER.info("Connessione Oracle attiva: versione database %s", connection.version)
        month = _ask_month()
        LOGGER.info("Mese selezionato: %s", MONTH_NAMES[month - 1])
        try:
            LOGGER.info("Esecuzione query Oracle")
            dataframe = extract_report_data(connection, settings.query_file, month)
        finally:
            connection.close()

        LOGGER.info("Record recuperati: %s", len(dataframe))
        dataframe, year = _filter_selected_period(dataframe, month)

        if dataframe.empty:
            print("Attenzione: nessun record per il mese selezionato.")
            LOGGER.warning("Nessun record dopo il filtro del periodo")

        model = build_report(dataframe, query_text, month_dates(month, year))

        LOGGER.info("Generazione file Excel")
        export_report(model, settings.output_file)

        print(f"Report generato correttamente: {settings.output_file}")
        LOGGER.info("[OK] Report completato")
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
    parser.add_argument(
        "--test-db",
        action="store_true",
        help=(
            "Modalità diagnostica: richiede un alias TNS, esegue un tnsping e prova la "
            "connessione Oracle con credenziali inserite a mano. Non genera alcun report "
            "e non modifica il comportamento della modalità normale."
        ),
    )
    parser.add_argument(
        "--test-month",
        action="store_true",
        help=(
            "Modalità offline: legge examples/caso1/input.xlsx, richiede il mese e "
            "genera output_test_month.xlsx senza connettersi a Oracle."
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


def _run_test_month_mode() -> int:
    """Generate a month-filtered report from the static Excel input."""

    settings = load_test_settings()
    setup_logging(settings.log_file)

    try:
        print("Modalità test mese: nessuna connessione Oracle verrà effettuata.")
        query_text = load_query_text(settings.reference_file.parent / "query.sql")
        dataframe = load_mock_dataframe_from_excel(settings.input_file)
        LOGGER.info("Record recuperati: %s", len(dataframe))

        month = _ask_month()
        LOGGER.info("Mese selezionato: %s", MONTH_NAMES[month - 1])
        dataframe, year = _filter_selected_period(dataframe, month)

        output_file = settings.output_file.with_name("output_test_month.xlsx")
        LOGGER.info("Generazione report Excel")
        export_report(build_report(dataframe, query_text, month_dates(month, year)), output_file)
        print(f"File generato: {output_file}")
        LOGGER.info("[OK] Report completato")
        return 0

    except FileNotFoundError as exc:
        _fail("File non trovato", exc)
    except ValueError as exc:
        _fail("Dati non validi", exc)
    except PermissionError as exc:
        _fail("File Excel bloccato o non scrivibile", exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        _fail("Errore inatteso durante il test mensile", exc)

    return 1


def _ask_month() -> int:
    """Prompt until the user enters a month number from 1 to 12."""

    print("\nSelezionare il mese da analizzare\n")
    for number, name in enumerate(MONTH_NAMES, start=1):
        print(f"{number} - {name}")

    while True:
        raw_value = input("\nInserire il numero del mese (1-12): ").strip()
        if not raw_value:
            print("Valore obbligatorio. Inserire un numero da 1 a 12.")
            continue
        if not raw_value.isdigit():
            print("Valore non valido. Inserire un numero da 1 a 12.")
            continue
        month = int(raw_value)
        if 1 <= month <= 12:
            return month
        print("Valore fuori intervallo. Inserire un numero da 1 a 12.")


def _filter_selected_period(dataframe: pd.DataFrame, month: int) -> tuple[pd.DataFrame, int]:
    """Ask for the year only when necessary, then apply the selected period."""

    years = available_years(dataframe)
    if len(years) == 1:
        year = years[0]
    elif not years:
        year = datetime.now().year
    else:
        year = _ask_year(years)

    LOGGER.info("Anno selezionato: %s", year)
    LOGGER.info("Applicazione filtro mese")
    filtered = filter_report_data(dataframe, month, year)
    LOGGER.info("Record dopo filtro: %s", len(filtered))
    return filtered, year


def _ask_year(available: list[int]) -> int:
    """Prompt for a valid year, restricted to years present in the source data."""

    if available:
        print(f"Anni disponibili: {', '.join(str(year) for year in available)}")
    while True:
        raw_value = input("Inserire anno da analizzare: ").strip()
        if not raw_value:
            print("Valore obbligatorio. Inserire un anno numerico.")
            continue
        if not raw_value.isdigit():
            print("Valore non valido. Inserire un anno numerico.")
            continue
        year = int(raw_value)
        if not available or year in available:
            return year
        print("Anno non presente nei dati estratti. Scegliere uno degli anni disponibili.")


def _report(tag: str, message: str, level: int = logging.INFO) -> None:
    """Print a human-readable tagged line and mirror it into the log file."""

    print(f"[{tag}] {message}")
    LOGGER.log(level, message)


def _describe_oracle_error(exc: oracledb.Error) -> str:
    """Translate an oracledb error into a short, non-technical message."""

    text = str(exc)
    if "ORA-01017" in text:
        return "Credenziali non valide. Controllare username e password."
    if "ORA-12154" in text or "TNS-12154" in text:
        return "Alias TNS non trovato. Verificare il nome del database inserito."
    if any(code in text for code in ("ORA-12541", "ORA-12170", "ORA-12537", "ORA-12535", "ORA-12560")):
        return "Database non raggiungibile tramite TNS. Verificare la connettività di rete."
    if any(code in text for code in ("DPY-4026", "DPY-4027", "DPY-4033")):
        return (
            "Impossibile risolvere l'alias TNS dal client Python. Verificare che la variabile "
            "d'ambiente TNS_ADMIN punti alla cartella con tnsnames.ora."
        )
    return f"Connessione Oracle fallita: {text.splitlines()[0].strip()}"


def _run_test_db_mode() -> int:
    """Interactive diagnostic mode: tnsping + credential test on a user-provided TNS alias.

    Does not read/write the report, does not touch saved credentials, and never
    affects the fixed production DSN used by the normal workflow.
    """

    settings = load_settings()
    setup_logging(settings.log_file, console=False)

    _report("INFO", "Avvio test connessione Oracle")

    alias = input("Inserisci il nome del database (TNS Alias): ").strip()
    if not alias:
        _report("ERRORE", "Nome database non valido.", logging.ERROR)
        return 1
    _report("INFO", f"Database richiesto: {alias}")

    _report("INFO", "Esecuzione tnsping...")
    try:
        ping_result = run_tnsping(alias)
    except TnsPingToolMissingError as exc:
        _report("ERRORE", str(exc), logging.ERROR)
        return 1

    if not ping_result.success:
        _report("ERRORE", ping_result.user_message, logging.ERROR)
        return 1

    _report("OK", "Database raggiungibile")
    if ping_result.host:
        _report("INFO", f"Host individuato: {ping_result.host}")
    if ping_result.port:
        _report("INFO", f"Porta individuata: {ping_result.port}")
    if ping_result.service_name:
        _report("INFO", f"Service Name individuato: {ping_result.service_name}")
    if ping_result.response_time_ms is not None:
        _report("INFO", f"Tempo risposta: {ping_result.response_time_ms} ms")

    _report("INFO", "Richiesta credenziali utente")
    print("Inserire le credenziali Oracle per il test.")
    username = input("Username Oracle: ").strip()
    password = masked_input("Password Oracle: ")

    config_dir = resolve_tns_admin(ping_result.tnsping_path)
    if config_dir:
        _report("INFO", f"Configurazione TNS individuata: {config_dir}")
    else:
        _report("WARNING", "Variabile TNS_ADMIN non impostata: verrà usata la configurazione di default.", logging.WARNING)

    _report("INFO", "Tentativo connessione Oracle")
    start = time.perf_counter()
    try:
        connection = try_connect_dsn(
            OracleCredentials(username=username, password=password), alias, config_dir=config_dir
        )
    except ThickModeUnavailableError as exc:
        _report("ERRORE", str(exc), logging.ERROR)
        return 1
    except oracledb.Error as exc:
        _report("ERRORE", _describe_oracle_error(exc), logging.ERROR)
        return 1

    elapsed_ms = round((time.perf_counter() - start) * 1000)
    try:
        _report("OK", "Connessione Oracle riuscita")
        _report("INFO", f"Versione database: {connection.version}")
        _report("INFO", f"Utente autenticato: {username}")
        _report("INFO", f"Tempo di connessione: {elapsed_ms} ms")
        _report("INFO", "Test completato con successo")
    finally:
        connection.close()

    return 0


def _fail(message: str, exc: Exception) -> None:
    logger = logging.getLogger(__name__)
    full_message = f"{message}: {exc}"
    if exc.__cause__ is not None and str(exc.__cause__) not in full_message:
        full_message += f" | causa originale: {exc.__cause__}"
    if logging.getLogger().handlers:
        logger.error(full_message)
    print(full_message, file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
