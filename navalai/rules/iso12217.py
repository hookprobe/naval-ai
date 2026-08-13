"""ISO 12217-1 (motor craft >= 6 m) — simplified stability assessment.

Implemented tests (each a typed executable checker with clause provenance):
  R-SCP  SCOPE: does 12217-1 govern this hull at all
  R-DFH  downflooding height vs design-category floor
  R-OLH  offset-load heel (crew crowding to one side)
  R-GM   metacentric-height floor per category — MONOHULLS ONLY
  R-MHS  multihull stability: REFUSED, not assessed (see below)
  R-CAT  category context (significant wave height the category implies)

WHICH STABILITY CRITERION APPLIES IS A FUNCTION OF TOPOLOGY, NOT ONLY OF
DESIGN CATEGORY (2026-08-14). `CATEGORY_TABLE` already varies the bars by
category; nothing varied them by hull count, and the two are ORTHOGONAL — a
category C catamaran and a category A catamaran face different sea states, and
a category C catamaran and a category C monohull face different FAILURE MODES.

A GM floor is the monohull criterion: GM is the initial slope of a righting-arm
curve that rises, peaks and vanishes, and below the angle of vanishing stability
a monohull self-rights. A catamaran's parallel-axis A_wp*d^2 term makes its GM
enormous, so it clears any GM floor by a wide margin AND CAN STILL CAPSIZE AND
STAY INVERTED. Reporting `R-GM PASS` for one is a green tick on the quantity
that does not govern — the same defect class as `gate2m.py` printing KCS's EFD
figure over a Wigley hull, pointed in the DANGEROUS direction: the L/B band that
started this work was a correct rule refusing a safe hull, and this is a
criterion admitting an unassessed one.

So for `n_hulls > 1` R-GM is WITHHELD (R-SCP's precedent: findings from a
standard we do not implement are not produced at all) and R-MHS refuses with
0 of 1 criteria assessed. R-OLH still runs, against the STRICTER of ISO's
length-based limit and a free multihull limit — see
`limits.MULTIHULL_OFFSET_LOAD_HEEL_LIMIT_DEG`.

Thresholds basis='approx': engineering-practice values standing in until the
licensed standard text parity review (BuildPlan Gate 6). The MECHANICS
(moment balance, geometry) are exact.

THE SCOPE OF THE STANDARD IS PART OF THE STANDARD (gap G8). This module is
named for ISO 12217-**1**, whose own title restricts it to craft of hull
length 6 m and over; craft below that are governed by ISO 12217-**3**, which
we do not hold and have not implemented. `assess()` nonetheless applied the
-1 category floors to anything handed to it, and the grammar admits hulls from
`PARAMS["LWL"].low` = 2.5 m (4.0 m until 2026-08-14) while the BuildPlan's
Dayboat SKU is 4-7 m.
MEASURED on a 4.5 m grammar hull at category C: five findings printed, four of
them numeric bars, under a header naming a standard that does not cover the
boat — the same defect shape as `gate2m.py` printing KCS's EFD figure for a
Wigley hull. A verdict from the wrong standard is worse than no verdict,
because it looks like a verdict.

The guard REFUSES rather than defaults to pass: R-SCP fails for a sub-6 m hull
and the numeric findings are not produced at all, so nothing downstream can
read an unassessed hull as an assessed one. `iso12217_3_thresholds` is already
recorded as absent in `navalai/refdata/ergonomics.py::NOT_SOURCED` — the
numeric content of -3 is paid text, so implementing it is a purchase, not a
sprint.
"""

from __future__ import annotations

import math

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:            # evaluate imports THIS module now, so the
    from ..evaluate import Evaluation   # runtime import would be circular
from ..limits import (CATEGORY_TABLE, CREW_MASS_KG,  # single source (limits.py)
                      MULTIHULL_OFFSET_LOAD_HEEL_LIMIT_DEG,
                      MULTIHULL_OFFSET_LOAD_SCOPE_LOA_M,
                      MULTIHULL_OFFSET_LOAD_SOURCE,
                      MULTIHULL_STABILITY_UNASSESSED,
                      gm_floor, stability_criterion)
from . import RuleFinding
from .review import basis_for

# ISO 12217-1's own scope: hull length 6 m and over. Below it the governing
# document is ISO 12217-3, which is NOT implemented here.
SCOPE_MIN_HULL_LENGTH_M = 6.0
SUB_SCOPE_STANDARD = "ISO 12217-3"

