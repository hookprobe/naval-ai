# Forensics — failure paths (§19), timers (§18), optional deps (§20)

> **DATED SNAPSHOT — NOT A CURRENT STATE.** This file was measured at
> `HEAD 3527a59` (2026-08-18). That commit is now **174 commits**
> behind `master`. Read it as evidence of what was true THEN, never as
> an answer to "what is the state now" — CLAUDE.md routes that question
> to `python -m navalai.gates` and `python scripts/reconcile_gaps.py`.
> The 2026-08-11 incident this repo records is exactly this failure: four
> documents each asserted a subsystem did not exist, and all four were
> false because they were read as current.
Agent report, HEAD 3527a59. Verdict up front: honest-by-construction
patterns are real but NOT uniformly applied; deviations cluster around
ONE quantity: trim.

## Class (c) — silent fallback where a failure becomes a valid-looking number
- C1 certify.py:313 — ev.trim_deg None (REFUSED equilibrium) becomes
  Quantity(0.0,"deg",...,"solved (wl0, theta) equilibrium") — E11
  regression; line 205 of the same file does it right.
- C1b certify.py:340,357 — gz_curve/multihull_gz_assessment called with
  trim_deg=0.0 when the solve was refused: stability numbers computed at
  a fabricated attitude (verdict still REFUSE, but per-quantity unflagged).
- C2 cfd/manifest.py:128 — trim_deg=float(ev.trim_deg or 0.0); guard
  (111-115) checks only hydro/masses, not ok/trim — a trim-refused hull
  gets a CFD case at even keel. SHARPEST: fix = refuse when trim is None.
- C3 scripts/mesh_robustness.py:242,247 — grab(default=0): unparsed
  checkMesh fields read as PASSING zeros (partially self-acknowledged;
  residual risk when cells parses but orientation regex drifts).
- C4 cfd/post.py:96-106 — unparseable force.dat segments silently dropped;
  no receipt of discarded row count.
- C5 scripts/blender_isosurface_probe.py:150-157 — PLY export failure
  prints FAILED then returns 0 (exit success).

## Class (c*) — refusing-direction but defect-masking
- C6 evaluate.py:477 — except (ValueError,TypeError,AttributeError,
  KeyError) → 'vessel:' L0 refusal: a TYPO in vessel_terms refuses a
  whole population with Python-internals prose instead of crashing.
  Narrow to ValueError/TypeError or prefix 'checker error:'.
- C7 agents.py:242 — gather(return_exceptions=True) + 2s blind re-request:
  a crashed worker = silent partial results at deadline, no refusal.

## Class (b) declared fallbacks (correct, receipted) — translate floors,
flywheel nan-receipt (never compared), post.py domain_assumed flag,
hydrostatics Newton→bisection fallback, blender CPU fallback,
mesh_robustness error rows, hull_form_audit NOT-CHECKED strings,
stl_thirdparty MISSING strings, reconcile broken-predicate NEEDS rows,
certify buildability 0.5 (conservative), stl_forensics failing defaults,
ui/server 400s. Class (a) honest refusals verified across evaluate
TierRefusal/TierUnavailable, cfd Aref RuntimeError, flywheel baseline
FileNotFoundError, gates Requirement probes, iso12217, blender/run,
dynamics, pipeline. design_report.py: clean.

## Timers (§18)
- run-case.sh SOLVER_TIMEOUT 21600s: verified kill (TERM→KILL→pgrep) — model citizen.
- run_campaign.sh MAX=20/sleep 120: STALL>=2 → exit 4 (divergence vs nap
  discriminated); incomplete → WARNING not success.
- FLAG mesh_robustness.py: timeout INVERSION (outer 3600/7200 < inner
  21600 → the UNVERIFIED blind-pkill layer always fires first, no
  survivor check → one hung rank = campaign-wide false-failure wall).
- FLAG agents.py: blind 2s re-request until deadline (duplicated work,
  dead-vs-slow indistinguishable).
- CI 50-min caps measurement-backed; pre-push exit-141-after-green
  documented residual. No timeout anywhere is interpreted as success.

## Optional deps (§20) — ALL explicit
capytaine → TierUnavailable + gate SKIPPED-not-GREEN; cadquery → hard
error at call; Blender subprocess-only + receipt-or-raise; pymoo core
dep; sklearn NOT USED (hand-rolled GP — no silent ML substitution
possible); trimesh/pymeshlab/open3d → 'MISSING' strings; LLM → rule
floor with receipts; gates.py Requirement probe = strongest contract
(unprobeable prerequisite = failure; present-but-skipped = failure).

## Sharpest findings
1. `ev.trim_deg or 0.0` is a FOUR-SITE E11 regression in the newest code
   (certify.py:313/340/357, cfd/manifest.py:128) and one site feeds CFD.
2. evaluate.py:477 masks code defects as design refusals.
3. mesh_robustness timeout inversion + unverified pkill.
4. agents.py dead-pipeline-as-slow.
5. Everything else audited holds the line.
