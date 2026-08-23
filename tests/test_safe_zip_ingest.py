"""Host-only adversarial tests for ``tools/safe_zip_ingest.py``.

The fixtures are tiny ZIPs created in temporary directories.  These tests do
not discover, open, or extract a downloaded firmware/source archive.
"""

from __future__ import annotations

import hashlib
import io
import json
import pathlib
import stat
import subprocess
import sys
import tempfile
import unittest
import warnings
import zipfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "safe_zip_ingest.py"


def run_tool(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )


def stored_zip(path: pathlib.Path, members: list[tuple[str, bytes]]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, payload in members:
            archive.writestr(name, payload)


class SafeZipIngestTests(unittest.TestCase):
    def test_nested_zip_is_processed_as_explicit_separate_transactions(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            inner_buffer = io.BytesIO()
            with zipfile.ZipFile(inner_buffer, "w", compression=zipfile.ZIP_STORED) as inner:
                inner.writestr("source.txt", b"nested")
            outer = root / "wrapper.zip"
            stored_zip(outer, [("base.zip", inner_buffer.getvalue())])

            wrapper_out = root / "wrapper-out"
            result = run_tool("extract", str(outer), str(wrapper_out))
            self.assertEqual(result.returncode, 0, result.stderr)
            inner_archive = wrapper_out / "base.zip"
            inner_out = root / "base-out"
            result = run_tool("extract", str(inner_archive), str(inner_out))

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((inner_out / "source.txt").read_bytes(), b"nested")

    def test_inspect_validates_complete_archive_and_reports_hashes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            archive = root / "source.zip"
            stored_zip(archive, [("src/README", b"hello"), ("LICENSE", b"ok")])

            result = run_tool("inspect", str(archive))

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["totals"]["members"], 2)
            entries = {entry["name"]: entry for entry in report["members"]}
            self.assertEqual(
                entries["src/README"]["sha256"],
                hashlib.sha256(b"hello").hexdigest(),
            )
            self.assertEqual(entries["LICENSE"]["size"], 2)
            self.assertEqual(report["archive"]["size"], archive.stat().st_size)

    def test_part_download_is_rejected_before_zip_read(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            partial = root / "source.zip.part"
            partial.write_bytes(b"not a zip")

            result = run_tool("inspect", str(partial))

            self.assertNotEqual(result.returncode, 0)
            self.assertIn(".part", result.stderr)
            self.assertNotIn("directorio central", result.stderr)

    def test_archive_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            target = root / "real.zip"
            stored_zip(target, [("payload", b"ok")])
            link = root / "source.zip"
            link.symlink_to(target)

            result = run_tool("inspect", str(link))

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("enlace simbólico", result.stderr)

    def test_truncated_or_crc_corrupt_archive_never_creates_destination(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            valid = root / "valid.zip"
            stored_zip(valid, [("payload", b"payload")])
            truncated = root / "truncated.zip"
            truncated.write_bytes(valid.read_bytes()[:-3])
            truncated_destination = root / "truncated-out"

            result = run_tool("extract", str(truncated), str(truncated_destination))

            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(truncated_destination.exists())

            corrupt = root / "corrupt.zip"
            data = bytearray(valid.read_bytes())
            offset = data.find(b"payload")
            self.assertGreaterEqual(offset, 0)
            data[offset] ^= 0x01
            corrupt.write_bytes(data)
            corrupt_destination = root / "corrupt-out"

            result = run_tool("inspect", str(corrupt))

            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(corrupt_destination.exists())

    def test_rejects_zip_slip_and_nonregular_members(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            traversal = root / "traversal.zip"
            stored_zip(traversal, [("../outside", b"no")])
            result = run_tool("inspect", str(traversal))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("ruta", result.stderr)

            directory = root / "directory.zip"
            with zipfile.ZipFile(directory, "w") as archive:
                archive.writestr("directory/", b"")
            result = run_tool("inspect", str(directory))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("no regular", result.stderr)

            symlink = root / "symlink.zip"
            with zipfile.ZipFile(symlink, "w") as archive:
                info = zipfile.ZipInfo("link")
                info.create_system = 3
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                archive.writestr(info, "/etc/passwd")
            result = run_tool("inspect", str(symlink))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("no regular", result.stderr)

    def test_rejects_duplicate_aliases_and_reasonable_bomb_ratio(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            duplicate = root / "duplicate.zip"
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with zipfile.ZipFile(duplicate, "w") as archive:
                    archive.writestr("same", b"one")
                    archive.writestr("same", b"two")
            result = run_tool("inspect", str(duplicate))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("duplic", result.stderr)

            alias = root / "alias.zip"
            stored_zip(alias, [("Readme", b"one"), ("README", b"two")])
            result = run_tool("inspect", str(alias))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("duplic", result.stderr)

            collision = root / "collision.zip"
            stored_zip(collision, [("tree/leaf", b"one"), ("tree", b"two")])
            result = run_tool("inspect", str(collision))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("colision", result.stderr)

            bomb = root / "bomb.zip"
            with zipfile.ZipFile(bomb, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("repeated", b"A" * (2 * 1024 * 1024))
            result = run_tool("inspect", str(bomb))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("ratio", result.stderr)

    def test_extract_is_transactional_and_never_overwrites_existing_destination(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            archive = root / "source.zip"
            stored_zip(archive, [("src/file.txt", b"content")])
            destination = root / "out"

            result = run_tool("extract", str(archive), str(destination))

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual((destination / "src/file.txt").read_bytes(), b"content")
            manifest = json.loads(
                (destination / ".safe-zip-manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["archive"]["sha256"], report["archive"]["sha256"])
            self.assertEqual(manifest["members"][0]["sha256"], hashlib.sha256(b"content").hexdigest())

            sentinel = destination / "src/file.txt"
            original = sentinel.read_bytes()
            result = run_tool("extract", str(archive), str(destination))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("no sobrescribir", result.stderr)
            self.assertEqual(sentinel.read_bytes(), original)

    def test_limits_can_be_lowered_explicitly(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            archive = root / "source.zip"
            stored_zip(archive, [("payload", b"1234")])

            result = run_tool("inspect", "--max-total-size", "3", str(archive))

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("total", result.stderr)


if __name__ == "__main__":
    unittest.main()
