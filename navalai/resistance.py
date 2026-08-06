"""L1 resistance: Michell thin-ship wave resistance + ITTC-57 friction.

Michell integral in the theta form (Tuck 1987 lineage):

    R_w = (4 rho g^2) / (pi U^2) * Int_0^{pi/2} |I(theta)|^2 sec^3(theta) dtheta
    I(theta) = Int_S (dy/dx)(x,z) * exp(k0 sec^2(theta) z)
                                  * exp(i k0 sec(theta) x) dz dx,   k0 = g/U^2

Validity: slender hulls, low-to-moderate Froude; known to overpredict at the
humps by tens of percent (the literature's standing caveat) — which is why
every number leaving this module carries tier='L1' and an uncertainty band.
Friction: ITTC-1957 line with a Watanabe-style form factor.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .geometry import G, Hull
from .holtrop import NU_SEA_15C, RHO_SEA_15C

# KINEMATIC VISCOSITY IS A PROPERTY OF THE WATER, NOT A MODULE CONSTANT.
# `NU_WATER = 1.14e-6` was a FRESH-water figure applied to every call, while
# `total_resistance(..., rho=1025.0)` is a supported argument and `geometry.py`
# says so in as many words ("pass 1025 for salt"). MEASURED on the reference
# hull at its cruise speed: asking for sea water moved rho by 2.5% and left nu
# untouched, so Re was overstated by 4.2% and C_F understated by 0.51% —
# small, but wrong in a fixed direction and invisible, which is the shape of
# every defect in this file's history.
#
# The two anchors are the ITTC-1957 table's 15 C rows. The salt row is
# IMPORTED from `holtrop.NU_SEA_15C` rather than retyped: this module and that
# one would otherwise hold the same physical constant twice, which is the
# defect `limits.py` exists to prevent, one floor down in the stack.
NU_FRESH_15C = 1.14e-6    # [m^2/s] the value this module has always shipped
_NU_ANCHORS = ((1000.0, NU_FRESH_15C), (RHO_SEA_15C, NU_SEA_15C))


def nu_water(rho: float = 1000.0) -> float:
    """Kinematic viscosity [m^2/s] at 15 C for water of density `rho`.

    Linear between the ITTC-1957 fresh and salt rows, and CLAMPED outside
    them: extrapolating a two-point fit to brine or to hot fresh water would
    invent a number the table does not support. At rho = 1000 this returns
    exactly the constant this module always used, so nothing fresh-water moves.
    """
    (r0, n0), (r1, n1) = _NU_ANCHORS
    f = (float(rho) - r0) / (r1 - r0)
    return float(n0 + min(max(f, 0.0), 1.0) * (n1 - n0))


NU_WATER = NU_FRESH_15C  # kept as the fresh-water name; prefer nu_water(rho)


# MICHELL'S VALIDITY ENVELOPE, ENFORCED.
# The thin-ship integral assumes a slender hull at low-to-moderate Froude
# number with no dynamic lift. MEASURED: a "3 t, 6 m, 25 kn tender" mission was
# evaluated at **Fn 1.09 / Fn_vol 3.42** -- deep planing -- and returned
# Rw 498 N against Rf 3832 N, i.e. "friction-dominated at 25 knots", with a
# PASS on every requirement. There is no planing lift, no dynamic trim, no
# spray and no appendage drag in this model; at that speed the answer is not
# approximate, it is about a different physical regime.
#
# 0.45 is the conventional upper limit for displacement/thin-ship methods
# (transom immersion and dynamic effects take over above it). Above the bar the
# result is still returned -- refusing outright would hide the number from a
# designer who wants to see it -- but `valid` is False and the tier reads
# L1-INVALID, so nothing downstream can badge it as a validated L1 quantity.
# The honest fix beyond this is a Savitsky planing model; that is gap B7's
# second half and is not yet built.
FN_MICHELL_MAX = 0.45


# THE GRID THE MICHELL INTEGRAL IS SHIPPED ON, AND THE ONE IT WAS CONVERGED ON.
#
# Gap E8: `total_resistance` defaulted to nz=14 over whatever station count the
# caller's `Hull` happened to carry (41, the geometry default), while the only
# convergence evidence in the repository lived in `benchmarks/wigley.py`, which
# builds its OWN 121x25 grid and never exercises the shipped one. So the
# convergence test and the production path had no grid in common.
#
# RE-MEASURED 2026-08-07 on the reference hull (`tests/test_phase0.mid_params`)
# at its 5 kn cruise, floated to the 6 t mission displacement — R_w [N] against
# (n_stations x nz):
#
#       nz:      14        28        45        65
#     41      425.770   429.768   431.131   431.617
#     81      448.127   449.453   449.636   449.778
#    161      454.481   455.334   455.609   455.659
#    241      455.589   456.502   456.685   456.857
#    321      455.982   456.912   457.125   457.246
#
# The shipped 41x14 corner is 425.8 N against 457.2 N at 321x65: **-6.9%**, and
# the register's -6.6% was measured on a slightly different floated state. Note
# WHICH AXIS: the z-grid is worth -1.3% and the STATION COUNT -6.2%, so a
# convergence study that refines z alone (the one this module's docstring
# pointed at) would have reported the integral converged.
#
# 161x28 is the production grid: -0.42% from the corner of the table, 7.1 ms.
# The station count is the expensive axis, and `offsets_grid` is a Python loop
# over stations x z, so this is a real cost — measured against the 50 ms
# Gate 1 latency bar in `tests/test_phase1.py`, not assumed to be free.
PRODUCTION_GRID = {"n_stations": 161, "nz": 28}
CONVERGED_GRID = {"n_stations": 321, "nz": 65}
GRID_CONVERGED_TO = 0.005   # |production - converged| / converged, MEASURED


# WATANABE'S FORM FACTOR, AND THE TWO WAYS IT LEAVES ITS SUPPORT.
# The regression is calibrated on L/B 6-8; `grammar.py` allows 2.2. Outside
# that band the formula still evaluates, and it evaluates LARGE: k goes as
# (L/B)^-2, so a beamy 3 m x 10 m hull gets four times the form drag of a
# slender one from the geometry term alone.
FORM_FACTOR_BAND = (0.0, 0.45)
WATANABE_L_OVER_B_BAND = (6.0, 8.0)
# One sigma on k INSIDE the band. Declared, not sourced — the same convention
# and the same honesty as `holtrop.SIGMA_DECLARED`: there is no published
# per-prediction standard error for this estimator that could be transcribed,
# and inventing one and attributing it to Watanabe would be a fabrication.
# It is superseded by a MEASURED spread the moment the clamp or the envelope
# bites (see `form_factor`), which is the case this constant is not asked to
# cover.
FORM_FACTOR_SIGMA_DECLARED = 0.05


@dataclass(frozen=True)
class FormFactor:
    """Watanabe's 1+k, the raw estimate behind it, and why they differ.

    Gap E7: the clamp was applied inside a `np.clip` and the fact that it had
    bitten was thrown away with the raw value. MEASURED over 400 L0-feasible
    grammar hulls floated to the 6 t mission displacement: **27.3%** of them
    return a raw k outside [0, 0.45] and are silently handed 0.4500, with a
    maximum raw k of **2.09** — i.e. for a quarter of the design space the
    friction model reports a number the estimator did not produce, with the
    same comfortable 10% band as a hull sitting mid-range.
    """

    k: float                    # the value actually used
    k_raw: float                # Watanabe's own value, unclamped
    clamped: bool
    sigma_k: float              # one sigma on k — MEASURED when clamped
    envelope_violations: tuple[str, ...] = ()

    @property
    def in_support(self) -> bool:
        return not self.clamped and not self.envelope_violations


@dataclass(frozen=True)
class ResistanceResult:
    speed: float      # m/s
    fn: float
    rw: float         # wave resistance [N]
    rf: float         # frictional (with form factor) [N]
    total: float      # N
    cw: float         # wave resistance coeff on 0.5 rho S U^2
    cf: float
    uncertainty: float  # one-sigma on total [N] — honest L1 band (~25%)
    valid: bool = True          # False above FN_MICHELL_MAX
    regime: str = "displacement"
    # The form factor is REPORTED, not just consumed: `k` alone cannot tell a
    # reader whether it came out of the regression or off the clamp.
    form: FormFactor | None = None
    grid: dict = field(default_factory=dict)   # the Michell grid this ran on


def michell_rw(xs: np.ndarray, zs: np.ndarray, Y: np.ndarray, speed: float,
               rho: float = 1000.0, n_theta: int = 220) -> float:
    """Wave resistance from a half-breadth grid Y[x, z] below the waterline."""
    if speed <= 0.05:
        return 0.0
    k0 = G / speed**2
    dydx = np.gradient(Y, xs, axis=0)
    # theta grid dense near pi/2 (integrand peaky), via substitution theta = pi/2 * s^0.7
    s = np.linspace(1e-4, 1.0, n_theta) ** 0.7
    thetas = 0.5 * math.pi * s * 0.998
    sec = 1.0 / np.cos(thetas)
    vals = np.empty(n_theta)
    for i, (th, sc) in enumerate(zip(thetas, sec)):
        # zs must be <= 0 (below the actual free surface); clamp defensively
        depth = np.exp(np.minimum(k0 * sc**2 * zs, 0.0))[None, :]
        phase = k0 * sc * xs                               # (nx,)
        gz = (dydx * depth)                                # (nx, nz)
        fx = np.trapezoid(gz, zs, axis=1)                  # integrate z
        re = np.trapezoid(fx * np.cos(phase), xs)
        im = np.trapezoid(fx * np.sin(phase), xs)
        vals[i] = (re**2 + im**2) * sc**3
    integral = np.trapezoid(vals, thetas)
    return float(4.0 * rho * G**2 / (math.pi * speed**2) * integral)


def ittc57_cf(speed: float, lwl: float, nu: float | None = None,
              rho: float = 1000.0) -> float:
    """ITTC-1957 friction line. `nu` defaults to the water `rho` describes."""
    nu = nu_water(rho) if nu is None else nu
    re = max(speed * lwl / nu, 1e4)
    return 0.075 / (math.log10(re) - 2.0) ** 2


def form_factor(cb: float, lwl: float, beam: float, t: float) -> FormFactor:
    """Watanabe's 1+k estimate, with the clamp and the envelope REPORTED.

    `cb`, `lwl`, `beam` and `t` must describe ONE state. Gap E7's other half:
    this was called with the FLOATED cb and the DESIGN beam and draft, and on
    the reference hull the design draft is 0.55 m against a floated 0.3737 m —
    a 47% error on an argument that enters as sqrt(B/T).

    Returns a `FormFactor`, not a float, because a bare 0.4500 cannot say
    whether Watanabe produced it or the clamp did.
    """
    # A STATE THAT CANNOT BE EVALUATED IS FATAL, NOT A DEFAULT. With t = 0 the
    # sqrt(B/T) term goes to infinity and k collapses to -0.095, which the old
    # `np.clip(k, 0.0, 0.45)` turned into a serene 0.0 — the most optimistic
    # form factor available, returned for a hull with no draft at all. That is
    # the `${VAR:-0}` pattern (an unreadable metric scored as perfect) which
    # has already cost this project a run.
    for name, v in (("cb", cb), ("lwl", lwl), ("beam", beam), ("t", t)):
        if not (isinstance(v, (int, float)) and math.isfinite(v) and v > 0.0):
            raise ValueError(
                f"form factor: {name} = {v!r} is not a positive finite length "
                f"or coefficient, so Watanabe's estimate has no value here. "
                f"Refused rather than clamped: k collapses to -0.095 for a "
                f"degenerate state and a clamp would report that as 0.000, "
                f"the best form factor there is.")
    lo, hi = FORM_FACTOR_BAND
    k_raw = -0.095 + 25.6 * cb / ((lwl / beam) ** 2 * math.sqrt(beam / t))
    k = float(min(max(k_raw, lo), hi))
    clamped = not (lo <= k_raw <= hi)
    viol: list[str] = []
    lb = lwl / beam
    if not (WATANABE_L_OVER_B_BAND[0] <= lb <= WATANABE_L_OVER_B_BAND[1]):
        viol.append(
            f"L/B {lb:.2f} outside Watanabe's calibration band "
            f"{list(WATANABE_L_OVER_B_BAND)} — the estimate carries (L/B)^-2 "
            f"and is an extrapolation here")
    if clamped:
        viol.append(
            f"raw k {k_raw:.3f} outside {list(FORM_FACTOR_BAND)}; the clamp "
            f"supplied {k:.3f}, so this is not the estimator's answer")
    # When the clamp bites, the distance to the raw value is a MEASURED lower
    # bound on how wrong k may be, and it beats any declared percentage.
    sigma_k = max(abs(k_raw - k), FORM_FACTOR_SIGMA_DECLARED)
    return FormFactor(k=k, k_raw=float(k_raw), clamped=clamped,
                      sigma_k=float(sigma_k),
                      envelope_violations=tuple(viol))


def total_resistance(hull: Hull, speed: float, wetted: float, cb: float,
                     rho: float = 1000.0, wl: float = 0.0,
                     nz: int | None = None, n_stations: int | None = None,
                     beam_wl: float | None = None,
                     draft: float | None = None) -> ResistanceResult:
    """Michell wave resistance + ITTC-57 friction on the PRODUCTION grid.

    `beam_wl` and `draft` are the FLOATED waterline beam and draft — pass them
    from the same `HydroState` that produced `cb` and `wetted`. Omitting them
    falls back to the design beam and design draft, which is the inconsistent
    state gap E7 measured; the fallback exists so a caller holding only a hull
    still gets an answer, and it is the caller's job not to be `evaluate()`.
    """
    nz = int(PRODUCTION_GRID["nz"] if nz is None else nz)
    ns = int(PRODUCTION_GRID["n_stations"] if n_stations is None
             else n_stations)
    # Refine the STATION axis for the integral only. The hull handed in carries
    # whatever station count its caller wanted for hydrostatics (41 by
    # default); the Michell integral needs 161 to be within 0.5% of converged,
    # and rebuilding is ~1 ms against the 4 ms integral.
    grid_hull = hull if hull.n_stations == ns else Hull(hull.params,
                                                        n_stations=ns)
    xs, zs, Y = grid_hull.offsets_grid(nz=nz, wl=wl)
    # Michell frame: free surface at z=0 — shift the grid by the floated WL
    rw = michell_rw(xs, zs - wl, Y, speed, rho)
    lwl = float(hull.x[-1])
    cf = ittc57_cf(speed, lwl, rho=rho)
    beam = (2.0 * float(hull.y_chine.max()) if beam_wl is None
            else float(beam_wl))
    t = (-float(hull.z_keel.min()) if draft is None else float(draft))
    form = form_factor(cb, lwl, beam, t)
    q = 0.5 * rho * wetted * speed**2
    rf = (1.0 + form.k) * cf * q
    total = rw + rf
    fn = speed / math.sqrt(G * lwl)
    cw = rw / max(q, 1e-9)
    # Honest L1 band: Michell hump overprediction (declared, the literature's
    # standing caveat) plus a friction term that now PROPAGATES the form
    # factor's own uncertainty instead of declaring a flat 10% over a k that
    # may have come off the clamp. sigma_rf = q*cf*sigma_k in quadrature with
    # the friction-line scatter.
    sigma_rf = rf * math.sqrt((form.sigma_k / (1.0 + form.k)) ** 2 + 0.10**2)
    sigma = 0.25 * rw + sigma_rf
    valid = fn <= FN_MICHELL_MAX
    if not valid:
        # The band is meaningless outside the model's regime; say so with a
        # sigma the size of the answer rather than a comfortable 25%.
        sigma = max(sigma, total)
    return ResistanceResult(speed, fn, rw, rf, total, cw, cf, sigma,
                            valid=valid,
                            regime="displacement" if valid else "planing",
                            form=form,
                            grid={"n_stations": ns, "nz": nz,
                                  "converged_to": GRID_CONVERGED_TO})
