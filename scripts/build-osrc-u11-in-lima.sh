#!/usr/bin/env bash
set -Eeuo pipefail

# Stage an Android 16/U11 OSRC delivery in a fresh Lima/ext4 run directory.
# Nothing from the delivery is unpacked on the host and the existing U3
# checkout/artifacts are never used as build inputs or output directories.

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
# shellcheck source=scripts/safety-paths.sh
source "$ROOT/scripts/safety-paths.sh"

VM=${LIMA_INSTANCE:-gts9fe-build}
INPUT=${OSRC_RELEASE:-}
MODE=${U11_BUILD:-inspect}
BUILD_JOBS=${U11_JOBS:-6}
RUN_ID=${U11_RUN_ID:-u11-$(date -u +%Y%m%dT%H%M%SZ)-$$}
HOST_RUNS=${U11_HOST_RUNS:-$ROOT/artifacts/u11}
GUEST_PARENT=${U11_GUEST_PARENT:-}

usage() {
    cat >&2 <<'EOF'
Uso:
  OSRC_RELEASE=/ruta/SM-X510.zip ./scripts/build-osrc-u11-in-lima.sh
  OSRC_RELEASE=/ruta/release-dir U11_BUILD=1 \
    ./scripts/build-osrc-u11-in-lima.sh

Opciones:
  --release PATH       sustituye OSRC_RELEASE
  --vm NAME            instancia Lima (por defecto gts9fe-build)
  --run-id ID          identificador nuevo para host y guest
  --build              inspecciona y ejecuta el perfil U11 fijo en el guest
  --inspect            sólo staging, extracción e inventario (por defecto)
  --jobs N             paralelismo del perfil fijo (1..64; por defecto 6)

La entrada puede ser un ZIP/TAR o un directorio ya entregado. Un fichero
.part, un enlace simbólico o una ruta dentro de sources/wifi-kernel se rechaza.
EOF
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --release)
            shift
            [ "$#" -gt 0 ] || { usage; exit 2; }
            INPUT=$1
            ;;
        --vm)
            shift
            [ "$#" -gt 0 ] || { usage; exit 2; }
            VM=$1
            ;;
        --run-id)
            shift
            [ "$#" -gt 0 ] || { usage; exit 2; }
            RUN_ID=$1
            ;;
        --build)
            MODE=build
            ;;
        --inspect)
            MODE=inspect
            ;;
        --jobs)
            shift
            [ "$#" -gt 0 ] || { usage; exit 2; }
            BUILD_JOBS=$1
            ;;
        --build-command)
            echo "--build-command se ha eliminado: usa el perfil U11 fijo con --build." >&2
            exit 2
            ;;
        -h|--help)
            usage 2>&1
            exit 0
            ;;
        *)
            echo "Argumento desconocido: $1" >&2
            usage
            exit 2
            ;;
    esac
    shift
done

[ -n "$INPUT" ] || { echo "Falta OSRC_RELEASE; no se elige ningún ZIP automáticamente." >&2; usage; exit 2; }
case "$MODE" in
    inspect|0|false|no) MODE=inspect ;;
    build|1|true|yes) MODE=build ;;
    *) echo "U11_BUILD debe ser inspect o build (recibido: $MODE)" >&2; exit 2 ;;
esac
case "$BUILD_JOBS" in ''|*[!0-9]*) echo "U11_JOBS/--jobs debe ser un entero positivo." >&2; exit 2 ;; esac
[ "$BUILD_JOBS" -ge 1 ] && [ "$BUILD_JOBS" -le 64 ] || { echo "U11_JOBS debe estar entre 1 y 64." >&2; exit 2; }
[ -z "${U11_BUILD_COMMAND:-}" ] || {
    echo "U11_BUILD_COMMAND se ha eliminado: no se ejecutan cadenas de shell arbitrarias." >&2
    exit 2
}

case "$RUN_ID" in
    ''|.|..|*[!A-Za-z0-9._-]*)
        echo "RUN_ID sólo puede contener letras, números, punto, guion y guion bajo: $RUN_ID" >&2
        exit 2
        ;;
esac
case "$VM" in
    ''|*[!A-Za-z0-9._-]*)
        echo "Nombre de VM no válido: $VM" >&2
        exit 2
        ;;
esac

