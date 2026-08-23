#!/usr/bin/env python3
"""Inspect Android boot v3/v4, vendor_boot v3/v4 and AVB footer sizes."""

from __future__ import annotations

import argparse
import json
import pathlib
import struct
import sys

BOOT_MAGIC = b"ANDROID!"
VENDOR_BOOT_MAGIC = b"VNDRBOOT"
AVB_FOOTER_MAGIC = b"AVBf"
BOOT_HEADER_MIN = {3: 1580, 4: 1584}
VENDOR_BOOT_HEADER_MIN = {3: 2112, 4: 2128}


def align(value: int, page_size: int) -> int:
    return (value + page_size - 1) // page_size * page_size


def compression_name(prefix: bytes) -> str:
    signatures = (
        (b"\x02\x21\x4c\x18", "lz4-legacy"),
        (b"\x04\x22\x4d\x18", "lz4-frame"),
        (b"\x1f\x8b", "gzip"),
        (b"\xfd7zXZ\x00", "xz"),
        (b"070701", "cpio-newc"),
    )
    for magic, name in signatures:
        if prefix.startswith(magic):
            return name
    return "unknown"


def parse_avb_footer(data: bytes) -> dict[str, int] | None:
    if len(data) < 64 or data[-64:-60] != AVB_FOOTER_MAGIC:
        return None
    major, minor = struct.unpack_from(">II", data, len(data) - 60)
    original_size, vbmeta_offset, vbmeta_size = struct.unpack_from(
        ">QQQ", data, len(data) - 52
    )
    footer_offset = len(data) - 64
    if major != 1 or original_size > len(data):
        raise ValueError("pie AVB con versión o tamaño original incoherente")
    if (
        original_size > vbmeta_offset
        or vbmeta_size == 0
        or vbmeta_offset > footer_offset
        or vbmeta_size > footer_offset - vbmeta_offset
    ):
        raise ValueError("rango VBMeta fuera de la imagen")
    return {
        "version_major": major,
        "version_minor": minor,
        "original_image_size": original_size,
        "vbmeta_offset": vbmeta_offset,
        "vbmeta_size": vbmeta_size,
        "partition_image_size": len(data),
        "partition_slack": len(data) - original_size,
    }


def parse_boot(data: bytes) -> dict[str, object]:
    if len(data) < 44:
        raise ValueError("cabecera boot truncada")
    kernel_size, ramdisk_size, os_version, header_size = struct.unpack_from(
        "<IIII", data, 8
    )
    header_version = struct.unpack_from("<I", data, 40)[0]
    if header_version not in (3, 4):
        raise ValueError(f"boot header v{header_version} no soportado")
    if header_size < BOOT_HEADER_MIN[header_version] or header_size > len(data):
        raise ValueError("header_size boot menor que la cabecera fija o truncado")
    page_size = 4096
    kernel_offset = align(header_size, page_size)
    ramdisk_offset = align(kernel_offset + kernel_size, page_size)
    if ramdisk_offset + ramdisk_size > len(data):
        raise ValueError("payload boot fuera de los límites de la imagen")
    result: dict[str, object] = {
        "kind": "boot",
        "header_version": header_version,
        "header_size": header_size,
        "page_size": page_size,
        "kernel_size": kernel_size,
        "kernel_offset": kernel_offset,
        "ramdisk_size": ramdisk_size,
        "ramdisk_offset": ramdisk_offset,
        "ramdisk_compression": compression_name(
            data[ramdisk_offset:ramdisk_offset + min(ramdisk_size, 16)]
        ) if ramdisk_size else "none",
        "os_version_raw": os_version,
    }
    if header_version == 4 and header_size >= 1584:
        result["boot_signature_size"] = struct.unpack_from("<I", data, 1580)[0]
    return result


def parse_vendor_boot(data: bytes) -> dict[str, object]:
    if len(data) < 2112:
        raise ValueError("cabecera vendor_boot truncada")
    header_version, page_size = struct.unpack_from("<II", data, 8)
    if header_version not in (3, 4) or page_size == 0:
        raise ValueError("versión o page size de vendor_boot no soportados")
    vendor_ramdisk_size = struct.unpack_from("<I", data, 24)[0]
    header_size, dtb_size = struct.unpack_from("<II", data, 2096)
    if (
        header_size < VENDOR_BOOT_HEADER_MIN[header_version]
        or header_size > len(data)
    ):
        raise ValueError("header_size vendor_boot menor que la cabecera fija o truncado")
    vendor_ramdisk_offset = align(header_size, page_size)
    dtb_offset = align(vendor_ramdisk_offset + vendor_ramdisk_size, page_size)
    if dtb_offset + dtb_size > len(data):
        raise ValueError("payload vendor_boot fuera de los límites de la imagen")
    result: dict[str, object] = {
        "kind": "vendor_boot",
        "header_version": header_version,
        "header_size": header_size,
        "page_size": page_size,
        "vendor_ramdisk_size": vendor_ramdisk_size,
        "vendor_ramdisk_offset": vendor_ramdisk_offset,
        "vendor_ramdisk_compression": compression_name(
            data[vendor_ramdisk_offset:vendor_ramdisk_offset + min(vendor_ramdisk_size, 16)]
        ) if vendor_ramdisk_size else "none",
        "dtb_size": dtb_size,
        "dtb_offset": dtb_offset,
    }
    if header_version == 4:
        if len(data) < 2128:
            raise ValueError("extensión vendor_boot v4 truncada")
        table_size, entry_count, entry_size, bootconfig_size = struct.unpack_from(
            "<IIII", data, 2112
        )
        result.update({
            "vendor_ramdisk_table_size": table_size,
            "vendor_ramdisk_table_entry_count": entry_count,
            "vendor_ramdisk_table_entry_size": entry_size,
            "bootconfig_size": bootconfig_size,
        })
        if entry_count and entry_size == 0:
            raise ValueError("tabla vendor ramdisk con entradas de tamaño cero")
        if entry_count * entry_size > table_size:
            raise ValueError("tabla vendor ramdisk menor que sus entradas")
        table_offset = align(dtb_offset + dtb_size, page_size)
        bootconfig_offset = align(table_offset + table_size, page_size)
        if bootconfig_offset + bootconfig_size > len(data):
            raise ValueError("tabla/bootconfig vendor_boot fuera de la imagen")
        result.update({
            "vendor_ramdisk_table_offset": table_offset,
            "bootconfig_offset": bootconfig_offset,
        })
    return result


def inspect(path: pathlib.Path) -> dict[str, object]:
    data = path.read_bytes()
    if data.startswith(BOOT_MAGIC):
        result = parse_boot(data)
    elif data.startswith(VENDOR_BOOT_MAGIC):
        result = parse_vendor_boot(data)
    else:
        raise ValueError("magic desconocido: no es boot/init_boot/vendor_boot")
    result["path"] = str(path)
    result["file_size"] = len(data)
    result["avb_footer"] = parse_avb_footer(data)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", nargs="+", type=pathlib.Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    reports = [inspect(path) for path in args.images]
    if args.json:
        print(json.dumps(reports, indent=2))
    else:
        for report in reports:
            print(f"{report['path']}: {report['kind']} v{report['header_version']}")
            for key, value in report.items():
                if key not in {"path", "kind", "header_version", "avb_footer"}:
                    print(f"  {key}: {value}")
            footer = report["avb_footer"]
            if footer:
                print("  avb_footer:")
                for key, value in footer.items():
                    print(f"    {key}: {value}")
            else:
                print("  avb_footer: none")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, struct.error) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
