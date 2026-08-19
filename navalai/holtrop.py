"""Holtrop-Mennen statistical resistance prediction — tier L1.

J. Holtrop and G.G.J. Mennen, "An approximate power prediction method",
International Shipbuilding Progress 29 (335), 166-170, 1982.  A regression on
the Netherlands Ship Model Basin's model-test and full-scale database, which
decomposes calm-water resistance into

    R_total = R_F (1+k1) + R_APP + R_W + R_B + R_TR + R_A                [N]

  R_F     ITTC-1957 flat-plate friction on the bare-hull wetted surface
  1+k1    form factor for the viscous pressure drag of the hull form
  R_APP   appendage drag, via an equivalent appendage form factor (1+k2)
  R_W     wave making and wave breaking
  R_B     additional pressure drag of a bulbous bow near the surface
  R_TR    additional pressure drag of an immersed transom
  R_A     model-ship correlation allowance

WHY THIS MODULE EXISTS AND WHAT IT IS FOR (gap E1)
--------------------------------------------------
Gate 1's bar in `NavalArchAI-BuildPlan.md` reads "Hydrostatics, Michell +
ITTC-1957, **Holtrop-Mennen**, and the mission-physics models ... Holtrop
reproduces its own validation set".  Until this file, `grep -rin holtrop`
across the repository hit the plan document and nothing else: no code, no
test, no validation set — while `python -m navalai.gates` printed Gate 1
GREEN.  A gate that cannot fail is not a gate.  `benchmarks/holtrop_cases.py`
carries the paper's own worked example and `tests/test_holtrop.py` asserts
this implementation against it PER INTERMEDIATE, because a total can be right
by cancelling errors in the parts.

EVERY intermediate here is a separate function taking scalars.  That is
deliberate: when a prediction disagrees with a tank or with CFD, the argument
is always about WHICH TERM, and a monolithic `holtrop(...)` returning one
number cannot take part in that argument.

SCOPE, stated so it is not overread
-----------------------------------
- RESISTANCE ONLY.  The paper's propulsion half (wake fraction, thrust
  deduction, propeller series, delivered power) is NOT implemented.
- The 1982 wave-resistance branch only (`R_W-a`).  The 1984 re-analysis adds a
  high-speed branch and a 0.40 < Fn < 0.55 interpolation; neither is here.
  The Fn <= 0.45 envelope below is what keeps that omission honest rather than
  silent.
- The method is a REGRESSION over a database of ships.  It has no knowledge of
  a hull beyond the dozen numbers it is handed, so two different hulls with
  identical particulars get identical answers.  It is a design-stage estimate
  and it is offered as one.

TWO KINDS OF "OUT OF RANGE", AND THEY GET DIFFERENT ANSWERS
-----------------------------------------------------------
1. OUTSIDE THE STATISTICAL ENVELOPE.  The formulae evaluate fine; the
   regression simply has no ships like this behind it.  Consistent in spirit
   with `navalai.resistance.FN_MICHELL_MAX`, the number is STILL RETURNED —
   refusing outright hides it from a designer who wants to see it — but
   `HoltropResult.valid` is False, `.tier` reads "L1H-INVALID",
   `.envelope_violations` names every clause that failed WITH its measured
   value, and `.sigma` is inflated to the size of the answer, because a
   comfortable percentage band outside a regression's support is a decoration.

2. OUTSIDE THE FORMULAE'S DOMAIN.  There is no number at all — a pole, or a
   negative base under a fractional power.  `total()` RAISES.  This is not
   defensive padding; it was MEASURED on the first draft of this module, which
   had no such check:

       Cp = 0.96                -> total = (8504.47-1749.72j) N.  A COMPLEX
                                   RESISTANCE, from (0.95 - Cp)^-0.521448,
                                   sitting in a float-typed dataclass field
                                   with valid=False set for an unrelated
                                   reason. Anything downstream comparing it to
                                   a threshold raises or silently misbehaves.
       Cwp = 1.0                -> ZeroDivisionError deep inside c1, because
                                   i_E hits exactly 90 deg and c1 carries
                                   (90 - i_E)^-1.37565.
       Cp = 0.25                -> ZeroDivisionError in the length of run
                                   (4 Cp - 1).
       lcb = +25 %              -> TypeError: complex, from the entrance-angle
                                   regression.
       A_T > B T C_M            -> c5 goes NEGATIVE and R_W comes back as a
                                   plausible positive number computed from a
                                   negative wave-resistance amplitude.

   Gap E10 in the register is "NaN in any constraint makes a design feasible";
   a complex or NaN resistance escaping into the constraint vector is the same
   failure with a worse disguise.  `domain_errors()` names each impossibility
   in words, and `total()` refuses rather than returning it.

UNITS: SI.  Lengths m, areas m^2, volumes m^3, angles deg where noted, speeds
m/s, forces N.  Every function's docstring states its own.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .geometry import G

# Sea water at 15 degrees centigrade, the condition the 1982 paper works in.
from .constants import RHO_SEA_HOLTROP  # see constants.py
from .constants import NU_SEA_HOLTROP  # see constants.py
from .limits import RE_TRANSITION_BAND

# The envelope's Reynolds floor: the fully-turbulent end of the one
# declared band. An alias, not a second number.
RE_TURBULENT_MIN = RE_TRANSITION_BAND[1]

# The uncertainty band attached to every prediction.  DECLARED, NOT SOURCED:
# the 1982 paper does not publish a per-prediction standard error in a form
# that could be transcribed, and inventing one and calling it Holtrop's would
# be exactly the fabrication this module was written to avoid.  0.10 is a
# deliberately round, deliberately unglamorous number for a statistical method
# applied inside its own support, and it is labelled as declared wherever it
# surfaces.  Replace it the day a measured spread against tank data exists.
SIGMA_DECLARED = 0.10     # one sigma as a fraction of R_total, inside envelope


@dataclass(frozen=True)
class ValidityBand:
    """One row of the 1982 paper's table of applicability."""

    ship_types: str
    fn_max: float
    cp: tuple[float, float]
    l_over_b: tuple[float, float]
    b_over_t: tuple[float, float]


