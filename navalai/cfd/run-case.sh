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

# AUDIT G8.1 (2026-08-14): the solver ran UNBOUNDED — a diverging interFoam
# (deltaT ~1e-40, Courant blowup: both documented below) would sit forever
# with the "already running" guard then refusing every later run on the
# machine. SOLVER_TIMEOUT is a HANG GUARD, not a latency bar: 6h default
# covers every measured Mac solve (minutes to ~1h) with an order of
# magnitude to spare; 0 disables it for a deliberately long campaign.
# Portable watchdog (macOS ships no GNU `timeout`), with a VERIFIED kill:
# the TERM is followed up, and surviving ranks are reported by name.
# RECEIPTS ARE REWRITTEN, NOT APPENDED (see the measured duplicate-receipt
# incident where this function is used, further down). Defined here at the
# top because run_solver's early-abort path writes receipts and the RESUME
# branch calls run_solver before the mesh-receipt section executes.
_mq_record() {
  grep -v "^$1=" case.info > case.info.tmp 2>/dev/null || : > case.info.tmp
  mv case.info.tmp case.info
  echo "$1=$2" >> case.info
}

SOLVER_TIMEOUT="${SOLVER_TIMEOUT:-21600}"
# run_solver append|trunc <logfile> <cmd...> — the solver's output goes to
# the log; the watchdog's own FATAL lines stay on the console (a timeout
# notice buried inside log.interFoam is a notice nobody sees).
run_solver() {
  rs_mode=$1; rs_log=$2; shift 2
  if [ "$rs_mode" = append ]; then
    "$@" >> "$rs_log" 2>&1 &
  else
    "$@" > "$rs_log" 2>&1 &
  fi
  solver_pid=$!
  waited=0
  while kill -0 "$solver_pid" 2>/dev/null; do
    if [ "$SOLVER_TIMEOUT" -gt 0 ] && [ "$waited" -ge "$SOLVER_TIMEOUT" ]; then
      say "FATAL: solver exceeded SOLVER_TIMEOUT=${SOLVER_TIMEOUT}s; killing PID $solver_pid"
      kill "$solver_pid" 2>/dev/null || true
      sleep 5
      kill -9 "$solver_pid" 2>/dev/null || true
      wait "$solver_pid" 2>/dev/null || true
      if pgrep -x interFoam >/dev/null 2>&1; then
        say "FATAL: interFoam ranks SURVIVED the kill: $(pgrep -xl interFoam | head -3 | tr '\n' ' ')"
        say "       clean up by hand before the next run."
      fi
      exit 124
    fi
    # EARLY ABORT ON FLOW-TIME-SCALE COLLAPSE (MEASURED 2026-08-18, the Mac's
    # paired dataset, filed in docs/audit/STATUS.md). Every checkMesh metric
    # is blind to the solve-killing cell class: zero_volume/wrong_oriented/
    # skewness are indistinguishable across the five solved hulls and the two
    # dead ones, while min_flow_time_scale separates them by TWELVE orders
    # (solved 7.8e-6..2.1e-5; diverged 4.356e-18). LTS interFoam prints
    # "Flow time scale min/max = ..." EVERY iteration, so the pathology is
    # visible within the first seconds of a solve — h18 burned 2700 s to a
    # timeout for want of this check. The bar is 1e-12, RE-BASED with this
    # dataset: the older 1e-20 bar was placed against a 1e-40-class
    # divergence and MISSES h18's 4.356e-18. Anchors: solved floor 7.8e-6,
    # worst divergence 4.356e-18 — ~5.9 and ~5.6 orders of margin. A
    # collapse is a MESH verdict
    # delivered by the solver, not a solver failure — the receipt says which.
    _fts=$(tail -c 65536 "$rs_log" 2>/dev/null | \
           awk '/^Flow time scale min\/max = / {v=$6; sub(/,$/,"",v)} END{print v}')
    if [ -n "$_fts" ] && \
       awk -v v="$_fts" 'BEGIN{exit !(v + 0 < 1e-12)}'; then
      say "FATAL: local flow time scale collapsed to ${_fts} s (bar 1e-12)."
      say "       This is a PATHOLOGICAL CELL, not a solver problem: a cell"
      say "       whose V/(A*U) is below the bar cannot be integrated, deltaT"
      say "       degrades locally and the run diverges or hangs. checkMesh"
      say "       is measured BLIND to this class — do not re-run; re-mesh."
      _mq_record solve_verdict pathological-cell-flow-time-collapse
      _mq_record min_flow_time_scale_at_abort "$_fts"
      kill "$solver_pid" 2>/dev/null || true
      sleep 5
      kill -9 "$solver_pid" 2>/dev/null || true
      wait "$solver_pid" 2>/dev/null || true
      if pgrep -x interFoam >/dev/null 2>&1; then
        say "FATAL: interFoam ranks SURVIVED the kill: $(pgrep -xl interFoam | head -3 | tr '\n' ' ')"
        say "       clean up by hand before the next run."
      fi
      exit 125
    fi
    sleep 10
    waited=$((waited + 10))
  done
  wait "$solver_pid"
}

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
  run_solver append log.interFoam mpirun -np "$NP" interFoam -parallel
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

