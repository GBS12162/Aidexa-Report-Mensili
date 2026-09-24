"""Pivot generation for the onboarding error report.

Reproduces the structure deduced from examples/caso1/output_atteso.xlsx:
rows grouped by tipo_errore (400/500) then by URL, columns grouped by
date then by stato (A, D, F, I, K, N, P, T), with per-date subtotal,
per-group subtotal row and an overall grand total row/column.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd

STATI: list[str] = ["A", "D", "F", "I", "K", "N", "P", "T"]

GROUP_DEFINITIONS = [
    ("400", "Errori gestiti (400)", "TOTALE ERRORI GESTITI"),
    ("500", "Errori non gestiti (500)", "TOTALE ERRORI NON GESTITI"),
]

GRAND_TOTAL_LABEL = "Grand Total"


@dataclass
class GroupResult:
    """Aggregated rows/subtotals for a single tipo_errore group."""

    code: str
    header_label: str
    subtotal_label: str
    urls: list[str] = field(default_factory=list)
    # values[url][date][stato] = count
    values: dict[str, dict] = field(default_factory=dict)
    # subtotal[date][stato] = sum across urls
    subtotal: dict = field(default_factory=dict)


@dataclass
class ReportModel:
    """Complete data model ready to be rendered to Excel."""

    title: str
    dates: list
    groups: list[GroupResult]


def extract_report_title(query_text: str) -> str:
    """Derive a friendly report title from the prdt_code filter in the query."""

    match = re.search(r"prdt_code\s+IN\s*\(\s*'([^']+)'", query_text, re.IGNORECASE)
    if not match:
        return "REPORT"

    code = match.group(1)
    friendly = code.removeprefix("DEPOSITO_").removesuffix("_AIDEXA")
    return friendly or code


def _row_total(day_values: dict) -> int:
    return sum(day_values.get(stato, 0) for stato in STATI)


def build_report(
    dataframe: pd.DataFrame,
    query_text: str,
    report_dates: list | None = None,
) -> ReportModel:
    """Build the full report data model from the raw query result set."""

    title = extract_report_title(query_text)

    dates = report_dates or []
    if dataframe.empty:
        groups = [
            GroupResult(code=code, header_label=header, subtotal_label=subtotal)
            for code, header, subtotal in GROUP_DEFINITIONS
        ]
        for group in groups:
            group.subtotal = {date: {stato: 0 for stato in STATI} for date in dates}
        return ReportModel(title=title, dates=dates, groups=groups)

    if not dates:
        dates = [
            date_value.to_pydatetime()
            for date_value in sorted(pd.to_datetime(dataframe["DATAA"]).dt.normalize().unique())
        ]

    lookup: dict[tuple, int] = {}
    for record in dataframe.itertuples(index=False):
        key = (
            str(record.URLL),
            pd.Timestamp(record.DATAA).normalize().to_pydatetime(),
            str(record.STATOO),
            str(record.TIPO_ERRORE),
        )
        lookup[key] = int(record.CONTEGGIO or 0)

    groups: list[GroupResult] = []
    for code, header_label, subtotal_label in GROUP_DEFINITIONS:
        group_mask = dataframe["TIPO_ERRORE"].astype(str) == code
        urls = sorted(dataframe.loc[group_mask, "URLL"].astype(str).unique())

        group = GroupResult(code=code, header_label=header_label, subtotal_label=subtotal_label, urls=urls)

        subtotal: dict = {date: {stato: 0 for stato in STATI} for date in dates}
        for url in urls:
            day_values: dict = {}
            for date in dates:
                stato_values = {
                    stato: lookup.get((url, date, stato, code), 0) for stato in STATI
                }
                day_values[date] = stato_values
                for stato in STATI:
                    subtotal[date][stato] += stato_values[stato]
            group.values[url] = day_values

        group.subtotal = subtotal
        groups.append(group)

    return ReportModel(title=title, dates=dates, groups=groups)
