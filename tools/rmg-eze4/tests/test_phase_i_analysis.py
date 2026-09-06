import copy
import csv
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ENGINE_PATH = ROOT / "tools/rmg-eze4/analysis/engine.py"
SPEC = importlib.util.spec_from_file_location("phase_i_engine", ENGINE_PATH)
engine = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(engine)

GROUPS = [f"G{i}" for i in range(1, 13)]
AMBIGUOUS = {"G10", "G12"}


def record(group="G8", parameter="SKB_SEND_SIZE", level="E4", compatible=True,
           incompatible=False, boot="SYN-BOOT-A", condition="SYN-COND-A"):
    return {
        "SESSION_ID": "SYN-SESSION-001", "BOOT_ID": boot,
        "CONDITION_ID": condition, "TRIAL_ID": "SYN-TRIAL-001",
        "MEASUREMENT_ID": f"SYN-M-{group}-{boot}-{condition}",
        "GROUP_ID": group, "PARAMETER": parameter,
        "OBSERVABLE": "synthetic_state_label", "TIMESTAMP_HOST": "2026-09-06T12:00:00Z",
        "TIMESTAMP_DEVICE_IF_AVAILABLE": None, "SOURCE": "SYNTHETIC_FIXTURE",
        "RAW_EVIDENCE_REF": f"raw/sha256:synthetic-{group}-{boot}-{condition}",
        "ENVIRONMENT": {"firmware": "SYNTHETIC_EZE4", "condition_kind": "OBSERVED_CONDITION"},
        "EXPECTED_CRITERION": "SYNTHETIC_PHASE_H_RULE",
        "OBSERVED_VALUE": {"label": "SYNTHETIC"}, "RESULT": "NOT_OBSERVED",
        "CONFIDENCE": "HIGH", "CONFOUNDERS": [], "NOTES": "SYNTHETIC",
        "SYNTHETIC": True, "EVIDENCE_LEVEL": level, "OBSERVABLE_AVAILABLE": True,
        "COMPATIBILITY_CRITERION_MET": compatible,
        "INCOMPATIBILITY_CRITERION_MET": incompatible,
        "P0_DEPENDENCY": "P0_INDEPENDENT", "CHANGED_PARAMETERS": [parameter],
        "BASELINE_MATCH": True, "SESSION_MATCH": True,
    }