# THE SURFACE IS CHECKED BEFORE ANYTHING SNAPS TO IT. Until 2026-08-12 this
# pipeline ran `surfaceCheck` NOWHERE — the string appears in the Blender
# comparison scripts and in CLAUDE.md's advice, and in no code that meshes a
# hull. So every case this project has generated snapped to an unverified
# surface, and the two checks that CLAUDE.md names as mandatory
# ("run surfaceCheck -checkSelfIntersection; plain surfaceCheck calls a broken
# surface fine") had never run on our own hulls at all.
#
# SELF-INTERSECTIONS ARE FATAL, and the flag matters: plain `surfaceCheck`
# reports a self-intersecting surface as clean, which is why the long form is
# spelled out here rather than left to a default.
#
# Cost is ~1 s against a mesh measured in minutes, so this is not a trade.
# It is EXPECTED to pass on our own hulls — trimesh, PyMeshLab and Open3D each
# find zero self-intersections across all 25 (commit 749801c) — and that is the
# point: a guard whose first run is the day it fires is a guard nobody trusts.
if command -v surfaceCheck >/dev/null 2>&1; then
  say "surfaceCheck -checkSelfIntersection ..."
  surfaceCheck -checkSelfIntersection constant/triSurface/hull.stl \
      > log.surfaceCheck 2>&1 || true
  # THE PATTERN IS OPENFOAM'S ACTUAL WORDING, and `|| true` is load-bearing.
  # MEASURED 2026-08-12, by breaking the campaign with the first draft of this
  # block: the pattern was "Found N self-intersection", v2606 writes
  # "Surface is self-intersecting at N locations.", so grep matched nothing,
  # exited 1, and under `set -euo pipefail` a failing command substitution in
  # an assignment KILLS THE SCRIPT. Campaign hulls 63 and 64 died at 1.2 s with
  # no log.blockMesh and were recorded `mesh-build-failed` — a guard that
  # refused two hulls for a defect in its own grep.
  _SI=$(grep -oE "self-intersecting at [0-9]+ location" log.surfaceCheck 2>/dev/null \
        | grep -oE "[0-9]+" | head -1) || true
  # A RECEIPT, NOT A REFUSAL, AND THE DATA SAYS WHY. The first draft made a
  # non-zero count FATAL. MEASURED 2026-08-12 across the seed-0 batch, with
  # self-intersection count against wrongly-oriented faces in the finished
  # mesh:
  #
  #     hull   self-intersections   wrongly-oriented faces
  #     h008          237                    0
  #     h000           42                    0
  #     h063           35                    (never meshed)
  #     h059            9                    2
  #     h039            8                    2
  #     h004            3                    0
  #
  # The hull with the MOST self-intersections meshes perfectly and the two with
  # the fewest are the two misses. The relationship is absent, if anything
  # inverted — so a fatal bar here would have refused hulls that mesh clean,
  # which is a bar calibrated against nothing. Same shape as the STL forensics
  # result (commit 749801c): STL metrics do not separate mesh outcomes.
  #
  # OpenFOAM counts contacts the segment-based Python checks skip (coplanar and
  # shared-edge touches at the deck lid, transom and stem caps), which is the
  # likely reason trimesh/PyMeshLab/Open3D each report ZERO on these same
  # hulls. That disagreement is worth recording and is NOT worth refusing on.
  #
  # `stl_watertight_report` in write_resistance_case stays FATAL, because an
  # open shell is a different simulation (water inside the hull), not a
  # quality metric.
  if grep -q "Checking self-intersection" log.surfaceCheck 2>/dev/null; then
    _SI="${_SI:-0}"
  else
    # The check did not run. UNMEASURED, never assumed zero — the ${VAR:-0}
    # lesson that this file already learned the expensive way.
    _SI="UNMEASURED"
    say "NOTE: surfaceCheck did not reach the self-intersection check"
  fi
  say "surface: self-intersections $_SI (RECORDED, not a bar — see comment)"
  _CLOSED=$(grep -c "Surface is closed" log.surfaceCheck 2>/dev/null) || true
  if [ "${_CLOSED:-0}" -eq 0 ]; then
    say "FATAL: surfaceCheck does not report hull.stl as closed."
    say "       An open shell floods the interior and yields a complete,"
    say "       plausible, meaningless force history."
    [ "$FORCE" = "1" ] || exit 1
  fi
  printf 'stl_self_intersections=%s\nstl_closed=yes\n' "$_SI" >> case.info
