# Recovery Readiness v2 — SM-X510 EZE4

Date: 2026-09-05. Verdict: **RECOVERY_NOT_VALIDATED**.

## Mechanical Matrix

| Control | Status | Evidence |
|---|---|---|
| Download Mode entry | YES | Physically observed: Warning Screen (`IMG_2113.HEIC`) and normal Odin Mode (`IMG_2114.HEIC`). Confirms `RP SWREV B:12`, `HW REV 4`, `BUILD EZE4`, `KG Completed (00)`. |
| USB enumeration | YES | Samsung `04e8:685d`, 480 Mbps on macOS. |
| Host tool installed | NO | No Heimdall/Odin/Odin4/Thor found. |
| Odin/Loke handshake | NO | Never executed. |
| PIT read | NO | Never executed. |
| Partition table understood | PARTIAL | AVB metadata and six images; no PIT. |
| Full EZE4 firmware present | NO | Historical ZIP no longer present at its path. |
| Stock hashes | PARTIAL | Historical ZIP hash and hashes of six extracted images. |
| AP/BL/CP/CSC/HOME_CSC present | NO | Not found; on Wi-Fi model exact CP content must be derived from actual package. |
| Write command available/validated | NO | No pinned client. |
| Full restore recipe | PARTIAL | Conceptual; package/PIT not reconciled. |
| Physical restore tested | NO | Prohibited/not executed. |

## Environment and Firmware

- Host: Apple Silicon `arm64`, macOS 27.0; libusb present.
- Lima `gts9fe-build`: **RUNNING** when queried outside sandbox. Contains no Samsung client and USB passthrough unproven.
- Historical firmware: `/Users/markpi/Downloads/SAMFW.COM_SM-X510_EUX_X510XXUCEZE4_fac.zip`, recorded size `10,717,872,605` bytes, SHA-256 `45a450875ce753e74d8183aa085837ada91cabe2832d9725a1567aa29b01d375`; vendor SamFW, not direct Samsung provenance; file currently absent.
- Preserved: boot/init_boot/vendor_boot/dtbo/vbmeta/recovery with hashes in `artifacts/stock/SHA256SUMS`.

## Tooling

Heimdall implements the general protocol, but its classic upstream is dated and does not validate this SM-X510/U12 or Apple Silicon. macOS forks and Odin4/Thor clients exist, but likewise do not constitute validation on this unit. Native Windows with known Odin or native Linux with a modern client are more realistic paths than USB inside Lima; none has yet been pinned.

First future session, strictly non-destructive: identify/hash tool, `detect`, and only after verifying help text for that version, read `print-pit --no-reboot`. A successful PIT read proves dialogue/control, not full restoration or large transfers.

## Exit Criteria

Exact, hashed full firmware; host/client pinned; repeatable handshake and PIT read without writing; PIT map reconciled with package; exact recipe for all partitions that could be touched. Until then, Download Mode constitutes access, not recovery.

Tooling sources: <https://github.com/Benjamin-Dobell/Heimdall>, <https://github.com/Benjamin-Dobell/Heimdall/pull/459>, <https://github.com/Samsung-Loki/Thor>, <https://github.com/Llucs/odin4>.
