# 8. Glosario y ejercicios

## Glosario corto

- **ABI/KMI**: contrato binario entre kernel y módulos.
- **ACPM**: microcontrolador/firmware Samsung que participa en energía y clocks.
- **AVB**: Android Verified Boot, cadena de integridad de imágenes.
- **binding DT**: contrato que define propiedades válidas para un dispositivo.
- **BOM**: lista de componentes; dos tablets del mismo modelo pueden montar
  proveedores de panel distintos.
- **clock**: señal temporal que habilita y marca la frecuencia de un bloque.
- **downstream**: árbol mantenido fuera de Linux upstream, aquí Samsung/Android.
- **driver probe**: momento en que un driver intenta enlazarse con un dispositivo.
- **earlycon**: consola disponible muy pronto, antes del driver serie completo.
- **FDT/DTB**: representación binaria de Device Tree.
- **IOMMU/SysMMU**: traduce direcciones DMA y aísla periféricos.
- **initramfs**: filesystem `cpio` temporal cargado junto al kernel.
- **phandle**: referencia entre nodos de Device Tree.
- **power domain**: conjunto de hardware que se enciende/apaga coordinadamente.
- **regulator**: fuente de tensión controlable.
- **reset**: línea que coloca un bloque hardware en estado inicial.
- **SoC**: sistema completo integrado en un chip.
- **upstream/mainline**: kernel Linux mantenido por la comunidad principal.

## Ejercicios guiados

1. Busca UART0 en el DTS base. Anota dirección, IRQ, clocks, pinctrl y estado.
2. En Wi-Fi compara r01 y r04 con `diff -u` (r02 sólo existe en la referencia
   5G). Clasifica cada cambio como periférico, parámetro eléctrico o simple
   renumeración de phandle.
3. Elige `samsung,exynos-ufs`; encuentra su `of_match_table` downstream y
   mainline. Dibuja qué datos privados consume cada implementación.
4. Explica por qué `synopsys,dwc3` exacto no basta para que funcione el USB.
5. Lista el `cpio` generado y sigue, línea por línea, qué hace `/init`.
6. Descomprime el `/proc/config.gz` del dispositivo y compáralo con el defconfig:

   ```sh
   gzip -dc reports/device-*/config.gz > /tmp/gts9fe-running.config
   diff -u sources/wifi-kernel/arch/arm64/configs/s5e8835-gts9fewifixx_defconfig \
     /tmp/gts9fe-running.config | less
   ```

7. Cuando tengas un log real, construye una hipótesis que explique **la primera
   línea de error**, no las consecuencias posteriores, y diseña una prueba que
   cambie una sola variable.
