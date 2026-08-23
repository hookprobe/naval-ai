"""Hydrostatics of a PUBLISHED hull, computed from its OFFSET TABLE alone.

GATE E5. This module is the INDEPENDENT half of the E5 round-trip, and its
independence is the whole point: it must be able to say what a real hull's
particulars are WITHOUT asking NavalAI's geometry kernel, because a test in
which the kernel supplies both the question and the answer measures nothing.

THE RULE THIS FILE IS UNDER, AND IT IS ENFORCED BY A TEST:

    NOTHING HERE MAY IMPORT `navalai.geometry`, `navalai.hydrostatics`,
    `navalai.grammar` OR ANY OTHER PART OF THE KERNEL UNDER TEST.

`tests/test_e5_real_hulls.py::test_the_independent_measurement_is_actually_
independent` reads this file's source and fails if it does. That fence exists
because the tempting shortcut — measure the source hull with
`hydrostatics.solve` because it is right there and already works — would turn
E5 from an external reality test into `solve(x) == solve(x)`.

WHAT AN OFFSET TABLE IS HERE. The classical naval-architecture form: a grid of
half-breadths y[station][waterline], plus the keel and sheer height at each
station. Waterline heights are ABSOLUTE, measured up from the moulded baseline
(z = 0 at the lowest point of the canoe body). A cell is NaN where that
waterline passes below the local keel — an undefined offset, not a zero one,
and `sectional_area` treats the two differently.

WHY THE TABLE AND NOT THE CAD. The offsets are what gets committed and what
the gate reads. Extracting them needs OpenCASCADE and a 16 MB download;
reading them needs numpy. Anyone can re-run the gate, and the artifact under
version control is a human-readable table a naval architect can check by eye,
not a binary a reviewer must take on trust. `scripts/extract_e5_offsets.py`
is the acquisition side and runs once.
"""
from __future__ import annotations

import math

import numpy as np

#: A tabulated waterline this close to the design waterline IS the design
#: waterline. Belt and braces beside the full-precision column labels: a
#: table written by another tool must not lose its DWL row to a rounding in
#: the last decimal place.
_WL_EPS = 1e-9

#: Sea water is irrelevant here — every quantity this module returns is
#: geometric (volumes, areas, coefficients, centroids). Mass never enters.


def sectional_area(y_row: np.ndarray, z_wl: np.ndarray, z_keel: float,
                   z_water: float) -> float:
    """Submerged area [m^2] of ONE station, to the waterline `z_water`.

    `y_row` is the half-breadth at each height in `z_wl`, NaN where the
    waterline is below this station's keel. The area is 2*integral(y dz) from
    the local keel to `z_water`, with y = 0 pinned AT the keel — the hull
    closes there, and leaving that point out is what makes a naive trapezoid
    over the table alone overstate a fine section.
    """
    if not np.isfinite(z_keel) or z_keel >= z_water:
        return 0.0
    ok = np.isfinite(y_row) & (z_wl >= z_keel) & (z_wl <= z_water + _WL_EPS)
    if not ok.any():
        return 0.0
    z, y = z_wl[ok], y_row[ok]
    # PIN y = 0 AT THE KEEL ONLY IF THE TABLE DOES NOT ALREADY REACH IT.
    # A canoe body closes to a point at the keel, so the lowest tabulated
    # waterline sits just above a section that has already narrowed to
    # nothing, and leaving the closure out overstates the area. A FLAT-
    # BOTTOMED hull does not: Series 60 carries a finite half-breadth at the
    # baseline over its whole parallel middle body, and pinning a zero under
    # it would slice a spurious triangle off every midship section. The rule
    # is therefore asked of the TABLE, not assumed from the hull family.
    if z[0] > z_keel + 1e-9:
        z = np.concatenate(([z_keel], z))
        y = np.concatenate(([0.0], y))
    if z_water > z[-1]:
        # Interpolate the last sliver up to the waterline rather than
        # truncating it: with a coarse waterline spacing the truncation is a
        # systematic UNDER-estimate of displacement, and it biases every
        # coefficient the same way, which is the hardest kind of error to see.
        y = np.concatenate((y, [np.interp(z_water, z, y)]))
        z = np.concatenate((z, [z_water]))
    if len(z) < 2:
        return 0.0
    return float(2.0 * np.trapezoid(y, z))


