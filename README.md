# GDF Survey Tool

Automated survey, layer discovery, equipment classification, and reporting tool for GraphWorX32 `.gdf` display files.

## Features

- **Automated Screen Inspection**: Analyzes `.gdf` displays using [`graphworx32-gdf-parser`](https://github.com/fcastel2002/graphworx32-gdf-parser) without requiring GraphWorX32 or Windows COM services.
- **Layer & Object Discovery**: Enumerates screen layers, dynamic visibility/size objects, and linked OPC data source tags.
- **Equipment & Device Classification**: Correlates device tags, identifies controller and communication interfaces, and consolidates multi-tag equipment records.
- **Dual Reporting**: Generates interactive HTML dashboards with equipment cards and formatted Excel multi-sheet survey workbooks via `openpyxl`.

## Installation

```bash
pip install git+https://github.com/fcastel2002/graphworx32-gdf-parser.git
pip install -e .
```

## Usage

```bash
# Single display to default surveys/ directory
gdf-survey display.gdf --name=Area1

# Group by custom root name pattern (e.g. prefix before underscore/dot)
gdf-survey display.gdf -r "^([A-Za-z0-9_-]+?)[_.]"

# Anchor root equipment by specific custom data key
gdf-survey display.gdf --root-custom-data "<<tag>>"

# Filter which custom data keys to report
gdf-survey display.gdf --custom-data "<<tag>>,<<speed>>,<<pv>>"

# Flat survey mode (each dynamic object individually without grouping)
gdf-survey display.gdf --flat

# Multiple displays to an output directory
gdf-survey displays/*.gdf --output-dir=reports/

# Custom Excel and HTML destinations
gdf-survey display.gdf -x report.xlsx -t report.html
```

## Options

- `-r`, `--root-name-pattern`: Regex pattern with capture group 1 to group objects by root name (default: `^([A-Za-z0-9_-]+?)(?:[_.]|$)`).
- `--root-custom-data`: Custom data key to identify/anchor each root entity (e.g. `<<tag>>` or `<<device>>`).
- `--custom-data`: Comma-separated list of custom data keys to include in reports (defaults to all dynamically discovered keys).
- `--flat`: Extract each visual/dynamic object individually without grouping.
- `-l`, `--layer`: Layer to survey (default: `1`).
- `-n`, `--name`: Custom name for Excel sheet / tab.
- `-o`, `--output-dir`: Output directory for generated reports.
- `-x`, `--out-excel`: Custom destination path for Excel report.
- `-t`, `--out-html`: Custom destination path for interactive HTML report.
- `--no-excel`: Skip generating Excel workbook.
- `--no-html`: Skip generating HTML dashboard.
- `-q`, `--quiet`: Quiet mode, suppress console summary.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
