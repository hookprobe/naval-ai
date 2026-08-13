# HULL-FORM RULES — what the drawings ask for, and what this code can say

Research record. Derived 2026-08-13 from the annotated schematics now in
`downloads/hull-examples/`, read against a clean tree extracted with
`git archive HEAD` because the working tree was mid-rewrite on both passes.

**Two passes, and the second one is why some numbers here changed.** R1–R19 came
from five sheets. Seven more were then read — 000, 004, 005, 006, 007, 008, 009
— giving R20–R27, three further drawing errors, and corrections to two counts
the first pass had estimated rather than tallied (§"the drawings are not
trustworthy", errors 2 and 6). Where the two passes disagree, the tallied figure
wins and the superseded one is named.

**This document carries no status.** Status is `python -m navalai.gates` and
`python scripts/reconcile_gaps.py`. What is here is a rule set, a verdict per
rule on whether the code can *express* it and whether it *measures* it, and the
list of things the current parametrisation cannot say at all.

Every distance-from-the-batch number below is reproduced by
`python scripts/hull_form_audit.py` — run it rather than trusting this prose.
That script is the only home of those numbers; this file quotes them and names
the script, per the one-source rule.

## Sources, and what they are worth

**THE SHEETS MOVED, AND SIX MORE ARRIVED.** Everything above R20 was derived
from five sheets then at `downloads/hull-example-*.png`; all twelve now live
under `downloads/hull-examples/`. **The paths in this table are the current
ones.** A citation is only as good as its path, so
`scripts/hull_form_audit.py:check_drawings_on_disk()` resolves every sheet named
here and REFUSES rather than warning — run it before trusting any row.

| file | what it carries | rules |
|---|---|---|
| `downloads/hull-examples/hull-example-000.png` | "NAVALAI – HULL TYPE REFERENCE LIBRARY". ~40 forms in 4 groups each with a knot band; the **only dimensioned table in the set**; a 6-section midship strip; a "common hull parameters (for model training)" list | R26, R27 |
| `downloads/hull-examples/hull-example-001.png` | symmetric catamaran, trimaran, planing. `L/B_h > 12`, wet-deck clearance, tunnel arch, cross-structure, asymmetric-demihull option | R1–R4, R16, R17 |
| `downloads/hull-examples/hull-example-002.png` | axe-bow wave-piercer, SWATH. Zero flare volume, reduced pitching axis, slender entrance, minimised waterplane, ride-control fins | R9–R11 |
| `downloads/hull-examples/hull-example-003.png` | classic displacement, semi-displacement, planing. Fine entry, round bilge, hard chines aft, chine flat, lifting strakes, LCB callouts | R6–R8, R13, R18 |
| `downloads/hull-examples/hull-example-004.png` | "Solar-Electric Displacement Cruiser" (a MONOHULL). Fine entrance `< 12 deg`, round-bilge section, parallel midbody, and three named sections — U bow / semi-circular midship / low-volume stern | R20, R21 |
| `downloads/hull-examples/hull-example-005.png` | "Solar-Electric Slender Catamaran Cruiser". Wet-deck platform sized for PV, tunnel clearance, `s/L` "tuned", transom stern, wave-interference inset | R21–R23 |
| `downloads/hull-examples/hull-example-006.png` | "Solar-Electric Stabilized Trimaran Cruiser". Extremely slender main hull, small amas, aka boom, **aft main-hull volume for the propulsion system** | R24 |
| `downloads/hull-examples/hull-example-007.png` | panga/modified dory, stepped planing (single step), cathedral/tri-hedral tunnel. Rocker, ventilated step cavity, separation edge, aerodynamic lift tunnel | R18, R25 |
| `downloads/hull-examples/hull-example-008.png` | "12m × 4m High-Efficiency Solar Catamaran". **Dimensioned**: `L/B_h 15.3`, `B_oa 4.0 m`, clearance `0.65 m`, entry `< 10 deg`, PV 35 m² at 6–8 kWp | R22, R23 |
| `downloads/hull-examples/hull-example-009.png` | "16m × 4.5m Long-Range Solar Catamaran". **Dimensioned**: `L/B_h 17.8`, `B_oa 4.5 m`, clearance `0.8 m`, entry `< 9 deg`, PV 55 m² at 10–14 kWp, deep immersed transom | R15, R22, R23 |
| `downloads/hull-examples/hull-designs.png` | "HULL DESIGN EXPLORER", ~40-form taxonomy across 6 families, one line of intent each | R26 |
| `downloads/hull-examples/hull-designs-gemini.png` | 14 forms, profile + half-breadth + waterline. 24 deg / 18 deg deadrise, variable deadrise, twin steps, wave-cancellation bulb, vertical stem, inward-facing flat sides, high cross-structure clearance | R10, R12, R16 |

The machine-readable half of this document is **`navalai/formlib.py`** — 31 form
families and 14 features, each with its regime, its proportion bands with
provenance, and a candidacy verdict against this mission. This file is the
argument; that file is the data. Neither restates the other's numbers: where a
figure is computable it lives in `scripts/hull_form_audit.py`, which both quote.

`downloads/catamaran-hull-design-motor-recess.png` — **named in the brief as the
actual target and NOT PRESENT ON DISK,** then or now. So the target geometry
used throughout this document is the one stated in prose — demihull
`L = 12 m, B = 0.8 m, T = 0.6 m` — and **nothing here is derived from the motor
recess**, which no one has seen. The nearest thing in the set arrived with the
new sheets and is the OPPOSITE shape: 006 labels an "AFT MAIN HULL VOLUME:
SUPPORTS PROPULSION SYSTEM", i.e. buoyancy ADDED aft to carry the drive, not a
cavity cut into the hull for it. A recess is still undrawn and is still a
topology question; see §3 item 5 and §5.

### The drawings are not trustworthy line-by-line, and SIX errors matter

Three were recorded on the first pass. Reading the other seven sheets found
three more, and **corrected the count in the first one**.

They are generated illustrations, not a naval architect's dimensioned drawing.
Recording the errors so no one downstream inherits them as rules:

1. **`L/B_h > 12` on 001 labels two dimensions that are not `L/B_h`.** The
   vertical arrow spans the demihull's depth (wet-deck underside to keel); the
   horizontal arrow spans demihull-centreline to demihull-centreline, i.e. the
   hull SEPARATION. Neither is a length-over-beam. The *rule* is real and
   standard; the *arrows* point at two other quantities, one of which
   (separation) has its own governing ratio and its own number. Read the rule,
   not the leader lines.
2. **"High Cp, Low Fn" is backwards, and 002 contradicts itself in one text
   block.** Prismatic coefficient RISES with Froude number — fine ends at low
   speed, full ends at high speed. 003 puts "High Cp, Low Fn" on the classic
   displacement trawler, and 002 puts the same string on the axe bow while the
   line beneath it reads "Very Low prismatic coefficient entry". The rule this
   document adopts (R5) is the monotone one; the drawing's label is discarded.

   **COUNTED 2026-08-13 across all twelve sheets: the block appears on SEVEN,
   not on the two recorded above** — 001, 002, 003, 005, 006, 008 and 009. It
   is one block pasted seven times, and the tell is that every copy also
   duplicates its last word ("Wave-making dominant dominant"). Sheets 004, 007,
   000 and the two taxonomies do not carry it. The correction matters because
   five of the seven are the SOLAR sheets — the drawings closest to this
   mission are the ones carrying the reversed rule.
3. **002's SWATH block reads "Low L/B, High Fn, Dynamic lift dominant"
   directly under its own "Submerged Buoyancy" heading.** A SWATH is a
   displacement form whose whole point is that buoyancy, not dynamic lift,
   carries it. The block is copy-pasted from the planing panel on 001.

   **The same block appears in three more places, and they are not equally
   wrong.** On 006 it sits under "FINE MAIN HULL ENTRY" and contradicts that
   sheet's own "Fn 0.2 – 0.35" title block — false. On 007 it heads the
   cathedral/tunnel hull, which really does plane — duplicated, but TRUE there.
   Its two legitimate homes are the planing panels on 001 and 003. Say which:
   "copy-pasted" and "wrong" are different findings and only the first two
   placements are refuted here.
4. **The resistance-vs-speed insets on 004 and 008 are STRAIGHT LINES** from
   4 to 20 knots. A displacement hull's `R(V)` has a pronounced wave-making
   hump — it is the entire physics the rest of both sheets is about, and the
   hump is why `Fn` appears in every other label on them. A straight line
   through 20 knots also implies no regime change at all. Read the labels;
   do not read the charts.
5. **009's "POWER BUDGET & RANGE FORECAST" has the wrong x-axis.** The axis is
   labelled "PROPULSION DEMAND (kW)" and its ticks run 0, 3, 6 … 24 under a
   bell curve: those are HOURS, and the curve is a day of solar generation.
   Two further inconsistencies with 009's own labels — the bell peaks near
   17 kW against the "10–14 kWp" array named on the same sheet, and it floors
   at about 4 kW at both ends of the day, which no solar array does. Nothing in
   this document or in `formlib.py` takes a power figure from this chart.
6. **The taxonomy sheets list BOW TREATMENTS as peers of whole-hull forms.**
   Counted on 000 and `hull-designs.png`: INVERTED BOW, TULIP BOW, TULIP HULL,
   X-BOW, CUTTER BOW, CAT'S PAW BOW, REVERSE BOW and MORTEK STYLE — eight
   panels for one idea (a fine, low-flare, vertical-or-reversed stem), sitting
   in the same lists as "catamaran" and "SWATH". `hull-designs.png` also files
   "AERODYNAMIC HULL — low drag superstructure" as a hull form, though it
   describes structure entirely above the waterline. This is why
   `formlib.py` splits `FormFamily` from `Feature`: a flat list of forty makes
   a bow look like an alternative to a topology.

Minor: `hull-designs-gemini.png` announces "7 designs" per section and then
repeats panels 4 and 12, so its numbering is not a key; `F_D` is used for the
Froude number, which is normally `Fn`; its own footer asks for "variations in
L/B ratio and block coefficient (Cb)", which are the two quantities this
grammar can least vary (see R26). 004 prints "Fn 0.2 - 0.35" while 005, 006,
008 and 009 all print "**Fn 2 - 0.35**", dropping the "0."; the band adopted
throughout is the one 004 spells out. 001's trimaran panel has no drawing of
its own — its four leader lines land on the planing hull below it.

---

## 0. The mission filter — most of what is drawn is not a candidate

The target is a **solar-electric displacement catamaran, Fn 0.2–0.3**, demihull
12 × 0.8 × 0.6 m. At L = 12 m that is U = 2.17–3.25 m/s (4.2–6.3 kn).

A rule set that lets a planing rule reach a displacement hull is worse than no
rule set, so the exclusions are stated before the rules:

| drawn form | verdict for this mission | why |
|---|---|---|
| Round-bilge / slender displacement demihull | **THE TARGET** | Fn 0.2–0.3 is squarely wave-making-dominant displacement |
| Wave-piercing catamaran | **adjacent, borrow selectively** | its slenderness and clearance rules transfer; its bow does not pay below Fn ~0.4 |
| Symmetric catamaran | **THE TOPOLOGY** | two identical demihulls is what the mission is |
| Asymmetric demihull | **open, low priority** | drawn as an option on 001; the literature is mixed and it costs a new topology (§4.10) |
| Axe bow / X-bow / inverted bow | **NO** | a seakeeping trade for a fast offshore ship; at Fn 0.2–0.3 in the intended service it buys nothing and costs reserve buoyancy forward |
| Deep-V / modified-V planing (24 deg, 18 deg) | **NO** | dynamic lift is irrelevant below Fn ~0.5. Applying a 24 deg deadrise here would be the exact error this section exists to prevent |
| Stepped hull, ventilation tunnels | **NO** | steps work by ventilating a planing surface; there is no planing surface |
| Lifting strakes, chine flat, pad hull, wedge | **NO** | all planing-lift devices |
| SWATH, semi-submersible | **NO** | minimised waterplane buys motions at the cost of a large wetted surface and near-zero reserve stability, and a solar boat's constraint is deck area and drag, not motions |
| Air cushion | **NO** | continuous lift power on a solar energy budget |
| Foil-assisted | **NO** | foils do not pay their drag below roughly Fn 0.5 |
| Bulbous bow / wave-cancellation bulb | **NO** | bulbs pay on large, full, low-Fn ships. On a 12 m demihull at L/B 15 the bulb's own wave is the same order as the hull's, and `holtrop.particulars_from_floated` already hardcodes the bulb to zero for craft this size |
| Trimaran, quadrimaran | **NO** for this SKU | not the stated topology. 006's argument is the strongest hydrodynamic case in the set and is recorded as R24 anyway, because it explains why a demihull may be slender at all |
| Transom stern | **partially yes** | already expressible via `r_transom`; but see R19, transom immersion drag is unmodelled |
| Panga / modified dory | **NO** | 007 sells it on "High Payload-to-Power Ratio", which is a different objective from low power at fixed payload, and draws the full bow and rocker that go with it |
| Cathedral / tri-hedral tunnel | **NO** | its tunnel lift is AERODYNAMIC and needs planing speed; at 6 kn it is a wetted cavity |
| Pontoon | **NO**, and it is the closest call here | the deck-area argument is genuinely attractive for solar. The hydrodynamics refuse it: a constant-section tube has no fine entry and no pressure recovery, so drag per tonne is highest exactly where the power budget is smallest |
| Multi-chine section | **the one open alternative** | a buildable approximation to the round bilge, reachable by the SAME grammar change (more section points) rather than by a new topology. NOTE 000 draws "wedge / multi-chine" as one panel: the wedge half is a planing device and is excluded with the rest |

The same verdict, per family and with the reason attached to the row, is
machine-readable in `navalai/formlib.py` (`Candidacy`); 24 of its 31 families
are `EXCLUDED`. `formlib.proposable()` is the function a sampler should call.

Everything below is tagged with the family it governs. **D** displacement,
**SD** semi-displacement, **P** planing, **WP** wave-piercer, **CAT**
catamaran/multihull, **ALL**.

---

## 1. The rule set

Each rule: the number, the family, whether the code can EXPRESS it, whether the
code MEASURES it, and what enforcement would take.

Vocabulary used consistently below:
- **express** = the parameter vector can reach a hull satisfying it.
- **measure** = the quantity appears in `evaluate.CONSTRAINT_NAMES`, a
  `HydroState` field, or an `Evaluation` badge.

---

### R1 — Demihull slenderness `L/B_h > 12` — CAT

**Rule.** Demihull waterline length over demihull waterline beam exceeds 12.
Source: `hull-example-001.png`, restated as "SLENDER HULLS / LOW DRAG HULLS" on
`hull-designs-gemini.png` panels 8 and 10. The target demihull is **L/B = 15.0**
and satisfies it.

**Express: NO — and the refusal is the L0 gate, not the bounds.** This
distinction decides the fix. The parameter box reaches it: `LWL` tops out at
20.0 m and `BWL` bottoms out at 1.2 m (`navalai/grammar.py:23-24`), so the box
admits `L/B` up to 16.67. But `grammar.check` applies
`grammar.L_OVER_B_BAND = (2.2, 8.5)` (`grammar.py:60`, clause at `:131`) and
refuses anything above 8.5. A bound can be widened; a gate clause has to be
re-argued.

**Measure: YES, and it is already a constraint row.**
`evaluate.CONSTRAINT_NAMES` contains `"proportions"`, computed at
`evaluate.py:578,590` from `grammar.proportion_margins(hs.lwl_eff,
hs.b_wl_max, hs.draft)` — the same kernel, re-applied to the FLOATED hull. So
the machinery to enforce a slenderness rule exists in full; it is currently
pointed at a band that excludes the target.

**Distance from the batch (`scripts/hull_form_audit.py --n 200 --seed 0`):**
`L/B` min 2.208, median 3.904, max 8.406. **0 of 200** exceed 12, and that zero
is structural rather than statistical — the sampler rejects the region.

**Enforcement.** Widen `L_OVER_B_BAND`'s ceiling, but **not globally**: 8.5 is a
defensible monohull number and a monohull at L/B 15 is a different craft. The
band has to become family-conditional — the natural home is the policy compiler
(`navalai/policy/`), which already emits a parameter BOX and appended
constraint rows from one source, and whose ratchet rule (a bound may only move
INWARD) means a catamaran constitution widening a monohull band needs an
explicit decision rather than a silent edit.

**Supporting argument, worth stating because it cuts the other way from
intuition:** widening the band moves the production resistance model INTO its
validity window, not out of it. `total_resistance` is Michell thin-ship plus
ITTC-57 (`resistance.py:711-764`), and thin-ship theory is most accurate for
slender hulls. `FN_MICHELL_MAX = 0.45` also comfortably contains Fn 0.2–0.3.

---

### R2 — `B/T` floor of 1.8 refuses the target — CAT (consequence of R1)

**Rule.** Not drawn. Recorded because it independently blocks the target and
would otherwise be discovered after R1 is fixed. The target demihull is
**B/T = 0.8 / 0.6 = 1.333**, against `grammar.B_OVER_T_BAND = (1.8, 12.0)`
(`grammar.py:61`, clause at `:133`).

**Express: NO.** `BWL`'s lower bound of 1.2 m also excludes B = 0.8 m outright.
The target hull therefore fails **three** clauses: `bound[BWL]`, `L/B`, `B/T`.
Verified by `scripts/hull_form_audit.py`, which prints all three.

**Measure: YES** — the same `"proportions"` row as R1.

**Enforcement.** Same shape as R1, same family-conditional argument. A deep,
narrow demihull is the point of a catamaran; a B/T floor is a monohull
form-stability heuristic, and on a catamaran transverse stability comes from
hull SEPARATION, not from demihull beam. Applying a monohull B/T floor to a
demihull is a category error, and it is the second one this document finds
(see also R24).

---

### R3 — Wet-deck clearance ≥ the bow-wave rise — CAT

**Rule.** The cross-structure underside must clear the water surface.
`hull-example-001.png` draws it as a dimension against a wave profile;
`hull-designs-gemini.png` panel 10 restates it as "HIGH CROSS-STRUCTURE
CLEARANCE". The bound already chosen by this project is the steady stagnation
rise `bow_wave_rise(U) = U²/(2g) = Fn²·Lwl/2`.

On the 12 m target (`scripts/hull_form_audit.py`):

| Fn | U | required clearance |
|---|---|---|
| 0.20 | 2.170 m/s | **0.240 m** |
| 0.25 | 2.712 m/s | **0.375 m** |
| 0.30 | 3.254 m/s | **0.540 m** |

**Express: NO.** There is no clearance parameter. `grammar.NAMES` is 15 entries
and none of them is a wet deck; grep for `wet_deck`, `wetdeck`, `tunnel`,
`hull_spacing` across the tree returns **zero hits**.

**Measure: the function exists and is wired to nothing.**
`navalai/resistance.py:561-576` defines `bow_wave_rise`, and `:579-604` defines
`wet_deck_clearance_g(clearance_m, speed) -> bow_wave_rise(speed) - clearance_m`
in metres, positive-when-violated, deliberately the same sign convention as
`evaluate`'s `"freeboard"` row. It has **zero production call sites** — grep
over the tree finds the definition, one string inside its own error message, one
docstring mention, and `tests/test_phase1.py:1052-1084`. Nothing else. It is not
in `CONSTRAINT_NAMES`, not in `Evaluation.g`, not in the NSGA-II G matrix.
(`navalai/cfd/case.py:640-652` discusses a wet-deck instrument for the CFD tier
in prose; it does not call this function, and the two are different questions —
see the reconciliation below.)

**Reconciliation, and it narrows the claim.** The drawing measures clearance to
a WAVE CREST. `bow_wave_rise` covers only the ship's OWN steady bow wave —
`resistance.py:553-558` says so explicitly, and points at seakeeping for the
seaway case. So satisfying this row is necessary and **not** sufficient: a hull
that passes it is not thereby free of wet-deck slamming, which is driven by
relative motion against the incident wave. Nothing computes that relative
motion (see R11).

**Enforcement.** One grammar parameter (`wet_deck_m`, or `wet_deck / BWL`), one
appended row. The row's text is already specified in the commit that added
`bow_wave_rise`; it needs the genome, not new physics. A non-finite clearance
must RAISE rather than pass — a wet deck nobody recorded is exactly the case
the row exists to catch, and scoring an unmeasured height as clear is the
`${VAR:-0}` defect in a safety dimension.

---

### R4 — Hull separation `s/L` sits at a wave-interference optimum — CAT

**Rule.** Drawn on 001 as the horizontal dimension (mislabelled `L/B_h`, see the
preamble). The drawings give no number. The project has already measured one:
at Fn 0.30 on a Wigley demihull, `s/Lwl = 0.4450` is the destructive optimum at
**0.9223** of two independent demihulls, and `s/Lwl = 0.1500` is the
constructive worst at **1.4730**. Those numbers live in the commit that added
`catamaran_interference` and in `tests/test_phase1.py`; they are cited here, not
restated as new.

**Express: NO.** No separation parameter in the genome.

**Measure: NO — and this is the sharpest finding in the document.** The
machinery is complete and disconnected. `resistance.py` carries
`catamaran_interference(k0, thetas, separation)` at `:317`,
`michell_rw(..., separation=)` at `:378`, `michell_rw_separation_sweep` at
`:431`, `free_wave_spectrum` at `:471`, plus the calibration constants
`CATAMARAN_INTERFERENCE_AT_INFINITY = 2.0` and
`CATAMARAN_THETA_QUADRATURE_ERROR = 0.00061`. And the one production call site,
`resistance.py:735`, reads:

    rw = michell_rw(xs, zs - wl, Y, speed, rho)

**with no `separation` argument.** The ladder that is meant to design a
catamaran computes the wave resistance of one isolated demihull. The module
docstring (`resistance.py:14-20`) states this plainly — "nothing in the genome,
the grammar or `total_resistance` has been wired to it yet" — so it is a known
gap, not a hidden one. It is recorded here because R1 and R3 are both pointless
without it: widening the L/B band lets the optimiser build a slender demihull,
and it will then choose a spacing blind to the one effect that makes catamaran
spacing matter.

**Enforcement.** One grammar parameter (`s_over_L`), pass it through
`total_resistance` to `michell_rw`, and the objective already being minimised
(`wh_per_nm`) picks up the interference for free. The unvalidated part is the
physics, not the plumbing: the tests prove the term is SELF-CONSISTENT
(`s → ∞` recovers 2× a demihull), not that it is RIGHT. The Southampton
catamaran series (Molland, Wellicome & Couser 1996) is the anchor named for
this and is not in the tree.

---

### R5 — Cp is set by the Fn regime — ALL

**Rule.** All three drawings tie prismatic coefficient to speed regime rather
than to a fixed band: "wave-making dominant" at low Fn, "Moderate Cp,
transitional Fn", "dynamic lift dominant" at high Fn.

**The drawings' own labels are discarded** — see the preamble, item 2. The rule
adopted is the standard monotone one: **Cp increases with Fn.** For a
displacement hull at **Fn 0.2–0.3 the working band is Cp 0.55–0.65**, and this
number's basis is `'approx'` (design literature, no anchor in this tree). It is
stated as a band to aim at, not a bar to fail on, until an anchor exists. Note
also that slender round-bilge demihulls of the NPL type run higher — near 0.69 —
so a catamaran-specific band is likely wider than the monohull one, and that is
a question for a measurement rather than for this document.

**Express: NO, in the sense that matters — Cp is an EMERGENT OUTPUT.** It is
computed at `hydrostatics.py:161` as `cp = vol / (amax * lwl_eff)` and stored
on `HydroState.cp`. There is no way to ask the grammar for a target Cp; you
change `p_bow`, `p_stern`, `x_mb` and `r_transom` and read off whatever Cp
results.

**Measure: computed, but NOT constrained.** `hs.cp` is read at exactly two
production sites, `evaluate.py:547` and `:548`, both feeding the Holtrop
ENVELOPE check, whose result lands in
`Evaluation.holtrop_envelope_violations` as a receipt string. `evaluate.py:531`
carries the measured batch band as a comment. Cp is not in `CONSTRAINT_NAMES`
and not in the objective vector.

**Enforcement — and this is the cheapest rule in the document.** Cp is already
measured on every evaluation, so enforcement costs **one appended constraint
row** and no geometry work whatsoever:

    "cp_regime": |hs.cp - cp_target(fn)| - cp_tolerance

The design decision it needs is `cp_target(fn)`, i.e. what the band is and
whether it is a bar or a soft objective. `evaluate.py:541-544` records the rule
that governs the choice: a row that is always satisfied is a defect, because it
occupies an NSGA-II dimension for nothing (gap E4 deleted four such rows). So
this row is worth adding only if the batch actually violates it — and the
figures already recorded in `evaluate.py:531` say the batch spans far wider
than any sensible band, so it will fire.

---

### R6 — Fine entry: half-angle of entrance — D, SD, WP

**Rule.** "Fine entry" (003, twice), "Slender Entrance" (002, twice), "FINE
ENTRY" (gemini panel 6). No number is drawn. The literature figure for a fine
displacement entry is **α_e ≈ 7–12 deg**, and below ~10 deg for a wave-piercer.
Basis `'approx'`.

**Express: PARTIALLY, and it is capped by R1.** The mechanism exists —
`p_bow` (`grammar.py:29`, "waterline fullness exponent, forward", bounds
1.2–4.0) controls it through
`w[fwd] = 1.0 - ((x - xm)/(L - xm))**p_bow` at `geometry.py:48`. Small `p_bow`
gives a fine entry, large `p_bow` a blunt one. But α_e is set jointly by beam
and length, so the L/B ceiling of 8.5 puts a floor under it: the batch cannot
reach a fine entry because it cannot reach a slender hull. **The two rules are
one rule.**

**Measure: NO. It is computed nowhere from this project's lines.** `grep -rn
"alpha_e"` over the tree returns **zero hits**. The only entrance angle in the
codebase is `holtrop.half_angle_entrance` (`holtrop.py:303`), which is a
REGRESSION on `(lwl, b, cwp, cp, lcb, lr, volume)` — not a measurement of the
waterline — and its single call site is inside `holtrop.total()`, which has no
production caller (tests only).

**Distance from the batch.** `scripts/hull_form_audit.py` measures α_e off the
actual waterline curve: min **12.339**, median **32.709**, max **62.741** deg;
**0 of 200** land in [7, 12]. The median hull's entry is roughly three times
blunter than the drawn rule.

A definition note, because several are in circulation and they disagree: the
script uses the **chord of the design waterline from the stem to 5% LWL aft**,
not a tangent at the stem. `station_geometry` carries a `w**0.15` sheer taper
whose x-derivative is unbounded at the stem (`geometry.py:102-110` records a
CubicSpline missing the sheer by 94.95 mm for this reason), so a stem tangent
measures the parametrisation's singularity rather than the hull. The brief's
figures (min 10.6 / median 31.6 / max 60.5) sit close to but not on these, which
is what a different chord fraction or sample would do — **the two are not the
same measurement and neither should be quoted as reproducing the other.**

**Enforcement.** Add the α_e instrument first — a `HydroState` field computed
from the waterline offsets, with the chord basis stated in the docstring. It is
a badge before it is a bar, because R1 currently makes the bar unreachable.

---

### R7 — Hard chines AFT, round bilge forward — SD

**Rule.** 003's semi-displacement panel: "Hard chines aft", with the forward
sections drawn round. **The section TYPE varies along the length.**

**Express: NO, structurally.** `Hull.section(i)` returns exactly three points —
keel, chine, sheer — as a literal `(3, 2)` array (`geometry.py:120-128`), and
`y_chine` is defined at every station from 0 to LWL by `geometry.py:47-52`. The
chine can TAPER to zero half-breadth at the stem; it can never begin or end.
Every hull this grammar emits is a hard chine from transom to stem by
construction. The 3-point count is not merely conventional: it is re-hardcoded
in at least five consumers (`geometry.py:142,182,485`, `export.py:28,81-82`), so
this is a rebuild, not a parameter.

**Measure: N/A** — there is no section-type quantity to measure.

**Enforcement.** See §4.2 and §4.3; this is a geometry-kernel change.

---

### R8 — Round bilge, fair lines — D

**Rule.** "Round bilge" (003), "ROUND-BILGE DISPLACEMENT / FAIR LINES / LOW
RESISTANCE AT CRUISE" (gemini panel 4), "ROUND BILGE — Smooth ride"
(hull-designs). **This is the form the mission actually wants**: a
solar-electric displacement demihull at Fn 0.2–0.3 is a round-bilge slender
hull, and every catamaran panel on every drawing shows one.

**Express: NO.** Same 3-point section as R7. `navalai/flywheel.py:187` states
it outright: the grammar's hull "has no bulbous bow, no bilge radius and no
parabolic waterline". A hard chine at Fn 0.2–0.3 on a slender demihull is a
drag penalty with no compensating benefit — chines earn their keep by spray
separation and dynamic lift, neither of which exists at this speed.

**Measure: NO.**

**Enforcement.** §4.2.

---

### R9 — Zero flare volume at the bow — WP

**Rule.** 002, "Zero Flare Volume" on the axe bow. The point is that the
topside carries no reserve buoyancy FORWARD, so the bow pierces rather than
lifts. It is emphatically **not** "zero flare everywhere" — the same hull wants
normal flare amidships and aft for deck area and reserve stability.

**Express: NO, and the reason is a one-character asymmetry in the code.**
`flare` is a single scalar (`grammar.py:35`, −5 to 25 deg) applied identically
at every station. `geometry.py:66`:

    ys = y_chine + (zs - z_chine) * math.tan(math.radians(p["flare"]))

Note `math.tan` on a Python scalar, one line below `np.tan(beta)` on an array.
Deadrise varies along the length; flare cannot. Setting `flare = 0` gives a
wall-sided hull from stem to transom, which is a different (and worse) boat than
the one drawn.

**Measure: NO.** `flare` is an input, not a measured quantity, and there is no
reserve-buoyancy or flare-volume metric anywhere.

**Enforcement — the cheapest structural fix in the document, because the
pattern already exists.** Deadrise is already a three-parameter longitudinal
law: `beta_mid`, `beta_bow`, `beta_len`, blended quadratically over the forward
`beta_len·L` at `geometry.py:54-60`. Flare needs the identical treatment —
`flare_mid`, `flare_bow`, `flare_len` — and it is a copy of a law already
written, tested and understood. Note the one live hazard: `admissibility.py:341,359`
records that negative flare (tumblehome) folds the sheer inboard and is clipped
by `np.maximum(ys, 0.0)`, so a bow-specific negative flare needs that clip
re-examined rather than inherited.

---

### R10 — Vertical stem — WP

**Rule.** gemini panel 7, "VERTICAL STEM".

**Express: YES — and only this.** At `x = LWL` the plan-form multiplier `w`
goes to zero, so `y_chine = 0` and `y_sheer = max(ys,0)·w**0.15 = 0`. The stem
is a vertical line at `y = 0` between `z_keel(L)` and `z_sheer(L)`.

**The inverse is the finding: this grammar cannot make anything BUT a plumb
stem.** `LOA == LWL` by construction. There is no stem rake, no bow overhang,
no counter stern, no clipper bow. So the axe bow's vertical stem is free, while
the classic displacement trawler drawn on 003 — which has an obviously raked
stem and a counter — is inexpressible. Recorded in §4.6.

**Measure: N/A.**

---

### R11 — Reduced pitching / reduced pitching axis — WP, D

**Rule.** 002, "Reduced Pitching Axis"; gemini panel 6, "REDUCED PITCHING";
panel 7, "SUPERIOR SEA-KEEPING". These are statements about longitudinal mass
and buoyancy distribution and about pitch response.

**Express: INDIRECTLY.** The levers exist — `x_mb`, `p_bow`, `p_stern`, `LCB`
via the plan-form, and `dynamics.py:46,49` carries `iyy` and the gyradius
`kyy/LWL`. Nothing lets a designer state a pitch target.

**Measure: NO. There is no pitch anything.** `navalai/seakeeping.py` computes
**heave only** — `heave_coeffs`, `heave_rao` (`:165`), a mesh
`convergence_sweep`, and the Hulme hemisphere validation anchor. Grep confirms
no pitch RAO, no added resistance in waves (`added_resistance`: zero hits), and
no deck wetness or green water (zero hits). No seakeeping quantity is a
constraint row; the L2 tier emits badges only.

**This is also what blocks the honest version of R3.** Wet-deck slamming needs
the relative vertical velocity between the cross-structure and the incident
wave. `seakeeping.py` has the impact model ready — `wagner_impact_cp` (`:357`)
and `slam_pressure` (`:417`), with `slam_pressure_band` (`:453`) bracketing
rather than predicting a point — and `seakeeping.py:14-16,316-318` names the
wet deck as the governing case for a catamaran and defers it. The missing piece
is the motion, not the impact.

**Enforcement.** Pitch RAO in `seakeeping.py`, then relative motion at the
wet-deck station, then `slam_pressure` as a SECOND CALL SITE — never a second
implementation, which is this repository's signature defect.

---

### R12 — Variable deadrise — P, SD

**Rule.** gemini panel 2, "VARIABLE DEADRISE". Deep-V 24 deg, modified-V 18 deg
(gemini panels 1, 2).

**Express: MOSTLY YES — the one drawn feature the parametrisation already
has.** `beta_mid` (0–25 deg), `beta_bow` (2–50 deg), `beta_len` (0.15–0.6 of
LWL), warped quadratically at `geometry.py:54-60`. The 24 deg and 18 deg
figures are both inside `beta_mid`'s range. `grammar.check` enforces
`deadrise.order` (`beta_bow >= beta_mid`, `:135`) and a twist rate
`MAX_PANEL_TWIST_DEG_PER_M = 14.0` (`:70`).

**Three limits worth naming.** The warp is **forward only** — aft of
`L - beta_len·L` deadrise is constant at `beta_mid` all the way to the transom,
so there is no transom deadrise and no aft warp. The blend is fixed quadratic,
not choosable. And `beta_len` is bounded at 0.6, so the warp can never cover
more than 60% of the length.

**Measure: it is an input, so it is exact.** `beta_mid` also feeds
`slam_pressure` as the wedge half-angle.

**Mission note.** 24 deg and 18 deg are **planing** numbers and must not travel
to the target hull. For a displacement demihull the relevant question is bilge
shape (R8), not deadrise magnitude.

---

### R13 — LCB position tracks the regime — ALL

**Rule.** 003 calls out LCB on both the semi-displacement and planing panels
and at visibly different longitudinal positions — LCB moves AFT as speed rises.

**Express: NO as an input** — LCB is emergent, computed at
`hydrostatics.py:130` as `2·∫a·x dx / vol`, with `lcb_pct_lwl` at `:45-55`.

**Measure: YES, and it is already a constraint row.** `evaluate.py:589`:
`"lcb": abs(hs.lcb_pct_lwl) - LCB_BAND_PCT_LWL`, with
`limits.LCB_BAND_PCT_LWL = 3.0` (`limits.py:153`). It also has a policy ratchet
at `policy/compiler.py:200-206`. `limits.py:126-152` is the one home of the
measured batch distribution and the note that the reference hull sits at −6.48%
and is infeasible; those figures are not restated here.

**The gap is that the band is symmetric and speed-blind.** `±3%` about midships
is displacement-hull practice — which happens to be right for this mission — but
it encodes no regime dependence, and it is signed-symmetric where the practice
is not (displacement hulls sit slightly AFT of midships; the acceptable forward
excursion is smaller than the aft one).

**Enforcement.** This is the second-cheapest rule in the document: the row
exists, the quantity is measured, and only the BAR needs to become a function
of Fn and family. No new row, no new instrument, no geometry.

---

### R14 — Fair lines, no abrupt curvature change — ALL

**Rule.** The owner's framing, and the drawings agree: "FAIR LINES"
(gemini panel 4), "smooth ride", "low drag". Water is a medium like air and the
hull must be streamlined in it — fine entry, smooth pressure recovery, no
abrupt curvature change.

**Express: NO.** The surface is two straight segments per section
(`geometry.py:3-5`, lofted linearly at `:321-324`), linear between 41 stations,
and it is **known to be C1-discontinuous at four longitudinal breakpoints** —
`x_mb`, `0.3L`, `0.7L`, and the deadrise-warp start — plus the chine crease and
the stem. The plan-form slope break at `x_mb` is measured: **12.308 deg** on the
reference hull, reported as `xmb_tangent_break_deg`
(`admissibility.py:485-489`).

**Measure: NO — and worse, the one curvature metric deliberately looks away
from exactly these points.** Curvature is computed in two places and both are
manufacturability, not fairness:
- `Hull.min_bend_radius()` (`geometry.py:407-431`) — Frenet curvature on the
  keel and chine, feeding the `"bend_radius"` constraint row against the
  plywood cold-bend limit `80 × thickness`. It bounds how tight a sheet must
  bend, not how fair the surface is.
- `admissibility.stack_over_min_radius` (`:411-444`) — a CFD prism-stack
  screen, and it **excludes the breakpoints**: `smooth &= np.abs(t - bp) > 3.0 *
  (t[1] - t[0])`, with the comment that "at a C1 break a discrete curvature is
  not a radius at all". Correct for its own purpose, and it means the project's
  only curvature instrument is blind to its only curvature defects.

`xmb_tangent_break_deg`, `bow_bluntness_cells` and `max_facet_turn_deg` are all
`Basis.DIAGNOSTIC` — "Reported, does not vote."

Grep for `curvature`, `fairness`, `second_derivative`, `continuity`, `G1`, `G2`
finds no hull fairness metric anywhere.

**Enforcement.** A curvature-continuity metric over the three edge curves plus
the waterline, refusing a tangent break above some bar. The honest sequencing
problem: on a hard-chine developable hull the chine crease is DELIBERATE, so a
naive fairness metric would refuse every hull the grammar can build. The metric
has to be defined on the longitudinal edge curves and the waterline — where a
break is a defect — and not on the transverse section, where the one break is
the design. That is why this rule is high-value but not first (§3).

---

### R15 — Transom / aft-body — D, SD

**Rule.** "TRANSOM STERN — Efficient aft section" (hull-designs); the drawings
show the displacement forms running out to a small or immersed transom.

**Express: YES.** `r_transom` (0–0.95, transom half-beam over max half-beam)
covers a pointed double-ender at 0 through a wide transom at 0.95, with
`rocker` lifting the keel aft. `grammar.check` has a `transom.chine` clause at
`:143`.

**Measure: transom IMMERSION drag is not modelled.** Holtrop's transom term
exists but `holtrop.particulars_from_floated` (`:627-628`) hardcodes appendages,
bulb and immersed transom to zero for small craft, and Holtrop is not the
production resistance model anyway. Michell's thin-ship integral has no transom
term. So at Fn 0.2–0.3, where an immersed transom is a real and avoidable drag
penalty, nothing in the ladder sees it.

**Enforcement.** Either a transom-immersion penalty in `resistance.py` or a
constraint row on transom immersion depth at design trim. Note the interaction:
`grammar.check`'s `transom.chine` clause permits the transom chine up to
`0.35·T` above the reference, which is a geometric guard and not a drag one.

---

### R16 — Asymmetric demihull, inward-facing flat sides — CAT

**Rule.** 001, "Asymmetric Demihull (option)"; gemini panel 9, "INWARD-FACING
FLAT SIDES / REDUCED WAVE INTERFERENCE".

**Express: NO.** Every section is symmetric about the demihull centreline, and
`catamaran_interference` models **two identical demihulls at ±s/2** by
construction — `4·cos²(k_y·s/2)` applied to a single-hull offsets grid. An
asymmetric demihull is outside that formula, not merely outside the genome.

**Priority: low.** It is drawn as an option, the literature benefit is
contested, and it costs both a new section topology and a new interference
derivation. R4 (spacing) delivers most of the same benefit for far less.

---

### R17 — Tunnel arch and cross-structure — CAT

**Rule.** 001, "Tunnel Arch" and "Cross-structure" as named parts; the front
view shows the arch profile with a centre pod.

**Express: NO.** No wet deck, no cross-structure, no second hull (§4.1).
`arrangement.py` has a cabin trunk (`:430,465`) but nothing spanning between
hulls.

**Note for the compliance tier.** `docs/research/COMPLIANCE.md:76,102,290-291`
records that ISO 12215-7 (multihull loads) blocks a catamaran SKU. That is a
certification-scope statement, not a hydrodynamics one, and it is cited here so
the geometry rebuild does not discover it late.

---

### R18 — Planing-only rules, recorded so they are not applied — P

Grouped because the verdict is identical: **not candidates, do not enforce, do
not add to the grammar for this SKU.**

Lifting strakes, chine flat, pad, wedge, steps and ventilation tunnels (gemini
panel 3, "TWIN STEPS / REDUCED WETTED SURFACE"). None is expressible: grep for
`step` finds only algorithm steps and a cabin-trunk step; every `strake` hit
(`unroll.py:616,1246,1271`, `engineer.py:97-116`) is a **plate strake**, a sheet
subdivision for nesting, with nothing hydrodynamic about it. Appendages and
bulbs are likewise absent from `geometry.py` and zeroed in Holtrop.

The one thing worth carrying forward from the planing panels is negative:
`FN_MICHELL_MAX = 0.45` already marks `valid=False` and `regime="planing"` above
that Froude number, and inflates sigma to the full total — so the ladder already
refuses to speak confidently about these forms. That is the correct behaviour
and it should not be softened.

---

### R19 — Freeboard measured on the wrong member — CAT

**Rule.** Not drawn; found while checking the target against the grammar, and
recorded because it is the same category error as R2.

`grammar.check` requires `freeboard.abs >= 0.30 m` and
`freeboard.rel >= 0.045·LWL` (`:125-126`). On the 12 m target that is
`D - T >= 0.54 m`, so `D >= 1.14 m` — a demihull with `D/B = 1.43`.

**On a catamaran the freeboard that governs seaworthiness is the WET-DECK
height, not the demihull sheer**, because the deck and the crew are on the
cross-structure. A monohull's `0.045·LWL` scaling applied to a demihull sizes
the wrong member, and it does so in the direction of making a slender demihull
even harder to reach.

**Enforcement.** Once R3 exists, the freeboard clause for a CAT constitution
should apply to the wet deck; the demihull retains only the absolute floor.

---

### R20 — The section SHAPE changes along the length — D, CAT

**Rule.** `hull-example-004.png` names three sections on one hull and they are
three different SHAPES, not three sizes of one shape: "SECTION A-A (BOW):
U-SHAPED", "SECTION B-B (MIDSHIP): SEMI-CIRCULAR", "SECTION C-C (STERN):
LOW-VOLUME". Read together with its "ROUND-BILGE SECTION: MINIMIZES WETTED
SURFACE AREA", the sheet is asking for a U forward, a semicircle amidships and a
shallow low-volume run aft.

The hydrodynamics are the owner's framing exactly. A U section puts reserve
buoyancy low and forward **without widening the waterline**, so the hull gets
volume where it needs it while keeping the fine entrance angle R6 asks for. A
semicircle is the minimum girth for a given section area — least wetted surface,
no crease to shed a vortex. A low-volume stern lets the pressure recover
gradually instead of leaving a wide wake. Three different jobs at three
stations, and one shape cannot do all three.

**Express.** NO, and this is the deepest single item in the document.
`geometry.Hull.section` returns a literal `(3, 2)` array — keel, chine, sheer —
and the count is re-hardcoded in five consumers. The parametrisation has ONE
section law for the whole hull, so "U forward, semicircle amidships" is not a
hull this grammar can draw badly; it is a sentence this grammar cannot say.

**Measure.** N/A — there is no section-shape quantity to measure.

**Enforcement.** The geometry rebuild (§3 item 14). R7, R8 and R20 are one
change, not three.

---

### R21 — Parallel midbody is the mechanism behind the Cp target — D, CAT

**Rule.** All four solar sheets call for it and each gives a different reason:
004 "PARALLEL MIDBODY: MAXIMIZES PRISMATIC", 005 "…SIMPLIFIES PV INTEGRATION",
008 "…EFFICIENT VOLUME DISTRIBUTION", 009 "…OPTIMIZED FOR ACCOMMODATION AND PV".

004's reason is the hydrodynamic one and it connects R21 to R5. A constant
section over the middle of the length raises Cp **without fattening the ends** —
it is how a slender hull gets displacement without buying a blunt entrance. The
other three reasons are arrangement reasons, and they happen to agree, which is
why this is the rare rule with no trade-off inside it.

**Express.** NO. `grammar.PARAMS` has `x_mb` — the max-beam STATION as a
fraction of LWL, bounded `[0.40, 0.68]` — and no midbody EXTENT. The waterline
is two fullness exponents (`p_bow`, `p_stern`) meeting at that station, so a
hull can have a **peak** but never a **plateau**. Every hull this grammar
generates has parallel midbody of exactly zero length.

**Measure.** No. Cp is computed (`hydrostatics.py`) and read into a receipt
string; midbody extent is not a quantity anywhere.

**Enforcement.** One parameter beside `x_mb` (a midbody extent), or replace the
two exponents with a waterline distribution. Cheaper than R20 and it is the
direct lever on R5 — worth doing in the same change as the R5 constraint row,
since a row that bars a Cp the grammar cannot reach would refuse everything.

---

### R22 — The solar platform sizes the cross-structure, and fights R3 — CAT

**Rule.** Drawn as a benefit on every solar sheet and never as a trade: 005
"WIDE WET-DECK PLATFORM: MAXIMIZES SOLAR PV AREA", 008 "WIDE SOLAR PV PLATFORM
(35m²): SUPPORTS 6-8 kWp ARRAY", 009 "EXPANDED SOLAR PV PLATFORM (55m²):
SUPPORTS 10-14 kWp ARRAY", 006 "WIDE SOLAR DECK PLATFORM: MAXIMIZES PV ARRAY
AREA".

**It is a trade, and the two sides are on the same sheet.** The cross-structure
is what carries the array, so PV area pushes the platform WIDE (larger `B_oa`,
therefore larger separation, therefore R4) and the slamming rule pushes it HIGH
(larger clearance, R3). Both are bought from the same structure, and both are
paid for in weight and in the height of the vertical centre of gravity. On a
solar boat the array is not an accessory — it is the powerplant — so this is the
coupling that makes the topology decision, and the drawings state only the
half that is free.

The two dimensioned sheets are self-consistent about area: 008 is 35 m² at
6–8 kWp (171–229 W/m²) and 009 is 55 m² at 10–14 kWp (182–255 W/m²), both
plausible for current modules. Nothing else on either sheet is derivable from
them, and 009's power chart is not usable (error 5 above).

**Express.** NO — R17. There is no cross-structure in the genome.

**Measure.** No. There is no deck-area quantity and no PV model in the ladder;
`energy.py` carries a flat payload figure.

**Enforcement.** Follows R3 and R17. When the wet deck becomes a parameter, deck
AREA becomes computable from it and the array becomes an objective rather than
an assumption — at which point R22 is a genuine two-sided constraint and not a
slogan.

---

### R23 — The drawn separations do NOT satisfy R4 — CAT

**Rule.** 005 labels its separation "HULL SEPARATION (s/L) TUNED FOR MINIMUM
RESISTANCE AT 10 KNOT CRUISE". 008 and 009 print the numbers that would let
anyone check it, and **the check fails**.

Neither sheet states `s/L`. Both determine it: separation is the overall beam
less one demihull beam, and the demihull beam is `LWL / (L/B_h)`. Computed by
`scripts/hull_form_audit.py:drawn_solar_cats()`, which is the one home of these
figures:

| sheet | LWL | `B_oa` | `L/B_h` | ⇒ `B_h` | ⇒ `s` | ⇒ `s/L` |
|---|---|---|---|---|---|---|
| 008 | 12.0 m | 4.0 m | 15.3 | 0.784 m | 3.216 m | **0.268** |
| 009 | 16.0 m | 4.5 m | 17.8 | 0.899 m | 3.601 m | **0.225** |

R4 records this tree's own measurement: at Fn 0.30 the destructive-interference
optimum is `s/L = 0.4450` and the constructive-interference WORST case is
`s/L = 0.1500` (`resistance.catamaran_interference`, owned by
`tests/test_phase1.py`). Both drawn boats sit well below the optimum, and 009 —
the one sold on "long-range efficiency" — sits nearer the worst case than the
best. The label is not supported by the sheet's own numbers.

**This is not a claim that the drawings are badly proportioned.** `B_oa` is
also set by stability, by deck area (R22) and by berth width, and a real design
trades those against interference. The finding is narrower and firmer: **a
separation presented as "tuned for minimum resistance" was not tuned for
minimum resistance**, and nothing downstream should inherit `s/L ≈ 0.22–0.27`
as a target.

**Express / measure.** As R4: `michell_rw` accepts `separation` and
`total_resistance` (`resistance.py:735`) does not pass it, so the ladder built
to design a catamaran computes one isolated demihull and could not currently
tell these two boats apart.

**Enforcement.** R4, unchanged. R23 only removes a wrong answer that the
drawings would otherwise supply.

---

### R24 — Stability duty and slenderness are separable — CAT (via a trimaran)

**Rule.** 006 draws "EXTREMELY SLENDER MAIN HULL (HIGH `L/B_m`): MINIMIZES
RESISTANCE" beside "SMALL, LOW-DRAG OUTRIGGERS (AMAS): PROVIDES PASSIVE
STABILITY", with a "TRANSVERSE STABILITY COMPARISON" inset.

**Recorded although the trimaran is excluded, because it states the principle
the mission depends on.** A monohull's beam is set by transverse stability, and
stability is why R1's `L/B > 12` is impossible for a monohull and ordinary for a
demihull: once stability comes from SEPARATION, each hull's beam is free to be
whatever resistance wants. R1 is not a different rule from R24 — it is R24
applied to two hulls instead of three.

That is also the argument for why `grammar.L_OVER_B_BAND`'s ceiling of 8.5 is
not merely tight but **categorically wrong for this topology**: 8.5 is a
monohull number, derived from a duty a demihull does not carry. See §4 item 1 —
the fix belongs in the policy compiler, where a family-conditional bound is an
explicit decision rather than a quiet widening.

**Express / measure / enforcement.** As R1 and R2.

---

### R25 — Rocker and forefoot are drawn as design variables — D, SD

**Rule.** 007's panga panel calls out "Moderate Rocker for Seakeeping" with a
leader line onto a pronounced keel curve, and its section shows the shallow
draft that goes with it. 003's classic displacement hull draws the opposite: a
long straight keel run with a deep forefoot.

**Express.** PARTIALLY, and the partial part is the finding. `grammar.PARAMS`
has `rocker` (keel rise at transom / T) and `forefoot` (keel rise at stem / T),
so the AMOUNT is parameterised — but the ZONES those amounts apply over are
**literals in `geometry.py`**, `0.3L` and `0.7L`, which fixes the flat-keel run
at 40% of the length for every hull the system will ever generate. So "moderate
rocker over a long run" and "moderate rocker over a short run" are the same hull
here, and they are not the same boat.

**Measure.** No — neither rocker extent nor keel-line fairness is a measured
quantity.

**Enforcement.** Two parameters, or fold the whole keel line into a
distribution. Low priority for this mission — the target is a slender demihull
with little rocker — but recorded because a LITERAL where a parameter belongs is
the same defect as a bound where a policy belongs, and §3 item 8 already carries
it.

---

### R26 — The drawings name a parameter vocabulary the grammar does not have — ALL

**Rule.** `hull-example-000.png` carries a panel headed **"COMMON HULL
PARAMETERS (FOR MODEL TRAINING)"** — the drawings' own specification of what a
generative hull model should carry. Set against `grammar.PARAMS` (15
parameters), it divides three ways:

| the sheet asks for | this tree |
|---|---|
| LWL, Beam, Draft | **inputs** — `LWL`, `BWL`, `T` |
| Displacement/Volume, Cb, Cp, Cm, Aw, Sw, LCB, LCF, KB, BM, GM | **computed outputs** — `hydrostatics.py` has all of them |
| Deadrise / **chine type** | deadrise yes (`beta_mid`/`beta_bow`/`beta_len`); **chine TYPE absent** — there is only ever a chine (R8) |
| **Length Overall (LOA)** | **absent** — `LOA == LWL` by construction (R10) |
| **Transom angle** | **absent** — `r_transom` is a half-beam RATIO, not an angle |
| **Hull count (1 / 2 / 3)** | **absent** (R17, §3 item 1) |
| **Hull separation (multi-hull)** | **absent** from the genome (R4, R23) |
| **Entry angle (α_e)** | **absent as an input AND as a measurement** (R6) |
| **Appendages (keel, skeg, etc.)** | **absent** (§3 item 13) |

Seven of the sheet's own named parameters have no representation at all, and six
of the seven are exactly the multihull and bow quantities this mission turns on.
`hull-designs-gemini.png` closes with the matching request — "include variations
in **L/B ratio** and **block coefficient (Cb)**" — and those are the two
quantities this grammar can least vary: `L/B` is capped at 8.5 by `grammar.check`
(R1) and `Cb` is an emergent output with no target (§3 item 11).

**Why this belongs in a rule set.** It is the same finding as R1–R19 taken from
the other end. Rather than asking "can the code express this shape", it asks
"does the code carry this WORD", and the answer localises the gap to a
vocabulary rather than to a kernel. That makes it the cheapest audit in the
document to re-run after the geometry rebuild.

**Enforcement.** None directly; it is the checklist §3 is derived against.

---

### R27 — The drawn dimension envelope, and the mission sits inside it — ALL

**Rule.** `hull-example-000.png` carries a "TYPICAL HULL DIMENSION RANGES"
table — five rows, four numeric columns — and apart from the two labelled solar
catamarans it is **the only place in twelve sheets where a proportion is printed
as a number rather than as an adjective**. Transcribed verbatim in
`navalai/formlib.py:DRAWN_DIMENSION_RANGES`; the catamaran row is
LWL 6–25 m, beam 3.0–10.0 m, draft 0.4–1.5 m, 6–20 kn.

Two cautions travel with it, both structural:

1. **The beam column is OVERALL beam** — the `B_oa` that 001, 005, 008 and 009
   dimension across both hulls. Dividing LWL by it yields a number that is not
   any family's `L/B`, so the table cannot supply a demihull proportion and is
   deliberately kept out of `FormFamily.proportions`, which is per-demihull.
2. **The "special forms" row prints "Varies" for beam and draft.** An adjective
   is not a band and is not converted into one: those keys are ABSENT, and
   `formlib.drawn_dimension_verdict` returns `None` for them rather than `True`.
   Scoring an unmeasured column as a pass is defect class 1.

**The one positive check in this document.** The mission's demihull — LWL 12 m,
draft 0.6 m, with 008's `B_oa` of 4.0 m — falls inside the catamaran row on all
three dimensioned columns. Every other comparison here is a hull the grammar
refuses or a rule the code cannot express; this is the drawings and the mission
agreeing, and it is worth recording that the disagreements are with the CODE and
not with the brief.

---

## 2. Rule-set summary

| # | rule | family | express | measure | fix |
|---|---|---|---|---|---|
| R1 | `L/B_h > 12` | CAT | NO (L0 gate, not bounds) | YES, `"proportions"` row | family-conditional band |
| R2 | `B/T` floor 1.8 refuses target | CAT | NO | YES, same row | family-conditional band |
| R3 | wet deck ≥ `U²/2g` | CAT | NO | function exists, 0 call sites | param + row |
| R4 | separation `s/L` at interference optimum | CAT | NO | machinery exists, unwired | param + one argument |
| R5 | `Cp = f(Fn)` | ALL | NO (emergent) | measured, not constrained | **one row** |
| R6 | `α_e` 7–12 deg | D SD WP | capped by R1 | **NOWHERE** | instrument, then bar |
| R7 | hard chines aft only | SD | NO (3-pt section) | N/A | geometry rebuild |
| R8 | round bilge | D | NO (3-pt section) | N/A | geometry rebuild |
| R9 | zero flare volume forward | WP | NO (scalar `flare`) | NO | copy the deadrise law |
| R10 | vertical stem | WP | YES (only this) | N/A | — |
| R11 | reduced pitching | WP D | indirectly | **no pitch anything** | pitch RAO |
| R12 | variable deadrise | P SD | MOSTLY YES | input | aft warp missing |
| R13 | LCB tracks regime | ALL | NO (emergent) | YES, `"lcb"` row | **make the bar `f(Fn)`** |
| R14 | fair lines | ALL | NO (C1 breaks) | NO (metric looks away) | new metric |
| R15 | transom | D SD | YES | immersion drag unmodelled | resistance term |
| R16 | asymmetric demihull | CAT | NO | NO | new topology, low priority |
| R17 | tunnel / cross-structure | CAT | NO | NO | new topology |
| R18 | planing devices | P | NO | NO | **do not add** |
| R19 | freeboard on the wet deck | CAT | NO | wrong member | follows R3 |
| R20 | section SHAPE varies with x (U bow / semicircle mid / low-volume stern) | D CAT | NO (one section law) | N/A | geometry rebuild — one change with R7, R8 |
| R21 | parallel midbody extent | D CAT | NO (`x_mb` is a station, not a plateau) | NO | one parameter; do it with the R5 row |
| R22 | PV platform sizes the cross-structure, and fights R3 | CAT | NO | NO (no deck area, no PV model) | follows R3 + R17 |
| R23 | drawn `s/L` 0.268 / 0.225 vs the 0.4450 optimum | CAT | NO | machinery exists, unwired | R4; R23 only deletes a wrong target |
| R24 | stability duty is separable from slenderness | CAT | NO | N/A | R1 + R2 — and it is the ARGUMENT for them |
| R25 | rocker / forefoot ZONES are literals | D SD | amount yes, extent NO | NO | two parameters; low priority |
| R26 | 7 named parameters have no representation | ALL | N/A | N/A | the checklist §3 is derived against |
| R27 | drawn dimension envelope; mission is inside it | ALL | N/A | N/A | — (the one positive check) |

---

## 3. What the parametrisation CANNOT SAY

This is the list the geometry rebuild is for. Each entry names the shape of the
fix, because "add a parameter" and "add a topology" are different projects.

**1. A second hull.** No demihull count, no spacing, no cross-structure; grep
for `demihull`, `catamaran`, `multihull`, `hull_spacing`, `tunnel`, `wet_deck`
over `navalai/` finds no genome, grammar or AST hit. *Fix: a new TOPOLOGY —
the design object stops being one `Hull` and becomes a hull plus a placement.
Everything downstream that assumes one hull (hydrostatics, weights, arrangement,
export, meshing) is in scope.* This is the largest single item and it is the
mission's own topology.

**2. A round bilge.** `section()` returns a literal `(3,2)` array
(`geometry.py:120-128`) and the count is re-hardcoded in five consumers.
*Fix: a variable-length section — a 4th point with a bilge radius at minimum, a
section-curve object properly. The count must stop being a literal before
anything else here is possible.*

**3. A chine that starts partway aft.** `y_chine` is defined at every x.
*Fix: a LONGITUDINAL DISTRIBUTION where there is now a topology constant — a
bilge radius `r(x)` that goes to zero aft turns R7 and R8 into one parameter.*

**4. Flare that varies along the length.** One scalar, `math.tan`, every
station (`geometry.py:66`). *Fix: a longitudinal distribution, copying the
`beta_mid`/`beta_bow`/`beta_len` law that already exists one line above it.*

**5. A wet deck / tunnel / motor recess.** No parameter, no geometry.
*Fix: parameters for the simple case (clearance, arch); a new AST NODE for
anything local like the recess, since a recess is a cavity in the aft body and
no scalar describes it.*

**6. Stem rake, bow overhang, counter stern.** `LOA == LWL` by construction
(R10). *Fix: new parameters (stem rake, overhang) — but note this breaks the
assumption that x ∈ [0, LWL] spans the hull, which `geometry.py`,
`hydrostatics.py` and `export.py` all rely on.*

**7. Aft deadrise variation.** The warp is forward-only and aft of
`L - beta_len·L` deadrise is frozen at `beta_mid`. *Fix: a third control point,
or a genuine distribution.*

**8. Rocker and forefoot extent.** The `0.3L` and `0.7L` zone limits are
LITERALS in `geometry.py:39-43`, not parameters — the flat-keel run is fixed at
40% of length. *Fix: two parameters, or fold into a keel distribution.*

**9. Sheer aft of `x_mb`.** Freeboard is flat aft of the max-beam station
(`geometry.py:62-65`); `sheer_rise` acts forward only. *Fix: a sheer
distribution.*

**10. Asymmetric sections.** Symmetric about the demihull centreline.
*Fix: new topology (independent port/starboard offsets) AND a new interference
derivation, since `catamaran_interference` assumes identical hulls.*

**11. A TARGET for Cp, LCB or α_e.** All three are emergent outputs; not one is
a design input. *Fix: this is a choice, not a defect — either constraint rows
on measured outputs (cheap, and the right answer for Cp and LCB), or an
inverse-design parametrisation (expensive). Do not do both for the same
quantity.*

**12. Fairness.** No curvature-continuity metric, and four known C1 breaks that
the one curvature metric explicitly excludes. *Fix: a new metric on the
longitudinal edge curves and the waterline — not on the section, where the chine
break is deliberate.*

**13. Bulb, step, lifting strake, appendage, rudder, skeg.** Absent from
`geometry.py` entirely. *Fix: new AST nodes — and for this mission, don't.*

**14. A section-type that varies along the length.** The general form of items
2, 3 and 7: the parametrisation has ONE section law for the whole hull.
*Fix: the deepest one — the section must become a function of x whose SHAPE, not
just whose dimensions, can change.*

**Two non-geometric ones, listed because they are the same defect class:**

**15. Catamaran wave interference is computed nowhere in the ladder.**
`michell_rw` accepts `separation`; `total_resistance` (`resistance.py:735`)
does not pass it. *Fix: one argument, once the genome has the parameter.*

**16. Pitch, relative motion and wet-deck slamming.** Heave only in
`seakeeping.py` — grep finds **zero** occurrences of "pitch" in the file.
*Fix: pitch RAO, then relative motion, then `slam_pressure` as a second CALL
SITE — never a second implementation.*

**Four more, from the seven sheets read on the second pass:**

**17. Parallel midbody extent (R21).** `x_mb` is the max-beam STATION; the
waterline is two fullness exponents meeting at it, so every hull has a peak and
none has a plateau. *Fix: one extent parameter beside `x_mb`, or replace the
two exponents with a waterline distribution.* Cheapest item on this list with a
first-order effect, and it is the direct lever on Cp (R5).

**18. Chine TYPE as a choice (R26).** 000's parameter list names "Deadrise /
Chine Type" and its midship strip draws six — round bilge, hard chine,
multi-chine, tunnel, twin keel, wedge. This grammar has one, permanently. *Fix:
this is item 2 and item 14 seen from the vocabulary end; the section-point count
must stop being a literal before "type" can mean anything.*

**19. Transom angle (R26).** `r_transom` is a half-beam RATIO. The angle at
which the transom meets the water — which is what governs flow release and
immersion (R15) — is not a parameter and is not derivable from the ratio.
*Fix: one parameter, cheap, and it should land with the transom-immersion
resistance term rather than before it.*

**20. Deck area, and therefore the PV array (R22).** No deck-area quantity
exists, so the array that powers the boat cannot be sized from the geometry;
`energy.py` carries a flat payload figure instead. *Fix: follows item 5 — once
the wet deck is a parameter, area is computable from it and the array becomes an
objective rather than an assumption.*

**The list above is the shape-side answer. R26 is the same audit from the
vocabulary side** — seven parameters the drawings name and this tree does not
carry — and the two agree, which is the reason to trust either.

---

## 4. What to enforce first

Ranked by how far the current batch sits from the rule and by what the fix
costs. The first two are ordered ahead of everything because nothing else can
be evaluated on the target hull until they move.

**1. R1 + R2 — the proportion bands, made family-conditional.**
The target demihull fails three grammar clauses (`bound[BWL]`, `L/B`, `B/T`) and
**0 of 200** sampled hulls exceed L/B 12, structurally. Every other catamaran
rule here is evaluated on a hull the grammar refuses to build, so this is not
merely first by value — it is first by dependency. The fix is small in code and
must NOT be a quiet widening: 8.5 is a defensible monohull number, and the
right home for a family-conditional bound is the policy compiler, whose ratchet
rule forces the widening to be an explicit decision. Confirming argument: at
L/B 15 the production Michell model is MORE valid, not less.

**2. R5 — a `Cp`-vs-`Fn` constraint row.**
Cheapest rule in the document with a real effect. Cp is already computed on
every evaluation (`hydrostatics.py:161`) and is read only into a receipt string.
Enforcement is one appended row and zero geometry. It is worth adding precisely
because it will fire — the recorded batch band is far wider than any sensible
target, so this is not the always-satisfied row that gap E4 deleted four of.

**3. R13 — make the LCB bar a function of Fn and family.**
The row exists (`evaluate.py:589`), the quantity is measured, the policy ratchet
is already wired. Only the constant `LCB_BAND_PCT_LWL = 3.0` needs to become
regime-dependent and asymmetric. No new instrument, no new row.

**4. R6 — build the α_e instrument.**
Nothing in the tree measures entrance angle from the lines; the only entrance
angle is a Holtrop regression on coefficients inside a function production never
calls. `scripts/hull_form_audit.py` is the first measurement of it and it should
become a `HydroState` field with its chord basis stated. Ship it as a BADGE, not
a bar — R1 currently puts a floor under α_e that no hull can get below, so a bar
would refuse everything and teach nothing.

**5. R3 + R4 — wire the two catamaran functions that are already written.**
`wet_deck_clearance_g` and `catamaran_interference` are both complete, tested
and connected to nothing. Each needs one grammar parameter and one call. They
rank below the bands only because the genome change has to follow the topology
decision; they rank above all geometry work because the physics is done. Both
carry an honesty caveat that must travel with them: the clearance row covers the
ship's own steady wave and not the seaway, and the interference term is proven
self-consistent but has no experimental anchor in this tree.

**6. R9 — give `flare` the longitudinal law `beta` already has.**
The cheapest structural change: the law is written, tested and understood one
line above the scalar that needs it. It unlocks the "zero flare volume forward,
normal flare aft" shape that no current hull can take, and it is a useful
rehearsal for item 7.

**7. R7 + R8 + item 14 — the variable section.**
Round bilge, a chine that starts aft, and a section law that varies along the
length are one change, not three: a section whose SHAPE is a function of x. This
is the geometry rebuild, and it is where the mission's actual hull form lives —
a solar-electric displacement demihull at Fn 0.2–0.3 is a round-bilge hull and
this grammar cannot draw one. It ranks below the items above only because they
are cheap and it is not.

**8. R14 — a fairness metric.**
The owner's framing is that efficiency follows from being hydrodynamically fair,
and the project currently measures nothing about fairness while carrying four
known C1 breaks. It ranks last of the things worth doing because it should be
built AFTER item 7: a fairness bar defined against a hard-chine 3-point section
would have to exempt so much that it would measure very little, and a metric
written to a geometry that is about to change is a metric written twice.

**Explicitly NOT to be enforced:** every planing rule (R18), the axe bow, SWATH,
air cushion, foils, bulbs and steps. They are drawn, they are interesting, and
for a solar-electric displacement catamaran at Fn 0.2–0.3 a rule set that
admitted them would be worse than none.

### Where R20–R27 land in that ranking

They do not reorder it. Three of them attach to items already ranked, and that
is the useful result — the second pass over seven sheets found no work the first
five had missed, which is some evidence the ranking is stable.

- **R21 (parallel midbody extent) belongs WITH item 2, not after it.** A `Cp`
  constraint row barring a Cp the grammar cannot reach would refuse every hull,
  and with `x_mb` a station rather than a plateau the reachable Cp range is
  whatever the two fullness exponents happen to produce. One parameter and one
  row, shipped together, or neither.
- **R24 is the ARGUMENT for item 1, not a new item.** It says why 8.5 is
  categorically a monohull number: once stability comes from separation, beam is
  free to be whatever resistance wants. Item 1 already had the measurement
  (0 of 200); R24 gives it the reason, which is what a policy ratchet needs in
  order to be an explicit decision rather than a widening.
- **R23 does not add work — it removes a wrong answer.** Without it, item 5
  would very plausibly be wired using the drawn `s/L ≈ 0.22–0.27` as a target,
  and that is nearer this tree's constructive-interference worst case than its
  optimum.
- **R20 is item 7, restated with the drawing that asks for it.** R22 follows
  item 5. R25, R26 and R27 are records, not work.

---

## 5. What could not be verified

- **`downloads/catamaran-hull-design-motor-recess.png` does not exist**, and did
  not appear with the six new sheets either. Nothing here is derived from it.
  The nearest drawn thing is 006's "AFT MAIN HULL VOLUME: SUPPORTS PROPULSION
  SYSTEM", which is added buoyancy aft and not a cavity — the opposite shape, so
  it does not stand in. The recess remains unaddressed and is a topology
  question (§3, item 5).
- **The two dimensioned solar catamarans are the only sheets whose claims can be
  checked, and they were.** Both self-checks (R23's `s/L`, R3's clearance
  against `U²/2g`) are closed-form arithmetic on labels read off the sheets, run
  by `scripts/hull_form_audit.py`. Neither is a hydrodynamic result: `s/L`
  0.4450 is this tree's own Michell computation with **no experimental anchor**
  (R4), and the clearance rule covers the ship's own steady wave and not a
  seaway (R3). Two drawn boats failing a bar derived from an unanchored model is
  a flag to investigate, not a verdict on the boats.
- **The entry-angle ceilings on 004, 008 and 009 (`< 12`, `< 10`, `< 9` deg)
  are not comparable to the α_e figures in R6.** The sheets state no basis, and
  R6's chord definition is one of several in the literature that disagree. They
  are recorded in `formlib.py` as `Basis.DRAWING` for the CEILINGS only; the
  floor of that band is practice.
- **Two bands in `navalai/formlib.py` claimed `Basis.DRAWING` off labels that
  are WORDS**, and were corrected to `APPROX` on this pass: 007's "Low L/B"
  had become `[2.5, 4.0]` and its "constant deep-V deadrise" had become
  `[18, 26]` with the edges borrowed from a different sheet. Neither number
  appears on 007. This is the number-declared-twice defect with the second copy
  laundered into a citation; `tests/test_formlib.py` now refuses a `DRAWING`
  source that admits no number was printed, and the guard is fired on both
  verbatim strings. **A qualitative label is evidence about the DIRECTION of a
  proportion and none at all about its EDGES.**
- **The counts in this document were counted, not remembered.** Two figures
  carried on the first pass were wrong when the sheets were tallied: the
  reversed "High Cp, Low Fn" block appears on **seven** sheets and not the two
  recorded, and the inverted-bow idea is drawn under **eight** names and not
  four. Both are now stated with the sheets named.
- **Nothing in `formlib.py` or here takes a figure from 009's power chart.** Its
  x-axis is mislabelled (error 5), so no propulsion-demand or generation number
  on that sheet is usable, including for the R22 platform trade.
- **No number in this document is a CFD or experimental result.** This work ran
  under a no-compute constraint. `bow_wave_rise` values are closed-form; α_e,
  L/B, B/T and flare figures are geometric measurements on sampled parameter
  vectors; the Cp and α_e bands are literature, basis `'approx'`, with no
  anchor in this tree.
- **The α_e figures here and the ones in the brief are not the same
  measurement** — see R6. Different chord bases give different numbers and
  neither reproduces the other.
- **α_e is highly sensitive to the geometry kernel, and the kernel is being
  rewritten as this is written.** MEASURED: `scripts/hull_form_audit.py --n 40
  --seed 0` run against commit `10a255a` gives α_e min 12.339 deg with 0 of 40
  hulls in [7, 12]; the SAME script, SAME n, SAME seed, run against the working
  tree mid-rewrite gives a min an order of magnitude lower and 6 of 40 in band,
  and the sampled `L/B` minimum moves too (2.208 → 2.224), so `grammar.check`
  itself is returning a different feasible set. The in-flight numbers are
  another agent's uncommitted work and are **deliberately not quoted here as a
  result** — the point is only that every α_e figure in this document is pinned
  to `10a255a` and must be re-run, not carried forward, once the kernel lands.
  R6's conclusion (nothing measures entrance angle from the lines) is a
  statement about the code's structure and survives the rewrite; R6's
  *distances* do not.
- **`navalai/formlib.py` is imported by nothing.** It is a library with no
  consumer, which is the defect §6 exists to prevent it becoming permanent. Said
  here so it is on the record and not discovered later as a surprise.
- **`scripts/hull_form_audit.py` carries a second copy of `bow_wave_rise`** so
  it can run against an archived tree while `resistance.py` is being rewritten.
  This is the number-declared-twice defect, admitted deliberately and fenced:
  the script asserts the copy equals `navalai.resistance.bow_wave_rise` at six
  speeds and exits non-zero if it has drifted. If `resistance.py` settles, delete
  the copy and import.

---

## 6. Who consumes `formlib`, and through which call site

**This section exists because the pattern in this tree is capabilities that
exist and nothing reaches.** Measured on the clean tree, three at once:
`navalai/arrangement.py` (1484 lines) is imported by NOTHING in `navalai/`,
`scripts/` or `ui/` — only by two test files; `compile_policy` is named in
comments in `optimize.py` and `evaluate.py` and **constructed nowhere** outside
`navalai/policy/`; and `resistance.bow_wave_rise` and
`resistance.wet_deck_clearance_g` have zero production call sites.
`navalai/formlib.py` is currently the fourth. Naming the call site is therefore
part of delivering it, not a follow-up.

**None of the wiring below is done, and none of it is claimed to be done.** The
point of this section is that each item names one existing symbol, so the work
is a named next step rather than an assumption.

### 1. The policy compiler — the PRIMARY consumer

`navalai/policy/dna.py:DesignDNA` is where an owner preference belongs, and the
chain from there already exists end to end:

```
formlib.target() / formlib.proposable()
    -> DesignDNA (a hull-family choice, as a PolicyValue)
    -> compile_policy(Constitution)                  policy/compiler.py:704
    -> CompiledPolicy.box(design_category, low, high) policy/compiler.py:366
    -> xl, xu = policy.box(...).as_bounds()           optimize.py:65-72
```

`optimize.py:65-72` is the single line where a bound becomes the sampler's
`xl`/`xu`, and it is the right place for a family band to land: **a length
ceiling becomes a BOUND, not a rejection**, so the search never spends
evaluations outside the envelope. A family's `l_over_b` and `b_over_t` bands are
exactly that kind of statement.

Two clauses of Gate V3.0 govern how: a policy may only **APPEND** a constraint
row, never rewrite one, and a ratchet may only move a bound **INWARD**.

**The second is why R1 cannot be delivered this way, and this is the load-bearing
caveat.** `grammar.L_OVER_B_BAND` is `(2.2, 8.5)`; the target demihull is L/B
15.0. Widening a bound OUTWARD is precisely what the ratchet forbids, so a
`formlib` family band cannot be ratcheted into the box to permit the target
hull. **The 8.5 ceiling has to move in `grammar.py` first, as a
family-conditional bound with R24's argument attached** (§4 item 1). Until then
`formlib` can only tighten a box that already refuses the mission's own hull.
Wiring it the other way round would be softening a gate to make a hull pass,
which this project does not do.

### 2. `hull_ast.Typology` — the direct, cheap one

`navalai/hull_ast.py` defines two typologies (`SHARP_CHINE`, `PRAM`) and
`TYPOLOGY_RULES` bands three parameters between them. `FormFamily.ast_typology`
already carries the mapping for the two families that correspond
(`hard_chine_displacement` → `SHARP_CHINE`, `pram_dory` → `PRAM`), so the fence
is writable today: a test asserting every `hull_ast.Typology` member is named by
exactly one `formlib` family, and that its `TYPOLOGY_RULES` bands sit inside
that family's. It costs nothing, and it stops the two typologies and the 31
families drifting into being two unrelated vocabularies.

### 3. `evaluate.CONSTRAINT_NAMES` — via a policy row, never directly

The R5 Cp-vs-Fn row (§4 item 2) reads its band from
`formlib.cp_envelope(fn)`. It must arrive as an **appended policy row**, not as
a new literal in `evaluate.py` — `Evaluation.g` is the one inequality vector and
NSGA-II consumes it automatically. **The ladder must never import
`navalai.formlib`**, for the same reason it must never import
`navalai.policy`: delete the constitution and every physics result must be
bit-identical. `formlib` imports no geometry and no grammar
(`tests/test_formlib.py` fences it on the source text); the dependency runs one
way, and it must keep running one way.

### 4. The mission translator, and the explainer

`formlib.families()` is a natural-language target: "a slender displacement
catamaran" resolves to a family key, and the family's `efficiency` sentence and
`candidacy_reason` are exactly what an explainer should say back. **LLMs
translate missions and explain; they have no code path to geometry** — reading
`formlib` to name a family, and then letting the policy compiler turn that name
into a bound, keeps that rule intact, because the LLM produces a KEY and the
compiler produces the NUMBERS.

### What must NOT consume it

Not `geometry.py`, not `grammar.py`, and not the resistance ladder. `formlib`
is data about hull forms; the moment a physics module reads a band from it, the
band becomes a bar and this becomes the second place a limit lives —
`navalai/limits.py` owns limits, and `tests/test_limits_single_source.py` is the
fence.

---

## 7. THE SOURCED BANDS — published literature, not the drawings

**Why this section is separate from R1–R27.** Everything above came off twelve
annotated schematics in `downloads/hull-examples/`. A schematic is an
illustration: §"the drawings are not trustworthy" records six errors in them,
and `Basis.DRAWING` in `navalai/formlib.py` exists precisely so a label read off
a picture cannot be mistaken for a measurement. This section is the other half —
bands taken from **published systematic series and peer-reviewed papers**, each
with the hull family it was measured on and the Froude range it is valid in.

**The problem it was written to solve, and the one number that matters.**
`scripts/hull_form_audit.py` measures the entry half-angle of the current
population off the waterline curve, and the answer is that the generator does
not make boat-shaped bows: the audit's own printout is the one home of the
figure, and R6 above is the argument. Nothing in `navalai/` measures α_e as a
constraint. A sourced band is what turns that from an observation into a bar.

### 7.0 The rules this section is written under

1. **A band with no family and no speed range is not a band.** Every row below
   names both. Where a source gives one and not the other, the row says so and
   is marked accordingly.
2. **UNVERIFIED means I did not open it.** Several numbers in this field are
   folklore repeated between textbooks. Anything not read from a document I
   fetched is labelled `UNVERIFIED` with the reason, and must not be promoted to
   a `Basis.SERIES` band in `formlib.py` until someone opens the source.
3. **NOT FOUND is an answer.** Where a search returned nothing defensible, the
   row says NOT FOUND rather than carrying a plausible number.
4. **Disagreement is reported, never averaged.** §7.9 lists the places two
   sources give different numbers for what looks like the same quantity, with
   the reason where the reason is known. There is no consensus band synthesised
   anywhere in this section.
5. **One home per number.** A band that reaches code lives in `formlib.py` (form
   data) or `navalai/limits.py` (a bar the ladder enforces) — not in both, and
   not restated here once it is there. This section carries the CITATION and the
   BASIS; the value lives with its owner.

### 7.1 Entry half-angle α_e — the priority

`i_e` in the literature, `alpha_e_deg` in `formlib.py`. Definition matters and
the sources do not all use the same one: see §7.9 item 1 before comparing any
two numbers below.

#### S1 — Blount & McGrath 2009 (READ IN FULL)

> D L Blount and J A McGrath, "Resistance Characteristics of Semi-Displacement
> Mega Yacht Hull Forms", *Trans RINA Vol 151, Part B2, International Journal of
> Small Craft Technology*, 2009 Jul–Dec. DOI 10.3940/rina.ijsct.2009.b2.95.
> Open copy: `oa.upm.es/14340/` (fetched 2026-08-13, 12 pp, read in full).

This is the strongest α_e source found, because it is a **cross-series
comparison** — nine systematic series scaled to a common 500 t displacement —
rather than one series' parent form. What it says about i_e, quoted rather than
paraphrased:

- *"Half angle of entrance at the waterline, i_e, from one series varying **3.7
  to 7.8 degrees** showed **no effect** on R/W for speeds from F_nL = 0.4 to 0.7
  for L/∇^(1/3) from 8.0 to 9.6."*
- *"A second hull series with i_e varying from **6.5 to 11.3 degrees** shows
  little effect on R/W for i_e **less than 8 degrees** for speeds up to
  F_nL = 0.8. For i_e **above 8 degrees** the change in R/W increases on the
  order of **0.01** for i_e up to 11+ degrees for intermediate speeds of
  F_nL = 0.5 and F_nL = 0.6. There is less of a change of R/W (less than 0.006)
  related to i_e above and below these speeds."*

**BAND (semi-displacement round-bilge, F_nL 0.4–0.8, slender):** i_e **≤ 8°** is
the flat part of the curve; 8–11° costs ~0.01 in R/W at F_nL 0.5–0.6 and less
elsewhere. Family: round-bilge / double-chine semi-displacement, slenderness
L/∇^(1/3) 8.0–9.6. **This is a resistance-optimum statement, not a geometric
feasibility statement** — 3.7° is measured and fine, so there is no lower bound
in this source at all.

**The caveat the paper states about its own numbers, and it must travel with
them:** *"Traditional displacement hull form coefficients such as C_B, C_P, C_X,
B/T, C_PF, L_E/L, i_e, etc. have **reduced significance** for optimizing total
resistance as a vessel approaches the planing speed threshold F_nL = 1.0"*, and
the guidance is *"a limited range of some hull form coefficients, but must be
used with caution as these data summaries are **subsets of single series
experiments**"*. So: valid as a band, not as an optimum, and not above F_nL ~1.

**Two i_e values for hard-chine craft, from the same paper's Appendix A:** the
USCG Series (Kowalyshyn & Metcalf 2006, 4 models, max F_nL 2.54) holds
i_e = **19.5°** fixed, *"for one model i_e = 21°"*. That is a hard-chine planing
series, and it is nearly **three times** the semi-displacement guidance above.
This is the single most important thing in §7.1: **α_e is family-dependent by a
factor of ~3, and a single 7–12° band applied to all families is wrong.**

#### S2 — Blount & McGrath, Appendix A: what the series themselves FIX

The same paper's Appendix A tabulates the fixed and variable parameters of nine
systematic series. Two of them treat i_e as a **variable** — Series 64 and the
NPL series — which is why S1 could say anything about it at all, and one fixes
it. Transcribed exactly:

| series | models | published | max F_nL | i_e |
|---|---|---|---|---|
| DTMB Series 64 (H.Y.H. Yeh) | 27 | 1965 | 1.50 | **variable** (with F_nL, L/∇^⅓, L/B, C_B, B/T, C_X) |
| NPL series (D. Bailey et al) | 22 | 1969 & 1976 | 1.20 | **variable** (with F_nL, L, L/B, B/T, L/∇^⅓) |
| DTMB Naval LCB-LCF mini-series (M. Lasky) | 9 | 1970 | 0.54 | **variable** (with C_PF, L_E/L, LCB/L, LCF/L) |
| USCG series (Kowalyshyn & Metcalf) | 4 | 2006 | 2.54 | **FIXED at 19.5°**, one model at 21° |

**Which of S1's two i_e ranges belongs to which series is NOT stated in the
paper** — it says "one series" and "a second hull series". Series 64 and NPL are
the two that vary i_e over a wide speed range, so they are the obvious
candidates, but that is an inference and it is recorded as one. **UNVERIFIED:
the assignment of 3.7–7.8° and 6.5–11.3° to named series.** Reading Yeh 1965 or
Bailey 1976 would settle it; neither could be opened (§7.10).

#### S3 — trade practice, and it DISAGREES with S1 by a factor of two

> *"How to make a better yacht bow"*, Boat International, published 2015-01-21,
> no named author. Fetched 2026-08-13.

Quoted exactly:

- sailing yachts: *"the half-angle might be between **10 and 20 degrees**, with
  10 degrees being a fine entry and 20 degrees being more suited for a slower
  displacement yacht"*
- motor yachts: *"a fine angle of entry, say **12 degrees**, is suited to
  high-speed semi-displacement style yachts, whereas a normal half-angle is
  between **18 to 24 degrees**"*
- *"A very fine half-angle – **less than 10 degrees** – is to be avoided."*
- *"The widest half-angles of entry – from **30 degrees to more than 40
  degrees** – are rarely found on yachts, but can be seen on scow-type barges
  that move at very slow speeds."*

**BASIS: trade press. This is `Basis.APPROX` at best and it must not be promoted
above that.** It carries no series, no model, no Froude number and no
measurement — it is a designer's rule of thumb written for a magazine. It is
recorded here for two reasons: it is the source of the numbers most likely to be
"remembered" into this project by someone, and it **contradicts S1 directly** —
S1 measured 3.7° with no resistance penalty in a peer-reviewed cross-series
comparison, and this says under 10° "is to be avoided". See §7.9 item 2 for why
both can be true.

#### S4 — the DEFINITION is not standard, and this bites before any band does

> Orca3D support article, *"Calculation of Half Entrance Angle, Immersed Transom
> Area, and Stern Coefficient for Holtrop Displacement Analysis"*. Fetched
> 2026-08-13.

The half entrance angle is *"the angle that the forward waterline makes with the
ship centerline when viewed in plan"* — but the tangent at the stem is unusable
on a real hull, so Orca3D measures *"the waterline angle to centerline at a
**modest distance aft of the stem**"* to avoid *"local geometric details like
rounded stems or flat waterline endings"*. **It does not say what that distance
is.** A commercial tool that feeds Holtrop's `c1` therefore uses an
implementation-defined station, and so does this project:
`scripts/hull_form_audit.py:alpha_e_deg(params, frac=0.05)` takes the fraction
as an argument and defaults it.

**Consequence, and it is the reason §7.9 item 1 exists:** two α_e numbers are
not comparable unless they share a station convention. A chord to 5% of L_wl and
a true tangent at the stem differ by more on a hollow waterline than the whole
width of the band this section is trying to establish. **Before any α_e
constraint ships, the station convention must be written down in ONE place and
the sourced bands re-read against it** — Blount & McGrath do not state theirs
either.

The tree's own Holtrop implementation is a THIRD convention:
`navalai/holtrop.py:half_angle_entrance` does not measure the lines at all — it
is the Holtrop–Mennen **regression** from L/B, C_wp, C_p, LCB, L_R and volume.
Its docstring already says it is *"the weakest link in the wave-resistance
chain because c1 goes as (90 − i_E)^−1.37565"*. That function is the one home of
that expression; nothing in this section restates it, and **it must not be used
as the measurement a constraint is judged on** — it is a prediction of i_E from
coefficients, so constraining it would constrain the coefficients twice.

#### S5 — Petersson 2020 (Uppsala, open access, READ IN FULL)

> Emil Petersson, *"Study of semi-empirical methods for ship resistance
> calculations"*, UPTEC F 20024, Examensarbete 30 hp, Uppsala Universitet, June
> 2020. Full text: `diva-portal.org/smash/get/diva2:1443385/FULLTEXT01.pdf`
> (fetched 2026-08-13, 66 pp, text extracted and read). Work done with FOI on a
> 249-model database.

**The one hard α_e datum in it, and it is a MEASURED hull rather than a rule:**
the MARIN Fast Displacement Ship parent form **FDS-5** — a round-bilge,
transom-stern semi-displacement hull — is tabulated at

    L_WL/B_WL 8    B_WL/T 4    C_P 0.626    C_B 0.396
    LCB -5.11 %L_WL    LCF -8.68 %L_WL    L/∇^(1/3) 8.68
    i_e = 11 deg

MARIN series speed range F_n 0.14–1.30, and the thesis records that the design
trade-off was *"prioritized"* over F_n 0.7–1.0.

**BAND (semi-displacement round-bilge monohull, L/B 8, F_n 0.14–1.30):
i_e = 11°, at the parent form of a 35-model series chosen for optimal
resistance AND seakeeping.** One hull, not a band — but it is a hull somebody
optimised, and it sits between S1's ≤8° and S3's 18–24°, at an L/B (8) between
S1's slender megayachts and S3's yachts. That is the pattern §7.9 item 2 turns
into an explanation.

The thesis also records that MARIN's `Sub-series 1` — six models, the
"forerunner series" — varied *"LCF, C_wp, C_vp and i_e"* against a **fixed curve
of sectional areas**, to find the best waterline shape for the parent. So i_e is
treated in that series as a **primary design variable at constant SAC**, which
is exactly the degree of freedom this project's generator does not have (R26,
§3). The six models' individual i_e values are in the MARIN report [6], not in
the thesis. **NOT FOUND: the per-model i_e values of MARIN Sub-series 1.**

#### S6 — catamarans: designer practice only, and NO peer-reviewed band was found

> Richard Woods, Woods Designs, *"Hull Resistance and Hull Shape Comparisons"*,
> `sailingcatamarans.com` (fetched 2026-08-13).

- *"So a **10 degree** angle seems a good compromise."* (half angle of entry)
- his stated failure modes at both ends: *"if it is too low then the boat is wet
  to sail, and if too fat it is also wet to sail as the bow wave goes vertically
  up the sides"* — i.e. **both bounds are SPRAY arguments, not resistance
  arguments.** Worth noting, because S1 measured no resistance penalty at 3.7°.
- Separately reported in the same search pass and **NOT opened, therefore
  UNVERIFIED**: that high-performance beach catamarans (Hobie, Dart) run under
  5°.

**BASIS: designer practice, a working catamaran designer's own site.
`Basis.APPROX`.** It is the best catamaran-specific α_e statement found.

**NOT FOUND — and this is the gap that matters most for this project's own
hull.** No published systematic catamaran series was located that reports a
demihull half-angle of entrance as a tested variable. The Southampton catamaran
series (§7.4) varies L/B, B/T and L/∇^(1/3) and its report is the obvious place
to look, but `eprints.soton.ac.uk` refused every fetch (§7.10). **So the target
family — a slender solar catamaran demihull — has NO sourced α_e band.** What it
has is: a designer's 10°, three drawing ceilings (`<12°`, `<10°`, `<9°` on
sheets 004, 008, 009 — R6 above), and the monohull evidence of S1/S5 that finer
is not penalised down to at least 3.7°.

#### 7.1.z What can be defended today

| family | F_n range | α_e | basis | source |
|---|---|---|---|---|
| slender semi-displacement round-bilge monohull, L/∇^⅓ 8.0–9.6 | 0.4–0.8 | **≤ 8° free; 8–11° costs ~0.01 R/W at F_n 0.5–0.6** | peer-reviewed, cross-series | S1 |
| semi-displacement round-bilge monohull, L/B 8, transom stern | 0.14–1.30 | **11° at an optimised parent form** | one measured hull | S5 |
| hard-chine planing, USCG series | up to 2.54 | **19.5° (one model 21°)**, fixed | series datum, not an optimum | S1 App. A |
| sailing yacht | not stated | 10–20° | trade press | S3 |
| motor yacht, semi-displacement | not stated | 12° fine / 18–24° normal | trade press | S3 |
| **catamaran demihull** | — | **NOT FOUND (peer-reviewed); 10° practice** | designer practice | S6 |
| planing craft, prismatic (Fridsma/Savitsky) | — | **NOT FOUND** — neither source opened; see §7.8.1 and §7.10 | — | — |

**The single most important line in this table is the spread: 3.7° to 21°, all
of it defensible, none of it interchangeable.** A generator judged against one
number would be judged against the wrong number for five of the six rows.

**What this does NOT license.** It does not license replacing the audit's 7–12°
window with any of these until the station convention (S4, §7.9 item 1) is
fixed, because none of the sources states one. The 7–12° window in
`scripts/hull_form_audit.py` came from the DRAWINGS, and §7.9 item 3 records
that it is narrower than every sourced band here.

---

### 7.2 Prismatic coefficient C_p versus Froude number

**`navalai/limits.py:PRISMATIC_BY_FROUDE` is the one home of this project's
curve, and its comment already says the right thing:** *"this table is NOT
transcribed from a licensed standard or from a series report this session could
open ... a citation is OWED"*. **The citation is still owed after this pass.**
Nothing below is a replacement table — restating those nine pairs here would be
the number-declared-twice defect — and no value in `limits.py` was changed by
this research. What follows is the evidence a future session should judge that
table against.

#### What the series actually FIX C_p at

From Petersson 2020 Table 3 (S5), transcribed exactly, plus C_p rows from
Blount & McGrath Appendix A (S1):

| series | C_p | L/∇^⅓ | B/T | L/B | F_n |
|---|---|---|---|---|---|
| MARIN Fast Displacement Ship | 0.561–0.685 (parent **0.626**) | 4.31–12.07 | 2.5–5.5 | 4–12 | 0.14–1.30 |
| DTMB Series 64 | **0.630** (fixed) | 8.60–12.40 | 2.0–4.0 | 8.45–18.26 | 0.06–1.50 |
| NPL round bilge | **0.693** (fixed) | 4.47–8.30 | 1.7–6.9 | 3.33–7.50 | 0.30–1.20 |
| NTUA double chine | 0.582–0.742 | 6.20–10.00 | 3.2–6.2 | 4.30–7.50 | 0.20–1.10 |
| **Southampton catamaran** | **0.693** (fixed) | 6.30–9.50 | **1.50–2.50** | **7–15.1** | 0.20–1.00 |
| Taylor–Gertler standard series | 0.50–0.80 | 5.50–10.00 | 2.25–3.75 | — | 0.16–0.58 |
| Harvald & Guldhammer | 0.50–0.80 | 4.00–8.00 | 2.5 | — | 0.15–0.50 |
| DTMB Naval LCB-LCF mini-series | 0.58 (fixed) | — | — | — | ≤0.54 |
| USCG series (hard chine) | 0.70 (fixed) | — | — | — | ≤2.54 |

**The MARIN result is the closest thing found to a sourced C_p optimum, and it
is a POINT, not a curve.** Petersson: *"All the models where designed to have
the prismatic coefficient close to C_P = 0.626, except for FDS-21 where
C_P = 0.685 and FDS-22 where C_P = 0.561. FDS-21 and FDS-22 was built with
identical dimensions as FDS-5, but with different prismatic coefficients. **This
was done to assert the belief that C_P = 0.626 indeed was the optimal choice for
the PHF**"*, for a series spanning F_n 0.14–1.30 with F_n 0.7–1.0 prioritised.

So a deliberate three-point C_p experiment at fixed dimensions concluded
**0.626 over 0.14–1.30**, which is *one* number for the whole regime — the
opposite shape of statement from a Cp(F_n) curve.

#### The sailing-yacht anchor — MEASURED, open data, 61 hulls

> J. den Ouden (2022), *"Delft Systematic Yacht Hull Series hydrostatics data"*,
> 4TU.ResearchData, **DOI 10.4121/21501375**, licence **CC0**. Downloaded
> 2026-08-13 (`ndownloader/items/21501375/versions/1`, two .xlsx, 84.6 kB) and
> reduced locally. Canoe-body hydrostatics for **61 DSYHS models**, upright and
> at 10/20/30° heel, at full scale L_wl = 10 m.

Computed from that file (upright, `cp0`; ranges are min–max with the median in
brackets). **This is the DSYHS geometry, not a resistance optimum** — DSYHS
varied these on purpose:

| DSYHS sub-series | n | C_p | C_m | C_wp | L_wl/B_wl | B_wl/T_c |
|---|---|---|---|---|---|---|
| Series 1 | 22 | 0.529–0.599 (0.564) | 0.646–0.647 | 0.651–0.724 | 2.73–3.62 | 2.81–5.35 |
| Series 2 | 10 | 0.543–0.548 (0.546) | 0.721–0.749 | 0.670–0.678 | 3.47–4.50 | 2.46–12.91 |
| Series 3 | 13 | 0.522–0.580 (0.549) | 0.657–0.758 | 0.649–0.694 | 3.00–5.00 | 6.97–19.38 |
| Series 4 | 13 | 0.539–0.566 (0.554) | 0.711–0.777 | 0.668–0.699 | 2.78–4.18 | 2.80–6.34 |
| Series 6 | 3 | 0.541–0.542 | 0.676–0.791 | 0.681–0.695 | 3.72–4.11 | 4.71–6.70 |
| **all 61** | 61 | **0.522–0.599** (0.549) | **0.646–0.791** (0.712) | **0.649–0.724** (0.677) | **2.73–5.00** | **2.46–19.38** |

Sailing-yacht canoe bodies therefore sit at C_p **0.52–0.60** — and the DSYHS
speed range is not in this dataset, so it carries **no Froude range** and by
rule 1 of §7.0 it is a family band only.

#### The disagreement, stated rather than averaged

The classical "optimum C_p rises with speed" relation that `limits.py` describes
as *"the classical Taylor/Saunders 'recommended prismatic' relation that every
small-craft text reproduces"* **could not be sourced in this pass.** No free copy
of Saunders, of *Principles of Naval Architecture*'s C_p-vs-V/√L figure, or of a
Taylor recommended-prismatic curve was opened. **NOT FOUND.**

What WAS found points two ways at once and both are recorded:

- **For it:** the fixed C_p of the series rises with the speed each was built
  for — Taylor–Gertler 0.50–0.80 at F_n ≤0.58, Series 64 0.630 at F_n ≤1.50,
  NPL 0.693 at F_n ≤1.20, USCG 0.70 at F_n ≤2.54, against DSYHS 0.52–0.60 for
  sailing yachts. That is the shape `PRISMATIC_BY_FROUDE` has.
- **Against it:** MARIN tested C_p directly at fixed dimensions and concluded
  ONE value (0.626) for F_n 0.14–1.30; and Blount & McGrath say outright that
  C_P *"and etc. have reduced significance for optimizing total resistance as a
  vessel approaches the planing speed threshold F_nL = 1.0"*. A curve that keeps
  rising through F_n 0.6 is asserting a sensitivity that the one paper here
  which compared nine series says is fading.

**No consensus is synthesised.** `PRISMATIC_BY_FROUDE` stays as it is, still
`approx`, still owed a citation, and now with the evidence for and against it
written down in one place.

---

### 7.3 LCB position versus Froude number

**`navalai/limits.py:LCB_BAND_PCT_LWL` is the one home of this project's ±%L_wl
band and nothing here changes it.** What the sources give is the CENTRE, not the
width, and they give it as a function of the design speed:

| source | family | LCB, %L_wl from midships (− = aft) | F_n | basis |
|---|---|---|---|---|
| Petersson 2020 §6.1 (S5) | MARIN FDS, semi-displacement transom stern | **−5.05 to −5.19**, held for the whole series | 0.14–1.30 | series datum |
| Petersson 2020 §6.2 (S5) | DTMB Series 64, round bilge | **−6.56**, constant for all 27 models | 0.06–1.50 | series datum |
| Petersson 2020 §6.4 (S5) | NPL round bilge | **−2 to −6.4** | 0.30–1.20 | series datum |
| Petersson 2020 §6.5 (S5) | Southampton catamaran demihull | **−6.4** | 0.20–1.00 | series datum |
| Blount & McGrath App. A (S1) | Taylor standard series | **0.0** (LCB/L = 0.50 fot), FIXED | ≤0.60 | series datum |
| Blount & McGrath App. A (S1) | USCG hard chine | LCB/L 0.38 fot = **−12** | ≤2.54 | series datum |
| Blount & McGrath §3.1 (S1) | semi-displacement, 500 t notional | locus of minimum R/W at LCB/L **0.40 fot = −10**, with L/∇^⅓ ≈ 9.0 | **0.6** | measured optimum |
| DSYHS dataset (§7.2) | sailing yacht canoe body, 61 hulls | **−7.90 to +0.01** (median −3.28) | not stated | measured geometry |

**The trend is real and it is monotone in the same direction the drawings claim
(R13): LCB moves AFT as design speed rises.** Taylor's low-speed series fixes it
at midships; the semi-displacement series sit at −5 to −6.5; Blount's measured
minimum-resistance locus at F_nL 0.6 is at **−10%**; the hard-chine USCG series
is at −12%.

**And that is the finding this project has to deal with.** `LCB_BAND_PCT_LWL` is
a band of ±3% and the sources put the CENTRE at −5 to −12% depending on speed.
Those are compatible statements only if the band is applied around an
Fn-dependent target — the same shape as `prismatic_target(fn)` — and **there is
no `lcb_target(fn)` in `limits.py`.** A ±3% band applied around midships would
exclude every semi-displacement series in the table above. **Whether it is
applied around midships or around a target is a question for `limits.py`'s owner
and is NOT answered here; this section only records that the sourced centres are
not zero and not constant.**

Two further LCB findings, both from S1, both about LCF rather than LCB:

- *"a round-bilge hull having **LCF 11% of L aft of LCB** has reduced pitch in
  head seas, pitch resonance occurs at low speeds, and low R/W for speeds from
  F_nL = 0.3 up to F_nL = 0.54"* — a seakeeping study on naval vessels. This is
  a **relative** placement rule and it is the only sourced statement found that
  ties the two centres together. Compare the measured hulls: FDS-5 has
  LCF−LCB = −8.68 − (−5.11) = **−3.6%** and the DSYHS median is
  −5.84 − (−3.28) = **−2.6%** — both well short of 11%.
- **Series 64's LCB is constant at −6.56% across 27 models spanning L/B
  8.45–18.26.** So slenderness alone does not move the sourced LCB.

---

### 7.4 L/B and B/T by family — and the catamaran cap is REFUTED

**This is the section that settles item 4 of the brief.** The project's
`grammar.L_OVER_B_BAND` ceiling of 8.5 refuses the target 12 × 0.8 m demihull at
L/B 15, and §6 above explains why a `formlib` band cannot ratchet it open. The
question this section answers is whether 15 is defensible at all.

**It is, and two published systematic series contain it:**

| series | family | L/B | B/T | L/∇^⅓ | F_n | source |
|---|---|---|---|---|---|---|
| **Southampton catamaran series** | **catamaran DEMIHULL** | **7 – 15.1** | **1.50 – 2.50** | 6.30–9.50 | 0.20–1.00 | S5 Table 3 |
| **DTMB Series 64** | round-bilge high-speed displacement monohull | **8.45 – 18.26** | 2.0–4.0 | 8.60–12.40 | 0.06–1.50 | S5 Table 3 |
| MARIN FDS | semi-displacement monohull, transom | 4 – 12 | 2.5–5.5 | 4.31–12.07 | 0.14–1.30 | S5 Table 3 |
| NPL round bilge | round-bilge high-speed displacement | 3.33 – 7.50 | 1.7 – 6.9 | 4.47–8.30 | 0.30–1.20 | S5 Table 3 |
| NTUA | double chine | 4.30 – 7.50 | 3.2–6.2 | 6.20–10.00 | 0.20–1.10 | S5 Table 3 |
| Taylor–Gertler | displacement monohull | — | 2.25–3.75 | 5.50–10.00 | 0.16–0.58 | S5 Table 3 |
| DSYHS (61 hulls) | sailing-yacht canoe body | 2.73 – 5.00 | 2.46 – 19.38 | — | not stated | §7.2 dataset |
| Woods Designs | sailing catamaran demihull | **10:1 – 16:1** | — | — | — | S6 (practice) |

**The target demihull at L/B 15.0, B/T 1.33 therefore sits INSIDE the
Southampton catamaran series on L/B (7–15.1) and just OUTSIDE it on B/T
(1.50–2.50).** That is a completely different verdict from the one `formlib`
currently records against the NPL envelope, and the reason is that NPL is a
MONOHULL series: **`_NPL_L_OVER_B` (3.33–7.50) is being asked a catamaran
question it cannot answer.** `formlib.py`'s own comment already names the
Southampton series as *"the anchor that would change that"*. It does.

Woods' practice band (10:1–16:1 for cruising to racing catamarans) brackets the
same place from the design side, and reaches the L/B 15.3 and 17.8 printed on
drawings 008 and 009 (R22, R23).

**A caution that must travel with this, and it is not a small one.** The
Southampton demihull B/T band is **1.50–2.50**. The target is 0.8/0.6 = **1.33**
— below it. And `formlib` records a project B/T FLOOR of 1.8 that already
refuses the target (R2). So the sourced series **supports the slenderness and
does not support the draft**: L/B 15 is inside a published series and B/T 1.33
is outside every one of the eight rows above. Whatever moves the L/B ceiling
must not silently import a B/T verdict with it.

#### The B/T disagreement inside this tree

`navalai/formlib.py:_NPL_B_OVER_T` records the NPL envelope as **(1.75, 10.77)**.
Petersson 2020 Table 3 records it as **1.7 – 6.9**. The lower edges agree to
rounding; **the upper edges differ by 56%**. Both claim to describe Bailey's NPL
series. This is not resolvable without Bailey 1976, which could not be opened
(§7.10), so it is recorded as an open disagreement rather than reconciled — and
`_NPL_B_OVER_T` should not be quoted as an authority until it is. See §7.9
item 4.

#### Ship-type L/B and slenderness, for context only

Petersson 2020 §5, citing his ref [3] and **explicitly for large commercial
ships, no Froude range given**: L/B 6.0–7.0 cargo, 5.5–6.5 tankers and bulkers,
6.0–8.0 passenger, 5.0–7.0 semi-displacement; slenderness L/∇^⅓ 5.0–7.0 cargo,
5.5–6.5 tankers/bulkers, 7.0–8.0 passenger, **6.0–9.0 semi-displacement craft**;
B/T *"about 2.5 for cargo vessel and as high as 5.0 for stability-sensitive
vessels such as passenger ships"*. **These are secondary — a textbook range
quoted in a thesis — and they are the wrong family for this product. Recorded so
nobody sources them a second time; not usable as a small-craft band.**

There is also a directional finding worth keeping, because it inverts:
Petersson reports that for **slow** vessels increasing B/T increases wave
resistance (BSRA and Taylor–Gertler, low F_n), and that in the MARIN parametric
study for **semi-displacing** ships *"the opposite relation for B/T can be
noted. For higher B/T the resistance decreases and lower B/T increases the
resistance"*. **So the sign of dR/d(B/T) is regime-dependent**, and a single
B/T preference across the speed range is wrong on one side of it.

---

### 7.5 THE DRAWINGS RE-OPENED — what they actually print for α_e

**Every sheet cited for an entry angle was opened again on 2026-08-13 for this
section, not taken from the table in §"Sources".** The §"Sources" table and the
six recorded drawing errors were checked against the images and are CORRECT as
written; what follows is what the sheets print about α_e, verbatim, plus one
error the first two passes did not record.

| sheet | what it prints about entry angle | verified |
|---|---|---|
| 000 | **`Entry Angle (αe)` — as a line item in "COMMON HULL PARAMETERS (FOR MODEL TRAINING)". NO VALUE.** | yes |
| 001 | nothing | yes |
| 002 | *"Very Low prismatic coefficient entry"* — words, no angle (already in error 2) | yes |
| 003 | *"Fine entry"* twice, on the classic-displacement panel. **NO NUMBER ANYWHERE ON THE SHEET.** | yes |
| 004 | *"FINE ENTRANCE ANGLE (< 12 deg)"* — **printed TWICE** (see below) | yes |
| 008 | *"FINE ENTRY ANGLE (<10°): SOFTENS WAVE IMPACT"*, on a demihull labelled `L/B_h 15.3` | yes |
| 009 | *"VERY FINE ENTRY ANGLE (<9°): ULTRA-LOW WAVE RESISTANCE"*, on a demihull labelled `L/B_h 17.8` | yes |
| gemini | nothing on entry angle; **`24° DEADRISE`** and **`18° DEADRISE`** confirmed | yes |

**So the entire numeric α_e content of twelve reference drawings is three
ceilings — `< 12°`, `< 10°`, `< 9°` — and all three are on the SOLAR sheets.**
`formlib.py`'s target family already carries them as
`alpha_e_deg = 6.0–12.0, Basis.DRAWING, "004 '< 12 deg', 008 '< 10 deg', 009
'< 9 deg'"`. **That transcription is correct and is confirmed by this pass.**
The 6.0 lower edge is not on any sheet — all three labels are one-sided
ceilings — and the band's own `Basis.DRAWING` source string does not claim it
is. Recorded so the floor is not later mistaken for a drawn number.

#### A SEVENTH drawing error: 004 prints the entry-angle callout twice, and both copies are corrupted

The existing list of six is correct and is not renumbered; this is an addition.
004 carries **two** leader lines to the bow, reading:

    "2INE ENTRANCE ANGLE (< 12 deg): SOFTEN WAVE PIERCING"
    "FINE ENTRANCE ANGLE (< 12 deg): SOFTEN WAVTED SURFACE AREA"

The first has lost its "F" to a stray "2"; the second reads "WAVTED", which is
"WETTED" with the "WAV" of the first label's "WAVE" written over it. **The two
justifications have been crossed**: a fine entrance softens WAVE-MAKING, and a
round-bilge section (the label immediately to its right) minimises WETTED
SURFACE AREA — which is exactly what 004's *other* callout says. So one callout
was duplicated and its text spliced with its neighbour's.

**Why this matters and is not pedantry: the NUMBER survives the corruption
intact in both copies.** `< 12 deg` is printed twice, identically, and the
leader lines land in the same place. The value is as well-attested as anything
on these sheets; only the reason given for it is garbled. Same conclusion as
error 1 — read the rule, not the annotation.

#### 003 carries R13's LCB claim with NO NUMBER — confirmed

R13 ("LCB position tracks the regime") cites 003. Re-opened: 003 prints
`LCB (Longitudinal Center of Buoyancy)` as a **leader label on the
semi-displacement and planing panels and nowhere else** — no percentage, no
station, no `%L_wl`, and none on the displacement panel at all. **The whole of
the drawn evidence for R13 is the POSITION of two leader lines.** That is
consistent with the sourced trend in §7.3 (LCB moves aft with speed) and it is
not a number. §7.3's series values are the first numeric basis this project has
for R13.

### 7.6 Drawings versus literature — where they agree, and where they do not

This is the corroboration pass. **A drawing label and a published series that
agree are worth far more than either alone; where they disagree, both are stated.**

#### AGREE — slenderness. The drawings are RIGHT and the code is wrong

| claim | drawn | published |
|---|---|---|
| catamaran demihull L/B | 001 `L/B_h > 12`; 008 `15.3`; 009 `17.8` | **Southampton catamaran series demihull L/B 7 – 15.1** (§7.4, S5 Table 3); Woods 10:1–16:1 (practice) |
| slender monohull L/B | 000 dimension table, and R26's "extreme slenderness" labels | **DTMB Series 64 L/B 8.45 – 18.26** (§7.4) |

**Two independent published series contain the slenderness the drawings ask for,
and `grammar.L_OVER_B_BAND`'s ceiling of 8.5 contains neither.** 008's 15.3 sits
inside the Southampton demihull band; 009's 17.8 sits outside it but inside
Series 64's monohull band. This is the strongest corroborated finding in §7:
**the drawn L/B is not an illustrator's exaggeration, it is normal published
practice for the family, and the refusal is the code's.**

#### AGREE — fine entry, in DIRECTION, and the agreement is stronger than it looks

The drawings tie a finer entry to a more slender demihull — `<10°` at
`L/B_h 15.3` (008) and `<9°` at `L/B_h 17.8` (009) — i.e. **the finer angle is
on the more slender hull.** That is not a stylistic choice; it is forced, and
§7.7 is the arithmetic. The published side agrees in the same direction: S1's
i_e ≤ 8° "no effect" band is measured on hulls at L/∇^(1/3) 8.0–9.6, and S5's
11° is at L/B 8.

#### DISAGREE — the drawn α_e ceilings are FINER than the published guidance, for a reason

004 says `< 12°` for a **monohull** displacement cruiser. S3 (trade press) calls
12° "fine" for a semi-displacement motor yacht and says under 10° "is to be
avoided"; S5's optimised MARIN parent form at L/B 8 measures **11°**. So 004's
ceiling sits at the fine edge of monohull practice rather than in the middle of
it, and 008/009's `<10°`/`<9°` are below the trade-press floor entirely.

**Both are defensible and the reason is the family, not an error.** S1 measured
i_e down to **3.7° with no resistance penalty at all** on slender hulls, and
008/009 are slender catamaran demihulls, not yachts. S3's "avoid under 10°" is
advice about a hull at L/B 3–4, where 10° is geometrically near-impossible
anyway (§7.7). **Averaged into one band these would produce a number wrong for
every family. They are not averaged.**

#### DISAGREE — Cp. The drawings are backwards and the literature does not rescue them

Drawing error 2 (seven sheets, "High Cp, Low Fn") is already recorded as
refuted. §7.2 adds that the correct direction is **also less well-sourced than
this project assumed**: MARIN tested C_p at fixed dimensions and concluded ONE
value across F_n 0.14–1.30, and Blount & McGrath say the coefficient loses
significance approaching F_n 1.0. **The drawings' label is wrong AND the
monotone curve replacing it is still uncited.** Recorded rather than resolved.

#### NOT CORROBORATED — everything else the drawings print

Wet-deck clearance 0.65/0.8 m, PV areas, s/L, tunnel arch, the 24°/18° deadrise
pair: **no published source was opened in this pass that speaks to any of
them at the small-craft scale.** They stand on the drawings alone, exactly as
`formlib.py` records them. Two deadrise anchors from the series literature are
in §7.8, and they do not corroborate 24°/18° — they are a different family.

### 7.7 α_e IS NOT INDEPENDENT OF L/B — and this is probably the real defect

**The measured population fact is that the median α_e is 31.6° with 1 hull of 74
inside 7–12°. Before that is read as "the bows are the wrong shape", note what
the waterline geometry forces.**

For a waterline of entry length `L_E` and maximum half-beam `B/2`, the CHORD
half-angle from the stem to the maximum-beam station is

    alpha_chord = atan( (B/2) / L_E ) = atan( (L/B)^-1 / (2 * L_E/L) )

which depends on **nothing but L/B and the entry-length fraction**. It is
arithmetic, not a source. It lives in `navalai/formlib.py` as
`alpha_e_chord_floor_deg(l_over_b, le_over_l)` — computed there, quoted here,
never restated — and the published `L_E/L` values it is evaluated at are real:
Taylor standard series **0.50**, Series 64 and NPL **0.60** (S1 Appendix A),
and Blount & McGrath's own guidance of `L_E/L 0.50` with `C_PE 0.59` at
F_nL 0.3–0.4 rising to `0.55` with `C_PE 0.62` up to F_nL 0.54.

Run `python -m navalai.formlib --alpha-e-floor` for the table. The shape of it:

- At **L/B 3** — a beamy small monohull — the chord angle alone is **15.5–18.4°**
  across the sourced `L_E/L` 0.50–0.60. A 7–12° band is not merely hard there,
  **it is unreachable**, and no bow shape fixes it.
- At **L/B 8.5**, the grammar's own ceiling, the chord angle falls to
  **5.6–6.7°** — the band becomes reachable only at the very top of the current
  box.
- At **L/B 15**, the target demihull, it is **3.2–3.8°**, comfortably finer
  than 009's drawn `<9°`.

**Calibration against the one hull where both numbers are known, and it is
n = 1.** FDS-5 (S5) is L/B 8 with a measured `i_e` of **11°**; its chord floor
at `L_E/L 0.6` is ~5.9°. So the tangent at the stem is roughly **twice** the
chord angle on a real convex waterline. One hull is not a calibration constant
and it is not treated as one — but it means the chord expression is a **FLOOR**,
and a real hull sits above it, which is the direction that matters here.

**The consequence for the 31.6° median.** The audit samples the monohull
grammar, whose L/B floor is about 2.2, and at L/B 2.2–3.0 the chord floor alone
is **15.5–24.4°**. A median of 31.6° is close to what that box produces even
with perfectly faired bows. **So the population's entry angle is mostly a symptom of the L/B
box, and the L/B box is the same 8.5 ceiling that refuses the target demihull.**

**What this does and does not license.**

- It does NOT excuse the generator. A tangent-to-chord ratio of ~2 at L/B 3
  would give ~31–37°, so the measured 31.6° is consistent with the box AND with
  bows that are no finer than the box forces. The two causes are not separated
  by this arithmetic, and **separating them needs the chord floor computed
  per-hull and subtracted** — which is a change to the audit, and the audit is
  not this agent's file.
- It DOES mean an α_e constraint applied at fixed L/B is partly a restatement of
  L/B, which is this project's number-declared-twice defect in its subtlest
  form: two constraint rows measuring one degree of freedom. §7.9 item 5.
- It DOES mean the ordering is: **move the L/B ceiling first** (§4 item 1, R24's
  argument, now corroborated by two published series in §7.6), and only then ask
  whether α_e still needs a row of its own.

---

### 7.8 The remaining bands: deadrise, SAC, transom, C_wp, C_m, spray rails

#### 7.8.1 Deadrise — four sourced values, and NONE of them corroborate the drawings

Every value here is from Blount & McGrath 2009 Appendix A (S1), read in full,
where it is stated as a series **fixed parameter** — a design choice held
constant, **not an optimum**. `β_T` is deadrise at the transom.

| series | family | β_T | max F_nL | note |
|---|---|---|---|---|
| DTMB Series 62 (Clement & Blount 1963) | hard chine planing | **12.5°** | 3.00 | 5 models |
| Delft series (Keuning & Gerritsma 1982), related to Series 62 | hard chine planing | **25.0°** | 1.65 | 5 models |
| NTUA series (Grigoropoulos et al 1999/2001) | double chine semi-displacement | **10°** | 1.10 | 5 models |
| USCG series (Kowalyshyn & Metcalf 2006) | hard chine | **16.6°**, one model **20°** | 2.54 | 4 models |

**MIDSHIP deadrise: NOT FOUND in any source opened.** All four values above are
at the transom. Series 62 is widely quoted as 13° amidships against 12.5° at the
transom; that came from a search result in this pass and the paper was **NOT
opened, so it is UNVERIFIED** and is not a band.

**Fridsma: NOT OPENED.** Fridsma's 1969 rough-water planing series is the
standard citation for deadrise's effect on impact accelerations and it is the
right source for a midship-deadrise band. No free copy was located in this pass.
The deadrise values commonly attributed to it are not recorded here, because
recording a remembered number is the defect this section exists to avoid.

**The drawings' 24° / 18° are NOT corroborated.** `hull-designs-gemini.png`'s
`24° DEADRISE` (deep-V) and `18° DEADRISE` (modified-V) are re-verified as
printed (§7.5). The four series above bracket them — 10°, 12.5°, 16.6°, 25° —
but not one is a deep-V *pleasure* craft at the drawn scale, and none states a
midship value. **So the drawn pair remains `Basis.DRAWING`, standing alone.**
This is a place where corroboration was attempted and did not arrive; saying so
is the finding.

**None of this reaches this product.** Every planing family in `formlib.py` is
`Candidacy.EXCLUDED`, and R18 records the planing rules so they are NOT applied.
Deadrise is recorded for completeness of the library, not as a live band.

#### 7.8.2 Transom immersion — three sourced A_T/A_M values

From Petersson 2020 (S5), each stated as held near-constant for its series:

| series | A_T / A_M | family | F_n |
|---|---|---|---|
| MARIN Fast Displacement Ship | **0.31** | semi-displacement monohull, transom stern | 0.14–1.30 |
| DTMB Series 64 | **0.40** | round-bilge high-speed displacement | 0.06–1.50 |
| NPL round bilge | **0.52** | round-bilge high-speed displacement | 0.30–1.20 |

**BAND (round-bilge/semi-displacement transom-stern monohulls, F_n 0.06–1.50):
A_T/A_M ≈ 0.31 – 0.52.** Three series, three points, all of them a series
constant rather than an optimum — so it is a band of PRACTICE across published
series, which is a real basis and a weak one. It is the first numeric transom
statement this project has: R15 ("Transom / aft-body") and the note at
`docs/research/HULL-FORM-RULES.md` R15 record that
`holtrop.particulars_from_floated` hardcodes the immersed transom to **zero**
for small craft. **A hull with A_T/A_M ≈ 0.4 modelled at A_T = 0 is not being
modelled.** That is a physics gap, not a band gap, and it is not this section's
to close.

`L_E/L`, the entry-length fraction, from the same two papers: Taylor **0.50**,
Series 64 **0.60**, NPL **0.60**, and Blount & McGrath's design guidance of
**0.50** with `C_PE 0.59` at F_nL 0.3–0.4, rising to **0.55** with `C_PE 0.62`
for F_nL 0.4–0.54. These are the values §7.7's chord expression is evaluated at.

**Sectional area curve SHAPE: NOT FOUND.** No source opened gives a defensible
statement of SAC shape beyond `C_P`, `C_PE`/`C_PF` (prismatic of the entrance /
forebody) and `L_E/L`. Recorded values of the forebody prismatic: Series 64
`C_PF = 0.52` (fixed), Blount's guidance `C_PE 0.59–0.62`. Those four quantities
— `C_P`, `C_PE`, `L_E/L`, `A_T/A_M` — are what the literature actually
constrains a SAC with, and they are a much weaker description than "the SAC
shape". Said plainly rather than dressed up as a curve.

#### 7.8.3 C_wp and C_m — one series anchor each, plus 61 measured yachts

| source | family | C_wp | C_m (or C_X) |
|---|---|---|---|
| DTMB Series 64 (S1 App. A) | round-bilge high-speed displacement | **0.76** (fixed) | C_X variable |
| NPL (S1 App. A) | round-bilge high-speed displacement | — | **C_X = 0.57** (fixed) |
| Taylor standard series (S1 App. A) | displacement | — | **C_X = 0.925** (fixed) |
| DTMB Naval LCB-LCF mini-series (S1 App. A) | round bilge | — | **C_X = 0.81** (fixed) |
| USCG (S1 App. A) | hard chine | — | — |
| **DSYHS, 61 hulls** (§7.2 dataset) | sailing-yacht canoe body | **0.649 – 0.724** (median 0.677) | **0.646 – 0.791** (median 0.712) |

**The C_X spread is the story: 0.57 (NPL) to 0.925 (Taylor).** Midship
coefficient is not a hull-form constant at all — it is a direct statement of how
round the bilge is, and it ranges over nearly a factor of two between a
high-speed round-bilge series and a classical displacement one. **A single C_m
band across families would be meaningless.** C_wp is better behaved: 0.76 for
Series 64 against 0.649–0.724 measured across all of DSYHS, i.e. roughly
**0.65 – 0.76** for displacement forms, which is the tightest cross-family
agreement found anywhere in §7 and is still only two sources.

#### 7.8.4 Spray rails, chines, and the flow separator — one GEOMETRIC rule, sourced

Blount & McGrath 2009 §5 "Design Guidance", quoted:

> *"An especially important feature for high-speed round-bilge hulls is
> longitudinal flow separators/chines/knuckles **beginning at the stem above the
> static waterline, continuing aft to at least midships below the waterline**.
> The placement of this flow separator in elevation relative to the bilge radius
> should be carefully considered as it serves competing technical purposes; both
> flow separation of the bow wave and below-water flow separation so as to
> minimize the probability of dynamic instability."*

**This is the only sourced spray-rail/chine GEOMETRY statement found, and it is
a topology rule rather than a band:** the separator starts *above* the waterline
at the stem and ends *below* it by midships, i.e. it CROSSES the waterline
somewhere in the forebody. It corroborates R7 ("hard chines AFT, round bilge
forward") in the sense that the chine's vertical position varies along the
length — and it corroborates it from the opposite direction, because Blount's
rule says the separator exists from the STEM, not from amidships aft.

The same paper's dynamic-stability numbers, which are the reason the separator
is placed where it is:

- non-oscillatory instability (bow diving, sudden heel, bow steering) *"result
  when a heavily-loaded vessel operates at speeds in excess of **22 to 25
  knots**"* and is *"usually ... remedied by reducing the operational speed of
  the vessel below 22/25 knots"*;
- *"Dynamic instabilities have been observed at speeds greater than
  **F_nL = 0.75**"*;
- the recommendation: model experiments whenever a **round-bilge** yacht may
  exceed **F_nL 0.75**, or a chine hull runs at **LCG/L approaching 45% fot or
  greater** (i.e. LCG less than 5% L aft of midships — a FORWARD LCG limit);
- *"Round-bilge vessels tend to be more susceptible to this form of instability
  than hard- or double-chine hulls"*;
- reference points from the same paper: hull speed `V/√L = 1.34` is **F_nL
  0.40**; the planing threshold is **F_nL ≈ 1.0**; modern yachts cruise at
  **F_nL 0.22–0.36**.

**All of it is above this mission's band** (F_n 0.20–0.30) and none of it is a
live constraint here. It is recorded because it is the only sourced statement
found that gives a SPEED at which a hull-form feature becomes mandatory, and
because the F_nL 0.40 = "hull speed" identity is a useful anchor for R5.

**Forefoot and rocker: NOT FOUND.** No numeric guidance was located in any
source opened. R25 records both as drawn design variables on sheet 007 with no
values printed; that remains the whole of the evidence.

---

### 7.9 Where the sources DISAGREE — stated, not averaged

1. **The DEFINITION of α_e.** Orca3D measures at *"a modest distance aft of the
   stem"* and does not say how far (S4). Blount & McGrath and Petersson state no
   convention at all. `holtrop.half_angle_entrance` does not measure the lines —
   it REGRESSES i_E from coefficients. `hull_form_audit.alpha_e_deg` takes the
   station as a `frac` argument, default 0.05. **Four conventions, no agreement,
   and the differences between them are comparable to the width of the bands in
   §7.1.** Nothing in §7.1 is comparable to anything else until this is fixed,
   and fixing it is a prerequisite to any α_e constraint.

2. **α_e: "3.7° costs nothing" (S1) versus "under 10° is to be avoided" (S3).**
   Not reconcilable as stated, and the likely explanation is that they are
   different claims about different hulls: S1 measures **calm-water resistance**
   on **slender** hulls (L/∇^⅓ 8.0–9.6), S3 is trade advice about **yachts** at
   L/B 3–4 where the failure mode is a **wet boat** — Woods (S6) gives exactly
   that reason for his own lower bound. **Resistance and spray are different
   objectives, and the sources are not measuring the same thing.** Recorded as
   an open disagreement because neither source says which it means.

3. **The 7–12° window this project audits against is narrower than every sourced
   band.** It comes from the drawings (`<12°`, `<10°`, `<9°`) and is applied as a
   two-sided band with a floor of 7°, but **all three drawn labels are one-sided
   ceilings** and S1 measured 3.7° with no penalty. **The floor of 7° has no
   source in the drawings and no source in the literature.** It should be
   treated as a reporting window, not a bar, until it has one.

4. **NPL's B/T envelope: `formlib._NPL_B_OVER_T` = (1.75, 10.77) versus
   Petersson 2020 Table 3 = (1.7, 6.9).** Upper edges differ by 56%. Both name
   Bailey's NPL series. Bailey 1976 could not be opened (§7.10). Unresolved;
   both are recorded and neither should be quoted as settled.

5. **C_p versus F_n: a rising curve (implied by the series' fixed values) versus
   MARIN's single optimum 0.626 over F_n 0.14–1.30, with Blount & McGrath saying
   the coefficient loses significance approaching F_nL 1.0.** §7.2. No
   reconciliation is attempted and `limits.PRISMATIC_BY_FROUDE` is unchanged.

6. **LCB: the sourced CENTRES (−5% to −12% L_wl, moving aft with speed) versus
   `limits.LCB_BAND_PCT_LWL` = ±3%.** These are compatible only if the band is
   applied around an Fn-dependent target, and no `lcb_target(fn)` exists.
   §7.3. Not resolved here — it is `limits.py`'s owner's call.

7. **α_e against L/B: an α_e row and an L/B row may be measuring one degree of
   freedom.** §7.7. This is a disagreement between this section's own
   recommendation and this project's one-number-one-place rule, and it is the
   reason §7.7 ends by ordering L/B first.

---

### 7.10 Sources: what was opened, what refused, what is still owed

**OPENED AND READ IN FULL** (all fetched 2026-08-13):

| # | source | how |
|---|---|---|
| S1 | Blount & McGrath, *"Resistance Characteristics of Semi-Displacement Mega Yacht Hull Forms"*, Trans RINA Vol 151 Part B2, IJSCT, 2009. DOI 10.3940/rina.ijsct.2009.b2.95 | open copy at `oa.upm.es/14340/`, 12 pp, text extracted |
| S5 | E. Petersson, *"Study of semi-empirical methods for ship resistance calculations"*, UPTEC F 20024, Uppsala Universitet, June 2020 | `diva-portal.org`, 66 pp, text extracted |
| — | J. den Ouden, *"Delft Systematic Yacht Hull Series hydrostatics data"*, 4TU.ResearchData, DOI **10.4121/21501375**, **CC0** | downloaded, 61 hulls, reduced locally |
| S3 | *"How to make a better yacht bow"*, Boat International, 2015-01-21 | web, trade press |
| S4 | Orca3D, *"Calculation of Half Entrance Angle, Immersed Transom Area, and Stern Coefficient..."* | web, tool documentation |
| S6 | R. Woods, *"Hull Resistance and Hull Shape Comparisons"*, sailingcatamarans.com | web, designer practice |
| — | the twelve drawings in `downloads/hull-examples/` | **opened as images** (§7.5) |

**REFUSED — every attempt, and this is why several bands are secondary:**

- `eprints.soton.ac.uk` — **HTTP 401/403 on every route.** This blocked BOTH
  Molland/Wellicome/Couser Ship Science Report 71 (the Southampton catamaran
  series report) and Report 127. So the Southampton demihull envelope in §7.4 is
  quoted from **Petersson 2020 Table 3**, a secondary source, not from the
  series report. It is the single most load-bearing number in §7 and it is
  second-hand. **Opening Report 71 is the highest-value follow-up in this whole
  section.**
- `orbit.dtu.dk`, `sciencedirect.com`, `repository.tudelft.nl`,
  `cembercikutuphanesi.biz.tr`, `apps.dtic.mil` (ADA174027, *"High Speed
  Displacement Vessels Parametric Studies"*) — 403/404.
- A partial Southampton demihull table was obtained from `ukdiss.com` quoting
  Wellicome et al. 1995 (models 4b/5b/6b: L/B 9.00/11.00/13.10, B/T 2,
  C_B 0.397, **C_P 0.693**, C_M 0.565, LCB **−6.40%**, S/L 0.2 and 0.4). It
  AGREES with Petersson on C_P, C_B and LCB, which is why §7.4 is trusted at
  all. **It is a student-essay site quoting a report; it is corroboration, not
  a source, and it is marked as such.**

**NOT FOUND / NOT OPENED — named so nobody assumes they were checked:**

- **Bailey (1976), NPL series** — would settle disagreement 4 and the two i_e
  ranges in S1/S2.
- **Yeh (1965), Series 64** — would settle whether 3.7–7.8° or 6.5–11.3° is
  Series 64's i_e range.
- **Clement & Blount (1963), Series 62** — midship deadrise.
- **Fridsma (1969)** — rough-water planing, midship deadrise.
- **Savitsky (1964) / Savitsky & Brown (1976)** — planing. Neither opened; no
  planing number in this section comes from either.
- **Keuning & Sonnenberg (1998), DSYHS** — the DSYHS *hydrostatics* were
  obtained as open data, but the resistance paper and therefore the **DSYHS
  Froude range** were not. That is why §7.2's DSYHS row carries no speed range.
- **Taylor / Saunders recommended-prismatic curve** — the citation
  `limits.PRISMATIC_BY_FROUDE` says is owed. **Still owed.**
- **Molland & Insel (1992), catamaran resistance components.**
- **A catamaran demihull α_e band from any peer-reviewed source** — the gap that
  matters most for this project's own hull (S6).

**What changed in the tree because of this section.** `navalai/limits.py` was
NOT touched: no band here was strong enough to overwrite a number that already
has an owner, and `PRISMATIC_BY_FROUDE` and `LCB_BAND_PCT_LWL` are unchanged.
`navalai/formlib.py` gained the literature citations, the `Basis.LITERATURE`
rung to carry them, and `alpha_e_chord_floor_deg`. Nothing here restates a
number that lives in either file.
