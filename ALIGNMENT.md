# Alignment audit — original agentic-PLM plan vs. built system

First audited 2026-07-30 against the original "Autonomous Naval Architecture
Platform" plan. **Rows re-verdicted against the code 2026-08-11**; the body
also carries updates dated 2026-08-05, -06 and -07. The single "Audited
2026-07-30" line that used to stand here under-dated the file by a week and a
half, which is why the date now names the last time the VERDICTS were
re-derived rather than the first time they were written.

Verdicts: **ALIGNED** (built as envisioned) · **CLOSED** (was a gap; the file,
symbol, behaviour and gate that closed it are named in the row) ·
**DIVERGED** (built differently, deliberately, with research grounding) ·
**GAP** (missing; closed by the stage listed) · **BLOCKED** (needs
hardware/software this machine lacks).

**A row is CLOSED only where a gate holds it closed.** Every closure below
names its gate row in `navalai/gates.py` and the suite behind it, because
presence of a name is not evidence of behaviour (`docs/LESSONS.md` §8) and a
closure with no gate is a sentence, not a state.

## Original Phase 1 — Foundation & Grammar Compiler

| Plan item | Verdict | Evidence / fix |
|---|---|---|
| Hull grammar "type checker" (hierarchical AST, typologies) | **CLOSED (Stage B)** | `navalai/hull_ast.py` — `HullDesign` is a 5-node AST over the flat vector (`Principal`/`Planform`/`SectionLaw`/`Profile`/`Topside`), each node validating itself; `TYPOLOGY_RULES` dispatches per-typology bounds for **2** typologies (`SHARP_CHINE`, `PRAM`) and `type_check` appends the universal `grammar.check` floor, all before any geometry is constructed. Held by **Gate B** (`test_typology_rules_dispatch` — the same vector type-checks as sharp-chine and is REFUSED as a pram) and by **Gate C** `test_the_l0_type_check_can_actually_reject`, which exists because the check was INERT in the agent network: `rep.ok` implied `grammar.check(x).ok`, so the disjunction was identically the flat check and 27,440 of 48,243 in-box vectors (56.9%) that fail the sharp-chine rules were delivered anyway. The row's "Fix: `ast.py`" named a file that was never created; the module is `hull_ast.py`. |
| Parameter constraint solver (math boundaries) | **ALIGNED, with a corrected count** | closed-form checks, <0.05 ms, reasons reported (`grammar.check`). The "30+" this row used to claim was wrong and so was the plan's "49": the 2026-08-05 audit measured **9 live** constraints — 28 emitted, of which 15 are bound checks the optimiser cannot violate and 4 more are tautologies inside the declared bounds (0 hits in 400 000 in-bounds samples). Gap E4. |
| — incl. plywood bend limits | **CLOSED (Stage B)** | the real curvature check, not the twist proxy: `geometry.Hull.min_bend_radius()` takes the minimum 3-D radius over the keel and chine polylines (Frenet κ, stem tip masked out), and `evaluate()` compares it against `limits.min_bend_radius_m(t_ply)` = `BEND_RADIUS_RATIO` (80) × the sheet, publishing `r_req - r_min` as the `bend_radius` row of `CONSTRAINT_NAMES`/`Evaluation.g` — so NSGA-II is constrained by it. The sheet is the DERIVED one, so a boat that needs thicker ply also gets a larger required radius. Held by **Gate B** (`test_extreme_rocker_flags_bend_limit`), **Gate 1C** (the constraint vector is complete, ordered and finite) and **Gate L**, whose `test_limits_single_source.py` forbids the literal `80.0 * 0.015` that a second copy would reintroduce. |
| VAE → guaranteed-valid latent space | **DIVERGED + CLOSED (Stage B)** | research (kept): VAEs guarantee nothing, the hard filter is mandatory. Built: `navalai/latent.py::Genome` — probabilistic PCA (Tipping & Bishop 1999), the closed-form linear-Gaussian VAE, `LATENT_DIM = 8`, encoder = posterior mean, `sample()` draws the N(0,I) prior and `decode()` passes every draw through the L0 gate and `_project_to_feasible`, returning a `DecodeInfo` so a substituted design is a fact the caller can read rather than a silence. Held by **Gate B**: variance explained > 0.85, round-trip median rel err < 0.10, every gated sample passes `grammar.check`, and — the honesty arm — `raw_prior_feasibility` must be **< 1.0**, i.e. the UNPROJECTED prior is never assumed valid. The gate delivers validity; the model is not claimed to. What the raw prior actually measures is Gate 4F's business, and it is RED (see the scorecard roster). |

