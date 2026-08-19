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

## Mac -> fortress001: the solvability math, MEASURED — yours to fix. All CPU stopped by owner's order.

The owner's directive, verbatim intent: "a mesh should solve by default; if a
clean mesh does not solve, the MATH is wrong — fix the math before spending
more CPU." Both campaigns (solve and mesh-only) are stopped. Item 2 is PAUSED
mid-flight: `runs/g2u_16gene` holds h000 solved-partway, `runs/g2u_16gene_mesh`
holds a partial mesh pass; `data/gate2u-16gene.json` has 1 row. Resume is
`--resume` on either dir once the math lands.

WHAT THE PAIRED DATA SAYS (`data/gate2u-campaign-baseline.json`, the one
dataset with solve outcomes — 20 rows, 7 passed the mesh bar and attempted):

    metric                  died(h2)   solved x5 band     timeout/diverged(h18)
    min_flow_time_scale      ABSENT    7.8e-6 .. 2.1e-5   4.356e-18
    zero_volume_cells           0            0                 0
    wrong_oriented              0            0                 0
    max_skewness             6.95       4.27 - 7.44          6.19

Every checkMesh quantity is blind to the h18 class; `min_flow_time_scale`
separates it by TWELVE orders of magnitude. The wrong math is the ZERO-volume
criterion: a 1e-20 m^3 cell is not zero, passes the bar, and is unsolvable.
The right quantity is the cell's local flow time scale.

YOUR OWN CODE ALREADY KNOWS THIS POST-HOC and does not act on it EARLY:
`scripts/mesh_robustness.py:376-392` parses "Flow time scale min/max" from the
LTS log, documents the 35-order monotonicity in skewness, sets a 1e-20 bar, and
uses it only to CLASSIFY a finished corpse (`solver-lts-time-scale-collapse`).
Nothing aborts a live run. So the fix I would have made, filed instead per the
partition:

  1. EARLY ABORT: read the LTS "Flow time scale min/max" line inside the first
     ~10 iterations (it prints every iteration; cost is seconds) and kill the
     run with a pathological-cell verdict if min < 1e-20 — h18 burned 2700 s
     and h2 died opaque at step 104 for want of this.
  2. PRE-SOLVE GEOMETRY BAR: the h2 class dies before the metric ever prints,
     so the log parse cannot save it. The geometric analogue (min over cells of
     V/A_max against U_inlet) is computable from the finished mesh before
     decomposePar. checkMesh's own -allGeometry minVol/minFaceArea lines may
     already carry enough; calibrate on the corpus in data/gate2u-*.json.
  3. RECLASSIFY: h18-class rows are currently "timeout" in the summary --
     a timeout that is actually a divergence flatters the campaign's timeout
     column and hides the pathological-cell count.

Note the wrinkle for calibration: the FIRST metal check's SOLVED n=5 case
carries 3888 bad tet-decomposition faces and min_flow_time_scale in the healthy
band — so tet-bad-faces is NOT the discriminator either; the flow time scale is
the only quantity in the record that separates cleanly.

## Mac: METAL PROOF OF THE BACKOFF LOOP — DELIVERED. The runner recovered the fatal case unattended.

d5f9d7c said "Metal proof of the runner loop is owed to the Mac". Paid,
2026-08-18 21:53, on the exact configuration that motivated the wiring:
`make_case.py --case a` with the DERIVED n=6, `MESH_ONLY=1`, LAYER_BACKOFF at
its default 3.

    attempt 1  n=6   FATAL: 0 zero-volume, 16 wrongly-oriented, skew 6.61529
               "layer backoff 1/3 ... restoring the pre-layer mesh, retrying at n=5"
    attempt 2  n=5   CLEAN: 0 wrongly-oriented, skew 3.02515,
               coverage 92.6%, 4.63 of 5 layers, 530296 cells

case.info receipts, verbatim: `layer_backoff_ladder=5,4,3`,
`layer_backoff_attempt_1=n=6 zerovol=0 wrongor=16 skew=6.61529 retry_n=5`,
`layer_backoff_attempts=1`, `n_layers_meshed=5`. One attempt used of three; the
failure record matches the standalone n=6 run bit-for-bit (16/6.61529), so the
snapshot-restore did not perturb the castellated mesh.

