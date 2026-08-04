#!/usr/bin/env bash
# Run a GCI triplet to completion on hardware that naps.
#
# This Mac has no working cooling and has already lost a triplet to
# 'Thermal Emergency Sleep' (power log, 2026-08-04 23:19) with the fine grid
# never started. A single run-case.sh invocation cannot finish an 8 h solve
# there, so each grid is re-invoked until it actually reaches endTime;
# run-case.sh resumes from the latest checkpoint rather than re-meshing.
#
# Usage (inside an openfoam session, or via `openfoam scripts/run_campaign.sh`):
#   scripts/run_campaign.sh runs/gci 6 [max-attempts]
#
# NP defaults to 6 rather than the 10 performance cores: the point is a run
# that FINISHES, and fewer hot cores is the only cooling knob we have.
set -uo pipefail

ROOT="${1:?usage: run_campaign.sh <triplet-root> [np] [max-attempts]}"
NP="${2:-6}"
MAX="${3:-20}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

end_time_of()  { foamDictionary -entry endTime  -value "$1/system/controlDict"; }
latest_of() {
  local best=0 t
  for d in "$1"/processor0/*/; do
    t="${d##*/processor0/}"; t="${t%/}"
    case "$t" in ''|*[!0-9.]*) continue;; esac
    awk -v a="$t" -v b="$best" 'BEGIN{exit !(a+0>b+0)}' && best="$t"
  done
  echo "$best"
}

for GRID in coarse medium fine; do
  CASE="$ROOT/$GRID"
  [ -d "$CASE" ] || { echo "[campaign] skip $GRID (no case dir)"; continue; }
  END="$(end_time_of "$CASE" 2>/dev/null || echo 0)"

  for attempt in $(seq 1 "$MAX"); do
    NOW="$(latest_of "$CASE")"
    if awk -v a="$NOW" -v b="$END" 'BEGIN{exit !(a+0 >= b+0-1e-6)}'; then
      echo "[campaign] $GRID COMPLETE at t=$NOW/$END"
      break
    fi
    echo "[campaign] $GRID attempt $attempt/$MAX (at t=$NOW/$END) $(date +%H:%M:%S)"
    "$HERE/navalai/cfd/run-case.sh" "$CASE" "$NP" || \
      echo "[campaign] $GRID attempt $attempt returned non-zero — will resume"

    # If a nap killed it, the machine may still be hot; let it breathe.
    AFTER="$(latest_of "$CASE")"
    if ! awk -v a="$AFTER" -v b="$END" 'BEGIN{exit !(a+0 >= b+0-1e-6)}'; then
      echo "[campaign] $GRID interrupted at t=$AFTER — cooling 120 s before resume"
      sleep 120
    fi
  done

  FINAL="$(latest_of "$CASE")"
  awk -v a="$FINAL" -v b="$END" 'BEGIN{exit !(a+0 >= b+0-1e-6)}' || \
    echo "[campaign] WARNING: $GRID stopped at t=$FINAL of $END after $MAX attempts"
done

echo "[campaign] done $(date +%H:%M:%S)"
