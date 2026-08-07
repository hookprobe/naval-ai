"""Tier E as an executable checker — the reference data given a consumer.

`navalai/refdata/ergonomics.py` carries ~40 sourced constants and, until this
module, ZERO consumers. A dead-code audit ruled them KEEP because Gate V2.0's
bar is provenance rather than consumption, which is correct and also not the
whole story: BuildPlan 2's product architecture wants an ergonomics stage that
PENALISES a design, and a constant nothing divides by has never been wrong.

This module wires TWO of them into one bar that a hull can fail:

  E-DECK  the craft must be able to accommodate its declared crew, against
          the working deck it actually has.

WHAT IT MEASURES, AND WHAT IT DOES NOT
--------------------------------------
ISO 15085:2024's requirement (`MAX_PERSONS_MUST_FIT_IN_Z1_PLUS_INTERIOR`) is
that the maximum persons fit within deck zone Z1 plus the interior. We model
neither zones nor interior joinery, so the measurand is the WORKING DECK PLAN
AREA and the check is a NECESSARY condition, not a sufficient one:

  - Passing does not mean the boat seats the crew. The whole deck is counted
    as if seating could go anywhere on it — no console, no cabin, no side-deck
    reservation, no Z1 boundary. A real layout takes area away and never adds
    it, so the real answer is always worse than this one.
  - Failing IS decisive. If the crew do not fit on the entire deck, they do
    not fit in a subset of it.

That asymmetry is the reason this ships as a bar at all. It is stated in the
finding's note as well as here, because a necessary-condition check read as a
verdict is exactly the failure mode `gate2m.py` had.

THE SLOPE RULE IS A SCOPE RULE, NOT A BAR. `WORKING_DECK_SLOPE_MAX_*` is
recorded in refdata with the note "surfaces steeper than this are excluded
from the working-deck definition — i.e. they do not COUNT, which is a scope
rule, not a bar". So it is applied as an EXCLUSION: deck forward of the point
where the sheer line pitches past 25 deg stops counting toward the area, and
does not by itself fail anything. Every hull this grammar emits has a flat
transverse deck, so only the longitudinal limit can bind; the transverse
constant is deliberately not used and `not_applicable()` says why.

WHERE THAT LIMB BINDS, MEASURED — because "it excluded nothing" is a claim
about the HULL, not evidence of a broken check. The deck lid rises with the
bow sheer, so its steepest panel is at the stem and is, in closed form,

    slope_max = atan( 2 * sheer_rise * D / (LWL * (1 - x_mb)) )

MEASURED 2026-08-07 on grammar hulls at the sheer_rise CEILING (0.5) with
otherwise mid parameters (D 1.55 m, x_mb 0.55), panel slopes off `Hull`:

    LWL  4.0 m -> 39.9 deg   EXCLUDES     LWL  7.0 m -> 25.6 deg  EXCLUDES
    LWL  5.0 m -> 33.8 deg   EXCLUDES     LWL  7.4 m -> 24.3 deg  keeps all
    LWL  6.0 m -> 29.2 deg   EXCLUDES     LWL 10.0 m -> 19.0 deg  keeps all

So the limb is live code — it fires below ~7.2 m — and on a 10 m hull it
excludes NOTHING even at the maximum sheer the grammar admits, because a
775 mm rise spread over 4.5 m of deck is a 19 deg ramp and ISO's bound is 25.
That is the right answer for that hull, and it is recorded here so the next
reader does not "fix" a check that is working by lowering a standard's number.

TWO BASIS VOCABULARIES MEET HERE AND THEY ARE NOT THE SAME WORD. `RuleFinding.
basis` is the Gate 6R vocabulary — 'standard' means A NAMED REVIEWER CONFIRMED
IT ON A DATE, which is why it comes from `review.basis_for(rule_id)` and reads
'approx' for E-DECK. `refdata`'s basis is a PROVENANCE vocabulary
('standard-2003' | 'approx' | 'purchased') about where the number was
transcribed from. A derived number is only as attributable as its least
attributable input, so `weakest_basis()` reports the refdata side in the note.
Writing 'standard-2003' into the RuleFinding field would have made
`rules.report()['unreviewed_bases']` drop a rule nobody has reviewed.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from ..geometry import Hull

from ..refdata import RefValue
from ..refdata.ergonomics import (MAX_PERSONS_MUST_FIT_IN_Z1_PLUS_INTERIOR,
                                  SEAT_MIN_MM,
                                  WORKING_DECK_SLOPE_MAX_LONGITUDINAL_DEG,
                                  WORKING_DECK_SLOPE_MAX_TRANSVERSE_DEG)
from . import RuleFinding
from .review import basis_for

_BASIS_RANK = {"standard-2003": 2, "purchased": 2, "approx": 1}


def weakest_basis(*vals: RefValue) -> str:
    """The least attributable basis among the inputs to a derived number.

    A result computed from a transcribed standard value and a preview value is
    a preview-grade result. Combining them and reporting the stronger basis is
    how false provenance gets manufactured one derivation at a time.
    """
    return min((v.basis for v in vals), key=lambda b: _BASIS_RANK.get(b, 0))


def seat_area_m2() -> float:
    """Plan area one person needs, from `SEAT_MIN_MM` (width, depth)."""
    w_mm, d_mm = SEAT_MIN_MM.value
    return (float(w_mm) / 1e3) * (float(d_mm) / 1e3)


def deck_panel_slope_deg(hull: "Hull") -> np.ndarray:
    """Longitudinal slope of each deck-lid PANEL [deg], transom -> stem.

    The working deck this geometry builds is the lid between the port and
    starboard sheer lines: `Hull.closed_mesh` lays it as
    `quad(S[i], P[i], P[i+1], S[i+1])` with both edges of a station at the same
    z, so the lid height depends on x alone. A surface z = f(x) has its
    steepest ascent along x and is horizontal athwartships, which is why ONE
    slope per panel describes it completely and the transverse limb is
    identically zero (`not_applicable()` says so, with the reason).

    Measured PER PANEL rather than by `np.gradient` over the stations. A
    central difference averages the two panels either side of a station, so one
    steep panel between two gentle ones reads as two moderate ones and the
    exclusion silently understates itself — the same shape of defect as the
    snappy layer table that reported the REQUESTED spec as the achieved one.
    """
    x = np.asarray(hull.x, dtype=float)
    z = np.asarray(hull.z_sheer, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.degrees(np.arctan(np.abs(np.diff(z) / np.diff(x))))


def working_deck_area_m2(hull: "Hull") -> tuple[float, float]:
    """(counting deck area [m2], excluded area [m2]) under the slope scope rule.

    Deck plan area is `2 * int(y_sheer dx)` — the same integral
    `Hull.deck_area()` performs — PARTITIONED over the panels whose
    longitudinal slope is within `WORKING_DECK_SLOPE_MAX_LONGITUDINAL_DEG`.
    The two returned numbers sum to `deck_area()` by construction: each panel's
    trapezoid `(y_i + y_i+1) * dx` lands in exactly one of the two bins, so the
    excluded area is not a second measurement of the same quantity computed a
    different way (the two-copies defect) and cannot disagree with the total.

    That partition replaces a per-STATION mask, `2 * trapezoid(where(keep, y,
    0), x)`, which is not a partition at all: a panel between a kept station
    and an excluded one contributes half its area to the counting integral and
    half to nothing, so the boundary of the excluded region was smeared over
    one panel in each direction and `total - counting` had to be clamped at
    zero to stay positive.

    An unreadable hull is REFUSED, not scored. A NaN in the sheer makes every
    `slope <= limit` comparison False, which would have silently excluded the
    whole deck and reported a hard, finite 0.00 m2 of working deck — an
    unmeasurable metric scored as a measured catastrophe. Both numbers come
    back NaN instead and `assess()` turns that into UNMEASURABLE.
    """
    x = np.asarray(hull.x, dtype=float)
    y = np.asarray(hull.y_sheer, dtype=float)
    z = np.asarray(hull.z_sheer, dtype=float)
    if not (np.all(np.isfinite(x)) and np.all(np.isfinite(y))
            and np.all(np.isfinite(z))):
        return float("nan"), float("nan")

    panel = (y[:-1] + y[1:]) * np.diff(x)     # 2 * trapezoid of one panel
    slope_deg = deck_panel_slope_deg(hull)
    keep = slope_deg <= float(WORKING_DECK_SLOPE_MAX_LONGITUDINAL_DEG.value)
    return float(panel[keep].sum()), float(panel[~keep].sum())


def not_applicable() -> dict[str, str]:
    """Constants this checker deliberately does NOT apply, and why.

    Returned as data so a reader does not have to infer an omission from
    silence — the same reason `refdata.NOT_SOURCED` exists.
    """
    return {
        "WORKING_DECK_SLOPE_MAX_TRANSVERSE_DEG": (
            f"{WORKING_DECK_SLOPE_MAX_TRANSVERSE_DEG.value} deg. The deck lid "
            f"this geometry builds is flat athwartships at every station, so "
            f"the transverse slope is identically 0 and the rule can never "
            f"bind. Applying it would add a check that cannot fire — the "
            f"defect gap E4 deleted four of."),
        "SIDE_DECK_WIDTH_MIN_MM": (
            "needs a superstructure to measure a side deck AGAINST; no "
            "deckhouse is modelled, so there is no side deck to be too narrow."),
    }


def assess(hull: "Hull", crew: int) -> list[RuleFinding]:
    """E-DECK for one hull and a declared crew count.

    An unreadable crew count is FATAL, not a default of one: the whole point
    of the bar is that it scales with the people aboard.
    """
    basis = basis_for("E-DECK")
    prov = weakest_basis(SEAT_MIN_MM, WORKING_DECK_SLOPE_MAX_LONGITUDINAL_DEG,
                         MAX_PERSONS_MUST_FIT_IN_Z1_PLUS_INTERIOR)
    clause = ("ISO 15085:2024 (max persons accommodated in Z1 + interior); "
              "ISO 15085:2003 working-deck slope scope rule")
    try:
        n = int(crew)
    except (TypeError, ValueError):
        n = -1
    if n <= 0:
        return [RuleFinding(
            "E-DECK", clause, basis, False, float("nan"), float("nan"),
            "m2", f"crew count {crew!r} is not a positive integer — the "
                  f"accommodation requirement is UNMEASURABLE, so no verdict "
                  f"is issued (refdata provenance {prov})")]

    counting, excluded = working_deck_area_m2(hull)
    required = n * seat_area_m2()
    if not math.isfinite(counting):
        return [RuleFinding(
            "E-DECK", clause, basis, False, float("nan"), required, "m2",
            "working deck area is not finite — UNMEASURABLE, no verdict")]
    return [RuleFinding(
        "E-DECK", clause, basis, counting >= required, counting, required,
        "m2",
        f"{n} persons x {seat_area_m2():.3f} m2 "
        f"({SEAT_MIN_MM.value[0]:.0f} x {SEAT_MIN_MM.value[1]:.0f} mm incl. "
        f"foot space) against {counting:.2f} m2 of working deck; "
        f"{excluded:.2f} m2 excluded for exceeding the "
        f"{WORKING_DECK_SLOPE_MAX_LONGITUDINAL_DEG.value} deg longitudinal "
        f"slope that bounds the working-deck definition. NECESSARY CONDITION "
        f"ONLY: the whole deck plan is counted, with no console, cabin, side "
        f"deck or Z1 boundary taken out, so a pass does not mean the crew fit "
        f"— a fail means they do not. Refdata provenance: {prov}.")]


__all__ = ["assess", "seat_area_m2", "working_deck_area_m2",
           "deck_panel_slope_deg", "not_applicable", "weakest_basis",
           "basis_for"]
