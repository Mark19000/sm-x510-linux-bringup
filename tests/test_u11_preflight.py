import hashlib
import tarfile
import tempfile
import unittest
from pathlib import Path

from tools.u11_preflight import (
    initramfs_fit,
    module_names_from_vendor_list,
    parse_env,
    parse_kernel_config,
    repro_report_valid,
    verify_checksum_file,
    verify_tar_extraction,
)


class U11PreflightTests(unittest.TestCase):
    def test_env_parser_is_data_only(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "identity.env"
            path.write_text("# comment\nU11_MODEL=SM-X510\nU11_KERNEL_RELEASE=5.15.180\n")
            self.assertEqual(parse_env(path)["U11_MODEL"], "SM-X510")
            path.write_text("BAD=$(touch nope)\n")
            with self.assertRaises(ValueError):
                parse_env(path)

    def test_checksum_manifest_detects_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = root / "Image"
            payload.write_bytes(b"kernel")
            digest = hashlib.sha256(b"kernel").hexdigest()
            manifest = root / "SHA256SUMS"
            manifest.write_text(f"{digest}  Image\n")
            checked, failures = verify_checksum_file(root, manifest)
            self.assertEqual(checked, ["Image"])
            self.assertEqual(failures, [])
            payload.write_bytes(b"changed")
            self.assertTrue(verify_checksum_file(root, manifest)[1])

    def test_checksum_manifest_rejects_symlink_escape_and_duplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "artifact"
            outside = root / "outside"
            artifact.mkdir()
            outside.write_bytes(b"secret")
            (artifact / "link").symlink_to(outside)
            digest = hashlib.sha256(b"secret").hexdigest()
            manifest = artifact / "SHA256SUMS"
            manifest.write_text(f"{digest}  link\n{digest}  link\n")
            checked, failures = verify_checksum_file(artifact, manifest)
            self.assertEqual(checked, [])
            self.assertTrue(any("symlink" in item for item in failures))
            self.assertTrue(any("duplicada" in item for item in failures))

    def test_config_and_vendor_module_parsers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / ".config"
            config.write_text("CONFIG_DEVTMPFS=y\n# CONFIG_VT is not set\n")
            self.assertEqual(parse_kernel_config(config), {"CONFIG_DEVTMPFS": "y", "CONFIG_VT": "n"})
            modules = root / "vendor.cfg"
            modules.write_text("# ignored\nmodprobe|input_booster_lkm.ko\ninsmod||/vendor/lib/modules/foo.ko\n")
            self.assertEqual(module_names_from_vendor_list(modules), ["input_booster_lkm.ko", "/vendor/lib/modules/foo.ko"])

    def test_initramfs_fit_reports_signed_margin(self):
        self.assertEqual(initramfs_fit(90, 100), {"bytes": 90, "limit": 100, "margin": 10, "fits": True})
        self.assertEqual(initramfs_fit(110, 100)["margin"], -10)
        self.assertFalse(initramfs_fit(110, 100)["fits"])

    def test_repro_report_requires_two_distinct_clean_runs(self):
        report = {
            "schema": 1,
            "profile": "SM-X510-X510XXSBDZB4-U11-fixed-offline",
            "reproducible": True,
            "physical_write_gate": "NO-GO",
            "first_run": "run-a",
            "second_run": "run-b",
            "missing_in_first": [],
            "missing_in_second": [],
            "only_in_first": [],
            "only_in_second": [],
            "differing": [],
            "unsafe_in_first": [],
            "unsafe_in_second": [],
            "first_metadata_errors": [],
            "second_metadata_errors": [],
        }
        self.assertTrue(repro_report_valid(report))
        report["second_run"] = "run-a"
        self.assertFalse(repro_report_valid(report))

    def test_tar_extraction_verifier_rejects_extra_or_changed_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            (source / "module.ko").write_bytes(b"module")
            archive = root / "modules.tar.gz"
            with tarfile.open(archive, "w:gz") as bundle:
                bundle.add(source / "module.ko", arcname="modules-root/module.ko")
            extracted = root / "extracted"
            (extracted / "modules-root").mkdir(parents=True)
            (extracted / "modules-root/module.ko").write_bytes(b"module")
            self.assertEqual(verify_tar_extraction(archive, extracted), (1, []))
            (extracted / "modules-root/extra").write_bytes(b"unexpected")
            self.assertTrue(verify_tar_extraction(archive, extracted)[1])

    def test_u11_initramfs_wrapper_has_separate_namespace_and_no_flash(self):
        root = Path(__file__).resolve().parent.parent
        script = (root / "scripts/build-u11-initramfs.sh").read_text()
        self.assertIn("artifacts/initramfs/u11", script)
        self.assertIn("artifacts/kernel/wifi", script)
        self.assertIn("artifacts/stock", script)
        self.assertIn("U11_KERNEL_RELEASE", script)
        self.assertIn("INITRAMFS_STAGE_PARENT", script)
        self.assertIn("physical_write_gate=NO-GO", script)
        self.assertIn("source_modules_archive_sha256", script)
        self.assertIn("source_modules_tree_sha256", script)
        for forbidden_command in ("fastboot flash", "heimdall flash", "dd of=/dev/"):
            self.assertNotIn(forbidden_command, script)


if __name__ == "__main__":
    unittest.main()
