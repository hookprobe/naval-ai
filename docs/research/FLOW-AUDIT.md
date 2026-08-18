# FLOW-AUDIT — the end-to-end handoffs, measured

**Audited 2026-08-13 against commit `173cd00` (`git archive HEAD` into a scratch
tree outside the repository), because the working tree holds an uncommitted
16-parameter geometry rebuild.** Every number below was produced by running the
code, not by reading it. Where a figure comes from the WORKING tree instead of
from HEAD it says so in the sentence that carries it.

The chain audited is the one the README claims:

    mission -> genome -> hull -> hydrostatics -> resistance -> energy
            -> rules -> arrangement -> export

Nobody had ever asserted it end to end. `tests/test_end_to_end_flow.py` now
does; this file is what the audit found while writing it.

**Population, stated once.** Unless a row says otherwise, "measured over N ok
designs" means: `grammar.sample(600, default_rng(seed))`, each evaluated by
`evaluate(x, MissionSpec())` — the default 6 t solar-electric liveaboard, 5 kn,
category C — and kept only when `ev.ok` is True. That is the population the
export boundary would accept, and it is the only one an end-to-end claim may be
made on. `Hull.n_stations = 41` throughout.

---

## 1. Is there ONE authoritative geometry?

**Yes for the LAW, no for the DISCRETISATION.** There is exactly one closed form
for the moulded surface — `geometry.station_geometry` (`navalai/geometry.py:22`)
— and a search of `navalai/`, `scripts/`, `benchmarks/` and `ui/` finds no
second copy of the plan-form, deadrise or sheer formulae. `Hull.chine_row` is
correctly shared between `closed_mesh` and `admissibility.surface_grid`, and
that copy is test-fenced.

What is not single-source is the GRID each stage samples that law on. Five
stages build a surface, and in four of them the resolution is a **local literal
in the function signature**, not a shared constant:

| stage | symbol | resolution | where the number lives |
|---|---|---|---|
| L1 hydrostatics | `Hull.hydro_arrays` | `n_stations = 41` | dataclass field default, `geometry.py:77` |
| L1 resistance | `Hull.offsets_grid` | 161 x 28 | **shared** — `resistance.PRODUCTION_GRID`, `resistance.py:114` |
| L2 BEM | `Hull.panel_mesh` | `nx=30, nz=8` default; ships (20,5)/(28,7) | local default `geometry.py:254` + `seakeeping.L2_MESHES` |
| L3 CFD | `Hull.closed_mesh` | `nx=80, nz=16` default; ships up to 600x120 | local default `geometry.py:280` + `cfd/case.stl_resolution` |
| export | `export._station_wires` | `hull.n_stations` | inherited (was a hard-coded **12**) |
| arrangement | `Envelope.from_hull` | `n_z = 41` | local kwarg default, `arrangement.py:310` |

### MEASURED: submerged volume at the FLOATED waterline, against the ladder

Worst |difference| from `ev.hydro.volume` over ok designs:

| geometry source | grid | worst diff | n designs |
|---|---|---|---|
| cadquery ruled loft (`export_step`) | `n_stations` = 41 | **0.2064%** | 30, seeds 0/3/11 |
| cadquery ruled loft | **12** (the historical default) | **2.72%** | 30, seeds 0/3/11 |
| CFD STL (`hull_to_stl` -> `post.stl_submerged_properties`) | 80 x 16 | **0.1834%** | 8, seed 0 |
| CFD STL | 600 x 120 (`stl_resolution`) | **0.1455%** | 8, seed 0 |
| **L2 BEM panel mesh** | **(20, 5) — shipped coarse** | **1.9795%** | 10, seed 0 |
| L2 BEM panel mesh | (28, 7) — shipped fine | 1.1092% | 10, seed 0 |

**Verdict: they agree, and the agreement is now asserted.** Three of the four
sit inside 0.21%; the residual is systematically NEGATIVE (the ruled and
triangulated surfaces chord between stations while `hydro_arrays` integrates the
exact section polygon), so it is a discretisation bias and not scatter.

### FINDING 1.1 — the L2 BEM mesh is the odd one out, by an order of magnitude