# The paper tabulates its range of applicability per ship type.  THREE of the
# five rows are reproduced here; they were confirmed from a peer-reviewed
# secondary source that cites Holtrop & Mennen 1982 directly (Annals of
# "Dunarea de Jos" University of Galati, Fascicle XI, 2021, section 2).  The
# other two rows (cargo liners; RoRo ships and car ferries) could not be
# recovered from any source reached, so they are NOT listed and NOT guessed —
# see `benchmarks.holtrop_cases.NOT_VERIFIED`.
VALIDITY_BANDS = (
    ValidityBand("oil tankers, bulk carriers", 0.24, (0.73, 0.85),
                 (5.1, 7.1), (2.4, 3.2)),
    ValidityBand("container ships, destroyer types", 0.45, (0.55, 0.67),
                 (6.0, 9.5), (3.0, 4.0)),
    ValidityBand("trawlers, coastal tugs, tugs", 0.38, (0.55, 0.65),
                 (3.9, 6.3), (2.1, 3.0)),
)

# The enforced envelope is the UNION of the bands above — the loosest claim the
# source supports.  A caller's brief named `L/B <= 15`; that number is not in
# any reading of the 1982 table we could reach, so the sourced 9.5 is used
# instead.  A tighter envelope only ever flags MORE predictions as outside
# support, which is the safe direction: nothing is refused, only badged.
FN_MAX = max(b.fn_max for b in VALIDITY_BANDS)                    # 0.45
CP_RANGE = (min(b.cp[0] for b in VALIDITY_BANDS),
            max(b.cp[1] for b in VALIDITY_BANDS))                 # 0.55 .. 0.85
L_OVER_B_RANGE = (min(b.l_over_b[0] for b in VALIDITY_BANDS),
                  max(b.l_over_b[1] for b in VALIDITY_BANDS))     # 3.9 .. 9.5
B_OVER_T_RANGE = (min(b.b_over_t[0] for b in VALIDITY_BANDS),
                  max(b.b_over_t[1] for b in VALIDITY_BANDS))     # 2.1 .. 4.0


@dataclass(frozen=True)
class Particulars:
    """The hull form as Holtrop-Mennen sees it.  SI units.

    lwl      length on the waterline [m] — the L of every formula here
    b        moulded breadth [m]
    tf       draught forward [m]
    ta       draught aft [m]
    volume   moulded displacement volume [m^3]
    cm       midship section coefficient [-]
    cwp      waterplane area coefficient [-]
    lcb      longitudinal centre of buoyancy, PER CENT of lwl forward of
             0.5 lwl; negative is aft.  Sign matters: it appears in the form
             factor, in the length of run and in the entrance angle.
    abt      transverse sectional area of the bulb at the forward
             perpendicular [m^2]; 0 for no bulb
    hb       height of the centre of `abt` above the keel line [m]
    at       immersed transom area at rest [m^2]; 0 for no immersed transom
    s_app    wetted surface of the appendages [m^2]
    k2_app   equivalent appendage form factor (1+k2) [-].  The paper
             tabulates approximate values (rudder behind stern 1.3-1.5,
             shaft brackets 3.0, bilge keels 1.4, ...); this is the
             area-weighted equivalent for the whole appendage set.
    c_stern  stern shape parameter [-]: -25 pram with gondola, -10 V-shaped,
             0 normal, +10 U-shaped with Hogner stern
    ie_deg   half angle of entrance [deg], if it is known from the lines.
             None (the default) uses the paper's regression for it.
    s        bare-hull wetted surface [m^2], if it is known from the lines.
             None uses the paper's regression for it.
    """

    lwl: float
    b: float
    tf: float
    ta: float
    volume: float
    cm: float
    cwp: float
    lcb: float
    abt: float = 0.0
    hb: float = 0.0
    at: float = 0.0
    s_app: float = 0.0
    k2_app: float = 1.0
    c_stern: float = 0.0
    ie_deg: float | None = None
    s: float | None = None

    @property
    def draught(self) -> float:
        """Mean moulded draught [m]."""
        return 0.5 * (self.tf + self.ta)


