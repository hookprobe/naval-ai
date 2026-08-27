#!/usr/bin/env python
"""Build the E5-CHINE corpus. GATE E5-CHINE.

E5 validated the geometry kernel against published ROUND-BILGE and
mathematical hulls. It did not, and could not, say anything about hard-chine
hulls -- and NavalAI exists to design plywood stitch-and-glue boats, which
are hard-chine by construction. E5-CHINE is the separate gate for that
branch, and it is separate on purpose: `E5 = GREEN, E5-CHINE = RED` is an
honest pair of statements, while one merged gate would let "NavalAI can
reproduce real hulls" be quoted without qualification.

THE SOURCE. Fridsma, G., "A Systematic Study of the Rough-Water Performance
of Planing Boats", Davidson Laboratory / Stevens Institute of Technology,
Report R-1275, November 1969. Prepared for the Naval Ship Systems Command
General Hydromechanics Research Program. The document carries "Approved for
public release; distribution is unlimited" on its own cover, and was read
from the DTIC accession AD0708694.

WHY THIS SOURCE IS UNUSUALLY STRONG, and it is worth being precise about the
distinction the E5-CHINE brief draws. This is NOT a body plan digitised off
a scan. Figure 1, "Lines of Prismatic Models", PRINTS THE EQUATIONS:

    chine planform   (x/9)^2 + (y/4.5)^2   = 1
    keel profile     (x/9)^2 + (8y/4.5)^2  = 1

with a 9.00 in beam, a bow one beam long, model lengths 36/45/54 in
(L/b = 4, 5, 6), deadrise 10/20/30 deg, a depth of 5 5/8 in, and vertical
topsides above the chine. Everything else is stated in the text (p. 9):
"Sections aft of the bow were constant hard-chine prismatic forms". So the
geometry is EVALUATED from published closed forms, exactly as the Wigley hull
is in E5 -- `geometry_status = PUBLISHED_PARAMETRIC`, with no transcription
and no digitisation anywhere in the chain.

THE WATERLINE IS PUBLISHED TOO, which a planing hull otherwise lacks: the
report tests at load coefficients C_delta = Delta/(w b^3) of 0.304, 0.608 and
0.912, so the design condition is "floating at rest at a published load",
not a draft this file invented.

SIZE IS A DECLARED CHOICE. Every dimension in the source scales with the
beam, so the family has no natural size; it is instantiated at a beam this
file names, inside the genome's own RCD length scope. Nothing is claimed
about a boat of that size existing -- what is claimed is that the SHAPE is
published.
"""
from __future__ import annotations

import csv
import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from benchmarks.e5_chine import chine_metrics                     # noqa: E402
from benchmarks.e5_hydro import particulars                       # noqa: E402
from scripts.extract_e5_offsets import write_table                # noqa: E402

OUT = ROOT / "tests" / "e5_hard_chine"

#: Beam the family is instantiated at. 1.0 m with L/b 4..6 gives 4-6 m hulls,
#: inside the genome's 2.5-24 m box and squarely in the size this product is
#: for. The source is dimensionless in beam; this is the only free choice.
BEAM_M = 1.0

#: Published load coefficient used for the design waterline. The middle of
#: the three the report tests.
C_DELTA = 0.608

#: Everything below is READ OFF FIGURE 1 as a ratio to the beam, so nothing
#: depends on the 9 in model size.
BOW_LEN = 1.0            # bow is one beam long (text p. 9 and Fig. 1)
KEEL_RISE = 0.0625       # keel-profile semi-axis 4.5/8 in over a 9 in beam
DEPTH = 0.625            # 5 5/8 in over a 9 in beam
HALF_BEAM = 0.5

MODELS = [
    ("fridsma_b10_lb5", 10.0, 5),
    ("fridsma_b20_lb4", 20.0, 4),
    ("fridsma_b20_lb5", 20.0, 5),
    ("fridsma_b20_lb6", 20.0, 6),
    ("fridsma_b30_lb5", 30.0, 5),
]


