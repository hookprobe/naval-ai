#!/usr/bin/env bash
# OpenFOAM resistance case runner (metal-gated: needs OpenFOAM 2306+).
# Usage: ./run-case.sh <case-dir> [n-procs] [--force]
# Produces postProcessing/forces/0/force.dat consumed by navalai.cfd.post.
set -euo pipefail

# --force (or FORCE=1) proceeds past a mesh-quality refusal. It exists so a
# deliberate experiment on a known-bad mesh is possible; it must never be the
# default, because a degenerate cell does not degrade a run, it invalidates it.
FORCE="${FORCE:-0}"
ARGS=()
for a in "$@"; do
  case "$a" in
    --force) FORCE=1 ;;
    *) ARGS+=("$a") ;;
  esac
done
set -- "${ARGS[@]+"${ARGS[@]}"}"

CASE="${1:?usage: run-case.sh <case-dir> [n-procs] [--force]}"
NP="${2:-4}"

[ -d "$CASE" ] || { echo "FATAL: case dir '$CASE' does not exist." \
  "Generate it first: python scripts/make_case.py --out <dir> [--triplet]"; exit 2; }
[ -f "$CASE/system/controlDict" ] || { echo "FATAL: '$CASE' is not an" \
  "OpenFOAM case (no system/controlDict)"; exit 2; }
command -v interFoam >/dev/null || { echo "FATAL: OpenFOAM not in PATH" \
  "(run inside an 'openfoam' session)"; exit 2; }

cd "$CASE"
say() { echo "[$CASE] $1"; }

# --- ONE SOLVE AT A TIME, CHECKED FIRST ------------------------------------
# This Mac has 15 cores and np=10 is the measured optimum for a SINGLE job.
# Three 10-rank jobs were once left running concurrently: load average 51.5,
# every rank at ~46% of a core, and each case at roughly a third of its proper
# speed — which reads as "the solver is slow" rather than "you are
# oversubscribed 3x". Refuse rather than crawl.
#
# THIS CHECK USED TO SIT AFTER THE ENTIRE MESH BUILD, and everything about that
# placement was wrong:
#   - it came after `rm -rf constant/polyMesh processor*`, so a run that was
#     about to be REFUSED had already destroyed the mesh it was refused for;
#   - it came after the resume early-exit, so in the normal (resuming) mode —
#     the mode this machine runs in, because it thermal-sleeps — it never fired
#     at all, which is exactly when a second solve is most likely to be running;
#   - it came BEFORE the MESH_ONLY exit, so the 2-minute mesh sweeps CLAUDE.md
#     recommends running while a solve is in progress were refused, and
#     `run_campaign.sh` retries exit 3 up to 20 times;
#   - `pgrep -f "interFoam -parallel"` misses `interFoam` run serially (NP=1),
#     which is the same machine and the same cores.
# It is now first, it matches both paths by process name, and MESH_ONLY skips it
# because meshing is not the thing that oversubscribes the box.
# `pgrep -x interFoam` matches the SOLVER PROCESS by name, which is what both
# the serial run and every mpirun rank actually is; the -f pattern additionally
# catches the mpirun wrapper. Neither matches `tail -f .../log.interFoam`, which
# a bare `pgrep -f interFoam` would — and CLAUDE.md tells people to run exactly
# that, so a looser pattern would refuse runs because someone is watching one.
solve_running() {
  pgrep -x interFoam > /dev/null 2>&1 ||
  pgrep -f "interFoam -parallel" > /dev/null 2>&1
}
if [ "${MESH_ONLY:-0}" != "1" ] && solve_running; then
  say "FATAL: an interFoam solve is already running on this machine."
  say "       $(pgrep -xl interFoam 2>/dev/null | head -1)"
  say "       np is per-MACHINE, not per-job. Wait for it, or kill it first."
  say "       (MESH_ONLY=1 sweeps are exempt and may run alongside a solve.)"
  exit 3
fi

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

# A full (re-)mesh must start from pristine initial fields and no stale mesh
# artifacts. setFields leaves 0/alpha.water as a non-uniform field sized for
# the PREVIOUS mesh, and snappyHexMesh then dies with an FPE in
# markFeatureCellLevel (exit 132) on a case that meshed cleanly before.
if [ -d 0.orig ]; then
  say "restoring pristine 0/ from 0.orig (re-mesh must be idempotent)"
  rm -rf 0 && cp -R 0.orig 0
else
  say "WARNING: no 0.orig — cannot guarantee a clean re-mesh"
fi
rm -rf constant/polyMesh constant/extendedFeatureEdgeMesh processor*

