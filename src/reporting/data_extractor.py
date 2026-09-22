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
WHERE DATA_VENDITA >= :start_date
  AND DATA_VENDITA < :end_date + 1
  AND (:region IS NULL OR REGIONE = :region)
ORDER BY DATA_VENDITA, REGIONE, CLIENTE
"""


def extract_sales_data(
    connection: oracledb.Connection,
    settings: QuerySettings,
) -> pd.DataFrame:
    """Extract sales data from Oracle using a parameterized query."""

    with connection.cursor() as cursor:
        cursor.execute(
            SALES_QUERY,
            {
                "start_date": settings.start_date,
                "end_date": settings.end_date,
                "region": settings.region,
            },
        )
        columns = [column[0] for column in cursor.description]
        dataframe = pd.DataFrame(cursor.fetchall(), columns=columns)

    LOGGER.info("Estratte %s righe da Oracle", len(dataframe))
    return dataframe
