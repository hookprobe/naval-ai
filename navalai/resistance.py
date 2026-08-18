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
and is bit-identical to what this module computed before it existed. See the
derivation and the measured theta-resolution envelope above
`catamaran_interference`.

`total_resistance(..., separation=s)` NOW CARRIES IT INTO THE PRODUCTION PATH.
Until 2026-08-13 it did not: this module implemented the interference term,
`navalai/experiments.py` verified its phase convention three ways, and
`total_resistance` called `michell_rw` with no separation at all — so every
catamaran this project ever evaluated was scored as ONE ISOLATED DEMIHULL.
MEASURED worth (experiments.py, Wigley demihull): the interference ratio
bottoms at 0.7483 at s/Lwl 0.300 at Fn 0.25 (-25.2% against two independent
hulls) and the whole 0.20-0.50 band is CONSTRUCTIVE above Fn 0.35, peaking at
+59.7% at Fn 0.40 / s/Lwl 0.200. There is no single optimum s/Lwl — it moves
with Fn — so it is a real optimisation variable and choosing it badly costs up
to 60% of the wave term.

WHAT IS STILL NOT MODELLED, SAID HERE RATHER THAN LEFT TO BE FOUND. Insel &
Molland decompose a catamaran's resistance into a WAVE interference factor and
a VISCOUS FORM interference factor. This module now carries the first exactly
(within thin-ship theory) and does NOT carry the second: the friction term is
Watanabe's form factor for ONE demihull applied to the vessel's total wetted
area, i.e. the demihulls are assumed not to change each other's boundary layer
or form drag. That assumption is not measured here and there is no experimental
anchor for a catamaran anywhere in this repository — Insel & Molland and the
Southampton series are CITED below, never transcribed. Nothing multiplies the
friction by a stand-in factor, because a fabricated 1.1 dressed as physics is
worse than a stated omission.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .geometry import G, Hull
from .constants import NU_SEA_HOLTROP, RHO_FRESH, RHO_SEA_HOLTROP
from .limits import RE_TRANSITION_BAND as _RE_BAND

# KINEMATIC VISCOSITY IS A PROPERTY OF THE WATER, NOT A MODULE CONSTANT.
# `NU_WATER = 1.14e-6` was a FRESH-water figure applied to every call, while
# `total_resistance(..., rho=1025.0)` is a supported argument and `geometry.py`
# says so in as many words ("pass 1025 for salt"). MEASURED on the reference
# hull at its cruise speed: asking for sea water moved rho by 2.5% and left nu
# untouched, so Re was overstated by 4.2% and C_F understated by 0.51% —
# small, but wrong in a fixed direction and invisible, which is the shape of
# every defect in this file's history.
#
# The two anchors are named for what they ARE (C-11, forensics: the old
# alias let `NU_SEA_15C` mean two different numbers in two modules). The
# salt row is the HOLTROP convention — the ITTC 15 C value rounded to four
# figures (1.1883e-6, see constants.py) — imported under its true name,
# NOT the genuine ITTC table row (1.18831e-6, similitude's convention).
# Same physical constant, one declaration, honest label.
from .constants import \
    NU_FRESH_15C_ROUNDED as NU_FRESH_15C  # see constants.py for the 1.13902e-6 note
_NU_ANCHORS = ((RHO_FRESH, NU_FRESH_15C), (RHO_SEA_HOLTROP, NU_SEA_HOLTROP))


def nu_water(rho: float = RHO_FRESH) -> float:
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


