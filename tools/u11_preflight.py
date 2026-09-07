#!/usr/bin/env python3
"""Audita offline la coherencia U11 para M2/M3 sin autorizar un flasheo."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Iterable


REQUIRED_EARLY_USERSPACE = (
    "CONFIG_BLK_DEV_INITRD",
    "CONFIG_DEVTMPFS",
    "CONFIG_DEVTMPFS_MOUNT",
    "CONFIG_FHANDLE",
    "CONFIG_TTY",
    "CONFIG_VT",
    "CONFIG_SERIAL_EARLYCON",
    "CONFIG_SERIAL_SAMSUNG_CONSOLE",
    "CONFIG_PROC_FS",
    "CONFIG_SYSFS",
    "CONFIG_TMPFS",
    "CONFIG_TMPFS_POSIX_ACL",
    "CONFIG_TMPFS_XATTR",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"{path}:{line_number}: asignación KEY=VALUE inválida")
        key, value = line.split("=", 1)
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
            raise ValueError(f"{path}:{line_number}: clave inválida: {key}")
        if value.startswith(("'", '"')) or "$" in value or "`" in value:
            raise ValueError(f"{path}:{line_number}: no se permiten expansiones de shell")
        values[key] = value
    return values


def parse_key_values(path: Path) -> dict[str, str]:
    return {
        key: value
        for raw in path.read_text(encoding="utf-8").splitlines()
        if raw and not raw.startswith("#") and "=" in raw
        for key, value in [raw.split("=", 1)]
    }


def parse_kernel_config(path: Path) -> dict[str, str]:
    config: dict[str, str] = {}
    unset = re.compile(r"^# (CONFIG_[A-Z0-9_]+) is not set$")
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if raw.startswith("CONFIG_") and "=" in raw:
            key, value = raw.split("=", 1)
            config[key] = value
        elif match := unset.match(raw):
            config[match.group(1)] = "n"
    return config


def verify_checksum_file(directory: Path, manifest: Path) -> tuple[list[str], list[str]]:
    checked: list[str] = []
    failures: list[str] = []
    root = directory.resolve()
    seen: set[str] = set()
    for line_number, raw in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", raw)
        if not match:
            failures.append(f"línea {line_number} inválida")
            continue
        expected, relative = match.groups()
        if relative in seen:
            failures.append(f"entrada duplicada: {relative}")
            continue
        seen.add(relative)
        candidate = directory / relative
        try:
            candidate.relative_to(directory)
        except ValueError:
            failures.append(f"ruta fuera del artefacto: {relative}")
            continue
        if candidate.is_symlink():
            failures.append(f"symlink no permitido: {relative}")
            continue
        try:
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(root)
        except (FileNotFoundError, ValueError, OSError):
            failures.append(f"ruta resuelta fuera o ausente: {relative}")
            continue
        if not resolved.is_file():
            failures.append(f"falta {relative}")
        elif sha256(resolved) != expected:
            failures.append(f"hash distinto: {relative}")
        else:
            checked.append(relative)
    return checked, failures


def verify_tar_extraction(archive: Path, destination: Path) -> tuple[int, list[str]]:
    """Compara todos los regulares del tar con una extracción, sin seguir links."""
    failures: list[str] = []
    expected: set[str] = set()
    count = 0
    with tarfile.open(archive, "r:*") as bundle:
        for member in bundle:
            path = Path(member.name)
            if path.is_absolute() or ".." in path.parts:
                failures.append(f"ruta insegura en tar: {member.name}")
                continue
            if member.isdir():
                continue
            if not member.isfile():
                failures.append(f"tipo no regular en tar: {member.name}")
                continue
            expected.add(member.name)
            extracted = destination / path
            stream = bundle.extractfile(member)
            if stream is None or not extracted.is_file() or extracted.is_symlink():
                failures.append(f"falta regular extraído: {member.name}")
                continue
            digest = hashlib.sha256()
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
            if digest.hexdigest() != sha256(extracted):
                failures.append(f"contenido distinto: {member.name}")
            count += 1
    actual = {
        str(path.relative_to(destination))
        for path in destination.rglob("*")
        if path.is_file() and not path.is_symlink()
    }
    for extra in sorted(actual - expected):
        failures.append(f"regular extra no presente en tar: {extra}")
    return count, failures


def non_comment_lines(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def module_names_from_vendor_list(path: Path) -> list[str]:
    result: list[str] = []
    for line in non_comment_lines(path):
        fields = line.split("|")
        result.append(fields[-1].strip())
    return result


def initramfs_fit(payload: int, limit: int) -> dict[str, int | bool]:
    return {"bytes": payload, "limit": limit, "margin": limit - payload, "fits": payload <= limit}


def repro_report_valid(report: dict[str, object]) -> bool:
    """Sólo acepta evidencia explícita de dos ejecuciones independientes."""
    return all((
        report.get("schema") == 1,
        report.get("profile") == "SM-X510-X510XXSBDZB4-U11-fixed-offline",
        report.get("reproducible") is True,
        report.get("physical_write_gate") == "NO-GO",
        isinstance(report.get("first_run"), str),
        isinstance(report.get("second_run"), str),
        report.get("first_run") != report.get("second_run"),
        report.get("missing_in_first") == [],
        report.get("missing_in_second") == [],
        report.get("only_in_first") == [],
        report.get("only_in_second") == [],
        report.get("differing") == [],
        report.get("unsafe_in_first") == [],
        report.get("unsafe_in_second") == [],
        report.get("first_metadata_errors") == [],
        report.get("second_metadata_errors") == [],
    ))


class Audit:
    def __init__(self) -> None:
        self.checks: list[dict[str, object]] = []

    def add(self, check_id: str, status: str, detail: str, evidence: str | None = None) -> None:
        assert status in {"PASS", "WARN", "FAIL"}
        item: dict[str, object] = {"id": check_id, "status": status, "detail": detail}
        if evidence:
            item["evidence"] = evidence
        self.checks.append(item)

    def passed(self, check_ids: Iterable[str]) -> bool:
        wanted = set(check_ids)
        return all(
            any(item["id"] == check_id and item["status"] == "PASS" for item in self.checks)
            for check_id in wanted
        )


def resolve(root: Path, value: str) -> Path:
    candidate = Path(value)
    return candidate if candidate.is_absolute() else root / candidate


def run_audit(root: Path, identity_path: Path) -> dict[str, object]:
    identity = parse_env(identity_path)
    audit = Audit()

    target = parse_env(root / "configs/target-sm-x510.env")
    identity_ok = (
        identity.get("U11_MODEL") == "SM-X510"
        and identity.get("U11_SOURCE_AP_VERSION") == "X510XXSBDZB4"
        and identity.get("U11_SOURCE_BASE_VERSION") == "X510XXU8DYJ4"
        and identity.get("U11_BOOTLOADER_REVISION") == "11"
        and identity.get("U11_KERNEL_RELEASE") == "5.15.180"
        and target.get("TARGET_AP_VERSION") == "X510XXUCEZE4"
        and target.get("TARGET_BOOTLOADER_REVISION") == "12"
    )
    audit.add(
        "identity_separation",
        "PASS" if identity_ok else "FAIL",
        "U11/B11 source and EZE4/U12 target are registered as distinct identities",
        str(identity_path.relative_to(root)),
    )

    package_keys = (
        ("U11_BASE_ZIP", "U11_BASE_ZIP_SHA256"),
        ("U11_OVERLAY_ZIP", "U11_OVERLAY_ZIP_SHA256"),
        ("U11_KERNEL_TARBALL", "U11_KERNEL_TARBALL_SHA256"),
    )
    package_failures: list[str] = []
    package_details: list[dict[str, object]] = []
    for path_key, hash_key in package_keys:
        path = resolve(root, identity[path_key])
        expected = identity[hash_key]
        actual = sha256(path) if path.is_file() else None
        if actual != expected:
            package_failures.append(path_key)
        package_details.append({"path": str(path), "bytes": path.stat().st_size if path.is_file() else None,
                                "expected_sha256": expected, "actual_sha256": actual})
    audit.add(
        "osrc_hashes",
        "FAIL" if package_failures else "PASS",
        "OSRC base, overlay, and Kernel.tar.gz hashes " + ("do not match: " + ", ".join(package_failures) if package_failures else "match"),
    )

    build = resolve(root, identity["U11_BUILD_ARTIFACTS"])
    manifest = build / "SHA256SUMS"
    checked, failures = verify_checksum_file(build, manifest) if manifest.is_file() else ([], ["falta SHA256SUMS"])
    audit.add(
        "build_hashes",
        "FAIL" if failures else "PASS",
        f"{len(checked)} build artifacts verified" + (f"; {', '.join(failures)}" if failures else ""),
        str(manifest.relative_to(root)) if manifest.exists() else None,
    )

    build_info_path = build / "BUILD_INFO.txt"
    build_info = parse_key_values(build_info_path) if build_info_path.is_file() else {}
    build_identity_ok = all((
        build_info.get("source_release") == identity.get("U11_SOURCE_AP_VERSION"),
        build_info.get("source_base") == identity.get("U11_SOURCE_BASE_VERSION"),
        build_info.get("kernel_release") == identity.get("U11_KERNEL_RELEASE"),
        build_info.get("full_build_exit_status") == "0",
        build_info.get("built_modules") == "282",
        build_info.get("installed_modules") == "282",
    ))
    audit.add("build_identity", "PASS" if build_identity_ok else "FAIL",
              "BUILD_INFO links source, kernel, and 282 modules" if build_identity_ok else "BUILD_INFO does not match U11 identity")

    config_path = build / "kernel.config"
    config = parse_kernel_config(config_path) if config_path.is_file() else {}
    missing_config = [key for key in REQUIRED_EARLY_USERSPACE if config.get(key) != "y"]
    audit.add(
        "early_userspace_config",
        "FAIL" if missing_config else "PASS",
        "config prepared for initramfs and early console" if not missing_config else "missing: " + ", ".join(missing_config),
        str(config_path.relative_to(root)) if config_path.exists() else None,
    )

    installed_parent = build / "modules-installed/modules-root/lib/modules"
    release_dirs = [item for item in installed_parent.iterdir() if item.is_dir()] if installed_parent.is_dir() else []
    release_ok = len(release_dirs) == 1 and release_dirs[0].name == identity.get("U11_KERNEL_RELEASE")
    installed_release = release_dirs[0] if release_ok else None
    installed_modules = list(installed_release.rglob("*.ko")) if installed_release else []
    symlinks = list((build / "modules-installed").rglob("*")) if (build / "modules-installed").exists() else []
    symlinks = [path for path in symlinks if path.is_symlink()]
    modules_tar = build / "modules-root.tar.gz"
    tar_count, tar_failures = verify_tar_extraction(modules_tar, build / "modules-installed") if modules_tar.is_file() else (0, ["falta modules-root.tar.gz"])
    modules_ok = release_ok and len(installed_modules) == 282 and not symlinks and not tar_failures
    audit.add(
        "installed_modules",
        "PASS" if modules_ok else "FAIL",
        f"release={release_dirs[0].name if len(release_dirs) == 1 else 'ambiguous'}, modules={len(installed_modules)}, "
        f"regular files verified against tar={tar_count}, symlinks={len(symlinks)}"
        + (f"; {', '.join(tar_failures)}" if tar_failures else ""),
    )

    build_order = non_comment_lines(build / "modules.order") if (build / "modules.order").is_file() else []
    installed_order_path = installed_release / "modules.order" if installed_release else Path("missing")
    installed_order = non_comment_lines(installed_order_path) if installed_order_path.is_file() else []
    normalized_installed = [line.removeprefix("kernel/") for line in installed_order]
    order_ok = len(build_order) == 282 and normalized_installed == build_order
    audit.add("module_order_consistency", "PASS" if order_ok else "FAIL",
              f"modules.order build/install: {len(build_order)}/{len(installed_order)}")

    available_names = {path.name for path in installed_modules}
    early_path = build / "vendor_boot_module_order_s5e8835.cfg"
    early_names = non_comment_lines(early_path) if early_path.is_file() else []
    vendor_names: list[str] = []
    for filename in ("vendor_module_list_s5e8835.cfg", "vendor_module_list_s5e8835_gts9fewifi.cfg"):
        path = build / filename
        if path.is_file():
            vendor_names.extend(module_names_from_vendor_list(path))
    missing_named = [name for name in early_names + vendor_names if name not in available_names]
    audit.add("vendor_module_lists", "PASS" if not missing_named and len(early_names) == 7 else "FAIL",
              f"7 early modules + {len(vendor_names)} product modules present" if not missing_named else "missing: " + ", ".join(missing_named))

    module_audit_path = root / "reports/generated/u11-modules/modules-audit.json"
    module_audit = json.loads(module_audit_path.read_text(encoding="utf-8"))
    required_module_checks = {
        "stock_provenance", "u11_module_metadata", "u11_hard_dependency_graph",
        "stock_u11_load_order", "ufs_closure", "usb_closure",
    }
    module_status = {item.get("id"): item.get("status") for item in module_audit.get("checks", [])}
    missing_module_checks = sorted(check for check in required_module_checks if module_status.get(check) != "PASS")
    module_audit_ok = (
        not missing_module_checks
        and module_audit.get("physical_write_gate") == "NO-GO"
        and module_audit.get("u11", {}).get("release") == identity.get("U11_KERNEL_RELEASE")
        and module_audit.get("u11", {}).get("modules") == 282
    )
    audit.add(
        "module_vendor_boot_audit",
        "PASS" if module_audit_ok else "FAIL",
        ("metadata, dependencies, stock order, and UFS/USB closures verified"
         if module_audit_ok else "missing/failed module checks: " + ", ".join(missing_module_checks)),
        str(module_audit_path.relative_to(root)),
    )

    layout_path = root / "artifacts/stock/boot-layout.json"
    layout = json.loads(layout_path.read_text(encoding="utf-8"))
    init_boot = next(item for item in layout if str(item.get("path", "")).endswith("init_boot.img"))
    stock_limit = int(init_boot["ramdisk_size"])
    init_root = resolve(root, identity["U11_INITRAMFS_ARTIFACTS"])
    init_metadata_path = init_root / "BUILD-METADATA"
    init_metadata = parse_key_values(init_metadata_path) if init_metadata_path.is_file() else {}
    expected_manifest_hash = sha256(build / "SHA256SUMS") if (build / "SHA256SUMS").is_file() else None
    expected_modules_hash = sha256(build / "modules-root.tar.gz") if (build / "modules-root.tar.gz").is_file() else None
    init_provenance_ok = all((
        init_metadata.get("source_ap_version") == identity.get("U11_SOURCE_AP_VERSION"),
        init_metadata.get("kernel_release") == identity.get("U11_KERNEL_RELEASE"),
        init_metadata.get("module_count") == "282",
        init_metadata.get("byte_reproducible") == "yes",
        init_metadata.get("source_build_manifest_sha256") == expected_manifest_hash,
        init_metadata.get("source_modules_archive_sha256") == expected_modules_hash,
        bool(re.fullmatch(r"[0-9a-f]{64}", init_metadata.get("source_modules_tree_sha256", ""))),
        init_metadata.get("physical_write_gate") == "NO-GO",
    ))
    audit.add(
        "initramfs_source_provenance", "PASS" if init_provenance_ok else "FAIL",
        ("initramfs linked by hash to U11 manifest, tar, and modules tree"
         if init_provenance_ok else "incomplete initramfs metadata or mismatch with U11 build"),
        str(init_metadata_path.relative_to(root)) if init_metadata_path.exists() else None,
    )
    profiles: dict[str, object] = {}
    expected_counts = {"minimal": 0, "ufs": 28, "usb": 45}
    for profile, expected_count in expected_counts.items():
        directory = init_root / profile
        payload = directory / "gts9fe-initramfs.cpio.lz4"
        profile_manifest = directory / "SHA256SUMS"
        profile_checked, profile_failures = verify_checksum_file(directory, profile_manifest) if profile_manifest.is_file() else ([], ["falta SHA256SUMS"])
        module_files = list((directory / "rootfs/lib/modules").rglob("*.ko")) if (directory / "rootfs/lib/modules").exists() else []
        fit = initramfs_fit(payload.stat().st_size, stock_limit) if payload.is_file() else initramfs_fit(stock_limit + 1, stock_limit)
        profile_ok = not profile_failures and len(module_files) == expected_count
        if not profile_ok:
            status = "FAIL"
        elif fit["fits"]:
            status = "PASS"
        else:
            status = "WARN"
        detail = f"{len(module_files)} modules, LZ4={fit['bytes']} B, margin={fit['margin']} B"
        if profile == "usb" and not fit["fits"]:
            detail += "; oversized diagnostic profile, unpackable"
        audit.add(f"initramfs_{profile}", status, detail,
                  str(profile_manifest.relative_to(root)) if profile_manifest.exists() else None)
        profiles[profile] = {"module_count": len(module_files), "checksums": len(profile_checked), **fit}

    semantic_dir = root / "reports/generated/u11-osrc"
    semantic_r04 = json.loads((semantic_dir / "semantic-r04-u11-eze4.json").read_text(encoding="utf-8"))
    compiled_base_path = root / "reports/generated/u11-dtb-binary/semantic-base-compiled-u11-eze4.json"
    semantic_base = json.loads(compiled_base_path.read_text(encoding="utf-8"))
    overlay_observed = semantic_r04.get("material_difference_count") == 0
    base_observed = semantic_base.get("material_difference_count") == 4
    audit.add(
        "dt_observed_distance",
        "WARN" if overlay_observed and base_observed else "FAIL",
        f"r04 material={semantic_r04.get('material_difference_count')}, unresolved={len(semantic_r04.get('unresolved', []))}; "
        f"compiled base DTB material={semantic_base.get('material_difference_count')}, unresolved={len(semantic_base.get('unresolved', []))}. Does not prove equivalence.",
        str(compiled_base_path.relative_to(root)),
    )

    repro_path = root / "reports/generated/u11-repro/reproducibility.json"
    repro_report = json.loads(repro_path.read_text(encoding="utf-8")) if repro_path.is_file() else {}
    reproducible = repro_report_valid(repro_report)
    audit.add(
        "kernel_binary_reproducibility", "PASS" if reproducible else "WARN",
        ("two clean runs of fixed profile are byte-for-byte identical"
         if reproducible else "missing valid comparison of two clean runs of fixed profile"),
        str(repro_path.relative_to(root)) if repro_path.exists() else None,
    )
    audit.add("exact_eze4_source", "WARN", "OSRC X510XXUCEZE4 request is pending; U11 is not U12/EZE4")
    audit.add("hardware_observation", "WARN", "no console or physical testing; M2/M3 not observed")
    audit.add("physical_write_gate", "WARN", "NO-GO: this report never authorizes flashing, signing, or downgrade")

    offline_ids = (
        "identity_separation", "osrc_hashes", "build_hashes", "build_identity",
        "early_userspace_config", "installed_modules", "module_order_consistency",
        "vendor_module_lists", "module_vendor_boot_audit", "initramfs_source_provenance",
        "initramfs_minimal", "initramfs_ufs",
    )
    result = {
        "schema": 1,
        "source": {"ap": identity.get("U11_SOURCE_AP_VERSION"), "base": identity.get("U11_SOURCE_BASE_VERSION"),
                   "kernel": identity.get("U11_KERNEL_RELEASE"), "bootloader_revision": 11},
        "target": {"ap": target.get("TARGET_AP_VERSION"), "bootloader_revision": 12,
                   "firmware_sha256": target.get("TARGET_FIRMWARE_SHA256")},
        "packages": package_details,
        "init_boot_stock_ramdisk_bytes": stock_limit,
        "initramfs_profiles": profiles,
        "checks": audit.checks,
        "gates": {
            "offline_u11_analysis_ready": audit.passed(offline_ids),
            "m2_observed": False,
            "m3_payload_ready": audit.passed(("early_userspace_config", "initramfs_minimal", "initramfs_ufs")),
            "m3_observed": False,
            "physical_write": "NO-GO",
        },
    }
    return result


def markdown(result: dict[str, object]) -> str:
    gates = result["gates"]
    profiles = result["initramfs_profiles"]
    lines = [
        "# U11 Offline Preflight for M2/M3",
        "",
        "This report verifies offline consistency. **It never authorizes writing to the tablet.**",
        "",
        "## Verdict",
        "",
        f"- U11 offline analysis: `{'READY' if gates['offline_u11_analysis_ready'] else 'NOT READY'}`",
        f"- M3 payload: `{'READY' if gates['m3_payload_ready'] else 'NOT READY'}`",
        f"- M2 observed on hardware: `{str(gates['m2_observed']).lower()}`",
        f"- M3 observed on hardware: `{str(gates['m3_observed']).lower()}`",
        f"- physical write: `{gates['physical_write']}`",
        "",
        "## Initramfs vs EZE4 init_boot",
        "",
        "| profile | modules | LZ4 (B) | margin (B) | fits |",
        "|---|---:|---:|---:|---|",
    ]
    for name in ("minimal", "ufs", "usb"):
        item = profiles[name]
        lines.append(f"| `{name}` | {item['module_count']} | {item['bytes']} | {item['margin']} | {'yes' if item['fits'] else 'no'} |")
    lines.extend(("", "## Checks", "", "| status | check | detail |", "|---|---|---|"))
    for item in result["checks"]:
        lines.append(f"| `{item['status']}` | `{item['id']}` | {item['detail']} |")
    lines.extend((
        "", "## How to Read the Result", "",
        "`READY` only means that offline inputs are consistent with each other. Incomplete",
        "DTS states, lack of exact EZE4 source, and the",
        "absence of physical observation keep the write gate at `NO-GO`.", "",
    ))
    return "\n".join(lines)


def atomic_write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        stream.write(data)
        temporary = Path(stream.name)
    os.replace(temporary, path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--identity", type=Path)
    parser.add_argument("--json", type=Path)
    parser.add_argument("--markdown", type=Path)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    identity = args.identity or root / "configs/u11-x510xxsbdzb4.env"
    output_json = args.json or root / "reports/generated/u11-preflight/preflight.json"
    output_markdown = args.markdown or root / "reports/generated/u11-preflight/preflight.md"
    try:
        result = run_audit(root, identity.resolve())
        atomic_write(output_json.resolve(), json.dumps(result, indent=2, sort_keys=True) + "\n")
        atomic_write(output_markdown.resolve(), markdown(result))
    except (OSError, ValueError, KeyError, StopIteration, json.JSONDecodeError) as error:
        print(f"u11-preflight: {error}", file=sys.stderr)
        return 2
    print(markdown(result), end="")
    return 1 if any(item["status"] == "FAIL" for item in result["checks"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
