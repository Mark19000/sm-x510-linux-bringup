#!/usr/bin/env python3
"""
compare-build-runs.py: Compare SHA-256 checksums and file sizes between two build runs.
"""

import os
import sys
import argparse

def parse_sha256sums(path):
    entries = {}
    if not os.path.isfile(path):
        return entries
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            parts = line.strip().split(None, 1)
            if len(parts) == 2:
                h, fn = parts[0], parts[1].strip()
                # Normalize filename: remove leading ./
                if fn.startswith('./'):
                    fn = fn[2:]
                entries[fn] = h
    return entries

def main():
    parser = argparse.ArgumentParser(description="Compare two build runs")
    parser.add_argument("--run-a", required=True, help="Path to dist directory or SHA256SUMS for Run A")
    parser.add_argument("--run-b", required=True, help="Path to dist directory or SHA256SUMS for Run B")
    parser.add_argument("--name-a", default="Run A (fixed1)", help="Display label for Run A")
    parser.add_argument("--name-b", default="Run B (fixed2)", help="Display label for Run B")
    parser.add_argument("--md-out", default=None, help="Markdown output file")
    args = parser.parse_args()

    file_a = args.run_a if os.path.isfile(args.run_a) else os.path.join(args.run_a, "SHA256SUMS")
    file_b = args.run_b if os.path.isfile(args.run_b) else os.path.join(args.run_b, "SHA256SUMS")

    sums_a = parse_sha256sums(file_a)
    sums_b = parse_sha256sums(file_b)

    all_files = sorted(set(sums_a.keys()) | set(sums_b.keys()))

    matches = []
    diffs = []
    only_a = []
    only_b = []

    for fn in all_files:
        if fn in sums_a and fn in sums_b:
            if sums_a[fn] == sums_b[fn]:
                matches.append((fn, sums_a[fn]))
            else:
                diffs.append((fn, sums_a[fn], sums_b[fn]))
        elif fn in sums_a:
            only_a.append((fn, sums_a[fn]))
        else:
            only_b.append((fn, sums_b[fn]))

    print("=" * 70)
    print(f"BUILD REPRODUCIBILITY COMPARISON: {args.name_a} vs {args.name_b}")
    print("=" * 70)
    print(f"Total files compared: {len(all_files)}")
    print(f"Byte-identical files: {len(matches)}")
    print(f"Differing files:      {len(diffs)}")
    print(f"Only in {args.name_a}: {len(only_a)}")
    print(f"Only in {args.name_b}: {len(only_b)}")
    print("=" * 70)

    if matches:
        print("\nByte-Identical Artifacts (100% Deterministic):")
        for fn, h in matches:
            print(f"  [OK] {fn:<35} : {h}")

    if diffs:
        print("\nDiffering Artifacts:")
        for fn, ha, hb in diffs:
            print(f"  [DIFF] {fn}:")
            print(f"     A: {ha}")
            print(f"     B: {hb}")

    if args.md_out:
        os.makedirs(os.path.dirname(os.path.abspath(args.md_out)), exist_ok=True)
        with open(args.md_out, 'w', encoding='utf-8') as f:
            f.write(f"### Reproducibility Comparison: {args.name_a} vs {args.name_b}\n\n")
            f.write(f"- **Total Files**: {len(all_files)}\n")
            f.write(f"- **Byte-Identical Matches**: {len(matches)} / {len(all_files)}\n")
            f.write(f"- **Differing Files**: {len(diffs)}\n\n")
            f.write("| Artifact | Hash in " + args.name_a + " | Hash in " + args.name_b + " | Status |\n")
            f.write("| :--- | :--- | :--- | :---: |\n")
            for fn, h in matches:
                f.write(f"| `{fn}` | `{h[:16]}...` | `{h[:16]}...` | **MATCH** |\n")
            for fn, ha, hb in diffs:
                f.write(f"| `{fn}` | `{ha[:16]}...` | `{hb[:16]}...` | **DIFF** |\n")
            for fn, ha in only_a:
                f.write(f"| `{fn}` | `{ha[:16]}...` | `(missing)` | **ONLY_A** |\n")
            for fn, hb in only_b:
                f.write(f"| `{fn}` | `(missing)` | `{hb[:16]}...` | **ONLY_B** |\n")
            f.write("\n")
        print(f"Saved markdown report to {args.md_out}")

if __name__ == "__main__":
    main()
