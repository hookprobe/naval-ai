"""Generate a PLYWOOD SOLAR-ELECTRIC CATAMARAN demi-hull corpus, and judge it.

    python scripts/build_plywood_catamaran_corpus.py --n 10000

WHY THIS FAMILY, AND WHY IT IS NOT AN ARBITRARY CHOICE. Two constraints decide
the geometry completely:

  1. PLYWOOD CANNOT BEND IN TWO DIRECTIONS AT ONCE. No compound curvature, no
     radiused bilge. The shell is flat sheet bent in one direction, meeting at
     HARD CHINES. `loft(ruled=True)` is what guarantees that: it builds the
     solid from planar facets, so the surface unrolls to a flat CNC cut file by
     construction rather than by hope. VERIFIED on a sample: 22 faces carrying
     15 distinct normals, watertight.
  2. A SOLAR-ELECTRIC CATAMARAN HAS ALMOST NO POWER. Demi-hulls must be slender
     -- high L/B -- or wave-making swallows the entire budget. The bounds below
     produce L/B ~ 6-15, which is the catamaran demihull band, NOT the 2.2-8.5
     monohull band this project's grammar enforces.

WHY IT MATTERS TO THIS REPOSITORY. `navalai/policy/dna.py` already pins
`construction = "sheet-developable"` and the compiled box already forces
`roundness = 0`. The product line IS plywood. But the corpus on disk is 51
Delft round-bilge yachts, one Series 60, one Wigley, five Fridsma models and a
container ship -- not one developable catamaran demi-hull among them. The
morphology critic was therefore calibrated entirely on hulls this product does
not build.

WHAT THIS IS NOT. It is not a positive corpus by fiat. Ship-D's lesson --
30,000 parametric hulls still contain many shapes no naval architect would
recognise -- applies with full force to a generator, and applies to THIS
generator. Every hull produced here is put through `morphology.critique` and
the pass rate is REPORTED, not assumed. A parametric dataset is a candidate
pool; the critic is what turns it into a corpus.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

# Slender developable demi-hull bounds. `draft` is a FRACTION of depth: a hull
# with no design waterline has no Cp, no Cb and no immersed anything, and a
# corpus of shapes without a waterline cannot teach a hydrostatic descriptor.
BOUNDS = {
    "length": (6.0, 12.0),
    "beam_top": (0.6, 1.2),        # sheer breadth — narrow
    "beam_bottom": (0.2, 0.6),     # waterline breadth — narrower still
    "depth": (0.8, 1.5),
    "bow_rocker": (0.2, 0.6),      # how far the bow sweeps up
    "stern_rocker": (0.05, 0.3),   # less aft, for displacement speed
    "draft_frac": (0.25, 0.55),    # design draft / depth
}


def demihull(length, beam_top, beam_bottom, depth, bow_rocker, stern_rocker):
    """A developable hard-chine demi-hull. Returns a CadQuery solid.

    Three stations lofted RULED: transom (raised by stern_rocker), midships
    (deepest, widest), and a stem that closes to a 20 mm sliver rather than a
    true point — a zero-width section is non-manifold and OCC refuses it.
    """
    import cadquery as cq

    s_stern = (cq.Workplane("XY").workplane(offset=0)
               .moveTo(-beam_bottom / 2, stern_rocker)
               .lineTo(beam_bottom / 2, stern_rocker)
               .lineTo(beam_top / 2, depth)
               .lineTo(-beam_top / 2, depth).close())
    s_mid = (s_stern.workplane(offset=length / 2)
             .moveTo(-beam_bottom / 2 - 0.05, 0.0)
             .lineTo(beam_bottom / 2 + 0.05, 0.0)
             .lineTo(beam_top / 2 + 0.1, depth)
             .lineTo(-beam_top / 2 - 0.1, depth).close())
    s_bow = (s_stern.workplane(offset=length)
             .moveTo(-0.01, bow_rocker).lineTo(0.01, bow_rocker)
             .lineTo(0.01, depth).lineTo(-0.01, depth).close())
    return s_stern.add(s_mid).add(s_bow).loft(ruled=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--out", default="data/plywood_catamaran")
    ap.add_argument("--keep-stl", action="store_true",
                    help="write every STL (10k hulls is ~400 MB); off by default")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    import cadquery as cq
    import trimesh

    from navalai.morphology import critique, describe, from_mesh

    out = Path(a.out)
    (out / "stls").mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(a.seed)

    rows, kept, tries, t0 = [], 0, 0, time.time()
    pathologies: dict[str, int] = {}
    while kept < a.n and tries < 40 * a.n:
        tries += 1
        p = {k: float(rng.uniform(*v)) for k, v in BOUNDS.items()}
        if p["beam_bottom"] >= p["beam_top"]:
            continue                      # dory flare: bottom narrower than top
        try:
            solid = demihull(p["length"], p["beam_top"], p["beam_bottom"],
                             p["depth"], p["bow_rocker"], p["stern_rocker"])
        except Exception:                                    # noqa: BLE001
            continue
        stl = (out / "stls" / f"plywood_hull_{kept:05d}.stl") if a.keep_stl \
            else Path(tempfile.mktemp(suffix=".stl"))
        try:
            cq.exporters.export(solid, str(stl))
            mesh = trimesh.load(str(stl))
        except Exception:                                    # noqa: BLE001
            continue
        finally:
            if not a.keep_stl and stl.exists():
                pass

        watertight = bool(mesh.is_watertight)
        normals = len(np.unique(np.round(mesh.face_normals, 3), axis=0))
        # the loft is (beam, depth, length) -> longitudinal is axis 2, up is 1
        o = from_mesh(mesh, axis=2, up=1, label=stl.stem)
        # put the design waterline at z = 0 so immersed coefficients exist
        dwl = float(o.z.min() + p["draft_frac"] * (o.z.max() - o.z.min()))
        from navalai.morphology import HullOffsets
        o = HullOffsets(x=o.x, z=o.z - dwl, y=o.y, z_keel=o.z_keel - dwl,
                        z_sheer=o.z_sheer - dwl, label=o.label)
        d = describe(o)
        # DECLARE THE FAMILY. Judged as a monohull, 55 of 300 of these were
        # rejected purely for being slender — which is the one property a
        # solar-electric catamaran demihull must have.
        c = critique(d, family="demihull")
        for path in c.pathologies:
            pathologies[path] = pathologies.get(path, 0) + 1
        rows.append({"id": stl.stem, **p, "watertight": watertight,
                     "distinct_normals": normals, "developable": normals <= 24,
                     "plausible": bool(c.ok), "score": c.score,
                     "pathologies": list(c.pathologies),
                     **{k: float(v) for k, v in d.as_dict().items()}})
        kept += 1
        if not a.keep_stl and stl.exists():
            os.unlink(stl)
        if kept % 250 == 0:
            print(f"  {kept}/{a.n}  ({time.time()-t0:.0f}s)")

    ok = sum(1 for r in rows if r["plausible"])
    wt = sum(1 for r in rows if r["watertight"])
    dev = sum(1 for r in rows if r["developable"])
    print(f"\ngenerated {len(rows)} demi-hulls from {tries} draws "
          f"in {time.time()-t0:.0f}s")
    print(f"  watertight             : {wt}/{len(rows)} = {100*wt/max(1,len(rows)):.1f}%")
    print(f"  developable (planar)   : {dev}/{len(rows)} = {100*dev/max(1,len(rows)):.1f}%")
    print(f"  morphologically PLAUSIBLE: {ok}/{len(rows)} = {100*ok/max(1,len(rows)):.1f}%")
    if pathologies:
        print("  rejections by pathology:")
        for k, v in sorted(pathologies.items(), key=lambda t: -t[1]):
            print(f"     {k:14s} {v}")

    with (out / "labels.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: (json.dumps(v) if isinstance(v, list) else v)
                        for k, v in r.items()})
    (out / "summary.json").write_text(json.dumps(
        {"n": len(rows), "draws": tries, "watertight": wt, "developable": dev,
         "plausible": ok, "pathologies": pathologies, "bounds": BOUNDS}, indent=1))
    print(f"wrote {out/'labels.csv'} and {out/'summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
