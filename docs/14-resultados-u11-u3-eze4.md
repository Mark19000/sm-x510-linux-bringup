# 14. Resultado U3 → U11 → EZE4 y decisión para M2/M3

Este capítulo es el corte auditable del 23 de agosto de 2026. Se analizaron
los paquetes descargados, se compuso el source U11 en ext4, se comparó con U3
y con los árboles de dispositivo extraídos de EZE4, y se compiló un kernel U11
completo. No se escribió nada en la tableta y U3 sigue siendo la fuente
canónica del pipeline existente.

## Inventario exacto de entregas

Se ignoraron `.part`, ficheros vacíos y placeholders. Los tres ZIP completos
relacionados con SM-X510 encontrados en `Downloads` fueron:

| fichero | bytes | SHA-256 | identidad |
|---|---:|---|---|
| `SM-X510.zip` | 285055969 | `3320da592f76b703531eee8c04ef9d872f7254cd906127dd2feda79c310e9928` | wrapper OSRC Android 16 |
| `SM-X510_EUR_16_Opensource.zip` | 284751324 | `18596f241925b729f48638a1750d3d71e3370d9056b2c9c4373a7cc04c1d9791` | base OSRC; copia idéntica a la incluida en el wrapper |
| `SAMFW.COM_SM-X510_EUX_X510XXUCEZE4_fac.zip` | 10717872605 | `45a450875ce753e74d8183aa085837ada91cabe2832d9725a1567aa29b01d375` | firmware stock EZE4, Android 16, U12/EUX |

El wrapper contiene además estas dos entregas independientes:

| miembro | bytes | SHA-256 | función |
|---|---:|---|---|
| `SM-X510_EUR_16_Opensource.zip` | 284751324 | `18596f241925b729f48638a1750d3d71e3370d9056b2c9c4373a7cc04c1d9791` | base `X510XXU8DYJ4` |
| `SM-X510_EUR_16_Opensource_X510XXSBDZB4.zip` | 237796 | `c0e3fb5bdbd6447669dd57e43d9817838c24ce0f08e6f0293f3cc98e1cefc5ad` | suplemento exacto `X510XXSBDZB4` |

La base contiene `Kernel.tar.gz` (254699729 bytes, SHA-256
`064746422c2c1ba83f3c245e137f6c0a105a19280d10ece48987cac5e9d26983`)
y `Platform.tar.gz` (37445621 bytes, SHA-256
`68929260cd0f996dc59121186ea4c87fe6ca762e849c661dce2eacfd3184d567`).
El tar del kernel tiene 80777 ficheros regulares y 39 symlinks internos seguros;
el de Platform, 13275 ficheros regulares. Platform no participa en el build
del kernel.

## Por qué sí es el corresponding source U11

La identificación no depende del nombre externo:

1. El README del suplemento dice expresamente descargar primero
   `X510XXU8DYJ4` y actualizarlo después con `X510XXSBDZB4`.
2. La raíz interna se llama `SM-X510_EUR_16_XX_X510XXSBDZB4/Kernel`.
3. El README de Platform declara Android 16.0.
4. El Makefile compuesto declara Linux 5.15.180.
5. La receta selecciona `s5e8835-gts9fewifixx_defconfig`, `TARGET_SOC=s5e8835`,
   `PLATFORM_VERSION=13`, `LLVM=1` y Clang `r450784d`.
6. `B` en `X510XXSBDZB4` es la revisión binaria U11.

El suplemento contiene 13 ficheros de kernel; tres DTSI de batería son
idénticos a la base y diez cambian realmente. Sus cambios se concentran en
defconfig, HID/accesorios, restricciones USB, F2FS, integridad de `/proc` y
limpieza DDAR. No incluye DTS/DTSI de placa o SoC: esos provienen de la base U8,
un detalle importante al atribuir la proximidad de DT a “U11”.

