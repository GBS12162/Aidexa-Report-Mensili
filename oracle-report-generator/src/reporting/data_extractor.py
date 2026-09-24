def extract_sales_data(connection: oracledb.Connection, query: str) -> pd.DataFrame:
    """Extract sales data from Oracle using a parameterized query."""
    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
            columns = [column[0] for column in cursor.description]
            dataframe = pd.DataFrame(cursor.fetchall(), columns=columns)
    except oracledb.DatabaseError as exc:
        LOGGER.error("Database error occurred: %s", exc)
        raise

    LOGGER.info("Extracted %s rows from Oracle", len(dataframe))
    return dataframe