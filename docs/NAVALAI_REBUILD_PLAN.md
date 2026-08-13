# NavalAI Rebuild Plan — dependency-ordered consolidation

Companion to `docs/NAVALAI_GEOMETRY_ARCHITECTURE_AUDIT.md` (2026-08-14,
base `70eb075`). Rules of engagement: incremental commits, tests after
every architectural change, consolidate-don't-duplicate, no cosmetic fixes,
no test edited merely to pass (pinned floats may move ONLY with a measured
justification in the same commit), **no OpenFOAM execution**.

Execution key: each item lists (defect → change → proof). Order is the
dependency graph from audit §20; do not reorder across rungs without
evidence that the dependency is false.

---

## R0 — Wiring truth (small diffs, unblocks honest measurement)

R0.1 **Thread the vessel through the ladder.** `evaluate.evaluate` and
`evaluate.sample_valid` pass `mission.vessel` to `grammar.check`; the
floated-state proportion re-check (`evaluate.py:720`) uses role bands; the
refusal message comes from `grammar._proportion_message` (kills the
hard-wired monohull literals at `evaluate.py:758`). Also
`pipeline.check_geometry`, `flywheel`, `generative`, `latent` call sites
gain the vessel argument where a mission is in scope; samplers without a
mission stay monohull (that IS the default contract).
Proof: the audit's executed trace inverts — 12×0.8×0.6 demihull under a
catamaran mission is judged by demihull bands (still refused on B/T 1.33 <
1.5, with the sourced-series message); `test_vessel_bands` Gate PV-B covers
the *production* entry point, not just `grammar.check` directly.

R0.2 **Optimizer honesty.** (a) admission consults `ev.ok`; (b) the three
excluded refusal classes (`early`, `multihull_stability_refusal`,
`manning_refusals`) become G-matrix rows (value = count>0), so NSGA-II can
see them; (c) `build_area` imports `energy.shell_area_m2` and multiplies by
`n_hulls`; (d) `gm_mid` uses the floated beam and a role-aware floor
(monohull floor only for monohulls; for multihulls, until R2.2 lands, the
GM objective is DROPPED to 2 objectives rather than steered by an
inapplicable rule — refusing is honest, steering wrong is not);
(e) de-duplicate the two `_evaluate` bodies into one shared function;
(f) `optimize` passes `provenance=` so searched designs are recorded;
(g) fix `ParetoResult.F` docstring.
Proof: a catamaran-mission NSGA-II run returns an empty-or-refused front
*explicitly* (not a fake front); monohull fronts unchanged within noise;
new tests assert an `ok=False` individual cannot dominate.

R0.3 **Ledger regression rule implemented.** `judge_red` compares a fresh
measurement (or the recorded `measured` field where re-measurement needs
hardware) against `watermark` using `better_is`; a RED gate lacking a
comparable watermark (string "NONE") is reported as
`UNCOMPARABLE — re-measure owed` instead of silently passing. Gate 2U row
re-based: keep the void 27.8% solve-rate as history, promote the
best *current-genome, shipped-config* figure with its N, and mark
metric="mesh-rate" so future comparisons are like-for-like.
Proof: unit tests around `judge_red` with better/worse/uncomparable
fixtures; ledger README claim now true.

R0.4 **Truth-record reconciliation (docs are code here).**
(a) `docs/GATE-6R-REVIEW.md` inline `**confirmed` markers removed/rewritten
to match `rules/review.py` (machine record wins; the doc states the
discrepancy history); (b) GAP-REGISTER rows A2 and G7 corrected;
(c) `BuildPlan2-FullVessel.md` restored into `docs/research/` from git
history (`git show 7ed06c4:BuildPlan2-FullVessel.md`) so seven citing files
point at something real; (d) delete `docs/SESSION-2026-08-13-HANDOFF.md`
per its own header; (e) untrack `.DS_Store`; (f) `formlib` stale
`_M_ROUND_BILGE`/`_M_SECTION`/`_M_SEPARATION` rows corrected to match the
shipped kernel, and a fence test greps registry claims against kernel
capability markers so they cannot drift silently again.