Por tanto, **sí tenemos el source correspondiente a X510XXSBDZB4/U11/Android
16**, compuesto como base U8 más suplemento U11. Samsung no incluyó `.git`,
un hash de commit ni una etiqueta upstream; ese dato es realmente no disponible
y no debe inventarse.

En APFS no se extrae el kernel completo porque el tar tiene nombres que
colisionan en un filesystem no sensible a mayúsculas. La copia íntegra vive en
ext4 en la VM. En el host sólo se guardan paquetes, manifiestos e informes bajo
`sources/osrc-releases/x510xxsbdzb4-u11-android16` y `artifacts/u11`; U3,
`sources/wifi-kernel` y `artifacts/stock` permanecen intactos.

## Distancia de kernel y configuración

| etapa | kernel | base/commit demostrable | Android / binario |
|---|---|---|---|
| U3 `X510XXU3BXDG` | 5.15.123 | commit `9a752a83347461b3785711760ba925fcabea3071` | Android 14 / U3 |
| U11 `X510XXSBDZB4` | 5.15.180 | archivo OSRC sin Git; base de entrega `X510XXU8DYJ4` | Android 16 / U11 |
| stock `X510XXUCEZE4` | 5.15.189-android13-3-33478785 | cadena Kbuild stock; source exacto solicitado y pendiente | Android 16 / U12 |

U11 reduce el salto conocido de 66 revisiones de kernel a sólo 9. Entre los
cambios de defconfig U3→U11 destacan SCMI virtio, RCU lazy, una mitigación
ARM64 adicional, CUBIC en lugar de BIC, NTFS3, el shim ashmem/memfd, HDM como
módulo y el cambio de firmware SCSC de `/vendor/etc/wifi` a
`/vendor/firmware/wifi`. `PABLO_OBTE_SUPPORT` pasa de módulo a desactivado.

El defconfig U11 de Samsung continúa sin `CONFIG_FHANDLE`, devtmpfs, VT y los
ACL/xattrs de tmpfs que necesita nuestro early userspace. El parche 0001 sigue
siendo necesario para M3. El config final contiene 312 símbolos `=m`; se
construyeron e instalaron 282 `.ko`, igual que en el ensayo U3, aunque la
composición no es idéntica (`PABLO_OBTE_SUPPORT` desaparece, entre otros cambios).

## DTS/DTSI y drivers

El inventario bruto cuenta 3200 DTS/DTSI en U3 y 3217 en U11; 228 rutas cambian.
En drivers hay 37094 rutas en U3 y 37155 en U11: 3721 cambian, 18 sólo existen
en U3 y 79 sólo en U11. Son métricas de rutas, no 3721 incompatibilidades de la
tablet. El desglose reproducible por subsistema está en
`reports/generated/u11-osrc/subsystems.md`.

| subsistema | rutas cambiadas | sólo U3 | sólo U11 |
|---|---:|---:|---:|
| DT S5E8835/X510 | 3 | 0 | 0 |
| PSCI/GIC/timers | 28 | 0 | 0 |
| CMU/clocks | 1 | 0 | 0 |
| pinctrl/GPIO/EINT | 31 | 0 | 0 |
| PMU/ACPM/power domains | 0 | 0 | 0 |
| SysMMU/IOMMU | 0 | 0 | 0 |
| UFS/PHY/FMP | 12 | 0 | 0 |
| USB/DWC3/Type-C | 164 | 1 | 0 |
| display/DSIM/panel | 43 | 0 | 1 |
| touchscreen/Wacom/pogo | 14 | 0 | 0 |
| GPU/Mali | 11 | 0 | 0 |
| Wi-Fi/BT SCSC | 45 | 0 | 0 |
| batería/PMIC/carga | 29 | 0 | 0 |
| thermal | 0 | 0 | 0 |
| build/toolchain | 7 | 0 | 0 |

