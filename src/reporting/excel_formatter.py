"""Excel report writing and formatting.

Renders a ReportModel (see pivot_generator.py) reproducing the layout of
examples/caso1/output_atteso.xlsx: title row, merged date headers, stato
sub-headers, one row per URL, per-group subtotal and an overall grand total.
"""

from __future__ import annotations

import logging
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.styles.colors import Color
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from src.reporting.pivot_generator import GRAND_TOTAL_LABEL, STATI, ReportModel

LOGGER = logging.getLogger(__name__)

DATA_START_COL = 4  # column D
COLS_PER_DATE_BLOCK = len(STATI) + 1  # 8 stato columns + 1 total column

# Automatic text color used by Excel's default theme ("Text 1").
TEXT_COLOR = Color(theme=1, tint=0.0)

TITLE_FILL = PatternFill("solid", fgColor="FF00B050")
DATE_FILL = PatternFill("solid", fgColor=Color(theme=4, tint=0.7999816888943144))
BLUE_FILL = PatternFill("solid", fgColor=Color(theme=4, tint=0.7999816888943144))
YELLOW_FILL = PatternFill("solid", fgColor="FFFFFF00")
GRAY_FILL = PatternFill("solid", fgColor=Color(theme=0, tint=-0.1499984740745262))

FONT_TITLE = Font(name="Calibri", size=11, bold=True, color=TEXT_COLOR)
FONT_NORMAL = Font(name="Calibri", size=11, bold=False, color=TEXT_COLOR)
FONT_HEADER = Font(name="Segoe UI", size=9, bold=True, color=TEXT_COLOR)

# Banner shown on the row where a tipo_errore group starts (e.g. "Errori gestiti (400)").
GROUP_BANNER_FILL = PatternFill("solid", fgColor=Color(theme=4, tint=0.0))
GROUP_BANNER_FONT_LABEL = Font(name="Calibri", size=11, bold=False, color=Color(theme=0, tint=0.0))
GROUP_BANNER_FONT_SPACER = Font(name="Calibri", size=11, bold=True, color=TEXT_COLOR)

# Label cells (col B/C) of a per-group subtotal row (e.g. "TOTALE ERRORI GESTITI").
SUBTOTAL_LABEL_FONT = Font(name="Calibri", size=11, bold=True, color=TEXT_COLOR)

THIN_SIDE = Side(style="thin")
THIN_BOTTOM = Border(bottom=THIN_SIDE)
THIN_TOP = Border(top=THIN_SIDE)
THIN_BOX = Border(left=THIN_SIDE, right=THIN_SIDE, top=THIN_SIDE, bottom=THIN_SIDE)
CENTER = Alignment(horizontal="center")
LEFT = Alignment(horizontal="left")

YELLOW_STATI = {"A", "D", "F", "I"}

# Row "kinds" controlling the border applied to each column (see analysis notes):
# Row "kinds" controlling the border/fill applied to each column (see analysis notes):
# - "header": the stato letters row (3) -> yellow=box+fill, blue=bottom+fill, total=gray
# - "subtotal": per-group subtotal rows -> same borders as header, but blue stato loses its fill
# - "data": plain url rows and group banner rows -> yellow=box+fill, blue=no border/fill
# - "grand_total": final grand total row -> every column gets a single top border
ROW_KIND_HEADER = "header"
ROW_KIND_SUBTOTAL = "subtotal"
ROW_KIND_DATA = "data"
ROW_KIND_GRAND_TOTAL = "grand_total"


def _stato_fill(stato: str) -> PatternFill:
    return YELLOW_FILL if stato in YELLOW_STATI else BLUE_FILL


def _cell_border(is_yellow: bool, row_kind: str) -> Border | None:
    if row_kind == ROW_KIND_GRAND_TOTAL:
        return THIN_TOP
    if is_yellow:
        return THIN_BOX
    if row_kind in (ROW_KIND_HEADER, ROW_KIND_SUBTOTAL):
        return THIN_BOTTOM
    return None


