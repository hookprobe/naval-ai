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
CATEGORY_TABLE: dict[str, tuple[float, float, float, float]] = {
    "A": (4.0, 0.65, 0.60, 10.0),
    "B": (4.0, 0.50, 0.50, 10.0),
    "C": (2.0, 0.35, 0.45, 10.0),
    "D": (0.3, 0.25, 0.35, 12.0),
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