# ---------------------------------------------------------------------------
# Form coefficients
# ---------------------------------------------------------------------------

def block_coefficient(volume: float, lwl: float, b: float, t: float) -> float:
    """C_B [-] on the waterline length."""
    return volume / (lwl * b * t)


def prismatic_coefficient(cb: float, cm: float) -> float:
    """C_P = C_B / C_M [-]."""
    return cb / cm


def length_of_run(lwl: float, cp: float, lcb: float) -> float:
    """Length of run L_R [m].

    L_R = L (1 - C_P + 0.06 C_P lcb / (4 C_P - 1)).  `lcb` is in per cent.
    """
    return lwl * (1.0 - cp + 0.06 * cp * lcb / (4.0 * cp - 1.0))


def c12(t: float, lwl: float) -> float:
    """c12 [-] — the draught-to-length term of the form factor.

    Two branches at T/L = 0.05.  The paper also caps the argument below
    T/L = 0.02, where the low branch turns complex; that cap is applied here.
    """
    r = t / lwl
    if r >= 0.05:
        return r ** 0.2228446
    if r <= 0.02:
        return 0.479948
    return 48.20 * (r - 0.02) ** 2.078 + 0.479948


def c13(c_stern: float) -> float:
    """c13 [-] — the stern-shape term of the form factor."""
    return 1.0 + 0.003 * c_stern


def form_factor(cp: float, lcb: float, b: float, lr: float,
                c12_: float, c13_: float) -> float:
    """1 + k1 [-], the hull's viscous form factor."""
    return c13_ * (0.93 + c12_ * (b / lr) ** 0.92497
                   * (0.95 - cp) ** -0.521448
                   * (1.0 - cp + 0.0225 * lcb) ** 0.6906)


def wetted_surface_bracket(b: float, t: float, cm: float, cb: float,
                           cwp: float) -> float:
    """The regression's shape bracket — the term that can go NEGATIVE.

    It carries `-0.003467 B/T`, and nothing in the 1982 paper bounds B/T, so a
    sufficiently wide, shallow hull drives the bracket through zero and the
    whole formula returns a negative AREA. Exposed as its own function so
    `domain_errors` and `wetted_surface` test the identical expression rather
    than each keeping a copy of the coefficients.
    """
    return (0.453 + 0.4425 * cb - 0.2862 * cm - 0.003467 * b / t
            + 0.3696 * cwp)


def wetted_surface(lwl: float, b: float, t: float, cm: float, cb: float,
                   cwp: float, abt: float) -> float:
    """Bare-hull wetted surface S [m^2] from the paper's regression."""
    bracket = wetted_surface_bracket(b, t, cm, cb, cwp)
    if bracket <= 0.0:
        # A NEGATIVE WETTED SURFACE PROPAGATED ALL THE WAY TO A TOTAL.
        # REPRODUCED with Particulars(lwl=100, b=39, tf=0.2, ta=0.2,
        # volume=390, cm=0.9, cwp=0.7, lcb=0) at 6.0 m/s — B/T = 195, bracket
        # = -6.8e-4 — giving S = -2.523 m^2, R_F = -77.70 N, R_A = -25.43 N and
        # a total of 3.0e13 N, while `domain_errors()` returned EMPTY so
        # `total()` never refused. This module's own contract is that it RAISES
        # outside the formulae's domain; a negative area is as far outside as
        # it gets. The bracket turns at B/T ~ 195 for this hull, and the exact
        # crossover moves with C_B, C_M and C_WP, which is why it is tested as
        # an expression and not as a B/T limit.
        raise ValueError(
            f"wetted-surface bracket = {bracket:.6f} <= 0 at B/T = {b / t:.1f} "
            f"(C_B {cb:.3f}, C_M {cm:.3f}, C_WP {cwp:.3f}): the regression "
            f"carries -0.003467 B/T and returns a NEGATIVE area here. There is "
            f"no wetted surface to report, so there is no resistance either.")
    s = lwl * (2.0 * t + b) * math.sqrt(cm) * bracket
    return s + 2.38 * abt / cb


