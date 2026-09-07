# Unlock evidence matrix — SM-X510/U12/EZE4

Date: 2026-09-05. Direct physical evidence:
- `/Users/markpi/Downloads/IMG_2113.HEIC`: Prior warning screen (Warning Screen).
- `/Users/markpi/Downloads/IMG_2114.HEIC`: Normal Odin Mode status screen (public transcript with unique identifiers redacted in [`docs/hardware/evidence/2026-09-05-odin-mode-stock-baseline.md`](file:///Users/markpi/tab-s9-fe-linux/docs/hardware/evidence/2026-09-05-odin-mode-stock-baseline.md)).

> [!NOTE]
> **Privacy**: Unique device identifiers (DID, Chip ID, Chip ID SJtag) are deliberately omitted and redacted in the public repository.

| Signal / Field | Observed Physical Value | What it proves | What it does not prove | Status |
|---|---|---|---|---|
| Model/CSC | SM-X510 / EUX (`EUX//`) | European identity and market channel | That EUX guarantees unlock | **CONFIRMED** |
| Lock/AVB (Android) | `flash.locked=1`, device locked, green | Current stock Android state | Policy after unlock | **CONFIRMED** |
| CURRENT BINARY | `Samsung Official` | Bootloader executes only official software | Behavior with custom binary | **CONFIRMED** |
| KG STATE | `Completed (00)` | Knox Guard completed; no leasing lock | Direct OEM permission | **CONFIRMED** |
| Secure Download | `Enabled` | Download requires official signature authentication | Impossibility of custom flashing after unlock | **CONFIRMED** |
| WARRANTY VOID | `0 (0x0000)` | Knox warranty fuse intact | Exact trigger moment | **CONFIRMED** |
| RP SWREV (Bootloader) | `B:12`, `K:12(...)`, `S:12` | Bootloader rollback level 12 confirmed directly in UI | Semantics of undocumented K/S tuples | **CONFIRMED** |
| HW REV | `4` | Board revision r04 on physical hardware | Dynamic DTBO selection | **CONFIRMED** |
| DDR SIZE | `8G` | Physical RAM capacity (8 GB) | Memory configuration in custom kernel | **CONFIRMED** |
| BUILD VERSION | `X510XXUCEZE4` | Build installed on physical hardware | Upstream kernel compatibility | **CONFIRMED** |
| Safe reboot combo | `Vol Down + Side Key > 7s` | Official cancel/reboot sequence | That it works in a low-level hang | **CONFIRMED** |
| OEM LOCK field (Odin) | `NOT DISPLAYED` | Field not shown on this screen | That the bootloader is unlocked | **NOT DISPLAYED** |
| FRP LOCK field (Odin) | `NOT DISPLAYED` | Field not shown on this screen | That FRP is disabled | **NOT DISPLAYED** |
| SYSTEM STATUS (Odin) | `NOT DISPLAYED` | Field not shown on this screen | Filesystem state | **NOT DISPLAYED** |
| DID / Chip IDs | `[REDACTED — DEVICE UNIQUE]` | Unique identifiers present | Omitted for privacy in public repo | **REDACTED** |
| Download warning | visible in photo (`IMG_2113.HEIC`) | Prior warning screen exists | Final confirmation screen | **CONFIRMED** |
| Chinese warning text | `长按音量增加键：设备解锁模式` | Bootloader announces entry into Device Unlock Mode | That unlock will execute | **CONFIRMED** |
| English warning text | omits the previous line | Omission in English localization | Absence of feature in firmware | **CONFIRMED** |
| Device Unlock Mode (2B) | unphotographed | — | Exact UI options and consequences | **UNKNOWN** |
| D2 | observed | Text `Reboot Device - D2` | That it means screen lock PIN | **CONFIRMED/UNKNOWN** |
| Recovery host | partially validated | Functional USB `04e8:685d` enumeration | Complete physical restoration tested | **PARTIALLY VALIDATED** |

## Rigorous Interpretation

- **RP SWREV B:12**: Samsung Odin Mode physically reports `RP SWREV B:12` on the project unit, directly confirming bootloader software revision 12 / rollback level 12 for the corresponding bootloader component.
- **Absent Fields**: The visual absence of `OEM LOCK` or `FRP LOCK` fields on this screen must not be interpreted as unlocked or without FRP.
- **Screen Distinction**:
  - Screen 1 (Warning Screen): **`CONFIRMED`**.
  - Screen 2A (Normal Odin Mode): **`CONFIRMED`**.
  - Screen 2B (Device Unlock Mode confirmation): **`NOT YET OBSERVED / NOT YET CAPTURED`**.
  - Successful unlock: **`NOT YET TESTED / LOCKED`**.

```text
================================================================================
CANONICAL UNLOCK & RECOVERY STATUS (SM-X510 U12/EZE4):
================================================================================
WARNING SCREEN:                 CONFIRMED
NORMAL ODIN MODE:               CONFIRMED
CURRENT BINARY:                 Samsung Official (CONFIRMED)
KG STATE:                       Completed (00) (CONFIRMED)
SECURE DOWNLOAD:                Enabled (CONFIRMED)
SALES CODE:                     EUX (CONFIRMED)
WARRANTY VOID:                  0 (0x0000) (CONFIRMED)
RP SWREV B:                     12 (CONFIRMED)
HW REV:                         4 (CONFIRMED)
DDR SIZE:                       8G (CONFIRMED)
BUILD VERSION:                  X510XXUCEZE4 (CONFIRMED)
DEVICE UNLOCK MODE ENTRY:       CONFIRMED AS BOOTLOADER UI AFFORDANCE
DEVICE UNLOCK MODE SCREEN:      NOT YET CAPTURED
SUCCESSFUL UNLOCK:              NOT YET TESTED
BOOTLOADER:                     LOCKED
OWNER UNLOCK DECISION:          READY_FOR_OWNER_UNLOCK_DECISION
FIRST CUSTOM FLASH:             NOT_READY_FOR_FIRST_CUSTOM_FLASH
RECOVERY:                       PARTIALLY VALIDATED
================================================================================
```