`revalidate(..., "L2")` hands `seakeeping.heave_seakeeping` the LADDER's
`disp_kg` and `awp` as the mass and waterplane, while Capytaine solves the
radiation problem on a `panel_mesh` that displaces **up to 1.98% less**. The
heave RAO is therefore the resonance of a body whose hydrodynamics and whose
mass are 2% apart. This is on the ladder's own escalation path and is the
loosest geometry in the package.

`tests/test_end_to_end_flow.py::test_one_geometry_the_l2_panel_mesh_displaces_what_the_ladder_validated`
holds it at 3.0% so it cannot grow. That is a fence, not a blessing.

### FINDING 1.2 — a stale receipt is sizing a live tolerance

`navalai/evaluate.py:780-782` states *"`hull_to_stl` at nx=80 lands within 0.91%
of the analytic displacement and at nx=400 within 0.07%"*, and that comment is
what sizes `_L3_VOLUME_TOL = 0.03` — the bar that decides whether a recorded
RANS campaign is about this hull. Re-measured on the reference hull at HEAD:
**0.052% at nx=80**, 17x better. Re-implementing the PRE-2026-08-12 uniform-in-z
`closed_mesh` (before `chine_row` put the knuckle on a grid row) reproduces
`-0.9075%` at 80x16 and `-0.0679%` at 400x80 — so the comment is an accurate
description of a surface that no longer exists. The tolerance errs loose, so
nothing is currently wrong; the receipt is.

### FINDING 1.3 — `wetted_surface` is a PROJECTED area, and it feeds friction

`Hull.wetted_surface` (`geometry.py:175`) integrates immersed girth x dx, which
drops the surface's longitudinal slope. Against a true 3-D triangulation at
600x120 on an n=2561 hull, converged in both axes: **30.5795 m^2 vs 30.7965
m^2 — 0.688% low**, on the reference hull at z = 0. It is not discretisation;
refining either axis does not move it. That number is `HydroState.wetted`, it
multiplies straight into `Rf = (1+k) Cf q`, and it is also the base of
`energy.shell_area_m2`, which understates the true shell to the sheer by
**2.50%** (51.616 vs 52.941 m^2) and sets structure mass.

For scale on the same hull, `holtrop.wetted_surface` (an empirical regression,
not a discretisation) reads **-5.75%**.

### FINDING 1.4 — `unroll.hull_panels(rulings="strakes")` does not conserve area

Per side, against an analytic 4001-station ruled-strip reference:

| ruling family | bottom-stbd m^2 | topside-stbd m^2 |
|---|---|---|
| true 3-D | 12.3234 | 14.1768 |
| `constant-x` | 12.3198 (-0.03%) | 14.1566 (-0.14%) |
| `developable` (SHIPPED default) | 12.2818 (-0.34%) | 14.1454 (-0.22%) |
| `strakes` | **11.4320 (-7.24%)** | 14.2864 (+0.77%) |

Not on the BOM path (`engineer._shell_parts` takes the default), but it is a
selectable, executable family whose developed area loses 7.24% of the bottom
panel — 0.18 m^2 of plywood on a 10 m boat.

### FINDING 1.5 — the reference genome is declared FOUR times

`tests/test_phase0.py:14`, `navalai/arrangement.py:1213` (whose own docstring
admits it: *"a duplication this module would rather not have"*),
`ui/index.html:106`, `scripts/make_case.py:24`. The first two were verified
byte-identical at HEAD; nothing enforces any of it. **All four hard-code fifteen
named parameters and all four break on the in-flight 16-parameter rebuild.**

---

## 2. Does every quantity keep its `{value, tier, sigma}`?

**No. Four quantities out of roughly forty carry a badge; the rest cross every
handoff as bare numbers.**

    dataclass            numeric fields   carries a sigma
    Evaluation.badges          4          yes (tier, sigma, basis)
    HydroState                16          NONE
    ResistanceResult          12          1 (`uncertainty`, on `total` only)
    EnergyReport               9          1 (`sigma_wh_per_nm` + `sigma_basis`)
    EngineerReport            13          NONE  (`basis` string only)
    ArrangementReport          2          NONE
    RuleFinding             measured/required   NONE (`basis` string only)

