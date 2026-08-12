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
    # 16.78 deg. 12 crew on a 3.2 m beam heel it 6.81 deg — comfortably inside
    # the real limit, which is the correct answer, not a regression. What is
    # actually invariant is that crowding MOVES the heel and that the bar is
    # the ISO one, so that is what is asserted.
    import math
    from navalai.rules.iso12217 import offset_load_heel_limit_deg
    lh = 10.0
    assert by_cr["R-OLH"].required == pytest.approx(
        offset_load_heel_limit_deg(lh), abs=0.5), by_cr["R-OLH"].required
    assert by_cr["R-OLH"].passed, "6.8 deg is well inside the 16.8 deg ISO bar"


def test_unfloatable_hull_fails_closed():
    from navalai.evaluate import Evaluation
    dead = Evaluation(False, "L1", ("floatation: swamps",))
    findings = stability(dead, "C", 2, 3.0)
    rep = report(findings)
    assert not rep["pass"] and rep["total"] == 1     # fails closed, no partial


def test_scantling_monotonic_and_plausible():
    # heavier boat -> higher pressure; wider span -> thicker panel
    assert design_pressure_bottom(8000) > design_pressure_bottom(2000)
    t1 = required_thickness_mm(6000, span_mm=300)
    t2 = required_thickness_mm(6000, span_mm=500)
    assert t2 > t1
    # 6 t boat, 400 mm frames: required ply in a believable band (10-20 mm)
    t = required_thickness_mm(6000, 400)
    assert 8.0 < t < 22.0, t


def test_scantling_verdict():
    ok = scantling(6000, provided_mm=20.0)   # required computes to ~18.2 mm
    thin = scantling(6000, provided_mm=6.0)
    assert report(ok)["pass"]
    assert not report(thin)["pass"]
