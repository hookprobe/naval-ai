"""Gate 6 (mechanics scope): rule verdicts flip on the right physics, clause
provenance everywhere, disclaimer always on, thickness formula behaves."""

import pytest

from navalai.evaluate import evaluate
from navalai.mission import MissionSpec
from navalai.rules import DISCLAIMER, report
from navalai.rules.iso12215 import (assess as scantling,
                                    design_pressure_bottom,
                                    required_thickness_mm)
from navalai.rules.iso12217 import CATEGORY_TABLE, assess as stability
from tests.test_phase0 import mid_params
from navalai import grammar


def _ev(cat="D"):
    m = MissionSpec(design_category=cat, displacement_target_kg=5000)
    return evaluate(mid_params(), m), m


def test_reference_hull_assessed_category_d():
    ev, m = _ev("D")
    findings = stability(ev, "D", crew=2, beam_m=grammar.named(mid_params())["BWL"])
    rep = report(findings)
    assert rep["disclaimer"] == DISCLAIMER
    assert rep["total"] == 4
    by = {f["rule_id"]: f for f in rep["findings"]}
    assert by["R-DFH"]["passed"], by["R-DFH"]
    assert by["R-OLH"]["passed"], by["R-OLH"]
    assert all(f["clause"] for f in rep["findings"])
    # Basis is DECLARED, never hidden. This asserted "R-GM" was unreviewed,
    # which encoded the state of the world before the Gate 6R parity review
    # (2026-08-05) rather than an invariant. The invariant is that every
    # finding's basis traces to the review record — and that a reviewed
    # threshold still does not make this a certification.
    from navalai.rules.review import basis_for
    for f in rep["findings"]:
        assert f["basis"] == basis_for(f["rule_id"]), f
    # R-GM CARRIES basis='approx' AND MUST SHOW UP HERE. Changed 2026-08-12:
    # a sweep of all 86 pages of ISO 12217-1:2015 finds NO absolute metacentric
    # requirement, so the GM floor is ours, not ISO. It stays as an L1
    # feasibility bar but it can never report 'standard', and a report that
    # listed no unreviewed bases while carrying it would be claiming ISO
    # backing for a number ISO does not contain.
    assert rep["unreviewed_bases"] == ["R-GM"], rep["unreviewed_bases"]
    assert "NOT CERTIFICATION" in rep["disclaimer"]


def test_stricter_category_is_harder():
    ev, _ = _ev()
    for cat in ("A", "B", "C", "D"):
        _hs, dfh, gm, _heel = CATEGORY_TABLE[cat]
    d = stability(ev, "D", 2, 3.2)
    a = stability(ev, "A", 2, 3.2)
    req = {f.rule_id: f.required for f in d}
    req_a = {f.rule_id: f.required for f in a}
    assert req_a["R-DFH"] > req["R-DFH"]
    assert req_a["R-GM"] > req["R-GM"]


def test_crowded_rail_flips_offset_load():
    ev, _ = _ev()
    ok = stability(ev, "D", crew=2, beam_m=3.2)
    crowded = stability(ev, "D", crew=12, beam_m=3.2)
    by_ok = {f.rule_id: f for f in ok}
    by_cr = {f.rule_id: f for f in crowded}
    assert by_cr["R-OLH"].measured > by_ok["R-OLH"].measured
    # THE "approach the limit" HEURISTIC WAS CALIBRATED AGAINST A BAR THAT WAS
    # TWICE TOO STRICT. Until 2026-08-12 the limit was a per-category constant
    # (12 deg for category D); ISO 12217-1:2015 6.2.3 a) makes it a function of
    # LENGTH only, phi_O(R) = 11,5 + (24 - LH)^3/520, which for this hull is
    # 16.78 deg. What is invariant is that crowding MOVES the heel and that the
    # bar is the ISO one, so that is what is asserted first.
    #
    # THIS TEST'S NAME IS TRUE AGAIN. Between 2026-08-12 and the geometry
    # kernel rebuild the crowded case PASSED — 12 crew on a 3.2 m beam heeled
    # the old reference hull 6.81 deg, comfortably inside 16.78, and this test
    # asserted `passed` and said so. RE-MEASURED 2026-08-13 on the plate-P1/P2
    # reference hull: GM is 0.861 m and the same 12 crew x 85 kg at 1.28 m
    # offset heel it **17.67 deg**, so R-OLH FAILS by 0.89 deg. Neither the
    # rule nor the crew model moved; the boat did — it is a narrower hull for
    # the same LWL and it is less stiff. Recorded, not softened: the offset-
    # load clause is now a live refusal on the reference hull and the 2 crew
    # case (2.90 deg) is the control that keeps this about crowding.
    from navalai.rules.iso12217 import offset_load_heel_limit_deg
    lh = 10.0
    assert by_cr["R-OLH"].required == pytest.approx(
        offset_load_heel_limit_deg(lh), abs=0.5), by_cr["R-OLH"].required
    assert by_ok["R-OLH"].measured == pytest.approx(2.90, abs=0.1)
    assert by_ok["R-OLH"].passed, "2 crew must not trip the offset-load clause"
    assert by_cr["R-OLH"].measured == pytest.approx(17.67, abs=0.2)
    assert not by_cr["R-OLH"].passed, (
        "12 crew no longer heel the reference hull past the ISO limit — "
        "re-measure and record BEFORE/AFTER; this test's name is the finding")


