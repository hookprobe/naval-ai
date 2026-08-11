# Alignment audit — original agentic-PLM plan vs. built system

Audited 2026-07-30 against the original "Autonomous Naval Architecture
Platform" plan. Verdicts: **ALIGNED** (built as envisioned) ·
**DIVERGED** (built differently, deliberately, with research grounding) ·
**GAP** (missing; closed by the stage listed) · **BLOCKED** (needs
hardware/software this machine lacks).

## Original Phase 1 — Foundation & Grammar Compiler

| Plan item | Verdict | Evidence / fix |
|---|---|---|
| Hull grammar "type checker" (hierarchical AST, typologies) | **GAP → Stage B** | built: flat 15-param vector + 30 constraints (`grammar.py`). Missing: typology hierarchy dispatching per-type constraints. Fix: `ast.py` typed grammar with ≥2 typologies. |
| Parameter constraint solver (math boundaries) | **ALIGNED, with a corrected count** | closed-form checks, <0.05 ms, reasons reported (`grammar.check`). The "30+" this row used to claim was wrong and so was the plan's "49": the 2026-08-05 audit measured **9 live** constraints — 28 emitted, of which 15 are bound checks the optimiser cannot violate and 4 more are tautologies inside the declared bounds (0 hits in 400 000 in-bounds samples). Gap E4. |
| — incl. plywood bend limits | **GAP → Stage B** | twist-rate proxy exists; true min-bend-radius vs sheet thickness missing. Fix: longitudinal panel curvature check. |
| VAE → guaranteed-valid latent space | **DIVERGED + GAP → Stage B** | research: VAEs guarantee nothing, hard filter mandatory (kept). Built: PCA/GMM latent. Fix: proper 8-D probabilistic-PCA latent generative model (the linear-Gaussian VAE) + prior-sampling validity gate — the "8-D genome" of the original plan. |

## Original Phase 2 — Agentic PLM Network

| Plan item | Verdict | Evidence / fix |
|---|---|---|
| Orchestrator agent (mission → constraints, delegates) | **GAP → Stage C** | logic exists as functions (`translate.py`, `evaluate.py`); no agent shell / async delegation. Fix: `agents.py` message-passing network. |
| Builder agent (mutates grammar only, never vertices) | **GAP → Stage C** | invariant already structural (generative model emits parameter vectors only); agent shell missing. |
| Engineer agent (materials, weight, panel counts, interior volume, build hours) | **GAP → Stage C** | weight budget exists (`energy.py`); panel counts, interior volume, build-hours estimator missing. |
| Validator agent (topology+hydrostatics, Fitness=∞ fast reject) | **ALIGNED** | `evaluate.py` fails fast at L0 (~ms), `optimize.py` assigns 1e9 fitness; agent shell added in Stage C. |
| Async CI/CD-style pipeline | **GAP → Stage C** | current pipeline is synchronous function calls. |
| CadQuery/OpenCascade kernel | **GAP → Stage C/F** | own analytic kernel built instead (faster for this grammar); CadQuery added for STEP/IGES export if installable. |

## Original Phase 3 — Physics Validation Plane

| Plan item | Verdict | Evidence / fix |
|---|---|---|
| MuJoCo/MJX dynamics (inertia, mooring, lifting) | **DIVERGED + GAP → Stage D** | research: MuJoCo has no free surface — hydro moved to Capytaine BEM (Hulme-anchored, GREEN). The valid MuJoCo scope (mass properties, mooring, lifting loads) was missing. Fix: `dynamics.py` analytic + MuJoCo cross-check when importable. |
| GraphCast wave/weather boundary conditions | **DIVERGED → Stage D** | research: design needs climatology, not forecasts. Fix: JONSWAP spectra (Black Sea fetch-limited + riverine wake) coupled to Capytaine RAOs → response spectra. |
| OpenFOAM snappyHexMesh + interFoam automation | **CLOSED (Stage D) — was BLOCKED, superseded 2026-08-06** | case generator, `run-case.sh`, forces post-processor and Roache GCI all built and tested. Execution is no longer metal-gated: OpenFOAM v2606 runs natively on the Mac node and KCS meshes and solves. What is open is a NUMBER, not a capability — Gate 2M is RED, measured, in `data/gate-ledger.json`. |
| PostgreSQL per-hull metric aggregation | **DIVERGED** | SQLite with PG-compatible schema (single-node edge posture); every result carries hull-id, solver, version, uncertainty. Documented, not planned to change until multi-node. |

