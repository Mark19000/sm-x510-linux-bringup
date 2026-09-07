# 7. Mainline Linux Roadmap

## Why Not Write the Final DTS First

Upstream mainline contains no `samsung,s5e8835-*` support. Submitting a monolithic DTS with hundreds of unknown nodes creates review churn and cannot be reviewed effectively. Upstreaming must follow a clean dependency hierarchy, introducing YAML bindings and drivers before DT consumer nodes.

## Series 1: Minimal Console Boot

1. SoC and board compatible bindings;
2. Clock IDs and minimal CMU driver;
3. Pinctrl / GPIO and EINT interrupt controllers;
4. Required PMU / reset lines;
5. UART / earlycon drivers;
6. Minimal `s5e8835.dtsi` defining CPU nodes, memory map, GIC, timer, and UART;
7. Minimal Galaxy Tab S9 FE DTS specifying `/chosen` and serial console.

Goal: Native mainline output on serial UART, even without storage or display drivers.

## Series 2: Storage and USB

1. UFS power domains and clock branches;
2. S5E8835 UFS PHY and calibration data;
3. UFS host controller glue layer;
4. UFS initialization in conservative, read-only mode;
5. USB2/3 PHY glue and DWC3 core integration;
6. Type-C role switching once the port controller is supported.

Goal: Booting a persistent external root filesystem or initramfs with reliable UFS/USB access.

## Series 3: Graphical User Interface

1. SysMMU v8 driver;
2. Display CMU clocks and power domains;
3. DPU / DECON display controller and DPP;
4. DSIM controller and MIPI D-PHY;
5. Panel drivers for both display variants and backlight control;
6. Touchscreen and Wacom digitizer drivers.

## Series 4: Daily Operation

GPU acceleration, Wi-Fi/BT, audio, system suspend/resume, sensors, and power management. Battery charging and thermal regulation must only be ported once reliable telemetry is proven; bugs in power subsystems can cause physical hardware damage rather than merely kernel crashes.

## Upstream Patch Acceptance Criteria

- One distinct concept per patch;
- Devicetree YAML binding documentation precedes or accompanies the driver;
- `make dt_binding_check` and `make dtbs_check` complete cleanly;
- `checkpatch.pl` reports zero material errors; during downstream work, use the vendor script, while for upstreaming, use the mainline kernel's script;
- Avoid Android-specific policy properties where standard Linux abstractions exist;
- Hardware register behaviors documented from datasheets or empirically verified traces;
- Real hardware boot test described in the commit message;
- Specific, lowercase compatible strings (e.g. `samsung,exynos1380-...`), subject to upstream maintainer convention.

The most useful style reference is not the vendor code, but the most recently merged Exynos SoC in upstream Linux. Study Exynos850/990/2200/AutoV9 for driver structure; verify every register address against S5E8835.