def waterline_halfbreadth(y_row: np.ndarray, z_wl: np.ndarray, z_keel: float,
                          z_water: float) -> float:
    """Half-breadth [m] where this station meets the waterline plane."""
    if not np.isfinite(z_keel) or z_keel >= z_water:
        return 0.0
    ok = np.isfinite(y_row) & (z_wl >= z_keel)
    if not ok.any():
        return 0.0
    z, y = z_wl[ok], y_row[ok]
    if z[0] > z_keel + 1e-9:                     # see `sectional_area`
        z = np.concatenate(([z_keel], z))
        y = np.concatenate(([0.0], y))
    return float(np.interp(z_water, z, y))


def particulars(x: np.ndarray, z_wl: np.ndarray, y: np.ndarray,
                z_keel: np.ndarray, z_sheer: np.ndarray,
                z_water: float) -> dict:
    """Every E5 particular, from the offset table and a waterline height.

    `x` is station position [m] from the aft end of the table, `y` is
    (n_stations, n_waterlines) of half-breadths, `z_water` the design
    waterline height above the moulded baseline.

    LCB AND LCF ARE RETURNED IN THIS PROJECT'S ONE CONVENTION: percent of LWL,
    POSITIVE FORWARD of amidships, where amidships is the mid-point of the
    WATERLINE (not of the table, which usually runs past both ends into the
    overhangs). Every source that disagrees is converted at the point it is
    read, and the conversion is recorded in the ledger row — never here, and
    never silently.
    """
    A = np.array([sectional_area(y[i], z_wl, z_keel[i], z_water)
                  for i in range(len(x))])
    B = np.array([waterline_halfbreadth(y[i], z_wl, z_keel[i], z_water)
                  for i in range(len(x))])

    wet = A > 0.0
    if wet.sum() < 3:
        raise ValueError("fewer than three wetted stations — the waterline "
                         "does not intersect this hull")

    # The waterline ENDS are where the keel line crosses `z_water`, found by
    # interpolation on the keel curve rather than by taking the first and last
    # wet station. Taking the stations quantises LWL to the station spacing,
    # and LWL divides three of the six E5 parameters.
    xa, xf = _waterline_ends(x, z_keel, z_water)
    lwl = xf - xa

    # Integrate over the WETTED span only. The area is pinned to zero at a
    # waterline end ONLY where the hull actually tapers to it -- that is,
    # where a DRY station lies beyond the last wet one.
    #
    # AN IMMERSED TRANSOM DOES NOT TAPER, AND PRETENDING IT DOES IS A BUG
    # THIS CODE HAD. Pinning zero unconditionally put a fabricated 0 at the
    # same x as the transom station, and the duplicate-x guard then kept the
    # ZERO and discarded the transom's real sectional area -- deleting the
    # widest part of a transom-sterned hull from its own displacement. It did
    # not show up against DSYHS, whose canoe bodies end in a point at both
    # ends so the pinned zero was already true, and that is precisely why it
    # survived: a fixture family that cannot express the defect cannot catch
    # it. It was found by round-tripping a GENERATED hull, which has a
    # transom, and it is why `tests/test_e5_real_hulls.py` carries an
    # immersed-transom case with a closed-form answer.
    idx = np.flatnonzero(wet)
    i0, i1 = int(idx[0]), int(idx[-1])
    xs = list(x[i0:i1 + 1])
    As = list(A[i0:i1 + 1])
    Bs = list(B[i0:i1 + 1])
    if i0 > 0:
        xs.insert(0, xa)
        As.insert(0, 0.0)
        Bs.insert(0, 0.0)
    if i1 < len(x) - 1:
        xs.append(xf)
        As.append(0.0)
        Bs.append(0.0)
    xs, As, Bs = np.array(xs), np.array(As), np.array(Bs)

    vol = float(np.trapezoid(As, xs))
    aw = float(np.trapezoid(2.0 * Bs, xs))
    if vol <= 0 or aw <= 0:
        raise ValueError("non-positive volume or waterplane area")

    lcb_m = float(np.trapezoid(xs * As, xs) / vol)
    lcf_m = float(np.trapezoid(xs * 2.0 * Bs, xs) / aw)
    mid = 0.5 * (xa + xf)

    ax = float(As.max())
    bwl = float(2.0 * Bs.max())
    i_ax = int(np.argmax(As))
    # TWO BEAMS, BECAUSE THERE ARE TWO DEFINITIONS. The classical waterline
    # beam -- and the one DSYHS publishes as `bwl0` -- is the MAXIMUM over
    # stations. `grammar.PARAMS` documents the `BWL` gene as the beam "at the
    # max-AREA station", which is a different station whenever the widest
    # section is not the largest.
    #
    # THE DOCSTRING IS WRONG AND THE MEASUREMENT SETTLED IT. Over eight
    # sampled genomes the generated hull's MAXIMUM waterline half-breadth
    # equals the commanded BWL/2 (2.5555 vs 2.5555, 2.1446 vs 2.1446, ...),
    # while the half-breadth AT x_mb falls short of it by up to 0.2% -- and
    # the station of maximum beam sits as far as 0.65 L, nowhere near the
    # max-area station. So the gene is the classical maximum, the encoder
    # pins the source's maximum, and both are still returned so the ledger
    # can show the gap rather than absorb it.
    bwl_at_ax = float(2.0 * Bs[i_ax])
    tc = float(z_water - np.nanmin(z_keel))

    # D IS MEASURED AT THE MAX-AREA STATION, NOT AT MID-LENGTH, BECAUSE THAT
    # IS WHERE THE KERNEL PUTS IT. `grammar.PARAMS` documents D as "depth,
    # keel to sheer at midship", but MEASURED over eight sampled genomes the
    # generated hull's sheer-minus-keel equals the commanded D exactly at
    # `x_mb`, the max-AREA station, and `x_mb` ranges over [0.40, 0.68] --
    # so "midship" means mid-length only when x_mb happens to be 0.5.
    # Measuring the source at mid-length and the generated hull at x_mb
    # produced a SYSTEMATIC +0.5% to +1.3% depth error across the corpus,
    # every hull the same sign, which is what a definition mismatch looks
    # like and what a noisy measurement does not.
    #
    # Both are returned. The one at mid-length is what a naval architect
    # means by "depth amidships" and is kept for reference; the one at the
    # max-area station is the one the round-trip compares.
    x_ax = xs[i_ax]
    d_ax = _at(x, z_sheer, x_ax) - _at(x, z_keel, x_ax)
    d_mid = _at(x, z_sheer, mid) - _at(x, z_keel, mid)

    return {
        "LWL_m": lwl,
        "BWL_m": bwl,
        "BWL_at_max_area_m": bwl_at_ax,
        "T_m": tc,
        "D_m": float(d_ax),
        "D_at_mid_length_m": float(d_mid),
        "vol_m3": vol,
        "Aw_m2": aw,
        "Ax_m2": ax,
        "Cb": vol / (lwl * bwl * tc),
        "Cm": ax / (bwl * tc),
        "Cp": vol / (ax * lwl),
        "Cw": aw / (lwl * bwl),
        "LCB_pct": 100.0 * (lcb_m - mid) / lwl,
        "LCF_pct": 100.0 * (lcf_m - mid) / lwl,
        "x_max_area_frac": float((xs[i_ax] - xa) / lwl),
        "x_aft_m": xa,
        "x_fwd_m": xf,
        "n_wet_stations": int(wet.sum()),
    }


