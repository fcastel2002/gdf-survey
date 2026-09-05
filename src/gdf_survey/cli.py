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
        description="Relevamiento de equipos, tipos de controladores y tags desde pantallas GraphWorX32 (.gdf).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Ejemplos:\n"
            "  gdf-survey pantalla.gdf --name=Area1 -o relevamientos/\n"
            "  gdf-survey pantalla.gdf -o informes/Area1_equipos\n"
            "  gdf-survey pantallas/*.gdf --output-dir=salidas/\n"
            "  gdf-survey pantalla.gdf -x reporte.xlsx -t reporte.html\n"
        ),
    )

    parser.add_argument(
        "inputs",
        nargs="+",
        help="Uno o mas archivos .gdf (acepta patrones glob como 'gdf_examples/*.gdf')",
    )
    parser.add_argument(
        "-l",
        "--layer",
        default="1",
        help="Capa a relevar (default: 1 o '1-ALM')",
    )
    parser.add_argument(
        "-n",
        "--name",
        default=None,
        help="Nombre personalizado para la hoja de Excel / solapa (ej: --name=Area1). Para multiples archivos se puede pasar lista separada por comas.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        "--out",
        dest="output_dir",
        default=None,
        help=(
            "Directorio o prefijo de ruta de salida para ambos reportes "
            "(ej: -o relevamientos/ o -o ./reportes/Area1). "
            "Crea automaticamente carpetas intermedias."
        ),
    )
    parser.add_argument(
        "-x",
        "--out-excel",
        default=None,
        help="Ruta especifica del archivo Excel de salida (sobrescribe -o)",
    )
    parser.add_argument(
        "-t",
        "--out-html",
        default=None,
        help="Ruta especifica del reporte HTML interactivo de salida (sobrescribe -o)",
    )
    parser.add_argument(
        "--no-excel",
        action="store_true",
        help="Omitir la generacion del archivo Excel",
    )
    parser.add_argument(
        "--no-html",
        action="store_true",
        help="Omitir la generacion del reporte HTML",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Modo silencioso, no imprime el resumen en consola",
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
                sys.stderr.write(f"Error: No se encontro el archivo '{pattern}'\n")
                return 1

    if not resolved_paths:
        sys.stderr.write("Error: No se especificaron archivos .gdf validos.\n")
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
        sys.stderr.write("Error: Ninguno de los archivos especificados tiene extension .gdf\n")
        return 1

    # 2. Parse sheet names
    custom_names: list[str] = []
    if args.name:
        custom_names = [n.strip() for n in args.name.split(",")]

    # 3. Extract each GDF
    results: list[GdfSurveyResult] = []
    had_errors = False
    for i, path in enumerate(unique_paths):
        if i < len(custom_names):
            sheet_name = custom_names[i]
        else:
            m_area = re.search(r"(?:equipos_|pantalla_|display_|area_)([A-Za-z0-9]+)", path.stem, re.IGNORECASE)
            sheet_name = m_area.group(1) if m_area else path.stem

        try:
            res = extract_gdf_survey(path, layer_target=args.layer, sheet_name=sheet_name)
            results.append(res)
        except Exception as err:
            had_errors = True
            sys.stderr.write(f"Error procesando '{path.name}': {err}\n")
    if not results:
        sys.stderr.write("Error: No se pudo procesar ningun archivo .gdf correctamente.\n")
        return 1

    # 4. Determine base name and resolve output paths
    default_name = f"relevamiento_{custom_names[0]}" if custom_names else f"relevamiento_{results[0].sheet_name}"
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

    # 5. Print Console Summary
    if not args.quiet:
        print("\n" + "=" * 70)
        print(" RELEVAMIENTO DE EQUIPOS Y PANTALLAS SCADA GDF")
        print("=" * 70)

        for res in results:
            print(f"\nPantalla: {res.gdf_path.name}  (Hoja: {res.sheet_name})")
            print(f"Capa:     {res.layer_name}")
            print(f"Total:    {res.total_pumps} renglones ({res.active_pumps} activos, {res.spare_pumps} reserva/plantilla)")

            if res.brand_counts:
                brands = ", ".join(f"{b}: {c}" for b, c in res.brand_counts.items())
                print(f"Controladores: {brands}")

        print("\n" + "-" * 70)
        if actual_excel:
            print(f"Excel generado:  {actual_excel} ({actual_excel.stat().st_size:,} bytes)")
        if actual_html:
            print(f"HTML interactivo: {actual_html} ({actual_html.stat().st_size:,} bytes)")
        print("=" * 70 + "\n")

    return 2 if had_errors else 0


if __name__ == "__main__":
    sys.exit(main())
