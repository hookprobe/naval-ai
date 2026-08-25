# Propulsion integration — how a drive system becomes part of a hull design
**Research record, 2026-08-25.** Sources are named per finding; measurements
carry their origin. This document exists because the owner asked how motor,
anti-roll and anti-pitch are integrated FROM THE DESIGN STAGE, and because the
repository's own record admits the gap: the held houseboat16 study
(`docs/morphology/pending/houseboat_16m.py.held`) states *"15 kW IS NOT
EXPRESSIBLE — there is no motor-power field anywhere in this codebase."*

## 1. The central finding of the literature: co-design or lose

- **Adjoint hull optimisation with a propulsion surrogate** (arXiv 2602.14907,
  CVAE surrogate for a Voith-Schneider propeller): hulls optimised WITHOUT the
  propulsion system in the loop come out inferior; coupling the two yields
  **>8% resistance reduction**. The propeller changes the stern pressure field
  the hull is being optimised in — sequential design leaves that on the table.
- **Integrated electric propulsion + hull, coupled transient model**
  (`downloads/hull-examples/research-gate/jmse-14-00122-v2.pdf` — the paper the
  owner linked; MDPI blocks robots but the PDF is already in the tree):
  controllability diagrams must be built from the COUPLED hull + propulsor +
  electric motor + power-system model; hull and plant "examined independently"
  is named as the traditional error.
- **Hull features around the propulsor are single-digit-percent levers, both
  ways** (`galati-romania.pdf`, JMSE 10:1523, planing hull CFD): tunnel
  configuration, spray rails and whiskers move total drag by **±3–4.5%** and
  shift sinkage and dynamic trim. A tunnel is not free; it is bought.
- **Power prediction is a discipline, not a formula** (Radojčić et al.,
  *Power Prediction Modeling of Conventional High-Speed Craft*, in-tree, 267
  pp): regression models over systematic series (including the Naples warped
  hard-chine series, `SSN.pdf`, already vendored into
  `navalai/morphology_families.py`).
- Note: the second arXiv link the owner sent (2509.21664) is a robotics
  object-placement paper; recorded here as checked and not applicable.

## 2. The quantities a propulsion-integrated design must carry

The chain from motor to hull, with the standard symbols:

    P_electric -> [motor eff] -> P_shaft -> [prop open-water eff x rotative]
    -> P_thrust = T * Va,  where Va = V * (1 - w)

1. **Wake fraction w** — the hull slows the water the prop works in.
   Follows from the AFT BODY SHAPE: a warped flat run gives a clean, thin
   wake (w ~ 0.05–0.15 small craft); a deep skeg or tunnel raises and
   distorts it.
2. **Thrust deduction t** — the working prop lowers pressure on the stern,
   ADDING resistance: R_effective = T(1 − t). Placement decision: distance
   from hull, tunnel roof clearance (≥15% D_prop, `galati` configurations).
3. **Hull efficiency η_H = (1−t)/(1−w)** — the coupling term the CVAE paper
   shows must be inside the optimisation loop, not applied after.
4. **Propeller point**: D_prop vs immersion vs RPM. Small craft electric:
   biggest slow prop that fits = highest η_o. The immersion is a HULL
   dimension — houseboat19 measured 0.33 m at the stern, which is what
   forced the tunnel decision (`data/exports/houseboat19/motor_integration.png`).
5. **Weight & LCG**: motor + battery are the largest movable masses
   (750 kg battery = 5–9% of displacement here). LCG must land on LCB —
   measured this session: GM_L ≈ 54 m makes trim forgiving (0.11°/2 m of
   battery misplacement), so REDUNDANCY/CABLES/BALLAST place the battery,
   not trim.
6. **Roll**: GM sets stiffness, DAMPING sets comfort. At 5–7 kn active fins
   are inert (lift ∝ V²); the working devices are bilge keels on the
   submerged chine, the hard chine itself, and (power-costly) gyros.
7. **Pitch**: excitation is cut by the fine entry + deep forefoot (the axe
   mechanism — Damen, and `stem_depth` in this grammar); damping added by a
   stern foil (Hull Vane on the Van Oossanen FDHF — Super Lauwersmeer
   Project 54) which also recovers thrust; running trim set by
   interceptors/tabs.
