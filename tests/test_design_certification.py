"""Gate DC — the pre-CFD design certification layer (screening directive).

Invariants and refusal boundaries, not float pins (§28): the engine must
classify cheaply, carry receipts, refuse unsupported regimes by name, and
never fabricate what the tree cannot answer.
"""

import numpy as np
import pytest

from navalai import formcheck
from navalai.certify import (REGIME_AUTONOMOUS_SLOW_CRUISE, REGIME_PLANING,
                             REGIME_SEMI_DISPLACEMENT, certify,
                             mission_regime, speed_curve)
from navalai.evaluate import evaluate
from navalai.mission import Manning, MissionSpec, VesselConfig
from navalai.reference import reference_params

CASES = {c.key: c for c in formcheck.CASES}


@pytest.fixture(scope="module")
def ref_cert():
    return certify(reference_params(),
                   MissionSpec(cruise_speed_kn=5, lwl_hint_m=10.0))


def test_the_reference_hull_is_refused_with_the_defect_named(ref_cert):
    """The known cold-bend violation refuses the reference hull — and the
    certification names it rather than reporting a bare fail."""
    assert ref_cert.verdict == "REFUSE"
    assert any("bend radius" in r for r in ref_cert.reasons)
    assert ref_cert.evaluation_ok is False
    # an ineligible design is not CFD-worthy
    assert ref_cert.cfd_candidate["eligible"] is False


def test_every_quantity_carries_its_receipt(ref_cert):
    """§25: value/unit/tier/sigma-where-meaningful/basis on every figure."""
    assert ref_cert.quantities, "a certification with no quantities"
    for name, q in ref_cert.quantities.items():
        assert np.isfinite(q.value), name
        assert q.unit, name
        assert q.tier, name
        assert q.basis and len(q.basis) > 10, (
            f"{name}: a basis must say where the number came from")


def test_unsupported_regimes_are_refused_by_name():
    """§16: no regime is enabled until its physics exists. A fast brief is
    routed to SEMI_DISPLACEMENT or PLANING and REFUSED with 'not yet
    supported' — never silently scored by Michell."""
    fast = MissionSpec(cruise_speed_kn=9, lwl_hint_m=8.0)     # Fn ~0.52
    reg, ok, why = mission_regime(fast)
    assert reg == REGIME_SEMI_DISPLACEMENT and not ok
    assert "not yet supported" in why
    planing = MissionSpec(cruise_speed_kn=14, lwl_hint_m=6.0)  # Fn ~0.94
    reg, ok, why = mission_regime(planing)
    assert reg == REGIME_PLANING and not ok
    cert = certify(reference_params(), fast, with_gz=False)
    assert cert.verdict == "REFUSE"
    assert not cert.regime_supported
    drone = MissionSpec(cruise_speed_kn=3, lwl_hint_m=5.0,
                        vessel=VesselConfig(manning=Manning.UNCREWED))
    reg, ok, _ = mission_regime(drone)
    assert reg == REGIME_AUTONOMOUS_SLOW_CRUISE and ok


def test_the_speed_curve_is_banded_and_monotone_where_valid(ref_cert):
    """§15: every point carries a validity band; within the continuously
    VALID/EXTRAPOLATED displacement range total resistance is monotone in
    speed (an invariant, not a float pin); UNSUPPORTED points never carry
    an energy figure."""
    curve = ref_cert.speed_curve
    assert curve
    bands = {p.validity for p in curve}
    assert bands <= {"VALID", "TRANSITION", "EXTRAPOLATED", "UNSUPPORTED"}
    usable = [p for p in curve if p.validity != "UNSUPPORTED"]
    rts = [p.rt_n for p in usable]
    assert rts == sorted(rts), "Rt must rise with speed in-regime"
    for p in curve:
        if p.validity == "UNSUPPORTED":
            assert p.wh_per_nm is None, (
                "an unsupported point carried an energy figure")
        else:
            assert p.wh_per_nm is not None and p.wh_per_nm > 0
        assert p.sigma_rt_n > 0


def test_a_fast_mission_curve_ends_unsupported():
    """Beyond FN_MICHELL_MAX the curve says UNSUPPORTED instead of drawing
    smooth fiction (§15)."""
    m = MissionSpec(cruise_speed_kn=7.5, lwl_hint_m=10.0)      # Fn ~0.39
    ev = evaluate(reference_params(), m)
    assert ev.hydro is not None
    curve = speed_curve(reference_params(), m, ev)
    assert curve[-1].fn > 0.45
    assert curve[-1].validity == "UNSUPPORTED"
    assert any(p.validity != "UNSUPPORTED" for p in curve)


