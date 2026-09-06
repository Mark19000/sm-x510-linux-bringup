import tempfile
import unittest
from pathlib import Path

from tools.u11_repro_compare import REQUIRED, REQUIRED_METADATA, compare
from tools.repro_compare import compare as alias_compare


class U11ReproCompareTests(unittest.TestCase):
    def populate(self, directory: Path, kernel_release: str = "5.15.189-android13-3-33478785") -> None:
        for name in REQUIRED:
            path = directory / name
            path.parent.mkdir(parents=True, exist_ok=True)
            if name == "BUILD-METADATA":
                path.write_text("\n".join((
                    "artifact_class=offline-reference-only", "flash_authorized=no",
                    "source_release=X510XXSBDZB4", "source_base=X510XXU8DYJ4",
                    "target_stock=X510XXUCEZE4", f"kernel_release={kernel_release}",
                    "modules=282", "boot_image_created=no", "avb_signature_created=no",
                )) + "\n")
            else:
                path.write_bytes(("fixed:" + name).encode())

    def test_identical_independent_trees_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "run-a/dist"
            second = root / "run-b/dist"
            self.populate(first)
            self.populate(second)
            result = compare(first, second)
            self.assertTrue(result["reproducible"])
            self.assertEqual(result["first_run"], "run-a")
            self.assertEqual(result["second_run"], "run-b")

    def test_canonical_alias_functions_identically(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "run-a/dist"
            second = root / "run-b/dist"
            self.populate(first)
            self.populate(second)
            result = alias_compare(first, second)
            self.assertTrue(result["reproducible"])

    def test_identical_wrong_kernel_identity_rejected(self):
        """Two trees sharing the same wrong identity (e.g. 5.15.180) cannot self-confirm."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "run-a/dist"
            second = root / "run-b/dist"
            # Populate both with the superseded 5.15.180 kernel release
            self.populate(first, kernel_release="5.15.180")
            self.populate(second, kernel_release="5.15.180")
            result = compare(first, second)
            self.assertFalse(result["reproducible"])
            self.assertTrue(result["first_metadata_errors"])
            self.assertTrue(result["second_metadata_errors"])
            self.assertIn("5.15.180", result["first_metadata_errors"][0])

    def test_kernel_release_grounded_in_physical_evidence(self):
        """Validate REQUIRED_METADATA matches raw physical baseline capture."""
        raw_uname = Path(__file__).resolve().parents[1] / "docs/rmg-eze4/runtime-evidence/20260906T094426Z/raw/06_uname.txt"
        self.assertTrue(raw_uname.is_file(), f"Missing physical raw evidence {raw_uname}")
        uname_text = raw_uname.read_text(encoding="utf-8")
        if "STDOUT_BEGIN" in uname_text:
            stdout = uname_text.split("STDOUT_BEGIN", 1)[1].split("STDOUT_END", 1)[0].strip()
        else:
            stdout = uname_text.strip()
        physical_kernel_release = stdout.split()[2]
        self.assertEqual(REQUIRED_METADATA["kernel_release"], physical_kernel_release)
        self.assertEqual(REQUIRED_METADATA["kernel_release"], "5.15.189-android13-3-33478785")

    def test_difference_and_missing_required_file_fail(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "run-a/dist"
            second = root / "run-b/dist"
            self.populate(first)
            self.populate(second)
            (second / "Image").write_bytes(b"different")
            (second / "System.map").unlink()
            result = compare(first, second)
            self.assertFalse(result["reproducible"])
            self.assertIn("Image", result["differing"])
            self.assertIn("System.map", result["missing_in_second"])

    def test_symlink_or_wrong_identity_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "run-a/dist"
            second = root / "run-b/dist"
            self.populate(first)
            self.populate(second)
            (first / "link").symlink_to("Image")
            (second / "BUILD-METADATA").write_text("source_release=wrong\n")
            result = compare(first, second)
            self.assertFalse(result["reproducible"])
            self.assertEqual(result["unsafe_in_first"], ["link"])
            self.assertTrue(result["second_metadata_errors"])

    def test_same_tree_is_not_independent(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)
            with self.assertRaises(ValueError):
                compare(path, path)


if __name__ == "__main__":
    unittest.main()