def _cell_fill(is_yellow: bool, row_kind: str, override_fill: PatternFill | None) -> PatternFill | None:
    if override_fill is not None:
        return override_fill
    if is_yellow:
        return YELLOW_FILL
    # Blue stato columns only keep their fill on the true stato header row (3);
    # subtotal and plain data rows leave them unfilled (matches the reference).
    if row_kind == ROW_KIND_HEADER:
        return BLUE_FILL
    return None


def _total_col_fill(override_fill: PatternFill | None) -> PatternFill:
    """Per-date total column is always gray-filled, on every row kind."""

    return override_fill if override_fill is not None else GRAY_FILL


def _write_group_banner(worksheet: Worksheet, row: int, label: str, num_dates: int, grand_total_col: int) -> None:
    """Style the row where a tipo_errore group label appears (col B/C banner).

    Yellow stato columns keep their box border/fill even on this label-only
    row (matching the reference layout); other columns stay blank.
    """

    label_cell = worksheet.cell(row=row, column=2, value=label)
    label_cell.font = GROUP_BANNER_FONT_LABEL
    label_cell.fill = GROUP_BANNER_FILL
    label_cell.alignment = LEFT

    spacer_cell = worksheet.cell(row=row, column=3)
    spacer_cell.font = GROUP_BANNER_FONT_SPACER
    spacer_cell.fill = GROUP_BANNER_FILL
    spacer_cell.number_format = "0%"
    spacer_cell.alignment = LEFT

    for date_index in range(num_dates):
        start_col = DATA_START_COL + date_index * COLS_PER_DATE_BLOCK
        for stato_index, stato in enumerate(STATI):
            if stato not in YELLOW_STATI:
                continue
            cell = worksheet.cell(row=row, column=start_col + stato_index)
            cell.fill = YELLOW_FILL
            cell.border = THIN_BOX


def _grand_total_col(num_dates: int) -> int:
    return DATA_START_COL + num_dates * COLS_PER_DATE_BLOCK


def export_report(model: ReportModel, output_path: Path) -> None:
    """Write the full report to an xlsx file matching the reference layout."""

    output_path.parent.mkdir(parents=True, exist_ok=True)

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Sheet1"

    grand_total_col = _grand_total_col(len(model.dates))

    _write_title_row(worksheet, model, grand_total_col)
    _write_stato_header_row(worksheet, model, grand_total_col)
    _write_body(worksheet, model, grand_total_col)
    _apply_sheet_layout(worksheet, grand_total_col)

    workbook.save(output_path)
    LOGGER.info("Report Excel salvato in %s", output_path)


def _write_title_row(worksheet: Worksheet, model: ReportModel, grand_total_col: int) -> None:
    title_cell = worksheet.cell(row=2, column=2, value=model.title)
    title_cell.font = FONT_TITLE
    title_cell.fill = TITLE_FILL
    title_cell.alignment = LEFT

    label_cell = worksheet.cell(row=2, column=3, value="TIPOLOGIA DI ERRORE")
    label_cell.font = FONT_TITLE
    label_cell.fill = TITLE_FILL
    label_cell.alignment = LEFT
    label_cell.number_format = "0%"

    for date_index, date_value in enumerate(model.dates):
        start_col = DATA_START_COL + date_index * COLS_PER_DATE_BLOCK
        end_col = start_col + len(STATI) - 1

        for col in range(start_col, end_col + 1):
            cell = worksheet.cell(row=2, column=col)
            cell.fill = DATE_FILL
            cell.font = FONT_HEADER

        header_cell = worksheet.cell(row=2, column=start_col, value=date_value)
        header_cell.number_format = "mm-dd-yy"
        header_cell.alignment = CENTER
        worksheet.merge_cells(start_row=2, start_column=start_col, end_row=2, end_column=end_col)

        total_col = end_col + 1
        total_cell = worksheet.cell(row=2, column=total_col)
        total_cell.fill = GRAY_FILL
        total_cell.font = FONT_HEADER
        total_cell.number_format = "mm-dd-yy"

    grand_cell = worksheet.cell(row=2, column=grand_total_col, value=GRAND_TOTAL_LABEL)
    grand_cell.font = FONT_HEADER
    grand_cell.fill = DATE_FILL
    grand_cell.number_format = "mm-dd-yy"
    grand_cell.alignment = CENTER