input_path=$(python3 -c 'import os,sys; print(os.path.abspath(sys.argv[1]))' "$INPUT")
[ -e "$input_path" ] || { echo "No existe OSRC_RELEASE: $INPUT" >&2; exit 1; }
[ ! -L "$input_path" ] || { echo "OSRC_RELEASE no puede ser un enlace simbólico: $INPUT" >&2; exit 1; }
case "$input_path" in
    *.part|*.PART|*/.part|*/.PART)
        echo "Se rechaza .part sin abrirlo: $INPUT" >&2
        exit 1
        ;;
esac

input_real=$(canonical_output_path "$input_path")
wifi_real=$(canonical_output_path "$ROOT/sources/wifi-kernel")
case "$input_real/" in
    "$wifi_real/"|"$wifi_real"/*)
        echo "La entrega no puede vivir dentro de sources/wifi-kernel (referencia U3): $INPUT" >&2
        exit 1
        ;;
esac

input_kind=file
if [ -d "$input_path" ]; then
    input_kind=directory
    if find "$input_path" -type l -print -quit | grep -q .; then
        echo "El directorio de release contiene enlaces simbólicos; se rechaza." >&2
        exit 1
    fi
    if find "$input_path" -name '*.part' -print -quit | grep -q .; then
        echo "El directorio de release contiene .part; no se lee ni se copia." >&2
        exit 1
    fi
elif [ ! -f "$input_path" ]; then
    echo "OSRC_RELEASE debe ser un fichero regular o directorio: $INPUT" >&2
    exit 1
fi

input_name=$(basename "$input_path")
case "$input_name" in
    ''|.|..|*[!A-Za-z0-9._-]*)
        echo "El nombre de la entrega contiene caracteres no permitidos: $input_name" >&2
        exit 1
        ;;
esac

command -v limactl >/dev/null || {
    echo "Falta limactl; prepara la VM con scripts/setup-lima.sh." >&2
    exit 1
}
command -v python3 >/dev/null || { echo "Falta python3 en el host." >&2; exit 1; }

if [ -z "$GUEST_PARENT" ]; then
    # Resolve the guest's HOME instead of expanding the host's /Users path.
    GUEST_PARENT=$(limactl shell "$VM" -- bash -lc 'printf "%s/osrc-u11-work" "$HOME"')
fi
case "$GUEST_PARENT" in
    /*|/*/*) ;;
    *) echo "U11_GUEST_PARENT debe ser una ruta absoluta dentro de la VM: $GUEST_PARENT" >&2; exit 2 ;;
esac
case "$GUEST_PARENT" in
    /|/tmp|/var|/var/*|/root|/home|/home/*/..)
        echo "U11_GUEST_PARENT es demasiado amplio; usa un subdirectorio nuevo de HOME." >&2
        exit 2
        ;;
esac
case "$GUEST_PARENT" in
    */../*|*/..|*/./*|*/.)
        echo "U11_GUEST_PARENT no puede contener componentes ambiguos: $GUEST_PARENT" >&2
        exit 2
        ;;
esac

mkdir -p "$HOST_RUNS"
guard_output_directory "$HOST_RUNS" "Registro host U11"
host_run="$HOST_RUNS/$RUN_ID"
if ! mkdir "$host_run" 2>/dev/null; then
    echo "El registro ya existe; se rechaza para no sobrescribir: $host_run" >&2
    exit 1
fi
guard_output_directory "$host_run" "Registro host U11"

guest_run="$GUEST_PARENT/$RUN_ID"
guest_input="$guest_run/input/$input_name"
guest_tool="$guest_run/tools/safe_release_extract.py"
guest_build_tool="$guest_run/tools/build-u11-kernel-guest.sh"

cat > "$host_run/host-input.txt" <<EOF
run_id=$RUN_ID
input_name=$input_name
input_kind=$input_kind
input_host_path=$input_real
vm=$VM
guest_run=$guest_run
mode=$MODE
build_jobs=$BUILD_JOBS
u3_source_protected=$wifi_real
EOF

# Create only the new guest run. Existing ext4 worktrees and the mounted
# project remain untouched; no cleanup command is issued on failure.
limactl shell "$VM" -- mkdir -p "$guest_run/input" "$guest_run/tools/patches" "$guest_run/logs"
if [ "$input_kind" = directory ]; then
    limactl copy --backend=scp -r "$input_path" "$VM:$guest_run/input/"
