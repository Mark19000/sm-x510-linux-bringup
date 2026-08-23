# 7. Roadmap hacia mainline

## Por qué no crear primero el DTS final

Mainline no tiene `samsung,s5e8835-*`. Un DTS enorme con cientos de nodos
desconocidos genera ruido y no puede revisarse. El upstreaming debe aportar una
cadena útil de dependencias, con bindings y drivers antes que consumidores.

## Serie 1: arranque mínimo

1. binding de SoC/placa;
2. IDs de clock y driver de CMU mínimo;
3. pinctrl/GPIO y EINT;
4. PMU/reset necesarios;
5. UART/earlycon;
6. `s5e8835.dtsi` mínimo con CPU, memory, GIC, timer y UART;
7. DTS de Tab S9 FE con `chosen` y consola.

Meta: texto mainline en UART, aunque no haya almacenamiento ni pantalla.

## Serie 2: almacenamiento y USB

1. power domain y CMU de UFS;
2. PHY/calibración UFS S5E8835;
3. glue del host UFS;
4. UFS en modo conservador y sólo lectura;
5. PHY/glue USB2 y DWC3;
6. role switch/Type-C cuando el controlador de puerto esté soportado.

Meta: raíz externa o initramfs con acceso fiable a UFS/USB.

## Serie 3: interfaz de usuario

1. SysMMU v8;
2. CMU/power domain de display;
3. DPU/DECON y DPP;
4. DSIM + PHY MIPI;
5. drivers de ambos paneles y backlight;
6. táctil y Wacom.

## Serie 4: operación diaria

GPU, Wi-Fi/BT, audio, suspensión, sensores y energía. Carga y gestión térmica
deben llegar después de tener telemetría fiable; un fallo ahí puede dañar
hardware, no sólo colgar el kernel.

## Criterios para cada parche upstream

- una sola idea por parche;
- binding YAML antes o junto al driver;
- `make dt_binding_check` y `make dtbs_check` limpios;
- `sources/wifi-kernel/scripts/checkpatch.pl` sin errores relevantes durante la
  fase downstream; para upstream, materializa y usa el script del snapshot
  mainline correspondiente;
- sin propiedades Android de política si existe una abstracción estándar;
- explicación de registros basada en documentación o comportamiento verificable;
- prueba en hardware descrita en el commit;
- compatibles minúsculos y específicos, por ejemplo
  `samsung,exynos1380-...`, sujetos a discusión con mantenedores.

La referencia de estilo más útil no es el driver vendor más parecido, sino el
SoC Exynos reciente mejor aceptado en mainline. Usa Exynos850/990/2200/AutoV9
para aprender estructura; verifica cada valor contra S5E8835.