else
  say "NOTE: surfaceCheck not on PATH — surface NOT verified before meshing"
fi

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

  # Snapshot the layer-less mesh so a refused layer count can be retried by
  # redoing ONLY the layer pass — castellate/snap/z-refine are the expensive
  # stages and do not depend on the count. Removed after the quality gate.
  rm -rf constant/polyMesh.prelayer
  cp -a constant/polyMesh constant/polyMesh.prelayer
  _LAYERS_DICT=system/snappyHexMeshDict.layers
fi

# LAYER BACKOFF (MEASURED 2026-08-18, the case-a metal check): the derived
# count n=6 produced 16 wrongly-oriented faces (bar 5) and n=5 produced 0 —
# and the ladder that recovers this existed only in scripts/mesh_robustness.py
# while this lane could only print "pass n_layers to the generator" and stop.
# The generator records the measured outward ladder in case.info
# (layer_backoff_ladder=..., holes and both directions — see
# navalai.cfd.case.layer_backoff_ladder); on a quality-bar failure the loop
# below restores the pre-layer snapshot, sets the next recorded count in the
# layers dict, and redoes the layer pass only. LAYER_BACKOFF caps attempts
# (default 3; 0 disables — mesh_robustness.py sets 0 because it measures one
# rung per invocation and a silent re-mesh would corrupt the measurement).
# The loop spans pass 2 -> checkMesh -> the quality gate; every receipt
# inside is written with _mq_record (rewrite, not append), so a retry
# overwrites the failed attempt's lines and the per-attempt history lives in
# layer_backoff_attempt_N.
_BK_LADDER=$(awk -F= '/^layer_backoff_ladder=/ {print $2}' case.info 2>/dev/null | tail -1 | tr ',' ' ' || true)
if [ "$_BK_LADDER" = "none" ]; then _BK_LADDER=""; fi
_BK_MAX="${LAYER_BACKOFF:-3}"
_BK_TRY=0
while :; do
  if [ -n "${_LAYERS_DICT:-}" ]; then
    say "snappyHexMesh pass 2 (layers only, on the z-refined mesh) ..."
    snappyHexMesh -overwrite -dict "$_LAYERS_DICT" \
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
# A RECEIPT IS REWRITTEN, NOT APPENDED. Every invocation appended its lines, so
# a case meshed three times (a MESH_ONLY sweep and then two campaign attempts)
# ended up with three copies of each — MEASURED on runs/val_coarse, whose
# case.info carries checkmesh_wrong_oriented_faces=10 three times over. Whoever
# reads it next gets whichever duplicate they happen to hit, so a receipt from a
# superseded mesh can outlive the mesh that produced it.
# _mq_record is defined at the TOP of this file (it is needed by
# run_solver's early-abort receipt, which the RESUME branch can reach
# before this point in the script).
_LAYERLOG=log.snappy; [ -s log.snappy.layers ] && _LAYERLOG=log.snappy.layers
_L_INIT=$(awk '/^Initial mesh :/ {gsub(/cells:/,"",$4); print $4}' "$_LAYERLOG" | tail -1)
_L_FINAL=$(awk '/^Layer mesh :/  {gsub(/cells:/,"",$4); print $4}' "$_LAYERLOG" | tail -1)
_L_ADDED=$(( ${_L_FINAL:-0} - ${_L_INIT:-0} ))
_L_WANT=$(awk '/Added [0-9]+ out of [0-9]+ cells/ {print $5}' "$_LAYERLOG" | tail -1)
# TWO `hull ...` TABLES, DIFFERENT COLUMNS, AND `tail -1` READ THE WRONG ONE.
# snappy prints the layer SPEC before extrusion and the ACHIEVED result after:
#
#   patch faces    layers avg thickness[m]        (5 fields: NF==5)
#                        near-wall overall
#   hull  11915    7      0.00265   0.0342
#
#   patch faces        layers        overall thickness   (6 fields: NF==6)
#                 target   mesh     [m]       [%]
#   hull  11915    7        5.68     0.0292    85.5
#
# The old `awk '/^hull +[0-9]/ {... "first "$4" m"}' | tail -1` matched BOTH and
# kept the LAST, so it printed column 4 of the *achieved* table under the label
# of column 4 of the *spec* table. MEASURED on this very case: it reported
# `first 5.68 m` — a first-layer thickness of 5.68 METRES on a 7.28 m hull,
# 2145x the 2.648 mm the case asked for. The number was not even wrong in
# magnitude, it was a different quantity: 5.68 is the achieved MEAN LAYER COUNT.
# Tables are told apart by NF, not by position, so inserting another one cannot
# silently re-point this again.
_L_SPEC=$(awk '/^hull +[0-9]/ && NF==5 {printf "requested n=%s, first %s m", $3, $4}' "$_LAYERLOG" | tail -1)
_L_GOT=$(awk '/^hull +[0-9]/ && NF==6 {printf "achieved %s of %s layers, stack %s m (%s%% of target)", $4, $3, $5, $6}' "$_LAYERLOG" | tail -1)
if [ "${_L_ADDED:-0}" -le 0 ]; then
  say "FATAL: layer addition produced ZERO cells (${_L_SPEC:-no spec found})."
  say "       The hull has no prism layers, so y+ is uncontrolled and the wall"
  say "       model is invalid. See log.snappy.layers 'Extruding 0 out of ...'."
  say "       Set LAYERS_OPTIONAL=1 to proceed deliberately anyway."
  [ "${LAYERS_OPTIONAL:-0}" = "1" ] || exit 1
