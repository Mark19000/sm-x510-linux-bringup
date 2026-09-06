"""Unit test wrapper for cross-artifact consistency checker."""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "rmg-eze4" / "analysis"))

from check_consistency import check_consistency  # noqa: E402


class PhaseJ21R1CrossArtifactConsistencyTests(unittest.TestCase):
    def test_cross_artifact_consistency(self):
        errors = check_consistency()
        self.assertEqual(len(errors), 0, f"Consistency check failed with errors: {errors}")


if __name__ == "__main__":
    unittest.main()
