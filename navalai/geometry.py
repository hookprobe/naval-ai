"""Geometry kernel: DESIGN CURVES -> stations -> sections -> integral properties.

THE PARAMETRISATION IS INVERTED (plate P1, 2026-08-13), AND THE SECTION IS NO
LONGER THREE POINTS (plate P2).

MEASURED at commit c7b7c4b on 200 draws of `evaluate.sample_valid(200,
MissionSpec(), seed=0)`, with Cp and LCB integrated off the delivered geometry:

    Cp      0.386 .. 0.832    only 18.0% inside the 0.55-0.62 band
    LCB   -10.02 .. +13.88    only 46.5% inside +-3 %LWL

Cp, LCB and the half-angle of entrance were EMERGENT OUTPUTS of fifteen
unrelated shape knobs. A naval architect CHOOSES Cp for the design Froude
number, CHOOSES LCB for balance, then finds a surface that satisfies them; that
generator could not aim. So:

  * `sac_ordinate` / `sectional_area` make the SECTIONAL AREA CURVE A(x) a
    first-class design curve. Its two shape exponents are SOLVED from the
    `Cp` and `lcb` genes (`sac_exponents`), so Cp and LCB are inputs and the
    exponents are outputs — the exact inverse of the old arrangement.
  * `design_waterline` makes the DESIGN WATERLINE y_wl(x) a first-class curve
    with a closed form, so `Hull.alpha_e_deg()` is a measured property of a
    named curve instead of an accident of the chine plan-form times a flare
    times a stem taper.
  * `_stations` SOLVES the chine half-breadth at every station, in closed
    form, so that the delivered immersed area IS A(x). The chine plan-form
    `0.5 * BWL * w(x)` is gone: a plan-form is what you get, not what you ask
    for.

THE SECTION IS A SHAPE FUNCTION, NOT A POLYLINE. `Hull.section` used to return
exactly three points — keel, chine, sheer — so every hull the grammar could
express was a hard chine BY CONSTRUCTION: round bilge was not untried, it was
inexpressible, and a polyline has no curvature, so surface fairness was
identically zero. `roundness` fillets the bilge with a quadratic Bezier whose
area is closed-form, and `roundness == 0` reproduces the old three-point
section EXACTLY (fenced by `tests/test_geometry_kernel.py`).

Coordinates: x = 0 at the transom, x = LWL at the stem; z = 0 at the design
waterline, z negative down; y is the starboard half-breadth.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache

import numpy as np

from . import grammar

# Declarations live in navalai/constants.py (§18, one home); geometry
# remains the import point its many consumers already use.
from .constants import G_STANDARD as G
from .constants import RHO_FRESH as RHO_WATER

# Sectional-area-curve shape exponents. The SOLVER may only return values in
# this band, and a (Cp, lcb) pair it cannot reach inside it is REFUSED by
# `grammar.check` rather than approximated — an unreachable design target
# scored as a reachable one is defect class 1 (an unmeasurable value scored as
# a passing one) applied to a design intent.
#
# THE FAMILY IS TWO-SIDED, and the first version of it was not — which cost
# five sixths of the search box. MEASURED on 4000 uniform in-bounds vectors
# with the one-sided shape `h(s) = s**p, p in [1, 8]`: `sac.target` refused
# 66.4% of them and the L0 feasible fraction fell from 20.69% to 4.00%. The
# mechanism is that `int h` only reaches (0, 1/2] for p >= 1, so the family
# could make a run FINER than a straight line but never FULLER, and the
# transom-area gene then fought the Cp gene over a range neither could give up.
#
#     h(s; p) = s**p                  p >= 1   (fine;  int h = 1/(p+1))
#     h(s; p) = 1 - (1-s)**(2-p)      p <= 1   (full;  int h = (2-p)/(3-p))
#
# The two branches agree in value AND first derivative at p = 1, so `int h` is
# a C1 monotone decreasing function of p over the whole band and the bisection
# below is bracketed on a continuous residual. Neither branch has an unbounded
# derivative anywhere in [SAC_P_MIN, SAC_P_MAX], which is why the band is
# closed at 2 - SAC_P_MAX rather than run to -inf.
SAC_P_MAX = 8.0
SAC_P_MIN = 2.0 - SAC_P_MAX

#: Closure cap on the flare slope forward of the max-area station: f is
#: allowed at most this fraction of A / d^2, so the section quadratic's
#: rhs = A - d^2 f keeps at least (1 - frac) * A of margin and yc stays
#: strictly positive wherever the section carries any area at all. This is a
#: kernel numerical guard, not a design limit — the DESIGN flare law is
#: `flare`/`flare_bow`/`flare_len`, and this cap binds only where sections
#: vanish (audit 2026-08-26, finding D.3: the old area-curve multiplier
#: made `flare_bow` a no-op at the stem).
_FLARE_CLOSURE_FRAC = 0.75

# Points sampled along each half of the section by `Hull.section` when
# `roundness > 0`.
#
# THIS RESOLUTION DOES NOT SET THE AREA. `immersed_section` integrates the
# section in CLOSED FORM off five control points, so displacement, waterplane
# and KB carry no sampling error at all (that is what meets plate P2's 1e-6
# bar; see `_immersed`). What this number sets is the GIRTH and the
# half-breadth table — `wetted_surface` and `offsets_grid` — which are
# piecewise-linear readings of the same shape function.
#
# MEASURED over `grammar.sample(20, rng(0))`, worst relative error against
# n = 4096:
#
#         n     wetted_surface    offsets_grid
#        16          6.24e-03        3.00e-03
#        32          2.01e-03        1.18e-03
#        64          6.01e-04        4.69e-04
#       128          4.45e-04        1.29e-04   <- SHIPPED
#       256          3.36e-04        2.91e-05
#
# 128 sits where the curve flattens: doubling it again buys 25% on the wetted
# surface, which is four orders below the friction-line uncertainty it feeds.
SECTION_FILLET_SAMPLES = 128


class GeometryError(ValueError):
    """A design target this shape family cannot realise.

    Raised rather than clamped. A hull whose sectional area curve asks for
    more area than the deadrise and draft can enclose is not a slightly-wrong
    hull, it is an unbuildable request, and `grammar.check` turns this into a
    named violation.
    """


# --------------------------------------------------------------------------
# The sectional area curve: A(x) = A_mid * a(x), with a(x)'s exponents SOLVED
# from Cp and LCB.
# --------------------------------------------------------------------------


def _require_finite(params) -> np.ndarray:
    """Refuse a non-finite genome AT THE KERNEL ENTRY, naming the gene.

    A REFUSAL THAT NAMES THE WRONG THING IS A DEFECT, NOT A COSMETIC ISSUE
    (G7, MEASURED 2026-08-20 on the reference genome, one gene poisoned at a
    time, 16 genes x {NaN, +inf} = 32 probes through `Hull(params)`):

        11 of 32 BUILT A HULL AND RAISED NOTHING (D, lcb/NaN, beta_bow,
          beta_len/NaN, rocker/NaN, forefoot/NaN, sheer_rise) — a Hull whose
          arrays are NaN, handed on to the ladder;
        20 raised a `GeometryError` whose sentence names an unreachable DESIGN
          TARGET, e.g. LWL = NaN -> "sac: no exponent pair reaches Cp 0.6000"
          and T = NaN -> "section: flare 10.0 deg consumes the whole 1.600 m
          half-beam"  — both blame a gene that is perfectly finite;
        1 escaped as a bare `ValueError: math domain error` (flare = +inf),
          which is not a `GeometryError` at all and so is not a refusal this
          package's callers know how to name.

    `grammar.check` already had the correct sentence one layer up (`finite:
    NaN/inf in parameter vector`), so a caller that goes through the gate was
    told the truth and a caller that reaches the kernel directly was not. The
    wording here MIRRORS that clause deliberately — same prefix, same words,
    plus the gene and its value — so the two layers cannot drift into two
    different names for one condition.

    IT IS ON THE HOT PATH, so the check is the PYTHON one and not the numpy
    one. MEASURED on this box, best of 5 x 300k calls on the reference genome
    (16 float64s), predicate only:

        np.isfinite(x).all()              7.80 us
        math.isfinite(float(x.sum()))     5.26 us
        all(map(math.isfinite, tolist))   0.41 us   <- SHIPPED

    numpy's per-call dispatch dominates at n = 16; sixteen `math.isfinite`
    calls over a materialised list beat both vectorised forms by an order of
    magnitude. Whole helper including `asarray` and `ravel`: 2.19 us, i.e.
    0.50% of `_stations` at 41 stations (0.436 ms) and 0.26% at the
    1921-station feasibility probe (0.844 ms). The slow path — locating and
    naming the offending gene — runs only when the refusal is about to be
    raised, so it is not costed.

    `.ravel()` costs 0.43 us of that 2.19 and is not decoration: without it a
    2-D input reaches `map(math.isfinite, [[...], ...])` and dies as a
    `TypeError` about a list, which is this function's own failure mode
    committed inside the fix for it.
    """
    x = np.asarray(params, dtype=float)
    if not all(map(math.isfinite, x.ravel().tolist())):
        flat = x.ravel()
        i = int(np.argmax(~np.isfinite(flat)))
        name = grammar.NAMES[i] if i < len(grammar.NAMES) else f"param[{i}]"
        raise GeometryError(
            f"finite: NaN/inf in parameter vector — {name} is "
            f"{float(flat[i])}")
    return x


def _shape(s: np.ndarray, p: float) -> np.ndarray:
    """The two-sided fullness shape h(s) on [0, 1]: h(0) = 0, h(1) = 1."""
    if p >= 1.0:
        return s ** p
    return 1.0 - (1.0 - s) ** (2.0 - p)


def _shape_moments(p: float) -> tuple[float, float]:
    """(int_0^1 h ds, int_0^1 s h ds) in closed form, both branches."""
    if p >= 1.0:
        return 1.0 / (p + 1.0), 1.0 / (p + 2.0)
    q = 2.0 - p
    return q / (q + 1.0), 0.5 - 1.0 / ((q + 1.0) * (q + 2.0))


def _pmb_span(L: float, xm: float, pmb: float) -> tuple[float, float]:
    """(x0, x1) of the parallel-midbody flat span, clipped to leave a real
    entrance and a real run. THE ONE HOME of the clip — `sac_ordinate` and
    `_sac_terms` must agree on the span or the solve inverts a different
    curve than the kernel draws, which is exactly the defect this helper
    closes (audit 2026-08-26, finding D.4)."""
    half = 0.5 * float(pmb) * L
    half = min(half, 0.98 * xm, 0.98 * (L - xm))
    return xm - half, xm + half


def _sac_terms(L: float, xm: float, R: float, pf: float, pa: float,
               S_stem: float = 0.0, pmb: float = 0.0):
    """Closed-form 0th and 1st moments of the ACTUAL a(x) family.

    a(x) = R + (1-R) h(x/x0; pa)                     for x <= x0
    a(x) = 1                                         for x0 < x < x1
    a(x) = 1 - (1-S_stem) h((x-x1)/(L-x1); pf)       for x >= x1

    with (x0, x1) = `_pmb_span(L, xm, pmb)`. At S_stem = 0 and pmb = 0 this
    reduces EXACTLY to the two-branch expression that stood here before —
    x0 == x1 == xm, zero-width flat span — so all-defaults hulls are
    bit-identical.

    INCIDENT (MEASURED 2026-08-26, audit finding D.4). Until this change the
    moments here modelled the OLD two-branch curve while `sac_ordinate` drew
    the three-piece one, so the solve inverted the wrong family: pmb = 0.3
    alone inflated delivered Cp from the 0.600 the gene asked to 0.720, and
    r_stem = 0.2 alone pushed delivered LCB +2.14 %LWL — 71% of the ±3 %LWL
    gate band — so the `lcb` row PUNISHED the anti-spearhead gene and the
    search had a gradient back toward the pointed bow it exists to prevent.

    S = int a dx and M = int x a dx, both exact. Cp = S / L and the
    longitudinal centre of buoyancy is M / S, so the two design targets are
    two equations in (pf, pa) — which is the whole point of writing them in
    closed form: the solve below is cheap enough to sit inside `grammar.check`.
    """
    x0, x1 = _pmb_span(L, xm, pmb)
    lf = L - x1
    ks = 1.0 - float(S_stem)
    h1a, h2a = _shape_moments(pa)
    h1f, h2f = _shape_moments(pf)
    S = (x0 * (R + (1.0 - R) * h1a)
         + (x1 - x0)
         + lf * (1.0 - ks * h1f))
    M = (x0 * x0 * (0.5 * R + (1.0 - R) * h2a)
         + 0.5 * (x1 * x1 - x0 * x0)
         + lf * (x1 * (1.0 - ks * h1f) + lf * (0.5 - ks * h2f)))
    return S, M


@lru_cache(maxsize=8192)
def sac_exponents(lwl: float, x_mb: float, r_transom: float,
                  cp: float, lcb_pct: float,
                  r_stem: float = 0.0, pmb: float = 0.0) -> tuple[float, float]:
    """Solve the SAC shape exponents (pf, pa) for a target (Cp, LCB).

    Returns (pf, pa). Raises `GeometryError` when the target lies outside what
    the family can reach with both exponents in [SAC_P_MIN, SAC_P_MAX].

    THE SOLVE IS TWO NESTED BISECTIONS, NOT A NEWTON STEP, and the reason is
    monotonicity rather than taste. S = int a dx is strictly increasing in pf
    (a fuller forebody) and strictly decreasing in pa (a finer run), so the
    inner solve for pf at fixed pa is a bracketed monotone root. With S pinned
    at Cp*L, raising pa removes aft area and forces pf up to replace it, so the
    LCB of the constrained family is monotone increasing in pa and the outer
    solve is bracketed too. Bisection cannot leave the bounds, cannot diverge,
    and needs no fallback — and a Newton iteration that walked outside
    [1, 8] would have to be clamped, which is where a solver quietly starts
    returning the nearest reachable target instead of the one asked for.

    COST, measured on the reference hull: 78 us, memoised per (design curve)
    tuple. `grammar.check` goes 88.8 us -> 186 us against its 1 ms bar.

    THE FINITENESS CLAUSE IS FIRST, and it is the same clause `_require_finite`
    states for the whole genome, restated over the five scalars this entry
    point receives (it is reachable without a parameter vector). Without it,
    LWL = NaN reaches the bracket tests below, every comparison against NaN is
    False, and the function refuses with `sac: no exponent pair reaches Cp
    0.6000` — a sentence about a Cp that is not the problem. See G7 in
    `_require_finite`.
    """
    for _nm, _v in (("LWL", lwl), ("x_mb", x_mb), ("r_transom", r_transom),
                    ("Cp", cp), ("lcb", lcb_pct),
                    ("r_stem", r_stem), ("pmb", pmb)):
        if not math.isfinite(float(_v)):
            raise GeometryError(
                f"finite: NaN/inf in parameter vector — {_nm} is {float(_v)}")
    L = float(lwl)
    xm = float(x_mb) * L
    R = float(r_transom)
    S_t = float(cp) * L
    x_t = L * (0.5 + float(lcb_pct) / 100.0)
    Sm = float(r_stem)
    pm = float(pmb)

    def S_of(pf: float, pa: float) -> float:
        return _sac_terms(L, xm, R, pf, pa, Sm, pm)[0]

    def pf_for(pa: float) -> float | None:
        lo, hi = SAC_P_MIN, SAC_P_MAX
        s_lo, s_hi = S_of(lo, pa), S_of(hi, pa)
        if not (s_lo <= S_t <= s_hi):
            # A target a float-width outside the bracket is AT the
            # endpoint, not out of band — measured 2026-08-26 at Cp 0.878
            # on the reference demihull: the outer bisection converged to
            # a pa whose inner bracket missed S_t by ~1e-12 and the solve
            # reported "lost its bracket" for a deliverable target.
            tol = 1e-9 * max(1.0, abs(S_t))
            if S_t < s_lo - tol or S_t > s_hi + tol:
                return None
            return lo if S_t <= s_lo else hi
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            if S_of(mid, pa) < S_t:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    # The pa values for which an admissible pf exists form an interval: S is
    # decreasing in pa, so S(P_MAX, pa) >= S_t bounds pa above and
    # S(P_MIN, pa) <= S_t bounds it below. Find both edges by bisection.
    def _edge(feasible_at_low: bool, test) -> float:
        lo, hi = SAC_P_MIN, SAC_P_MAX
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            if test(mid) == feasible_at_low:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    ok_lo = S_of(SAC_P_MIN, SAC_P_MIN) <= S_t
    ok_hi = S_of(SAC_P_MAX, SAC_P_MIN) >= S_t
    if S_of(SAC_P_MIN, SAC_P_MAX) > S_t or S_of(SAC_P_MAX, SAC_P_MIN) < S_t:
        _extra = (f", r_stem {r_stem:.3f}, pmb {pmb:.3f}"
                  if (r_stem or pmb) else "")
        raise GeometryError(
            f"sac: Cp {cp:.4f} unreachable at x_mb {x_mb:.3f}, "
            f"r_transom {r_transom:.3f}{_extra} with exponents in "
            f"[{SAC_P_MIN}, {SAC_P_MAX}]")
    pa_lo = SAC_P_MIN if ok_lo else _edge(False, lambda p: S_of(SAC_P_MIN, p) <= S_t)
    pa_hi = SAC_P_MAX if ok_hi else _edge(True, lambda p: S_of(SAC_P_MAX, p) >= S_t)
    if pa_hi < pa_lo:
        raise GeometryError(f"sac: no exponent pair reaches Cp {cp:.4f}")

    def lcb_res(pa: float) -> float:
        pf = pf_for(pa)
        if pf is None:                       # numerical edge of the interval
            pf = SAC_P_MIN if pa < 0.5 * (pa_lo + pa_hi) else SAC_P_MAX
        S, M = _sac_terms(L, xm, R, pf, pa, Sm, pm)
        return M - x_t * S

    r_lo, r_hi = lcb_res(pa_lo), lcb_res(pa_hi)
    if r_lo > 0.0 or r_hi < 0.0:
        raise GeometryError(
            f"sac: LCB {lcb_pct:+.3f} %LWL unreachable at Cp {cp:.4f}, "
            f"x_mb {x_mb:.3f} (bracket {100.0 * (r_lo / max(S_t, 1e-12)) / L:+.3f} "
            f".. {100.0 * (r_hi / max(S_t, 1e-12)) / L:+.3f} %LWL)")
    lo, hi = pa_lo, pa_hi
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if lcb_res(mid) < 0.0:
            lo = mid
        else:
            hi = mid
    pa = 0.5 * (lo + hi)
    pf = pf_for(pa)
    if pf is None:
        raise GeometryError("sac: inner solve lost its bracket")
    return float(pf), float(pa)


def cp_band(lwl: float, x_mb: float, r_transom: float,
            r_stem: float = 0.0, pmb: float = 0.0) -> tuple[float, float]:
    """The (min, max) prismatic coefficient the SAC family can DELIVER for
    these fullness genes, closed form — `_sac_terms` at the exponent corners.

    Exists because the corrected solve (audit 2026-08-26, D.4) refuses a
    (Cp, pmb, r_stem) request the family cannot reach, which is honest but
    makes a UNIFORM draw over the gene box waste most of its draws on
    contradictions: pmb 0.45 alone puts a floor near Cp 0.60. A sampler (or
    a test) that wants a consistent target draws the fullness genes first
    and then draws Cp INSIDE this band.
    """
    L = float(lwl)
    xm = float(x_mb) * L
    lo = _sac_terms(L, xm, float(r_transom), SAC_P_MIN, SAC_P_MAX,
                    float(r_stem), float(pmb))[0] / L
    hi = _sac_terms(L, xm, float(r_transom), SAC_P_MAX, SAC_P_MIN,
                    float(r_stem), float(pmb))[0] / L
    return lo, hi


def lcb_band(lwl: float, x_mb: float, r_transom: float, cp: float,
             r_stem: float = 0.0, pmb: float = 0.0) -> tuple[float, float]:
    """The (min, max) LCB in %LWL the family can DELIVER at this Cp.

    The companion of `cp_band`, for the same reason: with the corrected
    solve, big fullness genes shrink the reachable LCB interval (measured
    2026-08-26: x_mb 0.48, pmb 0.45, r_transom 0.40 at Cp 0.69 delivers
    only [-8.2, -2.4] %LWL), and a sampler that draws lcb blind wastes its
    draws on sac.target refusals. Raises GeometryError when Cp itself is
    out of band. Cost: two bracketed bisections, same as one
    `sac_exponents` call, memoised the same way.
    """
    L = float(lwl)
    xm = float(x_mb) * L
    R = float(r_transom)
    S_t = float(cp) * L
    Sm, pm = float(r_stem), float(pmb)

    def S_of(pf: float, pa: float) -> float:
        return _sac_terms(L, xm, R, pf, pa, Sm, pm)[0]

    if S_of(SAC_P_MIN, SAC_P_MAX) > S_t or S_of(SAC_P_MAX, SAC_P_MIN) < S_t:
        raise GeometryError(
            f"sac: Cp {cp:.4f} outside cp_band for these fullness genes")

    def pf_for(pa: float) -> float | None:
        lo, hi = SAC_P_MIN, SAC_P_MAX
        s_lo, s_hi = S_of(lo, pa), S_of(hi, pa)
        if not (s_lo <= S_t <= s_hi):
            # A target a float-width outside the bracket is AT the
            # endpoint, not out of band — measured 2026-08-26 at Cp 0.878
            # on the reference demihull: the outer bisection converged to
            # a pa whose inner bracket missed S_t by ~1e-12 and the solve
            # reported "lost its bracket" for a deliverable target.
            tol = 1e-9 * max(1.0, abs(S_t))
            if S_t < s_lo - tol or S_t > s_hi + tol:
                return None
            return lo if S_t <= s_lo else hi
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            if S_of(mid, pa) < S_t:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    def _edge(feasible_at_low: bool, test) -> float:
        lo, hi = SAC_P_MIN, SAC_P_MAX
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            if test(mid) == feasible_at_low:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    ok_lo = S_of(SAC_P_MIN, SAC_P_MIN) <= S_t
    ok_hi = S_of(SAC_P_MAX, SAC_P_MIN) >= S_t
    pa_lo = SAC_P_MIN if ok_lo else _edge(
        False, lambda p: S_of(SAC_P_MIN, p) <= S_t)
    pa_hi = SAC_P_MAX if ok_hi else _edge(
        True, lambda p: S_of(SAC_P_MAX, p) >= S_t)

    def lcb_at(pa: float) -> float:
        pf = pf_for(pa)
        if pf is None:
            pf = SAC_P_MIN if pa < 0.5 * (pa_lo + pa_hi) else SAC_P_MAX
        S, M = _sac_terms(L, xm, R, pf, pa, Sm, pm)
        return 100.0 * (M / max(S, 1e-12) - 0.5 * L) / L

    lo_v, hi_v = lcb_at(pa_lo), lcb_at(pa_hi)
    return (min(lo_v, hi_v), max(lo_v, hi_v))


def sac_ordinate(params: np.ndarray, x: np.ndarray) -> np.ndarray:
    """a(x) in [0, 1]: sectional area / maximum sectional area."""
    p = grammar.named(params)
    L, xm = p["LWL"], p["x_mb"] * p["LWL"]
    R = p["r_transom"]
    pf, pa = sac_exponents(p["LWL"], p["x_mb"], p["r_transom"],
                           p["Cp"], p["lcb"],
                           float(p.get("r_stem", 0.0)),
                           float(p.get("pmb", 0.0)))
    x = np.asarray(x, dtype=float)
    a = np.empty_like(x)
    # `r_stem` is the exact mirror of `r_transom`: a FLOOR on sectional area at
    # the forward end. Before it existed this line was `1.0 - _shape(...)`,
    # which is exactly 0.0 at x = LWL -- so every hull narrowed to a point at
    # the stem and the delivered houseboat read as a spearhead. At S = 0.0
    # `S + (1-S)*v` is bit-identical to `v`, which is what makes appending it
    # lawful under grammar.POST_HOC_DEFAULTS.
    S = float(p.get("r_stem", 0.0))
    # PARALLEL MIDBODY. Before `pmb` existed the two branches met at the single
    # station `xm`, so a(x) reached 1.0 exactly once and no hull could carry
    # its section -- see the gene's note in grammar.py. `pmb` opens a flat span
    # of full area centred on `xm`; each branch then falls away from the END of
    # that span rather than from its centre. At pmb = 0 the span has zero width
    # and x0 == x1 == xm, which restores the previous expression exactly.
    # The span comes from `_pmb_span` — the ONE home of the clip, shared with
    # `_sac_terms` so the solve inverts the same curve this function draws.
    return _ordinate(L, xm, R, S, float(p.get("pmb", 0.0)), pf, pa, x)


def _ordinate(L: float, xm: float, R: float, S: float, pmb: float,
              pf: float, pa: float, x: np.ndarray) -> np.ndarray:
    """The ONE ordinate family both design curves are drawn from.

    Extracted (Phase 3, 2026-08-27) so the SAC and the design waterline
    B(x) share one law instead of two transcribed copies — the same
    number-declared-twice fence, applied to a FUNCTION. `sac_exponents`
    inverts exactly this family, so any curve drawn here is solvable by it.
    """
    x = np.asarray(x, dtype=float)
    x0, x1 = _pmb_span(L, xm, pmb)
    a = np.ones_like(x)
    fwd = x >= x1
    a[fwd] = S + (1.0 - S) * (1.0 - _shape((x[fwd] - x1) / (L - x1), pf))
    aft = x <= x0
    a[aft] = R + (1.0 - R) * _shape(x[aft] / x0, pa)
    return np.clip(a, 0.0, 1.0)


def waterline_ordinate(params: np.ndarray, x: np.ndarray) -> np.ndarray:
    """b(x) in [0, 1]: designed waterline half-breadth / (BWL/2).

    THE SECOND OF THE THREE COUPLED CURVES (Phase 3). Reuses the SAC's
    exponent family with its own end ratios (`rb_transom`, `rb_stem`) and a
    waterplane fullness tied to the SAC's by a DELTA: cwp = Cp + cwp_x,
    clipped into the band the family can deliver at these ratios, with the
    waterline centroid tied to `lcb` the same way. Both clips are toward
    the band interior — this function is called with AUTO-DERIVED targets,
    so a band edge here is a fairing decision, not a user request to
    refuse; `sac_exponents` still refuses a genuinely unreachable pair by
    name. Only consulted when `dwl` > 0.
    """
    p = grammar.named(params)
    L, xmf = p["LWL"], p["x_mb"]
    Rb = float(p.get("rb_transom", 0.0))
    Sb = float(p.get("rb_stem", 0.0))
    pm = float(p.get("pmb", 0.0))
    lo, hi = cp_band(L, xmf, Rb, Sb, pm)
    # THE TARGET WALKS INWARD RATHER THAN REFUSING THE HULL. The closed-form
    # bands overpromise near their high edge (the solver's own bracket can
    # fail 10% inside — measured on the cruiser parent, recorded in
    # parents.refair), and (cwp, lcf) here are AUTO-DERIVED, not user
    # requests: a target curve whose exponents will not solve is a fairing
    # decision, so it eases toward band middle until the solve succeeds.
    # MEASURED before this walk: uniform full-box draws collapsed from
    # ~60% buildable to 6% — "sac: inner solve lost its bracket" from THIS
    # call, refusing whole hulls over a curve that only needed easing.
    # Mid-band solves for every case measured; if even it fails, the raise
    # stands and names the genes.
    cwp0 = p["Cp"] + float(p.get("cwp_x", 0.0))
    lcb0 = p["lcb"]
    mid_cp = 0.5 * (lo + hi)
    last_exc = None
    for frac in (0.0, 0.05, 0.1, 0.2, 0.35, 0.5, 0.75, 1.0):
        eps = 1e-2 * max(hi - lo, 1e-6)
        cwp = float(np.clip(cwp0 + frac * (mid_cp - cwp0),
                            lo + eps, hi - eps))
        try:
            l_lo, l_hi = lcb_band(L, xmf, Rb, cwp, Sb, pm)
        except (GeometryError, ValueError) as exc:
            last_exc = exc
            continue
        eps = 1e-2 * max(l_hi - l_lo, 1e-6)
        mid_l = 0.5 * (l_lo + l_hi)
        lcf = float(np.clip(lcb0 + frac * (mid_l - lcb0),
                            l_lo + eps, l_hi - eps))
        try:
            pf, pa = sac_exponents(L, xmf, Rb, cwp, lcf, Sb, pm)
        except (GeometryError, ValueError) as exc:
            last_exc = exc
            continue
        return _ordinate(L, xmf * L, Rb, Sb, pm, pf, pa, x)
    raise GeometryError(
        f"dwl: no design-waterline curve solves at rb_transom {Rb:.3f}, "
        f"rb_stem {Sb:.3f}, pmb {pm:.3f} (last: {last_exc})")


# --------------------------------------------------------------------------
# The station solve: design curves -> the three moulded edge curves.
# --------------------------------------------------------------------------


def _keel(p: dict, x: np.ndarray) -> np.ndarray:
    """Keel z: flat middle, quadratic forefoot rise (bow) and rocker (stern)."""
    L, T = p["LWL"], p["T"]
    zk = np.full_like(x, -T)
    bow = x > 0.7 * L
    # `forefoot` RAISES the keel toward the stem; `stem_depth` LOWERS it. The
    # second is the Damen Axe Bow mechanism — greatest draught at the front, so
    # the bow does not lift and therefore cannot slam back. They are opposite
    # intents kept as separate genes: a single signed parameter conflated them,
    # and widening one gene's bound silently re-drew every seeded population.
    _rise = float(p["forefoot"]) - float(p.get("stem_depth", 0.0))
    zk[bow] += T * _rise * ((x[bow] - 0.7 * L) / (0.3 * L)) ** 2
    st = x < 0.3 * L
    zk[st] += T * p["rocker"] * ((0.3 * L - x[st]) / (0.3 * L)) ** 2
    return zk


def _deadrise(p: dict, x: np.ndarray) -> np.ndarray:
    """Bottom-panel deadrise [rad]: warped toward the bow, and toward the STERN.

    THE AFT WARP EXISTS BECAUSE THE RUN HAS TO FLATTEN, and until 2026-08-24
    this kernel could not express that. `beta_mid` applied from the transom all
    the way forward to where the bow warp began, so TRANSOM DEADRISE WAS ALWAYS
    EXACTLY `beta_mid` — measured 25.0 deg at the transom and 25.2 deg at
    midships on the same hull, i.e. no run at all.

    Published practice prescribes deadrise at THREE stations and it DECREASES
    aft (De Luca & Pensa, "The Naples warped hard chine hulls systematic
    series", Ocean Engineering 139 (2017), Table 1):

        beta_transom 13.2  <  beta_50% 22.3  <  beta_75% 38.5

    A single forward quadratic cannot pass through three prescribed points, so
    this is a missing LAW, not a missing bound. It also matters mechanically:
    a single inboard shaft needs a flat run for clean inflow to the propeller
    and a shallow shaft angle, and 25 deg of vee at the transom gives neither.

    `beta_run` = 0 disables the aft warp and reproduces every hull drawn before
    this existed, bit for bit.
    """
    L = p["LWL"]
    beta = np.full_like(x, math.radians(p["beta_mid"]))
    warp0 = L - p["beta_len"] * L
    wz = x > warp0
    frac = (x[wz] - warp0) / (p["beta_len"] * L)
    beta[wz] += (math.radians(p["beta_bow"])
                 - math.radians(p["beta_mid"])) * frac ** 2
    run = float(p.get("beta_run", 0.0))
    if run > 0.0:
        aft = x < run * L
        f = (run * L - x[aft]) / (run * L)
        beta[aft] += (math.radians(float(p.get("beta_transom", p["beta_mid"])))
                      - math.radians(p["beta_mid"])) * f ** 2
    return beta


def _fillet_coeffs(rho: float) -> tuple[float, float]:
    """(c1, c2) of the section-area quadratic, from the bilge roundness.

    The fillet is the quadratic Bezier with control points C + rho*(K - C),
    C, C + rho*(W - C), where K is the keel point, C the chine and W the
    section's design-waterline point. Archimedes: the area between a parabolic
    arc and its chord is 2/3 of the triangle on that chord and the tangent
    intersection, so cutting the corner removes exactly 1/3 of the control
    triangle, whose area is rho**2 times the (K, C, W) triangle. That is where
    the rho**2 / 3 comes from and it is why the round-bilge section's area is
    CLOSED FORM rather than quadrature — the acceptance bar (1e-6) is met by
    construction and the sampled polygon is what has to converge to it.
    """
    return 2.0 - rho * rho / 3.0, 1.0 - rho * rho / 3.0


def _stations(params: np.ndarray, x: np.ndarray) -> dict:
    """Every moulded curve at `x`, solved from the design curves.

    THE ONE PLACE THE SECTION IS SOLVED. Given the keel depth d, the deadrise
    beta, the topside flare phi and the target sectional area A, the chine
    half-breadth is the root of a quadratic:

        A = K*yc*(c1*d - c2*m*yc) + d**2 * f
        m = tan(beta), f = tan(phi), K = 1 - m*f, (c1, c2) from the roundness

    written in the numerically stable form below so that beta -> 0 (a flat
    bottom, which `beta_mid` is allowed to be) degrades to the linear root
    instead of 0/0. The discriminant going negative is the statement that the
    requested area exceeds what a section of that draft and deadrise can
    enclose (A <= d**2 / tan(beta) at roundness 0, i.e. the chine reaching the
    waterline); that is a REFUSAL, not a clamp.

    The one clamp here is yc >= 0, and it is a geometric floor rather than a
    fudge: a flared topside encloses d**2*tan(phi) of area even with the chine
    on the centreline, so a station whose target area is below that floor
    cannot be met. It bites only where a(x) -> 0, i.e. inside the last station
    interval at the stem. MEASURED on the reference hull: the floor raises the
    displacement by 0.0087% and moves Cp by 6e-5, against a +-0.01 bar.

    THE FINITENESS CHECK IS THE FIRST STATEMENT because this is the funnel:
    `Hull.__post_init__`, `station_geometry`, `design_waterline`,
    `sectional_area`, `form_coefficients`, `fairness` and `section_probe` all
    arrive here, so one check names a poisoned gene for all of them. See
    `_require_finite` for the 32-probe measurement of what the kernel said
    before it existed.
    """
    p = grammar.named(_require_finite(params))
    L, B, T, D = p["LWL"], p["BWL"], p["T"], p["D"]
    x = np.asarray(x, dtype=float)
    c1, c2 = _fillet_coeffs(p["roundness"])

    zk = _keel(p, x)
    d = -zk
    beta = _deadrise(p, x)
    m = np.tan(beta)

    # THE FLARE CLOSES INTO THE STEM, and it has to, or the design waterline
    # does not close. A topside leaning out at a constant angle encloses
    # d**2 * tan(flare) of section area even with the chine on the centreline,
    # so a station whose target area is zero cannot be met. MEASURED on hull 27
    # of `grammar.sample(30, rng(0))` before this envelope: 0.4260 m of
    # waterline half-breadth AT THE STEM (0.85 m of blunt bow) and 0.3938 m^2
    # of sectional area against a target of ZERO — the largest single error in
    # the delivered area curve, at the one station whose target is exact. The
    # old kernel carried the same 0.426 m; it simply had no area curve to be
    # wrong against, and closed the DECK with a `w**0.15` envelope while
    # leaving the waterline open.
    #
    # The envelope is one-sided: full flare over the run and the midbody,
    # closing forward of the max-area station. Tapering it aft as well would
    # quietly reduce the transom flare by a sixth for no reason anyone asked
    # for. It is also what now closes the DECK at the stem, so `y_sheer` no
    # longer carries a second envelope of its own — that was the same taper
    # declared twice.
    a = sac_ordinate(params, x)
    xm_val = p["x_mb"] * L
    # FLARE THAT VARIES ALONG THE LENGTH. `formlib` records this as the single
    # blocker that made `axe_bow` and `wave_piercing_monohull` Expressible.NO:
    # "flare that varies along the length: `flare` is one scalar applied at
    # every station".
    #
    # Baltic Workboats state the mechanism plainly: "when the bow becomes
    # submerged, the top surface of the bow creates increased downforce, which
    # compensates for the buoyancy of the bow". Flare does the opposite — it
    # generates lift and reserve buoyancy — so a wave-piercer wants little or
    # none of it forward while keeping it amidships for dryness.
    #
    # `flare_len` = 0 disables the warp and is bit-identical to every hull
    # drawn before this existed.
    flare_deg = np.full_like(x, float(p["flare"]))
    fl_len = float(p.get("flare_len", 0.0))
    if fl_len > 0.0:
        w0 = L - fl_len * L
        wz = x > w0
        frac = (x[wz] - w0) / (fl_len * L)
        flare_deg[wz] += (float(p.get("flare_bow", p["flare"]))
                          - float(p["flare"])) * frac ** 2
    f_law = np.tan(np.radians(flare_deg))

    # A_mid from the DESIGN WATERLINE BEAM. `BWL` is the half-breadth of the
    # section at z = 0 at the max-area station, doubled — which is what the
    # symbol has always claimed and, until this commit, was not: it used to
    # scale the CHINE plan-form and the waterline came out wherever the flare
    # put it. Computed BEFORE the flare closure cap below, which needs A.
    xm = np.array([xm_val])
    # f_mid is the flare LAW at the max-area station — not the bare `flare`
    # gene. They differ when the flare warp reaches x_mb, which the gene box
    # permits with zero margin (flare_len ceiling 0.6 == 1 - x_mb floor
    # 0.40); reading the gene here silently broke "BWL = max beam" at that
    # edge (audit 2026-08-26, _stations finding b).
    _i_mid = int(np.searchsorted(x, xm_val))
    if 0 <= _i_mid < len(flare_deg) and abs(x[_i_mid] - xm_val) < 1e-9:
        _fl_mid_deg = float(flare_deg[_i_mid])
    else:
        _fl_mid_deg = float(p["flare"])
        if fl_len > 0.0 and xm_val > L - fl_len * L:
            _fr = (xm_val - (L - fl_len * L)) / (fl_len * L)
            _fl_mid_deg += (float(p.get("flare_bow", p["flare"]))
                            - float(p["flare"])) * _fr ** 2
    f_mid = math.tan(math.radians(_fl_mid_deg))
    m_mid = float(np.tan(_deadrise(p, xm))[0])
    d_mid = float(-_keel(p, xm)[0])          # == T; x_mb is inside the flat run
    K_mid = 1.0 - m_mid * f_mid
    yc_mid = (0.5 * B - d_mid * f_mid) / K_mid
    if not (yc_mid > 0.0):
        raise GeometryError(
            f"section: flare {p['flare']:.1f} deg consumes the whole "
            f"{0.5 * B:.3f} m half-beam at the max-area station")
    A_mid = (K_mid * yc_mid * (c1 * d_mid - c2 * m_mid * yc_mid)
             + d_mid ** 2 * f_mid)
    if not (A_mid > 0.0):
        raise GeometryError("section: non-positive maximum sectional area")

    # THE FLARE ENVELOPE — kept AREA-TAPERED, by measurement, not by taste.
    # Audit finding D.3 (2026-08-26) called the `* env` a defect: it makes
    # `flare_bow` a no-op at the stem when r_stem = 0. FULL decoupling was
    # implemented the same day (f = the designed law, capped only for
    # closure) and MEASURED to collapse plan convexity from a ~0.5 median
    # to ~0.32 on the reference hull, the hull-kb cruiser and random draws
    # alike: y_wl = K*yc + d*f, so at constant f the KEEL PROFILE's
    # quadratic (forefoot/rocker) leaks into the waterline plan over the
    # whole entrance, where the old a(x) taper had been accidentally
    # FAIRING it. The real repair is an independent design-waterline curve
    # B(x) solved jointly with the SAC (the audit's research answer — the
    # three-coupled-curves practice), which makes flare a derived
    # per-station quantity; until that lands, the taper stays and
    # `flare_bow` is effective SCALED BY a(x) — real wherever r_stem > 0,
    # and moot at r_stem = 0 where the stem is a point with nothing to
    # flare. The closure cap below is new and stays: it bounds |f| by the
    # area actually available so the section quadratic keeps margin in
    # both signs (tumblehome cannot ask the sheer past the centreline).
    env = np.where(x <= xm_val, 1.0, np.maximum(a, 0.0))
    with np.errstate(divide="ignore", invalid="ignore"):
        f_cap = np.where(
            x > xm_val,
            _FLARE_CLOSURE_FRAC * (A_mid * np.maximum(a, 0.0))
            / np.maximum(d, 1e-9) ** 2,
            np.inf)
    f = np.clip(f_law * env, -f_cap, f_cap)
    K = 1.0 - m * f

    A = A_mid * a

    # Solve the section quadratic, stable branch.
    #
    # PASS-1 REFUSALS ARE CONDITIONAL ON AUTHORITY (Phase 3). At dwl = 0
    # this solve IS the section and its refusals are the kernel's word. At
    # dwl > 0 it is only the BLEND SOURCE for the designed waterline below
    # — the joint solve re-derives (chine, flare) and carries its own
    # refusals — so a station pass 1 cannot reach is clamped to the closest
    # it CAN reach (chine at the waterline, the quadratic's vertex) instead
    # of refusing a hull whose final section never uses this answer.
    # MEASURED before this guard: r_stem 0.06 at beta_bow 30 refused in
    # pass 1 ("area 0.1664 m^2 unreachable") for a dwl = 1 hull whose
    # joint solve delivers that station fine — the exact coupling B(x)
    # exists to relieve.
    _dwl = float(p.get("dwl", 0.0))
    rhs = A - d * d * f
    disc = (K * c1 * d) ** 2 - 4.0 * K * c2 * m * rhs
    if _dwl > 0.0:
        disc = np.maximum(disc, 0.0)
        rhs = np.maximum(rhs, 0.0)
    if np.any(disc < 0.0):
        i = int(np.argmin(disc))
        raise GeometryError(
            f"section: area {A[i]:.4f} m^2 unreachable at x = {x[i]:.3f} m "
            f"(draft {d[i]:.3f} m, deadrise "
            f"{math.degrees(float(beta[i])):.1f} deg)")
    if np.any(rhs < -1e-12 * max(A_mid, 1.0)):
        i = int(np.argmin(rhs))
        raise GeometryError(
            f"section: the flare encloses {d[i] ** 2 * f[i]:.4f} m^2 at "
            f"x = {x[i]:.3f} m against a target of {A[i]:.4f} m^2 — the "
            f"topside is wider than the area curve asked for")
    den = K * c1 * d + np.sqrt(disc)
    yc = np.where(den > 1e-12, 2.0 * rhs / np.maximum(den, 1e-12), 0.0)
    yc = np.maximum(yc, 0.0)
    zc = zk + yc * m
    y_wl = K * yc + d * f

    # ---- THE DESIGN WATERLINE B(x) (Phase 3, 2026-08-27) -----------------
    # With `dwl` > 0 the section receives BOTH targets — A(x) above and a
    # designed waterline half-breadth w(x) — and (chine, flare) are solved
    # JOINTLY, which is what makes the flare a DERIVED per-station quantity
    # (the audit's three-coupled-curves repair). Substituting
    # u = w - d*f = K*yc into the area closed form gives a polynomial in f
    # whose f^2 coefficient is m*d^2*(c1 - c2 - 1); the fillet identity
    # c1 - c2 = 1 (see _fillet_coeffs) makes it VANISH for every roundness,
    # so the derived flare is the root of a LINEAR equation and the kernel
    # stays closed form. `dwl` blends the target between the pass-1
    # consequence (0, bit-identical legacy) and the prescribed curve (1).
    if _dwl > 0.0:
        b_wl = waterline_ordinate(params, x)
        w = (1.0 - _dwl) * y_wl + _dwl * (0.5 * B) * b_wl
        e = d
        a0 = A - c1 * e * w + c2 * m * w * w
        a1 = -A * m + c1 * e * (e + m * w) - 2.0 * c2 * m * e * w - e * e
        # f = -a0/a1, guarded: a vanishing a1 means no flare satisfies
        # both targets at this station; send it to +inf so the cap-and-
        # refair branch below owns it. (The first draft of this guard
        # composed sign() and a negation into +a0/a1 — the SIGN of the
        # solve — and every fuller-waterline request pinned at the
        # tumblehome cap; verified against 2000 synthetic sections.)
        with np.errstate(divide="ignore", invalid="ignore"):
            f_lin = np.where(np.abs(a1) > 1e-12,
                             -a0 / np.where(np.abs(a1) > 1e-12, a1, 1.0),
                             np.inf)
        # B(x) IS A HARD TARGET ONLY WHERE A BOUNDED FLARE CAN DELIVER IT.
        # MEASURED before this clamp: every tried configuration refused at
        # the STEM with derived flare 83-90 deg — near the tips A(x) and
        # w(x) fall at rates the section's one shape DOF cannot reconcile,
        # and demanding exactness there refused the whole hull for its last
        # 2% of length. This is what lines fairing IS: the waterline is
        # authoritative over the body and eased at the ends. So the derived
        # flare is capped at +-60 deg; where the cap binds, the section
        # reverts to AREA-faithful (the pass-1 quadratic at the capped
        # flare) and the delivered waterline deviates from the designed
        # curve THERE ONLY. The deviation is not silent: it is readable as
        # y_wl vs (BWL/2) * waterline_ordinate(...), and
        # `Hull.dwl_deviation()` reports it — a requested-vs-achieved gap
        # this kernel measures rather than hides.
        # THE DERIVED FLARE SATURATES SMOOTHLY, AND THE SECTION STAYS
        # AREA-FAITHFUL EVERYWHERE. The first cut clipped f_lin hard and
        # switched the section between waterline-exact and area-faithful
        # regimes; the switch was value-continuous but kinked the plan, and
        # the critic read the kinks as waists (+17..+19 margins on slender
        # hulls — WORSE than the lens it replaced). So: (1) f2 is a tanh
        # saturation of the linear solve toward per-station caps — near
        # zero it is the exact answer to machine precision growth, at the
        # caps it eases in smoothly, and it is C1 along the hull; (2) the
        # chine is then ALWAYS solved from the AREA at that flare, so the
        # SAC — the displacement contract — is delivered exactly at every
        # dwl, and the waterline APPROXIMATES the designed B(x) as closely
        # as the caps allow. That is what fairing a lines plan means; the
        # requested-vs-achieved gap is measurable (y_wl against
        # waterline_ordinate) and Hull.dwl_deviation() reports it.
        #
        # The caps: outward flare stops 5 deg short of panels-parallel
        # (K = 0 at beta + flare = 90 deg) and at 60 deg absolutely;
        # tumblehome is capped at 25 deg scaled by the one-sided envelope
        # AND the SAC ordinate — a short topside on a small section may
        # not chase the waterline far (measured: the sheer walked through
        # the centreline at both ends before these tapers).
        f_hi = np.tan(np.minimum(math.radians(60.0),
                                 (0.5 * math.pi - beta) - math.radians(5.0)))
        f_lo = math.tan(math.radians(25.0)) * env * np.minimum(a, 1.0)
        with np.errstate(divide="ignore", invalid="ignore"):
            f2 = np.where(
                f_lin >= 0.0,
                f_hi * np.tanh(np.minimum(f_lin, 1e6)
                               / np.maximum(f_hi, 1e-9)),
                -np.maximum(f_lo, 1e-9)
                * np.tanh(-np.maximum(f_lin, -1e6)
                          / np.maximum(f_lo, 1e-9)))
        K2 = 1.0 - m * f2
        if np.any(K2 <= 1e-6):
            i = int(np.argmin(K2))
            raise GeometryError(
                f"dwl: bottom and topside panels become parallel at "
                f"x = {x[i]:.3f} m")
        rhs2 = A - d * d * f2
        disc2 = (K2 * c1 * d) ** 2 - 4.0 * K2 * c2 * m * rhs2
        if np.any(disc2 < 0.0):
            i = int(np.argmin(disc2))
            raise GeometryError(
                f"dwl: area {A[i]:.4f} m^2 unreachable at x = {x[i]:.3f} m "
                f"at the faired flare "
                f"{math.degrees(math.atan(float(f2[i]))):.1f} deg — the "
                f"SAC and the designed waterline cannot be faired there")
        den2 = K2 * c1 * d + np.sqrt(np.maximum(disc2, 0.0))
        yc = np.where(den2 > 1e-12,
                      2.0 * np.maximum(rhs2, 0.0) / np.maximum(den2, 1e-12),
                      0.0)
        yc = np.maximum(yc, 0.0)
        f, K = f2, K2
        zc = zk + yc * m
        y_wl = K * yc + d * f

    # Sheer: freeboard at mid, rising toward the bow. The topside is ONE
    # straight run from the chine at the (enveloped) flare, so the sheer
    # half-breadth is the chine plus that flare over the topside height and
    # the deck closes at the stem because both terms do.
    fb = D - T
    zs = np.full_like(x, fb)
    fwd = x >= xm_val
    zs[fwd] *= 1.0 + p["sheer_rise"] * (
        (x[fwd] - xm_val) / (L - xm_val)) ** 2 * (D / fb)
    if _dwl > 0.0:
        # THE WATERLINE IS A KNUCKLE (Phase 3, slice 2). Below W the panel
        # carries the DERIVED flare (that is what delivers B(x)); above W
        # the topside is its own panel at the designed flare LAW, tapered
        # into the stem by the same one-sided envelope the legacy topside
        # used — that envelope is what closes the DECK, and W already
        # closes the WATERLINE by construction (b -> rb_stem). This is
        # what frees the sheer from the waterline: the measured
        # single-panel failure (5.7 m of deck on a 3.2 m BWL when derived
        # flare lifted the waterline) was the two jobs sharing one slope.
        # tapered by the DESIGNED WATERLINE ORDINATE, not the SAC envelope:
        # env's derivative jumps at the flat span's end, and the sheer
        # (y_wl + zs*f_law*env) inherited the kink — measured as a 0.045
        # plan waist on the barge (bar 0.020) purely from the taper
        # switching slope. b_wl is smooth by construction and IS the plan's
        # own shape, so the topside offset scales with the local waterline
        # and the deck closes exactly as much as the designed bow does.
        ys = y_wl + zs * (f_law * np.minimum(b_wl, 1.0))
    else:
        ys = yc + (zs - zc) * f
    # A NEGATIVE SHEER HALF-BREADTH IS REFUSED, NOT CLAMPED. The old kernel
    # wrote `np.maximum(ys, 0.0)`, and `admissibility` already reported that
    # clamp as a defect ("station_geometry replaced a NEGATIVE sheer
    # half-breadth"). It is worse than cosmetic here: clamping moves the
    # topside off the line through the design waterline point, so the section
    # no longer passes through `y_wl` and the closed-form area the kernel is
    # solved against stops describing the shape. MEASURED on hull 3 station 10
    # of `grammar.sample(20, rng(0))`: the exact immersed area read 6.4230e-3
    # m^2 against the algebra's 6.2426e-3 — 2.9% out, at one station, silently.
    if np.any(ys < -1e-12):
        i = int(np.argmin(ys))
        raise GeometryError(
            f"section: tumblehome closes the sheer past the centreline at "
            f"x = {x[i]:.3f} m (half-breadth {ys[i]:+.4f} m)")
    y_sheer = np.maximum(ys, 0.0)
    return {"x": x, "z_keel": zk, "d": d, "beta": beta, "m": m, "f": f, "K": K,
            "y_chine": yc, "z_chine": zc, "y_wl": y_wl,
            "y_sheer": y_sheer, "z_sheer": zs, "a": a, "A": A, "A_mid": A_mid,
            "c1": c1, "c2": c2}


# THE SECTION SOLVE IS A CONTINUOUS CONDITION AND THE L0 GATE SAMPLES IT.
#
# MOTIVATING INCIDENT, MEASURED 2026-08-13. `grammar.check` built a 41-station
# `Hull` and passed; `resistance.total_resistance` then rebuilt THE SAME vector
# at its Michell station count and `_stations` raised
# `section: area 0.1594 m^2 unreachable at x = 15.335 m` — an x the 41-point
# grid steps straight over. `scripts/make_baseline.py`, `test_optimize` and
# `test_policy` all died on that traceback, and each of them had already been
# told by L0 that the hull was fine. A refusal that depends on the station
# count is not a statement about the boat.
#
# MEASURED over 20,000 uniform in-bounds vectors, of which 11,909 build at 41
# stations. Of those 11,909, the number that FAIL when re-solved on a denser
# grid:
#
#       241 stations   113      <- the Michell production grid
#       481 stations   116      <- the Michell converged grid
#       801 stations   116
#      1921 stations   117      <- SHIPPED
#      3841 stations   117
#      7681 stations   117
#
# 1921 is the count for two reasons and the second is the load-bearing one.
# It is dense enough that doubling and quadrupling it find nothing further
# (117, 117, 117). And 1920 = 48 x 40 = 8 x 240 = 4 x 480, so the probe grid
# CONTAINS the 41-station hydrostatic grid, the 241-station Michell production
# grid and the 481-station converged grid EXACTLY, rather than merely being
# finer than them — a probe that is 3.3x denser but misaligned can still step
# over a station its consumer lands on. (The first version of this constant was
# 801, chosen when the Michell grid was 161; 800 is not a multiple of 240 and
# it stopped containing the production grid the moment that grid moved.)
#
# It is still a dense SAMPLE of a continuous condition, not a proof, and a
# refusal found later by a still-denser consumer is a loud `GeometryError`,
# never a wrong hull.
#
# Cost, measured on the reference hull: `grammar.check` 59.3 us -> 138 us
# against `tests/test_phase0`'s 1 ms bar.
FEASIBILITY_PROBE_STATIONS = 1921


def section_probe(params: np.ndarray) -> None:
    """Raise `GeometryError` if the section solve fails ANYWHERE on the hull.

    The L0 gate's buildability question, asked once on a grid denser than any
    consumer's. Returns nothing: the answer is the exception, and an exception
    is what `grammar.check` turns into a named violation.
    """
    lwl = float(grammar.named(params)["LWL"])
    _stations(params, np.linspace(0.0, lwl, FEASIBILITY_PROBE_STATIONS))


def station_geometry(params: np.ndarray, x: np.ndarray):
    """Closed-form hull offsets at longitudinal positions `x`.

    Returns (z_keel, y_chine, z_chine, y_sheer, z_sheer), each shaped like `x`.

    This is the ONE definition of the moulded surface's three edge curves.
    `Hull.__post_init__` calls it at `np.linspace(0, LWL, n_stations)` and
    `Hull.edge_curves` calls it anywhere else; a second copy evaluated at
    non-station x would be defect class 2 (a number — here a whole curve —
    declared twice) with the two copies free to drift.
    """
    s = _stations(params, x)
    return (s["z_keel"], s["y_chine"], s["z_chine"],
            s["y_sheer"], s["z_sheer"])


def design_waterline(params: np.ndarray, x: np.ndarray) -> np.ndarray:
    """Half-breadth of the moulded surface AT z = 0, in closed form.

    The design waterline is a first-class curve of this kernel, not something
    read off a section: `y_wl = (1 - tan(beta) tan(flare)) * y_chine
    + d * tan(flare)` is where the topside run crosses z = 0, and it is
    independent of the bilge roundness because the fillet never touches the
    topside line.
    """
    return _stations(params, x)["y_wl"]


def sectional_area(params: np.ndarray, x: np.ndarray) -> np.ndarray:
    """The sectional area curve A(x) [m^2], full section, at the DWL."""
    return _stations(params, x)["A"]


# --------------------------------------------------------------------------
# The section shape function
# --------------------------------------------------------------------------


def _bezier(p0: np.ndarray, p1: np.ndarray, p2: np.ndarray,
            s: np.ndarray) -> np.ndarray:
    s = s[:, None]
    return (1.0 - s) ** 2 * p0 + 2.0 * s * (1.0 - s) * p1 + s * s * p2


def sample_section(keel: np.ndarray, chine: np.ndarray, sheer: np.ndarray,
                   wl: np.ndarray, rho: float,
                   n_lo: int, n_hi: int, knuckle: bool = False) -> np.ndarray:
    """The section shape function, sampled to n_lo + n_hi + 1 (y, z) points.

    Point `n_lo` is the BILGE FEATURE: the chine itself at rho = 0, the
    mid-point of the fillet arc otherwise. Everything that needs a row index
    for the bilge (`Hull.chine_row`, `closed_mesh`,
    `admissibility.surface_grid`) reads that one convention.

    AT rho = 0 THIS IS THE OLD THREE-POINT SECTION, BIT FOR BIT: the lower
    parameter interval [0, 1-rho] collapses to [0, 1] on the keel->chine leg
    and the upper one to the chine->sheer leg, so `sample_section(..., 0.0,
    1, 1)` is `[keel, chine, sheer]` with no arithmetic in between.
    `tests/test_geometry_kernel.py::test_roundness_zero_is_the_old_polyline`
    is the fence, at 1e-12.

    The fillet's upper control point runs toward the WATERLINE point, not the
    sheer. Both lie on the same topside line so the tangent is identical, but
    anchoring on the waterline keeps the whole arc strictly below z = 0 for
    every rho in [0, 1] — which is what makes the immersed area closed-form
    instead of a case analysis on whether the fillet crosses the surface.
    """
    K, C, S, W = (np.asarray(v, float) for v in (keel, chine, sheer, wl))
    # `knuckle`: the WL point is a VERTEX (Phase 3, slice 2) — the topside
    # is the polyline C (or arc exit) -> W -> S rather than one leg to the
    # sheer. False on every legacy section, where the branches below are
    # byte-for-byte the pre-knuckle function.
    # With a knuckle, W must be a VERTEX OF THE OUTPUT, not merely of the
    # dense polyline: a uniform arc-length resample walks straight past a
    # breakpoint (measured 0.455 m from the nearest sample to W), and a
    # mesh that misses the knuckle is a different hull. The topside is
    # therefore resampled as its two legs, W pinned as the last point of
    # the first — which needs n_hi >= 2 (`Hull.section` guarantees it on
    # knuckle hulls).
    if knuckle and n_hi < 2:
        raise ValueError("a knuckle section needs n_hi >= 2 to carry both "
                         "the waterline vertex and the sheer")
    n_a = max(1, n_hi // 2)
    n_b = n_hi - n_a
    if rho <= 0.0:
        lo = K + np.linspace(0.0, 1.0, n_lo + 1)[:, None] * (C - K)
        if knuckle:
            leg_a = C + np.linspace(0.0, 1.0, n_a + 1)[1:, None] * (W - C)
            leg_b = W + np.linspace(0.0, 1.0, n_b + 1)[1:, None] * (S - W)
            hi = np.vstack([leg_a, leg_b])
        else:
            hi = C + np.linspace(0.0, 1.0, n_hi + 1)[1:, None] * (S - C)
        return np.vstack([lo, hi])
    P0 = C + rho * (K - C)
    P2 = C + rho * (W - C)
    m = max(128, 2 * max(n_lo, n_hi))
    s = np.linspace(0.0, 1.0, 2 * m + 1)
    arc = _bezier(P0, C, P2, s)
    lo = np.vstack([K[None, :], arc[:m + 1]])
    if knuckle:
        leg_a = _resample(np.vstack([arc[m:], W[None, :]]), n_a + 1)[1:]
        leg_a[-1] = W                       # the resample must END on W exactly
        leg_b = W + np.linspace(0.0, 1.0, n_b + 1)[1:, None] * (S - W)
        return np.vstack([_resample(lo, n_lo + 1), leg_a, leg_b])
    hi = np.vstack([arc[m:], S[None, :]])
    return np.vstack([_resample(lo, n_lo + 1), _resample(hi, n_hi + 1)[1:]])


def _resample_batch(polys: np.ndarray, n: int) -> np.ndarray:
    """`_resample` over a (k, m, 2) stack of dense polylines, one per station.

    THE ARITHMETIC IS `_resample`'s, OPERATION FOR OPERATION, so the result
    is bit-identical to calling `_resample` per row — fenced at 1e-12 in
    tests/test_admissibility.py::test_the_batch_section_sampler_is_the_loop,
    including at the screen's real 600x120 resolution:

      * diff, the 2-term norm (written out — see the note at the top of the
        body) and cumsum run along the point axis of the stack, the same
        values in the same order per row;
      * the query grid reproduces `np.linspace(0.0, L, n)` as numpy computes
        it — `arange(n) * (L / (n-1))`, then the endpoint pinned to L — one
        (k, n) array instead of k Python calls;
      * the interpolation is `np.interp`'s own C formula, batched:
        j = rightmost index with cum[j] <= t, slope = (f1-f0)/(x1-x0),
        ans = slope*(t-x0) + f0, with numpy's exact-hit branch
        (cum[j] == t -> f[j]) and right-endpoint branch (t at the last
        breakpoint -> f[-1]) applied in numpy's order. Only the per-row
        `searchsorted` stays a loop (its breakpoints differ per station).

    MEASURED 2026-08-20, and why the reproduction goes this deep: the
    per-station call overhead in `admissibility.surface_grid` (a fresh
    linspace, a `_bezier` and two `_resample` calls per station, ~600
    stations/hull) plus ~2400 `np.interp` wrapper calls per hull held that
    grid at ~113 ms/hull and the screen at ~140 ms/hull against its 100 ms
    bar (~265 ms/hull with the box under loadavg ~4). Batching took the
    loop's ~1200 linspace + 2400 interp calls to ~1200 bare searchsorted
    calls and the grid to ~28 ms/hull, values unchanged.
    """
    k, mm, _ = polys.shape
    # `np.linalg.norm(np.diff(polys, axis=1), axis=2)`, written out. That call
    # is `sqrt(add.reduce(x*x, axis=2))` and numpy sums fewer than eight
    # addends left to right from 0.0, so `sqrt(dy*dy + dz*dz)` is the same
    # float. MEASURED 2026-08-20 on the 241-station resistance hull, 2.48 ms
    # -> 1.14 ms: reducing over a LAST axis of length 2 makes numpy's inner
    # loop two elements long and runs it 62k times, where the explicit form
    # walks two contiguous (k, mm-1) arrays.
    dy = polys[:, 1:, 0] - polys[:, :-1, 0]
    dz = polys[:, 1:, 1] - polys[:, :-1, 1]
    d = np.sqrt(dy * dy + dz * dz)
    cum = np.concatenate([np.zeros((k, 1)), np.cumsum(d, axis=1)], axis=1)
    L = cum[:, -1]
    T = np.arange(n) * (L / (n - 1))[:, None]
    T[:, -1] = L
    j = np.empty((k, n), dtype=np.intp)
    for r in range(k):
        j[r] = np.searchsorted(cum[r], T[r], side="right")
    j -= 1
    at_end = j >= mm - 1
    jc = np.minimum(j, mm - 2)
    jc1 = jc + 1
    # `A[rows, idx]` IS what `take_along_axis` does — it builds exactly this
    # index pair and calls the same gather, so the values are identical and
    # only the wrapper goes. MEASURED 2026-08-20: 144 `take_along_axis` calls
    # per 6 `evaluate()` calls cost 0.043 s tottime plus 0.012 s in
    # `_make_along_axis_idx`, on gathers of (241, 129).
    rows = np.arange(k, dtype=np.intp)[:, None]
    x0 = cum[rows, jc]
    dx = cum[rows, jc1] - x0
    # a zero-width interval is only ever selected where a mask below already
    # decides the value (exact hit or endpoint); the guard silences 0/0 there
    dx = np.where(dx != 0.0, dx, 1.0)
    out = np.empty((k, n, 2))
    for c in (0, 1):
        # contiguous first: `polys[:, :, c]` is a strided view and the gather
        # below then walks it with a stride of two doubles per element.
        pc = np.ascontiguousarray(polys[:, :, c])
        f0 = pc[rows, jc]
        f1 = pc[rows, jc1]
        ans = (f1 - f0) / dx * (T - x0) + f0
        ans = np.where(x0 == T, f0, ans)
        out[:, :, c] = np.where(at_end, pc[:, -1][:, None], ans)
    deg = L <= 1e-15
    if deg.any():
        out[deg] = polys[deg, :1]
    return out


def _resample(poly: np.ndarray, n: int) -> np.ndarray:
    """`n` points spaced uniformly in ARC LENGTH along a dense polyline.

    THE SPACING HAS TO BE UNIFORM, and the first version of `sample_section`
    split the parameter interval by the roundness instead — which put a STEP
    in the segment length at the joint between the straight leg and the fillet
    arc. MEASURED: `Hull.fairness` then DIVERGED on a round bilge exactly as
    it does on a knuckle (2.7e3 -> 2.6e6 over nz 32 -> 1024 at roundness 1),
    because a jump of dh in spacing puts an O(dh) term into the second
    difference where a fair curve has O(h**2), and the estimator divides by
    h**3. The fairness of the SURFACE was fine; the sampling of it was not,
    and an artefact of the sampler read as a property of the hull.

    At roundness 0 this function is not called: the two legs are straight, and
    uniform arc length along a straight leg IS the old linear interpolation.
    """
    d = np.linalg.norm(np.diff(poly, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(d)])
    if cum[-1] <= 1e-15:
        return np.repeat(poly[:1], n, axis=0)
    t = np.linspace(0.0, cum[-1], n)
    return np.stack([np.interp(t, cum, poly[:, 0]),
                     np.interp(t, cum, poly[:, 1])], axis=1)


def _sections_batch(K: np.ndarray, C: np.ndarray, S: np.ndarray,
                    W: np.ndarray, rho: float, n_lo: int,
                    n_hi: int, knuckle: bool = False) -> np.ndarray:
    """`sample_section` over a STACK of control points: (k, n_lo+n_hi+1, 2).

    `sample_section` STAYS THE DEFINITION. This is that function with the
    station axis broadcast in — the same linspaces, the same Bezier
    coefficients off the same shared `s` grid, the same arc-length resample
    (`_resample_batch`, itself already fenced against `_resample`), in the
    same order — so every element is bit-identical, elementwise, to the
    per-station call it replaces. Fenced at exactly 0.0 in
    tests/test_geometry_kernel.py::
    test_the_batched_section_machinery_is_the_per_station_definition, for
    roundness 0 and roundness > 0, at 41 and 241 stations.

    It was already written INLINE inside `Hull._sections_at_rows_batch` for
    `admissibility.surface_grid`'s arbitrary-x consumers; lifting it out is
    what lets the STATION-indexed memo (`Hull._prime_sections`) share it
    rather than become a third copy of a shape function — defect class 2.

    MEASURED 2026-08-20 (cProfile, `evaluate()` on the 12-hull slider
    fixture): the per-station path spent 0.899 s of a 2.72 s profile (33%) in
    1692 `sample_section` calls, of which 0.549 s was 3384 `_resample` calls
    and 0.133 s was 1692 `_bezier` calls. The 241-station resistance hull
    accounts for 241 of the 282 sections an evaluation builds, and every one
    of them shares (rho, n_lo, n_hi) with all the others.
    """
    if knuckle and n_hi < 2:
        raise ValueError("a knuckle section needs n_hi >= 2 to carry both "
                         "the waterline vertex and the sheer")
    n_a = max(1, n_hi // 2)
    n_b = n_hi - n_a
    if rho <= 0.0:
        t_lo = np.linspace(0.0, 1.0, n_lo + 1)
        lo = K[:, None, :] + t_lo[None, :, None] * (C - K)[:, None, :]
        if knuckle:
            t_a = np.linspace(0.0, 1.0, n_a + 1)[1:]
            t_b = np.linspace(0.0, 1.0, n_b + 1)[1:]
            leg_a = (C[:, None, :]
                     + t_a[None, :, None] * (W - C)[:, None, :])
            leg_b = (W[:, None, :]
                     + t_b[None, :, None] * (S - W)[:, None, :])
            return np.concatenate([lo, leg_a, leg_b], axis=1)
        t_hi = np.linspace(0.0, 1.0, n_hi + 1)[1:]
        hi = C[:, None, :] + t_hi[None, :, None] * (S - C)[:, None, :]
        return np.concatenate([lo, hi], axis=1)
    P0 = C + rho * (K - C)
    P2 = C + rho * (W - C)
    m = max(128, 2 * max(n_lo, n_hi))
    # `_bezier`'s coefficients off the ONE shared parameter grid: the
    # per-element products are the scalar path's, in the scalar path's order,
    # broadcast over the station axis.
    # THE ARC IS BUILT (k, 2, 2m+1) AND TRANSPOSED AT THE END, not built
    # (k, 2m+1, 2). Elementwise arithmetic is order-independent bit for bit,
    # so this is the same float in every slot; what changes is that the
    # contiguous axis numpy iterates innermost becomes the 513-long parameter
    # axis instead of the 2-long coordinate axis. MEASURED 2026-08-20 on the
    # 241-station resistance hull, 7.41 ms -> 3.72 ms for the same array.
    # `a*P0 + b*C + c*P2` is accumulated LEFT TO RIGHT — the association the
    # scalar expression already has — into one buffer instead of five, which
    # on that hull saves 2 MB per avoided temporary.
    s = np.linspace(0.0, 1.0, 2 * m + 1)[None, None, :]
    arc = (1.0 - s) ** 2 * P0[:, :, None]
    tmp = np.empty_like(arc)
    np.multiply(2.0 * s * (1.0 - s), C[:, :, None], out=tmp)
    arc += tmp
    np.multiply(s * s, P2[:, :, None], out=tmp)
    arc += tmp
    del tmp
    arc = np.ascontiguousarray(arc.transpose(0, 2, 1))
    lo = np.concatenate([K[:, None, :], arc[:, :m + 1]], axis=1)
    if knuckle:
        leg_a = _resample_batch(
            np.concatenate([arc[:, m:], W[:, None, :]], axis=1),
            n_a + 1)[:, 1:]
        leg_a[:, -1] = W                    # end on W exactly, as the scalar
        t_b = np.linspace(0.0, 1.0, n_b + 1)[1:]
        leg_b = W[:, None, :] + t_b[None, :, None] * (S - W)[:, None, :]
        return np.concatenate([_resample_batch(lo, n_lo + 1), leg_a, leg_b],
                              axis=1)
    hi = np.concatenate([arc[:, m:], S[:, None, :]], axis=1)
    return np.concatenate([_resample_batch(lo, n_lo + 1),
                           _resample_batch(hi, n_hi + 1)[:, 1:]], axis=1)


# THE LADDER'S STATION COUNT. CALIBRATED, NOT DERIVED — no convergence
# criterion picks 41; a cost bar and an alignment rule do, and both are
# written down here so the next reader does not have to guess which.
#
# THE COST HALF. `export.py` (see `_LOFT_STATIONS`, lines 110-115) records the
# measurement that DECLINED 81: it takes `evaluate()` from 22.14 ms to
# 33.38 ms (+51%) against Gate 1's 50 ms bar, on every NSGA-II generation and
# every surrogate harvest, and it buys the LADDER wetted +0.014% and displaced
# volume +0.006%. RE-MEASURED on this box 2026-08-20 (reference hull, best of
# 7 `evaluate()` calls; the box is ~10x slower than the one above, so read the
# ratios, not the milliseconds):
#
#   n_stations   evaluate()       volume [m^3]  wetted [m^2]  twist [deg/m]
#           41    215.3 ms            8.285449     25.639213        11.2245
#           81    354.3 ms   +65%     8.286316     25.642969        11.4490
#          161    622.6 ms  +189%     8.286536     25.643922        11.7857
#
# i.e. 41 -> 161 costs 2.9x the ladder's wall clock and moves displaced volume
# by +0.013% and wetted surface by +0.018% — the volume figure is 154x inside
# `export.EXPORT_DISPLACEMENT_BAR_PCT` (2%) and 3x inside the 0.042% the
# exporter's own nz = 64 section sampling already spends.
#
# THE ALIGNMENT HALF, and it is the reason the number is 41 rather than 40 or
# 51: n - 1 = 40, and every denser grid in this tree is built to CONTAIN these
# stations exactly rather than merely be finer — `FEASIBILITY_PROBE_STATIONS`
# 1921 = 48 x 40 + 1, `export._LOFT_STATIONS` 161 = 4 x 40 + 1, the Michell
# production/converged grids 241 and 481. Both of those constants carry their
# own measurement of what an UNALIGNED count costs; moving 41 invalidates all
# of them at once.
#
# WHAT 41 DOES NOT BUY, named rather than left to be discovered:
#   * `panel_twist_rate` reads 95.5% of its converged value here (11.224
#     against 11.758 deg/m) — the LENIENT direction, stated at that method;
#   * `hydrostatics._waterline_ends` measured `lwl_eff` at 41 stations short by
#     0.969 of ONE station, inflating cb and cp by 2.4%, which is why that
#     function interpolates the waterline ends instead of snapping to a
#     station;
#   * `form_coefficients` refuses to trust these 41 at all: it resamples the
#     closed form at n = 401 with x_mb inserted, because a(x) touches 1 only at
#     x_mb and 41 linspace stations miss it by up to half a spacing (Cp 1.7%
#     high, the whole of plate P1's +-0.01 bar spent on a sampling artefact).
_LADDER_STATIONS = 41


@dataclass
class Hull:
    """Evaluated hull geometry at n stations."""

    params: np.ndarray
    n_stations: int = _LADDER_STATIONS

    x: np.ndarray = field(init=False)          # station positions [m], 0=transom
    z_keel: np.ndarray = field(init=False)     # keel z per station
    y_chine: np.ndarray = field(init=False)    # chine half-breadth
    z_chine: np.ndarray = field(init=False)
    y_sheer: np.ndarray = field(init=False)
    z_sheer: np.ndarray = field(init=False)
    y_wl: np.ndarray = field(init=False)       # design-waterline half-breadth
    A_sac: np.ndarray = field(init=False)      # target sectional area [m^2]
    _f: np.ndarray = field(init=False, repr=False)   # enveloped tan(flare)
    _m: np.ndarray = field(init=False, repr=False)   # tan(deadrise)
    _sections: dict = field(init=False, repr=False, default_factory=dict)
    # RESOLVED ONCE PER HULL, on the same standing assumption `_sections`
    # already makes — that `params` does not change under a built `Hull`.
    # MEASURED 2026-08-20 (cProfile, `evaluate()` on the 12-hull slider
    # fixture): the `roundness` property re-ran `grammar.named` 7566 times per
    # 6 evaluations (`section` and `section_control` both read it per call)
    # for 0.087 s, 3.2% of a 2.72 s profile, to return the same float.
    _rho: float = field(init=False, repr=False, default=0.0)
    # `section_control`'s five points for EVERY station, built in one batch on
    # first use: same expressions, station axis vectorised. See `_controls`.
    _ctrl: object = field(init=False, repr=False, default=None)
    # Per-station segment lengths of `section(i)`, for `wetted_surface`. See
    # `_section_stack`.
    _segs: dict = field(init=False, repr=False, default_factory=dict)
    # The (n_stations, N, 2) array `_prime_sections` builds, kept whole.
    _stack: object = field(init=False, repr=False, default=None)

    def __post_init__(self) -> None:
        # `_require_finite` BEFORE the linspace, not only inside `_stations`:
        # `np.linspace(0, nan, 41)` runs first otherwise and emits a numpy
        # RuntimeWarning on the way to a refusal that was going to happen
        # anyway — a warning that names an arithmetic operation instead of the
        # gene is exactly the misattribution this check exists to end.
        p0 = grammar.named(_require_finite(self.params))
        x = np.linspace(0.0, p0["LWL"], self.n_stations)
        s = _stations(self.params, x)
        self.x = x
        self.z_keel, self.y_chine, self.z_chine = (s["z_keel"], s["y_chine"],
                                                   s["z_chine"])
        self.y_sheer, self.z_sheer = s["y_sheer"], s["z_sheer"]
        self.y_wl, self.A_sac = s["y_wl"], s["A"]
        self._f, self._m = s["f"], s["m"]
        self._sections = {}
        self._segs = {}
        self._stack = None
        self._ctrl = None
        self._rho = float(p0["roundness"])

    @property
    def roundness(self) -> float:
        return self._rho

    # ---- the three edge curves, at ARBITRARY x ------------------------------

    def edge_curves(self, x: np.ndarray | None = None):
        """(keel, chine, sheer) as (n, 3) point arrays, ANALYTICALLY at `x`.

        The station arrays are a sample of these curves at `np.linspace`; this
        evaluates the same closed form anywhere, which is what a developable
        unroller needs when its rulings are NOT at constant station x and the
        two edges must therefore be read at different longitudinal parameters.

        MEASURED, and the reason this exists rather than a spline through the
        station points: `unroll` first resampled the edges with a CubicSpline
        through the 41 stations, and against the closed form that spline is
        0.16 mm off on the keel, 4.9 mm on the chine and **94.95 mm on the
        SHEER** — twenty times the 5 mm refold bar, before any developability
        question is asked. The sheer carries a taper to the stem whose
        x-derivative is unbounded there, so a cubic interpolant overshoots it
        badly. A refold measured against an interpolant is a refold measured
        against the wrong hull.
        """
        t = self.x if x is None else np.atleast_1d(np.asarray(x, dtype=float))
        zk, yc, zc, ys, zs = station_geometry(self.params, t)
        return (np.stack([t, np.zeros_like(t), zk], axis=1),
                np.stack([t, yc, zc], axis=1),
                np.stack([t, ys, zs], axis=1))

    # ---- section machinery -------------------------------------------------

    def _section_points(self, i: int, n_lo: int, n_hi: int) -> np.ndarray:
        return sample_section(
            (0.0, self.z_keel[i]),
            (self.y_chine[i], self.z_chine[i]),
            (self.y_sheer[i], self.z_sheer[i]),
            (self.y_wl[i], 0.0),
            self.roundness, n_lo, n_hi, knuckle=self.has_wl_knuckle)

    def section_control(self, i: int) -> tuple[np.ndarray, ...]:
        """(K, P0, P1, P2, S): the section as two legs and ONE quadratic arc.

        This is the section's EXACT description — five points, no sampling —
        and `immersed_section` integrates it in closed form off these. At
        `roundness == 0` the three arc controls collapse onto the chine and the
        description degenerates to the old keel/chine/sheer polyline.

        THE FIVE POINTS ARE BUILT FOR ALL STATIONS AT ONCE (`_controls`) and
        this returns row `i` of each. The expressions are unchanged and every
        one of them is elementwise, so the returned floats are bit-identical
        to the per-station construction this replaced — fenced at exactly 0.0
        in tests/test_geometry_kernel.py::
        test_the_batched_section_machinery_is_the_per_station_definition.
        MEASURED 2026-08-20 (cProfile, `evaluate()` on the 12-hull slider
        fixture): the per-station version built four `np.array` objects and
        ran two vector expressions on every one of 4182 calls per 6
        evaluations — 0.133 s tottime, 4.9% of a 2.72 s profile — for five
        points that do not depend on the waterline the caller is bisecting on.
        """
        K, P0, C, P2, S = self._controls()
        return K[i], P0[i], C[i], P2[i], S[i]

    def _controls(self):
        """(K, P0, C, P2, S), each (n_stations, 2). Memoised per hull."""
        c = self._ctrl
        if c is None:
            zero = np.zeros(self.n_stations)
            K = np.stack([zero, self.z_keel], axis=1)
            C = np.stack([self.y_chine, self.z_chine], axis=1)
            S = np.stack([self.y_sheer, self.z_sheer], axis=1)
            W = np.stack([self.y_wl, zero], axis=1)
            rho = self.roundness
            c = (K, C + rho * (K - C), C, C + rho * (W - C), S)
            # READ-ONLY: these rows are handed out to `_immersed`, which must
            # not be able to write back into another station's control points.
            for arr in c:
                arr.flags.writeable = False
            self._ctrl = c
        return c

    @property
    def has_wl_knuckle(self) -> bool:
        """True when the design waterline is a KNUCKLE vertex (dwl > 0):
        the topside is two legs, P2 -> W (derived flare, delivers B(x)) and
        W -> S (the designed law). False on every legacy hull, where W lies
        on the chine->sheer line and every consumer keeps its old shape."""
        return float(grammar.named(self.params).get("dwl", 0.0)) > 0.0

    def _knuckle_W(self):
        """(n, 2) waterline points, or None on a legacy hull — the exact
        argument `_immersed`/`_immersed_batch` take for the fifth leg."""
        if not self.has_wl_knuckle:
            return None
        return np.stack([self.y_wl, np.zeros(self.n_stations)], axis=1)

    def section(self, i: int) -> np.ndarray:
        """Section polyline, keel -> bilge -> sheer, as (N, 2) array of (y, z).

        N is 3 for a hard chine (`roundness == 0`) — the old shape, exactly —
        and 2 * SECTION_FILLET_SAMPLES + 1 for a radiused bilge.

        MEMOISED per hull. The section does not depend on the waterline, and
        `hydrostatics.solve_to_displacement` bisects on draft: MEASURED, ten
        `evaluate()` calls built 7842 sections where 410 are distinct, and
        `wetted_surface` alone accounted for 0.53 s of a 0.87 s profile.

        THE MISSES ARE FILLED FOR EVERY STATION AT ONCE (`_prime_sections`).
        MEASURED 2026-08-20: the memo itself was already perfect — 1021
        `section()` calls per evaluation, 282 misses, and 282 is exactly the
        two hulls' station counts (241 + 41), so nothing was being rebuilt.
        The cost was the 282 UNAVOIDABLE misses themselves, one Python call
        into `sample_section` each, at 0.899 s of a 2.72 s profile. They all
        share (rho, n_lo, n_hi) and a hull that needs one station's section
        needs every station's, so they are built in one batch.
        """
        cached = self._sections.get(i)
        if cached is None:
            self._prime_sections()
            cached = self._sections.get(i)
        if cached is None:
            # a negative or out-of-range index: `_section_points` keeps its
            # old numpy indexing semantics rather than becoming a KeyError.
            n = ((2 if self.has_wl_knuckle else 1)
             if self.roundness <= 0.0 else SECTION_FILLET_SAMPLES)
            cached = self._section_points(i, n, n)
            self._sections[i] = cached
        return cached

    def _prime_sections(self) -> None:
        """Fill `_sections` for EVERY station, in one `_sections_batch` call.

        `_section_points` stays the definition and this is the batch of it;
        the equality is fenced at exactly 0.0 (see `_sections_batch`).
        """
        n = ((2 if self.has_wl_knuckle else 1)
             if self.roundness <= 0.0 else SECTION_FILLET_SAMPLES)
        zero = np.zeros(self.n_stations)
        pts = _sections_batch(
            np.stack([zero, self.z_keel], axis=1),
            np.stack([self.y_chine, self.z_chine], axis=1),
            np.stack([self.y_sheer, self.z_sheer], axis=1),
            np.stack([self.y_wl, zero], axis=1),
            self.roundness, n, n, knuckle=self.has_wl_knuckle)
        self._stack = pts
        for i in range(self.n_stations):
            self._sections[i] = pts[i]

    def _section_stack(self):
        """(P, Z, SEG) for every station: points, the z column, segment lengths.

        Every section on a hull has the same point count, so the whole set is
        one (n_stations, N, 2) array — the array `_prime_sections` already
        built — and its z column and segment lengths are one batch each rather
        than 41 pairs of `np.diff`/`np.linalg.norm` calls per waterline.
        `SEG[i]` is a contiguous row, so `SEG[i][:k-1].sum()` sums the same
        operands in the same order as `norm(diff(pts[:k]))` did.
        """
        cached = self._segs.get("stack")
        if cached is None:
            if self._stack is None:
                self._prime_sections()
            P = self._stack
            dy = P[:, 1:, 0] - P[:, :-1, 0]
            dz = P[:, 1:, 1] - P[:, :-1, 1]
            cached = (P, np.ascontiguousarray(P[:, :, 1]),
                      np.sqrt(dy * dy + dz * dz))
            self._segs["stack"] = cached
        return cached

    def section_area(self, i: int) -> float:
        """CLOSED-FORM immersed half-area of section i at z = 0 [m^2].

        The analytic value the sampled section has to reproduce (plate P2's
        acceptance bar). It is A(x)/2 by construction wherever the geometric
        floor did not bite, which is what makes the bar meaningful: it tests
        the SAMPLING, not the target.
        """
        d = float(-self.z_keel[i])
        yc = float(self.y_chine[i])
        f, m = float(self._f[i]), float(self._m[i])
        K = 1.0 - m * f
        c1, c2 = _fillet_coeffs(self.roundness)
        return 0.5 * (K * yc * (c1 * d - c2 * m * yc) + d * d * f)

    def immersed_section(self, i: int, wl: float = 0.0):
        """Clip section at waterline wl. Returns (area_half, b_wl, zc_half).

        area_half: immersed area of the half-section [m^2]
        b_wl:      waterline half-breadth [m]
        zc_half:   z-centroid of immersed half-section [m]
        """
        W = self._knuckle_W()
        return _immersed(*self.section_control(i), wl,
                         W=None if W is None else W[i])

    # ---- integral properties ------------------------------------------------

    def hydro_arrays(self, wl: float = 0.0):
        """(a, b, zc) over all stations. `wl` is a height, or one per station.

        `immersed_section` STAYS THE DEFINITION and this is `_immersed_batch`,
        which is that closed form with the station axis broadcast in — every
        element bit-identical, fenced at exactly 0.0 in
        tests/test_geometry_kernel.py::
        test_the_batched_immersed_section_is_the_per_station_definition
        across the whole draft bracket and both bilge kinds.

        THE ARRAY FORM OF `wl` IS WHAT `hydrostatics.solve_trimmed` NEEDS: a
        trimmed waterplane clips each station at its own local height, which
        was already a per-station call and is now one batch.

        MEASURED 2026-08-20 (cProfile, `evaluate()` on the 12-hull slider
        fixture): 4182 `_immersed` calls per 6 evaluations cost 0.609 s of a
        1.737 s profile — 35%, the largest single item — for a five-point
        closed form whose Python and numpy call overhead dwarfs its
        arithmetic. 574 of the 738 calls an evaluation makes come from this
        method, 41 at a time, all at one waterline.
        """
        return _immersed_batch(*self._controls(), wl, W=self._knuckle_W())

    def dwl_deviation(self) -> np.ndarray:
        """|delivered - designed| waterline half-breadth, per station [m].

        THE REQUESTED-VS-ACHIEVED RECEIPT for the design waterline: the
        derived flare saturates toward per-station caps, so the delivered
        y_wl approximates B(x) rather than equalling it, and a designed
        curve the section family cannot fair is delivered as DEVIATION,
        never as a silent success (the snappy layer-table lesson, applied
        to geometry). All zeros when `dwl` == 0 — there is no designed
        curve to deviate from, so the legacy waterline is exact by
        definition.
        """
        p = grammar.named(self.params)
        d = float(p.get("dwl", 0.0))
        if d <= 0.0:
            return np.zeros_like(self.y_wl)
        b = waterline_ordinate(self.params, self.x)
        w = (1.0 - d) * self.y_wl + d * (0.5 * p["BWL"]) * b
        return np.abs(self.y_wl - w)

    def form_coefficients(self, n: int = 401) -> dict:
        """Cp, LCB, Cwp, LCF and Cm of the DELIVERED surface.

        Measured on a dense resample of the closed form that INCLUDES x_mb, so
        the maximum sectional area is the true continuous maximum. It matters:
        a(x) touches 1 only at x_mb, and 41 linspace stations miss it by up to
        half a spacing, which reads Cp about 1.7% HIGH — 0.010 on a Cp of 0.6,
        the whole of plate P1's +-0.01 bar spent on a sampling artefact.

        LCB is returned as % of LWL forward of midships, the same convention
        the `lcb` gene uses.
        """
        p = grammar.named(self.params)
        L = p["LWL"]
        xs = np.union1d(np.linspace(0.0, L, n), np.array([p["x_mb"] * L]))
        s = _stations(self.params, xs)
        yc, d, m, f, K = s["y_chine"], s["d"], s["m"], s["f"], s["K"]
        c1, c2 = s["c1"], s["c2"]
        A = K * yc * (c1 * d - c2 * m * yc) + d * d * f    # delivered, not target
        A = np.where(d > 0.0, A, 0.0)
        vol = float(np.trapezoid(A, xs))
        a_max = float(A.max())
        yw = 2.0 * s["y_wl"]
        awp = float(np.trapezoid(yw, xs))
        return {
            "volume_m3": vol,
            "Cp": vol / (a_max * L) if a_max > 0 else float("nan"),
            "lcb_pct": 100.0 * (float(np.trapezoid(A * xs, xs)) / vol - 0.5 * L) / L
            if vol > 0 else float("nan"),
            "Cm": a_max / (p["BWL"] * p["T"]),
            "Cwp": awp / (p["BWL"] * L),
            "lcf_pct": 100.0 * (float(np.trapezoid(yw * xs, xs)) / awp - 0.5 * L) / L
            if awp > 0 else float("nan"),
            "A_max_m2": a_max,
        }

    def alpha_e_deg(self, frac: float = 0.02) -> float:
        """Half-angle of entrance of the DESIGN WATERLINE [deg].

        THE CHORD OVER THE FORWARD `frac` OF LWL, not a tangent, and the
        method is part of the number. The tangent at the stem is not usable:
        the geometric floor on the chine half-breadth (see `_stations`) makes
        y_wl flatten inside the last fraction of a percent of LWL, so a
        one-sided derivative there measures the floor rather than the hull. A
        chord over a stated length is reproducible and is what a lines plan is
        read with.
        """
        L = grammar.named(self.params)["LWL"]
        yw = design_waterline(self.params, np.array([L * (1.0 - frac), L]))
        return math.degrees(math.atan2(float(yw[0] - yw[1]), frac * L))

    def fairness(self, nx: int = 41, nz: int = 64) -> float:
        """Transverse bending energy of the moulded surface, int ||d2p/ds2||^2.

        WHY THIS EXISTS: a polyline has no curvature, so on the old
        three-point section this integral was identically zero and a fairness
        objective had nothing to descend (plate P2). It is the discrete
        second difference along each section, normalised by the local chord
        so it estimates the continuous integral and therefore CONVERGES on a
        filleted section while DIVERGING like 1/h on a knuckle — which is the
        honest distinction between a fair surface and a creased one, and is
        the acceptance bar.
        """
        p = grammar.named(self.params)
        L = p["LWL"]
        xs = np.linspace(0.0, L, nx)
        s = _stations(self.params, xs)
        rho = self.roundness
        # THE STEM IS EXCLUDED, on the same rule and for the same reason as
        # `panel_twist_rate`'s >10% mask: the section shrinks to a point there,
        # so the bilge fillet's radius goes to zero with it and int kappa**2
        # genuinely diverges — a property of every hull that comes to a point,
        # not of an unfair one. MEASURED without the mask on a roundness-1.0
        # hull: 34.2 -> 88.8 over nz 16 -> 1024, i.e. RISING, because each
        # refinement resolves more of the near-stem singularity.
        half = np.maximum(s["y_wl"], s["y_sheer"])
        keep = half > 0.10 * float(half.max())
        tot = 0.0
        for i in range(nx):
            if not keep[i]:
                continue
            dense = sample_section((0.0, s["z_keel"][i]),
                                   (s["y_chine"][i], s["z_chine"][i]),
                                   (s["y_sheer"][i], s["z_sheer"][i]),
                                   (s["y_wl"][i], 0.0), rho, 8 * nz, 8 * nz,
                                   knuckle=self.has_wl_knuckle)
            # ONE uniform-arc-length resample over the WHOLE section, not one
            # per half. The two halves have different girths, so giving each
            # nz/2 points puts a step in the spacing at the bilge — and the
            # estimator then reads that step as a crease: MEASURED, the round
            # bilge diverged 3.2e2 -> 9.0e3 over nz 16 -> 1024, the same slope
            # as the knuckle it is supposed to be distinguished from.
            pts = _resample(dense, nz + 1)
            seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
            if seg.min() <= 0.0:
                continue
            d2 = pts[:-2] - 2.0 * pts[1:-1] + pts[2:]
            h = 0.5 * (seg[:-1] + seg[1:])
            tot += float(np.sum(np.sum(d2 * d2, axis=1) / h ** 3)) * (L / nx)
        return tot

    def wetted_surface(self, wl: float = 0.0) -> float:
        """Wetted surface [m^2], strip sum of immersed girth x dx (both sides).

        EVERYTHING BUT THE GIRTH SUM IS ONE BATCH over the stations: the dry
        test, the immersed point count and the part-segment up to the
        waterline are the same expressions with the station axis broadcast in.
        The SUM stays per station and stays a contiguous slice of the memoised
        segment lengths, because numpy's summation order is a function of the
        run length and a `cumsum` would not reproduce it. Fenced against a
        full recomputation at exactly 0.0 in
        tests/test_geometry_kernel.py::test_the_memoised_girth_is_the_
        recomputed_girth.

        MEASURED 2026-08-20 (cProfile, `evaluate()` on the 12-hull slider
        fixture): 19 calls per evaluation, each looping 41 stations in Python
        and re-running `np.diff` and `np.linalg.norm` on 257-point sections
        that were already memoised — 0.297 s of a 1.894 s profile.
        """
        P, Z, SEG = self._section_stack()
        n, N = Z.shape
        girth = np.zeros(n)
        live = ~(Z[:, 0] >= wl)                        # keel above water: dry
        ks = np.count_nonzero(Z < wl, axis=1)          # z monotone
        for i in np.flatnonzero(live):
            girth[i] = SEG[i, :max(int(ks[i]) - 1, 0)].sum()
        cut = live & (ks < N)
        if cut.any():
            j = np.flatnonzero(cut)
            kj = ks[j]
            prev, cur = P[j, kj - 1], P[j, kj]
            fr = ((wl - prev[:, 1]) / (cur[:, 1] - prev[:, 1]))[:, None]
            step = (prev + fr * (cur - prev)) - prev
            girth[j] += np.hypot(step[:, 0], step[:, 1])
        # GAP E17: THE STRIP IS NOT A RECTANGLE. `girth * dx` measures the
        # area of a surface whose sections are STACKED WITHOUT SHIFTING; a
        # real hull's sections move in y and z as x advances, so the ruled
        # surface between them is longer than dx wherever the form changes.
        #
        # The area element is |dP/dx x t_hat| ds dx, with t_hat the unit
        # tangent ALONG the section (no x-component). Only the part of dP/dx
        # PERPENDICULAR to that tangent adds area — a section sliding along
        # its own contour adds none — so the factor is
        #
        #     f = sqrt(1 + |perp(dP/dx)|^2)   >= 1, exactly 1 for a prism
        #
        # MEASURED on the mid-box hull: f runs 1.0000 to 1.1763 over the
        # immersed points (largest at the ends, where the form changes
        # fastest) and lifts the total by 1.04%. Small, one-signed, and it
        # feeds friction resistance directly, which is most of the total at
        # displacement speeds.
        dPdx = np.gradient(P, self.x, axis=0)
        tan = np.gradient(P, axis=1)
        that = tan / np.maximum(np.linalg.norm(tan, axis=2, keepdims=True),
                                1e-12)
        perp = dPdx - (dPdx * that).sum(axis=2, keepdims=True) * that
        slope = np.sqrt(1.0 + (perp ** 2).sum(axis=2))     # (n, N)
        # Weight each station's factor by the girth it actually carries: the
        # mean over IMMERSED points only, so a dry topside cannot inflate a
        # wetted strip.
        wet = Z < wl
        num = np.where(wet, slope, 0.0).sum(axis=1)
        den = np.maximum(wet.sum(axis=1), 1)
        girth = girth * np.where(wet.any(axis=1), num / den, 1.0)
        return 2.0 * float(np.trapezoid(girth, self.x))

    def deck_area(self) -> float:
        """Plan-view deck area [m^2] inside the sheer line (solar real estate)."""
        return 2.0 * float(np.trapezoid(self.y_sheer, self.x))

    def offsets_grid(self, nz: int = 12, wl: float = 0.0):
        """y(x, z) half-breadth grid below wl for the Michell integral.

        z points cluster quadratically toward the waterline (the Michell
        kernel decays fastest there — see benchmarks/wigley.py convergence).

        z = wl IS DELIBERATELY EXCLUDED, AND GAP E17's THIRD CLAUSE ASKING FOR
        IT IS REFUTED BY MEASUREMENT (2026-08-12). The clause reads "offsets_
        grid includes z = wl" and the reasoning is superficially right: the
        Michell kernel `exp(k0 sec^2(theta) z)` is largest at the surface, so
        stopping the interval short of it looks like throwing away the
        dominant slab. It was tried, measured, and it makes the answer WORSE by
        a factor of three.

        MEASURED on `tests/test_phase0.mid_params` at U = 2.5 m/s, identical
        grids either side of the keyword, R_w in newtons:

            n_stations   nz    excluded   included    included is
                   161   12     244.03     822.80      +237%
                   161   24     244.09     274.51       +12.5%
                   161   28     243.75     260.10        +6.7%   <- PRODUCTION
                   161   48     243.95     246.30        +1.0%
                   161   96     244.11     244.38        +0.1%
                    41   12     227.95     776.31      +241%
                    41   28     233.29     251.14        +7.6%

        THE EXCLUDED COLUMN IS ALREADY CONVERGED at every nz; the included one
        walks down to meet it and only arrives near nz = 96. The mechanism is
        the theta sweep: `sec` reaches ~318 at the last theta node, so
        `k0 sec^2` is ~1.6e5 and the kernel's decay scale there is SIX MICRONS.
        A trapezoid whose top interval is 4.5 mm wide, with the integrand equal
        to 1 at z = 0 and ~0 at the node below it, invents half of
        4.5 mm x 1 of contribution for an integral whose true width is 6 um.
        Excluding the endpoint puts the first node just under the surface,
        where the true value is already small, and the quadratic clustering
        (`s**2`) then resolves the low-theta contributions that actually have
        a z-scale of 1/k0 = 0.64 m.

        So this is not a truncated interval; it is the mitigation that makes a
        clustered trapezoid usable against a kernel whose width varies by five
        orders of magnitude across the theta sweep. The honest fix for the
        remaining 0.1% would be an analytic treatment of the near-surface
        layer, not a grid node at z = 0.
        """
        z0 = min(float(self.z_keel.min()), -1e-6)
        s = np.linspace(1.0, 0.0, nz, endpoint=False)
        zs = np.sort(wl + (z0 - wl) * s**2)
        Y = np.zeros((self.n_stations, nz))
        for i in range(self.n_stations):
            Y[i, :] = _halfbreadth_at(self.section(i), zs)
        return self.x, zs, Y

    def panel_mesh(self, nx: int = 30, nz: int = 8, wl: float = 0.0):
        """Quad panel mesh of the immersed hull (both sides), for Capytaine.

        Returns (vertices (N,3), faces (M,4) int indices).
        """
        xs = np.linspace(self.x[0], self.x[-1], nx)
        verts = []
        for xv in xs:
            pts = self._section_at(xv)
            zk = pts[0, 1]
            zt = np.linspace(min(zk, wl - 1e-9), wl, nz + 1)
            yv = _halfbreadth_at(pts, zt)
            for z, y in zip(zt, yv):
                verts.append((xv, y, z))
        verts = np.array(verts)
        faces = []
        for i in range(nx - 1):
            for j in range(nz):
                a = i * (nz + 1) + j
                faces.append((a, a + 1, a + nz + 2, a + nz + 1))
        # mirror to port
        nv = len(verts)
        port = verts * np.array([1.0, -1.0, 1.0])
        verts = np.vstack([verts, port])
        faces_p = [(d + nv, c + nv, b + nv, a + nv) for a, b, c, d in faces]
        return verts, np.array(faces + faces_p, dtype=int)

    def closed_mesh(self, nx: int = 80, nz: int = 16):
        """Watertight triangle mesh of the FULL hull (keel to sheer, both
        sides, deck lid, transom cap) — for CFD, where an open shell lets the
        mesher flood the interior (found by surfaceFeatureExtract: 198 open
        edges on the wetted-only STL).

        Returns (verts (N,3), tris (M,3) int). Degenerate slivers at the stem
        are skipped by area.

        THE BILGE IS A ROW OF THE GRID (`chine_row`), not something the
        z-sampling straddles. It used to be the latter: `z` ran uniformly from
        `z_keel` to `z_sheer` over nz+1 levels, so the chine KNUCKLE — the one
        hard feature every hull this grammar emits has — fell strictly inside a
        sampling interval and the mesh chorded across it.

        MEASURED 2026-08-12 on hulls 4/8/14 of `sample_valid(25, MissionSpec(),
        seed=0)`, at the nx=600/nz=120 triangulation `make_resistance_case`
        actually writes: the exact chine point sat 11.95 / 4.50 / 11.45 mm off
        the chord that replaced it, at EVERY x, not only at the ends. It was
        the whole of the ~10 mm floor in the deviation of this mesh from the
        analytic surface (`docs/research/NURBS.md` §1) — the rest of the hull
        agrees with the manufacturing loft to 0.3 mm rms. It also meant
        `surfaceFeatureExtract` had no chine crease to find: the knuckle was
        spread over two rows of triangles whose normal jump is half the real
        one, on both sides of a spurious edge.

        The rows are apportioned between the two panels ONCE per hull, by mean
        girth, so the row index of the bilge is the same at every station and
        the quad connectivity below is unchanged. Row count stays nz+1: this
        redistributes rows, it does not add any.

        SINCE PLATE P2 the rows come from `sample_section`, so a filleted
        bilge is resolved by the same grid rather than chorded: at roundness 0
        the sampler is the old two-segment linear interpolation, bit for bit.

        WHAT THIS ACTUALLY EMITS AT THE PRODUCTION 600x120, MEASURED
        2026-08-20 on the reference hull (`navalai.reference`) — the counts
        matter because `cfd/case.py`'s `_STL_NX_CAP` comment and CLAUDE.md
        both describe the cap as "600x120 ~ 144k triangles", which is HALF the
        truth and off by exactly the mirror:

            quads offered      144,599   (2 x (nx-1) x nz shell + deck strip
                                          + transom cap + stem cap)
            triangles offered  289,198   two per quad
            triangles emitted  288,862   336 dropped by the area bar below
            vertices STORED    866,586   = 3 x emitted
            vertices UNIQUE    144,433   6.00x duplication

        THE 6x DUPLICATION IS THE HONEST FACT ABOUT THIS MESH, and it is
        recorded rather than fixed: `vid()` below appends a fresh vertex per
        triangle corner, so there is NO indexed sharing anywhere in the
        output. Every interior vertex is stored once per incident triangle
        (6 of them on a quad grid, hence the ratio landing on 6.00 to three
        figures). The mesh is watertight by COORDINATE COINCIDENCE, not by
        connectivity: the duplicates are bit-identical (unique-at-full-
        precision and unique-after-rounding-to-6-decimals are the SAME 144,433
        vertices), because both copies come from the same element of the same
        `S`/`P` array, not from two independent evaluations.

        THAT IS WHY THE 1e-6 ROUNDING IN `cfd.case.stl_watertight_report` HAS
        NEVER FIRED A FALSE MERGE, and why it is nonetheless a coupling worth
        naming: that report keys edges on `round(coord, 6)` and the ASCII
        writer emits `%.6e`, so the tolerance of the watertightness VERDICT is
        pinned to the precision of the FILE FORMAT — two constants in another
        module that must move together. MEASURED here at 600x120 on the
        reference hull: `%.6e` formatting collapses 0 of the 144,433 unique
        vertices (144,433 distinct strings), so today the verdict is about the
        mesh and not about the format — a measurement, not a guarantee, and
        the one to repeat if either constant moves or the mesh gets finer.
        An indexed/welded emit would make the watertightness
        structural instead of coincidental; that refactor is DEFERRED, and
        this paragraph is what the next reader needs to decide whether to do
        it.
        """
        xs = np.linspace(float(self.x[0]), float(self.x[-1]), nx)
        jc = self.chine_row(nz)
        S = np.zeros((nx, nz + 1, 3))
        for i, xv in enumerate(xs):
            S[i, :, 1:] = self._section_at_rows(xv, jc, nz - jc)
            S[i, :, 0] = xv
        P = S * np.array([1.0, -1.0, 1.0])

        verts: list = []
        tris: list = []

        def vid(p) -> int:
            verts.append(p)
            return len(verts) - 1

        # THE SLIVER BAR IS A DEGENERACY BAR, NOT A QUALITY BAR, and the
        # measurement says so: at the production 600x120 EVERY triangle it
        # drops has area EXACTLY 0.0, and the smallest SURVIVING triangle is
        # four to five orders above the bar. Where the zeros are, MEASURED per
        # emitting site: 240 in the stem cap (all of it — the stem section is a
        # point, so every quad there is degenerate by construction), 1 in the
        # deck strip, 1 in the transom cap, and on the reference hull a further
        # 94 in the shell, ALL of them in the single last station interval
        # (i = 598, x = 9.9833 m of 10.0), where the hard-chine section
        # collapses onto the centreline. The round-bilge hulls below have no
        # shell zeros at all.
        # MEASURED 2026-08-20, reference hull plus `sample_valid(4,
        # MissionSpec(), seed=0)`, 289,198 triangles offered per hull:
        #
        #     hull        dropped   all of area 0.0?   smallest kept [m^2]
        #     reference       336         yes               3.209e-06
        #     sv0 rho .995    242         yes               7.764e-05
        #     sv1 rho .127    242         yes               5.590e-06
        #     sv2 rho .085    242         yes               7.514e-06
        #     sv3 rho .310    242         yes               1.886e-05
        #
        # So the count is IDENTICAL at 1e-6, 1e-8, 1e-10, 1e-12, 1e-14 and at
        # a strict `> 0.0`: nothing lives in the gap. In min-edge terms 1e-10
        # m^2 is an equilateral triangle of 0.0152 mm edge (1e-8 -> 0.152 mm,
        # 1e-12 -> 0.0015 mm) against a smallest kept min-edge of 0.378 mm on
        # the reference hull — 25x clear of the 1e-10 bar's own edge scale.
        # The value is therefore CALIBRATED, not derived: it is any number
        # inside the measured empty band (0, 5.6e-6] m^2, and it is left where
        # it is because nothing measured moves it. What WOULD move it is a
        # bar that starts deleting real triangles — a hole in a mesh whose
        # watertightness is coincidental (see the docstring) is not a smaller
        # mesh, it is an open shell that lets the mesher flood the interior.
        def quad(a, b, c, d) -> None:
            # split into two triangles; drop degenerate slivers
            for tri in ((a, b, c), (a, c, d)):
                p = np.array(tri)
                area = 0.5 * np.linalg.norm(np.cross(p[1] - p[0], p[2] - p[0]))
                if area > 1e-10:
                    tris.append((vid(p[0]), vid(p[1]), vid(p[2])))

        for i in range(nx - 1):
            for j in range(nz):
                # starboard shell (outward +y), port mirrored winding
                quad(S[i, j], S[i, j + 1], S[i + 1, j + 1], S[i + 1, j])
                quad(P[i + 1, j], P[i + 1, j + 1], P[i, j + 1], P[i, j])
            # Deck lid strip, outward +z. The winding was S[i], S[i+1],
            # P[i+1], P[i] — with S at +y and P at -y that gives
            # cross(b-a, c-a) with n_z = -2y*dx < 0, i.e. the ENTIRE DECK
            # POINTED DOWN INTO THE HULL. MEASURED on a fresh grammar hull:
            # 397 flipped triangles (mean n_z = -0.999), two orientation zones
            # by surfaceCheck, and a signed volume of 16.886 m^3 against a true
            # 27.279 — understated by 38.1%. runs/gci/coarse shipped with the
            # same defect at -43%.
            #
            # It survived because `stl_watertight_report` keyed edges on
            # tuple(sorted(edge)) — UNDIRECTED — so a flipped triangle still
            # gives every edge a count of 2 and the report says watertight.
            # snappy was unaffected (castellation uses ray parity from
            # locationInMesh, which does not care about winding), which is why
            # the meshes looked fine; but the divergence-theorem integrals in
            # cfd/post.py assume outward winding, and they feed the sixDoF mass
            # and inertia. They were safe only because the flipped patch is the
            # deck, which is clipped away above the waterline — luck, not design.
            quad(S[i, nz], P[i, nz], P[i + 1, nz], S[i + 1, nz])
        # transom cap at x = xs[0] (outward -x)
        for j in range(nz):
            quad(S[0, j], P[0, j], P[0, j + 1], S[0, j + 1])
        # stem cap (degenerate for sharp bows; quads self-filter by area)
        for j in range(nz):
            quad(S[-1, j], S[-1, j + 1], P[-1, j + 1], P[-1, j])

        return np.array(verts), np.array(tris, dtype=int)

    def chine_row(self, nz: int) -> int:
        """Row index of the BILGE in an (nz+1)-row section grid.

        ONE definition, because `closed_mesh` and `admissibility.surface_grid`
        both need it and a second copy would be defect class 2 — which is
        exactly why `surface_grid` is fenced by a test against `closed_mesh`'s
        own helpers.

        The split is by MEAN GIRTH of the two panels over the stations, not by
        z-extent: the bottom panel is wide and shallow at low deadrise, so a
        z-proportional split starves it of rows precisely on the hulls where
        it does the most work. It is a single integer per hull, so the row
        index does not move along the hull and the quad connectivity in
        `closed_mesh` is unchanged.

        Clamped to [1, nz-1]: a panel with zero rows is a panel that is not
        meshed, and returning 0 or nz would silently delete one.
        """
        g_lo = float(np.mean(np.hypot(self.y_chine, self.z_chine - self.z_keel)))
        g_hi = float(np.mean(np.hypot(self.y_sheer - self.y_chine,
                                      self.z_sheer - self.z_chine)))
        tot = g_lo + g_hi
        frac = 0.5 if tot <= 1e-12 else g_lo / tot
        return int(min(max(int(round(nz * frac)), 1), max(nz - 1, 1)))

    def _section_at_rows(self, xv: float, n_lo: int, n_hi: int) -> np.ndarray:
        """(n_lo+n_hi+1, 2) section at arbitrary x, bilge on row n_lo."""
        i = np.searchsorted(self.x, xv)
        i = min(max(i, 1), self.n_stations - 1)
        f = (xv - self.x[i - 1]) / (self.x[i] - self.x[i - 1])

        def lerp(lo, hi):
            return (1 - f) * lo + f * hi

        return sample_section(
            (0.0, lerp(self.z_keel[i - 1], self.z_keel[i])),
            (lerp(self.y_chine[i - 1], self.y_chine[i]),
             lerp(self.z_chine[i - 1], self.z_chine[i])),
            (lerp(self.y_sheer[i - 1], self.y_sheer[i]),
             lerp(self.z_sheer[i - 1], self.z_sheer[i])),
            (lerp(self.y_wl[i - 1], self.y_wl[i]), 0.0),
            self.roundness, n_lo, n_hi, knuckle=self.has_wl_knuckle)

    def _section_at(self, xv: float) -> np.ndarray:
        n = ((2 if self.has_wl_knuckle else 1)
             if self.roundness <= 0.0 else SECTION_FILLET_SAMPLES)
        return self._section_at_rows(xv, n, n)

    def _sections_at_rows_batch(self, xs: np.ndarray, n_lo: int,
                                n_hi: int) -> np.ndarray:
        """(len(xs), n_lo+n_hi+1, 2): `_section_at_rows` at every x, one batch.

        `_section_at_rows` STAYS THE DEFINITION and this is a transcription of
        it with the station axis vectorised — the same lerp, the same Bezier
        coefficients off the same shared `s` grid, the same arc-length
        resample, in the same evaluation order, so every element is
        bit-identical to the loop it replaces. That equality is FENCED, not
        trusted (tests/test_admissibility.py::
        test_the_batch_section_sampler_is_the_loop, 1e-12, roundness 0 and
        roundness > 0 both): a second copy of a shape function is defect
        class 2 and this is one.

        WHY IT EXISTS: `admissibility.surface_grid` needs ~600 sections per
        hull on the round-bilge path and the per-call overhead of
        `sample_section` (a fresh linspace, a (2m+1, 2) `_bezier` and two
        `_resample`s per station) put the screen at ~140 ms/hull against its
        100 ms bar (~265 ms/hull under loadavg ~4). All ~600 stations share
        (rho, n_lo, n_hi) and differ only in the four control points, which
        is exactly the shape a batch removes: MEASURED 2026-08-20, this
        method runs ~28 ms/hull at 600x120 (screen ~48 ms/hull) with the
        sampled points unchanged.
        """
        xs = np.asarray(xs, dtype=float)
        i = np.clip(np.searchsorted(self.x, xs), 1, self.n_stations - 1)
        f = (xs - self.x[i - 1]) / (self.x[i] - self.x[i - 1])

        def lerp(a):
            return (1 - f) * a[i - 1] + f * a[i]

        K = np.stack([np.zeros_like(xs), lerp(self.z_keel)], axis=1)
        C = np.stack([lerp(self.y_chine), lerp(self.z_chine)], axis=1)
        S = np.stack([lerp(self.y_sheer), lerp(self.z_sheer)], axis=1)
        W = np.stack([lerp(self.y_wl), np.zeros_like(xs)], axis=1)
        # The body that used to be inlined here now lives in `_sections_batch`
        # so the STATION-indexed memo can share it instead of copying it.
        return _sections_batch(K, C, S, W, self.roundness, n_lo, n_hi,
                               knuckle=self.has_wl_knuckle)

    def min_bend_radius(self) -> float:
        """Smallest 3-D bend radius [m] along the keel and chine curves.

        Developable panels bend about their rulings; the tightest curvature a
        sheet must take follows these edge curves. Checked against the marine-
        plywood cold-bend limit (~80 x thickness) in the ladder.
        """
        r_min = np.inf
        for ys, zs in ((np.zeros_like(self.x), self.z_keel),
                       (self.y_chine, self.z_chine)):
            d1 = np.stack([np.gradient(self.x, self.x),
                           np.gradient(ys, self.x),
                           np.gradient(zs, self.x)], axis=1)
            d2 = np.stack([np.gradient(d1[:, 0], self.x),
                           np.gradient(d1[:, 1], self.x),
                           np.gradient(d1[:, 2], self.x)], axis=1)
            cross = np.cross(d1, d2)
            speed = np.linalg.norm(d1, axis=1)
            kappa = np.linalg.norm(cross, axis=1) / np.maximum(speed**3, 1e-12)
            # ignore the stem tip where the chine collapses to a point
            mask = self.y_chine > 0.05 * max(float(self.y_chine.max()), 1e-9)
            k = kappa[mask] if mask.any() else kappa
            if k.size and k.max() > 1e-9:
                r_min = min(r_min, 1.0 / float(k.max()))
        return float(r_min)

    def panel_twist_rate(self) -> float:
        """Max bottom-panel twist [deg/m] — the developability metric.

        Only evaluated where the bottom panel has meaningful width (>10% of
        max chine half-breadth); at the stem the panel width -> 0 and the
        deadrise angle is undefined, not twisted.

        GAP E6: this is now what `grammar.check` gates on. It existed, it was
        correct, and until 2026-08-07 it was consumed by NO gate — the L0
        check used a MEAN twist instead, which averages a local fold away.
        Measured consequences of the swap are recorded at the call site.

        RESOLUTION, MEASURED on `tests/test_phase0.mid_params` (beta 8 -> 30
        deg over 0.35 L), because a discrete max under-reports a peak and
        under-reporting twist is the LENIENT direction, so it must be stated:

            n_stations   21     41     81    161    321    641
            deg/m      9.878 11.224 11.449 11.561 11.730 11.758

        The shipped 41 stations read 95.5% of the converged 11.76. The
        remaining gap to the unmasked continuous peak (2 x mean = 12.571 for
        this hull) is the >10%-width mask above, and is deliberate.
        """
        mask = self.y_chine > 0.10 * self.y_chine.max()
        ang = np.degrees(np.arctan2(self.z_chine - self.z_keel,
                                    np.maximum(self.y_chine, 1e-9)))
        rate = np.abs(np.diff(ang)) / np.maximum(np.diff(self.x), 1e-9)
        seg = mask[:-1] & mask[1:]
        return float(rate[seg].max()) if seg.any() else 0.0


def _split_at_z(P0: np.ndarray, P1: np.ndarray, P2: np.ndarray, z: float):
    """de Casteljau split of the bilge arc where it crosses height z.

    Returns the sub-arc's controls (P0, Q1, X) from the keel end up to z. The
    arc's z is monotone (z(P0) <= z(P1) <= z(P2) by construction), so the
    quadratic B_z(s) = z has exactly one root in [0, 1].
    """
    a = P0[1] - 2.0 * P1[1] + P2[1]
    b = 2.0 * (P1[1] - P0[1])
    c = P0[1] - z
    if abs(a) < 1e-14:
        s = -c / b if abs(b) > 1e-14 else 0.0
    else:
        disc = max(b * b - 4.0 * a * c, 0.0)
        r = math.sqrt(disc)
        s1, s2 = (-b + r) / (2.0 * a), (-b - r) / (2.0 * a)
        s = s1 if 0.0 <= s1 <= 1.0 else s2
    s = min(max(s, 0.0), 1.0)
    Q1 = (1.0 - s) * P0 + s * P1
    X = (1.0 - s) ** 2 * P0 + 2.0 * s * (1.0 - s) * P1 + s * s * P2
    return P0, Q1, X


def _immersed(K, P0, P1, P2, S, wl: float, W=None):
    """Immersed half-area, waterline half-breadth and z-centroid, EXACTLY.

    NO SAMPLING. The immersed region is a polygon on the section's control
    points plus (or minus) the parabolic segment between the arc's chord and
    the arc, and both have closed forms: the segment's area is 2/3 of its
    control triangle (Archimedes) and its centroid is
    (2/5)(P0 + P2) + (1/5)P1.

    THIS EXISTS BECAUSE THE SAMPLED POLYGON COULD NOT MEET PLATE P2's 1e-6
    AREA BAR AT ANY AFFORDABLE RESOLUTION. An inscribed polygon under-reads a
    convex arc by (2/3)T/n^2, and with the section sampled uniformly in ARC
    LENGTH — which the fairness estimator requires — only the arc's share of
    the girth lands on the fillet. MEASURED on the roundest hull of
    `grammar.sample(20, rng(0))` (roundness 0.995, closed-form half-area
    0.77065390 m^2): 4.80e-4 relative at 32 samples per half, 9.71e-6 at 256,
    2.43e-6 at 512, 6.08e-7 at 1024 — so the bar needed ~1000 points per
    section, which is 12 ms per `hydro_arrays` inside a draft bisection. The
    closed form is exact at five points and is cross-checked against BOTH the
    quadratic-coefficient algebra in `Hull.section_area` and a dense sampled
    polygon in `tests/test_geometry_kernel.py`.
    """
    zk = float(K[1])
    if zk >= wl:                                    # keel above water: dry
        return 0.0, 0.0, 0.0

    def leg_cut(A, B):
        t = (wl - A[1]) / (B[1] - A[1])
        return A + t * (B - A)

    seg = None                                      # (P0, P1, P2) of the arc
    if wl <= P0[1]:
        pts = [K, leg_cut(K, P0)]
    elif wl <= P2[1]:
        q0, q1, q2 = _split_at_z(P0, P1, P2, wl)
        pts, seg = [K, P0, q2], (q0, q1, q2)
    elif W is not None:
        # THE WATERLINE KNUCKLE (Phase 3, slice 2): the topside is TWO legs,
        # P2 -> W (carrying the derived flare that delivers B(x)) and
        # W -> S (the designed topside law). W is None on every legacy
        # section, and this branch does not exist for them — the four-case
        # clip above and below is byte-for-byte the pre-knuckle function.
        if wl <= W[1]:
            pts, seg = [K, P0, P2, leg_cut(P2, W)], (P0, P1, P2)
        elif wl <= S[1]:
            pts, seg = [K, P0, P2, W, leg_cut(W, S)], (P0, P1, P2)
        else:
            pts, seg = [K, P0, P2, W, S], (P0, P1, P2)
            wl = float(S[1])
    elif wl <= S[1]:
        pts, seg = [K, P0, P2, leg_cut(P2, S)], (P0, P1, P2)
    else:
        pts, seg = [K, P0, P2, S], (P0, P1, P2)
        wl = float(S[1])
    b_wl = float(pts[-1][0])
    poly = np.vstack(pts + [np.array([0.0, wl])])
    a_p, gy, gz = _signed_polygon(poly)
    a_s, sy, sz = 0.0, 0.0, 0.0
    if seg is not None:
        q0, q1, q2 = seg
        a_s = (2.0 / 3.0) * 0.5 * float((q1[0] - q0[0]) * (q2[1] - q0[1])
                                        - (q2[0] - q0[0]) * (q1[1] - q0[1]))
        g = 0.4 * (q0 + q2) + 0.2 * q1
        sy, sz = float(g[0]), float(g[1])
    tot = a_p + a_s
    if abs(tot) < 1e-15:
        return 0.0, b_wl, 0.0
    return abs(tot), b_wl, (a_p * gz + a_s * sz) / tot


def _py_max0(v: np.ndarray) -> np.ndarray:
    """`max(v, 0.0)` with PYTHON's tie rule, not `np.maximum`'s.

    Python's `max(a, b)` returns `b` only when `b > a`, so `max(-0.0, 0.0)` is
    -0.0 and `max(nan, 0.0)` is nan; `np.maximum` returns +0.0 for the first.
    A sign of zero that reaches `_split_at_z`'s `s * P1` can flip the sign of
    a zero in the returned control point, so the batch reproduces the scalar
    rule rather than the nearest numpy one.
    """
    return np.where(0.0 > v, 0.0, v)


def _py_min1(v: np.ndarray) -> np.ndarray:
    """`min(v, 1.0)` with Python's tie rule. See `_py_max0`."""
    return np.where(1.0 < v, 1.0, v)


def _split_at_z_rows(P0: np.ndarray, P1: np.ndarray, P2: np.ndarray,
                     z: np.ndarray):
    """`_split_at_z` over a stack of arcs. `_split_at_z` stays the definition.

    Operation for operation the scalar function, with the arc axis broadcast
    in. Two places need care and get it:

      * `(1.0 - s) ** 2` is a PYTHON float power in the scalar path, and
        MEASURED on this box over 400k random doubles, `float.__pow__(x, 2)`
        (libm `pow`) differs from `x * x` — and therefore from numpy's `x**2`,
        which numpy rewrites to `square` — in 239 of 300,000 cases, one ulp.
        `np.float_power(x, 2.0)` goes through the same libm `pow` and matches
        it in all 400,000. That is why the exponent is spelled this way here
        and must stay that way.
      * `max`/`min` keep Python's tie rule (`_py_max0`, `_py_min1`).

    The branch-free evaluation computes both roots for every arc, so the
    degenerate denominators of the LINEAR rows are substituted before the
    division rather than divided and discarded — no warning, and no reliance
    on a discarded inf.
    """
    z0, z1, z2 = P0[:, 1], P1[:, 1], P2[:, 1]
    a = z0 - 2.0 * z1 + z2
    b = 2.0 * (z1 - z0)
    c = z0 - z
    lin = np.abs(a) < 1e-14
    b_ok = np.abs(b) > 1e-14
    s_lin = np.where(b_ok, -c / np.where(b == 0.0, 1.0, b), 0.0)
    disc = _py_max0(b * b - 4.0 * a * c)
    r = np.sqrt(disc)
    den = np.where(lin, 1.0, 2.0 * a)
    s1 = (-b + r) / den
    s2 = (-b - r) / den
    s = np.where(lin, s_lin, np.where((s1 >= 0.0) & (s1 <= 1.0), s1, s2))
    s = _py_min1(_py_max0(s))[:, None]
    one_minus = 1.0 - s
    Q1 = one_minus * P0 + s * P1
    X = (np.float_power(one_minus, 2.0) * P0
         + 2.0 * s * one_minus * P1 + s * s * P2)
    return P0, Q1, X


def _immersed_batch(K: np.ndarray, P0: np.ndarray, P1: np.ndarray,
                    P2: np.ndarray, S: np.ndarray, wl, W=None):
    """`_immersed` over a stack of sections: (a, b_wl, zc), each (n,).

    `_immersed` STAYS THE DEFINITION. This is the same four-case clip, the
    same shoelace on the same vertices in the same order, and the same
    Archimedes segment, with the station axis broadcast in — so every element
    is bit-identical, not merely close. Fenced at exactly 0.0 in
    tests/test_geometry_kernel.py::
    test_the_batched_immersed_section_is_the_per_station_definition.

    THE PADDING IS AREA-NEUTRAL BY CONSTRUCTION, which is what lets one
    rectangular polygon array carry all four cases. The scalar clip emits 3,
    4 or 5 vertices; here the LAST REAL VERTEX IS REPEATED up to five before
    the closing `(0, wl)` point. A repeated vertex contributes
    `y*z - y*z == 0.0` exactly to the shoelace and `(y+y) * 0.0 == 0.0` to
    the centroid moment, and numpy sums fewer than eight addends left to
    right exactly as the scalar path does, so the padded sum is the unpadded
    sum term for term. `wl` is a scalar height or one per station.
    """
    n = K.shape[0]
    w = np.empty(n, dtype=float)
    w[:] = wl
    a_out = np.zeros(n)
    b_out = np.zeros(n)
    zc_out = np.zeros(n)
    # `~(zk >= wl)`, not `zk < wl`: the scalar guard is `if zk >= wl: dry`, so
    # a NaN keel height falls through to the clip rather than being called dry.
    live = ~(K[:, 1] >= w)
    if not live.any():
        return a_out, b_out, zc_out
    # A HULL FLOATING ANYWHERE ON ITS OWN BRACKET HAS EVERY STATION WET, and
    # the sub-selection is then five array copies that reproduce their inputs.
    # `sel is None` is that case, and it changes nothing but the copies.
    if live.all():
        sel = None
        Kv, P0v, P1v, P2v, Sv, wv = K, P0, P1, P2, S, w
        Wv = W
        m = n
    else:
        sel = np.flatnonzero(live)
        Kv, P0v, P1v, P2v, Sv = (A[sel] for A in (K, P0, P1, P2, S))
        Wv = W[sel] if W is not None else None
        wv = w[sel]
        m = sel.size

    # THE FOUR CASES, in the scalar function's order. With a KNUCKLE the
    # topside is two legs and the count is five; `_immersed` stays the
    # definition for both shapes, and W is None on every legacy call so
    # the four-case path below is untouched byte for byte.
    c1 = wv <= P0v[:, 1]                            # cut on the keel leg
    c2 = ~c1 & (wv <= P2v[:, 1])                    # cut inside the bilge arc
    if Wv is not None:
        c3a = ~c1 & ~c2 & (wv <= Wv[:, 1])          # cut on the P2->W leg
        c3b = ~c1 & ~c2 & ~c3a & (wv <= Sv[:, 1])   # cut on the W->S leg
        c3 = c3a | c3b
    else:
        c3a = c3b = None
        c3 = ~c1 & ~c2 & (wv <= Sv[:, 1])           # cut on the topside leg
    c4 = ~(c1 | c2 | c3)                            # fully immersed to sheer

    v1 = np.empty((m, 2))
    v2 = np.empty((m, 2))
    v3 = np.empty((m, 2))
    Q0 = np.zeros((m, 2))
    Q1 = np.zeros((m, 2))
    Q2 = np.zeros((m, 2))
    weff = wv.copy()

    if c1.any():
        j = np.flatnonzero(c1)
        A, B = Kv[j], P0v[j]
        t = ((wv[j] - A[:, 1]) / (B[:, 1] - A[:, 1]))[:, None]
        cut = A + t * (B - A)
        v1[j] = cut
        v2[j] = cut
        v3[j] = cut                                 # no arc: seg is None
    rest = np.flatnonzero(~c1)
    v1[rest] = P0v[rest]
    if c2.any():
        j = np.flatnonzero(c2)
        q0, q1, q2 = _split_at_z_rows(P0v[j], P1v[j], P2v[j], wv[j])
        v2[j] = q2
        v3[j] = q2
        Q0[j], Q1[j], Q2[j] = q0, q1, q2
    j34 = np.flatnonzero(c3 | c4)
    if j34.size:
        v2[j34] = P2v[j34]
        Q0[j34], Q1[j34], Q2[j34] = P0v[j34], P1v[j34], P2v[j34]
    if Wv is not None:
        v3b = np.empty((m, 2))
        if c3a.any():
            j = np.flatnonzero(c3a)
            A, B = P2v[j], Wv[j]
            t = ((wv[j] - A[:, 1]) / (B[:, 1] - A[:, 1]))[:, None]
            v3[j] = A + t * (B - A)
            v3b[j] = v3[j]                          # padding: repeat vertex
        if c3b.any():
            j = np.flatnonzero(c3b)
            v3[j] = Wv[j]
            A, B = Wv[j], Sv[j]
            t = ((wv[j] - A[:, 1]) / (B[:, 1] - A[:, 1]))[:, None]
            v3b[j] = A + t * (B - A)
        if c4.any():
            j = np.flatnonzero(c4)
            v3[j] = Wv[j]
            v3b[j] = Sv[j]
            weff[j] = Sv[j, 1]                      # wl = float(S[1])
        j12 = np.flatnonzero(c1 | c2)
        if j12.size:
            v3b[j12] = v3[j12]                      # padding: repeat vertex
        poly = np.empty((m, 6, 2))
        poly[:, 0] = Kv
        poly[:, 1] = v1
        poly[:, 2] = v2
        poly[:, 3] = v3
        poly[:, 4] = v3b
        poly[:, 5, 0] = 0.0
        poly[:, 5, 1] = weff
    else:
        if c3.any():
            j = np.flatnonzero(c3)
            A, B = P2v[j], Sv[j]
            t = ((wv[j] - A[:, 1]) / (B[:, 1] - A[:, 1]))[:, None]
            v3[j] = A + t * (B - A)
        if c4.any():
            j = np.flatnonzero(c4)
            v3[j] = Sv[j]
            weff[j] = Sv[j, 1]                      # wl = float(S[1])

        poly = np.empty((m, 5, 2))
        poly[:, 0] = Kv
        poly[:, 1] = v1
        poly[:, 2] = v2
        poly[:, 3] = v3
        poly[:, 4, 0] = 0.0
        poly[:, 4, 1] = weff

    py, pz = poly[:, :, 0], poly[:, :, 1]
    qy, qz = np.roll(py, -1, axis=1), np.roll(pz, -1, axis=1)
    cross = py * qz - qy * pz
    a_p = 0.5 * cross.sum(axis=1)
    small = np.abs(a_p) < 1e-15                     # `_signed_polygon`'s floor
    gz = ((pz + qz) * cross).sum(axis=1) / np.where(small, 1.0, 6.0 * a_p)
    a_p = np.where(small, 0.0, a_p)
    gz = np.where(small, 0.0, gz)

    a_s = (2.0 / 3.0) * 0.5 * ((Q1[:, 0] - Q0[:, 0]) * (Q2[:, 1] - Q0[:, 1])
                               - (Q2[:, 0] - Q0[:, 0]) * (Q1[:, 1] - Q0[:, 1]))
    sz = 0.4 * (Q0[:, 1] + Q2[:, 1]) + 0.2 * Q1[:, 1]

    tot = a_p + a_s
    tiny = np.abs(tot) < 1e-15
    zc = (a_p * gz + a_s * sz) / np.where(tiny, 1.0, tot)
    a_v = np.where(tiny, 0.0, np.abs(tot))
    zc_v = np.where(tiny, 0.0, zc)
    # the waterplane half-breadth is the LAST cut vertex: v3 on the
    # four-case shape, v3b when the knuckle adds the fifth leg (for the
    # padded c1/c2 rows v3b repeats v3, so the read is uniform)
    b_v = v3b[:, 0] if Wv is not None else v3[:, 0]
    if sel is None:
        return a_v, np.ascontiguousarray(b_v), zc_v
    a_out[sel] = a_v
    b_out[sel] = b_v
    zc_out[sel] = zc_v
    return a_out, b_out, zc_out


def _roll_back_one(v: np.ndarray) -> np.ndarray:
    """`np.roll(v, -1)` for a 1-D array, by slicing. VALUES ARE THE SAME.

    A permutation of the elements, so this is bit-exact by construction and
    not by tolerance — the shoelace sums below see the identical operands in
    the identical order.

    MEASURED 2026-08-20 (cProfile, `evaluate()` on the 12-hull slider
    fixture): `np.roll` cost 38 us per call at 7578 calls per 6 evaluations —
    0.29 s of a 2.72 s profile, 10.7% — because it goes through `normalize_
    axis_tuple`, builds a slice pair per axis and dispatches two assignments.
    On the 3-to-5-vertex polygons `_immersed` hands it, the wrapper is two
    orders of magnitude more expensive than the copy it performs.
    """
    out = np.empty_like(v)
    if v.size:
        out[:-1] = v[1:]
        out[-1] = v[0]
    return out


def _signed_polygon(pts) -> tuple[float, float, float]:
    """Signed area and centroid of a closed polygon (shoelace), open vertices."""
    p = np.asarray(pts, dtype=float)
    y1, z1 = p[:, 0], p[:, 1]
    y2, z2 = _roll_back_one(y1), _roll_back_one(z1)
    cross = y1 * z2 - y2 * z1
    a = 0.5 * float(cross.sum())
    if abs(a) < 1e-15:
        return 0.0, 0.0, 0.0
    return (a, float(((y1 + y2) * cross).sum()) / (6.0 * a),
            float(((z1 + z2) * cross).sum()) / (6.0 * a))


def _polygon(pts) -> tuple[float, float, float]:
    """Area (abs), y-centroid, z-centroid of a closed polygon (shoelace).

    `pts` is an OPEN vertex list, (N, 2); the closing edge back to pts[0] is
    supplied here. It used to take the closed list and loop in Python, which
    was affordable at three points per section and is not at the hundreds the
    bilge fillet needs.
    """
    p = np.asarray(pts, dtype=float)
    y1, z1 = p[:, 0], p[:, 1]
    y2, z2 = _roll_back_one(y1), _roll_back_one(z1)
    cross = y1 * z2 - y2 * z1
    a = 0.5 * float(cross.sum())
    if abs(a) < 1e-12:
        return 0.0, 0.0, 0.0
    cy = float(((y1 + y2) * cross).sum())
    cz = float(((z1 + z2) * cross).sum())
    return abs(a), cy / (6.0 * a), cz / (6.0 * a)


def _halfbreadth_at(pts: np.ndarray, z) -> float | np.ndarray:
    """Half-breadth of a keel->bilge->sheer section polyline at height(s) z.

    z increases monotonically along a section (keel -> bilge -> sheer), so
    this is `np.interp` and not a scan: below the keel it clamps to the keel's
    own half-breadth, which is 0, and above the sheer to the sheer's.
    """
    y = np.interp(z, pts[:, 1], pts[:, 0])
    return float(y) if np.isscalar(z) or np.ndim(z) == 0 else y