def c7(b: float, lwl: float) -> float:
    """c7 [-] — the breadth-to-length term entering c1."""
    r = b / lwl
    if r < 0.11:
        return 0.229577 * r ** (1.0 / 3.0)
    if r <= 0.25:
        return r
    return 0.5 - 0.0625 / r


def half_angle_entrance(lwl: float, b: float, cwp: float, cp: float,
                        lcb: float, lr: float, volume: float) -> float:
    """Half angle of entrance i_E [deg], from the paper's regression.

    Used only when the lines are not available; if they are, pass the measured
    angle in `Particulars.ie_deg` instead — the regression is the weakest link
    in the wave-resistance chain because c1 goes as (90 - i_E)^-1.37565.
    """
    return 1.0 + 89.0 * math.exp(
        -(lwl / b) ** 0.80856
        * (1.0 - cwp) ** 0.30484
        * (1.0 - cp - 0.0225 * lcb) ** 0.6367
        * (lr / b) ** 0.34574
        * (100.0 * volume / lwl ** 3) ** 0.16302)


def c1(c7_: float, t: float, b: float, ie_deg: float) -> float:
    """c1 [-] — the leading amplitude of the wave-resistance regression."""
    return (2223105.0 * c7_ ** 3.78613 * (t / b) ** 1.07961
            * (90.0 - ie_deg) ** -1.37565)


def c3(abt: float, b: float, t: float, tf: float, hb: float) -> float:
    """c3 [-] — bulb size parameter feeding c2.  0 for no bulb."""
    if abt <= 0.0:
        return 0.0
    denom = b * t * (0.31 * math.sqrt(abt) + tf - hb)
    return 0.56 * abt ** 1.5 / denom


def c2(c3_: float) -> float:
    """c2 [-] — the bulb's reduction of wave resistance.  1.0 for no bulb."""
    return math.exp(-1.89 * math.sqrt(c3_))


def c5(at: float, b: float, t: float, cm: float) -> float:
    """c5 [-] — the immersed transom's reduction of wave resistance."""
    return 1.0 - 0.8 * at / (b * t * cm)


def c15(lwl: float, volume: float) -> float:
    """c15 [-] — the slenderness term of the m2 exponent.  NEGATIVE or zero."""
    ratio = lwl ** 3 / volume
    if ratio < 512.0:
        return -1.69385
    if ratio > 1727.0:
        return 0.0
    return -1.69385 + (lwl / volume ** (1.0 / 3.0) - 8.0) / 2.36


def c16(cp: float) -> float:
    """c16 [-] — the prismatic term of the m1 exponent."""
    if cp < 0.8:
        return 8.07981 * cp - 13.8673 * cp ** 2 + 6.984388 * cp ** 3
    return 1.73014 - 0.7067 * cp


def m1(lwl: float, t: float, b: float, volume: float, c16_: float) -> float:
    """m1 [-] — the Froude-independent exponent of R_W."""
    return (0.0140407 * lwl / t
            - 1.75254 * volume ** (1.0 / 3.0) / lwl
            - 4.79323 * b / lwl
            - c16_)


def m2(c15_: float, cp: float, fn: float) -> float:
    """m2 [-] — the amplitude of the oscillatory (hump/hollow) term of R_W."""
    return c15_ * cp ** 2 * math.exp(-0.1 * fn ** -2)


def wave_length_parameter(cp: float, lwl: float, b: float) -> float:
    """lambda [-] — sets the position of the humps and hollows in Fn."""
    if lwl / b < 12.0:
        return 1.446 * cp - 0.03 * lwl / b
    return 1.446 * cp - 0.36


def wave_resistance(c1_: float, c2_: float, c5_: float, volume: float,
                    fn: float, m1_: float, m2_: float, lam: float,
                    rho: float = RHO_SEA_HOLTROP, g: float = G) -> float:
    """R_W [N] — wave making and wave breaking, the 1982 branch.

        R_W = c1 c2 c5 (volume rho g) exp(m1 Fn^d + m2 cos(lambda Fn^-2))

    with d = -0.9 fixed by the paper.  Valid to Fn ~ 0.45; the 1984 high-speed
    branch is not implemented (see the module docstring).
    """
    d = -0.9
    return (c1_ * c2_ * c5_ * volume * rho * g
            * math.exp(m1_ * fn ** d + m2_ * math.cos(lam * fn ** -2)))