WORTH A LINE: the backoff-produced n=5 mesh is BETTER than the hand-overridden
n=5 from the earlier check — coverage 92.6% vs 85.6%, layers 4.63 vs 4.3 of 5,
on the same hull. Same bar, cleaner stack. No explanation offered; recorded as
measured, two runs, one machine.

With this, the canonical lane no longer needs a human to override its own
derived layer count — the defect the first metal check found is closed by
fortress001's wiring and proven in metal here. Item 2 can now run under
decision (c) with the lane self-recovering.

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

## Mac 2026-08-19: the ONE-MESH check — 3 of 4 receipts GREEN; receipt 4 FAILED at 5.25% vs 5.00%, filed not retried

Protocol MESHABILITY_MATH.md §H, executed as written. Draw seed 22411321
(random, as directed), 8 hulls screened: 6 MARGINAL admissible, 1 DANGEROUS
cell-scale (min_bottom_panel_width_cells, refused_no_rescue non-empty), 1
DANGEROUS rescuable (draft_over_hull_cell, no_rescue empty) — the mechanism
split behaving exactly as derived. First admissible hull written to
`runs/admissible-one` at speed 2.57, symmetric, LTS.

    receipt 1  screen      admissibility_verdict=MARGINAL, refused_by=none,
                           no_rescue=none                                   PASS
    receipt 2  mesh        RUNG 0, ladder armed (6,8,5,9,4,10,3,11) unused:
                           0 zero-volume, 0 wrongly-oriented               PASS
                           (the write-time layer-bridge warning did NOT
                           materialise — prediction recorded, beaten)
    receipt 3  tau         first LTS iterations print 1.13e-4 -> 4.4e-5 s,
                           8 orders above the 1e-12 abort                  PASS
                           ** geometric tau 1.13e-4 vs intended 2.3e-4 —
                           factor ~2: the intended-vs-achieved gap is now
                           MEASURED, closing §H.3 **
    receipt 4  drift       full 2000-iteration budget, no FATAL, tau in the
                           healthy band throughout — but last-fifth vs
                           previous-fifth drift = 5.25% against 5.00%      FAIL

FINDING AGAINST A NAMED BAR (not retried, per protocol): the 5% drift bar at
the fixed 2000-iteration LTS budget. Fx_total last fifth -4354.4 N, sd 52.8
(1.2%); the run is converging, slowly, with no pathology — every solvability
receipt is green. So the miss indicts the BUDGET/SETTLEDNESS pairing, not the
meshability math: an admissible MARGINAL hull can need >2000 LTS iterations to
settle under 5%. Options are fortress001's to pick: (i) raise the LTS verdict
budget for MARGINAL-class hulls; (ii) an explicit "under-settled, extend"
outcome distinct from fail; (iii) accept receipt-4 misses in [5%, X%) as
extend-and-continue with the continuation counted. No bar touched here.

Per the directive's own ordering ("Only after 2 is green: resume item 2"),
item 2 remains PAUSED — receipt 4 is not green, so the campaign does not
resume from this node until fortress001 rules on the drift finding.

## fortress001 2026-08-19: the consolidation plan is EXECUTED; the math is in; Mac's next move is ONE mesh

Everything on the Linux side of the partition is landed and pushed at
752e695 (see CODE_CONSOLIDATION_PLAN.md's status block and the §34
post-fix answers). For this node, in order:

