#!/usr/bin/env python3
"""
verify-eze4-abi.py: Cross-check CONFIG_MODVERSIONS CRCs and vermagic
between stock vendor_boot DLKM modules and built Module.symvers.
"""

import os
import sys
import glob
import struct
import argparse
import subprocess
import json
from collections import defaultdict

def parse_module_symvers(symvers_path):
    """
    Parse Module.symvers into a dict:
    symbol_name -> {'crc': '0x12345678', 'location': 'vmlinux', 'type': 'EXPORT_SYMBOL'}
    """
    syms = {}
    if not os.path.isfile(symvers_path):
        raise FileNotFoundError(f"Module.symvers not found at {symvers_path}")

    with open(symvers_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 2:
                crc_str = parts[0].strip().lower()
                sym_name = parts[1].strip()
                loc = parts[2].strip() if len(parts) > 2 else ""
                exp_type = parts[3].strip() if len(parts) > 3 else ""
                crc_val = int(crc_str, 16)
                syms[sym_name] = {
                    'crc': f"0x{crc_val:08x}",
                    'location': loc,
                    'type': exp_type
                }
    return syms

def extract_modversions_from_ko(ko_path, llvm_objcopy="llvm-objcopy"):
    """
    Extract symbols and CRCs from __versions section of an ELF .ko file.
    Returns dict: sym_name -> crc_hex (e.g. '0x0222dd63')
    """
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_name = tmp.name
    try:
        cmd = [llvm_objcopy, f'--dump-section=__versions={tmp_name}', ko_path]
        res = subprocess.run(cmd, capture_output=True)
        if res.returncode != 0:
            return {}
        with open(tmp_name, 'rb') as f:
            data = f.read()
        syms = {}
        for i in range(0, len(data), 64):
            entry = data[i:i+64]
            if len(entry) < 64:
                break
            crc = struct.unpack('<Q', entry[:8])[0] & 0xFFFFFFFF
            name = entry[8:].split(b'\x00', 1)[0].decode('ascii', errors='ignore')
            if name:
                syms[name] = f"0x{crc:08x}"
        return syms
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)

def extract_modinfo(ko_path):
    """
    Run modinfo to extract vermagic and other fields.
    """
    cmd = ['modinfo', ko_path]
    res = subprocess.run(cmd, capture_output=True, text=True)
    info = {}
    if res.returncode == 0:
        for line in res.stdout.splitlines():
            if ':' in line:
                k, v = line.split(':', 1)
                info[k.strip()] = v.strip()
    return info

