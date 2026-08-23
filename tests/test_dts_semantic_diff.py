import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import dts_semantic_diff as semantic  # noqa: E402


def compare_text(left: str, right: str) -> semantic.Comparison:
    return semantic.compare_trees(
        semantic.parse_dts(left, source="left.dts"),
        semantic.parse_dts(right, source="right.dts"),
    )


class SemanticDtsDiffTest(unittest.TestCase):
    def test_phandle_renumbering_resolves_to_the_same_path(self):
        left = r"""
        /dts-v1/;
        / {
            producer: producer {
                phandle = <0x10>;
                compatible = "vendor,producer";
            };
            consumer {
                link = <0x10>;
            };
        };
        """
        right = r"""
        /dts-v1/;
        / {
            producer: producer {
                phandle = <0x44>;
                compatible = "vendor,producer";
            };
            consumer {
                link = <0x44>;
            };
        };
        """
        comparison = compare_text(left, right)
        self.assertTrue(comparison.equivalent)
        self.assertEqual(comparison.status, "EQUIVALENT")
        self.assertEqual(comparison.differences, [])
        self.assertEqual(
            comparison.phandle_renumbered,
            [("/producer", 0x10, 0x44)],
        )

    def test_unknown_numeric_property_is_not_normalised_as_a_reference(self):
        left = r"""
        / {
            producer: producer { phandle = <0x10>; };
            consumer { calibration = <0x10>; };
        };
        """
        right = r"""
        / {
            producer: producer { phandle = <0x44>; };
            consumer { calibration = <0x44>; };
        };
        """
        comparison = compare_text(left, right)
        self.assertFalse(comparison.equivalent)
        self.assertEqual(comparison.status, "DIFFERENT")
        self.assertEqual(len(comparison.differences), 1)
        self.assertEqual(comparison.differences[0].property, "calibration")

    def test_explicit_peer_label_can_prove_a_numeric_reference(self):
        left = r"""
        / {
            producer: producer { phandle = <0x10>; };
            consumer { target = <0x10>; };
        };
        """
        right = r"""
        / {
            producer: producer { phandle = <0x44>; };
            consumer { target = <&producer>; };
        };
        """
        comparison = compare_text(left, right)
        self.assertTrue(comparison.equivalent)
        self.assertEqual(comparison.phandle_renumbered[0][0], "/producer")

    def test_unresolved_external_reference_is_not_equivalence(self):
        comparison = compare_text(
            "/ { target = <0xffffffff>; };",
            "/ { target = <&external_controller>; };",
        )
        self.assertFalse(comparison.equivalent)
        self.assertEqual(comparison.status, "INCONCLUSIVE")
        self.assertEqual(comparison.differences, [])
        self.assertTrue(comparison.unresolved)

    def test_real_u3_eze4_overlay_reports_path_changes(self):
        u3 = ROOT / "sources/wifi-kernel/arch/arm64/boot/dts/samsung/gts9fewifi/gts9fewifi_eur_open_w00_r04.dts"
        eze4 = ROOT / "artifacts/stock/dt/recovery/fdt-02-offset-044fe3b8.dts"
        comparison = semantic.compare_paths(u3, eze4)
        changed = {
            item.property
            for item in comparison.differences
            if item.kind == "property-changed"
        }
        self.assertEqual(comparison.status, "DIFFERENT (INCOMPLETE)")
        self.assertIn("battery_full_capacity", changed)
        self.assertIn("pktproc_ul_hiprio_ack_only", changed)
        self.assertIn("model_name", changed)
        self.assertTrue(
            any(item.kind == "property-added" and item.property == "max" for item in comparison.differences)
        )
        self.assertIn(
            "/fragment@model/__overlay__/sec-bootstat/thermal-zones/zone_big",
            {item.path for item in comparison.differences if item.kind == "node-added"},
        )
        self.assertGreater(len(comparison.unresolved), 0)

    def test_real_u3_eze4_base_separates_renumbering_from_changes(self):
        u3 = ROOT / "sources/wifi-kernel/arch/arm64/boot/dts/exynos/s5e8835.dts"
        eze4 = ROOT / "artifacts/stock/dt/vendor_boot/fdt-00-offset-0113f040.dts"
        comparison = semantic.compare_paths(u3, eze4)
        self.assertGreater(len(comparison.phandle_renumbered), 500)
        self.assertEqual(comparison.status, "DIFFERENT (INCOMPLETE)")
        self.assertIn(
            ("node-added", "/reserved-memory/wdtmsg"),
            {(item.kind, item.path) for item in comparison.differences},
        )
        self.assertIn(
            ("property-added", "/mali@10300000", "clock-names"),
            {(item.kind, item.path, item.property) for item in comparison.differences},
        )

    def test_cli_json_is_deterministic_and_returns_difference(self):
        left = "/ { a { value = <1>; }; };\n"
        right = "/ { a { value = <2>; }; };\n"
        with tempfile.TemporaryDirectory() as temporary:
            directory = pathlib.Path(temporary)
            left_path = directory / "left.dts"
            right_path = directory / "right.dts"
            left_path.write_text(left, encoding="utf-8")
            right_path.write_text(right, encoding="utf-8")
            command = [
                sys.executable,
                str(ROOT / "tools/dts_semantic_diff.py"),
                "--format",
                "json",
                str(left_path),
                str(right_path),
            ]
            first = subprocess.run(command, capture_output=True, text=True)
            second = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 1)
            self.assertEqual(first.stdout, second.stdout)
            self.assertIn('"kind": "property-changed"', first.stdout)


if __name__ == "__main__":
    unittest.main()
