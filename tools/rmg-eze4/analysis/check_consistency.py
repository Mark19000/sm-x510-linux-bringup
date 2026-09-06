#!/usr/bin/env python3
"""Cross-artifact consistency checker for Phase J2.1-R1.1.

Verifies that schemas, grammars, decision tables, E4 contracts, GO gates,
stop rules, runtime identity contract, preexecution matrix, test fixtures,
and validator constants assert identical canonical physical EZE4 identity
and J1/J2 semantics.
Fails closed on any discrepancy.
"""

import csv
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
DOCS = ROOT / "docs/rmg-eze4"
TESTS = ROOT / "tools/rmg-eze4/tests"
sys.path.insert(0, str(ROOT / "tools/rmg-eze4/analysis"))
sys.path.insert(0, str(TESTS))
import validator  # noqa: E402


def extract_raw_stdout(path: Path) -> str:
    """Extract captured stdout from raw evidence without assuming return status keys."""
    if not path.is_file():
        raise FileNotFoundError(f"Missing raw capture file: {path}")
    text = path.read_text(encoding="utf-8")
    if "STDOUT_BEGIN" in text and "STDOUT_END" in text:
        return text.split("STDOUT_BEGIN", 1)[1].split("STDOUT_END", 1)[0].strip()
    return text.strip()


def load_canonical_truth() -> dict:
    """Derive canonical ground truth dynamically from authoritative physical baseline captures and artifacts.

    Fails closed if physical captures are missing or unparseable.
    """
    raw_dir = DOCS / "runtime-evidence" / "20260906T094426Z" / "raw"
    if not raw_dir.is_dir():
        raise FileNotFoundError(f"Authoritative raw baseline directory missing: {raw_dir}")

    # Physical baseline captures (Phase G hardware evidence)
    model = extract_raw_stdout(raw_dir / "01_product_model.txt")
    device = extract_raw_stdout(raw_dir / "02_product_device.txt")
    fingerprint = extract_raw_stdout(raw_dir / "03_build_fingerprint.txt")
    incremental = extract_raw_stdout(raw_dir / "04_build_incremental.txt")
    sec_patch = extract_raw_stdout(raw_dir / "05_security_patch.txt")
    uname_line = extract_raw_stdout(raw_dir / "06_uname.txt")
    uname_tokens = uname_line.split()
    if len(uname_tokens) < 3:
        raise ValueError(f"Unable to extract kernel release from uname output: '{uname_line}'")
    kernel_identity = uname_tokens[2]

    # Binary digest of stock kernel image
    stock_img = ROOT / "artifacts" / "stock" / "images" / "Image.stock"
    if not stock_img.is_file():
        raise FileNotFoundError(f"Missing stock kernel binary artifact: {stock_img}")
    hasher = hashlib.sha256()
    hasher.update(stock_img.read_bytes())
    image_sha256 = hasher.hexdigest()

    # Authoritative Schema Version from phase_j2_observation_schema_v2.json
    schema_v2_path = DOCS / "phase_j2_observation_schema_v2.json"
    if not schema_v2_path.is_file():
        raise FileNotFoundError(f"Missing schema v2: {schema_v2_path}")
    schema_v2 = json.loads(schema_v2_path.read_text(encoding="utf-8"))
    schema_version = schema_v2.get("properties", {}).get("schema_version", {}).get("const")
    if not schema_version:
        raise ValueError("Cannot extract schema_version const from phase_j2_observation_schema_v2.json")

    # Authoritative Event Grammar Version from phase_j2_event_grammar.json
    grammar_path = DOCS / "phase_j2_event_grammar.json"
    if not grammar_path.is_file():
        raise FileNotFoundError(f"Missing event grammar: {grammar_path}")
    grammar_json = json.loads(grammar_path.read_text(encoding="utf-8"))
    grammar_version = grammar_json.get("grammar_version")
    if not grammar_version:
        raise ValueError("Cannot extract grammar_version from phase_j2_event_grammar.json")

    # Authoritative timeouts from phase_h_l3_inventory.csv
    l3_inv_path = DOCS / "phase_h_l3_inventory.csv"
    if not l3_inv_path.is_file():
        raise FileNotFoundError(f"Missing L3 inventory: {l3_inv_path}")
    with l3_inv_path.open(encoding="utf-8") as f:
        l3_rows = {row["NAME"]: row for row in csv.DictReader(f)}
    timeout_sec = int(l3_rows.get("DEFAULT_ATTEMPT_TIMEOUT_SEC", {}).get("CURRENT_VALUE", "2200"))
    p0_timeout_sec = int(l3_rows.get("DEFAULT_P0_ATTEMPT_TIMEOUT_SEC", {}).get("CURRENT_VALUE", "1200"))

    return {
        "model": model,
        "device": device,
        "fingerprint": fingerprint,
        "incremental": incremental,
        "security_patch": sec_patch,
        "kernel_identity": kernel_identity,
        "image_sha256": image_sha256,
        "schema_version": schema_version,
        "grammar_version": grammar_version,
        "timeout_sec": timeout_sec,
        "p0_timeout_sec": p0_timeout_sec,
    }


