"""Oracle connection helpers (python-oracledb thin mode, DSN resolved via tnsping)."""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import oracledb

from config import get_app_dir, get_config
from src.security.credential_manager import OracleCredentials

LOGGER = logging.getLogger(__name__)

TNSPING_TIMEOUT_SECONDS = 60
_ALIAS_PATTERN = re.compile(r"^[A-Za-z0-9_.\-]+$")
_CONTACT_MARKER = "Attempting to contact"
_PE_MACHINE_AMD64 = 0x8664
INVALID_CREDENTIALS_CODE = "ORA-01017"


class TnsPingError(Exception):
    """Raised when tnsping is unavailable or cannot resolve the database name."""


class OracleClientNotFoundError(Exception):
    """Raised when thick mode is needed but no 64-bit Oracle Client is available."""


def error_code(exc: BaseException) -> str | None:
    """Return the Oracle/driver error code (e.g. ORA-01017, DPY-3015) of an exception."""

    error = exc.args[0] if exc.args else None
    return getattr(error, "full_code", None)


def is_invalid_credentials(exc: BaseException) -> bool:
    return error_code(exc) == INVALID_CREDENTIALS_CODE


@dataclass(frozen=True)
class OracleTarget:
    """Database name entered by the user and the DSN resolved by tnsping."""

    alias: str
    dsn: str


def _extract_descriptor(output: str) -> str | None:
    """Return the balanced (DESCRIPTION=...) string printed after 'Attempting to contact'."""

    marker = output.find(_CONTACT_MARKER)
    if marker < 0:
        return None
    start = output.find("(", marker)
    if start < 0:
        return None
    depth = 0
    for index in range(start, len(output)):
        if output[index] == "(":
            depth += 1
        elif output[index] == ")":
            depth -= 1
            if depth == 0:
                return " ".join(output[start:index + 1].split())
    return None


def _tns_errors(output: str) -> list[str]:
    return [line.strip() for line in output.splitlines() if line.strip().startswith("TNS-")]