## Original Phase 2 — Agentic PLM Network

| Plan item | Verdict | Evidence / fix |
|---|---|---|
| Orchestrator agent (mission → constraints, delegates) | **CLOSED (Stage C)** | `navalai/agents.py::_orchestrate` — translates the mission text, fits the Builder's genome on-mission, creates the three worker tasks, feeds `q_build` on a deadline and stops every worker through the queue in a `finally`. `run_plm` is the synchronous entry. Held by **Gate C** `test_audit_trail_flows`, which asserts the recorded flow `builder→validator→candidate`, `validator→engineer→validated`, `engineer→orchestrator→engineered` — the delegation is read out of the audit trail, not out of the docstring. |
| Builder agent (mutates grammar only, never vertices) | **CLOSED (Stage C)** | `agents.py::_builder` emits `genome.sample(batch)` and nothing else. The invariant is asserted rather than argued: **Gate C** `test_builder_emits_parameters_never_vertices` walks every message whose sender is `builder` and requires `isinstance(payload, np.ndarray)` with `shape == (grammar.N_PARAMS,)` — a genome, structurally not a mesh. |
| Engineer agent (materials, weight, panel counts, interior volume, build hours) | **CLOSED (Stage C)** | `navalai/engineer.py::assess` returns `EngineerReport` with `panel_count` (derived from the chosen nesting layout, deck tiles counted rather than assumed), `interior_volume_m3` (trapezoidal integration of sheer half-breadth × depth above the load WL, × 0.85 fit-out), `build_hours` (`HOURS_PER_M2 × area × (1 + 0.015·panels)`), `ply_sheets` COUNTED off `unroll.nest` rather than a waste factor, and a line-item BOM. Held by **Gate C** (`test_engineer_metrics_sane`, and `test_the_delivered_bom_is_built_to_the_rule_derived_thickness` — the agent shipped a 15 mm cut list for a boat the same ladder run had sized at 21 mm) and by **Gate 6M** for the nesting/BOM/receipt half. `basis` declares "approx", the same posture as the rules tier. |
| Validator agent (topology+hydrostatics, Fitness=∞ fast reject) | **ALIGNED** | `evaluate.py` fails fast at L0 (~ms), `optimize.py` assigns 1e9 fitness; agent shell added in Stage C. `agents.py::_validator` logs `fitness: inf` with the violations and the STAGE that refused (`L0 type-check` / `L1 ladder`) — **Gate C** `test_gatekeeper_assigns_infinite_fitness` plus the three-arm `test_the_l0_type_check_can_actually_reject`. |
| Async CI/CD-style pipeline | **CLOSED (Stage C)** | two halves, both shipped. ASYNC: `agents.py::_orchestrate` runs `_builder`/`_validator`/`_engineer` as concurrent `asyncio` tasks over four `asyncio.Queue`s, with a deadline and a stop message; **Gate F** `test_agent_handoff_overhead_is_noise` measures the queue round-trip at <1% of one L1 evaluation. CI/CD-STYLE: `navalai/pipeline.py` is the staged lifecycle — an 11-stage forward-only `Stage` graph, seven typed `Terminal` states, `transition()` raising `IllegalTransition` on any edge the graph lacks (and refusing a failure with no reason), and an append-only JSONL archive that refuses a truncated or corrupt log. Held by **Gate S**, whose central invariant is that every genome ends in EXACTLY ONE terminal state — the object that can say "this genome went to MESHING and never came back", which nothing could before. |
| CadQuery/OpenCascade kernel | **CLOSED (Stage C/F)** | the divergence stands — the own analytic kernel in `geometry.py` remains the design-loop kernel because it is faster for this grammar — and the CadQuery arm is no longer conditional prose: `navalai/export.py::_station_wires` lofts through `hull.n_stations` station polylines, `export_step` / `export_iges` write via `cadquery` and `OCP.IGESControl`, and both emit an `export_receipt` recording exported vs validated station counts and the solid-vs-kernel volume error. MEASURED on this node: cadquery **2.8.0** installed, **Gate C** `test_step_export` / `test_iges_export` RUN (ISO-10303-21 header, >10 kB STEP, >50 kB IGES) — they are not skipping here. CAVEAT, stated because it is the honest shape of the closure: cadquery is in `requirements-optional.txt`, so on a machine without it those two tests `importorskip` and Gate C reports `GREEN (2 skipped)` rather than covering this row. |

