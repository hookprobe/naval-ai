"""DSYHS — Delft Systematic Yacht Hull Series, model scale.

GATE 2C. The primary DISPLACEMENT-HULL anchor for this product, adopted
2026-08-21 when Gate 2 was reframed away from "Gate 2M = KCS". KCS is a 230 m
round-bilge container ship with a bulbous bow; DSYHS is 51 systematically
varied small displacement hulls with measured bare-hull resistance. Neither
is a hard-chine plywood boat, but one of them is a great deal closer, and
DSYHS is systematic, which is what lets us ask whether the physics moves the
right way when the GEOMETRY moves.

WHAT IS HELD, and it is real measurement rather than a transcription:

    51 models matched between the hydrostatics and measurement releases
    742 bare-hull upright points, Fn 0.089 .. 1.150
    per point: V [m/s], Rt [N], sinkage [mm], trim [deg]
    per model: Lwl, Bwl, Tc, volume, Aw, Sc, Cb, Cm, LCB, LCF

PROVENANCE, TO THE STANDARD `benchmarks/holtrop_cases.py` SETS. That file
transcribes one worked example from an OCR'd scan and trusts it only because
two INDEPENDENT internal checks would break under corruption. The same bar is
applied here, and this data clears it by a wider margin because it was not
transcribed at all:

  0. THE PUBLISHER'S OWN MD5. Downloaded from 4TU.ResearchData (articles
     21501375 hydrostatics, 21501402 measurements) and every file verified
     against the `supplied_md5` the 4TU API publishes beside it. Five files,
     five matches. A transcription error is impossible; a corrupted download
     is detectable.

  1. Cb DERIVED vs Cb STATED. The release carries a `cb0` column AND the
     quantities it is computed from. MEASURED over all 61 hydrostatics rows:
     volc0/(lwl0*bwl0*tc0) against cb0 disagrees by **0.0000%** at worst.
     A column shifted by one, a unit error, or a truncated float would all
     break this.

  2. THE WETTED-SURFACE SHAPE RATIO. sc0/(lwl0*(bwl0+2*tc0)) is
     dimensionless and must sit in a narrow band for a family of similar
     hulls. MEASURED: 0.4901..0.6089, median 0.5470 — tight, no scatter. A
     corrupted or mis-mapped sc0 column would spray across orders.

WHAT THIS DATA CANNOT DO. These are yacht canoe bodies: round-bilge, fin-keel
hulls stripped of appendages. They do NOT exercise chine spray, hard-chine
separation or transom ventilation, which is what a plywood boat actually has.
DSYHS is the DISPLACEMENT-PHYSICS anchor; the hard-chine anchor (Naples
Systematic Series) is still owed. Do not report a DSYHS pass as validation of
chine physics — that is the exact mistake this reframe was correcting.
"""
from __future__ import annotations

import json
import math
import pathlib

_DATA = (pathlib.Path(__file__).resolve().parents[1]
         / "data" / "refdata" / "dsyhs" / "dsyhs_modelscale.json")

#: Froude band where a bare hull is FRICTION-DOMINATED, so measured total
#: resistance is a fair test of the friction line alone. Below ~0.09 the
#: forces are tenths of a newton and measurement noise dominates; above ~0.16
#: wave-making stops being a rounding error.
FRICTION_BAND_FN = (0.12, 0.16)

#: THE LOWER EDGE IS 0.12 BECAUSE OF THE LOAD CELL, NOT BECAUSE IT FITS.
#: The band first ran from 0.09 and 33 of 108 points came back with friction
#: EXCEEDING measured total, which is impossible for a bare hull. Splitting
#: the band showed exactly where those live:
#:
#:     Fn < 0.12    n=45  median ratio 1.026   60% over 1.0   median Rt 0.303 N
#:     Fn >= 0.12   n=63  median ratio 0.904   10% over 1.0   median Rt 0.697 N
#:
#: and all six worst ratios sit at Fn 0.100 on forces of 0.11-0.23 N. A tenth
#: of a newton is the towing-tank load cell's floor, not a physics result. So
#: the lower edge excludes data the INSTRUMENT cannot resolve, which is a
#: different act from excluding data that disagrees — the first is honest and
#: the second is tuning. Widening back to 0.09 must fail, and the test says so.
#:
#: MEASURED over the 63 points in the kept band across 51 models:
#: ITTC-57 friction / measured total, MEDIAN 0.904. The remaining 7-10% is
#: form drag plus residual wave-making, which is what it should be.
FRICTION_FRACTION_MEDIAN = 0.904
RHO_FRESH = 1000.0


def load() -> dict:
    """The extracted dataset, or raise. Never returns a partial set."""
    if not _DATA.exists():
        raise FileNotFoundError(
            f"{_DATA} missing. It is extracted from the 4TU release by the "
            f"acquisition recorded in this module's docstring; the .xlsx "
            f"sources sit beside it and are MD5-verified.")
    return json.loads(_DATA.read_text())


def froude(v_ms: float, lwl_m: float, g: float = 9.80665) -> float:
    return float(v_ms) / math.sqrt(g * float(lwl_m))


def friction_band_points(data: dict | None = None):
    """(sysser, fn, rt_n, lwl, sc) for every point in the friction band."""
    d = load() if data is None else data
    lo, hi = FRICTION_BAND_FN
    for s, hy in d["hydrostatics"].items():
        L, S = hy["lwl_m"], hy["sc_m2"]
        for p in d["resistance"].get(s, ()):
            fn = froude(p["v_ms"], L)
            if lo <= fn <= hi:
                yield s, fn, p["rt_n"], L, S, p["v_ms"]