## R1 — Form follows function (mission → targets → geometry)

R1.1 **Design targets from the mission.** `MissionSpec` derives design Fn
from cruise speed + lwl hint; `evaluate.sample_valid` and `optimize` center
the Cp gene on `limits.prismatic_target(fn)` with `PRISMATIC_TOLERANCE` as
a *constraint row* (delivered-Cp vs target — the delivered check exists in
`form_coefficients`, currently unread); LCB band likewise becomes
mission-conditioned where the vision requires. Uniform sampling remains
available as an explicit exploration mode, not the silent default.
Proof: the four-mission form-follows-function test (audit §24 of the task):
solar-cat vs drone vs coastal monohull vs fishing drone produce measurably
different Cp/LCB/L-B distributions; test asserts distributional separation,
not exact values.

R1.2 **One length contract.** `mission.lwl_hint_m` bounds derive from
`grammar.PARAMS["LWL"]` (kill the (4,20) vs (2.5,24) drift); the ghost
symbol `SUPPORTED_HULL_COUNTS` comments corrected to name
`EVALUABLE_TOPOLOGIES`.

R1.3 **Typology consolidation.** `hull_ast` Typology layer retired from
the architecture: `agents.py` routes through `VesselConfig`+`HullRole`
instead; unfireable node rules deleted; `formlib.ast_typology` column
removed or re-pointed. (`hull_ast` file may remain as the AST bridge only
if `agents` still needs the vector<->tree round-trip; the *typology tables*
go.) One typology mechanism = `VesselConfig` (what vessel) +
`HullRole` (how a hull is judged).

R1.4 **Drone as a first-class mission.** `MissionSpec` gains
`payload: PayloadSpec` (mass, volume, power draw) and `endurance_h`;
UNCREWED routing unchanged; energy model consumes payload power.
No separate geometry engine (explicitly).

R1.5 **One reference genome.** Single canonical fixture module imported by
tests/arrangement/experiments; the two duplicates deleted; docstrings say
sixteen.

## R2 — Hydrostatic state (one floated truth)

R2.1 **Trim equilibrium.** Extend the float solve to (T, θ): iterate
ΣF_z=0 ∧ ΣM_y=0 (LCB↔LCG); report hydrostatics at the equilibrium
attitude; keep the 2° limit as a bar on the *solved* trim. Pinned-float
tests updated with measured justification (audit lists the ~30 pins).

R2.2 **Multihull stability criterion.** With vessel_terms' parallel-axis
I_T already correct, implement the demihull GM assessment against a
*sourced* multihull criterion; where no source exists, the refusal stays —
but R0.2 already made refusals visible, so the front is honest either way.
(The handoff names this "the largest single unlock": 6/40 feasibility was
a monohull floor mis-applied.)

R2.3 **Loading conditions.** `LoadingCondition` enumeration
(lightship/design/max) on `MissionSpec`; `evaluate` floats the governing
condition(s); asymmetric multihull loading representable in the mass model
reaches at least a documented refusal (not silence).

R2.4 **Mass-model unification.** `energy.weight_budget` collapses into
`weights.MassItem` emission (one representation); the provenance row
records the KG that actually produced GM; tier-E arrangement masses and
tier-F flotation items become admissible `MassItem` sources (wire
`arrangement.mass_items` behind a mission flag).

R2.5 **BEM at the floated waterline.** Production `heave_seakeeping` path
passes `ev.wl`; `panel_mesh` gets weld+closedness validation (or reuses
`closed_mesh` clipped at wl) so Capytaine's silent heal stops being the
only guard.

## R3 — Single-truth plumbing

