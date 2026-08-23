# A 16 m x 4 m electric liveaboard, and the eleven things it broke

**Measured 2026-08-23.** Driver: `scripts/houseboat_16m.py`.
Artefacts: `data/exports/houseboat16/{houseboat16.stl,report.json}`.

This is a MEASUREMENT RECORD, in the sense `CLAUDE.md` gives the word: it holds
what was measured and what was refuted, and it carries no schedule and no
status. The ordered work list lives in `docs/BUILD-PLAN.md` §16; the live gap
state comes from `python scripts/reconcile_gaps.py`. Nothing here is a gate
verdict — `data/gate-ledger.json` owns those.

## 0. Why this exercise existed

A brief arrived in prose: *16 m x 4 m x 3 m, 3 tonne displacement, 100 kWh
battery, 15 kW motor, 7-12 knots, full liveaboard accommodation — living room,
terrace, bathroom, kitchen.* It is an ordinary customer sentence and it is
outside every SKU this repository has built. That made it a good probe: it
exercises the mission front end, the grammar, the ladder, the arrangement
grammar, the rules tier and the exporter in one pass, at a size and a hull form
none of them were tuned for.

The hull was produced and it validates. **The interesting output is not the
hull — it is the list of things that had to be worked around to get it.**

## 1. What the brief asked for, and what is true

| asked | measured | verdict |
|---|---|---|
| 16.0 m LOA | LWL 15.2 m; grammar box is (2.5, 24.0) m | **fine** |
| 4.0 m beam | L/B 3.80 against a band of (2.2, 8.5) | **fine** |
| 3.0 m height | see §2 — it is not a hull dimension | **misread by construction** |
| 3.0 t displacement | B/T 18.47 against a ceiling of 12.0 | **REFUSED at L0 and L1** |
| 100 kWh battery | 750 kg at `energy.BATT_KG_PER_KWH` = 7.5 | fine, and see §3 |
| 15 kW motor | not expressible anywhere in the codebase | **DEFECT, §3** |
| 7 knots | 9.0 kW electrical; 7.78 kn available on 15 kW | **fine, with 40% headroom** |
| 12 knots | Fn 0.506, above `FN_MICHELL_MAX` 0.45 | **outside the model, §4** |

The delivered design, floated at 14 000 kg on fresh water:

    draft 0.496 m   B/T 8.06   Cb 0.464   Cp 0.650   Awp 35.9 m2
    GM 1.270 m (floor 0.35, cat D)        trim -0.044 deg
    freeboard_min 1.048 m                 ply 15 mm
    L0 grammar gate  ok      L1 ladder ok, 0 violations
    rules tier       7 of 7 pass          L0-A arrangement ok
    certification    MARGINAL             STL watertight, 15 856 tris, 0 open edges

MARGINAL for two named reasons, both left standing rather than tuned away:
`constraint margin thin: ['rules']`, and `delivered Cp 0.650 misses the mission
target 0.573 beyond tolerance` (see §9).

## 2. The 3 m is not a hull dimension, and the tree cannot hold it

`grammar.PARAMS` defines `D` as *"depth, keel to sheer AT THE MAX-AREA
STATION"*. The brief's 3 m is overall height — hull plus deckhouse. Setting
`D = 3.0` would draw a 16 m hull with a 3 m deep canoe body and no cabin, and
it happens to sit exactly on the gene ceiling, so it would pass silently.

`parse_mission._DENY_LENGTH` already refuses to read *"3 m height"* as a
length, which is right. But **nothing then holds the number.** The parser
appends the note *"a vertical clearance was stated and NOTHING checks it"* and
drops it. For an inland boat this is the wrong quantity to drop: air draft is
what decides which bridges a canal boat fits under, and it is frequently the
binding constraint on the whole design.

Modelled here as hull `D` 1.55 m + a 1.45 m `arrangement.Trunk`. That split is
this script's assumption, not the product's.

## 3. `EnergySpec` has no motor. Nothing checks the boat can reach its speed.

`EnergySpec` carries `motor_efficiency = 0.92` and **no rated power field.** A
grep across the package for `motor_kw|rated_power` returns nothing. So:

- the brief's 15 kW is silently discarded on every path;
- no constraint row, no rule and no badge asks whether the installed power
  reaches `mission.cruise_speed_kn`;
- a design can be validated, certified ACCEPT and exported with a motor that
  cannot move it.

This exercise had to check it from OUTSIDE the ladder, against
`EnergyReport.prop_power_w`, in `houseboat_16m.power_at`. That is the wrong
place for it. Measured on the delivered hull:

    5.0 kn   Fn 0.211     3.1 kW     within 15 kW
    7.0 kn   Fn 0.295     9.0 kW     within 15 kW
    9.0 kn   Fn 0.379    35.3 kW     OVER
   12.0 kn   Fn 0.506    92.9 kW     OVER, and outside the model

