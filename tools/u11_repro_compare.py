#!/usr/bin/env python3
"""Compara dos dist independientes y emite evidencia reproducible.

NOTA DE DEUDA TÉCNICA EN NOMBRADO:
Este script contiene 'u11' en el nombre de fichero por motivos históricos de
procedencia, pero es herramienta ACTIVA para la validación reproducible de
árboles EZE4 / U12 (referenciada en EZE4-SOURCE-MIGRATION-ASSESSMENT.md y tests).
Para EZE4, la identidad canónica del kernel stock es 5.15.189-android13-3-33478785.
Se expone un alias canónico en `tools/repro_compare.py`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path


REQUIRED = {
    "Image",
    "kernel.config",
    "Module.symvers",
    "System.map",
    "s5e8835.dtb",
    "gts9fewifi_eur_open_w00_r00.dtbo",
    "gts9fewifi_eur_open_w00_r01.dtbo",
    "gts9fewifi_eur_open_w00_r04.dtbo",
    "modules-root.tar.gz",
    "modules.order",
    "BUILD-METADATA",
    "PATCHES.sha256",
}
REQUIRED_METADATA = {
    "artifact_class": "offline-reference-only",
    "flash_authorized": "no",
    "source_release": "X510XXSBDZB4",
    "source_base": "X510XXU8DYJ4",
    "target_stock": "X510XXUCEZE4",
    "kernel_release": "5.15.189-android13-3-33478785",
    "modules": "282",
    "boot_image_created": "no",
    "avb_signature_created": "no",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inventory(directory: Path) -> tuple[dict[str, str], list[str]]:
    files: dict[str, str] = {}
    unsafe: list[str] = []
    for path in sorted(directory.rglob("*")):
        relative = str(path.relative_to(directory))
        mode = path.lstat().st_mode
        if stat.S_ISREG(mode):
            files[relative] = sha256(path)
        elif not stat.S_ISDIR(mode):
            unsafe.append(relative)
    return files, unsafe


def metadata_errors(directory: Path) -> list[str]:
    path = directory / "BUILD-METADATA"
    if not path.is_file() or path.is_symlink():
        return ["falta BUILD-METADATA regular"]
    values = {
        key: value
        for line in path.read_text(encoding="utf-8").splitlines()
        if "=" in line
        for key, value in [line.split("=", 1)]
    }
    return [
        f"{key}={values.get(key)!r}, esperado {expected!r}"
        for key, expected in REQUIRED_METADATA.items()
        if values.get(key) != expected
    ]


def compare(first: Path, second: Path) -> dict[str, object]:
    first = first.resolve()
    second = second.resolve()
    if first == second:
        raise ValueError("los dos runs deben ser directorios distintos")
    if not first.is_dir() or not second.is_dir():
        raise ValueError("ambos argumentos deben ser directorios dist existentes")
    if first.parent.name == second.parent.name:
        raise ValueError("los run-id deben ser distintos")
    first_files, unsafe_first = inventory(first)
    second_files, unsafe_second = inventory(second)
    first_metadata_errors = metadata_errors(first)
    second_metadata_errors = metadata_errors(second)
    missing_first = sorted(REQUIRED - first_files.keys())
    missing_second = sorted(REQUIRED - second_files.keys())
    only_first = sorted(first_files.keys() - second_files.keys())
    only_second = sorted(second_files.keys() - first_files.keys())
    differing = sorted(
        name for name in first_files.keys() & second_files.keys()
        if first_files[name] != second_files[name]
    )
    reproducible = not (
        missing_first or missing_second or only_first or only_second or differing
        or unsafe_first or unsafe_second or first_metadata_errors or second_metadata_errors
    )
    return {
        "schema": 1,
        "profile": "SM-X510-X510XXSBDZB4-U11-fixed-offline",
        "first_run": first.parent.name,
        "second_run": second.parent.name,
        "first_dist": str(first),
        "second_dist": str(second),
        "first_file_count": len(first_files),
        "second_file_count": len(second_files),
        "required_files": sorted(REQUIRED),
        "missing_in_first": missing_first,
        "missing_in_second": missing_second,
        "only_in_first": only_first,
        "only_in_second": only_second,
        "differing": differing,
        "unsafe_in_first": unsafe_first,
        "unsafe_in_second": unsafe_second,
        "first_metadata_errors": first_metadata_errors,
        "second_metadata_errors": second_metadata_errors,
        "reproducible": reproducible,
        "physical_write_gate": "NO-GO",
    }


def markdown(result: dict[str, object]) -> str:
    verdict = "PASS" if result["reproducible"] else "FAIL"
    lines = [
        "# Reproducibilidad del build U11 fijo",
        "",
        f"- resultado: `{verdict}`",
        f"- primer run: `{result['first_run']}` ({result['first_file_count']} ficheros)",
        f"- segundo run: `{result['second_run']}` ({result['second_file_count']} ficheros)",
        f"- escritura f\u00edsica: `{result['physical_write_gate']}`",
        "",
    ]
    for key, title in (
        ("missing_in_first", "Faltan en el primero"),
        ("missing_in_second", "Faltan en el segundo"),
        ("only_in_first", "S\u00f3lo en el primero"),
        ("only_in_second", "S\u00f3lo en el segundo"),
        ("differing", "Contenido distinto"),
        ("unsafe_in_first", "Tipos no regulares en el primero"),
        ("unsafe_in_second", "Tipos no regulares en el segundo"),
        ("first_metadata_errors", "Identidad inv\u00e1lida en el primero"),
        ("second_metadata_errors", "Identidad inv\u00e1lida en el segundo"),
    ):
        values = result[key]
        if values:
            lines.extend((f"## {title}", "", *(f"- `{value}`" for value in values), ""))
    if result["reproducible"]:
        lines.extend((
            "Todos los ficheros publicados, incluido el tar reproducible con los 282",
            "m\u00f3dulos, son id\u00e9nticos byte a byte entre dos \u00e1rboles limpios.", "",
        ))
    return "\n".join(lines)


def atomic_write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        stream.write(data)
        temporary = Path(stream.name)
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("first", type=Path)
    parser.add_argument("second", type=Path)
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = compare(args.first, args.second)
        atomic_write(args.json.resolve(), json.dumps(result, indent=2, sort_keys=True) + "\n")
        atomic_write(args.markdown.resolve(), markdown(result))
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(markdown(result), end="")
    return 0 if result["reproducible"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
