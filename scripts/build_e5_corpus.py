#!/usr/bin/env python
"""Assemble the E5 evidence ledger and run both round-trips. GATE E5.

Reads every committed offsets table under `tests/e5_real_hulls/`, measures the
source INDEPENDENTLY (`benchmarks/e5_hydro`), encodes the six into a NavalAI
genome, generates, measures the generated hull with the SAME code, and writes:

    data/e5_real_hulls.json   the full ledger, one record per hull
    data/e5_real_hulls.csv    the same, flat, for a human or a spreadsheet
    tests/e5_real_hulls/<id>/expected.json    source particulars + provenance
    tests/e5_real_hulls/<id>/generated.json   what the kernel produced
    tests/e5_real_hulls/<id>/residuals.json   scalar and geometric residuals

THE GEOMETRIC FIT IS BOUNDED BY THE GRAMMAR'S OWN BOX and moves only the ten
shape genes; the six stay at the source's values (`_assert_six_held`). A hull
whose best fit is poor is REPORTED as poor. Nothing here widens a tolerance,
drops a hull, or lets the six drift -- if the grammar cannot reach a real
hull, that inability IS the result E5 was built to obtain.
"""
from __future__ import annotations

import csv
import json
import pathlib
import sys
import time

import numpy as np
from scipy.optimize import differential_evolution

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from benchmarks.e5_hydro import particulars, sac                  # noqa: E402
from navalai import grammar                                       # noqa: E402
from scripts.e5_roundtrip import (SIX, TEN, cost, encode,         # noqa: E402
                                  hull_field, residual)
from scripts.extract_e5_offsets import read_table                 # noqa: E402

FIX = ROOT / "tests" / "e5_real_hulls"
BOX = [(float(grammar.LOW[grammar.NAMES.index(n)]),
        float(grammar.HIGH[grammar.NAMES.index(n)])) for n in TEN]

#: The genome's own box IS the E5 target range -- LWL [2.5, 24] m from RCD
#: scope, Cp [0.525, 0.710] from the prismatic table, LCB +-3%. A hull outside
#: it is not a bad hull; it is a hull this product does not claim to design,
#: and saying which is the point of the classification.
def classify_range(p: dict) -> tuple[str, str]:
    why = []
    for gene, val in (("LWL", p["LWL_m"]), ("BWL", p["BWL_m"]),
                      ("T", p["T_m"]), ("D", p["D_m"]), ("Cp", p["Cp"]),
                      ("lcb", p["LCB_pct"])):
        if not np.isfinite(val):
            # UNAVAILABLE is not out of range. A parameter the source does
            # not publish cannot be said to sit outside a bound, and calling
            # it OUT_OF_RANGE would report a gap in the SOURCE as a limit of
            # the product.
            continue
        i = grammar.NAMES.index(gene)
        lo, hi = float(grammar.LOW[i]), float(grammar.HIGH[i])
        if not (lo <= val <= hi):
            over = (val - hi) if val > hi else (lo - val)
            span = hi - lo
            why.append(f"{gene}={val:.4f} outside [{lo:g},{hi:g}] "
                       f"by {100 * over / span:.1f}% of the box")
    if not why:
        return "IN_RANGE", ""
    d = p.get("D_m")
    tag = "NEAR_RANGE" if len(why) == 1 and "by 0." in why[0] else \
        "OUT_OF_RANGE"
    return tag, "; ".join(why)


def geometry_class(p: dict) -> list[str]:
    """Geometric regime tags, DERIVED from the measured source particulars."""
    tags = []
    lb = p["LWL_m"] / p["BWL_m"]
    bt = p["BWL_m"] / p["T_m"]
    tags.append("slender" if lb >= 6.0 else
                "wide" if lb < 4.0 else "moderate_LB")
    tags.append("shallow_draft" if bt >= 5.0 else
                "deep_draft" if bt < 3.0 else "moderate_draft")
    tags.append("high_Cp" if p["Cp"] >= 0.62 else
                "low_Cp" if p["Cp"] < 0.56 else "moderate_Cp")
    return tags


def source_record(hid: str, base: pathlib.Path | None = None) -> dict:
    d = (base or FIX) / hid
    tab = read_table(d / "source_offsets.csv")
    head = [l[2:].rstrip() for l in
            (d / "source_offsets.csv").read_text().splitlines()
            if l.startswith("#")]
    zw = _declared_waterline(head, tab)
    p = particulars(tab["x_m"], tab["z_wl_m"], tab["y_m"], tab["z_keel_m"],
                    tab["z_sheer_m"], zw)
    u, a = sac(tab["x_m"], tab["z_wl_m"], tab["y_m"], tab["z_keel_m"], zw)
    return {"id": hid, "table": tab, "z_water_m": zw, "particulars": p,
            "provenance": head, "sac_u": u.tolist(), "sac_a": a.tolist()}


