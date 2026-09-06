"""Offline validator for Phase J2.1-R1.1 observation records and event grammar.

Enforces structural schema v2.2.1, event grammar v2.1.1, and semantic invariants
without requiring third-party dependencies.
"""

from collections import Counter
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = ROOT / "docs/rmg-eze4/phase_j2_observation_schema_v2.json"
GRAMMAR_PATH = ROOT / "docs/rmg-eze4/phase_j2_event_grammar.json"

SHA256_HEX_RE = re.compile(r"^[a-f0-9]{64}$")
EXPERIMENT_ID_RE = re.compile(r"^EXP-[A-F0-9]{8}$")
SESSION_ID_RE = re.compile(r"^SES-[A-F0-9]{8}$")
TRIAL_ID_RE = re.compile(r"^TRL-[0-9]{4}$")

# Exact canonical physical EZE4 identity constants (Phase G authority)
CANONICAL_SCHEMA_VERSION = "2.2.1"
CANONICAL_GRAMMAR_VERSION = "2.1.1"
CANONICAL_DEVICE_MODEL = "SM-X510"
CANONICAL_DEVICE_NAME = "gts9fewifi"
CANONICAL_INCREMENTAL = "X510XXUCEZE4"
CANONICAL_BUILD_FINGERPRINT = "samsung/gts9fewifieea/gts9fewifi:16/BP4A.251205.006/X510XXUCEZE4:user/release-keys"
CANONICAL_KERNEL_IDENTITY = "5.15.189-android13-3-33478785"
CANONICAL_STOCK_IMAGE_SHA256 = "ca56baf428a3f334d90f5d366f02e6cb36cf70fec23a2055b4f80c29cbe6ede9"


class ValidationError(Exception):
    pass


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text())


def load_grammar() -> dict:
    return json.loads(GRAMMAR_PATH.read_text())