else
  say "layers: ADDED ${_L_ADDED} of ${_L_WANT:-?} cells ($(awk -v a="$_L_ADDED" -v w="${_L_WANT:-1}" 'BEGIN{printf "%.1f", 100*a/w}')%), ${_L_SPEC}"
  say "layers: ${_L_GOT:-no achieved table found}"
  [ -n "$_L_GOT" ] && _mq_record layers_achieved \
    "$(awk '/^hull +[0-9]/ && NF==6 {print $4}' "$_LAYERLOG" | tail -1)"
fi
# `grep -c 'Failed'` COUNTS LINES, NOT CHECKS. checkMesh writes one line,
# "Failed 3 mesh checks.", so a mesh failing three checks was reported as
# "flagged 1 check(s)". MEASURED on runs/val_coarse: 3 failures (non-ortho,
# face pyramids, skewness) announced as 1.
if ! grep -q 'Mesh OK' log.checkMesh; then
  _MQ_NFAIL=$(awk '/Failed [0-9]+ mesh check/ {print $2}' log.checkMesh | tail -1)
  say "NOTE: checkMesh FAILED ${_MQ_NFAIL:-?} check(s) — see log.checkMesh"
  awk '/^ \*\*\*/ {sub(/^ *\*\*\* */,""); print "         " $0}' log.checkMesh