# category -> (significant wave height context [m], downflooding floor [m],
#              GM floor [m], max offset-load heel [deg])

# CREW_MASS_KG now comes from limits.py: it was declared here alone, so the
# stability check and the weight budget disagreed about how many people were
# aboard — 12 crew put 1020 kg on the rail here while the boat floated at the
# 2-crew displacement.
OFFSET_FRACTION = 0.40  # crew CG offset as fraction of beam (approx)


def offset_load_heel_limit_deg(lh_m: float) -> float:
    """Maximum permitted offset-load heel angle [deg], ISO 12217-1:2015 6.2.3 a).

        phi_O(R) = 11,5 + (24 - LH)^3 / 520

    VERIFIED against the standard's own Table 4 ("Maximum permitted heel angle
    for offset-load test for different lengths of hull"):

        LH (m)      6.0    7.0    8.0    9.0   10.0   12.0   15.0  18.0  21.0  24.0
        Table 4    22.7   20.9   19.4   18.0   16.8   14.8   12.9  11.9  11.6  11.5
        formula    22.72  20.95  19.38  17.99  16.78  14.82  12.90 11.92 11.55 11.50

    Every column agrees to the rounding the table is printed at.

    THE LIMIT DOES NOT DEPEND ON DESIGN CATEGORY. `CATEGORY_TABLE` carried it
    as a per-category constant (10/10/10/12 deg) until 2026-08-12, which is the
    wrong MODEL and not just the wrong number: at LH = 6 m the standard allows
    22.7 deg against the 10 deg we were enforcing, so the old bar was more than
    twice as strict at the small end and category-dependent where the standard
    is not.
    """
    return 11.5 + (24.0 - float(lh_m)) ** 3 / 520.0


def downflooding_height_required_m(lh_m: float, category: str,
                                   f1: float = 1.0, f2: float = 1.0,
                                   f3: float = 1.0, f4: float = 1.0,
                                   f5: float = 1.0) -> float:
    """Required downflooding height [m], ISO 12217-1:2015 Annex A (normative).

        hD(R) = H1 * F1 * F2 * F3 * F4 * F5,   H1 = LH/15        (A.1)

    then CLAMPED to Table A.1, whose limits are per design category (and per
    assessment option, which we do not model -- see limits.CATEGORY_TABLE).

    The five factors need per-boat opening geometry the ladder does not carry:
    F1 the opening POSITION factor (0,5..1,0), F2 the opening SIZE factor
    (0,6..1,0), F3 the recess factor, F4 displacement, F5 flotation option. All
    default to 1,0, which is the MOST DEMANDING value of each -- so the number
    returned is a conservative bound and a boat that passes it passes with any
    real opening layout. Declaring real openings can only lower it.
    """
    from ..limits import CATEGORY_TABLE
    if category not in CATEGORY_TABLE:
        raise ValueError(f"unknown design category {category!r}")
    _hs, lo, _gm, hi = CATEGORY_TABLE[category]
    h = (float(lh_m) / 15.0) * f1 * f2 * f3 * f4 * f5
    return float(min(max(h, lo), hi))


def hull_length_m(ev: "Evaluation") -> float | None:
    """The length the scope test is decided on, or None if there isn't one.

    ISO 12217-1's scope is stated on HULL length L_H. We do not model an
    overall hull length, and L_H >= L_WL for every hull this grammar emits, so
    the waterline length is used and the error is in the REFUSING direction:
    a hull between L_WL 6 m and L_H 6 m is declared out of scope and gets no
    verdict, rather than assessed by a standard that might not govern it.

    Returns None — not a number — when neither length is readable. `assess()`
    turns that into a failing finding, because a scope test that cannot be
    measured must not resolve to "in scope, carry on".
    """
    for val in (getattr(ev, "hull_lwl_m", 0.0) or 0.0,
                (ev.hydro.lwl_eff if ev.hydro is not None else 0.0) or 0.0):
        v = float(val)
        if math.isfinite(v) and v > 0.0:
            return v
    return None


