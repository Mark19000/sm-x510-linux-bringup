"""Host-only tests for the U3/U11 OSRC comparison pipeline."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/osrc_tree_compare.py"


def run_compare(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


class OsrcTreeCompareTest(unittest.TestCase):
    def make_tree(self, root: pathlib.Path, *, u11: bool = False) -> pathlib.Path:
        files = {
            "Makefile": "all:\n\t@true\n",
            "build_kernel.sh": "#!/bin/sh\ntrue\n",
            "arch/arm64/configs/board_defconfig": "CONFIG_TEST=y\n",
            "drivers/demo/demo.c": "int demo(void) { return 1; }\n",
            "drivers/demo/Kconfig": "config TEST\n\tbool \"test\"\n",
            "arch/arm64/boot/dts/vendor/board.dts": (
                "/dts-v1/;\n"
                "/ {\n"
                "  board: board { compatible = \"vendor,board\"; };\n"
                "};\n"
            ),
            "arch/arm64/boot/dts/vendor/common.dtsi": "/* fragment */\n",
            "download.tar.part": "not a source\n",
        }
        if u11:
            files["drivers/demo/demo.c"] = "int demo(void) { return 2; }\n"
            files["drivers/new/new.c"] = "int new_driver(void) { return 0; }\n"
            files["arch/arm64/configs/u11_defconfig"] = "CONFIG_NEW=y\n"
        for relative, content in files.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        return root

    def test_argument_validation_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            u3 = self.make_tree(root / "u3")
            output = root / "report"
            result = run_compare(
                "--u3-dir", str(u3),
                "--u11-dir", str(root / "missing.part"),
                "--output", str(output),
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn(".part", result.stderr)
            self.assertFalse(output.exists())

    def test_inventory_and_eze4_matrix_are_deterministic(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            u3 = self.make_tree(root / "u3")
            u11 = self.make_tree(root / "u11", u11=True)
            eze4 = root / "eze4"
            eze4.mkdir()
            (eze4 / "overlay.dts").write_text(
                "/dts-v1/;\n"
                "/ { board: board { compatible = \"vendor,board\"; }; };\n",
                encoding="utf-8",
            )
            # A binary DTB is retained in the evidence inventory but cannot be
            # compared semantically without a decompiled DTS.
            (eze4 / "base.dtb").write_bytes(b"\xd0\x0d\xfe\xed")
            output = root / "report"
            command = (
                "--u3-dir", str(u3), "--u11-dir", str(u11),
                "--eze4-dir", str(eze4), "--output", str(output),
            )
            first = run_compare(*command)
            second = run_compare(*command)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            report = json.loads((output / "comparison.json").read_text(encoding="utf-8"))
            self.assertEqual(first.stdout, second.stdout)
            self.assertEqual(report["tool"], "osrc-tree-compare")
            self.assertEqual(report["inputs"]["u3"]["ignored_partial_files"], 1)
            self.assertEqual(report["categories"]["drivers"]["changed"][0]["path"], "drivers/demo/demo.c")
            self.assertIn("drivers/new/new.c", report["categories"]["drivers"]["u11_only"])
            self.assertIn("arch/arm64/configs/u11_defconfig", report["categories"]["configs"]["u11_only"])
            self.assertEqual(len(report["dts_matrix"]), 1)
            row = report["dts_matrix"][0]
            self.assertEqual(row["u3"]["path"], "arch/arm64/boot/dts/vendor/board.dts")
            self.assertEqual(row["u11"]["confidence"], "path")
            self.assertEqual(row["u3_eze4"]["status"], "EQUIVALENT")
            self.assertEqual(len(report["eze4"]["unsupported"]), 1)
            self.assertTrue((output / "comparison.md").read_text(encoding="utf-8"))

    def test_failed_rerun_preserves_previous_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            u3 = self.make_tree(root / "u3")
            u11 = self.make_tree(root / "u11", u11=True)
            output = root / "report"
            good = run_compare(
                "--u3", str(u3), "--u11", str(u11), "--output", str(output)
            )
            self.assertEqual(good.returncode, 0, good.stderr)
            before = (output / "comparison.json").read_bytes()
            bad = run_compare(
                "--u3", str(u3), "--u11", str(root / "does-not-exist"),
                "--output", str(output),
            )
            self.assertEqual(bad.returncode, 2)
            self.assertEqual((output / "comparison.json").read_bytes(), before)

    def test_existing_non_transactional_directory_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            u3 = self.make_tree(root / "u3")
            u11 = self.make_tree(root / "u11", u11=True)
            output = root / "report"
            output.mkdir()
            sentinel = output / "do-not-touch"
            sentinel.write_text("keep", encoding="utf-8")
            result = run_compare(
                "--u3", str(u3), "--u11", str(u11), "--output", str(output)
            )
            self.assertEqual(result.returncode, 2)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")
            self.assertFalse((output / "comparison.json").exists())

    def test_output_inside_input_tree_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            u3 = self.make_tree(root / "u3")
            u11 = self.make_tree(root / "u11", u11=True)
            result = run_compare(
                "--u3", str(u3), "--u11", str(u11),
                "--output", str(u3 / "reports"),
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("árbol de entrada", result.stderr)
            self.assertFalse((u3 / "reports").exists())

    def test_symlink_tree_is_rejected_without_following_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            u3 = self.make_tree(root / "u3")
            u11 = self.make_tree(root / "u11", u11=True)
            link = root / "u11-link"
            link.symlink_to(u11, target_is_directory=True)
            result = run_compare(
                "--u3", str(u3), "--u11", str(link),
                "--output", str(root / "report"),
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("enlace simbólico", result.stderr)


if __name__ == "__main__":
    unittest.main()
