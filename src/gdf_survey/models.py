"""Data models for generic SCADA screen object and equipment survey."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


# Neutral controller signatures for device classification
CONTROLLER_SIGNATURES: dict[str, tuple[str, str]] = {
    "CTRL_A": ("Tipo A", "Controlador Tipo A"),
    "CTRL_B": ("Tipo B", "Controlador Tipo B"),
    "IO_MOD": ("Modulo IO", "Modulo Entrada/Salida"),
    "GEN_DEV": ("Generic", "Generic Device"),
}


def classify_device_type(device_name: str, signatures: dict[str, tuple[str, str]] | None = None) -> tuple[str, str]:
    """Classify the controller/device family and model from device name."""
    upper = device_name.upper()
    sigs = signatures if signatures is not None else CONTROLLER_SIGNATURES
    for sig, (brand, dev_type) in sigs.items():
        if sig in upper:
            return brand, dev_type
    if "PLC" in upper:
        return "PLC", "PLC Controller"
    if "RTU" in upper:
        return "RTU", "RTU Unit"
    if "IO" in upper or "MOD" in upper:
        return "Modulo IO", "IO Module"
    if "DRV" in upper:
        return "Device", "Field Device"
    return "Desconocido", "Generic Controller"


def extract_device_info(data_source: str) -> tuple[str, str]:
    """Extract device name and category from a data source or OPC item path."""
    clean = re.sub(r'^\$"|\"\$$', "", data_source).strip()
    if not clean or clean == "x=0":
        return "", ""

    # Check for [Server]Device.Item or Channel.Device.Item
    m_bracket = re.search(r'\[([^\]]+)\]([A-Za-z0-9_-]+)', clean)
    if m_bracket:
        return m_bracket.group(2), m_bracket.group(1)

    if "." in clean:
        parts = clean.split(".")
        dev_name = parts[0]
        brand_1, _ = classify_device_type(dev_name)
        if brand_1 != "Desconocido":
            return dev_name, brand_1
        brand_2, _ = classify_device_type(parts[1])
        if brand_2 != "Desconocido":
            return dev_name, brand_2
        return dev_name, parts[1]

    brand, _ = classify_device_type(clean)
    return clean, (brand if brand != "Desconocido" else "")


@dataclass
class ScreenObjectRecord:
    """Represents a single visual/dynamic object on the screen."""

    index: int
    root_id: str
    object_name: str
    custom_data: str
    data_source: str
    dynamic_type: str
    layer: str
    description: str = ""

    @property
    def clean_data_source(self) -> str:
        """Strip $\"...\"$ wrappers if present."""
        m = re.search(r'\$"([^"]+)"\$', self.data_source)
        return m.group(1) if m else self.data_source