def assess(ev: "Evaluation", category: str, crew: int,
           beam_m: float, length_m: float | None = None) -> list[RuleFinding]:
    if category not in CATEGORY_TABLE:
        raise ValueError(f"unknown design category {category!r}")
    hs, _dfh_lo, gm_req, _dfh_hi = CATEGORY_TABLE[category]
    out: list[RuleFinding] = []

    # ---- R-SCP: does this standard govern this hull? (gap G8) --------------
    # First, and returning early, because every finding after it is a bar this
    # standard sets and a bar from the wrong standard is not information.
    lh = length_m if length_m is not None else hull_length_m(ev)
    if lh is None or not math.isfinite(lh) or lh <= 0.0:
        out.append(RuleFinding(
            "R-SCP", "ISO 12217-1 §1 (scope: hull length >= 6 m)",
            basis_for("R-SCP"), False, float("nan"), SCOPE_MIN_HULL_LENGTH_M,
            "m", "hull length could not be read from the evaluation — the "
                 "scope of the standard is UNDECIDABLE, so no 12217-1 finding "
                 "is issued"))
        return out
    if lh < SCOPE_MIN_HULL_LENGTH_M:
        out.append(RuleFinding(
            "R-SCP", "ISO 12217-1 §1 (scope: hull length >= 6 m)",
            basis_for("R-SCP"), False, lh, SCOPE_MIN_HULL_LENGTH_M, "m",
            f"hull length {lh:.2f} m is below the scope of ISO 12217-1; "
            f"{SUB_SCOPE_STANDARD} governs craft this size and is NOT "
            f"implemented (its numeric content is paid text — see "
            f"refdata.ergonomics.NOT_SOURCED['iso12217_3_thresholds']). "
            f"No stability verdict is issued for this hull."))
        return out
    # IN SCOPE: no finding. A scope test that passes is a PRECONDITION, not a
    # statement about the boat, and emitting it as a fifth RuleFinding would
    # put an 'approx'-basis row into `unreviewed_bases` for every hull that
    # this standard does govern — reporting an unreviewed threshold where
    # there is no threshold. R-SCP speaks only when it refuses.

    if ev.hydro is None or ev.gm_m is None:
        out.append(RuleFinding("R-CAT", "ISO 12217-1 §5 (design categories)",
                               basis_for("R-CAT"), False, 0.0, hs, "m",
                               "no floatation state — cannot assess"))
        return out

    out.append(RuleFinding(
        "R-CAT", "ISO 12217-1 §5 (design categories)", basis_for("R-CAT"), True, hs, hs,
        "m", f"category {category}: significant wave height context {hs} m"))

    dfh = ev.hydro.freeboard_min   # lowest opening assumed at sheer (conservative
    # only if no lower openings exist — recorded in the note)
    dfh_req = downflooding_height_required_m(lh, category)
    out.append(RuleFinding(
        "R-DFH", "ISO 12217-1:2015 Annex A (A.1) + Table A.1 (downflooding "
        "height)", basis_for("R-DFH"),
        dfh >= dfh_req, dfh, dfh_req, "m",
        f"hD(R) = LH/15 clamped to Table A.1 for category {category}; all five "
        f"correction factors at their most demanding 1.0 (no openings "
        f"declared); lowest opening assumed at the sheer line"))

    # ---- WHICH STABILITY CRITERION GOVERNS (2026-08-14) --------------------
    # The hull count comes from `Evaluation.vessel`, which the multihull
    # landing fills in for EVERY vessel including a monohull (`n_hulls: 1`), so
    # a missing key is a genuinely unknown vessel and not a monohull by
    # omission. `limits.hull_role` refuses anything it cannot interpret.
    criterion = stability_criterion(_vessel_of(ev))

    if criterion.implemented:
        out.append(RuleFinding(
            "R-GM", "ISO 12217-1 annex (metacentric floor, practice value)",
            basis_for("R-GM"), ev.gm_m >= gm_req, ev.gm_m, gm_req, "m", ""))
    else:
        # R-GM IS NOT EMITTED FOR A MULTIHULL, AND THAT IS THE POINT.
        #
        # This follows R-SCP's precedent exactly: when the governing document
        # is one we do not implement, the numeric findings are WITHHELD rather
        # than produced, so nothing downstream can read an unassessed hull as
        # an assessed one. A catamaran clears any GM floor by a wide margin
        # because of the parallel-axis A_wp*d^2 term — emitting `R-GM PASS`
        # beside a refusal would put a green tick on the exact quantity that
        # does not govern, and a reader who saw only the tick would be wrong in
        # the dangerous direction.
        #
        # THE MEASURE IS A COUNT, NOT A LENGTH: 0 of the 1 criterion this
        # vessel needs has been assessed. `evaluate.g["rules"]` reads
        # |measured - required| / |required|, so this lands at 1.0 — a real,
        # finite, INFEASIBLE constraint value, not a nan and not a silent pass.
        out.append(RuleFinding(
            "R-MHS",
            "RCD 2013/53/EU Annex I A 3.3 (inversion) + ISO 12217-1:2015 cl. "
            "6.6 (habitable multihull boats) — NEITHER IMPLEMENTED",
            basis_for("R-MHS"), False, 0.0, 1.0, "criteria assessed",
            MULTIHULL_STABILITY_UNASSESSED + " GM here is "
            f"{ev.gm_m:.3f} m against the monohull floor of {gm_req:.2f} m; "
            f"that comparison is REPORTED and is not a verdict."))

    # offset-load heel: moment balance m*b = disp*GM*sin(phi)  (exact mechanics)
    m_crew = crew * CREW_MASS_KG
    b = OFFSET_FRACTION * beam_m
    sin_phi = min(m_crew * b / max(ev.hydro.disp_kg * ev.gm_m, 1e-9), 1.0)
    phi = math.degrees(math.asin(sin_phi))
    heel_max = offset_load_heel_limit_deg(lh)
    clause = "ISO 12217-1:2015 6.2.3 a) + Table 4 (offset-load test)"
    note = (f"{crew} crew x {CREW_MASS_KG:.0f} kg at {b:.2f} m offset; "
            f"phi_O(R) = 11.5 + (24 - {lh:.2f})^3/520 = {heel_max:.2f} deg, "
            f"a function of LENGTH only — not of design category")
    if not criterion.implemented:
        # THE ONE MULTIHULL BAR THAT IS COMPUTABLE FROM WHAT THIS LADDER HAS.
        # ISO 12217-1 sends habitable multihulls to clause 6.6, whose text this
        # project does not hold, so applying Table 4 to a catamaran is itself an
        # unexamined extrapolation. Maritime NZ states an offset-load/crowding
        # limit for multihulls explicitly and it is free; the STRICTER of the
        # two governs, and the clause string names both so the reader can see
        # which one bit. It is not a second measurement — same phi, two bars.
        iso_max = heel_max
        heel_max = min(heel_max, MULTIHULL_OFFSET_LOAD_HEEL_LIMIT_DEG)
        clause = (f"{clause} AND {MULTIHULL_OFFSET_LOAD_SOURCE}")
        note = (f"{note}. MULTIHULL: the stricter of ISO's {iso_max:.2f} deg "
                f"and the {MULTIHULL_OFFSET_LOAD_HEEL_LIMIT_DEG:.0f} deg "
                f"multihull limit governs")
        if lh > MULTIHULL_OFFSET_LOAD_SCOPE_LOA_M:
            note = (f"{note}. NOTE: hull length {lh:.2f} m is above the "
                    f"{MULTIHULL_OFFSET_LOAD_SCOPE_LOA_M:.0f} m scope of NZ "
                    f"cl. 1.3; cl. 1.1's offset-load table carries the same "
                    f"8 deg without that limit, and it is applied on that "
                    f"clause")
    out.append(RuleFinding(
        "R-OLH", clause, basis_for("R-OLH"), phi <= heel_max, phi, heel_max,
        "deg", note))
    return out


