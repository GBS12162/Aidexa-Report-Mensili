"""Data extraction logic for Oracle sales reporting."""

from __future__ import annotations

import logging

import pandas as pd
import oracledb

from config import QuerySettings

LOGGER = logging.getLogger(__name__)

SALES_QUERY = """
SELECT
    TRUNC(DATA_VENDITA) AS DATA_VENDITA,
    REGIONE,
    CLIENTE,
    CATEGORIA,
    PRODOTTO,
    IMPORTO,
    QTA
FROM VENDITE
WHERE DATA_VENDITA BETWEEN :start_date AND :end_date
  AND (:region IS NULL OR REGIONE = :region)
ORDER BY DATA_VENDITA, REGIONE, CLIENTE
"""


def extract_sales_data(
    connection: oracledb.Connection,
    settings: QuerySettings,
) -> pd.DataFrame:
    """Extract sales data from Oracle using a parameterized query."""

    dataframe = pd.read_sql(
        SALES_QUERY,
        con=connection,
        params={
            "start_date": settings.start_date,
            "end_date": settings.end_date,
            "region": settings.region,
        },
    )

    LOGGER.info("Estratte %s righe da Oracle", len(dataframe))
    return dataframe
