# HULL-FORM RULES — what the drawings ask for, and what this code can say

Research record. Derived 2026-08-13 from the annotated schematics in
`downloads/`, read against commit `10a255a` extracted to a scratch tree
(`git archive HEAD`), because the working tree was mid-rewrite.

**This document carries no status.** Status is `python -m navalai.gates` and
`python scripts/reconcile_gaps.py`. What is here is a rule set, a verdict per
rule on whether the code can *express* it and whether it *measures* it, and the
list of things the current parametrisation cannot say at all.

Every distance-from-the-batch number below is reproduced by
`python scripts/hull_form_audit.py` — run it rather than trusting this prose.
That script is the only home of those numbers; this file quotes them and names
the script, per the one-source rule.

## Sources, and what they are worth

| file | what it carries |
|---|---|
| `downloads/hull-example-001.png` | symmetric catamaran, trimaran, planing. `L/B_h > 12`, wet-deck clearance, tunnel arch, cross-structure, asymmetric-demihull option |
| `downloads/hull-example-002.png` | axe-bow wave-piercer, SWATH. Zero flare volume, reduced pitching axis, slender entrance, minimised waterplane, ride-control fins |
| `downloads/hull-example-003.png` | classic displacement, semi-displacement, planing. Fine entry, round bilge, hard chines aft, chine flat, lifting strakes, LCB callouts |
| `downloads/hull-designs.png` | ~40-form taxonomy across 6 families, one line of intent each |
| `downloads/hull-designs-gemini.png` | 14 forms, profile + half-breadth + waterline. 24 deg / 18 deg deadrise, variable deadrise, twin steps, wave-cancellation bulb, vertical stem, inward-facing flat sides, high cross-structure clearance |

`downloads/catamaran-hull-design-motor-recess.png` — **named in the brief as the
actual target and NOT PRESENT ON DISK.** `downloads/` was listed in full; it
does not exist under any name. So the target geometry used throughout this
document is the one stated in prose — demihull `L = 12 m, B = 0.8 m, T = 0.6 m`
— and **nothing here is derived from the motor recess**, which no one has seen.
A motor recess is a local aft-body cavity and it is a topology question; it is
listed as unanswered in §4.

### The drawings are not trustworthy line-by-line, and three errors matter

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
3. **002's SWATH block reads "Low L/B, High Fn, Dynamic lift dominant"
   directly under its own "Submerged Buoyancy" heading.** A SWATH is a
   displacement form whose whole point is that buoyancy, not dynamic lift,
   carries it. The block is copy-pasted from the planing panel on 001.

Minor: `hull-designs-gemini.png` announces "7 designs" per section and then
repeats panels 4 and 12, so its numbering is not a key; `F_D` is used for the
Froude number, which is normally `Fn`.

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
| Trimaran, quadrimaran | **NO** for this SKU | not the stated topology |
| Transom stern | **partially yes** | already expressible via `r_transom`; but see R19, transom immersion drag is unmodelled |

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
`seakeeping.py`. *Fix: pitch RAO, then relative motion, then `slam_pressure` as
a second CALL SITE — never a second implementation.*

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

---

## 5. What could not be verified

- **`downloads/catamaran-hull-design-motor-recess.png` does not exist.** The
  named target drawing was not on disk and nothing here is derived from it. The
  motor recess is unaddressed and is a topology question (§3, item 5).
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
- **`scripts/hull_form_audit.py` carries a second copy of `bow_wave_rise`** so
  it can run against an archived tree while `resistance.py` is being rewritten.
  This is the number-declared-twice defect, admitted deliberately and fenced:
  the script asserts the copy equals `navalai.resistance.bow_wave_rise` at six
  speeds and exits non-zero if it has drifted. If `resistance.py` settles, delete
  the copy and import.
