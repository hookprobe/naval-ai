"""GATE 2 — the physics stack that replaced "Gate 2M = KCS" (2026-08-21).

THE QUESTION CHANGED, SO THE BENCHMARK DID. Gate 2M was written when this
project intended to design arbitrary ships, and KCS -- a 230 m round-bilge
container ship with a bulbous bow -- was the right anchor for that. The
product is now low-cost BUILDABLE PLYWOOD boats: hard-chine, developable
panels, shallow draft, displacement to semi-displacement.

KCS is KEPT and DEMOTED. At model scale it sits at Fn 0.260 / Re 1.40e7
against our 10 m at 5 kn (Fn 0.260 / Re 2.26e7), so it still tests the
NUMERICS at our own operating point. It cannot exercise chine spray,
hard-chine separation or transom ventilation, which is all the product
builds.

This file carries the rungs that are EXECUTABLE TODAY. The rungs that need
data this tree does not hold are recorded in docs/audit/GATE2-PHYSICS-STACK.md
with what would close them -- not stubbed here, because a test that asserts
nothing is worse than an absent one.
"""
import numpy as np
import pytest

from benchmarks import wigley


def test_gate2a_hydrostatics_is_a_MATHEMATICAL_gate_not_a_CFD_one():
    """GATE 2A. The Wigley hull's displaced volume is EXACTLY 4LBT/9.

    That is the strongest kind of benchmark available anywhere in this
    project: an analytic truth with no experiment, no uncertainty band and
    no scatter to hide inside. If the integrator cannot reproduce a closed
    form, no CFD result standing on it means anything -- and this costs
    milliseconds, against ~69 h for the KCS triplet.

    MEASURED 2026-08-21, trapezoidal integration of the analytic offsets:

        grid        volume      err %
        121 x 25    2.768698    -0.3269
        241 x 61    2.776237    -0.0555
        481 x 121   2.777386    -0.0141
        961 x 241   2.777679    -0.0036

    The error falls by roughly 4x per doubling, which is SECOND ORDER and is
    what the trapezoid rule owes. Asserting the converged value alone would
    pass for an integrator that is accidentally close; asserting the ORDER
    is what says the method is right.
    """
    L = 10.0
    exact = wigley.displacement_exact(L)
    B, T = wigley.proportions(L)
    assert exact == pytest.approx(4.0 * L * B * T / 9.0, rel=1e-15), (
        "displacement_exact no longer returns the closed form 4LBT/9")

    errs = []
    for nx, nz in ((121, 25), (241, 61), (481, 121), (961, 241)):
        xs, zs, Y, _, _ = wigley.wigley_offsets(L, nx, nz)
        vol = 2.0 * np.trapezoid(np.trapezoid(Y, zs, axis=1), xs)
        errs.append(abs(vol - exact) / exact)

    # 1. it CONVERGES to the closed form
    assert errs[-1] < 1e-4, (
        f"finest grid is {100*errs[-1]:.4f}% from the exact volume")

    # 2. and it converges MONOTONICALLY -- an integrator that wanders is not
    #    converging, it is coincidentally passing at one resolution
    assert all(b < a for a, b in zip(errs, errs[1:])), (
        f"error is not monotone under refinement: "
        f"{[f'{100*e:.4f}%' for e in errs]}")

    # 3. at roughly SECOND order. The observed ratio is ~3.9-5.9 per
    #    doubling; the bar is deliberately loose because the z grid is
    #    quadratically clustered, which is not a uniform refinement.
    for a, b in zip(errs, errs[1:]):
        assert a / b > 2.5, (
            f"error fell only {a/b:.2f}x under a grid doubling — that is "
            f"below first order and the integrator is not converging as the "
            f"trapezoid rule requires")


def test_gate2a_the_analytic_hull_is_INDEPENDENT_of_our_geometry_kernel():
    """The invariant only means something if it is not our own code twice.

    `wigley_offsets` is y = (B/2)(1-(2x/L)^2)(1-(z/T)^2) written out, and the
    exact volume is a closed form. Neither passes through `navalai.geometry`,
    so Gate 2A checks an INTEGRATOR against MATHEMATICS rather than checking
    the kernel against itself -- the tautology this repository has already
    shipped once, in a layer table that printed the requested spec as the
    achieved one.
    """
    L = 10.0
    B, T = wigley.proportions(L)
    xs, zs, Y, B2, T2 = wigley.wigley_offsets(L, 61, 21)
    assert (B2, T2) == (B, T)

    # the offsets ARE the formula, checked at interior points
    for i in (5, 17, 40):
        for j in (3, 11, 18):
            want = (B / 2) * (1 - (2 * xs[i] / L) ** 2) * (1 - (zs[j] / T) ** 2)
            assert Y[i, j] == pytest.approx(max(want, 0.0), rel=1e-12)

    # ends and keel close to zero, which is what makes the volume finite
    assert Y[0].max() == pytest.approx(0.0, abs=1e-12)
    assert Y[-1].max() == pytest.approx(0.0, abs=1e-12)


def test_gate2d_KCS_is_labelled_SOLVER_VERIFICATION_and_cannot_drift_back():
    """GATE 2D. KCS keeps its place and loses its title.

    The registry row and the ledger entry must both say that passing it is a
    NUMERICAL result, because the old title said neither and that is exactly
    how a solver benchmark came to be read as small-craft validation. This
    fence exists so the demotion cannot be quietly undone by an edit that
    looks like tidying.
    """
    import json
    import pathlib

    from navalai import gates as G

    row = next(g for g in G.GATES if g.name == "Gate 2M")
    scope = f"{row.scope} {row.detail or ''}"
    assert "SOLVER VERIFICATION" in scope.upper(), row.scope
    assert "not small-craft validation" in scope.lower(), row.scope

    led = json.loads(
        pathlib.Path("data/gate-ledger.json").read_text())["Gate 2M"]
    assert "scope" in led, "the ledger entry lost its scope note"
    text = led["scope"].lower()
    for phrase in ("bulbous bow", "chine", "numerical anchor"):
        assert phrase in text, f"the scope note no longer says {phrase!r}"
    assert "must never be reported as validating a plywood hull" in text
