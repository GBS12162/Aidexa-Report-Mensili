from __future__ import annotations

import logging
import sys

from config import load_config
from src.db.oracle_connection import OracleSettings, get_connection
from src.reporting.data_extractor import extract_sales_data
from src.reporting.excel_formatter import export_report
from src.utils.logger import setup_logging

LOGGER = logging.getLogger(__name__)

def main() -> int:
    """Run the report generation workflow."""
    settings = load_config()
    setup_logging(settings.log_file)

    try:
        LOGGER.info("Starting sales report generation")

        with get_connection(
            OracleSettings(
                host=settings.database.host,
                port=settings.database.port,
                service_name=settings.database.service_name,
            )
        ) as connection:
            dataframe = extract_sales_data(connection, "")

        pivot = dataframe
        export_report(dataframe, pivot, settings.output_file)
        LOGGER.info("Report generated successfully")
        return 0
    except ValueError as exc:
        LOGGER.error("Invalid configuration: %s", exc)
    except Exception as exc:
        LOGGER.error("Unexpected error during report generation: %s", exc)

    return 1

if __name__ == "__main__":
    raise SystemExit(main())