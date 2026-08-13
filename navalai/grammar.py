"""Hull grammar: parameter vector + closed-form feasibility constraints (L0 gate).

Pattern from Ship-D (Bagazinski & Ahmed 2023): validity is decided by cheap
algebraic constraints on the parameter vector (their 49 checks run in ~0.2 ms,
~10,000x faster than mesh checks), which is what makes slider-rate gating
possible. This grammar targets small craft: **LWL 2.5-24 m, the scope of
Directive 2013/53/EU** (it said "4-20 m" until 2026-08-14, which was a box
nobody had sourced and which refused this project's own 12.0 x 0.8 m demihull
on beam alone — see the incident block below `PARAMS`).

THE GENOME IS DESIGN TARGETS PLUS SHAPE, NOT SHAPE ALONE (plate P1,
2026-08-13). `Cp` and `lcb` are the prismatic coefficient and the longitudinal
centre of buoyancy the designer ASKS FOR, and `geometry.sac_exponents` solves
the sectional area curve that delivers them; `p_bow` and `p_stern`, the old
chine plan-form exponents, are gone because a plan-form is a consequence of
the area curve and the section law, not an input. `roundness` is the bilge
shape function's blend from hard chine (0) to a full radiused fillet (1).

MEASURED at commit c7b7c4b on 200 draws of `evaluate.sample_valid`, integrating
Cp and LCB off the DELIVERED geometry: Cp spanned 0.386..0.832 with 18.0% in
the 0.55-0.62 band, and LCB spanned -10.02..+13.88 %LWL with 46.5% inside
+-3 %LWL. Both were emergent outputs of fifteen unrelated shape knobs.

Coordinate system: x=0 at transom, x=LWL at stem; z=0 at design waterline,
z negative down; y is half-breadth (starboard).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from . import formlib
from .limits import (CP_GENE_BOUNDS, LCB_BAND_PCT_LWL,
                     RCD_HULL_LENGTH_SCOPE_M, HullRole, hull_role)

# ==========================================================================
# THE PROPORTION BANDS, WHICH ARE CONDITIONAL ON WHAT THE HULL IS PART OF
#
# INCIDENT, 2026-08-14. This project's own target — a catamaran with 12.0 m x
# 0.8 m demihulls — was refused by `check()` on three clauses before a line of
# physics ran:
#
#     bound[BWL]: 0.8 outside [1.2, 6.0]
#     L/B: 15.00 outside [2.2, 8.5]
#     B/T: 1.33 outside [1.8, 12.0]
#
# The narrowest 12 m hull this grammar could express was 1.42 m. The owner
# asked for 0.8 m.
#
# THE DIAGNOSIS IS NOT "THE BANDS ARE WRONG". They are correct MONOHULL bands.
# A 12 m monohull 0.8 m wide would capsize and the band is right to refuse it.
# They were applied to the wrong OBJECT, and the fix is therefore NOT to widen
# them: `L_OVER_B_BAND` and `B_OVER_T_BAND` below are BYTE-FOR-BYTE what they
# were, they remain what a monohull is judged against, and
# `tests/test_vessel_bands.py` proves a 12.0 x 0.8 m MONOHULL is still refused
# on the same clause with the same numbers.
#
# WHAT CHANGED IS THAT A SECOND ROW EXISTS, and it is SOURCED. A demihull's
# band is the UNION of the monohull band and the published catamaran-demihull
# series envelope. The union is stated as a rule rather than as four literals:
#
#   L/B  [2.2, 8.5] u [7.00, 15.10] = [2.2, 15.10]
#   B/T  [1.8, 12.0] u [1.50,  2.50] = [1.50, 12.0]
#
# and the sourced half comes from `formlib.SOTON_DEMIHULL_*` — the Southampton
# catamaran series (Molland, Wellicome & Couser, Ship Science Report 71, 1994)
# demihull envelope, quoted SECONDARY from Petersson (2020) Table 3 because the
# report itself refused every fetch. THE IMPORT IS THE POINT: writing 15.10
# here as a literal beside a comment naming Southampton is this repository's
# signature defect with the second copy laundered into a citation.
#
# WHY A UNION, AND NOT THE SERIES ENVELOPE ALONE. Southampton's L/B floor is
# 7.00 and its B/T ceiling is 2.50. Adopting those as the demihull band would
# REFUSE a power-catamaran demihull at L/B 5 — a boat that exists, that
# `formlib.power_cat_demihull` describes, and that is no more extreme than a
# monohull this grammar already admits. The asymmetry is deliberate and it runs
# one way only: a demihull may be anything an admissible MONOHULL may be, plus
# whatever the catamaran series adds beyond that. Both unions come out
# CONTIGUOUS (the intervals overlap at 7.00-8.50 and 1.80-2.50), so neither
# band has a hole in it that a min/max would paper over; the test asserts it.
#
# WHAT WAS **NOT** WIDENED, AND WHY IT MATTERS MORE THAN WHAT WAS.
#
#   B/T. The target's 0.8/0.6 = 1.33 is BELOW the Southampton floor of 1.50, so
#   IT IS STILL REFUSED — on draft, not on slenderness. There is no published
#   demihull at that draft to band against, and inventing 1.3 to make the
#   owner's number fit would be exactly the move honesty rule 6 forbids. The
#   refusal SAYS SO: it names the series, the edge, and the fact that what is
#   missing is EVIDENCE rather than a feature. A 12.0 x 0.8 m demihull at
#   T <= 0.533 m (B/T >= 1.50) is accepted today.
#
#   The demihull L/B ceiling is 15.10 and NOT DTMB Series 64's 18.26.
#   `formlib.S64_MONOHULL_L_OVER_B` reaches 18.26 and is why the drawings'
#   L/B 15-18 demihulls are credible practice rather than an illustrator's
#   exaggeration — but Series 64 is a MONOHULL series, and taking a monohull
#   ceiling for a demihull is the same category error as the monohull ceiling
#   that started this, pointed the other way. It corroborates; it does not band.
#
# THERE IS NO TRIMARAN ROW. `mission.SUPPORTED_HULL_COUNTS` is (1, 2) and
# refuses three, and `limits.HullRole` has two members for the same reason: a
# role with no sourced band would fall through to the monohull one, which is an
# unmeasured quantity scored as a passing one.

# THE MONOHULL BANDS — UNCHANGED, AND THEY KEEP THEIR ORIGINAL NAMES.
#
# They used to be four literals inside `check()`, which is how gap B9 became
# possible: L0 bounded BWL/T at 12 on the PARAMETER vector and nothing ever
# re-checked the proportions of the hull that was actually delivered. MEASURED
# on 200 L0-feasible hulls floated to their mission displacement: 28.0% sit
# outside the B/T band and 4.5% outside the L/B band ON THE FLOATED STATE, and
# one delivered hull reached B/T 14.4 against the project's own <= 12 bar. The
# parameter T is the DESIGN draft at midship; the floated draft is whatever the
# weight model produces, so the two are simply different numbers and the gate
# was checking the one nobody sails.
#
# `proportion_margins` is the shared kernel: `check()` applies it to the
# parameters and `evaluate()` applies it to `HydroState`, so the band cannot
# drift between the two. The names are kept because `evaluate.py`,
# `experiments.py`, `resistance.py`, `formlib.py` and four test modules read
# them, and because THE MONOHULL BAND IS STILL THE DEFAULT: an ungoverned call
# to `check(x)` is judged by exactly the numbers it was judged by before.
L_OVER_B_BAND = (2.2, 8.5)
B_OVER_T_BAND = (1.8, 12.0)

# THE DEMIHULL BANDS, as the union rule above. Written as `min`/`max` over the
# two contributing intervals rather than as literals, so that moving either
# contributor moves this band and cannot leave a stale copy behind.
_SOTON_LB = formlib.SOTON_DEMIHULL_L_OVER_B
_SOTON_BT = formlib.SOTON_DEMIHULL_B_OVER_T
L_OVER_B_BAND_DEMIHULL = (min(L_OVER_B_BAND[0], _SOTON_LB.low),
                          max(L_OVER_B_BAND[1], _SOTON_LB.high))
B_OVER_T_BAND_DEMIHULL = (min(B_OVER_T_BAND[0], _SOTON_BT.low),
                          max(B_OVER_T_BAND[1], _SOTON_BT.high))

# THE PROVENANCE OF EACH EDGE, carried beside the band and printed in the
# refusal. A band whose refusal cannot say where its number came from is a bar
# a designer cannot argue with, and this project has already shipped one.
_MONOHULL_SRC = ("this project's own L0 band for a single hull; practice, no "
                 "anchor in this tree")
_DEMIHULL_SRC = (f"union of the monohull band and {_SOTON_LB.source}")

# role -> {metric: (band, source)}. ONE table, read by `proportion_margins`,
# by `check()` and by `evaluate()` through the first of those.
PROPORTION_BANDS: dict[HullRole, dict[str, tuple[tuple[float, float], str]]] = {
    HullRole.MONOHULL: {
        "L/B": (L_OVER_B_BAND, _MONOHULL_SRC),
        "B/T": (B_OVER_T_BAND, _MONOHULL_SRC),
    },
    HullRole.DEMIHULL: {
        "L/B": (L_OVER_B_BAND_DEMIHULL, _DEMIHULL_SRC),
        "B/T": (B_OVER_T_BAND_DEMIHULL, _DEMIHULL_SRC),
    },
}

# WHERE A REFUSAL STOPS BEING "TOO SLENDER" AND BECOMES "NOBODY HAS MEASURED
# ONE". Below the Southampton B/T floor there is no published demihull to band
# against, so the honest refusal names the missing evidence instead of implying
# a number exists. This is the sentence the owner's 12.0 x 0.8 x 0.6 m demihull
# gets, and it is the whole point of the change: the target is refused ON DRAFT,
# with the reason, rather than refused on slenderness for no reason.
OUT_OF_SOURCED_RANGE = (
    "OUT OF SOURCED RANGE, not out of physics: no published catamaran-demihull "
    "series in this tree reaches it. The floor is the Southampton series' own "
    "minimum and what is missing is EVIDENCE, not a feature — see "
    "formlib.SOTON_DEMIHULL_B_OVER_T and docs/research/HULL-FORM-RULES.md §7.4")

# The two freeboard floors `check()` enforces on the parameter vector. Hoisted
# out of the constraint expressions on 2026-08-14 because each was written
# TWICE — once in the condition and once in the message beside it — which is
# the exact pattern that put a 15 mm ply outside its own scantling rule, and
# because the D floor below is derived from the first of them.
MIN_FREEBOARD_ABS_M = 0.30
MIN_FREEBOARD_FRAC_LWL = 0.045

# THE DERIVED BOX FLOORS. Computed from the bands above so that no bound
# without naval-architecture content can refuse a hull a sourced band accepts —
# the rule stated in the PARAMS comment, executed rather than asserted.
_LWL_BOX = RCD_HULL_LENGTH_SCOPE_M   # RCD Art. 3(2); limits.py owns it
_BWL_CEILING = formlib.DRAWN_DIMENSION_RANGES["large monohull"]["beam_m"].high
_T_CEILING = formlib.DRAWN_DIMENSION_RANGES["large monohull"]["draft_m"].high
_L_OVER_B_CEILING_ANY = max(b["L/B"][0][1] for b in PROPORTION_BANDS.values())
_B_OVER_T_CEILING_ANY = max(b["B/T"][0][1] for b in PROPORTION_BANDS.values())
_BWL_FLOOR = _LWL_BOX[0] / _L_OVER_B_CEILING_ANY
_T_FLOOR = _BWL_FLOOR / _B_OVER_T_CEILING_ANY
_D_FLOOR = _T_FLOOR + MIN_FREEBOARD_ABS_M

# (name, unit, low, high, description)
PARAMS = [
    # ------------------------------------------------------------------
    # THE ABSOLUTE SIZE BOX. Every edge below is either SOURCED or DERIVED
    # from a band, and it says which. It used to be LWL [4, 20], BWL
    # [1.2, 6.0], T [0.2, 1.5] — monohull-recreational scaling with no stated
    # provenance, and the BWL floor of 1.2 m is what refused the owner's 0.8 m
    # demihull before any ratio rule got to speak.
    #
    # THE RULE THIS BOX IS NOW SET BY: **a bound with no naval-architecture
    # content must not refuse a hull that a SOURCED band accepts.** A box
    # cannot express a ratio, so the two ends are set differently and both are
    # written down:
    #
    #   the FLOORS are DERIVED from the bands, so the box cannot bind first;
    #   the CEILINGS are SOURCED, and where a ceiling can still bind before a
    #   band does, that is recorded here rather than discovered later.
    #
    # MEASURED consequence on the rejection sampler, because widening a box is
    # not free: uniform-in-box yield through `check()` falls 13.2% -> 6.7%
    # (4000 draws, seed 1). `sample()` allows 200 tries per sample and needs
    # ~15, so it still converges; it costs about 2x the draws.
    #
    # LWL: Directive 2013/53/EU (RCD) Art. 3(2), OJ L 354/95 — "recreational
    # craft ... of hull length from 2,5 m to 24 m". BOTH edges are that scope.
    # Outside it the entire rules tier (ISO 12217-1, ISO 12215-5, the design
    # categories) does not govern the boat, so a hull there would be scored by
    # a compliance tier that has nothing to say about it — the `gate2m.py`
    # printing KCS's EFD over a Wigley hull defect, in the rules tier. LOA ==
    # LWL by construction in this grammar (see `formlib`'s `_M_STEM`), so
    # bounding LWL bounds hull length. NOTE WHAT IS **NOT** TAKEN:
    # `formlib.DRAWN_DIMENSION_RANGES` draws hulls to 30 m; 30 m is outside RCD
    # scope and is refused rather than adopted.
    ("LWL",        "m",   _LWL_BOX[0], _LWL_BOX[1], "waterline length"),
    # BWL floor: DERIVED as LWL_low / (the largest L/B ceiling over all roles),
    # i.e. the beam at which the box stops binding before the L/B band does.
    # It is NOT a claim that a 0.166 m hull is a boat — what refuses that hull
    # is `freeboard.rel`, `section.solve` and the ladder's own validity
    # envelope, all of which have content, rather than a bound that has none.
    # BWL ceiling: `formlib.DRAWN_DIMENSION_RANGES` largest PER-HULL beam
    # (6.0 m, "large monohull"); the catamaran and trimaran rows are OVERALL
    # beam and are not per-hull numbers. RECORDED CONSEQUENCE: 6.0 m can bind
    # before the L/B floor of 2.2 above LWL 13.2 m, so a 24 m x 9 m barge is
    # not expressible. Nothing in this tree sources one and the product line
    # does not want one; the defect was at the NARROW end.
    ("BWL",        "m",   _BWL_FLOOR, _BWL_CEILING,
     "beam ON THE DESIGN WATERLINE at the "
                                     "max-area station"),
    # T floor: DERIVED as BWL_low / (the largest B/T ceiling over all roles),
    # on the same rule and with the same disclaimer. T ceiling: the largest
    # draft `formlib.DRAWN_DIMENSION_RANGES` draws (2.0 m, "large monohull") —
    # the old 1.5 m ceiling was a real restriction at the top of the length
    # range, where a 24 m displacement hull drafts more than that.
    ("T",          "m",   _T_FLOOR, _T_CEILING,
     "design draft (keel at midship)"),
    # D floor: DERIVED as T_low + MIN_FREEBOARD_ABS_M — the shallowest depth at
    # which ANY hull can clear `freeboard.abs`, so a shallower bound would
    # enclose only hulls this gate already refuses. D ceiling UNCHANGED at 3.0.
    ("D",          "m",   _D_FLOOR, 3.0,
     "depth, keel to sheer at midship"),
    # Cp and lcb are DESIGN TARGETS, and both are bounded from `limits.py`
    # rather than by a literal here: `CP_GENE_BOUNDS` is the span of the
    # Froude-number prismatic table (`limits.prismatic_target`), so the gene
    # can always be set to the target the mission implies, and the LCB gene
    # spans exactly the band the ladder already enforces on the FLOATED hull.
    # A bound written twice is the same defect as a threshold written twice.
    ("Cp",         "-", CP_GENE_BOUNDS[0], CP_GENE_BOUNDS[1],
     "TARGET prismatic coefficient (see limits.prismatic_target)"),
    ("lcb",        "%", -LCB_BAND_PCT_LWL, LCB_BAND_PCT_LWL,
     "TARGET LCB, % LWL forward of midships"),
    ("x_mb",       "-",   0.40, 0.68, "max-AREA station / LWL"),
    ("r_transom",  "-",   0.05, 0.50, "transom sectional area / max sectional "
                                      "area"),
    ("beta_mid",   "deg", 0.0, 25.0, "deadrise at midship"),
    ("beta_bow",   "deg", 2.0, 50.0, "deadrise at forward stations"),
    ("beta_len",   "-",   0.15, 0.6, "fraction of LWL over which deadrise warps"),
    ("roundness",  "-",   0.0,  1.0, "bilge roundness: 0 hard chine, 1 full "
                                     "fillet"),
    ("rocker",     "-",   0.0,  0.6, "keel rise at transom / T"),
    ("forefoot",   "-",   0.0,  1.0, "keel rise at stem / T"),
    ("flare",      "deg", -5.0, 25.0, "topside flare angle"),
    ("sheer_rise", "-",   0.0,  0.5, "bow sheer rise / D"),
]

N_PARAMS = len(PARAMS)
NAMES = [p[0] for p in PARAMS]
LOW = np.array([p[2] for p in PARAMS])
HIGH = np.array([p[3] for p in PARAMS])

# Cold-bend twist a sheet panel will take without a jig or heat, in degrees of
# deadrise change per metre of run. Declared once, here, and read by `check()`
# and by nothing else — the number that was inlined as a bare `14.0` in the
# constraint expression AND in the message beside it, which is the two-copies
# pattern that put a 15 mm ply outside its own scantling rule. It is a
# WORKSHOP limit, not a class-society one, so it is not `limits.py`'s to own;
# if a rule ever derives it, it moves there and this becomes an import.
MAX_PANEL_TWIST_DEG_PER_M = 14.0


def proportion_ratios(lwl: float, b_wl: float, t: float) -> dict[str, float]:
    """The two proportions themselves, guarded against a zero denominator.

    Split out so `proportion_margins` and `check()` compute L/B and B/T from
    one expression: they printed the ratio in the refusal message and computed
    the margin from a second copy of the same division, and a message that
    disagrees with the number it explains is how a designer is sent chasing the
    wrong parameter.
    """
    return {"L/B": lwl / max(b_wl, 1e-9), "B/T": b_wl / max(t, 1e-9)}


def bands_for(vessel=None) -> dict[str, tuple[tuple[float, float], str]]:
    """The proportion bands and their provenance for a hull in `vessel`.

    `vessel` is anything `limits.hull_role` accepts: a `HullRole`, a
    `mission.VesselConfig` (or anything carrying `n_hulls`), or None. None is a
    MONOHULL and gives the bands this module has always enforced.
    """
    return PROPORTION_BANDS[hull_role(vessel)]


def proportion_margins(lwl: float, b_wl: float, t: float,
                       vessel=None) -> dict[str, float]:
    """Relative band margins for L/B and B/T: > 0 means OUTSIDE the band.

    Normalised by the band edge rather than left absolute, so the number is
    scale-free and continuous — NSGA-II needs a gradient out of an infeasible
    region, and "L/B is 1.2 too big" means something different on a 4 m tender
    than on a 20 m barge.

    `vessel` DEFAULTS TO A MONOHULL, so every existing caller — `check()` with
    no vessel, and `evaluate()`'s re-application to the FLOATED state (gap B9) —
    gets the identical numbers it got before this argument existed. The band a
    demihull is judged against is wider on both metrics, so defaulting the
    other way would have silently loosened the bar for every monohull in the
    tree, which is the failure this change exists to avoid the mirror image of.
    """
    bands = bands_for(vessel)
    ratios = proportion_ratios(lwl, b_wl, t)
    out: dict[str, float] = {}
    for key, val in ratios.items():
        lo, hi = bands[key][0]
        out[key] = max((lo - val) / lo, (val - hi) / hi)
    return out


@dataclass(frozen=True)
class GateReport:
    ok: bool
    violations: tuple[str, ...]


def _rel(name: str, cond: bool, msg: str, out: list[str]) -> None:
    if not cond:
        out.append(f"{name}: {msg}")


def _proportion_message(key: str, val: float, vessel=None) -> str:
    """The refusal sentence for one proportion, naming the ROLE and the SOURCE.

    The old sentence — the ratio, the word "outside", and the monohull band —
    told this project's owner that his own boat was illegal without telling him
    it was being judged as a MONOHULL, which is the whole content of the
    2026-08-14 finding. The incident block at the top of this module quotes it
    verbatim. The clause NAME is unchanged
    ("L/B", "B/T") because consumers key on it; only the sentence grew.
    """
    role = hull_role(vessel)
    (lo, hi), src = PROPORTION_BANDS[role][key]
    msg = f"{key} {val:.2f} outside {[lo, hi]} for a {role.value} ({src})"
    # BELOW the floor of a band whose floor came from a published series is a
    # DIFFERENT refusal from above its ceiling, and saying so is the honesty
    # half of this change: the hull is not impossible, it is UNEVIDENCED.
    if key == "B/T" and role is HullRole.DEMIHULL and val < lo:
        return f"{msg}. {OUT_OF_SOURCED_RANGE}"
    return msg


def check(x: np.ndarray, vessel=None) -> GateReport:
    """L0 algebraic gate: closed-form, plus the geometric metrics.

    Returns every violated constraint (not just the first) so the UI can
    grey sliders with a reason, mirroring the manifest-style gating rule.

    `vessel` SAYS WHAT THIS HULL IS PART OF, and it is the argument this gate
    was missing on 2026-08-14. A `mission.VesselConfig`, a `limits.HullRole`,
    or None. **None is a MONOHULL and reproduces this gate exactly as it stood**
    — same bands, same numbers, same messages — so an ungoverned call cannot be
    loosened by the existence of the demihull row. Only the proportion bands
    are conditional; every other clause here is a property of one moulded
    surface and does not care how many of them the vessel has.

    THE GEOMETRY IS BUILT ONCE and four checks read it: `sac.target`,
    `section.solve`, `chine.submerged`, `transom.chine` and `panel.twist`. It
    is called here rather than re-derived in closed form, because a closed
    form here would be the same number declared twice and the two copies would
    drift — which is what produced gap E6 in the first place.

    FAILS CLOSED. A parameter vector whose bounds are already violated can
    make `Hull` divide by zero (e.g. x_mb = 1.0). Those bounds are reported
    separately; here an unbuildable geometry counts as a violated design
    target rather than as a pass, because `${VAR:-0}` — an unmeasurable
    quantity scored as perfect — is the failure mode this repository keeps
    paying for.
    """
    x = np.asarray(x, dtype=float)
    v: list[str] = []
    if x.shape != (N_PARAMS,):
        return GateReport(False, (f"shape: expected {N_PARAMS} params",))
    if not np.all(np.isfinite(x)):
        return GateReport(False, ("finite: NaN/inf in parameter vector",))

    # bound constraints
    for i, (name, _u, lo, hi, _d) in enumerate(PARAMS):
        _rel(f"bound[{name}]", lo <= x[i] <= hi, f"{x[i]:.4g} outside [{lo}, {hi}]", v)

    p = named(x)
    lwl, bwl, t, d = p["LWL"], p["BWL"], p["T"], p["D"]

    # draft below depth with real freeboard
    fb = d - t
    _rel("freeboard.abs", fb >= MIN_FREEBOARD_ABS_M,
         f"freeboard {fb:.2f} m < {MIN_FREEBOARD_ABS_M:.2f} m", v)
    _rel("freeboard.rel", fb >= MIN_FREEBOARD_FRAC_LWL * lwl,
         f"freeboard {fb:.2f} m < {MIN_FREEBOARD_FRAC_LWL * 100:.1f}% LWL", v)
    # SLENDERNESS / STABILITY PROPORTIONS — THE ROLE-CONDITIONAL PAIR.
    # Same kernel evaluate() re-applies to the FLOATED hull (gap B9): one band,
    # two states. The refusal now names the ROLE and the SOURCE, because
    # "L/B 15.00 outside [2.2, 8.5]" told the owner his own boat was illegal
    # without telling him it was being judged as a monohull.
    #
    # THE TWO ROWS ARE WRITTEN OUT, NOT LOOPED, AND THAT IS DELIBERATE.
    # `tests/test_constraints_honest.py` censuses the live relational
    # constraints by scanning this function for each relation's literal NAME
    # in its reporting call — the fence
    # that deleted four dead checks in gap E4 and refuses a constraint that
    # cannot fire. A loop over ("L/B", "B/T") makes both rows invisible to it,
    # which trades a real gate for two lines of tidiness.
    marg = proportion_margins(lwl, bwl, t, vessel)
    ratios = proportion_ratios(lwl, bwl, t)
    _rel("L/B", marg["L/B"] <= 0.0,
         _proportion_message("L/B", ratios["L/B"], vessel), v)
    _rel("B/T", marg["B/T"] <= 0.0,
         _proportion_message("B/T", ratios["B/T"], vessel), v)
    # deadrise ordering (bow at least as steep as midship)
    _rel("deadrise.order", p["beta_bow"] >= p["beta_mid"],
         f"beta_bow {p['beta_bow']:.1f} < beta_mid {p['beta_mid']:.1f}", v)
    #
    # FOUR CHECKS WERE DELETED HERE, AND DELETING THEM CHANGES NO VERDICT.
    # Gap E4: `keel.rocker`, `keel.forefoot`, `x_mb.margin` and `flare.fold`
    # cannot fire anywhere inside the declared parameter bounds, so they padded
    # the constraint count and nothing else. Ship-D's "49 closed-form
    # constraints" is a count this grammar was written to echo; echoing it with
    # tautologies makes the count true and the claim false.
    #
    # Each is dead for a reason that is arithmetic, not empirical:
    #   keel.rocker    `rocker * T <= 0.75 * T` with rocker bounded at 0.6.
    #   keel.forefoot  `forefoot <= 1.0` IS the forefoot upper bound, restated.
    #   x_mb.margin    0.05..0.95 against an x_mb bound of [0.40, 0.68].
    #   flare.fold     needs BWL < 0.70 m (flare >= -5 deg, freeboard <= 2.8 m)
    #                  against a BWL minimum of 1.20 m.
    #
    # THREE CHECKS ARE NEW WITH PLATE P1/P2, and two of them are refusals of a
    # DESIGN TARGET rather than of a shape:
    #
    #   sac.target       (Cp, lcb) outside what a(x) can reach with both shape
    #                    exponents in [1, 8]. Refused, never approximated: a
    #                    generator that silently returns the nearest reachable
    #                    Cp is exactly the generator plate P1 replaced.
    #   section.solve    the sectional area curve asks a station for more area
    #                    than its draft and deadrise can enclose
    #                    (A <= d^2 / tan(beta) at roundness 0, i.e. the chine
    #                    reaching the waterline), or the flare consumes the
    #                    whole half-beam at the max-area station.
    #   chine.submerged  REPLACES the old `chine.height`, which allowed the
    #                    midship chine 0.25 T ABOVE the waterline. With the
    #                    design waterline a first-class curve the chine has to
    #                    sit at or below it, or the section's waterline point
    #                    is not on the topside run and the closed-form area
    #                    the whole kernel is solved against does not hold. The
    #                    bar moved because the quantity changed meaning; it
    #                    moved TIGHTER, and it is measured on the delivered
    #                    geometry rather than on a midship closed form.
    #
    # C43 developability: MAX bottom-panel twist per metre (plywood twist limit)
    #
    # GAP E6 — THE PROXY MEASURED THE WRONG QUANTITY. This check used to read
    #
    #     twist_rate = (beta_bow - beta_mid) / (beta_len * LWL)
    #
    # which is the MEAN twist over the warp length. The warp is quadratic, so
    # d(beta)/dx rises linearly from 0 at the aft end of the warp to 2x the
    # mean at the stem — and a mean averages a local fold away. A hull with one
    # unbuildable panel and nine flat ones passed. MEASURED over 400,000
    # uniform in-bounds vectors on the pre-P1 genome: the max/mean ratio had
    # median 1.774 (p95 1.869), the old mean check passed 93.180% of them and
    # the honest max metric passes 81.198%, so 12.243% of the box was blessed
    # on a number the sheet does not feel — and the worst true twist hiding
    # under a passing mean was 50.2 deg/m against this 14 deg/m limit.
    from . import geometry  # local: geometry imports this module at load time

    try:
        with np.errstate(divide="ignore", invalid="ignore"):
            # THE PROBE COMES FIRST, AND IT IS DENSER THAN THE HULL. `Hull`
            # solves the section at ITS OWN 41 stations, so a vector could pass
            # here and blow up inside `resistance.total_resistance`, which
            # rebuilds the same params at 161 stations for the Michell grid.
            # See `geometry.FEASIBILITY_PROBE_STATIONS` for the incident and
            # the density measurement.
            geometry.section_probe(x)
            hull = geometry.Hull(x)
            twist_rate = hull.panel_twist_rate()
        if not math.isfinite(twist_rate):
            raise ValueError(f"twist is {twist_rate}")
    except geometry.GeometryError as exc:
        name = "sac.target" if str(exc).startswith("sac:") else "section.solve"
        v.append(f"{name}: {exc}")
    except (ValueError, ZeroDivisionError, FloatingPointError) as exc:
        v.append(f"panel.twist: bottom twist not evaluable ({exc})")
    else:
        _rel("panel.twist", twist_rate <= MAX_PANEL_TWIST_DEG_PER_M,
             f"max bottom twist {twist_rate:.1f} deg/m > "
             f"{MAX_PANEL_TWIST_DEG_PER_M:.0f}", v)
        z_ch = float(hull.z_chine.max())
        _rel("chine.submerged", z_ch <= 0.0,
             f"chine {z_ch:.3f} m above the design waterline", v)
        _rel("chine.below.sheer", z_ch <= fb - 0.05, "chine reaches sheer", v)
        # `transom.chine` WAS HERE AND IS DELETED, on gap E4's rule and with
        # gap E4's evidence. It read `z_chine[0] <= 0.35 * T` — the transom
        # chine may not fly more than a third of a draft above the waterline —
        # and `chine.submerged` above now requires the chine to be at or below
        # the waterline at EVERY station, which subsumes it. MEASURED over
        # 40,000 uniform in-bounds vectors, 23,596 of which build: it fires on
        # ZERO of them. A constraint that cannot fire pads the count and
        # nothing else, and `tests/test_constraints_honest.py` refuses one.

    return GateReport(len(v) == 0, tuple(v))


def sample(n: int, rng: np.random.Generator | None = None,
           max_tries: int = 200, vessel=None) -> np.ndarray:
    """Rejection-sample n feasible parameter vectors (uniform in bounds).

    `vessel` is passed straight through to `check`, so sampling for a catamaran
    draws demihulls and sampling for nothing draws monohulls. MEASURED
    2026-08-14 over 4000 uniform draws (seed 1): 6.7% pass as a monohull and
    9.6% as a demihull, against 13.2% in the old, narrower box — the widened
    box costs about 2x the draws and `max_tries` of 200 leaves ~15x of headroom.
    """
    rng = rng or np.random.default_rng(0)
    out = np.empty((n, N_PARAMS))
    got = 0
    for _ in range(max_tries * n):
        cand = rng.uniform(LOW, HIGH)
        if check(cand, vessel).ok:
            out[got] = cand
            got += 1
            if got == n:
                return out
    raise RuntimeError(f"only {got}/{n} feasible samples after {max_tries * n} tries")


def named(x: np.ndarray) -> dict[str, float]:
    return {n: float(val) for n, val in zip(NAMES, np.asarray(x, dtype=float))}


def vector(d: dict[str, float]) -> np.ndarray:
    return np.array([d[n] for n in NAMES], dtype=float)
