# Inventario Técnico de Artefactos — SM-X510 (EZE4)

- **Dispositivo**: Samsung Galaxy Tab S9 FE Wi-Fi (`SM-X510`)
- **Codename**: `gts9fewifi`
- **SoC**: Samsung Exynos 1380 (`s5e8835`)
- **Firmware Objetivo**: `X510XXUCEZE4` (Android 16 / One UI 8.5 / Bootloader U12 / REV00)
- **Kernel Release Stock**: `5.15.189-android13-3-33478785`
- **Vermagic Stock**: `5.15.189-android13-3-33478785 SMP preempt mod_unload modversions aarch64`
- **Estado de Hardware**: Bootloader bloqueado (`ro.boot.flash.locked=1`, `SWREV B:12`, `WARRANTY VOID: 0`)
- **Fecha de Auditoría**: 2026-09-06

---

## 1. Tabla Maestra de Artefactos

| Categoría | PATH (Relativo a `tab-s9-fe-linux/` o Guest) | TYPE | VERSION | HASH (SHA-256) | PURPOSE |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Kernel Source** | `audit/eze4-source-intake/packages/base/Kernel.tar.gz` | Tar Gzip | 5.15.189 | `2f3e18626011311a1450138e19b2091f7c177a5f8be6400a091f216800969b0f` | Código fuente downstream oficial Samsung OSRC para EZE4. |
| **Kernel Source** | `audit/eze4-source-intake/wrapper/SM-X510_EUR_16_Opensource.zip` | Zip | 5.15.189 | `72378f3be5c38344d52d231f85ee75c4b775feaac3ecbc794a1b59d791b1aad0` | Paquete envoltorio OSRC original distribuido por Samsung. |
| **Kernel Source (Tree)** | `audit/eze4-source-intake/extracted/kernel/` | Directorio / Árbol C | 5.15.189 | *(Directorio de 86,456 entradas)* | Árbol fuente completo extraído para auditoría estática. |
| **Boot Image** | `artifacts/stock/images/boot.img` | Android Boot v4 | EZE4 | `c96c0eb033d2208e84fbe0a0926df3ce2e8c6a94066702f2592e7bc165d11013` | Imagen oficial `boot.img` (67.1 MB), contiene el kernel Image stock y footer AVB. |
| **Boot Image (LZ4)** | `artifacts/stock/raw/boot.img.lz4` | LZ4 frame | EZE4 | `4a1cb8550faad30bda66df9d432dd6ec815ce79a795d12a9c35d01f4c7e3cc1f` | Flujo LZ4 comprimido extraído del archivo `AP_*.tar.md5`. |
| **Init Boot** | `artifacts/stock/images/init_boot.img` | Android Boot v4 | EZE4 | `9efb41692562f648b1227a7f7212bd87eec59d299689ac0b11c51348800e969c` | Imagen de ramdisk inicial genérico (16.8 MB), LZ4-legacy ramdisk. |
| **Init Boot (LZ4)** | `artifacts/stock/raw/init_boot.img.lz4` | LZ4 frame | EZE4 | `40f6be7510ae627bde0e6d8f4ff1136ba3d2175e95ff4b6d92d6af38499629c1` | Flujo LZ4 de init_boot extraído de AP. |
| **Vendor Boot** | `artifacts/stock/images/vendor_boot.img` | Android Vendor Boot v4 | EZE4 | `60e85ca061cc67cfa1f8d9fd86fc3840ccb46d87887c9b3ed20deca7c02459e8` | Imagen con fragmentos ramdisk (generic + DLKM con 281 módulos) y DTB base (33.6 MB). |
| **Vendor Boot (LZ4)** | `artifacts/stock/raw/vendor_boot.img.lz4` | LZ4 frame | EZE4 | `c7278a25410a8bc0c1bc0d1571df50487937ec11f7b684c9e1ed30ccf5c71046` | Flujo LZ4 de vendor_boot. |
| **DTBO Image** | `artifacts/stock/images/dtbo.img` | Android DTBO | EZE4 | `0dd2392e46fdd404d807b4d866b78f6a5c4833220c35fb2618f2651dce04469b` | Contenedor de overlays de hardware (8.4 MB), contiene 3 overlays (r00, r01, r04). |
| **DTBO (LZ4)** | `artifacts/stock/raw/dtbo.img.lz4` | LZ4 frame | EZE4 | `5f872b1537387c7639f30e6f91e9b9044ea69ab087cb201196b24360df02ffa5` | Flujo LZ4 de DTBO extraído de AP. |
| **VBMeta Image** | `artifacts/stock/images/vbmeta.img` | AVB 2.0 Descriptor | EZE4 | `bef09047de0beb48c8e8c57c283be46a283268cbf248b68c40b125441df40a9f` | Partición raíz de firma AVB 2.0 (10,128 bytes) con claves públicas Samsung. |
| **VBMeta (LZ4)** | `artifacts/stock/raw/vbmeta.img.lz4` | LZ4 frame | EZE4 | `2106019b8a159b6237641faa850619a78feb9f470b2b3a0bd416598ad3245740` | Flujo LZ4 de VBMeta extraído de AP. |
| **Stock Kernel Image** | Extraído de `boot.img` @ offset 4096 (len 39,356,928) | ARM64 Linux Image (PE/COFF) | 5.15.189-33478785 | `ca56baf428a3f334d90f5d366f02e6cb36cf70fec23a2055b4f80c29cbe6ede9` | Binario ejecutable exacto del kernel cargado de fábrica en el firmware EZE4. |
| **Built Kernel Image** | `artifacts/eze4/x510xxuceze4-baseline-20260905/Image` | ARM64 Linux Image | 5.15.189-33478785 | `a6f5c4f1b0e88191c395fa91cead4756986a5466d9da199558948358f0c6758b` | Kernel reconstruido de forma determinista mediante el pipeline Lima del proyecto. |
| **vmlinux (ELF DWARF)** | Lima VM: `/home/markpi.guest/osrc-eze4-work/runs/eze4-fixed2/build-source/out-eze4/vmlinux` | ELF 64-bit LSB (DWARF/BTF) | 5.15.189-33478785 | `44fd5d2b8949924c44d8809063763a099f6b6e1a00ab46c8c48262388724de8d` | Binario unstripped vmlinux (552 MB) con secciones `.BTF` y `.debug_info`. |
| **System.map** | `artifacts/eze4/x510xxuceze4-baseline-20260905/System.map` | Texto plano | 5.15.189-33478785 | `ec6047c299488b63d71a61facfae66a50fa1864b6c5499a8992768eb311d4515` | Tabla completa de símbolos virtuales del kernel compilado EZE4. |
| **Module.symvers** | `artifacts/eze4/x510xxuceze4-baseline-20260905/Module.symvers` | Texto plano | 5.15.189-33478785 | `f57afda2eb6a6755a7237b99e0f6908c0f39066929d9fda30b2e8011087df841` | CRCs de 15,123 símbolos exportados (`EXPORT_SYMBOL`) para `CONFIG_MODVERSIONS`. |
| **Kernel Config** | `artifacts/eze4/x510xxuceze4-baseline-20260905/kernel.config` | Kconfig config | 5.15.189 | `f9bb6c47759b96749258ae1081a8aa9e0e0c0a7a0774fe554708345ba08a64db` | Configuración `.config` exacta generada por `s5e8835-gts9fewifixx_defconfig`. |
| **BTF** | En `vmlinux` (sección `.BTF`, 6,000,722 bytes @ offset 0x1bdab1c) | BPF Type Format | 5.15.189 | *(Incrustado en ELF/Image)* | Información de tipos de datos, structs y offsets del kernel para BPF/tracing. |
| **Base DTB** | `artifacts/eze4/x510xxuceze4-baseline-20260905/s5e8835.dtb` | Device Tree Blob | 5.15.189 | `814f78c734c7a7d43e1fceb9fc35faa95f8c04c8313cc3973a04eadac473254f` | Árbol de dispositivos base para el SoC Exynos 1380 (s5e8835). |
| **Stock DTB** | `artifacts/stock/dt/vendor_boot/fdt-00-offset-0113f040.dtb` | Device Tree Blob | EZE4 Stock | `f5c015b6d5102a013fa7d10e8284566c3c737c357f495ca973ce96f7c8ec3f62` | DTB extraído directamente de la partición de fábrica `vendor_boot.img`. |
| **DTBO Overlay r00** | `artifacts/eze4/x510xxuceze4-baseline-20260905/gts9fewifi_eur_open_w00_r00.dtbo` | Device Tree Overlay | EZE4 r00 | `4f2fd84ef62c70d4143919d8ddbe6d1152f6532d078878dc30fcb1cf68b790be` | Overlay hardware rev 00 (idéntico byte a byte con stock `overlay-00`). |
| **DTBO Overlay r01** | `artifacts/eze4/x510xxuceze4-baseline-20260905/gts9fewifi_eur_open_w00_r01.dtbo` | Device Tree Overlay | EZE4 r01 | `c764f7c69a9fef235af7c042b1ec7331f600b7eb60dd67d465ec721f8386f325` | Overlay hardware rev 01 (idéntico byte a byte con stock `overlay-01`). |
| **DTBO Overlay r04** | `artifacts/eze4/x510xxuceze4-baseline-20260905/gts9fewifi_eur_open_w00_r04.dtbo` | Device Tree Overlay | EZE4 r04 | `cdee895e13eae5ed35c3a951eb3b8a448a46f60c89f73546bcb7c3b4fae8d403` | Overlay hardware rev 04 comercial (idéntico byte a byte con stock `overlay-02`). |
| **Stock Modules Audit** | `artifacts/stock/vendor-ramdisk-audit/` | Metadatos CPIO | EZE4 Stock | `06adcacad3020efcc0a263c1d62c83ab1504e30f79114398a45250fe8da76deb` | Registro de 281 módulos DLKM stock, con tablas de dependencias y hashes. |
| **Built Modules Tarball** | `artifacts/eze4/x510xxuceze4-baseline-20260905/modules-root.tar.gz` | Tar Gzip | 5.15.189-33478785 | `18d3768e66c934c063133c1cf9ebdf1a4448c1cf45fcb4e95ed49e5485feed0c` | 282 módulos de kernel compilados con paridad ABI del 100.00% demostrada. |
| **AVB Toolchain** | `sources/toolchain/avb-android16/` | Python / Binario | Android 16 | `d4683e75f9a12a0a7089871fcc0432d242ccc6d44e7c5fe18f4a0f527151ab66` | Herramientas oficiales AOSP AVB 2.0 para inspección de firmas y descriptores. |
| **MagiskBoot Tool** | `sources/toolchain/magisk-v30.7/` | Binario host / guest | v30.7 | N/A | Utilidad para desempaquetar y recomponer cabeceras Android boot v4. |
| **Compiler Toolchain** | Lima VM: Ubuntu Clang / LLD | Clang 21.1.8 | LLVM 21.1.8 | N/A | Compilador cruzado aarch64 reproducible utilizado en el pipeline. |
| **Build Scripts** | `scripts/build-eze4-in-lima.sh` | Bash Script | v1.0 | N/A | Orquestador de compilación en el entorno virtualizado Lima. |
| **ABI Verification Tool** | `scripts/verify-eze4-abi.py` | Python 3 Script | v1.0 | N/A | Verificador automático de CRCs `__versions` contra `Module.symvers`. |
| **Firmware Archive Reference**| En host: `/Users/markpi/Downloads/SAMFW.COM_SM-X510_EUX_X510XXUCEZE4_fac.zip` | Zip | EZE4 EUX | `45a450875ce753e74d8183aa085837ada91cabe2832d9725a1567aa29b01d375` | Firmware completo oficial descargado de fábrica. |

---

## 2. Estado de Componentes de Bootloader (`sboot`)

- **Presencia Local**: No existen archivos binarios desensamblados de `sboot.bin` en el workspace local de trabajo, debido a que el paquete AP sólo incluye particiones Android estándar del sistema operativo (`boot`, `init_boot`, `vendor_boot`, `recovery`, `dtbo`, `vbmeta`, `super`). El firmware BL (`BL_X510XXUCEZE4_*.tar.md5`) no fue extraído localmente para ahorrar espacio de almacenamiento.
- **Evidencia Física de Hardware**: La ejecución de diagnósticos físicos en Odin Mode (registrada en `docs/hardware/evidence/2026-09-05-odin-mode-stock-baseline.md`) confirmó que la unidad real cuenta con bootloader de revisión 12 (`RP SWREV B:12`), binario oficial (`CURRENT BINARY: Samsung Official`), estado Knox intacto (`WARRANTY VOID: 0x0000`) y protección Knox Guard completada (`KG STATE: Completed (00)`).
- **Guardas de Seguridad**: El bootloader se encuentra estrictamente bloqueado.