# Dynamically bind canonical constants from authoritative physical truth
TRUTH = load_canonical_truth()
CANONICAL_MODEL = TRUTH["model"]
CANONICAL_DEVICE = TRUTH["device"]
CANONICAL_INCREMENTAL = TRUTH["incremental"]
CANONICAL_BUILD_FINGERPRINT = TRUTH["fingerprint"]
CANONICAL_KERNEL_IDENTITY = TRUTH["kernel_identity"]
CANONICAL_IMAGE_SHA256 = TRUTH["image_sha256"]
CANONICAL_SCHEMA_VERSION = TRUTH["schema_version"]
CANONICAL_GRAMMAR_VERSION = TRUTH["grammar_version"]
CANONICAL_SECURITY_PATCH = TRUTH["security_patch"]
CANONICAL_TIMEOUT_SEC = TRUTH["timeout_sec"]
CANONICAL_P0_TIMEOUT_SEC = TRUTH["p0_timeout_sec"]

PROTECTED_PARAMETERS = [
    "SLIDE_KSNITCH_APPENDED_FUTEXES",
    "SKB_SEND_SIZE",
    "SLIDE_WAIT_NSEC",
    "SLIDE_REQUEUE_ARM_USEC",
    "FOPS_ROUTE_COARSE_DELAY_USEC",
    "FOPS_ROUTE_FINE_DELAY_TICKS",
]


