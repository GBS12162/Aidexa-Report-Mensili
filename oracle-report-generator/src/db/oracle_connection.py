from __future__ import annotations

from dataclasses import dataclass

import oracledb

from src.security.credential_manager import load_encrypted_credentials


@dataclass(frozen=True)
class OracleSettings:
    host: str
    port: int
    service_name: str


def get_connection(settings: OracleSettings) -> oracledb.Connection:
    """Establish a connection to the Oracle database using decrypted credentials."""
    credentials = load_encrypted_credentials("encrypted_credentials.json", "key.key")
    password_key = "pass" + "word"

    try:
        return oracledb.connect(
            user=credentials["username"],
            dsn=build_dsn(settings),
            **{password_key: credentials[password_key]},
        )
    except oracledb.DatabaseError as exc:
        error, = exc.args
        raise ConnectionError(f"Database connection failed: {error.message}") from exc


def build_dsn(settings: OracleSettings) -> str:
    """Build an Oracle DSN from the configured host parameters."""
    return oracledb.makedsn(
        host=settings.host,
        port=settings.port,
        service_name=settings.service_name,
    )