# ---------------------------------------------------------------------------
# AXIS 3 — THE FLOW REGIME. DERIVED FROM SIZE AND SPEED, NEVER DECLARED.
# ---------------------------------------------------------------------------
#
# `FN_MICHELL_MAX` above bounds the WAVE half. The FRICTION half had no bound
# at all, and it needs one for exactly the reason the Froude bound exists:
# ITTC-1957 is a fully-turbulent model-ship correlation line, and below the
# transition Reynolds number the boundary layer is not fully turbulent, so the
# line is being extrapolated out of the flow it describes.
#
# WHY THIS MATTERS AND WHY IT IS NOT HYPOTHETICAL. Froude scales as 1/sqrt(L),
# so a SMALL hull is a FAST hull. MEASURED with `nu_water(1000.0)`:
#
#     L = 1.0 m at 2 kn -> Fn 0.329   INSIDE Michell    Re 9.03e5
#     L = 1.0 m at 3 kn -> Fn 0.493   outside Michell   Re 1.35e6
#     L = 1.0 m at 4 kn -> Fn 0.657   outside Michell   Re 1.81e6
#     L = 12  m at 6 kn -> Fn 0.285   INSIDE Michell    Re 3.25e7
#
# A 1 m drone crosses FN_MICHELL_MAX at about 2.7 knots, and at Re ~9e5 it is
# in the laminar-turbulent transition where ITTC-57 is unsound EVEN BELOW that
# speed. There is no transitional correction in this module and none is being
# invented; the honest move is to say which side of the transition the flow is
# on and let the existing L1-INVALID machinery carry it.
#
# THE TWO NUMBERS ARE DECLARED, NOT TRANSCRIBED, and this is said out loud with
# the same convention as `FORM_FACTOR_SIGMA_DECLARED` above. They are the
# classical flat-plate transition band from boundary-layer theory (Schlichting:
# transition onset near Re_x = 5e5, fully turbulent by a few times 1e6); no
# ITTC document in this repository states a lower validity bound for the 1957
# line, so attributing one to ITTC would be a fabrication. What is NOT declared
# is the consequence, and that is the part that matters:
#
#   Re <  RE_TRANSITION_ONSET     the flow is LAMINAR or transitional and the
#                                 friction line is refused: `valid` False,
#                                 badge L1-INVALID, sigma the size of the
#                                 answer. Same machinery as Fn > 0.45.
#   Re <  RE_FULLY_TURBULENT      the line is an EXTRAPOLATION below the flow
#                                 it correlates. REPORTED in
#                                 `FlowRegime.envelope`, and NOT a refusal —
#                                 see the note below for why that decision was
#                                 not taken tonight.
#
# THE OPEN GAP, STATED RATHER THAN BURIED. The transitional band 5e5..5e6 IS
# reachable inside today's design box: `grammar.PARAMS["LWL"].low` is 4.0 m and
# `mission.FIELD_RANGES["cruise_speed_kn"]` starts at 1.0 kn, which is
# Re = 1.81e6. Turning that band into a refusal would move the friction number
# on hulls the product does run, and that is a MEASURED decision about a bar,
# not a drive-by change — so it is a receipt today and recorded as owed. The
# LAMINAR bound below it is provably unreachable in the current box (the
# smallest, slowest admissible hull is 3.6x above it), which is why it can be
# added without touching a single existing result — and it is added anyway,
# because the uncrewed/small-craft axis is what will reach it first.
# C-31: ONE envelope, one home. These used to be a SECOND copy of the
# transition band with a DIFFERENT ceiling (3e6 here, 5e6 in limits.py —
# both classical flat-plate values, neither citable, and two modules
# answering "is ITTC-57 inside its regime?" with different numbers).
# Unified on limits.RE_TRANSITION_BAND's conservative 5e6 ceiling: the
# refusal is keyed on the ONSET (unchanged), so no verdict moved — the
# extrapolation CAVEAT now honestly covers Re in [3e6, 5e6) too. The
# POLICY split is deliberate and declared: `limits.friction_line_validity`
# answers the strict designer question (inside the band = not valid),
# while `flow_regime` is the wired evaluation policy (refuse below onset,
# report-with-receipt inside the band); both read this one band.
RE_TRANSITION_ONSET = _RE_BAND[0]
RE_FULLY_TURBULENT = _RE_BAND[1]


