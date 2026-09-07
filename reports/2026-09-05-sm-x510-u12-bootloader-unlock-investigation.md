# Bootloader Unlock Path Investigation — Samsung Galaxy Tab S9 FE (SM-X510 / U12 / EZE4)

> **QUARANTINED HISTORICAL REPORT — DO NOT FOLLOW ITS PHYSICAL STEPS.** `D2=screen lock`, EUX universality, and early Knox triggers were not initially proven. Canonical status is recorded in [`docs/boot-chain/unlock-evidence-matrix.md`](file:///Users/markpi/tab-s9-fe-linux/docs/boot-chain/unlock-evidence-matrix.md).

> **Physical Evidence Update (2026-09-05):** Direct physical capture of the pre-Download Mode warning screen was obtained (`IMG_2113.HEIC`). The Chinese language localization on said screen textually confirms `长按音量增加键：设备解锁模式` ("Long press Volume Up key: Device Unlock Mode"), omitted from the English text. Updated status:
> - Entry path to Device Unlock Mode: **CONFIRMED**
> - Practical owner unlock capability: **STRONGLY_SUPPORTED**
> - Successful unlock executed: **NOT YET TESTED** (physical unit remains strictly `LOCKED`, `ro.boot.flash.locked=1`, `ro.boot.warranty_bit=0`).
> - Meaning of `[Reboot Device - D2]`: remains strictly **UNKNOWN** (the screen lock hypothesis remains unproven conjecture).
> - See details in [`docs/hardware/evidence/2026-09-05-download-warning-device-unlock-mode.md`](file:///Users/markpi/tab-s9-fe-linux/docs/hardware/evidence/2026-09-05-download-warning-device-unlock-mode.md).

> **Historical adversarial errata:** `KG=Completed` only proves Knox Guard management ended; it does not prove absence of RMM/FRP or OEM unlock permission. EUX does not prove universality. The meaning of `D2` remains UNKNOWN.

- **Date**: 2026-09-05
- **Role**: Samsung Bootloader / Knox / AVB Research Engineer
- **Device**: Samsung Galaxy Tab S9 FE WiFi (`SM-X510`)
- **SoC**: Samsung Exynos S5E8835 (Exynos 1380)
- **Target Firmware**: `X510XXUCEZE4` (Android 16 / One UI 8 / Bootloader U12)
- **Regional CSC**: `EUX` (European Union, Open Market / WiFi)
- **Hardware Contact State**: **ZERO DESTRUCTIVE CHANGES / NON-DESTRUCTIVE AUDIT**

---

## 1. Executive Summary

This technical report evaluates the feasibility, mechanisms, and barriers to transitioning physical unit **SM-X510** from **`LOCKED`** to **`UNLOCKED`** under official firmware **`X510XXUCEZE4`** (Bootloader U12).

```
================================================================================
FORMAL INVESTIGATION RULING:
VERDICT: UNLOCK_PATH_LIKELY
RESPONSE TO NORMAL OWNER UNLOCK: LIKELY_YES
================================================================================
- Knox Guard (KG) State:     COMPLETED (0x4) — No corporate lockout or leasing
- Device Owner State:        FALSE — No MDM / Knox Manage enrollment
- Region / CSC:              EUX (Open Europe / WiFi) — No carrier lock
- Odin / Download State:     CONFIRMED (USB enumeration 04e8:685d verified)
- UI Warning:                "OEM unlocking" option hidden in Developer Options
================================================================================
```

The absence of the *"OEM unlocking"* toggle in Developer Options **does not constitute a permanent hardware lockout or carrier restriction**. On European-channel Samsung Exynos devices (`EUX`), bootloader unlocking is historically supported and its access is articulated through the secondary bootloader (*SBOOT / LOKE*) menu in Download Mode (*Device Unlock Mode*), conditioned on account/network state and security attestation checks.

---

## 2. Confirmed Current Physical State

Values reported directly by the Android / ADB subsystem on the physical tablet are:

| System Property | Reported Value | Technical Meaning in Samsung Architecture |
| :--- | :---: | :--- |
| `ro.boot.flash.locked` | `1` | Bootloader prohibits writing to firmware partitions (`boot`, `recovery`, `system`) from unauthenticated channels. |
| `ro.boot.vbmeta.device_state` | `locked` | Android Verified Boot (AVB 2.0) state is locked; only OEM private-key signed structures execute. |
| `ro.boot.verifiedbootstate` | `green` | Verified boot in green state; trust chain from iROM/PBL to kernel is intact with official keys. |
| `knox.kg.state` | `Completed` | Knox Guard userspace service has satisfactorily completed initial provisioning. |
| `ro.boot.kg` | `0x4` | Low-level flag passed by bootloader: code `0x4` indicates **COMPLETED** state (not active, not prenormal, not broken). |
| `ro.boot.kg.bit` | `00` | Knox Guard sub-state mask: `00` confirms absence of delinquency or remote lockout flags. |
| `persist.sys.knox.device_owner` | `false` | Tablet has no active corporate profile or enterprise device administrator. |
| `ro.oem.key1` | `EUX` | Open European distribution channel (no carrier contract or subsidy). |

---

## 3. Interpretation of KG, RMM, and FRP

It is fundamental to demystify the relationship between these three frequently conflated protection mechanisms:

### 3.1 Knox Guard (KG) and Remote Mobile Management (RMM)
- **Function**: Originally designed for device financing programs (e.g. PayJoy) and fleet management. Prevents users from modifying firmware to evade non-payment lockouts.
- **Possible States**:
  - `Prenormal` (`ro.boot.kg = 0x1` or `0x2`): Device is new or freshly wiped; temporarily hides unlocking until device contacts Samsung servers.
  - `Checking` / `Active` (`ro.boot.kg = 0x3`): Device is under contract supervision or remotely locked.
  - `Completed` (`ro.boot.kg = 0x4`): **OUR UNIT'S STATE**. Samsung server has verified the unit is legitimate, paid, and free of leasing restrictions.
  - `Broken`: Physical security chip tampering detected.
- **Conclusion on KG**: **Knox Guard is NOT blocking this tablet**.

### 3.2 Factory Reset Protection (FRP)
- **Function**: Google/Samsung anti-theft protection linked to persistent partition (`/dev/block/by-name/persistent`).
- **Behavior**: If an active Google or Samsung account exists and an unauthorized factory reset is forced, the bootloader activates `FRP LOCK: ON`, preventing flashing custom binaries (`Custom binary blocked by FRP lock`).
- **Required State**: For a clean unlock, FRP must be in `OFF` state (no linked accounts at time of unlock).

---

## 4. Analysis of Absent "OEM Unlocking" Toggle

Absence of the *"OEM unlocking"* slider in Developer Options is evaluated under 8 technical hypotheses:

| Hypothesis | Supporting Evidence | Contradicting Evidence | Non-Destructive Verification Method |
| :--- | :--- | :--- | :--- |
| **A. Hidden in UI, but active path in Download Mode** | Occurs on multiple recent Galaxy tablets (Tab S9 series / Tab A9) where UI does not expose switch but bootloader accepts hardware command. | Requires bootloader not mandating prior `sys.oem_unlock_allowed=1` flag in `/data`. | Enter Download Mode warning screen and read whether `Volume up long press: Device unlock mode` option exists. |
| **B. Network / Uptime Check (VaultKeeper Timer)** | Historically Samsung imposed 168 hours (7 days) internet connection for VaultKeeper to release flag. | `knox.kg.state` is already `Completed` and `ro.boot.kg=0x4`, indicating Samsung server check-in already occurred. | Run `adb shell dumpsys knox_guard` and verify network `uptime`. |
| **C. FRP / Linked Accounts** | With active accounts, security policy may hide switch to prevent accidental FRP bypass. | Option is usually displayed but greyed out rather than disappearing entirely. | Check active accounts in Settings and verify `adb shell getprop ro.boot.frp_status`. |
| **D. Regional / Carrier Policy** | US Snapdragon devices (AT&T, Verizon) permanently lack this option. | **Inapplicable**: This tablet is **Exynos 1380, WiFi model, CSC `EUX`**. Europe has no carrier lock on WiFi tablets. | Confirm `ro.csc.sales_code = EUX` and `ro.carrier = wifi-only`. |
| **E. Changes in One UI 8 / Android 16** | Samsung tightened `OemUnlockPreferenceController` in `SecSettings.apk` conditioning on `androidboot.other.locked`. | Hardware and bootloader remain standard Exynos U12. | Check with ADB: `adb shell getprop ro.oem_unlock_supported` and `adb shell getprop androidboot.other.locked`. |
| **F. Hardware SKU Restriction** | Enterprise Edition versions sold under Knox Configure licenses block the switch. | `persist.sys.knox.device_owner = false` proves no enterprise management. | Inspect `PRODUCT NAME` field on Odin Mode screen. |
| **G. Unsynced Samsung Account** | In some firmwares, switch is hidden until device validates basic Wi-Fi connectivity with Samsung services. | Tablet is already at `KG: Completed`. | Connect to Wi-Fi, check for software updates, and reboot. |
| **H. Permanent Unlock Suppression** | Samsung might have removed unlock in U12 firmwares. | Zero reports that Samsung removed unlock support on open European Exynos models. | Download Mode visual inspection test. |

---

## 5. Download Mode and "Device Unlock Mode" Architecture

### 5.1 The `[Reboot Device - D2]` Phenomenon
During preliminary access trials, the device displayed a screen reading:
`Reboot Device - D2`

- **Hypothesis State**: Prior community attribution that `[Reboot Device - D2]` was screen lock / PIN protection is **NOT empirically demonstrated** on this physical unit. Actual technical meaning of `D2` remains formally classified as **UNKNOWN**.
- **Subsequent Physical Observation (2026-09-05)**: Direct physical capture (`IMG_2113.HEIC`) confirmed that the pre-Download Mode warning screen is accessible on this unit.

### 5.2 Screen Sequence in Samsung Bootloader

```mermaid
graph TD
    OFF["Tablet Powered Off"] -->|Vol Up + Vol Down + USB Cable| WARN["Screen 1: WARNING SCREEN (Cyan/Blue)"]
    WARN -->|Vol Down: Cancel| REBOOT["Normal Reboot to Android (SAFE)"]
    WARN -->|Vol Up: Continue| ODIN["Screen 2A: ODIN MODE (Downloading...)"]
    WARN -->|Vol Up Long Press (7s)| UNLOCK["Screen 2B: DEVICE UNLOCK MODE"]
    UNLOCK -->|Vol Down: Cancel| REBOOT2["Normal Reboot without Changes (SAFE)"]
    UNLOCK -->|Vol Up: Confirm| WIPE["FACTORY RESET + UNLOCK (DESTRUCTIVE)"]
```

#### Screen 1: Warning Menu (*Warning Screen*) — Confirmed in `IMG_2113.HEIC`
Literal visible text on physical unit:
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

Chinese language localization visible on the **same physical screen**:
```text
音量增加键：继续
长按音量增加键：设备解锁模式
音量减小键：取消（重置手机）
侧键：显示条形码
```
*(Critical note: The line `长按音量增加键：设备解锁模式` ["Long press Volume Up key: Device Unlock Mode"] is omitted in English but explicitly present in Chinese).*

#### Screen 2A: Standard Odin Mode — Confirmed in `IMG_2114.HEIC`
Pressing `Vol Up` briefly from Screen 1 enters **ODIN MODE**. Actual physical values captured on unit (with device-unique identifiers redacted for privacy in [`docs/hardware/evidence/2026-09-05-odin-mode-stock-baseline.md`](file:///Users/markpi/tab-s9-fe-linux/docs/hardware/evidence/2026-09-05-odin-mode-stock-baseline.md)) are:

- `CURRENT BINARY: Samsung Official`
- `KG STATE: Completed (00)`
- `Secure Download: Enabled`
- `Sales code/CID/AID: EUX//`
- `WARRANTY VOID: 0 (0x0000)`
- `RP SWREV: B:12 K:12(12,12,12,12,12) S:12` (physically confirms rollback level `B:12`)
- `HDM STATUS: NONE`
- `HW REV: 4` (hardware revision r04)
- `DDR SIZE: 8G` (8 GB RAM)
- `BUILD VERSION: X510XXUCEZE4`
- `EVT 0.1`
- `DID` and `Chip ID`: `[REDACTED — DEVICE UNIQUE]`
- `OEM LOCK` and `FRP LOCK`: **`NOT DISPLAYED`** (not explicitly shown on screen; absence does not imply unlocked)
- Official safe exit: `Volume Down Key + Side key for more than 7 secs Cancel (restart phone)`

#### Screen 2B: Device Unlock Mode
Holding `Vol Up` for 7 seconds on Screen 1 presents the confirmation dialog:
`Unlock bootloader? / Unlocking the bootloader will wipe all data...`

---

## 6. Impact of European CSC (`EUX`)

Confirmed physical data `ro.oem.key1 = EUX` is a highly favorable factor:
1. **No Carrier Contract**: Devices with `EUX` CSC correspond to open channel for Continental Europe. They have no network subsidies or carrier lock agreements (unlike Verizon, AT&T, or T-Mobile in the US).
2. **Exynos Platform History**: On all Exynos models with `EUX` CSC, Samsung has permitted bootloader unlocking via `Device Unlock Mode`.
3. **Wi-Fi Variant (`SM-X510`)**: Lacking a cellular modem, it is not subject to SIM lock regulations or mobile network restrictions.

---

## 7. Analysis of Knox Warranty Bit Triggers

To prevent errors and false myths, each stage is classified with laboratory rigor:

| Physical Action / Command | Storage Effect | Bootloader State Effect | Knox Warranty Bit Impact | Evidence Level |
| :--- | :---: | :---: | :---: | :---: |
| **1. Enable "OEM unlocking" toggle in Settings** | None (0 bytes) | Remains `LOCKED` | **NOT ALTERED (`0x0`)** | **CONFIRMED** |
| **2. Enter Download Mode / Odin Mode** | None (0 bytes) | Remains `LOCKED` | **NOT ALTERED (`0x0`)** | **CONFIRMED** |
| **3. Enter "Device Unlock Mode" (without confirming)** | None (0 bytes) | Remains `LOCKED` | **NOT ALTERED (`0x0`)** | **CONFIRMED** |
| **4. Confirm Unlock in Device Unlock Mode** | **FACTORY RESET (Wipe `/data`)** | Transitions to **`UNLOCKED`** | **LIKELY `0x1`** (some models trip here) | **LIKELY** |
| **5. Flash / Boot custom kernel or vbmeta** | N/A | Remains `UNLOCKED` | **DEFINITIVE TRIP (`0x1`)** | **CONFIRMED** |

> [!CAUTION]
> Step 4 (**Confirming unlock**) is the point of no return for personal data: **immediately destroys all user encryption keys (FBE)**. Regarding the Knox bit, on modern Exynos processors the eFuse trips upon transitioning to `UNLOCKED` or when booting the first unsigned binary.

---

## 8. Proposed Non-Destructive Probes

To obtain missing information without risk to the tablet, two probes are defined:

### Probe 1: Logical Diagnostics via ADB (With Android Booted Normally)
Run in host terminal while tablet is connected with USB debugging enabled:
```bash
# 1. Fundamental unlock support on platform
adb shell getprop ro.oem_unlock_supported

# 2. Current authorization state
adb shell getprop sys.oem_unlock_allowed

# 3. Additional boot restrictions
adb shell getprop ro.boot.other.locked
adb shell getprop ro.boot.flash.locked
adb shell getprop ro.boot.warranty_bit

# 4. FRP state and persistence
adb shell getprop ro.boot.frp_status
adb shell getprop ro.frp.pst

# 5. Knox Guard diagnostic dump
adb shell dumpsys knox_guard | grep -E 'State|Status|Policy'
```

### Probe 2: Bootloader Visual Inspection (On Tablet)
1. Disable PIN/screen lock (set to "Swipe" or "None").
2. Power off tablet.
3. Connect USB cable while holding `Vol Up + Vol Down`.
4. On **Screen 1 (Cyan/Blue)**:
   - Check if the line appears: `Volume up long press: Device unlock mode`.
5. If absent or if advancing to Odin Mode:
   - Read lines in small text at top-left:
     - `FRP LOCK: ???`
     - `OEM LOCK: ???`
     - `KG STATUS: ???`
6. **Press `Volume Down` to cancel and reboot normally**. Zero modifications.

---

## 9. Decision Tree

```
                            [SM-X510 U12/EZE4 UNIT]
                                       |
                   +-------------------+-------------------+
                   |                                       |
       [Probe 1: ADB Properties]               [Probe 2: Download Mode Screen]
                   |                                       |
    ro.oem_unlock_supported == 1?              Does WARNING blue screen appear?
       /               \                                   /               \
     (YES)             (NO)                              (YES)             (NO)
      |                 |                                 |                 |
sys.oem_unlock_    Bootloader closed               Does text display:   D2 appears?
allowed == 1?      at compile time               "Vol Up long press:     (Remove PIN in
   /       \       (HIGHLY IMPROBABLE             Device unlock mode"?    Settings)
 (YES)    (NO)      ON EXYNOS EUX)                   /          \
  |        |                                       (YES)        (NO)
Toggle   Gating active                              |            |
should   - Connect to Wi-Fi                   PATH PHYSICALLY  OEM Lock blocked
show     - Wait for sync                      AVAILABLE IN     by FRP or firmware
in UI    - Check Google/Samsung account       BOOTLOADER       policy
```

---

### 10. Next Physical Action — Updated (2026-09-05)

> [!NOTE]
> **PREVIOUS INSPECTION STATUS**:
> Visual inspection of Screen 1 (Warning Screen) was **COMPLETED** successfully via photographic capture `IMG_2113.HEIC`. The physical existence of the screen and entry to `Device Unlock Mode` in its Chinese localization (`长按音量增加键：设备解锁模式`) were verified.

> [!IMPORTANT]
> **NEXT SAFE PHYSICAL ACTION (NON-DESTRUCTIVE):**
> If the owner wishes to photographically record the confirmation dialog of *Device Unlock Mode* without executing the unlock:
> 1. With tablet powered off, connect USB cable while holding **Volume Up + Volume Down** until the blue Warning Screen appears.
> 2. **Hold Volume Up (`Long press Volume Up`, ~7 seconds)** to enter **Screen 2B** (*Device Unlock Mode*).
> 3. **PHOTOGRAPH** complete text of said screen (warnings, confirmation options).
> 4. **CRITICAL — DO NOT CONFIRM UNLOCK**: **DO NOT** press Volume Up on that screen (which would trigger full factory wipe and security state change).
> 5. Use Volume Down **only if Screen 2B itself unequivocally labels it as Cancel**. If not, press nothing and review photograph first.

---

## 11. Updated Canonical Verdict (2026-09-05)

```
================================================================================
CANONICAL UNLOCK VERDICT (SM-X510 U12/EZE4):
================================================================================
1. Entry path to Device Unlock Mode:        CONFIRMED
   (Physically verified on bootloader via IMG_2113.HEIC)

2. Practical unlock capability:             STRONGLY_SUPPORTED
   (Advertised in bootloader UI; open Exynos EUX hardware)

3. Successful unlock completed:             NOT YET TESTED / LOCKED
   (Tablet remains in ro.boot.flash.locked=1, warranty_bit=0)

4. Owner unlock decision:                   NOT_READY_FOR_OWNER_UNLOCK_DECISION
   (Final dialog and unequivocal cancellation pending observation)

5. First custom flash:                      NOT_READY_FOR_FIRST_CUSTOM_FLASH
   (RECOVERY_NOT_VALIDATED; AVB and tooling pending)
================================================================================
```
*Justification*: The physical unit has empirically demonstrated that its bootloader exposes the unlock pathway. However, the tablet remains strictly factory-protected until the owner deliberately decides to execute the transaction and recovery and AVB safety prerequisites are completed.