def test_unfloatable_hull_fails_closed():
    from navalai.evaluate import Evaluation
    dead = Evaluation(False, "L1", ("floatation: swamps",))
    findings = stability(dead, "C", 2, 3.0)
    rep = report(findings)
    assert not rep["pass"] and rep["total"] == 1     # fails closed, no partial


def test_scantling_monotonic_and_plausible():
    """THIS TEST WAS STALE, AND ONE OF ITS CALLS PASSED A 400 m BOAT.

    Both scantling entry points take LWL as their SECOND positional argument
    since the Gate 6R re-shape (2026-08-19) rebuilt this module against the
    ISO 12215-5:2008(E) clause text. It is not a widened signature: Eq (8)
    gives the bottom-pressure MINIMUM as

        P_BM_MIN = (0.45*mLDC^0.33 + 0.9*LWL) * kDC     [kN/m^2]

    which is length-dependent, and it REPLACED a flat `max(10, P_BASE)` floor
    that was neither length- nor category-dependent and is recorded as known
    wrong. So `lwl_m` is load-bearing physics and the missing-argument
    TypeError was the correct answer to the old call.

    The old test read

        design_pressure_bottom(8000) > design_pressure_bottom(2000)
        required_thickness_mm(6000, span_mm=300)
        required_thickness_mm(6000, 400)          <-- LWL = 400 metres

    The first two raise TypeError; the third would NOT have — it binds 400 to
    `lwl_m` and asks for the plating of a 400 m ship on the default 400 mm
    frame spacing, which Eq (8) answers with 220.8 kN/m^2 and **43.0 mm** of
    plywood, sailing straight past the `8 < t < 22` band this test believed it
    was checking. A stale positional call is not always a crash.

    Monotonicity in mLDC is now asserted at a FIXED length, monotonicity in
    span at a fixed length and mass, and the length dependence that made the
    argument mandatory is asserted in its own right.
    """
    lwl = 10.0
    # heavier boat -> higher pressure, at ONE length
    assert (design_pressure_bottom(8000, lwl)
            > design_pressure_bottom(2000, lwl))
    assert design_pressure_bottom(8000, lwl) == pytest.approx(27.941, abs=1e-2)
    assert design_pressure_bottom(2000, lwl) == pytest.approx(16.866, abs=1e-2)

    # wider span -> thicker panel, same boat, same length
    t1 = required_thickness_mm(6000, lwl, span_mm=300)
    t2 = required_thickness_mm(6000, lwl, span_mm=500)
    assert t2 > t1

    # Eq (8)'s floor is why lwl_m cannot be defaulted: below ~25 m Eq (7)
    # governs and length does nothing, above it the minimum takes over. A
    # signature that let LWL be omitted could not express either half.
    assert (design_pressure_bottom(2000, 25.0)
            == pytest.approx(design_pressure_bottom(2000, 5.0)))
    assert design_pressure_bottom(2000, 30.0) > design_pressure_bottom(2000, 25.0)

    # 6 t boat, 10 m, 400 mm frames: required ply in a believable band
    t = required_thickness_mm(6000, lwl, span_mm=400)
    assert 8.0 < t < 22.0, t
    # and the 400 m boat the stale call actually asked for is NOT in it
    assert required_thickness_mm(6000, 400.0, span_mm=400) > 22.0


def test_scantling_verdict():
    """STALE FOR THE SAME REASON, and it failed CLOSED rather than wrong.

    `scantling(6000, provided_mm=20.0)` leaves `lwl_m=None`, and `assess`
    REFUSES that: it returns a single R-PBM finding with `passed=False` and
    measured/required NaN, noting that Eq (8)'s minimum is length-dependent
    and the assessment will not be run on the base pressure alone. So the
    `assert report(ok)["pass"]` failure was the refusal working, not a broken
    verdict — the right behaviour for a rule module that must never invent an
    input. The refusal is asserted here rather than merely repaired away.
    """
    lwl = 10.0
    refused = report(scantling(6000, provided_mm=20.0))
    assert not refused["pass"] and refused["total"] == 1
    assert "refused" in refused["findings"][0]["note"]

    ok = scantling(6000, provided_mm=20.0, lwl_m=lwl)   # required ~15.8 mm
    thin = scantling(6000, provided_mm=6.0, lwl_m=lwl)  # required ~14.5 mm
    assert report(ok)["pass"]
    assert not report(thin)["pass"]
    by_ok = {f.rule_id: f for f in ok}
    assert by_ok["R-TBM"].required == pytest.approx(15.768, abs=1e-2)
    assert {f.rule_id for f in ok} == {"R-PBM", "R-TBM"}
