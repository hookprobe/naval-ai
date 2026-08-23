#!/usr/bin/env python
"""Is the reported E5 residual the grammar's limit, or the optimiser's?

GATE E5. The geometric round-trip reports "the best this grammar can do at
representing this hull". That claim is only worth anything if the search
actually FOUND the best -- a global optimisation that stopped in a local
minimum would report the optimiser's bad luck as a property of the kernel,
and it would look exactly the same on the page.

So the fit is re-run from independent seeds on a sample and the SPREAD is
published beside the residual. A tight spread means the number is the
grammar's; a loose one means it is the search's, and the residual must then
be read as an UPPER BOUND on the grammar's error, never as its value.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.build_e5_corpus import fit, source_record            # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hulls", default="dsyhs_01,dsyhs_25,dsyhs_44,"
                                       "series60_4210W,wigley")
    ap.add_argument("--seeds", default="11,29,73")
    ap.add_argument("--maxiter", type=int, default=50)
    a = ap.parse_args()
    out = {}
    print(f"{'hull':18s} {'seed':>5s} {'rms_m':>10s} {'rms %halfbeam':>14s}")
    for hid in a.hulls.split(","):
        if not (ROOT / "tests" / "e5_real_hulls" / hid).exists():
            print(f"{hid}: no fixture, skipped")
            continue
        src = source_record(hid)
        vals = []
        for s in (int(x) for x in a.seeds.split(",")):
            _, res, _, _, _ = fit(src, s, a.maxiter)
            vals.append(res["rms_pct_halfbeam"])
            print(f"{hid:18s} {s:5d} {res['rms_m']:10.5f} "
                  f"{res['rms_pct_halfbeam']:14.3f}", flush=True)
        v = np.array(vals)
        out[hid] = {"seeds": a.seeds, "rms_pct_halfbeam": vals,
                    "spread_pct_of_mean": float(100 * (v.max() - v.min())
                                                / v.mean())}
        print(f"{'':18s} {'spread':>5s} {'':10s} "
              f"{out[hid]['spread_pct_of_mean']:13.2f}% of mean\n")
    (ROOT / "data" / "e5_fit_robustness.json").write_text(
        json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
