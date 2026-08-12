# PRODUCTION — the owner's vessel-as-a-system vision, audited against the code

> **Role: RESEARCH / EVIDENCE.** A dated audit record. It carries measurements,
> file paths and symbol names, and it carries **no status and no forward plan** —
> per `docs/BUILD-PLAN.md` §0, status comes from `python -m navalai.gates` and
> `python scripts/reconcile_gaps.py`, and the ordered plan is `docs/BUILD-PLAN.md`
> §16. Read this for *what was found on 2026-08-12 and how it was measured*.
>
> **Audited 2026-08-12** at `68d0854`, by reading code, not documents. Numerics
> were run against `git archive HEAD` in a scratch directory outside the tree,
> because another session held uncommitted work in `energy.py`, `resistance.py`
> and six other files at the time.

## 0 · Why this record exists, and the failure it is written against

The owner set out a production architecture — optimise the vessel as a coupled
system against **mission energy**, not a hull against `min R_T` — and asked
whether the project is over-invested in CFD calibration.

**A great deal of that architecture already exists.** This repository's recurring
defect is a thing declared twice, and on 2026-08-11 four documents each claimed
the governance kernel and the arrangement grammar did not exist; all four were
false. So the first duty of this audit is *not* to propose building what is
built. Each vision element below is classified **EXISTS / PARTIAL / MISSING /
REFUTED**, and where the vision restates something already shipped, it says so
plainly.

The second duty is the opposite one. Three vision elements are **contradicted by
measurements this repository already took**, and a plan that adopts them would
spend months re-learning what `docs/research/BLENDER.md` and `data/gate-ledger.json`
already record. Those are marked REFUTED with the measurement.

---

## 1 · The inventory

### 1.1 Summary table

| # | Vision element | Verdict | Where it lives / what is missing |
|---|---|---|---|
| 1 | Objective is `E_mission`, not `min R_T` | **PARTIAL** | `optimize.py` already minimises `wh_per_nm` as objective 1 of 3. But `wh_per_nm` is an *instantaneous intensity at one speed*, not an integral. §2.1 |
| 2 | `R(V)` over a weighted speed distribution | **MISSING** | Nothing computes it. The machinery to do so exists and is exercised one point at a time. **Highest value-per-effort item in this audit.** §2.1 |
| 3 | `R(V, Hs, Tp, β)` — added resistance in waves | **MISSING** | No drift force, no heading sweep, no acceptance data. Gap `F1`, filed CRITICAL. §2.2 |
| 4 | Four wave problems kept distinct | **PARTIAL** | Wave resistance: `resistance.michell_rw`. Seakeeping: heave only, zero speed. Slamming: absent. Green water: absent. §2.2 |
| 5 | Displacement a first-class variable with a full mass budget | **PARTIAL** | `weights.MassItem`/`aggregate` is a correct positioned spine with LCG/TCG/VCG and quadrature sigma. The *budget* feeding it is five bucket fractions. §2.3 |
| 6 | Every item's location matters | **EXISTS (spine) / PARTIAL (data)** | `MassItem.x_m/y_m/z_m` are required. Every production item has `y_m = 0.0`, so the `list` constraint is structurally dead. §2.3 |
| 7 | ≥5 loading conditions | **MISSING** | One condition, one hydrostatic solve. Zero hits for `lightship\|load_case\|loading_condition` in the tree. §2.4 |
| 8 | Solar roof as a parametric structural component | **MISSING** | Largest single gap in the inventory. Solar is `deck_area × 0.55 × 0.21 × 4.2`, a scalar. The coachroof is a declared 4-number box the geometry kernel has never heard of. §2.5 |
| 9 | Interior as a graph of spaces and connections | **PARTIAL** | `arrangement.py` has 14 classes, a 12-rule L0-A gate at 0.44 ms median, and boxes with real geometry. Adjacency is **carried and deliberately never checked**. There is no traversal. §2.6 |
| 10 | Watertight subdivision as a second graph, flooding, ΔGM | **MISSING** | No `Compartment`, no `Bulkhead`, no permeability, no damage case. In this repo "bulkhead" means a sheet of plywood in a BOM. §2.7 |
| 11 | Human accommodation as a deterministic constraint engine | **PARTIAL** | Deterministic: **yes, verified** — zero LLM references in `rules/`, `refdata/`, `arrangement.py`. But it is *one clause*, `E-DECK`, and **zero body dimensions are transcribed**. §2.8 |
| 12 | ISO 7250 / ISO 15537 anthropometry | **MISSING — and unlogged** | Not present, and unlike every other absence, not recorded in `NOT_SOURCED` or `PURCHASE_QUEUE`. §2.8 |
| 13 | Blender as spatial/visual layer, never source of truth | **EXISTS — already the shipped position** | `navalai/blender/__init__.py` says it in the package's own contract. §2.9 |
| 14 | Two coupled optimisers (outer hull, inner layout/systems) | **MISSING** | `optimize.py` contains zero references to `arrangement`. `arrangement.py` has exactly one importer in the repo: its own test. §2.6 |
| 15 | Hull genome becomes a vessel genome with 8 layers | **PARTIAL** | Genome is 15 hull numbers (`grammar.PARAMS`). Other layers exist as *declared specs*, not searchable dimensions. §2.10 |
| 16 | Compliance as a constraint engine from the start | **EXISTS** | `navalai/policy/compile_policy` emits a parameter BOX plus appended constraint ROWS, with a compile-time ratchet law. **The vision restates something built.** §2.11 |
| 17 | P2: replace crude STL-first geometry with an authoritative NURBS hull | **REFUTED** | §3.1 |
| 18 | P8: Blender as the spatial execution engine (subdivision / remesh / unfold) | **REFUTED** | §3.2 |
| 19 | P10: production output | **EXISTS, and it is the most complete layer in the repository** | DXF in millimetres with `$INSUNITS`, MaxRects nesting, counted BOM, ISO-derived ply schedule, gated export. §2.12 |

### 1.2 Reading the verdicts

Six of nineteen are MISSING. Two are REFUTED by measurements already in the
tree. Three EXIST and are restatements of shipped work. The remaining eight are
PARTIAL, and in **six of those eight the spine is correct and only the data or
one loop is missing** — which is the cheapest shape a gap can have.

---

## 2 · The measurements, element by element

### 2.1 The objective, and the one number that reframes the whole vision

`navalai/optimize.py:117` sets three objectives:

```python
F[i] = (ev.energy.wh_per_nm, build_area, abs(ev.gm_m - gm_mid))
```

so **`wh_per_nm` is already objective 1**, and the vision's "the objective is
`E_mission`, not `min R_T`" is half-shipped. `pymoo` NSGA-II, `pop=40, gens=30`
by default (`optimize.pareto_front:211`), consuming L1 only.