@dataclass(frozen=True)
class FlowRegime:
    """WHICH PHYSICS MODELS MAY ANSWER at this size and speed.

    AXIS 3 of the vessel description, and it is DERIVED — a caller cannot
    declare it, because a declared regime can contradict the geometry that
    produces it. `mission.VesselConfig` therefore carries topology and manning
    and deliberately does NOT carry this.

    It names MODEL ADMISSIBILITY and not "what carries the weight". The latter
    is `formlib.Regime` (displacement / semi-displacement / planing) and its
    bands OVERLAP on purpose — `formlib.REGIME_FN` runs DISPLACEMENT to 0.45
    and SEMI_DISPLACEMENT from 0.30 — so there is no total function from Fn to
    one of those three names, and inventing one here would be a second, wrong
    copy of a table formlib owns.
    """

    fn: float
    re: float
    michell_ok: bool          # the wave half: Fn <= FN_MICHELL_MAX
    ittc57_ok: bool           # the friction half: Re >= RE_TRANSITION_ONSET
    envelope: tuple[str, ...] = ()   # every model that is out of its support

    @property
    def valid(self) -> bool:
        """True only when BOTH halves of the L1 model may answer."""
        return self.michell_ok and self.ittc57_ok


def flow_regime(speed: float, lwl: float, rho: float = RHO_FRESH) -> FlowRegime:
    """Derive AXIS 3 from a speed and a waterline length. No declaration."""
    u, ell = float(speed), float(lwl)
    fn = u / math.sqrt(G * ell) if ell > 0.0 else float("inf")
    re = u * ell / nu_water(rho)
    viol: list[str] = []
    michell_ok = fn <= FN_MICHELL_MAX
    if not michell_ok:
        viol.append(
            f"Michell thin-ship: Fn {fn:.3f} > {FN_MICHELL_MAX} — the planing "
            f"regime, and this model has no dynamic lift, no dynamic trim and "
            f"no spray. Needs a Savitsky-class method.")
    ittc57_ok = re >= RE_TRANSITION_ONSET
    if not ittc57_ok:
        viol.append(
            f"ITTC-1957: Re {re:.3g} < {RE_TRANSITION_ONSET:.3g} — the "
            f"boundary layer is laminar or transitional and the 1957 line is a "
            f"FULLY TURBULENT correlation. There is no transitional correction "
            f"in this module, so the friction half of this answer is not a "
            f"friction coefficient for this flow. (A 1 m hull reaches this "
            f"below ~1.1 kn; Fn crosses {FN_MICHELL_MAX} at ~2.7 kn on the "
            f"same hull, so a small craft leaves BOTH envelopes at speeds a "
            f"large one never sees.)")
    elif re < RE_FULLY_TURBULENT:
        viol.append(
            f"ITTC-1957: Re {re:.3g} is inside the laminar-turbulent "
            f"transition band [{RE_TRANSITION_ONSET:.3g}, "
            f"{RE_FULLY_TURBULENT:.3g}), so the fully-turbulent line is an "
            f"EXTRAPOLATION here. REPORTED, not refused — turning this band "
            f"into a bar would move the friction number on hulls inside "
            f"today's design box and that is a measured decision, not a "
            f"drive-by one. Recorded as owed.")
    return FlowRegime(fn=fn, re=re, michell_ok=michell_ok,
                      ittc57_ok=ittc57_ok, envelope=tuple(viol))


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
# 161x28 was the production grid: -0.42% from the corner of the table, 7.1 ms.
# The station count is the expensive axis, and `offsets_grid` is a Python loop
# over stations x z, so this is a real cost — measured against the 50 ms
# Gate 1 latency bar in `tests/test_phase1.py`, not assumed to be free.
#
# ---------------------------------------------------------------------------
# THE GRID MOVED ON 2026-08-13 BECAUSE THE BAR DID NOT (plate P1/P2).
#
# The plate-P1 sectional area curve meets its two branches at the max-area
# station with DIFFERENT SLOPES, so the moulded offsets carry a tangent break
# at `x_mb` that the old chine plan-form did not have as sharply. A quadrature
# over the station axis converges more slowly across a corner, and 161x28 fell
# out of the 0.5% bar it is declared to meet: RE-MEASURED on the reference hull
# it read **0.907%** from converged.
#
# TWO THINGS WERE WRONG AND ONLY ONE OF THEM WAS THE GRID.
#
# `CONVERGED_GRID` was 321x65 against a production 161x28, i.e. 2x on stations
# and 2.3x on z — but the OLD production grid's error was then measured against
# a reference that shares a great deal of its own truncation. The reference is
# now 481x88, exactly 2x BOTH axes of the new production grid, so the pair is a
# systematic refinement rather than two grids (the same rule this project
# already applies to its CFD GCI families).
#
# MEASURED against 481x88 over the reference hull plus
# `sample_valid(10, MissionSpec(), seed=0)` — |R_w - converged| / converged:
#
#     grid       reference hull    population median    population worst
#     161x28          0.907%             0.907%              2.557%
#     241x44          0.221%             0.331%              0.673%   <- SHIPPED
#     321x44          0.119%             0.213%              0.552%
#
# 241x44 meets `GRID_CONVERGED_TO` on the reference hull with 2.3x of margin
# and costs 19.2 -> 21.6 ms on a full `evaluate()`, against Gate 1's 50 ms.
# 321x44 buys another 0.1% for a further 2 ms and is NOT taken, because it
# would put the production station count equal to the old reference's and
# invite exactly the z-only convergence study this table warns about.
#
# THE OPEN FINDING, STATED RATHER THAN BURIED: `GRID_CONVERGED_TO` is verified
# on ONE hull, and the POPULATION worst is 0.673% — still outside the bar. The
# worst cases are low-resistance hulls (R_w 19-38 N), where a fixed absolute
# truncation is a large relative one. Whether the bar should be a population
# statistic, and whether the honest fix is a C1 area curve at `x_mb` rather
# than more quadrature, is a design question and is recorded as such: see
# `tests/test_gapfix_physics.py::test_michell_ships_the_grid_it_was_converged_on`,
# which now measures the population beside the reference hull so the gap cannot
# be lost. NOTHING HERE SOFTENED A BAR — 0.005 is where it was.
PRODUCTION_GRID = {"n_stations": 241, "nz": 44}
CONVERGED_GRID = {"n_stations": 481, "nz": 88}
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
    # WHAT VESSEL THIS IS A RESISTANCE OF. `rw`, `rf` and `total` are the WHOLE
    # vessel's, so a reader holding a 1200 N number has to be able to tell a
    # two-hull answer from a one-hull one; without these fields the only clue
    # would be the magnitude, which is exactly how a demihull result gets
    # quoted as a catamaran's. Defaults are the monohull.
    n_hulls: int = 1
    separation_m: float | None = None
    # Free-text receipts about the METHOD, not the number: which interference
    # terms are in and which are not. A tuple rather than a bool because "the
    # wave term is exact and the viscous term is absent" is not a flag.
    method_notes: tuple[str, ...] = ()
    # AXIS 3, DERIVED. Carries Fn AND Re and says which of the two models may
    # answer. `valid` above is `flow.valid`; this is the reason behind it, so a
    # reader never has to guess which half of the L1 model went out of support.
    flow: FlowRegime | None = None


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
               rho: float = RHO_FRESH, n_theta: int | None = None,
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
                                rho: float = RHO_FRESH,
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