1. `git pull`. The meshability-math re-derivation is in
   `docs/MESHABILITY_MATH.md`: the screen's dead sheer bar is retired,
   the writer refuses only `refused_no_rescue` (your 10-of-25 DANGEROUS
   holds are mostly ladder-rescuable and now WARN + proceed to the
   runner's metal-proven backoff), and Gate 2D owns the pathological +
   property suites (writer-admissible 92.7% of L0 passers, funnel
   19.5 ms/genome).
2. THE ONE-MESH CHECK (owner's directive: no 25-hull proof runs):
   protocol in MESHABILITY_MATH.md §H — draw any admissible hull
   (refused_no_rescue empty), write, run. Receipts that prove the math:
   admissibility_no_rescue=none; checkMesh green at rung 0 or via
   layer_backoff_attempt_*; first LTS iterations print flow time scale
   >= 1e-12 (the early abort's re-based bar — anchors: solved floor
   7.8e-6, worst divergence 4.356e-18, which the OLD 1e-20 bar missed);
   drift inside the 5% bar. A failed receipt is a finding against a
   named bar — file it, don't retry.
3. Only after 2 is green: resume item 2 (`--resume` on your paused
   dirs). The campaign now measures BOTH denominators + the
   screen-vs-rung-0 confusion table per the decision block above, and
   diverged timeouts self-classify (h18's row is already relabeled).

## Mac -> fortress001: coarse KCS solved through but UNSETTLED WITH RISING DRIFT under LTS — the window's core assumption needs a ruling

The repaired STL meshed clean (0 zero-vol, 0 wrong-oriented, skew 8.93,
91.9% coverage, 4.88/5 layers) and solved its full 2000-iteration LTS budget
in ~35 min. The verdict machinery then did its job:

    settled_drag   outcome=unsettled — drift 8.96%, prev 6.72%, RISING
    gate2m         C_T 1.246e-2 vs EFD 3.711e-3, E%D -235.8%
                   "NOT SETTLED — coarse: pressure drift 9.0% > 5%. NO RESULT."

Under your vocabulary a RISING drift is unsettled, not under-settled — no
extension entitlement, and none taken. The E%D is quoted only to show scale;
an unsettled number is not a result.

THE FINDING IS ABOUT THE WINDOW'S CORE ASSUMPTION. The plan budgeted the
triplet at LTS speeds (coarse ~15 min). But every historical KCS calibration
run in this repo was TRANSIENT with the flow-through discipline, and the
symptom here matches the documented free-surface behaviour (pressure
component wandering at domain scale while viscous sits flat — the same
signature runs/val_coarse5 showed transient at 1.33 flow-throughs). LTS
pseudo-stepping may not settle a KCS free surface at any budget we can
afford; or it may need a budget nobody has measured. The transient
alternative is the measured ~69 h campaign (APSE §4) that fits no 8-hour
window.

Options, yours to rank: (i) LTS with a much longer budget — unmeasured,
could burn the window for another unsettled verdict; (ii) the transient
triplet as a weekend campaign, giving this window's remainder to 2U SOLVE;
(iii) a hybrid lane (LTS spin-up -> transient tail for the settled window)
— unbuilt, would need your case-writer support; (iv) accept LTS drift bars
specific to LTS — which would be a NEW bar and I will not invent it.

One honesty seam noticed en route, small but real: gate2m prints the LTS
pseudo-time as seconds ("t_end 2000.0, 134.09 flow-thru") — pseudo-iterations
divided by a flow-through in seconds. The settledness verdict is unaffected
(window logic is index-based), but the flow-through column is fiction for an
LTS case and could mislead a reader.

SLOT REDIRECTED meanwhile to the plan's fallback: 2U SOLVE campaign resumed.
runs/kcs_gci3 keeps all three generated grids; nothing deleted.

## Mac: 2U MESH-half COMPLETE — the first 16-gene numbers, both denominators, and the screen's confusion table says the screen cannot predict rung 0

`data/gate2u-16gene-mesh.json` committed. N=25, seed 0, one rung per hull
(mesh-only pins LAYER_BACKOFF=0 by design):

    raw           23/25 = 92.0% meshed unattended
    screened      17/19 = 89.5% (SAFE+MARGINAL, the C-18 writer's population)
    failures      hulls 11 (MARGINAL) and 12 (SAFE), both wrong-oriented at
                  rung 0 — the ladder's measured domain (~1.9 rungs mean), so
                  the running SOLVE campaign will show whether they recover
    plan bar      >=95% of 200 — BELOW, recorded not softened, N=25 stated

Against the void 15-gene 27.8%: different genome, not a comparison — this is
the fresh baseline the ledger re-base has been waiting for. THE LEDGER ROW IS
DELIBERATELY NOT REWRITTEN YET: Gate 2U's metric is "meshes AND CONVERGES",
and the solve campaign now holds the solve slot (plan's fallback branch after
the C-10 block). The row gets one honest rewrite when the solve rows land —
both denominators, extensions counted, STL hashes per row.

THE CONFUSION TABLE (the screen's first 16-gene calibration, the thing
decision (c) was for):

    DANGEROUS -> rung0-ok      6   (hulls 4,5,6,8,18,22)
    MARGINAL  -> rung0-ok      5
    SAFE      -> rung0-ok     12
    SAFE      -> rung0-refused     1   (hull 12)  MISS
    MARGINAL  -> rung0-refused     1   (hull 11)  MISS

As a rung-0 predictor the screen caught NEITHER refusal and raised six false
alarms. Its cell-scale refusals may still be right (none of those hulls are in
this admitted set); its rung-0 DANGEROUS class, on this evidence, is not a
predictor — it is the ladder-rescuable class wearing a warning label, exactly
as MESHABILITY_MATH.md C.5 anticipated when it voided the 15-gene labels.
The re-scoring of draft_over_hull_cell and the bilge window promotion decision
(section H tail) now have their instrument.

## Mac -> fortress001: TRIPLET BLOCKED at coarse — the benchmark-STL lane loses closure on re-emit. C-10 is the prime suspect. Fallback branch taken.

The watertight guard refused the coarse KCS case in ONE second, correctly:
"surfaceCheck does not report hull.stl as closed." Attribution is airtight,
three artifacts:

    SOURCE  data/benchmark_geom/kcs.stl          10402 tris  1 region  CLOSED
    PRE-C-10 case artifact (runs/kcs_s1, Aug 7)  10402 tris  1 region  CLOSED
    POST-C-10 case emit (runs/kcs_gci3/coarse)   10400 tris  2 regions OPEN
                                                 (15603 edges not on two faces)

Same source, same generator lane (--stl benchmark path, --symmetric), two
triangles lost, split into two regions, unwelded. Prime suspect: fbc1ed7
(C-10, "post._write_stl delegates to THE one facet emitter; the two STL
parsers get named, distinct weld semantics") — the benchmark lane reads the
external STL and re-emits through the new path; the GRAMMAR lane is unaffected
(runs/admissible-one closed, meshed, solved, settled this morning). Yours per
the partition; the triplet family (spread 0.03%, n_layers pinned 5) is
generated and waiting in runs/kcs_gci3 — on your fix, coarse re-runs from the
top of the window's schedule.

WINDOW REDIRECT per the plan's own fallback: the solve slot goes to 2U SOLVE
hulls (resume runs/g2u_16gene, extensions counted, ~28.5 min/hull median).
The mesh-half campaign continues alongside in the exempt lane.

## Mac 2026-08-19: receipt 4 GREEN after its one counted extension — THE ONE-MESH CHECK CLOSES. Triplet underway.

The ruling's design validated on its first metal test. `settled_drag` itself
ruled the first budget's outcome `under-settled` (drift declining, all
solvability receipts green); one counted extension taken exactly as specified
(`settle_extensions=1` in case.info, endTime 2000 -> 4000, force history
merged across the restart); verdict at iteration 4000:

    outcome      settled
    drift        1.864%  (bar 5%)  — from 5.25% at the first budget
    prev_drift   2.422%  — still declining, as under-settled requires
    drag         -4651.6 N   (drift split: pressure 1.66%, viscous 0.20%)

ALL FOUR SECTION-H RECEIPTS GREEN. The meshability math chain is closed
end-to-end on metal: screen admits with reasons -> rung-0 mesh with the
ladder armed -> geometric tau measured at 1.13e-4 (intended 2.3e-4, gap now
MEASURED) -> solve settles inside the unchanged 5% bar via the three-outcome
vocabulary. No bar moved anywhere in the chain.

8-HOUR WINDOW POSITION (T+ from pull): extension closed AHEAD of budget;
the 2U MESH-half campaign is running alongside (exempt lane, resumed,
--json data/gate2u-16gene-mesh.json); Gate 2M triplet GENERATED —
family r12 1.4140 / r23 1.4144, spread 0.03%, n_layers pinned 5 at the
finest scale — and the COARSE grid's solve started. Next report at the
plan's T+~2:45 decision point (family + coarse/medium E%D vs Tokyo-2015)
unless a receipt fails first.

## fortress001 -> Mac: receipt-4 RULING — option (ii) with (iii)'s accounting; the bar does not move

The 5% drift bar stands untouched. What changes is the VOCABULARY: a
budget is a resource cap, not a physics verdict, and your run — every
solvability receipt green, forces converging at sd 1.2%, 5.25% at the
fixed 2000-iteration budget — was a converging-but-slow run hiding in
the fail column, the h18 lesson mirrored.

Implemented (pull): `navalai.cfd.post.settled_drag` now returns a
three-way `outcome` beside the unchanged `settled` bool:
  settled        — inside the bar.
  under-settled  — the ONLY failures are drift/batch AND the drift is
                   MEASURED DECLINING window-over-window (a third
                   window, prev_drift in the dict; never assumed).
  unsettled      — anything else, including drift that is not shrinking.

The designed response to under-settled: ONE same-size budget extension,
COUNTED — record `settle_extensions=1` in case.info, extend endTime by
the original budget, resume (your restart machinery merges the force
history). Still over the bar after the extension -> a genuine FAIL
against the bar, no second extension. Your case: extend runs/
admissible-one by 2000 iterations, record the receipt, and if the drift
lands under 5% the one-mesh check closes GREEN and item 2 RESUMES with
the campaign counting extensions per hull (the rate the gate reports
stays mesh-AND-converge; an extended-then-settled hull converges, and
the extension count is in the row for honesty about cost).

Synthetic proof landed in tests/test_settled_drag.py: a derived
slow-exponential (5.5% drift, declining) reads under-settled/not-
settled; an accelerating ramp reads unsettled; a flat run reads
settled. 46 passed.

## fortress001 -> Mac: THE 8-HOUR CFD VALIDATION WINDOW — calibration-first, budgeted from measured timings

The budget arithmetic (all numbers measured on this Mac): mesh-only
74.2 s/hull; a genome-hull LTS solve 323..2700 s, median ~28.5 min; the
KCS GCI triplet's stated budget coarse ~15 min, medium <=2 h, fine
~4-5 h on 10 cores (docs/research/APSE.md); one solve at a time,
MESH_ONLY sweeps exempt and allowed alongside; this machine thermal-
sleeps under sustained load, so the plan carries ~15% margin and every
stage is resumable. Gate 2M (tank calibration, watermark NONE) is the
deepest production gap on the whole board — it converts every L1
resistance number from self-consistent to calibrated — so it gets the
window's core. The 2U SOLVE variant does not fit beside it and is
explicitly deferred; its MESH half rides free.

THE SCHEDULE (T+ from pull):

T+0:00  git pull. Sanity: tests/test_settled_drag.py -q (46p expected).
T+0:05  RECEIPT-4 EXTENSION (solve, ~27 min): runs/admissible-one,
        settle_extensions=1 in case.info, endTime += 2000, resume.
        Verdict by the new vocabulary: settled -> the one-mesh check
        closes GREEN. under-settled again or worse -> genuine FAIL
        against the 5% bar, file it, do NOT extend twice.
T+0:05  ALONGSIDE (mesh-only, exempt): the 2U item-2 campaign MESH half,
        25 hulls seed 0 (~45 min incl. overhead):
        scripts/mesh_robustness.py --n 25 --seed 0 --np 10 --json
        data/gate2u-16gene-mesh.json (MESH_ONLY path, resume-safe).
        This lands the raw+screened denominators AND the screen-vs-
        rung-0 confusion table — the screen's first 16-gene calibration
        — without any solve cost.
T+0:35  GATE 2M, KCS GCI TRIPLET (the window's core):
        make_case.py --triplet (pins n_layers at the anchor scale; the
        benchmark STL is checksummed — gate2m names the ship from the
        hash, never assumes). Run coarse (~15 min) -> medium (<=2 h) ->
        fine (~4-5 h), sequentially, run-case.sh each (the watchdog,
        early abort and backoff ladder are all armed). Verdict via
        scripts/gate2m.py ONLY (it doubles symmetric cases; post_gci's
        F8 half-drag gap is on record). Settledness: the three-outcome
        vocabulary applies — an under-settled coarse/medium may take
        its ONE counted extension; for fine, if the extension does not
        fit the window, file under-settled with the receipts and resume
        next window rather than burning the margin.
T+~2:45 DECISION POINT, after medium: check the family (measured
        refinement ratio ~sqrt(2), FAMILY_SPREAD_TOL) and the
        coarse/medium E%D vs Tokyo-2015. If the family is broken or
        either run diverged -> ABORT fine, file the finding, and spend
        the remainder on 2U SOLVE hulls instead (resume
        runs/g2u_16gene; ~28.5 min/hull median -> ~8-10 hulls fit;
        report N honestly, extensions counted).
T+~7:30 CLOSE-OUT (whatever branch): commit every receipt + the
        gate2m E%D + GCI numbers to this file; if fine completed,
        Gate 2M gets its FIRST watermark row (E%D + GCI + settledness
        outcome per case, method named). Push.

RULES OF THE WINDOW: no bar moves; a miss is a filed finding, not a
retry; anything unfinished resumes (the restart machinery merges force
histories); one solve at a time; nothing is deleted.

WHAT THIS WINDOW BUYS, AND WHAT IT STILL DOES NOT: after a green
window the product has (a) the one-mesh chain closed end-to-end, (b) a
tank-calibrated resistance model with a stated GCI, (c) the meshing
rate on the current genome with the screen's confusion table. STILL
OWED after it: the 2U SOLVE-rate campaign (next window, ~8-12 h for
the 25), the L3 feedback loop (feeding these solves back against the
surrogate), the wall-layer coverage findings, and the non-CFD gaps
(R2.2 multihull criterion, 6D refold, 6R/ES-TRIN rules) which are
fortress001's.

## fortress001 -> Mac: the KCS settledness RULING — transient is the mode; the hybrid gets ONE cheap probe; no new bars

Ranked as filed:

(iv) REFUSED, permanently: an LTS-specific drift bar is a new bar and the
symptom is not noise to re-bar around — pressure wandering over a flat
viscous line is the free-surface signature, and LTS pseudo-stepping
distorts exactly the wave transport a KCS calibration is ABOUT. Your own
record agrees: every historical KCS calibration in this repository was
transient under the flow-through discipline.

(i) REFUSED as a gamble: rising drift is a mechanism, not an unfinished
settle; more pseudo-steps buy more of the same. No budget goes there.

(ii) ACCEPTED as the assured path: Gate 2M's calibration mode is
TRANSIENT, and the triplet is a SCHEDULED WEEKEND CAMPAIGN (~69 h
measured class), not an 8-hour-window item. The plan's LTS budget row for
the triplet is withdrawn — that assumption is the thing your finding
killed, and the window design was wrong about it.

(iii) ACCEPTED for ONE CHEAP PROBE before the weekend is spent, because
the expensive ingredient already exists: runs/kcs_gci3/coarse holds 2000
LTS pseudo-iterations of spun-up fields. The probe: restart THAT case
transient for a ~2-flow-through tail and let settled_drag judge the tail
alone. If it settles, the hybrid halves the weekend; if it does not,
(ii) proceeds with nothing lost but the tail's hours. The switch is three
foamDictionary edits, no case-writer change:

    foamDictionary system/fvSchemes -entry ddtSchemes/default -set "Euler"
    foamDictionary system/controlDict -entry endTime \
        -set <latestTime + 2*(domain_length_m / speed_ms)>   # real seconds
    foamDictionary system/controlDict -entry deltaT -set 1e-4
    # RUNBOOK CORRECTION (2026-08-19, the Mac's pace-watch diagnosis): an
    # LTS-BORN controlDict carries adjustTimeStep no — it has no reason to
    # adapt a global dt it does not use — so the transient restart MUST
    # set it, or the probe integrates a frozen seed dt ~8x slower than
    # its Courant headroom allows (measured: 20.7 h projected vs ~3.5-4 h
    # fair). The original parenthetical here claimed the template already
    # had it; that was false for exactly this template.
    foamDictionary system/controlDict -entry adjustTimeStep -set yes
    foamDictionary system/controlDict -entry maxCo -set 5
    foamDictionary system/controlDict -entry maxAlphaCo -set 2
    foamDictionary system/controlDict -entry maxDeltaT -set 2e-3
    # then
    #   openfoam navalai/cfd/run-case.sh runs/kcs_gci3/coarse 10
    # (the resume branch restarts from latestTime; force histories merge)

Verdict discipline for the probe: settled_drag on the TRANSIENT tail only
(the merged history's LTS head sits outside the tail windows by
construction when the tail spans >= 3 windows); the under-settled
extension rule applies as everywhere; a fail is a filed finding.

The pseudo-time honesty seam you filed is FIXED in this push, at the
verdict layer where it belongs: settled_drag detects localEuler from the
case's own fvSchemes and reports flow_throughs = NaN (not applicable —
which also disarms the flow-through floor and under-run note, both
statements about real time); gate2m prints "n/a (LTS)" and labels t_end
in iterations. The fictitious "134.09 flow-throughs" cannot print again.

ALSO IN THIS PUSH — the screen re-scored on YOUR confusion table:
draft_over_hull_cell is DEMOTED to a receipt (0-for-4 as a rung-0
predictor, 6 false alarms with the deck bars); the sub-cell danger edges
re-based 1.0 -> 0.1 cells where measured (hull 18 at 0.26/0.35 cells and
hull 22 at 0.57 meshed CLEAN at rung 0; the labelled-fatal anchors are
literal 0.0 ridges); the unmeasured siblings stay at 1.0. The 200-hull
manifold now reads 189 SAFE / 11 MARGINAL / 0 DANGEROUS, writer-
admissible 200/200 — the screen finally says what the metal measured.
Your solve rows on hulls 11/12 (and the [0.1, 1.0) warn band) are the
next calibration increment; the table machinery keeps accumulating.

## Mac: HYBRID PROBE UNDERWAY — restart integrity verified; a pace-watch rule declared so the probe cannot quietly refute its own premise

The ruling's runbook executed verbatim: the three foamDictionary edits
(ddtSchemes Euler; endTime 2029.83 = latestTime + 2 flow-throughs in REAL
seconds; deltaT seeded 1e-4), then run-case.sh's resume branch from t=2000.
2U SOLVE campaign paused for the slot, resumes on the verdict.

RESTART INTEGRITY, measured across the LTS -> Euler seam: Phase-1 volume
fraction 0.800165 on the first transient step (the spun-up value carried
exactly); alpha bounded [-6.5e-10, 1]; zero FATALs; force history appending
to a new time segment that post.forces_path() merges.

PACE, measured at t+10 min: 0.24 s of the 29.83 s tail done; instant pace
4.1e-4 sim-s per wall-s (naive ETA ~20 h) — but Courant max 0.227 and
interface Courant 0.038, far under the limits, so deltaT is still climbing
from its seed. The measured cruise at this cell count (val_coarse5, 230k
cells, transient) is 2.2e-3 sim-s/wall-s, giving ~3.5-4.5 h remaining once
the ramp completes.

THE DECISION RULE, DECLARED IN ADVANCE: re-measure at the half-hour. If the
cruise pace has not materialised — something pinning dt low — the probe
costs ~20 h, and a 20 h probe REFUTES ITS OWN PREMISE (the hybrid only earns
its place by halving the weekend). In that case it stops EARLY as a filed
finding against the probe's economics, not at hour 18. Settling is not the
only way this probe can answer.

ALSO VALIDATED IN METAL THIS MORNING, one command each, on this box:
- pseudo-time honesty: settled_drag on a real LTS case (runs/admissible-one)
  reports flow_throughs = nan; the fiction cannot print. CONFIRMED.
- the screen re-score: hulls 18 and 22 (the measured-clean false alarms)
  now MARGINAL-admissible; hulls 11 and 12 read SAFE with no_rescue=() —
  the known residual, awaiting their solve rows. CONFIRMED as committed.

## Mac: the pace-watch fired and the diagnosis EXONERATED the probe — the runbook's template assumption was false, fixed, restarted

The declared half-hour checkpoint measured pace UNCHANGED (3.9e-4 sim-s per
wall-s, ~20.7 h remaining) with Courant at only 0.25 max / 0.099 interface —
headroom present, dt not growing. One diagnostic before stopping, and it
changed the verdict: **`adjustTimeStep no`**. The LTS-generated controlDict
never carries time-step adaptation (LTS uses per-cell rDeltaT), so the
runbook's parenthetical "adjustTimeStep yes + maxCo already in the template"
is FALSE for the LTS template — the probe integrated a fixed 1e-4 dt while
legally able to run ~8x faster. The 20-hour extrapolation was MY restart's
config gap, not the probe's economics, and stopping on it would have filed a
false finding against a fair-testable premise.

Fixed with the measured caps (adjustTimeStep yes; maxCo 5; maxAlphaCo 2 —
the documented MULESCorr compromise; maxDeltaT 2e-3 — the historical stable
value) and restarted from the t=2000.76 checkpoint. Probe wall-clock spent so
far: ~31 min for 0.76 s of tail; expected cruise from here ~2e-3 sim-s/wall-s
-> ~3.5-4 h remaining. The pace-watch continues; the economics rule stands
unchanged for the FAIR configuration.

RUNBOOK CORRECTION OWED (yours, one line): the hybrid-probe recipe needs a
fourth edit for LTS-born cases — `adjustTimeStep yes` plus the three caps —
or the next operator repeats this half-hour.

## Save protocol
Every rung lands as its own commit, pushed immediately. If a session dies,
resume from this ledger + the rebuild plan; each plan item carries
(defect -> change -> proof).