@dataclass(frozen=True)
class _NHulls:
    """Minimal carrier so `limits.hull_role` sees the attribute it duck-types
    on. Not `mission.VesselConfig`: `rules/` must not import `mission`, and a
    real config would refuse a hull count this module only wants to classify."""

    n_hulls: int


def _vessel_of(ev: "Evaluation") -> _NHulls:
    """The vessel descriptor `limits.hull_role` needs, out of an `Evaluation`.

    `Evaluation.vessel` is a REPORT dict, not `mission.VesselConfig`, so this
    adapts it.

    A MISSING `n_hulls` READS AS A MONOHULL, AND THAT IS A STATED RISK RATHER
    THAN AN OVERSIGHT. `evaluate()` fills the key in for every vessel it
    produces, monohull included, so on the ladder's own output the key is
    always there. The default exists for evaluations assembled by hand — every
    test in this tree that constructs an `Evaluation` directly predates the
    vessel contract — and it falls to the STRICTER treatment: the monohull path
    emits R-GM and applies the ISO offset-load limit, so nothing is granted a
    pass by omission. What a missing key CAN do is hide a real catamaran behind
    monohull criteria, which is exactly the hole this block closes; the guard
    against that is `evaluate()` filling the field, and it is asserted in
    `tests/test_vessel_bands.py`.
    """
    v = getattr(ev, "vessel", None) or {}
    n = v.get("n_hulls", 1)
    return _NHulls(int(n))
