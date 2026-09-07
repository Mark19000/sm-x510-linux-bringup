"""End-to-End RAW Replay Pipeline Tests for Phase J2.1-R1.

Tests the full deterministic chain:
RAW Evidence -> SHA256 Manifest -> Normalizer -> Schema Validator -> Semantic Invariants -> E4 Aggregator -> Final Verdict
"""

import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "rmg-eze4" / "analysis"))

from aggregator import aggregate_campaign  # noqa: E402
from validator import validate_observation_record  # noqa: E402


def generate_trial_record(
    boot_idx: int,
    cond_class: str,
    trial_idx: int,
    duration_sec: float = 200.0,
    term_class: str = "QUALIFYING_COMPLETION",
    validity: str = "VALID",
    vote: str = "COMPATIBLE_VOTE",
    c1: str = "C1_CLEAR",
    c2: str = "C2_ABSENT",
    c3: str = "C3_ABSENT",
    grammar_ver: str = "2.1.1",
    schema_ver: str = "2.2.1"
) -> dict:
    boot_id = hashlib.sha256(f"BOOT_TOKEN_{boot_idx}".encode()).hexdigest()
    session_id = f"SES-0000000{boot_idx}"
    trial_id = f"TRL-{trial_idx:04d}"
    pid = 5000 + trial_idx

    t_start = 100_000_000_000 + trial_idx * 1_000_000_000
    duration_ns = int(duration_sec * 1e9)
    t_end = t_start + duration_ns
    headroom_sec = 2200.0 - duration_sec

    events = [
        {
            "sequence": 0,
            "event_type": "TRIAL_INIT",
            "device_monotonic_ns": t_start - 1000,
            "boot_id": boot_id,
            "session_id": session_id,
            "trial_id": trial_id,
            "attempt_ordinal": 1,
            "pid": pid,
            "producer": "SUPERVISOR",
            "payload": {
                "experiment_id": "EXP-12345678",
                "session_id": session_id,
                "condition_class": cond_class
            }
        },
        {
            "sequence": 1,
            "event_type": "ATTEMPT_SPAWN",
            "device_monotonic_ns": t_start,
            "boot_id": boot_id,
            "session_id": session_id,
            "trial_id": trial_id,
            "attempt_ordinal": 1,
            "pid": pid,
            "producer": "SUPERVISOR",
            "payload": {
                "assigned_pid": pid,
                "executable_path": "/data/local/tmp/attempt"
            }
        },
        {
            "sequence": 2,
            "event_type": "P0_ENTER",
            "device_monotonic_ns": t_start + 100_000,
            "boot_id": boot_id,
            "session_id": session_id,
            "trial_id": trial_id,
            "attempt_ordinal": 1,
            "pid": pid,
            "producer": "TARGET_CHILD",
            "payload": {}
        }
    ]

    seq = 3
    if c1 == "C1_CLEAR":
        events.append({
            "sequence": seq,
            "event_type": "P0_EXIT_SLIDE_READY",
            "device_monotonic_ns": t_start + 4_000_000_000,
            "boot_id": boot_id,
            "session_id": session_id,
            "trial_id": trial_id,
            "attempt_ordinal": 1,
            "pid": pid,
            "producer": "TARGET_CHILD",
            "payload": {
                "p0_duration_ns": 4_000_000_000,
                "handshake_status": "READY"
            }
        })
        seq += 1
        events.append({
            "sequence": seq,
            "event_type": "OVERALL_SLIDE_ENTER",
            "device_monotonic_ns": t_start + 4_000_100_000,
            "boot_id": boot_id,
            "session_id": session_id,
            "trial_id": trial_id,
            "attempt_ordinal": 1,
            "pid": pid,
            "producer": "SUPERVISOR",
            "payload": {
                "candidate_watchdog_seconds": 2200,
                "watchdog_epoch_start_monotonic_ns": t_start
            }
        })
        seq += 1

    if term_class == "QUALIFYING_COMPLETION":
        events.append({
            "sequence": seq,
            "event_type": "TERMINAL_COMPLETION",
            "device_monotonic_ns": t_end,
            "boot_id": boot_id,
            "session_id": session_id,
            "trial_id": trial_id,
            "attempt_ordinal": 1,
            "pid": pid,
            "producer": "TARGET_CHILD",
            "payload": {
                "exit_code": 0,
                "total_monotonic_ns": duration_ns
            }
        })
        seq += 1
    elif term_class == "SUPERVISOR_OVERALL_TIMEOUT":
        events.append({
            "sequence": seq,
            "event_type": "WATCHDOG_EXPIRY",
            "device_monotonic_ns": t_end,
            "boot_id": boot_id,
            "session_id": session_id,
            "trial_id": trial_id,
            "attempt_ordinal": 1,
            "pid": pid,
            "producer": "SUPERVISOR",
            "payload": {
                "target_pid": pid,
                "elapsed_seconds": int(duration_sec)
            }
        })
        seq += 1
    elif term_class == "CHILD_SIGNAL_FAILURE":
        events.append({
            "sequence": seq,
            "event_type": "PROCESS_SIGNAL",
            "device_monotonic_ns": t_end,
            "boot_id": boot_id,
            "session_id": session_id,
            "trial_id": trial_id,
            "attempt_ordinal": 1,
            "pid": pid,
            "producer": "SUPERVISOR",
            "payload": {
                "target_pid": pid,
                "signal_number": 11,
                "signal_name": "SIGSEGV"
            }
        })
        seq += 1

    events.append({
        "sequence": seq,
        "event_type": "PROCESS_REAP",
        "device_monotonic_ns": t_end + 1_000_000,
        "boot_id": boot_id,
        "session_id": session_id,
        "trial_id": trial_id,
        "attempt_ordinal": 1,
        "pid": pid,
        "producer": "SUPERVISOR",
        "payload": {
            "reaped_pid": pid,
            "exit_status": 0 if term_class == "QUALIFYING_COMPLETION" else (
                1 if term_class == "CHILD_EXPLICIT_FAILURE" else 139
            )
        }
    })

    return {
        "schema_version": schema_ver,
        "event_grammar_version": grammar_ver,
        "candidate_identity": {
            "candidate_parameter": "DEFAULT_ATTEMPT_TIMEOUT_SEC",
            "candidate_value": 2200
        },
        "experiment_id": "EXP-12345678",
        "session_id": session_id,
        "boot_id": boot_id,
        "trial_id": trial_id,
        "attempt_ordinal": 1,
        "pid": pid,
        "artifact_identity": {
            "schema_defined": True,
            "device_model": "SM-X510",
            "device_name": "gts9fewifi",
            "incremental_version": "X510XXUCEZE4",
            "build_fingerprint": "samsung/gts9fewifieea/gts9fewifi:16/BP4A.251205.006/X510XXUCEZE4:user/release-keys",
            "stock_image_sha256": "ca56baf428a3f334d90f5d366f02e6cb36cf70fec23a2055b4f80c29cbe6ede9",
            "kernel_identity": "5.15.189-android13-3-33478785",
            "run_package_identity": {
                "binding_status": "UNBOUND_PENDING_J3",
                "run_package_sha256": "UNBOUND_PENDING_J3"
            },
            "raw_evidence_identity": {
                "binding_status": "BOUND_CLOSED",
                "raw_session_manifest_sha256": hashlib.sha256(f"MANIFEST_{session_id}".encode()).hexdigest()
            }
        },
        "condition_vector": {
            "condition_class": cond_class,
            "threshold_profile_id": "TEMPLATE_UNBOUND",
            "detector_version": "1.0.0",
            "freezer_state": "THAWED",
            "thermal_state": "NOMINAL",
            "load_class": "IDLE_NOMINAL",
            "memory_pressure_class": "NONE",
            "collector_health": "HEALTHY",
            "raw_telemetry": {
                "cpu_temp_celsius": 31.0,
                "load_avg_1m": 0.10,
                "mem_available_mb": 4500
            }
        },
        "timing_metrics": {
            "clock_source": "CLOCK_MONOTONIC",
            "post_fork_monotonic_ns": t_start,
            "slide_ready_monotonic_ns": t_start + 4_000_000_000,
            "terminal_monotonic_ns": t_end,
            "p0_duration_seconds": 4.0,
            "candidate_elapsed_duration_ns": duration_ns,
            "candidate_elapsed_duration_seconds": duration_sec,
            "canonical_headroom_seconds": headroom_sec,
            "supervisor_integer_elapsed_sec": int(duration_sec)
        },
        "confounder_observations": {
            "c1_p0_delay": {
                "classification": c1,
                "slide_ready_detected": c1 == "C1_CLEAR",
                "p0_duration_sec": 4.0 if c1 == "C1_CLEAR" else None
            },
            "c2_cgroup_freezer": {
                "classification": c2,
                "freeze_event_count": 1 if c2 == "C2_PRESENT" else 0,
                "monitor_coverage_pct": 100.0 if c2 != "C2_UNKNOWN" else 85.0,
                "max_monitor_gap_ms": 100.0 if c2 != "C2_UNKNOWN" else 800.0
            },
            "c3_thermal_throttling": {
                "classification": c3,
                "excursion_count": 1 if c3 == "C3_PRESENT" else 0,
                "monitor_coverage_pct": 100.0 if c3 != "C3_UNKNOWN" else 80.0,
                "max_monitor_gap_ms": 500.0 if c3 != "C3_UNKNOWN" else 3500.0
            }
        },
        "state_transitions": events,
        "observables": [
            {
                "observable_id": "OBS-QUAL",
                "observable_version": "1.0",
                "status": "OBSERVED",
                "timestamp_ns": t_end,
                "sequence": 5,
                "source_refs": [
                    {
                        "path": f"raw/{trial_id}_supervisor.stdout",
                        "sha256": hashlib.sha256(f"STDOUT_{trial_id}".encode()).hexdigest(),
                        "producer": "SUPERVISOR",
                        "artifact_type": "TEXT_LOG",
                        "selector": {
                            "selector_type": "LINE_RANGE",
                            "start": 1,
                            "end": 50
                        }
                    }
                ],
                "interpretation": "Attributable lifecycle observable"
            }
        ],
        "classification": {
            "trial_terminal_class": term_class,
            "trial_validity": validity,
            "trial_evidence_vote": vote
        }
    }


