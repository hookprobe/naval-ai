"""Shared numeric limits — ONE definition each, imported by everyone.

Why this module exists. The GM floor was hard-coded in four places (optimize.py
0.35, rules/iso12217.py 0.45 for category C, evaluate.py 0.35, translate.py
0.35) and the copies drifted. NSGA-II optimised to its own 0.35 bar, returned a
GM 0.40 m hull that was feasible by that constraint, and the rules gate then
rejected it. Nothing was broken except that two numbers meant to be the same
number were not.

PLM.md §1 platform law says a product may configure the kernel but never bypass
a gate. A threshold that exists twice IS a way to bypass a gate, so thresholds
live here, once. This module imports nothing from the package: `rules/` imports
`evaluate`, so anything `evaluate` needs must sit below both.
"""

from __future__ import annotations

import enum
import math

# ---------------------------------------------------------------------------
# WHAT KIND OF OBJECT IS THIS HULL? (2026-08-14)
#
# THE INCIDENT. `grammar.check` refused this project's own target — a catamaran
# with 12.0 x 0.8 m demihulls — on three clauses before any physics ran:
#
#     bound[BWL]: 0.8 outside [1.2, 6.0]
#     L/B: 15.00 outside [2.2, 8.5]
#     B/T: 1.33 outside [1.8, 12.0]
#
# NONE OF THOSE BANDS WAS WRONG. A 12 m MONOHULL 0.8 m wide would capsize and
# the band is right to refuse it. They were being applied to the wrong OBJECT:
# a demihull of a catamaran is not a monohull, and nothing in the tree could
# say so. The same error appeared three times in one day — this band, the ISO
# GM floor rejecting slender hulls, and `gate2m.py` printing KCS's EFD figure
# over a Wigley hull — which is one missing concept wearing three costumes.
#
# `mission.VesselConfig` (landed the same day) is the vessel contract and owns
# `n_hulls`. This enum is the ONE mapping from that count to the question every
# per-hull rule actually needs answered, and it lives here rather than in
# `grammar.py` because `rules/` needs the same answer and `rules/` must not
# import the grammar.
#
# THE DEFAULT IS MONOHULL AND IT IS NOT NEGOTIABLE. Anything this function
# cannot positively identify as a demihull keeps the monohull bands, because
# the monohull band is the STRICTER one and an unidentified object must not be
# granted the looser rule by accident. `hull_role(None)` is a monohull.


class HullRole(enum.Enum):
    """What the parameter vector describes: a whole vessel, or one of a pair.

    Two members, not six. `mission.EVALUABLE_TOPOLOGIES` is (monohull, catamaran) and refuses
    three, so a TRIMARAN role would be a member this tree cannot construct and
    cannot band — and a role with no band would silently fall back to the
    monohull one, which is the `${VAR:-0}` defect (LESSONS.md #1) wearing an
    enum. When `n_hulls = 3` becomes constructible, the member and its SOURCED
    bands arrive together or not at all.
    """

    MONOHULL = "monohull"
    DEMIHULL = "demihull"


def hull_role(vessel=None) -> HullRole:
    """The role of the hull described by a genome, given the vessel it is in.

    Accepts, deliberately, three things — a `HullRole`, anything carrying an
    `n_hulls` attribute (`mission.VesselConfig` is the one that matters), or
    `None`. Duck-typed on the attribute rather than imported, because
    `limits.py` imports nothing from this package by construction: `rules/`
    imports `evaluate`, so anything `evaluate` needs must sit below both.

    REFUSES a hull count it cannot interpret rather than defaulting it. A
    `n_hulls` of 0 or 2.5 is not a magnitude error a default could resolve; it
    is an unspecified vessel, and returning MONOHULL for it would hand the
    stricter-looking answer while hiding that the question was never answered.
    """
    if vessel is None:
        return HullRole.MONOHULL
    if isinstance(vessel, HullRole):
        return vessel
    n = getattr(vessel, "n_hulls", None)
    if n is None:
        raise TypeError(
            f"hull_role: {vessel!r} is neither a HullRole nor a vessel "
            f"configuration carrying `n_hulls`. A role guessed from an object "
            f"that does not declare one is a monohull verdict on a boat "
            f"nobody described.")
    if not (isinstance(n, int) and not isinstance(n, bool) and n >= 1):
        raise ValueError(
            f"hull_role: n_hulls = {n!r} is not a positive whole number of "
            f"hulls, so this vessel has no role to report")
    return HullRole.MONOHULL if n == 1 else HullRole.DEMIHULL