fi

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
#   INCORRECTLY-ORIENTED FACES -> FATAL AT 5. The bar was 10, interpolated
#   between the only two points then available (5 faces -> the fixed KCS mesh,
#   which SOLVES; 73 -> the mirrored KCS.igs mesh, which dies on the first
#   timestep). MEASURED 2026-08-06, the gap between them is now filled and 10
#   is on the WRONG side of it:
#       0  faces -> KCS coarse n_layers=3 and n=5, and runs/wigley (n=10,
#                   solved 10 s to completion) -- all clean
#       5  faces -> the fixed KCS mesh, SOLVES
#      10  faces -> KCS coarse symmetric, nx 57, n_layers=7 (what make_case.py
#                   DERIVES for this hull today). interFoam died at t=0.0072
#                   with deltaT 1.2e-3 -> 2.5e-26 while Courant max stayed 9-12
#                   and alpha.water reached 1503.95 -- the documented
#                   pathological-cell signature, and it passed this guard by
#                   exactly one face.
#      73  faces -> the mirrored KCS.igs mesh, dies on the first timestep
#   5 is now the largest count measured to SOLVE, and the next count up is
#   measured to die. Interpolating a bar between two points is a guess; this
#   one is now pinned by the measurement in between. Tightening a gate on
#   evidence is the opposite of softening one.
#
#   MAX SKEWNESS -> FATAL AT 20, which is checkMesh's OWN boundary-face limit
#   (its internal limit is 4, which every mesh in this project exceeds, so 4
#   would refuse everything we have ever solved). MEASURED:
#       6.32  KCS coarse n=3   |  8.68  wigley (solved)   |  8.93  KCS n=5
#       9.64  kcs_gci2/coarse  | 42.94  KCS n=7 (DIED at t=0.0072)
#   Every mesh that solved is under 10; the one that died is 4.7x the worst of
#   them. The bar sits at OpenFOAM's documented value rather than at a number
#   invented to separate these two clusters.
#
#   AN UNPARSED METRIC IS FATAL, NEVER ZERO. Every one of these used to end in
#   `${VAR:-0}`, which silently converts "I could not measure this" into "this
#   is perfect" — the same failure class as the layer table that reported the
#   REQUESTED spec as the achieved one, and as `${_L_WANT:-1}` dividing by a
#   fabricated denominator. checkMesh's wording is not contractual (the counts
#   only appear when non-zero, and the skewness line carries a `***` prefix
#   when it fails and none when it passes), so a parse that comes back empty
#   means the guard has no evidence, and a guard with no evidence must refuse.
#   The skewness value is read by SUBSTRING after "Max skewness =" rather than
#   by field index, so the `***` prefix cannot shift the column out from under
#   it.
_mq_num() {   # _mq_num <awk-program> <what>  -> value, or "UNPARSED"
  local v; v=$(awk "$1" log.checkMesh | tail -1)
  case "$v" in ''|*[!0-9.eE+-]*) echo "UNPARSED";; *) echo "$v";; esac
}
# The zero-volume and wrong-orientation lines are printed ONLY when the count
# is non-zero, so "no line" genuinely means zero for those two and the default
# is correct. Skewness is printed on EVERY run, so a missing value there means
# the parse broke.
_MQ_ZEROVOL=$(awk '/zero volume cells to set zeroVolumeCells/ {print $2}' log.checkMesh | tail -1)
_MQ_WRONGOR=$(awk '/faces with incorrect orientation to set wrongOrientedFaces/ {print $2}' log.checkMesh | tail -1)
_MQ_ZEROVOL=${_MQ_ZEROVOL:-0}; _MQ_WRONGOR=${_MQ_WRONGOR:-0}
_MQ_SKEW=$(_mq_num '/Max skewness *=/ {v=$0; sub(/.*Max skewness *= */,"",v); sub(/[^0-9.eE+-].*/,"",v); print v}' skewness)
say "mesh quality: ${_MQ_ZEROVOL} zero-volume cell(s), ${_MQ_WRONGOR} incorrectly-oriented face(s), max skewness ${_MQ_SKEW}"
# RECEIPTS ARE REWRITTEN, NOT APPENDED. Every invocation appended, so a case
# meshed three times (a MESH_ONLY sweep then two campaign attempts) carried
# three copies of each line — MEASURED on runs/val_coarse and runs/val_coarse5.
# A later reader gets whichever duplicate it happens to hit, which is how a
# stale receipt outlives the mesh that produced it.
_mq_record checkmesh_zero_volume_cells "${_MQ_ZEROVOL}"
_mq_record checkmesh_wrong_oriented_faces "${_MQ_WRONGOR}"
_mq_record checkmesh_max_skewness "${_MQ_SKEW}"
if [ "$_MQ_SKEW" = "UNPARSED" ]; then
  _MQ_SKEWBAD=1
else
  _MQ_SKEWBAD=$(awk -v s="$_MQ_SKEW" 'BEGIN{print (s+0 > 20.0) ? 1 : 0}')