def hull(beta_deg: float, l_over_b: int, b: float = BEAM_M,
         n_st: int = 81, n_wl: int = 41):
    """Offsets of one Fridsma model, EVALUATED from the published equations."""
    L = l_over_b * b
    tb = np.tan(np.radians(beta_deg))
    D = DEPTH * b
    x = np.linspace(0.0, L, n_st)
    u = np.clip(x - (L - BOW_LEN * b), 0.0, BOW_LEN * b)   # fwd of bow origin
    e = np.sqrt(np.clip(1.0 - (u / (BOW_LEN * b)) ** 2, 0.0, 1.0))
    y_chine = HALF_BEAM * b * e
    z_keel = KEEL_RISE * b * (1.0 - e)
    z_chine = z_keel + y_chine * tb
    z = np.linspace(0.0, D, n_wl)
    Y = np.full((n_st, n_wl), np.nan)
    for i in range(n_st):
        for j, zz in enumerate(z):
            if zz < z_keel[i] - 1e-12:
                continue
            Y[i, j] = (min((zz - z_keel[i]) / tb, y_chine[i])
                       if zz <= z_chine[i] else y_chine[i])
    return {"x_m": x, "z_wl_m": z, "y_m": Y, "z_keel_m": z_keel,
            "z_sheer_m": np.full(n_st, D), "y_chine_m": y_chine,
            "z_chine_m": z_chine, "L": L, "B": b, "D": D, "beta": beta_deg}


def design_waterline(h: dict, c_delta: float = C_DELTA) -> float:
    """The draft at which the hull displaces the PUBLISHED load."""
    vol = c_delta * h["B"] ** 3
    lo, hi = 1e-5, h["D"]
    for _ in range(80):
        m = 0.5 * (lo + hi)
        try:
            v = particulars(h["x_m"], h["z_wl_m"], h["y_m"], h["z_keel_m"],
                            h["z_sheer_m"], m)["vol_m3"]
        except ValueError:
            lo = m
            continue
        if v < vol:
            lo = m
        else:
            hi = m
    return 0.5 * (lo + hi)