# ---------------------------------------------------------------------------
# WHICH STABILITY CRITERION GOVERNS — and the one this project cannot compute.
#
# THE HOLE POINTS THE OPPOSITE WAY FROM THE L/B BAND, AND THAT MAKES IT WORSE.
# The L/B band was a correct rule REFUSING a hull it should have accepted. The
# GM floor applied to a catamaran is a monohull criterion the catamaran passes
# TRIVIALLY while remaining capsizable, so it lets a dangerous vessel through.
#
# The physics is genuinely different, not merely scaled:
#   * MONOHULL — the righting-arm curve rises to a maximum and falls to zero at
#     the angle of vanishing stability; below it the boat self-rights. GM is the
#     initial slope of that curve, so a GM floor is a defensible proxy.
#   * MULTIHULL — the parallel-axis term A_wp*d^2 makes initial stability
#     enormous, so ANY GM floor is cleared by a wide margin. The failure mode is
#     elsewhere: once the windward hull lifts and the vessel passes peak
#     righting moment it capsizes AND IS STABLE INVERTED. GM is close to
#     irrelevant to whether that happens.
#
# This is why Directive 2013/53/EU Annex I A 3.3 (OJ L 354/115) says "All
# habitable multihull recreational craft susceptible of inversion shall have
# sufficient buoyancy to remain afloat in the inverted position", and why
# ISO 12217-1:2015 gives habitable multihulls a clause of their own (6.6, p.27,
# mapped by EN ISO 12217-1:2017 Annex ZA to BOTH RCD A 3.3 and A 3.8 Escape).


class StabilityCriterion(enum.Enum):
    """Which family of stability criterion applies to a vessel.

    `IMPLEMENTED` is a property of THIS CODEBASE, not of the criterion.
    """

    MONOHULL_GM_FLOOR = "monohull-gm-floor"
    MULTIHULL_RIGHTING_CURVE = "multihull-righting-curve"

    @property
    def implemented(self) -> bool:
        return self is StabilityCriterion.MONOHULL_GM_FLOOR


# THE SIGMA THE PRODUCT NEEDS (operator fix #4, derived 2026-08-20, the
# measured route: from the energy budget's own margins, not tradition).
# Wh/NM feeds exactly two product decisions: the solar-day verdict
# (net = solar - hotel - prop) and battery range (linear in 1/Wh_NM).
# MEASURED across the canonical fleet at their missions: the NEAREST
# verdict flip is 25.2% of Wh/NM away (case e; others 39..104%), so a
# calibrated band of +-10% leaves a >= 2.5x guard factor to the tightest
# decision the number participates in — while a paper-grade 2% GCI buys
# nothing any current verdict can feel. Gate 2M's calibration target is
# therefore THIS number; tightening it below 10% is a product decision
# that must name the verdict which needs it.
WH_PER_NM_SIGMA_PRODUCT = 0.10


def stability_criterion(vessel=None) -> StabilityCriterion:
    """The criterion family that governs, from the vessel's hull count."""
    return (StabilityCriterion.MONOHULL_GM_FLOOR
            if hull_role(vessel) is HullRole.MONOHULL
            else StabilityCriterion.MULTIHULL_RIGHTING_CURVE)


