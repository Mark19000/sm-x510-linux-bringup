# Emergency and Recovery Protocol (Hardware Recovery Runbook)

> **SUPERSEDED — DO NOT EXECUTE.** Preserved as historical design. Assumes unobserved screens/values and a complete package that is no longer present. The active authority is `docs/hardware/recovery-readiness-v2.md`, whose verdict is `RECOVERY_NOT_VALIDATED`.

- **Device**: Samsung Galaxy Tab S9 FE WiFi (`SM-X510`)
- **SoC**: Samsung Exynos S5E8835
- **Official Backup Firmware**: `X510XXUCEZE4` (Android 16 / U12 / CSC EUX)
- **Stock Firmware SHA-256 Hash**: `45a450875ce753e74d8183aa085837ada91cabe2832d9725a1567aa29b01d375`

---

## 1. Fundamental Safety Principle

> [!IMPORTANT]
> At no time will a physical test be performed on the device without having the full official firmware locally verified beforehand and empirical confirmation of access to Download Mode.

Entry into Download Mode is confirmed only with the current stock system. It is not guaranteed after boot chain corruption, power failure, or writing to critical partitions; Loke must not be attributed to PBL/iROM without evidence. See `docs/hardware/recovery-readiness-v2.md`.

---

## 2. Procedure to Enter Download Mode

For the **SM-X510 (WiFi)** model without a physical Home button:

1. **Full Power Off**:
   - If the tablet is powered on or in a boot loop, force shutdown by holding down **Power + Volume Down (Vol Down)** for 8 to 10 seconds until the screen goes completely black.
2. **Key Combination Connection**:
   - With the USB-C cable connected to the host computer (but **disconnected** from the tablet).
   - Simultaneously hold down **Volume Up (Vol Up) + Volume Down (Vol Down)**.
   - While continuing to hold both volume buttons, **insert the USB-C cable** into the tablet.
3. **Warning Screen**:
   - The tablet will power on showing a light cyan/blue screen with a warning triangle.
   - Release the volume buttons.
4. **Download Mode Entry Confirmation**:
   - Briefly press **Volume Up (Vol Up)** to enter formal flashing mode (*Download Mode*).
   - The screen will display bootloader information in small text in the upper left corner:
     - `PRODUCT NAME: SM-X510`
     - `CURRENT BINARY: Samsung Official` (or `Custom` post-unlock)
     - `FRP LOCK: OFF`
     - `OEM LOCK: OFF`
     - `WARRANTY VOID: 0x0` (or `0x1`)
     - `AP SWREV: B:12 K:12 S:12`

---

## 3. Host Communications Verification

On the host machine (Linux or macOS), the tablet in Download Mode must enumerate with Samsung's Vendor ID (`04e8`):
```bash
# On macOS:
system_profiler SPUSBDataType | grep -A 5 "SAMSUNG"

# On Linux:
lsusb -d 04e8:685d  # Or equivalent Samsung modem/CDC ID
```

The flashing protocol used by Samsung is **LOKE / Odin**. It can be interfaced via open-source tools like `heimdall` or via the official `Odin3` utility in a Windows/VM environment.

---

## 4. Immutable Official Restoration Package

For any restoration to 100% stock factory state, use exclusively the complete downloaded and verified package:
- **Archive**: `SM-X510_EUX_X510XXUCEZE4_fac.zip` (or uncompressed equivalent).
- **Components**:
  - `AP_X510XXUCEZE4_...tar.md5`: Contains `boot.img`, `init_boot.img`, `vendor_boot.img`, `dtbo.img`, `system.img`, `vendor.img`.
  - `BL_X510XXUCEZE4_...tar.md5`: Contains secondary bootloader (`sboot.bin`), partition tables (`pit`), `param.bin`.
  - `CSC_OXM_X510OXMCEZE4_...tar.md5`: Contains regional configuration and partitioning script.
  - `HOME_CSC_...`: Alternative that preserves user data if only restoring the system.

---

## 5. Abort and Safe Exit Protocol

If the device becomes unresponsive during a physical test or canceling the process is desired:
1. **Force Reboot**:
   - Hold down **Power + Volume Down (Vol Down)** for 7 to 10 uninterrupted seconds.
   - The device will immediately reboot.
2. **Emergency Restoration Upon Bootloop**:
   - If after flashing a test image the kernel enters panic or cyclic reboot:
     1. Force power off and immediately enter Download Mode (step 2).
     2. Restore every partition that was modified; do not assume `boot` and `vendor_boot` suffice if `vbmeta`, `init_boot`, or `dtbo` also changed.
     3. Do not promise return to Android or user data preservation until tooling, full package, and unlock/FRP policies are validated.
