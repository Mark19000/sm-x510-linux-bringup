#!/usr/bin/env python3
"""Extrae una lista cerrada de ficheros regulares desde tar o stdin.

No materializa nombres elegidos por el archivo tar. Cada miembro solicitado
debe ser un basename normal, aparecer exactamente una vez y ser regular. Las
salidas sólo se publican después de haber validado la lista completa.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import pathlib
import shutil
import sys
import tarfile
import tempfile


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", help="tar/tar.md5 o - para stdin")
    parser.add_argument("output", type=pathlib.Path)
    parser.add_argument("members", nargs="+")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    requested = set(args.members)
    if len(requested) != len(args.members):
        raise SystemExit("la lista contiene miembros duplicados")
    for name in requested:
        if pathlib.PurePosixPath(name).name != name or name in {"", ".", ".."}:
            raise SystemExit(f"nombre de miembro no seguro: {name!r}")

    args.output.mkdir(parents=True, exist_ok=True)
    stage = pathlib.Path(tempfile.mkdtemp(prefix=".tar-extract.", dir=args.output))
    seen: set[str] = set()
    stream = sys.stdin.buffer if args.archive == "-" else open(args.archive, "rb")
    try:
        with contextlib.closing(stream) if args.archive != "-" else contextlib.nullcontext(stream):
            with tarfile.open(fileobj=stream, mode="r|*") as archive:
                for member in archive:
                    if member.name not in requested:
                        continue
                    if member.name in seen:
                        raise RuntimeError(f"miembro duplicado: {member.name}")
                    if not member.isfile():
                        raise RuntimeError(
                            f"el miembro solicitado no es regular: {member.name}"
                        )
                    source = archive.extractfile(member)
                    if source is None:
                        raise RuntimeError(f"no se pudo leer: {member.name}")
                    destination = stage / member.name
                    with source, destination.open("xb") as output:
                        shutil.copyfileobj(source, output, length=1024 * 1024)
                    if destination.stat().st_size != member.size:
                        raise RuntimeError(f"tamaño incompleto: {member.name}")
                    seen.add(member.name)

        missing = sorted(requested - seen)
        if missing:
            raise RuntimeError("faltan miembros: " + ", ".join(missing))
        for name in args.members:
            os.replace(stage / name, args.output / name)
    except (OSError, tarfile.TarError, RuntimeError) as error:
        print(f"Extracción tar rechazada: {error}", file=sys.stderr)
        return 1
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