# THE MULTIHULL CRITERIA THAT EXIST, ARE FREE, AND WE STILL CANNOT RUN. Named
# in full so the refusal below cites evidence rather than gesturing at a gap,
# and so nobody re-researches this: it was swept out of
# `docs/research/standards/NATIONAL-CODES.md` and `docs/research/EU-REGULATORY.md`
# on 2026-08-14 and these are all of them.
#
# Every one of the three needs a RIGHTING-ARM CURVE. This ladder computes GM —
# one point, the slope at the origin — and no GZ(phi) at all, so not one of
# them is computable today. That is the missing evidence, and it is a missing
# COMPUTATION rather than a missing document, which is the useful half of the
# finding: the standards are free and in the tree, the physics is not.
MULTIHULL_RIGHTING_CRITERIA: tuple[tuple[str, str], ...] = (
    ("MCA Workboat Code Ed. 3 cl. 12B.3.9",
     "the broad-beam/multihull alternative to 12B.3.8: area under GZ >= 0.085 "
     "m.rad to theta_GZmax when theta_GZmax = 15 deg and >= 0.055 m.rad at "
     "30 deg, interpolated A = 0.055 + 0.002 (30 - theta_GZmax); area 30-40 "
     "deg (or theta_f) >= 0.03 m.rad; GZ >= 0.2 m at 30 deg; max GZ at >= 15 "
     "deg; GM0 >= 0.35 m"),
    ("AMSA NSCV Part C Subsection 6A Ch. 5B",
     "the catamaran alternative to Ch. 5A for operational areas B-E: max GZ at "
     "a heel >= 10 deg; heel <= theta_s under any single moment; crowding OR "
     "turning combined with the wind heeling lever must not heel the vessel "
     "more than 16 deg. Cl. 5B.1's area formula is recorded in "
     "NATIONAL-CODES.md as NOT SAFELY TRANSCRIBED (scrambled inline image) and "
     "is deliberately not quoted here"),
    ("Maritime NZ Part 40A App. 1 cl. 1.4",
     "multihulls >= 15 m LOA or > 50 passengers: area under GZ >= 0.055 * "
     "30/theta m.rad to theta = least of downflooding angle, angle of max GZ, "
     "30 deg; max GZ at >= 10 deg; heel due to steady wind <= 16 deg under "
     "h_w = P.A.Z / (9800 disp)"),
)

# WHAT WE WOULD NEED IN ORDER TO RUN ANY OF THEM. Stated as data rather than as
# prose so a later session can check the list off instead of re-deriving it.
MULTIHULL_CRITERION_INPUTS_MISSING: tuple[str, ...] = (
    "GZ(phi), the righting arm as a function of heel, to at least 40 deg — "
    "hydrostatics returns GM (the slope at phi = 0) and no curve",
    "the downflooding angle theta_f — `rules/iso12217.py` models downflooding "
    "as a HEIGHT (Annex A) and never as an angle",
    "the projected windage area above the waterline and the height of its "
    "centroid above the centre of lateral underwater area — the genome "
    "declares no superstructure, so there is nothing to project",
)

# The refusal text itself. ONE string, so the rules tier, the ladder and any
# report say the same sentence.
MULTIHULL_STABILITY_UNASSESSED = (
    "MULTIHULL STABILITY IS NOT ASSESSED. A metacentric-height floor is the "
    "MONOHULL criterion; a catamaran clears any GM floor by a wide margin "
    "because of the parallel-axis A_wp*d^2 term and can still capsize and stay "
    "inverted, which is why RCD 2013/53/EU Annex I A 3.3 legislates inversion "
    "for habitable multihulls and ISO 12217-1:2015 gives them clause 6.6. "
    "PASSING THE GM FLOOR ESTABLISHES NOTHING ABOUT THIS VESSEL'S SAFETY. "
    "Three free, sourced criteria would apply "
    "(see limits.MULTIHULL_RIGHTING_CRITERIA) and all three need a righting-arm "
    "curve this ladder does not compute "
    "(see limits.MULTIHULL_CRITERION_INPUTS_MISSING).")


