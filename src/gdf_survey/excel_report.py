"""Excel workbook generator for GDF pump survey using openpyxl."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Sequence

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from gdf_survey.models import GdfSurveyResult

COLOR_HEADER_BG = "0F172A"       # Slate 900
COLOR_HEADER_FG = "FFFFFF"
COLOR_TITLE_BG = "1E293B"        # Slate 800
COLOR_SUBTITLE_BG = "334155"     # Slate 700
COLOR_ZEBRA_ODD = "F8FAFC"       # Slate 50
COLOR_ZEBRA_EVEN = "FFFFFF"
COLOR_BORDER = "CBD5E1"          # Slate 300
COLOR_YES_BG = "DCFCE7"          # Green 100
COLOR_YES_FG = "166534"          # Green 800
COLOR_NO_BG = "F1F5F9"           # Slate 100
COLOR_NO_FG = "94A3B8"           # Slate 400

CONTROLLER_COLORS = {
    "Tipo A": ("EFF6FF", "1E40AF"),      # Blue
    "Tipo B": ("FAF5FF", "6B21A8"),      # Purple
    "PLC": ("F0FDF4", "15803D"),         # Emerald
    "RTU": ("FFFBEB", "B45309"),         # Amber
    "Modulo IO": ("FEF2F2", "991B1B"),    # Red
}
BRAND_COLORS = CONTROLLER_COLORS


def _thin_border() -> Border:
    thin = Side(border_style="thin", color=COLOR_BORDER)
    return Border(left=thin, right=thin, top=thin, bottom=thin)


def generate_excel_survey(
    results: Sequence[GdfSurveyResult],
    output_path: str | Path,
) -> Path:
    """Generate a formatted multi-sheet Excel workbook with equipment survey results."""
    target_path = Path(output_path).resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)

    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # type: ignore[arg-type]

    # Summary sheet if multiple screens are surveyed
    if len(results) > 1:
        _build_summary_sheet(wb, results)

    # Consolidated pump sheet for each GDF result
    for res in results:
        _build_pumps_sheet(wb, res)

    wb.save(str(target_path))
    return target_path


def _build_summary_sheet(wb: openpyxl.Workbook, results: Sequence[GdfSurveyResult]) -> None:
    ws = wb.create_sheet(title="General Summary")
    ws.views.sheetView[0].showGridLines = True

    # Title
    ws.merge_cells("A1:F1")
    title_cell = ws["A1"]
    title_cell.value = "SCADA DISPLAY & EQUIPMENT SURVEY - CONSOLIDATED SUMMARY"
    title_cell.font = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
    title_cell.fill = PatternFill(start_color=COLOR_TITLE_BG, end_color=COLOR_TITLE_BG, fill_type="solid")
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 36

    headers = [
        "Sheet / Display",
        "GDF File",
        "Surveyed Layer",
        "Surveyed Items",
        "Active Items",
        "Discovered Custom Data Keys",
    ]
    ws.append([])
    ws.append(headers)
    ws.row_dimensions[3].height = 24

    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=3, column=col_num)
        cell.font = Font(name="Calibri", size=11, bold=True, color=COLOR_HEADER_FG)
        cell.fill = PatternFill(start_color=COLOR_HEADER_BG, end_color=COLOR_HEADER_BG, fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = _thin_border()

    for r_idx, res in enumerate(results, start=4):
        cd_keys_str = ", ".join(res.discovered_custom_data_keys) if res.discovered_custom_data_keys else "(None)"
        row_vals = [
            res.sheet_name,
            res.gdf_path.name,
            res.layer_name,
            res.total_items,
            res.active_items,
            cd_keys_str,
        ]
        ws.append(row_vals)
        ws.row_dimensions[r_idx].height = 20

        zebra = COLOR_ZEBRA_ODD if r_idx % 2 == 1 else COLOR_ZEBRA_EVEN
        for col_num, val in enumerate(row_vals, start=1):
            cell = ws.cell(row=r_idx, column=col_num)
            if isinstance(val, str):
                cell.data_type = "s"
            cell.border = _thin_border()
            cell.fill = PatternFill(start_color=zebra, end_color=zebra, fill_type="solid")
            cell.font = Font(name="Calibri", size=10)
            if col_num in (4, 5):
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 14)


def _build_pumps_sheet(wb: openpyxl.Workbook, res: GdfSurveyResult) -> None:
    """Build the consolidated sheet with 1 row per equipment/item showing all its configuration properties."""
    clean_title = re.sub(r'[\\/*?:\[\]]', "_", res.sheet_name)[:31]
    ws = wb.create_sheet(title=clean_title)
    ws.views.sheetView[0].showGridLines = True

    # 1. Main Banner
    num_cols = max(5 + len(res.discovered_custom_data_keys), 6)
    end_col_letter = get_column_letter(num_cols)
    ws.merge_cells(f"A1:{end_col_letter}1")
    title = ws["A1"]
    title.value = f"SCADA DISPLAY SURVEY - DISPLAY: {res.display_name}.gdf"
    title.font = Font(name="Calibri", size=13, bold=True, color="FFFFFF")
    title.fill = PatternFill(start_color=COLOR_TITLE_BG, end_color=COLOR_TITLE_BG, fill_type="solid")
    title.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 36

    # 2. Sub-banner
    ws.merge_cells(f"A2:{end_col_letter}2")
    info = ws["A2"]
    cd_count = len(res.discovered_custom_data_keys)
    info.value = (
        f"Layer: {res.layer_name}   |   "
        f"Total Surveyed Items: {res.total_items}   |   "
        f"Active: {res.active_items}   |   "
        f"Custom Data Attributes: {cd_count}"
    )
    info.font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    info.fill = PatternFill(start_color=COLOR_SUBTITLE_BG, end_color=COLOR_SUBTITLE_BG, fill_type="solid")
    info.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 24

    # 3. Headers
    headers = [
        "No.",
        "Root ID",
        "Primary Data Source",
        "Device",
        "Controller / Type",
    ]
    for k in res.discovered_custom_data_keys:
        headers.append(k)

    ws.append([])
    ws.append(headers)
    ws.row_dimensions[4].height = 26

    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=4, column=col_idx)
        cell.font = Font(name="Calibri", size=10, bold=True, color=COLOR_HEADER_FG)
        cell.fill = PatternFill(start_color=COLOR_HEADER_BG, end_color=COLOR_HEADER_BG, fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = _thin_border()

    # 4. Data rows
    for r_idx, item in enumerate(res.items, start=5):
        row_vals = [
            item.index,
            item.root_id,
            item.primary_source or "-",
            item.device_name or "-",
            item.controller_type or "-",
        ]
        for k in res.discovered_custom_data_keys:
            raw_v = item.custom_data.get(k, "")
            if raw_v == "1":
                row_vals.append("YES")
            elif raw_v == "0":
                row_vals.append("NO")
            else:
                row_vals.append(raw_v)

        ws.append(row_vals)
        ws.row_dimensions[r_idx].height = 20

        zebra = COLOR_ZEBRA_ODD if r_idx % 2 == 1 else COLOR_ZEBRA_EVEN
        for col_idx, val in enumerate(row_vals, start=1):
            cell = ws.cell(row=r_idx, column=col_idx)
            if isinstance(val, str):
                cell.data_type = "s"
            cell.border = _thin_border()
            cell.font = Font(name="Calibri", size=9)
            cell.fill = PatternFill(start_color=zebra, end_color=zebra, fill_type="solid")

            # Alignments
            if col_idx in (1, 2):
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

            # YES / NO badges
            if val == "YES":
                cell.fill = PatternFill(start_color=COLOR_YES_BG, end_color=COLOR_YES_BG, fill_type="solid")
                cell.font = Font(name="Calibri", size=9, bold=True, color=COLOR_YES_FG)
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif val == "NO":
                cell.fill = PatternFill(start_color=COLOR_NO_BG, end_color=COLOR_NO_BG, fill_type="solid")
                cell.font = Font(name="Calibri", size=9, color=COLOR_NO_FG)
                cell.alignment = Alignment(horizontal="center", vertical="center")

    end_col = get_column_letter(len(headers))
    last_row = 4 + len(res.items)
    ws.auto_filter.ref = f"A4:{end_col}{last_row}"
    ws.freeze_panes = "A5"

    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        val_lens = [len(str(cell.value or "")) for cell in col[3:]]
        max_len = max(val_lens) if val_lens else 10
        ws.column_dimensions[col_letter].width = max(min(max_len + 4, 45), 12)