Estas cifras clasifican rutas por nombre y presencia. Por ejemplo, “164 USB”
incluye backports generales bajo `drivers/usb`; no significa que existan 164
cambios específicos del controlador USB de la tablet.

Los cambios materiales U3→U11 del DT base que más importan al arranque son:

- una reserva `wdtmsg` en `0x08adb11000`, tamaño `0x1000`;
- banco GPIO/EINT `gph1` y sus interrupciones 0x4f–0x52;
- `snps,usb2-lpm-disable` en DWC3;
- `dsim,disable-shdw-vss-updt = <1>` en DSIM;
- reloj y `clock-names = "gpu_clock"` en Mali.

En el overlay r04 hay 17 diferencias semánticas materiales: nuevos teclados y
touchpad, pinning/preload de IMX355, nombres de zonas térmicas, política
`pktproc` y capacidad de batería 10090→8000. Son periféricos y política de
producto; no parecen por sí solos bloqueadores del primer mensaje del kernel.

Para PSCI/GIC/timers, CMU, pinctrl, UFS/PHY/FMP, USB/Type-C, display/panel,
entrada/Wacom, GPU, SCSC, batería/PMIC/carga y thermal, el informe separa rutas
modificadas y permite auditarlas sin confundir un backport general de Linux con
un cambio específico de X510. No aparecieron cambios de ruta bajo los patrones
específicos de PMU/ACPM/power domains, SysMMU/IOMMU ni thermal; eso no demuestra
identidad interna de todos sus includes.

## Qué parte de U3→EZE4 ya estaba en U11

La correspondencia stock es r00→overlay-00, r01→overlay-01 y r04→overlay-02.
La comparación semántica r04 U11→EZE4 encuentra **cero diferencias materiales**
en 1215 nodos, pero quedan 207 referencias externas sin resolver: su estado
correcto es `INCONCLUSIVE`, no “idéntico”. En el DT base U11→EZE4 ambos tienen
1493 nodos. Comparar sólo el DTS fuente mostraba una diferencia (`/mfc
debug_mode`, de 1 a 0), pero era insuficiente: al comparar los **DTB ya
compilados** aparecen cuatro y quedan 14 referencias sin resolver:

- dos string-lists `cpus` de `/ems/pe-list` se codifican de manera distinta;
- `/mfc debug_mode` cambia de 1 a 0;
- `cpu_table_rps` de SCSC cambia de dos strings a cuatro.

Los escapes octales del DTS Samsung explican por qué el diff del source no veía
los tres cambios de strings. La receta reproducible es `make u11-dtb-audit` y
la evidencia vive en `reports/generated/u11-dtb-binary/`.

Conclusión limitada pero útil: todos los cambios materiales que veíamos en el
overlay U3→EZE4 ya están en U11, y el DT base U11 sigue muy cerca del binario
EZE4. Las cuatro diferencias compiladas afectan EMS, MFC y SCSC y no forman el
camino mínimo hacia `/init`, pero pueden importar después del arranque. Las
renumeraciones masivas de phandle U3→U11 no son por sí mismas cambios de
hardware. No podemos concluir equivalencia completa hasta resolver referencias
o recibir el source EZE4 exacto.

## Compilación y errores provocados

Se aplicaron por separado los nueve parches actuales al composite U11. Los nueve
aplican textualmente. El build limpio con Clang 21 descubrió primero dos errores
de declaraciones en scheduler EMS y KVM, cubiertos por 0002. Después se retiró
cada parche relevante y se recompiló la unidad afectada:

| sin parche | fallo reproducido en U11 + Clang 21 |
|---|---|
| 0002 | implicit-int en EMS y puntero `clidr` sin inicializar en KVM |
| 0003 | implicit-int en `exynos-devfreq.h` |
| 0004 | nombre sin inicializar en exynos-cpupm |
| 0005 | implicit-int en QoS Mali |
| 0006 | buffer sin inicializar en exynos-devfreq |
| 0008 | valor sin inicializar en cargador y FPSIMD prohibido en `sec_debug_test` |
| 0009 | conversión de enum inválida a `irqreturn_t` |
| 0010 | comparación entre enums distintos en Type-C |