fi
if [ "$_MQ_ZEROVOL" -gt 0 ] || [ "$_MQ_WRONGOR" -gt 5 ] || [ "$_MQ_SKEWBAD" = "1" ]; then
  # Try the next recorded backoff rung before declaring FATAL — but only when
  # a layer pass exists to redo, a pre-layer snapshot is present, and the
  # attempt budget is not spent. An UNPARSED skewness is NOT retried: it is a
  # broken parse, not a layer defect, and re-meshing cannot fix a grep.
  _BK_NEXT=""
  if [ -n "${_LAYERS_DICT:-}" ] && [ -d constant/polyMesh.prelayer ] && \
     [ "$_BK_TRY" -lt "$_BK_MAX" ] && [ "$_MQ_SKEW" != "UNPARSED" ]; then
    _BK_NEXT=$(printf '%s\n' $_BK_LADDER | sed -n "$((_BK_TRY + 1))p" || true)
  fi
  if [ -n "$_BK_NEXT" ]; then
    _BK_CUR=$(grep -o 'nSurfaceLayers [0-9]*' "$_LAYERS_DICT" | awk '{print $2}' | head -1 || true)
    _BK_TRY=$((_BK_TRY + 1))
    say "layer backoff ${_BK_TRY}/${_BK_MAX}: quality bar failed at n=${_BK_CUR:-?}"
    say "       (${_MQ_ZEROVOL} zero-volume, ${_MQ_WRONGOR} wrongly-oriented, skew ${_MQ_SKEW})"
    say "       -> restoring the pre-layer mesh, retrying at n=${_BK_NEXT}"
    _mq_record "layer_backoff_attempt_${_BK_TRY}" "n=${_BK_CUR:-?} zerovol=${_MQ_ZEROVOL} wrongor=${_MQ_WRONGOR} skew=${_MQ_SKEW} retry_n=${_BK_NEXT}"
    rm -rf constant/polyMesh
    cp -a constant/polyMesh.prelayer constant/polyMesh
    # -i.bak works on both GNU and BSD sed (this script runs on the Mac).
    sed -i.bak "s/nSurfaceLayers [0-9][0-9]*;/nSurfaceLayers ${_BK_NEXT};/" "$_LAYERS_DICT"
    rm -f "${_LAYERS_DICT}.bak"
    continue
  fi
  say "FATAL: mesh quality below the bar (${_MQ_ZEROVOL} zero-volume cells,"
  say "       ${_MQ_WRONGOR} incorrectly-oriented faces, max skewness ${_MQ_SKEW};"
  say "       bars are 0, 5 and 20)."
  [ "$_BK_TRY" -gt 0 ] && \
    say "       ${_BK_TRY} layer-backoff attempt(s) already tried and failed —"
  [ "$_BK_TRY" -gt 0 ] && \
    say "       see layer_backoff_attempt_* in case.info; the defect is likely"
  [ "$_BK_TRY" -gt 0 ] && \
    say "       not the layer count."
  [ "$_MQ_SKEW" = "UNPARSED" ] && \
    say "       max skewness could NOT BE READ from log.checkMesh. An unmeasured"
  [ "$_MQ_SKEW" = "UNPARSED" ] && \
    say "       metric is refused, not assumed good — see the comment above."
  say "       A degenerate cell does not degrade a solve, it invalidates it:"
  say "       deltaT collapses to ~1e-40 while Courant stays high and interFoam"
  say "       dies in the GAMG p_rgh solve. Re-mesh; do not spend hours on this."
  say "       If the layer count is the cause (MEASURED on KCS coarse: n=7 gives"
  say "       10 faces and dies, n=5 gives 0 and solves), pass n_layers to the"
  say "       generator -- make_case.py --n-layers N."
  say "       Pass --force (or FORCE=1) to run it anyway, deliberately."
  [ "$FORCE" = "1" ] || exit 1
  say "       --force given: proceeding on a mesh that failed the bar."
fi
break
done
# The quality gate passed (or --force). Record what the mesh actually carries:
# after a backoff, case.info's n_layers= line still names the DERIVED count,
# so the meshed count gets its own receipt instead of silently rewriting it.
rm -rf constant/polyMesh.prelayer
if [ "$_BK_TRY" -gt 0 ]; then
  _mq_record layer_backoff_attempts "$_BK_TRY"
  _BK_FINAL=$(grep -o 'nSurfaceLayers [0-9]*' "${_LAYERS_DICT:-/dev/null}" 2>/dev/null | awk '{print $2}' | head -1 || true)
  _mq_record n_layers_meshed "${_BK_FINAL:-UNPARSED}"
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
_mq_record tet_bad_faces_at_1e-15 "${_TETBAD:-unknown}"
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
  run_solver trunc log.interFoam mpirun -np "$NP" interFoam -parallel
  reconstructPar -latestTime > log.reconstruct 2>&1
else
  say "interFoam ..."
  run_solver trunc log.interFoam interFoam
fi
say "done: $(ls postProcessing/forces/0/ 2>/dev/null || echo 'NO FORCES OUTPUT')"
