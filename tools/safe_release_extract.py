#!/usr/bin/env python3
"""Safely stage and inventory a Samsung OSRC release inside the guest.

The host wrapper copies the release archive to Lima's ext4 disk first.  This
helper is deliberately small and conservative: it accepts regular files,
directories, and only relative in-tree symlinks from ZIP/TAR archives, rejects
traversal and special files, refuses ``.part`` inputs, and never replaces an
existing output.  It also scans an already staged tree without following
symlinks so a future OSRC layout can be reviewed before a build is attempted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import posixpath
import re
import shutil
import stat
import sys
import tarfile
import zipfile
from collections.abc import Iterator


ARCHIVE_SUFFIXES = (
    ".tar.gz",
    ".tar.bz2",
    ".tar.xz",
    ".tar.zst",
    ".tar.lz4",
    ".tar.md5",
    ".tgz",
    ".tbz",
    ".tbz2",
    ".txz",
    ".tar",
)
ZIP_SUFFIXES = (".zip",)
MAX_MEMBERS = 250_000
MAX_MEMBER_BYTES = 32 * 1024 * 1024 * 1024
HEX_COMMIT = re.compile(r"\b[0-9a-fA-F]{40}\b")


class ReleaseError(RuntimeError):
    """An archive or staged release violated a safety invariant."""


def die(message: str) -> "NoReturn":
    raise ReleaseError(message)


def is_part(path: pathlib.PurePath | str) -> bool:
    return pathlib.PurePath(str(path)).name.lower().endswith(".part")


def archive_kind(path: pathlib.Path) -> str | None:
    name = path.name.lower()
    if name.endswith(ZIP_SUFFIXES):
        return "zip"
    if name.endswith(ARCHIVE_SUFFIXES):
        return "tar"
    return None


def safe_member_name(name: str) -> pathlib.PurePosixPath:
    """Return a normalized member path or reject it.

    OSRC archives are expected to use POSIX names.  Backslashes are rejected
    rather than interpreted differently on the host and in the guest.
    """

    if not name or "\\" in name or "\x00" in name:
        die(f"nombre de miembro no válido: {name!r}")
    if name.startswith("/") or name.startswith("~"):
        die(f"nombre absoluto rechazado: {name!r}")
    # GNU tar commonly emits every path as ``./foo``.  Canonicalize only
    # leading ``./`` components; a dot component in the middle remains
    # ambiguous and is rejected below.
    while name.startswith("./"):
        name = name[2:]
    if not name:
        die("nombre de miembro vacío")
    parts = name.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        # A trailing slash is a normal directory marker.  Empty path
        # components in the middle are ambiguous, so reject all of them and
        # handle the marker before this function is called.
        die(f"nombre de miembro no normalizado: {name!r}")
    normalized = posixpath.normpath(name)
    if normalized != name or normalized == "." or normalized.startswith("../"):
        die(f"nombre de miembro no seguro: {name!r}")
    return pathlib.PurePosixPath(normalized)


def safe_destination(root: pathlib.Path, member: str) -> pathlib.Path:
    relative = safe_member_name(member)
    destination = root.joinpath(*relative.parts)
    # ``root`` is created by this process and must not be a symlink.  The
    # parent check also prevents an archive-created symlink from becoming a
    # path component for a later member.
    root_real = root.resolve()
    parent = destination.parent
    parent_real = parent.resolve(strict=False)
    try:
        parent_real.relative_to(root_real)
    except ValueError:
        die(f"salida fuera del directorio de staging: {member!r}")
    if destination.exists() or destination.is_symlink():
        die(f"colisión en la extracción: {member!r}")
    return destination


def ensure_empty_output(output: pathlib.Path) -> None:
    if output.exists() or output.is_symlink():
        die(f"la salida ya existe; se rechaza para no sobrescribir: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir()
    if output.is_symlink():
        die(f"la salida no puede ser un enlace: {output}")


def safe_mode(mode: int) -> int:
    # Preserve only the executable/read/write bits needed by build scripts;
    # never carry setuid/setgid/sticky bits out of an untrusted archive.
    return mode & 0o777


def safe_dir_mode(mode: int) -> int:
    # Extraction creates/needs descendants, so retain archive permissions but
    # guarantee the staging owner can traverse and publish them.
    return (safe_mode(mode) or 0o755) | 0o700


def stream_copy(source: object, destination: pathlib.Path, expected: int | None) -> None:
    written = 0
    with destination.open("xb") as output:
        while True:
            chunk = source.read(1024 * 1024)  # type: ignore[attr-defined]
            if not chunk:
                break
            written += len(chunk)
            if written > MAX_MEMBER_BYTES:
                die(f"miembro demasiado grande: {destination}")
            output.write(chunk)
    if expected is not None and written != expected:
        die(f"tamaño incompleto para {destination}: {written} != {expected}")


def validate_part_name(name: str) -> None:
    if is_part(name):
        die(f"se rechaza cualquier miembro .part sin leerlo: {name}")


def safe_link_target(member_name: str, linkname: str) -> str:
    """Normalize a link target and require it to remain under the archive root."""

    validate_part_name(linkname)
    if not linkname or "\\" in linkname or "\x00" in linkname:
        die(f"objetivo de enlace no válido: {linkname!r}")
    if posixpath.isabs(linkname) or linkname.startswith("~"):
        die(f"enlace absoluto rechazado: {member_name} -> {linkname}")
    target = posixpath.normpath(posixpath.join(posixpath.dirname(member_name), linkname))
    if target == "." or target.startswith("../") or target == "..":
        die(f"enlace fuera del staging rechazado: {member_name} -> {linkname}")
    # The normalized form has no dot components, so this also rejects an
    # escaped target while allowing ordinary links such as ../include/foo.
    safe_member_name(target)
    # Keep the link text relative to the member itself.  Returning the
    # root-relative target would silently change ``scripts/dtc -> ../../dtc``
    # into a different link after extraction.
    return posixpath.normpath(linkname)


def reject_symlink_parents(key: str, symlinks: set[str]) -> None:
    parts = key.split("/")
    for index in range(1, len(parts)):
        parent = "/".join(parts[:index])
        if parent in symlinks:
            die(f"un miembro usa un enlace como directorio padre: {key}")


def make_parent(root: pathlib.Path, key: str, symlinks: set[str]) -> pathlib.Path:
    parts = key.split("/")
    current = root
    for index in range(1, len(parts)):
        parent_key = "/".join(parts[:index])
        if parent_key in symlinks:
            die(f"un miembro usa un enlace como directorio padre: {key}")
        current = current / parts[index - 1]
        if current.exists() or current.is_symlink():
            if not current.is_dir() or current.is_symlink():
                die(f"el padre no es un directorio real: {parent_key}")
        else:
            current.mkdir()
    return current


def publish_symlink(root: pathlib.Path, key: str, target: str) -> None:
    destination = root.joinpath(*key.split("/"))
    if destination.exists() or destination.is_symlink():
        die(f"colisión en la extracción: {key}")
    destination.parent.mkdir(parents=False, exist_ok=True)
    os.symlink(target, destination)
    try:
        destination.resolve(strict=False).relative_to(root.resolve())
    except (OSError, RuntimeError, ValueError) as error:
        destination.unlink(missing_ok=True)
        raise ReleaseError(f"enlace fuera del staging: {key} -> {target}") from error


def extract_zip(archive: pathlib.Path, output: pathlib.Path) -> dict[str, object]:
    if is_part(archive):
        die(f"no se lee un archivo .part: {archive}")
    ensure_empty_output(output)
    seen: set[str] = set()
    total = 0
    regular_count = 0
    try:
        with zipfile.ZipFile(archive) as source:
            infos = source.infolist()
            if len(infos) > MAX_MEMBERS:
                die(f"demasiados miembros ZIP: {len(infos)}")
            directories: list[tuple[str, int]] = []
            regulars: list[tuple[str, zipfile.ZipInfo, int]] = []
            links: list[tuple[str, str]] = []
            for info in infos:
                validate_part_name(info.filename)
                marker = info.filename.endswith("/")
                name = info.filename[:-1] if marker else info.filename
                if marker and name in {"", ".", "./"}:
                    # GNU tar/ZIP may carry an explicit archive-root marker.
                    # It has no filesystem object to publish.
                    continue
                if not name:
                    continue
                relative = safe_member_name(name)
                key = relative.as_posix()
                if key in seen:
                    die(f"miembro ZIP duplicado: {key}")
                seen.add(key)
                mode = (info.external_attr >> 16) & 0xFFFF
                if marker:
                    if mode and stat.S_IFMT(mode) not in {0, stat.S_IFDIR}:
                        die(f"directorio ZIP con tipo no permitido: {key}")
                    directories.append((key, safe_dir_mode(mode)))
                    continue
                if stat.S_ISLNK(mode):
                    with source.open(info, "r") as stream:
                        target_bytes = stream.read(4097)
                    if len(target_bytes) > 4096:
                        die(f"objetivo de enlace ZIP demasiado largo: {key}")
                    try:
                        target = target_bytes.decode("utf-8")
                    except UnicodeDecodeError as error:
                        raise ReleaseError(f"objetivo de enlace ZIP no UTF-8: {key}") from error
                    links.append((key, safe_link_target(key, target)))
                    continue
                if stat.S_IFMT(mode) not in {0, stat.S_IFREG}:
                    die(f"tipo especial ZIP rechazado: {key}")
                regulars.append((key, info, safe_mode(mode) or 0o644))

            symlink_names = {key for key, _ in links}
            for key in seen:
                reject_symlink_parents(key, symlink_names)
            for key, mode in sorted(directories, key=lambda item: (item[0].count("/"), item[0])):
                destination = output.joinpath(*key.split("/"))
                if destination.exists() or destination.is_symlink():
                    die(f"colisión en la extracción: {key}")
                make_parent(output, key, symlink_names)
                destination.mkdir()
                destination.chmod(mode)
            for key, info, mode in regulars:
                destination = output.joinpath(*key.split("/"))
                if destination.exists() or destination.is_symlink():
                    die(f"colisión en la extracción: {key}")
                make_parent(output, key, symlink_names)
                with source.open(info, "r") as stream:
                    stream_copy(stream, destination, info.file_size)
                destination.chmod(mode)
                total += info.file_size
                regular_count += 1
                if total > MAX_MEMBER_BYTES:
                    die("tamaño total ZIP demasiado grande")
            for key, target in sorted(links):
                make_parent(output, key, symlink_names)
                publish_symlink(output, key, target)
    except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile) as error:
        raise ReleaseError(f"ZIP rechazado: {error}") from error
    return {"kind": "zip", "members": len(seen), "regular_files": regular_count, "symlinks": len(links), "bytes": total}


def extract_tar(archive: pathlib.Path, output: pathlib.Path) -> dict[str, object]:
    if is_part(archive):
        die(f"no se lee un archivo .part: {archive}")
    ensure_empty_output(output)
    seen: set[str] = set()
    total = 0
    regular_count = 0
    try:
        with tarfile.open(archive, mode="r:*") as source:
            members = source.getmembers()
            if len(members) > MAX_MEMBERS:
                die(f"demasiados miembros TAR: {len(members)}")
            directories: list[tuple[str, int]] = []
            regulars: list[tuple[str, tarfile.TarInfo, int]] = []
            links: list[tuple[str, str]] = []
            for member in members:
                validate_part_name(member.name)
                if member.isdir() and member.name in {".", "./"}:
                    # tarfile normalizes a ``./`` root marker to ``.``.
                    continue
                marker = member.name.endswith("/")
                name = member.name[:-1] if marker else member.name
                if marker and name in {"", ".", "./"}:
                    continue
                if not name:
                    continue
                relative = safe_member_name(name)
                key = relative.as_posix()
                if key in seen:
                    die(f"miembro TAR duplicado: {key}")
                seen.add(key)
                if member.isdir():
                    directories.append((key, safe_dir_mode(member.mode)))
                    continue
                if member.issym():
                    links.append((key, safe_link_target(key, member.linkname)))
                    continue
                if member.islnk() or not member.isfile():
                    die(f"tipo TAR no permitido (hardlink/dispositivo): {key}")
                regulars.append((key, member, safe_mode(member.mode) or 0o644))

            symlink_names = {key for key, _ in links}
            for key in seen:
                reject_symlink_parents(key, symlink_names)
            for key, mode in sorted(directories, key=lambda item: (item[0].count("/"), item[0])):
                destination = output.joinpath(*key.split("/"))
                if destination.exists() or destination.is_symlink():
                    die(f"colisión en la extracción: {key}")
                make_parent(output, key, symlink_names)
                destination.mkdir()
                destination.chmod(mode)
            for key, member, mode in regulars:
                destination = output.joinpath(*key.split("/"))
                if destination.exists() or destination.is_symlink():
                    die(f"colisión en la extracción: {key}")
                make_parent(output, key, symlink_names)
                stream = source.extractfile(member)
                if stream is None:
                    die(f"no se pudo leer el miembro TAR: {key}")
                with stream:
                    stream_copy(stream, destination, member.size)
                destination.chmod(mode)
                total += member.size
                regular_count += 1
                if total > MAX_MEMBER_BYTES:
                    die("tamaño total TAR demasiado grande")
            for key, target in sorted(links):
                make_parent(output, key, symlink_names)
                publish_symlink(output, key, target)
    except (OSError, tarfile.TarError) as error:
        raise ReleaseError(f"TAR rechazado: {error}") from error
    return {"kind": "tar", "members": len(seen), "regular_files": regular_count, "symlinks": len(links), "bytes": total}


def iter_files(root: pathlib.Path) -> Iterator[pathlib.Path]:
    """Walk without following symlinks and without opening ``.part`` files."""

    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = sorted(name for name in dirnames if not is_part(name))
        for name in sorted(filenames):
            if is_part(name):
                continue
            path = pathlib.Path(directory) / name
            if path.is_symlink():
                continue
            yield path


def relpath(path: pathlib.Path, root: pathlib.Path) -> str:
    return path.relative_to(root).as_posix()


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_commit_refs(path: pathlib.Path, limit: int = 256 * 1024) -> list[str]:
    try:
        with path.open("rb") as stream:
            data = stream.read(limit)
        text = data.decode("utf-8", errors="ignore")
    except OSError:
        return []
    return sorted(set(match.lower() for match in HEX_COMMIT.findall(text)))


def scan_release(root: pathlib.Path) -> dict[str, object]:
    if not root.is_dir() or root.is_symlink():
        die(f"no es un directorio de release válido: {root}")
    files = list(iter_files(root))
    archives: list[dict[str, object]] = []
    build_scripts: list[str] = []
    config_files: list[dict[str, object]] = []
    toolchain_paths: list[str] = []
    commit_refs: list[dict[str, object]] = []
    for path in files:
        relative = relpath(path, root)
        kind = archive_kind(path)
        size = path.stat().st_size
        if kind:
            archives.append({"path": relative, "kind": kind, "bytes": size})
        lower_name = path.name.lower()
        if (
            lower_name == "makefile"
            or lower_name in {"kbuild", "build.sh", "build_kernel.sh"}
            or (lower_name.startswith("build") and lower_name.endswith((".sh", ".py", ".mk")))
        ):
            build_scripts.append(relative)
        if (
            "defconfig" in lower_name
            or lower_name == ".config"
            or lower_name.startswith("build.config")
            or lower_name.startswith("kconfig")
        ):
            config_files.append({"path": relative, "bytes": size, "sha256": sha256(path)})
        if any(token in lower_name or token in relative.lower() for token in ("toolchain", "clang", "llvm", "gcc", "prebuilt")):
            toolchain_paths.append(relative)
        if lower_name.startswith(("manifest", "readme", "version", "build")) or lower_name in {"makefile", "build_kernel.sh"}:
            refs = read_commit_refs(path)
            if refs:
                commit_refs.append({"path": relative, "commits": refs})

    directories: set[pathlib.Path] = {root}
    for path in files:
        current = path.parent
        while True:
            directories.add(current)
            if current == root:
                break
            current = current.parent
    kernel_roots: list[dict[str, object]] = []
    for directory in sorted(directories):
        # A Linux source tree has a distinctive *combination* of top-level
        # paths.  Scoring generic Makefile/Kconfig names used to classify
        # hundreds of arch/, drivers/ and tools/ subdirectories as kernels.
        # Require the complete structural signature instead.
        markers = {
            "Makefile": (directory / "Makefile").is_file(),
            "Kconfig": (directory / "Kconfig").is_file(),
            "arch/arm64": (directory / "arch" / "arm64").is_dir(),
            "include/linux": (directory / "include" / "linux").is_dir(),
            "drivers": (directory / "drivers").is_dir(),
            "kernel": (directory / "kernel").is_dir(),
        }
        if all(markers.values()):
            reasons = list(markers)
            if (directory / "build_kernel.sh").is_file():
                reasons.append("build_kernel.sh")
            kernel_roots.append(
                {
                    "path": relpath(directory, root) or ".",
                    "score": len(reasons),
                    "reasons": reasons,
                }
            )

    git = None
    git_dir = root / ".git"
    if git_dir.is_dir() and not git_dir.is_symlink():
        # Do not trust or execute anything from the release tree.  Reading the
        # ref files is enough to record a detached/source revision when OSRC
        # happens to include a git checkout.
        head = git_dir / "HEAD"
        try:
            head_text = head.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            head_text = ""
        git = {"head": head_text}

    return {
        "root": str(root),
        "archives": sorted(archives, key=lambda item: str(item["path"])),
        "kernel_roots": sorted(kernel_roots, key=lambda item: (-int(item["score"]), str(item["path"]))),
        "build_scripts": sorted(set(build_scripts)),
        "config_files": sorted(config_files, key=lambda item: str(item["path"])),
        "toolchain_paths": sorted(set(toolchain_paths)),
        "commit_refs": sorted(commit_refs, key=lambda item: str(item["path"])),
        "git": git,
        "file_count": len(files),
    }


def write_json(path: pathlib.Path, value: object) -> None:
    if path.exists() or path.is_symlink():
        die(f"el manifiesto ya existe; se rechaza sobrescribirlo: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def unpack_tree(root: pathlib.Path) -> list[dict[str, object]]:
    if not root.is_dir() or root.is_symlink():
        die(f"no es un árbol de release: {root}")
    # OSRC deliveries commonly wrap a base ZIP and a regional overlay ZIP,
    # while the kernel itself is a TAR.GZ.  Process both archive families in
    # the guest so the scanner sees the complete layout.
    candidates = [path for path in iter_files(root) if archive_kind(path) is not None]
    # Expand both Kernel.tar.gz and Platform.tar.gz.  The latter is not a
    # kernel build input, but the user requested a complete, independently
    # inspectable OSRC delivery.  It remains separated below the fresh run.
    # Archives found inside an extracted TAR are source fixtures/data, not
    # Samsung delivery layers.  Only ZIP containers can enqueue another
    # delivery layer, with a hard nesting limit for malicious wrappers.
    queue = [(path, 0) for path in candidates]
    max_zip_depth = 4
    processed: set[pathlib.Path] = set()
    results: list[dict[str, object]] = []
    while queue:
        archive, depth = queue.pop(0)
        if archive in processed:
            continue
        processed.add(archive)
        if is_part(archive):
            continue
        output = archive.with_name(archive.name + ".contents")
        kind = archive_kind(archive)
        if kind == "zip":
            existed = output.exists() or output.is_symlink()
            try:
                result = extract_zip(archive, output)
            except Exception:
                if not existed and output.is_dir() and not output.is_symlink():
                    shutil.rmtree(output, ignore_errors=True)
                raise
        elif kind == "tar":
            existed = output.exists() or output.is_symlink()
            try:
                result = extract_tar(archive, output)
            except Exception:
                if not existed and output.is_dir() and not output.is_symlink():
                    shutil.rmtree(output, ignore_errors=True)
                raise
        else:
            die(f"formato de archivo no soportado: {archive}")
        result["archive"] = relpath(archive, root)
        result["output"] = relpath(output, root)
        results.append(result)
        if kind == "zip":
            nested = [
                path for path in iter_files(output)
                if archive_kind(path) is not None
            ]
            if nested and depth >= max_zip_depth:
                die(f"demasiados niveles ZIP anidados bajo {archive}")
            queue.extend((path, depth + 1) for path in nested)
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name in ("extract-zip", "extract-tar"):
        sub = subparsers.add_parser(name)
        sub.add_argument("archive", type=pathlib.Path)
        sub.add_argument("output", type=pathlib.Path)

    sub = subparsers.add_parser("unpack-tree")
    sub.add_argument("root", type=pathlib.Path)
    sub.add_argument("--manifest", type=pathlib.Path)

    sub = subparsers.add_parser("scan")
    sub.add_argument("root", type=pathlib.Path)
    sub.add_argument("--output", type=pathlib.Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "extract-zip":
            result: object = extract_zip(args.archive, args.output)
        elif args.command == "extract-tar":
            result = extract_tar(args.archive, args.output)
        elif args.command == "unpack-tree":
            result = unpack_tree(args.root)
        else:
            result = scan_release(args.root)
        if getattr(args, "manifest", None) is not None:
            write_json(args.manifest, result)
        elif getattr(args, "output", None) is not None and args.command == "scan":
            write_json(args.output, result)
        else:
            print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (OSError, ReleaseError, tarfile.TarError, zipfile.BadZipFile) as error:
        # ``extract-*`` creates a fresh output before streaming payloads.  If
        # validation or I/O fails, remove only that newly-created directory;
        # an existing output was rejected before creation and is untouched.
        if args.command in {"extract-zip", "extract-tar"}:
            output = args.output
            if output.is_dir() and not output.is_symlink():
                shutil.rmtree(output, ignore_errors=True)
        print(f"Release rechazado: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