## Original Phase 3 — Physics Validation Plane

| Plan item | Verdict | Evidence / fix |
|---|---|---|
| MuJoCo/MJX dynamics (inertia, mooring, lifting) | **DIVERGED + CLOSED (Stage D)** | the divergence stands (MuJoCo has no free surface, so hydro is Capytaine BEM, Hulme-anchored, GREEN). The valid MuJoCo scope is now built: `navalai/dynamics.py::inertia` lumps component inertias about the composite CG from the SAME positioned `energy.weight_items` the stability model uses — it used to inline a third placement table that had drifted 0.7 m on payload LCG — plus `mooring` (storm wind + current on the correctly single-sided projected area; the old factor 2 doubled line tension) and `lifting` (two-sling, angle from vertical, WLL at SF=4). The cross-check is real physics, not an import: `pendulum_period_mujoco` builds an MJCF body with the computed `iyy` and integrates it. Held by **Gate D** — gyradius bands, and the MuJoCo period within **2%** of `pendulum_period_analytic` (mujoco 3.11.0 present here, so the arm RAN) — and by **Gate 1** `test_phase1.py`, which asserts `dynamics.inertia` re-declares no placement fraction. CAVEAT: the module has no production call site; it is a gated reportable capability, not a stage of `evaluate()`'s ladder. |
| GraphCast wave/weather boundary conditions | **DIVERGED → Stage D** | research: design needs climatology, not forecasts. Fix: JONSWAP spectra (Black Sea fetch-limited + riverine wake) coupled to Capytaine RAOs → response spectra. |
| OpenFOAM snappyHexMesh + interFoam automation | **CLOSED (Stage D) — was BLOCKED, superseded 2026-08-06** | case generator, `run-case.sh`, forces post-processor and Roache GCI all built and tested. Execution is no longer metal-gated: OpenFOAM v2606 runs natively on the Mac node and KCS meshes and solves. What is open is a NUMBER, not a capability — **Gate 2M is RED BY RECORD** in `data/gate-ledger.json`, and its watermark is deliberately not a number: `"NONE — no reproducible measurement exists"`, `measured_on: "NOTHING. runs/kcs ... was DELETED"`. This row used to say the gate was "RED on a MEASURED number rather than blocked on hardware", which claims a measurement the ledger explicitly refuses to state — defect class 5 reproduced inside the document that records class 5. "Blocked", "measured and failing", and "no reproducible measurement exists" are three different claims and only the ledger gets to make this one. |
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
| Zig/C low-overhead runtimes for handoffs | **DIVERGED (measured, Stage F)** | research position: physics wall-time dominates, handoff overhead is noise. **The profile was taken, so the divergence is measured and not asserted**: **Gate F** `test_agent_handoff_overhead_is_noise` runs 200 `asyncio.Queue` round-trips and requires the per-handoff cost to be **<1%** of one L1 `evaluate()` call. The rewrite the original plan proposed would optimise noise. |
| Interactive dashboard w/ Pareto front | **CLOSED (Stage F)** | `ui/server.py::get_pareto` / `pareto_payload` run NSGA-II (`optimize.pareto_front`, pop 24 × 10 gens) and return points carrying `params` (15), `wh_per_nm`, `build_area_m2`, `gm_m`, behind a mission-keyed FIFO cache under a lock; `POST /pareto {mission}` is the wire, because `GET /pareto` takes no body and so the dashboard could only ever draw the DEFAULT mission's front. `ui/index.html` draws it on `<canvas id="pareto">` and clicking a point loads that design into the slider surface. Held by **Gate F**: `test_pareto_endpoint_serves_designs` (≥3 points, exact key set, `tier == "L1"`, second call <10 ms) and `test_dashboard_html_has_pareto_ui`. |
| STEP / IGES / DXF manufacturing export | **CLOSED (Stage C/F)** | all three exist and all three are gated. DXF: `unroll.develop` (isometric, edge lengths preserved) → `split_panel` → `nest` → `export_dxf`, which writes millimetres and DECLARES them (`$INSUNITS 4`) — it previously wrote metres with no header, so a shop importing the file cut a 10 mm part instead of a 10 m one — and the round-trip is asserted over the split, rotated, PLACED pieces, because the whole panels measure 10.05 × 1.62 m against a 1.22 × 2.44 m sheet and used to be drawn whole. STEP/IGES: `export.export_step` / `export_iges` (CadQuery row above). The export boundary now refuses: `export.refuse_unvalidated(ev, what)` raises unless the design passed the ladder — before it, a hull failing L0 exported an 8,487-byte DXF and a 174,406-byte STEP without a murmur, and honesty rule 2 had no implementation anywhere in the package. Held by **Gate F** (`test_dxf_roundtrip`) and **Gate 6M** (nesting, BOM reconciliation, export receipt, `test_export_refuses_a_design_that_failed_the_ladder`). **ONE SUB-CLAUSE IS STILL OPEN and is not softened here:** the panels are exportable but not yet refoldable to the hull — MEASURED max \|refold − hull\| 141.0 mm (bottom) and 225.7 mm (topside) against a 5 mm bar, and it does not refine away (143.8 / 206.1 mm at 161 stations). The aft half of the bottom panel refolds to 0.008 mm, so the error is the bow warp and the fix is slanted rulings (developable-surface FITTING), not a wider tolerance. `tests/test_manufacturing.py::test_gate6_refold_clause_is_red_on_the_hull` asserts the shortfall so it cannot be forgotten — but Gate 6M is GREEN and no ledger row owns the clause, which is Gate 4F's shape before it was split out (see `tests/test_red_by_record.py`). Register row G4. |

