#!/usr/bin/env bash
# OpenFOAM resistance case runner (metal-gated: needs OpenFOAM 2306+).
# Usage: ./run-case.sh <case-dir> [n-procs]
# Produces postProcessing/forces/0/force.dat consumed by navalai.cfd.post.
set -euo pipefail
CASE="${1:?usage: run-case.sh <case-dir> [n-procs]}"
NP="${2:-4}"

[ -d "$CASE" ] || { echo "FATAL: case dir '$CASE' does not exist." \
  "Generate it first: python scripts/make_case.py --out <dir> [--triplet]"; exit 2; }
[ -f "$CASE/system/controlDict" ] || { echo "FATAL: '$CASE' is not an" \
  "OpenFOAM case (no system/controlDict)"; exit 2; }
command -v interFoam >/dev/null || { echo "FATAL: OpenFOAM not in PATH" \
  "(run inside an 'openfoam' session)"; exit 2; }

cd "$CASE"
say() { echo "[$CASE] $1"; }

# --- resume support -------------------------------------------------------
# This machine has no working cooling and has already lost a triplet to
# 'Thermal Emergency Sleep' (power log, 2026-08-04 23:19). A multi-hour run
# that always restarts from t=0 can never finish on hardware that naps, so a
# case with a decomposed mesh and at least one written time resumes instead
# of re-meshing. interFoam checkpoints every writeInterval anyway; this just
# stops us throwing those checkpoints away.
latest_proc_time() {
  local best=0 t
  for d in processor0/*/; do
    t="${d#processor0/}"; t="${t%/}"
    case "$t" in ''|*[!0-9.]*) continue;; esac
    awk -v a="$t" -v b="$best" 'BEGIN{exit !(a+0>b+0)}' && best="$t"
  done
  echo "$best"
}

# Resume is only valid against a decomposition of the SAME width: mpirun -np N
# against N' processor dirs either fails or silently reads the wrong ranks.
NPROC_DIRS="$(find . -maxdepth 1 -type d -name 'processor*' | wc -l | tr -d ' ')"
RESUME_FROM=""
if [ -d processor0 ] && [ -f constant/polyMesh/points ]; then
  if [ "$NPROC_DIRS" = "$NP" ]; then
    RESUME_FROM="$(latest_proc_time)"
  else
    say "decomposition is ${NPROC_DIRS}-way but NP=$NP — re-meshing from scratch"
    rm -rf processor*
  fi
fi

if [ -n "$RESUME_FROM" ] && [ "$RESUME_FROM" != "0" ]; then
  say "RESUMING from t=$RESUME_FROM (mesh + decomposition reused)"
  foamDictionary -entry startFrom -set latestTime system/controlDict >/dev/null
  say "interFoam -parallel (resume; tail -f $CASE/log.interFoam) ..."
  mpirun -np "$NP" interFoam -parallel >> log.interFoam 2>&1
  reconstructPar -latestTime > log.reconstruct 2>&1
  say "done: $(ls postProcessing/forces/ 2>/dev/null | tr '\n' ' ' || echo 'NO FORCES')"
  exit 0
fi

say "blockMesh ..."
blockMesh > log.blockMesh 2>&1
say "surfaceFeatureExtract ..."
surfaceFeatureExtract > log.surfaceFeatures 2>&1 || true
say "snappyHexMesh ..."
snappyHexMesh -overwrite > log.snappy 2>&1
say "checkMesh ..."
checkMesh > log.checkMesh 2>&1 || true
# Report mesh quality rather than bury it: free-surface grading leaves ~20:1
# cells where the hull pierces the waterline, so a handful of skew faces is
# expected — but it must be VISIBLE and tracked, not discovered months later.
say "mesh: $(grep -m1 'cells:' log.checkMesh | tr -s ' ') | \
$(grep -m1 'non-orthogonality Max' log.checkMesh | tr -s ' ' | cut -c1-46) | \
$(grep -m1 'Max skewness' log.checkMesh | tr -s ' ' | sed 's/^ *//' | cut -c1-40)"
say "layers: $(grep -oE 'Added [0-9]+ out of [0-9]+ cells \([0-9.]+%\)' log.snappy \
  | head -1 || echo 'none reported')"
grep -q 'Mesh OK' log.checkMesh || say "NOTE: checkMesh flagged $(grep -c 'Failed' log.checkMesh) check(s) — see log.checkMesh"
setFields > log.setFields 2>&1 || true
if [ "$NP" -gt 1 ]; then
  say "decomposePar ($NP ranks) ..."
  decomposePar -force > log.decompose 2>&1
  say "interFoam -parallel (tail -f $CASE/log.interFoam to watch) ..."
  mpirun -np "$NP" interFoam -parallel > log.interFoam 2>&1
  reconstructPar -latestTime > log.reconstruct 2>&1
else
  say "interFoam ..."
  interFoam > log.interFoam 2>&1
fi
say "done: $(ls postProcessing/forces/0/ 2>/dev/null || echo 'NO FORCES OUTPUT')"
