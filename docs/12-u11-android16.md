# 12. Comparación reproducible U3 ↔ U11 ↔ EZE4

Este capítulo define la puerta de comparación para la entrega OSRC Android 16
ya obtenida. La fuente U11 de SM-X510 es el overlay `X510XXSBDZB4` aplicado
sobre la base `X510XXU8DYJ4`, con kernel 5.15.180. Se mantiene separada de U3
(`X510XXU3BXDG`) y no sustituye el paquete OSRC exacto de `X510XXUCEZE4`.

El kernel observado en el boot stock EZE4 es 5.15.189-android13-3-33478785,
con Clang `r450784d`. Por tanto, los números de kernel, el nivel Android y el
binario de bootloader se registran por separado; que una rama U11 compile no
demuestra que coincida con EZE4.

## Comando host-only

Con el composite U11 completo en ext4, ejecutar desde la raíz o desde el guest:

```sh
./scripts/compare-osrc-trees.sh \
  --u3-dir sources/wifi-kernel \
  --u11-dir /ruta/OSRC-U11-extraido \
  --eze4-dir artifacts/stock/dt \
  --output reports/generated/u11-osrc
```

El comparador sólo lee los dos directorios y los DTS EZE4. No descarga OSRC,
no invoca una VM y no espera que termine un archivo `.part`; los fragmentos
`.part` que aparezcan dentro de un árbol se ignoran. Una ruta dada directamente
como `.part` se rechaza, para evitar confundir un archivo parcial con una fuente
reproducible. El informe actual ya fue generado con el composite exacto y está
en `reports/generated/u11-osrc/`. Consulta el capítulo 14 para interpretarlo.

La salida contiene `comparison.json` (datos completos, hashes SHA-256 y listas
de rutas) y `comparison.md` (resumen auditable). La publicación se hace desde un
directorio temporal y sólo sustituye una salida anterior creada por esta misma
herramienta; un error de lectura, parseo o validación deja la salida anterior
intacta. No se escribe en `sources/` ni en `artifacts/`.

## Qué se compara

El inventario separa cuatro categorías, que pueden solaparse (por ejemplo,
`drivers/foo/Kconfig` pertenece a `drivers` y `configs`):

| Categoría | Ejemplos | Evidencia producida |
|---|---|---|
| `dts` | `*.dts`, `*.dtsi` | rutas U3/U11, añadidas, eliminadas y hashes cambiados |
| `drivers` | cualquier fichero bajo `drivers/` | presencia y contenido por ruta; prioriza ABI y código de dispositivo |
| `configs` | `Kconfig*`, `*_defconfig`, `.config*`, `*.cfg`, `configs/` | diferencias de símbolos y fragmentos que habrá que revisar |
| `build_scripts` | `Makefile`, `Kbuild`, `build*.sh`, `build.config*`, `Android.bp/mk`, `*.mk` | diferencias de reglas, toolchain y empaquetado |

En cada categoría, “cambiado” significa que el SHA-256 del mismo camino
relativo difiere. “Sólo U3/U11” significa que la ruta está ausente en el otro
árbol; no significa automáticamente que un driver sea necesario o seguro.

## Matriz de DTS EZE4

Si `--eze4-dir` contiene los decompilados `.dts`/`.dtsi` que producen
`tools/dtbo_extract.py` o `tools/fdt_scan.py`, el JSON y el Markdown añaden una
fila por DTS EZE4 con:

- candidato U3 y candidato U11, priorizados por cadenas `compatible`, rango
  `dtbo-hw_rev` y tokens de la ruta;
- comparación semántica U3↔U11, U3↔EZE4 y U11↔EZE4 usando
  `tools/dts_semantic_diff.py`;
- estado, número de diferencias materiales, referencias sin resolver y
  renumeraciones de phandle.

Una coincidencia automática ambigua queda como `UNMAPPED` y muestra los cinco
candidatos con mayor puntuación. Para fijar una revisión concreta, usar un JSON
externo (no modificar las fuentes):

```json
[
  {
    "eze4": "overlays/overlay-02-id-00000000-rev-00000000.dts",
    "u3": "arch/arm64/boot/dts/samsung/gts9fewifi/gts9fewifi_eur_open_w00_r04.dts",
    "u11": "arch/arm64/boot/dts/samsung/gts9fewifi/gts9fewifi_eur_open_w00_r04.dts"
  }
]
```

Se pasa con `--dts-map mapa.json`; las rutas U3/U11 son relativas a sus árboles
y la ruta EZE4 coincide con el nombre mostrado por el informe. Un `.dtb`
binario se inventaría, pero no se compara semánticamente sin su DTS decompilado;
el informe lo deja explícito. Un estado `INCONCLUSIVE` o `DIFFERENT
(INCOMPLETE)` nunca se convierte en equivalencia.

## Interpretación y siguiente puerta

La matriz sirve para localizar divergencias antes de portar un parche: DT,
drivers, Kconfig y reglas de build deben revisarse juntos. En particular, la
referencia U11 `X510XXSBDZB4`/`X510XXU8DYJ4` y el kernel stock EZE4
5.15.189 no deben mezclarse por proximidad numérica. Antes de cualquier build
destinado al dispositivo se requiere el checkout OSRC exacto de EZE4, commit o
hash de la entrega, defconfig, toolchain y correspondencia de DT/DTBO anotados.