else
    limactl copy --backend=scp "$input_path" "$VM:$guest_run/input/"
fi
limactl copy --backend=scp "$ROOT/tools/safe_release_extract.py" "$VM:$guest_run/tools/"
limactl copy --backend=scp "$ROOT/scripts/build-u11-kernel-guest.sh" "$VM:$guest_run/tools/"
limactl copy --backend=scp "$ROOT/configs/gts9fe-linux.fragment" "$VM:$guest_run/tools/"
limactl copy --backend=scp "$ROOT/configs/u11-patches.sha256" "$VM:$guest_run/tools/"
limactl copy --backend=scp -r "$ROOT/patches/downstream/wifi" "$VM:$guest_run/tools/patches/"

set +e
limactl shell "$VM" -- bash -s -- \
    "$guest_run" "$guest_input" "$input_kind" "$MODE" "$BUILD_JOBS" "$guest_tool" "$guest_build_tool" <<'GUEST_SCRIPT' \
    2>&1 | tee "$host_run/guest-console.log"
set -Eeuo pipefail

run=$1
input=$2
input_kind=$3
mode=$4
build_jobs=$5
tool=$6
build_tool=$7
mkdir -p "$run/logs"
exec > >(tee -a "$run/logs/u11-build.log") 2>&1

status=0
finish() {
    status=$?
    {
        printf 'status=%s\n' "$status"
        printf 'run=%s\n' "$run"
        printf 'input=%s\n' "$input"
        printf 'mode=%s\n' "$mode"
        printf 'finished_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    } > "$run/STATUS"
    if [ "$status" -eq 0 ]; then
        echo "U11 staging/build terminado; el checkout queda sólo en ext4: $run"
    else
        echo "U11 staging/build falló con código $status; conserva el log: $run/logs/u11-build.log" >&2
    fi
    return "$status"
}
trap finish EXIT

printf 'run=%s\ninput=%s\ninput_kind=%s\nmode=%s\n' "$run" "$input" "$input_kind" "$mode"
printf 'guest=%s\n' "$(uname -a)"
printf 'toolchain.clang=%s\n' "$(command -v clang 2>/dev/null || echo missing)"
printf 'toolchain.clang_version=%s\n' "$(clang --version 2>/dev/null | sed -n '1p' || echo missing)"
printf 'toolchain.make=%s\n' "$(make --version 2>/dev/null | sed -n '1p' || echo missing)"
printf 'toolchain.dtc=%s\n' "$(dtc --version 2>/dev/null | sed -n '1p' || echo missing)"
printf 'toolchain.python=%s\n' "$(python3 --version 2>&1 | sed -n '1p' || echo missing)"

if [ "$input_kind" = file ]; then
    case "$(printf '%s' "$input" | tr '[:upper:]' '[:lower:]')" in
        *.zip)
            release="$run/release"
            python3 "$tool" extract-zip "$input" "$release"
            ;;
        *.tar|*.tar.gz|*.tar.bz2|*.tar.xz|*.tar.zst|*.tar.lz4|*.tar.md5|*.tgz|*.tbz|*.tbz2|*.txz)
            release="$run/release"
            python3 "$tool" extract-tar "$input" "$release"
            ;;
        *)
            echo "Formato de release no reconocido; use ZIP/TAR o directorio." >&2
            exit 1
            ;;
    esac
else
    release="$input"
fi

# A wrapper can contain both Kernel.tar.gz and a regional overlay ZIP. All
# archive expansion happens below $run on ext4; each output directory is
# fresh and the helper rejects links/traversal/collisions.
python3 "$tool" unpack-tree "$release" --manifest "$run/archive-manifest.json"
python3 "$tool" scan "$release" --output "$run/release-layout.json"

base_kernel_root=$(python3 - "$run/release-layout.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as stream:
    layout = json.load(stream)
roots = layout.get("kernel_roots", [])
if len(roots) != 1:
    raise SystemExit(
        "Se esperaba exactamente un kernel root para build; encontrados: "
        + ", ".join(str(item.get("path")) for item in roots)
    )
print(roots[0]["path"])
PY
)
base_kernel_root="$release/$base_kernel_root"

