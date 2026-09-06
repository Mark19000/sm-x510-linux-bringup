#!/usr/bin/env python3
"""
tools/rmg-eze4/generate_p0_fingerprint.py

Deterministic P0 KASLR Fingerprint Table Generator and Verifier
for Samsung Galaxy Tab S9 FE Wi-Fi (SM-X510 / Exynos 1380 / gts9fewifi)
and compatible ARM64 Samsung kernel targets.

Standard Library only (Python 3.8+).
"""

import argparse
import hashlib
import os
import re
import struct
import sys
from typing import List, Tuple, Dict, Optional

P0_FINGERPRINT_OFFSETS = (
    0x000, 0x200, 0x400, 0x600,
    0x800, 0xa00, 0xc00, 0xe00,
)
P0_FINGERPRINT_WORDS = len(P0_FINGERPRINT_OFFSETS)


def auto_int(val: str) -> int:
    """Parse integer from hex (0x...) or decimal string."""
    val = val.strip()
    if val.startswith(("0x", "0X")):
        return int(val, 16)
    return int(val, 10)


def compute_sha256(filepath: str, block_size: int = 65536) -> str:
    """Compute SHA-256 hash of a file."""
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(block_size):
            sha.update(chunk)
    return sha.hexdigest()


def extract_fingerprints(
    image_bytes: bytes,
    probe_offset: int,
    step: int,
) -> List[Tuple[int, int, List[int]]]:
    """
    Extract fingerprint rows from image buffer.
    Returns list of (slide, page_source_offset, [word0, ..., word7]).
    """
    image_len = len(image_bytes)
    rows: List[Tuple[int, int, List[int]]] = []

    slide = 0
    while slide <= probe_offset:
        page_source = probe_offset - slide
        if page_source < 0:
            raise ValueError(f"Slide 0x{slide:x} exceeds probe offset 0x{probe_offset:x}")

        words: List[int] = []
        for page_offset in P0_FINGERPRINT_OFFSETS:
            source_offset = page_source + page_offset
            if source_offset + 8 > image_len:
                raise ValueError(
                    f"Source offset 0x{source_offset:x} (+8) exceeds image length 0x{image_len:x}"
                )
            word = struct.unpack_from("<Q", image_bytes, source_offset)[0]
            words.append(word)

        rows.append((slide, page_source, words))
        slide += step

    return rows


def verify_readback(
    image_path: str,
    rows: List[Tuple[int, int, List[int]]],
) -> bool:
    """Reopen the raw image file and verify each extracted QWORD independently."""
    with open(image_path, "rb") as f:
        for slide, page_source, words in rows:
            for idx, page_offset in enumerate(P0_FINGERPRINT_OFFSETS):
                src_off = page_source + page_offset
                f.seek(src_off)
                chunk = f.read(8)
                if len(chunk) != 8:
                    raise IOError(f"Short read at 0x{src_off:x} for slide 0x{slide:x}")
                val = struct.unpack("<Q", chunk)[0]
                if val != words[idx]:
                    raise AssertionError(
                        f"Readback mismatch at slide 0x{slide:x} (source 0x{src_off:x}): "
                        f"expected 0x{words[idx]:016x}, got 0x{val:016x}"
                    )
    return True


def format_header(rows: List[Tuple[int, int, List[int]]], probe_offset: int, step: int) -> str:
    """Format fingerprints into C header string."""
    lines = [
        "// Generated from the exact raw Image.",
        f"// Probe offset 0x{probe_offset:x}, step 0x{step:x} ({len(rows)} candidates).",
        "#ifndef P0_FINGERPRINT_H",
        "#define P0_FINGERPRINT_H",
        "",
        f"#define P0_FINGERPRINT_WORDS {P0_FINGERPRINT_WORDS}",
        "",
        "static const uint16_t p0_fingerprint_offsets[P0_FINGERPRINT_WORDS] = {",
        "  0x000, 0x200, 0x400, 0x600, 0x800, 0xa00, 0xc00, 0xe00,",
        "};",
        "",
        "struct p0_fingerprint {",
        "  uintptr_t slide;",
        "  uint64_t words[P0_FINGERPRINT_WORDS];",
        "};",
        "",
        "static const struct p0_fingerprint p0_fingerprints[] = {",
    ]
    for slide, _, words in rows:
        lines.append(f"  {{ 0x{slide:06x}ULL, {{ 0x{words[0]:016x}ULL, 0x{words[1]:016x}ULL,")
        lines.append(f"    0x{words[2]:016x}ULL, 0x{words[3]:016x}ULL,")
        lines.append(f"    0x{words[4]:016x}ULL, 0x{words[5]:016x}ULL,")
        lines.append(f"    0x{words[6]:016x}ULL, 0x{words[7]:016x}ULL }} }},")
    lines.append("};")
    lines.append("")
    lines.append("#endif")
    lines.append("")
    return "\n".join(lines)


def format_csv(rows: List[Tuple[int, int, List[int]]]) -> str:
    """Format fingerprints into CSV string."""
    header = "slide,image_offset,word_000,word_200,word_400,word_600,word_800,word_a00,word_c00,word_e00\n"
    lines = [header]
    for slide, page_source, words in rows:
        word_strs = [f"0x{w:016x}" for w in words]
        lines.append(f"0x{slide:06x},0x{page_source:06x}," + ",".join(word_strs) + "\n")
    return "".join(lines)


