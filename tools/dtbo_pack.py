#!/usr/bin/env python3
"""Pack DTBO blobs while preserving IDs/revisions from an extracted manifest."""

from __future__ import annotations

import argparse
import json
import pathlib
import struct
import sys

MAGIC = 0xD7B7AB1E
HEADER = struct.Struct(">8I")
ENTRY = struct.Struct(">8I")


def pack(template: dict[str, object], blobs: list[bytes]) -> bytes:
    entries = template.get("entries")
    if not isinstance(entries, list) or len(entries) != len(blobs):
        raise ValueError("el número de DTBO no coincide con el manifiesto")
    header_size = int(template.get("header_size", HEADER.size))
    entry_size = int(template.get("entry_size", ENTRY.size))
    page_size = int(template.get("page_size", 4096))
    version = int(template.get("version", 0))
    if header_size < HEADER.size or entry_size < ENTRY.size:
        raise ValueError("tamaños de cabecera/entrada DTBO inválidos")
    entries_offset = header_size
    payload_offset = entries_offset + entry_size * len(entries)
    total_size = payload_offset + sum(map(len, blobs))
    output = bytearray(total_size)
    HEADER.pack_into(
        output, 0, MAGIC, total_size, header_size, entry_size, len(entries),
        entries_offset, page_size, version,
    )
    current = payload_offset
    for index, (metadata, blob) in enumerate(zip(entries, blobs)):
        if not isinstance(metadata, dict):
            raise ValueError(f"metadatos inválidos en entrada {index}")
        custom = metadata.get("custom", [0, 0, 0, 0])
        if not isinstance(custom, list) or len(custom) != 4:
            raise ValueError(f"custom inválido en entrada {index}")
        ENTRY.pack_into(
            output, entries_offset + index * entry_size,
            len(blob), current, int(metadata.get("id", 0)),
            int(metadata.get("rev", 0)), *(int(value) for value in custom),
        )
        output[current:current + len(blob)] = blob
        current += len(blob)
    return bytes(output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    parser.add_argument("dtbo", nargs="+", type=pathlib.Path)
    args = parser.parse_args()
    template = json.loads(args.template.read_text(encoding="utf-8"))
    image = pack(template, [path.read_bytes() for path in args.dtbo])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(image)
    print(f"{args.output}: {len(args.dtbo)} overlays, {len(image)} bytes")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError, struct.error) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