def bulbous_bow(abt: float, tf: float, hb: float, speed: float,
                rho: float = RHO_SEA_HOLTROP,
                g: float = G) -> tuple[float, float, float]:
    """(P_B [-], Fn_i [-], R_B [N]) — bulb pressure drag near the surface.

    Returns zeros for a hull with no bulb.  P_B is the emergence parameter
    0.56 sqrt(A_BT) / (T_F - 1.5 h_B); R_B collapses as the bulb goes deep
    because of the exp(-3 P_B^-2) factor.
    """
    if abt <= 0.0:
        return 0.0, 0.0, 0.0
    denom = tf - 1.5 * hb
    if denom <= 0.0:
        # A bulb whose centre sits at or above 2/3 of the forward draught puts
        # P_B through a pole.  An earlier draft returned (0, 0, 0) here, which
        # reports "this bulb costs nothing" for a bulb the method cannot price
        # — a wrong number, not a missing one.  `total()` refuses such a hull
        # in `domain_errors` before reaching this line; direct callers get the
        # same refusal rather than a comfortable zero.
        raise ValueError(
            f"P_B has a pole at h_B = 2 T_F / 3: T_F = {tf} m, h_B = {hb} m")
    pb = 0.56 * math.sqrt(abt) / denom
    fni = speed / math.sqrt(g * (tf - hb - 0.25 * math.sqrt(abt))
                            + 0.15 * speed ** 2)
    rb = (0.11 * math.exp(-3.0 * pb ** -2) * fni ** 3 * abt ** 1.5 * rho * g
          / (1.0 + fni ** 2))
    return pb, fni, rb


def transom(at: float, b: float, cwp: float, speed: float,
            rho: float = RHO_SEA_HOLTROP,
            g: float = G) -> tuple[float, float, float]:
    """(Fn_T [-], c6 [-], R_TR [N]) — immersed-transom pressure drag.

    c6 falls linearly to zero at Fn_T = 5 and is zero beyond, which is where
    the transom is running dry and stops shedding a pressure loss.
    """
    if at <= 0.0:
        return 0.0, 0.0, 0.0
    fnt = speed / math.sqrt(2.0 * g * at / (b + b * cwp))
    c6_ = 0.2 * (1.0 - 0.2 * fnt) if fnt < 5.0 else 0.0
    return fnt, c6_, 0.5 * rho * speed ** 2 * at * c6_


def c4(tf: float, lwl: float) -> float:
    """c4 [-] — forward-draught term of C_A, capped at 0.04."""
    return min(tf / lwl, 0.04)


def model_ship_correlation(lwl: float, cb: float, c2_: float, c4_: float,
                           s_total: float, speed: float,
                           rho: float = RHO_SEA_HOLTROP) -> tuple[float, float]:
    """(C_A [-], R_A [N]) — the model-ship correlation allowance.

    R_A rides on the TOTAL wetted surface (hull + appendages).  MEASURED
    against the paper's worked example, where R_A prints as 221.98 kN: on the
    hull alone it comes out 220.68 kN (-0.59%), on hull + appendages
    222.07 kN (+0.039%).  See `benchmarks.holtrop_cases`.
    """
    ca = (0.006 * (lwl + 100.0) ** -0.16 - 0.00205
          + 0.003 * math.sqrt(lwl / 7.5) * cb ** 4 * c2_ * (0.04 - c4_))
    return ca, 0.5 * rho * speed ** 2 * s_total * ca


def ittc57_cf(speed: float, lwl: float, nu: float = NU_SEA_HOLTROP) -> float:
    """ITTC-1957 flat-plate friction coefficient C_F [-], sea-water default.

    CONSOLIDATED 2026-08-14 (§18): this was a deliberate local COPY, argued
    from "sharing the function would mean sharing a default that is wrong
    for one of them" — but the canonical `resistance.ittc57_cf` takes `nu`
    EXPLICITLY, so the fresh-water default never fires when this wrapper
    passes its sea value. The argument defended against a hazard the
    signature already prevents; what remains is one formula, one home, and
    this module's own sea-water default preserved at ITS boundary.
    """
    from .resistance import ittc57_cf as _canonical
    return _canonical(speed, lwl, nu=nu)


@dataclass(frozen=True)
class HoltropResult:
    """Every intermediate, not just the total.  SI units; forces in N.

    The components are what make a disagreement diagnosable: "12% high" says
    nothing, "R_W 30% high and R_F on the nose" says where to look.
    """

    # operating point
    speed: float          # m/s
    fn: float             # Froude number on Lwl [-]
    # form
    cb: float             # [-]
    cp: float             # [-]
    lr: float             # length of run [m]
    lcb: float            # [%] of Lwl forward of 0.5 Lwl
    # viscous
    c12: float
    c13: float
    form_factor: float    # 1+k1 [-]
    s: float              # bare-hull wetted surface [m^2]
    cf: float             # [-]
    rf: float             # bare friction WITHOUT the form factor [N]
    rapp: float           # appendage resistance [N]
    # wave
    c7: float
    ie: float             # half angle of entrance [deg]
    c1: float
    c3: float
    c2: float
    c5: float
    c16: float
    m1: float
    c15: float
    m2: float
    lam: float            # lambda [-]
    rw: float             # [N]
    # bulb / transom
    pb: float
    fni: float
    rb: float             # [N]
    fnt: float
    c6: float
    rtr: float            # [N]
    # correlation
    c4: float
    ca: float
    ra: float             # [N]
    # totals
    total: float          # [N]
    pe: float             # effective power = total * speed [W]
    # honesty
    sigma: float          # one sigma on `total` [N]
    tier: str             # "L1H" or "L1H-INVALID"
    valid: bool
    envelope_violations: tuple[str, ...] = field(default_factory=tuple)


