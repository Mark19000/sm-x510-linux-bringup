import ast
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
ANALYSIS_DIR = ROOT / "tools" / "rmg-eze4" / "analysis"
TESTS_DIR = ROOT / "tools" / "rmg-eze4" / "tests"

sys.path.insert(0, str(ANALYSIS_DIR))
sys.path.insert(0, str(TESTS_DIR))

from aggregator import aggregate_campaign  # noqa: E402
from validator import validate_observation_record  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures" / "phase_j2_timeout_scenarios.json"


class PhaseJ2CanonicalDesignTests(unittest.TestCase):
    """Canonical Phase J2 campaign design and semantic boundary tests."""

    def test_canonical_campaign_scenarios(self):
        """All canonical campaign fixtures in phase_j2_timeout_scenarios.json pass."""
        scenarios = json.loads(FIXTURES.read_text())
        self.assertGreaterEqual(len(scenarios), 12)

        for scenario in scenarios:
            scn_id = scenario["id"]
            with self.subTest(scenario=scn_id):
                records = scenario["records"]
                expected_verdict = scenario["expected"]
                expected_reason_substr = scenario.get("expected_reason_substr")

                # Every record, including a trial classified INVALID, must be a
                # structurally and semantically valid observation record.
                for r in records:
                    valid, errors = validate_observation_record(r)
                    self.assertTrue(valid, f"Scenario {scn_id} record invalid: {errors}")

                result = aggregate_campaign(records)

                # Use independent string literal assertions
                self.assertEqual(result["verdict"], expected_verdict)
                if expected_reason_substr:
                    all_reasons = " ".join(result.get("reasons", []))
                    self.assertIn(
                        expected_reason_substr,
                        all_reasons,
                        f"Scenario {scn_id}: reason '{expected_reason_substr}' not found in '{all_reasons}'"
                    )

    def test_semantic_boundary_single_timeout_is_inconclusive(self):
        """CRITICAL: One attributable timeout at E4 yields INCONCLUSIVE, not INCOMPATIBLE.

        Guards against the error-cancelling bug where single_timeout previously downgraded
        evidence_level to E2 to mask legacy engine.py's incorrect falsification logic.
        """
        scenarios = {s["id"]: s for s in json.loads(FIXTURES.read_text())}
        scn = scenarios["single_attributable_timeout"]

        # Ensure evidence level is full E4 across all records
        for r in scn["records"]:
            self.assertEqual(r.get("schema_version"), "2.2.1")
            self.assertEqual(r.get("event_grammar_version"), "2.1.1")
            art = r.get("artifact_identity", {})
            self.assertEqual(art.get("kernel_identity"), "5.15.189-android13-3-33478785")

        result = aggregate_campaign(scn["records"])

        # Canonical semantics: 1 timeout -> INCONCLUSIVE
        self.assertEqual(result["verdict"], "INCONCLUSIVE")
        self.assertNotEqual(result["verdict"], "INCOMPATIBLE")
        self.assertIn(
            "ATTRIBUTABLE_TIMEOUT_WITHOUT_MEETING_FALSIFICATION_THRESHOLD",
            result["reasons"]
        )

    def test_adversarial_neighboring_boundaries(self):
        """Adversarial boundary cases protecting the timeout falsification rule."""
        scenarios = {s["id"]: s for s in json.loads(FIXTURES.read_text())}

        # 1 timeout -> not INCOMPATIBLE
        res1 = aggregate_campaign(scenarios["single_attributable_timeout"]["records"])
        self.assertEqual(res1["verdict"], "INCONCLUSIVE")
        self.assertNotEqual(res1["verdict"], "INCOMPATIBLE")

        # 2 timeouts -> not INCOMPATIBLE
        res2 = aggregate_campaign(scenarios["two_attributable_timeouts"]["records"])
        self.assertEqual(res2["verdict"], "INCONCLUSIVE")
        self.assertNotEqual(res2["verdict"], "INCOMPATIBLE")

        # 3 timeouts on single boot -> not INCOMPATIBLE
        res3 = aggregate_campaign(scenarios["three_timeouts_single_boot"]["records"])
        self.assertEqual(res3["verdict"], "INCONCLUSIVE")
        self.assertNotEqual(res3["verdict"], "INCOMPATIBLE")

        # 3 timeouts in same condition across 2 boots -> INCOMPATIBLE
        res4 = aggregate_campaign(scenarios["three_timeouts_same_condition_two_boots"]["records"])
        self.assertEqual(res4["verdict"], "INCOMPATIBLE")

        # Cross-condition timeouts do not pool -> not INCOMPATIBLE
        res5 = aggregate_campaign(scenarios["cross_condition_timeouts_do_not_pool"]["records"])
        self.assertEqual(res5["verdict"], "INCONCLUSIVE")
        self.assertNotEqual(res5["verdict"], "INCOMPATIBLE")

        # Invalid trial does not count toward threshold -> not INCOMPATIBLE
        res6 = aggregate_campaign(scenarios["invalid_timeout_not_counted"]["records"])
        self.assertEqual(res6["verdict"], "INCONCLUSIVE")
        self.assertNotEqual(res6["verdict"], "INCOMPATIBLE")

        # Threshold + 1 (4) remains INCOMPATIBLE. Build this mutation without
        # consulting aggregator constants so a changed production threshold is killed.
        four = copy.deepcopy(scenarios["three_timeouts_same_condition_two_boots"]["records"])
        timeout_template = next(
            r for r in four
            if r["classification"]["trial_terminal_class"] == "SUPERVISOR_OVERALL_TIMEOUT"
        )
        fourth = next(
            r for r in four
            if r["condition_vector"]["condition_class"] == "SETTLED_NOMINAL"
            and r["classification"]["trial_terminal_class"] == "QUALIFYING_COMPLETION"
        )
        fourth["timing_metrics"] = copy.deepcopy(timeout_template["timing_metrics"])
        fourth["classification"] = copy.deepcopy(timeout_template["classification"])
        self.assertEqual(aggregate_campaign(four)["verdict"], "INCOMPATIBLE")

    def test_isolated_cell_deficit_requires_two_trials_per_cell(self):
        """CRITICAL: Every boot x condition cell requires >= 2 valid trials (E4 invariant).

        This test evaluates the 'isolated_cell_deficit' scenario, which deliberately contains
        exactly 12 valid qualifying trials (Boot 1: 1 SETTLED_NOMINAL + 3 ELEVATED_VALID;
        Boot 2: 2 + 2; Boot 3: 2 + 2 = 12 total).

        By ensuring total qualifying trials == 12 (>= 12), the global trial count guard cannot mask
        the per-cell requirement. If the per-cell check is relaxed (e.g. MUT-10: cell_count < 1),
        the verdict becomes COMPATIBLE (or the cell deficit reason disappears), immediately
        failing the independent oracle assertion below.
        """
        scenarios = {s["id"]: s for s in json.loads(FIXTURES.read_text())}
        self.assertIn("isolated_cell_deficit", scenarios)
        scn = scenarios["isolated_cell_deficit"]

        records = scn["records"]
        # Invariant: exactly 12 records, all valid qualifying trials
        self.assertEqual(len(records), 12)
        valid_records = [r for r in records if r.get("classification", {}).get("trial_validity") == "VALID"]
        self.assertEqual(len(valid_records), 12)

        # Invariant: Schema v2.2.1 and Event Grammar v2.1.1 compliance
        for r in records:
            valid, errors = validate_observation_record(r)
            self.assertTrue(valid, f"isolated_cell_deficit record invalid: {errors}")

        result = aggregate_campaign(records)

        # Independent semantic oracle assertions:
        # 1. Campaign verdict must be INCONCLUSIVE (rejected specifically due to cell deficit)
        self.assertEqual(result["verdict"], "INCONCLUSIVE")
        # 2. Verdict must NOT be COMPATIBLE (which MUT-10 incorrectly produces)
        self.assertNotEqual(result["verdict"], "COMPATIBLE")
        # 3. Specific cell deficit reason must be present
        reasons = result.get("reasons", [])
        self.assertTrue(
            any("VALID_TRIALS_LT_2" in r for r in reasons),
            f"Expected cell deficit reason containing 'VALID_TRIALS_LT_2', got: {reasons}"
        )
        # 4. Total valid trials must NOT be cited as a deficit because count is 12
        self.assertFalse(
            any("TOTAL_VALID_TRIALS" in r for r in reasons),
            f"Global total trial count guard fired unexpectedly: {reasons}"
        )

    def test_no_engine_import_in_j2(self):
        """Regression guard: ensure canonical J2 code does not import legacy engine.py."""
        j2_files = [
            *(
                path for path in (ROOT / "tools/rmg-eze4/analysis").glob("*.py")
                if path.name != "engine.py"
            ),
            ROOT / "tools/rmg-eze4/tests/test_phase_j2_design.py",
            ROOT / "tools/rmg-eze4/tests/test_phase_j2_1_r1_replay.py",
            ROOT / "tools/rmg-eze4/tests/test_phase_j2_1_r1_schema.py",
            ROOT / "tools/rmg-eze4/tests/test_phase_j2_1_r1_consistency.py",
        ]

        for filepath in j2_files:
            with self.subTest(file=filepath.name):
                tree = ast.parse(filepath.read_text(), filename=str(filepath))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            self.assertNotEqual(
                                alias.name, "engine",
                                f"{filepath.name} imports legacy 'engine'"
                            )
                    elif isinstance(node, ast.ImportFrom):
                        self.assertNotEqual(
                            node.module, "engine",
                            f"{filepath.name} imports from legacy 'engine'"
                        )

    def test_aggregator_rejects_malformed_missing_and_unsupported_schema(self):
        scenarios = {s["id"]: s for s in json.loads(FIXTURES.read_text())}
        clean = scenarios["clean_compatible"]["records"]

        malformed = copy.deepcopy(clean)
        malformed[0] = "not-an-observation"
        self.assertEqual(aggregate_campaign(malformed)["verdict"], "INVALID_EXPERIMENT")

        missing = copy.deepcopy(clean)
        del missing[0]["classification"]
        self.assertEqual(aggregate_campaign(missing)["verdict"], "INVALID_EXPERIMENT")

        old_schema = copy.deepcopy(clean)
        old_schema[0]["schema_version"] = "2.2.0"
        result = aggregate_campaign(old_schema)
        self.assertEqual(result["verdict"], "INVALID_EXPERIMENT")
        self.assertTrue(any("INVALID_SCHEMA_VERSION_2.2.0" in r for r in result["reasons"]))

    def test_duplicate_trial_and_hidden_extra_record_fail_closed(self):
        scenarios = {s["id"]: s for s in json.loads(FIXTURES.read_text())}
        clean = copy.deepcopy(scenarios["clean_compatible"]["records"])
        clean.append(copy.deepcopy(clean[0]))
        result = aggregate_campaign(clean)
        self.assertEqual(result["verdict"], "INVALID_EXPERIMENT")
        self.assertTrue(any("DUPLICATE_TRIAL_RECORD" in r for r in result["reasons"]))

    def test_reordered_and_duplicate_events_fail_closed(self):
        scenarios = {s["id"]: s for s in json.loads(FIXTURES.read_text())}
        clean = scenarios["clean_compatible"]["records"]

        reordered = copy.deepcopy(clean)
        reordered[0]["state_transitions"] = list(reversed(reordered[0]["state_transitions"]))
        self.assertEqual(aggregate_campaign(reordered)["verdict"], "INVALID_EXPERIMENT")

        duplicate_event = copy.deepcopy(clean)
        duplicate_event[0]["state_transitions"].append(
            copy.deepcopy(duplicate_event[0]["state_transitions"][-1])
        )
        self.assertEqual(aggregate_campaign(duplicate_event)["verdict"], "INVALID_EXPERIMENT")


if __name__ == "__main__":
    unittest.main()
