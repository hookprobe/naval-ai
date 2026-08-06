"""Holtrop-Mennen worked example — the published anchor for Gate 1H.

PROVENANCE, stated exactly (this file is the whole point of gap E1, so the
sourcing is written out rather than gestured at)
---------------------------------------------------------------------------
J. Holtrop and G.G.J. Mennen, "An approximate power prediction method",
*International Shipbuilding Progress* **29** (335), 166-170, Delft University
Press, 1982.  The paper closes with a fully worked numerical example: a
single-screw 25-knot ship, its principal particulars, and a table of EVERY
intermediate the method produces.  That example is transcribed below.

The copy read was a scanned reproduction of the paper circulating on document
hosts (pdfcoffee.com, doc id `holtrop-amp-mennen-an-approximate-power-
prediction-method`), NOT the publisher's typeset original — IOS Press /
SAGE hold it behind a paywall (doi 10.3233/ISP-1982-2933501) and it was not
accessed.  A scan can be OCR-corrupted, so the transcription is not trusted on
its face.  It is trusted because of two INDEPENDENT internal checks that an
OCR corruption would break:

  1. THE PRINTED COMPONENTS SUM TO THE PRINTED TOTAL.
     R_F(1+k1) + R_APP + R_W + R_B + R_TR + R_A
       = 869.63*1.156 + 8.83 + 557.11 + 0.049 + 0.00 + 221.98
       = 1793.26 kN, which is the printed R_total to the last digit.
  2. THE PRINTED TOTAL TIMES THE PRINTED SPEED IS THE PRINTED EFFECTIVE POWER.
     1793.26 kN * 12.8611 m/s = 23063 kW, which is the printed P_E.

Both hold, so the numbers below are the paper's numbers and not a scanner's.
`tests/test_holtrop.py` asserts check (1) directly, on the transcribed data,
before it asserts anything about our implementation — a validation set that
does not close against itself is not a validation set.

WHAT IS TRANSCRIBED, WHAT IS DERIVED, WHAT IS ABSENT
---------------------------------------------------
Honesty rule: an invented anchor is worse than no anchor.  So every constant
below is tagged.

  TRANSCRIBED  read directly off the paper's example table.
  DERIVED      not printed by the paper; back-solved from printed values and
               said so at the point of use.  There are exactly two, both in
               `DERIVED_INPUTS`.
  ABSENT       the paper states it but this reading could not recover it; see
               `NOT_VERIFIED`.  Nothing absent is guessed at.

UNITS: SI throughout.  Lengths m, areas m^2, volumes m^3, forces N in code
(the paper prints kN, and `Printed.unit` says which), speeds m/s.
"""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Physical constants the example implies.
#
# The paper's own convention (stated in its text) is sea water at 15 degrees
# centigrade, rho = 1025 kg/m^3.  The kinematic viscosity is the ITTC-1957
# value for that condition, 1.1883e-6 m^2/s, and it is CONFIRMED by the example
# rather than assumed: it is the value that reproduces the printed
# C_F = 0.001390 at L = 205 m and V = 12.8611 m/s.  1 knot = 0.514444 m/s
# likewise reproduces the printed Fn = 0.2868.
# g is NOT stated by the paper.  We use the repository's single-source
# `navalai.geometry.G` = 9.80665; g enters R_W and R_B linearly and Fn as
# 1/sqrt(g), so the choice between 9.80665 and 9.81 moves R_total by 0.03% —
# smaller than the tolerances below.  Recorded so nobody re-derives it.
# ---------------------------------------------------------------------------
RHO_SEA_15C = 1025.0      # kg/m^3   TRANSCRIBED (paper text)
NU_SEA_15C = 1.1883e-6    # m^2/s    ITTC-1957 15 C sea water; confirmed by C_F
KNOTS_TO_MS = 0.514444    # m/s per knot; confirmed by the printed Fn


