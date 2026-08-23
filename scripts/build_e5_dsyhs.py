#!/usr/bin/env python
"""Extract the DSYHS half of the E5 corpus. Acquisition side, runs once.

Writes one offsets table per hull under `tests/e5_real_hulls/<id>/` and a
survey JSON recording, for EVERY hull, how the geometry-measured particulars
compare with the publisher's own hydrostatics table. The survey is the
evidence that the extraction is right; the tables are what the gate reads.
"""
from __future__ import annotations

import json
import pathlib
import sys
import time
import zipfile

import numpy as np
import openpyxl

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from benchmarks.e5_hydro import particulars                      # noqa: E402
from scripts.extract_e5_offsets import Surface, extract, write_table  # noqa: E402

ZIP = ROOT / "data" / "refdata" / "dsyhs" / "geometriesIGSmodelscale.zip"
OUT = ROOT / "tests" / "e5_real_hulls"
SURVEY = ROOT / "data" / "e5_dsyhs_survey.json"
N_ST, N_WB, N_WA = 41, 33, 8


def published() -> dict:
    """(sysser -> row) at model and full scale, overhang = 1 only."""
    def grab(name):
        wb = openpyxl.load_workbook(ROOT / "data" / "refdata" / "dsyhs" / name,
                                    read_only=True, data_only=True)
        ws = wb["Canoe body hydrostatics"]
        rows = list(ws.iter_rows(values_only=True))
        hdr = list(rows[0])
        out = {}
        for r in rows[1:]:
            if r[0] is None:
                continue
            d = dict(zip(hdr, r))
            if d["Overhang"] != 1:
                continue
            out[int(d["Sysser"])] = d
        return out
    return grab("DSYHS_hydrostatics_modelscale.xlsx"), \
        grab("DSYHS_hydrostatics_fullscale.xlsx")


def _one(job):
    """Extract ONE hull. Runs in its own process: OpenCASCADE is imported
    lazily inside `Surface`, so each worker gets its own reader and they do
    not share state."""
    sysser, pm, pf, name, blob = job
    t0 = time.time()
    tmp = pathlib.Path("/tmp/e5_igs")
    tmp.mkdir(exist_ok=True)
    p = tmp / f"SYSSER{sysser:02d}.igs"
    p.write_bytes(blob)
    scale = pf["lwl0"] / pm["lwl0"]
    try:
        surf = Surface(p)
        tab = extract(surf, pm["tc0"] * 1000.0, N_ST, N_WB, N_WA, scale=scale)
        got = particulars(tab["x_m"], tab["z_wl_m"], tab["y_m"],
                          tab["z_keel_m"], tab["z_sheer_m"], tab["z_water_m"])
    except Exception as exc:                            # noqa: BLE001
        return sysser, {"status": "FAILED", "error": repr(exc)}, None, None
    pub = {"LWL_m": pf["lwl0"], "BWL_m": pf["bwl0"], "T_m": pf["tc0"],
           "vol_m3": pf["volc0"], "Aw_m2": pf["aw0"], "Ax_m2": pf["ax0"],
           "Cb": pf["cb0"], "Cm": pf["cm0"], "Cp": pf["cp0"], "Cw": pf["cw0"],
           "LCB_pct": 100.0 * pf["lcb0"] / pf["lwl0"],
           "LCF_pct": 100.0 * pf["lcf0"] / pf["lwl0"]}
    dev = {k: 100.0 * (got[k] - pub[k]) / pub[k]
           for k in pub if pub[k] not in (0, None)}
    rec = {"status": "ok", "series": int(pm["Series"]), "scale": scale,
           "measured": got, "published": pub, "dev_pct": dev,
           "seconds": time.time() - t0}
    head = [
        f"DSYHS Sysser {sysser} (series {int(pm['Series'])}), canoe body, "
        f"overhang 1.",
        "SOURCE: Delft Systematic Yacht Hull Series Geometries data,",
        "  4TU.ResearchData / figshare 21501330, DOI 10.4121/21501330.v1,",
        f"  licence CC0. File {name}, publisher MD5 verified on the "
        f"release zip.",
        f"Extracted by scripts/build_e5_dsyhs.py at {N_ST} stations x "
        f"{N_WB}+{N_WA} waterlines.",
        f"Model scale geometry x published scale factor {scale:.4f} -> full "
        f"scale, LWL nominal {pf['lwl0']:.3f} m.",
        "z = 0 is the moulded baseline (lowest point of the canoe body).",
        f"Design waterline z = {tab['z_water_m']:.9g} m "
        "(= published maximum canoe-body draft tc0).",
        "y is HALF-breadth. Blank = waterline below the local keel.",
    ]
    return sysser, rec, tab, head


def main() -> int:
    import argparse
    import multiprocessing as mp

    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=10,
                    help="worker processes. This Mac has 15 logical cores; "
                         "the hulls are independent, so extraction is "
                         "embarrassingly parallel and a serial run was "
                         "using one of them.")
    a = ap.parse_args()

    mod, full = published()
    zf = zipfile.ZipFile(ZIP)
    names = {int(n.split("SYSSER")[1][:2]): n for n in zf.namelist()
             if n.endswith("_surface.igs") and "SYSSER" in n
             and n.count("_") == 1}
    jobs = [(s, mod[s], full[s], names[s], zf.read(names[s]))
            for s in sorted(names) if s in mod]
    # BIGGEST FIRST. Sysser 23's surface is 3.7 MB against 271 kB for Sysser
    # 24 and sections proportionally slower, so scheduling it last would
    # leave one worker running alone after the other nine had finished.
    jobs.sort(key=lambda j: -len(j[4]))
    print(f"{len(jobs)} hulls on {a.jobs} workers", flush=True)

    survey = {}
    done = 0
    with mp.Pool(a.jobs) as pool:
        for sysser, rec, tab, head in pool.imap_unordered(_one, jobs):
            done += 1
            survey[sysser] = rec
            if rec["status"] != "ok":
                print(f"[{done:2d}/{len(jobs)}] SYSSER{sysser:02d} FAILED "
                      f"{rec['error']}", flush=True)
                continue
            write_table(tab, OUT / f"dsyhs_{sysser:02d}" / "source_offsets.csv",
                        head)
            d = rec["dev_pct"]
            print(f"[{done:2d}/{len(jobs)}] SYSSER{sysser:02d} "
                  f"s{rec['series']} LWL{d['LWL_m']:+6.3f}% "
                  f"BWL{d['BWL_m']:+6.3f}% vol{d['vol_m3']:+6.3f}% "
                  f"Cp{d['Cp']:+6.3f}% D={rec['measured']['D_m']:.3f}m "
                  f"({rec['seconds']:.0f}s)", flush=True)

    SURVEY.write_text(json.dumps(survey, indent=2, default=float))
    ok = [s for s in survey.values() if s.get("status") == "ok"]
    print(f"\n{len(ok)} of {len(survey)} extracted -> {SURVEY}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