8. **Transom immersion vs speed**: Fn_transom = V/√(g·h_transom) ≥ ~2.5 for
   clean ventilation. MEASURED houseboat19: 1.42 @ 5 kn, 1.99 @ 7 kn — the
   stern drags a dead-water eddy at every governed speed. This is a DESIGN
   input (rocker/stern rise), not an outfitting detail.

## 3. What NavalAI carries today (audited 2026-08-25)

| capability | state | where |
|---|---|---|
| propulsion power demand | DERIVED from resistance | `energy.EnergyReport.prop_power_w` |
| motor POWER (installed kW) | **ABSENT** — nothing checks deliverability | `EnergySpec` has only efficiencies |
| prop diameter / immersion / tunnel | **ABSENT** from genome and checks | — |
| wake fraction / thrust deduction / η_H | **ABSENT** (prop_efficiency 0.55 lumps everything) | `energy.py:25` |
| weight placement / LCG | EXISTS — positioned truth | `weights.MassItem`, `energy.weight_items`, `dynamics.inertia` |
| heave seakeeping | EXISTS (L2 Capytaine RAO) | `seakeeping.heave_rao` |
| slam pressure by deadrise | EXISTS (Wagner) | `seakeeping.wagner_impact_cp` |
| added resistance in waves | EXISTS (STAWAVE-1) | `seakeeping.added_resistance_stawave1` |
| roll damping / bilge keels | **ABSENT** (GM only — stiffness without damping) | — |
| pitch RAO / gyradius check | PARTIAL (inertia exists; no pitch response) | `dynamics.inertia` |
| transom ventilation check | **ABSENT** | — |
| governed energy plan | EXISTS — solar fraction floor refused 6 kn for houseboat19 | `policy_energy` |

## 4. The upgrade list — status as of 2026-08-25 (same day)

The owner then made the scope a product definition, twice: "all boats will
have motors, electric motors and solar panels ... naval-ai only designs
boats with motors." Implemented accordingly in `navalai/propulsion.py`,
gated by `tests/test_propulsion.py` (Gate PROP):

1. **DONE — `EnergySpec.motor_kw` (default 15 kW, the original brief) and a
   `motor_power` row** in `CONSTRAINT_NAMES` (grown 8 → 10): cruise demand
   must fit the continuous rating (`MOTOR_CONTINUOUS_FRACTION`).
2. **DONE (v1) — `prop_space` row**: thrust → minimum disc at
   `PROP_DISC_LOADING_MAX_PA`, against the room the stern offers
   (immersion + tunnel recess + below-keel hang). Calibration incident,
   recorded in `max_prop_diameter_m`: the first version omitted the
   below-keel hang and refused the kit reference hull — a boat every yard
   builds daily. The η_o regression replacing the flat 0.55 remains OPEN.
3. **PARTIAL — transom Froude** is measured and reported
   (`PropulsionReport.transom_fn` vs `TRANSOM_FN_CLEAN`), deliberately NOT
   a row: an immersed transom at displacement speed is a costed choice,
   not an invalid design.
4. **PARTIAL — roll**: bilge-keel real estate measured
   (`wetted_chine_span_frac` vs `BILGE_KEEL_MIN_SPAN_FRAC`); a damping
   COEFFICIENT band remains OPEN.
5. **PARTIAL — pitch**: entry angle + axe forefoot drop reported
   (`pitch_entry_report`); stern-foil as an arrangement item remains OPEN.
6. OPEN — the CVAE lesson proper: propulsor-aware stern optimisation, an
   actuator-disc term in the L2/L3 tiers.

Motor MASS stays inside the outfit bucket (55 kg/m) for now: a dedicated
MassItem at 3 kg/kW (`MOTOR_KG_PER_KW`) would move every floated state by
~0.5% and belongs in a deliberate re-baselining, not a side effect.

## 5. Fact-check of the end-to-end claim

The pipeline user → mission → policy → genome → ladder → arrangement is real
and demonstrated this session (houseboat19: `policy_legal`/`policy_dna`/
`policy_energy` rows live, the energy row REFUSING the 6 kn plan). What it
does NOT yet do is items 1–5 above: today a hull arrives at `arrangement`
with the motor unplaced, the prop unsized, roll damping unmodelled and the
transom unchecked — those are exactly the defects the owner spotted by eye
on houseboat19 ("looks ok for a paddle boat"). The eye found what the
pipeline does not yet measure; this document is the plan to close that.