What is *not* shipped is the integral. `navalai/evaluate.py:488` takes
`u = mission.cruise_speed_ms()` — **one speed** — calls `total_resistance` once
(line 495) and `energy_report` once (line 511). `EnergySpec.cruise_hours_day = 8.0`
multiplies that single point into a day. A grep for
`speed_profile|speed_distribution|duty|histogram` across `navalai/` and
`scripts/` returns nothing but `_L3_SPEED_TOL = 0.02`, a single-speed *lookup*
tolerance — the opposite of a distribution.

**MEASURED 2026-08-12**, reference hull `tests.test_phase0.mid_params`
(LWL 10.00 m), swept by speed through the shipped `evaluate()` + `energy_report`
with `EnergySpec` defaults (deck 27.86 m², 8 h/day, hotel 3.0 kWh/day):

| kn | Fn | R_T [N] | Wh/NM | prop kWh/day | net kWh/day | range_solar NM/day | solar/demand |
|---|---|---|---|---|---|---|---|
| 2   | 0.1039 |   59.8 |   60.8 |  0.97 |  +9.54 | 172.93 | 3.402 |
| 3   | 0.1558 |  132.6 |  134.8 |  3.24 |  +7.28 |  78.01 | 2.168 |
| 3.5 | 0.1818 |  177.6 |  180.5 |  5.05 |  +5.46 |  58.25 | 1.678 |
| 4   | 0.2078 |  293.4 |  298.3 |  9.55 |  +0.97 |  35.25 | 1.077 |
| 4.5 | 0.2338 |  504.0 |  512.4 | 18.45 |  −7.93 |  20.52 | 0.630 |
| **5** | **0.2597** | **772.2** | **785.0** | **31.40** | **−20.89** | **13.40** | **0.393** |
| 6   | 0.3117 | 1721.0 | 1749.7 | 83.99 | −73.47 |   6.01 | 0.155 |

`MissionSpec.cruise_speed_kn` defaults to **5.0**, and the last column is what
the `policy_energy` constraint row measures against `KIT_LINE_V3.min_solar_fraction
= 0.60`. **The platform evaluates exactly one of these rows, and the row it
evaluates by default is the first one that fails.** Between 4 kn and 5 kn,
`R_T` rises 2.63× and daily propulsion demand rises 3.29×; between 3 kn and 5 kn,
solar range falls **5.8×**. The mission is decided by a number the model never
integrates over.

This is not an accuracy argument. It is a *modelling* argument: a solar-electric
craft's viability is a property of the speed **distribution**, and the platform
currently asks a yes/no question at one point on the steepest part of the curve.

**Cost to close:** the loop is `for (v, w) in profile:` around two existing calls,
plus three fields on `MissionSpec` and a weighted sum in `EnergyReport`. The
physics is already there and already carries a sigma. This is days, not weeks,
and it changes what the optimiser optimises.

### 2.2 The four wave problems

`docs/BUILD-PLAN.md` §11 and `docs/research/CFD.md` are the homes of the CFD
measurements; this section records only which of the four problems has code.

| Problem | Symbol | State |
|---|---|---|
| Wave resistance | `resistance.michell_rw`, `total_resistance` (`navalai/resistance.py:170`) | EXISTS, L1, valid to `FN_MICHELL_MAX = 0.45` |
| Seakeeping | `seakeeping.heave_rao`, `heave_seakeeping`, `waves.jonswap`, `encounter_omega` | PARTIAL — **heave only, zero forward speed** (`seakeeping.py:5`). No pitch RAO, no roll RAO, no 6-DOF |
| Slamming | — | MISSING. The only hit is `similitude.CAUCHY`, an enum entry naming a scaling law |
| Green water / deck wetness | — | MISSING. No symbol, no mention |

Added resistance in waves is gap `F1`, filed CRITICAL in `docs/GAP-REGISTER.md:160`
as "the largest un-started clause of Gate 2": zero implementation, no drift-force
routine, no heading sweep, no acceptance data, no gate row, no test.

**The asymmetry is the finding.** The vision is right that these four must not be
collapsed into one CFD number, and the repository has not collapsed them — it has
built one and left three empty, while a 74-hull mesh-only campaign
(`scripts/mesh_robustness.py --n 74`, `runs/g2u_n74`) was consuming the
simulation node during this audit.

### 2.3 Mass, and the location that never moves

`navalai/weights.py:35` — `MassItem` is a frozen dataclass with `id, mass_kg,
x_m` (LCG, 0 at transom, +forward), `z_m` (VCG, 0 at design WL, +up), `y_m`
(TCG, +starboard), `sigma_kg, tier, source, basis, volume_m3, material,
fluid_rho, fsm_i_t_m4, slack`. **`x_m` and `z_m` are required positional
arguments** — an item cannot exist without a location. `aggregate()` (line 99)
returns mass-weighted `lcg_m/tcg_m/vcg_m`, `sigma_kg` in quadrature, a free-surface
moment, and a `by_tier` breakdown; it raises on an empty list rather than
inventing a displacement.

**The spine is right. The data is five fractions.** `navalai/energy.py:106`:

```python
LCG_FRACTION = {"structure": 0.50, "battery": 0.45, "panels": 0.52,
                "outfit": 0.50, "payload": 0.48}
VCG_FRACTION = {"structure": 0.55, "battery": 0.15, "panels": 1.02,
                "outfit": 0.60, "payload": 0.70}
```

Five buckets plus an `"unaccounted"` filler injected at the aggregate's own
centre (`evaluate.py:445`) with `sigma_kg = 0.5 × gap`. Battery mass is real
(`BATT_KG_PER_KWH = 7.5`) and low (`VCG 0.15`); panel mass is real
(`PANEL_KG_PER_M2 = 12.0`) and high (`VCG 1.02`). So the vision's "battery low,
PV high" is *already encoded* — as two constants, not as a placement decision.

**Every production item has `y_m = 0.0`.** `evaluate.py:69-84` records the
consequence in its own comment: the `list` constraint "read EXACTLY −2.000
across 800 evaluations, because `agg.tcg_m` is identically 0 while no mass item
declares a transverse offset." One of eight `CONSTRAINT_NAMES` rows occupies an
NSGA-II dimension it can never move in.

A richer positioned source **already exists and is not wired**:
`arrangement.Space.mass_item()` / `DeckZone.mass_item()` / `Arrangement.mass_items()`
(`navalai/arrangement.py:636, 684, 776`) emit tier-`E` items with real `y_m`.
`evaluate.py` does not import `arrangement`. Wiring that one import is what makes
the `list` row live.

`MassAggregate` carries no sigma on the centres — item mass uncertainty
propagates into `sigma_kg` but not into LCG/TCG/VCG, so the GM badge's sigma
(`evaluate.py:619`) propagates mass uncertainty through `kg` and *position*
uncertainty not at all.

### 2.4 Loading conditions

