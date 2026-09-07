#!/usr/bin/env python3
"""Fail-closed structural and documentation gate for Phase J2 closure."""

import ast
import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
DOCS = ROOT / "docs" / "rmg-eze4"
ANALYSIS = ROOT / "tools" / "rmg-eze4" / "analysis"


def errors() -> list[str]:
    failures: list[str] = []

    # No active J2 implementation module may depend on the historical engine.
    for path in ANALYSIS.glob("*.py"):
        if path.name == "engine.py":
            continue
        for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[-1] for alias in node.names]
                if "engine" in names:
                    failures.append(f"LEGACY_ENGINE_IMPORT:{path.relative_to(ROOT)}")
            elif isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[-1] == "engine":
                failures.append(f"LEGACY_ENGINE_IMPORT:{path.relative_to(ROOT)}")

    required_docs = {
        "CANONICAL_STATUS.md": ["RMG/EZE4/Phase J2", "J2 COMPLETE"],
        "J2_FINAL_STATUS.md": ["J2 COMPLETE", "OWNER_UNLOCK_DECISION_READY"],
        "audit/J2_CLOSURE_AUDIT.md": ["Oracle independence", "Final verdict"],
    }
    for rel, tokens in required_docs.items():
        path = DOCS / rel
        if not path.is_file():
            failures.append(f"MISSING_DOCUMENT:{rel}")
            continue
        text = path.read_text()
        for token in tokens:
            if token not in text:
                failures.append(f"DOCUMENT_TOKEN_MISSING:{rel}:{token}")

    for rel in [
        "audit/DUPLICATED_TRUTH.csv",
        "audit/TEST_ORACLE_MAP.csv",
        "audit/ACTIVE_SUPERSEDED_REFERENCES.csv",
    ]:
        path = DOCS / rel
        try:
            with path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            if not rows:
                failures.append(f"EMPTY_AUDIT_CSV:{rel}")
        except (OSError, csv.Error) as exc:
            failures.append(f"INVALID_AUDIT_CSV:{rel}:{exc}")

    # Canonical J2 docs must be portable repository references.
    for path in [DOCS / "CANONICAL_STATUS.md", DOCS / "J2_FINAL_STATUS.md"]:
        if path.is_file():
            text = path.read_text()
            if "file:///Users/" in text or "/Users/markpi/" in text:
                failures.append(f"ABSOLUTE_LOCAL_REFERENCE:{path.relative_to(ROOT)}")

    return failures


def main() -> int:
    failures = errors()
    if failures:
        print("FAIL: J2 closure structural errors:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("PASS: J2 closure documents, audit CSVs, and legacy-engine guard")
    return 0


if __name__ == "__main__":
    sys.exit(main())
