# Informe de Cierre de Fase 3B: P0 Fingerprint Quality, Collision Analysis y Validación Offline

- **Dispositivo**: Samsung Galaxy Tab S9 FE Wi-Fi (`SM-X510` / `gts9fewifi`)
- **SoC**: Samsung Exynos 1380 (`s5e8835`)
- **Firmware Base Objetivo**: `X510XXUCEZE4` (Kernel Linux 5.15.189-android13-3-33478785)
- **Firmware de Referencia**: `X510XXSEEZG3` (Kernel Linux 5.15.189-android13-3-33478785)
- **Fecha**: 2026-09-06
- **Estado de Fase 3B**: **COMPLETADA**
- **Ámbito**: Exclusivamente auditoría estática, análisis combinatorio y validación de datos offline.

---

## 1. Resumen Ejecutivo de la Fase 3B

En esta fase se ha sometido la tabla de huellas KASLR del oráculo P0 a una rigurosa batería de pruebas combinatorias, de entropía posicional, simulación de degradación ante palabras corruptas y comparación binaria contra la compilación previa ZG3.

Resultados esenciales:
1. **Auditoría de Rederivación Binaria**: Se rederivó directamente desde `artifacts/stock/images/Image.stock` (SHA-256: `ca56baf428a3f334d90f5d366f02e6cb36cf70fec23a2055b4f80c29cbe6ede9`) cada uno de los 1,000 QWORDs (125 candidatos $\times$ 8 posiciones). El resultado es **`EXACT_MATCH`** (100% de coherencia).
2. **Matriz de Similitud 125 $\times$ 125**: El 96.80% de los candidatos (121/125 slides) alcanza la categoría máxima **`PASS_STRONG`** con un margen de separación $\ge 5$ palabras respecto al competidor más cercano.
3. **Identificación de la Zona de Colisión**: Las únicas 4 entradas que no alcanzaron `PASS_STRONG` corresponden a los slides de la cola superior:
   - `FAIL_SLIDES`: `0x1e4000`, `0x1e8000`, `0x1ec000` ($\text{margin} = 0$, `best_other_score = 8`).
   - `BORDERLINE_SLIDES`: `0x1f0000` ($\text{margin} = 1$, `best_other_score = 7`).
   Estas 4 entradas mapean físicamente a los desplazamientos de cabecera `0x00c000`, `0x008000`, `0x004000` y `0x000000` del binario `Image`, que contienen secuencias de padding de instrucciones `nop` (`0xd503201fd503201f`) del kernel ARM64. Esta propiedad es idéntica en la tabla de referencia ZG3.
4. **Simulación de Errores (11,500 Casos Evaluados)**:
   - **0 misidentificaciones** (0.00%): Ni un solo patrón corrupto produjo una selección de slide errónea.
   - En los 121 slides de código (`0x000000` a `0x1e0000`), la tasa de identificación correcta es del **100.00%** ante 1, 2 e incluso 3 QWORDs corruptos.
   - En las 4 posiciones de relleno NOP, el algoritmo activa un **rechazo seguro** (`SAFE_REJECTION`) por empate de candidatos o margen insuficiente, impidiendo fallos catastróficos.
5. **Equivalencia de Generadores**: Se verificó la equivalencia numérica y estructural del script Perl original (`tools/generate_p0_fingerprint.pl`) contra la tabla EZE4: **`ALGORITHM_EQUIVALENT`**.
6. **Comparación ZG3 vs EZE4**: 106 de 125 filas (84.80%) y 978 de 1,000 QWORDs (97.80%) son exactamente idénticos, confirmando una alta estabilidad binaria entre builds.

---

## 2. Auditoría y Rederivación de la Tabla EZE4