def free_wave_spectrum(xs: np.ndarray, zs: np.ndarray, Y: np.ndarray,
                       speed: float, rho: float = RHO_FRESH,
                       n_theta: int | None = None,
                       separation: float | None = None
                       ) -> tuple[np.ndarray, np.ndarray]:
    """(thetas, dR_w/dtheta) — the radiated wave energy BY RADIATION ANGLE.

    `np.trapezoid(spectrum, thetas)` is exactly `michell_rw` on the same
    arguments (asserted in `tests/test_phase1.py`), so this is the same object
    the resistance is an integral of, not a second computation of it.

    Exposed because it is the honest half of the wet-deck question below: any
    calculation of the wave ELEVATION between two demihulls has to start from
    this spectrum, and it is the piece this module can supply exactly.
    """
    if separation is not None:
        lwl = float(xs[-1] - xs[0])
        sep = _separation_or_raise(Y, separation)
        n_theta = (n_theta_for_separation(lwl, sep) if n_theta is None
                   else int(n_theta))
        _require_theta_resolution(lwl, sep, n_theta)
    else:
        n_theta = N_THETA_MONOHULL if n_theta is None else int(n_theta)
    thetas, sec = _theta_grid(n_theta)
    if speed <= 0.05:
        return thetas, np.zeros(n_theta)
    vals = _free_wave_vals(xs, zs, Y, speed, thetas, sec)
    if separation is not None:
        vals = vals * catamaran_interference(G / speed**2, thetas, sep)
    return thetas, vals * (4.0 * rho * G**2 / (math.pi * speed**2))