def test_loading_matrix_obeys_conservation_invariants(ref_cert):
    """§28: removing load must not increase displacement; a mirrored
    symmetric loading has zero TCG; the MAXIMUM state is UNKNOWN rather
    than fabricated (no declared maximum exists)."""
    lm = ref_cert.loading
    # The reference mission declares a 6000 kg DISPLACEMENT TARGET, so
    # removing the provision re-grows the declared `unaccounted` filler and
    # both states float at the target (equal within solver tolerance) —
    # the honest invariant under a pinned target is equality-with-tolerance,
    # not decrease. The real decrease is asserted on the drone case below,
    # whose budget exceeds its target.
    assert lm["LIGHTSHIP"]["displacement_kg"] <= \
        lm["DESIGN"]["displacement_kg"] * (1.0 + 2e-3)
    drone = certify(CASES["e"].params, CASES["e"].mission, with_gz=False)
    dl = drone.loading
    assert dl["LIGHTSHIP"]["displacement_kg"] < \
        dl["DESIGN"]["displacement_kg"] - 1.0, (
        "removing the drone's provision must reduce displacement")
    for st in ("DESIGN", "LIGHTSHIP"):
        assert lm[st]["tcg_m"] == pytest.approx(0.0, abs=1e-9)
        assert lm[st]["freeboard_m"] > 0
    assert "unknown" in lm["MAXIMUM"]
    assert "not fabricated" in lm["MAXIMUM"]["unknown"]
    # the people-shift states exist for a crewed mission and TRIM apart
    assert "PEOPLE_FORWARD" in lm and "PEOPLE_AFT" in lm
    tf = lm["PEOPLE_FORWARD"]["trim_deg"]
    ta = lm["PEOPLE_AFT"]["trim_deg"]
    if tf is not None and ta is not None:
        assert tf > ta, "people forward must trim the bow DOWN relative " \
                        "to people aft"


def test_the_catamaran_certification_refuses_and_measures(ref_cert):
    """The 12 m catamaran case: verdict REFUSE (criterion unassessable by
    construction), but clauses (a)/(b) are MEASURED and the GZ assumptions
    ride on the certification — a refusal with evidence, not a shrug."""
    case = CASES["d"]
    cert = certify(case.params, case.mission)
    assert cert.verdict == "REFUSE"
    st = cert.stability
    assert st["verdict"] == "REFUSED"
    assert st["clause_a"]["area_m_rad"] > 0
    assert st["clause_b"]["heel_at_gz_max_deg"] > 0
    assert any("windage" in u or "lateral area" in u
               for u in st["unassessable"])
    assert any("fixed longitudinal attitude" in a for a in cert.assumptions)
    assert any("watertight to the sheer" in a for a in cert.assumptions)


def test_certification_composes_it_does_not_fork():
    """§4: the engine composes the EXISTING Evaluation — same verdict
    inputs, same violations, no parallel ladder."""
    m = MissionSpec(cruise_speed_kn=5, lwl_hint_m=10.0)
    ev = evaluate(reference_params(), m)
    cert = certify(reference_params(), m, with_gz=False)
    assert cert.violations == ev.violations
    assert cert.evaluation_ok == ev.ok
    assert cert.targets == dict(ev.targets)


def test_a_refused_trim_equilibrium_is_never_an_even_keel_C02():
    """Forensics C-02 (E11 reborn): four sites collapsed a REFUSED trim
    (None) into 0.0 — one of them fed CFD manifests. A hull whose
    equilibrium the solver refused must not carry a 'solved equilibrium'
    quantity, must not get a GZ curve at a fabricated attitude, and must
    not become an even-keel CFD case."""
    from navalai.cfd.manifest import manifest_from_evaluation
    from navalai.evaluate import evaluate
    from navalai.mission import PayloadSpec
    from navalai.reference import reference_params

    m = MissionSpec(payload=PayloadSpec(mass_kg=3000.0, x_frac_lwl=0.99,
                                        z_frac_depth=0.5))
    ev = evaluate(reference_params(), m)
    assert ev.trim_deg is None and ev.hydro is not None, (
        "fixture must float but refuse the trim equilibrium")

    cert = certify(reference_params(), m)
    assert cert.verdict == "REFUSE"
    assert "trim" not in cert.quantities, (
        "a refused equilibrium reappeared as a 'solved' trim quantity")
    assert "refused" in cert.stability
    assert "fabricated attitude" in cert.stability["refused"]
    assert "gz_max_m" not in cert.stability, (
        "a GZ curve was computed at an attitude the solver refused")

    with pytest.raises(ValueError, match="REFUSED"):
        manifest_from_evaluation(ev, m)