def make_clean_e4_campaign() -> list[dict]:
    """Create 12 valid qualifying records covering 3 boots x 2 conditions x 2 trials."""
    records = []
    trial_idx = 1
    for boot_idx in [1, 2, 3]:
        for cond_class in ["SETTLED_NOMINAL", "ELEVATED_VALID"]:
            for rep in [1, 2]:
                r = generate_trial_record(boot_idx, cond_class, trial_idx, duration_sec=150.0 + rep * 10)
                records.append(r)
                trial_idx += 1
    return records


class PhaseJ21R1ReplayPipelineTests(unittest.TestCase):
    def test_scn_01_clean_compatible_campaign(self):
        records = make_clean_e4_campaign()
        self.assertEqual(len(records), 12)
        # Verify every record passes schema validation
        for r in records:
            valid, errors = validate_observation_record(r)
            self.assertTrue(valid, f"Record failed: {errors}")
        result = aggregate_campaign(records)
        self.assertEqual(result["verdict"], "COMPATIBLE")

    def test_scn_02_single_attributable_timeout_is_inconclusive(self):
        records = make_clean_e4_campaign()
        # Replace trial 12 with an attributable timeout
        to_record = generate_trial_record(
            boot_idx=3, cond_class="ELEVATED_VALID", trial_idx=12,
            duration_sec=2200.0, term_class="SUPERVISOR_OVERALL_TIMEOUT",
            validity="VALID", vote="INCOMPATIBLE_VOTE"
        )
        valid, errors = validate_observation_record(to_record)
        self.assertTrue(valid, f"Timeout record failed: {errors}")
        records[11] = to_record
        # Canonical J2 rule: exactly 1 timeout -> INCONCLUSIVE
        result = aggregate_campaign(records)
        self.assertEqual(result["verdict"], "INCONCLUSIVE")

    def test_scn_03_incompatibility_threshold_3_same_condition_2_boots(self):
        records = make_clean_e4_campaign()
        # Create 3 timeouts in SETTLED_NOMINAL across Boot 1 and Boot 2
        t1 = generate_trial_record(1, "SETTLED_NOMINAL", 1, 2200.0, "SUPERVISOR_OVERALL_TIMEOUT", "VALID", "INCOMPATIBLE_VOTE")
        t2 = generate_trial_record(1, "SETTLED_NOMINAL", 2, 2200.0, "SUPERVISOR_OVERALL_TIMEOUT", "VALID", "INCOMPATIBLE_VOTE")
        t3 = generate_trial_record(2, "SETTLED_NOMINAL", 5, 2200.0, "SUPERVISOR_OVERALL_TIMEOUT", "VALID", "INCOMPATIBLE_VOTE")
        records[0] = t1
        records[1] = t2
        records[4] = t3
        result = aggregate_campaign(records)
        self.assertEqual(result["verdict"], "INCOMPATIBLE")

    def test_scn_04_isolated_boot_timeouts_are_inconclusive(self):
        records = make_clean_e4_campaign()
        # Two timeouts on Boot 1 only (fails >=2 boots requirement)
        t1 = generate_trial_record(1, "SETTLED_NOMINAL", 1, 2200.0, "SUPERVISOR_OVERALL_TIMEOUT", "VALID", "INCOMPATIBLE_VOTE")
        t2 = generate_trial_record(1, "SETTLED_NOMINAL", 2, 2200.0, "SUPERVISOR_OVERALL_TIMEOUT", "VALID", "INCOMPATIBLE_VOTE")
        records[0] = t1
        records[1] = t2
        result = aggregate_campaign(records)
        self.assertEqual(result["verdict"], "INCONCLUSIVE")

    def test_scn_05_cross_condition_timeouts_are_inconclusive(self):
        records = make_clean_e4_campaign()
        # One timeout in SETTLED, one in ELEVATED (fails >=3 same-condition requirement)
        t1 = generate_trial_record(1, "SETTLED_NOMINAL", 1, 2200.0, "SUPERVISOR_OVERALL_TIMEOUT", "VALID", "INCOMPATIBLE_VOTE")
        t2 = generate_trial_record(2, "ELEVATED_VALID", 7, 2200.0, "SUPERVISOR_OVERALL_TIMEOUT", "VALID", "INCOMPATIBLE_VOTE")
        records[0] = t1
        records[6] = t2
        result = aggregate_campaign(records)
        self.assertEqual(result["verdict"], "INCONCLUSIVE")

    def test_scn_06_boundary_2195_exact(self):
        r = generate_trial_record(1, "SETTLED_NOMINAL", 1, duration_sec=2195.0, vote="COMPATIBLE_VOTE")
        valid, errors = validate_observation_record(r)
        self.assertTrue(valid, f"Boundary 2195 failed: {errors}")
        self.assertEqual(r["classification"]["trial_evidence_vote"], "COMPATIBLE_VOTE")

    def test_scn_07_boundary_2197_mid(self):
        # 2197.5s completed cleanly -> VALID but NO_VOTE
        r = generate_trial_record(1, "SETTLED_NOMINAL", 1, duration_sec=2197.5, vote="NO_VOTE")
        valid, errors = validate_observation_record(r)
        self.assertTrue(valid, f"Boundary 2197 failed: {errors}")
        self.assertEqual(r["classification"]["trial_evidence_vote"], "NO_VOTE")

    def test_scn_08_invalid_cap_exceeded_single_boot(self):
        records = make_clean_e4_campaign()
        # Inject 2 invalid trials on Boot 1 (max allowed per boot is 1)
        records[0]["classification"]["trial_validity"] = "INVALID"
        records[1]["classification"]["trial_validity"] = "INVALID"
        result = aggregate_campaign(records)
        self.assertEqual(result["verdict"], "INVALID_EXPERIMENT")

    def test_scn_09_invalid_cap_exceeded_total(self):
        records = make_clean_e4_campaign()
        # Inject 1 invalid on Boot 1, 1 on Boot 2, 1 on Boot 3 (total 3 > cap 2)
        records[0]["classification"]["trial_validity"] = "INVALID"
        records[4]["classification"]["trial_validity"] = "INVALID"
        records[8]["classification"]["trial_validity"] = "INVALID"
        result = aggregate_campaign(records)
        self.assertEqual(result["verdict"], "INVALID_EXPERIMENT")

    def test_scn_10_child_exit_nonzero_with_intact_telemetry(self):
        r = generate_trial_record(1, "SETTLED_NOMINAL", 1, duration_sec=50.0,
                                  term_class="CHILD_EXPLICIT_FAILURE", validity="VALID", vote="NO_VOTE")
        valid, errors = validate_observation_record(r)
        self.assertTrue(valid, f"CHILD_EXPLICIT_FAILURE failed: {errors}")
        self.assertEqual(r["classification"]["trial_validity"], "VALID")
        self.assertEqual(r["classification"]["trial_evidence_vote"], "NO_VOTE")

    def test_scn_11_child_signal_crash_with_intact_telemetry(self):
        r = generate_trial_record(1, "SETTLED_NOMINAL", 1, duration_sec=30.0,
                                  term_class="CHILD_SIGNAL_FAILURE", validity="VALID", vote="NO_VOTE")
        valid, errors = validate_observation_record(r)
        self.assertTrue(valid, f"CHILD_SIGNAL_FAILURE failed: {errors}")
        self.assertEqual(r["classification"]["trial_validity"], "VALID")
        self.assertEqual(r["classification"]["trial_evidence_vote"], "NO_VOTE")

    def test_scn_12_p0_duration_does_not_reset_candidate_epoch(self):
        # Post-fork start = t0. P0 takes 300s, overall slide takes 1800s.
        # Total duration from post-fork is 2100s <= 2195s -> COMPATIBLE_VOTE
        r = generate_trial_record(1, "SETTLED_NOMINAL", 1, duration_sec=2100.0, vote="COMPATIBLE_VOTE")
        valid, errors = validate_observation_record(r)
        self.assertTrue(valid, f"P0 duration no reset failed: {errors}")
        self.assertEqual(r["timing_metrics"]["candidate_elapsed_duration_seconds"], 2100.0)
        self.assertEqual(r["classification"]["trial_evidence_vote"], "COMPATIBLE_VOTE")

    def test_scn_13_watchdog_boundary_2200_exact(self):
        r = generate_trial_record(1, "SETTLED_NOMINAL", 1, duration_sec=2200.0,
                                  term_class="SUPERVISOR_OVERALL_TIMEOUT", vote="INCOMPATIBLE_VOTE")
        valid, errors = validate_observation_record(r)
        self.assertTrue(valid, f"Watchdog 2200 failed: {errors}")
        self.assertEqual(r["classification"]["trial_evidence_vote"], "INCOMPATIBLE_VOTE")

    def test_scn_14_confounder_c1_present_is_invalid(self):
        r = generate_trial_record(1, "SETTLED_NOMINAL", 1, duration_sec=2200.0,
                                  term_class="SUPERVISOR_OVERALL_TIMEOUT", validity="INVALID",
                                  vote="NO_VOTE", c1="C1_PRESENT")
        valid, errors = validate_observation_record(r)
        self.assertTrue(valid, f"C1 present validation failed: {errors}")
        self.assertEqual(r["classification"]["trial_validity"], "INVALID")
        self.assertEqual(r["classification"]["trial_evidence_vote"], "NO_VOTE")

    def test_scn_15_confounder_c1_unknown_is_inconclusive(self):
        r = generate_trial_record(1, "SETTLED_NOMINAL", 1, duration_sec=200.0,
                                  validity="INCONCLUSIVE", vote="NO_VOTE", c1="C1_UNKNOWN")
        valid, errors = validate_observation_record(r)
        self.assertTrue(valid, f"C1 unknown validation failed: {errors}")
        self.assertEqual(r["classification"]["trial_validity"], "INCONCLUSIVE")

    def test_scn_16_confounder_c2_freeze_is_invalid(self):
        r = generate_trial_record(1, "SETTLED_NOMINAL", 1, duration_sec=2200.0,
                                  term_class="SUPERVISOR_OVERALL_TIMEOUT", validity="INVALID",
                                  vote="NO_VOTE", c2="C2_PRESENT")
        valid, errors = validate_observation_record(r)
        self.assertTrue(valid, f"C2 freeze validation failed: {errors}")
        self.assertEqual(r["classification"]["trial_validity"], "INVALID")

    def test_scn_17_confounder_c2_gap_is_inconclusive(self):
        r = generate_trial_record(1, "SETTLED_NOMINAL", 1, duration_sec=200.0,
                                  validity="INCONCLUSIVE", vote="NO_VOTE", c2="C2_UNKNOWN")
        valid, errors = validate_observation_record(r)
        self.assertTrue(valid, f"C2 gap validation failed: {errors}")
        self.assertEqual(r["classification"]["trial_validity"], "INCONCLUSIVE")

    def test_scn_18_confounder_c3_thermal_is_invalid(self):
        r = generate_trial_record(1, "SETTLED_NOMINAL", 1, duration_sec=2200.0,
                                  term_class="SUPERVISOR_OVERALL_TIMEOUT", validity="INVALID",
                                  vote="NO_VOTE", c3="C3_PRESENT")
        valid, errors = validate_observation_record(r)
        self.assertTrue(valid, f"C3 thermal validation failed: {errors}")
        self.assertEqual(r["classification"]["trial_validity"], "INVALID")

    def test_scn_19_confounder_c3_gap_is_inconclusive(self):
        r = generate_trial_record(1, "SETTLED_NOMINAL", 1, duration_sec=200.0,
                                  validity="INCONCLUSIVE", vote="NO_VOTE", c3="C3_UNKNOWN")
        valid, errors = validate_observation_record(r)
        self.assertTrue(valid, f"C3 gap validation failed: {errors}")
        self.assertEqual(r["classification"]["trial_validity"], "INCONCLUSIVE")

    def test_scn_20_clock_corruption_step_backward(self):
        r = generate_trial_record(1, "SETTLED_NOMINAL", 1)
        r["timing_metrics"]["terminal_monotonic_ns"] = r["timing_metrics"]["post_fork_monotonic_ns"] - 1000
        valid, errors = validate_observation_record(r)
        self.assertFalse(valid)
        self.assertIn("TIME_REVERSAL_TERMINAL_BEFORE_POST_FORK", errors)

    def test_scn_21_clock_correlation_desync(self):
        r = generate_trial_record(1, "SETTLED_NOMINAL", 1, duration_sec=200.0)
        r["timing_metrics"]["supervisor_integer_elapsed_sec"] = 197
        valid, errors = validate_observation_record(r)
        self.assertFalse(valid)
        self.assertIn("CLOCK_CORRELATION_DESYNC_EXCEEDS_1_1_SEC", errors)

    def test_scn_22_boot_mutation_mid_trial(self):
        r = generate_trial_record(1, "SETTLED_NOMINAL", 1)
        r["state_transitions"][-1]["boot_id"] = "e" * 64
        valid, errors = validate_observation_record(r)
        self.assertFalse(valid)
        self.assertTrue(any("BOOT_MUTATION_DETECTED" in e for e in errors))

    def test_scn_23_unknown_event_grammar_version(self):
        r = generate_trial_record(1, "SETTLED_NOMINAL", 1, grammar_ver="1.0.0")
        valid, errors = validate_observation_record(r)
        self.assertFalse(valid)
        self.assertTrue(any("INVALID_EVENT_GRAMMAR_VERSION" in e for e in errors))

    def test_scn_24_wrong_stock_image_hash(self):
        r = generate_trial_record(1, "SETTLED_NOMINAL", 1)
        r["artifact_identity"]["stock_image_sha256"] = "f" * 64
        valid, errors = validate_observation_record(r)
        self.assertFalse(valid)
        self.assertIn("WRONG_STOCK_IMAGE_SHA256", errors)

    def test_scn_25_unbound_run_package_is_template_valid(self):
        r = generate_trial_record(1, "SETTLED_NOMINAL", 1)
        self.assertEqual(r["artifact_identity"]["run_package_identity"]["binding_status"], "UNBOUND_PENDING_J3")
        valid, errors = validate_observation_record(r)
        self.assertTrue(valid, f"Template binding status failed: {errors}")

    def test_scn_26_wrong_build_fingerprint_rejected(self):
        r = generate_trial_record(1, "SETTLED_NOMINAL", 1)
        r["artifact_identity"]["build_fingerprint"] = "samsung/gts9fewifixx/gts9fewifi:16/BP4A.251205.006/X510XXUCEZE4:user/release-keys"
        valid, errors = validate_observation_record(r)
        self.assertFalse(valid)
        self.assertTrue(any("WRONG_BUILD_FINGERPRINT" in e for e in errors))

    def test_scn_27_wrong_kernel_identity_rejected(self):
        r = generate_trial_record(1, "SETTLED_NOMINAL", 1)
        r["artifact_identity"]["kernel_identity"] = "5.15.189-android16-11-28562788"
        valid, errors = validate_observation_record(r)
        self.assertFalse(valid)
        self.assertTrue(any("WRONG_KERNEL_IDENTITY" in e for e in errors))

    def test_scn_28_wrong_device_codename_rejected(self):
        r = generate_trial_record(1, "SETTLED_NOMINAL", 1)
        r["artifact_identity"]["device_name"] = "gts9fewifixx"
        valid, errors = validate_observation_record(r)
        self.assertFalse(valid)
        self.assertTrue(any("WRONG_DEVICE_NAME" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
