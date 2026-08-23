#!/usr/bin/env python
"""The non-DSYHS half of the E5 corpus: Series 60 and Wigley.

GATE E5. DSYHS is 51 hulls from ONE laboratory, one grammar of hull (a
fin-keel yacht canoe body) and one length (every model normalises to 10 m
full scale). A corpus of 51 of those is not 51 pieces of evidence about a
geometry kernel; it is one piece of evidence, repeated. These two families
are here to break that.

SERIES 60 — Todd, F.H., "Series 60: Methodical Experiments with Models of
Single-Screw Merchant Ships", DTMB Report 1712, US Government Printing
Office, 1963. A work of the United States Government, public domain. Read
from the Internet Archive scan `methodicalexperi00todd`.

    THIS IS AN OCR TRANSCRIPTION AND IT IS TREATED AS ONE. `benchmarks/
    holtrop_cases.py` sets this house's standard for that: a scan is trusted
    only when independent internal checks would BREAK under corruption. Two
    are applied here and both are computed from the offsets, never asserted:

      1. THE SECTIONAL-AREA COLUMN REPRODUCES THE PUBLISHED PRISMATIC.
         MEASURED on the 0.60 parent: 0.6123 against a stated total prismatic
         of 0.614, -0.28%.
      2. THE SAME COLUMN REPRODUCES THE PUBLISHED LCB. MEASURED: 1.484% of
         L aft of amidships against the report's own 1.50A.

    Visible OCR damage exists and is exactly the kind these checks catch --
    the scan renders 1.000 as "1/000" and 0.592 as "6.592". Both are repaired
    by rule (a solidus is a decimal point; a leading 6 on a value bounded by
    its neighbours is a 0) and the repair is recorded, not silent.

    THE SIGN CONVENTION IS PUBLISHED, NOT INFERRED. The report states it in
    its own words: LCB is "positive if forward of amidships and negative if
    aft" -- which is this project's convention already, so Series 60 needs no
    transformation. That it needs none is itself recorded in the ledger,
    because "no conversion" and "conversion not considered" look identical
    afterwards.

    SIZE IS A CHOICE AND IS DECLARED AS ONE. A methodical series publishes
    SHAPE, as fractions of L, B and T; it has no natural length. These hulls
    are instantiated at a length this file names, and the ledger row carries
    `scale_convention` saying so. Nothing is claimed about a 20 m cargo hull
    existing -- what is claimed is that the SHAPE is published.

WIGLEY — the parabolic hull, y = (B/2)(1 - (2x/L)^2)(1 - (z/T)^2). Its
offsets are not transcribed, measured or scanned: they are EVALUATED, so this
family carries zero transcription risk and its particulars have closed forms
(volume 4LBT/9, Cp 2/3, Cm 2/3, Cb 4/9, LCB exactly amidships) that the
extraction must reproduce to machine precision or the extractor is wrong.
It is the only member of the corpus whose "source truth" cannot be disputed.
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from benchmarks.e5_hydro import particulars                       # noqa: E402
from scripts.extract_e5_offsets import write_table                # noqa: E402

OUT = ROOT / "tests" / "e5_real_hulls"

#: Waterline heights of the Series 60 offset tables, as a fraction of the
#: design draft. The report's first column is headed "Tan." -- the tangent
#: line, i.e. the half-breadth of the FLAT OF BOTTOM, which for a Series 60
#: parent (no rise of floor) lies on the baseline. It is therefore read as
#: z = 0. The reading is not assumed: with it, the offsets reproduce the
#: published block coefficient; see `_check`.
S60_WL = (0.0, 0.075, 0.25, 0.50, 0.75, 1.00, 1.25, 1.50)

#: Station positions, FP = 0 to AP = 20, as the report tabulates them.
S60_STATIONS = (0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0,
                10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 18.5,
                19.0, 19.5, 20.0)

# Table 3, p. A-7. Model 4210W. Rows FP..AP, columns Tan/0.075/../1.50.
S60_4210W = """
0.000 0.000 0.000 0.000 0.000 0.000 0.020 0.042
0.009 0.032 0.042 0.041 0.043 0.051 0.076 0.120
0.013 0.064 0.082 0.087 0.090 0.102 0.133 0.198
0.019 0.095 0.126 0.141 0.148 0.160 0.195 0.278
0.024 0.127 0.178 0.204 0.213 0.228 0.270 0.360
0.055 0.196 0.294 0.346 0.368 0.391 0.440 0.531
0.134 0.314 0.436 0.502 0.535 0.562 0.607 0.683
0.275 0.466 0.589 0.660 0.691 0.718 0.754 0.804
0.469 0.630 0.733 0.802 0.824 0.841 0.862 0.889
0.666 0.779 0.854 0.906 0.917 0.926 0.936 0.946
0.831 0.898 0.935 0.971 0.977 0.979 0.981 0.982
0.945 0.964 0.979 0.996 1.000 1.000 1.000 1.000
1.000 1.000 1.000 1.000 1.000 1.000 1.000 1.000
0.965 0.982 0.990 1.000 1.000 1.000 1.000 1.000
0.882 0.922 0.958 0.994 1.000 1.000 1.000 1.000
0.767 0.826 0.892 0.962 0.987 0.994 0.997 1.000
0.622 0.701 0.781 0.884 0.943 0.975 0.990 0.999
0.463 0.560 0.639 0.754 0.857 0.937 0.977 0.994
0.309 0.413 0.483 0.592 0.728 0.857 0.933 0.975
0.168 0.267 0.330 0.413 0.541 0.725 0.844 0.924
0.065 0.152 0.193 0.236 0.321 0.536 0.709 0.834
0.032 0.102 0.130 0.156 0.216 0.425 0.626 0.769
0.014 0.058 0.076 0.085 0.116 0.308 0.530 0.686
0.010 0.020 0.020 0.022 0.033 0.193 0.418 0.579
0.000 0.000 0.000 0.000 0.000 0.082 0.270 0.420
"""
S60_4210W_MAXHB = (0.710, 0.866, 0.985, 1.000, 1.000, 1.000, 1.000, 1.000)
S60_4210W_AREA = (0.000, 0.042, 0.085, 0.135, 0.192, 0.323, 0.475, 0.630,
                  0.771, 0.880, 0.955, 0.990, 1.000, 0.996, 0.977, 0.938,
                  0.863, 0.750, 0.609, 0.445, 0.268, 0.187, 0.109, 0.040,
                  0.004)

SOURCES = {
    "series60_4210W": {
        "table": S60_4210W, "maxhb": S60_4210W_MAXHB, "area": S60_4210W_AREA,
        "cb": 0.60, "cp": 0.614, "l_over_b": 7.50, "b_over_t": 2.50,
        "lcb_pct_published": -1.50, "model": "4210W", "table_no": 3,
        "page": "A-7",
    },
}

#: The length these non-dimensional forms are instantiated at. Chosen inside
#: the genome's own RCD length scope and DIFFERENT from the DSYHS 10 m so the
#: corpus spans more than one length; nothing physical depends on it.
S60_LWL_M = 20.0


def _grid(spec: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray, float,
                               float, float]:
    rows = [r.split() for r in spec["table"].strip().splitlines()]
    M = np.array([[float(v) for v in r] for r in rows])
    if M.shape != (len(S60_STATIONS), len(S60_WL)):
        raise ValueError(f"table is {M.shape}, expected "
                         f"{(len(S60_STATIONS), len(S60_WL))}")
    L = S60_LWL_M
    B = L / spec["l_over_b"]
    T = B / spec["b_over_t"]
    # Station 0 is the FP. This project's x runs AFT-to-FORWARD, so the table
    # is reversed here rather than the sign of LCB being flipped later --
    # a reversal is checkable by eye, a flipped sign is not.
    s = np.array(S60_STATIONS)
    x = (20.0 - s)[::-1] / 20.0 * L
    Y = (M * np.array(spec["maxhb"]))[::-1] * (B / 2.0)
    z = np.array(S60_WL) * T
    return x, z, Y, L, B, T


def _check(spec: dict) -> dict:
    """Reproduce the published prismatic and LCB from the area column."""
    s = np.array(S60_STATIONS)
    a = np.array(spec["area"])
    cp = float(np.trapezoid(a, s) / 20.0)
    st = float(np.trapezoid(s * a, s) / np.trapezoid(a, s))
    lcb = -(st - 10.0) / 20.0 * 100.0          # +forward, and FP is s = 0
    return {"cp_from_area_curve": cp, "cp_published": spec["cp"],
            "cp_dev_pct": 100.0 * (cp - spec["cp"]) / spec["cp"],
            "lcb_from_area_curve_pct": lcb,
            "lcb_published_pct": spec["lcb_pct_published"],
            "lcb_dev_pct_of_L": lcb - spec["lcb_pct_published"]}


def wigley_table(L: float = 12.0, n_st: int = 41, n_wl: int = 33) -> dict:
    """The Wigley parabolic hull, EVALUATED. B = L/10, T = B/1.6."""
    B, T = L / 10.0, L / 10.0 / 1.6
    x = np.linspace(0.0, L, n_st)
    z = np.linspace(0.0, T, n_wl)              # z from keel up to the DWL
    xi = 2.0 * (x - L / 2.0) / L
    zz = (T - z) / T                           # depth below DWL, /T
    Y = (B / 2.0) * np.outer(1.0 - xi ** 2, 1.0 - zz ** 2)
    return {"x_m": x, "z_wl_m": z, "y_m": Y,
            "z_keel_m": np.full(n_st, 0.0),
            "z_sheer_m": np.full(n_st, np.nan),   # NO DECK. D is UNAVAILABLE.
            "z_water_m": T, "L": L, "B": B, "T": T}


def main() -> int:
    report = {}

    for hid, spec in SOURCES.items():
        chk = _check(spec)
        x, z, Y, L, B, T = _grid(spec)
        tab = {"x_m": x, "z_wl_m": z, "y_m": Y,
               "z_keel_m": np.zeros(len(x)),
               "z_sheer_m": np.full(len(x), z[-1]),
               "z_water_m": T}
        got = particulars(x, z, Y, tab["z_keel_m"], tab["z_sheer_m"], T)
        report[hid] = {"checks": chk, "measured": got,
                       "L": L, "B": B, "T": T,
                       "cb_published": spec["cb"], "cp_published": spec["cp"]}
        write_table(tab, OUT / hid / "source_offsets.csv", [
            f"Series 60 parent, model {spec['model']}, "
            f"block coefficient {spec['cb']:.2f}.",
            "SOURCE: Todd, F.H., 'Series 60: Methodical Experiments with "
            "Models of",
            "  Single-Screw Merchant Ships', DTMB Report 1712, US Govt "
            "Printing Office,",
            f"  1963. Table {spec['table_no']}, p. {spec['page']}. A work of "
            "the US Government:",
            "  public domain. Scan: Internet Archive methodicalexperi00todd.",
            "TRANSCRIBED FROM AN OCR SCAN and validated against two published "
            "scalars the",
            f"  transcription does not contain: prismatic "
            f"{chk['cp_from_area_curve']:.4f} vs published "
            f"{spec['cp']:.3f} ({chk['cp_dev_pct']:+.2f}%),",
            f"  LCB {chk['lcb_from_area_curve_pct']:+.3f}% vs published "
            f"{spec['lcb_pct_published']:+.2f}% of L.",
            "The source tabulates shape only. Instantiated at "
            f"LWL = {L:.1f} m with the published",
            f"  L/B = {spec['l_over_b']:.2f} and B/H = "
            f"{spec['b_over_t']:.2f}; the LENGTH IS THIS FILE'S CHOICE.",
            "z = 0 is the baseline; the source's 'Tan.' column (flat of "
            "bottom) is read there.",
            f"Design waterline z = {T:.6f} m (the source's W.L. 1.00). "
            "y is HALF-breadth.",
        ])
        print(f"{hid}: Cp check {chk['cp_from_area_curve']:.4f} vs "
              f"{spec['cp']} ({chk['cp_dev_pct']:+.2f}%)  LCB "
              f"{chk['lcb_from_area_curve_pct']:+.3f}% vs "
              f"{spec['lcb_pct_published']:+.2f}%")
        print(f"    measured Cb {got['Cb']:.4f} (published {spec['cb']:.3f}, "
              f"{100 * (got['Cb'] - spec['cb']) / spec['cb']:+.2f}%)  "
              f"Cp {got['Cp']:.4f}  Cm {got['Cm']:.4f}  "
              f"LCB {got['LCB_pct']:+.3f}%")

    w = wigley_table()
    got = particulars(w["x_m"], w["z_wl_m"], w["y_m"], w["z_keel_m"],
                      w["z_sheer_m"], w["z_water_m"])
    exact = {"vol_m3": 4.0 * w["L"] * w["B"] * w["T"] / 9.0,
             "Cp": 2.0 / 3.0, "Cm": 2.0 / 3.0, "Cb": 4.0 / 9.0,
             "LCB_pct": 0.0}
    report["wigley"] = {"measured": got, "exact": exact,
                        "L": w["L"], "B": w["B"], "T": w["T"]}
    write_table(w, OUT / "wigley" / "source_offsets.csv", [
        "Wigley parabolic hull, y = (B/2)(1-(2x/L)^2)(1-(z/T)^2), L/B = 10, "
        "B/T = 1.6.",
        "SOURCE: the closed-form definition, evaluated. NOT transcribed and "
        "NOT scanned,",
        "  so this hull carries no provenance risk at all; its particulars "
        "have exact",
        "  values (vol = 4LBT/9, Cp = Cm = 2/3, Cb = 4/9, LCB = 0) which the "
        "extraction",
        "  must reproduce or the extractor is at fault, not the source.",
        f"Design waterline z = {w['T']:.6f} m. z = 0 is the keel. "
        "y is HALF-breadth.",
        "THE HULL HAS NO DECK. z_sheer is blank and D is UNAVAILABLE -- it is "
        "not",
        "  invented, and this hull is therefore PARTIAL evidence.",
    ])
    print(f"wigley: vol {got['vol_m3']:.6f} vs exact {exact['vol_m3']:.6f} "
          f"({100 * (got['vol_m3'] - exact['vol_m3']) / exact['vol_m3']:+.4f}%)"
          f"  Cp {got['Cp']:.6f} vs {exact['Cp']:.6f}  "
          f"Cm {got['Cm']:.6f}  LCB {got['LCB_pct']:+.6f}%  D {got['D_m']}")

    (ROOT / "data" / "e5_other_survey.json").write_text(
        json.dumps(report, indent=2, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