@dataclass(init=False)
class EquipmentRecord:
    """Consolidated survey record for an equipment, device, or visual group."""

    index: int
    root_id: str
    label: str
    device_name: str = ""
    controller_type: str = ""
    primary_source: str = ""
    is_active: bool = True
    layer: str = ""
    custom_data: dict[str, str] = field(default_factory=dict)
    objects: list[ScreenObjectRecord] = field(default_factory=list)

    def __init__(
        self,
        index: int = 1,
        root_id: str = "",
        label: str = "",
        *args,
        device_name: str = "",
        controller_type: str = "",
        primary_source: str = "",
        is_active: bool = True,
        layer: str = "",
        custom_data: dict[str, str] | None = None,
        objects: list[ScreenObjectRecord] | None = None,
        **kwargs,
    ) -> None:
        self._well_id = ""
        if args:
            # Handle legacy positional signature: (index, label, root_id, pump_code, battery, device_name, brand, type, pt, tke, tkq, sam, exp, is_active, layer)
            self.index = index
            self.label = root_id
            self.root_id = str(label)
            self._well_id = str(label)
            self.primary_source = str(args[0]) if len(args) > 0 else ""
            self.device_name = str(args[2]) if len(args) > 2 else device_name
            self.controller_type = str(args[4]) if len(args) > 4 else controller_type
            self.is_active = args[10] if len(args) > 10 else is_active
            self.layer = str(args[11]) if len(args) > 11 else layer
            cd = dict(custom_data or {})
            if len(args) > 0 and args[0]: cd["<<tag>>"] = str(args[0])
            if len(args) > 1 and args[1]: cd["<<group>>"] = str(args[1])
            if len(args) > 5 and args[5]: cd["<<tienept>>"] = str(args[5])
            if len(args) > 6 and args[6]: cd["<<tienetke>>"] = str(args[6])
            if len(args) > 7 and args[7]: cd["<<tienetkq>>"] = str(args[7])
            if len(args) > 8 and args[8]: cd["<<tienesam>>"] = str(args[8])
            if len(args) > 9 and args[9]: cd["<<esexp>>"] = str(args[9])
            self.custom_data = cd
            self.objects = objects or []
        else:
            self.index = index
            self.root_id = root_id
            self.label = label or root_id
            self.device_name = device_name
            self.controller_type = controller_type
            self.primary_source = primary_source
            self.is_active = is_active
            self.layer = layer
            self.custom_data = custom_data if custom_data is not None else {}
            self.objects = objects if objects is not None else []

    @property
    def status_label(self) -> str:
        return "Active" if self.is_active else "Spare / Template"

    @property
    def custom_data_map(self) -> dict[str, str]:
        """Backwards compatibility alias."""
        return self.custom_data

    @property
    def pozo_index(self) -> int:
        return self.index

    @property
    def pozo_label(self) -> str:
        return self.label

    @property
    def well_id(self) -> str:
        return self._well_id or self.device_name or self.root_id

    @property
    def pump_code(self) -> str:
        return self.custom_data.get("<<tag>>") or self.custom_data.get("<<pozo>>") or self.root_id

    @property
    def battery(self) -> str:
        return self.custom_data.get("<<group>>") or self.custom_data.get("<<bat>>") or ""

    @property
    def controller_brand(self) -> str:
        return self.controller_type or self.device_name

    @property
    def has_pt(self) -> str:
        return self.custom_data.get("<<tienept>>", "0")

    @property
    def has_tke(self) -> str:
        return self.custom_data.get("<<tienetke>>", "0")

    @property
    def has_tkq(self) -> str:
        return self.custom_data.get("<<tienetkq>>", "0")

    @property
    def has_sam(self) -> str:
        return self.custom_data.get("<<tienesam>>", "0")

    @property
    def is_exp(self) -> str:
        return self.custom_data.get("<<esexp>>", "0")


PumpRecord = EquipmentRecord


@dataclass(init=False)
class GdfSurveyResult:
    """Complete survey result for one GDF file and layer."""

    gdf_path: Path
    display_name: str
    sheet_name: str
    layer_name: str
    objects: list[ScreenObjectRecord] = field(default_factory=list)
    items: list[EquipmentRecord] = field(default_factory=list)
    discovered_custom_data_keys: list[str] = field(default_factory=list)

    def __init__(
        self,
        gdf_path: Path,
        display_name: str,
        sheet_name: str,
        layer_name: str,
        objects: list[ScreenObjectRecord] | None = None,
        items: list[EquipmentRecord] | None = None,
        discovered_custom_data_keys: list[str] | None = None,
        pumps: list[EquipmentRecord] | None = None,
    ) -> None:
        self.gdf_path = gdf_path
        self.display_name = display_name
        self.sheet_name = sheet_name
        self.layer_name = layer_name
        self.objects = objects if objects is not None else []
        if items is not None:
            self.items = items
        elif pumps is not None:
            self.items = pumps
        else:
            self.items = []
        if discovered_custom_data_keys is not None:
            self.discovered_custom_data_keys = discovered_custom_data_keys
        else:
            keys = set()
            for it in self.items:
                keys.update(it.custom_data.keys())
            self.discovered_custom_data_keys = sorted(keys)

    @property
    def brand_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for it in self.items:
            brand = it.controller_brand or it.device_name
            if it.is_active and brand:
                counts[brand] = counts.get(brand, 0) + 1
        return dict(sorted(counts.items(), key=lambda x: -x[1]))

    @property
    def pumps(self) -> list[EquipmentRecord]:
        """Backwards compatibility alias for items."""
        return self.items

    @pumps.setter
    def pumps(self, val: list[EquipmentRecord]) -> None:
        self.items = val

    @property
    def total_objects(self) -> int:
        return len(self.objects)

    @property
    def total_items(self) -> int:
        return len(self.items)

    @property
    def total_pumps(self) -> int:
        return self.total_items

    @property
    def active_items(self) -> int:
        return sum(1 for item in self.items if item.is_active)

    @property
    def active_pumps(self) -> int:
        return self.active_items

    @property
    def spare_items(self) -> int:
        return sum(1 for item in self.items if not item.is_active)

    @property
    def spare_pumps(self) -> int:
        return self.spare_items

    @property
    def custom_data_types(self) -> list[str]:
        return self.discovered_custom_data_keys