## Original Phase 4 — Autonomous Evolution & Learning

| Plan item | Verdict | Evidence / fix |
|---|---|---|
| PINNs replacing data-driven surrogates | **DIVERGED (evidence-closed)** | NeurIPS-2021 failure modes + no PINN beats data-driven on free-surface flows; ladder uses kriging/co-kriging (Forrester-anchored, calibrated). Interface admits a PINN tier if the literature turns. |
| Surrogate predicts from the 8-D latent genome | **CLOSED (Stage E), with a measured caveat** | GP on the 8-D genome works, but costs ~2–3× accuracy vs the full 15-param GP (median rel err ~0.30 vs ~0.10–0.15 at n=200). The original plan's 8-D assumption has a real, now-quantified price; the full vector remains the default surrogate input. |
| NSGA-II / CMA-ES over the latent space | **CLOSED (Stage E)** | `pareto_front_latent`: NSGA-II in the 8-D genome, decoded designs all feasible, best Wh/NM within 20% of raw-parameter search at equal budget. |
| Continuous DB-driven refinement | **ALIGNED** | `flywheel.py`: harvest → retrain → frozen-benchmark regression gate (poisoned model refused). |

## Original Phase 5 — Production & Execution

| Plan item | Verdict | Evidence / fix |
|---|---|---|
| Zig/C low-overhead runtimes for handoffs | **DIVERGED → Stage F measures** | research position: physics wall-time dominates, handoff overhead is noise. Stage F records the actual profile so the divergence is measured, not asserted. |
| Interactive dashboard w/ Pareto front | **GAP → Stage F** | slider surface exists (p95 <100 ms, tier badges); Pareto-front view missing. |
| STEP / IGES / DXF manufacturing export | **GAP → Stage C/F** | STL exists (CFD path). Fix: developable-panel unrolling → DXF; STEP/IGES via CadQuery if installable. |

## Scorecard

- Before gap-closure: ALIGNED 4 · DIVERGED (research-grounded) 6 · GAP 11 · BLOCKED 1
- **After gap-closure (stages B–F): ALIGNED/CLOSED 15 ·
  DIVERGED-with-receipts 6 · BLOCKED 0.**

> **THE SCORECARD AND THE TABLE ABOVE IT DISAGREE, AND THE TABLE IS THE STALE
> ONE. MEASURED 2026-08-11.** The scorecard claims 15 ALIGNED/CLOSED; the rows
> above show **7** (3 `ALIGNED` + 1 `ALIGNED, with a corrected count` +
> 3 `CLOSED`) with **11 still carrying the literal string `GAP`**. Spot-checks
> against the tree say the scorecard is nearer the truth: `hull_ast.py`,
> `agents.py`, `engineer.py`, `dynamics.py`, `pipeline.py` and `export.py` all
> exist, and the "Pareto-front view missing" row is contradicted by a shipped
> `Gate F` whose scope names the Pareto dash. **But presence of a name is not
> evidence of behaviour** (`docs/LESSONS.md` §8), so no row is re-verdicted here
> on inspection alone.
>
> The "before" line does not reconcile either: 4+6+11+1 = 22 tokens over 21 rows
> with 2 dual-verdict rows, where 23 is expected. It is a frozen historical
> snapshot written in the present tense.
>
> **This is defect class 4 — prose standing in for a verdict — in the file whose
> job is verdicts.** Two counts of one state, neither derived. The fix is not to
> edit the numbers: it is to re-verdict the 11 `GAP` rows **by predicate**, the
> way `scripts/reconcile_gaps.py` already derives all 119 register rows from the
> code. Scheduled as **P0-7** in `docs/BUILD-PLAN.md` §5. Until then, treat every
> row above as *unverified*, and take status from
> `python scripts/reconcile_gaps.py` and `python -m navalai.gates`.
>
> Two further corrections, measured the same day:
> - The header says "Audited 2026-07-30" while the body carries updates dated
>   2026-08-05, -06 and -07. A reader taking the header at face value under-dates
>   the file by a week.
> - The Gate 2M row states the gate is "RED on a MEASURED number rather than
>   blocked on hardware". `data/gate-ledger.json` says the opposite —
>   `watermark: "NONE — no reproducible measurement exists"`,
>   `measured_on: "NOTHING. runs/kcs ... was DELETED"`. This file claims a
>   measurement the ledger explicitly refuses to state: defect class 5,
>   reproduced inside the document that records class 5.
> - The red-gate roster below names 2M, 2U and 6R. There are **four**;
>   **Gate 4F** (79.33% against a ≥99% bar) was measured 2026-08-07, the same day
>   this file was last touched, and is missing.
  **UPDATED 2026-08-06 — the BLOCKED row is retired.** It read "OpenFOAM
  execution — templates, runner and GCI post-processor all ready and tested on
  synthetic data", which stopped being true when the Mac simulation node came
  online: OpenFOAM v2606 runs natively, KCS meshes and solves, and Gate 2M is
  RED on a MEASURED number rather than blocked on hardware. PLM §3 step 7
  requires a superseded item to be removed with a note, never left ambiguous —
  this is that note. "Blocked" and "measured and failing" are different claims,
  and the second one is worse; leaving the first in place understated the
  state of the work.
  The clause "all gates green" is also removed: it was written before Gates 2M,
  2U and 6R were red. `python -m navalai.gates` is the status.