Se verificaron las propiedades geométricas y binarias de `docs/rmg-eze4/eze4_p0_fingerprint_table.csv` frente al binario stock:
- **Número de filas**: Exactamente 125.
- **Rango de slides**: `0x000000` a `0x1f0000` (desplazamientos de sondeo: `0x1f0000` a `0x000000`).
- **Paso KASLR**: `0x4000` (16 KB) constante.
- **Offsets intrapágina**: `0x000, 0x200, 0x400, 0x600, 0x800, 0xa00, 0xc00, 0xe00`.
- **Endianness**: Little-endian (`<Q`, 64 bits sin signo).
- **Límites de acceso**: Máximo offset leído en imagen: $\text{0x1f0000} + \text{0xe00} + 8 = \text{0x1f0e08}$ (2,035,208 bytes), muy por debajo del tamaño de `Image.stock` (39,356,928 bytes).

**Veredicto de Auditoría**: **`EXACT_MATCH`** (125/125 filas, 1000/1000 QWORDs validados).

---

## 3. Matriz Completa de Similitud y Discriminación

Se generó [**`docs/rmg-eze4/p0_similarity_matrix.csv`**](file:///Users/markpi/tab-s9-fe-linux/docs/rmg-eze4/p0_similarity_matrix.csv) ($125 \times 125$) y [**`docs/rmg-eze4/p0_discrimination_report.csv`**](file:///Users/markpi/tab-s9-fe-linux/docs/rmg-eze4/p0_discrimination_report.csv).

### 3.1 Distribución de Veredictos de Discriminación
| Veredicto | Criterio | Filas | Porcentaje |
| :--- | :--- | :---: | :---: |
| **PASS_STRONG** | $\text{margin} \ge 5$ | 121 | 96.80% |
| **PASS** | $3 \le \text{margin} < 5$ | 0 | 0.00% |
| **BORDERLINE** | $0 < \text{margin} < 3$ | 1 | 0.80% |
| **FAIL** | $\text{margin} \le 0$ (empate o superado) | 3 | 2.40% |
| **Total** | | **125** | **100.00%** |

### 3.2 Análisis de las Excepciones de Discriminación
- **`0x1e4000` (FAIL)**: $\text{Image\_offset} = \text{0x00c000}$. 8 palabras `0xd503201fd503201f` (`nop; nop`). Empata con `0x1e8000` y `0x1ec000` con score 8 ($\text{margin} = 0$).
- **`0x1e8000` (FAIL)**: $\text{Image\_offset} = \text{0x008000}$. 8 palabras `0xd503201fd503201f`. Empata con `0x1e4000` y `0x1ec000` con score 8 ($\text{margin} = 0$).
- **`0x1ec000` (FAIL)**: $\text{Image\_offset} = \text{0x004000}$. 8 palabras `0xd503201fd503201f`. Empata con `0x1e4000` y `0x1e8000` con score 8 ($\text{margin} = 0$).
- **`0x1f0000` (BORDERLINE)**: $\text{Image\_offset} = \text{0x000000}$. Contiene 1 instrucción de salto ARM64 (`0x1487bffffa405a4d`) y 7 `nop`. Su score frente a los slides de padding es 7 ($\text{margin} = 8 - 7 = 1 < 3$).

---

## 4. Análisis de Colisiones Posicionales y Entropía

Se generó [**`docs/rmg-eze4/p0_word_entropy.csv`**](file:///Users/markpi/tab-s9-fe-linux/docs/rmg-eze4/p0_word_entropy.csv).

| Índice | Offset Intrapágina | Valores Únicos (de 125) | Grupo Máx. Colisión | Recuento Ceros | Valores Repetidos | Entropía Shannon (bits) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 0 | `0x000` | 121 | 3 (`0x1e4000-1ec000`) | 0 (0.0%) | 7 (5.6%) | 6.896 |
| 1 | `0x200` | 121 | 4 (`0x1e4000-1f0000`) | 0 (0.0%) | 6 (4.8%) | 6.886 |
| 2 | `0x400` | 120 | 4 (`0x1e4000-1f0000`) | 1 (0.8%) | 8 (6.4%) | 6.870 |
| 3 | `0x600` | 118 | 4 (`0x1e4000-1f0000`) | 2 (1.6%) | 12 (9.6%) | 6.838 |
| 4 | `0x800` | 119 | 4 (`0x1e4000-1f0000`) | 0 (0.0%) | 10 (8.0%) | 6.854 |
| 5 | `0xa00` | 121 | 4 (`0x1e4000-1f0000`) | 0 (0.0%) | 6 (4.8%) | 6.886 |
| 6 | `0xc00` | 122 | 4 (`0x1e4000-1f0000`) | 0 (0.0%) | 4 (3.2%) | 6.902 |
| 7 | `0xe00` | 120 | 4 (`0x1e4000-1f0000`) | 0 (0.0%) | 8 (6.4%) | 6.870 |

*Nota metodológica*: La entropía de Shannon observada oscila entre **6.838 y 6.902 bits** por posición (el máximo teórico para 125 elementos es $\log_2(125) \approx 6.966$ bits). Esto evidencia una dispersión posicional casi óptima a lo largo del kernel `.text`.

---

## 5. Robustez ante Muestras Corruptas (Simulación Combinatoria)

Se generó [**`docs/rmg-eze4/p0_error_tolerance.csv`**](file:///Users/markpi/tab-s9-fe-linux/docs/rmg-eze4/p0_error_tolerance.csv) evaluando $125 \times (8 + 28 + 56) = 11,500$ combinaciones de corrupción:

| Nivel de Error | Patrones Totales | Aceptados (Correctos) | Rechazados de Forma Segura | Misidentificaciones | Tasa de Aceptación |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **1 QWORD Erróneo** | 1,000 | 968 | 32 | **0** (0.00%) | **96.80%** |
| **2 QWORDs Erróneos** | 3,500 | 3,388 | 112 | **0** (0.00%) | **96.80%** |
| **3 QWORDs Erróneos** | 7,000 | 6,776 | 224 | **0** (0.00%) | **96.80%** |
| **Total Global** | **11,500** | **11,132** | **368** | **0** (0.00%) | **96.80%** |

### Conclusiones Críticas de Seguridad:
1. **Cero Falsos Positivos**: El oráculo **nunca confunde un slide con otro**, incluso ante un 37.5% de datos destruidos (3 de 8 palabras).
2. **Rechazos Seguros**: Los 368 casos rechazados corresponden exclusivamente a las 4 posiciones de padding NOP (`0x1e4000`, `0x1e8000`, `0x1ec000`, `0x1f0000`), donde el runtime aborta limpiamente retornando `-1` para reintentar la lectura sin provocar pánico de kernel.

---

## 6. Comparación Cruzada: EZE4 vs ZG3 Reference Table

Se generó [**`docs/rmg-eze4/zg3_eze4_p0_diff.csv`**](file:///Users/markpi/tab-s9-fe-linux/docs/rmg-eze4/zg3_eze4_p0_diff.csv) comparando los 1,000 QWORDs:
- **Filas 8/8 idénticas**: **106 / 125 (84.80%)**
- **Filas con diferencias**: **19 / 125 (15.20%)**
- **QWORDs totales idénticos**: **978 / 1,000 (97.80%)**
- **QWORDs diferentes**: **22 / 1,000 (2.20%)**
- **Distribución de diferencias**: Pos 0: 2, Pos 1: 6, Pos 2: 4, Pos 3: 3, Pos 4: 1, Pos 5: 2, Pos 6: 3, Pos 7: 1.
- **Interpretación**: Alta estabilidad binaria entre versiones de compilación Samsung (Kernel 5.15.189).

---

## 7. Validación del Generador Original en Perl

Se auditó y ejecutó `tools/generate_p0_fingerprint.pl`:
1. Lectura de `SLIDE_KASLR_STEP`: Extraído de `target.h` (`0x4000`).
2. Cálculo de filas: $\text{int}(\text{0x1f0000} / \text{0x4000}) + 1 = 125$.
3. Desplazamiento de imagen: $\text{Image\_offset} = \text{0x1f0000} - \text{slide}$.
4. Orden de slides: Creciente de `0x000000` a `0x1f0000`.
5. Offsets intrapágina: Exactamente `0x000, 0x200, 0x400, 0x600, 0x800, 0xa00, 0xc00, 0xe00`.
6. Formato de enteros: Little-endian 64-bit (`Q<`).
7. Comparación numérica con la tabla EZE4 rederivada: **100% idéntica (0 discrepancias)**.

**Veredicto del Generador**: **`ALGORITHM_EQUIVALENT`**.

---

## 8. Artefacto Generado

Se generó el archivo de cabecera como artefacto de análisis offline:
- [**`docs/rmg-eze4/p0_fingerprint_EZE4.generated.h`**](file:///Users/markpi/tab-s9-fe-linux/docs/rmg-eze4/p0_fingerprint_EZE4.generated.h) (529 líneas, 125 entradas).
- Contiene la advertencia obligatoria:
  ```c
  /*
   * OFFLINE-GENERATED ANALYSIS ARTIFACT.
   * NOT YET VALIDATED ON HARDWARE.
   */
  ```
- **NO se ha copiado a `src/targets/`**.
- **NO se ha generado `target.h` ejecutable**.
- **NO se ha compilado ningún código**.

---

## 9. Métricas y Parámetros Obligatorios de Fase 3B

```
P0_TABLE_ROWS: 125
P0_TABLE_REDERIVATION: EXACT_MATCH
PERL_GENERATOR_EQUIVALENCE: ALGORITHM_EQUIVALENT
MIN_SELF_MARGIN: 0
MAX_OTHER_SCORE: 8
BORDERLINE_SLIDES: 0x1f0000
FAIL_SLIDES: 0x1e4000, 0x1e8000, 0x1ec000

ONE_QWORD_ERROR: 96.80% ACCEPTED (968/1000), 3.20% REJECTED (32/1000), 0.00% MISIDENTIFIED (0/1000)
TWO_QWORD_ERROR: 96.80% ACCEPTED (3388/3500), 3.20% REJECTED (112/3500), 0.00% MISIDENTIFIED (0/3500)
THREE_QWORD_ERROR: 96.80% ACCEPTED (6776/7000), 3.20% REJECTED (224/7000), 0.00% MISIDENTIFIED (0/7000)

SAFE_REJECTIONS: 368
MISIDENTIFICATIONS: 0

ZG3_IDENTICAL_ROWS: 106 / 125 (84.80%)
ZG3_IDENTICAL_QWORDS: 978 / 1000 (97.80%)

HEADER_GENERATED: YES (docs/rmg-eze4/p0_fingerprint_EZE4.generated.h - OFFLINE ANALYSIS ARTIFACT ONLY)
BLOCKERS: Ninguno (las 3 colisiones corresponden a padding NOP inherente a la arquitectura de imagen de kernel Samsung ARM64, idénticas a ZG3, y neutralizadas por el filtro de margen P0_FINGERPRINT_MIN_MARGIN = 3).
```

---

## 10. Veredicto Final de Fase 3B

$$\mathbf{P0\_OFFLINE\_VALIDATED\_WITH\_WARNINGS}$$

### Justificación del Veredicto:
- **Validado**: 121 de 125 candidatos (96.8%) presentan un margen $\ge 5$ con 100% de tolerancia ante hasta 3 errores simultáneos. En 11,500 simulaciones se registraron 0 casos de identificación errónea.
- **Con Advertencias (`WITH_WARNINGS`)**: Los 3 slides `0x1e4000`, `0x1e8000`, `0x1ec000` presentan colisión idéntica (8 NOPs) y `0x1f0000` presenta score 7 (7 NOPs + 1 salto). Si el bootloader cargase aleatoriamente el kernel en uno de estos 4 slides, el oráculo rechazará la lectura de forma segura por margen insuficiente forzando un reintento limpio.

---

## 11. Detención Preventiva

Conforme a las instrucciones del usuario, se da por finalizada la sesión de trabajo en este punto:
- **No se continúa a ninguna fase posterior**.
- **No se genera `target.h` ejecutable**.
- **No se compila nada**.
- **No se interactúa con el dispositivo**.