# THE ONE MULTIHULL BAR THAT *IS* COMPUTABLE FROM WHAT THIS LADDER HAS.
#
# Maritime NZ, Maritime Rule Part 40A Appendix 1 cl. 1.3: a multihull decked
# ship under 15 m LOA carrying <= 50 passengers "must be tested to establish
# that, in the fully loaded condition, the ship does not heel or trim in any
# direction by more than 8 deg when subject to uncontrolled passenger
# crowding"; cl. 1.1 tabulates the same offset-load limit as <= 15 deg for a
# monohull and <= 8 deg for a multihull. Transcribed in
# `docs/research/standards/NATIONAL-CODES.md` (cl. 1.3 and the offset-load
# table). The footnote matters and is why we may use it: "The heel test may be
# established by a physical test or by calculation."
#
# WHY IT IS HERE AND NOT A SECOND OPINION ON R-OLH. `rules/iso12217.py` already
# computes the crowding heel; this is a BAR on that same measurement, not a
# second measurement. It is applied as the STRICTER of the two, because ISO
# 12217-1's Table 4 limit (11.5-22.7 deg by length) sits in a part whose
# multihull provisions are clause 6.6 — text this project does not hold — so
# applying Table 4 to a catamaran is itself an unexamined extrapolation.
#
# 8 deg BITES: at LH = 12 m ISO Table 4 allows 14.8 deg, so this is 1.8x
# stricter on exactly the vessel the product line is built around.
MULTIHULL_OFFSET_LOAD_HEEL_LIMIT_DEG = 8.0
MULTIHULL_OFFSET_LOAD_SOURCE = (
    "Maritime NZ Maritime Rule Part 40A App. 1 cl. 1.3 (multihull heeling "
    "test, < 15 m LOA, <= 50 passengers) and cl. 1.1 (offset load: <= 15 deg "
    "monohull, <= 8 deg multihull); see docs/research/standards/"
    "NATIONAL-CODES.md")
MULTIHULL_OFFSET_LOAD_SCOPE_LOA_M = 15.0


# ---------------------------------------------------------------------------
# THE LENGTH RANGE IN WHICH THIS PRODUCT'S WHOLE COMPLIANCE TIER EXISTS.
#
# Directive 2013/53/EU (RCD) Art. 3(2), OJ L 354/95: "'recreational craft'
# means any watercraft of any type, excluding personal watercraft, intended for
# sports and leisure purposes OF HULL LENGTH FROM 2,5 m TO 24 m, regardless of
# the means of propulsion". Outside that band the RCD is not the instrument
# that governs the craft, ISO 12217-1 and ISO 12215-5 are not the standards
# that implement it, and the design categories do not apply — so a hull there
# would be scored by a compliance tier with nothing to say about it, which is
# the `gate2m.py` printing KCS's EFD over a Wigley hull defect wearing a
# regulation.
#
# IT LIVES HERE BECAUSE TWO LAYERS THAT MAY NOT SEE EACH OTHER BOTH NEED IT.
# `policy/legal.py` wraps it in a `PolicyValue` to route conformity modules;
# `grammar.PARAMS` uses it as the LWL box, added 2026-08-14 when that box was
# widened from an unsourced [4, 20]. The ladder must never import
# `navalai.policy` (CLAUDE.md, and `tests/test_policy.py` fences it), so the
# tuple cannot live in `legal.py` and be read by the grammar — and a second
# copy in `grammar.py` is the defect this module exists to end. `limits.py`
# imports nothing and sits below both, which is exactly the case it is for.
#
# LOA == LWL by construction in this grammar (there is no stem rake and no
# overhang — see `formlib`'s `_M_STEM`), so bounding LWL bounds hull length.
# Where the two ever diverge, L_H >= L_WL and the error is in the REFUSING
# direction, which is the same convention `rules/iso12217.hull_length_m` uses.
RCD_HULL_LENGTH_SCOPE_M = (2.5, 24.0)


