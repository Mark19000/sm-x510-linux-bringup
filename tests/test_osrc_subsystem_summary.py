import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "osrc_subsystem_summary", ROOT / "tools" / "osrc_subsystem_summary.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class SubsystemSummaryTests(unittest.TestCase):
    def test_deduplicates_overlapping_categories(self) -> None:
        changed = {"path": "drivers/usb/dwc3/core.c"}
        data = {
            "categories": {
                "drivers": {"changed": [changed], "u3_only": [], "u11_only": []},
                "build_scripts": {"changed": [changed], "u3_only": [], "u11_only": []},
            }
        }
        summary = MODULE.build_summary(data)
        usb = summary["subsystems"]["usb_dwc3_typec"]
        self.assertEqual(usb["counts"]["changed"], 1)

    def test_classifies_x510_dts_and_scsc(self) -> None:
        data = {
            "categories": {
                "dts": {
                    "changed": [{"path": "arch/arm64/boot/dts/samsung/gts9fewifi/a.dts"}],
                    "u3_only": [],
                    "u11_only": [],
                },
                "drivers": {
                    "changed": [],
                    "u3_only": [],
                    "u11_only": ["drivers/net/wireless/scsc/new.c"],
                },
            }
        }
        summary = MODULE.build_summary(data)["subsystems"]
        self.assertEqual(summary["device_tree_s5e8835_x510"]["counts"]["changed"], 1)
        self.assertEqual(summary["wifi_bt_scsc"]["counts"]["u11_only"], 1)


if __name__ == "__main__":
    unittest.main()
