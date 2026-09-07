# Device Unlock Mode & Download Mode — Capture Checklist (Non-Destructive)

Objective: Record diagnostic evidence from the bootloader without confirming unlock, without erasing data, and without flashing.

## 1. Physical Evidence Already Confirmed

- [x] **Screen 1: Warning Screen (Pre-Download)**:
  - Captured in `IMG_2113.HEIC`.
  - Displays in English `Volume up : Continue`, `Volume down : Cancel (reset phone)`, `Side key : Show Barcode`.
  - Chinese localization adds: `长按音量增加键：设备解锁模式` ("Long press Volume Up key: Device Unlock Mode").
- [x] **Screen 2A: Normal Odin Mode Status Screen**:
  - Captured in `IMG_2114.HEIC` (public transcription with unique identifiers redacted in [`docs/hardware/evidence/2026-09-05-odin-mode-stock-baseline.md`](file:///Users/markpi/tab-s9-fe-linux/docs/hardware/evidence/2026-09-05-odin-mode-stock-baseline.md)).
  - Directly confirms on UI: `CURRENT BINARY: Samsung Official`, `KG STATE: Completed (00)`, `Secure Download: Enabled`, `Sales code: EUX`, `WARRANTY VOID: 0 (0x0000)`, `RP SWREV B:12`, `HW REV: 4`, `DDR SIZE: 8G`, `BUILD VERSION: X510XXUCEZE4`.
  - Fields not displayed: `OEM LOCK`, `FRP LOCK`, `SYSTEM STATUS` (**`NOT DISPLAYED`**).
  - Official reboot/cancel sequence: `Volume Down Key + Side key for more than 7 secs`.

---

## 2. Next Specific Physical Experiment (Screen 2B: Device Unlock Mode)

1. **Exit current Odin Mode**:
   - Hold down **Volume Down + Side key (`Volume Down Key + Side key`) for more than 7 seconds**, following the official on-screen instruction, to reboot into stock Android.
2. **Return to Warning Screen (Screen 1)**:
   - Power off the tablet.
   - Connect USB cable while holding down **Volume Up + Volume Down** until the blue Warning screen appears.
3. **Enter Device Unlock Mode**:
   - From Screen 1: **HOLD DOWN VOLUME UP (`Long press Volume Up`, ~7 seconds)**.
4. **Photograph Screen 2B (Device Unlock Mode)**:
   - Photographically capture the full screen without cropping edges or text.
5. **CRITICAL: DO NOT CONFIRM BOOTLOADER UNLOCK**:
   - **DO NOT** press the confirmation key (typically Vol Up).
   - Do not execute any action that triggers a factory wipe or alters the Knox fuse.
6. **Meticulously record**:
   - Exact warning text.
   - Explicit list of displayed consequences.
   - Button assigned to confirmation.
   - Button assigned to cancellation.
   - Whether factory reset (`factory reset` / data erasure) is explicitly mentioned.
   - Whether Knox state or warranty void is explicitly mentioned.
   - Any wording referring to bootloader status or OEM lock.
7. **Exit safely**:
   - Press the button assigned to cancellation (typically **Volume Down / `Volume Down`**) to cancel and reboot the device into stock Android without changes.

> [!CAUTION]
> **STRICT SAFETY BOUNDARY**:
> It is strictly forbidden to instruct or authorize the owner to proceed beyond the observation screen. This observation is 100% read-only and non-destructive.

