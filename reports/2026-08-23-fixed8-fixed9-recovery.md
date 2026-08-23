# Recuperación fixed8/fixed9 y demostración de reproducibilidad U11

Fecha: 2026-08-23 · Alcance: sólo laboratorio offline, sin escritura física.

## Resultado final

`fixed8` y `fixed9` terminaron con `status=0`. La comparación con `tools/u11_repro_compare.py` produce **PASS**: los 19 ficheros del dist, incluyendo Image, DTB, DTBOs y el tar de 282 módulos, son **idénticos byte a byte** entre dos árboles limpios independientes.

Este resultado confirma que el parche 0011 (build IDs reproducibles) resuelve la única divergencia que impedía el PASS en `fixed6/fixed7`.

## Fallos encontrados durante la recuperación

Cada fallo se documenta con: qué ocurrió, por qué ocurrió, cómo se detectó, cómo se solucionó y qué conocimiento aporta.

### 1. Espacio insuficiente en disco (causa raíz de los fallos originales)

- **Qué ocurrió:** `fixed8` y `fixed9` fallaron con `Errno 28 No space left on device`.
- **Por qué:** La VM Lima tenía 33 GB llenos al 98% (852 MB libres). Cada build genera ~6 GB entre fuentes extraídas, objetos intermedios y dist.
- **Cómo se detectó:** `df -h /` mostró 852 MB libres; los STATUS de ambos runs mostraban `status=1`.
- **Solución:** Se liberaron ~17 GB eliminando únicamente directorios regenerables dentro de `~/osrc-u11-work`: runs fallidos (`fixed8/fixed9` previos), subdirectorios voluminosos de `fixed7` (cuyo dist completo ya estaba copiado al host) y staging-only de `inspect4`. No se tocaron `artifacts/`, `sources/` ni `configs/` del host.
- **Conocimiento:** Un build kernel LTO/BTF necesita mínimo ~8 GB libres en el guest. Antes de cada run, verificar `df -h` es tan crítico como verificar hashes de receta.

### 2. Estructura incorrecta del árbol fuente (tar sin subdirectorio Kernel/)

- **Qué ocurrió:** El primer intento manual asumió que el tar extraía a un subdirectorio `Kernel/`, pero lo hizo directamente en `build-source/`.
- **Por qué:** El tar de Samsung no tiene un directorio raíz explícito.
- **Cómo se detectó:** `test -f Makefile` falló; `git apply --check` reportó archivos inexistentes.
- **Solución:** Extraer directamente en `build-source/` y aplicar el overlay ahí, no en un subdirectorio inexistente.
- **Conocimiento:** Siempre verificar la estructura real post-extracción antes de asumir rutas.

### 3. Guardia `OUT ya existe`

- **Qué ocurrió:** Reintentar el build sin limpiar `out-u11` provocó rechazo inmediato.
- **Por qué:** El script exige un run nuevo para evitar mezclar artefactos obsoletos.
- **Cómo se detectó:** Mensaje `OUT ya existe; cada build U11 requiere un run nuevo`.
- **Solución:** Eliminar `out-u11`, revertir patches aplicados (`git apply -R`) y relanzar.
- **Conocimiento:** Las guardias anti-reutilización son intencionales; nunca forzar su bypass.

### 4. Guardia `modules-stage ya existe`

- **Qué ocurrió:** Tras un intento parcial, el re-run falló porque `build-output/modules-stage` ya existía.
- **Por qué:** Misma política anti-mezcla que OUT/DIST.
- **Cómo se detectó:** Mensaje `modules-stage ya existe`.
- **Solución:** Eliminar el directorio antes de reintentar.
- **Conocimiento:** Cada intento debe partir de cero en todos los outputs, no sólo en uno.

### 5. Rutas físicas en módulos (guardia de reproducibilidad)

- **Qué ocurrió:** El primer build exitoso compilación-wise fue rechazado por contener rutas absolutas en `.rodata` de módulos.
- **Por qué:** Usé `--out build-output` (hermano del source) en lugar de `out-u11` (hijo directo del source), causando que ThinLTO registrara la ruta absoluta del guest.
- **Cómo se detectó:** `grep -a -F "$RUN_ROOT" ems.ko` encontró 7 coincidencias.
- **Solución:** Cambiar `--out` a `$RUN/build-source/out-u11` para que Kbuild use `srctree=..` y las flags `-fdebug-prefix-map` normalicen correctamente.
- **Conocimiento:** La posición de `O=` respecto al source tree determina si Kbuild pasa rutas relativas o absolutas a Clang. Es una restricción estructural de ThinLTO, no un bug.

## Procedimiento correcto documentado

Para futuros builds manuales fuera del wrapper:

1. Extraer Kernel.tar.gz directamente en `RUN/build-source/` (sin subdirectorio).
2. Aplicar overlay X510XXSBDZB4 sobre ese mismo nivel.
3. Verificar `git apply --check patches/*.patch`.
4. Invocar `build-u11-kernel-guest.sh` con `--run-root RUN --kernel RUN/build-source --out RUN/build-source/out-u11 --dist RUN/dist`.
5. Nunca precrear `out-u11` ni `build-output/modules-stage`; el script los crea él mismo.
6. Si un intento parcial falla: revertir patches (`git apply -R`), eliminar `out-u11`, `dist` y `modules-stage`, luego relanzar.

## Evidencia generada

| Artefacto | Ubicación |
|---|---|
| Dist fixed8 | `artifacts/u11/x510xxsbdzb4-u11-fixed8-20260823/dist/` |
| Dist fixed9 | `artifacts/u11/x510xxsbdzb4-u11-fixed9-20260823/dist/` |
| STATUS fixed8 | `artifacts/u11/x510xxsbdzb4-u11-fixed8-20260823/STATUS` |
| STATUS fixed9 | `artifacts/u11/x510xxsbdzb4-u11-fixed9-20260823/STATUS` |
| Log build fixed8 | `artifacts/u11/x510xxsbdzb4-u11-fixed8-20260823/u11-build.log` |
| Log build fixed9 | `artifacts/u11/x510xxsbdzb4-u11-fixed9-20260823/u11-build.log` |
| Informe reproducibilidad | `reports/generated/u11-repro/reproducibility.md` |
| JSON reproducibilidad | `reports/generated/u11-repro/reproducibility.json` |

Veredicto operativo: **NO-GO físico**. Escritura en hardware sigue bloqueada.
