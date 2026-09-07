# Physical Evidence: Download Mode Warning Screen Capture and Device Unlock Mode Entry

Artifact external to repo: `/Users/markpi/Downloads/IMG_2113.HEIC`; size `4,361,729` bytes; SHA-256 `18e17038e45d37b2b7410ab659d5e98121ce16b4fdb7669a1b761f012a20924e`. Visually verified on 2026-09-05; temporary PNG conversion did not alter the original.

- **Capture Date**: 2026-09-05
- **Device**: Samsung Galaxy Tab S9 FE WiFi (`SM-X510`)
- **SoC**: Samsung Exynos S5E8835
- **Firmware on Unit**: `X510XXUCEZE4` (Android 16 / One UI 8 / Bootloader U12)
- **Regional CSC**: `EUX` (European Union, Open Market / WiFi)
- **Source Image File**: `/Users/markpi/Downloads/IMG_2113.HEIC` (4.2 MB)
- **Hardware Contact State**: **NON-DESTRUCTIVE VISUAL OBSERVATION (NO FLASHING, NO PARTITION MODIFICATIONS)**

---

## 1. Physical Observation Performed

A photograph of the pre-Download-Mode warning screen was physically captured directly from the project's `SM-X510` tablet.

### 1.1 Visible English Text
```text
Warning

A custom OS can cause critical problems in
phone and installed applications. If you want
to download a custom OS, press the volume
up key.

Volume up : Continue
Volume down : Cancel (reset phone)
Side key : Show Barcode
```

### 1.2 Chinese Localization on the Same Screen (Critical Detail)
The same screen contains additional localized text in Chinese. In that section, the following explicitly appears:

```text
长按音量增加键：设备解锁模式
```

**Approximate translation**:
> *"Long press Volume Up key: Device Unlock Mode"*

### 1.3 Evidence Analysis
- **Omission in English**: This line is **NOT** visibly present in the English text of the same screen.
- **Direct Interface Proof**: It constitutes direct physical evidence that the bootloader microcode (SBOOT/LOKE U12) of this specific physical unit actively exposes an entry path to *Device Unlock Mode* via a long press of Volume Up.
- **Hierarchy of Evidence**: This direct observation on real project hardware carries technical weight substantially superior to generic Samsung documentation or community forum reports.

---

## 2. Evidence Level Classification

| Component / Claim | Evidence Level | Detail / Rationale |
| :--- | :---: | :--- |
| **Pre-Download Mode warning screen** | **CONFIRMED** | Photographed and directly verified on the `SM-X510` tablet (`IMG_2113.HEIC`). |
| **Vol Up $\to$ Continue (Download Mode)** | **CONFIRMED** | Displayed directly on bootloader UI. |
| **Vol Down $\to$ Cancel / Reset** | **CONFIRMED** | Displayed directly on bootloader UI. |
| **Side key $\to$ Show Barcode** | **CONFIRMED** | Displayed directly on bootloader UI. |
| **Long press Vol Up $\to$ Entry to Device Unlock Mode** | **CONFIRMED (UI Route)** | Explicitly announced in Chinese text of the unit's bootloader. |
| **Practical owner unlocking capability** | **STRONGLY_SUPPORTED** | Route exists in UI; verification of subsequent screen pending. |
| **Subsequent unlock confirmation screen observed** | **NOT YET** | Long press has not yet been executed to view subsequent dialog. |
| **Unlock successfully completed** | **NO / NOT YET TESTED** | No unlock confirmation has been executed. |
| **Current bootloader status** | **LOCKED** | `ro.boot.flash.locked = 1`, `ro.boot.vbmeta.device_state = locked`. |
| **Verified boot state (AVB)** | **GREEN** | `ro.boot.verifiedbootstate = green`. |
| **Knox Warranty Bit** | **0 (Last obs.)** | `ro.boot.warranty_bit = 0`. No custom binaries have been flashed. |

---

## 3. Chronological Record and Correction of Prior Assertions

The evolution of project observations must be documented rigorously to separate hypotheses from demonstrated facts:

1. **Initial Prediction**: Generic Samsung Exynos behavior suggested this screen and the long-press route should exist.
2. **First Physical Trials**: Initial trials failed to capture this screen (initially displaying the `Reboot Device - D2` screen and subsequently the direct `ODIN MODE Downloading...` screen).
3. **Correct State Degradation**: The project downgraded the state with scientific rigor to **`NOT OBSERVED`** / **`UNKNOWN`** in adversarial reports, refusing to take unobserved physical states for granted.
4. **Definitive Physical Capture (2026-09-05)**: Photograph `IMG_2113.HEIC` irrefutably proves the physical existence of the warning screen on this device.
5. **Localized String Discovery**: Entry to *Device Unlock Mode* is found to be explicitly present in the Chinese section of the screen, while omitted in English.

---

## 4. Status of the `[Reboot Device - D2]` Screen

- The exact meaning of diagnostic code `[Reboot Device - D2]` formally remains **`UNKNOWN`**.
- Prior community hypotheses (e.g. that it corresponded to presence of a screen lock) remain **empirically unproven conjectures** on this unit. It must not be assumed as proven cause.

---

## 5. Recommended Next Physical Step

Having resolved the unknown regarding the physical existence of *Device Unlock Mode*, the next non-destructive experimental step is:

```
[Confirmed Warning Screen]
               │
               ▼
[Hold down Volume Up (Long press Vol Up)]
               │
               ▼
[View Subsequent Device Unlock Mode Screen]
               │
               ├──► Photograph and transcribe exact text
               │
               └──► [CRITICAL: DO NOT CONFIRM UNLOCK]
                     Use only an unambiguous cancellation shown on that screen;
                     if none exists, do not press and review the photo
```

> [!CAUTION]
> A strict distinction must be maintained between **entering the Device Unlock Mode UI to photograph it** and **confirming unlock**. Data erasure is **STRONGLY_SUPPORTED** by standard owner unlock semantics, but the exact dialog has not yet been observed; the precise trigger for the Warranty Bit remains **UNKNOWN**.
