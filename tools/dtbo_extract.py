#!/usr/bin/env python3
"""Extract entries from an Android DTBO container without external libraries."""

from __future__ import annotations

import argparse
import json
import pathlib
import struct
import sys

MAGIC = 0xD7B7AB1E
HEADER = struct.Struct(">8I")
ENTRY_PREFIX = struct.Struct(">8I")
FDT_MAGIC = 0xD00DFEED
FDT_HEADER_SIZE = 40


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=pathlib.Path)
    parser.add_argument("output", type=pathlib.Path)
    args = parser.parse_args()

    data = args.image.read_bytes()
    if len(data) < HEADER.size:
        raise SystemExit("imagen demasiado pequeña para ser DTBO")

    (magic, total_size, header_size, entry_size, entry_count,
     entries_offset, page_size, version) = HEADER.unpack_from(data)
    if magic != MAGIC:
        raise SystemExit(f"magic DTBO incorrecto: 0x{magic:08x}")
    if (
        total_size > len(data)
        or total_size < HEADER.size
        or header_size < HEADER.size
        or header_size > total_size
        or entry_size < ENTRY_PREFIX.size
        or entry_count == 0
        or page_size == 0
        or page_size & (page_size - 1)
    ):
        raise SystemExit("cabecera DTBO incoherente o truncada")
    table_end = entries_offset + entry_count * entry_size
    if entries_offset < header_size or table_end > total_size:
        raise SystemExit("tabla de entradas DTBO fuera de límites")

    manifest: dict[str, object] = {
        "source": str(args.image),
        "total_size": total_size,
        "header_size": header_size,
        "entry_size": entry_size,
        "entry_count": entry_count,
        "page_size": page_size,
        "version": version,
        "entries": [],
    }
    validated: list[tuple[str, bytes, dict[str, object], int, int]] = []
    payload_intervals: list[tuple[int, int]] = []

    for index in range(entry_count):
        offset = entries_offset + index * entry_size
        dt_size, dt_offset, ident, rev, custom0, custom1, custom2, custom3 = \
            ENTRY_PREFIX.unpack_from(data, offset)
        dt_end = dt_offset + dt_size
        if dt_size < FDT_HEADER_SIZE or dt_offset < table_end or dt_end > total_size:
            raise SystemExit(f"entrada {index} fuera de los límites del contenedor")
        blob = data[dt_offset:dt_end]
        if struct.unpack_from(">I", blob)[0] != FDT_MAGIC:
            raise SystemExit(f"entrada {index} no comienza por una cabecera FDT")
        fdt_total_size = struct.unpack_from(">I", blob, 4)[0]
        if fdt_total_size < FDT_HEADER_SIZE or fdt_total_size > dt_size:
            raise SystemExit(f"entrada {index} declara un tamaño FDT incoherente")
        for previous_start, previous_end in payload_intervals:
            if dt_offset < previous_end and previous_start < dt_end:
                raise SystemExit(f"entrada {index} solapa otro payload")
        payload_intervals.append((dt_offset, dt_end))
        name = f"overlay-{index:02d}-id-{ident:08x}-rev-{rev:08x}.dtbo"
        metadata = {
            "index": index, "file": name, "size": dt_size,
            "offset": dt_offset, "id": ident, "rev": rev,
            "custom": [custom0, custom1, custom2, custom3],
        }
        manifest["entries"].append(metadata)
        validated.append((name, blob, metadata, dt_offset, dt_end))

    args.output.mkdir(parents=True, exist_ok=True)
    for name, blob, _metadata, _start, _end in validated:
        path = args.output / name
        path.write_bytes(blob)
        index = _metadata["index"]
        dt_size = _metadata["size"]
        print(f"{index:02d}: {name} ({dt_size} bytes)")

    (args.output / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, struct.error) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