Max speed on the installed 15 kW: **7.78 kn.**

## 4. 12 knots is outside the resistance model, not merely expensive

`resistance.FN_MICHELL_MAX` is 0.45, which at LWL 15.2 m is **10.68 kn**. Above
it `ResistanceResult.valid` goes False, the badge degrades to `L1-INVALID`
(which `tier_rank` ranks BELOW L0) and the Wh/NM sigma widens to 100% of the
answer. The displacement hull speed here is 9.4 kn.

This is correct behaviour and it is well signposted. It is recorded because the
PRODUCT has no answer for a customer who asks for 12 knots: there is no
semi-displacement or planing model behind the refusal, and `formlib` marks the
planing families `Expressible.NO`.

## 5. DEFECT — prose that says "river" is exactly what stops the river rules

`evaluate` consults ES-TRIN when `mission.waters` contains one of
`river | canal | lake | inland` (the C-23 wire). But `parse_mission` writes the
resolved design CATEGORY LETTER into `waters`. Measured:

    parse_mission("16 m liveaboard houseboat, inland river and canal cruising")
        -> waters = "D"     ES-TRIN fires: False
    parse_mission("10 m Danube river liveaboard, 2 crew")
        -> waters = "D"     ES-TRIN fires: False

The default `MissionSpec.waters` is `"river+coastal"`, which DOES fire. So the
inland rules run for a mission nobody described, and stop running the moment a
user says the word "river". **The wire is dead on the prose path, which is the
product's front door.** This exercise set `waters="river+canal+inland"`
structurally to reach the checkers at all.

## 6. DEFECT — manning is never parsed, so the liveaboard bars never select

    parse_mission("16 m liveaboard houseboat")  -> Manning.CREWED
    parse_mission("uncrewed survey 8 m")        -> Manning.CREWED

`Manning` is AXIS 2 — *"who is aboard, and therefore WHICH RULE SET APPLIES"*.
`rules/iso12217.py` branches on `manning != "liveaboard"`, and UNCREWED is
supposed to take a craft outside the RCD entirely. Neither is reachable from
prose. Set structurally here.

## 7. DEFECT — `design_kit.py --ungoverned` raises NameError

`box` is bound only inside the `else` branch at `scripts/design_kit.py:350`,
and is passed to `_refine(...)` unconditionally at :469. `--ungoverned` sets
`policy = None`, takes the `if` branch, and any run that reaches stage 3 —
which the module docstring says is the EXPECTED outcome for an ungoverned run —
dies with `NameError: name 'box' is not defined` instead of the intended
refusal. Not exercised here (this exercise did not use `design_kit.py`), but
found while tracing it.

## 8. There is no constitution for a boat over 12 m

`policy.reference_policy()` compiles KIT_LINE_V3, whose `max_hull_length_m` is
**11.9 m**; for category C the RCD Art. 20 Module A break also pins LWL high to
just under 12.0 m. A 16 m hull is refused before any physics runs, for a
COMMERCIAL reason.

That is the constitution behaving correctly. The gap is that **it is the only
one there is**, so every vessel between 12 m and the grammar's 24 m ceiling can
only be designed UNGOVERNED — which is what this exercise did, and why its
output is an engineering result and explicitly not a compliance verdict.

## 9. The grammar cannot express a barge, and a houseboat is a barge

This is the deepest finding and the most work to fix.

`formlib.pontoon` — the obvious houseboat form — is `Candidacy.EXCLUDED` and
`Expressible.NO`. The only whole-hull family the grammar builds is
`hard_chine_displacement`, itself marked EXCLUDED on the honest grounds that
*"it is the ONLY form the current grammar can build"*. A real houseboat carries
near-full beam over near-full length. This one cannot:

- **The SAC kernel refuses parallel middle body at high Cp.** At Cp 0.70,
  x_mb 0.52, l_pmb 0.55 it raises outright — *"LCB -1.000 %LWL unreachable
  (bracket -3.032 .. -2.850 %LWL)"*. Of a 3x3x3x3 sweep over
  (Cp, x_mb, l_pmb, lcb), **9 of 81 combinations built**, and every one had
  l_pmb 0.30.
- **A fine bow and a shallow draft are mutually exclusive.** At beta_bow 24 deg
  and forefoot 0.30 the section solver refused every draft below 0.60 m —
  *"section: area 0.9853 m2 unreachable at x = 11.400 m (draft 0.446 m)"*.
  Dropping to 10 deg / 0.10 opened the whole 0.35-0.55 m band.
