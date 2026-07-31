#!/usr/bin/env bash
# OpenFOAM resistance case runner (metal-gated: needs OpenFOAM 2306+).
# Usage: ./run-case.sh <case-dir> [n-procs]
# Produces postProcessing/forces/0/force.dat consumed by navalai.cfd.post.
set -euo pipefail
CASE="${1:?usage: run-case.sh <case-dir> [n-procs]}"
NP="${2:-4}"
cd "$CASE"

command -v interFoam >/dev/null || { echo "FATAL: OpenFOAM not in PATH"; exit 2; }

blockMesh > log.blockMesh 2>&1
surfaceFeatureExtract > log.surfaceFeatures 2>&1 || true
snappyHexMesh -overwrite > log.snappy 2>&1
checkMesh > log.checkMesh 2>&1 || { echo "WARN: checkMesh reported errors"; }
setFields > log.setFields 2>&1 || true
if [ "$NP" -gt 1 ]; then
  decomposePar -force > log.decompose 2>&1
  mpirun -np "$NP" interFoam -parallel > log.interFoam 2>&1
  reconstructPar -latestTime > log.reconstruct 2>&1
else
  interFoam > log.interFoam 2>&1
fi
echo "done: $(ls postProcessing/forces/0/ 2>/dev/null || echo 'NO FORCES OUTPUT')"
