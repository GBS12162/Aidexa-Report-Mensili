"""Secure credential storage using the Windows Credential Manager (via keyring)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import keyring
from keyring.errors import KeyringError, PasswordDeleteError

from config import CREDENTIAL_SERVICE_NAME

LOGGER = logging.getLogger(__name__)

_USERNAME_KEY = "oracle_username"


@dataclass(frozen=True)
class OracleCredentials:
    """Oracle username/password pair. Never log or print the password."""

    username: str
    password: str


def load_saved_credentials() -> OracleCredentials | None:
    """Load previously saved credentials from the OS credential store, if any."""

    try:
        username = keyring.get_password(CREDENTIAL_SERVICE_NAME, _USERNAME_KEY)
        if not username:
            return None
        password = keyring.get_password(CREDENTIAL_SERVICE_NAME, username)
        if password is None:
            return None
        return OracleCredentials(username=username, password=password)
    except KeyringError as exc:
        LOGGER.warning("Impossibile leggere le credenziali salvate: %s", exc)
        return None


def save_credentials(credentials: OracleCredentials) -> bool:
    """Persist credentials securely in the OS credential store."""

    try:
        keyring.set_password(CREDENTIAL_SERVICE_NAME, _USERNAME_KEY, credentials.username)
        keyring.set_password(CREDENTIAL_SERVICE_NAME, credentials.username, credentials.password)
        return True
    except KeyringError as exc:
        LOGGER.warning("Impossibile salvare le credenziali: %s", exc)
        return False


def delete_saved_credentials() -> None:
    """Remove any saved credentials from the OS credential store."""

    try:
        username = keyring.get_password(CREDENTIAL_SERVICE_NAME, _USERNAME_KEY)
        if username:
            try:
                keyring.delete_password(CREDENTIAL_SERVICE_NAME, username)
            except PasswordDeleteError:
                pass
            try:
                keyring.delete_password(CREDENTIAL_SERVICE_NAME, _USERNAME_KEY)
            except PasswordDeleteError:
                pass
    except KeyringError as exc:
        LOGGER.warning("Impossibile rimuovere le credenziali salvate: %s", exc)