# ---------------------------------------------------------------------------
# MAIN SHIP CHARACTERISTICS — all TRANSCRIBED.
# ---------------------------------------------------------------------------
INPUTS = {
    "lwl": 205.00,        # m    length on waterline
    "lpp": 200.00,        # m    length between perpendiculars (context only:
                          #      the method itself uses L = Lwl throughout)
    "b": 32.00,           # m    breadth moulded
    "tf": 10.00,          # m    draught forward
    "ta": 10.00,          # m    draught aft
    "volume": 37500.0,    # m^3  displacement volume, moulded
    "cm": 0.980,          # -    midship section coefficient
    "cwp": 0.750,         # -    waterplane area coefficient
    "abt": 20.0,          # m^2  transverse bulb area
    "hb": 4.0,            # m    centre of bulb area above keel
    "at": 16.0,           # m^2  transom area at rest
    "s_app": 50.0,        # m^2  wetted area of appendages
    "c_stern": 10.0,      # -    stern shape parameter (V-shaped sections)
    "speed_kn": 25.0,     # kn   ship speed
}

# lcb: the paper's input line reads "longitudinal centre of buoyancy 2.02% aft
# of 1/2 Lpp"; its RESULTS line reads "lcb -0.75%", which is the same position
# expressed the way every formula in the method wants it — per cent of Lwl
# FORWARD of 0.5 Lwl, negative aft.  -0.75 is TRANSCRIBED (it is printed); the
# 2.02%-of-Lpp figure is recorded here only because it is what the input table
# says, and the two are consistent for a hull whose 205 m waterline overhangs
# the 200 m perpendiculars aft by 5 m:
#     (100 - 0.0202*200 + 5) - 205/2 = -1.54 m -> -1.54/205 = -0.751%.
INPUTS["lcb"] = -0.75     # %    of Lwl, forward of 0.5 Lwl (negative = aft)


# ---------------------------------------------------------------------------
# DERIVED INPUTS — the two quantities the method needs that the example table
# does not print.  Neither is invented; both are back-solved from printed
# values, and the back-solve is written out so it can be checked.
# ---------------------------------------------------------------------------
DERIVED_INPUTS = {
    # Appendage form factor (1+k2).  The paper prints S_APP = 50 m^2 and
    # R_APP = 8.83 kN but not (1+k2).  R_APP = 1/2 rho V^2 S_APP (1+k2) C_F
    # with the printed C_F = 0.001390 inverts to
    #     (1+k2) = 8830 / (0.5*1025*12.8611^2 * 50 * 0.001390) = 1.499
    # and the paper's own table of approximate 1+k2 values gives "rudder behind
    # stern: 1.3-1.5".  So 1.5 it is — consistent with the appendage a
    # single-screw ship of this example would have.  DERIVED, not printed.
    "k2_app": 1.5,        # -    1+k2 for the appendage(s)
}

# The reference wetted surface used by R_A.  The paper prints S = 7381.45 m^2
# (hull) and S_APP = 50 m^2 separately, and does not print which one R_A rides
# on.  MEASURED both ways against the printed R_A = 221.98 kN:
#     on S alone       -> 220.68 kN   (-0.59%)
#     on S + S_APP     -> 222.07 kN   (+0.039%)
# so the example uses the TOTAL wetted surface, and `navalai.holtrop` does the
# same.  This is a determination from the data, recorded rather than assumed.
RA_USES_TOTAL_WETTED_SURFACE = True


# THE TOLERANCE RULE, and why it is these two arms and not one.
#
#   tol = max( 1 unit in the last printed decimal place,  RTOL_FLOOR * |value| )
#
# ARM 1 (printed precision) is the right bar for the dimensionless coefficients,
# where the paper's own rounding is the only disagreement possible: c15 prints
# to five places, so 1e-5 is all the source can resolve.  One unit and not a
# half, because the paper is inconsistent about rounding vs truncating — C_A
# prints 0.000352 for a value of 0.0003525 (truncated) while c1 prints 1.398
# for 1.3977 (rounded) — and half a unit would fail truncated rows for a reason
# that says nothing about the implementation.
#
# ARM 2 (relative floor) is needed because arm 1 is ABSURDLY tight on the
# dimensional rows: R_total prints as 1793.26 kN, so one unit in the last place
# is 1e-2 kN, i.e. 6 parts per million on a statistical resistance estimate.
# Nothing on earth reproduces that; demanding it would not be rigour, it would
# be a test that has to be special-cased away row by row.
#
# 5e-4 IS MEASURED, NOT CHOSEN FOR COMFORT.  Across all 33 transcribed rows the
# worst disagreement that arm 1 does not already cover is m2 at 0.0395%, then
# R_A 0.0387%, R_W 0.0285%, P_E 0.0197%, R_total 0.0184%, Fn_i 0.0077%.  The
# floor sits at 0.05%: a 1.27x margin on the worst row, which is enough to
# absorb the fact that the paper states neither g nor its knot conversion, and
# nowhere near enough to hide a wrong coefficient.  (The single largest
# relative gap anywhere is R_B at 0.383%, and it passes on arm 1 alone: the
# paper prints it as 0.049 kN, where one unit in the last place IS 2%.)
RTOL_FLOOR = 5.0e-4