# The exact U11 delivery is a base U8 tree plus the X510XXSBDZB4 regional
# overlay. Keep both extracted inputs immutable and materialize a third,
# guest-only composite before any build. An arbitrary README is not accepted
# as an overlay: both the expected U11 marker and the stated U8 base marker
# must be present next to a Kernel/ tree.
overlay_root=
overlay_readme=
while IFS= read -r readme; do
    candidate="$(dirname "$readme")/Kernel"
    [ -d "$candidate" ] || continue
    [ "$candidate" != "$base_kernel_root" ] || continue
    if grep -Eiq 'X510XXSBDZB4' "$readme" && grep -Eiq 'X510XXU8DYJ4' "$readme"; then
        [ -z "$overlay_root" ] || {
            echo "Más de un overlay U11 elegible; se detiene antes de combinar." >&2
            exit 1
        }
        overlay_root="$candidate"
        overlay_readme="$readme"
    fi
done < <(find "$release" -type f -iname 'README*' -print | LC_ALL=C sort)

kernel_root="$base_kernel_root"
composite_root=
overlay_status=missing
if [ -n "$overlay_root" ]; then
    composite_root="$run/u11-composite/Kernel"
    mkdir -p "$run/u11-composite"
    cp -a "$base_kernel_root" "$composite_root"
    # Samsung ships most regular files read-only.  Overlay replacement only
    # needs writable parent directories, so do not change the file modes of
    # the exact composite.  Restore every directory mode from the delivered
    # base/overlay after copying; regular overlay files keep their cp -a mode.
    find "$composite_root" -type d -exec chmod u+w {} +
    cp -a --remove-destination "$overlay_root/." "$composite_root/"
    while IFS= read -r -d '' overlay_file; do
        relative=${overlay_file#"$overlay_root"/}
        composite_file="$composite_root/$relative"
        [ -f "$composite_file" ] || {
            echo "Falta en el composite un fichero del overlay: $relative" >&2
            exit 1
        }
        cmp -s "$overlay_file" "$composite_file" || {
            echo "El composite no reproduce exactamente el overlay: $relative" >&2
            exit 1
        }
    done < <(find "$overlay_root" -type f -print0 | LC_ALL=C sort -z)
    while IFS= read -r -d '' relative; do
        chmod --reference="$base_kernel_root/$relative" "$composite_root/$relative"
    done < <(cd "$base_kernel_root" && find . -type d -print0)
    while IFS= read -r -d '' relative; do
        chmod --reference="$overlay_root/$relative" "$composite_root/$relative"
    done < <(cd "$overlay_root" && find . -type d -print0)
    kernel_root="$composite_root"
    overlay_status=applied-in-guest-composite
    python3 "$tool" scan "$kernel_root" --output "$run/composite-layout.json"
    {
        printf 'overlay_root=%s\n' "$overlay_root"
        printf 'overlay_readme=%s\n' "$overlay_readme"
        printf 'marker=X510XXSBDZB4\nbase_marker=X510XXU8DYJ4\n'
        while IFS= read -r -d '' file; do
            printf '%s  %s\n' "$(sha256sum "$file" | cut -d ' ' -f1)" "${file#"$release"/}"
        done < <(find "$overlay_root" -type f -print0 | LC_ALL=C sort -z)
    } > "$run/overlay-manifest.txt"
else
    echo "No se encontró el overlay exacto X510XXSBDZB4; la inspección queda en la base." >&2
fi

{
    printf 'release_root=%s\n' "$release"
    printf 'base_kernel_root=%s\n' "$base_kernel_root"
    printf 'kernel_root=%s\n' "$kernel_root"
    printf 'overlay_root=%s\n' "${overlay_root:-missing}"
    printf 'overlay_status=%s\n' "$overlay_status"
    printf 'archive_manifest=%s\n' "$run/archive-manifest.json"
    printf 'release_layout=%s\n' "$run/release-layout.json"
    [ -f "$run/composite-layout.json" ] && printf 'composite_layout=%s\n' "$run/composite-layout.json"
    [ -f "$run/overlay-manifest.txt" ] && printf 'overlay_manifest=%s\n' "$run/overlay-manifest.txt"
    printf 'logs=%s\n' "$run/logs"
    printf 'source_commit='
    git -C "$kernel_root" rev-parse HEAD 2>/dev/null || printf 'not-a-git-checkout\n'
    printf 'source_dirty='
    if git -C "$kernel_root" diff --quiet 2>/dev/null; then printf 'no\n'; else printf 'yes-or-unavailable\n'; fi
    printf 'defconfigs='
    find "$kernel_root" -type f -iname '*defconfig*' -print | LC_ALL=C sort | tr '\n' ';'
    printf '\n'
    printf 'build_scripts='
    find "$kernel_root" -type f \( -name 'build*.sh' -o -name 'Makefile' \) -print | LC_ALL=C sort | tr '\n' ';'
    printf '\n'
} > "$run/build-metadata.txt"

if [ "$mode" = build ]; then
    [ -n "$overlay_root" ] || {
        echo "El build U11 exige el overlay exacto X510XXSBDZB4; no se compila la base U8 sola." >&2
        exit 1
    }
    [ "$kernel_root" = "$composite_root" ] || {
        echo "El build U11 sólo puede usar el composite nuevo del guest." >&2
        exit 1
    }
    # Some Samsung Makefiles generate helper C files below the source tree
    # even with O=.  Build from a private full copy so those writes cannot
    # alter the exact composite retained as release evidence.
    build_kernel_root="$run/build-source/Kernel"
    mkdir -p "$run/build-source"
    cp -a "$composite_root" "$build_kernel_root"
    chmod -R u+w "$build_kernel_root"
    build_output="$run/build-output"
    mkdir -p "$build_output"
    # O= is a direct child of the source on purpose. Kbuild then sets
    # srctree=.. and passes relative source names to Clang. With a sibling O=,
    # ThinLTO records the unique absolute run path in module .rodata.
    kernel_out="$build_kernel_root/out-u11"
    echo "Ejecutando el perfil U11 fijo dentro de $build_kernel_root"
    "$build_tool" \
        --run-root "$run" \
        --kernel "$build_kernel_root" \
        --out "$kernel_out" \
        --dist "$build_output/dist" \
        --patch-dir "$run/tools/patches/wifi" \
        --patch-manifest "$run/tools/u11-patches.sha256" \
        --fragment "$run/tools/gts9fe-linux.fragment" \
        --jobs "$build_jobs"
else
    echo "Sólo inspección: no se ejecuta ningún build de terceros."
fi
GUEST_SCRIPT
guest_status=${PIPESTATUS[0]}
set -e

# Export only small evidence files. Sources, tarballs, kernel objects and
# build outputs remain on ext4, so a host rerun cannot overwrite current U3
# sources or artifacts.
for evidence in STATUS archive-manifest.json release-layout.json composite-layout.json overlay-manifest.txt build-metadata.txt; do
    if limactl copy --backend=scp "$VM:$guest_run/$evidence" "$host_run/" 2>/dev/null; then
        :
    else
        echo "Aviso: no se pudo copiar $evidence desde el guest" >&2
    fi
done
if limactl copy --backend=scp "$VM:$guest_run/logs/u11-build.log" "$host_run/"; then
    :
else
    echo "Aviso: no se pudo copiar el log de build desde el guest" >&2
fi

if [ "$MODE" = build ] && [ "$guest_status" -eq 0 ]; then
    if limactl copy --backend=scp -r "$VM:$guest_run/build-output/dist" "$host_run/"; then
        python3 - "$host_run/dist" <<'PY'
import hashlib
import pathlib
import re
import sys

root = pathlib.Path(sys.argv[1])
manifest = root / "SHA256SUMS"
if not manifest.is_file():
    raise SystemExit("Falta SHA256SUMS en el dist U11 exportado")
for number, raw in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
    match = re.fullmatch(r"([0-9a-f]{64})  (.+)", raw)
    if not match:
        raise SystemExit(f"SHA256SUMS inválido en línea {number}")
    expected, relative = match.groups()
    path = root / relative
    path.resolve().relative_to(root.resolve())
    if not path.is_file():
        raise SystemExit(f"Falta artefacto exportado: {relative}")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise SystemExit(f"Hash distinto tras exportar: {relative}")
PY
    else
        echo "No se pudo exportar el dist U11; el build queda sólo en ext4." >&2
        exit 1
    fi
fi

printf 'Registro host: %s\nGuest ext4: %s\n' "$host_run" "$guest_run"
exit "$guest_status"
