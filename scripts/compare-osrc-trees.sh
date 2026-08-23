#!/usr/bin/env bash
set -euo pipefail

# Thin host-only entry point.  It deliberately does not unwrap archives,
# poll downloads, or accept a .part file as a source tree; pass an extracted
# U11 checkout when Samsung publishes it.
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
exec python3 "$ROOT/tools/osrc_tree_compare.py" "$@"