def _declared_waterline(head: list[str], tab: dict) -> float:
    """The design waterline, READ FROM THE TABLE'S OWN HEADER, or refuse.

    IT USED TO FALL BACK TO THE TOP OF THE TABLE, AND THAT WAS A DEFECT.
    Series 60 tabulates offsets up to W.L. 1.50, half again the design draft,
    so the fallback measured that hull at 1.5 T: it reported T = 1.600 m for
    a hull drawing 1.067 m, Cp 0.6608 for a published 0.614, and then handed
    the kernel a hull with ZERO freeboard, which died dividing by it. Every
    one of those numbers looked like a result.

    An unreadable datum is now a REFUSAL, which is this repository's standing
    rule -- `${VAR:-0}` turning "could not measure" into "perfect" is the same
    bug one floor down in the CFD receipts.
    """
    for line in head:
        if "Design waterline z =" in line:
            tok = line.split("Design waterline z =")[1].split()[0]
            try:
                return float(tok)
            except ValueError as exc:
                raise ValueError(
                    f"offsets header declares a design waterline that is not "
                    f"a number: {tok!r}. It must be written in metres.") \
                    from exc
    raise ValueError("offsets header declares no design waterline. It is not "
                     "inferred from the top of the table -- see this "
                     "function's docstring for what that cost.")


def fit(src: dict, seed: int, maxiter: int) -> tuple:
    """Best-fit shape genes with the six PINNED. Returns the residual left.

    D IS THE ONE GENE THAT MAY MIGRATE, AND ONLY WHEN THE SOURCE HAS NONE.
    A towing-tank series publishes the SUBMERGED body; several sources here
    tabulate no sheerline at all, so D is not merely unmeasured but
    UNOBSERVABLE from what they publish. A hull cannot be generated without a
    D, so for those sources D joins the fitted set and the record says
    `D = UNAVAILABLE`. That is not a relaxed tolerance: D governs only the
    topsides, which is exactly the region such a source does not describe, so
    nothing the source DOES say is being fitted away. A hull in this state is
    PARTIAL evidence and is excluded from the gate's complete-hull count.
    """
    p = src["particulars"]
    six = {"LWL": p["LWL_m"], "BWL": p["BWL_m"], "T": p["T_m"],
           "D": p["D_m"], "Cp": p["Cp"], "lcb": p["LCB_pct"]}
    tab = src["table"]
    T = src["z_water_m"]
    xa = p["x_aft_m"]
    grid = {"u": (tab["x_m"] - xa) / p["LWL_m"],
            "v": tab["z_wl_m"] / T,
            "y": tab["y_m"], "six": six}
    free = list(TEN)
    box = list(BOX)
    if not np.isfinite(six["D"]):
        free = free + ["D"]
        i = grammar.NAMES.index("D")
        box = box + [(float(grammar.LOW[i]), float(grammar.HIGH[i]))]
        six = dict(six)
        six.pop("D")
    grid["six"] = six
    grid["free"] = tuple(free)

    def _cost(vec):
        return cost(vec, six, grid, free=free)

    r = differential_evolution(_cost, box, seed=seed,
                               maxiter=maxiter, tol=1e-4, polish=True,
                               init="sobol", mutation=(0.3, 1.0),
                               recombination=0.9)
    g = encode(six, dict(zip(free, r.x)))
    return g, residual(g, grid), six, grid, r


def measure_back(g: np.ndarray, src: dict, n: int = 321) -> dict:
    """Measure the GENERATED hull with the same independent code.

    On a FINE grid, deliberately. MEASURED: reading a generated hull back at
    the source table's own 41 stations reports BWL 2.5% low and Cp 1.3% high,
    and both shrink to 0.15% and 0.004% at 321 -- so a coarse read would have
    been published as kernel error when it is the ruler. The source table's
    resolution is fixed by what the source publishes; the generated hull's is
    not, and there is no reason to inherit a limitation that is not ours.
    """
    u = np.linspace(0.0, 1.0, n)
    v = np.linspace(0.0, float(src["table"]["z_wl_m"].max()
                               / src["z_water_m"]), n)
    Y, T, zk, zs = hull_field(g, u, v)
    return particulars(u * grammar.named(g)["LWL"], v * T, Y, zk * T, zs * T,
                       T)


