"""Host-only tests for the future Android 16/U11 OSRC staging flow."""

from __future__ import annotations

import json
import hashlib
import os
import pathlib
import stat
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/safe_release_extract.py"
SCRIPT = ROOT / "scripts/build-osrc-u11-in-lima.sh"
GUEST_BUILD = ROOT / "scripts/build-u11-kernel-guest.sh"
PATCH_MANIFEST = ROOT / "configs/u11-patches.sha256"


def run_tool(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


class SafeReleaseArchiveTests(unittest.TestCase):
    def test_tar_allows_relative_internal_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            archive = root / "kernel.tar.gz"
            with tarfile.open(archive, "w:gz") as output:
                directory = tarfile.TarInfo("include")
                directory.type = tarfile.DIRTYPE
                output.addfile(directory)
                header = tarfile.TarInfo("./include/generated.h")
                payload = b"header\n"
                header.size = len(payload)
                output.addfile(header, __import__("io").BytesIO(payload))
                link = tarfile.TarInfo("./scripts/dtc/include-prefixes")
                link.type = tarfile.SYMTYPE
                link.linkname = "../../include"
                output.addfile(link)
            destination = root / "out"
            result = run_tool("extract-tar", str(archive), str(destination))
            self.assertEqual(result.returncode, 0, result.stderr)
            link = destination / "scripts/dtc/include-prefixes"
            self.assertTrue(link.is_symlink())
            self.assertEqual(os.readlink(link), "../../include")
            self.assertEqual((link / "generated.h").read_text(), "header\n")

    def test_tar_canonicalizes_only_leading_dot_slash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            archive = root / "dot.tar"
            with tarfile.open(archive, "w") as output:
                member = tarfile.TarInfo("./Makefile")
                payload = b"all:\n"
                member.size = len(payload)
                output.addfile(member, __import__("io").BytesIO(payload))
            destination = root / "out"
            result = run_tool("extract-tar", str(archive), str(destination))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((destination / "Makefile").read_bytes(), b"all:\n")

            nested = root / "nested.tar"
            with tarfile.open(nested, "w") as output:
                member = tarfile.TarInfo("./a/./b")
                member.size = 1
                output.addfile(member, __import__("io").BytesIO(b"x"))
            rejected = run_tool("extract-tar", str(nested), str(root / "nested-out"))
            self.assertNotEqual(rejected.returncode, 0)
            self.assertFalse((root / "nested-out").exists())

    def test_tar_ignores_explicit_archive_root_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            archive = root / "root-marker.tar"
            with tarfile.open(archive, "w") as output:
                marker = tarfile.TarInfo("./")
                marker.type = tarfile.DIRTYPE
                output.addfile(marker)
                member = tarfile.TarInfo("./Makefile")
                member.size = 1
                output.addfile(member, __import__("io").BytesIO(b"x"))
            destination = root / "out"
            result = run_tool("extract-tar", str(archive), str(destination))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((destination / "Makefile").read_text(), "x")

    def test_unpack_tree_does_not_expand_archives_found_inside_tar_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            bad = __import__("io").BytesIO()
            with tarfile.open(fileobj=bad, mode="w") as output:
                member = tarfile.TarInfo("../escape")
                member.size = 1
                output.addfile(member, __import__("io").BytesIO(b"x"))
            outer = root / "Kernel.tar"
            with tarfile.open(outer, "w") as output:
                payload = bad.getvalue()
                member = tarfile.TarInfo("nested-bad.tar")
                member.size = len(payload)
                output.addfile(member, __import__("io").BytesIO(payload))
            result = run_tool("unpack-tree", str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / "Kernel.tar.contents").is_dir())
            self.assertFalse((root / "Kernel.tar.contents/nested-bad.tar.contents").exists())

    def test_tar_rejects_escape_link_and_preserves_outside(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            archive = root / "bad.tar"
            with tarfile.open(archive, "w") as output:
                link = tarfile.TarInfo("scripts/bad")
                link.type = tarfile.SYMTYPE
                link.linkname = "../../../../etc"
                output.addfile(link)
            destination = root / "out"
            result = run_tool("extract-tar", str(archive), str(destination))
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((root / "etc").exists())
            self.assertIn("enlace", result.stderr)

    def test_zip_rejects_traversal_and_symlink_payload_is_checked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            archive = root / "bad.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("../outside", b"do not publish")
            destination = root / "out"
            result = run_tool("extract-zip", str(archive), str(destination))
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((root / "outside").exists())

    def test_part_archive_is_rejected_without_opening(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            part = pathlib.Path(temporary) / "release.zip.part"
            part.write_bytes(b"not an archive")
            part.chmod(stat.S_IWUSR)
            result = run_tool("extract-zip", str(part), str(pathlib.Path(temporary) / "out"))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(".part", result.stderr)

    def test_scan_records_kernel_build_config_and_archive_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            kernel = root / "base" / "Kernel"
            (kernel / "arch/arm64/configs").mkdir(parents=True)
            (kernel / "include/linux").mkdir(parents=True)
            (kernel / "drivers").mkdir()
            (kernel / "kernel").mkdir()
            (kernel / "Makefile").write_text("VERSION = 5\n")
            (kernel / "Kconfig").write_text('mainmenu "Linux"\n')
            (kernel / "build_kernel.sh").write_text("#!/bin/sh\n")
            (kernel / "arch/arm64/configs/s5e8835-gts9fewifixx_defconfig").write_text("CONFIG_ARM64=y\n")
            false_root = kernel / "tools/perf"
            (false_root / "arch/arm64").mkdir(parents=True)
            (false_root / "Makefile").write_text("all:\n")
            (false_root / "Kconfig").write_text("menu test\n")
            (root / "Platform.tar.gz").write_bytes(b"placeholder")
            output = root / "layout.json"
            result = run_tool("scan", str(root), "--output", str(output))
            self.assertEqual(result.returncode, 0, result.stderr)
            layout = json.loads(output.read_text())
            self.assertEqual(
                [item["path"] for item in layout["kernel_roots"]],
                ["base/Kernel"],
            )
            self.assertIn("base/Kernel/build_kernel.sh", layout["build_scripts"])
            self.assertIn(
                "base/Kernel/arch/arm64/configs/s5e8835-gts9fewifixx_defconfig",
                {item["path"] for item in layout["config_files"]},
            )
            self.assertEqual(layout["archives"][0]["path"], "Platform.tar.gz")


class U11WrapperInputTests(unittest.TestCase):
    def test_fixed_build_profile_replaces_arbitrary_shell_command(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn('bash -x -lc "$build_command"', text)
        self.assertIn("build-u11-kernel-guest.sh", text)
        self.assertIn("U11_BUILD_COMMAND se ha eliminado", text)
        guest = GUEST_BUILD.read_text(encoding="utf-8")
        self.assertIn("flash_authorized=no", guest)
        self.assertIn("avb_signature_created=no", guest)
        self.assertIn("KBUILD_BUILD_TIMESTAMP='Thu Jan 1 00:00:00 UTC 1970'", guest)
        self.assertIn("[ \"$version\" = 5.15.180 ]", guest)
        self.assertIn("-fdebug-prefix-map=$RUN_ROOT=/build/u11", guest)
        self.assertIn("-ffile-prefix-map=$RUN_ROOT=/build/u11", guest)
        self.assertIn('KCPPFLAGS="$prefix_flags"', guest)
        self.assertIn('grep -a -F -q "$RUN_ROOT" "$OUT/arch/arm64/boot/Image"', guest)
        self.assertIn("module-path-scan.list0", guest)
        self.assertIn("while IFS= read -r -d '' module", guest)
        self.assertIn('[ "$grep_status" -eq 1 ]', guest)
        self.assertNotIn("-exec grep -a -F -l", guest)
        self.assertIn('kernel_out="$build_kernel_root/out-u11"', text)

    def test_patch_manifest_matches_the_exact_nine_patch_files(self) -> None:
        entries = []
        for raw in PATCH_MANIFEST.read_text().splitlines():
            digest, name = raw.split("  ", 1)
            path = ROOT / "patches/downstream/wifi" / name
            self.assertTrue(path.is_file())
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
            entries.append(name)
        self.assertEqual(len(entries), 10)

    def test_wrapper_accepts_samsung_readme_kerne_naming(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("-iname 'README*'", text)
        self.assertNotIn("-iname 'README.*'", text)

    def test_wrapper_copies_guest_evidence_without_host_path_probe(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn('[ -f "$guest_run/$evidence" ]', text)
        self.assertIn('"$VM:$guest_run/$evidence"', text)

    def test_composite_handles_read_only_base_and_verifies_overlay(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('find "$composite_root" -type d -exec chmod u+w {} +', text)
        self.assertIn('chmod --reference="$base_kernel_root/$relative"', text)
        self.assertIn('build_kernel_root="$run/build-source/Kernel"', text)
        self.assertIn('chmod -R u+w "$build_kernel_root"', text)
        self.assertIn('cp -a --remove-destination "$overlay_root/."', text)
        self.assertIn('cmp -s "$overlay_file" "$composite_file"', text)

    def test_wrapper_rejects_part_before_limactl(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            part = root / "SM-X510.zip.part"
            part.write_bytes(b"partial")
            fake_bin = root / "bin"
            fake_bin.mkdir()
            calls = root / "calls"
            fake = fake_bin / "limactl"
            fake.write_text(f"#!/bin/sh\necho called >> {calls}\nexit 99\n")
            fake.chmod(0o755)
            env = os.environ.copy()
            env.update({"PATH": f"{fake_bin}:{env['PATH']}", "OSRC_RELEASE": str(part)})
            result = subprocess.run(
                ["bash", str(SCRIPT)],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(".part", result.stderr)
            self.assertFalse(calls.exists(), "limactl must not receive a partial release")

    def test_wrapper_rejects_u3_checkout_as_release(self) -> None:
        env = os.environ.copy()
        env["OSRC_RELEASE"] = str(ROOT / "sources/wifi-kernel")
        result = subprocess.run(
            ["bash", str(SCRIPT)],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("wifi-kernel", result.stderr)


if __name__ == "__main__":
    unittest.main()
