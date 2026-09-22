"""Centralized application configuration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import os

from dotenv import load_dotenv


@dataclass(frozen=True)
class OracleSettings:
    """Oracle connection settings loaded from environment variables."""

    host: str
    port: int
    service_name: str
    username: str
    password: str


@dataclass(frozen=True)
class QuerySettings:
    """Query parameter settings for the sales extraction."""

    start_date: date
    end_date: date
    region: str | None = None


@dataclass(frozen=True)
class AppSettings:
    """Complete application configuration."""

    oracle: OracleSettings
    query: QuerySettings
    output_file: Path
    log_file: Path = Path("logs/report.log")


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Variabile ambiente obbligatoria mancante: {name}")
    return value


def load_settings() -> AppSettings:
    """Load and validate runtime settings from a .env file."""

    load_dotenv()

    output_file = Path(os.getenv("OUTPUT_FILE", "output/report.xlsx"))
    region_value = os.getenv("QUERY_REGION", "").strip() or None

    start_date = date.fromisoformat(_require_env("QUERY_START_DATE"))
    end_date = date.fromisoformat(_require_env("QUERY_END_DATE"))
    if start_date > end_date:
        raise ValueError("QUERY_START_DATE non può essere successiva a QUERY_END_DATE")

    return AppSettings(
        oracle=OracleSettings(
            _require_env("ORACLE_HOST"),
            int(_require_env("ORACLE_PORT")),
            _require_env("ORACLE_SERVICE_NAME"),
            _require_env("ORACLE_USERNAME"),
            _require_env("ORACLE_PASSWORD"),
        ),
        query=QuerySettings(
            start_date=start_date,
            end_date=end_date,
            region=region_value,
        ),
        output_file=output_file,
    )