R3.1 **Constants home.** `navalai/constants.py`: ρ_fresh/ρ_sea/ν/g with
sources; the 12 retyped `rho=1000.0` defaults import it; cfd/case keeps
9.81 ONLY via a documented alias that names the OpenFOAM `constant/g`
parity reason; grep-fence test (pattern already exists in
`test_limits_single_source`).

R3.2 **CFD manifest object.** Dataclass assembled from (kernel geometry,
floated state, similitude condition): domain, counts, layers, y+ target,
fluid props, motion/mass **from the L1 floated weight model** (closing the
disjoint-mass break; the 19% KCS KG error becomes a regression test),
free-surface receipts. `case.info` becomes a *rendering* of the manifest;
fidelity imports the same object (kills the third copy).

R3.3 **Receipts become gates.** cells-per-wavelength check moves from
unread receipt to generation-time bar (with an explicit override flag);
import winding: either `repair()` runs for imported STLs (recording
actual `applied`) or the receipt line is removed — no false receipts;
`run-case.sh` gains a solver timeout + verified kill (config via one
timing policy block; the 7200/3600/120/20 magic numbers documented or
measured).

R3.4 **De-transcription.** `admissibility.surface_grid` and
`blender/build_hull` consume exported kernel arrays (or a fence test
compares their output to `closed_mesh` per commit); section-area algebra
factored to one function used three places.

## R4 — Retirement (the repo gets smaller)

R4.1 Wire-or-delete, per module, with the decision recorded: `experiments`
(keep as measurement suite; its separation finding feeds R2.2 docs),
`estrin` (wire into rules/__init__ + evaluate for ES-TRIN missions — the
Danube SKU's only rule module), `waves.heave_response` (wire into
revalidate or delete), `dynamics` (delete or move to docs/research — dead
heuristics), `wet_deck_clearance_g` (wire once a clearance parameter
exists per R2.2, else mark unexpressible in formlib), `fairness` (add as
optimizer soft objective or reporting row — it was built for exactly
that), `pipeline`/`planner`/`agents` (either drive the spine from a script
entry point or fold their unique value into evaluate/gates and delete),
`policy/dna` (compile_policy already consumed via optimize? verify; else
retire), `stl_thirdparty_check` p_bow forensics (delete stale branch).

R4.2 Stale-prose sweep: unroll/hull_form_audit/mesh_repair docstrings
describing the deleted kernel; `crew (1,12)`; "fifteen numbers";
`_M_SEPARATION` rows (done in R0.4); seiche: `fidelity.admit` consumes
`tank_resonance`'s dispersion model or stops refusing on the refuted one;
`fidelity.density_for_wave_resolution` reads `background_counts`.

R4.3 Test-debt: Gate 2's `importorskip` becomes per-test skip + the gate
reports SKIPPED-IN-CI rather than GREEN (D15); `requirements.txt` pinned;
bare `==` float comparisons get tolerances.

## R5 — Validation matrix + final report

R5.1 `tests/test_vessel_matrix.py`: deterministic cases — small monohull
(5 m), large monohull (18 m), small catamaran (8 m), large catamaran
(15 m, the 12×0.8 demihull class), drone (4 m UNCREWED with payload) —
each asserting geometry/topology/watertightness/dimensions/volume/
delivered-Cp/LCB/wetted/draft/stability-inputs/bow-SAC-slope/STL/manifest.
Every cell PASS or EXPLICITLY UNSUPPORTED; no silent third state.

R5.2 Final report per task §34 with the five-case verdict, measured.

---

### Deliberately NOT changed
- The closed-form kernel (it is the asset; NURBS stays out per the
  measured 94.95 mm spline failure — revisit only with a fairing need the
  fairness functional cannot meet).
- Michell/interference formulation (verified in-file; only its *bar*
  statistics widen to population level).
- The refusal-over-clamp philosophy, refdata provenance discipline,
  mesh_repair's refusal to patch generated geometry, absolute objectives.
- Holtrop stays badge-only (envelope measured at 5% coverage — honest).
- No CFD runs; Gate 2M/2U re-measurement remains owed to the Mac node.
