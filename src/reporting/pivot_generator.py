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

    if TOTAL_LABEL not in pivot.columns:
        pivot = pivot.reset_index()
        total_rows = pivot[pivot["REGIONE"] == TOTAL_LABEL]
        detail_rows = pivot[pivot["REGIONE"] != TOTAL_LABEL].copy()
        numeric_columns = [column for column in detail_rows.columns if column != "REGIONE"]
        detail_rows[TOTAL_LABEL] = detail_rows[numeric_columns].sum(axis=1) if numeric_columns else 0.0

        if not total_rows.empty:
            total_row = total_rows.copy()
            total_row[TOTAL_LABEL] = detail_rows[TOTAL_LABEL].sum()
            pivot = pd.concat([detail_rows, total_row], ignore_index=True)
        else:
            pivot = detail_rows
    else:
        pivot = pivot.reset_index()

    total_rows = pivot[pivot["REGIONE"] == TOTAL_LABEL]
    detail_rows = pivot[pivot["REGIONE"] != TOTAL_LABEL]
    detail_rows = detail_rows.sort_values(by=TOTAL_LABEL, ascending=False)

    return pd.concat([detail_rows, total_rows], ignore_index=True)