def _write_stato_header_row(worksheet: Worksheet, model: ReportModel, grand_total_col: int) -> None:
    if model.groups:
        _write_group_banner(worksheet, row=3, label=model.groups[0].header_label,
                             num_dates=len(model.dates), grand_total_col=grand_total_col)

    for date_index in range(len(model.dates)):
        start_col = DATA_START_COL + date_index * COLS_PER_DATE_BLOCK
        for stato_index, stato in enumerate(STATI):
            cell = worksheet.cell(row=3, column=start_col + stato_index, value=stato)
            cell.font = FONT_HEADER
            cell.fill = _stato_fill(stato)
            cell.number_format = "0"
            cell.border = _cell_border(stato in YELLOW_STATI, ROW_KIND_HEADER)
        total_col = start_col + len(STATI)
        total_cell = worksheet.cell(row=3, column=total_col)
        total_cell.fill = GRAY_FILL
        total_cell.font = FONT_HEADER
        total_cell.number_format = "0"
        total_cell.border = _cell_border(False, ROW_KIND_HEADER)

    grand_cell = worksheet.cell(row=3, column=grand_total_col)
    grand_cell.fill = DATE_FILL
    grand_cell.font = FONT_HEADER
    grand_cell.number_format = "0"
    grand_cell.border = _cell_border(False, ROW_KIND_HEADER)


def _write_date_block(
    worksheet: Worksheet,
    row: int,
    start_col: int,
    values: dict,
    bold: bool,
    override_fill: PatternFill | None,
    row_kind: str,
) -> int:
    """Write the 8 stato values + total cell for one date block. Returns the total."""

    font = FONT_HEADER if bold else FONT_NORMAL
    date_total = 0
    for stato_index, stato in enumerate(STATI):
        value = values.get(stato, 0)
        date_total += value
        is_yellow = stato in YELLOW_STATI
        cell = worksheet.cell(row=row, column=start_col + stato_index, value=value)
        cell.font = font
        fill = _cell_fill(is_yellow, row_kind, override_fill)
        if fill is not None:
            cell.fill = fill
        cell.number_format = "0"
        cell.border = _cell_border(is_yellow, row_kind)

    total_col = start_col + len(STATI)
    total_cell = worksheet.cell(row=row, column=total_col, value=date_total)
    total_cell.font = font
    total_cell.fill = _total_col_fill(override_fill)
    total_cell.number_format = "0"
    total_cell.border = _cell_border(False, row_kind)

    return date_total


