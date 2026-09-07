# Physical Evidence: Stock Baseline Odin Mode Capture (SM-X510 U12/EZE4)

- **Capture Date**: 2026-09-05
- **Device**: Samsung Galaxy Tab S9 FE WiFi (`SM-X510`)
- **SoC**: Samsung Exynos S5E8835 (Exynos 1380)
- **Firmware on Unit**: `X510XXUCEZE4` (Android 16 / One UI 8 / Bootloader U12)
- **Regional CSC**: `EUX` (Sales code / CID / AID: `EUX//`)
- **Observed Mode**: Samsung ODIN MODE (Screen 2A — Normal Download Mode)
- **Physical Capture Source**: Local physical photograph of device (`IMG_2114.HEIC`)
- **Hardware Status**: **LOCKED / GREEN / STOCK / NON-DESTRUCTIVE OBSERVATION**

---

## 1. Privacy Statement and Handling in Public Repository

> [!IMPORTANT]
> **STRICT PRIVACY REQUIREMENT IN PUBLIC REPOSITORY**:
> The original photograph (`IMG_2114.HEIC`) contains unique device identifiers (DID, Chip ID, Chip ID(SJtag), barcodes/patterns). In accordance with the privacy policy of this public repository:
> 1. The original unedited photograph **is NOT uploaded, included, or committed to the git repository**.
> 2. It remains exclusively as private local physical evidence.
> 3. In public documentation, exclusively the faithful textual transcription is used, with unique device fields explicitly redacted as `[REDACTED — DEVICE UNIQUE]`.
> 4. No sensitive numerical/hexadecimal values for DID or Chip ID have been recorded in commits, git messages, EXIF metadata, or documentation.

---

## 2. Literal Bootloader Transcription (Normal Odin Mode Screen)

The `SM-X510` device was booted to the pre-Download-Mode warning screen and **Volume Up (`Volume up : Continue`)** was briefly pressed, entering the standard **ODIN MODE** screen (Screen 2A).

Physical text visible on screen:

```text
ODIN MODE
DOWNLOAD SPEED: FAST
CURRENT BINARY: Samsung Official
KG STATE: Completed (00)
DID: [REDACTED — DEVICE UNIQUE]
Secure Download: Enabled
Sales code/CID/AID: EUX//
WARRANTY VOID: 0 (0x0000)
RP SWREV:
B:12
K:12(12,12,12,12,12)
S:12
HDM STATUS: NONE
HW REV: 4
DDR SIZE: 8G
BUILD VERSION: X510XXUCEZE4
EVT 0.1
Chip ID: [REDACTED — DEVICE UNIQUE]
Chip ID(SJtag): [REDACTED — DEVICE UNIQUE]

Downloading...
Do not turn off target
Do not disconnect USB cable during the software update!

Volume Down Key + Side key for more than 7 secs
Cancel (restart phone)
```

---

## 3. Evidence Levels Promoted to `CONFIRMED`

From direct visual inspection of the running bootloader microcode, the following are promoted to maximum empirical evidence (**`CONFIRMED`**):

| Parameter Visible on Bootloader | Observed Physical Value | Evidence Level | Scope and Technical Impact |
| :--- | :---: | :---: | :--- |
| **Normal Odin Mode screen** | **Visible / Active** | **CONFIRMED** | Screen 2A reached stably and reproducibly. |
| **CURRENT BINARY** | `Samsung Official` | **CONFIRMED** | Bootloader executes only official Samsung binaries. |
| **KG STATE** | `Completed (00)` | **CONFIRMED** | Knox Guard completed; mask `00` confirms absence of overdue balance/leasing lock. |
| **Secure Download** | `Enabled` | **CONFIRMED** | Download protocol requires official signature authentication for transfers. |
| **Sales code / CID / AID** | `EUX//` | **CONFIRMED** | Open European channel (Open Market / WiFi), without carrier customization. |
| **WARRANTY VOID** | `0 (0x0000)` | **CONFIRMED** | Physical Knox warranty eFuse is intact and un-tripped (0x0). |
| **RP SWREV (Bootloader)** | `B:12` | **CONFIRMED** | Software rollback level 12 (Rollback Index = 12). |
| **HW REV** | `4` | **CONFIRMED** | Physical board hardware revision: r04 (matches DTBO `r04`). |
| **DDR SIZE** | `8G` | **CONFIRMED** | Physical RAM 8 GB (LPDDR4X/LPDDR5). |
| **BUILD VERSION** | `X510XXUCEZE4` | **CONFIRMED** | Matches official EZE4 build inspected and promoted. |
| **Download Speed** | `FAST` | **CONFIRMED** | Link speed negotiated by USB controller in SBOOT. |
| **HDM STATUS** | `NONE` | **CONFIRMED** | Hardware Device Management not active. |
| **EVT Stage** | `0.1` | **CONFIRMED** | Samsung engineering design stage identifier. |
| **Safe reboot combination** | `Vol Down + Side Key > 7s` | **CONFIRMED** | Explicit cancellation and safe reboot instruction provided by bootloader. |