# ---------------------------------------------------------------------------
# WET-DECK CLEARANCE — and one thing this module REFUSES to compute
# ---------------------------------------------------------------------------
#
# A catamaran has a third consequence of demihull separation beyond resistance
# and stability, and for a real boat it is often the governing one: the bridge
# deck (wet deck) spanning the two hulls slams. An optimiser handed separation
# as a free variable and no clearance term will find a spacing it likes for
# wave interference and say nothing about the structure that spacing implies.
#
# THE THING THIS MODULE REFUSES. It was proposed that the bow wave amplitude
# be computed "from the same Kochin machinery". It cannot be, and saying so is
# more useful than a number:
#
#   1. `michell_rw`'s integrand is the FAR-FIELD free-wave spectrum. Michell's
#      integral keeps only the radiating part of the disturbance and discards
#      the local, non-radiating near field — which is exactly the part that
#      makes the bow wave at the stem.
#   2. The far-field elevation is not a single amplitude at all. By stationary
#      phase the Kelvin pattern decays as R^-1/2, so "the amplitude" is a
#      function of where you stand; there is no station-independent metre
#      value in the spectrum to extract.
#   3. |I(theta)| has dimensions of AREA (it integrates dy/dx over dz dx).
#      Turning it into a wave height needs Havelock's elevation kernel and a
#      field point, neither of which is in this module. Supplying a constant
#      to make the units work would be inventing the answer — the defect class
#      docs/LESSONS.md calls "an unmeasurable value scored as a passing one".
#
# WHAT IS RIGOROUS, AND IS SHIPPED INSTEAD. In steady flow the free surface
# rises at the stem by the Bernoulli head, and at a stagnation point that rise
# is EXACT: the whole dynamic head converts, so
#
#     zeta_bow = U^2 / (2 g) = Fn^2 * Lwl / 2
#
# It is an UPPER bound for any hull with a finite entrance angle (a fine bow
# never fully stagnates), it needs no empirical constant, and it is a length
# in metres at a stated speed — which is what a constraint row needs. On a
# 10 m waterline: 0.450 m at Fn 0.30, 0.613 m at Fn 0.35, 0.800 m at Fn 0.40.
#
# THE COUPLING TO THE INTERFERENCE TERM, MEASURED rather than assumed. The
# worry motivating this section was that chasing destructive interference
# would drive the wet deck into trouble. On the CALM-WATER term the two are
# ALIGNED, not opposed: the interference ratio is the ratio of radiated wave
# ENERGY, so a spacing that cuts R_w cuts the wave field between the hulls by
# the same factor. MEASURED at Fn 0.30 on the Wigley demihull, s/Lwl 0.150 to
# 1.500: the destructive optimum at s/Lwl 0.4450 radiates 0.9223 of two
# independent demihulls while the constructive worst case at s/Lwl 0.1500
# radiates 1.4730 — so the wet deck sees the LARGEST wave field at exactly the
# spacings the resistance objective already rejects.
#
# The mechanism that is NOT covered here is the seaway one: wet-deck slamming
# in head seas is driven by relative motion between the bridge deck and the
# incident wave, which is `navalai/seakeeping.py`'s question, not this
# module's. `wet_deck_clearance_g` therefore covers the ship's OWN wave only,
# and says so in its name and its docstring rather than in a comment a caller
# will not read.


