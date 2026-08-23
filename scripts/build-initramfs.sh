#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
# shellcheck source=scripts/safety-paths.sh
source "$ROOT/scripts/safety-paths.sh"
VARIANT=${DEVICE_VARIANT:-wifi}
case "$VARIANT" in wifi|5g) ;; *) echo "DEVICE_VARIANT debe ser wifi o 5g" >&2; exit 2 ;; esac
BUSYBOX=${BUSYBOX:-$ROOT/artifacts/busybox/busybox}
OUT=${INITRAMFS_OUT:-$ROOT/artifacts/initramfs/$VARIANT}
STAGE_PARENT=${INITRAMFS_STAGE_PARENT:-}
MODULES_ROOT=${MODULES_ROOT:-$ROOT/artifacts/kernel/$VARIANT/dist/modules-root/lib/modules}
MODULES_MODE=${MODULES_MODE:-none}
MODULES_LIST=${MODULES_LIST:-$ROOT/configs/initramfs-modules.conf}
SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH:-0}

if [ ! -x "$BUSYBOX" ]; then
    echo "No encuentro BusyBox en $BUSYBOX" >&2
    echo "Ejecuta scripts/build-busybox.sh en Linux o pasa BUSYBOX=/ruta/busybox." >&2
    exit 1
fi
if ! file "$BUSYBOX" | grep -Eq 'ARM aarch64|ARM64'; then
    echo "BusyBox debe ser AArch64: $(file "$BUSYBOX")" >&2
    exit 1
fi
if ! file "$BUSYBOX" | grep -q 'statically linked'; then
    echo "BusyBox debe estar enlazado estáticamente." >&2
    exit 1
fi
command -v cpio >/dev/null || { echo "Falta cpio." >&2; exit 1; }
case "$MODULES_MODE" in
    none|all|deps) ;;
    *) echo "MODULES_MODE debe ser none, deps o all" >&2; exit 2 ;;
esac

mkdir -p "$OUT"
out_real=$(cd "$OUT" && pwd -P)
guard_output_directory "$out_real" "INITRAMFS_OUT"
project_parent=$(dirname "$ROOT")
case "$out_real" in
    /|/tmp|/var/tmp|"$ROOT"|"$project_parent"|"${HOME:-__no_home__}")
        echo "INITRAMFS_OUT demasiado amplio y rechazado: $out_real" >&2
        exit 1
        ;;