def resolve_tns_alias(alias: str) -> OracleTarget:
    """Resolve a database name with `tnsping` and return the connection descriptor."""

    alias = alias.strip()
    if not alias or not _ALIAS_PATTERN.match(alias):
        raise TnsPingError(f"Nome database non valido: '{alias}'")

    executable = shutil.which("tnsping")
    if executable is None:
        raise TnsPingError("Comando tnsping non trovato nel PATH: impossibile cercare il database")

    LOGGER.info("Ricerca database '%s' con tnsping (%s)", alias, executable)
    try:
        result = subprocess.run(
            [executable, alias],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=TNSPING_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise TnsPingError(f"tnsping non ha risposto entro {TNSPING_TIMEOUT_SECONDS}s per '{alias}'") from exc
    except OSError as exc:
        raise TnsPingError(f"Esecuzione tnsping fallita: {exc}") from exc

    output = f"{result.stdout}\n{result.stderr}"
    descriptor = _extract_descriptor(output)
    if descriptor is None:
        LOGGER.error("Output tnsping (exit code %s):\n%s", result.returncode, output.strip())
        errors = "; ".join(_tns_errors(output)) or "nessuna stringa di connessione restituita"
        raise TnsPingError(f"Database '{alias}' non trovato con il comando tnsping ({errors})")

    LOGGER.info("Database '%s' trovato con tnsping", alias)
    LOGGER.info("Stringa di connessione: %s", descriptor)
    if result.returncode != 0 or _tns_errors(output):
        LOGGER.warning(
            "tnsping ha risolto il nome ma il server non risponde (exit code %s): %s",
            result.returncode,
            "; ".join(_tns_errors(output)) or "n/d",
        )
    return OracleTarget(alias=alias, dsn=descriptor)


def _descriptor_values(dsn: str, key: str) -> list[str]:
    return re.findall(rf"\(\s*{key}\s*=\s*([^)\s]+)\s*\)", dsn, re.IGNORECASE)


def _log_connection_failure(credentials: OracleCredentials, target: OracleTarget, exc: Exception) -> None:
    error = exc.args[0] if exc.args else None
    LOGGER.error("Connessione Oracle fallita. Dettagli connessione:")
    LOGGER.error("  Nome database (alias TNS): %s", target.alias)
    LOGGER.error("  Stringa di connessione: %s", target.dsn)
    LOGGER.error("  Host: %s", ", ".join(_descriptor_values(target.dsn, "HOST")) or "n/d")
    LOGGER.error("  Porta: %s", ", ".join(_descriptor_values(target.dsn, "PORT")) or "n/d")
    LOGGER.error("  Protocollo: %s", ", ".join(_descriptor_values(target.dsn, "PROTOCOL")) or "n/d")
    LOGGER.error("  Service name: %s", ", ".join(_descriptor_values(target.dsn, "SERVICE_NAME")) or "n/d")
    LOGGER.error("  SID: %s", ", ".join(_descriptor_values(target.dsn, "SID")) or "n/d")
    LOGGER.error("  Username: %s", credentials.username or "(vuoto)")
    LOGGER.error("  Password fornita: %s", "sì" if credentials.password else "no")
    LOGGER.error("  Driver: python-oracledb %s, modalità %s",
                 oracledb.__version__, "thin" if oracledb.is_thin_mode() else "thick")
    LOGGER.error("  Codice errore: %s", getattr(error, "full_code", None) or "n/d")
    LOGGER.error("  Messaggio errore: %s", getattr(error, "message", None) or str(exc))


def _is_64bit_dll(path: Path) -> bool:
    """Read the PE header of a DLL and tell whether it is built for x64."""

    try:
        with path.open("rb") as file:
            if file.read(2) != b"MZ":
                return False
            file.seek(0x3C)
            pe_offset = int.from_bytes(file.read(4), "little")
            file.seek(pe_offset)
            if file.read(4) != b"PE\0\0":
                return False
            return int.from_bytes(file.read(2), "little") == _PE_MACHINE_AMD64
    except OSError:
        return False


def _client_lib_candidates() -> list[Path]:
    """Candidate Oracle Client folders, in priority order."""

    candidates = sorted(path for path in get_app_dir().glob("instantclient*") if path.is_dir())
    configured = get_config().client_lib_dir
    if configured:
        candidates.append(Path(configured))
    oracle_home = os.environ.get("ORACLE_HOME")
    if oracle_home:
        candidates += [Path(oracle_home), Path(oracle_home) / "bin"]
    candidates += [Path(entry) for entry in os.environ.get("PATH", "").split(os.pathsep) if entry]
    return candidates


def find_64bit_client() -> Path | None:
    """Return the first folder containing a 64-bit oci.dll, skipping 32-bit clients."""

    seen: set[str] = set()
    for folder in _client_lib_candidates():
        key = str(folder).lower()
        if key in seen:
            continue
        seen.add(key)
        oci = folder / "oci.dll"
        if not oci.is_file():
            continue
        if _is_64bit_dll(oci):
            return folder
        LOGGER.info("Oracle Client scartato (32 bit): %s", folder)
    return None


def _enable_thick_mode() -> None:
    """Switch python-oracledb to thick mode using a 64-bit Oracle Client."""

    if not oracledb.is_thin_mode():
        return
    lib_dir = find_64bit_client()
    if lib_dir is None:
        raise OracleClientNotFoundError(
            "Oracle Client a 64 bit non trovato: estrarre Oracle Instant Client 19 x64 "
            f"in una cartella 'instantclient' accanto all'eseguibile ({get_app_dir()}) "
            "oppure impostare oracle.client_lib_dir in config.json"
        )
    LOGGER.info("Attivazione thick mode (Oracle Client: %s)", lib_dir)
    oracledb.init_oracle_client(lib_dir=str(lib_dir))
    LOGGER.info("Thick mode attiva, versione Oracle Client: %s",
                ".".join(str(part) for part in oracledb.clientversion()))


def _connect(credentials: OracleCredentials, target: OracleTarget) -> oracledb.Connection:
    return oracledb.connect(
        user=credentials.username,
        password=credentials.password,
        dsn=target.dsn,
    )


def try_connect(credentials: OracleCredentials, target: OracleTarget) -> oracledb.Connection:
    """Open an Oracle connection with the DSN resolved by tnsping.

    On DPY-3015 (password verifier not supported by thin mode) retries in thick mode.
    Logs every connection parameter (except the password) and re-raises on failure.
    """

    LOGGER.info("Connessione a '%s' con utente '%s'", target.alias, credentials.username)
    try:
        return _connect(credentials, target)
    except oracledb.Error as exc:
        if error_code(exc) != "DPY-3015" or not oracledb.is_thin_mode():
            _log_connection_failure(credentials, target, exc)
            raise
        LOGGER.warning("Thin mode non supportata (DPY-3015): nuovo tentativo in thick mode")

    try:
        _enable_thick_mode()
        return _connect(credentials, target)
    except (oracledb.Error, OracleClientNotFoundError) as exc:
        _log_connection_failure(credentials, target, exc)
        raise


@contextmanager
def get_connection(credentials: OracleCredentials, target: OracleTarget) -> Iterator[oracledb.Connection]:
    """Create and yield an Oracle connection with automatic cleanup."""

    connection = try_connect(credentials, target)
    try:
        yield connection
    finally:
        connection.close()
