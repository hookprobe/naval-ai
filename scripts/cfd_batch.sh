#!/bin/bash
# cfd_batch.sh <case-dir> <wall-minutes> [np]
#
# Run a CFD case for a bounded slice of WALL CLOCK, then stop CLEANLY at a
# checkpoint and hand the machine back. Repeat until the case reports
# COMPLETE. This is how a ~78 CPU-hour solve fits a machine that is also a
# workstation: nights and idle hours, in pieces, losing nothing between them.
#
#   scripts/cfd_batch.sh runs/kcs_free1 120        # tonight: 2 hours
#   scripts/cfd_batch.sh runs/kcs_free1 120        # tomorrow: 2 more
#   ...                                            # until "COMPLETE at t=60/60"
#
# WHY NOT JUST KILL IT (2026-09-02). The resume machinery tolerates an
# ungraceful death — it was built for this Mac's thermal-emergency sleeps —
# but a kill loses everything since the last 6-sim-second checkpoint, which
# at this case's measured rate is up to ~100 minutes of wall clock. The
# clean stop is OpenFOAM's own: `stopAt writeNow` in a run-time-modifiable
# controlDict makes the solver finish the CURRENT step, WRITE a checkpoint
# at whatever time it reached, and exit 0. A batch therefore ends exactly
# where the next one begins, to the timestep.
#
# ORDER OF THE SHUTDOWN, and why it is this order: the campaign wrapper is
# killed FIRST, then stopAt is flipped. Flipping first would let the
# wrapper see the solver's clean exit-0, notice t < endTime, and re-invoke
# it against a controlDict that still says writeNow — a start/write/exit
# loop burning attempts until the campaign's stall guard (exit 4) fires.
# The wrapper dies; the solver alone finishes its step and writes; stopAt
# is restored to endTime for the next batch.
set -u
CASE="${1:?usage: cfd_batch.sh <case-dir> <wall-minutes> [np]}"
MINUTES="${2:?usage: cfd_batch.sh <case-dir> <wall-minutes> [np]}"
NP="${3:-10}"
CTRL="$CASE/system/controlDict"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

[ -f "$CTRL" ] || { echo "[batch] FATAL: no $CTRL" >&2; exit 2; }
if pgrep -x interFoam >/dev/null; then
  echo "[batch] FATAL: an interFoam is already running (np=$(pgrep -xc interFoam))." >&2
  exit 2
fi

# the clean stop needs both of these; pin them rather than assume defaults
grep -q '^runTimeModifiable' "$CTRL" || \
  sed -i '' '1a\
runTimeModifiable yes;
' "$CTRL"
sed -i '' 's/^runTimeModifiable.*/runTimeModifiable yes;/' "$CTRL"
sed -i '' 's/^stopAt  *[a-zA-Z]*;/stopAt          endTime;/' "$CTRL"

latest() {
  ls "$CASE"/processor0/ 2>/dev/null | grep -E '^[0-9]' | sort -g | tail -1
}
T0="$(latest)"; T0="${T0:-0}"
echo "[batch] $CASE: ${MINUTES} min slice on $NP ranks, resuming from t=${T0}"

openfoam bash "$HERE/scripts/run_campaign.sh" "$CASE" "$NP" &
CAMPAIGN=$!

SECS=$((MINUTES * 60)); WAITED=0
while [ "$WAITED" -lt "$SECS" ]; do
  sleep 30; WAITED=$((WAITED + 30))
  # the campaign finishing early IS the good ending — nothing to stop
  kill -0 "$CAMPAIGN" 2>/dev/null || break
done

if kill -0 "$CAMPAIGN" 2>/dev/null; then
  echo "[batch] slice over — clean checkpoint stop (stopAt writeNow) ..."
  kill "$CAMPAIGN" 2>/dev/null              # the wrapper, NOT the solver
  pkill -f "run-case.sh $CASE" 2>/dev/null  # its inner shell, same reason
  sed -i '' 's/^stopAt  *endTime;/stopAt          writeNow;/' "$CTRL"
  # the solver finishes its step and writes; give it time for the write
  for _ in $(seq 1 120); do
    pgrep -x interFoam >/dev/null || break
    sleep 5
  done
  if pgrep -x interFoam >/dev/null; then
    echo "[batch] WARNING: solver ignored writeNow after 10 min — killing" >&2
    echo "[batch]          (resume falls back to the last 6 s checkpoint)" >&2
    pkill -x interFoam; sleep 3
  fi
  sed -i '' 's/^stopAt  *writeNow;/stopAt          endTime;/' "$CTRL"
fi

T1="$(latest)"; T1="${T1:-0}"
# AN UNPARSEABLE endTime IS REFUSED, NEVER A VERDICT — the run_campaign.sh
# lesson, which this script promptly re-learned on its own SECOND run:
# with runTimeModifiable yes, OpenFOAM re-serialises controlDict (the
# one-line "stopAt endTime;  endTime 60.0;" became two lines and "60"),
# a one-space regex parsed END as EMPTY, and `awk -v b=""` printed
# "CASE COMPLETE" at t = 1.49 of 60. Same defect class, hours apart,
# different file. The parse below survives both serialisations, and an
# empty result is fatal to the VERDICT while still reporting progress.
END="$(grep -oE 'endTime[[:space:]]+[0-9.eE+-]+;' "$CTRL" | tail -1 \
       | grep -oE '[0-9.eE+-]+' | tail -1)"
echo "[batch] t=${T0} -> t=${T1} of ${END:-UNKNOWN} this slice."
if [ -z "$END" ]; then
  echo "[batch] FATAL: cannot parse endTime from $CTRL — no completion" >&2
  echo "[batch]        verdict is possible. The checkpoint at t=${T1} is" >&2
  echo "[batch]        intact; fix the controlDict read and re-run." >&2
  exit 3
fi
awk -v a="$T1" -v b="$END" 'BEGIN{exit !(a+0 >= b+0-1e-6)}' \
  && echo "[batch] CASE COMPLETE — run the post-processing next." \
  || echo "[batch] re-run the same command for the next slice; it resumes at t=${T1}."