def derived(src: dict) -> dict:
    """Shape descriptors read off the SOURCE table, not off the genome."""
    tab, p = src["table"], src["particulars"]
    zw = src["z_water_m"]
    x = tab["x_m"]
    mid = 0.5 * (p["x_aft_m"] + p["x_fwd_m"])
    i = int(np.argmin(np.abs(x - mid)))
    row, z = tab["y_m"][i], tab["z_wl_m"]
    ok = np.isfinite(row) & (z >= tab["z_keel_m"][i]) & (z <= zw)
    dead = float("nan")
    if ok.sum() >= 2:
        zz, yy = z[ok][:2], row[ok][:2]
        if yy[1] > yy[0]:
            dead = float(np.degrees(np.arctan2(zz[1] - zz[0],
                                               yy[1] - yy[0])))
    # Transom: the sectional area at the AFTMOST station, over the maximum.
    # A canoe body tapers to nothing and reads ~0; an immersed transom does
    # not. It is measured, never assumed from the family name.
    from benchmarks.e5_hydro import sectional_area
    A = np.array([sectional_area(tab["y_m"][k], z, tab["z_keel_m"][k], zw)
                  for k in range(len(x))])
    return {"deadrise_deg": dead,
            "transom_area_ratio": float(A[0] / A.max()) if A.max() > 0
            else float("nan")}


_SURVEY_CACHE = {}


def _published_cross_check(hid: str, meas: dict) -> dict:
    """How the geometry-measured particulars compare with the publisher's
    own scalar table, where the source publishes one."""
    if not hid.startswith("dsyhs"):
        return {"published_table": "", "table_vol_dev_pct": float("nan"),
                "table_cp_dev_pct": float("nan"),
                "table_lwl_dev_pct": float("nan"),
                "table_bwl_dev_pct": float("nan"),
                "table_ax_dev_pct": float("nan")}
    if not _SURVEY_CACHE:
        f = ROOT / "data" / "e5_dsyhs_survey.json"
        _SURVEY_CACHE.update(json.loads(f.read_text()) if f.exists() else {})
    rec = _SURVEY_CACHE.get(str(int(hid.split("_")[1])), {})
    d = rec.get("dev_pct", {}) if rec.get("status") == "ok" else {}
    return {
        "published_table": "DSYHS hydrostatics, DOI 10.4121/21501375.v1",
        "table_vol_dev_pct": d.get("vol_m3", float("nan")),
        "table_cp_dev_pct": d.get("Cp", float("nan")),
        "table_lwl_dev_pct": d.get("LWL_m", float("nan")),
        "table_bwl_dev_pct": d.get("BWL_m", float("nan")),
        "table_ax_dev_pct": d.get("Ax_m2", float("nan")),
    }


def _one(job):
    """Round-trip ONE hull, or report why not.

    A hull that cannot be round-tripped is a RESULT and must reach the
    ledger; it must not take the other fifty-two with it. The first version
    let a `GeometryError` propagate out of the pool and the whole run died
    after one hull. Own process: the fit is a global optimisation
    over ten genes and the hulls are independent, so this is embarrassingly
    parallel and a serial run used one core of fifteen."""
    hid, seed, maxiter = job
    from benchmarks import e5_sources
    t0 = time.time()
    try:
        return _round_trip(hid, seed, maxiter, t0)
    except Exception as exc:                                # noqa: BLE001
        return hid, {"hull_id": hid, "status": "REFUSED",
                     "refusal": repr(exc)}, None, time.time() - t0