# ---------------------------------------------------------------------------
# WHERE THE FRICTION MODEL STOPS BEING VALID, WHICH IS A FUNCTION OF SIZE
#
# WIDENING THE PARAMETER BOX EXPOSES HULLS THE PHYSICS CANNOT HONESTLY SCORE,
# and that is acceptable ONLY if the ladder refuses them by name. `resistance`
# already does exactly this at the top end — above `FN_MICHELL_MAX` the result
# is returned with `valid = False` and badged `L1-INVALID`, which `evaluate`
# ranks BELOW `L0`. There was no equivalent at the bottom end.
#
# MEASURED 2026-08-14 at `resistance.NU_FRESH_15C` = 1.14e-6 m2/s:
#
#     Lwl     speed    Fn      Re        ITTC-57 valid?
#     1.0 m   3 kn    0.493   1.35e6     transitional, and Fn is over the bar
#     1.0 m   2 kn    0.329   9.03e5     TRANSITIONAL — Re below 5e6
#     12.0 m  6 kn    0.284   3.25e7     yes
#
# So a 1 m hull crosses `FN_MICHELL_MAX` at 2.74 kn AND sits in the
# laminar-turbulent transition below that: there is no speed at which both
# halves of `total_resistance` are inside their envelopes. A 12 m hull at 6 kn
# is comfortable in both. The band is a property of SIZE, so the box that lets
# a 2.5 m hull be expressed is the box that needs this constant.
#
# PROVENANCE, STATED PLAINLY. The transition edges are the classical smooth
# flat-plate values — transition begins near Re_x = 5e5 and the boundary layer
# is fully turbulent by roughly Re_x = 5e6 — and this project holds no text it
# can cite for them, so their basis is 'approx' in the sense `rules/review.py`
# uses the word. What is NOT approximate is the consequence: the ITTC-1957
# model-ship correlation line is a FULLY TURBULENT line, and reading it inside
# the transition region is reading it outside the regime it correlates. That is
# why model basins fit turbulence stimulators.
RE_TRANSITION_BAND = (5.0e5, 5.0e6)


def friction_line_validity(re: float) -> tuple[bool, str]:
    """Is ITTC-57 inside its regime at this Reynolds number, and if not, why.

    C-31, THE POLICY SPLIT DECLARED: this is the STRICT designer-facing
    question — inside the transition band counts as NOT valid. The wired
    evaluation policy lives in `resistance.flow_regime`: it refuses only
    below the band's onset and REPORTS (with a receipt) inside the band,
    for the measured-decision reasons documented at its constants. Both
    read the ONE band, RE_TRANSITION_BAND, above.

    Returns `(valid, reason)`; `reason` is empty exactly when `valid` is True.
    A REASON, not a bool, for the same purpose `resistance.FormFactor` carries
    its raw estimate: a caller that only learns "invalid" cannot tell the
    designer which way to move.

    Refuses a non-finite or non-positive Reynolds number rather than reporting
    it valid — an unmeasurable quantity scored as a passing one is this
    repository's defect class 1.
    """
    lo, hi = RE_TRANSITION_BAND
    if not (isinstance(re, (int, float)) and math.isfinite(re) and re > 0.0):
        return False, (f"Reynolds number is {re!r}, so no friction line can be "
                       f"said to apply")
    if re >= hi:
        return True, ""
    if re >= lo:
        return False, (
            f"Re {re:.3g} is inside the laminar-turbulent transition "
            f"{lo:.0e}-{hi:.0e}; ITTC-57 is a FULLY TURBULENT correlation line "
            f"and is being read outside the regime it correlates")
    return False, (
        f"Re {re:.3g} is below the transition floor {lo:.0e}; the boundary "
        f"layer is laminar and ITTC-57 does not describe it at all")


def min_lwl_for_turbulent_flow_m(speed_ms: float, nu_m2_s: float) -> float:
    """Shortest waterline at which ITTC-57 is inside its regime at `speed_ms`.

    `nu` is REQUIRED and has no default. `resistance.py` owns the kinematic
    viscosity of water (`NU_FRESH_15C`, `nu_water(rho)`) and a default here
    would be that number declared twice — the defect this module was created
    to end. `limits.py` imports nothing from the package, so the caller passes
    it in.
    """
    for name, v in (("speed_ms", speed_ms), ("nu_m2_s", nu_m2_s)):
        if not (isinstance(v, (int, float)) and math.isfinite(v) and v > 0.0):
            raise ValueError(f"min_lwl_for_turbulent_flow_m: {name} = {v!r} "
                             f"is not a positive finite number")
    return RE_TRANSITION_BAND[1] * nu_m2_s / speed_ms


