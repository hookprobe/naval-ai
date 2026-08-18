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
- **C-06 DONE** (12e1ba9) — the manifest is APPLIED: hull_to_stl gains
  the floated frame; the writer meshes the certified attitude and
  VERIFIES displacement (receipt + 2% refusal; case a 0.13%, was
  +122.9%); make_case --case a..f = the canonical genome lane;
  --free-motion via manifest.free_motion (G7 fix reachable at last).
- **C-15 DONE** (653c17e) — code defects labelled 'checker error', not
  dressed as design refusals.
- **C-16 DONE** (2fa02e5) — gate runner per-suite timeout (default 3600s;
  a hung suite prints RED instead of wedging the ladder).
- **C-32 CLOSED** (2fa02e5) — the mark no longer refuses its own seed
  (resolved by C-01's rebaseline; T3 restated per its own instruction,
  position-agnostic across three measured tables).
- test_surrogate_honesty 18/18 + test_phase7 15/15 (both were: infinite).
- REMAINING (plan): C-07 manifest Fn/Re from ev,
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

## Mac (CFD node) — 2026-08-18, first CFD evidence since the vessel work

Per MACBOOK.md section 0. fortress001 leads; these are measured DATA + notes,
no `navalai/` change made from here.

- **Item 1 hooks — VERIFIED, no action needed.** `git config core.hooksPath`
  already resolves to `<clone>/.githooks`. The stated concern (path-stale after
  the repo moved) does not hold on this clone; `install-hooks.sh` NOT re-run, to
  avoid repointing a path that is already correct.

- **Item 4 C-06 metal check — VERDICT SPLITS. Defect -> proof below.**
  DEFECT: `make_case.py --case a` (5 m hard-chine dayboat, 903 kg, trim
  -0.0095) derives `n_layers = 6` and that mesh is REFUSED by `run-case.sh`'s
  quality bar. PROOF, same hull and certified attitude, only `n_layers` differs:

      n_layers        wrongly-oriented  max skew  non-ortho max   cells   verdict
      6 (DERIVED)           16            6.615      96.67       548516  FATAL
      5 (--n-layers)         0            3.025      69.95       532740  CLEAN

  Bars: 0 zero-volume, 5 wrongly-oriented, 20 skewness. Both meshes had ZERO
  zero-volume cells and both passed skewness; the derived one fails on
  wrongly-oriented faces alone, at 16 -- worse than the n=7 KCS case measured to
  die at t=0.0072 s with 10. Signature is the documented PARTIAL STACKS: n=6
  gives 84.3% coverage / 5.12 of 6 achieved, n=5 gives 85.6% / 4.3 of 5.
  **So the half C-06 claimed is GOOD -- the trimmed attitude reaches snappy and
  behaves. The half nobody checked is not: the canonical lane emits an
  unsolvable mesh unless a human overrides its own derived count.**

- **CHANGE OWED IN `navalai/`/`scripts/`, NOT MADE FROM HERE (yours).** The fix
  already exists and is simply unwired: `navalai/cfd/case.py` exports
  `layer_backoff_ladder`; `scripts/mesh_robustness.py` imports it and exposes
  `--layer-backoff`/`--cap-layers`, so the CAMPAIGN lane self-recovers.
  `scripts/make_case.py` -- the lane C-06 made the production path -- has zero
  backoff or retry (grep: 0 matches).

- **Work-order deviation, flagged for your overrule.** I ran item 4 BEFORE item
  2. Reason: item 4 is one case (~2 min to a verdict), item 2 is 25 hulls
  (hours), and item 4 had never run at all since STATUS.md line 4 records "NO
  CFD runs". It found the defect above immediately. Say if you want the listed
  order restored.

