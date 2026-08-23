#!/usr/bin/env python3
"""Inspect and extract a complete ZIP archive without unsafe materialisation.

This is deliberately a host-only helper for downloaded source archives.  The
archive path is always supplied explicitly; the helper never searches a
directory and refuses paths whose final component ends in ``.part``.  Before
anything is published it validates every central-directory entry, consumes
every member (thereby checking its CRC), and calculates SHA-256 digests.

Only regular files with canonical, relative POSIX names are accepted.  ZIP
directories, symbolic links, device/fifo entries, duplicate names (including
case-folded aliases), encrypted members, path traversal, and unreasonable
member counts/sizes/compression ratios are rejected.

The ``extract`` command requires a new destination directory.  Members are
written below a private staging directory and the completed directory is
published with one rename, so a failed validation leaves no destination and
an existing destination can never be overwritten.

Examples::

    python3 tools/safe_zip_ingest.py inspect ~/Downloads/osrc.zip
    python3 tools/safe_zip_ingest.py extract ~/Downloads/osrc.zip artifacts/osrc

No ``.part`` file is opened or read.  Keep this helper separate from any
download process and invoke it only after the browser has renamed the
completed ZIP.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as _datetime
import hashlib
import json
import os
import pathlib
import shutil
import stat
import tempfile
import unicodedata
import zipfile
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any


CHUNK_SIZE = 1024 * 1024
DEFAULT_MAX_MEMBERS = 100_000
DEFAULT_MAX_ENTRY_SIZE = 8 * 1024**3
DEFAULT_MAX_TOTAL_SIZE = 64 * 1024**3
DEFAULT_MAX_COMPRESSION_RATIO = 1_000.0
MANIFEST_NAME = ".safe-zip-manifest.json"

_COMPRESSION_NAMES = {
    zipfile.ZIP_STORED: "stored",
    zipfile.ZIP_DEFLATED: "deflated",
    zipfile.ZIP_BZIP2: "bzip2",
    zipfile.ZIP_LZMA: "lzma",
}


class ZipSafetyError(RuntimeError):
    """An archive or extraction destination failed a safety check."""


@dataclass(frozen=True)
class _FileSnapshot:
    device: int
    inode: int
    size: int
    mtime_ns: int


@dataclass(frozen=True)
class Limits:
    max_members: int = DEFAULT_MAX_MEMBERS
    max_entry_size: int = DEFAULT_MAX_ENTRY_SIZE
    max_total_size: int = DEFAULT_MAX_TOTAL_SIZE
    max_compression_ratio: float = DEFAULT_MAX_COMPRESSION_RATIO

    def as_dict(self) -> dict[str, int | float]:
        return {
            "max_members": self.max_members,
            "max_entry_size": self.max_entry_size,
            "max_total_size": self.max_total_size,
            "max_compression_ratio": self.max_compression_ratio,
        }


def _snapshot(st: os.stat_result) -> _FileSnapshot:
    return _FileSnapshot(
        device=st.st_dev,
        inode=st.st_ino,
        size=st.st_size,
        mtime_ns=st.st_mtime_ns,
    )


def _archive_label(path: pathlib.Path) -> str:
    return os.path.abspath(os.fspath(path))


def _reject_part_name(path: pathlib.Path) -> None:
    """Reject a browser's incomplete download before touching the path."""

    if path.name.casefold().endswith(".part"):
        raise ZipSafetyError(
            f"no se abre un archivo de descarga incompleto (.part): {path}"
        )


