"""Synthetic test fixtures for gdf-survey."""

from __future__ import annotations

import io
import struct
from pathlib import Path
import pytest


def make_mfc_cstring_bytes(text: str) -> bytes:
    raw = text.encode("utf-16le")
    length = len(text)
    if length < 0xFF:
        return b"\xff\xfe\xff" + bytes([length]) + raw
    else:
        return b"\xff\xfe\xff\xff" + struct.pack("<H", length) + raw


def create_synthetic_survey_gdf(path: Path) -> Path:
    """Generate a synthetic GDF display with ObjectManager, ODynamicManager, and OPointManager."""
    # 1. ObjectManager section
    layer_name = "1-PROCESS"
    layer_cstring = make_mfc_cstring_bytes(layer_name)
    child_ids = list(range(101, 109))
    arr_chunk = b"\x83\x44\x00\x00\x00" + struct.pack("<H", len(child_ids)) + struct.pack(f"<{len(child_ids)}I", *child_ids)
    om_section = b"ObjectManager" + layer_cstring + arr_chunk + b"\x00" * 32

    # 2. ODynamicManager and 3. OPointManager objects
    # 8 items for Equipo 1
    items_data = [
        ("eq1_disp", "<<dispositivo>>", "EQ_01.CTRL_A"),
        ("eq1_well", "<<pozo>>", "TAG_101"),
        ("eq1_bat", "<<bat>>", "B-101"),
        ("eq1_pt", "<<tienept>>", "1"),
        ("eq1_tke", "<<tienetke>>", "0"),
        ("eq1_tkq", "<<tienetkq>>", "0"),
        ("eq1_sam", "<<tienesam>>", "0"),
        ("eq1_exp", "<<esexp>>", "0"),
    ]

    dm_items = bytearray()
    opm_items = bytearray()

    for i, (name, custom_data, expr) in enumerate(items_data):
        obj_id = 101 + i
        dyn_id = 501 + i

        # Prefix: dyn_id at -13, obj_id at -9
        prefix = struct.pack("<I", dyn_id) + struct.pack("<I", obj_id) + b"\x00\x00\x00\x00\x00"
        name_cs = make_mfc_cstring_bytes(name)
        desc_cs = make_mfc_cstring_bytes("Description")
        cd_cs = make_mfc_cstring_bytes(custom_data)

        dm_items += b"\x00" * 8 + prefix + name_cs + desc_cs + cd_cs

        # OPoint chunk
        expr_cs = make_mfc_cstring_bytes(f'$"{expr}"$')
        opm_chunk = struct.pack("<I", dyn_id) + b"\x98\xf0\x98\xf0" + struct.pack("<H", 0) + expr_cs
        opm_items += opm_chunk + b"\x00" * 8

    dm_section = b"ODynamicManager" + bytes(dm_items) + b"\x00" * 32
    opm_section = b"OPointManager" + bytes(opm_items) + b"\x00" * 32

    contents_payload = om_section + dm_section + opm_section

    # Write CFBF v3 file
    header = bytearray(512)
    header[0:8] = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
    header[24:26] = struct.pack("<H", 0x003E)
    header[26:28] = struct.pack("<H", 0x0003)
    header[28:30] = struct.pack("<H", 0xFFFE)
    header[30:32] = struct.pack("<H", 9)
    header[32:34] = struct.pack("<H", 6)
    header[44:48] = struct.pack("<I", 1)
    header[48:52] = struct.pack("<I", 1)
    header[56:60] = struct.pack("<I", 4096)
    header[60:64] = struct.pack("<I", 0xFFFFFFFE)
    header[64:68] = struct.pack("<I", 0)
    header[68:72] = struct.pack("<I", 0xFFFFFFFE)
    header[72:76] = struct.pack("<I", 0)
    header[76:80] = struct.pack("<I", 0)
    for k in range(1, 109):
        header[76 + k*4: 80 + k*4] = struct.pack("<I", 0xFFFFFFFF)

    # 8 sectors for 4096 bytes
    fat = bytearray(512)
    fat[0:4] = struct.pack("<I", 0xFFFFFFFD)
    fat[4:8] = struct.pack("<I", 0xFFFFFFFE)
    for s in range(2, 9):
        fat[s*4:(s+1)*4] = struct.pack("<I", s + 1)
    fat[9*4:10*4] = struct.pack("<I", 0xFFFFFFFE)
    for k in range(10, 128):
        fat[k*4:(k+1)*4] = struct.pack("<I", 0xFFFFFFFF)

    root_entry = bytearray(128)
    root_name = "Root Entry\0".encode("utf-16le")
    root_entry[0:len(root_name)] = root_name
    root_entry[64:66] = struct.pack("<H", len(root_name))
    root_entry[66] = 5
    root_entry[67] = 1
    root_entry[68:72] = struct.pack("<I", 0xFFFFFFFF)
    root_entry[72:76] = struct.pack("<I", 0xFFFFFFFF)
    root_entry[76:80] = struct.pack("<I", 1)

    contents_data = contents_payload.ljust(4096, b"\x00")
    contents_entry = bytearray(128)
    c_name = "Contents\0".encode("utf-16le")
    contents_entry[0:len(c_name)] = c_name
    contents_entry[64:66] = struct.pack("<H", len(c_name))
    contents_entry[66] = 2
    contents_entry[67] = 1
    contents_entry[68:72] = struct.pack("<I", 0xFFFFFFFF)
    contents_entry[72:76] = struct.pack("<I", 0xFFFFFFFF)
    contents_entry[76:80] = struct.pack("<I", 0xFFFFFFFF)
    contents_entry[116:120] = struct.pack("<I", 2)
    contents_entry[120:128] = struct.pack("<Q", len(contents_data))

    empty_entry = bytearray(128)
    for k in range(68, 80):
        empty_entry[k] = 0xFF

    dir_sector = root_entry + contents_entry + empty_entry + empty_entry
    cfbf_bytes = bytes(header + fat + dir_sector + contents_data)

    path.write_bytes(cfbf_bytes)
    return path


@pytest.fixture
def synthetic_gdf(tmp_path: Path) -> Path:
    return create_synthetic_survey_gdf(tmp_path / "pantalla_pozos_Planta1.gdf")