`grep -r "lightship\|light_ship\|load_case\|loading_condition\|LoadCondition" navalai/`
returns **zero hits**. The ladder floats the hull once, at
`evaluate.py:452`:

```python
target = max(agg.total_kg, mission.displacement_target_kg)
hs, wl = solve_to_displacement(hull, target, rho)
```

One `HydroState`, one `MassAggregate`, one GM, one trim, one heel.
`navalai/hydrostatics.py` exposes `solve`, `solve_to_displacement`, `gm`,
`gm_long` and no condition sweep.

Two things exist that are *adjacent* and are not the same thing. `R-OLH`
(`navalai/rules/iso12217.py`) moves `crew × 85 kg` to `0.40 × beam` and computes
heel from an exact moment balance — one prescribed transverse offset **within**
the single displacement; it does not re-float. And `agg.free_surface_correction()`
is subtracted from GM but is exactly zero with no tanks declared.

The vision's five conditions are therefore MISSING, and the cost is bounded: the
solver is already a function of a target displacement and a mass list, so a
condition is a `(name, items, target)` tuple and a loop. The expensive part is
not the loop; it is that four of the five conditions need mass items the bucket
model does not distinguish (payload in/out, tanks full/empty), which is the same
missing data as §2.3.

### 2.5 The solar roof — the largest single gap

The vision asks for the solar roof as a parametric structural component: PV area,
mass, tilt, shading, wind load, walkability.

**Solar in this platform is one line** (`navalai/energy.py:232`):

```python
solar = deck_area * spec.panel_packing * spec.panel_eff * spec.solar_yield_kwh_m2_day
```

with `panel_packing = 0.55`, `panel_eff = 0.21`,
`solar_yield_kwh_m2_day = 4.2` ("Danube ~45N summer average, horizontal") and
`deck_area = Hull.deck_area()` = `2·∫ y_sheer dx`, the sheer plan-form.

*Checked, because the naming invites a double-count:* 4.2 is **irradiance**, not
yield. 27.86 m² × 0.55 × 0.21 × 4.2 = 13.52 kWh/day = 0.88 kWh per m² of panel
per day, which is what 21 % modules return under 4.2 kWh/m²/day. **The
multiplication is correct**; only the field name is misleading.

Absent: tilt, azimuth, shading, temperature derate, wind load. Grepped —
no hits in the energy path.

**And the coachroof does not exist as geometry.** `navalai/arrangement.py:254`,
`Trunk`, says it in the code's own words:

> "A **DECLARED** coachroof, and the only thing in this module the geometry
> kernel does not know about. The hull grammar emits a flush deck at the sheer —
> `Hull` has `y_sheer` and `z_sheer` and **no superstructure** — so on a 10 m hull
> with D = 1.55 m and T = 0.55 m the whole interior is 1.5 m tall and **NOTHING
> can stand up in it**. … **Nothing validates its structure, its windage or its
> effect on stability.**"

`Trunk(x0, x1, half_width, height)` is four numbers with hand-authored constants
(`_TRUNK_X0 = 0.13`, `_TRUNK_X1 = 0.70`, `_SIDE_DECK_M = 0.25`, documented as
"the AUTHOR'S split"). It is not in the genome, not exported, not unrolled, not
meshed, not in any CFD case, and not in the weight budget as structure.

**Consequence, and this is the sharp end:** `Trunk` never reaches `energy.py`, so
**the largest flat horizontal surface on a solar liveaboard contributes zero m²
to the solar model**. For a platform whose binding constraint is PV area, the
deckhouse is the missing half of the vessel. Unlike Gate 6D it has no gate, no
owner and no ledger row.

Every other `panel` in `navalai/` is plywood (`panel_twist`, `panel_mesh`,
`panel_thickness_m`, `hull_panels`), not photovoltaic. `arrangement.py:611` states
that its systems envelope explicitly excludes "the hull structure, batteries or
**PV**".

### 2.6 The interior graph, and the second optimiser

`navalai/arrangement.py` is 1484 lines, 14 classes, Gate V2.1. It is real work
and the vision should not propose rebuilding it: `Envelope.from_hull()` reads the
actual hull, `check_l0a()` runs 12 rule ids (`R_DEGENERATE`, `R_ENVELOPE_X/Y/Z`,
`R_OVERLAP`, `R_MIN_DIMS`, `R_DECK_PLAN`, `R_DECK_TRUNK`, `R_DECK_OVERLAP`,
`R_DECK_MIN_WIDTH`, `R_BARRIER`, `R_NODE`) at a **measured median 0.44 ms**
(`tests/test_arrangement.py:213`, bar 10 ms), `TOUCH_TOL_M = 1e-3` because
"touching faces are how bulkheads work", and envelope-Y is checked at two
z-levels after a saloon "protruded 435 mm through the side of the coachroof".

**But it is not a graph.** `Adjacency` is an enum with `PREFER`/`AVOID`;
`Space.adjacency` is a tuple of `(id_string, Adjacency)`. The module docstring:
"Adjacency preferences are PARSED AND CARRIED, never checked", and
`tests/test_arrangement.py:1112` *enforces* that no gate reads them. No edge
object, no node registry, no traversal, no `networkx` in either requirements
file. Nothing checks that an adjacency target id exists — the reference layout
points `berth.aft` at `"cockpit"`, a `DeckZone` and not a `Space`, a dangling
cross-namespace reference nothing catches.

Egress is absent outright: zero hits for `escape|egress|evacuat|corridor` in
`arrangement.py` or `rules/`. Circulation passage width is absent **and logged**
— `refdata/ergonomics.NOT_SOURCED` calls it "the single most load-bearing number
in an interior arrangement" and warns that `SOLE_MIN_CLEAR_WIDTH_MM` "must not be
quietly promoted into a passage rule."

Placement is neither packing nor grammar nor optimiser: `reference_layout()` is
hand-authored, "the x-stations are the author's". The module says why —
"There is no solver. V2.3 is the CP+GA generator … writing the optimiser here
would be borrowing that risk a phase early" — and it has already built the
interface a solver would need: `to_vector()`, `from_vector()`, `bounds()`,
`n_slots == 6·len(spaces) + 4·len(deck_zones) == 64`.

**The inner optimiser the vision asks for has its socket already cut.**
`navalai/optimize.py` contains zero references to `arrangement`, and
`navalai/arrangement.py` has exactly **one** importer in the whole repository:
`tests/test_arrangement.py:45`. Not `pipeline.py`, not `agents.py`, not
`evaluate.py`.

### 2.7 Watertight subdivision

MISSING, and the codebase never claims otherwise. Grepping
`bulkhead|compartment|flooding|damage|subdivision|watertight|downflood` across
`navalai/` returns four unrelated families:

- `engineer.py:53,144` — `BULKHEAD_SPACING_M = 1.4`,
  `bulkheads = max(2, int(np.floor(lwl / 1.4)))`, feeding `rect_parts("bulkhead-k", …)`.
  **This is a plywood cut list.** No position, no watertightness, no volume.
- `stl_watertight_report` (`cfd/case.py:1229`, `mesh_repair.py`, `stl_forensics.py`)
  — mesh topology for CFD.
- `subdivision_type = "CATMULL_CLARK"` (`blender/build_hull.py:178`) — surface
  refinement.
- `R-DFH` (`rules/iso12217.py:86`) — **intact** downflooding height,
  `hD(R) = (LH/15) × F1…F5` clamped to Table A.1. No compartment is ever flooded.

No `Compartment`, no `Bulkhead`, no permeability, no lost-buoyancy or
added-weight method, no damage case, no ΔGM. **In this repository, "bulkhead"
means a sheet of plywood in a bill of materials.**

### 2.8 Human accommodation

The vision's structural claim — *deterministic constraint engine, not an LLM
judging a room* — is **already the shipped position and is verified**. Grepping
`llm|anthropic|openai|claude|gpt|prompt|ollama|gemini` across `navalai/rules/`,
`navalai/refdata/` and `arrangement.py` returns zero hits. The single LLM seam in
the repository is `navalai/translate.py`, an injected
`Callable[[str], str] | None` defaulting to `None`, and it can reach ergonomics
only through one clamped integer, `MissionSpec.crew`. `agents.py:14`: "the
deterministic solvers stay deterministic; 'agent' here is an isolation + audit +
async-throughput shell, not an LLM."

**What is thin is the engine, not its determinism.** `navalai/rules/ergonomics.py`
implements exactly **one** clause, `E-DECK`:
`working_deck_area_m2(hull) >= crew × seat_area_m2()`, with
`seat_area_m2() = 0.400 × 0.750 = 0.300 m²/person` from ISO 15085:2024-preview
`SEAT_MIN_MM`. Panels steeper than 25° longitudinal are **excluded from the area,
not failed** — a scope rule, and the module insists on the distinction. Its own
docstring records the limb firing below ~7.2 m LWL and excluding nothing at 10 m.
It frames itself correctly: "a pass is not 'the crew fit'; a fail is 'they do not.'"

**Anthropometry: zero body dimensions.** `refdata/ergonomics.py` holds 43
`RefValue`s (31 `approx`, 12 `standard-2003`). The `RefValue` schema has a
`percentile` field (`refdata/__init__.py:74`) and **it is set on 0 of 68
constants across all of `refdata/`** — the field is dead. The file says so:
"No body dimension is transcribed here." What exists is *furniture*:
`BERTH_LENGTH_STANDARD_MM = 2060`, `HEADROOM_COMPROMISE_MIN_MM = 1905`,
`HEAD_BOWL_TO_DOOR_MIN_MM = 560`, `SHOWER_MIN_SQUARE_MM = 610`,
`HATCH_CLEAR_MIN_MM = 460`, and 12 verified ISO 15085:2003 deck values.