def domain_errors(p: Particulars, speed: float,
                  g: float = G) -> tuple[str, ...]:
    """Inputs for which the published formulae have NO VALUE.

    Distinct from `envelope_violations`, which is about the regression's
    support.  Each entry names the impossibility and the coefficient it kills,
    so the message is a diagnosis and not just a rejection.  Empty tuple means
    every expression below is evaluable.
    """
    out: list[str] = []
    for name, v in (("lwl", p.lwl), ("b", p.b), ("tf", p.tf), ("ta", p.ta),
                    ("volume", p.volume), ("cm", p.cm), ("cwp", p.cwp)):
        if not (v > 0.0):
            out.append(f"{name} = {v} must be positive")
    if speed <= 0.0:
        # R_W carries Fn^-2 and Fn^-0.9: zero speed is a pole, not a limit.
        # Gap E12 in the register is a mission that reached the physics at
        # 0 knots and got a finite, cheerful answer back.
        out.append(f"speed = {speed} m/s: R_W carries Fn^-2, so zero speed is "
                   f"a pole, not a limit")
    if out:
        return tuple(out)      # the rest would divide by these

    t = p.draught
    cb = block_coefficient(p.volume, p.lwl, p.b, t)
    cp = prismatic_coefficient(cb, p.cm)
    if not (0.25 < cp < 0.95):
        out.append(f"Cp = {cp:.4f}: the length of run divides by (4 Cp - 1) "
                   f"and the form factor carries (0.95 - Cp)^-0.521448, so Cp "
                   f"must lie strictly inside (0.25, 0.95)")
    else:
        lr = length_of_run(p.lwl, cp, p.lcb)
        if lr <= 0.0:
            out.append(f"length of run {lr:.3f} m <= 0 (Cp {cp:.3f}, lcb "
                       f"{p.lcb}%): the form factor carries (B/L_R)^0.92497")
        if 1.0 - cp + 0.0225 * p.lcb <= 0.0:
            out.append(f"1 - Cp + 0.0225 lcb = {1 - cp + 0.0225 * p.lcb:.4f} "
                       f"<= 0: negative base under the form factor's ^0.6906")
        if 1.0 - cp - 0.0225 * p.lcb <= 0.0:
            out.append(f"1 - Cp - 0.0225 lcb = {1 - cp - 0.0225 * p.lcb:.4f} "
                       f"<= 0: negative base under the entrance angle's ^0.6367")
    # THE WETTED SURFACE CAN GO NEGATIVE, AND NOTHING CAUGHT IT.
    # See `wetted_surface` for the reproduction: B/T = 195 gave S = -2.523 m^2,
    # R_F = -77.70 N and a total of 3.0e13 N with this function returning an
    # empty tuple, so `total()` handed back a HoltropResult instead of
    # refusing. `envelope_violations` did flag "B/T 195.00 outside [2.1, 4.0]",
    # but that badges the result as out-of-support — it does not refuse it, and
    # a negative area is not a support question, it is an impossibility.
    bracket = wetted_surface_bracket(p.b, t, p.cm, cb, p.cwp)
    if bracket <= 0.0:
        out.append(
            f"wetted-surface bracket = {bracket:.6f} <= 0 at B/T = "
            f"{p.b / t:.1f}: S = L(2T + B) sqrt(C_M) * bracket returns a "
            f"NEGATIVE area, and R_F, R_A and R_W are all built on it")
    if p.ie_deg is None:
        if p.cwp >= 1.0:
            out.append(f"Cwp = {p.cwp} >= 1: the entrance-angle regression "
                       f"carries (1 - Cwp)^0.30484, which drives i_E to "
                       f"exactly 90 deg, and c1 carries (90 - i_E)^-1.37565")
    elif not (0.0 < p.ie_deg < 90.0):
        out.append(f"i_E = {p.ie_deg} deg: c1 carries (90 - i_E)^-1.37565, so "
                   f"i_E must lie strictly inside (0, 90)")
    if p.abt > 0.0:
        if 0.31 * math.sqrt(p.abt) + p.tf - p.hb <= 0.0:
            out.append(f"bulb centre h_B = {p.hb} m against T_F = {p.tf} m: "
                       f"c3's denominator 0.31 sqrt(A_BT) + T_F - h_B <= 0")
        if p.tf - 1.5 * p.hb <= 0.0:
            out.append(f"bulb centre h_B = {p.hb} m against T_F = {p.tf} m: "
                       f"P_B = 0.56 sqrt(A_BT)/(T_F - 1.5 h_B) has a pole at "
                       f"h_B = 2 T_F / 3")
        if g * (p.tf - p.hb - 0.25 * math.sqrt(p.abt)) + 0.15 * speed ** 2 <= 0:
            out.append(f"A_BT = {p.abt} m^2 at T_F = {p.tf} m and "
                       f"{speed:.3f} m/s: Fn_i's radicand is negative")
    if p.at > 0.0 and p.at >= p.b * t * p.cm:
        out.append(f"transom area {p.at} m^2 >= midship area "
                   f"{p.b * t * p.cm:.2f} m^2: c5 = 1 - 0.8 A_T/(B T C_M) "
                   f"goes negative and R_W is computed from a negative "
                   f"amplitude — a plausible-looking wrong number")
    return tuple(out)