def _open_regular_archive(
    path: pathlib.Path,
) -> contextlib.AbstractContextManager[tuple[Any, _FileSnapshot]]:
    """Open *path* by descriptor, refusing symlink/non-regular inputs.

    The descriptor is retained throughout the ZIP pass.  The final path and
    descriptor identities are checked again when the context closes, which
    catches a download process replacing or modifying the archive mid-read.
    """

    @contextlib.contextmanager
    def _opened() -> Iterator[tuple[Any, _FileSnapshot]]:
        _reject_part_name(path)
        try:
            before = os.lstat(path)
        except FileNotFoundError as error:
            raise ZipSafetyError(f"no existe el ZIP indicado: {path}") from error
        except OSError as error:
            raise ZipSafetyError(f"no se puede inspeccionar el ZIP: {path}: {error}") from error

        if stat.S_ISLNK(before.st_mode):
            raise ZipSafetyError(f"el ZIP indicado es un enlace simbólico: {path}")
        if not stat.S_ISREG(before.st_mode):
            raise ZipSafetyError(f"el ZIP indicado no es un archivo regular: {path}")
        if before.st_size <= 0:
            raise ZipSafetyError(f"el ZIP indicado está vacío: {path}")

        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(path, flags)
        except OSError as error:
            raise ZipSafetyError(f"no se puede abrir el ZIP: {path}: {error}") from error

        stream = None
        snapshot = _snapshot(before)
        try:
            try:
                opened = os.fstat(descriptor)
            except OSError as error:
                raise ZipSafetyError(f"no se puede verificar el ZIP abierto: {path}") from error
            if not stat.S_ISREG(opened.st_mode) or _snapshot(opened) != snapshot:
                raise ZipSafetyError(f"el ZIP cambió mientras se abría: {path}")
            stream = os.fdopen(descriptor, "rb")
            descriptor = -1
            yield stream, snapshot
        finally:
            if stream is not None:
                try:
                    stream.close()
                finally:
                    pass
            elif descriptor >= 0:
                os.close(descriptor)

            try:
                after_fd = os.stat(path, follow_symlinks=False)
            except OSError as error:
                raise ZipSafetyError(f"el ZIP desapareció o cambió: {path}") from error
            if stat.S_ISLNK(after_fd.st_mode) or _snapshot(after_fd) != snapshot:
                raise ZipSafetyError(
                    f"el ZIP cambió durante la validación; vuelve a intentar con la descarga completa: {path}"
                )

    return _opened()


def _assert_limits(limits: Limits) -> None:
    if limits.max_members <= 0:
        raise ZipSafetyError("--max-members debe ser positivo")
    if limits.max_entry_size <= 0:
        raise ZipSafetyError("--max-entry-size debe ser positivo")
    if limits.max_total_size <= 0:
        raise ZipSafetyError("--max-total-size debe ser positivo")
    if limits.max_compression_ratio <= 0:
        raise ZipSafetyError("--max-compression-ratio debe ser positivo")


def _canonical_name(name: str) -> str:
    # NFC makes aliases predictable on macOS; case-folding prevents a ZIP
    # extracted on a case-insensitive host from colliding with itself.
    return unicodedata.normalize("NFC", name).casefold()


def _member_mode(info: zipfile.ZipInfo) -> int:
    return (info.external_attr >> 16) & 0xFFFF


def _member_name(
    info: zipfile.ZipInfo,
    seen: set[str],
    seen_prefixes: set[str],
) -> str:
    name = info.filename
    if not isinstance(name, str) or not name:
        raise ZipSafetyError("entrada ZIP sin nombre")
    if "\x00" in name:
        raise ZipSafetyError(f"nombre ZIP con NUL: {name!r}")
    if any(ord(character) < 0x20 or ord(character) == 0x7F for character in name):
        raise ZipSafetyError(f"nombre ZIP con carácter de control: {name!r}")
    # Backslashes and drive prefixes are rejected even on POSIX so the same
    # manifest cannot become a traversal when consumed on Windows.
    if "\\" in name or PureWindowsPath(name).drive:
        raise ZipSafetyError(f"nombre ZIP no portable o absoluto: {name!r}")
    if name.startswith("/") or PurePosixPath(name).is_absolute():
        raise ZipSafetyError(f"ruta absoluta dentro del ZIP: {name!r}")
    if info.is_dir() or name.endswith("/"):
        raise ZipSafetyError(f"entrada ZIP no regular (directorio): {name!r}")

    parts = name.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ZipSafetyError(f"ruta no canónica dentro del ZIP: {name!r}")
    if ":" in name:
        raise ZipSafetyError(f"nombre ZIP no portable: {name!r}")
    if len(name.encode("utf-8")) > 4096:
        raise ZipSafetyError(f"nombre ZIP demasiado largo: {name!r}")

    mode = _member_mode(info)
    kind = stat.S_IFMT(mode)
    if kind and kind != stat.S_IFREG:
        kind_name = stat.filemode(mode) if mode else "tipo desconocido"
        raise ZipSafetyError(f"entrada ZIP no regular ({kind_name}): {name!r}")
    # DOS archives carry the directory bit in the low external-attribute
    # byte.  A regular file with that bit is not safe to materialise.
    if info.create_system == 0 and (info.external_attr & 0x10):
        raise ZipSafetyError(f"entrada ZIP no regular (atributo DOS): {name!r}")
    if info.flag_bits & 0x1:
        raise ZipSafetyError(f"entrada ZIP cifrada no admitida: {name!r}")
    if info.compress_type not in _COMPRESSION_NAMES:
        raise ZipSafetyError(
            f"método de compresión ZIP no admitido ({info.compress_type}): {name!r}"
        )

    canonical = _canonical_name(name)
    if canonical == _canonical_name(MANIFEST_NAME):
        raise ZipSafetyError(
            f"la entrada ZIP reserva el nombre de manifiesto: {name!r}"
        )
    if canonical in seen:
        raise ZipSafetyError(f"entradas ZIP duplicadas o alias de nombre: {name!r}")
    canonical_parts = canonical.split("/")
    if any(
        "/".join(canonical_parts[:index]) in seen
        for index in range(1, len(canonical_parts))
    ) or canonical in seen_prefixes:
        raise ZipSafetyError(
            f"entradas ZIP con rutas que colisionan: {name!r}"
        )
    seen.add(canonical)
    seen_prefixes.update(
        "/".join(canonical_parts[:index])
        for index in range(1, len(canonical_parts) + 1)
    )
    return name