# ISO 12217-1 design categories.
#   (significant wave height context [m], downflooding floor [m],
#    GM floor [m], max offset-load heel [deg])
# Values carry basis='approx' where they are practice figures rather than
# licensed standard text — see rules/ for the per-finding provenance and the
# PURCHASE queue that upgrades them.
# Column 2 (downflooding) and column 4 (offset-load heel) are the ISO 12217-1
# LIMITS, not the requirement itself: both requirements are FORMULAS in the
# standard and are computed in `rules/iso12217.py`.
#
# CORRECTED 2026-08-12 against ISO 12217-1:2015 (Third edition, 2015-10-15),
# Annex A Table A.1 and Table 4. The previous values were engineering-practice
# stand-ins with the WRONG MODEL, not merely the wrong numbers:
#
#   downflooding was a fixed per-category floor (0.65 / 0.50 / 0.35 / 0.25 m).
#   The standard computes hD(R) = (LH/15) * F1*F2*F3*F4*F5 (A.1) and then
#   CLAMPS it to Table A.1. So the requirement scales with hull length and the
#   old column could not have been right at more than one length.
#
#   offset-load heel was a per-CATEGORY constant (10/10/10/12 deg). The
#   standard makes it a function of LENGTH ONLY (6.2.3 a):
#   phi_O(R) = 11.5 + (24 - LH)^3 / 520. A 6 m boat is allowed 22.7 deg, not
#   10 -- the old bar was more than twice as strict at the small end and the
#   category played no part in it at all.
#
# Column 3 (GM floor) is OURS. Nothing in 12217-1:2015 sets an absolute
# metacentric floor -- it governs offset-load heel, downflooding and
# wave/wind resistance instead -- so R-GM is listed in review.NOT_FROM_STANDARD
# and its basis is 'approx'. It is kept because a GM floor is a useful L1
# feasibility bar, not because a standard demands it.
#
# Table A.1 columns are (min, max) per category, taking the option-1 column for
# A, options 1+3 for B, and options 2/4/5 for C and D -- we do not model the
# six assessment options, so the more common column is used and said out loud.
# D under options 2/4/5 has max 0.4 m; D under option 6 has no upper limit.
CATEGORY_TABLE: dict[str, tuple[float, float, float, float]] = {
    "A": (4.0, 0.50, 0.60, 1.41),
    "B": (4.0, 0.40, 0.50, 1.41),
    "C": (2.0, 0.30, 0.45, 0.75),
    "D": (0.3, 0.20, 0.35, 0.40),
}

# Minimum freeboard [m] used as an L1 feasibility floor and an optimizer
# constraint. Not an ISO number; a build-sense floor.
FREEBOARD_FLOOR_M = 0.25

# Plywood cold-bend limit: sheet thickness [m] and the minimum bend radius as a
# multiple of it. These two are consumed by the optimizer's bend constraint AND
# by the weight model's panel thickness; keeping them together stops the sheet
# changing in one place without the bend limit following.
#
# PLY_THICKNESS_M is the NOMINAL stock sheet — topsides, deck, and the floor for
# anything the scantling rule does not size. It is NOT the bottom-panel
# thickness. MEASURED 2026-08-05: ISO 12215-5 wants 15 mm only below
# mLDC = 845 kg, so this sheet failed the platform's own rule for EVERY SKU in
# PLM.md (Dayboat 1-3 t needs 15.2-16.9 mm, the 6 t Solar Liveaboard 18.24 mm).
# The demo hid it by hand-passing provided_mm=20.0 — a fourth thickness that
# existed nowhere else. The bottom panel is now DERIVED from the rule
# (`rules.iso12215.select_stock_thickness_m`) instead of declared here, so the
# contradiction is impossible by construction rather than by discipline.
PLY_THICKNESS_M = 0.015
BEND_RADIUS_RATIO = 80.0

# Marine plywood is sold in discrete sheets, so a derived requirement of
# 18.24 mm means you buy 21 mm and carry its weight. Rounding UP to stock is
# what makes the derived thickness a buildable number rather than an arithmetic
# result. Extend this tuple, do not round the requirement down to meet it.
STOCK_PLY_THICKNESS_M = (0.006, 0.009, 0.012, 0.015, 0.018, 0.021, 0.025)