def particulars_from_floated(lwl: float, b: float, draught: float,
                             volume: float, cb: float, cp: float,
                             awp: float, lcb_pct: float) -> Particulars:
    """`Particulars` from a FLOATED hydrostatic state, in one place (gap E1b).

    The ladder holds `HydroState`, which carries `cb`, `cp`, `awp`, `b_wl_max`
    and `lwl_eff` but not the two coefficients Holtrop names: `cm` and `cwp`.
    Both are derivable — `cm = cb / cp` by definition, and
    `cwp = A_wp / (L_wl B_wl)` — and deriving them at the call site is how a
    number gets declared twice. This module owns the mapping because it owns
    what the symbols mean.

    Takes floats, not a `HydroState`: `navalai.holtrop` must not import the
    ladder it is a candidate model FOR. Even-keel is assumed (`tf = ta`), and
    appendages, bulb and immersed transom are zero for the small craft this
    grammar produces — stated here rather than left as defaults nobody read.
    """
    return Particulars(
        lwl=float(lwl), b=float(b), tf=float(draught), ta=float(draught),
        volume=float(volume), cm=float(cb) / max(float(cp), 1e-9),
        cwp=float(awp) / max(float(lwl) * float(b), 1e-9),
        lcb=float(lcb_pct))


def envelope_violations(p: Particulars, fn: float, cp: float,
                        re: float | None = None) -> tuple[str, ...]:
    """Which clauses of the method's stated applicability this case breaks.

    Empty tuple means the case sits inside the union of the validity bands.
    Each string names the clause AND the measured value, because "outside the
    envelope" without a number is not actionable.

    THE REYNOLDS CLAUSE (2026-08-19). This envelope had no Re check at all:
    every band above is DIMENSIONLESS in hull proportions (Fn, Cp, L/B, B/T),
    so nothing about SIZE was checked, and `total` returned valid=True for a
    0.5 m hull at Re 2.3e5 — a point `resistance.flow_regime` refuses,
    because ITTC-57 (the friction line this method is built on) is a fully
    turbulent correlation and the flow there is laminar. The L1H tier could
    badge-valid a hull the L1 tier refuses. The clause bar is the top of
    `limits.RE_TRANSITION_BAND` (5e6): Holtrop-Mennen's regression corpus is
    ship models and ships, all far above it, and ITTC 7.5-02-05-01 requires
    artificial turbulence stimulation below that same number — a regime the
    regression has no data in. `re=None` (an old caller) skips the clause
    rather than inventing a Reynolds number.
    """
    out: list[str] = []
    if re is not None and re < RE_TURBULENT_MIN:
        out.append(
            f"Re {re:.3g} < {RE_TURBULENT_MIN:.0e} — below the fully "
            f"turbulent support of the ITTC-57 line the method is built on "
            f"(transitional/laminar; limits.RE_TRANSITION_BAND)")
    lb = p.lwl / p.b
    bt = p.b / p.draught
    if fn > FN_MAX:
        out.append(f"Fn {fn:.3f} > {FN_MAX} — above the 1982 regression's "
                   f"support; the 1984 high-speed branch is not implemented")
    if not (CP_RANGE[0] <= cp <= CP_RANGE[1]):
        out.append(f"Cp {cp:.3f} outside [{CP_RANGE[0]}, {CP_RANGE[1]}]")
    if not (L_OVER_B_RANGE[0] <= lb <= L_OVER_B_RANGE[1]):
        out.append(f"L/B {lb:.2f} outside "
                   f"[{L_OVER_B_RANGE[0]}, {L_OVER_B_RANGE[1]}]")
    if not (B_OVER_T_RANGE[0] <= bt <= B_OVER_T_RANGE[1]):
        out.append(f"B/T {bt:.2f} outside "
                   f"[{B_OVER_T_RANGE[0]}, {B_OVER_T_RANGE[1]}]")
    return tuple(out)