- Measured findings produced by the closure campaign:
  1. the 8-D genome costs ~2–3× surrogate accuracy vs the full 15-param
     vector (Stage E) — the original plan's 8-D assumption now has a price tag;
  2. agent-handoff latency is <1% of one L1 physics evaluation (Stage F) —
     the Zig/C rewrite the original plan proposed would optimise noise;
  3. Capytaine diffraction forces alone are NOT the excitation force — the
     RAO long-wave-limit gate caught the missing Froude–Krylov term (Stage D);
  4. ruled-surface development had a mirror-side bug caught by the exact-
     cylinder anchor (Stage F) — analytic anchors catch what eyeballs miss.
  5. **a GCI number is worthless unless the three grids are a refinement
     FAMILY** (Gate 2M campaign, Mac): the generator snapped nz to a multiple
     of 3 to keep the waterline on a cell face, which made the z-refinement
     ratios 1.333 and 1.5 (effective r = 1.297 then 1.368) while post_gci
     assumed sqrt(2). Reported p=nan / GCI 58.5%. post_gci now MEASURES r from
     cell counts and warns when the steps disagree — an assumed r is exactly
     how a triplet reports precision it has not earned.
  6. **an unresolved free surface fails silently** (same campaign): with
     `refinementRegions {}` the wave field ran at 5.1–10.2 cells per
     wavelength against the ≥20 standard, and the background cell was
     0.63–1.25 m against ~0.1 m waves. Nothing errored; the drag simply rode
     on hull-local refinement, and one z-cell tripled it. `case.info` now
     carries cells_per_wavelength as a receipt.
  7. **`relativeSizes true` silently decouples y+ from physics** (same
     campaign): near-wall cells were ~2.7 cm, so wall functions ran far
     outside their band. Nothing measured y+ at all until a yPlus function
     object was added — the instrumentation was the finding. Corollary: the
     hull-patch AVERAGE y+ is not a metric, because the patch includes dry
     deck/topsides whose y+ inverts to a 0.18–1.4 m first cell and dominates
     it; read the min.

## Gate 2M: RAN, and RED

**This section used to carry the measured table. It does not any more, and that
is gap J1 being closed rather than information being lost.** One Gate 2M
figure was written into README, PLM §5, PLM §6, this
file and `docs/BUILD-PLAN.md` Part V.f in a single commit. Two later commits then
invalidated it — a pressure double-counting bug, and a force parser reading a
pre-restart fragment — and only `gates.py` was updated. Five figures ended up in
circulation and only one of them was reproducible from any run directory in the
repository.

So the measurement lives in exactly one place now: **`data/gate-ledger.json`**,
which carries the watermark, the units and sign convention, the run it was
measured on, the owner, the review-by date, and a superseded-by trail naming all
five figures and what killed each. `python scripts/gate2m.py <run>` re-measures
it. `docs/GAP-REGISTER.md` §F carries what is still wrong with the number.

What the campaign BUYS, which is the whole reason KCS exists and does not depend
on the value: the own-hull C_T/C_F ~ 9.8 is **our setup, not the hull**. The
same pipeline on a hull with published tank data reads far high, so the bias is
in the machinery. Before this run that was undecidable — a perfectly converged
own-hull GCI could not distinguish the two.

