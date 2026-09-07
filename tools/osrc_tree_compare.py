#!/usr/bin/env python3
"""Compare two Samsung OSRC/kernel trees without changing either input.

The comparison is intentionally host-only.  It inventories the parts that are
most likely to affect a board port (DTS/DTSI, drivers, Kconfig/defconfigs and
build files), compares file content by SHA-256, and optionally relates
decompiled EZE4 Device Trees to likely U3/U11 board sources.  Reports are
written to a staging directory and published only after every input and
comparison has succeeded; an existing report is left untouched on failure.

No archive download is performed here.  In particular, files ending in
``.part`` are ignored and a ``.part`` path is not accepted as an input tree.
The caller must provide an extracted, stable U11 tree when one is available.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence


TOOL_NAME = "osrc-tree-compare"
SCHEMA_VERSION = 1
CATEGORY_NAMES = ("dts", "drivers", "configs", "build_scripts")
DTS_SUFFIXES = {".dts", ".dtsi"}
TEXT_DTS_SUFFIXES = {".dts", ".dtsi"}
PARTIAL_SUFFIX = ".part"

# This deliberately follows filenames rather than trying to infer build
# systems from file contents.  Samsung OSRC drops have used both the Linux
# Kbuild names and small shell/Android build wrappers over time.
_CONFIG_NAME_RE = re.compile(
    r"(?:^Kconfig(?:\..*)?$|(?:^|_)defconfig$|^\.config(?:\..*)?$|config$)",
    re.IGNORECASE,
)
_BUILD_NAME_RE = re.compile(
    r"(?:^Makefile(?:\..*)?$|^Kbuild(?:\..*)?$|^Android\.(?:bp|mk)$|"
    r"^BUILD(?:\.bazel)?$|^build(?:[-_.].*)?\.sh$|^build\.config(?:\..*)?$|"
    r".*\.mk$|.*\.bzl$)",
    re.IGNORECASE,
)
_COMPAT_ASSIGNMENT_RE = re.compile(
    r"\bcompatible\s*=\s*((?:\"(?:\\.|[^\"])*\"\s*,?\s*)+);",
    re.DOTALL,
)
_QUOTED_RE = re.compile(r'"((?:\\.|[^"\\])*)"')
_HW_REV_RE = re.compile(
    r"\bdtbo-hw_rev(?:_end)?\s*=\s*<\s*(0x[0-9a-fA-F]+|[0-9]+)"
)
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_GENERIC_DTS_TOKENS = {
    "dts",
    "dtb",
    "overlay",
    "offset",
    "vendor",
    "boot",
    "recovery",
    "fdt",
    "id",
    "rev",
    "open",
    "eur",
    "samsung",
}


class ComparisonError(RuntimeError):
    """An input or output failed a deterministic safety/validation check."""


@dataclass(frozen=True)
class FileRecord:
    path: str
    size: int
    sha256: str

    def as_dict(self) -> dict[str, object]:
        return {"path": self.path, "size": self.size, "sha256": self.sha256}


@dataclass
class TreeSnapshot:
    label: str
    root: Path
    file_count: int
    partial_count: int
    symlink_count: int
    categories: dict[str, dict[str, FileRecord]]
    git: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        return {
            "label": self.label,
            "root": str(self.root),
            "file_count": self.file_count,
            "ignored_partial_files": self.partial_count,
            "ignored_symlinks": self.symlink_count,
            "git": self.git,
            "categories": {
                name: {
                    "count": len(records),
                    "files": [records[path].as_dict() for path in sorted(records)],
                }
                for name, records in self.categories.items()
            },
        }


@dataclass(frozen=True)
class Eze4Input:
    path: Path
    display: str
    kind: str
    text: str | None
    compatibles: tuple[str, ...]
    hw_revision: tuple[int, int] | None

    def as_dict(self) -> dict[str, object]:
        return {
            "path": str(self.path),
            "display": self.display,
            "kind": self.kind,
            "compatibles": list(self.compatibles),
            "hw_revision": list(self.hw_revision) if self.hw_revision else None,
        }


def _canonical(path: Path) -> Path:
    """Resolve an existing or future path without requiring it to exist."""

    return path.expanduser().resolve(strict=False)


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _reject_symlink_components(path: Path, label: str) -> None:
    """Reject a symlink at the requested path itself.

    Parent aliases such as macOS's conventional ``/var`` → ``/private/var``
    are intentionally allowed; ``Path.resolve`` below still applies the
    containment checks to the canonical destination.
    """

    candidate = path.expanduser()
    try:
        if candidate.is_symlink():
            raise ComparisonError(f"{label} no puede ser un enlace simbólico: {path}")
    except OSError as exc:
        raise ComparisonError(f"No se puede inspeccionar {label}: {path}: {exc}") from exc


def _check_tree(path: Path, label: str) -> Path:
    _reject_symlink_components(path, label)
    candidate = _canonical(path)
    if str(candidate).endswith(PARTIAL_SUFFIX):
        raise ComparisonError(
            f"{label} apunta a un fragmento .part; espera una extracción completa"
        )
    if not candidate.exists():
        raise ComparisonError(f"No existe el árbol {label}: {path}")
    if not candidate.is_dir():
        raise ComparisonError(f"{label} no es un directorio: {path}")
    if candidate.is_symlink():
        raise ComparisonError(f"{label} no puede ser un enlace simbólico: {path}")
    return candidate


def _check_eze4_path(path: Path) -> Path:
    _reject_symlink_components(path, "Entrada EZE4")
    candidate = _canonical(path)
    if str(candidate).endswith(PARTIAL_SUFFIX):
        raise ComparisonError(
            f"La entrada EZE4 apunta a un fragmento .part: {path}; "
            "usa el DTS/DTB extraído"
        )
    if not candidate.exists():
        raise ComparisonError(f"No existe la entrada EZE4: {path}")
    if not candidate.is_dir() and not candidate.is_file():
        raise ComparisonError(f"La entrada EZE4 no es fichero/directorio: {path}")
    return candidate


def _classify(relative: Path) -> set[str]:
    """Return the inventory categories to which a relative path belongs."""

    name = relative.name
    lowered_parts = {part.lower() for part in relative.parts}
    categories: set[str] = set()
    if relative.suffix.lower() in DTS_SUFFIXES:
        categories.add("dts")
    # A release may wrap the kernel under one directory, so accept any
    # drivers/ component except the Documentation/driver-api/... example.
    # Documentation is deliberately excluded to avoid a false driver count.
    driver_index = next(
        (index for index, part in enumerate(relative.parts) if part.lower() == "drivers"),
        None,
    )
    if driver_index is not None and not any(
        part.lower() == "documentation" for part in relative.parts[:driver_index]
    ):
        categories.add("drivers")
    if (
        _CONFIG_NAME_RE.search(name)
        or "configs" in lowered_parts
        or name.lower().endswith((".cfg", ".config"))
    ):
        categories.add("configs")
    if (
        _BUILD_NAME_RE.search(name)
        or "build" in lowered_parts
        or ("scripts" in lowered_parts and name.lower().endswith(".sh"))
    ):
        categories.add("build_scripts")
    return categories


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise ComparisonError(f"No se puede leer {path}: {exc}") from exc
    return digest.hexdigest()


def _git_metadata(root: Path) -> dict[str, object]:
    """Collect local Git identity only; never fetches or modifies the checkout."""

    try:
        commit = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return {"present": False}
    if not commit:
        return {"present": False}
    try:
        dirty_result = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        dirty = bool(dirty_result.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        dirty = None
    return {"present": True, "commit": commit, "dirty": dirty}


def collect_snapshot(root: Path, label: str) -> TreeSnapshot:
    """Build a deterministic, content-addressed inventory for one tree."""

    categories: dict[str, dict[str, FileRecord]] = {
        name: {} for name in CATEGORY_NAMES
    }
    file_count = 0
    partial_count = 0
    symlink_count = 0
    hash_cache: dict[str, str] = {}

    for directory, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        # Git metadata is not source input and can contain huge object packs.
        dirnames[:] = sorted(
            name for name in dirnames if name != ".git" and not name.endswith(PARTIAL_SUFFIX)
        )
        for name in sorted(filenames):
            candidate = Path(directory) / name
            relative = candidate.relative_to(root)
            if name.endswith(PARTIAL_SUFFIX) or any(
                part.endswith(PARTIAL_SUFFIX) for part in relative.parts
            ):
                partial_count += 1
                continue
            try:
                stat = candidate.lstat()
            except OSError as exc:
                raise ComparisonError(f"No se puede inspeccionar {candidate}: {exc}") from exc
            if not candidate.is_file() or os.path.islink(candidate):
                symlink_count += 1
                continue
            file_count += 1
            category_names = _classify(relative)
            if not category_names:
                continue
            relative_name = relative.as_posix()
            if relative_name not in hash_cache:
                # stat.st_size is captured before hashing so a concurrent change
                # cannot silently become a successful comparison.
                hash_cache[relative_name] = _sha256(candidate)
                try:
                    after_size = candidate.stat().st_size
                except OSError as exc:
                    raise ComparisonError(f"No se puede inspeccionar {candidate}: {exc}") from exc
                if after_size != stat.st_size:
                    raise ComparisonError(f"El fichero cambió durante la lectura: {candidate}")
            record = FileRecord(relative_name, stat.st_size, hash_cache[relative_name])
            for category in category_names:
                categories[category][relative_name] = record

    if file_count == 0:
        raise ComparisonError(f"El árbol {label} no contiene ficheros regulares utilizables")
    return TreeSnapshot(
        label=label,
        root=root,
        file_count=file_count,
        partial_count=partial_count,
        symlink_count=symlink_count,
        categories=categories,
        git=_git_metadata(root),
    )


def compare_category(
    left: Mapping[str, FileRecord], right: Mapping[str, FileRecord]
) -> dict[str, object]:
    left_paths = set(left)
    right_paths = set(right)
    common = left_paths & right_paths
    changed = [
        {
            "path": path,
            "u3": left[path].as_dict(),
            "u11": right[path].as_dict(),
        }
        for path in sorted(common)
        if left[path].sha256 != right[path].sha256
    ]
    return {
        "u3_count": len(left_paths),
        "u11_count": len(right_paths),
        "common_count": len(common),
        "unchanged_count": len(common) - len(changed),
        "u3_only": sorted(left_paths - right_paths),
        "u11_only": sorted(right_paths - left_paths),
        "changed": changed,
    }


def _read_dts(path: Path) -> tuple[str, tuple[str, ...], tuple[int, int] | None]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise ComparisonError(f"No se puede leer DTS EZE4 {path}: {exc}") from exc
    values: list[str] = []
    for assignment in _COMPAT_ASSIGNMENT_RE.findall(text):
        for raw in _QUOTED_RE.findall(assignment):
            value = bytes(raw, "utf-8").decode("unicode_escape", errors="replace")
            for compatible in value.replace("\\0", "\0").split("\0"):
                compatible = compatible.strip()
                if compatible and compatible not in values:
                    values.append(compatible)
    revisions = [int(value, 0) for value in _HW_REV_RE.findall(text)]
    hw_revision = None
    if revisions:
        hw_revision = (min(revisions), max(revisions))
    return text, tuple(sorted(values)), hw_revision


def discover_eze4(inputs: Sequence[Path]) -> tuple[list[Eze4Input], list[dict[str, str]]]:
    """Find decompiled DTS/DTSI and record DTB inputs that need decompilation."""

    found: dict[Path, Eze4Input] = {}
    unsupported: list[dict[str, str]] = []
    for raw in inputs:
        path = _check_eze4_path(raw)
        if path.is_file():
            candidates = [path]
            base = path.parent
        else:
            base = path
            candidates = []
            for directory, dirnames, filenames in os.walk(path, followlinks=False):
                dirnames[:] = sorted(
                    name for name in dirnames
                    if name != ".git" and not name.endswith(PARTIAL_SUFFIX)
                )
                for name in sorted(filenames):
                    candidate = Path(directory) / name
                    if name.endswith(PARTIAL_SUFFIX):
                        continue
                    if candidate.suffix.lower() in TEXT_DTS_SUFFIXES | {".dtb"}:
                        candidates.append(candidate)
        for candidate in sorted(candidates):
            resolved = _canonical(candidate)
            if resolved.name.endswith(PARTIAL_SUFFIX):
                continue
            suffix = resolved.suffix.lower()
            if suffix == ".dtb":
                unsupported.append(
                    {
                        "path": str(resolved),
                        "reason": "binary DTB; provides decompiled DTS for semantic comparison",
                    }
                )
                continue
            if suffix not in TEXT_DTS_SUFFIXES:
                raise ComparisonError(
                    f"La entrada EZE4 no es DTS/DTSI/DTB: {resolved}"
                )
            if not resolved.is_file() or resolved.is_symlink():
                raise ComparisonError(f"La entrada EZE4 no es un fichero regular: {resolved}")
            text, compatibles, hw_revision = _read_dts(resolved)
            try:
                display = resolved.relative_to(base).as_posix()
            except ValueError:
                display = resolved.name
            found[resolved] = Eze4Input(
                path=resolved,
                display=display,
                kind=suffix[1:],
                text=text,
                compatibles=compatibles,
                hw_revision=hw_revision,
            )
    return [found[path] for path in sorted(found)], sorted(
        unsupported, key=lambda item: item["path"]
    )


def _source_dts(
    snapshot: TreeSnapshot,
) -> dict[str, tuple[Path, tuple[str, ...], tuple[int, int] | None]]:
    result: dict[str, tuple[Path, tuple[str, ...], tuple[int, int] | None]] = {}
    for relative in sorted(snapshot.categories["dts"]):
        if Path(relative).suffix.lower() != ".dts":
            continue
        path = snapshot.root / Path(relative)
        try:
            _, compatibles, hw_revision = _read_dts(path)
        except ComparisonError:
            # collect_snapshot already proved the file readable; this protects
            # the heuristic from a source file disappearing between phases.
            continue
        result[relative] = (path, compatibles, hw_revision)
    return result


def _path_tokens(value: str) -> set[str]:
    return {
        token
        for token in _TOKEN_RE.findall(value.lower())
        if len(token) >= 3 and token not in _GENERIC_DTS_TOKENS
    }


def _candidate_score(
    eze4: Eze4Input,
    eze4_tokens: set[str],
    relative: str,
    compatibles: tuple[str, ...],
    hw_revision: tuple[int, int] | None,
) -> tuple[int, list[str]]:
    reasons: list[str] = []
    common = set(eze4.compatibles) & set(compatibles)
    score = len(common) * 100
    if common:
        reasons.append("compatible=" + ",".join(sorted(common)))
    if eze4.hw_revision and hw_revision:
        eze4_start, eze4_end = eze4.hw_revision
        candidate_start, candidate_end = hw_revision
        if max(eze4_start, candidate_start) <= min(eze4_end, candidate_end):
            score += 60
            reasons.append(
                "hw-rev=" + f"{candidate_start}..{candidate_end}"
            )
    candidate_tokens = _path_tokens(relative)
    overlap = sorted(eze4_tokens & candidate_tokens)
    score += len(overlap) * 20
    if overlap:
        reasons.append("path=" + ",".join(overlap))
    stem = Path(relative).stem.lower()
    if stem and stem in eze4_tokens:
        score += 80
        reasons.append("stem")
    return score, reasons


def _pick_dts_candidate(
    eze4: Eze4Input,
    candidates: Mapping[str, tuple[Path, tuple[str, ...], tuple[int, int] | None]],
) -> dict[str, object]:
    eze4_tokens = _path_tokens(eze4.display + " " + " ".join(eze4.compatibles))
    scored: list[tuple[int, str, list[str]]] = []
    for relative, (_, compatibles, hw_revision) in candidates.items():
        score, reasons = _candidate_score(
            eze4, eze4_tokens, relative, compatibles, hw_revision
        )
        if score:
            scored.append((score, relative, reasons))
    scored.sort(key=lambda item: (-item[0], item[1]))
    if not scored:
        return {
            "path": None,
            "confidence": "none",
            "reason": "no hay compatible común; se requiere mapeo manual",
            "candidates": [],
        }
    top_score = scored[0][0]
    top = [item for item in scored if item[0] == top_score]
    confidence = "high" if len(top) == 1 else "ambiguous"
    chosen = top[0]
    return {
        "path": chosen[1] if len(top) == 1 else None,
        "confidence": confidence,
        "reason": "; ".join(chosen[2]) if chosen[2] else "heurística",
        "candidates": [
            {"path": path, "score": score, "reason": "; ".join(reasons)}
            for score, path, reasons in scored[:5]
        ],
    }


def _semantic_summary(left: Path | None, right: Path | None) -> dict[str, object]:
    if left is None or right is None:
        return {"status": "UNMAPPED", "equivalent": None}
    try:
        # Import lazily: inventory-only comparisons remain useful if a future
        # host has only the standard library files but not the project parser.
        tools_dir = Path(__file__).resolve().parent
        if str(tools_dir) not in sys.path:
            sys.path.insert(0, str(tools_dir))
        import dts_semantic_diff as semantic  # type: ignore

        comparison = semantic.compare_paths(left, right)
    except Exception as exc:  # parser errors are evidence, not fatal input loss
        return {"status": "ERROR", "equivalent": None, "error": str(exc)}
    return {
        "status": comparison.status,
        "equivalent": comparison.equivalent,
        "differences": len(comparison.differences),
        "unresolved": len(comparison.unresolved),
        "phandle_renumbered": len(comparison.phandle_renumbered),
    }


def build_dts_matrix(
    u3: TreeSnapshot,
    u11: TreeSnapshot,
    eze4_inputs: Sequence[Eze4Input],
) -> list[dict[str, object]]:
    u3_candidates = _source_dts(u3)
    u11_candidates = _source_dts(u11)
    rows: list[dict[str, object]] = []
    for eze4 in eze4_inputs:
        u3_match = _pick_dts_candidate(eze4, u3_candidates)
        u11_match: dict[str, object]
        u3_path = u3_match.get("path")
        if isinstance(u3_path, str) and u3_path in u11_candidates:
            u11_match = {
                "path": u3_path,
                "confidence": "path",
                "reason": "misma ruta relativa que U3",
                "candidates": [],
            }
        else:
            u11_match = _pick_dts_candidate(eze4, u11_candidates)
        u11_path = u11_match.get("path")
        u3_file = u3.root / u3_path if isinstance(u3_path, str) else None
        u11_file = u11.root / u11_path if isinstance(u11_path, str) else None
        rows.append(
            {
                "eze4": eze4.as_dict(),
                "u3": u3_match,
                "u11": u11_match,
                "u3_u11": _semantic_summary(u3_file, u11_file),
                "u3_eze4": _semantic_summary(u3_file, eze4.path),
                "u11_eze4": _semantic_summary(u11_file, eze4.path),
            }
        )
    return rows


def _validate_map_path(root: Path, relative: object, label: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise ComparisonError(f"El mapeo DTS requiere una ruta {label} no vacía")
    raw_candidate = root / relative
    _reject_symlink_components(raw_candidate, f"Ruta DTS {label}")
    candidate = _canonical(raw_candidate)
    if not _is_relative_to(candidate, root) or not candidate.is_file():
        raise ComparisonError(f"Ruta DTS fuera del árbol {label}: {relative}")
    if candidate.suffix.lower() not in TEXT_DTS_SUFFIXES:
        raise ComparisonError(f"Ruta DTS {label} no termina en .dts/.dtsi: {relative}")
    return candidate


def apply_dts_map(
    matrix: list[dict[str, object]],
    map_path: Path,
    u3: TreeSnapshot,
    u11: TreeSnapshot,
    eze4_inputs: Sequence[Eze4Input],
) -> list[dict[str, object]]:
    """Override heuristic rows from a small JSON mapping file.

    Accepted shape is ``[{"eze4": "...", "u3": "...", "u11": "..."}]``
    or ``{"mappings": [...]}``, with U3/U11 paths relative to their trees and
    EZE4 matching either the displayed path or its basename.  This keeps the
    automatic matrix useful while making ambiguous board revisions auditable.
    """

    try:
        raw = json.loads(map_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ComparisonError(f"No se puede leer --dts-map {map_path}: {exc}") from exc
    mappings = raw.get("mappings") if isinstance(raw, dict) else raw
    if not isinstance(mappings, list):
        raise ComparisonError("--dts-map debe ser una lista o un objeto {\"mappings\": [...]}")
    by_eze4: dict[str, Eze4Input] = {}
    for item in eze4_inputs:
        by_eze4[item.display] = item
        by_eze4[item.path.name] = item
    updated = list(matrix)
    row_by_display = {
        row["eze4"]["display"]: row for row in updated  # type: ignore[index]
    }
    for item in mappings:
        if not isinstance(item, dict):
            raise ComparisonError("Cada entrada de --dts-map debe ser un objeto")
        eze4_key = item.get("eze4")
        if not isinstance(eze4_key, str) or eze4_key not in by_eze4:
            raise ComparisonError(f"EZE4 no encontrado en --dts-map: {eze4_key}")
        eze4 = by_eze4[eze4_key]
        u3_file = _validate_map_path(u3.root, item.get("u3"), "U3")
        u11_file = _validate_map_path(u11.root, item.get("u11"), "U11")
        u3_rel = u3_file.relative_to(u3.root).as_posix()
        u11_rel = u11_file.relative_to(u11.root).as_posix()
        row = row_by_display[eze4.display]
        row["u3"] = {
            "path": u3_rel,
            "confidence": "explicit",
            "reason": f"mapeo {map_path.name}",
            "candidates": [],
        }
        row["u11"] = {
            "path": u11_rel,
            "confidence": "explicit",
            "reason": f"mapeo {map_path.name}",
            "candidates": [],
        }
        row["u3_u11"] = _semantic_summary(u3_file, u11_file)
        row["u3_eze4"] = _semantic_summary(u3_file, eze4.path)
        row["u11_eze4"] = _semantic_summary(u11_file, eze4.path)
    return updated


def _validate_output(output: Path, roots: Iterable[Path], eze4_inputs: Sequence[Path]) -> Path:
    _reject_symlink_components(output, "Salida")
    candidate = _canonical(output)
    if str(candidate).endswith(PARTIAL_SUFFIX):
        raise ComparisonError("La salida no puede terminar en .part")
    if candidate == Path("/"):
        raise ComparisonError("La salida no puede ser la raíz del sistema")
    for root in roots:
        if _is_relative_to(candidate, root):
            raise ComparisonError("La salida no puede estar dentro de un árbol de entrada")
    for raw in eze4_inputs:
        path = _canonical(raw)
        if _is_relative_to(candidate, path):
            raise ComparisonError("La salida no puede estar dentro de una entrada EZE4")
    if candidate.exists() and candidate.is_symlink():
        raise ComparisonError("La salida no puede ser un enlace simbólico")
    if candidate.exists() and not candidate.is_dir():
        raise ComparisonError(f"La salida existe y no es directorio: {output}")
    return candidate


def _write_text(path: Path, content: str) -> None:
    try:
        with path.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as exc:
        raise ComparisonError(f"No se puede escribir {path}: {exc}") from exc


def _md_cell(value: object) -> str:
    text = str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def render_markdown(report: Mapping[str, object], detail_limit: int) -> str:
    u3 = report["inputs"]["u3"]  # type: ignore[index]
    u11 = report["inputs"]["u11"]  # type: ignore[index]
    lines = [
        "# OSRC U3 ↔ U11 Comparison",
        "",
        "Host-only report generated by `tools/osrc_tree_compare.py`. Inputs are read",
        "without modifying them; `.part` files are ignored and no incomplete download is",
        "expected.",
        "",
        "## Inputs",
        "",
        "| tree | root | Git commit | files | ignored `.part` | ignored links |",
        "|---|---|---|---:|---:|---:|",
    ]
    for tree in (u3, u11):
        git = tree["git"]  # type: ignore[index]
        commit = git.get("commit", "-") if isinstance(git, dict) else "-"
        lines.append(
            "| `{}` | `{}` | `{}` | {} | {} | {} |".format(
                _md_cell(tree["label"]),  # type: ignore[index]
                _md_cell(tree["root"]),  # type: ignore[index]
                _md_cell(commit),
                tree["file_count"],  # type: ignore[index]
                tree["ignored_partial_files"],  # type: ignore[index]
                tree["ignored_symlinks"],  # type: ignore[index]
            )
        )
    lines.extend(
        [
            "",
            "## Inventory by Component",
            "",
            "| component | U3 | U11 | U3 only | U11 only | changed | unchanged |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    categories = report["categories"]  # type: ignore[index]
    for name in CATEGORY_NAMES:
        item = categories[name]  # type: ignore[index]
        lines.append(
            "| `{}` | {} | {} | {} | {} | {} | {} |".format(
                name,
                item["u3_count"],
                item["u11_count"],
                len(item["u3_only"]),
                len(item["u11_only"]),
                len(item["changed"]),
                item["unchanged_count"],
            )
        )
    for name in CATEGORY_NAMES:
        item = categories[name]  # type: ignore[index]
        if not item["u3_only"] and not item["u11_only"] and not item["changed"]:
            continue
        lines.extend(["", f"### Detail `{name}`", ""])
        for title, values in (
            ("U3 only", item["u3_only"]),
            ("U11 only", item["u11_only"]),
            ("Changed", [entry["path"] for entry in item["changed"]]),
        ):
            if not values:
                continue
            lines.append(f"- **{title}** ({len(values)}):")
            for value in list(values)[:detail_limit]:
                lines.append(f"  - `{_md_cell(value)}`")
            if len(values) > detail_limit:
                lines.append(f"  - … and {len(values) - detail_limit} more (see JSON).")
    lines.extend(["", "## DTS Matrix U3 ↔ U11 ↔ EZE4", ""])
    eze4 = report["eze4"]  # type: ignore[index]
    if not eze4["dts"]:  # type: ignore[index]
        lines.append(
            "No EZE4 DTS/DTSI found. Tree comparison remains valid; "
            "add `--eze4-dir` when decompiled DTS exist."
        )
    else:
        lines.extend(
            [
                "| EZE4 | U3 | U11 | U3↔U11 | U3↔EZE4 | U11↔EZE4 |",
                "|---|---|---|---|---|---|",
            ]
        )
        for row in report["dts_matrix"]:  # type: ignore[index]
            eze4_item = row["eze4"]
            u3_item = row["u3"]
            u11_item = row["u11"]
            lines.append(
                "| `{}` | `{}` ({}) | `{}` ({}) | {} | {} | {} |".format(
                    _md_cell(eze4_item["display"]),
                    _md_cell(u3_item.get("path") or "-"),
                    u3_item.get("confidence", "-"),
                    _md_cell(u11_item.get("path") or "-"),
                    u11_item.get("confidence", "-"),
                    row["u3_u11"]["status"],
                    row["u3_eze4"]["status"],
                    row["u11_eze4"]["status"],
                )
            )
    unsupported = eze4["unsupported"]  # type: ignore[index]
    if unsupported:
        lines.extend(["", "Binary DTBs detected but not compared semantically:", ""])
        for item in unsupported:
            lines.append(f"- `{_md_cell(item['path'])}`: {_md_cell(item['reason'])}")
    lines.extend(
        [
            "",
            "The `INCONCLUSIVE`/`DIFFERENT (INCOMPLETE)` states do not prove equivalence.",
            "The DTS mapping heuristic only prioritizes candidates by `compatible` and path;",
            "review or pin ambiguous pairs with `--dts-map` before porting changes.",
            "",
        ]
    )
    return "\n".join(lines)


def _existing_output_is_ours(output: Path) -> bool:
    marker = output / "comparison.json"
    if not marker.is_file():
        return False
    try:
        payload = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return payload.get("tool") == TOOL_NAME and payload.get("schema_version") == SCHEMA_VERSION


def publish_report(output: Path, report: Mapping[str, object], markdown: str) -> None:
    """Write and atomically publish ``comparison.json`` and ``comparison.md``."""

    parent = output.parent
    try:
        parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ComparisonError(f"No se puede crear el directorio padre {parent}: {exc}") from exc
    if output.exists() and not _existing_output_is_ours(output):
        raise ComparisonError(
            f"La salida existente no parece generada por {TOOL_NAME}; no se sobrescribe: {output}"
        )
    stage: Path | None = None
    try:
        stage = Path(tempfile.mkdtemp(prefix=f".{output.name}.tmp-", dir=str(parent)))
        _write_text(
            stage / "comparison.json",
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        )
        _write_text(stage / "comparison.md", markdown)
        try:
            directory_fd = os.open(stage, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            # Directory fsync is unavailable on a few host filesystems.  The
            # file fsyncs above still provide the useful guarantee there.
            pass

        if output.exists():
            backup = parent / f".{output.name}.old-{next(tempfile._get_candidate_names())}"
            os.replace(output, backup)
            try:
                os.replace(stage, output)
            except OSError:
                os.replace(backup, output)
                raise
            shutil.rmtree(backup)
            stage = None
        else:
            os.replace(stage, output)
            stage = None
    except OSError as exc:
        raise ComparisonError(f"No se puede publicar la salida {output}: {exc}") from exc
    finally:
        if stage is not None:
            shutil.rmtree(stage, ignore_errors=True)


def build_report(
    u3: TreeSnapshot,
    u11: TreeSnapshot,
    eze4_inputs: Sequence[Eze4Input],
    eze4_unsupported: Sequence[dict[str, str]],
    dts_map: Path | None,
) -> dict[str, object]:
    categories = {
        name: compare_category(u3.categories[name], u11.categories[name])
        for name in CATEGORY_NAMES
    }
    matrix = build_dts_matrix(u3, u11, eze4_inputs)
    if dts_map is not None:
        matrix = apply_dts_map(matrix, dts_map, u3, u11, eze4_inputs)
    return {
        "tool": TOOL_NAME,
        "schema_version": SCHEMA_VERSION,
        "inputs": {"u3": u3.as_dict(), "u11": u11.as_dict()},
        "categories": categories,
        "eze4": {
            "dts": [item.as_dict() for item in eze4_inputs],
            "unsupported": list(eze4_unsupported),
        },
        "dts_matrix": matrix,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compara dos árboles Samsung OSRC/kernel y, opcionalmente, DTS EZE4 "
            "decompilados; no descarga ni espera archivos .part."
        )
    )
    parser.add_argument("--u3", "--u3-dir", dest="u3", required=True, type=Path, help="árbol U3 extraído")
    parser.add_argument("--u11", "--u11-dir", dest="u11", required=True, type=Path, help="árbol U11 extraído")
    parser.add_argument(
        "--eze4", "--eze4-dir", dest="eze4", action="append", default=[], type=Path,
        help="DTS/DTSI EZE4 o directorio a recorrer (se puede repetir)",
    )
    parser.add_argument("--dts-map", type=Path, help="JSON opcional para fijar mapeos DTS ambiguos")
    parser.add_argument("--output", required=True, type=Path, help="directorio de salida transaccional")
    parser.add_argument(
        "--detail-limit", type=int, default=50,
        help="máximo de rutas por componente en Markdown (el JSON conserva todas; por defecto: 50)",
    )
    return parser


def run(args: argparse.Namespace) -> Path:
    if args.detail_limit < 1:
        raise ComparisonError("--detail-limit debe ser positivo")
    u3_root = _check_tree(args.u3, "U3")
    u11_root = _check_tree(args.u11, "U11")
    if u3_root == u11_root:
        raise ComparisonError("U3 y U11 deben ser árboles distintos")
    eze4_paths = [_check_eze4_path(path) for path in args.eze4]
    output = _validate_output(args.output, (u3_root, u11_root), eze4_paths)
    if args.dts_map is not None:
        _reject_symlink_components(args.dts_map, "--dts-map")
        map_path = _canonical(args.dts_map)
        if not map_path.is_file() or map_path.is_symlink():
            raise ComparisonError(f"--dts-map no es un fichero regular: {args.dts_map}")
        if _is_relative_to(map_path, u3_root) or _is_relative_to(map_path, u11_root):
            raise ComparisonError("--dts-map no puede estar dentro de un árbol comparado")
    else:
        map_path = None

    # All expensive/read-only work happens before creating the output parent.
    u3 = collect_snapshot(u3_root, "U3")
    u11 = collect_snapshot(u11_root, "U11")
    eze4_inputs, eze4_unsupported = discover_eze4(eze4_paths)
    report = build_report(u3, u11, eze4_inputs, eze4_unsupported, map_path)
    markdown = render_markdown(report, args.detail_limit)
    publish_report(output, report, markdown)
    return output


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        output = run(args)
    except ComparisonError as exc:
        parser.error(str(exc))
    print(f"Comparación publicada en {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
