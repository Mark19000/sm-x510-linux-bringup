#!/usr/bin/env python3
"""Compara módulos U11, vendor_boot EZE4 y perfiles initramfs sin mezclar binarios."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path


SIGNATURE_MAGIC = b"~Module signature appended~\n"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_evidence_manifest(directory: Path) -> tuple[int, list[str]]:
    manifest = directory / "SHA256SUMS"
    failures: list[str] = []
    checked = 0
    if not manifest.is_file():
        return 0, ["falta SHA256SUMS"]
    for number, raw in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_.-]+)", raw)
        if not match:
            failures.append(f"línea inválida {number}")
            continue
        expected, name = match.groups()
        path = directory / name
        if not path.is_file() or path.is_symlink():
            failures.append(f"falta regular {name}")
        elif sha256(path) != expected:
            failures.append(f"hash distinto {name}")
        else:
            checked += 1
    return checked, failures


def lines(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")]


def module_filename(value: str) -> str:
    return Path(value.strip()).name


def module_id(value: str) -> str:
    name = module_filename(value)
    if name.endswith(".ko"):
        name = name[:-3]
    return name.replace("-", "_")


def dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def common_order_equal(left: list[str], right: list[str]) -> tuple[bool, int]:
    common = set(left) & set(right)
    left_common = [item for item in left if item in common]
    right_common = [item for item in right if item in common]
    return left_common == right_common, len(common)


def parse_modules_dep(path: Path) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        owner, separator, dependencies = raw.partition(":")
        if not separator:
            raise ValueError(f"línea modules.dep inválida: {raw}")
        key = module_id(owner)
        if key in result:
            raise ValueError(f"módulo duplicado en modules.dep: {key}")
        result[key] = {module_id(item) for item in dependencies.split()}
    return result


def parse_softdeps(path: Path) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for raw in lines(path):
        fields = raw.replace("pre:", " pre: ").replace("post:", " post: ").split()
        if len(fields) < 2 or fields[0] != "softdep":
            raise ValueError(f"línea modules.softdep inválida: {raw}")
        owner = module_id(fields[1])
        dependencies = {module_id(item) for item in fields[2:] if item not in {"pre:", "post:"}}
        result.setdefault(owner, set()).update(dependencies)
    return result


def missing_closure(included: set[str], deps: dict[str, set[str]], softdeps: dict[str, set[str]]) -> list[str]:
    missing: list[str] = []
    for owner in sorted(included):
        for dependency in sorted(deps.get(owner, set()) | softdeps.get(owner, set())):
            if dependency not in included:
                missing.append(f"{owner}->{dependency}")
    return missing


def module_metadata(path: Path, release: str) -> tuple[bool, bool, str | None]:
    data = path.read_bytes()
    match = re.search(rb"vermagic=([^\0]+)", data)
    vermagic = match.group(1).decode("ascii", "replace") if match else None
    return bool(vermagic and vermagic.startswith(release + " ")), data.endswith(SIGNATURE_MAGIC), vermagic


def parse_key_values(path: Path) -> dict[str, str]:
    return {key: value for raw in path.read_text(encoding="utf-8").splitlines()
            if raw and not raw.startswith("#") and "=" in raw
            for key, value in [raw.split("=", 1)]}


def add(checks: list[dict[str, object]], check_id: str, status: str, detail: str) -> None:
    checks.append({"id": check_id, "status": status, "detail": detail})


def run(root: Path) -> dict[str, object]:
    build = root / "artifacts/u11/x510xxsbdzb4-u11-clang21-20260823"
    installed = build / "modules-installed/modules-root/lib/modules/5.15.180"
    stock = root / "artifacts/stock/vendor-ramdisk-audit"
    initramfs = root / "artifacts/initramfs/u11/x510xxsbdzb4-clang21"
    checks: list[dict[str, object]] = []

    stock_checked, stock_hash_failures = verify_evidence_manifest(stock)
    provenance = parse_key_values(stock / "PROVENANCE.txt")
    stock_evidence_ok = (
        provenance.get("source_ap_version") == "X510XXUCEZE4"
        and provenance.get("source_vendor_boot_sha256") == "60e85ca061cc67cfa1f8d9fd86fc3840ccb46d87887c9b3ed20deca7c02459e8"
        and provenance.get("fragment_count") == "2"
        and provenance.get("fragment_1_modules") == "281"
    )
    stock_evidence_ok = stock_evidence_ok and stock_checked == 6 and not stock_hash_failures
    add(checks, "stock_provenance", "PASS" if stock_evidence_ok else "FAIL",
        ("vendor_boot EZE4 v4: fragmentos generic + dlkm, 281 módulos; 6 ficheros verificados"
         if stock_evidence_ok else "provenance stock incompleta o alterada: " + ", ".join(stock_hash_failures)))

    modules = sorted(installed.rglob("*.ko"))
    module_ids = {module_id(path.name) for path in modules}
    bad_vermagic: list[str] = []
    unsigned: list[str] = []
    vermagic_values: set[str] = set()
    for path in modules:
        valid_release, signed, vermagic = module_metadata(path, "5.15.180")
        if not valid_release:
            bad_vermagic.append(path.name)
        if not signed:
            unsigned.append(path.name)
        if vermagic:
            vermagic_values.add(vermagic)
    metadata_ok = len(modules) == 282 and not bad_vermagic and not unsigned and len(vermagic_values) == 1
    add(checks, "u11_module_metadata", "PASS" if metadata_ok else "FAIL",
        f"282/282 módulos con vermagic 5.15.180 y firma añadida" if metadata_ok else
        f"módulos={len(modules)}, vermagic inválido={len(bad_vermagic)}, sin firma={len(unsigned)}")

    dependencies = parse_modules_dep(installed / "modules.dep")
    softdeps = parse_softdeps(installed / "modules.softdep")
    missing_global = sorted({dependency for values in dependencies.values() for dependency in values if dependency not in module_ids})
    missing_soft = sorted({dependency for values in softdeps.values() for dependency in values if dependency not in module_ids})
    dep_ok = len(dependencies) == 282 and not missing_global
    add(checks, "u11_hard_dependency_graph", "PASS" if dep_ok else "FAIL",
        "282 entradas modules.dep; todas las dependencias duras están presentes" if dep_ok else
        f"dependencias duras ausentes: {', '.join(missing_global)}")
    stock_softdeps = parse_softdeps(stock / "modules.softdep")
    stock_module_ids = {module_id(line.split(maxsplit=1)[1]) for line in lines(stock / "MODULES_SHA256SUMS")}
    stock_missing_soft = sorted({dependency for values in stock_softdeps.values() for dependency in values
                                 if dependency not in stock_module_ids})
    mirrored_stale_softdeps = missing_soft == stock_missing_soft
    add(checks, "softdep_stale_names", "WARN" if missing_soft else "PASS",
        (f"referencias no resolubles {missing_soft}; coinciden con vendor_boot EZE4={mirrored_stale_softdeps}"
         if missing_soft else "todas las referencias softdep se resuelven"))

    prefix = lines(build / "vendor_boot_module_order_s5e8835.cfg")
    build_order = [module_filename(item) for item in lines(build / "modules.order")]
    generated_load = dedupe(prefix + build_order)
    stock_load = lines(stock / "modules.load")
    same_common_order, common_count = common_order_equal(generated_load, stock_load)
    only_stock = sorted(set(stock_load) - set(generated_load))
    only_u11 = sorted(set(generated_load) - set(stock_load))
    order_ok = (
        len(prefix) == 7 and len(generated_load) == 282 and len(stock_load) == 281
        and common_count == 280 and same_common_order
        and only_stock == ["sec_debug_test.ko"]
        and only_u11 == ["a96t396.ko", "input_booster_lkm.ko"]
    )
    add(checks, "stock_u11_load_order", "PASS" if order_ok else "FAIL",
        f"280 common in same order; stock only={only_stock}; U11 only={only_u11}")

    profile_details: dict[str, object] = {}
    for profile, expected, required in (
        ("ufs", 28, {"ufs_exynos_core"}),
        ("usb", 45, {"phy_exynos_usbdrd_super", "dwc3_exynos_usb"}),
    ):
        profile_modules = list((initramfs / profile / "rootfs/lib/modules/5.15.180").rglob("*.ko"))
        included = {module_id(path.name) for path in profile_modules}
        closure_missing = missing_closure(included, dependencies, softdeps)
        wrong_release = [path.name for path in profile_modules if not module_metadata(path, "5.15.180")[0]]
        ok = len(profile_modules) == expected and required <= included and not closure_missing and not wrong_release
        add(checks, f"{profile}_closure", "PASS" if ok else "FAIL",
            f"{len(profile_modules)} U11 modules; missing dependencies={len(closure_missing)}")
        profile_details[profile] = {"modules": len(profile_modules), "required": sorted(required),
                                    "missing_dependencies": closure_missing, "wrong_release": wrong_release}

    usb_ids = {module_id(path.name) for path in (initramfs / "usb/rootfs/lib/modules/5.15.180").rglob("*.ko")}
    host_mode_present = "xhci_exynos" in usb_ids
    add(checks, "usb_role_scope", "WARN",
        "profile gadget/ACM-oriented; xhci-exynos not included" if not host_mode_present else "xhci-exynos included; audit host/dual-role")
    add(checks, "scsc_firmware", "WARN",
        "Wi-Fi/BT is not included for M2/M3; /vendor/firmware/wifi and EFS calibration still need extraction")
    add(checks, "physical_write_gate", "WARN", "NO-GO: module audit does not authorize packaging or flashing")

    return {
        "schema": 1,
        "u11": {"release": "5.15.180", "modules": len(modules), "vermagic": sorted(vermagic_values)},
        "stock_eze4": {"modules": len(stock_load), "vendor_boot_sha256": provenance.get("source_vendor_boot_sha256")},
        "load_order": {"prefix": prefix, "common": common_count, "common_relative_order_equal": same_common_order,
                       "only_stock": only_stock, "only_u11": only_u11},
        "profiles": profile_details,
        "checks": checks,
        "physical_write_gate": "NO-GO",
    }


def render(result: dict[str, object]) -> str:
    order = result["load_order"]
    lines_out = [
        "# U11 Modules Audit ↔ EZE4 vendor_boot",
        "",
        "## Result",
        "",
        f"- U11 modules: `{result['u11']['modules']}` (`{result['u11']['release']}`)",
        f"- stock EZE4 modules in dlkm: `{result['stock_eze4']['modules']}`",
        f"- common modules: `{order['common']}`, same relative order: `{str(order['common_relative_order_equal']).lower()}`",
        f"- stock only: `{', '.join(order['only_stock'])}`",
        f"- U11 only: `{', '.join(order['only_u11'])}`",
        f"- physical gate: `{result['physical_write_gate']}`",
        "",
        "## Checks",
        "",
        "| status | check | detail |",
        "|---|---|---|",
    ]
    for item in result["checks"]:
        lines_out.append(f"| `{item['status']}` | `{item['id']}` | {item['detail']} |")
    lines_out.extend((
        "", "## Interpretation", "",
        "Equal relative order reduces early initialization risk, but does not prove",
        "U11↔EZE4 binary ABI. Stock modules are never loaded with the U11 kernel, nor U11",
        "modules with the stock kernel. UFS and USB only have static closure proven;",
        "DT, clocks, PHY, regulators, and Type-C still require hardware observation.",
        "",
    ))
    return "\n".join(lines_out)


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        stream.write(text)
        temporary = Path(stream.name)
    os.replace(temporary, path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--json", type=Path)
    parser.add_argument("--markdown", type=Path)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    output_json = args.json or root / "reports/generated/u11-modules/modules-audit.json"
    output_markdown = args.markdown or root / "reports/generated/u11-modules/modules-audit.md"
    try:
        result = run(root)
    except (OSError, ValueError) as error:
        print(f"u11-modules-audit: {error}", file=sys.stderr)
        return 2
    atomic_write(output_json.resolve(), json.dumps(result, indent=2, sort_keys=True) + "\n")
    report = render(result)
    atomic_write(output_markdown.resolve(), report)
    print(report, end="")
    return 1 if any(item["status"] == "FAIL" for item in result["checks"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
