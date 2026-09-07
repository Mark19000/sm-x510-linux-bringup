# Platform Expansion Model: SM-X510 Bring-up Architecture

- **Platform**: Samsung Galaxy Tab S9 FE (`SM-X510`)
- **SoC**: Samsung Exynos S5E8835 (Exynos 1380)
- **Purpose**: Decouple project infrastructure to support both Linux and Android without code duplication or rigid assumptions.

---

## 1. Platform Tree Overview

The project evolves from an effort focused exclusively on downstream Linux toward a unified platform engineering umbrella:

```
SM-X510 Platform Bring-up
├── Android
│   ├── stock-research       # Extraction, stock image auditing, partitions, AVB
│   └── aosp                 # AOSP tree / LineageOS / Generic System Images (GSI)
└── Linux
    ├── downstream-samsung   # Official Samsung 5.15.189 kernel (current canonical EZE4)
    └── mainline             # Upstream Linux kernel / upstream devicetree for Exynos 1380
```

---

## 2. Cross-Cutting Shared Components (Shared Core)

The following research, documentation, and tooling modules are independent of the final operating system and must remain decoupled:

### 2.1 Hardware & Silicon Documentation
- Hardware register documentation, memory mapping, and Exynos S5E8835 power domains (`docs/hardware/`).
- PMIC protocols (`S2MPU15`, `S2MPU16`) and CMUCAL clock controllers.

### 2.2 Device Tree Research
- Peripheral mapping, DSI displays, Wacom / S-Pen digitizer, Cirrus CS35L45 audio, charging controllers, and DWC3 USB.
- Decompiled device trees and semantic `.dtbo` analyses apply equally to AOSP and downstream Linux.

### 2.3 Chain of Trust and Boot Packaging (Boot & AVB Engine)
- Android v4 boot header manipulation scripts (`magiskboot-arm64`, `avbtool`).
- `vbmeta` generation and AVB 2.0 digest computation.
- LOKE/Odin download protocols and emergency runbooks.

### 2.4 Stock Audit and Partition Extraction
- `vendor_boot` analysis tools, ramdisk inventories, and DLKM auditing.
- SHA-256 integrity verification of stock images (`artifacts/stock/`).

### 2.5 Parity and Diagnostic Tools (ABI & Observability)
- Symbol binary audit tools (`verify-eze4-abi.py`, ELF `__versions` parsers).
- `sec_debug` / DSS capture modules in DRAM and crash dump analyzers.
- USB-C power consumption profiles and Power Delivery negotiation.

---

## 3. Decoupling Guidelines for New Developments

1. **Do not hardcode Linux-specific absolute paths in shared tools**: Shared utilities in `tools/` and `scripts/` must accept working paths via CLI arguments or environment variables.
2. **Preserve namespace separation in `artifacts/`**:
   - `artifacts/stock/`: Immutable stock factory evidence.
   - `artifacts/eze4/`: Canonical downstream kernel outputs.
   - `artifacts/aosp/` (future): Android userspace builds.
   - `artifacts/mainline/` (future): Upstream kernel experiments.
3. **Reuse of EZE4 Kernel as Gold Reference**: Any divergence in a future kernel (e.g. Mainline) will be benchmarked against the 100% parity of `Module.symvers` and DTBOs demonstrated in EZE4.
