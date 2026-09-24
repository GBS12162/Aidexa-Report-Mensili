from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

@dataclass(frozen=True)
class DatabaseConfig:
    """Database configuration settings loaded from environment variables."""
    host: str
    port: int
    service_name: str
    username: str
    password: str

@dataclass(frozen=True)
class AppConfig:
    """Application configuration settings."""
    database: DatabaseConfig
    output_file: Path
    log_file: Path = Path("logs/report.log")

def load_config() -> AppConfig:
    """Load and validate application configuration from environment variables."""
    host = os.getenv("ORACLE_HOST")
    port = int(os.getenv("ORACLE_PORT", 1521))
    service_name = os.getenv("ORACLE_SERVICE_NAME")
    username = os.getenv("ORACLE_USERNAME")
    password = os.getenv("ORACLE_PASSWORD")

    if not all([host, service_name, username, password]):
        raise ValueError("Missing required database configuration in environment variables.")

    output_file = Path(os.getenv("OUTPUT_FILE", "output/report.xlsx"))
    
    return AppConfig(
        database=DatabaseConfig(
            host=host,
            port=port,
            service_name=service_name,
            username=username,
            password=password,
        ),
        output_file=output_file,
    )