"""Adversarial, host-only safety checks for the X510 build helpers.

These tests deliberately use temporary files and small command shims.  They
must never need a firmware download, a VM, an Android device, or a real
flashing tool.  A few tests are expected to fail against an unsafe revision of
the shell helpers; that is useful during the audit because the failure is the
reproduction to fix in production code.
"""

from __future__ import annotations

import json
import os
import pathlib
import stat
import struct
import subprocess
import sys
import tempfile
import textwrap
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
TOOLS = ROOT / "tools"


def run_script(
    name: str,
    *args: str,
    env: dict[str, str] | None = None,
    timeout: float = 20,
) -> subprocess.CompletedProcess[str]:
    """Run a project helper in a child process with a deterministic timeout."""

    child_env = os.environ.copy()
    if env:
        child_env.update(env)
    return subprocess.run(
        ["bash", str(SCRIPTS / name), *args],
        cwd=ROOT,
        env=child_env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def write_executable(path: pathlib.Path, body: str) -> pathlib.Path:
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def minimal_boot_image() -> bytes:
    """Return a small structurally parseable Android boot v4 image."""

    header = bytearray(4096)
    header[:8] = b"ANDROID!"
    # kernel_size, ramdisk_size, os_version, header_size
    struct.pack_into("<IIII", header, 8, 0, 0, 0, 4096)
    struct.pack_into("<I", header, 40, 4)
    return bytes(header)


def minimal_fdt_blob() -> bytes:
    """Return the smallest structurally valid FDT used by DTBO fixtures."""

    return struct.pack(
        ">10I", 0xD00DFEED, 40, 40, 40, 40, 17, 16, 0, 0, 0
    )


def make_fake_magiskboot(path: pathlib.Path, output_name: str) -> pathlib.Path:
    """Make a harmless unpack/repack shim for alias tests.

    It emits a valid boot-shaped output but changes one header byte.  If a
    production script accepts STOCK == OUTPUT, this makes the destructive
    overwrite observable without invoking a real image tool.
    """

    unpack_files = (
        "printf payload > ramdisk.cpio"
        if "init" in output_name
        else "printf payload > kernel"
    )
    return write_executable(
        path,
        f"""
        #!/bin/sh
        set -eu
        case "$1" in
          unpack)
            {unpack_files}
            ;;
          repack)
            cp stock.img {output_name}
            printf X | dd of={output_name} bs=1 seek=100 conv=notrunc 2>/dev/null
            ;;
          *) exit 2 ;;
        esac
        """,
    )


class ShellGuardTests(unittest.TestCase):
    def test_output_guard_rejects_device_nodes(self):
        result = subprocess.run(
            [
                "bash",
                "-c",
                'source "$1"; guard_output_file /dev/null test-output',
                "guard-test",
                str(SCRIPTS / "safety-paths.sh"),
            ],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ruta del sistema", result.stderr)

    def test_output_guard_rejects_system_directories(self):
        result = subprocess.run(
            [
                "bash",
                "-c",
                'source "$1"; guard_output_directory /etc test-output',
                "guard-test",
                str(SCRIPTS / "safety-paths.sh"),
            ],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ruta del sistema", result.stderr)

    def test_project_shell_helpers_are_syntax_valid(self):
        for script in sorted(SCRIPTS.glob("*.sh")):
            with self.subTest(script=script.name):
                result = subprocess.run(
                    ["bash", "-n", str(script)],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_invalid_variant_is_rejected_before_any_build_work(self):
        result = run_script("build-downstream.sh", env={"DEVICE_VARIANT": "tablet"})
        self.assertEqual(result.returncode, 2)
        self.assertIn("wifi o 5g", result.stderr)

    def test_target_variant_mismatch_is_blocked(self):
        result = run_script("build-downstream.sh", env={"DEVICE_VARIANT": "5g"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("BLOQUEADO", result.stderr)
        self.assertIn("SM-X510", result.stderr)

    def test_initramfs_rejects_invalid_variant_without_touching_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = pathlib.Path(temporary) / "out"
            result = run_script(
                "build-initramfs.sh",
                env={
                    "DEVICE_VARIANT": "tablet",
                    "INITRAMFS_OUT": str(output),
                },
            )
            self.assertEqual(result.returncode, 2)
            self.assertFalse(output.exists())

    def test_initramfs_rejects_unknown_module_profile(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = pathlib.Path(temporary) / "out"
            result = run_script(
                "build-initramfs.sh",
                env={
                    "BUSYBOX": str(ROOT / "artifacts/busybox/busybox"),
                    "INITRAMFS_OUT": str(output),
                    "MODULES_MODE": "unexpected",
                },
            )
            self.assertEqual(result.returncode, 2)
            self.assertFalse(output.exists())

    def test_dtbo_5g_mapping_is_explicitly_blocked(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = run_script(
                "build-dtbo.sh",
                env={
                    "DEVICE_VARIANT": "5g",
                    "DIST_DIR": str(pathlib.Path(temporary) / "dist"),
                },
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("aún no se ha validado", result.stderr)

    def test_repack_helpers_require_a_stock_argument(self):
        for script in ("repack-boot.sh", "repack-init-boot.sh"):
            with self.subTest(script=script):
                result = run_script(script)
                self.assertEqual(result.returncode, 2)
                self.assertIn("Uso:", result.stderr)

    def test_verify_avb_requires_a_present_tool(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            result = run_script(
                "verify-avb-candidates.sh",
                env={
                    "AVBTOOL": str(root / "does-not-exist.py"),
                    "STOCK_DIR": str(root / "stock"),
                    "CANDIDATE_DIR": str(root / "candidate"),
                },
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("Falta avbtool", result.stderr)

    def test_scripts_do_not_offer_a_flashing_command(self):
        forbidden = ("fastboot", "heimdall", "adb flash", "dd of=/dev/")
        for path in sorted(SCRIPTS.glob("*.sh")):
            source = path.read_text(encoding="utf-8").lower()
            with self.subTest(script=path.name):
                for token in forbidden:
                    self.assertNotIn(token, source)


class RepackAliasTests(unittest.TestCase):
    def _run_alias_case(self, script: str, output_name: str) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            stock = root / "stock.img"
            stock.write_bytes(minimal_boot_image())
            original = stock.read_bytes()
            payload = root / ("Image" if script == "repack-boot.sh" else "ramdisk.cpio")
            payload.write_bytes(b"payload")
            magiskboot = make_fake_magiskboot(root / "magiskboot", output_name)

            result = run_script(
                script,
                str(stock),
                str(payload),
                str(stock),
                env={
                    "DEVICE_VARIANT": "wifi",
                    "MAGISKBOOT": str(magiskboot),
                    "TMPDIR": temporary,
                },
            )

            self.assertNotEqual(
                result.returncode,
                0,
                f"accepted STOCK == OUTPUT:\nstdout={result.stdout}\nstderr={result.stderr}",
            )
            self.assertTrue(
                stock.exists(),
                "repack must reject an alias before clearing the output path",
            )
            self.assertEqual(
                stock.read_bytes(),
                original,
                "a rejected alias must not overwrite the stock input",
            )

    def test_boot_repack_rejects_stock_output_alias(self):
        self._run_alias_case("repack-boot.sh", "new-boot.img")

    def test_init_boot_repack_rejects_stock_output_alias(self):
        self._run_alias_case("repack-init-boot.sh", "new-init-boot.img")


class RepackPublishTests(unittest.TestCase):
    def _oversized_candidate_is_never_published(self, script: str) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            stock = root / "stock.img"
            stock.write_bytes(minimal_boot_image())
            is_init = script == "repack-init-boot.sh"
            payload = root / ("ramdisk.cpio" if is_init else "Image")
            payload.write_bytes(b"payload")
            unpack_file = "ramdisk.cpio" if is_init else "kernel"
            output_name = "new-init-boot.img" if is_init else "new-boot.img"
            magiskboot = write_executable(
                root / "magiskboot",
                f"""
                #!/bin/sh
                set -eu
                case "$1" in
                  unpack) printf payload > {unpack_file} ;;
                  repack)
                    cp stock.img {output_name}
                    printf X >> {output_name}
                    ;;
                  *) exit 2 ;;
                esac
                """,
            )
            output = root / "candidate.img"
            result = run_script(
                script,
                str(stock),
                str(payload),
                str(output),
                env={"MAGISKBOOT": str(magiskboot), "TMPDIR": temporary},
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("supera la partición stock", result.stderr)
            self.assertFalse(output.exists(), "an invalid candidate was published")

    def test_oversized_boot_is_not_published(self):
        self._oversized_candidate_is_never_published("repack-boot.sh")

    def test_oversized_init_boot_is_not_published(self):
        self._oversized_candidate_is_never_published("repack-init-boot.sh")


class DtboSafetyTests(unittest.TestCase):
    @staticmethod
    def _header(
        *,
        total_size: int,
        header_size: int = 32,
        entry_size: int = 32,
        entry_count: int = 1,
        entries_offset: int = 32,
        page_size: int = 2048,
    ) -> bytes:
        return struct.pack(
            ">8I",
            0xD7B7AB1E,
            total_size,
            header_size,
            entry_size,
            entry_count,
            entries_offset,
            page_size,
            0,
        )

    def _extract(self, image: bytes) -> subprocess.CompletedProcess[str]:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = pathlib.Path(temporary.name)
        source = root / "dtbo.img"
        source.write_bytes(image)
        return subprocess.run(
            [
                sys.executable,
                str(TOOLS / "dtbo_extract.py"),
                str(source),
                str(root / "out"),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

    def test_dtbo_extract_rejects_zero_length_payload(self):
        image = self._header(total_size=64) + struct.pack(">8I", 0, 64, 0, 0, 0, 0, 0, 0)
        result = self._extract(image)
        self.assertNotEqual(result.returncode, 0, result.stdout)

    def test_dtbo_extract_rejects_entry_table_overlapping_header(self):
        image = self._header(
            total_size=64,
            header_size=64,
            entries_offset=32,
        ) + struct.pack(">8I", 1, 64, 0, 0, 0, 0, 0, 0)
        image += b"x"
        result = self._extract(image)
        self.assertNotEqual(result.returncode, 0, result.stdout)

    def test_dtbo_extract_rejects_zero_page_size(self):
        image = self._header(total_size=68, page_size=0)
        image += struct.pack(">8I", 4, 64, 0, 0, 0, 0, 0, 0) + b"ABCD"
        result = self._extract(image)
        self.assertNotEqual(result.returncode, 0, result.stdout)

    def test_build_dtbo_does_not_overwrite_an_overlay_input(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            dist = root / "dist"
            overlay_dir = dist / "dtbs" / "samsung" / "gts9fewifi"
            overlay_dir.mkdir(parents=True)
            overlays = [
                overlay_dir / f"gts9fewifi_eur_open_w00_{revision}.dtbo"
                for revision in ("r00", "r01", "r04")
            ]
            for overlay in overlays:
                overlay.write_bytes(minimal_fdt_blob())
            original = [overlay.read_bytes() for overlay in overlays]
            template = root / "manifest.json"
            template.write_text(
                json.dumps(
                    {
                        "header_size": 32,
                        "entry_size": 32,
                        "page_size": 2048,
                        "version": 0,
                        "entries": [
                            {"id": 0, "rev": 0, "custom": [0, 0, 0, 0]}
                            for _ in overlays
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = run_script(
                "build-dtbo.sh",
                env={
                    "DEVICE_VARIANT": "wifi",
                    "DIST_DIR": str(dist),
                    "DTBO_TEMPLATE": str(template),
                    "DTBO_OUTPUT": str(overlays[0]),
                },
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(
                [overlay.read_bytes() for overlay in overlays],
                original,
                "DTBO output must be distinct from every input overlay",
            )

    def test_build_dtbo_does_not_overwrite_its_manifest_input(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            dist = root / "dist"
            overlay_dir = dist / "dtbs" / "samsung" / "gts9fewifi"
            overlay_dir.mkdir(parents=True)
            overlays = [
                overlay_dir / f"gts9fewifi_eur_open_w00_{revision}.dtbo"
                for revision in ("r00", "r01", "r04")
            ]
            for overlay in overlays:
                overlay.write_bytes(minimal_fdt_blob())
            template = root / "manifest.json"
            template.write_text(
                json.dumps(
                    {
                        "header_size": 32,
                        "entry_size": 32,
                        "page_size": 2048,
                        "entries": [{}, {}, {}],
                    }
                ),
                encoding="utf-8",
            )
            original = template.read_bytes()
            result = run_script(
                "build-dtbo.sh",
                env={
                    "DEVICE_VARIANT": "wifi",
                    "DIST_DIR": str(dist),
                    "DTBO_TEMPLATE": str(template),
                    "DTBO_OUTPUT": str(template),
                },
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(template.read_bytes(), original)

    def test_build_dtbo_roundtrip_uses_manifest_ids_and_revisions(self):
        """Non-zero stock metadata must not be mistaken for a failed round trip."""

        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            dist = root / "dist"
            overlay_dir = dist / "dtbs" / "samsung" / "gts9fewifi"
            overlay_dir.mkdir(parents=True)
            overlays = [
                overlay_dir / f"gts9fewifi_eur_open_w00_{revision}.dtbo"
                for revision in ("r00", "r01", "r04")
            ]
            for overlay in overlays:
                overlay.write_bytes(minimal_fdt_blob())
            entries = [
                {"id": 0x100 + index, "rev": 10 + index, "custom": [index, 0, 0, 0]}
                for index in range(3)
            ]
            template = root / "manifest.json"
            template.write_text(
                json.dumps(
                    {
                        "header_size": 32,
                        "entry_size": 32,
                        "page_size": 2048,
                        "version": 0,
                        "entries": entries,
                    }
                ),
                encoding="utf-8",
            )
            result = run_script(
                "build-dtbo.sh",
                env={
                    "DEVICE_VARIANT": "wifi",
                    "DIST_DIR": str(dist),
                    "DTBO_TEMPLATE": str(template),
                },
            )
            self.assertEqual(
                result.returncode,
                0,
                f"metadata-preserving DTBO round trip failed:\n{result.stderr}",
            )

    def test_failed_dtbo_build_invalidates_previous_outputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            dist = root / "dist"
            overlay_dir = dist / "dtbs" / "samsung" / "gts9fewifi"
            overlay_dir.mkdir(parents=True)
            overlays = [
                overlay_dir / f"gts9fewifi_eur_open_w00_{revision}.dtbo"
                for revision in ("r00", "r01", "r04")
            ]
            for overlay in overlays:
                overlay.write_bytes(minimal_fdt_blob())
            template = root / "manifest.json"
            template.write_text(
                json.dumps({
                    "header_size": 32,
                    "entry_size": 32,
                    "page_size": 2048,
                    "entries": [{}, {}, {}],
                }),
                encoding="utf-8",
            )
            env = {
                "DEVICE_VARIANT": "wifi",
                "DIST_DIR": str(dist),
                "DTBO_TEMPLATE": str(template),
            }
            first = run_script("build-dtbo.sh", env=env)
            self.assertEqual(first.returncode, 0, first.stderr)
            output = dist / "dtbo-unsigned.img"
            checksum = dist / "dtbo-unsigned.img.sha256"
            entries = dist / "dtbo-unsigned.entries"
            self.assertTrue(output.exists() and checksum.exists() and entries.exists())

            overlays[-1].unlink()
            second = run_script("build-dtbo.sh", env=env)
            self.assertNotEqual(second.returncode, 0)
            self.assertFalse(output.exists())
            self.assertFalse(checksum.exists())
            self.assertFalse(entries.exists())


class BootImageParserSafetyTests(unittest.TestCase):
    def _inspect(self, data: bytes) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary:
            image = pathlib.Path(temporary) / "image.img"
            image.write_bytes(data)
            return subprocess.run(
                [sys.executable, str(TOOLS / "bootimg_info.py"), "--json", str(image)],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )

    def test_boot_parser_rejects_header_smaller_than_fixed_header(self):
        image = bytearray(4096)
        image[:8] = b"ANDROID!"
        struct.pack_into("<IIII", image, 8, 0, 0, 0, 0)
        struct.pack_into("<I", image, 40, 4)
        result = self._inspect(bytes(image))
        self.assertNotEqual(result.returncode, 0, result.stdout)

    def test_boot_parser_rejects_avb_original_size_past_partition(self):
        image = bytearray(minimal_boot_image())
        image.extend(bytes(64))
        image[-64:-60] = b"AVBf"
        struct.pack_into(
            ">IIQQQ",
            image,
            len(image) - 60,
            1,
            0,
            len(image) + 1,
            4096,
            64,
        )
        result = self._inspect(bytes(image))
        self.assertNotEqual(result.returncode, 0, result.stdout)

    def test_vendor_boot_parser_rejects_header_smaller_than_format(self):
        image = bytearray(4096)
        image[:8] = b"VNDRBOOT"
        struct.pack_into("<II", image, 8, 4, 4096)
        struct.pack_into("<I", image, 24, 0)
        struct.pack_into("<II", image, 2096, 0, 0)
        struct.pack_into("<IIII", image, 2112, 0, 0, 0, 0)
        result = self._inspect(bytes(image))
        self.assertNotEqual(result.returncode, 0, result.stdout)


class InitramfsOutputTests(unittest.TestCase):
    def test_output_cannot_alias_the_source_rootfs(self):
        """A user-friendly OUT name must never delete the rootfs template."""

        with tempfile.TemporaryDirectory() as temporary:
            project = pathlib.Path(temporary) / "project"
            scripts = project / "scripts"
            source_rootfs = project / "initramfs" / "rootfs"
            fake_bin = project / "fake-bin"
            scripts.mkdir(parents=True)
            source_rootfs.mkdir(parents=True)
            fake_bin.mkdir()
            (scripts / "build-initramfs.sh").write_bytes(
                (SCRIPTS / "build-initramfs.sh").read_bytes()
            )
            (scripts / "safety-paths.sh").write_bytes(
                (SCRIPTS / "safety-paths.sh").read_bytes()
            )
            sentinel = source_rootfs / "init"
            sentinel.write_text("do not delete\n", encoding="utf-8")
            busybox = project / "busybox"
            busybox.write_bytes(b"fixture")
            busybox.chmod(busybox.stat().st_mode | stat.S_IXUSR)
            write_executable(
                fake_bin / "file",
                """
                #!/bin/sh
                echo "$1: ELF 64-bit LSB executable, ARM aarch64, statically linked"
                """,
            )
            result = subprocess.run(
                ["bash", str(scripts / "build-initramfs.sh")],
                cwd=project,
                env={
                    **os.environ,
                    "BUSYBOX": str(busybox),
                    "INITRAMFS_OUT": str(project / "initramfs"),
                    "MODULES_MODE": "none",
                    "PATH": os.pathsep.join([str(fake_bin), "/usr/bin", "/bin"]),
                },
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("árbol fuente", result.stderr)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "do not delete\n")

    def test_stale_lz4_is_not_included_when_lz4_is_unavailable(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            # Keep the build host-only and avoid depending on the host's
            # architecture or on Homebrew's optional lz4 executable.
            write_executable(
                fake_bin / "file",
                """
                #!/bin/sh
                echo "$1: ELF 64-bit LSB executable, ARM aarch64, statically linked"
                """,
            )
            write_executable(
                fake_bin / "touch",
                """
                #!/bin/sh
                # GNU touch's @EPOCH syntax is unavailable on macOS.  The
                # production helper is Linux-oriented, so this shim removes
                # only its date arguments while keeping all file operations in
                # the temporary fixture.
                if [ "$1" = "-h" ]; then shift; fi
                if [ "$1" = "-d" ]; then shift 2; fi
                exec /usr/bin/touch "$@"
                """,
            )
            write_executable(
                fake_bin / "cpio",
                """
                #!/bin/sh
                # BSD cpio on macOS lacks GNU cpio's reproducibility flags;
                # consume the generated name stream and emit a harmless
                # deterministic fixture instead.
                cat >/dev/null
                printf 'fake-newc-archive\\n'
                """,
            )
            busybox = root / "busybox"
            busybox.write_bytes(b"fake busybox")
            busybox.chmod(busybox.stat().st_mode | stat.S_IXUSR)
            output = root / "out"
            output.mkdir()
            stale = output / "gts9fe-initramfs.cpio.lz4"
            stale.write_bytes(b"stale artifact")

            path = os.pathsep.join(
                [str(fake_bin), "/usr/bin", "/bin", "/sbin"]
            )
            result = run_script(
                "build-initramfs.sh",
                env={
                    "BUSYBOX": str(busybox),
                    "INITRAMFS_OUT": str(output),
                    "MODULES_MODE": "none",
                    "PATH": path,
                },
            )
            self.assertEqual(
                result.returncode,
                0,
                f"initramfs fixture failed:\nstdout={result.stdout}\nstderr={result.stderr}",
            )
            sums = (output / "SHA256SUMS").read_text(encoding="utf-8")
            self.assertNotIn(stale.name, sums)
            self.assertFalse(stale.exists())


class AvbCandidateSafetyTests(unittest.TestCase):
    def test_oversized_candidate_is_rejected_before_avb_claim(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            stock_dir = root / "stock"
            candidate_dir = root / "candidate"
            stock_dir.mkdir()
            candidate_dir.mkdir()
            for partition in ("boot", "init_boot"):
                (stock_dir / f"{partition}.img").write_bytes(b"s")
                (candidate_dir / f"{partition}-UNSIGNED.img").write_bytes(b"candidate")

            avbtool = write_executable(
                root / "fake-avbtool.py",
                """
                #!/usr/bin/env python3
                import pathlib
                import sys

                args = sys.argv[1:]
                image = pathlib.Path(args[args.index("--image") + 1])
                if args[0] == "verify_image" and image.parent.name in {"boot", "init_boot"}:
                    print("does not match digest in descriptor")
                    print("Successfully verified footer and SHA256_RSA4096 vbmeta struct")
                    raise SystemExit(1)
                if args[0] == "verify_image":
                    print("stock verified")
                elif args[0] == "info_image":
                    print("info")
                """,
            )
            result = run_script(
                "verify-avb-candidates.sh",
                env={
                    "AVBTOOL": str(avbtool),
                    "STOCK_DIR": str(stock_dir),
                    "CANDIDATE_DIR": str(candidate_dir),
                    "TMPDIR": temporary,
                },
            )
            self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
