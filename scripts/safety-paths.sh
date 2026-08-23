#!/usr/bin/env bash

# Funciones compartidas por scripts que crean o sustituyen artefactos. Este
# archivo se carga con `source`; no activa opciones del shell por su cuenta.

canonical_output_path() {
    python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$1"
}

reject_system_path() {
    candidate=$1
    label=${2:-Ruta de salida}
    case "$candidate" in
        /|/bin|/bin/*|/boot|/boot/*|/dev|/dev/*|/etc|/etc/*|/lib|/lib/*|\
        /lib64|/lib64/*|/proc|/proc/*|/run|/run/*|/sbin|/sbin/*|/sys|/sys/*|\
        /usr|/usr/*|/var|/var/lib|/var/lib/*|/var/log|/var/log/*|/var/run|/var/run/*|\
        /System|/System/*|/Library|/Library/*|/Applications|/Applications/*|\
        /private/etc|/private/etc/*|/private/var/db|/private/var/db/*|\
        /private/var/root|/private/var/root/*|/private/var/run|/private/var/run/*)
            echo "$label apunta a una ruta del sistema y se rechaza: $candidate" >&2
            return 1
            ;;
    esac
}

guard_output_directory() {
    directory=$1
    label=${2:-Directorio de salida}
    resolved=$(canonical_output_path "$directory")
    reject_system_path "$resolved" "$label"
}

guard_output_file() {
    output=$1
    label=${2:-Fichero de salida}
    resolved=$(canonical_output_path "$output")
    reject_system_path "$resolved" "$label"
    if [ -L "$output" ]; then
        echo "$label no puede ser un enlace simbólico: $output" >&2
        return 1
    fi
    if [ -e "$output" ] && [ ! -f "$output" ]; then
        echo "$label debe ser un fichero regular: $output" >&2
        return 1
    fi
}