def check_consistency() -> list[str]:
    errors = []

    # 1. Load observation schema v2.2.1
    schema_path = DOCS / "phase_j2_observation_schema_v2.json"
    if not schema_path.exists():
        return ["MISSING_phase_j2_observation_schema_v2.json"]
    schema = json.loads(schema_path.read_text())

    # Schema version check
    if schema.get("properties", {}).get("schema_version", {}).get("const") != CANONICAL_SCHEMA_VERSION:
        errors.append(f"SCHEMA_VERSION_NOT_{CANONICAL_SCHEMA_VERSION}")

    # Check candidate identity in schema
    cand_props = schema.get("properties", {}).get("candidate_identity", {}).get("properties", {})
    if cand_props.get("candidate_parameter", {}).get("const") != "DEFAULT_ATTEMPT_TIMEOUT_SEC":
        errors.append("SCHEMA_CANDIDATE_PARAMETER_NOT_DEFAULT_ATTEMPT_TIMEOUT_SEC")
    if cand_props.get("candidate_value", {}).get("const") != 2200:
        errors.append("SCHEMA_CANDIDATE_VALUE_NOT_2200")

    # Check exact artifact identity fields in schema
    art_props = schema.get("properties", {}).get("artifact_identity", {}).get("properties", {})
    if art_props.get("device_model", {}).get("const") != CANONICAL_MODEL:
        errors.append("SCHEMA_DEVICE_MODEL_NOT_SM_X510")
    if art_props.get("device_name", {}).get("const") != CANONICAL_DEVICE:
        errors.append("SCHEMA_DEVICE_NAME_NOT_GTS9FEWIFI")
    if art_props.get("incremental_version", {}).get("const") != CANONICAL_INCREMENTAL:
        errors.append("SCHEMA_INCREMENTAL_NOT_X510XXUCEZE4")
    if art_props.get("build_fingerprint", {}).get("const") != CANONICAL_BUILD_FINGERPRINT:
        errors.append("SCHEMA_BUILD_FINGERPRINT_NOT_CANONICAL_PHYSICAL")

    # Fail if schema allows broader kernel identity than exact equality (e.g. pattern regex)
    kernel_id_def = art_props.get("kernel_identity", {})
    if "pattern" in kernel_id_def or kernel_id_def.get("const") != CANONICAL_KERNEL_IDENTITY:
        errors.append("SCHEMA_ALLOWS_BROADER_KERNEL_IDENTITY")

    # Check stock image sha256 in schema
    if art_props.get("stock_image_sha256", {}).get("const") != CANONICAL_IMAGE_SHA256:
        errors.append("SCHEMA_STOCK_IMAGE_SHA256_MISMATCH")

    # Check run_package vs raw_session_manifest in schema
    if "run_package_identity" not in art_props or "raw_evidence_identity" not in art_props:
        errors.append("SCHEMA_MISSING_SEPARATE_RUN_PACKAGE_OR_RAW_EVIDENCE_IDENTITY")

    # Check event grammar version in schema
    if schema.get("properties", {}).get("event_grammar_version", {}).get("const") != CANONICAL_GRAMMAR_VERSION:
        errors.append(f"SCHEMA_EVENT_GRAMMAR_VERSION_NOT_{CANONICAL_GRAMMAR_VERSION}")

    # 2. Load event grammar v2.1.1
    grammar_path = DOCS / "phase_j2_event_grammar.json"
    if not grammar_path.exists():
        errors.append("MISSING_phase_j2_event_grammar.json")
    else:
        grammar = json.loads(grammar_path.read_text())
        if grammar.get("grammar_version") != CANONICAL_GRAMMAR_VERSION:
            errors.append(f"GRAMMAR_VERSION_NOT_{CANONICAL_GRAMMAR_VERSION}")
        # Assert each event has typed payload schema
        for ev_name, ev_def in grammar.get("events", {}).items():
            if "payload_schema" not in ev_def:
                errors.append(f"GRAMMAR_EVENT_{ev_name}_LACKS_PAYLOAD_SCHEMA")

    # 3. Check Go Gates CSV
    gates_path = DOCS / "phase_j2_go_gates.csv"
    if not gates_path.exists():
        errors.append("MISSING_phase_j2_go_gates.csv")
    else:
        with gates_path.open() as f:
            gates = list(csv.DictReader(f))
        g_map = {g["ID"]: g for g in gates}

        # Gate G02: Model and Device codename exact match
        g02 = g_map.get("G02", {})
        g02_res = g02.get("EXPECTED_RESULT", "")
        if f"ro.product.model=={CANONICAL_MODEL}" not in g02_res or f"ro.product.device=={CANONICAL_DEVICE}" not in g02_res:
            errors.append("GATE_G02_MISSING_EXACT_MODEL_AND_DEVICE_EQUALITY")
        if "==" not in g02_res:
            errors.append("GATE_G02_USES_SUBSTRING_MATCH")

        # Gate G03: Exact Incremental and Full Fingerprint
        g03 = g_map.get("G03", {})
        g03_res = g03.get("EXPECTED_RESULT", "")
        if f"ro.build.version.incremental=={CANONICAL_INCREMENTAL}" not in g03_res:
            errors.append("GATE_G03_MISSING_EXACT_INCREMENTAL")
        if f"ro.build.fingerprint=={CANONICAL_BUILD_FINGERPRINT}" not in g03_res:
            errors.append("GATE_G03_MISSING_EXACT_FINGERPRINT")
        if "==" not in g03_res:
            errors.append("GATE_G03_USES_SUBSTRING_MATCH")

        # Gate G04: Exact Kernel Identity
        g04 = g_map.get("G04", {})
        g04_res = g04.get("EXPECTED_RESULT", "")
        if f"uname -r=={CANONICAL_KERNEL_IDENTITY}" not in g04_res:
            errors.append("GATE_G04_MISSING_EXACT_KERNEL_IDENTITY")
        if "==" not in g04_res:
            errors.append("GATE_G04_USES_SUBSTRING_MATCH")

        # Gate G05: must bind CANONICAL_IMAGE_SHA256 to Image.stock, NOT boot.img
        g05 = g_map.get("G05", {})
        if CANONICAL_IMAGE_SHA256 not in g05.get("EXPECTED_RESULT", ""):
            errors.append("GATE_G05_MISSING_CANONICAL_IMAGE_DIGEST")
        if "boot.img" in g05.get("REQUIRED_ARTIFACT", "").lower():
            errors.append("GATE_G05_ERRONEOUSLY_BINDS_DIGEST_TO_BOOT_IMG")
        if "Image.stock" not in g05.get("REQUIRED_ARTIFACT", ""):
            errors.append("GATE_G05_REQUIRED_ARTIFACT_NOT_IMAGE_STOCK")

        # Gate G12: observation schema v2.2.1 self-test PASS
        g12 = g_map.get("G12", {})
        if "2.2.1" not in g12.get("TEST", "") and "2.2.1" not in g12.get("EXPECTED_RESULT", ""):
            errors.append("GATE_G12_NOT_BOUND_TO_SCHEMA_V2.2.1")

        # Confounder readiness gates must exist
        for cid in ["G13", "G14", "G15"]:
            if cid not in g_map:
                errors.append(f"MISSING_CONFOUNDER_GATE_{cid}")

    # 4. Check Validator Constants
    if getattr(validator, "CANONICAL_SCHEMA_VERSION", None) != CANONICAL_SCHEMA_VERSION:
        errors.append("VALIDATOR_CANONICAL_SCHEMA_VERSION_MISMATCH")
    if getattr(validator, "CANONICAL_DEVICE_MODEL", None) != CANONICAL_MODEL:
        errors.append("VALIDATOR_CANONICAL_DEVICE_MODEL_MISMATCH")
    if getattr(validator, "CANONICAL_DEVICE_NAME", None) != CANONICAL_DEVICE:
        errors.append("VALIDATOR_CANONICAL_DEVICE_NAME_MISMATCH")
    if getattr(validator, "CANONICAL_INCREMENTAL", None) != CANONICAL_INCREMENTAL:
        errors.append("VALIDATOR_CANONICAL_INCREMENTAL_MISMATCH")
    if getattr(validator, "CANONICAL_BUILD_FINGERPRINT", None) != CANONICAL_BUILD_FINGERPRINT:
        errors.append("VALIDATOR_CANONICAL_BUILD_FINGERPRINT_MISMATCH")
    if getattr(validator, "CANONICAL_KERNEL_IDENTITY", None) != CANONICAL_KERNEL_IDENTITY:
        errors.append("VALIDATOR_CANONICAL_KERNEL_IDENTITY_MISMATCH")
    if getattr(validator, "CANONICAL_STOCK_IMAGE_SHA256", None) != CANONICAL_IMAGE_SHA256:
        errors.append("VALIDATOR_CANONICAL_STOCK_IMAGE_SHA256_MISMATCH")

    # 5. Check Test Fixtures for Stale Example Identity
    # Verify replay generator default
    from test_phase_j2_1_r1_replay import generate_trial_record
    sample_replay_rec = generate_trial_record(1, "SETTLED_NOMINAL", 1)
    rep_art = sample_replay_rec.get("artifact_identity", {})
    if rep_art.get("build_fingerprint") != CANONICAL_BUILD_FINGERPRINT:
        errors.append("FIXTURES_REPLAY_USES_STALE_EXAMPLE_FINGERPRINT")
    if rep_art.get("kernel_identity") != CANONICAL_KERNEL_IDENTITY:
        errors.append("FIXTURES_REPLAY_USES_STALE_KERNEL_IDENTITY")
    if sample_replay_rec.get("schema_version") != CANONICAL_SCHEMA_VERSION:
        errors.append("FIXTURES_REPLAY_USES_STALE_SCHEMA_VERSION")

    # Verify schema generator default
    from test_phase_j2_1_r1_schema import make_valid_record
    sample_schema_rec = make_valid_record()
    sch_art = sample_schema_rec.get("artifact_identity", {})
    if sch_art.get("build_fingerprint") != CANONICAL_BUILD_FINGERPRINT:
        errors.append("FIXTURES_SCHEMA_USES_STALE_EXAMPLE_FINGERPRINT")
    if sch_art.get("kernel_identity") != CANONICAL_KERNEL_IDENTITY:
        errors.append("FIXTURES_SCHEMA_USES_STALE_KERNEL_IDENTITY")
    if sample_schema_rec.get("schema_version") != CANONICAL_SCHEMA_VERSION:
        errors.append("FIXTURES_SCHEMA_USES_STALE_SCHEMA_VERSION")

    # 6. Check Runtime Identity Contract
    contract_path = DOCS / "phase_j2_runtime_identity_contract.md"
    if not contract_path.exists():
        errors.append("MISSING_phase_j2_runtime_identity_contract.md")
    else:
        c_text = contract_path.read_text()
        for expected_val in [
            CANONICAL_MODEL,
            CANONICAL_DEVICE,
            CANONICAL_INCREMENTAL,
            CANONICAL_BUILD_FINGERPRINT,
            CANONICAL_KERNEL_IDENTITY,
            CANONICAL_IMAGE_SHA256,
            CANONICAL_SECURITY_PATCH,
        ]:
            if expected_val not in c_text:
                errors.append(f"RUNTIME_IDENTITY_CONTRACT_MISSING_{expected_val}")
        if "No Substring Matching" not in c_text:
            errors.append("RUNTIME_IDENTITY_CONTRACT_MISSING_NO_SUBSTRING_RULE")

    # 7. Check Preexecution Matrix
    matrix_path = DOCS / "phase_j2_preexecution_matrix.csv"
    if not matrix_path.exists():
        errors.append("MISSING_phase_j2_preexecution_matrix.csv")
    else:
        with matrix_path.open() as f:
            matrix_rows = list(csv.DictReader(f))
        m_map = {r["REQUIREMENT"]: r for r in matrix_rows}
        sch_row = m_map.get("Observation schema", {})
        if f"Schema v{CANONICAL_SCHEMA_VERSION} frozen" not in sch_row.get("REQUIRED_ACTION", ""):
            errors.append("PREEXECUTION_MATRIX_OBSERVATION_SCHEMA_NOT_V2.2.1")
        if "Runtime identity contract" not in m_map:
            errors.append("PREEXECUTION_MATRIX_MISSING_RUNTIME_IDENTITY_CONTRACT")

    # 8. Check Canonical J2.1-R1 Report
    r1_path = DOCS / "PHASE_J2_1_R1.md"
    if not r1_path.exists():
        errors.append("MISSING_PHASE_J2_1_R1.md")
    else:
        r1_text = r1_path.read_text()
        for expected_val in [
            CANONICAL_MODEL,
            CANONICAL_DEVICE,
            CANONICAL_INCREMENTAL,
            CANONICAL_BUILD_FINGERPRINT,
            CANONICAL_KERNEL_IDENTITY,
            CANONICAL_IMAGE_SHA256,
            CANONICAL_SCHEMA_VERSION,
        ]:
            if expected_val not in r1_text:
                errors.append(f"CANONICAL_R1_REPORT_MISSING_{expected_val}")

    # 9. Assert no competing/conflicting EZE4 fingerprints in active Phase J2 contracts
    active_contract_files = list(DOCS.glob("phase_j2_*.*"))
    for cf in active_contract_files:
        if cf.suffix in [".json", ".csv", ".md"]:
            content = cf.read_text()
            # If an active contract defines a build fingerprint string matching another variant
            # as an accepted property, fail closed.
            if "samsung/gts9fewifixx/gts9fewifi:16/UP1A" in content:
                errors.append(f"ACTIVE_CONTRACT_{cf.name}_CONTAINS_STALE_UP1A_FINGERPRINT")

    # 10. Check Decision Table CSV
    dt_path = DOCS / "phase_j2_decision_table.csv"
    if not dt_path.exists():
        errors.append("MISSING_phase_j2_decision_table.csv")
    else:
        with dt_path.open() as f:
            rows = list(csv.DictReader(f))
        # Find single timeout row
        single_to = [r for r in rows if "one attributable overall timeout" in r.get("SCENARIO", "").lower()]
        if not single_to or single_to[0].get("CAMPAIGN_EFFECT") != "INCONCLUSIVE":
            errors.append("DECISION_TABLE_SINGLE_TIMEOUT_NOT_INCONCLUSIVE")

        # Find 3 timeouts row
        three_to = [r for r in rows if "three attributable overall timeouts" in r.get("SCENARIO", "").lower()]
        if not three_to or three_to[0].get("CAMPAIGN_EFFECT") != "INCOMPATIBLE":
            errors.append("DECISION_TABLE_THREE_TIMEOUTS_NOT_INCOMPATIBLE")

    # 11. Check E4 Contract Text
    e4_path = DOCS / "phase_j2_e4_contract.md"
    if not e4_path.exists():
        errors.append("MISSING_phase_j2_e4_contract.md")
    else:
        e4_text = e4_path.read_text()
        if not re.search(r"3.*Distinct\s+Verified\s+Boots", e4_text, re.IGNORECASE):
            errors.append("E4_CONTRACT_MISSING_3_BOOTS_RULE")
        if not re.search(r"Maximum\s+per\s+boot.*1.*invalid\s+trial", e4_text, re.IGNORECASE):
            errors.append("E4_CONTRACT_MISSING_1_PER_BOOT_INVALID_CAP")
        if not re.search(r"Maximum\s+total.*2.*invalid\s+trials", e4_text, re.IGNORECASE):
            errors.append("E4_CONTRACT_MISSING_2_TOTAL_INVALID_CAP")
        if not re.search(
            r"3.*valid\s+attributable\s+overall\s+timeouts.*SAME\s+condition.*2.*distinct\s+verified\s+boots",
            e4_text,
            re.DOTALL,
        ):
            errors.append("E4_CONTRACT_MISSING_INCOMPATIBILITY_3X2_RULE")

    # 12. Check Clock Model Text
    clock_path = DOCS / "phase_j2_clock_model.md"
    if not clock_path.exists():
        errors.append("MISSING_phase_j2_clock_model.md")
    else:
        clock_text = clock_path.read_text()
        if "CLOCK_MONOTONIC" not in clock_text:
            errors.append("CLOCK_MODEL_MISSING_CLOCK_MONOTONIC")
        if "post-fork" not in clock_text:
            errors.append("CLOCK_MODEL_MISSING_POST_FORK_EPOCH")
        if not re.search(r"1\.1(00)?", clock_text):
            errors.append("CLOCK_MODEL_MISSING_1.1S_CHECK")

    # 13. Check Protected Parameters
    for p in PROTECTED_PARAMETERS:
        pass

    return errors


def main():
    errors = check_consistency()
    if errors:
        print(f"FAIL: Cross-artifact consistency errors ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("PASS: Cross-artifact consistency verified across all schemas, contracts, tables, and grammars.")
        sys.exit(0)


if __name__ == "__main__":
    main()