# Transverse frame spacing [m] = the ISO 12215-5 panel short span `b`.
# It lived as a bare 400 mm default inside the scantling checker while
# `engineer.py` built bulkheads 1.4 m apart and modelled no frames between
# them, so the two modules described different boats: at 1400 mm the same rule
# wants 63.8 mm of plywood. One number, consumed by both.
FRAME_SPACING_M = 0.40

# ISO default person mass [kg]. It was declared only inside the rules tier,
# where it drove the offset-load heel, while the weight budget carried a flat
# 800 kg payload regardless of crew — so a 12-crew boat put 1020 kg on the rail
# for the stability check and floated at exactly the 2-crew displacement.
CREW_MASS_KG = 85.0


def gm_floor(category: str) -> float:
    """Metacentric-height floor [m] for an ISO 12217 design category."""
    if category not in CATEGORY_TABLE:
        raise ValueError(f"unknown design category {category!r}")
    return CATEGORY_TABLE[category][2]


def min_bend_radius_m(thickness_m: float = PLY_THICKNESS_M) -> float:
    """Minimum cold-bend radius [m] for a plywood sheet of `thickness_m`."""
    return BEND_RADIUS_RATIO * thickness_m


# Static attitude from the ARRANGEMENT alone (no crew movement, no seaway).
# Not an ISO number: 12217 governs stability, not trim. This is the design
# bar we hold ourselves to, so that moving mass has a consequence the ladder
# can report. MEASURED on the mid hull with the default bucket placement:
# trim +0.91 deg, list 0.00 deg — so the bar is a real constraint, not a
# rubber stamp, and not one tuned to whatever the current model happens to give.
TRIM_LIMIT_DEG = 2.0
LIST_LIMIT_DEG = 2.0


# LONGITUDINAL CENTRE OF BUOYANCY band, as a percentage of the floated
# waterline length, signed negative aft of midships.
#
# LCB WAS UNCONSTRAINED ANYWHERE IN THE LADDER (gap B8). It is one of the two
# or three numbers a naval architect fixes first, because it sets where the
# displacement sits against the LCG the arrangement will produce; a hull whose
# buoyancy is far aft either trims by the bow when loaded or needs its whole
# interior pushed aft to compensate. The ladder computed `HydroState.lcb`,
# used it for trim, and never asked whether it was a sane place for it to be.
# MEASURED on delivered hulls: -6.47 and -7.86 %LWL, and still -5.3..-7.3 with
# length pinned to the mission hint.
#
# The band is +-3%, which is displacement-hull practice (Holtrop's own lcb
# regressor spans roughly -4..+2% for the merchant hulls behind it, and small
# displacement craft are conventionally drawn within a few percent of
# midships). It is a PRACTICE figure, basis='approx' in the sense rules/ uses
# the word, not a licensed standard text.
#
# HOW HARD IT BITES, MEASURED before it was adopted, on 200 L0-feasible hulls
# floated to a 6 t mission displacement:
#
#     min -13.21 | p05 -7.17 | median -0.85 | p95 +8.50 | max +14.79
#     inside +-3%: 46.5%
#
# So it is a real constraint on a real trade — it removes half the box, not
# 1% of it and not 99% — which is what distinguishes it from `keel.rocker`
# (0 hits in 400,000, deleted) at one end and from a bar nothing can meet at
# the other. RECORDED, NOT SOFTENED: the hand-picked reference hull
# `tests/test_phase0.mid_params` sits at -6.48% and is now INFEASIBLE by this
# constraint. That is information about the reference hull.
LCB_BAND_PCT_LWL = 3.0