def main() -> int:
    rows = []
    for hid, beta, lb in MODELS:
        h = hull(beta, lb)
        tw = design_waterline(h)
        p = particulars(h["x_m"], h["z_wl_m"], h["y_m"], h["z_keel_m"],
                        h["z_sheer_m"], tw)
        cm = chine_metrics(h["x_m"], h["y_chine_m"], h["z_chine_m"],
                           h["z_keel_m"], h["z_sheer_m"], p["LWL_m"],
                           p["x_aft_m"])
        d = OUT / hid
        write_table({**h, "z_water_m": tw}, d / "source_offsets.csv", [
            f"Fridsma prismatic planing model, deadrise {beta:.0f} deg, "
            f"L/b = {lb}.",
            "SOURCE: Fridsma, G., 'A Systematic Study of the Rough-Water "
            "Performance of",
            "  Planing Boats', Davidson Laboratory, Stevens Institute of "
            "Technology,",
            "  Report R-1275, November 1969. DTIC AD0708694. The report "
            "carries",
            "  'Approved for public release; distribution is unlimited'.",
            "GEOMETRY STATUS: PUBLISHED_PARAMETRIC. Figure 1 PRINTS the "
            "equations --",
            "  chine planform (x/9)^2+(y/4.5)^2=1, keel profile "
            "(x/9)^2+(8y/4.5)^2=1 --",
            "  and the text (p. 9) states the sections aft of the bow are "
            "constant",
            "  hard-chine prismatic forms. NOTHING HERE IS DIGITISED FROM A "
            "DRAWING.",
            f"Instantiated at beam {BEAM_M:.3f} m; the source is "
            f"dimensionless in beam and",
            "  THE SIZE IS THIS FILE'S CHOICE. Depth 5 5/8 in / 9 in beam, "
            "bow one beam.",
            f"Design waterline from the PUBLISHED load coefficient "
            f"C_delta = {C_DELTA} :",
            f"Design waterline z = {tw:.9g} m. z = 0 is the keel aft. "
            "y is HALF-breadth.",
            "Topsides are VERTICAL above the chine (Fig. 1 body plan); the "
            "chine curve",
            "  itself is in chine.csv beside this file.",
        ])
        with (d / "chine.csv").open("w", newline="") as fh:
            fh.write("# chine curve of the same hull, from the same "
                     "published equations\n")
            w = csv.writer(fh)
            w.writerow(["x_m", "y_chine_m", "z_chine_m"])
            for i in range(len(h["x_m"])):
                w.writerow([f"{h['x_m'][i]:.6f}", f"{h['y_chine_m'][i]:.6f}",
                            f"{h['z_chine_m'][i]:.6f}"])
        (d / "expected.json").write_text(json.dumps(
            {"id": hid, "source_particulars": p,
             "chine": {k: v.tolist() for k, v in cm.items()},
             "beta_deg": beta, "l_over_b": lb, "c_delta": C_DELTA,
             "geometry_status": "PUBLISHED_PARAMETRIC"},
            indent=2, default=float))
        rows.append({
            "source_id": "fridsma_R1275", "family": "Fridsma R-1275",
            "hull_id": hid,
            "original_title": "A Systematic Study of the Rough-Water "
                              "Performance of Planing Boats",
            "authors": "Fridsma, G.", "year": 1969,
            "institution": "Davidson Laboratory, Stevens Institute of "
                           "Technology",
            "publication": "Report R-1275; DTIC AD0708694",
            "source_url": "https://apps.dtic.mil/sti/tr/pdf/AD0708694.pdf",
            "source_type": "government technical report",
            "public_domain_status": "approved for public release, "
                                    "distribution unlimited",
            "geometry_available": "YES", "offsets_available": "PARAMETRIC",
            "body_plan_available": "YES", "profile_available": "YES",
            "station_count": len(h["x_m"]),
            "waterline_count": len(h["z_wl_m"]),
            "LWL": p["LWL_m"], "BWL": p["BWL_m"], "T": p["T_m"],
            "D": p["D_m"], "Cp": p["Cp"], "Cb": p["Cb"], "Cm": p["Cm"],
            "LCB": p["LCB_pct"],
            "deadrise": beta, "chine_type": "single",
            "hard_chine": "YES", "warped": "NO", "double_chine": "NO",
            "source_page": "p. 9 (text), Fig. 1 (equations)",
            "source_figure": "Fig. 1, Lines of Prismatic Models",
            "source_table": "",
            "extraction_method": "evaluated from the equations printed in "
                                 "Fig. 1; no digitisation",
            "geometry_status": "PUBLISHED_PARAMETRIC",
            "checksum": "md5 fa37451fac6651d8b6f598164be5de9a (PDF)",
            "confidence": "HIGH",
            "notes": f"instantiated at beam {BEAM_M} m; design waterline "
                     f"from published C_delta {C_DELTA}",
        })
        print(f"{hid:20s} LWL {p['LWL_m']:.3f} BWL {p['BWL_m']:.3f} "
              f"T {p['T_m']:.4f} D {p['D_m']:.3f} Cp {p['Cp']:.4f} "
              f"Cb {p['Cb']:.4f} LCB {p['LCB_pct']:+.2f}%  "
              f"deadrise@0.5L {cm['deadrise_deg'][5]:.1f} deg")

    out = ROOT / "data" / "e5_hard_chine_sources.csv"
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"\n{len(rows)} hard-chine hulls -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# ---------------------------------------------------------------------------
# The round-trip attempt, and what it costs to be honest about the answer.
# ---------------------------------------------------------------------------

