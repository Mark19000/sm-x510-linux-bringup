#!/usr/bin/env python3
"""Find and extract flattened device-tree blobs embedded in a binary image."""

from __future__ import annotations

import argparse
import json
import mmap
import pathlib
import struct
import sys

FDT_MAGIC = b"\xd0\x0d\xfe\xed"
MIN_HEADER = 40
MAX_DTB = 64 * 1024 * 1024


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=pathlib.Path)
    parser.add_argument("output", type=pathlib.Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    found: list[dict[str, int | str]] = []
    with args.image.open("rb") as stream:
        with mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as data:
            cursor = 0
            while True:
                offset = data.find(FDT_MAGIC, cursor)
                if offset < 0:
                    break
                cursor = offset + 4
                if offset + MIN_HEADER > len(data):
                    continue
                total_size = struct.unpack_from(">I", data, offset + 4)[0]
                version = struct.unpack_from(">I", data, offset + 20)[0]
                last_compatible = struct.unpack_from(">I", data, offset + 24)[0]
                if not (MIN_HEADER <= total_size <= MAX_DTB):
                    continue
                if offset + total_size > len(data) or not (1 <= version <= 17):
                    continue
                name = f"fdt-{len(found):02d}-offset-{offset:08x}.dtb"
                (args.output / name).write_bytes(data[offset:offset + total_size])
                found.append({
                    "file": name, "offset": offset, "size": total_size,
                    "version": version, "last_compatible_version": last_compatible,
                })
                print(f"{name}: offset=0x{offset:x}, size={total_size}, version={version}")
                cursor = offset + total_size

    (args.output / "manifest.json").write_text(
        json.dumps({"source": str(args.image), "fdts": found}, indent=2) + "\n",
        encoding="utf-8",
    )
    if not found:
        print("No se encontraron FDT válidos.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, struct.error) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)

