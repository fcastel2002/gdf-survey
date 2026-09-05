"""Generic GDF Layer and Equipment/Object Survey extraction engine."""

from __future__ import annotations

import re
from collections import OrderedDict
from pathlib import Path
from typing import Sequence

from graphworx32_gdf_parser import parse_gdf
from graphworx32_gdf_parser.screen import clean_expression

from gdf_survey.models import (
    EquipmentRecord,
    GdfSurveyResult,
    ScreenObjectRecord,
    extract_device_info,
)

_clean_val = clean_expression


def extract_gdf_survey(
    gdf_path: str | Path,
    layer_target: str = "1",
    sheet_name: str | None = None,
    root_name_pattern: str | None = None,
    root_custom_data: str | None = None,
    custom_data_filter: Sequence[str] | None = None,
    flat: bool = False,
) -> GdfSurveyResult:
    """Extract and consolidate SCADA equipment, dynamic objects, and custom data from GDF.

    Args:
        gdf_path: Path to the GraphWorX32 .gdf file.
        layer_target: Layer symbol or number to inspect (e.g. "1").
        sheet_name: Custom sheet/display name for reporting.
        root_name_pattern: Regex pattern with capture group 1 to group objects by root name.
        root_custom_data: Custom data key used to anchor root entities (e.g. "<<tag>>").
        custom_data_filter: Optional sequence of custom data keys to include in report.
        flat: If True, each visual/dynamic object is treated individually without grouping.
    """
    path = Path(gdf_path).resolve(strict=True)

    parsed = parse_gdf(path, profiles=("screen",), layer_target=layer_target)
    if parsed.document is None:
        errors = [d.message for d in parsed.diagnostics if d.severity == "error"]
        details = "; ".join(errors) if errors else "input could not be inspected"
        raise ValueError(f"Failed to parse GDF {path.name}: {details}")

    derived_sheet = sheet_name or path.stem
    screen = parsed.document.screen
    if screen is None or not screen.layers:
        return GdfSurveyResult(
            gdf_path=path,
            display_name=path.stem,
            sheet_name=derived_sheet,
            layer_name=layer_target,
            objects=[],
            items=[],
            discovered_custom_data_keys=[],
        )

    selected_layer = screen.selected_layer or layer_target

    all_objects: list[ScreenObjectRecord] = []
    discovered_keys_set: set[str] = set()

    # Strategy 1: Flat mode (1 record per raw dynamic object)
    if flat:
        items: list[EquipmentRecord] = []
        for idx, raw in enumerate(screen.objects, start=1):
            clean_source = _clean_val(raw.data_source)
            rec = ScreenObjectRecord(
                index=raw.index,
                root_id=raw.object_name,
                object_name=raw.object_name,
                custom_data=raw.custom_data,
                data_source=clean_source,
                dynamic_type=raw.dynamic_type,
                layer=selected_layer,
                description=raw.description,
            )
            all_objects.append(rec)

            cd_map: dict[str, str] = {}
            if raw.custom_data:
                cd_map[raw.custom_data] = clean_source
                discovered_keys_set.add(raw.custom_data)

            dev_name, ctrl_type = extract_device_info(clean_source)
            is_active = bool(clean_source and clean_source != "x=0")

            eq = EquipmentRecord(
                index=idx,
                root_id=raw.object_name,
                label=raw.object_name,
                device_name=dev_name,
                controller_type=ctrl_type,
                primary_source=clean_source,
                is_active=is_active,
                layer=selected_layer,
                custom_data=cd_map,
                objects=[rec],
            )
            items.append(eq)

    # Strategy 2: Grouping mode (grouping by root name pattern or root custom data)
    else:
        # Determine effective regex pattern
        pattern = root_name_pattern or r"^([A-Za-z0-9_-]+?)(?:_|\.|$)"

        # Pre-pass: if root_custom_data is specified, find anchor prefixes
        anchor_prefixes: set[str] = set()
        if root_custom_data:
            for raw in screen.objects:
                if raw.custom_data == root_custom_data:
                    m = re.search(pattern, raw.object_name)
                    prefix = m.group(1) if m and m.groups() else (m.group(0) if m else raw.object_name)
                    anchor_prefixes.add(prefix)

        # Build object records and group them
        groups: OrderedDict[str, list[ScreenObjectRecord]] = OrderedDict()

        for raw in screen.objects:
            m = re.search(pattern, raw.object_name)
            root_key = m.group(1) if m and m.groups() else (m.group(0) if m else raw.object_name)

            rec = ScreenObjectRecord(
                index=raw.index,
                root_id=root_key,
                object_name=raw.object_name,
                custom_data=raw.custom_data,
                data_source=_clean_val(raw.data_source),
                dynamic_type=raw.dynamic_type,
                layer=selected_layer,
                description=raw.description,
            )
            all_objects.append(rec)
            groups.setdefault(root_key, []).append(rec)

        items = []
        for idx, (root_key, grp_objects) in enumerate(groups.items(), start=1):
            cd_map = {}
            for o in grp_objects:
                if o.custom_data:
                    cd_map[o.custom_data] = o.data_source
                    discovered_keys_set.add(o.custom_data)

            # Determine primary data source
            primary_source = ""
            if root_custom_data and root_custom_data in cd_map:
                primary_source = cd_map[root_custom_data]
            else:
                for pref in ("<<dispositivo>>", "<<device>>", "<<tag>>", "<<source>>", "<<name>>"):
                    if pref in cd_map:
                        primary_source = cd_map[pref]
                        break
                if not primary_source:
                    for o in grp_objects:
                        if o.data_source and o.data_source != "x=0":
                            primary_source = o.data_source
                            break

            dev_name, ctrl_type = extract_device_info(primary_source)

            # Active check
            is_active = bool(
                primary_source
                and primary_source != "x=0"
                and not re.search(r"(?:item|disp)\d+_(?:disp|item)\d+", primary_source, re.IGNORECASE)
            )

            eq = EquipmentRecord(
                index=idx,
                root_id=root_key,
                label=root_key,
                device_name=dev_name,
                controller_type=ctrl_type,
                primary_source=primary_source,
                is_active=is_active,
                layer=selected_layer,
                custom_data=cd_map,
                objects=grp_objects,
            )
            items.append(eq)

    # Filter custom data keys if specified
    all_discovered = sorted(discovered_keys_set)
    if custom_data_filter:
        allowed = set(custom_data_filter)
        final_keys = [k for k in all_discovered if k in allowed]
        for it in items:
            it.custom_data = {k: v for k, v in it.custom_data.items() if k in allowed}
    else:
        final_keys = all_discovered

    return GdfSurveyResult(
        gdf_path=path,
        display_name=path.stem,
        sheet_name=derived_sheet,
        layer_name=selected_layer,
        objects=all_objects,
        items=items,
        discovered_custom_data_keys=final_keys,
    )