say "blockMesh ..."
blockMesh > log.blockMesh 2>&1
say "surfaceFeatureExtract ..."
surfaceFeatureExtract > log.surfaceFeatures 2>&1 || true


# STAGED snappy. The z-only refineMesh rounds have to happen BETWEEN snapping
# and layer addition, and the ordering is forced from both sides:
#   - AFTER snapping, because snapping an anisotropic cell folds it inside out
#     (the 38:1 background incident) — snappy must see cubic cells;
#   - BEFORE layers, because refining z HALVES the prism cells. Measured with
#     the rounds last: min z edge went 1.3e-4 -> 3.8e-5 -> 1.1e-5 m over three
#     rounds and checkMesh found 72988 zero-volume cells. An 11 micron cell in
#     a 0.7 mm boundary layer is a destroyed boundary layer, not a fine one.
say "snappyHexMesh pass 1 (castellate + snap, NO layers) ..."
snappyHexMesh -overwrite > log.snappy 2>&1
# Anisotropic free-surface refinement AFTER snappy. Order matters both ways:
# snappy gets a clean isotropic octree (its comfort zone, and the best chance
# of inserting prism layers), and refineMesh then splits x,y ONLY in the wave
# band, which snappy never has to understand. The topoSet subtracts a shield
# around the hull so the prism layers just built are not split.
ROUNDS=0
for _f in system/topoSetDict.*; do [ -e "$_f" ] && ROUNDS=$((ROUNDS + 1)); done
if [ "$ROUNDS" -gt 0 ]; then
  for i in $(seq 1 "$ROUNDS"); do
    say "free-surface refine round $i/$ROUNDS (z only, hull shielded) ..."
    topoSet -dict "system/topoSetDict.$i" > "log.topoSet.$i" 2>&1 || \
      { say "FATAL: topoSet round $i failed — see log.topoSet.$i"; exit 1; }
    refineMesh -dict system/refineMeshDict -overwrite > "log.refineMesh.$i" 2>&1 || \
      { say "FATAL: refineMesh round $i failed — see log.refineMesh.$i"; exit 1; }
  done

  # snappy leaves its octree bookkeeping (cellLevel/pointLevel/polyMesh) in 0/
  # as well as constant/polyMesh. refineMesh -overwrite updates only the latter,
  # so 0/ keeps a cellLevel sized for the PRE-refinement mesh and decomposePar
  # dies with "Size 230265 is not equal to the expected length 920407". These
  # are mesh topology, not initial conditions — the mesh in constant/ is the
  # authority, so drop the stale copies.
  rm -rf 0/cellLevel 0/pointLevel 0/polyMesh 0/refinementHistory 0/surfaceIndex
  # refineMesh does not maintain snappy's octree bookkeeping, so what is left in
  # constant/polyMesh describes the PRE-refinement mesh. Layer addition uses
  # absolute thicknesses (relativeSizes false), so it does not need the levels —
  # but it does refuse to read ones of the wrong length.
  rm -f constant/polyMesh/cellLevel constant/polyMesh/pointLevel \
        constant/polyMesh/level0Edge constant/polyMesh/surfaceIndex \
        constant/polyMesh/refinementHistory

  say "snappyHexMesh pass 2 (layers only, on the z-refined mesh) ..."
  snappyHexMesh -overwrite -dict system/snappyHexMeshDict.layers \
    > log.snappy.layers 2>&1 || \
    { say "FATAL: layer pass failed — see log.snappy.layers"; exit 1; }
fi

