"""Gate DWL: the design waterline B(x) — the second of the three coupled
curves, and the audit's named kernel repair for one-curve-two-jobs.

Phase 3, slice 1 (2026-08-27). With `dwl` > 0 the section receives BOTH
targets — A(x) from the SAC and w(x) from the designed waterline — and the
flare becomes a DERIVED per-station quantity: substituting u = w - d*f into
the section's closed form gives a polynomial in f whose f^2 coefficient is
m*d^2*(c1 - c2 - 1), and the fillet identity c1 - c2 = 1 makes it VANISH,
so the joint solve is the root of a LINEAR equation and the kernel stays
closed form. The derived flare saturates smoothly (tanh) toward
per-station caps and the chine is then always solved from the AREA, so the
SAC — the displacement contract — is delivered exactly at every dwl and
the waterline approximates B(x) as closely as the caps allow.

WHAT THIS SLICE DELIVERS, measured: the barge family reaches critic margin
+0.06 under the GENERAL monohull bar (legacy needed a family-specific bar
at +4.26). WHAT IT DOES NOT, measured and recorded as a sentinel below: a
slender-Cp hull cannot take a much fuller waterline yet, because the
topside is ONE panel — flare that lifts the waterline drags the SHEER out
with it (5.7 m of deck beam on a 3.2 m hull). The fix is the waterline as
a true KNUCKLE vertex (Phase 3's knuckle-list item), not more genes.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from navalai import grammar, morphology
from navalai.geometry import Hull, waterline_ordinate
from navalai.reference import REFERENCE_HULL


def _margin(h: Hull) -> float:
    return float(morphology.shape_margin(
        morphology.describe(morphology.from_hull(h))))


def test_dwl_zero_is_bit_identical():
    """The POST_HOC law, asserted at exactly 0.0 difference: at dwl = 0 the
    joint-solve branch is unreachable code and every station quantity is
    the legacy solve's, bit for bit — on the reference hull and on 10
    seeded legacy draws."""
    h0 = Hull(grammar.vector(REFERENCE_HULL))
    h1 = Hull(grammar.vector(dict(REFERENCE_HULL, dwl=0.0)))
    for attr in ("y_wl", "y_chine", "z_chine", "y_sheer", "z_sheer"):
        assert np.array_equal(getattr(h0, attr), getattr(h1, attr)), attr

    rng = np.random.default_rng(7)
    X = grammar.sample(10, rng)
    for row in X:
        assert float(row[grammar.NAMES.index("dwl")]) == 0.0, (
            "the legacy stream drew a non-zero dwl — the draw is no longer "
            "arity-stable and every seeded population just moved")
        try:
            h = Hull(row)
        except Exception:
            continue
        row2 = row.copy()
        assert np.array_equal(h.y_wl, Hull(row2).y_wl)


def test_the_joint_solve_is_the_exact_inverse_of_the_section_form():
    """Property test of the linear flare solve: generate TRUE sections
    (pick yc, f; derive A, w), invert, and demand f back to 1e-6. The f^2
    coefficient vanishing is an identity, not an approximation — 2000
    random sections measured 0 mismatches when this landed."""
    rng = np.random.default_rng(3)
    checked = 0
    for _ in range(400):
        d = rng.uniform(0.2, 1.0)
        m = math.tan(rng.uniform(0.0, 0.5))
        rho = rng.uniform(0.0, 1.0)
        c1, c2 = 2.0 - rho * rho / 3.0, 1.0 - rho * rho / 3.0
        yc_t = rng.uniform(0.05, 2.0)
        f_t = rng.uniform(-0.4, 1.5)
        K_t = 1.0 - m * f_t
        if K_t <= 0.05:
            continue
        A = K_t * yc_t * (c1 * d - c2 * m * yc_t) + d * d * f_t
        w = K_t * yc_t + d * f_t
        if A <= 0.0 or w <= 0.0:
            continue
        a0 = A - c1 * d * w + c2 * m * w * w
        a1 = -A * m + c1 * d * (d + m * w) - 2.0 * c2 * m * d * w - d * d
        if abs(a1) < 1e-12:
            continue
        assert abs(-a0 / a1 - f_t) < 1e-6
        checked += 1
    assert checked > 200


def test_the_sac_is_still_delivered_exactly_at_every_dwl():
    """The section is AREA-faithful whatever the waterline asks: delivered
    Cp tracks the gene at dwl = 1 exactly as it does at dwl = 0 — the
    displacement contract survives the second curve."""
    from navalai.limits import PRISMATIC_TOLERANCE

    g = dict(REFERENCE_HULL, dwl=1.0, cwp_x=0.10, r_stem=0.06, rb_stem=0.05,
             rb_transom=0.60, forefoot=0.15)
    h = Hull(grammar.vector(g))
    cp = h.form_coefficients()["Cp"]
    assert abs(cp - g["Cp"]) <= PRISMATIC_TOLERANCE


def test_waterline_ordinate_is_the_sac_family_with_its_own_ratios():
    g = dict(REFERENCE_HULL, dwl=1.0, rb_transom=0.55, rb_stem=0.12,
             cwp_x=0.05)
    x = grammar.vector(g)
    L = g["LWL"]
    xs = np.array([0.0, g["x_mb"] * L, L])
    b = waterline_ordinate(x, xs)
    assert b[0] == pytest.approx(0.55)          # transom ratio
    assert b[1] == pytest.approx(1.0)           # unity at the max station
    assert b[2] == pytest.approx(0.12)          # stem ratio


def test_the_barge_no_longer_needs_its_family_bar_THE_PAYOFF():
    """MEASURED the day this landed. The proven 16x4 barge under the
    GENERAL monohull critic: legacy (dwl = 0) margin +4.26 — refused, and
    P5 added a barge family bar to keep the shape row satisfiable. The
    SAME hull with the waterline DESIGNED (dwl = 1, rb_transom 0.97,
    rb_stem 0.35): margin +0.06, beam carried 0.85 vs 0.61. One gene set
    to 1 did more for the barge than the family bar — because the barge's
    real shape IS a designed waterline, and the kernel could finally be
    told so. Bars: dwl margin under 1.0 and at least 3.0 better than
    legacy, so drift in either solve fails loudly without pinning noise.
    """
    barge = dict(Cp=0.92, r_transom=0.92, r_stem=0.40, lcb=-1.5,
                 x_mb=0.50, beta_mid=8.0, beta_bow=10.0, beta_len=0.45,
                 roundness=0.0, rocker=0.05, forefoot=0.10, flare=6.0,
                 sheer_rise=0.12, LWL=15.2, BWL=4.0, T=0.391, D=1.55)
    legacy = Hull(grammar.vector(dict(REFERENCE_HULL, **barge)))
    designed = Hull(grammar.vector(dict(
        REFERENCE_HULL, **barge, dwl=1.0, rb_transom=0.97, rb_stem=0.35)))
    m_legacy, m_dwl = _margin(legacy), _margin(designed)
    assert m_dwl < 1.0, (
        f"designed-waterline barge margin {m_dwl:+.2f} — the dwl solve "
        f"regressed")
    assert m_legacy - m_dwl >= 3.0, (
        f"legacy {m_legacy:+.2f} vs dwl {m_dwl:+.2f}: the payoff shrank")
    carried = float((2.0 * designed.y_wl >= 0.9 * 4.0).mean())
    assert carried >= 0.75


def test_SENTINEL_the_single_panel_topside_still_blocks_slender_full_wl():
    """A NEGATIVE RESULT, recorded so nobody re-derives it (the stageE
    pattern). The #17 collision — slender mission Cp + critic-clean
    waterline — is NOT yet closed by dwl: making the waterline fuller
    through derived flare drags the SHEER out on the same panel. MEASURED:
    Cp 0.573 with cwp_x +0.20, rb_transom 0.60 builds, but the critic
    still refuses (margin +11.4 when this landed; asserted only > 1 so
    fairness drift does not false-alarm) and the sheer beam reads ~5.7 m
    on a 3.2 m BWL hull. THE FIX IS A KNUCKLE AT THE WATERLINE — the
    section gaining a vertex so the topside stops being one panel — which
    is Phase 3's knuckle-list item. When that lands, this test should be
    INVERTED into the second payoff test, not deleted.
    """
    g = dict(REFERENCE_HULL, dwl=1.0, Cp=0.573, cwp_x=0.20, r_stem=0.04,
             rb_stem=0.06, rb_transom=0.60, forefoot=0.15)
    h = Hull(grammar.vector(g))
    assert _margin(h) > 1.0, (
        "the slender full-waterline hull now PASSES the critic — the "
        "knuckle (or something else) landed; invert this sentinel into a "
        "payoff test and record what changed")
    assert float(np.max(h.y_sheer)) > 1.5 * float(np.max(h.y_wl)) - 1.0, (
        "the sheer no longer explodes past the waterline — re-measure "
        "this sentinel's mechanism")


def test_an_impossible_request_is_delivered_as_measured_deviation():
    """rb_stem 0.4 with r_stem = 0 asks for waterline beam at a stem with
    ZERO sectional area. The faired solve does not refuse it — B(x) is a
    target the caps approximate — but it must not pretend either: the
    delivered stem waterline stays near zero (the AREA is the contract)
    and `Hull.dwl_deviation()` reports the gap, so the request-vs-achieved
    difference is a RECEIPT, never a silent success."""
    g = dict(REFERENCE_HULL, dwl=1.0, rb_stem=0.4, r_stem=0.0)
    h = Hull(grammar.vector(g))
    dev = h.dwl_deviation()
    # the stem asked for 0.4 * BWL/2 = 0.64 m of half-breadth on zero area;
    # the flare cap delivers 0.18 m (measured) — area-faithful, not the ask
    assert float(h.y_wl[-1]) < 0.25
    assert float(dev[-1]) > 0.3, (
        "the deviation receipt does not show the impossible stem request")
    # and a hull with no designed curve reports zero deviation everywhere
    h0 = Hull(grammar.vector(REFERENCE_HULL))
    assert not h0.dwl_deviation().any()


def test_the_arity_event_is_lawful():
    """27 genes; the four new ones are post-hoc with in-bounds no-op
    defaults; pad_genome lifts a 23-vector to the same hull."""
    assert grammar.N_PARAMS == 27
    for g in ("dwl", "cwp_x", "rb_transom", "rb_stem"):
        assert g in grammar.POST_HOC_DEFAULTS
        i = grammar.NAMES.index(g)
        v = grammar.POST_HOC_DEFAULTS[g]
        assert grammar.LOW[i] <= v <= grammar.HIGH[i]
    x27 = grammar.vector(REFERENCE_HULL)
    x23 = x27[:23]
    assert np.array_equal(grammar.pad_genome(x23), x27)