esac
source_rootfs=$(cd "$ROOT/initramfs/rootfs" && pwd -P)
temporary_stage=0
if [ -n "$STAGE_PARENT" ]; then
    mkdir -p "$STAGE_PARENT"
    stage_parent_real=$(cd "$STAGE_PARENT" && pwd -P)
    guard_output_directory "$stage_parent_real/gts9fe-initramfs-stage.placeholder" "INITRAMFS_STAGE_PARENT"
    case "$stage_parent_real" in
        /|"$ROOT"|"$project_parent"|"${HOME:-__no_home__}"|"$source_rootfs"|"$source_rootfs"/*)
            echo "INITRAMFS_STAGE_PARENT demasiado amplio o peligroso: $stage_parent_real" >&2
            exit 1
            ;;
    esac
    STAGE=$(mktemp -d "$stage_parent_real/gts9fe-initramfs-stage.XXXXXX")
    temporary_stage=1
    cleanup_stage() { rm -rf -- "$STAGE"; }
    trap cleanup_stage EXIT
else
    STAGE="$OUT/rootfs"
fi
stage_path=$STAGE
stage_real=$(canonical_output_path "$stage_path")
case "$stage_real" in
    "$source_rootfs"|"$source_rootfs"/*)
        echo "El staging del initramfs apunta al árbol fuente y se rechaza: $stage_real" >&2
        exit 1
        ;;
esac
# Si una ejecución posterior falla, no debe quedar un archivo anterior con
# apariencia de éxito bajo el mismo OUT.
rm -f -- "$OUT/gts9fe-initramfs.cpio" \
    "$OUT/gts9fe-initramfs.cpio.gz" \
    "$OUT/gts9fe-initramfs.cpio.lz4" "$OUT/SHA256SUMS"
if [ "$temporary_stage" -eq 0 ] && [ -d "$STAGE" ]; then
    case "$STAGE" in
        "$OUT"/rootfs) rm -rf -- "$STAGE" ;;
        *) echo "Ruta de staging inesperada: $STAGE" >&2; exit 1 ;;
    esac
fi
mkdir -p "$STAGE/bin" "$STAGE/sbin" "$STAGE/usr/bin" "$STAGE/usr/sbin" \
    "$STAGE/etc" "$STAGE/proc" "$STAGE/sys" "$STAGE/dev" "$STAGE/run" \
    "$STAGE/tmp" "$STAGE/root" "$STAGE/newroot"
cp "$BUSYBOX" "$STAGE/bin/busybox"
cp "$ROOT/initramfs/rootfs/init" "$STAGE/init"
cp "$ROOT/initramfs/rootfs/etc/passwd" "$ROOT/initramfs/rootfs/etc/group" \
    "$ROOT/initramfs/rootfs/etc/fstab" "$STAGE/etc/"
chmod 0755 "$STAGE/init" "$STAGE/bin/busybox"
chmod 0644 "$STAGE/etc/passwd" "$STAGE/etc/group" "$STAGE/etc/fstab"

case "$MODULES_MODE" in
    none)
        echo "Perfil de módulos: none (rescate mínimo)"
        ;;
    all)
        test -d "$MODULES_ROOT" || { echo "Falta $MODULES_ROOT" >&2; exit 1; }
        mkdir -p "$STAGE/lib/modules"
        cp -R "$MODULES_ROOT"/. "$STAGE/lib/modules/"
        echo "AVISO: perfil all; comprueba que el archivo cabe en la partición."
        ;;
    deps)
        test -f "$MODULES_LIST" || { echo "Falta $MODULES_LIST" >&2; exit 1; }
        command -v modprobe >/dev/null || { echo "Falta modprobe en el host." >&2; exit 1; }
        command -v depmod >/dev/null || { echo "Falta depmod en el host." >&2; exit 1; }
        shopt -s nullglob
        releases=("$MODULES_ROOT"/*)
        shopt -u nullglob
        if [ "${#releases[@]}" -ne 1 ] || [ ! -d "${releases[0]}" ]; then
            echo "Se esperaba exactamente un kernel release bajo $MODULES_ROOT" >&2
            exit 1
        fi
        release=$(basename "${releases[0]}")
        install_root=${MODULES_ROOT%/lib/modules}
        declare -A copied=()
        mkdir -p "$STAGE/lib/modules/$release"
        : > "$STAGE/lib/modules/$release/modules.order"
        requested_file="$STAGE/.requested-modules"
        dependency_file="$STAGE/.module-dependencies"
        sed 's/#.*//; /^[[:space:]]*$/d' "$MODULES_LIST" > "$requested_file"
        : > "$dependency_file"
        # No uses una sustitución de proceso que contenga modprobe: bash no
        # propaga de forma fiable su exit status al while consumidor. Generar
        # primero el listado hace que una dependencia ausente detenga el build.
        while IFS= read -r module; do
            modprobe -d "$install_root" -S "$release" \
                --show-depends "$module" >> "$dependency_file"
        done < "$requested_file"
        while read -r action module_path rest; do
            [ "$action" = insmod ] || continue
            case "$module_path" in
                "$MODULES_ROOT/$release/"*) ;;
                *) echo "Ruta de módulo inesperada: $module_path" >&2; exit 1 ;;
            esac
            relative=${module_path#"$MODULES_ROOT/"}
            module_relative=${module_path#"$MODULES_ROOT/$release/"}
            [ -n "${copied[$relative]:-}" ] && continue
            copied[$relative]=1
            mkdir -p "$STAGE/lib/modules/$(dirname "$relative")"
            cp "$module_path" "$STAGE/lib/modules/$relative"
            printf '%s\n' "$module_relative" >> \
                "$STAGE/lib/modules/$release/modules.order"
        done < "$dependency_file"
        rm -f -- "$requested_file" "$dependency_file"
        [ "${#copied[@]}" -gt 0 ] || {
            echo "La lista de módulos no produjo ningún .ko" >&2
            exit 1
        }
        for metadata in modules.builtin modules.builtin.modinfo; do
            [ -f "$MODULES_ROOT/$release/$metadata" ] && \
                cp "$MODULES_ROOT/$release/$metadata" "$STAGE/lib/modules/$release/"
        done
        depmod -b "$STAGE" "$release"
        cp "$MODULES_LIST" "$STAGE/etc/gts9fe-modules"
        echo "Perfil de módulos: deps (${#copied[@]} módulos para $release)"
        ;;
esac

for applet in sh mount mkdir hostname uname cat ls head ln setsid sleep dmesg \
    find grep sed dd hexdump blkid mdev modprobe depmod switch_root poweroff reboot \
    rm rmdir; do
    ln -sf busybox "$STAGE/bin/$applet"
done

# Utilities conventionally searched in /sbin.
for applet in mdev modprobe depmod switch_root; do
    [ -e "$STAGE/bin/$applet" ] && ln -sf ../bin/busybox "$STAGE/sbin/$applet"
done

# newc conserva mtime y uid/gid. Normalizarlos hace que dos builds con los
# mismos inputs produzcan exactamente los mismos bytes.
find "$STAGE" -type d -exec chmod 0755 {} +
find "$STAGE" -exec touch -h -d "@$SOURCE_DATE_EPOCH" {} +
(
    cd "$STAGE"
    find . -print0 | LC_ALL=C sort -z | \
        cpio --null --reproducible --owner=0:0 -o -H newc
) > "$OUT/gts9fe-initramfs.cpio"
gzip -n -9 -c "$OUT/gts9fe-initramfs.cpio" > "$OUT/gts9fe-initramfs.cpio.gz"

if command -v lz4 >/dev/null 2>&1; then
    lz4 -l -12 -f "$OUT/gts9fe-initramfs.cpio" "$OUT/gts9fe-initramfs.cpio.lz4"
else
    echo "AVISO: falta lz4; no se generó gts9fe-initramfs.cpio.lz4." >&2
fi

# Cuando OUT está en un mount virtiofs/APFS, Linux observa modos distintos para
# symlinks (0755) que en ext4 (0777). newc conserva ese modo y rompe la
# reproducibilidad aunque el contenido lógico sea igual. Si se pidió un staging
# temporal, el archivo ya se generó íntegramente en el filesystem Linux; se
# publica después una copia de rootfs sólo para inspección humana.
if [ "$temporary_stage" -eq 1 ]; then
    published_stage="$OUT/rootfs"
    if [ -e "$published_stage" ]; then
        case "$published_stage" in
            "$OUT"/rootfs) rm -rf -- "$published_stage" ;;
            *) echo "Ruta de publicación de rootfs inesperada: $published_stage" >&2; exit 1 ;;
        esac
    fi
    cp -a "$STAGE" "$published_stage"
    cleanup_stage
    trap - EXIT
fi

(
    cd "$OUT"
    checksum_files=(gts9fe-initramfs.cpio gts9fe-initramfs.cpio.gz)
    [ ! -f gts9fe-initramfs.cpio.lz4 ] || checksum_files+=(gts9fe-initramfs.cpio.lz4)
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "${checksum_files[@]}" > SHA256SUMS
    else
        shasum -a 256 "${checksum_files[@]}" > SHA256SUMS
    fi
)

echo "Contenido del initramfs:"
cpio -it < "$OUT/gts9fe-initramfs.cpio" | sed -n '1,30p'
echo "Artefactos en $OUT"