class PhaseIAnalysisTests(unittest.TestCase):
    def test_all_12_groups_three_way(self):
        for group in GROUPS:
            with self.subTest(group=group, outcome="compatible"):
                if group in AMBIGUOUS:
                    compatible_record = record(group=group)
                    if group == "G10":
                        compatible_record["P0_DEPENDENCY"] = "P0_ONLY"
                    got = engine.analyze_observations([compatible_record], required_level="E4",
                                                      p0_resolved=False if group == "G10" else True)
                    expected = engine.INCONCLUSIVE if group == "G10" else engine.COMPATIBLE
                else:
                    got = engine.analyze_observations([record(group=group)], required_level="E4")
                    expected = engine.COMPATIBLE
                self.assertEqual(got["classification"], expected)
            with self.subTest(group=group, outcome="incompatible"):
                r = record(group=group, compatible=False, incompatible=True)
                got = engine.analyze_observations([r], required_level="E4")
                self.assertEqual(got["classification"], engine.INCOMPATIBLE)
            with self.subTest(group=group, outcome="inconclusive"):
                r = record(group=group, level="E1")
                got = engine.analyze_observations([r], required_level="E4")
                self.assertEqual(got["classification"], engine.INCONCLUSIVE)

    def test_all_19_parameters_positive_and_negative(self):
        with (ROOT / "docs/rmg-eze4/phase_h_evidence_requirements.csv").open() as handle:
            rows = list(csv.DictReader(handle))
        with (ROOT / "docs/rmg-eze4/phase_h_p0_dependency.csv").open() as handle:
            p0 = {r["PARAMETER"]: r["P0_DEPENDENCY"] for r in csv.DictReader(handle)}
        self.assertEqual(len(rows), 19)
        for row in rows:
            with self.subTest(parameter=row["NAME"], outcome="positive"):
                r = record(parameter=row["NAME"], level=row["MINIMUM_VALIDATED_COMPATIBLE"])
                r["P0_DEPENDENCY"] = p0[row["NAME"]]
                unresolved = p0[row["NAME"]] == "P0_ONLY"
                got = engine.analyze_observations(
                    [r], required_level=row["MINIMUM_VALIDATED_COMPATIBLE"],
                    p0_resolved=not unresolved)
                expected = engine.INCONCLUSIVE if unresolved else engine.COMPATIBLE
                self.assertEqual(got["classification"], expected)
            with self.subTest(parameter=row["NAME"], outcome="negative"):
                r = record(parameter=row["NAME"], level=row["MINIMUM_VALIDATED_INCOMPATIBLE"],
                           compatible=False, incompatible=True)
                r["P0_DEPENDENCY"] = p0[row["NAME"]]
                got = engine.analyze_observations([r], required_level=row["MINIMUM_VALIDATED_INCOMPATIBLE"])
                self.assertEqual(got["classification"], engine.INCOMPATIBLE)

    def test_evidence_totals_and_enforcement(self):
        with (ROOT / "docs/rmg-eze4/phase_h_evidence_requirements.csv").open() as handle:
            rows = list(csv.DictReader(handle))
        counts = {level: sum(r["MINIMUM_VALIDATED_COMPATIBLE"] == level for r in rows)
                  for level in ("E2", "E3", "E4")}
        self.assertEqual(counts, {"E2": 0, "E3": 3, "E4": 16})
        for row in rows:
            r = record(parameter=row["NAME"], level="E1")
            got = engine.analyze_observations([r], required_level=row["MINIMUM_VALIDATED_COMPATIBLE"])
            self.assertEqual(got["classification"], engine.INCONCLUSIVE)

    def test_edge_case_fixture(self):
        path = ROOT / "tools/rmg-eze4/tests/fixtures/synthetic_edge_cases.json"
        cases = json.loads(path.read_text())["cases"]
        self.assertEqual(len(cases), 10)
        for case in cases:
            with self.subTest(case=case["id"]):
                a = record()
                records = [a]
                if case.get("compatibility") is False:
                    a["COMPATIBILITY_CRITERION_MET"] = False
                if case.get("incompatibility"):
                    a["INCOMPATIBILITY_CRITERION_MET"] = True
                if case.get("evidence_level"):
                    a["EVIDENCE_LEVEL"] = case["evidence_level"]
                if case.get("observable_available") is False:
                    a["OBSERVABLE_AVAILABLE"] = False
                if case.get("outlier_unresolved"):
                    a["OUTLIER_UNRESOLVED"] = True
                if case.get("omit"):
                    del a[case["omit"]]
                if case.get("baseline_match") is False:
                    a["BASELINE_MATCH"] = False
                if case.get("session_match") is False:
                    a["SESSION_MATCH"] = False
                if case.get("two_opposed_records") or case.get("two_opposed_boots") or case.get("two_opposed_conditions"):
                    b = copy.deepcopy(a)
                    b["COMPATIBILITY_CRITERION_MET"] = False
                    b["INCOMPATIBILITY_CRITERION_MET"] = True
                    if case.get("two_opposed_boots"):
                        b["BOOT_ID"] = "SYN-BOOT-B"
                    if case.get("two_opposed_conditions"):
                        b["CONDITION_ID"] = "SYN-COND-B"
                    records.append(b)
                got = engine.analyze_observations(records, required_level="E4")
                self.assertEqual(got["classification"], case["expected"])

    def test_attribution_rules(self):
        r = record()
        self.assertEqual(engine.assess_attribution(r)[0], engine.ATTRIBUTABLE)
        r["CHANGED_PARAMETERS"] = ["SKB_SEND_SIZE", "SKB_RECLAIM_SENDS"]
        self.assertEqual(engine.assess_attribution(r)[0], engine.PARTIALLY_ATTRIBUTABLE)
        self.assertEqual(engine.assess_attribution(r, prerequisites_valid=False)[0],
                         engine.NOT_ATTRIBUTABLE)

    def test_five_must_validate_six_scenarios(self):
        parameters = {
            "SKB_SEND_SIZE": ("G8", "E3"),
            "SLIDE_WAIT_NSEC": ("G3", "E4"),
            "SLIDE_REQUEUE_ARM_USEC": ("G3", "E4"),
            "FOPS_ROUTE_COARSE_DELAY_USEC": ("G4", "E4"),
            "FOPS_ROUTE_FINE_DELAY_TICKS": ("G4", "E4"),
        }
        for parameter, (group, required) in parameters.items():
            with self.subTest(parameter=parameter, scenario="compatible"):
                a = record(group=group, parameter=parameter, level=required)
                b = record(group=group, parameter=parameter, level=required,
                           condition="SYN-COND-B")
                got = engine.analyze_observations([a, b], required_level=required,
                                                  require_cross_condition=required == "E4")
                self.assertEqual(got["classification"], engine.COMPATIBLE)
            with self.subTest(parameter=parameter, scenario="incompatible"):
                a = record(group=group, parameter=parameter, level="E3",
                           compatible=False, incompatible=True)
                got = engine.analyze_observations([a], required_level="E3")
                self.assertEqual(got["classification"], engine.INCOMPATIBLE)
            with self.subTest(parameter=parameter, scenario="insufficient"):
                a = record(group=group, parameter=parameter, level="E1")
                got = engine.analyze_observations([a], required_level=required)
                self.assertEqual(got["classification"], engine.INCONCLUSIVE)
            with self.subTest(parameter=parameter, scenario="confounded"):
                a = record(group=group, parameter=parameter, level=required)
                a["CHANGED_PARAMETERS"] = [parameter, "SYNTHETIC_OTHER_PARAMETER"]
                got = engine.analyze_observations([a], required_level=required)
                self.assertEqual(got["classification"], engine.INCONCLUSIVE)
            with self.subTest(parameter=parameter, scenario="condition_drift"):
                a = record(group=group, parameter=parameter, level=required)
                b = copy.deepcopy(a)
                b["MEASUREMENT_ID"] += "-DRIFT"
                b["ENVIRONMENT"] = {**b["ENVIRONMENT"], "load_class": "SYNTHETIC_ALT"}
                got = engine.analyze_observations([a, b], required_level=required)
                self.assertEqual(got["classification"], engine.INVALID_MEASUREMENT)
            with self.subTest(parameter=parameter, scenario="missing_prerequisite"):
                a = record(group=group, parameter=parameter, level=required)
                got = engine.analyze_observations([a], required_level=required,
                                                  prerequisites_valid=False)
                self.assertEqual(got["classification"], engine.INCONCLUSIVE)

    def test_p0_uncertainty_is_preserved(self):
        r = record(group="G10", parameter="P0_FINGERPRINT_MIN_MARGIN")
        r["P0_DEPENDENCY"] = "P0_ONLY"
        r["OBSERVED_VALUE"] = {"table_member": True, "log_absent": True,
                               "one_observed_label": "SYNTHETIC_LABEL"}
        got = engine.analyze_observations([r], required_level="E4", p0_resolved=False)
        self.assertEqual(got["classification"], engine.INCONCLUSIVE)

    def test_cross_boot_and_condition_requirements(self):
        a = record()
        self.assertEqual(engine.analyze_observations([a], required_level="E4",
                                                    require_cross_boot=True)["classification"],
                         engine.INCONCLUSIVE)
        b = record(boot="SYN-BOOT-B", condition="SYN-COND-B")
        self.assertEqual(engine.analyze_observations([a, b], required_level="E4",
                                                    require_cross_boot=True,
                                                    require_cross_condition=True)["classification"],
                         engine.COMPATIBLE)

    def test_synthetic_campaign_shape(self):
        path = ROOT / "tools/rmg-eze4/tests/fixtures/synthetic_campaign.json"
        campaign = json.loads(path.read_text())
        self.assertTrue(campaign["synthetic"])
        self.assertGreaterEqual(len(campaign["sessions"]), 2)
        self.assertGreaterEqual(len(campaign["boots"]), 2)
        self.assertGreaterEqual(len(campaign["conditions"]), 2)
        self.assertTrue(any(case.get("stop_rule") for case in campaign["cases"]))
        self.assertTrue(any(case.get("reason") == "P0_BLOCKED" for case in campaign["cases"]))


if __name__ == "__main__":
    unittest.main()