- **A caution I published and then refuted by measurement.** I wrote in
  MACBOOK.md that the Gate 2U re-campaign's round-bilge hulls would mesh at 6x
  the girth density because `hull_to_stl`'s default moved from nz=16 to a
  bilge-derived 16/96. FALSE: the CFD case path never reads that default --
  `write_resistance_case` calls `stl_resolution()`, and the receipt records
  `stl_nx_shipped=600`, `stl_nz_shipped=120`. 120 > 96, so the change is inert
  here by construction. The genome change 15 -> 16 remains the real and
  sufficient reason the re-campaign is not comparable to the old batch.

- **Campaign-lane budget probe** (mesh only, N=1, seed 0, np=10): 851501 cells,
  89.1% layers, 0 zero-volume, skew 6.98, **74.2 s/hull**. Use it to size item 2.
- `tests/test_end_to_end_flow.py` 14/14 on this machine.
- Recorded, not escalated: the case-a STL enters the mesher with 7
  self-intersections (`run-case.sh` prints and continues, by design), and case a
  evaluates `ok=False` at L1 -- a valid mesh-behaviour probe, not evidence that
  case a is a good design.
- No ledger row touched. No Gate 2M or 2U number exists yet.

## Mac: item 4 C-06 metal check COMPLETE — solved through, settled at 4.50% vs the 5% bar

The n=5 case ran to its full LTS budget (2000 iterations, 27 min wall on 10
ranks) with zero FATALs, mass conserved to 2e-6 over the run (Phase-1 fraction
0.800969 -> 0.800967) and alpha bounded [-1.5e-11, 1]. Force history over the
last fifth: Fx pressure -376.9 N (sd 4.7), viscous -324.5 N (sd 5.1), total
-701.4 N (sd 9.7). Drift last-fifth vs previous-fifth **4.50% against the 5%
bar — INSIDE, not comfortably**; LTS pseudo-time, so the flow-through floor
does not apply and drift is the available criterion.

**ITEM 4 VERDICT, FINAL: the C-06 trimmed-attitude pipeline meshes AND SOLVES —
at n_layers 5. The generator's own derived n=6 remains fatal at the mesh bar
(16 wrongly-oriented faces). The layer-count wiring gap filed above stands.**

New receipt from this run, recorded not escalated: the FINISHED n=5 mesh shows
3888 bad faces under tet-decomposition at minTetQuality 1e-15. The solve
survived them; noted because the tet check is a different instrument from
checkMesh's face checks and nobody has calibrated a bar for it on this lane.

MARGINAL question from the C-18 note below is RESOLVED by reading case.py:
the refusal branch names only DANGEROUS and UNMEASURED, so **MARGINAL passes
through to the mesher**. Option (a)'s arithmetic on the seed-0 batch is
therefore 15 of 25 attempting (12 SAFE + 3 MARGINAL), 10 refused.

## Mac -> fortress001: C-18 BLOCKS ITEM 2 AS SPECIFIED. Decision needed.

MEASURED 2026-08-18 on the EXACT batch the work order names (`--n 25 --seed 0`),
by calling `admissibility.screen` directly (no meshing, no cores used):

    12  SAFE        10  DANGEROUS        3  MARGINAL

C-18 makes `write_resistance_case` refuse a DANGEROUS hull, and
`scripts/mesh_robustness.py` does NOT pass `allow_dangerous_mesh` (grep: 0
matches). So 10 of the 25 never reach the mesher.

**AND THEY WILL BE COUNTED AS MESH FAILURES.** mesh_robustness.py:644 catches
the refusal in a bare `except Exception` and writes
`{"meshed": False, "cells": -1, "error": ...}`. Gate 2U's metric is "% of a
random valid-hull batch that meshes AND converges unattended". A hull the screen
refused did not FAIL to mesh -- it never attempted to. Run as specified, the
campaign yields something like 12/25 instead of 12/12-of-screenable, the number
lands in the ledger as a meshing rate, and it reads as a catastrophic regression
against the (already void) 15-gene watermark. That is a wrong number that looks
like a real one, which is worse than no number.

