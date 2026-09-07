# 8. Glossary and Exercises

## Concise Glossary

- **ABI/KMI**: Binary contract between kernel core and loadable modules.
- **ACPM**: Proprietary Samsung microcontroller/firmware managing power domains and clocks.
- **AVB**: Android Verified Boot, cryptographic image integrity chain.
- **DT binding**: Specification defining valid properties for a device tree node.
- **BOM**: Bill of Materials; two tablets of the same model designation may populate different display or touchscreen vendors.
- **clock**: Timing reference signal that gates and clocks an IP block.
- **downstream**: Kernel tree maintained outside upstream Linux, here Samsung / Android.
- **driver probe**: Initialization phase where a driver attempts to bind to a matched device.
- **earlycon**: Early console available before full serial subsystem initialization.
- **FDT/DTB**: Flattened Device Tree binary format.
- **IOMMU/SysMMU**: Manages DMA address translation and peripheral memory isolation.
- **initramfs**: Ephemeral `cpio` root filesystem loaded into memory alongside the kernel.
- **phandle**: Pointer/reference between Device Tree nodes.
- **power domain**: Group of hardware blocks whose power rails are switched in coordination.
- **regulator**: Controllable voltage/current supply rail.
- **reset**: Hardware line that resets an IP block into its initial state.
- **SoC**: System-on-Chip integrating cores, buses, and peripherals onto one die.
- **upstream/mainline**: The canonical Linux kernel maintained by Linus Torvalds and the community.

## Guided Exercises

1. Locate UART0 in the base DTS. Note its register address, IRQ, parent clocks, pinctrl, and status.
2. For the Wi-Fi variant, compare r01 and r04 with `diff -u` (r02 exists only in the 5G reference). Classify each delta as peripheral, electrical parameter, or phandle renumbering.
3. Locate `samsung,exynos-ufs`; inspect its `of_match_table` in downstream and mainline. Diagram what private platform data each implementation consumes.
4. Explain why an exact `synopsys,dwc3` compatible match is insufficient to enable operational USB.
5. List the generated `cpio` contents and trace line-by-line what `/init` executes.
6. Decompress the `/proc/config.gz` extracted from the physical device and compare it against the defconfig:

   ```sh
   gzip -dc reports/device-*/config.gz > /tmp/gts9fe-running.config
   diff -u sources/wifi-kernel/arch/arm64/configs/s5e8835-gts9fewifixx_defconfig \
     /tmp/gts9fe-running.config | less
   ```

7. When you capture a live hardware boot log, construct a hypothesis that explains **the first failure line**, not cascading secondary symptoms, and design an experiment changing only a single variable.
