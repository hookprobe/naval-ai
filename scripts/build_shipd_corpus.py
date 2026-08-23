"""ONE-TIME extraction of the ShipD corpus into vendored descriptors.

    python scripts/build_shipd_corpus.py --n 30000

`navalai/` MUST NEVER IMPORT ShipD. This script reads it once, computes this
project's own morphology descriptors, and writes them to
`data/shipd_morphology.json`. Everything downstream reads that file. Three
reasons, and the first is the binding one:

  1. LICENCE. github.com/noahbagz/ShipD declares NO licence, which means all
     rights reserved. Measuring against a public dataset and recording the
     resulting statistics is a different act from shipping its code or its
     geometry inside this product. The vendored artifact is OUR measurement,
     with its provenance named.
  2. REPRODUCIBILITY. The corpus is a fixed input to the critic's bands. A
     band that moves when someone re-clones an upstream repo is not a band.
  3. A RUNTIME DEPENDENCY ON A RESEARCH REPO IS A LIABILITY. It needs a local
     patch to run at all (below), and it pulls `numpy-stl`.

WHY IT NEEDED PATCHING, and the patch is in `downloads/shipd/` not here.
MEASURED on 500 sampled hulls before the fix: 111 crashed with
`ValueError: setting an array element with a sequence` — exactly the 21%
carrying a bulbous bow. `halfBeam_BB` returns a VECTOR and its result was
assigned into a scalar slot at HullParameterization.py:1239, which numpy 1.x
tolerated and numpy 2.x refuses. The author had already applied the same `[0]`
to the STERN bulb eight lines of logic away, with the comment "ad the [0] so
that y_int is interpretted as a float", and missed the bow. After the patch:
500 of 500 generate cleanly.

WHY LOA = 10 DOES NOT MATTER FOR MORPHOLOGY. Every ShipD hull is normalised to
LOA 10 and the rest are ratios, which looks like a size-corpus gap. It is not:
`morphology.describe` is provably SCALE-FREE — verified over 0.37x to 23x,
worst relative change 1.2e-15. (Getting there took a fix: `section_fullness_mean`
floored a DIMENSIONAL quantity against an absolute 1e-9 and moved 2.3% under a
7.3x scaling while the other 32 descriptors were exact.) A realistic LOA is
sampled and RECORDED anyway, because anything dimensional downstream —
resistance, scantlings, structures — needs one, and inventing it later would be
worse than declaring it here.

WHAT THE CORPUS IS FOR. MEASURED on 389 hulls: 60.4% morphologically
plausible, against ~9% for this project's own L0-valid genomes and 100% for 58
published hulls. That 60/40 split is the point. A corpus that is 99.9% good
teaches nothing about failure — the 10,000-hull plywood set built here on
2026-08-23 had 12 negatives in 10,000 and was useless as a discriminator. Ship-D's
documented weakness ("many randomly generated hulls do not look like realistic
ships") is precisely the asset: it supplies the NEGATIVE half of the manifold.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

_SHIPD = Path(__file__).resolve().parents[1] / "downloads" / "shipd"

# Realistic LOA spread for the craft this project designs, log-uniform so small
# boats are not swamped by ships. Recorded per hull; NOT used by any descriptor.
LOA_RANGE_M = (6.0, 40.0)


def _offsets(vec, n_stations=41, nz=41):
    """A ShipD design vector -> this project's own offsets table."""
    import HullParameterization as HP

    from navalai.morphology import HullOffsets

    h = HP.Hull_Parameterization(vec)
    if (np.asarray(h.input_Constraints()) > 0).any():
        return None, "shipd-constraint"
    try:
        wls = h.gen_MeshGridPointCloud(NUM_WL=nz, PointsPerLOA=81,
                                       bit_GridOrList=1)
    except Exception as exc:                                    # noqa: BLE001
        return None, f"gen:{type(exc).__name__}"
    zs, curves = [], []
    for w in wls:
        a = np.asarray(w, float)
        if a.shape[0] >= 3:
            zs.append(float(np.median(a[:, 2])))
            curves.append(a)
    if len(zs) < 5:
        return None, "too-few-waterlines"
    zs = np.array(zs)
    xa = np.concatenate([c[:, 0] for c in curves])
    x = np.linspace(float(xa.min()), float(xa.max()), n_stations)
    y = np.full((n_stations, len(zs)), np.nan)
    for j, c in enumerate(curves):
        o = np.argsort(c[:, 0])
        xs_, ys_ = c[o, 0], np.abs(c[o, 1])
        m = (x >= xs_.min()) & (x <= xs_.max())
        y[m, j] = np.interp(x[m], xs_, ys_)
    zk = np.full(n_stations, np.nan)
    zsh = np.full(n_stations, np.nan)
    for i in range(n_stations):
        g = np.where(~np.isnan(y[i]))[0]
        if g.size:
            zk[i], zsh[i] = zs[g[0]], zs[g[-1]]
    good = ~np.isnan(zk)
    if good.sum() < 2:
        return None, "no-keel"
    zk[~good] = np.interp(x[~good], x[good], zk[good])
    zsh[~good] = np.interp(x[~good], x[good], zsh[good])
    dwl = float(np.nanpercentile(zs, 55))       # ShipD declares WL as a ratio
    return HullOffsets(x=x, z=zs - dwl, y=y, z_keel=zk - dwl,
                       z_sheer=zsh - dwl, label="shipd"), None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="data/shipd_morphology.json")
    a = ap.parse_args()

    if not (_SHIPD / "InputVectors_30k.npy").exists():
        print(f"ShipD not present at {_SHIPD}. This is a ONE-TIME extractor; "
              f"the vendored result at {a.out} is what the product reads.")
        return 2
    sys.path.insert(0, str(_SHIPD))
    from navalai.morphology import critique, describe

    X = np.load(_SHIPD / "InputVectors_30k.npy")
    rng = np.random.default_rng(a.seed)
    n = min(a.n, len(X))
    idx = rng.permutation(len(X))[:n]
    loas = np.exp(rng.uniform(np.log(LOA_RANGE_M[0]), np.log(LOA_RANGE_M[1]), n))

    rows, skips, t0 = [], {}, time.time()
    for k, i in enumerate(idx):
        o, why = _offsets(X[i])
        if o is None:
            skips[why] = skips.get(why, 0) + 1
            continue
        try:
            d = describe(o)
        except Exception as exc:                                # noqa: BLE001
            skips[f"describe:{type(exc).__name__}"] = \
                skips.get(f"describe:{type(exc).__name__}", 0) + 1
            continue
        c = critique(d)
        rows.append({"shipd_index": int(i), "loa_m": float(loas[k]),
                     "plausible": bool(c.ok), "score": float(c.score),
                     "pathologies": list(c.pathologies),
                     **{kk: float(vv) for kk, vv in d.as_dict().items()}})
        if len(rows) % 2500 == 0:
            print(f"  {len(rows)} described ({time.time()-t0:.0f}s)")

    ok = sum(1 for r in rows if r["plausible"])
    keys = [k for k in rows[0] if k not in
            ("shipd_index", "loa_m", "plausible", "score", "pathologies")]

    def pct(k, q):
        v = sorted(r[k] for r in rows if np.isfinite(r[k]))
        return float(v[min(len(v) - 1, int(q * len(v)))]) if v else float("nan")

    out = {
        "source": "github.com/noahbagz/ShipD, InputVectors_30k.npy",
        "licence": "NONE DECLARED upstream (all rights reserved). This file "
                   "records OUR descriptor measurements, not their geometry.",
        "upstream_patch": "HullParameterization.py:1239 halfBeam_BB(...)[0] — "
                          "numpy 2.x scalar assignment; 111/500 hulls (all "
                          "bulbous-bow) crashed without it, 500/500 pass with.",
        "scale_free": "descriptors verified invariant 0.37x..23x, worst 1.2e-15",
        "loa_range_m": list(LOA_RANGE_M),
        "n": len(rows), "sampled": n, "plausible": ok,
        "plausible_frac": ok / max(1, len(rows)), "skips": skips,
        "bands": {k: [pct(k, .05), pct(k, .95)] for k in keys},
        "bands_plausible_only": {
            k: [float(np.nanpercentile([r[k] for r in rows if r["plausible"]], 5)),
                float(np.nanpercentile([r[k] for r in rows if r["plausible"]], 95))]
            for k in keys},
        "hulls": rows,
    }
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(f"\n{len(rows)} hulls described in {time.time()-t0:.0f}s (skips {skips})")
    print(f"  morphologically PLAUSIBLE: {ok}/{len(rows)} = {100*ok/max(1,len(rows)):.1f}%")
    print(f"  wrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
