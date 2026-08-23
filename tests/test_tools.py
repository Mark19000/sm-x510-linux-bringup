import json
import pathlib
import struct
import subprocess
import sys
import tarfile
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def minimal_fdt() -> bytes:
    # Valid enough for the structural scanner: 40-byte FDT v17 header.
    return struct.pack(
        ">10I", 0xD00DFEED, 40, 40, 40, 40, 17, 16, 0, 0, 0
    )


class DeviceTreeToolsTest(unittest.TestCase):
    def test_fdt_scanner_extracts_embedded_blob(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            image = root / "vendor_boot.img"
            output = root / "out"
            image.write_bytes(b"prefix" + minimal_fdt() + b"suffix")
            subprocess.run(
                [sys.executable, str(ROOT / "tools/fdt_scan.py"), str(image), str(output)],
                check=True,
                capture_output=True,
                text=True,
            )
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertEqual(manifest["fdts"][0]["offset"], 6)
            self.assertEqual(manifest["fdts"][0]["size"], 40)

    def test_dtbo_extractor_preserves_entry_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            image = root / "dtbo.img"
            output = root / "out"
            fdt = minimal_fdt()
            header_size = 32
            entry_size = 32
            payload_offset = header_size + entry_size
            total_size = payload_offset + len(fdt)
            header = struct.pack(
                ">8I", 0xD7B7AB1E, total_size, header_size, entry_size,
                1, header_size, 4096, 0,
            )
            entry = struct.pack(
                ">8I", len(fdt), payload_offset, 0x510, 4, 1, 2, 3, 4
            )
            image.write_bytes(header + entry + fdt)
            subprocess.run(
                [sys.executable, str(ROOT / "tools/dtbo_extract.py"), str(image), str(output)],
                check=True,
                capture_output=True,
                text=True,
            )
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertEqual(manifest["entry_count"], 1)
            self.assertEqual(manifest["entries"][0]["id"], 0x510)
            self.assertEqual(manifest["entries"][0]["rev"], 4)
            extracted = output / manifest["entries"][0]["file"]
            self.assertEqual(extracted.read_bytes(), fdt)

    def test_dtbo_packer_round_trip(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            blob_a = root / "r00.dtbo"
            blob_b = root / "r04.dtbo"
            blob_a.write_bytes(minimal_fdt())
            blob_b.write_bytes(minimal_fdt() + b"revision-four")
            template = root / "manifest.json"
            template.write_text(json.dumps({
                "header_size": 32, "entry_size": 32, "page_size": 2048,
                "version": 0,
                "entries": [
                    {"id": 0, "rev": 0, "custom": [0, 0, 0, 0]},
                    {"id": 0, "rev": 0, "custom": [4, 32, 0, 0]},
                ],
            }))
            packed = root / "dtbo.img"
            extracted = root / "out"
            subprocess.run([
                sys.executable, str(ROOT / "tools/dtbo_pack.py"),
                "--template", str(template), "--output", str(packed),
                str(blob_a), str(blob_b),
            ], check=True, capture_output=True, text=True)
            subprocess.run([
                sys.executable, str(ROOT / "tools/dtbo_extract.py"),
                str(packed), str(extracted),
            ], check=True, capture_output=True, text=True)
            manifest = json.loads((extracted / "manifest.json").read_text())
            self.assertEqual(manifest["entries"][1]["custom"], [4, 32, 0, 0])
            self.assertEqual(
                (extracted / manifest["entries"][1]["file"]).read_bytes(),
                blob_b.read_bytes(),
            )


class SafeTarExtractTest(unittest.TestCase):
    def test_extracts_only_requested_regular_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            source = root / "payload"
            source.write_bytes(b"boot payload")
            archive = root / "ap.tar"
            with tarfile.open(archive, "w") as output:
                output.add(source, arcname="boot.img.lz4")
            destination = root / "out"
            subprocess.run(
                [sys.executable, str(ROOT / "tools/safe_tar_extract.py"),
                 str(archive), str(destination), "boot.img.lz4"],
                check=True, capture_output=True, text=True,
            )
            self.assertEqual((destination / "boot.img.lz4").read_bytes(), b"boot payload")

    def test_rejects_requested_symlink_without_publishing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            archive = root / "ap.tar"
            with tarfile.open(archive, "w") as output:
                info = tarfile.TarInfo("boot.img.lz4")
                info.type = tarfile.SYMTYPE
                info.linkname = "/etc/passwd"
                output.addfile(info)
            destination = root / "out"
            result = subprocess.run(
                [sys.executable, str(ROOT / "tools/safe_tar_extract.py"),
                 str(archive), str(destination), "boot.img.lz4"],
                capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((destination / "boot.img.lz4").exists())


class BootImageInfoTest(unittest.TestCase):
    def test_boot_v4_offsets_compression_and_avb_footer(self):
        with tempfile.TemporaryDirectory() as temporary:
            image = pathlib.Path(temporary) / "init_boot.img"
            header = bytearray(4096)
            header[:8] = b"ANDROID!"
            struct.pack_into("<IIII", header, 8, 0, 16, 0, 1584)
            struct.pack_into("<I", header, 40, 4)
            payload = b"\x02\x21\x4c\x18" + bytes(12)
            partition = bytearray(16384)
            partition[:4096] = header
            partition[4096:4112] = payload
            footer = bytearray(64)
            footer[:4] = b"AVBf"
            struct.pack_into(">IIQQQ", footer, 4, 1, 0, 4112, 8192, 2112)
            partition[-64:] = footer
            image.write_bytes(partition)
            result = subprocess.run(
                [sys.executable, str(ROOT / "tools/bootimg_info.py"),
                 "--json", str(image)],
                check=True, capture_output=True, text=True,
            )
            report = json.loads(result.stdout)[0]
            self.assertEqual(report["kind"], "boot")
            self.assertEqual(report["ramdisk_offset"], 4096)
            self.assertEqual(report["ramdisk_compression"], "lz4-legacy")
            self.assertEqual(report["avb_footer"]["original_image_size"], 4112)


if __name__ == "__main__":
    unittest.main()
