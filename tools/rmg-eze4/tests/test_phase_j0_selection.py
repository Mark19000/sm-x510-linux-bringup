import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "phase_i_engine", ROOT / "tools/rmg-eze4/analysis/engine.py")
engine = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(engine)


def observation(*, level="E4", compatible=True, incompatible=False):
    return {
        "SESSION_ID": "SYN-J0-SESSION", "BOOT_ID": "SYN-J0-BOOT",
        "CONDITION_ID": "SYN-J0-CONDITION", "TRIAL_ID": "SYN-J0-TRIAL",
        "MEASUREMENT_ID": "SYN-J0-MEASUREMENT", "GROUP_ID": "G11",
        "PARAMETER": "DEFAULT_ATTEMPT_TIMEOUT_SEC",
        "OBSERVABLE": "synthetic_stage_labelled_duration",
        "TIMESTAMP_HOST": "2026-09-06T13:00:00Z",
        "TIMESTAMP_DEVICE_IF_AVAILABLE": None, "SOURCE": "SYNTHETIC_J0",
        "RAW_EVIDENCE_REF": "raw/sha256:synthetic-j0-timeout",
        "ENVIRONMENT": {"firmware": "SYNTHETIC_EZE4", "kind": "CONTROLLED_CONDITION"},
        "EXPECTED_CRITERION": "SYNTHETIC_TIMEOUT_RULE",
        "OBSERVED_VALUE": {"label": "SYNTHETIC"}, "RESULT": "NOT_OBSERVED",
        "CONFIDENCE": "HIGH", "CONFOUNDERS": [], "NOTES": "SYNTHETIC",
        "SYNTHETIC": True, "EVIDENCE_LEVEL": level,
        "OBSERVABLE_AVAILABLE": True,
        "COMPATIBILITY_CRITERION_MET": compatible,
        "INCOMPATIBILITY_CRITERION_MET": incompatible,
        "P0_DEPENDENCY": "P0_INDEPENDENT",
        "CHANGED_PARAMETERS": ["DEFAULT_ATTEMPT_TIMEOUT_SEC"],
        "BASELINE_MATCH": True, "SESSION_MATCH": True,
    }


class PhaseJ0SelectedCandidateGuards(unittest.TestCase):
    def test_compatible(self):
        got = engine.analyze_observations([observation()], required_level="E4")
        self.assertEqual(got["classification"], engine.COMPATIBLE)

    def test_incompatible(self):
        record = observation(compatible=False, incompatible=True)
        got = engine.analyze_observations([record], required_level="E4")
        self.assertEqual(got["classification"], engine.INCOMPATIBLE)

    def test_below_minimum_is_inconclusive(self):
        got = engine.analyze_observations([observation(level="E3")], required_level="E4")
        self.assertEqual(got["classification"], engine.INCONCLUSIVE)

    def test_missing_provenance_is_invalid(self):
        record = observation()
        del record["RAW_EVIDENCE_REF"]
        got = engine.analyze_observations([record], required_level="E4")
        self.assertEqual(got["classification"], engine.INVALID_MEASUREMENT)

    def test_attribution_failure_is_inconclusive(self):
        record = observation()
        record["CHANGED_PARAMETERS"].append("SYNTHETIC_SECOND_PARAMETER")
        got = engine.analyze_observations([record], required_level="E4")
        self.assertEqual(got["classification"], engine.INCONCLUSIVE)

    def test_cross_condition_requirement(self):
        got = engine.analyze_observations(
            [observation()], required_level="E4", require_cross_condition=True)
        self.assertEqual(got["classification"], engine.INCONCLUSIVE)


if __name__ == "__main__":
    unittest.main()
