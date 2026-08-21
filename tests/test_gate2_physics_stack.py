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
    """GATE 2-PHYS-A. The Wigley hull's displaced volume is EXACTLY 4LBT/9.

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
    so Gate 2-PHYS-A checks an INTEGRATOR against MATHEMATICS rather than checking
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
    """GATE 2-PHYS-D. KCS keeps its place and loses its title.

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


def test_gate2c_the_DSYHS_data_verifies_ITSELF_before_anything_is_claimed():
    """GATE 2-PHYS-C, integrity half. Acquired data is guilty until checked.

    `benchmarks/holtrop_cases.py` sets the standard three files away: one
    worked example from an OCR'd scan, trusted only because two INDEPENDENT
    internal checks would break under corruption. DSYHS clears that bar by a
    wider margin, because it was downloaded rather than transcribed and
    4TU.ResearchData publishes an MD5 beside every file.

    These are the two internal checks, re-run here rather than asserted from
    the docstring -- a provenance note nothing executes is exactly the
    'claim of single-sourcing' this project has been burned by before.
    """
    import statistics

    from benchmarks import dsyhs

    d = dsyhs.load()
    hyd = d["hydrostatics"]
    assert len(hyd) >= 50, f"only {len(hyd)} models — the extraction is short"

    # CHECK 1: Cb derived from the primaries must equal the file's own cb0.
    # A shifted column, a unit error or a truncated float all break this.
    worst = 0.0
    for s, h in hyd.items():
        cb = h["vol_m3"] / (h["lwl_m"] * h["bwl_m"] * h["tc_m"])
        worst = max(worst, abs(cb - h["cb"]) / h["cb"])
    assert worst < 1e-6, (
        f"derived Cb disagrees with the released cb0 by {100*worst:.4f}% — "
        f"the extraction has mis-mapped a column")

    # CHECK 2: the wetted-surface shape ratio is dimensionless and must sit
    # in a narrow band for a family of similar hulls. A corrupted sc0 sprays.
    rat = [h["sc_m2"] / (h["lwl_m"] * (h["bwl_m"] + 2 * h["tc_m"]))
           for h in hyd.values()]
    assert 0.45 < min(rat) and max(rat) < 0.65, (
        f"wetted-surface shape ratio {min(rat):.4f}..{max(rat):.4f} is "
        f"outside the measured 0.4901..0.6089 band")
    assert 0.50 < statistics.median(rat) < 0.60

    # and the source files' publisher checksums are recorded, so a silent
    # re-download of different data is detectable
    md5 = d["source"]["files_md5"]
    assert len(md5) >= 4 and all(len(v) == 32 for v in md5.values())


def test_gate2c_our_FRICTION_LINE_reproduces_51_real_hulls():
    """GATE 2-PHYS-C, physics half — and this is the rung KCS could never provide.

    At Fn ~0.1 a bare hull is friction-dominated, so measured TOTAL
    resistance is a fair test of the friction line by itself. MEASURED
    2026-08-21 over 108 points in Fn 0.09-0.16 across 51 DSYHS models:

        ITTC-57 friction / measured total
        min 0.531   MEDIAN 0.932   max 2.438

    The median is the claim: our viscous model accounts for 93% of the
    measured resistance of real displacement hulls, with the remainder being
    form drag and residual wave-making — which is what it should be.

    THE BAND'S LOWER EDGE IS AN INSTRUMENT LIMIT, NOT A FIT. It first ran
    from Fn 0.09 and 33 of 108 points came back with friction EXCEEDING
    measured total — impossible for a bare hull. Splitting the band located
    them exactly: below Fn 0.12 the median ratio is 1.026 on a median force
    of 0.303 N, and all six worst cases sit at Fn 0.100 on 0.11-0.23 N. A
    tenth of a newton is the towing-tank load cell's floor. Excluding data
    the INSTRUMENT cannot resolve is a different act from excluding data that
    disagrees, and the test below refuses the wider band so the distinction
    cannot quietly erode.

    NOT CLAIMED: these are round-bilge yacht canoe bodies. They do not
    exercise chine spray, hard-chine separation or transom ventilation. The
    hard-chine anchor (Naples Systematic Series) is still owed, and a DSYHS
    pass must never be reported as validating chine physics — that is the
    exact mistake the 2026-08-21 reframe was correcting.
    """
    import statistics

    from benchmarks import dsyhs
    from navalai.resistance import NU_FRESH_15C, ittc57_cf

    ratios = []
    for _s, _fn, rt, lwl, sc, v in dsyhs.friction_band_points():
        rf = 0.5 * dsyhs.RHO_FRESH * v * v * sc * ittc57_cf(
            v, lwl, nu=NU_FRESH_15C)
        ratios.append(rf / rt)

    assert len(ratios) >= 60, f"only {len(ratios)} points in the band"
    med = statistics.median(ratios)

    # the friction line carries most of the measured resistance...
    assert 0.85 < med < 1.00, (
        f"ITTC-57 accounts for {100*med:.1f}% of measured total at low Fn; "
        f"measured 90.4% on acquisition. Outside 85-100% the viscous model "
        f"or the wetted surface has moved.")
    assert med == pytest.approx(dsyhs.FRICTION_FRACTION_MEDIAN, abs=0.02)

    # ...and it must not EXCEED it for most points, because friction cannot
    # be more than the total. A majority above 1.0 would mean the wetted
    # surface or the friction line is systematically too big.
    over = sum(1 for r in ratios if r > 1.0)
    assert over < 0.20 * len(ratios), (
        f"{over}/{len(ratios)} points have friction exceeding measured "
        f"total — physically impossible for a bare hull. Measured 10% on "
        f"acquisition in this band.")

    # AND THE EXCLUDED BAND MUST STILL BE UNUSABLE. If Fn 0.09-0.12 ever
    # passed, the lower edge would be an arbitrary trim rather than an
    # instrument limit, and this whole rung would be tuned.
    import math as _m

    from navalai.resistance import NU_FRESH_15C as _NU
    from navalai.resistance import ittc57_cf as _cf
    d = dsyhs.load()
    below = []
    for s, hy in d["hydrostatics"].items():
        L, S = hy["lwl_m"], hy["sc_m2"]
        for p in d["resistance"].get(s, ()):
            fn = dsyhs.froude(p["v_ms"], L)
            if 0.09 <= fn < dsyhs.FRICTION_BAND_FN[0]:
                v = p["v_ms"]
                below.append(0.5 * dsyhs.RHO_FRESH * v * v * S
                             * _cf(v, L, nu=_NU) / p["rt_n"])
    assert below, "the excluded band is empty — the split has been lost"
    assert statistics.median(below) > 1.0, (
        f"Fn 0.09-0.12 now reads a median ratio of "
        f"{statistics.median(below):.3f}; if that band became physical the "
        f"lower edge is no longer an instrument limit and must be re-derived")
