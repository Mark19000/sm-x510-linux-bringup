# 0. Seguridad, modelos y regla de no perder Android

## Antes de empezar

Desbloquear el bootloader de una Samsung normalmente borra todos los datos y
puede activar de forma irreversible el estado Knox Warranty Bit. La posibilidad
de desbloqueo depende de la región, el operador y la versión del dispositivo.
Este proyecto no intenta saltarse esas restricciones.

No desbloquees ni flashees todavía. Primero completa el análisis sin escritura:

```sh
./scripts/collect-device.sh
./scripts/extract-stock.sh AP_DE_TU_VERSION.tar.md5
```

El segundo comando opera sobre una copia local del firmware. El primero usa ADB
para leer información; algunas lecturas estarán bloqueadas en un Android de
producción y eso es normal.

## Identidad que debes registrar

La unidad de este proyecto ya está identificada así:

| Campo | Valor |
|---|---|
| Modelo | `SM-X510` |
| Variante | Wi-Fi / `gts9fewifi` |
| Build Android | `BP4A.251205.006` |
| Versión AP/PDA | `X510XXUCEZE4` |
| Sistema | Android 16 / One UI 8.5 |
| Binario de bootloader | `C` = U12 |
| CSC activo | `EUX` |
| Familia multi-CSC | `OXM` |
| Versión CSC | `X510OXMCEZE4` |

En `X510XXUCEZE4`, `X510` identifica la familia del modelo, `XX` la rama
internacional, `U` una actualización funcional y `C` es el contador binario
del bootloader (12). El resto codifica la generación/fecha de la revisión. El
prefijo `BP4A.251205.006` pertenece a la base de Android y no sustituye al
identificador AP de Samsung.

La cadena bruta observada `SAOMC_SM-x510_oxm_eux_16_0001EUX/EUX/` confirma el CSC
activo `EUX`, la familia multi-CSC `OXM` y Android 16. No forma parte del kernel,
pero es necesaria para elegir un firmware completo coherente y una copia de
restauración adecuada.

Guarda en el cuaderno de pruebas:

- modelo completo (`SM-X510...` o `SM-X516...`);
- región/CSC;
- versión de bootloader y número de compilación;
- revisión de hardware si Android la expone;
- hash SHA-256 del paquete AP original;
- salida de `getprop`, `/proc/cmdline` y mapa de particiones.

Se conservan dos bases separadas:

- SM-X510 Wi-Fi: `underdog54/android_kernel_samsung_gts9fewifi`, rama `stock`,
  commit `9a752a83347461b3785711760ba925fcabea3071`, importación `X510XXU3BXDG` y
  kernel 5.15.123;
- SM-X516 5G: `Fede2782/android_kernel_samsung_gts9fe`, commit
  `56f84616c0263aa85ccbbfb77f69af2fe4aa4bb6`, importación `X516BXXU7CYE1` y
  kernel 5.15.153.

Ninguna demuestra por sí sola que coincida con tu firmware instalado. Cuando
exista una fuente OSRC exacta para tu build, se debe comparar y preferir esa
versión.

En este caso ya sabemos que **no coincide**: `X510XXU3BXDG` es U3/Android 14 y
la tablet ejecuta `X510XXUCEZE4`, U12/Android 16. No se debe degradar el
bootloader ni tratar un kernel U3 como imagen de arranque U12.

## Variantes

| Modelo | Conectividad | Riesgo particular |
|---|---|---|
| SM-X510 | Wi-Fi | no debe recibir overlays/configuración de módem |
| SM-X516/B/N | Wi-Fi + 5G | añade módem, memoria reservada e interfaces CP |

`gts9fewifi` y `gts9fe` comparten mucho código, pero no son intercambiables. Una
DT incorrecta puede asignar dos drivers al mismo registro, GPIO o reloj.

## Política de pruebas

1. Mantén el firmware oficial completo y una forma conocida de restaurarlo.
2. Nunca escribas `boot`, `vendor_boot`, `dtbo`, `vbmeta` o `super` sin verificar
   modelo, tamaño de partición y hash.
3. Genera una imagen nueva a partir de la imagen stock; no inventes parámetros de
   cabecera, offsets o AVB.
4. En la primera prueba, no montes UFS en escritura. El initramfs usa `ro`.
5. Cambia una sola variable por intento y guarda el log completo.
6. No pruebes carga/batería con drivers incompletos: usa alimentación estable y
   vigila temperatura fuera del software experimental.

No hay scripts de flasheo en este repositorio. Es deliberado: la transición de
M1 (artefactos construidos) a M2 (primer boot) requiere conocer tu unidad real.