def roundtrip() -> int:
    """Encode each hard-chine hull, and record exactly what happens.

    TWO RESULTS ARE RECORDED AND THEY MUST NOT BE CONFUSED.

    `as_published` pins all six at the source's own values, which is the only
    thing that counts as a pass. For this family it does not even reach the
    geometry kernel: a prismatic planing hull has Cp ~ 0.95, the genome's box
    stops at 0.710, and the kernel's own sectional-area-curve family stops at
    ~0.848 whatever the box says. The refusal is recorded verbatim.

    `nearest_expressible` then clamps Cp to what the kernel CAN build and
    fits the shape genes. It is a diagnostic, not a result: it answers "how
    close can this grammar get, and what does it get wrong", and every record
    it writes is labelled `is_pass: false` so no later reader can quote it as
    agreement.
    """
    import json as _json

    from navalai import geometry, grammar
    from scripts.build_e5_corpus import fit, measure_back, source_record

    cp_i = grammar.NAMES.index("Cp")
    box_hi = float(grammar.HIGH[cp_i])
    out = {}
    for hid, beta, lb in MODELS:
        src = source_record(hid, OUT)
        p = src["particulars"]
        six = {"LWL": p["LWL_m"], "BWL": p["BWL_m"], "T": p["T_m"],
               "D": p["D_m"], "Cp": p["Cp"], "lcb": p["LCB_pct"]}
        mid = {n: float(0.5 * (grammar.LOW[i] + grammar.HIGH[i]))
               for i, n in enumerate(grammar.NAMES) if n not in six}
        rec = {"id": hid, "source_Cp": p["Cp"], "genome_Cp_ceiling": box_hi}
        # AS PUBLISHED: does ANY setting of the free genes build this hull with
        # all six pinned at the source's own values? That is a SEARCH, not a
        # point. Building once with the free genes at mid-box was the wrong
        # question and gave the wrong answer: a prismatic hull needs a long
        # parallel middle body and no keel rise, and mid-box supplies neither.
        try:
            # pmb FREE: a Fridsma model is a prismatic hull, and the
            # parallel middle body is the feature the E5 clamp table
            # (round-bilge yachts) zeroes out. r_stem stays 0 — the chine
            # planform ellipse closes to a point at the stem.
            g, res, six_used, grid, r = fit(
                src2_for(src, p), seed=11, maxiter=60,
                ceilings={"stem_depth": 0.0, "flare_len": 0.0,
                          "r_stem": 0.0})
            rec["as_published"] = {
                "status": "BUILT", "is_pass": True,
                "geom_rms_m": res["rms_m"],
                "geom_rms_pct_halfbeam": res["rms_pct_halfbeam"],
                "geom_max_m": res["max_m"],
                "genome": {k: float(v) for k, v in grammar.named(g).items()},
            }
        except Exception as exc:                            # noqa: BLE001
            rec["as_published"] = {"status": "REFUSED",
                                   "refusal": str(exc), "is_pass": False}

        if rec["as_published"]["status"] == "BUILT":
            out[hid] = rec
            print(f"{hid:20s} as-published BUILT    | Cp {p['Cp']:.4f} | "
                  f"geom rms "
                  f"{rec['as_published']['geom_rms_pct_halfbeam']:.2f}% "
                  f"halfbeam", flush=True)
            (OUT / hid / "residuals.json").write_text(
                _json.dumps(rec, indent=2, default=float))
            continue

        # Nearest expressible: Cp clamped, everything else at the source.
        cp_max = _max_buildable_cp(six, mid)
        # the measured reach is part of the RECORD, not only of the print:
        # the gate's "the reason is a number" test cites it, and for a hull
        # whose nearest-expressible fit also refuses (b30 at 0.95) it was
        # otherwise lost with the print buffer
        rec["max_buildable_cp"] = cp_max
        clamped = dict(six)
        clamped["Cp"] = cp_max
        src2 = dict(src)
        src2["particulars"] = dict(p)
        src2["particulars"]["Cp"] = cp_max
        try:
            # same clamp table as the as-published attempt: a prismatic
            # hull needs its pmb free HERE too, or the clamped-Cp retry
            # refuses for a reason that has nothing to do with the clamp
            g, res, _, _, r = fit(src2, seed=11, maxiter=40,
                                  ceilings={"stem_depth": 0.0,
                                            "flare_len": 0.0,
                                            "r_stem": 0.0})
            mb = measure_back(g, src2)
            rec["nearest_expressible"] = {
                "is_pass": False,
                "why": "Cp was CLAMPED to what the kernel can build; the "
                       "source value is not represented",
                "Cp_clamped_to": cp_max, "Cp_source": p["Cp"],
                "Cp_shortfall": p["Cp"] - cp_max,
                "geom_rms_m": res["rms_m"],
                "geom_rms_pct_halfbeam": res["rms_pct_halfbeam"],
                "geom_max_m": res["max_m"],
                "measured_back_Cp": mb["Cp"],
                "genome": {k: float(v) for k, v in grammar.named(g).items()},
            }
        except Exception as exc:                            # noqa: BLE001
            rec["nearest_expressible"] = {"is_pass": False,
                                          "status": "REFUSED",
                                          "refusal": str(exc)}
        out[hid] = rec
        a = rec["as_published"]
        n = rec.get("nearest_expressible", {})
        print(f"{hid:20s} REFUSED | Cp source {p['Cp']:.4f}, largest the "
              f"kernel will build at this hull's other five: {cp_max:.4f} "
              f"| nearest-expressible rms "
              f"{n.get('geom_rms_pct_halfbeam', float('nan')):.2f}% halfbeam",
              flush=True)
        (OUT / hid / "residuals.json").write_text(
            _json.dumps(rec, indent=2, default=float))
    (ROOT / "data" / "e5_hard_chine_roundtrip.json").write_text(
        _json.dumps(out, indent=2, default=float))
    return 0