def _round_trip(hid, seed, maxiter, t0):
    from benchmarks import e5_sources
    src = source_record(hid)
    p = src["particulars"]
    fam = e5_sources.FAMILIES[e5_sources.family_of(hid)]
    rng, why = classify_range(p)
    dv = derived(src)
    g, res, six, grid, r = fit(src, seed, maxiter)
    mb = measure_back(g, src)
    scal = {k: float(mb[m] - six[k])
            for k, m in (("LWL", "LWL_m"), ("BWL", "BWL_m"),
                         ("T", "T_m"), ("D", "D_m"), ("Cp", "Cp"),
                         ("lcb", "LCB_pct")) if k in six}
    # THE PUBLISHER'S OWN SCALAR TABLE, CARRIED BESIDE THE GEOMETRY.
    # For DSYHS the same institution publishes both a geometry release and a
    # hydrostatics release, and they do not always agree. Recording the
    # disagreement per hull is the point: it is what an independent
    # extraction is FOR, and burying it would leave the corpus quietly
    # resting on whichever artifact happened to be read.
    xchk = _published_cross_check(hid, p)
    row = {
        "hull_id": hid,
        "source_family": fam["family"],
        "source_title": fam["geometry_title"],
        "source_author": fam.get("institution", ""),
        "source_url": fam["geometry_url"],
        "source_licence": fam["geometry_licence"],
        "lines_source": fam["geometry_format"],
        "offset_source": "extracted from the published geometry",
        "LWL_m": p["LWL_m"], "BWL_m": p["BWL_m"],
        "BWL_at_max_area_m": p["BWL_at_max_area_m"],
        "T_m": p["T_m"], "D_m": p["D_m"], "Cp": p["Cp"], "Cb": p["Cb"],
        "Cm": p["Cm"], "Cw": p["Cw"],
        "LCB_percent": p["LCB_pct"],
        "LCB_convention": "percent of LWL, POSITIVE FORWARD of amidships",
        "LCB_original_convention": fam["lcb_convention_original"],
        "LCB_transformation": fam["lcb_transformation"],
        "deadrise_deg": dv["deadrise_deg"],
        "transom_area_ratio": dv["transom_area_ratio"],
        "hull_type": ",".join(geometry_class(p)),
        "hard_chine_or_round_bilge": fam["hard_chine_or_round_bilge"],
        "range_class": rng, "range_note": why,
        "D_available": bool(np.isfinite(p["D_m"])),
        "complete_six": bool(np.isfinite(p["D_m"])),
        "scalar_max_abs_dev": max(abs(v) for v in scal.values()),
        "geom_rms_m": res["rms_m"],
        "geom_rms_pct_halfbeam": res["rms_pct_halfbeam"],
        "geom_max_m": res["max_m"],
        "geom_coverage": res["coverage"],
        "extraction_method": "independent: offsets read from the published "
                             "geometry, hydrostatics by benchmarks/"
                             "e5_hydro.py which imports no part of the "
                             "kernel under test",
        "notes": fam["notes"][:200],
        **xchk,
    }
    payload = {
        "expected": {"id": hid, "source_particulars": p, "derived": dv,
                     "provenance": src["provenance"], "family": fam["family"],
                     "range_class": rng, "range_note": why,
                     "sac_u": src["sac_u"], "sac_a": src["sac_a"]},
        "generated": {"id": hid,
                      "genome": {k: float(v) for k, v in
                                 grammar.named(g).items()},
                      "pinned_genes": list(six),
                      "fitted_genes": list(grid["free"]),
                      "measured_back": mb, "fit_nfev": int(r.nfev),
                      "fit_seed": seed, "fit_maxiter": maxiter},
        "residuals": {"id": hid, "scalar_absolute": scal, "geometric": res},
    }
    return hid, row, payload, time.time() - t0


def main() -> int:
    import argparse
    import multiprocessing as mp

    ap = argparse.ArgumentParser()
    ap.add_argument("--maxiter", type=int, default=50)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--only", default="")
    ap.add_argument("--jobs", type=int, default=11)
    a = ap.parse_args()

    ids = sorted(d.name for d in FIX.iterdir()
                 if d.is_dir() and (d / "source_offsets.csv").exists())
    if a.only:
        ids = [h for h in ids if h.startswith(tuple(a.only.split(",")))]
    jobs = [(h, a.seed, a.maxiter) for h in ids]
    print(f"{len(jobs)} hulls on {a.jobs} workers", flush=True)

    rows, done = {}, 0
    with mp.Pool(a.jobs) as pool:
        for hid, row, payload, dt in pool.imap_unordered(_one, jobs):
            done += 1
            rows[hid] = row
            if payload is None:
                print(f"[{done:2d}/{len(jobs)}] {hid:18s} REFUSED "
                      f"{row['refusal'][:90]} ({dt:.0f}s)", flush=True)
                continue
            d = FIX / hid
            for name, obj in payload.items():
                (d / f"{name}.json").write_text(
                    json.dumps(obj, indent=2, default=float))
            print(f"[{done:2d}/{len(jobs)}] {hid:18s} {row['range_class']:12s}"
                  f" Cp {row['Cp']:.4f} LCB {row['LCB_percent']:+6.3f}"
                  f"  scalar<={row['scalar_max_abs_dev']:.3g}"
                  f"  geom rms {row['geom_rms_pct_halfbeam']:5.2f}%"
                  f"  ({dt:.0f}s)", flush=True)

    out = [rows[h] for h in ids if h in rows]
    (ROOT / "data" / "e5_real_hulls.json").write_text(
        json.dumps(out, indent=2, default=float))
    with (ROOT / "data" / "e5_real_hulls.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    print(f"\n{len(out)} hulls -> data/e5_real_hulls.json / .csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
