# DTS semantic diff

This is a conservative path/property comparison. It ignores label spelling,
canonicalises NUL-separated strings, and maps a phandle only when its local
definition or an explicit peer reference proves the target path. An
`INCONCLUSIVE`/`INCOMPLETE` result is not an equivalence claim.

- Left: `<project-root>/reports/generated/u11-dtb-binary/u11-compiled.dts`
- Right: `<project-root>/reports/generated/u11-dtb-binary/eze4-stock.dts`
- Status: **DIFFERENT (INCOMPLETE)**
- Nodes: 1493 left / 1493 right
- Material differences: 4
- Phandle renumberings ignored by path: 0
- Unresolved references: 14

## Differences by path

| kind | path | property | left | right |
|---|---|---|---|---|
| `property-changed` | `/ems/pe-list/list@0` | `cpus` | `[["bytes",["30","2d","33","04","2d","37","00"]]]` | `[["strings",["0-3","4-7"]]]` |
| `property-changed` | `/ems/pe-list/list@1` | `cpus` | `[["strings",["4-7","-3"]]]` | `[["strings",["4-7","0-3"]]]` |
| `property-changed` | `/mfc` | `debug_mode` | `[["cells",[["number",1]]]]` | `[["cells",[["number",0]]]]` |
| `property-changed` | `/scsc_wifibt@11B40000` | `cpu_table_rps` | `[["strings",["00","  "]]]` | `[["strings",["00","00","40","40"]]]` |

## Unresolved/incomplete evidence

The following references were not resolved to a local node; therefore the result cannot be called equivalent:

- `<project-root>/reports/generated/u11-dtb-binary/eze4-stock.dts: unresolved &camera_rmem in memory-region`
- `<project-root>/reports/generated/u11-dtb-binary/eze4-stock.dts: unresolved &sysmmu_brp_s0 in iommus`
- `<project-root>/reports/generated/u11-dtb-binary/eze4-stock.dts: unresolved &sysmmu_csis_s0 in iommus`
- `<project-root>/reports/generated/u11-dtb-binary/eze4-stock.dts: unresolved &sysmmu_cstat_s0 in iommus`
- `<project-root>/reports/generated/u11-dtb-binary/eze4-stock.dts: unresolved &sysmmu_rgbp_s0 in iommus`
- `<project-root>/reports/generated/u11-dtb-binary/eze4-stock.dts: unresolved &sysmmu_yuvp_s0 in iommus`
- `<project-root>/reports/generated/u11-dtb-binary/eze4-stock.dts: unresolved &wlbt_hw_ver in wlbt_hcf`
- `<project-root>/reports/generated/u11-dtb-binary/u11-compiled.dts: unresolved &camera_rmem in memory-region`
- `<project-root>/reports/generated/u11-dtb-binary/u11-compiled.dts: unresolved &sysmmu_brp_s0 in iommus`
- `<project-root>/reports/generated/u11-dtb-binary/u11-compiled.dts: unresolved &sysmmu_csis_s0 in iommus`
- `<project-root>/reports/generated/u11-dtb-binary/u11-compiled.dts: unresolved &sysmmu_cstat_s0 in iommus`
- `<project-root>/reports/generated/u11-dtb-binary/u11-compiled.dts: unresolved &sysmmu_rgbp_s0 in iommus`
- `<project-root>/reports/generated/u11-dtb-binary/u11-compiled.dts: unresolved &sysmmu_yuvp_s0 in iommus`
- `<project-root>/reports/generated/u11-dtb-binary/u11-compiled.dts: unresolved &wlbt_hw_ver in wlbt_hcf`