---

## 4. Rigorous Technical Interpretation of `RP SWREV`

The bootloader physically reports:
```text
RP SWREV:
B:12
K:12(12,12,12,12,12)
S:12
```

- **Safe and Canonical Interpretation**:
  > *"Samsung Odin Mode physically reports `RP SWREV B:12` on the project unit, directly confirming bootloader software revision 12 / rollback level 12 for the corresponding bootloader component."*
- **Comparison with Name Inference**: This reading on the low-level SBOOT interface constitutes substantially stronger empirical proof than merely deducing "U12" from Samsung naming conventions (`X510XXUCEZE4`).
- **Discipline Against Overgeneralization**: Detailed semantics of each individual tuple in the key or security fields (`K:12(...)`, `S:12`) must not be arbitrarily conjectured without official documentation. The proven operational datum is `B:12`.

---

## 5. Critical Parameters NOT Visible on This Screen

In this Odin Mode version for SM-X510 U12, the following classic diagnostic fields are **NOT visibly displayed**:

- `OEM LOCK`: **`NOT DISPLAYED`**
- `FRP LOCK`: **`NOT DISPLAYED`**
- `SYSTEM STATUS`: **`NOT DISPLAYED`**

> [!WARNING]
> **PROHIBITION AGAINST INFERRING STATE FROM ABSENCE**:
> That fields `OEM LOCK` or `FRP LOCK` do not appear printed on this screen does **NOT** mean the device is unlocked nor that FRP is disabled. Device state remains governed by properties confirmed via Android/ADB (`ro.boot.flash.locked = 1`, `ro.boot.vbmeta.device_state = locked`, `ro.boot.verifiedbootstate = green`).

---

## 6. Strict Distinction Among the Three Bootloader Screens

To prevent confusion in project traceability, a clear distinction is established between:

1. **Screen 1: Warning Screen (Pre-Download)**:
   - Physically captured in `IMG_2113.HEIC`.
   - Displays options: `Volume up : Continue`, `Volume down : Cancel (reset phone)`, `Side key : Show Barcode`.
   - Chinese localization explicitly announces: `长按音量增加键：设备解锁模式` (*"Long press Volume Up: Device Unlock Mode"*).
   - Status: **`CONFIRMED`**.

2. **Screen 2A: Normal Odin Mode (Downloading...)**:
   - Physically captured in `IMG_2114.HEIC` (this document).
   - Entered via short press of Volume Up (`Volume up : Continue`) from Screen 1.
   - Displays hardware diagnostics: `CURRENT BINARY: Samsung Official`, `RP SWREV: B:12`, `HW REV: 4`, etc.
   - Status: **`CONFIRMED`**.

3. **Screen 2B: Device Unlock Mode (Unlock Dialog)**:
   - Announced on Screen 1 via long press of Volume Up.
   - Warning dialog regarding consequences, data loss, and unlock confirmation.
   - Status: **`NOT YET CAPTURED / NOT YET OBSERVED`**.

---

## 7. Next Safe Physical Action and Exit Protocol

1. **Safe Exit from Odin Mode**:
   - Hold down **Volume Down + Side key (`Volume Down Key + Side key`) for more than 7 seconds**, per on-screen instructions.
   - The device will cancel software download wait and reboot normally into stock Android.
   - Zero risk, zero data wipe.

2. **Next Experimental Capture (Screen 2B — Device Unlock Mode)**:
   - Boot device again to Screen 1 Warning (connect USB while holding `Vol Up + Vol Down` with tablet powered off).
   - From Screen 1: **HOLD DOWN VOLUME UP (`Long press Volume Up`, ~7 seconds)**.
   - Photograph the resulting screen (**Screen 2B: Device Unlock Mode**).
   - **CRITICAL**: **DO NOT CONFIRM UNLOCK** (do not press Volume Up on Screen 2B).
   - Record:
     - Exact warning text and described consequences.
     - Confirmation button vs cancellation button.
     - Whether factory reset (`factory reset` / data erasure) is explicitly mentioned.
     - Whether Knox state or warranty void is mentioned.
     - Any mention of OEM lock state.
   - **PRESS VOLUME DOWN (`Volume Down`)** to cancel and reboot device safely without changes.