@dataclass(frozen=True)
class Printed:
    """One value as the paper prints it, with the tolerance that implies.

    `decimals` is the number of decimal places PRINTED.  `atol` overrides the
    whole rule where — and only where — it provably has to; there are currently
    no overrides, and any that appear must carry their measured gap in `note`.
    """

    value: float
    decimals: int
    unit: str
    note: str = ""
    atol: float | None = None

    @property
    def tol(self) -> float:
        if self.atol is not None:
            return self.atol
        return max(10.0 ** (-self.decimals), RTOL_FLOOR * abs(self.value))


# ---------------------------------------------------------------------------
# THE RESULTS TABLE — all TRANSCRIBED, in the order the paper prints them.
# Keys match the attribute names on `navalai.holtrop.HoltropResult`.
# ---------------------------------------------------------------------------
EXPECTED = {
    "fn":       Printed(0.2868, 4, "-", "Froude number on Lwl"),
    "cp":       Printed(0.5833, 4, "-", "prismatic coefficient"),
    "lr":       Printed(81.385, 3, "m", "length of run"),
    "lcb":      Printed(-0.75, 2, "%", "as used by the formulae"),
    "c12":      Printed(0.5102, 4, "-"),
    "c13":      Printed(1.030, 3, "-"),
    "form_factor": Printed(1.156, 3, "-", "1+k1"),
    "s":        Printed(7381.45, 2, "m^2", "wetted surface of the bare hull"),
    "cf":       Printed(0.001390, 6, "-", "ITTC-1957"),
    "rf":       Printed(869.63, 2, "kN", "bare friction, WITHOUT the form factor"),
    "rapp":     Printed(8.83, 2, "kN"),
    "c7":       Printed(0.1561, 4, "-"),
    "ie":       Printed(12.08, 2, "deg", "half angle of entrance"),
    "c1":       Printed(1.398, 3, "-"),
    "c3":       Printed(0.02119, 5, "-"),
    "c2":       Printed(0.7595, 4, "-"),
    "c5":       Printed(0.9592, 4, "-"),
    "m1":       Printed(-2.1274, 4, "-"),
    # SIGN CORRECTED, and this is the one place the transcription departs from
    # what the scan shows.  The scanned table renders c15 as "1.69385"; the
    # method's own definition is c15 = -1.69385 for L^3/volume < 512, and the
    # scan's OWN NEXT LINE, m2 = -0.17087, is negative — which is impossible
    # from a positive c15 since m2 = c15 * Cp^2 * exp(...) and the other two
    # factors are positive.  So the minus sign was lost by the scan, not by
    # Holtrop.  Recorded here rather than silently fixed.
    "c15":      Printed(-1.69385, 5, "-", "sign restored from the definition"),
    # THE WORST ROW IN THE SET, and the one that sets RTOL_FLOOR.  Ours is
    # -0.170937 against a printed -0.17087: 6.8e-5 absolute, 6.8 units in the
    # last printed place, 0.0395% relative.  m2 depends on Fn through
    # exp(-0.1 Fn^-2), and the paper states neither g nor its knot conversion,
    # so a two-digit difference in the Fn its authors carried explains it
    # exactly — Fn 0.286794 reproduces -0.17087 against our 0.286841.  Recorded
    # rather than swept up.  The knock-on to R_W is 4e-6 relative, because m2
    # multiplies cos(lambda Fn^-2) = -0.064 at this speed.
    "m2":       Printed(-0.17087, 5, "-",
                        "worst row: 0.0395% high; sets RTOL_FLOOR"),
    "lam":      Printed(0.6513, 4, "-", "lambda"),
    "rw":       Printed(557.11, 2, "kN"),
    "pb":       Printed(0.6261, 4, "-", "bulb emergence parameter P_B"),
    "fni":      Printed(1.5084, 4, "-", "Froude number on bulb immersion"),
    "rb":       Printed(0.049, 3, "kN"),
    "fnt":      Printed(5.433, 3, "-", "Froude number on transom immersion"),
    # The scan's results table shows a value of 0.04 on the c6 line and a blank
    # on the c4 line — a one-row shift, because c4 = TF/L = 0.0488 clipped to
    # its ceiling of 0.04, while c6 is identically ZERO here: the method sets
    # c6 = 0 for FnT >= 5 and the printed FnT is 5.433.  The printed
    # R_TR = 0.00 kN confirms c6 = 0.  Both rows are restored to what the
    # method requires, and the reasoning is written down rather than assumed.
    "c6":       Printed(0.0, 2, "-", "zero because FnT = 5.433 >= 5"),
    "rtr":      Printed(0.00, 2, "kN"),
    "c4":       Printed(0.04, 2, "-", "TF/L = 0.0488 clipped to the 0.04 ceiling"),
    "ca":       Printed(0.000352, 6, "-"),
    "ra":       Printed(221.98, 2, "kN"),
    "total":    Printed(1793.26, 2, "kN"),
    "pe":       Printed(23063.0, 0, "kW", "effective power = R_total * V"),
}

