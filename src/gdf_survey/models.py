"""Data models for GDF screen pump and well survey."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# Neutral controller and device signatures for SCADA tag classification
CONTROLLER_SIGNATURES: dict[str, tuple[str, str]] = {
    "CTRL_A": ("Tipo A", "Controlador Tipo A"),
    "CTRL_B": ("Tipo B", "Controlador Tipo B"),
    "IO_MOD": ("Modulo IO", "Modulo Entrada/Salida"),
    "GEN_DEV": ("Genérico", "Dispositivo Genérico"),
}


def classify_device_type(device_name: str, signatures: dict[str, tuple[str, str]] | None = None) -> tuple[str, str]:
    """Classify the controller/device family and model from device name."""
    upper = device_name.upper()
    sigs = signatures if signatures is not None else CONTROLLER_SIGNATURES
    for sig, (brand, dev_type) in sigs.items():
        if sig in upper:
            return brand, dev_type
    if "PLC" in upper:
        return "PLC", "Controlador PLC"
    if "RTU" in upper:
        return "RTU", "Unidad Remota RTU"
    if "IO" in upper or "MOD" in upper:
        return "Modulo IO", "Modulo Entrada/Salida"
    if "DRV" in upper:
        return "Dispositivo", "Dispositivo de Campo"
    return "Desconocido", "Controlador Genérico"


@dataclass
class ScreenObjectRecord:
    """Represents a single visual/dynamic object or tab on the screen."""

    index: int
    pozo_index: int
    pozo_label: str
    object_name: str
    custom_data: str
    data_source: str
    dynamic_type: str
    layer: str

    @property
    def clean_data_source(self) -> str:
        """Strip $\"...\"$ wrappers if present."""
        m = re.search(r'\$"([^"]+)"\$', self.data_source)
        return m.group(1) if m else self.data_source


@dataclass
class PumpRecord:
    """Consolidated survey record for one equipment/channel position."""

    pozo_index: int
    pozo_label: str
    well_id: str
    pump_code: str
    battery: str
    device_name: str
    controller_brand: str
    controller_type: str
    has_pt: str
    has_tke: str
    has_tkq: str
    has_sam: str
    is_exp: str
    is_active: bool
    layer: str
    custom_data_map: dict[str, str] = field(default_factory=dict)

    @property
    def status_label(self) -> str:
        return "Activo" if self.is_active else "Plantilla / Reserva"


@dataclass
class GdfSurveyResult:
    """Complete survey result for one GDF file and layer."""

    gdf_path: Path
    display_name: str
    sheet_name: str
    layer_name: str
    objects: list[ScreenObjectRecord] = field(default_factory=list)
    pumps: list[PumpRecord] = field(default_factory=list)

    @property
    def total_objects(self) -> int:
        return len(self.objects)

    @property
    def total_pumps(self) -> int:
        return len(self.pumps)

    @property
    def active_pumps(self) -> int:
        return sum(1 for p in self.pumps if p.is_active)

    @property
    def spare_pumps(self) -> int:
        return sum(1 for p in self.pumps if not p.is_active)

    @property
    def brand_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for p in self.pumps:
            if p.is_active and p.controller_brand not in ("Desconocido", "Reserva"):
                counts[p.controller_brand] = counts.get(p.controller_brand, 0) + 1
        return dict(sorted(counts.items(), key=lambda x: -x[1]))

    @property
    def custom_data_types(self) -> list[str]:
        seen = set()
        result = []
        for obj in self.objects:
            if obj.custom_data and obj.custom_data not in seen:
                seen.add(obj.custom_data)
                result.append(obj.custom_data)
        return sorted(result)
