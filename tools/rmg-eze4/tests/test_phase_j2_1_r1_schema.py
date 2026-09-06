"""Unit and invariant tests for Phase J2.1-R1.1 observation schema v2.2.1 and grammar v2.1.1."""

import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "rmg-eze4" / "analysis"))

from validator import validate_observation_record  # noqa: E402


def make_valid_record(**updates) -> dict:
    t_start = 100_000_000_000
    t_end = 100_000_000_000 + 200_000_000_000  # 200s duration
    duration_ns = t_end - t_start
    duration_sec = duration_ns / 1e9
    headroom_sec = 2200.0 - duration_sec

    boot_id = "a" * 64
    session_id = "SES-12345678"
    trial_id = "TRL-0001"
    pid = 4096

    record = {
        "schema_version": "2.2.1",
        "event_grammar_version": "2.1.1",
        "candidate_identity": {
            "candidate_parameter": "DEFAULT_ATTEMPT_TIMEOUT_SEC",
            "candidate_value": 2200
        },
        "experiment_id": "EXP-ABCDEF01",
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
                "raw_session_manifest_sha256": "b" * 64
            }
        },
        "condition_vector": {
            "condition_class": "SETTLED_NOMINAL",
            "threshold_profile_id": "TEMPLATE_UNBOUND",
            "detector_version": "1.0.0",
            "freezer_state": "THAWED",
            "thermal_state": "NOMINAL",
            "load_class": "IDLE_NOMINAL",
            "memory_pressure_class": "NONE",
            "collector_health": "HEALTHY",
            "raw_telemetry": {
                "cpu_temp_celsius": 32.5,
                "load_avg_1m": 0.15,
                "mem_available_mb": 4200
            }
        },
        "timing_metrics": {
            "clock_source": "CLOCK_MONOTONIC",
            "post_fork_monotonic_ns": t_start,
            "slide_ready_monotonic_ns": t_start + 5_000_000_000,
            "terminal_monotonic_ns": t_end,
            "p0_duration_seconds": 5.0,
            "candidate_elapsed_duration_ns": duration_ns,
            "candidate_elapsed_duration_seconds": duration_sec,
            "canonical_headroom_seconds": headroom_sec,
            "supervisor_integer_elapsed_sec": int(duration_sec)
        },
        "confounder_observations": {
            "c1_p0_delay": {
                "classification": "C1_CLEAR",
                "slide_ready_detected": True,
                "p0_duration_sec": 5.0
            },
            "c2_cgroup_freezer": {
                "classification": "C2_ABSENT",
                "freeze_event_count": 0,
                "monitor_coverage_pct": 100.0,
                "max_monitor_gap_ms": 120.0
            },
            "c3_thermal_throttling": {
                "classification": "C3_ABSENT",
                "excursion_count": 0,
                "monitor_coverage_pct": 100.0,
                "max_monitor_gap_ms": 650.0
            }
        },
        "state_transitions": [
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
                    "experiment_id": "EXP-ABCDEF01",
                    "session_id": session_id,
                    "condition_class": "SETTLED_NOMINAL"
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
                    "executable_path": "/data/local/tmp/target_attempt"
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
            },
            {
                "sequence": 3,
                "event_type": "P0_EXIT_SLIDE_READY",
                "device_monotonic_ns": t_start + 5_000_000_000,
                "boot_id": boot_id,
                "session_id": session_id,
                "trial_id": trial_id,
                "attempt_ordinal": 1,
                "pid": pid,
                "producer": "TARGET_CHILD",
                "payload": {
                    "p0_duration_ns": 5_000_000_000,
                    "handshake_status": "READY"
                }
            },
            {
                "sequence": 4,
                "event_type": "OVERALL_SLIDE_ENTER",
                "device_monotonic_ns": t_start + 5_000_100_000,
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
            },
            {
                "sequence": 5,
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
            },
            {
                "sequence": 6,
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
                    "exit_status": 0
                }
            }
        ],
        "observables": [
            {
                "observable_id": "OBS-01",
                "observable_version": "1.0",
                "status": "OBSERVED",
                "timestamp_ns": t_end,
                "sequence": 5,
                "source_refs": [
                    {
                        "path": "raw/T0001_supervisor.stdout",
                        "sha256": "c" * 64,
                        "producer": "SUPERVISOR",
                        "artifact_type": "TEXT_LOG",
                        "selector": {
                            "selector_type": "LINE_RANGE",
                            "start": 10,
                            "end": 20
                        }
                    }
                ],
                "interpretation": "Clean terminal completion observed within 200s"
            }
        ],
        "classification": {
            "trial_terminal_class": "QUALIFYING_COMPLETION",
            "trial_validity": "VALID",
            "trial_evidence_vote": "COMPATIBLE_VOTE"
        }
    }
    for k, v in updates.items():
        record[k] = v
    return record


