"""Oracle connection helpers (python-oracledb, thin mode by default, fixed DSN).

Falls back to Oracle Client 'thick' mode, on demand, only when the target
account uses a legacy password verifier (DPY-3015) that thin mode cannot
authenticate. Requires Oracle Instant Client to be installed for the fallback
to succeed; production behavior/DSN is otherwise unchanged.
"""

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

from config import ORACLE_DSN
from src.security.credential_manager import OracleCredentials

LOGGER = logging.getLogger(__name__)

_thick_mode_enabled = False


class ThickModeUnavailableError(RuntimeError):
    """Raised when DPY-3015 fallback is needed but Oracle Instant Client is unusable."""


def _enable_thick_mode() -> None:
    """Initialize python-oracledb thick mode (uses Oracle Instant Client).

    Safe to call multiple times; only the first call has effect. Must not be
    called after any connection/pool has already been successfully created.
    """

    global _thick_mode_enabled
    if _thick_mode_enabled:
        return

    lib_dir = os.environ.get("ORACLE_INSTANT_CLIENT_DIR") or None
    try:
        oracledb.init_oracle_client(lib_dir=lib_dir)
    except oracledb.Error as exc:
        raise ThickModeUnavailableError(
            "Questo account Oracle usa un metodo di autenticazione legacy non supportato "
            "in modalità 'thin'. Serve Oracle Instant Client installato sulla macchina "
            "(indicare la cartella con la variabile d'ambiente ORACLE_INSTANT_CLIENT_DIR "
            "se non è già nel PATH)."
        ) from exc

    _thick_mode_enabled = True
    LOGGER.info("Modalità Oracle 'thick' attivata (Instant Client: %s)", lib_dir or "PATH/ORACLE_HOME di sistema")


def resolve_tns_admin(tnsping_path: str | None = None) -> str | None:
    """Find the directory containing tnsnames.ora, the same way the Oracle client does.

    Checks TNS_ADMIN first, then falls back to <ORACLE_HOME>/network/admin
    derived from the location of the 'tnsping' executable, if known.
    """

    tns_admin = os.environ.get("TNS_ADMIN")
    if tns_admin and (Path(tns_admin) / "tnsnames.ora").is_file():
        return tns_admin

    if tnsping_path:
        candidate = Path(tnsping_path).resolve().parent.parent / "network" / "admin"
        if (candidate / "tnsnames.ora").is_file():
            return str(candidate)

    return None


def try_connect_dsn(
    credentials: OracleCredentials, dsn: str, config_dir: str | None = None
) -> oracledb.Connection:
    """Open an Oracle connection to an arbitrary DSN or TNS alias (used by diagnostics).

    config_dir points python-oracledb thin mode to the tnsnames.ora directory
    when dsn is a plain TNS alias instead of a full connect descriptor.

    Automatically retries in Oracle Client 'thick' mode if the account uses a
    legacy password verifier (DPY-3015) unsupported in thin mode.
    Raises oracledb.Error on any authentication/network failure.
    """

    kwargs = {"user": credentials.username, "password": credentials.password, "dsn": dsn}
    if config_dir and not _thick_mode_enabled:
        kwargs["config_dir"] = config_dir

    try:
        return oracledb.connect(**kwargs)
    except oracledb.DatabaseError as exc:
        if "DPY-3015" not in str(exc) or _thick_mode_enabled:
            raise
        LOGGER.warning("Verificatore password legacy rilevato, tentativo con modalità 'thick'")
        _enable_thick_mode()
        kwargs.pop("config_dir", None)
        return oracledb.connect(**kwargs)


def try_connect(credentials: OracleCredentials) -> oracledb.Connection:
    """Open an Oracle connection using thin mode and the fixed production DSN.

    Raises oracledb.Error on any authentication/network failure.
    """

    return try_connect_dsn(credentials, ORACLE_DSN)


@contextmanager
def get_connection(credentials: OracleCredentials) -> Iterator[oracledb.Connection]:
    """Create and yield an Oracle connection with automatic cleanup."""

    connection = try_connect(credentials)
    try:
        yield connection
    finally:
        connection.close()


class TnsPingToolMissingError(RuntimeError):
    """Raised when the 'tnsping' Oracle client utility is not available on PATH."""


@dataclass(frozen=True)
class TnsPingResult:
    """Outcome of a 'tnsping' diagnostic run against a TNS alias."""

    alias: str
    success: bool
    host: str | None
    port: str | None
    service_name: str | None
    response_time_ms: int | None
    user_message: str
    raw_output: str
    tnsping_path: str | None = None


_HOST_RE = re.compile(r"HOST\s*=\s*([^)]+)", re.IGNORECASE)
_PORT_RE = re.compile(r"PORT\s*=\s*([^)]+)", re.IGNORECASE)
_SERVICE_RE = re.compile(r"SERVICE_NAME\s*=\s*([^)]+)", re.IGNORECASE)
_OK_TIME_RE = re.compile(r"OK\s*\(\s*(\d+)\s*msec\s*\)", re.IGNORECASE)

_ALIAS_NOT_FOUND_CODES = ("TNS-03505", "TNS-12154", "ORA-12154")
_UNREACHABLE_CODES = ("TNS-12541", "TNS-12170", "TNS-12537", "TNS-12535", "TNS-12560")


def run_tnsping(alias: str, timeout_seconds: int = 15) -> TnsPingResult:
    """Run the Oracle 'tnsping' client utility against the given TNS alias.

    Requires the Oracle client tools to be installed with 'tnsping' available on PATH.
    Raises TnsPingToolMissingError if the utility cannot be found.
    """

    tnsping_path = shutil.which("tnsping") or shutil.which("tnsping.exe")
    if not tnsping_path:
        raise TnsPingToolMissingError(
            "Strumento 'tnsping' non trovato. Verificare che il client Oracle sia "
            "installato e presente nel PATH di sistema."
        )

    try:
        completed = subprocess.run(
            [tnsping_path, alias],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return TnsPingResult(
            alias=alias,
            success=False,
            host=None,
            port=None,
            service_name=None,
            response_time_ms=None,
            user_message="Database non raggiungibile tramite TNS. Verificare la connettività di rete.",
            raw_output="",
        )

    output = f"{completed.stdout}\n{completed.stderr}"

    host_match = _HOST_RE.search(output)
    port_match = _PORT_RE.search(output)
    service_match = _SERVICE_RE.search(output)
    ok_match = _OK_TIME_RE.search(output)

    host = host_match.group(1).strip() if host_match else None
    port = port_match.group(1).strip() if port_match else None
    service_name = service_match.group(1).strip() if service_match else None

    if completed.returncode == 0 and ok_match:
        return TnsPingResult(
            alias=alias,
            success=True,
            host=host,
            port=port,
            service_name=service_name,
            response_time_ms=int(ok_match.group(1)),
            user_message="Database raggiungibile.",
            raw_output=output,
            tnsping_path=tnsping_path,
        )

    if any(code in output for code in _ALIAS_NOT_FOUND_CODES):
        message = "Alias TNS non trovato. Verificare il nome del database inserito."
    else:
        message = "Database non raggiungibile tramite TNS. Verificare la connettività di rete."

    return TnsPingResult(
        alias=alias,
        success=False,
        host=host,
        port=port,
        service_name=service_name,
        response_time_ms=None,
        user_message=message,
        raw_output=output,
        tnsping_path=tnsping_path,
    )