def parse_header_file(header_path: str) -> Dict[int, List[int]]:
    """Parse an existing p0_fingerprint.h file into a dict of slide -> 8 words."""
    result: Dict[int, List[int]] = {}
    with open(header_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Match each struct entry: { 0xXXXXXXULL, { 0x...ULL, ... } }
    pattern = re.compile(
        r'\{\s*(0x[0-9a-fA-F]+)ULL\s*,\s*\{\s*([^}]+)\s*\}\s*\}',
        re.MULTILINE
    )
    for match in pattern.finditer(content):
        slide_str = match.group(1)
        slide_val = int(slide_str, 16)
        words_blob = match.group(2)
        hex_words = re.findall(r'(0x[0-9a-fA-F]+)ULL', words_blob)
        if len(hex_words) != P0_FINGERPRINT_WORDS:
            continue
        words = [int(hw, 16) for hw in hex_words]
        result[slide_val] = words
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Deterministic P0 KASLR Fingerprint Table Generator and Verifier."
    )
    parser.add_argument(
        "--image", required=True,
        help="Path to raw kernel Image (binary)."
    )
    parser.add_argument(
        "--probe-offset", type=auto_int, default=0x1f0000,
        help="Physical P0 probe offset (default: 0x1f0000 / 2MB)."
    )
    parser.add_argument(
        "--step", type=auto_int, default=0x4000,
        help="KASLR slide step (default: 0x4000 / 16KB; use 0x10000 for 64KB devices)."
    )
    parser.add_argument(
        "--output-header", default=None,
        help="Optional path to write generated p0_fingerprint.h header file."
    )
    parser.add_argument(
        "--output-csv", default=None,
        help="Optional path to write generated CSV table."
    )
    parser.add_argument(
        "--verify-header", default=None,
        help="Optional path to an existing p0_fingerprint.h to verify against."
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable verbose output."
    )

    args = parser.parse_args()

    # 1. Validate Image existence
    if not os.path.isfile(args.image):
        print(f"[-] ERROR: Image file not found: {args.image}", file=sys.stderr)
        sys.exit(1)

    file_size = os.path.getsize(args.image)
    file_sha256 = compute_sha256(args.image)

    print(f"[*] Raw Kernel Image: {args.image}")
    print(f"[*] Size: {file_size} bytes ({file_size / (1024*1024):.2f} MB)")
    print(f"[*] SHA-256: {file_sha256}")
    print(f"[*] Probe Offset: 0x{args.probe_offset:x} ({args.probe_offset} bytes)")
    print(f"[*] Slide Step:   0x{args.step:x} ({args.step} bytes)")

    expected_rows = (args.probe_offset // args.step) + 1
    print(f"[*] Calculated Table Rows: {expected_rows} candidate slides")

    # 2. Extract fingerprints
    with open(args.image, "rb") as f:
        image_bytes = f.read()

    rows = extract_fingerprints(image_bytes, args.probe_offset, args.step)
    if len(rows) != expected_rows:
        print(f"[-] ERROR: Extracted {len(rows)} rows, expected {expected_rows}", file=sys.stderr)
        sys.exit(1)

    # 3. Deterministic readback verification
    verify_readback(args.image, rows)
    print(f"[+] Readback verification passed: {len(rows)} rows x {P0_FINGERPRINT_WORDS} QWORDs verified 100%.")

    # 4. Compare with reference header if requested
    if args.verify_header:
        if not os.path.isfile(args.verify_header):
            print(f"[-] ERROR: Verification header not found: {args.verify_header}", file=sys.stderr)
            sys.exit(1)

        ref_table = parse_header_file(args.verify_header)
        print(f"[*] Parsed {len(ref_table)} entries from reference header: {args.verify_header}")

        exact_rows = 0
        total_matched_words = 0
        total_words = len(rows) * P0_FINGERPRINT_WORDS

        for slide, page_src, words in rows:
            if slide not in ref_table:
                if args.verbose:
                    print(f"[-] Slide 0x{slide:06x} missing from reference table")
                continue

            ref_words = ref_table[slide]
            score = sum(1 for i in range(P0_FINGERPRINT_WORDS) if words[i] == ref_words[i])
            total_matched_words += score

            if score == P0_FINGERPRINT_WORDS:
                exact_rows += 1
            elif args.verbose:
                print(f"[~] Slide 0x{slide:06x}: {score}/8 matched (source 0x{page_src:06x})")

        match_pct = (total_matched_words / total_words) * 100.0 if total_words else 0.0
        print(f"[+] Comparison against reference header:")
        print(f"    - Exact 8/8 matched rows: {exact_rows} / {len(rows)} ({exact_rows/len(rows)*100:.2f}%)")
        print(f"    - Total words matched:    {total_matched_words} / {total_words} ({match_pct:.2f}%)")

    # 5. Output header if requested
    if args.output_header:
        header_content = format_header(rows, args.probe_offset, args.step)
        with open(args.output_header, "w", encoding="utf-8") as f:
            f.write(header_content)
        print(f"[+] Written C header to: {args.output_header}")

    # 6. Output CSV if requested
    if args.output_csv:
        csv_content = format_csv(rows)
        with open(args.output_csv, "w", encoding="utf-8") as f:
            f.write(csv_content)
        print(f"[+] Written CSV table to: {args.output_csv}")

    print("[+] Done.")


if __name__ == "__main__":
    main()
