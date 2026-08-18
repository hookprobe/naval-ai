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
## Phase 3 — consolidation directive (2026-08-14, §1-24): ledger
- **§8/R2.2-prereq DONE** (dcc6f77) — GZ(phi) heeled-waterplane solve
  (polygon clip anchored on analytic wedges; trim-0 == level solver
  bit-for-bit; catamaran curve saturates/peaks/declines where GM.sin
  claims 10m); NZ cl.1.4 (a)/(b) MEASURED via multihull_gz_assessment;
  criterion stays refusal-first ((c) windage undeclarable, (d) unread).
- **§5/§6 DONE** (aa621e3) — target/sampled/delivered Cp receipt on
  Evaluation.targets (conformance judged on the EQUILIBRIUM state);
  LCB target honestly UNKNOWN with the safe band + basis.
- **§18/R3.1 DONE** (e90aad8) — navalai/constants.py, values bit-identical,
  conventions named; fence test caught 3 more copies on first run.
- **§11+§14 DONE** (4383493) — PayloadSpec first-class (positioned mass,
  hotel-load wiring, uncrewed provision zeroed-with-note, JSON round-trip);
  CFDManifest = the one vessel description (G7 disjoint-mass fix
  structural; case.info renders it behind a genome-fingerprint guard);
  §13 non-zero-trim one-state regression green.
- **§19/§20 DONE** (0460b48, Gate VM) — vessel matrix end-to-end on
  formcheck.CASES; trimaran refused by name; 12x0.8 demihull judged by
  role.
- **§3 DONE** (7209918) — README capability truth rewritten with the
  IMPLEMENTED/PARTIAL/REFUSED/UNKNOWN taxonomy (four disproved absence
  claims corrected).
- Pins re-based with measurement en route: multihull GM/I_T table (R2.1
  attitude), holtrop envelope B/T + cross-platform coverage counts,
  stageG density floor.
## Phase 4 — pre-CFD screening directive (2026-08-14, §0-31): ledger
- **§3 DONE** — docs/POST_REBUILD_L1_AUDIT.md (verified at c017851).
- **§1/§4/§14/§15/§16/§25 CORE DONE** (f6eca26, Gate DC) — certify.py
  (composition over Evaluation; Quantity receipts; validity-banded speed
  curves; loading matrix incl. people-shift + honest UNKNOWN MAXIMUM;
  GZ summary w/ assumptions; buildability report; regime router refusing
  SEMI_DISPLACEMENT/PLANING by name; cfd_candidate single-design score) +
  python -m navalai.design_report + 3 docs + 8 invariant tests.
- OPEN (population layer, next): §5-6 geometry fingerprint (moments),
  §7 design-space sweeps, §8-9 hydrostatic curves + Bonjean, §18 shape
  improvement, §19 sensitivity table, §20 versioned dataset generator,
  §21 baseline surrogate benchmark w/ MAE/RMSE/R2, §22 reference
  adapters, §24 population factors (Pareto/novel/robust/uncertainty),
  §26 wire-or-delete triage, §27 single-source second pass (STL readers,
  weight_budget merge).

- OPEN (next sessions): §7 bow-form comparator, §9 vessel-arrangement
  object, §10 full mass consolidation (payload done; weight_budget merge
  open), §12 energy/length governance beyond hint+policy, §17 timer
  policy, §18 remaining sweeps (ITTC-57 x4, STL readers x3), R2.3
  loading conditions, R2.4 tier E/F admission, R2.5 BEM attitude.

- Next rungs: R2.2 (GZ solver first), R2.3-2.5, R1.3 typology
  consolidation, R3.1 constants home, R3.2 CFD manifest from the floated
  state, R4 wire-or-delete, R5 five-case validation matrix + final
  report (audit q.36).

## Phase 5 — CODE FORENSICS directive (2026-08-14 night, §0-35): in flight
Phase 1 fan-out (7 read-only agents), reports banked to docs/forensics/ on
arrival, committed+pushed immediately:
- import-graph.md (§6/§7 module classification + reachability) — PENDING
- e2e-map.md (§2/§3/§14 four-vessel executed trace + mutation probes) — PENDING
- ownership.md (§4/§5/§16/§17 quantity/object tables + duplicates) — PENDING
- scripts-files-artifacts.md (§8/§9/§10/§21/§22) — PENDING
- failure-paths.md (§18/§19/§20) — PENDING
- tests-gates-docs.md (§11/§12/§13/§24) — PENDING
- shadow-api.md (§15/§23 + live-map skeleton) — PENDING
Baseline (§1/§32): full gates+reconcile+pytest running in pinned worktree
at f6eca26 (verify-f6eca26.txt). Repo state at fan-out: HEAD 3527a59,
clean, synced, 77,644 py LOC.
Then: CODE_FORENSICS_REPORT + LIVE_SYSTEM_MAP + E2E map + CONSOLIDATION
PLAN (Phase 2), incremental fixes (Phase 3), verification + the 17-question
answer (Phase 4). Deletion rule: find -> trace consumers -> gates -> docs ->
history -> classify -> migrate -> only then delete/archive.

## Phase 6 — forensics Phase 3 execution (2026-08-18): ledger
- **C-01 DONE** (d30270e + f680750) — the 4-day infinite loop: held-out
  wedge re-anchored to the L/B corridor (box moves cannot empty a
  proportion region); draw-budget guard RAISES on an empty wedge;
  baselines.json regenerated (8-seed ensemble, fresh fingerprints);
  test_phase7 15/15 (was: infinite).
- **C-02 DONE** (d30270e) — refused trim is never an even keel (certify
  quantity/GZ block + manifest raise + regression fixture).
- **C-03+C-09 DONE** (20a4d33) — dead assertion asserts again;
  grammar_version derives from the genome (genome-16).
- **C-04 DONE** (6a5823b) — one mLDC: stock sheet = fixed point on the
  ACTUAL loaded displacement; R-TBM sliver dead; blast radius 121 green.
- **C-05+C-19 DONE** (61ff4e8) — certification consumes the ladder's
  sheet (structure mass identical); buildability refusal = missing
  metric, round-bilge class CFD-eligible (case b REFUSE-by-veto ->
  MARGINAL 0.777).
- **C-20 DONE** (f680750) — renders untracked; J6 guard probes ls-files;
  reconcile C3 predicate follows the invariant; cycle_time seed re-based
  with measurement.
- **C-11 DONE** (41e2a4d) — NU_SEA one-name-one-number; Michell
  population pins re-based as cross-platform bands (gapfix_physics
  26/26, first fully-green run on this box).
- IN FLIGHT: full-suite baseline (minus the two formerly-hanging suites,
  now fixed) + test_surrogate_honesty on the fresh baselines.
- REMAINING (plan): C-06 manifest-applied + make_case --mission lane,
  C-07 manifest Fn/Re from ev, C-15 broad-except, C-16 gate-runner
  timeout, C-18 screen wired, C-12/34/35 wire fronts, C-25 labels,
  C-28 docs wave, C-29..C-36.

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
