"""Oracle connection helpers."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import oracledb

from config import OracleSettings


def build_dsn(settings: OracleSettings) -> str:
    """Build an Oracle DSN from the configured host parameters."""

    return oracledb.makedsn(
        host=settings.host,
        port=settings.port,
        service_name=settings.service_name,
    )


@contextmanager
def get_connection(settings: OracleSettings) -> Iterator[oracledb.Connection]:
    """Create and yield an Oracle connection with automatic cleanup."""

    connection = oracledb.connect(
        **{
            "user": settings.username,
            "password": settings.password,
            "dsn": build_dsn(settings),
        }
    )
    try:
        yield connection
    finally:
        connection.close()