## Scorecard

**Counted off the rows above, 2026-08-11. Recount them if you doubt it — that
is the point of stating the arithmetic.**

- **Now (21 rows): ALIGNED 3 · CLOSED 14 · DIVERGED-with-receipts 6 ·
  GAP 0 · BLOCKED 0.** ALIGNED/CLOSED = **17**.
  Arithmetic: 17 + 6 = 23 verdict tokens over 21 rows, and 21 + 2 = 23 because
  exactly **two** rows carry two verdicts (`VAE → latent space` and
  `MuJoCo/MJX dynamics`, both `DIVERGED + CLOSED`). The counts reconcile; if a
  future edit makes them stop reconciling, that is the signal that a row moved
  and the scorecard did not.
- *Frozen historical snapshot, kept as recorded and NOT back-fitted:*
  "Before gap-closure: ALIGNED 4 · DIVERGED 6 · GAP 11 · BLOCKED 1."
  It does not reconcile — 4+6+11+1 = 22 tokens where 23 are needed — and it does
  not describe today's row set even in shape: rewinding the current 21 rows to
  their pre-closure verdicts gives ALIGNED 3 · DIVERGED 6 · GAP 13 · BLOCKED 1,
  because rows have been added, split and re-verdicted since it was written.
  Adjusting it to make the sum work would be inventing a verdict for a row set
  that no longer exists, so it stays as written, marked as history, in the past
  tense.

