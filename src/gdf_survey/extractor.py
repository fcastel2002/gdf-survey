"""GDF Layer and Pump Survey extraction engine."""

from __future__ import annotations

import re
from pathlib import Path

from graphworx32_gdf_parser import parse_gdf
from graphworx32_gdf_parser.screen import clean_expression

from gdf_survey.models import (
    GdfSurveyResult,
    PumpRecord,
    ScreenObjectRecord,
    classify_device_type,
)

_clean_val = clean_expression


def extract_gdf_survey(
    gdf_path: str | Path,
    layer_target: str = "1",
    sheet_name: str | None = None,
) -> GdfSurveyResult:
    """Extract all objects, custom data, data sources, and consolidated equipment records from GDF."""
    path = Path(gdf_path).resolve(strict=True)

    parsed = parse_gdf(path, profiles=("screen",), layer_target=layer_target)
    if parsed.document is None:
        errors = [d.message for d in parsed.diagnostics if d.severity == "error"]
        details = "; ".join(errors) if errors else "input could not be inspected"
        raise ValueError(f"Failed to parse GDF {path.name}: {details}")

    screen = parsed.document.screen
    if screen is None or not screen.layers:
        derived_sheet = sheet_name or path.stem
        return GdfSurveyResult(
            gdf_path=path,
            display_name=path.stem,
            sheet_name=derived_sheet,
            layer_name=layer_target,
            objects=[],
            pumps=[],
        )

    selected_layer = screen.selected_layer or layer_target

    all_objects: list[ScreenObjectRecord] = []
    for raw in screen.objects:
        name = raw.object_name
        pozo_m = re.search(r"(?:pozo|item|eq|unit)(\d+)", name, re.IGNORECASE)
        pozo_idx = int(pozo_m.group(1)) if pozo_m else 0

        rec = ScreenObjectRecord(
            index=raw.index,
            pozo_index=pozo_idx,
            pozo_label=f"Equipo {pozo_idx}" if pozo_idx else "General",
            object_name=name,
            custom_data=raw.custom_data,
            data_source=raw.data_source,
            dynamic_type=raw.dynamic_type,
            layer=selected_layer,
        )
        all_objects.append(rec)

    # Group into consolidated equipment
    pozo_groups: dict[int, list[ScreenObjectRecord]] = {}
    for obj in all_objects:
        if obj.pozo_index:
            pozo_groups.setdefault(obj.pozo_index, []).append(obj)

    pumps: list[PumpRecord] = []
    for p_idx in sorted(pozo_groups):
        items = {o.custom_data: o for o in pozo_groups[p_idx]}
        disp_obj = items.get("<<dispositivo>>")
        pozo_obj = items.get("<<pozo>>")
        bat_obj = items.get("<<bat>>")
        pt_obj = items.get("<<tienept>>")
        tke_obj = items.get("<<tienetke>>")
        tkq_obj = items.get("<<tienetkq>>")
        sam_obj = items.get("<<tienesam>>")
        exp_obj = items.get("<<esexp>>")

        disp_val = _clean_val(disp_obj.data_source if disp_obj else "")
        pozo_val = _clean_val(pozo_obj.data_source if pozo_obj else "")
        bat_val = _clean_val(bat_obj.data_source if bat_obj else "")
        pt_val = _clean_val(pt_obj.data_source if pt_obj else "0")
        tke_val = _clean_val(tke_obj.data_source if tke_obj else "0")
        tkq_val = _clean_val(tkq_obj.data_source if tkq_obj else "0")
        sam_val = _clean_val(sam_obj.data_source if sam_obj else "0")
        exp_val = _clean_val(exp_obj.data_source if exp_obj else "0")

        # Active check: has non-empty device, not x=0, not placeholder itemXX_dispXX
        is_active = bool(
            disp_val
            and disp_val != "x=0"
            and not re.search(r"(?:pozo|item|disp)\d+_(?:disp|item)\d+", disp_val, re.IGNORECASE)
            and pozo_val
            and pozo_val != "x=0"
        )

        well_id = ""
        device_name = ""
        controller_brand = "Desconocido"
        controller_type = ""

        if is_active:
            if "." in disp_val:
                parts = disp_val.split(".", 1)
                m_well = re.search(r"([A-Za-z0-9_]+)", parts[0])
                well_id = m_well.group(1) if m_well else parts[0]
                device_name = parts[1]
                controller_brand, controller_type = classify_device_type(device_name)
            else:
                well_id = f"EQ_{p_idx:02d}"
                device_name = disp_val
                controller_brand, controller_type = classify_device_type(device_name)
        else:
            well_id = f"EQ_{p_idx:02d}"

        cd_map = {
            o.custom_data: _clean_val(o.data_source)
            for o in pozo_groups[p_idx]
            if o.custom_data
        }

        pump = PumpRecord(
            pozo_index=p_idx,
            pozo_label=f"Equipo {p_idx}",
            well_id=well_id,
            pump_code=pozo_val,
            battery=bat_val,
            device_name=device_name,
            controller_brand=controller_brand,
            controller_type=controller_type,
            has_pt=pt_val,
            has_tke=tke_val,
            has_tkq=tkq_val,
            has_sam=sam_val,
            is_exp=exp_val,
            is_active=is_active,
            layer=selected_layer,
            custom_data_map=cd_map,
        )
        pumps.append(pump)

    # Exclude x=0 and template spares
    real_pumps = [p for p in pumps if p.is_active]
    for idx_num, p in enumerate(real_pumps, start=1):
        p.pozo_index = idx_num
        p.pozo_label = f"Equipo {idx_num}"

    disp_name = path.stem
    derived_sheet = sheet_name
    if not derived_sheet:
        m_area = re.search(r"(?:equipos_|pantalla_|display_|area_)([A-Za-z0-9]+)", disp_name, re.IGNORECASE)
        derived_sheet = m_area.group(1) if m_area else disp_name

    return GdfSurveyResult(
        gdf_path=path,
        display_name=disp_name,
        sheet_name=derived_sheet,
        layer_name=selected_layer,
        objects=all_objects,
        pumps=real_pumps,
    )
