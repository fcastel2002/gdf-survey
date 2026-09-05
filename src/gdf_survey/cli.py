"""Command Line Interface for GDF Pump Survey tool."""

from __future__ import annotations

import argparse
import glob
import re
import sys
from pathlib import Path
from typing import Sequence

from gdf_survey.excel_report import generate_excel_survey
from gdf_survey.extractor import extract_gdf_survey
from gdf_survey.html_report import generate_html_survey
from gdf_survey.models import GdfSurveyResult


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gdf-survey",
        description="Survey equipment, controller types, and tags from GraphWorX32 displays (.gdf).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  gdf-survey display.gdf --name=Area1 -o surveys/\n"
            "  gdf-survey display.gdf -o reports/Area1_equipment\n"
            "  gdf-survey displays/*.gdf --output-dir=output/\n"
            "  gdf-survey display.gdf -x report.xlsx -t report.html\n"
        ),
    )

    parser.add_argument(
        "inputs",
        nargs="+",
        help="One or more .gdf files (accepts glob patterns like 'displays/*.gdf')",
    )
    parser.add_argument(
        "-l",
        "--layer",
        default="1",
        help="Layer to survey (default: 1 or '1-ALM')",
    )
    parser.add_argument(
        "-r",
        "--root-name-pattern",
        default=None,
        help="Regex pattern with capture group 1 to group objects by root name (default: '^([A-Za-z0-9_-]+?)(?:[_.]|$)')",
    )
    parser.add_argument(
        "--root-custom-data",
        default=None,
        help="Custom data key to identify/anchor each root entity (e.g. '<<tag>>' or '<<device>>')",
    )
    parser.add_argument(
        "--custom-data",
        default=None,
        help="Comma-separated list of custom data keys to include in report (default: all discovered keys)",
    )
    parser.add_argument(
        "--flat",
        action="store_true",
        help="Survey each visual/dynamic object individually without grouping",
    )
    parser.add_argument(
        "-n",
        "--name",
        default=None,
        help="Custom name for Excel sheet / tab (e.g. --name=Area1). Comma-separated list for multiple files.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        "--out",
        dest="output_dir",
        default=None,
        help=(
            "Output directory or path prefix for both reports "
            "(e.g. -o surveys/ or -o ./reports/Area1). "
            "Creates intermediate folders automatically."
        ),
    )
    parser.add_argument(
        "-x",
        "--out-excel",
        default=None,
        help="Specific path for output Excel workbook (overrides -o)",
    )
    parser.add_argument(
        "-t",
        "--out-html",
        default=None,
        help="Specific path for interactive HTML report (overrides -o)",
    )
    parser.add_argument(
        "--no-excel",
        action="store_true",
        help="Skip generating the Excel workbook",
    )
    parser.add_argument(
        "--no-html",
        action="store_true",
        help="Skip generating the HTML report",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Quiet mode, suppress console summary",
    )

    return parser