> **HOW THESE VERDICTS WERE REACHED (2026-08-11), and what was wrong before.**
> The scorecard used to claim 15 ALIGNED/CLOSED while the rows below it showed
> **7**, with **11 still carrying the literal string `GAP`** — two counts of one
> state, neither derived from the other or from the code. That is defect class 4
> (prose standing in for a verdict) in the file whose job is verdicts, and the
> "before" line did not reconcile either.
>
> The fix was NOT to edit the numbers. Each of the 11 `GAP` rows was re-verdicted
> against the tree, one at a time, and **all 11 closed** — but a name was never
> accepted as evidence (`docs/LESSONS.md` §8: gap B4 nearly closed on
> `has(energy.py, "crew")` where the word was in the comment ON the defect).
> Every row above names the file, the SYMBOL, the BEHAVIOUR, and the gate row in
> `navalai/gates.py` that holds it closed. MEASURED the same day:
> `python -m pytest tests/test_stageB.py tests/test_stageC.py
> tests/test_stageD.py tests/test_stageE.py tests/test_stageF.py -q` →
> **49 passed, 0 skipped** on this node (cadquery 2.8.0 and mujoco 3.11.0 both
> present, so the optional arms RAN), and `python -m navalai.gates` reports
> Gates B, C, D, E, F, L, S, 6M and 1C all GREEN.
>
> Two closures carry a stated caveat rather than a silence — the CadQuery arm
> `importorskip`s where cadquery is absent, and `dynamics.py` has no production
> call site — and one carries an OPEN sub-clause that is recorded, not softened:
> the refold deviation on the STEP/IGES/DXF row. A closure whose caveat is
> unwritten is the same defect as an unmeasured metric scored as a pass.
>
> Row-level verdicts here are still WEAKER than `scripts/reconcile_gaps.py`,
> which derives 122 register rows from the code by predicate and re-runs on
> demand; this table is re-derived by hand and therefore goes stale between
> audits. **For live status ask `python -m navalai.gates` and
> `python scripts/reconcile_gaps.py`, never this file.**
- **UPDATED 2026-08-06 — the BLOCKED row is retired.** It read "OpenFOAM
  execution — templates, runner and GCI post-processor all ready and tested on
  synthetic data", which stopped being true when the Mac simulation node came
  online: OpenFOAM v2606 runs natively, KCS meshes and solves, and Gate 2M is
  **RED BY RECORD** rather than blocked on hardware — with a watermark the
  ledger deliberately refuses to state as a number (corrected 2026-08-11; the
  sentence here used to say "RED on a MEASURED number", which is a claim
  `data/gate-ledger.json` does not make). PLM §3 step 7
  requires a superseded item to be removed with a note, never left ambiguous —
  this is that note. "Blocked", "measured and failing" and "no reproducible
  measurement exists" are three different claims, and leaving the first in place
  understated the state of the work.
  The clause "all gates green" is also removed: it was written before the red
  gates existed. There are **four**, not the three this line used to name:
  **2M, 2U, 6R and 4F** — Gate 4F (raw generative feasibility, watermark 79.33%
  against a ≥99% bar, measured 2026-08-07) was missing from this roster.
  `python -m navalai.gates` is the status, and `data/gate-ledger.json` is the
  only home of each watermark.
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
| ~~Pressure drag is 3-6x too high **and grows with time**~~ **still OPEN, but not that shape** | **SUPERSEDED 2026-08-07 by `runs/kcs_s1`; read `docs/BUILD-PLAN.md` Part IV.a.** At 3.40 flow-throughs drift collapsed to 0.31% and C_T flattened: pressure is **2.32×** expected with a **36%** batch error — broadband noise, not growth and not a mode. `scripts/tank_resonance.py` over 2041 samples finds the best single sinusoid explains **0.4%** of the detrended signal against a 50% bar: NO RESULT. The "grows with time" and the later "~5 s oscillation" were both periods invented by windows too short to contain them (1.33 flow-throughs, and a different mesh family). Viscous survives re-measurement at **1.161×** ITTC-57, batch error 1.7% — inside the form-factor band. | The discrepancy is real and still blocks the number, but **more wall-clock will not close it** and neither will an absorbing domain: that was the fix for a mechanism now measured not to exist. Next experiment is free sinkage and trim (`rigidBodyMotion`) — KCS Case 2.1 is towed FREE and we solve FIXED — which is code, not compute. A GCI built on the old reading would have converged precisely onto a phase of a period that was not there. |
| **Benchmark anchor set is wrong for the product line** | KCS is slender, displacement, Fn 0.26, no chines, no immersed transom, no spray. The SKUs (Solar Liveaboard, Dayboat) are chined semi-displacement craft with immersed transoms. | KCS calibrates the INSTRUMENT (free-surface capture, friction line, force integration, mesh convergence) and gives a bias floor — it does not validate small-craft physics. Per BuildPlan §1.3 (Islam & Guedes Soares 2019) V&V is case-specific. A second anchor sharing our dominant features is owed: DTMB 5415 (transom stern, already in the plan) or DSYHS / Series 62 for chined planing craft. Until then, Gate 2M's pass must NOT be read as small-craft validation. |

## Gap-closure stages

**This is the plan the closures were done TO, not a list of outstanding work.**
All five stages have landed and each has a gate row carrying it — Gates B, C, D,
E, F in `navalai/gates.py`, all GREEN as of 2026-08-11 (49 passed, 0 skipped
across the five suites on this node). Kept for the mapping from the original
plan's phases to the stages, which is the only thing here a reader still needs.

- **Stage B** (orig. P1): grammar AST/typologies · plywood bend-radius · 8-D pPCA latent + validity gate
- **Stage C** (orig. P2): async agent network (Orchestrator/Builder/Engineer/Validator) · engineer metrics (panels, interior volume, build hours) · STEP export attempt
- **Stage D** (orig. P3): JONSWAP + RAO response spectra · dynamics (inertia/mooring/lifting, MuJoCo cross-check) · CFD runner + forces/GCI post-processor
- **Stage E** (orig. P4): latent-space NSGA-II + latent-GP surrogate comparison
- **Stage F** (orig. P5): panel unrolling + DXF export · Pareto dashboard · handoff-latency profile