The badged four are `displacement`, `GM`, `resistance` and `wh_per_nm`. What
that leaves unbadged, on the path:

- **`freeboard_min`** — it is the quantity behind the `freeboard` constraint row,
  and it has no sigma, while `GM` (behind the `gm` row) has one. Two rows of one
  vector, one with an uncertainty and one without.
- every other `HydroState` field: `lcb`, `kb`, `bm`, `bm_l`, `awp`, `lcf`,
  `b_wl_max`, `lwl_eff`, `cb`, `cp`, `wetted`, `volume`, `draft`. `lcb` feeds the
  `lcb` row; `lwl_eff` and `cb` feed resistance; `awp` feeds L2.
- `rw`, `rf`, `cw`, `cf`, `fn` on `ResistanceResult` — the sigma is on the total
  only, so the split between wave and friction carries none.
- `prop_power_w`, `solar_kwh_day`, `net_kwh_day`, `range_solar_nm_day`,
  `range_battery_nm` — the whole range/endurance story a buyer reads.
- every field of `EngineerReport`: sheet count, epoxy mass, interior volume,
  build hours, and every `BomLine.area_m2`.
- every `RuleFinding.measured` — the ISO tier reports a measured value against a
  required one with no band on either, and a margin of 1% and a margin of 100%
  are reported identically.

### What IS clean, and was verified

- **Gap H1 is closed and stays closed.** `evaluate.py:550` passes
  `resistance_sigma_n=res.uncertainty`, the report's basis reads
  `propagated-lower-bound` on every ok design, and the badge carries the
  report's own sigma rather than a second copy. Re-propagating
  `wh_per_nm_sigma(en.wh_per_nm, res.total, res.uncertainty)` reproduces the
  shipped sigma to 1e-12. Asserted.
- No badge on an ok design carries a non-finite or negative sigma, and every
  basis string is non-empty. Asserted.

---

## 3. Which computed capabilities have no production caller?

"Production" means reachable from `navalai/` itself. A function only a test or a
demo reaches is a mechanism nothing on the product path uses.

### 3.1 The whole tail of the advertised chain is test-only

**`arrangement` -> `export` is not connected to anything.**

- `navalai/arrangement.py` — 1484 lines, Gate V2.1 — is imported by **nothing**
  in `navalai/`, **nothing** in `scripts/`, and nothing in `ui/`. Only
  `tests/test_arrangement.py`. `check_l0a`, `reference_layout`, `min_dims_m`,
  `supersede_outfit`, `Envelope.deck_area_m2`,
  `Arrangement.interior_volume_used_m3` all follow it.
- `export_step` / `export_iges` (`navalai/export.py:121,139`) and `export_dxf`
  (`navalai/unroll.py:1453`): **nothing in `navalai/`, `scripts/` or `ui/` ever
  emits a manufacturing file.** `navalai/export.py`'s only importer inside the
  package is `unroll.py:1473`, and it imports `refuse_unvalidated` alone.
  `scripts/demo_mission.py` — the script whose docstring is "one mission
  sentence -> a validated hull" — stops at the BOM and writes nothing.
- `engineer.assess` (the BOM) is reachable only from `scripts/demo_mission.py`
  and from `agents.run_plm`, which is itself test-only.

So of the nine stages in the headline chain, **arrangement and export have no
production caller at all**, and manufacturing has one only inside a demo script.

### 3.2 `revalidate` — honesty rule 2, called by nothing but tests

`navalai/evaluate.py:975` is the escalation verb that makes "any kept design
re-validates up the ladder" a mechanism instead of a sentence, and it has no
caller outside `tests/`. It is also the only production route to
`seakeeping.heave_seakeeping`, so **the entire L2 BEM tier hangs off a test-only
entry point**.

### 3.3 The governance kernel is never CONSTRUCTED