def sac(x: np.ndarray, z_wl: np.ndarray, y: np.ndarray, z_keel: np.ndarray,
        z_water: float) -> tuple[np.ndarray, np.ndarray]:
    """The sectional-area curve: (x/LWL from the aft waterline end, A/Ax)."""
    A = np.array([sectional_area(y[i], z_wl, z_keel[i], z_water)
                  for i in range(len(x))])
    xa, xf = _waterline_ends(x, z_keel, z_water)
    lwl = xf - xa
    return (x - xa) / lwl, A / A.max()


def _waterline_ends(x: np.ndarray, z_keel: np.ndarray,
                    z_water: float) -> tuple[float, float]:
    """Where the keel line crosses the waterline, aft end and forward end."""
    wet = np.isfinite(z_keel) & (z_keel < z_water)
    if not wet.any():
        raise ValueError("no station has its keel below the waterline")
    i0, i1 = int(np.argmax(wet)), int(len(wet) - 1 - np.argmax(wet[::-1]))
    xa = (x[i0] if i0 == 0 else
          _cross(x[i0 - 1], z_keel[i0 - 1], x[i0], z_keel[i0], z_water))
    xf = (x[i1] if i1 == len(x) - 1 else
          _cross(x[i1], z_keel[i1], x[i1 + 1], z_keel[i1 + 1], z_water))
    return float(xa), float(xf)


def _cross(x0: float, z0: float, x1: float, z1: float, zw: float) -> float:
    if not (math.isfinite(z0) and math.isfinite(z1)) or z1 == z0:
        return x0
    return x0 + (zw - z0) * (x1 - x0) / (z1 - z0)


def _at(x: np.ndarray, v: np.ndarray, xq: float) -> float:
    ok = np.isfinite(v)
    if not ok.any():
        return float("nan")
    return float(np.interp(xq, x[ok], v[ok]))
