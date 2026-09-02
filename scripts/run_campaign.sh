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

# HOW FAR THE SOLVE ACTUALLY GOT — from the solver's own log, not the
# checkpoint. The two are NOT the same number, and judging completion by
# the checkpoint alone produced a false DIVERGENCE verdict on a COMPLETE
# case (MEASURED 2026-09-02, runs/kcs_free1): a cfd_batch.sh `writeNow`
# stop re-anchors the adjustableRunTime write grid (resume at 51.648 ->
# writes at 57.648, next due 63.6 > endTime 60), so t=60 never got a field
# write. The solver ran to 60.0002 and printed "End"; the checkpoint said
# 57.648 forever; this loop re-solved the last 2.35 s, saw the checkpoint
# unmoved, and exit-4'd a finished run as a divergence. Completion now
# takes the MAX of both readings. The checkpoint remains the resume truth;
# the log is the completion truth.
solved_to() {
  local ck lg
  ck="$(latest_of "$1")"
  lg="$(grep -a '^Time = ' "$1/log.interFoam" 2>/dev/null | tail -1         | sed 's/^Time = //')"
  awk -v a="${ck:-0}" -v b="${lg:-0}" 'BEGIN{print (a+0 > b+0) ? a : b}'
}

# A single case directory is a campaign of one. Without this, pointing the
# script at one case printed "skip coarse/medium/fine (no case dir)" followed
# by "done" — a SUCCESSFUL-looking exit that ran nothing, which is exactly the
# failure mode that loses an overnight run.
GRIDS="coarse medium fine"
if [ -d "$ROOT/system" ]; then
  GRIDS="."
  echo "[campaign] single case: $ROOT"
elif [ ! -d "$ROOT/coarse" ] && [ ! -d "$ROOT/medium" ] && [ ! -d "$ROOT/fine" ]; then
  echo "[campaign] FATAL: $ROOT is neither a case (no system/) nor a triplet root" >&2
  exit 2
fi

for GRID in $GRIDS; do
  CASE="$ROOT/$GRID"
  [ "$GRID" = "." ] && CASE="$ROOT"
  [ -d "$CASE" ] || { echo "[campaign] skip $GRID (no case dir)"; continue; }
  # AN UNMEASURED endTime IS REFUSED, NEVER ASSUMED ZERO. This line was
  # `|| echo 0`, and `foamDictionary` exists only inside the `openfoam`
  # environment -- so invoking this script outside the wrapper made END=0,
  # NOW(0) >= END(0), and it printed "COMPLETE at t=0/0" and exited 0
  # HAVING RUN NOTHING (measured 2026-09-02 launching runs/kcs_free1).
  # That is the same class as the `${VAR:-0}` receipts run-case.sh already
  # purged: a metric that could not be measured reported as its most
  # permissive value. A campaign that cannot read the endTime it is
  # supposed to reach cannot claim to have reached it.
  if ! END="$(end_time_of "$CASE" 2>/dev/null)" || [ -z "$END" ]; then
    echo "[campaign] FATAL: cannot read endTime of $CASE/system/controlDict" >&2
    echo "[campaign]        (foamDictionary missing? run via: openfoam bash $0 ...)" >&2
    exit 3
  fi
  STALL=0            # consecutive attempts that advanced t by nothing

  for attempt in $(seq 1 "$MAX"); do
    NOW="$(solved_to "$CASE")"
    if awk -v a="$NOW" -v b="$END" 'BEGIN{exit !(a+0 >= b+0-1e-6)}'; then
      echo "[campaign] $GRID COMPLETE at t=$NOW/$END"
      break
    fi
    echo "[campaign] $GRID attempt $attempt/$MAX (at t=$NOW/$END) $(date +%H:%M:%S)"
    "$HERE/navalai/cfd/run-case.sh" "$CASE" "$NP" || \
      echo "[campaign] $GRID attempt $attempt returned non-zero — will resume"

    # A CRASH IS NOT A NAP, AND THIS LOOP COULD NOT TELL THEM APART.
    # Every non-zero exit was treated as "interrupted, will resume", so a
    # DIVERGED case was re-meshed and re-run up to MAX times. MEASURED
    # 2026-08-06 on runs/val_coarse: interFoam died at t=0.0072 with the
    # pathological-cell signature, no checkpoint was ever written, and the loop
    # settled into "attempt N/20 (at t=0/20)" -> mesh 3 min -> die -> cool
    # 120 s, i.e. ~100 minutes of re-running a mesh that cannot solve, ending
    # in a WARNING phrased as though the machine had napped.
    # A thermal nap always leaves a LATER checkpoint than the attempt started
    # from; a divergence leaves the same one. So: no progress twice in a row
    # is fatal, and the message names the real cause.
    AFTER="$(solved_to "$CASE")"
    if awk -v a="$AFTER" -v b="$END" 'BEGIN{exit !(a+0 >= b+0-1e-6)}'; then
      continue
    fi
    if awk -v a="$AFTER" -v b="$NOW" 'BEGIN{exit !(a+0 <= b+0)}'; then
      STALL=$((${STALL:-0} + 1))
      if [ "$STALL" -ge 2 ]; then
        echo "[campaign] FATAL: $GRID made NO progress in $STALL attempts" \
             "(still t=$AFTER of $END)." >&2
        echo "[campaign] That is a DIVERGENCE, not a thermal nap — resuming" \
             "cannot help. Check log.interFoam for deltaT collapsing while" \
             "Courant stays high (a pathological cell) and re-mesh." >&2
        exit 4
      fi
    else
      STALL=0
    fi
    echo "[campaign] $GRID interrupted at t=$AFTER — cooling 120 s before resume"
    sleep 120
  done

  FINAL="$(solved_to "$CASE")"
  awk -v a="$FINAL" -v b="$END" 'BEGIN{exit !(a+0 >= b+0-1e-6)}' || \
    echo "[campaign] WARNING: $GRID stopped at t=$FINAL of $END after $MAX attempts"
done

echo "[campaign] done $(date +%H:%M:%S)"
