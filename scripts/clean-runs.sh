#!/usr/bin/env bash
# Strip bulky intermediates from OpenFOAM run dirs, KEEPING the valuables:
#   postProcessing/ (force histories), log.*, case.info, system/, 0/
# Removes: processor dirs, time dirs, meshes, debug OBJs, eMesh caches.
# Usage:  scripts/clean-runs.sh runs/gci/coarse [more dirs...]
#         scripts/clean-runs.sh --all runs/gci      (all subdirs)
#         scripts/clean-runs.sh --purge runs/smoke  (delete entirely)
set -euo pipefail
[ $# -ge 1 ] || { echo "usage: clean-runs.sh [--all|--purge] <dir>..."; exit 2; }

MODE=trim
case "$1" in
  --all)   MODE=all;   shift ;;
  --purge) MODE=purge; shift ;;
esac

trim() {
  local d="$1"
  [ -d "$d" ] || { echo "skip (not a dir): $d"; return; }
  local before
  before=$(du -sh "$d" 2>/dev/null | cut -f1)
  rm -rf "$d"/processor* \
         "$d"/constant/polyMesh \
         "$d"/constant/extendedFeatureEdgeMesh \
         "$d"/constant/triSurface/*.eMesh
  # numeric time dirs except 0
  find "$d" -maxdepth 1 -type d -regex '.*/[0-9]+\.?[0-9]*' \
       ! -name 0 -exec rm -rf {} + 2>/dev/null || true
  local after
  after=$(du -sh "$d" 2>/dev/null | cut -f1)
  echo "trimmed $d: $before -> $after (kept postProcessing/, logs, case.info)"
}

for target in "$@"; do
  case "$MODE" in
    purge) rm -rf "$target"; echo "purged $target" ;;
    all)   for sub in "$target"/*/; do trim "${sub%/}"; done ;;
    trim)  trim "$target" ;;
  esac
done
