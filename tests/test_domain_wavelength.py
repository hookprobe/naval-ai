"""The tank must contain the ship's OWN wave.

MEASURED 2026-08-28 on `runs/hookprobe_v5_20kn` (v5 hull, 10.29 m/s, Fn 0.95):
the transverse wavelength 2*pi*U^2/g is 67.8 m and the 4.5 Lwl tank was 53.2 m,
so the box held 0.78 of ONE wavelength. The run solved cleanly for 24 s and the
drag it produced was meaningless — a wave that does not fit cannot form. The
`case.info` receipt printed `domain_length_m=53.19` directly beside
`wavelength_m=67.82` and nothing in the pipeline compared them.

The depth rule (`depth = max(1.0*lwl, 1.5*half_lambda)`) had scaled with the
wave since it was written; the LENGTH rule never did. These tests fence the
asymmetry so it cannot come back, and pin the MAX behaviour that keeps every
case at or below the design point bit-identical to the pre-fix pipeline.
"""
import math

from navalai.cfd.case import _DOMAIN_X, _G, domain_x_bounds

LWL = 11.82


def _lam(u):
    return 2.0 * math.pi * u ** 2 / _G


def test_design_point_is_unchanged():
    """Fn 0.26-0.48 must return the historic 4.5 Lwl box, exactly.

    The whole v1/v2/v3 ladder and the 10-kn point were run at these speeds; if
    this rule moved them, every delta in the campaign would silently stop being
    comparable to the ones recorded before it.
    """
    for speed in (2.57, 4.1, 5.14):
        x0, x1 = domain_x_bounds(LWL, speed)
        assert math.isclose(x0, _DOMAIN_X[0] * LWL, rel_tol=1e-12)
        assert math.isclose(x1, _DOMAIN_X[1] * LWL, rel_tol=1e-12)


def test_high_froude_tank_contains_at_least_two_wavelengths():
    """At Fn 0.95 the box must hold the wave that killed the first attempt."""
    speed = 10.29
    x0, x1 = domain_x_bounds(LWL, speed)
    assert (x1 - x0) / _lam(speed) >= 2.0


def test_wake_gets_one_and_a_half_wavelengths_astern():
    """The transverse system trails the hull; astern is where it must fit."""
    speed = 10.29
    x0, _ = domain_x_bounds(LWL, speed)
    assert -x0 >= 1.5 * _lam(speed) - 1e-9


def test_rule_is_monotone_in_speed():
    """A faster case may never get a shorter tank than a slower one."""
    lengths = [domain_x_bounds(LWL, u)[1] - domain_x_bounds(LWL, u)[0]
               for u in (2.0, 4.0, 6.0, 8.0, 10.29, 12.0)]
    assert lengths == sorted(lengths)