class PhaseJ21R1SchemaAndInvariantTests(unittest.TestCase):
    def test_positive_canonical_record(self):
        record = make_valid_record()
        valid, errors = validate_observation_record(record)
        self.assertTrue(valid, f"Validation failed with: {errors}")
        self.assertEqual(len(errors), 0)

    def test_neg_01_empty_artifact_identity(self):
        record = make_valid_record(artifact_identity={})
        valid, errors = validate_observation_record(record)
        self.assertFalse(valid)
        self.assertIn("EMPTY_ARTIFACT_IDENTITY", errors)

    def test_neg_02_forbidden_field(self):
        record = make_valid_record()
        record["FORBIDDEN_EXTRA_PROPERTY"] = "FAIL"
        valid, errors = validate_observation_record(record)
        self.assertFalse(valid)
        self.assertTrue(any("FORBIDDEN_FIELD" in e for e in errors))

    def test_neg_03_invalid_enum_validity(self):
        record = make_valid_record()
        record["classification"]["trial_validity"] = "MAYBE"
        valid, errors = validate_observation_record(record)
        self.assertFalse(valid)
        self.assertTrue(any("ILLEGAL_TRIAL_VALIDITY" in e for e in errors))

    def test_neg_04_bad_sha256_format(self):
        record = make_valid_record(boot_id="not_a_valid_sha256_hex")
        valid, errors = validate_observation_record(record)
        self.assertFalse(valid)
        self.assertIn("INVALID_BOOT_ID_SHA256_FORMAT", errors)

    def test_neg_05_duration_mismatch(self):
        record = make_valid_record()
        record["timing_metrics"]["candidate_elapsed_duration_ns"] += 1000
        valid, errors = validate_observation_record(record)
        self.assertFalse(valid)
        self.assertIn("DERIVED_DURATION_NS_MISMATCH", errors)

    def test_neg_06_headroom_mismatch(self):
        record = make_valid_record()
        record["timing_metrics"]["canonical_headroom_seconds"] = 1500.0
        valid, errors = validate_observation_record(record)
        self.assertFalse(valid)
        self.assertIn("CANONICAL_HEADROOM_MISMATCH", errors)

    def test_neg_07_clock_correlation_desync_1_1s(self):
        record = make_valid_record()
        # duration is 200.0s, set supervisor integer to 198 (delta 2.0 > 1.1)
        record["timing_metrics"]["supervisor_integer_elapsed_sec"] = 198
        valid, errors = validate_observation_record(record)
        self.assertFalse(valid)
        self.assertIn("CLOCK_CORRELATION_DESYNC_EXCEEDS_1_1_SEC", errors)

    def test_neg_08_boot_mutation_mid_trial(self):
        record = make_valid_record()
        # Change boot_id on the last event
        record["state_transitions"][-1]["boot_id"] = "f" * 64
        valid, errors = validate_observation_record(record)
        self.assertFalse(valid)
        self.assertTrue(any("BOOT_MUTATION_DETECTED" in e for e in errors))

    def test_neg_09_pid_mismatch_in_events(self):
        record = make_valid_record()
        record["state_transitions"][-1]["pid"] = 9999
        valid, errors = validate_observation_record(record)
        self.assertFalse(valid)
        self.assertTrue(any("PID_MISMATCH" in e for e in errors))

    def test_neg_10_illegal_reap_before_spawn(self):
        record = make_valid_record()
        reap_ev = copy.deepcopy(record["state_transitions"][-1])
        reap_ev["sequence"] = 0
        record["state_transitions"].insert(0, reap_ev)
        for idx, ev in enumerate(record["state_transitions"]):
            ev["sequence"] = idx
        valid, errors = validate_observation_record(record)
        self.assertFalse(valid)
        self.assertIn("ILLEGAL_REAP_BEFORE_SPAWN", errors)

    def test_neg_11_confounder_c2_freeze_with_valid_vote(self):
        record = make_valid_record()
        record["confounder_observations"]["c2_cgroup_freezer"]["classification"] = "C2_PRESENT"
        record["confounder_observations"]["c2_cgroup_freezer"]["freeze_event_count"] = 1
        valid, errors = validate_observation_record(record)
        self.assertFalse(valid)
        self.assertIn("CONFOUNDER_C2_PRESENT_CONFLICTS_WITH_VALID", errors)

    def test_neg_12_confounder_unknown_with_valid_vote(self):
        record = make_valid_record()
        record["confounder_observations"]["c3_thermal_throttling"]["classification"] = "C3_UNKNOWN"
        valid, errors = validate_observation_record(record)
        self.assertFalse(valid)
        self.assertIn("UNKNOWN_CONFOUNDER_CONFLICTS_WITH_VALID", errors)

    def test_neg_13_compatible_vote_exceeds_2195_headroom(self):
        record = make_valid_record()
        # Set duration to 2196.0 seconds
        t_start = 100_000_000_000
        t_end = t_start + int(2196.0 * 1e9)
        record["timing_metrics"]["post_fork_monotonic_ns"] = t_start
        record["timing_metrics"]["terminal_monotonic_ns"] = t_end
        record["timing_metrics"]["candidate_elapsed_duration_ns"] = t_end - t_start
        record["timing_metrics"]["candidate_elapsed_duration_seconds"] = 2196.0
        record["timing_metrics"]["canonical_headroom_seconds"] = 2200.0 - 2196.0
        record["timing_metrics"]["supervisor_integer_elapsed_sec"] = 2196
        record["state_transitions"][-1]["device_monotonic_ns"] = t_end
        # Attempting COMPATIBLE_VOTE at 2196s must fail validation
        valid, errors = validate_observation_record(record)
        self.assertFalse(valid)
        self.assertIn("COMPATIBLE_VOTE_EXCEEDS_2195_SEC_HEADROOM", errors)

    def test_neg_identity_wrong_full_build_fingerprint(self):
        """Negative test: wrong full build fingerprint -> REJECT."""
        record = make_valid_record()
        record["artifact_identity"]["build_fingerprint"] = "samsung/walleye/walleye:16/BP4A.251205.006/X510XXUCEZE4:user/release-keys"
        valid, errors = validate_observation_record(record)
        self.assertFalse(valid)
        self.assertTrue(any("WRONG_BUILD_FINGERPRINT" in e for e in errors))

    def test_neg_identity_correct_incremental_wrong_fingerprint(self):
        """Negative test: correct incremental but wrong fingerprint -> REJECT."""
        record = make_valid_record()
        record["artifact_identity"]["build_fingerprint"] = "samsung/gts9fewifieea/gts9fewifi:16/UP1A.231005.007/X510XXUCEZE4:user/release-keys"
        valid, errors = validate_observation_record(record)
        self.assertFalse(valid)
        self.assertTrue(any("WRONG_BUILD_FINGERPRINT" in e for e in errors))

    def test_neg_identity_5_15_189_wrong_kernel_build_identity(self):
        """Negative test: 5.15.189 kernel family but wrong kernel build identity -> REJECT."""
        record = make_valid_record()
        record["artifact_identity"]["kernel_identity"] = "5.15.189-android16-11-28562788"
        valid, errors = validate_observation_record(record)
        self.assertFalse(valid)
        self.assertTrue(any("WRONG_KERNEL_IDENTITY" in e for e in errors))

    def test_neg_identity_correct_model_wrong_device_codename(self):
        """Negative test: correct model but wrong device codename -> REJECT."""
        record = make_valid_record()
        record["artifact_identity"]["device_name"] = "gts9fewifixx"
        valid, errors = validate_observation_record(record)
        self.assertFalse(valid)
        self.assertTrue(any("WRONG_DEVICE_NAME" in e for e in errors))

    def test_neg_identity_fingerprint_csc_segment_changed(self):
        """Negative test: correct fingerprint except CSC/device segment changed -> REJECT."""
        record = make_valid_record()
        record["artifact_identity"]["build_fingerprint"] = "samsung/gts9fewifixx/gts9fewifi:16/BP4A.251205.006/X510XXUCEZE4:user/release-keys"
        valid, errors = validate_observation_record(record)
        self.assertFalse(valid)
        self.assertTrue(any("WRONG_BUILD_FINGERPRINT" in e for e in errors))

    def test_neg_identity_wrong_stock_image_sha256(self):
        """Negative test: wrong Image.stock SHA256 -> REJECT."""
        record = make_valid_record()
        record["artifact_identity"]["stock_image_sha256"] = "0" * 64
        valid, errors = validate_observation_record(record)
        self.assertFalse(valid)
        self.assertIn("WRONG_STOCK_IMAGE_SHA256", errors)

    def test_neg_superseded_clock_source_device_clock_monotonic(self):
        """Negative test: superseded clock source DEVICE_CLOCK_MONOTONIC -> REJECT."""
        record = make_valid_record()
        record["timing_metrics"]["clock_source"] = "DEVICE_CLOCK_MONOTONIC"
        valid, errors = validate_observation_record(record)
        self.assertFalse(valid)
        self.assertIn("ILLEGAL_CLOCK_SOURCE_DEVICE_CLOCK_MONOTONIC", errors)

    def test_neg_superseded_freezer_state_not_frozen(self):
        """Negative test: superseded freezer state NOT_FROZEN -> REJECT."""
        record = make_valid_record()
        record["condition_vector"]["freezer_state"] = "NOT_FROZEN"
        valid, errors = validate_observation_record(record)
        self.assertFalse(valid)
        self.assertIn("ILLEGAL_FREEZER_STATE_NOT_FROZEN", errors)


if __name__ == "__main__":
    unittest.main()