def validate_observation_record(record: dict) -> Tuple[bool, List[str]]:
    """Validate a single Phase J2.1-R1.1 observation record."""
    errors = []

    # 1. Root Required Fields
    required_root = [
        "schema_version", "event_grammar_version", "candidate_identity",
        "experiment_id", "session_id", "boot_id", "trial_id",
        "attempt_ordinal", "pid", "artifact_identity", "condition_vector",
        "timing_metrics", "confounder_observations", "state_transitions",
        "observables", "classification"
    ]
    for field in required_root:
        if field not in record:
            errors.append(f"MISSING_ROOT_FIELD_{field}")

    if errors:
        return False, errors

    # Check forbidden additional fields
    for k in record:
        if k not in required_root:
            errors.append(f"FORBIDDEN_FIELD_{k}")

    # 2. Version & Candidate Identity
    if record.get("schema_version") != CANONICAL_SCHEMA_VERSION:
        errors.append(f"INVALID_SCHEMA_VERSION_{record.get('schema_version')}")
    if record.get("event_grammar_version") != CANONICAL_GRAMMAR_VERSION:
        errors.append(f"INVALID_EVENT_GRAMMAR_VERSION_{record.get('event_grammar_version')}")

    cand_ident = record.get("candidate_identity", {})
    if cand_ident.get("candidate_parameter") != "DEFAULT_ATTEMPT_TIMEOUT_SEC":
        errors.append(f"INVALID_CANDIDATE_PARAM_{cand_ident.get('candidate_parameter')}")
    if cand_ident.get("candidate_value") != 2200:
        errors.append(f"INVALID_CANDIDATE_VALUE_{cand_ident.get('candidate_value')}")

    # 3. String Patterns
    if not EXPERIMENT_ID_RE.match(record.get("experiment_id", "")):
        errors.append("INVALID_EXPERIMENT_ID_FORMAT")
    if not SESSION_ID_RE.match(record.get("session_id", "")):
        errors.append("INVALID_SESSION_ID_FORMAT")
    if not SHA256_HEX_RE.match(record.get("boot_id", "")):
        errors.append("INVALID_BOOT_ID_SHA256_FORMAT")
    if not TRIAL_ID_RE.match(record.get("trial_id", "")):
        errors.append("INVALID_TRIAL_ID_FORMAT")

    if not isinstance(record.get("attempt_ordinal"), int) or record["attempt_ordinal"] < 1:
        errors.append("INVALID_ATTEMPT_ORDINAL")
    if not isinstance(record.get("pid"), int) or record["pid"] < 1:
        errors.append("INVALID_PID")

    # 4. Artifact Identity
    art_ident = record.get("artifact_identity", {})
    if art_ident == {}:
        errors.append("EMPTY_ARTIFACT_IDENTITY")
    else:
        req_art = [
            "schema_defined", "device_model", "device_name", "incremental_version",
            "build_fingerprint", "stock_image_sha256", "kernel_identity",
            "run_package_identity", "raw_evidence_identity"
        ]
        for f in req_art:
            if f not in art_ident:
                errors.append(f"MISSING_ARTIFACT_FIELD_{f}")
        if art_ident.get("schema_defined") is not True:
            errors.append("ARTIFACT_SCHEMA_DEFINED_NOT_TRUE")
        if art_ident.get("device_model") != CANONICAL_DEVICE_MODEL:
            errors.append(f"WRONG_DEVICE_MODEL_{art_ident.get('device_model')}")
        if art_ident.get("device_name") != CANONICAL_DEVICE_NAME:
            errors.append(f"WRONG_DEVICE_NAME_{art_ident.get('device_name')}")
        if art_ident.get("incremental_version") != CANONICAL_INCREMENTAL:
            errors.append(f"WRONG_INCREMENTAL_VERSION_{art_ident.get('incremental_version')}")
        if art_ident.get("build_fingerprint") != CANONICAL_BUILD_FINGERPRINT:
            errors.append(f"WRONG_BUILD_FINGERPRINT_{art_ident.get('build_fingerprint')}")
        if art_ident.get("kernel_identity") != CANONICAL_KERNEL_IDENTITY:
            errors.append(f"WRONG_KERNEL_IDENTITY_{art_ident.get('kernel_identity')}")
        if art_ident.get("stock_image_sha256") != CANONICAL_STOCK_IMAGE_SHA256:
            errors.append("WRONG_STOCK_IMAGE_SHA256")

        run_pkg = art_ident.get("run_package_identity", {})
        if run_pkg.get("binding_status") not in ("UNBOUND_PENDING_J3", "BOUND_FROZEN"):
            errors.append("INVALID_RUN_PACKAGE_BINDING_STATUS")

        raw_ev = art_ident.get("raw_evidence_identity", {})
        if raw_ev.get("binding_status") not in ("UNBOUND_PENDING_SESSION_CLOSE", "BOUND_CLOSED"):
            errors.append("INVALID_RAW_EVIDENCE_BINDING_STATUS")

    # 5. Condition Vector
    cond_vec = record.get("condition_vector", {})
    req_cond = [
        "condition_class", "threshold_profile_id", "detector_version",
        "freezer_state", "thermal_state", "load_class", "memory_pressure_class",
        "collector_health", "raw_telemetry"
    ]
    for f in req_cond:
        if f not in cond_vec:
            errors.append(f"MISSING_CONDITION_FIELD_{f}")
    if cond_vec.get("condition_class") not in ("SETTLED_NOMINAL", "ELEVATED_VALID"):
        errors.append(f"ILLEGAL_CONDITION_CLASS_{cond_vec.get('condition_class')}")
    if cond_vec.get("threshold_profile_id") not in ("TEMPLATE_UNBOUND", "J3_PROFILE_S9FE_CALIBRATED"):
        errors.append(f"ILLEGAL_THRESHOLD_PROFILE_{cond_vec.get('threshold_profile_id')}")
    if cond_vec.get("freezer_state") not in ("THAWED", "FROZEN", "TRANSITIONING", "UNKNOWN"):
        errors.append(f"ILLEGAL_FREEZER_STATE_{cond_vec.get('freezer_state')}")

    # 6. Timing Metrics & Derived Invariants
    tm = record.get("timing_metrics", {})
    req_tm = [
        "clock_source", "post_fork_monotonic_ns", "slide_ready_monotonic_ns",
        "terminal_monotonic_ns", "p0_duration_seconds", "candidate_elapsed_duration_ns",
        "candidate_elapsed_duration_seconds", "canonical_headroom_seconds",
        "supervisor_integer_elapsed_sec"
    ]
    for f in req_tm:
        if f not in tm:
            errors.append(f"MISSING_TIMING_FIELD_{f}")

    if tm.get("clock_source") != "CLOCK_MONOTONIC":
        errors.append(f"ILLEGAL_CLOCK_SOURCE_{tm.get('clock_source')}")

    t_start = tm.get("post_fork_monotonic_ns", 0)
    t_end = tm.get("terminal_monotonic_ns", 0)
    if not isinstance(t_start, int) or t_start < 0:
        errors.append("INVALID_POST_FORK_MONOTONIC_NS")
    if not isinstance(t_end, int) or t_end < 0:
        errors.append("INVALID_TERMINAL_MONOTONIC_NS")

    if t_end < t_start:
        errors.append("TIME_REVERSAL_TERMINAL_BEFORE_POST_FORK")

    expected_duration_ns = t_end - t_start
    if tm.get("candidate_elapsed_duration_ns") != expected_duration_ns:
        errors.append("DERIVED_DURATION_NS_MISMATCH")

    expected_duration_sec = expected_duration_ns / 1e9
    if abs(tm.get("candidate_elapsed_duration_seconds", 0.0) - expected_duration_sec) > 1e-6:
        errors.append("DERIVED_DURATION_SECONDS_MISMATCH")

    expected_headroom = 2200.0 - expected_duration_sec
    if abs(tm.get("canonical_headroom_seconds", 0.0) - expected_headroom) > 1e-6:
        errors.append("CANONICAL_HEADROOM_MISMATCH")

    # 1.1s supervisor sanity check
    sup_int = tm.get("supervisor_integer_elapsed_sec", 0)
    if abs(expected_duration_sec - sup_int) > 1.100:
        errors.append("CLOCK_CORRELATION_DESYNC_EXCEEDS_1_1_SEC")

    # 7. State Transitions & Invariant Validation
    transitions = record.get("state_transitions", [])
    if not isinstance(transitions, list) or len(transitions) < 2:
        errors.append("STATE_TRANSITIONS_MUST_HAVE_AT_LEAST_2_EVENTS")
    else:
        grammar = load_grammar()
        grammar_events = grammar["events"]

        trial_boot = record.get("boot_id")
        trial_session = record.get("session_id")
        trial_id = record.get("trial_id")
        trial_pid = record.get("pid")
        trial_attempt = record.get("attempt_ordinal")

        prev_seq = -1
        prev_time = -1
        event_types = []

        for idx, ev in enumerate(transitions):
            # Envelope requirements
            req_ev = [
                "sequence", "event_type", "device_monotonic_ns", "boot_id",
                "session_id", "trial_id", "attempt_ordinal", "pid", "producer", "payload"
            ]
            for ef in req_ev:
                if ef not in ev:
                    errors.append(f"EVENT_{idx}_MISSING_FIELD_{ef}")

            seq = ev.get("sequence", 0)
            if seq <= prev_seq:
                errors.append(f"EVENT_{idx}_SEQUENCE_NOT_STRICTLY_INCREASING")
            prev_seq = seq

            ev_time = ev.get("device_monotonic_ns", 0)
            if ev_time < prev_time:
                errors.append(f"EVENT_{idx}_TIME_NOT_MONOTONIC")
            prev_time = ev_time

            # Check identity bindings on every event
            if ev.get("boot_id") != trial_boot:
                errors.append(f"BOOT_MUTATION_DETECTED_AT_EVENT_{idx}")
            if ev.get("session_id") != trial_session:
                errors.append(f"SESSION_MISMATCH_AT_EVENT_{idx}")
            if ev.get("trial_id") != trial_id:
                errors.append(f"TRIAL_ID_MISMATCH_AT_EVENT_{idx}")
            if ev.get("attempt_ordinal") != trial_attempt:
                errors.append(f"ATTEMPT_ORDINAL_MISMATCH_AT_EVENT_{idx}")
            if ev.get("pid") != trial_pid:
                errors.append(f"PID_MISMATCH_AT_EVENT_{idx}")

            etype = ev.get("event_type")
            if etype not in grammar_events:
                errors.append(f"UNKNOWN_EVENT_TYPE_{etype}")
            else:
                event_types.append(etype)
                # Validate payload schema
                pschema = grammar_events[etype].get("payload_schema", {})
                req_pfields = pschema.get("required", [])
                payload = ev.get("payload", {})
                for pf in req_pfields:
                    if pf not in payload:
                        errors.append(f"EVENT_{idx}_PAYLOAD_MISSING_{pf}")

        # State transition ordering check
        if "ATTEMPT_SPAWN" not in event_types:
            errors.append("MISSING_ATTEMPT_SPAWN_EVENT")
        if "PROCESS_REAP" in event_types:
            reap_idx = event_types.index("PROCESS_REAP")
            spawn_idx = event_types.index("ATTEMPT_SPAWN")
            if reap_idx < spawn_idx:
                errors.append("ILLEGAL_REAP_BEFORE_SPAWN")

    # 8. Confounders & Classification Consistency
    cls = record.get("classification", {})
    t_term = cls.get("trial_terminal_class")
    t_valid = cls.get("trial_validity")
    t_vote = cls.get("trial_evidence_vote")

    if t_term not in [
        "QUALIFYING_COMPLETION", "EXPECTED_P0_TIMEOUT", "SUPERVISOR_OVERALL_TIMEOUT",
        "CHILD_EXPLICIT_FAILURE", "CHILD_SIGNAL_FAILURE", "WRONG_STATE_TERMINATION",
        "EXTERNAL_INTERRUPTION", "MEASUREMENT_FAILURE"
    ]:
        errors.append(f"ILLEGAL_TERMINAL_CLASS_{t_term}")

    if t_valid not in ["VALID", "INVALID", "INCONCLUSIVE"]:
        errors.append(f"ILLEGAL_TRIAL_VALIDITY_{t_valid}")

    if t_vote not in ["COMPATIBLE_VOTE", "INCOMPATIBLE_VOTE", "NO_VOTE"]:
        errors.append(f"ILLEGAL_EVIDENCE_VOTE_{t_vote}")

    c_obs = record.get("confounder_observations", {})
    c1 = c_obs.get("c1_p0_delay", {}).get("classification")
    c2 = c_obs.get("c2_cgroup_freezer", {}).get("classification")
    c3 = c_obs.get("c3_thermal_throttling", {}).get("classification")

    # If any HIGH confounder is PRESENT, trial validity cannot be VALID
    if c1 == "C1_PRESENT" and t_valid == "VALID":
        errors.append("CONFOUNDER_C1_PRESENT_CONFLICTS_WITH_VALID")
    if c2 == "C2_PRESENT" and t_valid == "VALID":
        errors.append("CONFOUNDER_C2_PRESENT_CONFLICTS_WITH_VALID")
    if c3 == "C3_PRESENT" and t_valid == "VALID" and t_term == "SUPERVISOR_OVERALL_TIMEOUT":
        errors.append("CONFOUNDER_C3_PRESENT_CONFLICTS_WITH_VALID")

    # If confounder is UNKNOWN, validity cannot be VALID
    if (c1 == "C1_UNKNOWN" or c2 == "C2_UNKNOWN" or c3 == "C3_UNKNOWN") and t_valid == "VALID":
        errors.append("UNKNOWN_CONFOUNDER_CONFLICTS_WITH_VALID")

    # Voting rules
    if t_vote == "COMPATIBLE_VOTE":
        if t_valid != "VALID":
            errors.append("COMPATIBLE_VOTE_REQUIRES_VALID")
        if t_term != "QUALIFYING_COMPLETION":
            errors.append("COMPATIBLE_VOTE_REQUIRES_QUALIFYING_COMPLETION")
        if expected_duration_sec > 2195.000:
            errors.append("COMPATIBLE_VOTE_EXCEEDS_2195_SEC_HEADROOM")

    if t_vote == "INCOMPATIBLE_VOTE":
        if t_valid != "VALID":
            errors.append("INCOMPATIBLE_VOTE_REQUIRES_VALID")
        if t_term != "SUPERVISOR_OVERALL_TIMEOUT":
            errors.append("INCOMPATIBLE_VOTE_REQUIRES_SUPERVISOR_OVERALL_TIMEOUT")
        if expected_duration_sec < 2200.000:
            errors.append("INCOMPATIBLE_VOTE_UNDER_2200_SEC")

    return len(errors) == 0, errors