say "checkMesh ..."
checkMesh > log.checkMesh 2>&1 || true
# Report mesh quality rather than bury it: free-surface grading leaves ~20:1
# cells where the hull pierces the waterline, so a handful of skew faces is
# expected — but it must be VISIBLE and tracked, not discovered months later.
say "mesh: $(grep -m1 'cells:' log.checkMesh | tr -s ' ') | \
$(grep -m1 'non-orthogonality Max' log.checkMesh | tr -s ' ' | cut -c1-46) | \
$(grep -m1 'Max skewness' log.checkMesh | tr -s ' ' | sed 's/^ *//' | cut -c1-40)"
# LAYER COVERAGE IS MEASURED FROM THE CELL DELTA, NOT FROM THE TABLE.
#
# This block used to parse the `patch faces layers avg thickness` table and
# report "n=3, near-wall 0.000795 m (11175 faces)". That table is the layer
# specification snappy was ASKED for — it is printed at log line 246, BEFORE
# `Outer iteration : 0` at line 251 — and it prints identically whether the
# extrusion succeeds or fails completely. The old comment here asserted the
# opposite and dismissed the "Added N out of M cells" lines as misleading.
#
# MEASURED 2026-08-06 on runs/kcs_sym, the mesh that had been solving for
# hours, and on a freshly generated runs/kcs_gci2/coarse:
#     Initial mesh : cells:241946
#     Layer mesh   : cells:241946          <-- zero cells added
#     Extruding 0 out of 11175 faces (0%)
#     Added 0 out of 33525 cells (0%)
# Independent geometric check: wall-normal distance from each hull face to its
# owner cell centre had p50 = 10.62 mm against a requested first-layer
# half-height of 0.397 mm, and 0 of 11175 faces below 1 mm. Measured y+ on the
# hull averaged 644. There were NO PRISM LAYERS AT ALL, and both CLAUDE.md and
# this script had been reporting full coverage for weeks.
#
# A wall model with no boundary-layer mesh is not a degraded result, it is a
# different simulation. So this is FATAL unless LAYERS_OPTIONAL=1.
_LAYERLOG=log.snappy; [ -s log.snappy.layers ] && _LAYERLOG=log.snappy.layers
_L_INIT=$(awk '/^Initial mesh :/ {gsub(/cells:/,"",$4); print $4}' "$_LAYERLOG" | tail -1)
_L_FINAL=$(awk '/^Layer mesh :/  {gsub(/cells:/,"",$4); print $4}' "$_LAYERLOG" | tail -1)
_L_ADDED=$(( ${_L_FINAL:-0} - ${_L_INIT:-0} ))
_L_WANT=$(awk '/Added [0-9]+ out of [0-9]+ cells/ {print $5}' "$_LAYERLOG" | tail -1)
_L_SPEC=$(awk '/^hull +[0-9]/ {print "requested n="$3", first "$4" m"}' "$_LAYERLOG" | tail -1)
if [ "${_L_ADDED:-0}" -le 0 ]; then
  say "FATAL: layer addition produced ZERO cells (${_L_SPEC:-no spec found})."
  say "       The hull has no prism layers, so y+ is uncontrolled and the wall"
  say "       model is invalid. See log.snappy.layers 'Extruding 0 out of ...'."
  say "       Set LAYERS_OPTIONAL=1 to proceed deliberately anyway."
  [ "${LAYERS_OPTIONAL:-0}" = "1" ] || exit 1
else
  say "layers: ADDED ${_L_ADDED} of ${_L_WANT:-?} cells ($(awk -v a="$_L_ADDED" -v w="${_L_WANT:-1}" 'BEGIN{printf "%.1f", 100*a/w}')%), ${_L_SPEC}"
fi
grep -q 'Mesh OK' log.checkMesh || say "NOTE: checkMesh flagged $(grep -c 'Failed' log.checkMesh) check(s) — see log.checkMesh"

# CHECKMESH HAD NO FATAL THRESHOLD AT ALL. It ran with `|| true` and the only
# consequence was the NOTE above, so a mesh with degenerate cells went straight
# into a multi-hour solve. Two counts are read, and they are treated
# differently because the measurements say different things:
#
#   ZERO-VOLUME CELLS -> FATAL AT 1. Every mesh in this project that solved had
#   zero (the fixed KCS meshes at all three refinement levels: 0, 0, 0); every
#   mesh that died had some (72988 with the refineMesh rounds last, 20 on the
#   (4,5)/n=4 sweep, 14 on the mirrored KCS.igs path). A cell of zero volume is
#   CLAUDE.md's documented pathological-cell signature: no timestep can fix it,
#   the adaptive controller shrinks deltaT to ~1e-40 and interFoam dies with an
#   FPE in the GAMG p_rgh solve.
#
#   INCORRECTLY-ORIENTED FACES -> FATAL AT 10, not at 1, and the bar is
#   CALIBRATED BETWEEN THE TWO MEASUREMENTS WE HAVE rather than set to the
#   comfortable value:
#       5  faces -> the fixed KCS mesh, which SOLVES (CLAUDE.md records it)
#       73 faces -> the mirrored KCS.igs mesh, which dies on the first timestep
#   Setting this to zero would refuse a mesh measured to work, which is the
#   mirror image of softening a gate and just as dishonest. Move it when a
#   measurement says to.
_MQ_ZEROVOL=$(awk '/zero volume cells to set zeroVolumeCells/ {print $2}' log.checkMesh | tail -1)
_MQ_WRONGOR=$(awk '/faces with incorrect orientation to set wrongOrientedFaces/ {print $2}' log.checkMesh | tail -1)
_MQ_ZEROVOL=${_MQ_ZEROVOL:-0}; _MQ_WRONGOR=${_MQ_WRONGOR:-0}
say "mesh quality: ${_MQ_ZEROVOL} zero-volume cell(s), ${_MQ_WRONGOR} incorrectly-oriented face(s)"
echo "checkmesh_zero_volume_cells=${_MQ_ZEROVOL}" >> case.info
echo "checkmesh_wrong_oriented_faces=${_MQ_WRONGOR}" >> case.info
if [ "$_MQ_ZEROVOL" -gt 0 ] || [ "$_MQ_WRONGOR" -gt 10 ]; then
  say "FATAL: mesh quality below the bar (${_MQ_ZEROVOL} zero-volume cells,"
  say "       ${_MQ_WRONGOR} incorrectly-oriented faces; bars are 0 and 10)."
  say "       A degenerate cell does not degrade a solve, it invalidates it:"
  say "       deltaT collapses to ~1e-40 while Courant stays high and interFoam"
  say "       dies in the GAMG p_rgh solve. Re-mesh; do not spend hours on this."
  say "       Pass --force (or FORCE=1) to run it anyway, deliberately."
  [ "$FORCE" = "1" ] || exit 1
  say "       --force given: proceeding on a mesh that failed the bar."