`refdata.absent()` records **14 entries (9 ergonomics, 5 flotation)**, including
`anthropometric_percentile_tables` ("Panero & Zelnik (1979) is named as the
canonical decomposition … but the tables themselves are not reproduced in any
source we hold"), `percentile_stretch_factor`, `circulation_passage_width_mm`,
`berth_vertical_clearance_mm`, `abyc_h41_dimensions`. **ABYC H-41 is PARTIAL** —
two values only, `REBOARDING_MUST_BE_UNASSISTED` and
`LADDER_AND_GATE_DESIGN_LOAD_N = 1780` ("400 lb").

**ISO 7250 and ISO 15537 are absent and are not recorded as absent.** Zero hits
across `navalai/`, `tests/`, `docs/`; they appear in neither `NOT_SOURCED` nor
`PURCHASE_QUEUE`. Every other missing standard in this repository is logged with
a reason and an unblocking action. These two are the one hole in that discipline,
and they are exactly the two the vision names.

Rules-tier state, read through `navalai/rules/review.py` (which is the authority
for confirmed-vs-`unconfirmed` and is the home of those counts): six rule ids —
`R-SCP`, `E-DECK`, and the four ES-TRIN ids — appear in **neither** set, which by
the module's own definition ("a rule missing from both sets is an oversight; a
rule here is a decision") makes them oversights.

### 2.9 Blender

**EXISTS, and the vision restates the shipped position.**
`navalai/blender/__init__.py:40`:

> "**WHAT THIS PACKAGE IS NOT.** It is not in the ladder, not in `pipeline.py`,
> and no gate consumes an STL it produces."

Five modules split across a process boundary (Blender ships CPython 3.13; the
venv is 3.12), subprocess only, never `import bpy` on the venv side.
`metrics.py` is the one ruler used for every table in `docs/research/BLENDER.md`.
Its only consumer is `tests/test_blender_hull.py`.

The architectural limit is stated in `BLENDER.md` §5 and it is load-bearing for
the vision: any Blender-side deformation "produces geometry that is not
describable by `grammar.named(params)`, so `evaluate()` cannot score it, the
policy box cannot bound it, the surrogate cannot be queried on it."

### 2.10 The genome

`navalai/grammar.py:22` — `PARAMS`, `N_PARAMS = 15`: `LWL, BWL, T, D, beta_mid,
beta_bow, p_bow, p_stern, x_mb, r_transom, rocker, forefoot, flare, sheer_rise,
beta_len`. `navalai/hull_ast.py:126` — `HullDesign` regroups the same 15 into
`Typology / Principal / Planform / SectionLaw / Profile / Topside`, round-tripping
exactly through `to_vector()`.

**Hull-only.** Structure, layout, energy, propulsion, systems and safety exist as
downstream *declared specs* — `EnergySpec`'s 8 defaults, `limits.PLY_THICKNESS_M`,
`FRAME_SPACING_M`, the hand-authored `reference_layout()` — not as searchable
dimensions. The vision's "vessel genome" is therefore PARTIAL in a specific
sense: **the layers exist; they are not in the search space.**

Grammar cost, MEASURED over 400 000 uniform in-bounds vectors (comment block,
`grammar.py:143`): 15 bound checks + 9 live relations, L0-feasible fraction of
the box **20.686 %**, `check()` at **88.8 µs**. Four checks were deleted as
tautologies at 0 hits each.

The policy box bounds **two** of the fifteen — `LWL` and `T`
(`policy/compiler.py:366` `ParameterBox`, edits from RCD Art. 3(2) scope,
Art. 20 Module A break, `KIT_LINE_V3.max_hull_length_m = 11.9`,
`max_draft_m = 1.10`). Everything else is free.

### 2.11 Compliance as a constraint engine — the vision restates a shipped system

`navalai/policy/compiler.py:704`, `compile_policy(constitution) -> CompiledPolicy`,
emits exactly the two outputs the vision asks for:

1. **A parameter BOX** — `CompiledPolicy.box(category, low, high) -> ParameterBox`,
   applied via `tighten()` which is `max` on low / `min` on high and records a
   `BoxEdit` only when a bound actually moved. `optimize.py:65` constructs the
   NSGA-II sampler inside it, so a length ceiling is a **bound**, not a rejection.
2. **Constraint ROWS appended** to `evaluate.CONSTRAINT_NAMES` / `Evaluation.g` —
   `policy_legal`, `policy_dna`, `policy_energy`, `policy_floors`. Append-only-ness
   is enforced: a policy row colliding with a base name raises
   `ConstraintOrderError` (`evaluate.py:140`).

And a **ratchet law enforced at compile time**: for every floor, `tighter` must
hold against the live `limits.py` value; *equal* raises ("POLICY IS NOT A
RATCHET, IT IS A SECOND COPY") and looser raises. Every `PolicyValue` carries a
`basis ∈ {directive, regulation, policy, derived}` and a source string of at
least `MIN_SOURCE_CHARS = 20`.

Measured effect (`optimize.py:45`): "pop 24, 8 generations, seed 5: the ungoverned
search drew 143 of 192 individuals above the 11.9 m ceiling … the governed search
drew 0."

**Scope, stated honestly by the code:** one directive (RCD 2013/53/EU: Art. 3(2),
Art. 20, Art. 2(2)(a)(vii), Art. 19(4), Annex I 3.2/3.3) and one regulation
(AI Act Art. 6(1), Annex I §A item 3). `SAFETY_COMPONENT_QUESTION`
(`policy/legal.py:153`) says "OPEN, AND WE DO NOT ANSWER IT … `high_risk` is
therefore None and never True or False." The ISO conformity work is in
`navalai/rules/`, not here. And `KIT_LINE_V3.floors = {}` — **the reference SKU
ratchets nothing**, so on the shipped configuration the ratchet engine has zero
findings and `policy_floors` never appears. Three of ten `RATCHETS` entries have
`measure=None` (`bend_radius_ratio`, `frame_spacing_m`, `crew_mass_kg`) and can
never produce a row.

**Verdict: EXISTS.** The vision's "compliance is a constraint engine from the
start, not a document at the end" describes `navalai/policy/`. What it needs is
*more clauses*, not an architecture.

### 2.12 Production output

The most complete layer in the repository, and the vision's P10 should be read as
already delivered in outline:

| Artefact | Symbol | Note |
|---|---|---|
| DXF | `unroll.export_dxf:1448`, `parse_dxf_polylines:1497` | R12 ASCII, **in millimetres, declared via `$INSUNITS 4`** — it previously wrote metres with no header, i.e. a shop would cut a 10 mm part instead of a 10 m one |
| Nesting | `unroll.nest:1375`, `_MaxRects:1152`, `Nesting.utilisation()` | Real MaxRects with rotation. Sheet `1.22 × 2.44 m` declared once |
| Part splitting | `unroll.split_panel:1263`, `min_strakes:1241`, `SCARPH_RATIO` | Panels measure 10.05 × 1.62 m and 10.54 × 1.44 m — **neither fits a sheet** — so they split at 8:1 scarphs |
| BOM | `engineer.BomLine`, `EngineerReport:80`, `assess:127` | `ply_sheets` **counted off the layout**; previously area × a 1.30 waste factor, reporting "35 sheets" for panels that fit on no sheet |
| Ply schedule | `limits.STOCK_PLY_THICKNESS_M`, `rules.iso12215.select_stock_thickness_m` | Derived, and it **raises** rather than rounding a requirement down |
| STEP / IGES | `export.export_step`, `export_iges`, `refuse_unvalidated` | Gated: an L0-failing hull previously exported an 8 487-byte DXF and a 174 406-byte STEP without complaint |

`engineer.STRAKE_TRIALS = 5`, MEASURED to saturate at 4 (1 trial → 81 sheets @
57.1 %; 2 → 72 @ 66.9 %; **4 → 68 @ 76.8 %**; 8 → 68 @ 76.8 %).

MISSING: G-code, post-processor, toolpath, kerf/lead-in/tab. DXF outlines are as
far as it goes, and for a CNC kit that is the remaining step.

---

## 3 · The two REFUTED items

A vision item that survives a measurement contradicting it will cost months. Both
of these are refuted by measurements already committed to this tree.

### 3.1 REFUTED — "replace the crude STL-first geometry with an authoritative NURBS hull"

**There is no NURBS hull in this repository, and adding one does not change the
surface.**

`navalai/geometry.py:22` `station_geometry` emits three closed-form edge curves
(keel, chine, sheer); `Hull.section` returns **two straight segments** per
half-section. `navalai/export.py:132` `export_step` builds one **closed 5-point
polygon** per station and calls `cq.Solid.makeLoft(wires, ruled=True)` —
`ruled=True` meaning no fairing, each face bilinear.

**MEASURED 2026-08-12** by parsing the committed artifact
`data/exports/hull.step` (589 067 B, `n_stations = 41`):

```
ADVANCED_FACE                    202
B_SPLINE_SURFACE_WITH_KNOTS      200      ← all 200 parse as degree (1,1)
PLANE                              2      ← transom cap + stem cap
CLOSED_SHELL                       1
```

Every one of the 200 reads `'',1,1,((#a,#b),(#c,#d)),…,(2,2),(2,2),…,
.PIECEWISE_BEZIER_KNOTS.` — **degree 1×1, a 2×2 control net, four corner
points**. 200 = 40 spans × 5 ring edges. A degree-1×1 B-spline with a 2×2 pole
net *is a bilinear quadrilateral wearing a NURBS costume*; OCC writes it that way
because ThruSections always emits B-spline geometry. (One correction to the claim
as I received it: the solid has **202** faces, not 200 — the two extra are planar
caps.)

Two independent measurements close the argument:

- **Blender reproduces `closed_mesh` to float32.** `docs/research/BLENDER.md` §2,
  hull 14: 288 836 triangles and 144 420 vertices identical, vertex map bijective,
  every triangle matched, **max coordinate difference 9.67e-07 m**. There is no
  second geometry with a different answer to reproduce.
- **Adding smoothness moves the surface OFF the hull.** BLENDER.md §4, one
  Catmull-Clark level on the shipped 600×120 cage, without creases:
  **up to 19.07 mm (hull 4), 17.40 mm (hull 14), 11.80 mm (hull 8)**, with the
  chine dihedral collapsing 53.5 / 72.0 / 69.4° → 28.0 / 39.9 / 37.8°. With
  creases at the 30° bar it is 0.12 mm (hull 14) and 1.70 mm (hull 4) — *at best
  equal to the current path*, for **4× the triangles** (1 155 588 vs 288 836) and
  **3.3× the file** (230.3 vs 68.8 MB).

**And the piecewise-linear surface is not "crude", it is the product.** The scope
is plywood-native craft cut on a CNC kit-cutter (`docs/BUILD-PLAN.md` §1.4). Two
straight segments per half-section is what makes a panel developable at all. At
41 stations the loft volume error against the kernel is **−0.0004 %**, a factor
of 1240 better than the old 12-station loft's −0.497 %
(`tests/test_manufacturing.py`).

**Therefore:** the phase list should **skip P2**. What a NURBS kernel would buy —
fairness — is a property the manufacturing constraint forbids, and the two paths
that exist already agree to a micron.

**One caveat that is NOT a refutation, and belongs to the next section.**
`data/gate-ledger.json` records Gate 6D at a refold watermark far outside its bar,
and `navalai/unroll.py:84-108` locates two of the three causes **in
`geometry.station_geometry`, not in the unroller**: the sheer envelope
`y_sheer = ys · w**0.15` drives `dy/dx → ∞` at the stem (the sheer polyline is
65.6 mm off the analytic sheer at 41 stations *before developability is asked
about*, converging at ~O(h^0.5): 81.0 / 65.6 / 47.3 / 29.9 mm at 21/41/81/161
stations), and chine and sheer have a **slope discontinuity at `x = x_mb·L`**
where `dw/dx` jumps 0.1364 → 0, which alone puts a 6.02–6.16 mm step into the
topside refold — **larger than the whole bar by itself**. Both refold families get
*worse* with refinement. So the geometry kernel does owe a change; it is
`C1 continuity at x_mb` and `bounded dy/dx at the stem`, which is the ledger's own
`next` field. **That is a two-parameter repair to the existing analytic hull, not
a NURBS kernel** — and confusing the two would buy the expensive answer to the
cheap problem.

### 3.2 REFUTED — "Blender as the spatial execution engine"

The vision is right that Blender must never be the engineering source of truth,
and §2.9 shows the repository already agrees. The refutation is of the *other*
half: the specific Blender operations a spatial engine would use are measured to
destroy the product.

- **Voxel remesh deletes the chine.** BLENDER.md §3, chine dihedral median over
  400 stations at 5 mm offset, `voxel_size = 0.05`: **0.0 / 0.0 / 0.0°** on hulls
  4/8/14 against **53.5 / 69.4 / 72.0°** analytic. "0.0 deg is not a rounded
  chine, it is no chine: both probe points land on the same face." At 0.025 m it
  is 9.4 / 14.2 / 1.7° — no rescue. Deviation moves from a 0.01–3.03 mm band to
  **22.2–57.6 mm**; `surfaceCheck` self-intersections go 3–237 → **1479–1866**.
  BLENDER.md's verdict: "Do not put a voxel Remesh on the hull path, at any voxel
  size measured."
- **`bpy.ops.export_mesh.paper_model` does not exist.** MEASURED: Blender 5.2.0
  ships **13** add-ons and Paper Model is not among them; the
  `bpy.ops.export_mesh` namespace is **empty**, and there is **no DXF exporter**.
  And it would not help: it unfolds a *triangle mesh*, so 289 000 triangles with
  seams and tabs yields confetti, not boat panels. The repository's own unroller
  (`navalai/unroll.py`, §2.12) operates on ruled panels and is the right tool.
- **Subdivision** — §3.1.

What Blender *is* good for is exactly what it is used for: Cycles rendering
(hull 14 STL, 960×600 @ 64 samples on M5 Pro Metal = **99.3 s**) and independent
measurement. Keep it there.

---

## 4 · The CFD question, answered directly

The owner believes the project is over-invested in CFD calibration. **The
evidence supports that, with one important correction to the reason.**

### 4.1 What CFD has cost and what it has returned

`data/gate-ledger.json` is the home of both watermarks and this section does not
restate them; read it, and `docs/research/CFD.md` §2, for the numbers. The shape
of the record is what matters here:

- Gate 2M's watermark is deliberately **not a number**. Six figures have
  circulated and every one was superseded or is unreproducible; the run that
  carried the last of them was deleted.
- Gate 2U's watermark is **mesh-only** at N=18 in a configuration the product no
  longer ships, against a bar of ≥95 % of 200 hulls, and its `why_red` states
  that the "converges" half of "meshes AND converges" **has never been measured**.
  The campaign running during this audit (`scripts/mesh_robustness.py --n 74`,
  `runs/g2u_n74`, `data/gate2u-n74-mesh.json`) is again mesh-only.
- `docs/research/CFD.md` §2 retires the standing assumption that run length was
  the blocker: at 3.40 flow-throughs drift collapsed to 0.31 % and the error did
  not move. Viscous is right (1.161× ITTC-57, 1.7 % batch error); **the residual
  is in the pressure — the wave-making half — at 2.32× with a 36 % batch error.**
- `docs/research/APSE.md` §4 prices a GCI triplet at **3.24 + 13.58 + 51.89 =
  68.7 h ≈ 2.9 days**, 21.2× the coarse grid, and records a test proving the
  stated compute budget and the ≥20 cells-per-wavelength bar are **unsatisfiable
  together** — `cheapest_admissible` returns `None` for both the coarse and medium
  budgets.

And the geometry of the cost is against us specifically. APSE's closed form is
`cells/wavelength = 5.585 · Fn² · nx`, with `Lwl` cancelling. **Fn enters
squared, so low-Froude cases are the expensive ones to resolve.**

### 4.2 Where the product actually sits

MEASURED, from the code's own defaults (`grammar.PARAMS` LWL ∈ [4, 20] m;
`MissionSpec.cruise_speed_kn = 5.0`):

| LWL | Fn at 5 kn |
|---|---|
| 10 m | 0.2597 |
| 11 m | 0.2477 |
| 12 m | 0.2371 |

So the product sits at **Fn 0.237–0.260**, and at nx = 57 that is 19–21.5
cells/wavelength — right on the ≥20 bar, with the *longer and slower* SKUs
falling under it. KCS is calibrated at Fn 0.26, which is the top of our band and
the cheapest point in it. Every SKU condition is more expensive to resolve than
the anchor, and the anchor is a **container ship** (`benchmarks/kcs.py:87`) that
shares no chine, transom or spray physics with the product line.

### 4.3 Does L1 need to be calibration-grade to RANK hulls?

**No — and here is the measurement.**

MEASURED 2026-08-12 on `git archive HEAD`: 600 grammar draws with `LWL` pinned at
the Kit-Line ceiling **11.9 m** (the length the policy box fixes, so the remaining
decision is *shape*), mission 6 t / 5 kn / cat C, keeping only hulls that pass the
full ladder (`ev.ok`) — **n = 68 feasible hulls, all at Fn 0.2381**.

Spread of the objective across that feasible set: `R_T` from **322.9 N to 2201.7 N,
a 6.82× spread**, CoV 48.7 %. Declared L1 sigma averages 19.44 % of `R_T`.

**(a) A common-mode Michell bias does not change the answer.** Scale the wave
component `Rw` by a common factor and re-rank:

| `Rw ×` | Spearman ρ vs unbiased | top-10 overlap | winner unchanged |
|---|---|---|---|
| 0.60 | 0.996870 | 9/10 | **yes** |
| 0.80 | 0.999046 | 9/10 | **yes** |
| 1.00 | 1.000000 | 10/10 | yes |
| 1.25 | 0.998664 | 10/10 | **yes** |
| 1.50 | 0.998015 | 10/10 | **yes** |

A ±50 % systematic error in the *dominant* resistance component leaves the
selected hull unchanged and preserves 9–10 of the top 10. It is not exactly 1.000
because `Rw/R_T` varies hull to hull (17.4–86.9 %), so the bias does not cancel
perfectly — but ρ ≥ 0.9969 across a 2.5× range of bias.

**(b) It takes a huge *hull-specific* error to break the ranking.** Apply an
independent lognormal error to each hull's `Rw`, 1000 trials per level:

| σ on `Rw`, hull-specific | mean top-10 overlap | P(perturbed winner ∈ true top-10) |
|---|---|---|
| 5 %   | 9.4 / 10 | 100.0 % |
| 10 %  | 9.2 / 10 | 100.0 % |
| **25 %** | **8.5 / 10** | **100.0 %** |
| 50 %  | 7.2 / 10 |  98.4 % |
| 100 % | 5.1 / 10 |  73.8 % |

At the L1 model's own declared 25 % on the wave term, the perturbed winner is in
the true top 10 in **100.0 %** of trials. **A 5 % resistance uncertainty is
comfortably good enough to rank hulls; so, on this evidence, is 25 %.** The
selection is protected because the candidate set spans 6.8× while the error spans
tens of percent.

**The reasoning, stated plainly:** ranking is invariant to any error that is a
function of the operating point, and every candidate here shares the operating
point exactly — the policy box pins `LWL`, and the mission pins the speed, so all
68 hulls sit at the same Fn to four decimals. Michell's known systematic — hump
overprediction — is precisely such a function. What could break the ranking is an
error that varies *with the shape parameters NSGA-II is free to move*, and the
table above shows even that must reach ~100 % before the winner leaves the top 10.

### 4.4 What CFD is then still needed for

Three things, and none of them is a GCI triplet on KCS.

1. **Absolute numbers for the final candidate.** Ranking is invariant to bias;
   *sizing* is not. MEASURED on the reference hull at 5 kn, applying a common-mode
   bias to `R_T` and re-running `energy_report`:

   | bias | `R_T` [N] | Wh/NM | range_solar [NM/day] | range_batt [NM] |
   |---|---|---|---|---|
   | 0.75 |  579.1 |  588.8 | 17.86 | 40.76 |
   | 1.00 |  772.2 |  785.0 | 13.40 | 30.57 |
   | 1.50 | 1158.2 | 1177.6 |  8.93 | 20.38 |
   | 2.00 | 1544.3 | 1570.1 |  6.70 | 15.29 |

   Range varies **2.7× across a 0.75–2.0 bias**. That is the number a customer is
   quoted and a battery is sized against, and no amount of ranking invariance
   helps it. **One absolute anchor on the delivered hull is worth more than a
   convergence study on somebody else's container ship.**

2. **The three wave problems L1 cannot touch at all** — added resistance in waves
   (gap `F1`, CRITICAL), slamming, green water. These are not accuracy
   improvements to an existing number; they are numbers that do not exist. §2.2.

3. **The regime the anchor does not cover.** KCS validates VOF capture, wave
   resolution and the ITTC friction line. It does not validate chine, transom or
   spray physics, and `benchmarks/kcs.py:109` already records that a second
   anchor is owed.

### 4.5 The correction to the owner's reason

The owner's *conclusion* is right; one premise needs adjusting, and it cuts
against the comfortable version of the argument.

**The L1 sigma is a declaration, not a measurement, and the wave term dominates
at the product's own cruise point.** `resistance.py:290` sets
`sigma = 0.25·rw + sigma_rf`, and its own comment says the 0.25 is "declared, the
literature's standing caveat"; `FORM_FACTOR_SIGMA_DECLARED = 0.05` is "declared,
not sourced"; `holtrop.SIGMA_DECLARED = 0.10` says "DECLARED, NOT SOURCED …
Replace it the day a measured spread against tank data exists." **No tank-data
spread exists anywhere in this repository for either model.** Wigley validates
the *arithmetic* of the Michell integral against a closed form (production grid
within 0.86–2.11 % of `benchmarks/wigley.rw_analytic`, and that file says
outright it "does NOT validate thin-ship theory against a towing tank"); Holtrop
validates a *transcription* against the 1982 worked example (`R_total` +0.0184 %,
18 tests) — and gap `E1b` records that Holtrop **is not wired into `evaluate()`**
and that our own small craft fall outside its envelope (a 10 m tender returns
`L1H-INVALID` on B/T 6.67 against a band of 2.1–4.0 and L/B 3.33 against 3.9–9.5).

And MEASURED 2026-08-12, reference hull, the component split by speed:

| kn | Fn | `Rw`/`R_T` |
|---|---|---|
| 2 | 0.1039 |  1.1 % |
| 3 | 0.1558 |  6.4 % |
| 4 | 0.2078 | 28.3 % |
| **5** | **0.2597** | **59.0 %** |
| 6 | 0.3117 | 74.3 % |

At the default cruise point **59 % of total resistance is the Michell wave term** —
the component with the largest declared uncertainty and no tank anchor — and
across the 68-hull feasible batch at Fn 0.2381 the mean is **60.6 %**. So it is
not true that "the physics is friction-dominated and therefore safe at Fn 0.25";
by the model's own accounting it is wave-dominated there.

**That does not rescue the CFD programme, because the CFD cannot arbitrate it.**
The KCS residual is *in the pressure half* at 2.32× with a 36 % batch error
(`docs/research/CFD.md` §2). The tool that would settle the wave term is the
tool that is currently wrong about the wave term, at 68.7 h per triplet, on a
container ship, at the cheapest Froude number in our band.

### 4.6 The verdict, unhedged

**Yes — the project is over-invested in CFD calibration, and the over-investment
is specifically in *calibration-grade convergence work on KCS*.**

- L1 is good enough to RANK, measured: at the declared 25 % wave-term
  uncertainty the selected hull stays in the true top 10 in 100 % of 1000 trials,
  and a ±50 % common-mode bias leaves the winner unchanged (§4.3).
- The design loop does not consume CFD and never has. `optimize.py` imports
  nothing from `navalai.cfd` and calls only `evaluate()`; `evaluate()` imports
  `resistance` (Michell) and reaches `cfd.post` solely inside `l3_case_evidence`,
  which **never starts a solver** and refuses with "NO EVIDENCE AT THIS TIER"
  absent a hand-run directory. `admissibility.py` and `fidelity.py` import CFD
  *constants* to price a case, not to get a force. `docs/BUILD-PLAN.md` §11.1
  already says "CFD is an anchor, not a loop"; the code is honest and the spending
  is not aligned with it.
- The compute is unsatisfiable against its own bars (APSE §4) and the residual is
  measured not to be a settling problem (CFD.md §2), so the next increment of the
  same work has a *measured* expectation of returning nothing.

**But the money should not simply stop — it should MOVE, and it should get
cheaper.** Two of the three CFD-shaped debts are cheap and untouched. *These are
this audit's conclusions, not a schedule; the ordered plan that consumes them is
`docs/BUILD-PLAN.md` §16, P5.*

1. **A small-craft resistance anchor** (Fridsma hard-chine, DSYHS, or DTMB 5415),
   used to replace `SIGMA_DECLARED` with a *measured* spread. This converts the
   L1 band from an assertion into a measurement and is the single highest-value
   physics item in the audit. It is literature transcription plus a comparison —
   days, not machine-days — and it needs **no OpenFOAM at all**.
2. **Added resistance in waves** (gap `F1`), which is Capytaine at L2, not
   interFoam at L3, and which no amount of KCS convergence work produces.
3. And a **single absolute point on the delivered hull**, once, to bound the
   sizing error in §4.4 — one grid, not a triplet, and the honest output is a
   sigma rather than a validated C_T.

The 74-hull mesh-only campaign is worth finishing since it is already 43/74 done
and its artifact is committed data. **The GCI triplet is not worth starting**: it
costs 2.9 machine-days to bound a discretisation error on a benchmark whose
remaining error is measured not to be discretisation.

---

## 4A · Two incidental findings, recorded because they were found here

**A RED ledger row with no scheduling home.** `data/gate-ledger.json` carries five
expected-red rows, each with a metric, an owner and a `review_by`. Reading
`docs/BUILD-PLAN.md` §16 in full as it stood before this audit, **Gate 6D
appeared in no phase** — manufacturing and refold were absent from P0–P6
entirely. It is the fifth and most recently measured row, its owner is
`chief-architect`, and `navalai/unroll.py:84-108` already localises its two live
mechanisms to `geometry.station_geometry`. §0's law is that no work item may
exist only in prose; a work item existing only in the *ledger*, with no plan
slot, is the same law read from the other side. Filed as §16 P2-5.

**A stale claim that a commit had already refuted.** §16 P3 and §11.5 both said
free sinkage and trim "needs `rigidBodyMotion` — code, not compute". Commit
`7b8f628` (2026-08-12, HEAD−1) measured that the code has existed for some time —
`cfd/case.DYNAMIC_MESH`, `POINT_DISPLACEMENT`, `sixdof_properties`,
`motion_from_geometry`, `make_case.py --free-motion --kg`, three suites
exercising `free_motion` — and that the real blocker was **one number**: KCS's
published `KG = 0.2303 m` lived only inside a comment, and the VCB fallback gives
0.187 m, **19 % low**, which is the lever that sets trim under tow. That commit
sourced the constant and did not correct the documents. `docs/BUILD-PLAN.md`
§11.5 and §16 are corrected. **`CLAUDE.md` still carries the old phrasing in two
places** (its "next experiment" paragraph and its numbered CFD list) and is
flagged rather than edited, because that file is read first by every session and
a correction to it belongs to its owner.

**A transient RED that does not reproduce.** During this audit
`python -m navalai.gates` exited 1 with Gate 0G (1 failed, 29 passed) and Gate 1
(1 failed, 24 passed), neither of which has a ledger entry — by the ledger's own
rule, a NEW break. Both suites were re-run individually afterwards and **both
passed** (`tests/test_gate_integrity.py` 30 passed; `tests/test_phase1.py` 26
passed — note 26, against the 25 implied by the failing run, so a test landed
between them). The ladder was run while the 74-hull campaign held the CPU **and**
while another session had uncommitted work in eight modules. **This audit does
not attribute the failure**, and records it only so that a later reader does not
mistake a clean re-run for the absence of an observation. Re-run
`python -m navalai.gates` on a quiet tree.

## 5 · What this audit could not verify

- **Test outcomes.** Nothing in the suite was re-run beyond the numerics reported
  above; every "MEASURED" attributed to a docstring is the authors' measurement,
  cross-checked for internal consistency across files but not reproduced.
- **The running campaign's result.** `runs/g2u_n74` held 43 of 74 hull
  directories at 01:07 elapsed when this was written. Nothing here anticipates
  its outcome.
- **Whether the committed `data/exports/hull.step` came from a validated
  design.** The receipt records `n_stations_exported == n_stations_validated == 41`
  and `volume_error_pct = −0.0004`, but it was written by
  `tests/test_stageC.py::test_step_export`, which passes no `ev`, so
  `refuse_unvalidated` is a no-op there. **The face-count measurement is sound;
  the provenance-as-validated-design is not.**
- **Four files under concurrent edit** — `grammar.py`, `hull_ast.py`,
  `surrogate.py`, `latent.py`, plus `energy.py` and `resistance.py` — were read at
  a point in time. Numerics were run against `git archive HEAD`, so they describe
  `68d0854` and not the working tree.
- **`BuildPlan2-FullVessel.md`**, cited by `refdata/ergonomics.py` as the
  transcription source for its 31 `approx` marine-practice values, could not be
  located in the tree. The provenance chain for those values terminates in a
  document this audit did not find.

## 6 · Three things to put in front of the owner

1. **The solar roof does not exist as an object** (§2.5). Solar is
   `deck_area × 0.55 × 0.21 × 4.2`; the coachroof is four declared numbers the
   geometry kernel has never heard of, and its roof contributes **zero m²** to the
   solar model. For a platform whose binding constraint is PV area, this is the
   missing half of the vessel, and it has no gate, no owner and no ledger row.
2. **The mission is decided by a speed the model never integrates over** (§2.1).
   Between 4 and 5 knots the same hull goes from solar-positive to
   solar-negative and its daily range falls 2.6×. The machinery to sweep it
   already exists and is called once.
3. **Do not build the NURBS hull** (§3.1). Both existing paths emit the same
   piecewise-linear surface and agree to 9.67e-07 m; smoothing it moves points up
   to 19 mm off the analytic hull and collapses the chine. What the geometry
   kernel genuinely owes is `C1` continuity at `x_mb` and bounded `dy/dx` at the
   stem — two properties of the existing analytic hull, and the actual cause of
   Gate 6D's refold residual.