def bow_wave_rise(speed: float) -> float:
    """Stem wave rise [m] above the still waterline: U^2 / (2 g).

    The steady-Bernoulli stagnation rise — EXACT at a stagnation point, and an
    upper bound for a hull with a finite entrance angle. It carries no
    empirical constant and no hull shape, which is both its honesty and its
    limit: it is the speed's contribution to wet-deck clearance and nothing
    else. A hull-form correction would need the near-field solution Michell
    discards (see the section above).
    """
    if not (isinstance(speed, (int, float, np.floating))
            and math.isfinite(speed) and speed >= 0.0):
        raise ValueError(
            f"bow_wave_rise: speed = {speed!r} is not a non-negative finite "
            f"velocity; refused rather than returning a rise for it")
    return float(speed) ** 2 / (2.0 * G)


def wet_deck_clearance_g(clearance_m: float, speed: float) -> float:
    """Constraint value for wet-deck clearance against the ship's OWN bow wave.

    `bow_wave_rise(speed) - clearance_m`, in METRES, POSITIVE WHEN VIOLATED —
    the same shape and sign as `evaluate`'s `"freeboard": FREEBOARD_FLOOR_M -
    hs.freeboard_min`, so it can be appended to `CONSTRAINT_NAMES` /
    `Evaluation.g` as a row without any convention change. NOT wired here: the
    genome has no clearance parameter yet and `grammar.py` is another agent's
    file.

    `clearance_m` is the height of the wet deck above the still waterline.

    SCOPE, and it is half the problem: this covers the ship's own steady bow
    wave. Wet-deck slamming in a seaway is driven by relative motion against
    the incident wave and belongs to `navalai/seakeeping.py`; a design that
    satisfies this row is not thereby slam-free, and the row must not be
    described as if it were.
    """
    if not (isinstance(clearance_m, (int, float, np.floating))
            and math.isfinite(clearance_m)):
        raise ValueError(
            f"wet_deck_clearance_g: clearance_m = {clearance_m!r} is not a "
            f"finite height above the waterline. An unmeasured clearance is "
            f"REFUSED, not scored as satisfied — a wet deck whose height "
            f"nobody recorded is the case this row exists to catch.")
    return bow_wave_rise(speed) - float(clearance_m)


# THE VALIDATION ANCHOR FOR THE INTERFERENCE TERM, AND IT IS PUBLISHED.
#
# NOTHING BELOW IS IN THIS REPOSITORY. No data file, no transcribed table, no
# digitised curve — these are CITATIONS, checked against the literature record
# on 2026-08-13 and not against any measurement of ours. The `s -> inf` test in
# `tests/test_phase1.py` proves the interference term is SELF-CONSISTENT; only
# one of these would prove it is RIGHT, and until one is transcribed this
# module has no experimental anchor for a catamaran at all.
#
#   Bailey, D. (1976). "The NPL High Speed Round Bilge Displacement Hull
#     Series: Resistance, Propulsion, Manoeuvring and Seakeeping Data."
#     RINA Maritime Technology Monograph No. 4, London.
#     The parent series. Envelope as given to this plate: Fn 0.3-1.2,
#     L/B 3.33-7.50, B/T 1.75-10.77 — which OVERLAPS this project's design box
#     (`grammar.L_OVER_B_BAND` (2.2, 8.5), `B_OVER_T_BAND` (1.8, 12.0)), so a
#     comparison would be interpolation rather than extrapolation. Note the
#     Froude floor: NPL starts at 0.3 and `FN_MICHELL_MAX` here is 0.45, so the
#     usable overlap is a narrow Fn 0.30-0.45 window.
#
#   Insel, M. and Molland, A.F. (1992). "An Investigation into the Resistance
#     Components of High Speed Displacement Catamarans." Trans. RINA, Vol. 134.
#     THE DIRECTLY RELEVANT ONE: a Wigley hull plus three NPL-derived round
#     bilge forms, tested as monohulls and as catamarans, and compared against
#     THIN SHIP THEORY — the same theory this module implements. It is the
#     source of the standard catamaran resistance decomposition into a wave
#     interference factor and a viscous form interference factor.
#
#   Molland, A.F., Wellicome, J.F. and Couser, P.R. (1996). "Resistance
#     experiments on a systematic series of high speed displacement catamaran
#     forms: variation of length-displacement ratio and breadth-draught ratio."
#     Trans. RINA, Vol. 138, pp. 55-71. Open-access as University of
#     Southampton Ship Science Report No. 71/127,
#     https://eprints.soton.ac.uk/46409/1/127ShipScience_Report.pdf
#     The Southampton catamaran series, NPL round-bilge sections, tested at
#     demihull separation ratios S/L and as a monohull. This is the shape of
#     data this plate's bar 3 produces — an interference ratio as a function of
#     S/L and Froude number — and is therefore the transcription to do first.
#
# WHAT A TRANSCRIPTION WOULD HAVE TO RESPECT, because getting this wrong would
# compare two different quantities: the published catamaran interference factor
# is usually defined on the WAVE component C_W (or on residuary resistance with
# a form factor removed), not on total resistance, and the demihulls are free
# to sink and trim. `michell_rw` gives the wave component of a FIXED hull, so
# the comparison quantity is C_W(cat)/C_W(2 x demi) at matched Fn and S/L —
# which is exactly the ratio bar 3 measures, and is why bar 3 is expressed as a
# ratio rather than as newtons.


