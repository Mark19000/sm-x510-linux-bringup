import tempfile
import unittest
from pathlib import Path

from tools.u11_repro_compare import REQUIRED, compare


class U11ReproCompareTests(unittest.TestCase):
    def populate(self, directory: Path) -> None:
        for name in REQUIRED:
            path = directory / name
            path.parent.mkdir(parents=True, exist_ok=True)
            if name == "BUILD-METADATA":
                path.write_text("\n".join((
                    "artifact_class=offline-reference-only", "flash_authorized=no",
                    "source_release=X510XXSBDZB4", "source_base=X510XXU8DYJ4",
                    "target_stock=X510XXUCEZE4", "kernel_release=5.15.180",
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