**The gate is RED and stays RED.** Recorded rather than softened (honesty rule 6).

## Open, measured, not yet closed (Gate 2M campaign)

| Item | Measurement | Consequence |
|---|---|---|
| ~~Prism-layer coverage ~50% is the ceiling~~ | **SUPERSEDED 2026-08-05.** Those coverages were measured on an anisotropic background and single-pass snappy. With a near-cubic background and layers added in their OWN pass after refinement, the KCS hull patch takes its full stack over all 22 881 faces. | The sweep was measuring the background aspect ratio, not the layer algorithm. Coverage still beats stack depth, so n=3 stays — but not for the reason the old row gave. |
| ~~72 skew faces are inherent to graded cells at the waterline~~ | **SUPERSEDED 2026-08-05.** Not inherent: the cause was a 38:1 background cell, and `hexRef8` refines ISOTROPICALLY, so refinement preserved the aspect ratio while shrinking the height. Removing the free-surface box never fixed it because the box was never the cause. | Deriving `dz` from `dx` (near-cubic background) plus z-only `refineMesh` after snapping took KCS from 72 988 zero-volume cells to 4 open cells / 5 wrongly-oriented faces / 77 skew. |
| ~~The near-wall envelope is narrow and y+ cannot be fixed inside it~~ | **SUPERSEDED 2026-08-05, same root cause.** "(2,3) clean, (3,4) fails, (4,5) fails worse" was the aspect-ratio signature, not a wall-model limit: snap displacement scales with the LONG edge, so moving a node millimetres moved it several cell HEIGHTS and folded the cell. `_HULL_REFINE` is (4, 5) now, and all three levels mesh clean. | The old row's conclusion — "fixing it needs something outside mesh parameters" — was right for the wrong reason. It needed a different mesh *construction*, not different mesh *parameters*. |
| Wetted-only (alpha-masked) y+ | implemented (`scripts/yplus_wetted.py`) | Read the MIN, never the patch average: the `hull` patch includes deck and topsides, which sit in air, and their y+ inverts to a first cell larger than the background cell. Dry faces dominate max and average. |
| **Unattended meshing (plan Phase 2 bar: >=95% of 200 hulls)** | **Gate 2U, RED — watermark in `data/gate-ledger.json`** (`scripts/mesh_robustness.py`) | BuildPlan Risk #1 called this "the largest unknown"; it is a number instead of a worry. Two caveats travel with it: N=8 is a small sample, and the "converges" half of the bar has never been measured at all. |
| **Pressure drag is 3-6x too high and grows with time** | OPEN, and it is the real blocker — see `docs/BUILD-PLAN.md` Part V.d R5.5, which lists five hypotheses tested and eliminated at real compute cost. Viscous drag is now correct (1.15-1.22x ITTC-57). | Nothing downstream is trustworthy until it closes. A GCI would converge onto a wrong number more precisely, and a DSYHS or Fridsma validation would be corrupted identically. |
| **Benchmark anchor set is wrong for the product line** | KCS is slender, displacement, Fn 0.26, no chines, no immersed transom, no spray. The SKUs (Solar Liveaboard, Dayboat) are chined semi-displacement craft with immersed transoms. | KCS calibrates the INSTRUMENT (free-surface capture, friction line, force integration, mesh convergence) and gives a bias floor — it does not validate small-craft physics. Per BuildPlan §1.3 (Islam & Guedes Soares 2019) V&V is case-specific. A second anchor sharing our dominant features is owed: DTMB 5415 (transom stern, already in the plan) or DSYHS / Series 62 for chined planing craft. Until then, Gate 2M's pass must NOT be read as small-craft validation. |

## Gap-closure stages

- **Stage B** (orig. P1): grammar AST/typologies · plywood bend-radius · 8-D pPCA latent + validity gate
- **Stage C** (orig. P2): async agent network (Orchestrator/Builder/Engineer/Validator) · engineer metrics (panels, interior volume, build hours) · STEP export attempt
- **Stage D** (orig. P3): JONSWAP + RAO response spectra · dynamics (inertia/mooring/lifting, MuJoCo cross-check) · CFD runner + forces/GCI post-processor
- **Stage E** (orig. P4): latent-space NSGA-II + latent-GP surrogate comparison
- **Stage F** (orig. P5): panel unrolling + DXF export · Pareto dashboard · handoff-latency profile
