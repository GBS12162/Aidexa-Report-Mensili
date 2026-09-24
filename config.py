"""Centralized application configuration."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

# Fixed Oracle connection descriptor (never configurable at runtime).
ORACLE_DSN = (
    "(DESCRIPTION="
    "(ADDRESS=(PROTOCOL=TCP)(HOST=oramonprex-scan.sg.gbs.pro)(PORT=1521))"
    "(ADDRESS=(PROTOCOL=TCP)(HOST=oramonprey-scan.sg.gbs.pro)(PORT=1521))"
    "(ADDRESS=(PROTOCOL=TCP)(HOST=oramonprez-scan.sg.gbs.pro)(PORT=1521))"
    "(FAILOVER=ON)"
    "(CONNECT_DATA="
    "(SERVER=DEDICATED)"
    "(SERVICE_NAME=OTH_ORAMON.bsella.it)"
    "))"
)

CREDENTIAL_SERVICE_NAME = "AidexaReportMensili-Oracle"

QUERY_RELATIVE_PATH = Path("examples") / "caso1" / "query.sql"
TEST_INPUT_RELATIVE_PATH = Path("examples") / "caso1" / "input.xlsx"
TEST_REFERENCE_RELATIVE_PATH = Path("examples") / "caso1" / "output_atteso.xlsx"
TEST_OUTPUT_FILENAME = "output_test.xlsx"


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


def load_settings() -> AppSettings:
    """Build runtime settings using fixed, non-configurable paths."""

    app_dir = get_app_dir()
    return AppSettings(
        query_file=get_base_dir() / QUERY_RELATIVE_PATH,
        output_file=app_dir / "output" / "report.xlsx",
        log_file=app_dir / "logs" / "report.log",
    )


def load_test_settings() -> TestSettings:
    """Build settings for the offline Excel-only test mode."""

    base_dir = get_base_dir()
    app_dir = get_app_dir()
    return TestSettings(
        input_file=base_dir / TEST_INPUT_RELATIVE_PATH,
        reference_file=base_dir / TEST_REFERENCE_RELATIVE_PATH,
        output_file=app_dir / TEST_OUTPUT_FILENAME,
        log_file=app_dir / "logs" / "report.log",
    )