def total(p: Particulars, speed: float, rho: float = RHO_SEA_HOLTROP,
          nu: float = NU_SEA_HOLTROP, g: float = G) -> HoltropResult:
    """Full Holtrop-Mennen calm-water resistance at `speed` [m/s].

    Returns every intermediate.  The result is badged, not refused, outside the
    method's envelope — see `HoltropResult.valid` and `.envelope_violations`.
    """
    bad = domain_errors(p, speed, g)
    if bad:
        raise ValueError(
            "Holtrop-Mennen has no value for these particulars:\n  - "
            + "\n  - ".join(bad))
    t = p.draught
    cb = block_coefficient(p.volume, p.lwl, p.b, t)
    cp = prismatic_coefficient(cb, p.cm)
    lr = length_of_run(p.lwl, cp, p.lcb)
    fn = speed / math.sqrt(g * p.lwl)

    c12_ = c12(t, p.lwl)
    c13_ = c13(p.c_stern)
    k1 = form_factor(cp, p.lcb, p.b, lr, c12_, c13_)
    s = p.s if p.s is not None else wetted_surface(
        p.lwl, p.b, t, p.cm, cb, p.cwp, p.abt)
    cf = ittc57_cf(speed, p.lwl, nu)
    q = 0.5 * rho * speed ** 2
    rf = cf * q * s
    rapp = q * p.s_app * p.k2_app * cf

    c7_ = c7(p.b, p.lwl)
    ie = (p.ie_deg if p.ie_deg is not None
          else half_angle_entrance(p.lwl, p.b, p.cwp, cp, p.lcb, lr, p.volume))
    c1_ = c1(c7_, t, p.b, ie)
    c3_ = c3(p.abt, p.b, t, p.tf, p.hb)
    c2_ = c2(c3_)
    c5_ = c5(p.at, p.b, t, p.cm)
    c16_ = c16(cp)
    m1_ = m1(p.lwl, t, p.b, p.volume, c16_)
    c15_ = c15(p.lwl, p.volume)
    m2_ = m2(c15_, cp, fn)
    lam = wave_length_parameter(cp, p.lwl, p.b)
    rw = wave_resistance(c1_, c2_, c5_, p.volume, fn, m1_, m2_, lam, rho, g)

    pb, fni, rb = bulbous_bow(p.abt, p.tf, p.hb, speed, rho, g)
    fnt, c6_, rtr = transom(p.at, p.b, p.cwp, speed, rho, g)

    c4_ = c4(p.tf, p.lwl)
    ca, ra = model_ship_correlation(p.lwl, cb, c2_, c4_, s + p.s_app, speed,
                                    rho)

    rt = rf * k1 + rapp + rw + rb + rtr + ra
    # Belt and braces after `domain_errors`. Honesty rule 1 wants every
    # quantity to carry {value, tier, sigma}; a NaN carries a tier and a sigma
    # too, and gap E10 is precisely a NaN passing a constraint because
    # `nan > 0.0` is False. Nothing non-finite leaves this function.
    if not math.isfinite(rt):
        raise ValueError(
            f"R_total came out {rt!r} — non-finite. domain_errors() did not "
            f"catch this input, which is a bug in domain_errors(), not a "
            f"property of the hull. Particulars: {p!r}, speed {speed} m/s")
    viol = envelope_violations(p, fn, cp, re=speed * p.lwl / nu)
    valid = not viol
    # Outside the envelope the declared band is meaningless, so it is inflated
    # to the size of the answer — the same convention as
    # navalai.resistance.total_resistance, and for the same reason.
    sigma = SIGMA_DECLARED * rt if valid else rt
    return HoltropResult(
        speed=speed, fn=fn, cb=cb, cp=cp, lr=lr, lcb=p.lcb,
        c12=c12_, c13=c13_, form_factor=k1, s=s, cf=cf, rf=rf, rapp=rapp,
        c7=c7_, ie=ie, c1=c1_, c3=c3_, c2=c2_, c5=c5_, c16=c16_, m1=m1_,
        c15=c15_, m2=m2_, lam=lam, rw=rw,
        pb=pb, fni=fni, rb=rb, fnt=fnt, c6=c6_, rtr=rtr,
        c4=c4_, ca=ca, ra=ra,
        total=rt, pe=rt * speed, sigma=sigma,
        tier="L1H" if valid else "L1H-INVALID", valid=valid,
        envelope_violations=viol)
