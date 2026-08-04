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
| Parameter constraint solver (math boundaries) | **ALIGNED** | 30+ closed-form checks, <0.05 ms, reasons reported (`grammar.check`) |
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
| OpenFOAM snappyHexMesh + interFoam automation | **BLOCKED (partially GAP) → Stage D** | case generator built (deterministic, tested); `run-case.sh` referenced but MISSING; forces post-processor + GCI missing (both testable without OpenFOAM). Execution stays metal-gated. |
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
- **After gap-closure (stages B–F, all gates green): ALIGNED/CLOSED 15 ·
  DIVERGED-with-receipts 6 · BLOCKED 1** (OpenFOAM execution — templates,
  runner, and GCI post-processor all ready and tested on synthetic data).
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

## Open, measured, not yet closed (Gate 2M campaign)

| Item | Measurement | Consequence |
|---|---|---|
| Prism-layer coverage on the hull | ~50% (swept: n=3 50.3% · n=5 36.5% · n=8 26.2% · n=15 11.2%; nLayerIter/nRelaxedIter change nothing) | y+ controlled on layered faces only. Layer config is IDENTICAL across the triplet, so GCI still bounds outer-flow discretisation — but absolute C_t carries a bias that Gate 2M (KCS vs Tokyo-2015) must quantify, not the triplet. |
| 72 skew faces, max skewness 6.03 | isolated: removing the free-surface box does NOT fix it | inherent to ~20:1 graded cells where the hull pierces the waterline; v1 avoided it only by not resolving waves. Reported by run-case.sh rather than buried. |
| Wetted-only (alpha-masked) y+ | not implemented | the honest per-face wall-function check is still owed. |

## Gap-closure stages

- **Stage B** (orig. P1): grammar AST/typologies · plywood bend-radius · 8-D pPCA latent + validity gate
- **Stage C** (orig. P2): async agent network (Orchestrator/Builder/Engineer/Validator) · engineer metrics (panels, interior volume, build hours) · STEP export attempt
- **Stage D** (orig. P3): JONSWAP + RAO response spectra · dynamics (inertia/mooring/lifting, MuJoCo cross-check) · CFD runner + forces/GCI post-processor
- **Stage E** (orig. P4): latent-space NSGA-II + latent-GP surrogate comparison
- **Stage F** (orig. P5): panel unrolling + DXF export · Pareto dashboard · handoff-latency profile