0001 se justificó por el defconfig, no por un error del compilador. Con los nueve
parches, `Image`, DTB, r00/r01/r04, LTO/BTF, módulos y `modules_install`
terminaron con código 0 en 58:08, usando como máximo 6661420 KiB. La build usó
Clang 21.1.8 ARM64 porque el binario oficial r450784d es x86-64 y no corre de
forma nativa en esta VM ARM64. Es una prueba fuerte de compilabilidad, no una
reproducción binaria de Samsung.

Quedan diagnósticos no fatales que conviene no ocultar: cinco warnings de LLD
por frames de pila grandes en nanohub/sec_debug y mensajes de kperfmon porque el
árbol OSRC aislado no trae `aprotoc` de la plataforma Android; su regla genera
el sustituto dummy y el build continúa. No hubo líneas `error:` en el build
completo parcheado.

Los binarios y logs están en
`artifacts/u11/x510xxsbdzb4-u11-clang21-20260823`. Dos enlaces LTO sucesivos
produjeron `Image` con distinto SHA-256, aunque DTB y DTBO permanecieron
estables; falta fijar la causa de no-reproducibilidad antes de exigir hashes
binarios idénticos.

## Plan de migración U3→U11

U11 es claramente una base de ingeniería superior, pero no se convierte aún en
canónica. La migración debe hacerse como una variante nueva:

1. Mantener U3, el composite U11, el stock U12 y el futuro source EZE4 en cuatro
   rutas y namespaces de artefactos distintos.
2. Reaplicar los nueve parches. Ninguno desaparece en el pipeline Clang 21;
   0001 es funcional y 0008 también reduce superficie de crash. Reescribir la
   descripción “Android 14” de 0002 y revisar los parches de compatibilidad con
   r450784d antes de declararlos universales.
3. Reutilizar sin cambios la extracción segura, Lima, inventarios, análisis DT,
   constructor DTBO e initramfs. Adaptar `build-downstream.sh` para aceptar
   procedencia de archivo sin commit Git y para publicar sólo bajo `u11/`; hoy
   está deliberadamente anclado a U3/EZE4 y debe seguir bloqueando.
4. Comparar el orden de módulos de `vendor_boot`, firmware SCSC y dependencias
   del initramfs antes de empaquetar; no mezclar módulos U3 con kernel U11.
5. Cuando llegue OSRC EZE4, repetir composición, diff semántico, config, build y
   pruebas negativas; no aplicar el overlay U11 encima de EZE4.

## Efecto sobre M2 y M3

Para **M2, primer mensaje del kernel**, la confianza técnica sube de baja a
moderada-alta: tenemos una base Android 16 compilable, sólo nueve revisiones por
debajo de stock y un DT casi coincidente en lo observable. No sube a “listo para
flashear”: aún faltan fuente EZE4 exacta, ruta de consola observable, revisión
física elegida, desbloqueo/AVB y comprobación anti-rollback.

Para **M3, `/init` como PID 1**, la confianza sube a moderada. El kernel U11
parcheado tiene initrd/devtmpfs/VT/FHANDLE/tmpfs y nuestro initramfs ya es
reproducible. Siguen dependiendo de M2, del layout y tamaño final de boot,
DTBO correcto, AVB y del conjunto/orden de módulos y firmware. La conclusión
es que U11 elimina gran parte de la incertidumbre de source/DT; no elimina la
incertidumbre del contrato de arranque del dispositivo.

Por tanto, el siguiente paso sigue siendo offline: integrar U11 como variante
no canónica y esperar la respuesta OSRC EZE4. No se desmonta, no se flashea y no
se hace downgrade U12→U11.