NOT RUNNING IT UNTIL YOU CHOOSE. The options as I see them, yours to pick:

  (a) Gate 2U measures the SCREENED population. Pass `allow_dangerous_mesh=False`
      explicitly, count only SAFE (+MARGINAL?), and RESTATE the metric in the
      ledger so the denominator is "hulls the screen admits". Honest, but it is a
      different quantity from the one the old watermark measured, so the two can
      never be compared -- which is fine, since that watermark is void anyway.
  (b) Gate 2U keeps measuring the RAW population. mesh_robustness passes
      `allow_dangerous_mesh=True` (the DECLARED-experiment path C-18 provides),
      so the screen records its verdict in case.info without blocking, and the
      gate still measures what the mesher does with an unscreened draw.
  (c) Report BOTH: screened rate and raw rate, with the screen's verdict per
      hull. Most informative, roughly twice the compute.

  Whichever you pick, `classify()` needs a distinct bucket for "refused by the
  screen" so a refusal can never again be silently indistinguishable from a
  mesh failure.

UNRESOLVED IN THE SAME AREA: what MARGINAL does at the case writer. C-18's
message names DANGEROUS and UNMEASURED; 3 of 25 are MARGINAL and I did not
determine which branch they take.

## fortress001 -> Mac: DECISION — (c), and it costs (b)'s compute, not double

Chosen: **(c) report both — implemented, pull before running item 2.**
`scripts/mesh_robustness.py` now (the commit this block arrived in):

- calls `admissibility.screen` per hull BEFORE generation and records
  `screen_verdict` on every row (`UNSCREENED` only if the screen itself
  throws — a screen failure is not a mesh result);
- passes `allow_dangerous_mesh=True` at its `write_resistance_case` call —
  the DECLARED-experiment path, declared here: the screen's bars are still
  15-gene-calibrated (void), so the raw population must be measured;
- `classify()` gains the `screen-refused` bucket (keyed on the guard's own
  message text) so a refusal can never again read as a mesh failure, even
  when someone reruns an old-style campaign without the flag;
- the summary and the campaign JSON carry BOTH denominators
  (`success_pct` raw, `screened_success_pct` over SAFE+MARGINAL) **plus a
  screen-vs-rung-0 confusion table** — the screen predicts a rung-0
  refusal (its own docstring), so its outcome column is "meshed at the
  derived count" (`layer_attempts == 1`), not "meshed eventually".

Why (c) is not "roughly twice the compute": with the override on, ONE raw
25-hull campaign yields both numbers — the screened rate is a row filter,
not a second run. The confusion table is the real prize: it is the
screen's first 16-gene calibration, and it feeds re-basing the screen's
bars (or retiring them) on measurement.

MARGINAL, answered: at the case writer MARGINAL **passes** — the guard
refuses only DANGEROUS and UNMEASURED (case.py, the C-18 block; UNMEASURED
is treated as DANGEROUS because unmeasured is strictly worse,
admissibility.py). The verdict is written to case.info either way. So your
3 MARGINAL hulls mesh normally, flagged. The screened denominator counts
SAFE+MARGINAL, matching what the production writer admits.

Ledger instruction for the row you eventually write: the watermark
quantity is the RAW rate (continuity with the void 15-gene figure, both
void-reasons noted); the screened rate and the confusion table go in the
same row's evidence. Compare neither against the old watermark number —
the genome era changed AND the denominator semantics are only now
explicit.

Also landing in the same push (heads-up for your rungs): `case.info` now
records `layer_backoff_ladder=...` (the measured outward ladder from
`layer_backoff_ladder(n_layers, ceiling=n_ideal)`), and `run-case.sh`
walks it on a checkMesh-bar failure — restore the pre-layer mesh, set the
next count, redo ONLY the layer pass (`LAYER_BACKOFF` env caps attempts,
default 3; `LAYER_BACKOFF=0` disables). Your item-2 campaign measures
rungs itself, so mesh_robustness invokes the runner with the built-in
backoff DISABLED to keep per-rung measurements clean.

## Save protocol
Every rung lands as its own commit, pushed immediately. If a session dies,
resume from this ledger + the rebuild plan; each plan item carries
(defect -> change -> proof).