# The paper's example continues past resistance into propulsion — C_V, c9,
# c11, Cp/i, w, c10, t, T, A_E/A_O, eta_R, c0.75, t/c0.75, dC_D, K_T/s, n,
# K_Qo, eta_0, P_S.  NONE of it is transcribed and none of it is tested,
# because `navalai.holtrop` implements RESISTANCE ONLY.  Listing it here is the
# point: Gate 1H anchors the resistance half of Holtrop-Mennen and nothing
# more, and the propulsion half remains unimplemented and unanchored.
NOT_IMPLEMENTED = (
    "wake fraction w", "thrust deduction t", "relative rotative efficiency",
    "open-water efficiency", "propeller design", "delivered/shaft power",
)

# What this reading of the paper could NOT recover, and therefore what is
# neither transcribed nor tested.  Left named rather than guessed at.
NOT_VERIFIED = (
    "Two of the five rows of the paper's validity table (cargo liners, and "
    "RoRo ships / car ferries). Three rows were confirmed from a secondary "
    "source that cites the paper; see navalai.holtrop.VALIDITY_BANDS.",
    "The 1984 re-analysis (Holtrop, 'A statistical re-analysis of resistance "
    "and propulsion data', ISP 31) and its high-speed wave-resistance branch "
    "R_W-b, the c17/m3/m4 coefficients, and the 0.40 < Fn < 0.55 "
    "interpolation. Not read, not implemented; the Fn <= 0.45 envelope is "
    "what keeps that omission honest.",
    "A published per-prediction uncertainty for the method. The sigma "
    "navalai.holtrop attaches is DECLARED, not sourced -- see its docstring.",
)


def check_internal_consistency() -> dict[str, float]:
    """Does the transcribed table close against itself?  Relative errors.

    This is the guard against a corrupted source: it uses ONLY the paper's own
    printed numbers, never ours.
    """
    comps = (EXPECTED["rf"].value * EXPECTED["form_factor"].value
             + EXPECTED["rapp"].value + EXPECTED["rw"].value
             + EXPECTED["rb"].value + EXPECTED["rtr"].value
             + EXPECTED["ra"].value)
    total = EXPECTED["total"].value
    v = INPUTS["speed_kn"] * KNOTS_TO_MS
    return {
        "components_vs_total": abs(comps - total) / total,
        "pe_vs_total_times_speed": abs(total * v - EXPECTED["pe"].value)
        / EXPECTED["pe"].value,
    }
