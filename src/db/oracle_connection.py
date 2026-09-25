"""Oracle connection helpers (python-oracledb, thin mode, fixed DSN)."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

import oracledb

from config import get_config
from src.security.credential_manager import OracleCredentials

LOGGER = logging.getLogger(__name__)


def try_connect(credentials: OracleCredentials) -> oracledb.Connection:
    """Open an Oracle connection using thin mode and the configured DSN.

    Raises oracledb.Error on any authentication/network failure.
    """

    return oracledb.connect(
        user=credentials.username,
        password=credentials.password,
        dsn=get_config().oracle_dsn,
    )


@contextmanager
def get_connection(credentials: OracleCredentials) -> Iterator[oracledb.Connection]:
    """Create and yield an Oracle connection with automatic cleanup."""

    connection = try_connect(credentials)
    try:
        yield connection
    finally:
        connection.close()
