# Architecture audit + rebuild — execution status (updated 2026-08-14)

Campaign: deep inspection -> docs/NAVALAI_GEOMETRY_ARCHITECTURE_AUDIT.md ->
docs/NAVALAI_REBUILD_PLAN.md -> incremental execution. NO CFD runs.

## Phase 1 — audit: COMPLETE
All 7 domain reports banked in this directory; master synthesis + the
dependency-ordered rebuild plan are in docs/ (commit 537beef). A dedicated
full-suite pytest baseline was NOT captured cleanly (two attempts died to
session-kill and to mixed-tree edits); per-change targeted suites were run
instead, and every pre-existing failure met en route is classified below.

## Phase 2 — execution ledger (rebuild plan rungs)
- **R0.1 DONE** (b890762) — vessel context threads through the production
  L0 gate; demihull bands reachable; proof trace inverted.
- **R0.2 DONE** (a77f131) — optimizer honesty: ev.ok consulted, one
  scoring body, n_hulls build area, floated-beam GM band, provenance
  recorded; catamaran fronts now explicitly EMPTY until R2.2; four stale
  trajectory pins re-measured + re-based with in-file justification.
- **R0.3 DONE** (c11918e) — ledger regression rule implemented
  (judge_red measured= + --measured CLI + calibration_void); Gate 2U
  marked void-calibration (15-gene batch), re-base owed on the CFD node.
- **R0.4 DONE** (b4bffa1) — formlib registry re-audited vs shipped kernel
  (round bilge + separation markers retired, verdict flips, fence test);
  GATE-6R packet reconciled to review.py; GAP-REGISTER A2 closed/G7
  corrected; BuildPlan2-FullVessel.md restored; stale handoff deleted.
- **Gate PF DONE** (9d73ef1) — physical form regression layer (operator
  directive): formcheck descriptors, six deterministic cases,
  PHYSICAL_FORM_REPORT.md, 46 ratcheted tests. Findings recorded: case-b
  entrance 22.9° vs 7-14 band; transom-waterline pinch (kernel section
  law); cold-bend on small chine hulls; uncrewed GM-floor wiring.
- **R1.2 DONE** (b2bbbd4) — lwl hint band derives from the grammar box;
  ghost SUPPORTED_HULL_COUNTS comments corrected.
- **R1.1 DONE** (0b15811) — MissionSpec.design_fn + mission_cp_band wired
  into HullProblem bounds and sample_valid; four-mission proof green
  (slow/coastal/fast briefs get SEPARATED, ordered Cp boxes); dict-vessel
  rehydration at the MissionSpec boundary; server pareto budget 48/15
  (measured: the narrower Cp box needs population diversity).
- **R1.5 DONE** (95db6e9) — one reference genome (navalai/reference.py);
  three transcribed copies delegate.
- **R2.1 DONE** (0b15811) — solve_trimmed + solve_equilibrium (warm-start
  Newton, 963ms->~30ms marginal; bisection = authoritative fallback +
  sole refusal issuer); evaluate reports ALL hydrostatics at the solved
  attitude; artifact fences compare at the attitude (STL reader gained
  trim_deg/x_pivot); LCB pins replaced by the equilibrium identity
  lcb == lcg; panel-mesh fence holds level-plane identity + records the
  BEM-attitude residue as R2.5.
- **G7.1 DONE** (654d39b) — import path REALLY repairs winding (repair()
  runs; repaired mesh written; truthful receipt + proof tests).
- **G8.1 DONE** (654d39b) — run-case.sh SOLVER_TIMEOUT watchdog (portable,
  verified kill, exit 124).
- **R4.2-seiche DONE** (ed1cf83) — refuted still-water seiche replaced by
  the MEASURED Doppler tank-mode model (5.80 s predicted vs 5.53
  measured); fidelity's fourth _NX_BASE copy retired (a978108 re-base).
- P0 scorecard: 12 of 14 closed. OPEN: GZ(phi) curve (needs the heeled-
  waterplane solve — the prerequisite of the multihull criterion R2.2,
  which is additionally blocked on windage/superstructure the genome
  cannot express) and loading conditions (R2.3) + tier E/F mass admission
  (R2.4).
- Next rungs: R2.2 (GZ solver first), R2.3-2.5, R1.3 typology
  consolidation, R3.1 constants home, R3.2 CFD manifest from the floated
  state, R4 wire-or-delete, R5 five-case validation matrix + final
  report (audit q.36).

## Pre-existing failures classified en route (not caused by the rebuild)
- Wall-clock bars on this box (fortress001 is slower than the bar-setting
  machine; all reproduce on the UNMODIFIED tree): catamaran latency 120ms
  bar (~195-340ms), L0-check 1ms bar (1.34ms under load), L1 50ms bar
  (139ms under load), kernel slider p95 100ms bar (~230ms).
- test_optimize policy-rows: ALREADY failing at the audit base commit
  (11 < 15 members; witness draws 0/1500 ladder-ok) — stale 2026-08-13
  pins; re-based with fresh measurements in R0.2.
- test_phase3 calibration-curve + saturated-ARD: fail IDENTICALLY at the
  audit base commit (Mac-measured GP pins; platform float drift).
- test_gapfix_physics Michell population-worst: 1.178% here vs the
  Mac-measured 0.673% — identical at base commit; platform drift.

## Save protocol
Every rung lands as its own commit, pushed immediately. If a session dies,
resume from this ledger + the rebuild plan; each plan item carries
(defect -> change -> proof).