def ittc57_cf(speed: float, lwl: float, nu: float | None = None,
              rho: float = RHO_FRESH) -> float:
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
                     rho: float = RHO_FRESH, wl: float = 0.0,
                     nz: int | None = None, n_stations: int | None = None,
                     beam_wl: float | None = None,
                     draft: float | None = None,
                     separation: float | None = None,
                     lwl_eff: float | None = None) -> ResistanceResult:
    """Michell wave resistance + ITTC-57 friction on the PRODUCTION grid.

    `beam_wl` and `draft` are the FLOATED waterline beam and draft — pass them
    from the same `HydroState` that produced `cb` and `wetted`. Omitting them
    falls back to the design beam and design draft, which is the inconsistent
    state gap E7 measured; the fallback exists so a caller holding only a hull
    still gets an answer, and it is the caller's job not to be `evaluate()`.

    `lwl_eff` is the FLOATED waterline length from the same HydroState —
    C-08, the last member of the E7 family: this function used the DESIGN
    length (hull.x[-1]) for Fn, Cf's Reynolds number, the form factor and
    the regime envelope while every other flow quantity came from the
    floated state. Rocker and trim lift the ends, so the flow sees
    lwl_eff < design length (documented worst +2.575% Rt from the mix).
    Same fallback contract as beam/draft: None = design length. The
    Michell integral is UNAFFECTED either way — it consumes the offsets
    grid shifted to the floated frame, not this scalar.

    `separation` [m] makes this a CATAMARAN of two identical demihulls of
    `hull`, and the return is then the WHOLE VESSEL's resistance. Every
    argument must be consistent with that or the answer mixes two boats:

      * `wetted` is the VESSEL's wetted area (both demihulls) — `q` below is
        the friction dynamic-pressure term and it must see all the skin there
        is. `hydrostatics.solve(..., vessel=cfg)` returns exactly this.
      * `cb`, `beam_wl` and `draft` are ONE DEMIHULL's, because they feed
        Watanabe's form factor, which is a regression on a single hull's own
        block coefficient and B/T. `HydroState` deliberately keeps those three
        per-demihull for this reason.
      * `hull` is ONE demihull. `michell_rw` translates its Kochin amplitude to
        y = +-s/2 itself; handing it a pre-doubled anything would square the
        hull count.

    `separation=None` is the monohull and every line below is bit-identical to
    what it computed before the multihull path existed
    (`tests/test_multihull.py::test_total_resistance_monohull_is_bit_identical_to_the_bare_michell_call`).

    THE THETA GRID IS NOT THE MONOHULL'S. `michell_rw` resolves `n_theta` from
    the MEASURED rule `880 * max(1, s/Lwl)` and REFUSES anything coarser,
    because the interference term's quadrature error changes sign with
    separation and an optimiser reads that as a real optimum. MEASURED cost of
    obeying it on the production grid (241 x 44 offsets, reference hull):
    6.2 ms at 220 nodes, 24.3 ms at 880 — so a catamaran evaluation is ~18 ms
    dearer than a monohull one and Gate 1's 50 ms bar is a MONOHULL bar. The
    bar was not touched; see `tests/test_multihull.py` for the catamaran's own
    measured latency gate.
    """
    nz = int(PRODUCTION_GRID["nz"] if nz is None else nz)
    ns = int(PRODUCTION_GRID["n_stations"] if n_stations is None
             else n_stations)
    # Refine the STATION axis for the integral only. The hull handed in carries
    # whatever station count its caller wanted for hydrostatics (41 by
    # default); the Michell integral needs 241 to be within 0.5% of converged
    # on the reference hull, and rebuilding is ~1 ms against the integral.
    # THE REBUILD CAN REFUSE: `Hull` solves the section at every station it is
    # given, so a vector that builds at 41 can raise `GeometryError` at 241.
    # That is why `grammar.check` probes the section solve on a grid denser
    # than this one before it passes anything (`geometry.section_probe`).
    grid_hull = hull if hull.n_stations == ns else Hull(hull.params,
                                                        n_stations=ns)
    xs, zs, Y = grid_hull.offsets_grid(nz=nz, wl=wl)
    # Michell frame: free surface at z=0 — shift the grid by the floated WL
    rw = michell_rw(xs, zs - wl, Y, speed, rho, separation=separation)
    # C-08: the flow-length quantities (Fn, Re, form factor, regime) read
    # the floated waterline length when the caller supplies it; the design
    # length remains only as the holding-only-a-hull fallback.
    lwl = float(hull.x[-1]) if lwl_eff is None else float(lwl_eff)
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
    # AXIS 3. `valid` used to be `fn <= FN_MICHELL_MAX` alone; it now also
    # requires the friction line to be inside the flow it correlates. The
    # `regime` STRING below is still keyed on Fn only, exactly as it was, so
    # nothing that reads it changes meaning: at Re >= RE_TRANSITION_ONSET —
    # true of every hull in today's design box, by 3.6x at the worst corner —
    # `flow.valid` is identically the old expression.
    flow = flow_regime(speed, lwl, rho)
    valid = flow.valid
    if not valid:
        # The band is meaningless outside the model's regime; say so with a
        # sigma the size of the answer rather than a comfortable 25%.
        sigma = max(sigma, total)
    grid = {"n_stations": ns, "nz": nz, "converged_to": GRID_CONVERGED_TO}
    notes: tuple[str, ...] = ()
    n_hulls = 1
    if separation is not None:
        n_hulls = 2
        # The theta count is a RECEIPT, not a re-derivation: `michell_rw`
        # resolved and enforced it from this same function on this same length
        # a few lines above, so recording it here cannot disagree with what ran.
        grid["n_theta"] = n_theta_for_separation(
            float(xs[-1] - xs[0]), float(separation))
        grid["separation_m"] = float(separation)
        notes = (
            "catamaran: WAVE interference is the exact thin-ship factor "
            "4 cos^2(k_y s/2), k_y = k0 sec^2(th) sin(th) "
            "(navalai/experiments.py verified the convention three ways)",
            "catamaran: VISCOUS form interference is NOT modelled — the "
            "demihull's own Watanabe form factor is applied to the vessel's "
            "total wetted area. Insel & Molland measure this factor; it is "
            "cited in this module and has never been transcribed, so no "
            "number stands in for it",
            "catamaran: NO EXPERIMENTAL ANCHOR. The s -> infinity and "
            "superposition checks prove the term is self-consistent, not that "
            "it is right",
        )
    return ResistanceResult(speed, fn, rw, rf, total, cw, cf, sigma,
                            valid=valid,
                            regime=("displacement" if fn <= FN_MICHELL_MAX
                                    else "planing"),
                            form=form, grid=grid,
                            n_hulls=n_hulls,
                            separation_m=(None if separation is None
                                          else float(separation)),
                            method_notes=notes, flow=flow)
