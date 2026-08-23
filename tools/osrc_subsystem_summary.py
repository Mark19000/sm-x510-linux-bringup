#!/usr/bin/env python3
"""Summarise a comparison.json by bring-up subsystem.

This consumes the immutable output of osrc_tree_compare.py.  Counts describe
changed paths, not runtime compatibility; semantic DTS conclusions belong in
the accompanying analysis report.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import tempfile


SUBSYSTEMS = {
    "device_tree_s5e8835_x510": r"^arch/arm64/boot/dts/(?:exynos/.*s5e8835|samsung/gts9fewifi)/",
    "psci_gic_timers": r"^(?:arch/arm64/(?:kernel/(?:psci|time)|kvm)/?|drivers/(?:firmware/psci|irqchip|clocksource)/)",
    "cmu_clocks": r"^(?:drivers/clk/samsung/|drivers/soc/samsung/cal-if/)",
    "pinctrl_gpio_eint": r"^drivers/(?:pinctrl/samsung|gpio)/",
    "pmu_acpm_power_domains": r"^drivers/soc/samsung/(?:acpm|exynos-pm|exynos-pd|cal-if)/",
    "sysmmu_iommu": r"^drivers/iommu/samsung/",
    "ufs_phy_fmp": r"^drivers/scsi/ufs/",
    "usb_dwc3_typec": r"^drivers/usb/",
    "display_dsim_panel": r"^drivers/gpu/drm/samsung/",
    "touchscreen_wacom_pogo": r"^drivers/input/(?:touchscreen|wacom|sec_input)/",
    "gpu_mali": r"^drivers/gpu/arm/",
    "wifi_bt_scsc": r"^drivers/(?:misc/samsung/scsc(?:_bt)?|net/wireless/scsc)/",
    "battery_pmic_charging": r"^drivers/(?:battery|mfd/(?:sm|samsung/pmic)|regulator/samsung/pmic)/",
    "thermal": r"^drivers/thermal/samsung/",
    "build_toolchain": r"^(?:Makefile$|Kbuild$|build\.config|build.*\.sh$|arch/arm64/Makefile$)",
}


def paths_for_state(data: dict, state: str) -> set[str]:
    paths: set[str] = set()
    for category in data.get("categories", {}).values():
        for item in category.get(state, []):
            paths.add(item["path"] if isinstance(item, dict) else item)
    return paths


def build_summary(data: dict) -> dict:
    states = {
        "changed": paths_for_state(data, "changed"),
        "u3_only": paths_for_state(data, "u3_only"),
        "u11_only": paths_for_state(data, "u11_only"),
    }
    result = {"schema_version": 1, "source": "comparison.json", "subsystems": {}}
    for name, expression in SUBSYSTEMS.items():
        pattern = re.compile(expression)
        matches = {
            state: sorted(path for path in paths if pattern.search(path))
            for state, paths in states.items()
        }
        result["subsystems"][name] = {
            "pattern": expression,
            "counts": {state: len(paths) for state, paths in matches.items()},
            "paths": matches,
        }
    return result


def markdown(summary: dict) -> str:
    lines = [
        "# Resumen de cambios U3 → U11 por subsistema",
        "",
        "Los números cuentan rutas cuyo contenido/presencia cambia. No prueban por sí",
        "solos compatibilidad de hardware; deben leerse junto al diff semántico DTS.",
        "",
        "| subsistema | cambiados | sólo U3 | sólo U11 | ejemplos |",
        "|---|---:|---:|---:|---|",
    ]
    for name, entry in summary["subsystems"].items():
        counts = entry["counts"]
        examples = (entry["paths"]["changed"] + entry["paths"]["u11_only"])[:3]
        rendered = "<br>".join(f"`{path}`" for path in examples) or "—"
        lines.append(
            f"| `{name}` | {counts['changed']} | {counts['u3_only']} | "
            f"{counts['u11_only']} | {rendered} |"
        )
    lines.append("")
    return "\n".join(lines)


def atomic_write(path: Path, contents: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(contents)
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("comparison", type=Path)
    parser.add_argument("--json", dest="json_output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()
    with args.comparison.open(encoding="utf-8") as stream:
        data = json.load(stream)
    summary = build_summary(data)
    atomic_write(args.json_output, json.dumps(summary, indent=2, sort_keys=True) + "\n")
    atomic_write(args.markdown, markdown(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