- **The result still tapers hard.** The delivered hull carries 2.00 m
  half-breadth amidships and 0.67-0.72 m at the ends, so the deckhouse could
  only be 8.4 m of the 15.2 m waterline, and the cabin half-width came out
  **0.943 m** once the ISO 15085 side deck was paid for. That is a 1.89 m wide
  saloon on a 4.0 m boat.

**Consequence for the accommodation.** The brief's living room, terrace,
bathroom and kitchen all fit, but only ONE double cabin does:
`min_dims_m(Function.BERTH)` sets a 1.98 m floor on the longer plan dimension,
and two berths plus head, galley and saloon do not fit in 8.4 m. Delivered:

    machinery.aft  2.60 x 1.38 x 1.10 m      berth.aft   2.20 x 1.77 x 2.05 m
    head           1.77 x 1.40 x 2.05 m      galley      1.77 x 1.60 x 2.05 m
    saloon         3.20 x 1.77 x 2.05 m      stowage.fwd 1.40 x 0.64 x 1.20 m
    interior 68.2 m3 (35.4 used)             deck 38.8 m2

**A related measurement worth keeping.** A 10-point Cp sweep at FIXED 14 t, each
member re-solved for its own draft:

    Cp     T m    kW @ 7 kn   max kn on 15 kW   interior m3
    0.580  0.539     14.5          7.05             64.4
    0.630  0.507      9.2          7.66             68.1
    0.650  0.496      9.0          7.78             69.6   <- chosen
    0.700  0.471     10.6          7.79             73.6

The minimum is flat across 0.64-0.66. Taking `l_pmb` from 0.30 to 0.0 was worth
MORE than the entire Cp sweep — at Cp 0.70 it took 7 kn from 15.3 kW to
10.6 kW. **This does not refute `limits.PRISMATIC_BY_FROUDE`** (0.573 at
Fn 0.295): that table holds DIMENSIONS fixed while this sweep holds
DISPLACEMENT fixed, so a higher Cp here buys a shallower draft and the
wetted-area saving is what pays. `certify` still reports the miss, and the
report is left standing.

## 10. Smaller gaps, recorded

- **No beam input.** `MissionSpec` has `lwl_hint_m` and no beam counterpart, so
  "4 m beam" cannot be asked for; beam is an optimizer output. The string
  `"beam"` appears in `mission.py` only in `_DENY_LENGTH`, where it
  DISQUALIFIES a match.
- **The terrace has no dimensional bar.** `deck_min_width_m` returns `None` for
  `AFTDECK` and `FOREDECK` — no source in this tree holds a width floor for
  open deck — so the terrace is checked for overlap and plan containment and
  nothing else. There is also no `Function` for outdoor living space; it is a
  deck zone or it is nothing.
- **`arrangement` is not wired into `evaluate`.** The caller must pass
  `extra_mass_items=supersede_outfit(...)` by hand, and forgetting
  `supersede_outfit` double-counts roughly half a tonne against
  `energy.OUTFIT_KG_PER_M`.
- **Superstructure is not a modelled mass or a windage area.** `Trunk` declares
  a volume; its mass and its lateral area do not automatically reach the weight
  model or `WindageSpec`. On a 16 x 4 x 3 m houseboat the deckhouse is both the
  largest single windage area and a significant VCG contributor.
- **`reference_layout()` cannot be reused above a certain bluffness** — it
  raises on a hull too full forward to carry its V-berth, which is every barge.
  A second reference layout is owed.

## 11. What to fix, in the order it would pay

1. **`parse_mission` must not overwrite `waters` with the category** (§5). One
   defect, dead rules tier, prose path only. Cheapest fix with the largest
   correctness gain, and it needs a test that asserts ES-TRIN actually fires
   for a mission whose text says "river".
2. **Parse manning** (§6), for the same reason.
3. **Give `EnergySpec` a rated motor power, and add a constraint row that the
   installed power reaches `cruise_speed_kn`** (§3). Today a boat that cannot
   move can be certified.
4. **Carry air draft** (§2) — for inland craft it is often the binding
   dimension, and it is currently parsed, noted and discarded.
5. **Fix `design_kit.py --ungoverned`** (§7). One line.
6. **Superstructure as mass + windage** (§10).
7. **A constitution for 12-24 m** (§8), or an explicit refusal that says which
   one to write.
8. **A barge/pontoon form the grammar can actually build** (§9). The largest
   piece of work here, and the one that decides whether this product can answer
   a houseboat brief at all rather than approximating one with a chined
   displacement hull.

## Reproducing

    source ~/.venvs/naval/bin/activate
    python scripts/houseboat_16m.py --out data/exports/houseboat16
    python -m pytest tests/test_houseboat_16m.py -q

`report.json` carries every number above, including the constraint vector, the
rules findings and the STL sha256, so nothing in this document has to be taken
on trust.
