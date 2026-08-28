"""Gate PREFLIGHT: ask the cheap questions before buying a solve.

CFD-audit P1. The campaigns' most expensive lesson is that hours were
spent on questions already answered — by theory, by a prior run of the
same surface, or by the family's own measured band — and on comparisons
the evidence could not support. Each function here is a refusal with a
number in it; each test feeds it the VERBATIM case that motivated it.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from navalai.cfd import preflight as pf
from navalai.constants import G_STANDARD

BOOK = Path(__file__).resolve().parents[1] / "data" / "cfd_anchors.json"


def _anchors() -> dict:
    return json.loads(BOOK.read_text())["anchors"]


def test_theory_refuses_to_buy_what_a_closed_form_already_gives():
    for q in ("what is the wake wavelength",
              "viscous resistance at cruise",
              "GM and displacement",
              "is this near the hump"):
        a = pf.theory_answers(q)
        assert a, f"{q!r} should be answered by theory"
        assert a.detail
    # and the four things the campaign named as simulation-only
    for q in ("tunnel inflow quality at the prop plane",
              "fin wake structure behind a tapered trailing edge",
              "the stern wave system of this shoulder",
              "which cell folds first at an impulsive start"):
        a = pf.theory_answers(q)
        assert not a, f"{q!r} must NOT be claimed by theory"
        assert "what a solve is for" in a.detail


def test_a_surface_already_solved_is_reported_before_it_is_re_bought():
    book = _anchors()
    sha = book["hookprobe_v3"]["stl_sha256"]
    speed = book["hookprobe_v3"]["speed_ms"]
    hit = pf.already_measured(sha, speed_ms=speed)
    assert hit and hit.data["same_speed"], (
        "the preflight did not recognise a re-solve of the same surface at "
        "the same speed")
    assert "hookprobe_v3" in hit.data["runs"]
    # a known surface at a NEW speed is a different question, said so
    other = pf.already_measured(sha, speed_ms=speed * 1.25)
    assert other and other.data["same_speed"] is False
    # an unknown surface refuses by name
    miss = pf.already_measured("0" * 64, speed_ms=speed)
    assert not miss and "no run of surface" in miss.detail


def test_the_family_band_answers_before_a_run_and_refuses_off_support():
    a = pf.family_expectation("hookprobe_hybrid", 0.38)
    assert a and "pressure drag" in a.detail
    assert 0.75 <= a.data["lo"] <= a.data["hi"] <= 0.85
    off = pf.family_expectation("hookprobe_hybrid", 0.90)
    assert not off and "new run" in off.detail


def test_the_kelvin_check_is_the_free_validation():
    """lambda = 2*pi*U^2/g needs no reference data. At 8 kn the campaign
    computed 10.77 m and reported the wake matched — by hand, once."""
    u = 4.1
    theory = 2.0 * math.pi * u * u / G_STANDARD
    assert theory == pytest.approx(10.766, abs=0.01)
    assert pf.kelvin_check(u, theory)
    assert pf.kelvin_check(u, theory * 1.05)              # inside 10%
    bad = pf.kelvin_check(u, theory * 1.4)
    assert not bad and "not the physics" in bad.detail
    # an unmeasured wavelength is never a passing one
    assert not pf.kelvin_check(u, 0.0)


def test_the_ab_rule_refuses_the_campaigns_own_confounded_ladder():
    """THE MEASURED CASE. v2 vs v3 is the campaign's headline geometry
    A/B: 2997.6 vs 2965.6 N, a 1.1% delta — inside the +-2.5% window
    scatter — across meshes of 513941 and 414395 cells, a 24% difference.
    The +33% appendage delta (v3 vs v4) SURVIVES the same rule, which is
    what makes it a rule and not a blanket refusal."""
    book = _anchors()
    v2, v3, v4 = book["hookprobe_v2"], book["hookprobe_v3"], book["hookprobe_v4"]

    bad = pf.ab_comparable(v2, v3)
    assert not bad, "the confounded ladder was accepted as a geometry A/B"
    assert "meshes differ" in bad.detail or "scatter" in bad.detail

    good = pf.ab_comparable(v3, v4)
    assert good, f"the +33% appendage A/B was refused: {good.detail}"
    assert good.data["delta"] > pf.WINDOW_SCATTER
    assert good.data["mesh_gap"] <= pf.AB_CELL_TOL

    # an unsettled record can never be one side of a comparison
    assert not pf.ab_comparable(v3, book["hookprobe_v3_10kn"])
    # nor can a wave-loads record
    assert not pf.ab_comparable(v3, book["hookprobe_v3_seas"])


def test_the_impulsive_start_ceiling_is_the_measured_one():
    """Three deaths at n_layers 10, 8 and 5 say the ladder is the wrong
    instrument above Fn ~0.5; the ramp is the fix, and a naive ramp is
    worse than none."""
    lwl = 11.84
    ok = pf.start_is_survivable(4.1, lwl)                 # Fn 0.38
    assert ok and ok.data["fn"] < 0.5
    bad = pf.start_is_survivable(5.66, lwl)               # Fn 0.53
    assert not bad
    assert "layer backoff" in bad.detail and "PASSIVE" in bad.detail
    # ramped, the same speed is allowed to proceed
    assert pf.start_is_survivable(5.66, lwl, ramped=True)


def test_extend_on_drift_not_on_the_clock():
    """The two measured cases, opposite answers. v3_10kn stopped at its
    TARGET TIME with 11.5% drift still falling — time would have helped.
    kcs_s1 converged (0.31% drift) to a -43.5% error — time would not."""
    still_moving = {"settled": False, "drift": 0.115, "prev_drift": 0.152}
    a = pf.more_time_will_help(still_moving)
    assert a and "FALLING" in a.detail

    converged_wrong = {"settled": True, "drift": 0.0031, "prev_drift": 0.004}
    b = pf.more_time_will_help(converged_wrong)
    assert not b and "physics or mesh, not duration" in b.detail

    stuck = {"settled": False, "drift": 0.18, "prev_drift": 0.17}
    c = pf.more_time_will_help(stuck)
    assert not c and "NOT falling" in c.detail


def test_the_divergence_signature_is_named_while_the_solve_still_runs():
    """MEASURED: the 11-kn deaths ran dt 1e-105..1e-26 against a healthy
    1e-3 while Courant max held ~10; KCS n=7 went 1.2e-3 -> 2.5e-26 with
    Courant 9-12. A human read that out of a log three times."""
    bad = pf.diagnose_divergence(dt_now=2.5e-26, dt_healthy=1.2e-3,
                                 courant_max=11.0)
    assert not bad and "PATHOLOGICAL CELL" in bad.detail
    assert "do not resume" in bad.detail

    healthy = pf.diagnose_divergence(dt_now=3.2e-3, dt_healthy=3.2e-3,
                                     courant_max=0.9)
    assert healthy and "no collapse" in healthy.detail

    # dt small but Courant falling is a different (survivable) story
    slow = pf.diagnose_divergence(dt_now=1e-10, dt_healthy=1e-3,
                                  courant_max=0.4)
    assert not slow and "limiter is working" in slow.detail
