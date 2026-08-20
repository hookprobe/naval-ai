"""Gate tests for the P1/P2 geometry kernel — design curves and the section
shape function.

THE TWO MOTIVATING MEASUREMENTS, both taken at commit c7b7c4b on the shipped
code, on 200 draws of `evaluate.sample_valid(200, MissionSpec(), seed=0)` with
Cp and LCB integrated off the DELIVERED geometry:

    Cp      0.386 .. 0.832    18.0% inside the 0.55-0.62 band that was quoted
    LCB   -10.02 .. +13.88    46.5% inside +-3 %LWL

Cp, LCB and the half-angle of entrance were EMERGENT OUTPUTS of fifteen
unrelated shape knobs — the generator could not aim — and `Hull.section()`
returned exactly three points, so every hull it could draw was a hard chine BY
CONSTRUCTION and a fairness integral had nothing to descend.

These tests are the acceptance bars for both plates, and each is written so it
FAILS on the pre-plate kernel (docs/LESSONS.md defect class 3: a test showing a
guard accepts a good case proves nothing).
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from navalai import geometry, grammar, limits
from navalai.evaluate import sample_valid
from navalai.geometry import GeometryError, Hull
from navalai.mission import MissionSpec

G = geometry.G

# The reference hull for the kernel, in the new genome. It is
# `tests/test_phase0.mid_params` with `forefoot` 0.85 -> 0.60: at 0.85 the keel
# rises to within 0.225 m of the waterline at x/L = 0.95 and a 24 deg local
# deadrise cannot enclose the area the sectional area curve asks for there, so
# the old reference vector is REFUSED by `section.solve`. That is information
# about the old reference hull, not a reason to loosen the check.
# R1.5: MID is the ONE reference genome, imported — see navalai/reference.py
# for the provenance of forefoot 0.60 and r_transom 0.30.
from navalai.reference import REFERENCE_HULL

MID = dict(REFERENCE_HULL)

def hull(**kw) -> Hull:
    return Hull(grammar.vector({**MID, **kw}))


# ---------------------------------------------------------------------------
# P1 — the design curves
# ---------------------------------------------------------------------------


def test_the_kernel_delivers_the_prismatic_and_lcb_it_was_asked_for():
    """PLATE P1's ACCEPTANCE BAR: Cp within +-0.01 and LCB within +-0.3 %LWL
    of target on >= 95% of draws.

    BEFORE (c7b7c4b, same 200 draws, targets read as the 0.55-0.62 / +-3%
    bands because there were no targets in the genome to compare against):
    18.0% and 46.5%.

    AFTER, against each hull's OWN `Cp` and `lcb` genes: worst |dCp| 4.30e-06
    and worst |dLCB| 0.000 %LWL, i.e. 100.0% and 100.0%. The residual is
    discretisation of the dense form-coefficient integral, not the solve; the
    solve is exact by construction because `sac_exponents` inverts closed-form
    moments.
    """
    X, _ = sample_valid(60, MissionSpec(), seed=0)
    dcp, dlcb = [], []
    for x in X:
        h = Hull(np.asarray(x, dtype=float))
        fc = h.form_coefficients()
        p = grammar.named(x)
        dcp.append(fc["Cp"] - p["Cp"])
        dlcb.append(fc["lcb_pct"] - p["lcb"])
    dcp, dlcb = np.abs(np.array(dcp)), np.abs(np.array(dlcb))
    assert np.mean(dcp <= limits.PRISMATIC_TOLERANCE) >= 0.95, dcp.max()
    assert np.mean(dlcb <= 0.3) >= 0.95, dlcb.max()
    # and the margin is three orders, not a whisker
    assert dcp.max() < 1e-3 and dlcb.max() < 0.05


def test_the_prismatic_target_is_a_function_of_froude_number_not_a_band():
    """The Cp target is Cp(Fn), and the kernel hits it at every design speed.

    The plate brief originally quoted a FIXED 0.55-0.62 band. A fixed band
    bakes one design speed into the geometry kernel forever: the optimum
    prismatic tracks the transverse-wave hump, so a displacement hull at
    Fn 0.20 and a semi-displacement hull at Fn 0.45 want different numbers.
    `limits.prismatic_target` is the ONE place that relation lives.

    This test asks the kernel to AIM at the Fn-derived target across the SKU
    envelope and measures what it delivers.
    """
    for lwl, kn in ((6.0, 3.0), (6.0, 7.0), (10.0, 5.0), (10.0, 9.0),
                    (16.0, 5.0), (16.0, 12.0)):
        fn = kn * 0.514444 / math.sqrt(G * lwl)
        cp_star = limits.prismatic_target(fn)
        assert grammar.LOW[grammar.NAMES.index("Cp")] <= cp_star \
            <= grammar.HIGH[grammar.NAMES.index("Cp")]
        h = hull(LWL=lwl, BWL=lwl / 3.6, T=lwl / 3.6 / 3.5,
                 D=lwl / 3.6 / 3.5 + 0.30 + 0.045 * lwl, Cp=cp_star)
        assert abs(h.form_coefficients()["Cp"] - cp_star) \
            <= limits.PRISMATIC_TOLERANCE


def test_the_prismatic_curve_rises_with_froude_number_and_clamps_at_both_ends():
    """The relation is a table, and the table has to mean something.

    Monotone increasing (the optimum prismatic rises with speed), and CLAMPED
    rather than extrapolated outside the tabulated range — extrapolating a
    curve whose provenance is 'approx' would manufacture precision it does not
    have.
    """
    fns = [f for f, _ in limits.PRISMATIC_BY_FROUDE]
    cps = [limits.prismatic_target(f) for f in fns]
    assert cps == sorted(cps) and cps[0] < cps[-1]
    assert limits.prismatic_target(-1.0) == cps[0]
    assert limits.prismatic_target(0.05) == cps[0]
    assert limits.prismatic_target(3.0) == cps[-1]
    # the three anchors the relation was pinned to
    assert limits.prismatic_target(0.24) == pytest.approx(0.550, abs=1e-9)
    assert limits.prismatic_target(0.35) == pytest.approx(0.600, abs=1e-9)
    assert limits.prismatic_target(0.50) >= 0.68


def test_the_design_waterline_is_a_curve_the_kernel_owns():
    """`design_waterline` is the section's half-breadth at z = 0, in closed
    form, and the sections agree with it.

    Before plate P1 there was no such curve: the waterline was wherever the
    chine plan-form plus the flare happened to cross z = 0, which is why the
    half-angle of entrance could not be designed. The bar here is that the
    named curve and the sampled sections are the same object — a second
    definition of the waterline is exactly the defect class this repository
    pays for.
    """
    h = hull(roundness=0.6)
    for i in range(1, h.n_stations - 1):
        pts = h.section(i)
        y = float(np.interp(0.0, pts[:, 1], pts[:, 0]))
        assert y == pytest.approx(float(h.y_wl[i]), abs=1e-9)


def test_an_unreachable_design_target_is_refused_not_approximated():
    """Feed the guard the VERBATIM vectors it must reject.

    A generator that silently returns the nearest reachable prismatic is the
    generator plate P1 replaced, so an unreachable (Cp, lcb) is a named
    violation and `Hull` raises rather than clamping.
    """
    # LCB far forward of what a transom-sterned area curve can reach
    with pytest.raises(GeometryError) as e:
        geometry.sac_exponents(10.0, 0.42, 0.50, 0.62, 8.0)
    assert "LCB" in str(e.value)
    # a prismatic below what the transom ordinate alone already contributes
    with pytest.raises(GeometryError) as e:
        geometry.sac_exponents(10.0, 0.68, 0.95, 0.30, 0.0)
    assert "Cp" in str(e.value)
    # and the L0 gate reports it by name rather than building a wrong hull
    bad = grammar.vector({**MID, "x_mb": 0.42, "r_transom": 0.50,
                          "Cp": 0.62, "lcb": 3.5})
    rep = grammar.check(bad)
    assert not rep.ok
    assert any(v.startswith("sac.target") for v in rep.violations), rep.violations


def test_a_non_finite_gene_is_refused_by_name_not_as_an_unreachable_target():
    """G7: a NaN/inf genome must be NAMED as non-finite, at the kernel entry.

    A REFUSAL THAT NAMES THE WRONG THING IS A DEFECT (docs/LESSONS.md: the
    failure must be named correctly), and this kernel had both halves of that
    defect. MEASURED 2026-08-20 BEFORE `geometry._require_finite`, poisoning
    the reference genome one gene at a time, 16 genes x {NaN, +inf} through
    `Hull(params)`:

        11 of 32   BUILT A HULL AND RAISED NOTHING — D, lcb/NaN, beta_bow,
                   beta_len/NaN, rocker/NaN, forefoot/NaN, sheer_rise: a Hull
                   of NaN arrays handed on to the ladder;
        20 of 32   raised `GeometryError` blaming an unreachable DESIGN TARGET
                   instead, e.g. LWL = NaN -> "sac: no exponent pair reaches
                   Cp 0.6000" and T = NaN -> "section: flare 10.0 deg consumes
                   the whole 1.600 m half-beam" — every gene named there is
                   finite and innocent;
         1 of 32   escaped as a bare `ValueError: math domain error`
                   (flare = +inf), which is not a `GeometryError` at all.

    `grammar.check` was already correct one layer up ("finite: NaN/inf in
    parameter vector"), so the gate told the truth and the kernel did not.
    This test sweeps ALL SIXTEEN GENES against NaN, +inf and -inf and demands
    the kernel's own sentence carry both the `finite:` clause and the gene's
    name — the pin that keeps the two layers from drifting into two names for
    one condition.
    """
    base = grammar.vector(MID)
    assert Hull(base) is not None                      # the clean genome builds
    seen = 0
    for i, name in enumerate(grammar.NAMES):
        for bad in (float("nan"), float("inf"), float("-inf")):
            x = base.copy()
            x[i] = bad
            with pytest.raises(GeometryError) as e:
                Hull(x)
            msg = str(e.value)
            assert msg.startswith("finite:"), (name, bad, msg)
            assert name in msg, (name, bad, msg)
            # and the gate's wording is the kernel's wording, not a second one
            assert "NaN/inf in parameter vector" in msg, (name, bad, msg)
            rep = grammar.check(x)
            assert not rep.ok and rep.violations[0].startswith("finite:"), \
                (name, bad, rep.violations)
            seen += 1
    assert seen == 3 * len(grammar.NAMES) == 48

    # the same clause on `sac_exponents`, which is reachable WITHOUT a
    # parameter vector and used to answer LWL = NaN with "sac: no exponent
    # pair reaches Cp 0.6000"
    for pos, nm in enumerate(("LWL", "x_mb", "r_transom", "Cp", "lcb")):
        args = [10.0, 0.55, 0.30, 0.60, -1.0]
        args[pos] = float("nan")
        with pytest.raises(GeometryError) as e:
            geometry.sac_exponents(*args)
        assert str(e.value).startswith("finite:") and nm in str(e.value), \
            str(e.value)


def test_a_section_that_cannot_hold_its_target_area_is_refused():
    """The other half of the same rule, on the SECTION rather than the curve.

    `tests/test_phase0.mid_params`' old forefoot of 0.85 is the verbatim input:
    the keel rises to 0.225 m of draft at x/L = 0.95 while the warped deadrise
    is 24.2 deg there, and a section of that draft and deadrise cannot enclose
    the 0.2000 m^2 the area curve asks for (the cap is A <= d^2 / tan(beta)).
    """
    with pytest.raises(GeometryError) as e:
        Hull(grammar.vector({**MID, "forefoot": 0.85}))
    assert "unreachable" in str(e.value)
    rep = grammar.check(grammar.vector({**MID, "forefoot": 0.85}))
    assert any(v.startswith("section.solve") for v in rep.violations)


def test_a_tumblehome_that_closes_past_the_centreline_is_refused():
    """`np.maximum(ys, 0.0)` used to hide this, and it was not cosmetic.

    Clamping a negative sheer half-breadth moves the topside off the line
    through the design waterline point, so the section stops passing through
    `y_wl` and the closed-form area the kernel is solved against stops
    describing the shape. MEASURED on hull 3 station 10 of
    `grammar.sample(20, rng(0))` under the clamp: exact immersed area
    6.4230e-3 m^2 against the algebra's 6.2426e-3 — 2.9% out, silently.
    """
    bad = {"LWL": 19.4524, "BWL": 5.4214, "T": 0.4144, "D": 2.4449,
           "Cp": 0.6774, "lcb": -2.748, "x_mb": 0.5585, "r_transom": 0.239,
           "beta_mid": 15.4687, "beta_bow": 44.5456, "beta_len": 0.4753,
           "roundness": 0.2112, "rocker": 0.3328, "forefoot": 0.5617,
           "flare": -4.6583, "sheer_rise": 0.0659}
    with pytest.raises(GeometryError) as e:
        Hull(grammar.vector(bad))
    assert "tumblehome" in str(e.value)
    # It is a live constraint, not a tautology: MEASURED over 200,000 uniform
    # in-bounds vectors it fires on 878 of them (0.44%), against gap E4's four
    # deleted checks that fired on 0 of 400,000.
    assert not grammar.check(grammar.vector(bad)).ok


def test_the_delivered_area_curve_is_the_sectional_area_curve():
    """The whole of plate P1 in one assertion: A(x) is DELIVERED, not aimed at.

    `hydro_arrays` integrates the moulded sections; `Hull.A_sac` is the design
    curve. They agree to machine precision at every station, which is what
    makes Cp and LCB properties of a curve the designer set.
    """
    for rho in (0.0, 0.35, 0.9):
        h = hull(roundness=rho)
        a, _b, _zc = h.hydro_arrays(0.0)
        assert np.allclose(2.0 * a, h.A_sac, atol=1e-12, rtol=0.0)


def test_the_entrance_half_angle_is_measured_on_a_named_curve():
    """alpha_e is the DWL's entry slope and it MOVES when the bow is fined.

    Not an acceptance bar for this plate — constraining alpha_e is plate P5 —
    but the quantity has to exist and be sensitive before P5 can constrain it.
    A finer forebody (a lower prismatic at a fixed max-area station) gives a
    finer entry.
    """
    fine = hull(Cp=0.53).alpha_e_deg()
    full = hull(Cp=0.60).alpha_e_deg()
    assert 0.0 < fine < full
    # MEASURED on the reference hull: 34.39 deg at Cp 0.53, 43.66 at Cp 0.60.
    # Both are far outside the 7-12 deg band a fine entry wants, which is
    # plate P5's finding and not this plate's to fix — but it is now a number
    # measured on a named curve rather than an accident of three others.
    assert full - fine > 5.0


# ---------------------------------------------------------------------------
# P2 — the section shape function
# ---------------------------------------------------------------------------


def test_roundness_zero_is_the_old_three_point_polyline_to_1e_12():
    """PLATE P2's compatibility clause: hard chine stays EXACTLY reachable.

    `roundness == 0` must reproduce the pre-plate geometry, or every gate that
    measures a chine hull — Gate 6D's refold, Gate F's manufacturing export,
    the chine-row work in bbf1a47 — is measuring a different surface.
    """
    h = hull(roundness=0.0)
    for i in (0, 7, 20, 33, 40):
        pts = h.section(i)
        assert pts.shape == (3, 2)
        assert pts[0] == pytest.approx([0.0, h.z_keel[i]], abs=1e-12)
        assert pts[1] == pytest.approx([h.y_chine[i], h.z_chine[i]], abs=1e-12)
        assert pts[2] == pytest.approx([h.y_sheer[i], h.z_sheer[i]], abs=1e-12)
    # and the mesh rows are the old two-panel linear interpolation, exactly
    nz, xv = 16, 4.321
    jc = h.chine_row(nz)
    S = h._section_at_rows(xv, jc, nz - jc)
    K, _p0, C, _p2, Sh = h.section_control(0)      # shape at the transom only
    i = int(np.searchsorted(h.x, xv))
    f = (xv - h.x[i - 1]) / (h.x[i] - h.x[i - 1])

    def lerp(a):
        return (1 - f) * a[i - 1] + f * a[i]

    Kv = np.array([0.0, lerp(h.z_keel)])
    Cv = np.array([lerp(h.y_chine), lerp(h.z_chine)])
    Sv = np.array([lerp(h.y_sheer), lerp(h.z_sheer)])
    for j in range(jc + 1):
        want = Kv + (j / jc) * (Cv - Kv)
        assert S[j] == pytest.approx(want, abs=1e-12)
    for j in range(1, nz - jc + 1):
        want = Cv + (j / (nz - jc)) * (Sv - Cv)
        assert S[jc + j] == pytest.approx(want, abs=1e-12)


def test_a_round_bilge_section_reproduces_its_analytic_area_to_1e_6():
    """PLATE P2's ACCEPTANCE BAR, on THREE independent derivations of one area.

    (1) `Hull.section_area` — the quadratic-coefficient algebra the chine
        half-breadth is solved from,
    (2) `immersed_section` — a polygon on five control points plus the
        parabolic segment (Archimedes' 2/3 of the control triangle),
    (3) a dense sampled polygon of the shape function itself.

    (1) and (2) agree to 8.9e-16 m^2, and (3) converges on them: MEASURED on
    the roundest hull of `grammar.sample(20, rng(0))` (roundness 0.995,
    half-area 0.77065390 m^2) the sampled polygon reads 4.80e-4 relative at 32
    points per half, 9.71e-6 at 256 and 6.08e-7 at 1024. Two closed forms that
    agree and a quadrature that converges to both is what makes the number
    trustworthy; one closed form on its own is an assertion.
    """
    for rho in (0.15, 0.5, 0.85, 1.0):
        h = hull(roundness=rho)
        for i in (5, 15, 25, 35):
            exact = h.section_area(i)
            assert h.immersed_section(i, 0.0)[0] == pytest.approx(exact, abs=1e-12)
            pts = h._section_points(i, 4000, 4000)
            k = int(np.count_nonzero(pts[:, 1] < 0.0))
            prev, cur = pts[k - 1], pts[k]
            t = -prev[1] / (cur[1] - prev[1])
            poly = np.vstack([pts[:k],
                              [[prev[0] + t * (cur[0] - prev[0]), 0.0]],
                              [[0.0, 0.0]]])
            sampled = geometry._polygon(poly)[0]
            assert abs(sampled - exact) < 1e-6
            assert abs(sampled - exact) / exact < 1e-6


def test_the_immersed_area_is_exact_at_every_waterline_not_only_the_design_one():
    """`hydrostatics` floats the hull, so the area has to be exact off z = 0.

    The waterline can cut the bilge fillet itself, which is why `_immersed`
    splits the arc with de Casteljau rather than integrating a chord.
    """
    h = hull(roundness=0.8)
    for i in (4, 12, 28):
        d = float(-h.z_keel[i])
        for wl in (-0.75 * d, -0.5 * d, -0.25 * d, 0.0, 0.2 * float(h.z_sheer[i])):
            a, _b, _zc = h.immersed_section(i, wl)
            pts = h._section_points(i, 4000, 4000)
            if pts[0, 1] >= wl:
                assert a == 0.0
                continue
            k = int(np.count_nonzero(pts[:, 1] < wl))
            if k >= len(pts):
                poly = np.vstack([pts, [[0.0, pts[-1, 1]]]])
            else:
                prev, cur = pts[k - 1], pts[k]
                t = (wl - prev[1]) / (cur[1] - prev[1])
                poly = np.vstack([pts[:k],
                                  [[prev[0] + t * (cur[0] - prev[0]), wl]],
                                  [[0.0, wl]]])
            ref = geometry._polygon(poly)[0]
            assert a == pytest.approx(ref, rel=2e-6)


def test_fairness_is_finite_on_a_radiused_bilge_and_diverges_on_a_knuckle():
    """PLATE P2's second acceptance bar, and one clause of it is REFUTED.

    The bar as written was "fairness is finite and FALLS under refinement".
    MEASURED on the reference hull at nx = 21:

        nz        rho=0     rho=0.25      rho=0.5      rho=1.0
        32        143.6        68.33        42.79        24.17
        64        276.7        85.56        48.87        26.14
       128          568        98.37        53.07        27.16
       256         1089        106.4        55.32        27.70
       512         2273        111.3        56.53        27.96
      1024         4654        113.8        57.13        28.08

    The knuckle DIVERGES linearly in nz — int ||d2S/ds2||^2 across a corner is
    genuinely infinite and the discrete estimator says so, doubling with every
    doubling of the sampling. A radiused bilge CONVERGES, and it converges
    from BELOW: the increments halve (1.97, 1.02, 0.54, 0.26, 0.12 at
    roundness 1). So "falls under refinement" is refuted as stated — a
    consistent estimator of a finite integral approaches its limit from
    whichever side its truncation error sits, and for a C1 section sampled
    uniformly in arc length that is from below. What DOES fall is the
    fairness with roundness, which is the next test.

    Recorded rather than quietly re-worded, because the bar came from a plan
    and the measurement disagrees with it.
    """
    e = {nz: hull(roundness=0.0).fairness(nx=21, nz=nz) for nz in (128, 256, 512)}
    assert e[256] / e[128] > 1.85 and e[512] / e[256] > 1.85     # diverges
    r = {nz: hull(roundness=0.5).fairness(nx=21, nz=nz)
         for nz in (128, 256, 512, 1024)}
    assert all(math.isfinite(v) for v in r.values())
    d1, d2, d3 = r[256] - r[128], r[512] - r[256], r[1024] - r[512]
    assert d1 > d2 > d3 > 0.0                       # converging, from below
    assert d3 / d1 < 0.35


def test_fairness_falls_monotonically_as_the_bilge_is_rounded():
    """MEASURED at nz = 256 on the reference hull, roundness 0 -> 1:

        1088.67, 235.04, 106.40, 55.32, 37.07, 27.70

    a factor of 39 from knuckle to full fillet, monotone. THIS is the signal
    an optimiser can descend, and it did not exist before plate P2: on a
    three-point section every interior second difference is exactly zero and
    the entire metric is carried by the one corner point, so it was a pure
    function of the sampling with no dependence on the hull's shape.
    """
    vals = [hull(roundness=r).fairness(nx=21, nz=256)
            for r in (0.0, 0.1, 0.25, 0.5, 0.75, 1.0)]
    assert vals == sorted(vals, reverse=True)
    assert vals[0] / vals[-1] > 20.0


def test_the_unroller_refuses_a_round_bilge_rather_than_measuring_the_wrong_hull():
    """A filleted bilge is not developable from flat sheet — that is a fact
    about sheet material, not a limitation of `unroll`.

    `_PANEL_EDGES` assumes exactly two panels meeting at a chine. Developing a
    round-bilge hull against it would return a refold deviation measured
    against the chine curve of a hull that has no chine, which is Gate 6D
    reporting a number for the wrong surface. Gate 6D and Gate F keep working
    on hard-chine hulls, where the kernel reproduces the old geometry exactly
    (see the 1e-12 test above).
    """
    from navalai import unroll
    assert len(unroll.hull_panels(hull(roundness=0.0))) == 2
    with pytest.raises(ValueError) as e:
        unroll.hull_panels(hull(roundness=0.4))
    assert "roundness" in str(e.value)


def test_the_bilge_feature_is_on_a_grid_row_for_a_fillet_as_well_as_a_chine():
    """bbf1a47's rule, generalised: the mesh resolves the bilge, it does not
    chord across it.

    At roundness 0 the row carries the chine itself. At roundness > 0 it
    carries the fillet's mid-point, which is the same convention
    `Hull.chine_row` has always described — the row where the bottom panel's
    allocation ends.
    """
    for rho in (0.0, 0.55):
        h = hull(roundness=rho)
        nz = 24
        jc = h.chine_row(nz)
        assert 1 <= jc <= nz - 1
        for xv in (1.0, 5.0, 8.5):
            rows = h._section_at_rows(xv, jc, nz - jc)
            coarse = h._section_at_rows(xv, 1, 1)
            assert rows[jc] == pytest.approx(coarse[1], abs=1e-9)


def test_the_section_sampler_is_uniform_in_arc_length():
    """The spacing has to be uniform or the fairness estimator reads its own
    sampling as a crease.

    MEASURED with the first sampler, which split the parameter interval by the
    roundness instead: a step in segment length at the joint between the
    straight leg and the fillet made the ROUND bilge diverge 2.7e3 -> 2.6e6
    over nz 32 -> 1024, indistinguishable from the knuckle it exists to be
    told apart from.
    """
    h = hull(roundness=0.7)
    for i in (6, 18, 30):
        for n in (32, 96):
            pts = h._section_points(i, n, n)
            seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
            for half in (seg[:n], seg[n:]):
                # The CHORDS are shorter than the arc they subtend by
                # (kappa*h)**2/24, so equal arc length does not give exactly
                # equal chords and the right bar is on the STEP, not the
                # spread: no neighbouring pair may differ by more than 1e-3.
                # MEASURED worst 1.78e-3 at 32 points per half, all of it
                # inside the fillet where the curvature is; the straight legs
                # are uniform to 1e-16, and the step falls as 1/n**2 (7.1e-4 at
                # 64, 1.0e-4 at 128). The first sampler, which split the
                # parameter interval by the roundness instead, put a step of
                # O(1) here — which is 2000x this and is what the fairness
                # estimator read as a crease.
                step = np.abs(half[1:] / half[:-1] - 1.0).max()
                assert step < 3e-3, step


def test_the_kernel_stays_inside_the_slider_budget():
    """Gate 4's bar is p95 < 100 ms on `evaluate()`, and a geometry kernel that
    quietly breaks the slider gate is a regression whatever else it fixes.

    MEASURED on this machine over 30 L0-feasible hulls: p95 11.1 ms before the
    plates and 28.2 ms after, against the 100 ms bar. The cost is the section
    shape function, and it is bounded by MEMOISING the section per hull — the
    draft bisection in `solve_to_displacement` built 7842 sections where 410
    were distinct, which alone was 61.6 ms.

    The station count is UNCHANGED at 41: this kernel adds points ACROSS a
    section, never along the hull.
    """
    import time

    from navalai.evaluate import evaluate

    assert Hull(grammar.vector(MID)).n_stations == 41
    X, _ = sample_valid(12, MissionSpec(), seed=3)
    m = MissionSpec()
    ts = []
    for x in X:
        t = time.perf_counter()
        evaluate(np.asarray(x, dtype=float), m)
        ts.append((time.perf_counter() - t) * 1e3)
    assert float(np.percentile(ts, 95)) < 100.0, sorted(ts)
