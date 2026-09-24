from __future__ import annotations

import logging
import sys

from src.db.oracle_connection import get_connection
from src.reporting.data_extractor import extract_sales_data
from src.reporting.excel_formatter import export_report
from src.security.credential_manager import load_encrypted_credentials
from src.utils.logger import setup_logging
from config import load_settings

LOGGER = logging.getLogger(__name__)

def main() -> int:
    """Run the report generation workflow."""
    setup_logging()

    try:
        settings = load_settings()
        LOGGER.info("Starting sales report generation")

        credentials = load_encrypted_credentials()
        with get_connection(credentials) as connection:
            dataframe = extract_sales_data(connection, settings.query)

        export_report(dataframe, settings.output_file)
        LOGGER.info("Report generated successfully")
        return 0
    except ValueError as exc:
        LOGGER.error("Invalid configuration: %s", exc)
    except Exception as exc:
        LOGGER.error("Unexpected error during report generation: %s", exc)

    return 1

if __name__ == "__main__":
    raise SystemExit(main())