fi
# TET-DECOMPOSITION RECEIPT. minTetQuality is DISABLED during layer addition
# (see the meshQualityControls comment in case.py: enforcing it there made the
# mesh measurably worse — 18 folded cells against 0). That is a knowing trade,
# but the mesh-motion machinery used by free sinkage and trim DOES consume the
# tet decomposition, so the finished mesh is re-checked against a real bar and
# the number is recorded rather than left unknown.
# checkMesh in v2606 takes NO -dict; -meshQuality reads system/meshQualityDict.
cat > system/meshQualityDict <<'TETEOF'
FoamFile { version 2.0; format ascii; class dictionary; object meshQualityDict; }
#includeEtc "caseDicts/meshQualityDict"
minTetQuality 1e-15;
TETEOF
checkMesh -meshQuality > log.checkMesh.tet 2>&1 || true
_TETBAD=$(awk '/tet quality/ {print $NF}' log.checkMesh.tet | tail -1)
say "tet-decomposition check (minTetQuality 1e-15 on the FINISHED mesh): ${_TETBAD:-not reported} bad faces"
echo "tet_bad_faces_at_1e-15=${_TETBAD:-unknown}" >> case.info
# MESH_ONLY exists so the robustness harness measures THIS pipeline. It used
# to call `snappyHexMesh -overwrite` itself, which was a fair copy of the
# single-pass mesher and is now simply a different mesher: it skips the z-only
# refineMesh rounds and the separate layer pass, so with staged meshing it
# would have graded a layerless mesh and called the result a success rate.
if [ "${MESH_ONLY:-0}" = "1" ]; then
  say "MESH_ONLY=1 — stopping after checkMesh"
  exit 0
fi

# setFields IS NOT OPTIONAL, AND `|| true` SAID IT WAS.
# It is what puts water in the tank: `0.orig/alpha.water` is uniform 0, and
# every cell below z=0 is filled by the boxToCell entry here. If setFields
# fails the solve starts in PURE AIR, runs to completion, writes forces, and
# reports a drag that is ~1/800 of the right one — a plausible-looking number
# from a tank with no water in it. The `boxToFace` entry (written only for
# moving cases) is exactly the kind of selector that can be rejected on a
# version mismatch, so this failure mode is reachable, not hypothetical.
say "setFields ..."
setFields > log.setFields 2>&1 || {
  say "FATAL: setFields failed — see log.setFields."
  say "       The tank would start as PURE AIR and the run would produce a"
  say "       complete, plausible, meaningless force history."
  exit 1
}
if [ "$NP" -gt 1 ]; then
  # Reconcile the rank count with the dict BEFORE meshing costs anything.
  # A mismatch is only discovered by interFoam, which aborts after the whole
  # mesh has been built — twice now. decomposeParDict is the case's own
  # declaration, so rewrite it to what was actually asked for.
  _WANT=$(foamDictionary -entry numberOfSubdomains -value system/decomposeParDict 2>/dev/null || echo "$NP")
  if [ "$_WANT" != "$NP" ]; then
    say "decomposeParDict says $_WANT ranks, run asked for $NP — using $NP"
    foamDictionary -entry numberOfSubdomains -set "$NP" system/decomposeParDict > /dev/null
    foamDictionary -entry hierarchicalCoeffs/n -set "($NP 1 1)" system/decomposeParDict > /dev/null 2>&1 || true
    rm -rf processor*
  fi
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