def _validate_info_sizes(
    info: zipfile.ZipInfo,
    name: str,
    total_size: int,
    limits: Limits,
) -> int:
    if info.file_size < 0 or info.compress_size < 0:
        raise ZipSafetyError(f"tamaño ZIP inválido: {name!r}")
    if info.file_size > limits.max_entry_size:
        raise ZipSafetyError(
            f"entrada ZIP demasiado grande ({info.file_size} bytes): {name!r}"
        )
    new_total = total_size + info.file_size
    if new_total > limits.max_total_size:
        raise ZipSafetyError(
            f"tamaño ZIP descomprimido total demasiado grande ({new_total} bytes)"
        )
    if info.file_size and info.compress_size == 0:
        raise ZipSafetyError(f"entrada ZIP con ratio de compresión infinito: {name!r}")
    ratio = info.file_size / max(info.compress_size, 1)
    if ratio > limits.max_compression_ratio:
        raise ZipSafetyError(
            f"ratio de compresión ZIP sospechoso ({ratio:.1f}): {name!r}"
        )
    return new_total


def _entry_timestamp(info: zipfile.ZipInfo) -> str:
    try:
        value = _datetime.datetime(*info.date_time, tzinfo=_datetime.timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return "invalid"
    return value.isoformat()


def _metadata_without_hash(
    info: zipfile.ZipInfo,
    name: str,
) -> dict[str, Any]:
    mode = _member_mode(info)
    return {
        "name": name,
        "size": info.file_size,
        "compressed_size": info.compress_size,
        "crc32": f"{info.CRC & 0xFFFFFFFF:08x}",
        "sha256": None,
        "compression": _COMPRESSION_NAMES[info.compress_type],
        "date_time": _entry_timestamp(info),
        "create_system": info.create_system,
        "external_attr": info.external_attr,
        "mode": mode or None,
    }


def _consume_member(
    archive: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    destination: pathlib.Path | None = None,
) -> str:
    digest = hashlib.sha256()
    total = 0
    output = None
    try:
        if destination is not None:
            destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            flags |= getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(destination, flags, 0o600)
            output = os.fdopen(descriptor, "wb")
        with archive.open(info, "r") as source:
            while True:
                chunk = source.read(CHUNK_SIZE)
                if not chunk:
                    break
                total += len(chunk)
                if total > info.file_size:
                    raise ZipSafetyError(f"datos de más en la entrada ZIP: {info.filename!r}")
                digest.update(chunk)
                if output is not None:
                    output.write(chunk)
        if total != info.file_size:
            raise ZipSafetyError(
                f"tamaño descomprimido incompleto ({total}/{info.file_size}): {info.filename!r}"
            )
        if output is not None:
            output.flush()
            os.fsync(output.fileno())
        return digest.hexdigest()
    except (OSError, EOFError, RuntimeError, zipfile.BadZipFile) as error:
        if isinstance(error, ZipSafetyError):
            raise
        raise ZipSafetyError(f"no se pudo leer la entrada ZIP {info.filename!r}: {error}") from error
    finally:
        if output is not None:
            output.close()


def _checked_infos(
    archive: zipfile.ZipFile,
    limits: Limits,
) -> tuple[list[tuple[zipfile.ZipInfo, str, dict[str, Any]]], int, int]:
    try:
        infos = archive.infolist()
    except (OSError, EOFError, RuntimeError, zipfile.BadZipFile) as error:
        raise ZipSafetyError(f"directorio central ZIP inválido: {error}") from error
    if len(infos) > limits.max_members:
        raise ZipSafetyError(
            f"demasiadas entradas ZIP ({len(infos)} > {limits.max_members})"
        )

    seen: set[str] = set()
    seen_prefixes: set[str] = set()
    total_size = 0
    total_compressed = 0
    checked: list[tuple[zipfile.ZipInfo, str, dict[str, Any]]] = []
    for info in infos:
        name = _member_name(info, seen, seen_prefixes)
        total_size = _validate_info_sizes(info, name, total_size, limits)
        total_compressed += info.compress_size
        checked.append((info, name, _metadata_without_hash(info, name)))
    return checked, total_size, total_compressed


def _hash_archive(stream: Any) -> str:
    digest = hashlib.sha256()
    try:
        stream.seek(0)
        while True:
            chunk = stream.read(CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
        stream.seek(0)
    except OSError as error:
        raise ZipSafetyError(f"no se pudo calcular el hash del ZIP: {error}") from error
    return digest.hexdigest()


def _base_report(
    path: pathlib.Path,
    limits: Limits,
) -> dict[str, Any]:
    _assert_limits(limits)
    with _open_regular_archive(path) as (stream, snapshot):
        archive_sha256 = _hash_archive(stream)
        try:
            with zipfile.ZipFile(stream, mode="r") as archive:
                checked, total_size, total_compressed = _checked_infos(archive, limits)
                members: list[dict[str, Any]] = []
                for info, _name, metadata in checked:
                    metadata = dict(metadata)
                    metadata["sha256"] = _consume_member(archive, info)
                    members.append(metadata)
        except (OSError, EOFError, RuntimeError, zipfile.BadZipFile, NotImplementedError) as error:
            raise ZipSafetyError(f"ZIP incompleto o ilegible: {error}") from error

    return {
        "format": "safe-zip-ingest/v1",
        "archive": {
            "path": _archive_label(path),
            "size": snapshot.size,
            "sha256": archive_sha256,
        },
        "limits": limits.as_dict(),
        "totals": {
            "members": len(members),
            "uncompressed_size": total_size,
            "compressed_size": total_compressed,
        },
        "members": members,
    }


def _destination(path: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
    if not os.fspath(path):
        raise ZipSafetyError("el destino es obligatorio y debe ser explícito")
    if path.name in {"", ".", ".."}:
        raise ZipSafetyError("destino de extracción no válido")
    try:
        if os.path.lexists(path):
            raise ZipSafetyError(
                f"el destino ya existe; se rechaza para no sobrescribir: {path}"
            )
        parent = path.parent
        parent_real = pathlib.Path(os.path.realpath(parent))
        if not parent_real.is_dir():
            raise ZipSafetyError(f"el padre del destino no es un directorio: {parent}")
    except OSError as error:
        raise ZipSafetyError(f"no se puede comprobar el destino {path}: {error}") from error
    return path, parent_real


def _fsync_directory(path: pathlib.Path) -> None:
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


def _extract_archive(
    path: pathlib.Path,
    destination: pathlib.Path,
    parent: pathlib.Path,
    expected: dict[str, Any],
    limits: Limits,
) -> dict[str, Any]:
    stage: pathlib.Path | None = None
    expected_members = {member["name"]: member for member in expected["members"]}
    try:
        with _open_regular_archive(path) as (stream, _snapshot_value):
            actual_archive_sha256 = _hash_archive(stream)
            if actual_archive_sha256 != expected["archive"]["sha256"]:
                raise ZipSafetyError("el ZIP cambió entre validación y extracción")
            try:
                with zipfile.ZipFile(stream, mode="r") as archive:
                    checked, total_size, total_compressed = _checked_infos(archive, limits)
                    actual_names = [name for _info, name, _metadata in checked]
                    if actual_names != [member["name"] for member in expected["members"]]:
                        raise ZipSafetyError("el ZIP cambió entre validación y extracción")
                    stage = pathlib.Path(
                        tempfile.mkdtemp(prefix=f".{destination.name}.safe-zip-", dir=parent)
                    )
                    for info, name, _metadata in checked:
                        target = stage / PurePosixPath(name)
                        actual_sha256 = _consume_member(archive, info, target)
                        if actual_sha256 != expected_members[name]["sha256"]:
                            raise ZipSafetyError(
                                f"el hash de la entrada cambió durante la extracción: {name!r}"
                            )

                    report = dict(expected)
                    report["output"] = _archive_label(destination)
                    report["manifest"] = MANIFEST_NAME
                    report["totals"] = {
                        "members": len(checked),
                        "uncompressed_size": total_size,
                        "compressed_size": total_compressed,
                    }
                    manifest_path = stage / MANIFEST_NAME
                    manifest_path.write_text(
                        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
                        + "\n",
                        encoding="utf-8",
                    )
                    os.chmod(manifest_path, 0o600)
                    _fsync_directory(stage)
            except (OSError, EOFError, RuntimeError, zipfile.BadZipFile, NotImplementedError) as error:
                if isinstance(error, ZipSafetyError):
                    raise
                raise ZipSafetyError(f"ZIP incompleto o ilegible: {error}") from error

        # Check immediately before publication.  os.rename does not follow a
        # destination symlink, and the explicit check prevents replacing a
        # destination created by another process during this run in normal
        # operation.  Any failure still removes our private stage.
        if os.path.lexists(destination):
            raise ZipSafetyError(
                f"el destino apareció durante la extracción; no se sobrescribe: {destination}"
            )
        assert stage is not None
        os.rename(stage, destination)
        stage = None
        _fsync_directory(parent)
        return report
    except OSError as error:
        raise ZipSafetyError(f"no se pudo publicar la extracción: {error}") from error
    finally:
        if stage is not None:
            shutil.rmtree(stage, ignore_errors=True)


def _limits_from_args(args: argparse.Namespace) -> Limits:
    return Limits(
        max_members=args.max_members,
        max_entry_size=args.max_entry_size,
        max_total_size=args.max_total_size,
        max_compression_ratio=args.max_compression_ratio,
    )


def _add_limits(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--max-members",
        type=int,
        default=DEFAULT_MAX_MEMBERS,
        help=f"máximo de entradas (por defecto: {DEFAULT_MAX_MEMBERS})",
    )
    parser.add_argument(
        "--max-entry-size",
        type=int,
        default=DEFAULT_MAX_ENTRY_SIZE,
        help=f"máximo de bytes descomprimidos por entrada (por defecto: {DEFAULT_MAX_ENTRY_SIZE})",
    )
    parser.add_argument(
        "--max-total-size",
        type=int,
        default=DEFAULT_MAX_TOTAL_SIZE,
        help=f"máximo de bytes descomprimidos totales (por defecto: {DEFAULT_MAX_TOTAL_SIZE})",
    )
    parser.add_argument(
        "--max-compression-ratio",
        type=float,
        default=DEFAULT_MAX_COMPRESSION_RATIO,
        help=f"ratio máximo tamaño/descomprimido (por defecto: {DEFAULT_MAX_COMPRESSION_RATIO:g})",
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Valida, lista hashes y extrae ZIPs completos de forma transaccional."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    inspect_parser = commands.add_parser(
        "inspect",
        aliases=["list", "validate"],
        help="valida todos los miembros y muestra metadatos/hashes en JSON",
    )
    inspect_parser.add_argument("archive", type=pathlib.Path)
    _add_limits(inspect_parser)

    extract_parser = commands.add_parser(
        "extract",
        help="valida y publica el ZIP en un directorio nuevo",
    )
    extract_parser.add_argument("archive", type=pathlib.Path)
    extract_parser.add_argument("destination", type=pathlib.Path)
    _add_limits(extract_parser)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    limits = _limits_from_args(args)
    try:
        if args.command in {"inspect", "list", "validate"}:
            report = _base_report(args.archive, limits)
        else:
            destination, parent = _destination(args.destination)
            report = _base_report(args.archive, limits)
            report = _extract_archive(args.archive, destination, parent, report, limits)
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (ZipSafetyError, OSError, EOFError, RuntimeError, ValueError, zipfile.BadZipFile) as error:
        print(f"ZIP rechazado: {error}", file=os.sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
