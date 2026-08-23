"""Describe every REAL hull on disk, and measure the bands the critic uses.

    python scripts/build_morphology_corpus.py            # -> data/morphology_corpus.json
    python scripts/build_morphology_corpus.py --compare  # + the generated-vs-real gap

THE POSITIVE CORPUS IS THE TEACHER. A critic calibrated on anything else is a
preference, not a measurement. Re-run this after adding real geometry; the
bands in `navalai.morphology._BAR` are quoted against its output and every one
of them names the percentile it came from.
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from navalai import grammar
from navalai.geometry import GeometryError, Hull
from navalai.morphology import (critique, describe, from_hull, load_offsets_csv)

SOURCES = ("tests/e5_real_hulls/*/source_offsets.csv",
           "tests/e5_hard_chine/*/source_offsets.csv")


def real_hulls():
    for pat in SOURCES:
        for f in sorted(glob.glob(pat)):
            try:
                o = load_offsets_csv(f)
                yield o.label, o.n_gaps, describe(o)
            except Exception as exc:                        # noqa: BLE001
                print(f"  SKIP {f}: {type(exc).__name__}: {exc}")


def _pct(vals, q):
    v = sorted(x for x in vals if np.isfinite(x))
    return float(v[min(len(v) - 1, int(q * len(v)))]) if v else float("nan")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--compare", action="store_true",
                    help="also sample L0-valid generated hulls and report the gap")
    ap.add_argument("--n", type=int, default=200)
    a = ap.parse_args()

    rows, descs = [], []
    for label, gaps, d in real_hulls():
        rows.append({"id": label, "gaps": gaps, **d.as_dict()})
        descs.append(d)
    print(f"POSITIVE CORPUS: {len(rows)} real hulls")

    keys = [k for k in rows[0] if k not in ("id", "gaps")] if rows else []
    bands = {k: [_pct([r[k] for r in rows], .05), _pct([r[k] for r in rows], .95)]
             for k in keys}
    rejected = [r["id"] for r, d in zip(rows, descs) if not critique(d).ok]
    out = {"n": len(rows), "bands": bands, "hulls": rows,
           "critic_false_positives": rejected}

    if a.compare:
        rng = np.random.default_rng(7)
        gen, tries = [], 0
        while len(gen) < a.n and tries < 30 * a.n:
            tries += 1
            x = grammar.LOW + rng.random(grammar.N_PARAMS) * (grammar.HIGH - grammar.LOW)
            try:
                if not grammar.check(x).ok:
                    continue
                gen.append(describe(from_hull(Hull(x))))
            except (GeometryError, ValueError, ZeroDivisionError):
                pass
        rej = sum(1 for d in gen if not critique(d).ok)
        out["generated"] = {
            "n": len(gen), "draws": tries, "rejected": rej,
            "reject_rate": rej / max(1, len(gen)),
            "bands": {k: [_pct([getattr(d, k) for d in gen], .05),
                          _pct([getattr(d, k) for d in gen], .95)] for k in keys},
        }
        print(f"GENERATED (L0-valid): {len(gen)} from {tries} draws")
        print(f"  morphology REJECTED: {rej}/{len(gen)} = {100*rej/max(1,len(gen)):.0f}%")
        print(f"  real hulls REJECTED: {len(rejected)}/{len(rows)}")

    Path("data/morphology_corpus.json").write_text(json.dumps(out, indent=1))
    print("wrote data/morphology_corpus.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
