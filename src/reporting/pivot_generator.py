"""Pivot table generation for sales reporting."""

from __future__ import annotations

import pandas as pd


TOTAL_LABEL = "TOTALE_GENERALE"


def create_sales_pivot(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Create a sales pivot ordered by descending row total."""

    if dataframe.empty:
        return pd.DataFrame([{"REGIONE": TOTAL_LABEL, TOTAL_LABEL: 0.0}])

    pivot = pd.pivot_table(
        dataframe,
        index="REGIONE",
        columns="CATEGORIA",
        values="IMPORTO",
        aggfunc="sum",
        fill_value=0,
        margins=True,
        margins_name=TOTAL_LABEL,
    )

    pivot = pivot.reset_index()
    if TOTAL_LABEL not in pivot.columns:
        numeric_columns = [column for column in pivot.columns if column != "REGIONE"]
        pivot[TOTAL_LABEL] = pivot[numeric_columns].sum(axis=1) if numeric_columns else 0.0

    total_rows = pivot[pivot["REGIONE"] == TOTAL_LABEL]
    detail_rows = pivot[pivot["REGIONE"] != TOTAL_LABEL]
    detail_rows = detail_rows.sort_values(by=TOTAL_LABEL, ascending=False)

    return pd.concat([detail_rows, total_rows], ignore_index=True)