# PRISMATIC COEFFICIENT AS A FUNCTION OF DESIGN FROUDE NUMBER.
#
# THE OPTIMUM Cp IS NOT A BAND, IT IS A CURVE, and writing it as a band is the
# defect this repository keeps paying for in another disguise: a number that
# should be a function of something. The plate-P1 brief originally quoted a
# fixed 0.55-0.62 target; that bakes ONE design speed into the geometry kernel
# forever. A displacement hull at Fn 0.24 wants a finer prismatic than a
# semi-displacement hull at Fn 0.45, because the optimum tracks the position of
# the transverse-wave hump: at low Fn the residuary resistance is minimised by
# keeping the ends fine, and as speed rises the volume has to move outboard and
# aft to delay and flatten the hump.
#
# PROVENANCE, STATED HONESTLY: this table is NOT transcribed from a licensed
# standard or from a series report this session could open. It is a PRACTICE
# curve — the shape is the classical Taylor/Saunders "recommended prismatic"
# relation that every small-craft text reproduces, pinned to the three anchors
# the project owner stated (Cp ~0.55 at Fn 0.24, ~0.60 near Fn 0.35, 0.68+ once
# dynamic lift matters). Its basis is 'approx' in the sense `rules/` uses the
# word, and a citation is OWED: when one is obtained the numbers change HERE
# and nowhere else, which is the whole point of it being a table rather than an
# expression scattered through the kernel.
#
# It is deliberately a TABLE with linear interpolation and not a fitted
# polynomial. An unsourced curve is better than an unsourced curve pretending
# to be physics, and a polynomial invites the next reader to differentiate it.
PRISMATIC_BY_FROUDE: tuple[tuple[float, float], ...] = (
    (0.15, 0.525),
    (0.20, 0.535),
    (0.24, 0.550),
    (0.30, 0.575),
    (0.35, 0.600),
    (0.40, 0.635),
    (0.45, 0.660),
    (0.50, 0.680),
    (0.60, 0.710),
)

# How far a design may sit from the Fn-derived prismatic and still be called
# on target. It is the plate-P1 acceptance bar and it is a TOLERANCE on the
# kernel's aim, not a design band: the kernel either delivers the prismatic it
# was asked for or it does not.
PRISMATIC_TOLERANCE = 0.01


def prismatic_target(fn: float) -> float:
    """Design prismatic coefficient for a design Froude number.

    ONE definition. `geometry.sac_exponents` takes a target rather than owning
    one, `grammar.PARAMS` bounds `Cp` to this table's span, and the plate-P1
    acceptance test measures the DELIVERED prismatic against this function —
    so there is no second copy of the relation to drift.

    Clamped at both ends rather than extrapolated: outside the tabulated Froude
    range the practice curve has no content, and extrapolating a curve whose
    provenance is 'approx' would manufacture precision it does not have.
    """
    fns = [f for f, _ in PRISMATIC_BY_FROUDE]
    cps = [c for _, c in PRISMATIC_BY_FROUDE]
    if fn <= fns[0]:
        return cps[0]
    if fn >= fns[-1]:
        return cps[-1]
    for (f0, c0), (f1, c1) in zip(PRISMATIC_BY_FROUDE, PRISMATIC_BY_FROUDE[1:]):
        if f0 <= fn <= f1:
            return c0 + (c1 - c0) * (fn - f0) / (f1 - f0)
    raise AssertionError("unreachable: PRISMATIC_BY_FROUDE is not monotone")


# The span of the table above, as the `Cp` gene's declared bounds. Written here
# so the gene cannot be bounded somewhere the target function can reach — or,
# worse, somewhere it cannot, which would make the acceptance bar unreachable
# by construction at one end of the speed range.
CP_GENE_BOUNDS = (PRISMATIC_BY_FROUDE[0][1], PRISMATIC_BY_FROUDE[-1][1])


# GM CEILING as a fraction of waterline beam. GM has always had a floor (the
# ISO category table) and never a ceiling, and `optimize.py` MAXIMISED it as an
# objective. That is not a naval-architecture goal: a stiff boat has a violent
# roll and high rig loads. MEASURED on a delivered 1.5 t dayboat: GM/B 0.821
# and a 1.5 s roll period, where small craft sit at 0.08-0.20 and 3-5 s.
# Used as the top of the band the optimiser now aims at, not as a hard bar —
# a genuinely beamy shallow hull can exceed it for good reasons.
GM_OVER_BEAM_MAX = 0.20