def _resolve_output_paths(
    output_dir: str | None,
    out_excel: str | None,
    out_html: str | None,
    default_base_name: str,
) -> tuple[Path, Path]:
    """Determine final Excel and HTML paths based on output_dir and explicit overrides."""
    base_dir = Path(".")
    base_filename = default_base_name

    if output_dir:
        raw_p = Path(output_dir)
        is_directory = (
            output_dir.endswith(("/", "\\"))
            or (raw_p.exists() and raw_p.is_dir())
        )

        if is_directory:
            base_dir = raw_p
            base_filename = default_base_name
        elif raw_p.suffix.lower() == ".xlsx":
            base_dir = raw_p.parent
            base_filename = raw_p.stem
            if out_excel is None:
                out_excel = str(raw_p)
        elif raw_p.suffix.lower() == ".html":
            base_dir = raw_p.parent
            base_filename = raw_p.stem
            if out_html is None:
                out_html = str(raw_p)
        else:
            base_dir = raw_p.parent
            base_filename = raw_p.name
    final_excel = Path(out_excel) if out_excel else base_dir / f"{base_filename}.xlsx"
    final_html = Path(out_html) if out_html else base_dir / f"{base_filename}.html"

    return final_excel, final_html


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # 1. Expand input files / globs
    resolved_paths: list[Path] = []
    for pattern in args.inputs:
        matched = [Path(p) for p in glob.glob(pattern)]
        if matched:
            resolved_paths.extend(matched)
        else:
            p = Path(pattern)
            if p.exists():
                resolved_paths.append(p)
            else:
                sys.stderr.write(f"Error: File '{pattern}' not found.\n")
                return 1

    if not resolved_paths:
        sys.stderr.write("Error: No valid .gdf files specified.\n")
        return 1

    # Deduplicate while preserving order
    seen: set[Path] = set()
    unique_paths: list[Path] = []
    for p in resolved_paths:
        abs_p = p.resolve()
        if abs_p not in seen and abs_p.suffix.lower() == ".gdf":
            seen.add(abs_p)
            unique_paths.append(p)

    if not unique_paths:
        sys.stderr.write("Error: None of the specified files have .gdf extension.\n")
        return 1

    # 2. Parse sheet names
    custom_names: list[str] = []
    if args.name:
        custom_names = [n.strip() for n in args.name.split(",")]

    # 3. Parse custom data filter if provided
    cd_filter = [k.strip() for k in args.custom_data.split(",")] if args.custom_data else None

    # 4. Extract each GDF
    results: list[GdfSurveyResult] = []
    had_errors = False
    for i, path in enumerate(unique_paths):
        if i < len(custom_names):
            sheet_name = custom_names[i]
        else:
            m_area = re.search(r"(?:equipos_|pantalla_|display_|area_)([A-Za-z0-9]+)", path.stem, re.IGNORECASE)
            sheet_name = m_area.group(1) if m_area else path.stem

        try:
            res = extract_gdf_survey(
                path,
                layer_target=args.layer,
                sheet_name=sheet_name,
                root_name_pattern=args.root_name_pattern,
                root_custom_data=args.root_custom_data,
                custom_data_filter=cd_filter,
                flat=args.flat,
            )
            results.append(res)
        except Exception as err:
            had_errors = True
            sys.stderr.write(f"Error processing '{path.name}': {err}\n")
    if not results:
        sys.stderr.write("Error: Could not process any .gdf file successfully.\n")
        return 1

    # 5. Determine base name and resolve output paths
    default_name = f"survey_{custom_names[0]}" if custom_names else f"survey_{results[0].sheet_name}"
    excel_path, html_path = _resolve_output_paths(
        args.output_dir,
        args.out_excel,
        args.out_html,
        default_name,
    )

    actual_excel: Path | None = None
    actual_html: Path | None = None

    if not args.no_excel:
        actual_excel = generate_excel_survey(results, excel_path)
    if not args.no_html:
        actual_html = generate_html_survey(results, html_path)

    # 6. Print Console Summary
    if not args.quiet:
        print("\n" + "=" * 70)
        print(" GDF SCADA SCREEN & EQUIPMENT SURVEY")
        print("=" * 70)

        for res in results:
            print(f"\nDisplay:  {res.gdf_path.name}  (Sheet: {res.sheet_name})")
            print(f"Layer:    {res.layer_name}")
            print(f"Items:    {res.total_items} surveyed ({res.active_items} active, {res.spare_items} spare/template)")

            if res.discovered_custom_data_keys:
                keys_str = ", ".join(res.discovered_custom_data_keys)
                print(f"Custom Data: {keys_str}")

        print("\n" + "-" * 70)
        if actual_excel:
            print(f"Generated Excel:  {actual_excel} ({actual_excel.stat().st_size:,} bytes)")
        if actual_html:
            print(f"Interactive HTML: {actual_html} ({actual_html.stat().st_size:,} bytes)")
        print("=" * 70 + "\n")

    return 2 if had_errors else 0


if __name__ == "__main__":
    sys.exit(main())