def main():
    parser = argparse.ArgumentParser(description="Audit ABI & Modversions CRC Parity")
    parser.add_argument("--symvers", required=True, help="Path to built Module.symvers")
    parser.add_argument("--stock-modules-dir", required=True, help="Directory containing stock .ko files")
    parser.add_argument("--built-modules-dir", default=None, help="Directory containing built .ko files")
    parser.add_argument("--json-out", default=None, help="Path to write output JSON")
    parser.add_argument("--md-out", default=None, help="Path to write output Markdown")
    args = parser.parse_args()

    print(f"Loading built Module.symvers from {args.symvers}...")
    built_syms = parse_module_symvers(args.symvers)
    print(f"Loaded {len(built_syms)} exported symbols from Module.symvers.")

    stock_ko_files = sorted(glob.glob(os.path.join(args.stock_modules_dir, "**", "*.ko"), recursive=True))
    print(f"Found {len(stock_ko_files)} stock .ko files in {args.stock_modules_dir}.")

    if not stock_ko_files:
        print("ERROR: No stock .ko files found!")
        sys.exit(1)

    # Core modules of special interest for early boot
    early_boot_targets = [
        "exynos-chipid_v2.ko",
        "clk_exynos.ko",
        "exynos_mct_v3.ko",
        "ufs-exynos.ko",
        "dwc3-exynos-usb.ko",
        "sec_debug.ko",
        "s2mpu15_mfd.ko",
        "s2mpu16_mfd.ko",
        "ems.ko",
        "zram.ko",
        "mali_kbase.ko"
    ]

    results = {
        "summary": {
            "total_stock_modules": len(stock_ko_files),
            "modules_perfect_match": 0,
            "modules_with_crc_mismatches": 0,
            "modules_with_missing_symbols": 0,
            "total_symbols_referenced": 0,
            "total_symbols_matched": 0,
            "total_symbols_mismatched": 0,
            "total_symbols_missing": 0,
        },
        "early_boot": {},
        "mismatched_symbols_frequency": defaultdict(int),
        "missing_symbols_frequency": defaultdict(int),
        "per_module": {}
    }

    vermagic_set = set()

    for ko in stock_ko_files:
        mod_name = os.path.basename(ko)
        info = extract_modinfo(ko)
        vm = info.get("vermagic", "UNKNOWN")
        vermagic_set.add(vm)

        needed_syms = extract_modversions_from_ko(ko)
        mod_stats = {
            "vermagic": vm,
            "total_needed": len(needed_syms),
            "matched": 0,
            "mismatched": [],
            "missing": []
        }

        results["summary"]["total_symbols_referenced"] += len(needed_syms)

        for sym, stock_crc in needed_syms.items():
            if sym in built_syms:
                built_crc = built_syms[sym]['crc']
                if stock_crc.lower() == built_crc.lower():
                    mod_stats["matched"] += 1
                    results["summary"]["total_symbols_matched"] += 1
                else:
                    mod_stats["mismatched"].append({
                        "symbol": sym,
                        "stock_crc": stock_crc,
                        "built_crc": built_crc,
                        "location": built_syms[sym]['location']
                    })
                    results["summary"]["total_symbols_mismatched"] += 1
                    results["mismatched_symbols_frequency"][sym] += 1
            else:
                mod_stats["missing"].append({
                    "symbol": sym,
                    "stock_crc": stock_crc
                })
                results["summary"]["total_symbols_missing"] += 1
                results["missing_symbols_frequency"][sym] += 1

        if len(mod_stats["mismatched"]) == 0 and len(mod_stats["missing"]) == 0:
            results["summary"]["modules_perfect_match"] += 1
        if len(mod_stats["mismatched"]) > 0:
            results["summary"]["modules_with_crc_mismatches"] += 1
        if len(mod_stats["missing"]) > 0:
            results["summary"]["modules_with_missing_symbols"] += 1

        results["per_module"][mod_name] = mod_stats

        if any(target in mod_name for target in early_boot_targets):
            results["early_boot"][mod_name] = mod_stats

    # Convert defaultdicts for serialization
    results["mismatched_symbols_frequency"] = dict(sorted(results["mismatched_symbols_frequency"].items(), key=lambda x: x[1], reverse=True))
    results["missing_symbols_frequency"] = dict(sorted(results["missing_symbols_frequency"].items(), key=lambda x: x[1], reverse=True))
    results["vermagic_distinct"] = list(vermagic_set)

    # Print console summary
    tot_syms = results["summary"]["total_symbols_referenced"]
    matched_syms = results["summary"]["total_symbols_matched"]
    pct = (matched_syms / tot_syms * 100.0) if tot_syms > 0 else 0.0

    print("=" * 60)
    print("ABI / MODVERSIONS CRC VALIDATION RESULTS")
    print("=" * 60)
    print(f"Total Stock Modules Audited:       {results['summary']['total_stock_modules']}")
    print(f"Modules with 100% Symbol Match:    {results['summary']['modules_perfect_match']} / {results['summary']['total_stock_modules']}")
    print(f"Modules with CRC Mismatches:       {results['summary']['modules_with_crc_mismatches']}")
    print(f"Modules with Missing Symbols:      {results['summary']['modules_with_missing_symbols']}")
    print(f"Total Symbol References:           {tot_syms}")
    print(f"Total Symbols Matched (CRC exact): {matched_syms} ({pct:.2f}%)")
    print(f"Total Symbols Mismatched (CRC):    {results['summary']['total_symbols_mismatched']}")
    print(f"Total Symbols Missing in symvers:  {results['summary']['total_symbols_missing']}")
    print(f"Distinct Vermagic in Stock:        {results['vermagic_distinct']}")
    print("=" * 60)

    print("\nEarly Boot Modules Parity Table:")
    print(f"{'Module Name':<28} | {'Total':<6} | {'Matched':<7} | {'Mismatched':<10} | {'Missing':<7} | {'Status'}")
    print("-" * 75)
    for mod_name, stats in sorted(results["early_boot"].items()):
        status = "PERFECT" if len(stats["mismatched"]) == 0 and len(stats["missing"]) == 0 else "MISMATCH"
        print(f"{mod_name:<28} | {stats['total_needed']:<6} | {stats['matched']:<7} | {len(stats['mismatched']):<10} | {len(stats['missing']):<7} | {status}")

    if results["mismatched_symbols_frequency"]:
        print("\nTop 15 Mismatched Symbols:")
        for sym, count in list(results["mismatched_symbols_frequency"].items())[:15]:
            print(f"  {sym:<35} : referenced by {count} modules")

    if results["missing_symbols_frequency"]:
        print("\nTop 15 Missing Symbols:")
        for sym, count in list(results["missing_symbols_frequency"].items())[:15]:
            print(f"  {sym:<35} : referenced by {count} modules")

    if args.json_out:
        os.makedirs(os.path.dirname(os.path.abspath(args.json_out)), exist_ok=True)
        with open(args.json_out, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        print(f"\nWrote detailed JSON results to {args.json_out}")

    if args.md_out:
        os.makedirs(os.path.dirname(os.path.abspath(args.md_out)), exist_ok=True)
        with open(args.md_out, 'w', encoding='utf-8') as f:
            f.write("# CONFIG_MODVERSIONS CRC Parity Audit Report\n\n")
            f.write("## Executive Summary\n\n")
            f.write(f"- **Total Stock Modules Audited**: {results['summary']['total_stock_modules']}\n")
            f.write(f"- **Stock Vermagic**: `{', '.join(results['vermagic_distinct'])}`\n")
            f.write(f"- **Modules with 100% Symbol Match**: {results['summary']['modules_perfect_match']} / {results['summary']['total_stock_modules']}\n")
            f.write(f"- **Total Symbol References**: {tot_syms}\n")
            f.write(f"- **Total Matched CRCs**: {matched_syms} ({pct:.2f}%)\n")
            f.write(f"- **Total Mismatched CRCs**: {results['summary']['total_symbols_mismatched']}\n")
            f.write(f"- **Total Missing Symbols**: {results['summary']['total_symbols_missing']}\n\n")
            f.write("## Early-Boot Critical Drivers Parity\n\n")
            f.write("| Module Name | Total Symbols | Matched | Mismatched | Missing | Parity Status |\n")
            f.write("| :--- | :---: | :---: | :---: | :---: | :---: |\n")
            for mod_name, stats in sorted(results["early_boot"].items()):
                status = "PERFECT_MATCH" if len(stats["mismatched"]) == 0 and len(stats["missing"]) == 0 else "MISMATCH"
                f.write(f"| `{mod_name}` | {stats['total_needed']} | {stats['matched']} | {len(stats['mismatched'])} | {len(stats['missing'])} | `{status}` |\n")
            f.write("\n")
            if results["mismatched_symbols_frequency"]:
                f.write("## Most Frequent CRC Mismatches\n\n")
                f.write("| Symbol Name | Referenced Count | Sample Stock CRC | Sample Built CRC |\n")
                f.write("| :--- | :---: | :---: | :---: |\n")
                for sym, count in list(results["mismatched_symbols_frequency"].items())[:20]:
                    sample = None
                    for m in results["per_module"].values():
                        for mis in m["mismatched"]:
                            if mis["symbol"] == sym:
                                sample = mis
                                break
                        if sample: break
                    st_crc = sample["stock_crc"] if sample else "N/A"
                    bu_crc = sample["built_crc"] if sample else "N/A"
                    f.write(f"| `{sym}` | {count} | `{st_crc}` | `{bu_crc}` |\n")
        print(f"Wrote Markdown summary to {args.md_out}")

if __name__ == "__main__":
    main()