`compile_policy` / `reference_policy` / `KIT_LINE_V3_CONSTITUTION` appear outside
`tests/` only inside `navalai/policy/` itself. Neither
`scripts/demo_mission.py:36` nor `ui/server.py:135` passes `policy=` to
`pareto_front`, so **every `if policy is not None` branch in `optimize.py` and
`evaluate.py` is dead in production**, and `CompiledPolicy.check_selection` and
`ParameterBox.contains` have no caller. The ladder's NON-import of
`navalai.policy` is correct and deliberate (CLAUDE.md's structural clause); the
non-construction is a different thing and is not.

### 3.4 Confirmed instances from the brief, re-verified

- `resistance.py:735` — `rw = michell_rw(xs, zs - wl, Y, speed, rho)`. **No
  `separation`.** Confirmed at HEAD. With it, `michell_rw_separation_sweep`,
  `free_wave_spectrum`, `wet_deck_clearance_g`, `bow_wave_rise`,
  `catamaran_interference` and the four measured CATAMARAN_* constants are all
  test-only. The multi-hull capability is complete, measured, documented — and
  unreachable.
- `hull_ast.Typology` / `TYPOLOGY_RULES` — reachable only through
  `navalai/agents.py`, which nothing imports. Two hops dead.
- `stl_watertight_report` — **now wired**, at `cfd/case.py:1853` and
  `pipeline.py:615`. Closed.

### 3.5 The rest, by category

**No caller anywhere (A):** `cfd/post.weld_vertices:595` and
`cfd/post.mirror_half_hull:634` — prescribed as the benchmark-geometry recipe in
`benchmarks/kcs.py:32,39` **inside a comment**, so the recipe exists as prose and
no code path runs it; `extrapolate.ittc78_from_model:304` and its sole callee
`similitude.PhysicalModel.to_ship` — the model<->ship scaling leg is dead in both
directions; `stl_forensics.render_facets:718`; `blender/spec.grid_from_spec:112`;
`fidelity.FidelitySpec.finer:230`; `mesh_repair.RepairReport.summary:115`;
`gaps.GapQueue.by_state:248`; `fidelity.STATED_FINE:154`;
`waves.BLACK_SEA_INSHORE:32` / `CALM_RIVER:34`. Plus 26 `refdata` constants
reachable only via a `vars(module)` introspection that only tests call.

**Called only by tests (B), on or beside the path:**

- **`navalai/rules/estrin.py` — a whole compliance module, 349 lines, no
  importer.** `in_scope` (Directive 2016/1629 Art. 2(1)), `required_freeboard_mm`
  (ES-TRIN 4.02), `assess`. `evaluate.py:52-54` wires ISO 12215 and ISO 12217;
  ES-TRIN is wired to nothing.
- **`navalai/pipeline.py` — 777 lines.** Imported by `gaps.py:36` for `JsonlLog`
  ALONE. `Pipeline`, `apply_check`, `abandoned`, `cycle_complete` and all five
  stage gates (`check_geometry`, `check_stl`, `check_hydrostatics`, `check_mesh`,
  `check_cfd`) are test-only. The object built so that "no genome is walked into
  a stage and left there" is checkable is not on the path any genome takes.
- **`navalai/dynamics.py` — whole module.** `inertia`, `mooring`, `lifting`, the
  MuJoCo-vs-analytic pendulum cross-check.
- **`navalai/waves.py` — whole module.** `heave_response`, `jonswap`,
  `encounter_omega`.
- `seakeeping.convergence_sweep:208`, `hemisphere_added_mass_lowfreq:272`, and
  the entire slamming instrument (`slam_pressure_band:453`, `slam_pressure:417`,
  `wagner_impact_cp:357`).
- `optimize.pareto_front_latent:223` and `LatentHullProblem` — the latent-space
  search never reaches the optimizer in production.
- The conditional/latent half of the generator interface: `sample_conditioned`,
  `to_latent`, `from_latent`, `raw_feasibility` on all three classes.
  `ui/server.py:172` calls `make_generator` and then only `.sample()`.
- `surrogate.CoKriging:395` — the whole multi-fidelity co-kriging surrogate;
  production uses `GP` (`flywheel.py:42`). With it `batch_infill`, `calibration`,
  `coverage_curve`.
- `mesh_repair.repair:231` — `cfd/case.py:1790` names it in an ERROR-MESSAGE
  STRING and tells the operator to run it by hand.
- `unroll.rulings_that_cross:1002`, `extrapolate.calibrate_form_factor:238`
  (Prohaska), `rules/review.is_complete:188`, `db.Provenance.get_params:117`,
  `evidence.EvidenceGraph.save:457`.

**Reachable only from a demo (C):** the entire APSE cluster —
`evidence.EvidenceGraph:289`, `planner.plan_for:358`,
`fidelity.cheapest_admissible:451`, `extrapolate.residuary_check:262` — has
`scripts/demo_apse.py` as its sole non-test consumer.

### 3.6 `pipeline.Stage` has eleven states and five checks

`Stage` enumerates NEW, GENERATING, VALIDATING, HYDROSTATICS, MESHING, CFD,
SEA_STATE, ERGONOMICS, MANUFACTURING, SCORING, ARCHIVED. There are
`check_geometry`, `check_stl`, `check_hydrostatics`, `check_mesh` and
`check_cfd`. **SEA_STATE, ERGONOMICS, MANUFACTURING and SCORING have no
`StageCheck` at all**, so a genome can be advanced into four of the eleven
stages with no physics verdict that could fail it — and `advance()` is the only
gate, which checks graph adjacency and nothing else.

---

## 4. Where does a downstream stage re-derive an upstream input?

### FINDING 4.1 — resistance re-derives the LENGTH, and it is gap E7's residue

`evaluate.py:506` calls

    total_resistance(hull, u, hs.wetted, hs.cb, rho, wl,
                     beam_wl=hs.b_wl_max, draft=hs.draft)

— four quantities handed over from the floated `HydroState`, exactly as gap E7
required. But `resistance.py:736` then does

    lwl = float(hull.x[-1])

which is the **DESIGN** waterline length, and `hs.lwl_eff` — the length the hull
actually floats at — is sitting in the same object as the four arguments above.
That length sets the Froude number, the Reynolds number for ITTC-57, and the L/B
that Watanabe's form factor carries as `(L/B)^-2`.

MEASURED over 12 ok designs, seed 0:

    hull   LWL_design   lwl_eff    dL       dRf      dRt     k_design  k_floated
      2      15.075     13.568   -10.00%  +5.17%   +2.57%    0.0605     0.0969
      4      16.691     15.021   -10.00%  +3.93%   +2.56%    0.0003     0.0227
      8      14.880     12.648   -15.00%  +8.55%   +1.89%    0.0658     0.1276
      9      16.448     15.214    -7.50%  +3.34%   +2.24%    0.0331     0.0547

Worst over the twelve: **-15.00% on length, +8.55% on the friction term, +2.575%
on total resistance**, and the form factor moves by a factor of **76** on hull 4.
Five of the twelve are unaffected (their floated length equals the design one);
the error is one-directional on the rest — `lwl_eff <= LWL` always, because the
rocker lifts the transom clear — so it never averages out.

Wh/NM is linear in `total`, so this is a systematic bias on the optimiser's
first objective.

**FIXED 2026-08-19 (C-08).** `total_resistance` gained `lwl_eff=` beside
`beam_wl`/`draft` (same E7 contract: None = design-length fallback for a
caller holding only a hull); `evaluate()` and `certify()` pass
`hs.lwl_eff`; the Michell term is untouched (it consumes the frame-shifted
offsets grid, not the scalar). The predicted move was real but small on
the CURRENT population: MEASURED at the fix over the seed-0 ok-population,
dRt median +0.000% (most hulls now float at full length — the trim
equilibrium and the kernel rebuild shrank the rocker-lift), worst +1.279%.
`test_the_floated_state_reaches_the_resistance_model` now asserts the
length parity in its loop, per its own docstring's instruction.

### FINDING 4.2 — the beam for the ISO 12217 offset-load test is re-derived per call site

Three expressions, three call sites, one rule:

| caller | expression | reference hull |
|---|---|---|
| `evaluate.py:567` | `2.0 * hull.y_chine.max()` | 5.2326 m |
| `scripts/demo_mission.py:63` | `p["BWL"]` (the grammar parameter) | 5.2665 m |
| `optimize.py:115` | `2.0 * hull.y_chine.max()` (a third copy of the same text) | 5.2326 m |

`iso12217.assess` uses it as `b = OFFSET_FRACTION * beam_m` — the crew's offset
lever. The two DIFFERENT values disagree by up to **0.65%** over 12 ok designs at
seed 0, so the ladder and the demo assess the same hull under the same clause
with different levers. (For reference, the floated `hs.b_wl_max` is a further
0.13%-107% away, but it is arguably not the right beam for this rule; the defect
is that no call site names WHICH beam it means.)

### FINDING 4.3 — the ply thickness, twice derived, currently agreeing by luck

`evaluate.py:416` derives `t_ply = select_stock_thickness_m(
mission.displacement_target_kg)` and validates the boat on it: structure mass,
`bend_radius` constraint, ISO 12215-5 finding. `engineer.assess` derives its own
from `mldc_kg`, and `Envelope.from_hull` defaults to `limits.PLY_THICKNESS_M`.

MEASURED: `select_stock_thickness_m` steps at **1000 -> 18 mm, 5500 -> 21 mm,
19750 -> 25 mm**, and at HEAD `target = max(agg.total_kg, mission_target)` keeps
the floated displacement at or above the mission target, so the two derivations
land on the same 21.0 mm sheet across all ten designs sampled. The disagreement
is **latent, one-directional and firable above 19750 kg** — nothing in the code
prevents it.

**Two routes are live right now, though:**

1. `engineer.assess(hull)` with no `mldc_kg` returns the **nominal 15 mm** while
   the ladder validated **21 mm** — a 40% thin bottom panel, from a default
   argument, on the same boat the rules tier passed. It announces itself in the
   BOM note (`"nominal stock sheet (no mLDC given — NOT rule-derived)"`), which
   is the correct behaviour, and `scripts/demo_mission.py` wires it properly.
   Nothing enforces that any other caller will.
2. `Envelope.from_hull` defaults to the same nominal 15 mm, so the DEFAULT
   arrangement envelope is **0.39%-0.61% more generous** than the derived panel
   allows (measured over 6 ok designs, seed 0). It accepts the thickness as an
   argument; the value is one keyword away and no production caller exists to
   pass it.

This is the "15 mm ply that failed its own scantling rule" incident's exact
shape, one stage further downstream.

### FINDING 4.4 — the optimiser's build-area objective is a second copy of `shell_area_m2`

`optimize.py:109`:

    build_area = hull.wetted_surface(float(hull.z_sheer.max())) + hull.deck_area()

`energy.shell_area_m2` is `float(hull.wetted_surface(float(hull.z_sheer.max())))`
— the identical expression, inlined rather than imported. MEASURED: they agree
to **exactly 0.0** on four ok designs, because they are the same text. That is
not reassurance, it is the definition of the defect: gap C9 measured a second
shell-area expression wrong by up to 76%, and there is a second expression here
again, free to drift the moment `shell_area_m2` gains a transom or a deduction.

Asserted at machine precision (not at a tolerance, which would license drift) in
`test_the_hull_the_rules_tier_assessed_is_the_hull_the_optimiser_scored`.

### FINDING 4.5 — the exporter's receipt compares against the wrong quantity

`export.export_receipt` compares the solid to `moulded_volume_m3` — the volume
to the SHEER. That catches a coarse loft, but the ladder applied every one of its
gates to the DISPLACEMENT at the floated waterline, and no artefact anywhere
compares the exported solid against it. The smoke test now does; the receipt
still does not, and the receipt is what ships with the file.

---

## 5. What the smoke test asserts, and the MEASURED tolerances

`tests/test_end_to_end_flow.py`, 14 tests, **~13 s**, all green on `173cd00`.

| bar | value | worst measured | what it refuses |
|---|---|---|---|
| `STEP_VOLUME_TOL_PCT` | **0.40%** | 0.2064% (30 designs, seeds 0/3/11) | the 12-station loft, which reads **2.72%** on the same designs |
| `STL_VOLUME_TOL_PCT` | **0.35%** | 0.1834% at 80x16, 0.1455% at 600x120 (8 designs, seed 0) | a CFD surface drifting from the validated hull; cf. `_L3_VOLUME_TOL` at 3%, 16x looser |
| `PANEL_MESH_VOLUME_TOL_PCT` | **3.0%** | 1.9795% at (20,5), 1.1092% at (28,7) (10 designs, seed 0) | growth of finding 1.1; it is a fence, not a blessing |
| resistance -> energy round trip | **1e-12** relative | **2.2e-16** (one ulp, 10 designs) | a second resistance reaching the energy model |
| Wh/NM sigma vs re-propagation | **1e-12** relative | exact | gap H1 reopening in either half |
| optimiser G vs ladder `g` | **1e-12** | exact | gap E16 — a shifted constraint column under `python -O` |
| build-area objective | **1e-12** | **0.0** | gap C9's second expression drifting |
| ply thickness | **0.05 mm** | 0.0 | a BOM cut from a sheet the ladder did not validate |
| arrangement inset | **>= t_ply** | exactly 21.0 mm on 6 of 8; 21.8 / 23.7 mm on the two negative-flare hulls | rooms planned through the planking |

### Every guard was MADE TO FIRE (docs/LESSONS.md defect class 3)

Each was re-run against the verbatim historical defect, monkeypatched in:

| defect injected | caught by | first line of the failure |
|---|---|---|
| `_station_wires` lofting 12 stations | STEP volume | *"the exported solid displaces 5.940527 m^3 and the ladder validated 6.001738 m^3 ... 1.019% apart"* |
| `energy_report` called with no `resistance_sigma_n` (the pre-H1 call) | Wh/NM sigma | *"Wh/NM sigma basis is 'placeholder': the energy model was given no input sigma"* |
| `np.roll(G, 1, axis=1)` on the optimiser's constraint matrix | optimiser/ladder | *"the optimiser was shown -0.01 in column 0 ('freeboard') and the ladder computed -0.854"* |
| `engineer.assess` forced to `mldc_kg=None` | ply thickness | *"the BOM cuts a 15.0 mm bottom and the ladder validated 21.0 mm"* |
| `HydroState.awp` set to NaN (a field no constraint reads) | finite-numbers | *"HydroState.awp = nan on a design the ladder passed"* |

The last one is the interesting case: injecting the NaN into `freeboard_min`
instead makes `_validated` fail with "the ladder produced 0 fully-valid
designs", because `evaluate`'s own gap-E10 guard already refuses it. The test
was re-run against `awp` — a field NO constraint reads — to prove the new guard
fires on its own and is not shadowed by an existing one.

### What is deliberately NOT asserted

- **The floated LENGTH reaching the resistance model** (finding 4.1). It is a
  defect, not a tolerance, and pinning the present disagreement as a watermark
  would legitimise it. When it is fixed, `lwl_eff` joins the loop in
  `test_the_floated_state_reaches_the_resistance_model`.
- **The 15-vs-16 parameter genome.** No test in this file names `N_PARAMS`,
  builds a named parameter dict, or pins a vector. Designs come from
  `grammar.sample`, which reads `LOW`/`HIGH`/`N_PARAMS` at call time. Verified:
  the file runs unchanged against both the 15-parameter HEAD and the
  16-parameter working tree.

### The gate row this suite needs

`navalai/gates.py` is another agent's file. The row to add, in the house style
and placed after `Gate 1C` (it belongs to the same "the ladder cannot be talked
into agreeing with itself" family):

```python
    # Split out for the reason Gate 1H and Gate 1C were: the ladder should show
    # WHICH clause is covered by what. Every other gate tests a STAGE; this one
    # tests the HANDOFFS between them, which is where every confirmed defect of
    # 2026-08-12/13 lived — a michell_rw with no separation, an energy_report
    # with no input sigma, a 12-station loft against 41 validated ones, a
    # watertight report nothing called. MEASURED 2026-08-13: five geometry
    # sources agree on the validated displacement to 0.21% (the L2 BEM mesh to
    # 1.98%), and every one of the suite's guards was fired against the
    # verbatim historical defect. See docs/research/FLOW-AUDIT.md section 5.
    Gate("Gate 1E", "the stages agree with each other: one geometry, one "
         "resistance, one ply, tier+sigma across every handoff",
         "tests/test_end_to_end_flow.py"),
```

---

## 6. What could NOT be verified, and why

**The working tree holds an uncommitted 16-parameter geometry rebuild that
another agent is greening.** The audit above is against `173cd00`. Running the
same suite against the working tree gives **11 passed, 3 failed**, and all three
failures are the rebuild, not the suite. They are reported here because they are
exactly what an end-to-end smoke test exists to surface, and because the agent
holding those files should see them:

### CRITICAL — the manufacturing export path was not carried across the rebuild

In the working tree `Hull.section(i)` returns a **257-point** polyline (the new
`roundness` parameter produces a rounded section) where at HEAD it returned the
**3-point** keel -> chine -> sheer polyline. Two consumers read `pts[0]`,
`pts[1]` and `pts[2]` positionally and still "work":

- `export._station_wires` (`navalai/export.py:25-36`)
- `export.moulded_volume_m3` (`navalai/export.py:79-83`)

The first three points of a 257-point section are ~11 mm apart at the keel, so
both now describe a sliver. MEASURED on the working tree, three ok designs:

    hull  ladder m^3   STEP solid m^3      error     CFD STL m^3     error
      0     5.995409       0.001506      -99.975%      5.978597      -0.280%
      1     5.994181       0.000935      -99.984%      5.931344      -1.048%
      2     5.996411       0.000150      -99.997%      5.844108      -2.540%

`export.moulded_volume_m3` returns the same ~0.001 m^3, so **the receipt agrees
with the sliver** and would report `volume_error_pct` near zero. The export
raises nothing, warns nothing, and writes a STEP file. This is the 12-station
defect again, four orders of magnitude larger, and this time the receipt built to
catch it is broken by the same change.

`unroll.hull_panels` shares the assumption: `engineer.assess` now dies with
`ValueError: no feasible nesting layout for this hull`, which is at least loud.

### The CFD STL is also drifting

`closed_mesh` still runs, but its volume error against the ladder grows to
**-2.54%** on the third design, past the 0.35% bar measured at HEAD. Whether
that is the rounded section being chorded or something else was NOT diagnosed —
it is the rebuilding agent's file and diagnosing it would mean guessing at
in-flight work.

### Other limits on this audit

1. **`ui/index.html` was not parsed.** If a capability is reached only by a JS
   fetch to an endpoint absent from `ui/server.py`, it would read here as dead.
   `server.py` imports only `grammar`, `evaluate`, `sample_valid`, `generative`,
   `mission` and `optimize.pareto_front`.
2. **Method reachability resolves by SHORT name**, so `Class.method` counts as
   used if any attribute of that name is loaded anywhere. That can only HIDE
   dead code, never invent it — every symbol in section 3 is dead, and there may
   be more. The worst collisions are `assess` (5 definitions) and
   `sample`/`fit`/`predict` (3 each).
3. **`navalai/blender/build_hull.py` was not executed** — `bpy` is not installed
   in `~/.venvs/naval`. It transcribes `closed_mesh`'s winding, so it is an
   eighth discretisation whose agreement is unmeasured. `build_hull.py` and
   `render_hull.py` read as "nothing imports them" but are invoked by path as
   Blender subprocess scripts from `blender/run.py:20-21`; they are not dead.
4. **No compute was run.** No OpenFOAM, no `mesh_robustness.py`. Every L3
   statement here is about the READING path (`l3_case_evidence`, `post`), never
   about a solve.
5. **Findings 1.3 and 1.4** were measured on the reference hull at z = 0 by a
   delegated agent, not over the sampled ok population, and are reported at that
   configuration. They are converged in both grid axes, so they are properties
   of the method and not of the sampling — but the population dependence is
   unmeasured.
