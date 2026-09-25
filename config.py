"""Centralized application configuration.

Loading order (config.json always wins when present):
1. config.json next to the executable/script, merged over the defaults.
2. Built-in DEFAULT_CONFIG (used for any missing key, or entirely if
   config.json does not exist).

The rest of the application only talks to ConfigManager / get_config() and
never needs to know whether a value came from the file or from the default.
"""

from __future__ import annotations

import copy
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)

CONFIG_FILENAME = "config.json"
EXAMPLE_CONFIG_FILENAME = "config.example.json"

CREDENTIAL_SERVICE_NAME = "AidexaReportMensili-Oracle"

# Values currently used by the project, kept as the built-in fallback.
DEFAULT_CONFIG: dict[str, Any] = {
    "oracle": {
        "hosts": [
            "oramonprex-scan.sg.gbs.pro",
            "oramonprey-scan.sg.gbs.pro",
            "oramonprez-scan.sg.gbs.pro",
        ],
        "port": 1521,
        "protocol": "TCP",
        "service_name": "OTH_ORAMON.bsella.it",
        "server_mode": "DEDICATED",
        "failover": True,
        "credential_service_name": CREDENTIAL_SERVICE_NAME,
    },
    "paths": {
        "query_file": "examples/caso1/query.sql",
        "test_input_file": "examples/caso1/input.xlsx",
        "test_reference_file": "examples/caso1/output_atteso.xlsx",
        "output_file": "output/report.xlsx",
        "test_output_file": "output_test.xlsx",
        "log_file": "logs/report.log",
    },
    "columns": {
        "query_columns": ["URLL", "DATAA", "STATOO", "TIPO_ERRORE", "CONTEGGIO", "CONTEGGIO_RAW"],
        "input_header_names": ["URLL", "DATAA", "STATOO", "TIPO_ERRORE"],
    },
    "report": {
        "stato_order": ["A", "D", "F", "I", "K", "N", "P", "T"],
        "error_groups": [
            ["400", "Errori gestiti (400)", "TOTALE ERRORI GESTITI"],
            ["500", "Errori non gestiti (500)", "TOTALE ERRORI NON GESTITI"],
        ],
    },
    "logging": {
        "level": "INFO",
        "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    },
}


def get_base_dir() -> Path:
    """Return the base directory for bundled resources (frozen or source)."""

    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).parent


def get_app_dir() -> Path:
    """Return the directory where the running executable/script lives."""

    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge override into a copy of base."""

    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


@dataclass(frozen=True)
class AppSettings:
    """Complete application configuration."""

    query_file: Path
    output_file: Path
    log_file: Path


@dataclass(frozen=True)
class TestSettings:
    """Configuration for the offline Excel-only test mode (--test-excel)."""

    input_file: Path
    reference_file: Path
    output_file: Path
    log_file: Path


class ConfigManager:
    """Loads config.json when present, otherwise falls back to defaults."""

    def __init__(self, config_path: Path | None = None) -> None:
        self._app_dir = get_app_dir()
        self._base_dir = get_base_dir()
        self._config_path = config_path or (self._app_dir / CONFIG_FILENAME)
        self._data, self._loaded_from_file = self._load()

    def _load(self) -> tuple[dict[str, Any], bool]:
        LOGGER.info("Caricamento configurazione")
        if self._config_path.is_file():
            try:
                raw = json.loads(self._config_path.read_text(encoding="utf-8-sig"))
                if not isinstance(raw, dict):
                    raise ValueError("il contenuto non è un oggetto JSON")
                merged = _deep_merge(DEFAULT_CONFIG, raw)
                LOGGER.info("Configurazione letta da %s", self._config_path)
                return merged, True
            except (json.JSONDecodeError, OSError, ValueError) as exc:
                LOGGER.warning("config.json non valido (%s)", exc)
        else:
            LOGGER.info("Configurazione esterna non presente")
        LOGGER.info("Utilizzo configurazione interna di default")
        return copy.deepcopy(DEFAULT_CONFIG), False

    @property
    def loaded_from_file(self) -> bool:
        return self._loaded_from_file

    @property
    def config_path(self) -> Path:
        return self._config_path

    def _resolve(self, relative: str) -> Path:
        path = Path(relative)
        return path if path.is_absolute() else self._base_dir / path

    def _resolve_app(self, relative: str) -> Path:
        path = Path(relative)
        return path if path.is_absolute() else self._app_dir / path

    @property
    def oracle_dsn(self) -> str:
        oracle = self._data["oracle"]
        addresses = "".join(
            f"(ADDRESS=(PROTOCOL={oracle['protocol']})(HOST={host})(PORT={oracle['port']}))"
            for host in oracle["hosts"]
        )
        failover = "(FAILOVER=ON)" if oracle.get("failover", True) else ""
        return (
            "(DESCRIPTION="
            f"{addresses}{failover}"
            "(CONNECT_DATA="
            f"(SERVER={oracle['server_mode']})"
            f"(SERVICE_NAME={oracle['service_name']})"
            "))"
        )

    @property
    def credential_service_name(self) -> str:
        return self._data["oracle"]["credential_service_name"]

    @property
    def query_columns(self) -> list[str]:
        return list(self._data["columns"]["query_columns"])

    @property
    def input_header_names(self) -> list[str]:
        return list(self._data["columns"]["input_header_names"])

    @property
    def stato_order(self) -> list[str]:
        return list(self._data["report"]["stato_order"])

    @property
    def error_groups(self) -> list[tuple[str, str, str]]:
        return [tuple(group) for group in self._data["report"]["error_groups"]]

    @property
    def logging_level(self) -> str:
        return self._data["logging"]["level"]

    @property
    def logging_format(self) -> str:
        return self._data["logging"]["format"]

    def get_settings(self) -> AppSettings:
        paths = self._data["paths"]
        return AppSettings(
            query_file=self._resolve(paths["query_file"]),
            output_file=self._resolve_app(paths["output_file"]),
            log_file=self._resolve_app(paths["log_file"]),
        )

    def get_test_settings(self) -> TestSettings:
        paths = self._data["paths"]
        return TestSettings(
            input_file=self._resolve(paths["test_input_file"]),
            reference_file=self._resolve(paths["test_reference_file"]),
            output_file=self._resolve_app(paths["test_output_file"]),
            log_file=self._resolve_app(paths["log_file"]),
        )

    def generate_example_file(self, path: Path | None = None) -> Path:
        """Write config.example.json with every available parameter."""

        target = path or (self._app_dir / EXAMPLE_CONFIG_FILENAME)
        target.write_text(json.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=False), encoding="utf-8")
        LOGGER.info("File di esempio generato: %s", target)
        return target


_config_manager: ConfigManager | None = None


def get_config() -> ConfigManager:
    """Return the process-wide ConfigManager singleton (lazy-loaded)."""

    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def load_settings() -> AppSettings:
    """Build runtime settings (backward-compatible helper)."""

    return get_config().get_settings()


def load_test_settings() -> TestSettings:
    """Build settings for the offline Excel-only test mode (backward-compatible helper)."""

    return get_config().get_test_settings()