def _write_body(worksheet: Worksheet, model: ReportModel, grand_total_col: int) -> int:
    row = 4

    for group_index, group in enumerate(model.groups):
        if group_index > 0:
            _write_group_banner(worksheet, row=row, label=group.header_label,
                                 num_dates=len(model.dates), grand_total_col=grand_total_col)
            row += 1

        for url in group.urls:
            url_cell = worksheet.cell(row=row, column=2, value=url)
            url_cell.font = FONT_NORMAL
            url_cell.alignment = LEFT
            worksheet.cell(row=row, column=3).alignment = LEFT
            row_grand_total = 0
            for date_index, date_value in enumerate(model.dates):
                start_col = DATA_START_COL + date_index * COLS_PER_DATE_BLOCK
                values = group.values[url][date_value]
                row_grand_total += _write_date_block(
                    worksheet, row, start_col, values, bold=False, override_fill=None, row_kind=ROW_KIND_DATA
                )

            grand_cell = worksheet.cell(row=row, column=grand_total_col, value=row_grand_total)
            grand_cell.font = FONT_NORMAL
            grand_cell.number_format = "0"
            grand_cell.border = _cell_border(False, ROW_KIND_DATA)
            row += 1

        label_cell = worksheet.cell(row=row, column=2, value=group.subtotal_label)
        label_cell.font = SUBTOTAL_LABEL_FONT
        label_cell.fill = BLUE_FILL
        label_cell.number_format = "0%"
        label_cell.alignment = LEFT
        spacer_cell = worksheet.cell(row=row, column=3)
        spacer_cell.font = SUBTOTAL_LABEL_FONT
        spacer_cell.fill = BLUE_FILL
        spacer_cell.alignment = LEFT

        group_grand_total = 0
        for date_index, date_value in enumerate(model.dates):
            start_col = DATA_START_COL + date_index * COLS_PER_DATE_BLOCK
            group_grand_total += _write_date_block(
                worksheet, row, start_col, group.subtotal[date_value], bold=True, override_fill=None,
                row_kind=ROW_KIND_SUBTOTAL,
            )

        grand_cell = worksheet.cell(row=row, column=grand_total_col, value=group_grand_total)
        grand_cell.font = FONT_HEADER
        grand_cell.number_format = "0"
        grand_cell.border = _cell_border(False, ROW_KIND_HEADER)
        row += 1

    # blank spacer row before the overall grand total: values are cleared but
    # the bold header font/number format remain as leftover formatting.
    worksheet.cell(row=row, column=2).alignment = LEFT
    worksheet.cell(row=row, column=3).alignment = LEFT
    for date_index in range(len(model.dates)):
        start_col = DATA_START_COL + date_index * COLS_PER_DATE_BLOCK
        for col in range(start_col, start_col + len(STATI) + 1):
            spacer_data_cell = worksheet.cell(row=row, column=col)
            spacer_data_cell.font = FONT_HEADER
            spacer_data_cell.number_format = "0"
        total_col = start_col + len(STATI)
        worksheet.cell(row=row, column=total_col).fill = GRAY_FILL
    worksheet.cell(row=row, column=grand_total_col).font = FONT_HEADER
    worksheet.cell(row=row, column=grand_total_col).number_format = "0"
    row += 1

    label_cell = worksheet.cell(row=row, column=2, value=GRAND_TOTAL_LABEL)
    label_cell.font = FONT_HEADER
    label_cell.fill = BLUE_FILL
    label_cell.alignment = LEFT
    label_cell.border = THIN_TOP
    spacer_cell = worksheet.cell(row=row, column=3)
    spacer_cell.font = FONT_HEADER
    spacer_cell.fill = BLUE_FILL
    spacer_cell.alignment = LEFT
    spacer_cell.border = THIN_TOP

    overall_grand_total = 0
    for date_index, date_value in enumerate(model.dates):
        start_col = DATA_START_COL + date_index * COLS_PER_DATE_BLOCK
        combined_values = {
            stato: sum(group.subtotal[date_value][stato] for group in model.groups)
            for stato in STATI
        }
        overall_grand_total += _write_date_block(
            worksheet, row, start_col, combined_values, bold=True, override_fill=BLUE_FILL,
            row_kind=ROW_KIND_GRAND_TOTAL,
        )

    grand_cell = worksheet.cell(row=row, column=grand_total_col, value=overall_grand_total)
    grand_cell.font = FONT_HEADER
    grand_cell.fill = BLUE_FILL
    grand_cell.number_format = "0"
    grand_cell.border = _cell_border(False, ROW_KIND_GRAND_TOTAL)

    return row


def _apply_sheet_layout(worksheet: Worksheet, grand_total_col: int) -> None:
    worksheet.column_dimensions["B"].width = 70
    worksheet.column_dimensions["C"].width = 20
    for col in range(DATA_START_COL, grand_total_col + 1):
        worksheet.column_dimensions[get_column_letter(col)].width = 3.5

    worksheet.sheet_view.zoomScale = 55
    worksheet.sheet_view.showGridLines = True
