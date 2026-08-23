#!/usr/bin/env python3
"""Compare DT compatible strings with exact matches in vendor and mainline code."""

from __future__ import annotations

import argparse
import collections
import pathlib
import re

COMPAT_ASSIGNMENT = re.compile(r"compatible\s*=\s*((?:\"[^\"]*\"\s*,?\s*)+);", re.S)
QUOTED = re.compile(r'"([^\"]*)"')
SOURCE_SUFFIXES = {".c", ".h", ".dts", ".dtsi", ".yaml", ".txt"}


def extract_from_dts(path: pathlib.Path) -> collections.Counter[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    result: collections.Counter[str] = collections.Counter()
    for assignment in COMPAT_ASSIGNMENT.findall(text):
        for value in QUOTED.findall(assignment):
            for compatible in value.replace("\\0", "\0").split("\0"):
                compatible = compatible.strip()
                if compatible:
                    result[compatible] += 1
    return result


def index_tree(root: pathlib.Path) -> dict[str, list[str]]:
    index: dict[str, list[str]] = collections.defaultdict(list)
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in SOURCE_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        relative = str(path.relative_to(root))
        for value in set(QUOTED.findall(text)):
            if "," in value and len(value) < 160:
                index[value].append(relative)
    return index


def esc(value: str) -> str:
    return value.replace("|", "\\|")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dts", action="append", required=True, type=pathlib.Path)
    parser.add_argument("--vendor", required=True, type=pathlib.Path)
    parser.add_argument("--mainline", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()

    counts: collections.Counter[str] = collections.Counter()
    for dts in args.dts:
        counts.update(extract_from_dts(dts))
    vendor = index_tree(args.vendor)
    mainline = index_tree(args.mainline)

    rows = []
    for compatible in sorted(counts):
        main_hits = mainline.get(compatible, [])
        vendor_hits = vendor.get(compatible, [])
        status = "exacto" if main_hits else "ausente"
        rows.append((compatible, counts[compatible], status, vendor_hits, main_hits))

    exact = sum(1 for row in rows if row[2] == "exacto")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as output:
        output.write("# Compatibles DT: downstream frente a mainline\n\n")
        output.write("Informe mecánico: una coincidencia sólo significa que la cadena aparece "
                     "en el checkout; no demuestra compatibilidad eléctrica ni funcional.\n\n")
        output.write(f"- Cadenas únicas: {len(rows)}\n")
        output.write(f"- Coincidencia textual exacta en mainline: {exact}\n")
        output.write(f"- Sin coincidencia exacta: {len(rows) - exact}\n\n")
        output.write("| compatible | usos DT | mainline | ejemplo vendor | ejemplo mainline |\n")
        output.write("|---|---:|---|---|---|\n")
        for compatible, uses, status, vendor_hits, main_hits in rows:
            output.write(
                f"| `{esc(compatible)}` | {uses} | {status} | "
                f"`{esc(vendor_hits[0]) if vendor_hits else '-'} ` | "
                f"`{esc(main_hits[0]) if main_hits else '-'} ` |\n"
            )
    print(f"{args.output}: {len(rows)} compatibles, {exact} coincidencias exactas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

