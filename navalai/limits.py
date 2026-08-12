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


# GM CEILING as a fraction of waterline beam. GM has always had a floor (the
# ISO category table) and never a ceiling, and `optimize.py` MAXIMISED it as an
# objective. That is not a naval-architecture goal: a stiff boat has a violent
# roll and high rig loads. MEASURED on a delivered 1.5 t dayboat: GM/B 0.821
# and a 1.5 s roll period, where small craft sit at 0.08-0.20 and 3-5 s.
# Used as the top of the band the optimiser now aims at, not as a hard bar —
# a genuinely beamy shallow hull can exceed it for good reasons.
GM_OVER_BEAM_MAX = 0.20
