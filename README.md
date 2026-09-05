# GDF Survey Tool

Automated survey, layer discovery, equipment classification, and reporting tool for GraphWorX32 `.gdf` display files.

## Features

- **Automated Screen Inspection**: Analyzes `.gdf` displays using `graphworx32-gdf-parser` without requiring GraphWorX32 or Windows COM services.
- **Layer & Object Discovery**: Enumerates screen layers, dynamic visibility/size objects, and linked OPC data source tags.
- **Equipment & Device Classification**: Correlates device tags, identifies controller and communication interfaces, and consolidates multi-tag equipment records.
- **Dual Reporting**: Generates interactive HTML dashboards with equipment cards and formatted Excel multi-sheet survey workbooks via `openpyxl`.

## Installation

```bash
pip install -e ../graphworx32-gdf-parser
pip install -e .
```

## Usage

```bash
# Single display to default relevamientos/ directory
gdf-survey pantalla.gdf --name=Planta1

# Multiple displays to an output directory
gdf-survey pantallas/*.gdf --output-dir=informes/

# Custom Excel and HTML destinations
gdf-survey pantalla.gdf -x reporte.xlsx -t reporte.html
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
