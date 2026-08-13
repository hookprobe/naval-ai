"""L1 resistance: Michell thin-ship wave resistance + ITTC-57 friction.

Michell integral in the theta form (Tuck 1987 lineage):

    R_w = (4 rho g^2) / (pi U^2) * Int_0^{pi/2} |I(theta)|^2 sec^3(theta) dtheta
    I(theta) = Int_S (dy/dx)(x,z) * exp(k0 sec^2(theta) z)
                                  * exp(i k0 sec(theta) x) dz dx,   k0 = g/U^2

Validity: slender hulls, low-to-moderate Froude; known to overpredict at the
humps by tens of percent (the literature's standing caveat) — which is why
every number leaving this module carries tier='L1' and an uncertainty band.
Friction: ITTC-1957 line with a Watanabe-style form factor.

MULTI-HULL: `michell_rw(..., separation=s)` puts two identical demihulls at
y = +-s/2 and returns the wave resistance of the pair, including their mutual
wave interference. It is a pure addition — `separation=None` is the monohull
and is bit-identical to what this module computed before it existed — and
nothing in the genome, the grammar or `total_resistance` has been wired to it
yet. See the derivation and the measured theta-resolution envelope above
`catamaran_interference`.
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


# ---------------------------------------------------------------------------
# MULTI-HULL WAVE INTERFERENCE — two demihulls, one factor, no genome change
# ---------------------------------------------------------------------------
#
# THE LAMBDA FORM AND THE THETA FORM ARE THE SAME INTEGRAL. Stated here because
# it is what makes the interference factor below safe to write: the literature
# gives Michell either as
#
#     R_w = (4 rho g^2 / (pi U^2)) Int_0^{pi/2} |I(th)|^2 sec^3(th) dth
# or  R_w = (4 rho g^2 / (pi U^2)) Int_1^{inf} |I|^2 lam^2/sqrt(lam^2-1) dlam
#
# (|I|^2 is written (Re I)^2 + (Im I)^2 in some references — the `re**2 + im**2`
# of the loop below, one complex amplitude, not two independent ones.)
#
# and with lam = sec(th): dlam = sec th tan th dth = lam sqrt(lam^2 - 1) dth, so
# sec^3(th) dth = lam^3 dlam / (lam sqrt(lam^2 - 1)) = lam^2/sqrt(lam^2-1) dlam.
# Identical, term for term. This module ships the theta form and `michell_rw`
# implements it verbatim (`vals[i] = (re**2 + im**2) * sc**3`, prefactor
# `4 rho G^2 / (pi U^2)`), so a result derived in either form transfers.
#
# THE DERIVATION, done here rather than cited, because the transverse
# wavenumber is the one place this can go silently wrong:
#
#   A free wave radiated at angle theta from the track has wave vector
#   (k_x, k_y) = (k0 sec th, k0 sec^2 th sin th) with k = |k| = k0 sec^2 th.
#   Both components are already IN this file and can be read off the code:
#   the longitudinal one is the `phase = k0 * sc * xs` factor, and the full
#   magnitude is the `k0 * sc**2 * zs` depth decay (a free wave decays as
#   e^{k z} with the SAME k that sets its length). k_y = k sin th then follows,
#   which is `k0 sec^2 th sin th` — the brief's expression, confirmed.
#
#   Thin-ship theory is LINEAR in the hull surface, so the Kochin amplitude of
#   a source sheet translated to y = y0 picks up exactly e^{i k_y y0}. Two
#   identical demihulls at y = +-s/2 therefore give
#
#       I_cat = I_demi (e^{i k_y s/2} + e^{-i k_y s/2}) = 2 I_demi cos(k_y s/2)
#       |I_cat|^2 = 4 |I_demi|^2 cos^2(k_y s / 2)
#
#   so the whole change is one multiplicative factor under the theta integral.
#
# ONE CORRECTION TO THE BRIEF, and it does not change the formula: the factor
# 4 cos^2(u) averages to **2** over u, not to 1. The brief's conclusion
# (R_w(cat) -> 2 R_w(demi) as s -> inf) is right; the intermediate sentence
# "the interference factor averages to 1" is not, and 4 cos^2 is what is
# implemented.
CATAMARAN_INTERFERENCE_AT_INFINITY = 2.0   # <4 cos^2(u)>_u, i.e. two demihulls

# THE SHIPPED THETA GRID, AND THE ONE THE INTERFERENCE FACTOR NEEDS.
#
# `michell_rw`'s theta grid clusters toward pi/2 (`s**0.7`), which is right for
# |I|^2 sec^3 and WRONG for the interference factor: the interference phase is
# phi(th) = k0 s sec^2 th sin th, so dphi/dth = k0 s (1 + sin^2 th)/cos^3 th
# grows as sec^3 while the node density grows far more slowly. The oscillation
# is therefore worst-resolved exactly where the grid is coarsest.
#
# MEASURED 2026-08-13 on the Wigley demihull (L = 10 m, 121 x 25 offsets),
# worst |error| over 25-91 separations per band at Fn 0.20 / 0.30 / 0.40 /
# 0.45, against a converged reference (n_theta 40000 for the fixed-n_theta
# columns, 60000 for the rule column; the reference itself moves 3e-5% between
# 40000 and 160000, so it is not the thing being measured):
#
#     s / Lwl      n_theta 220   440     880     rule-compliant n_theta
#     0.1 - 1.0        0.62%    0.23%   0.089%      880  ->  0.058%
#     1.0 - 2.0        1.21%    0.39%   0.148%     1760  ->  0.061%
#     2.0 - 5.0          -        -       -        4400  ->  0.021%
#     5.0 - 10.0         -        -       -        8800  ->  0.026%
#    10.0 - 20.0         -        -       -       17600  ->  0.018%
#
# So the shipped 220 nodes carry up to 1.2% of pure quadrature noise on the
# interference term at separations an optimiser would sweep — noise that CHANGES
# SIGN with separation, which is precisely the shape of a spurious optimum. The
# rule `n_theta >= 880 * max(1, separation / Lwl)` holds every band above to
# **0.061%**, and it is ENFORCED rather than documented: a separation the grid
# cannot resolve is REFUSED, never returned (the `${VAR:-0}` defect class, see
# docs/LESSONS.md — an unmeasurable metric is fatal, not a default).
N_THETA_MONOHULL = 220
N_THETA_PER_HULL_LENGTH_OF_SEPARATION = 880
CATAMARAN_THETA_QUADRATURE_ERROR = 0.00061   # MEASURED worst, in-envelope

# THE ASYMPTOTIC RESIDUAL, MEASURED AND EXPLAINED RATHER THAN TOLERATED.
#
# R_w(cat, s -> inf) / (2 R_w(demi)) does NOT reach 1 on the shipped grid; it
# sits ~0.25-0.46% low, and the deficit does not shrink with n_theta. The cause
# is the grid's LOWER END: `np.linspace(1e-4, 1.0, n)**0.7` starts at
# theta_0 = 0.5 pi * 0.998 * (1e-4)^0.7 = 2.484e-3 rad for EVERY n_theta, so
# the trapezoid omits [0, theta_0] in both cases — but the catamaran omits it
# weighted by ~4 (phi(theta_0) = k0 s theta_0 is still << pi at any practical
# separation) where the monohull-doubled reference omits it weighted by 2.
#
# PREDICTED deficit = (4 - 2) * vals(0) * theta_0 / (2 * Int vals dtheta):
#
#     Fn      predicted    measured (s/Lwl = 20, n_theta 17600)
#     0.20     -0.4805%     -0.3427%   (-0.4811% at s/Lwl = 5)
#     0.30     -0.2540%     -0.2440%
#     0.40     -0.3300%     -0.3229%
#
# The prediction is the s -> inf limit of the sliver; the measured value walks
# back toward zero once phi(theta_0) = k0 s theta_0 approaches pi, which for
# Fn 0.20 at s/Lwl = 20 is 1.24 rad — hence the two Fn 0.20 entries. The
# mechanism is IDENTIFIED, so the bar in `tests/test_phase1.py` is set AT the
# worst measured residual and not at a round number chosen to swallow it.
# MEASURED worst over Fn 0.20-0.45 x s/Lwl 5/10/20: 0.4811%, at Fn 0.20.
CATAMARAN_ASYMPTOTIC_RESIDUAL = 0.0049


def _theta_grid(n_theta: int) -> tuple[np.ndarray, np.ndarray]:
    """The shipped theta sweep and its secants. Dense near pi/2 (integrand
    peaky), via the substitution theta = pi/2 * s^0.7."""
    s = np.linspace(1e-4, 1.0, n_theta) ** 0.7
    thetas = 0.5 * math.pi * s * 0.998
    return thetas, 1.0 / np.cos(thetas)


def _free_wave_vals(xs: np.ndarray, zs: np.ndarray, Y: np.ndarray,
                    speed: float, thetas: np.ndarray,
                    sec: np.ndarray) -> np.ndarray:
    """|I(theta)|^2 sec^3(theta) for ONE centreplane — the expensive part.

    Factored out of `michell_rw` verbatim so that a separation sweep pays the
    x-z double integral ONCE instead of once per separation: the interference
    factor is the only thing that depends on the separation, and it is a
    multiply. Nothing here is reordered — the monohull result is bit-identical
    (`tests/test_phase1.py::test_michell_monohull_is_bit_identical_...`).
    """
    k0 = G / speed**2
    dydx = np.gradient(Y, xs, axis=0)
    vals = np.empty(len(thetas))
    for i, (th, sc) in enumerate(zip(thetas, sec)):
        # zs must be <= 0 (below the actual free surface); clamp defensively
        depth = np.exp(np.minimum(k0 * sc**2 * zs, 0.0))[None, :]
        phase = k0 * sc * xs                               # (nx,)
        gz = (dydx * depth)                                # (nx, nz)
        fx = np.trapezoid(gz, zs, axis=1)                  # integrate z
        re = np.trapezoid(fx * np.cos(phase), xs)
        im = np.trapezoid(fx * np.sin(phase), xs)
        vals[i] = (re**2 + im**2) * sc**3
    return vals


def catamaran_interference(k0: float, thetas: np.ndarray,
                           separation: float) -> np.ndarray:
    """|I_cat|^2 / |I_demi|^2 for two identical demihulls at y = +- s/2.

    THE ONE HOME OF THE INTERFERENCE FACTOR. `4 cos^2(k_y s / 2)` with
    k_y = k0 sec^2(theta) sin(theta); see the derivation above the constants.
    Ranges over [0, 4]: 0 is total destructive cancellation of the free-wave
    system at that radiation angle, 4 is the two demihulls radiating in phase,
    and the theta average is 2 — two independent demihulls.
    """
    ky = k0 * (1.0 / np.cos(thetas)) ** 2 * np.sin(thetas)
    return 4.0 * np.cos(0.5 * ky * float(separation)) ** 2


def _separation_or_raise(Y: np.ndarray, separation) -> float:
    """The separation as a float, or a refusal naming what is wrong with it."""
    if not (isinstance(separation, (int, float, np.floating))
            and math.isfinite(separation) and separation > 0.0):
        raise ValueError(
            f"michell_rw: separation = {separation!r} is not a positive finite "
            f"length. A demihull spacing of zero, negative or NaN is not a "
            f"degenerate boat, it is an unspecified one — refused rather than "
            f"quietly treated as a monohull, which would report a two-hull "
            f"vessel as a one-hull one.")
    s = float(separation)
    beam = 2.0 * float(np.max(Y))
    if s <= beam:
        raise ValueError(
            f"michell_rw: separation {s:.4f} m is not greater than the "
            f"demihull beam {beam:.4f} m, so the two demihull surfaces at "
            f"y = +-{s / 2:.4f} m INTERSECT. Thin-ship theory is linear in the "
            f"hull surface and will happily integrate that and return a "
            f"number; it is not a hull.")
    return s


def n_theta_for_separation(lwl: float, separation: float) -> int:
    """The theta-sweep size the interference factor needs at this separation.

    `N_THETA_PER_HULL_LENGTH_OF_SEPARATION * max(1, s/Lwl)`, MEASURED — see the
    table above that constant. Public because a caller sweeping separations
    must pin ONE grid across the sweep (see `michell_rw_separation_sweep`).
    """
    return int(math.ceil(N_THETA_PER_HULL_LENGTH_OF_SEPARATION
                         * max(1.0, float(separation) / float(lwl))))


def _require_theta_resolution(lwl: float, separation: float,
                              n_theta: int) -> None:
    need = n_theta_for_separation(lwl, separation)
    if n_theta < need:
        raise ValueError(
            f"michell_rw: n_theta = {n_theta} cannot resolve the interference "
            f"oscillation at separation {separation:.4f} m on a {lwl:.4f} m "
            f"waterline; {need} nodes are required "
            f"(N_THETA_PER_HULL_LENGTH_OF_SEPARATION * max(1, s/Lwl)). "
            f"MEASURED at 220 nodes over Fn 0.20-0.45: up to 1.2% of "
            f"quadrature error that CHANGES SIGN with separation, which an "
            f"optimiser reads as a real optimum. Refused rather than returned.")


def michell_rw(xs: np.ndarray, zs: np.ndarray, Y: np.ndarray, speed: float,
               rho: float = 1000.0, n_theta: int | None = None,
               separation: float | None = None) -> float:
    """Wave resistance from a half-breadth grid Y[x, z] below the waterline.

    `separation` is the transverse spacing [m] between the two demihull
    CENTREPLANES of a catamaran, and `Y` is then ONE demihull's half-breadth
    grid; the return is the wave resistance of the WHOLE vessel (both
    demihulls). `separation=None` is a monohull and is this function's
    behaviour before multi-hull support existed, bit for bit.

    `n_theta=None` resolves to `N_THETA_MONOHULL` (220, unchanged) for a
    monohull and to the MEASURED rule for a catamaran — see
    `N_THETA_PER_HULL_LENGTH_OF_SEPARATION`. An explicit `n_theta` below that
    rule is REFUSED for a catamaran, because the interference term's quadrature
    error changes sign with separation and would be read as physics.

    WHY THE PHYSICS GETS BETTER, NOT WORSE, WHEN THE ANSWER IS A CATAMARAN:
    Michell's derivation assumes beam << length. MEASURED 2026-08-13 at commit
    c7b7c4b over 4000 grammar samples (`grammar.sample(4000, default_rng(0))`,
    all 4000 L0-feasible; `grammar.L_OVER_B_BAND` is (2.2, 8.5) so the whole
    admissible band is beamy): median L/B **3.96**, 5th-95th 2.39-7.44, and
    `tests/test_phase0.mid_params` — the hull most of this repository's
    measurements are taken on — is L/B **3.13**. Every one of those violates
    the theory's own slenderness assumption; the model has been running outside
    its envelope on the monohull path all along. Splitting the same
    displacement into two demihulls at fixed length roughly halves each
    demihull's beam, so the reference hull's 3.13 becomes ~6.3 and a genuinely
    slender demihull (L/B 15, as catamaran practice runs) lands squarely in the
    regime Michell derived. The interference factor is exact within thin-ship
    theory, and the theory itself is being asked a fairer question.
    """
    # The separation is validated BEFORE anything is integrated: a NaN spacing
    # must not first be turned into a theta-grid size, and a refusal must not
    # cost the x-z double integral it is refusing to use.
    if separation is not None:
        lwl = float(xs[-1] - xs[0])
        sep = _separation_or_raise(Y, separation)
        n_theta = (n_theta_for_separation(lwl, sep) if n_theta is None
                   else int(n_theta))
        _require_theta_resolution(lwl, sep, n_theta)
    else:
        n_theta = N_THETA_MONOHULL if n_theta is None else int(n_theta)
    if speed <= 0.05:
        return 0.0
    thetas, sec = _theta_grid(n_theta)
    vals = _free_wave_vals(xs, zs, Y, speed, thetas, sec)
    if separation is not None:
        vals = vals * catamaran_interference(G / speed**2, thetas, sep)
    integral = np.trapezoid(vals, thetas)
    return float(4.0 * rho * G**2 / (math.pi * speed**2) * integral)


def michell_rw_separation_sweep(xs: np.ndarray, zs: np.ndarray, Y: np.ndarray,
                                speed: float, separations: np.ndarray,
                                rho: float = 1000.0,
                                n_theta: int | None = None) -> np.ndarray:
    """`michell_rw` over many separations, paying the x-z integral ONCE.

    The demihull free-wave spectrum |I(theta)|^2 sec^3(theta) does not depend on
    the separation, so a sweep of N separations costs one spectrum plus N
    multiplies rather than N spectra. MEASURED on the Wigley demihull at
    n_theta = 880: the spectrum is 14.4 ms and each additional separation is
    ~0.05 ms, so a 60-point sweep is 17 ms instead of 0.9 s.

    `n_theta` is resolved ONCE, from the LARGEST separation asked for, so every
    point of the sweep is on one grid and on the right side of the resolution
    rule — a sweep whose members sat on different grids would compare
    quadrature errors as if they were interference.
    """
    seps = np.asarray(separations, dtype=float)
    if seps.ndim != 1 or seps.size == 0:
        raise ValueError("michell_rw_separation_sweep: `separations` must be a "
                         "non-empty 1-D array of demihull spacings [m]")
    lwl = float(xs[-1] - xs[0])
    checked = [_separation_or_raise(Y, s) for s in seps]
    n_theta = (n_theta_for_separation(lwl, max(checked)) if n_theta is None
               else int(n_theta))
    for s in checked:
        _require_theta_resolution(lwl, s, n_theta)
    if speed <= 0.05:
        return np.zeros_like(seps)
    thetas, sec = _theta_grid(n_theta)
    vals = _free_wave_vals(xs, zs, Y, speed, thetas, sec)
    k0 = G / speed**2
    pre = 4.0 * rho * G**2 / (math.pi * speed**2)
    out = np.empty_like(seps)
    for i, s in enumerate(checked):
        out[i] = pre * np.trapezoid(
            vals * catamaran_interference(k0, thetas, s), thetas)
    return out


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