def src2_for(src: dict, p: dict) -> dict:
    """The source record unchanged — the six stay the source's own."""
    out = dict(src)
    out["particulars"] = dict(p)
    return out


def _max_buildable_cp(six: dict, other: dict) -> float:
    """The largest Cp the kernel will build AT THIS HULL'S OTHER SIX.

    A GRID SCAN, NOT A BISECTION, and the difference is not pedantry. A
    parallel middle body gives the family a Cp FLOOR as well as a ceiling —
    at l_pmb 0.60 on a 5 m hull the feasible band is Cp 0.724 .. 0.966 — so a
    bisection seeded below the floor walks the wrong way and converges on its
    own starting point. It reported "0.500" for four hulls, which is the
    initial bracket and not a property of anything.

    For each candidate Cp the free genes are tried at a handful of
    configurations a prismatic hull actually needs (a long middle body, no
    keel rise) rather than at mid-box, because mid-box supplies neither.
    """
    from navalai import geometry, grammar
    import numpy as _np
    best = 0.0
    # `l_pmb` DIED in the E5 recalibration and `grammar.vector` now refuses
    # unknown genes by name — so this probe, still passing it, raised on
    # every configuration and reported "largest buildable Cp: 0.0000" for
    # hulls the kernel builds fine (measured 2026-08-27, all five Fridsma
    # rows). The probe now speaks the current fullness vocabulary.
    for cp in _np.arange(0.60, 1.00, 0.005):
        ok = False
        for lam in (0.55, 0.40, 0.20, 0.0):
            for xmb in (0.40, 0.45, 0.50):
                for rt in (0.50, 0.35, 0.20):
                    d = {**other, **six, "Cp": float(cp), "pmb": lam,
                         "x_mb": xmb, "r_transom": rt,
                         "forefoot": 0.0, "rocker": 0.0}
                    try:
                        geometry.Hull(grammar.vector(d), n_stations=81)
                        ok = True
                        break
                    except Exception:                       # noqa: BLE001
                        continue
                if ok:
                    break
            if ok:
                break
        if ok:
            best = float(cp)
    return best
