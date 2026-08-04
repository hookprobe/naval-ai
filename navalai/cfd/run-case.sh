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

say "blockMesh ..."
blockMesh > log.blockMesh 2>&1
say "surfaceFeatureExtract ..."
surfaceFeatureExtract > log.surfaceFeatures 2>&1 || true
say "snappyHexMesh ..."
snappyHexMesh -overwrite > log.snappy 2>&1
say "checkMesh ..."
checkMesh > log.checkMesh 2>&1 || say "WARN: checkMesh reported errors"
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
