import tempfile
import unittest
from pathlib import Path

from tools.u11_modules_audit import (
    common_order_equal,
    dedupe,
    missing_closure,
    module_id,
    parse_modules_dep,
    parse_softdeps,
    verify_evidence_manifest,
)


class U11ModulesAuditTests(unittest.TestCase):
    def test_module_names_normalize_dash_and_underscore(self):
        self.assertEqual(module_id("kernel/drivers/ufs-exynos-core.ko"), "ufs_exynos_core")
        self.assertEqual(module_id("ufs_exynos_core"), "ufs_exynos_core")

    def test_prefix_dedupe_preserves_first_occurrence(self):
        self.assertEqual(dedupe(["early.ko", "other.ko", "early.ko"]), ["early.ko", "other.ko"])

    def test_common_relative_order_ignores_set_differences(self):
        self.assertEqual(common_order_equal(["a", "u11", "b"], ["stock", "a", "b"]), (True, 2))
        self.assertEqual(common_order_equal(["a", "b"], ["b", "a"]), (False, 2))

    def test_dependency_and_softdep_closure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dep = root / "modules.dep"
            dep.write_text("kernel/a.ko: kernel/b.ko\nkernel/b.ko:\n")
            soft = root / "modules.softdep"
            soft.write_text("softdep a pre: b post:c\n")
            dependencies = parse_modules_dep(dep)
            softdeps = parse_softdeps(soft)
            self.assertEqual(missing_closure({"a", "b", "c"}, dependencies, softdeps), [])
            self.assertEqual(missing_closure({"a", "b"}, dependencies, softdeps), ["a->c"])

    def test_stock_evidence_manifest_detects_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = root / "PROVENANCE.txt"
            payload.write_bytes(b"stock\n")
            import hashlib
            digest = hashlib.sha256(payload.read_bytes()).hexdigest()
            (root / "SHA256SUMS").write_text(f"{digest}  PROVENANCE.txt\n")
            self.assertEqual(verify_evidence_manifest(root), (1, []))
            payload.write_bytes(b"changed\n")
            self.assertTrue(verify_evidence_manifest(root)[1])


if __name__ == "__main__":
    unittest.main()
