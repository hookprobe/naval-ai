"""OCEAN 17 -- houseboat17's four lines, proportioned for the open ocean.

    python scripts/ocean17.py --out data/exports/ocean17

SAME TOPOLOGY, THREE KNOBS RAISED. The assessment of houseboat17 found the
shape ocean-worthy and the PROPORTIONS not: tunnel crown 0.71 m above the
waterline at 8 t against the >= 1.0-1.2 m ocean-catamaran practice for a
16 m boat (wet-deck slamming in the mid-Atlantic 2-3 m routine seas), and a
1.55 m hull depth that cannot carry the freeboard an ocean stability case
needs. The energy story was already marginal-but-real (~24 kWh/day net solar
-> ~3.5 kn continuous, the Sun21 regime).

So `ocean17` raises exactly what the wave climate prices and keeps
everything the owner designed: the deep-V forward half, the centre keel that
rises and closes into the tunnel crown, the chines that become the demihull
keels, the 20 deg reverse-raked axe stem, twin protected props.

    knob            houseboat17     ocean17     why
    depth           1.55 m          2.20 m      freeboard + interior
    crown_aft       +0.44           +1.00       wet-deck clearance >= 1.2 m
    sheer_aft       +0.70           +1.35       reserve buoyancy, deck dry
    sheer_bow       +1.48           +2.10       keeps the bow proportion
    t_stem          1.30            1.42        the axe grows with the seas
    t_demi          0.88            0.95        prop room under each hull
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.houseboat17 import Hull17, float_to, write_stl  # noqa: E402
from scripts.hookprobe_hull import hydrostatics              # noqa: E402


def ocean17() -> Hull17:
    return Hull17(depth=2.20, crown_aft=1.00, sheer_aft=1.35, sheer_bow=2.10,
                  t_stem=1.42, t_demi=0.95, stern_rise=0.16)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/exports/ocean17")
    ap.add_argument("--mass", type=float, default=8500.0,
                    help="lightship 6.6 t + taller topsides + ocean stores")
    args = ap.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    h = ocean17()
    wl = float_to(h, args.mass)
    r = hydrostatics(h, wl, ns=161)
    kg = 0.50 * h.depth - 0.55          # taller boat, KG rises with it
    gm = r["kb_m"] + r["bm_m"] - kg
    s = np.linspace(0, 1, 801)
    zc = h.z_c(s)
    print(f"OCEAN 17 at {args.mass:.0f} kg (wl z = {wl:+.3f})")
    print(f"  crown clearance over WL: {zc[0]-wl:.2f} m at the transom "
          f"(houseboat17 at 8 t: 0.71; ocean practice >= 1.0-1.2)")
    print(f"  freeboard aft {float(h.z_sh(0.2))-wl:.2f} m | stem draft "
          f"{wl-zc[-1]:.2f} m | demihull keel draft "
          f"{wl-float(h.z_ch(np.linspace(0,1,200)).min()):.2f} m")
    print(f"  BWL {r['bwl_m']:.2f} | Awp {r['awp_m2']:.1f} m2 | GM {gm:.2f} m")
    stl = out / "ocean17.stl"
    n = write_stl(h, stl)
    from navalai import mesh_repair as _mr

    def _rewrite(V, T):
        with open(stl, "w") as f:
            f.write("solid ocean17\n")
            for t in T:
                a, b, c = V[t[0]], V[t[1]], V[t[2]]
                nn = np.cross(b - a, c - a); ln = np.linalg.norm(nn)
                nn = nn / ln if ln > 0 else nn
                f.write(f" facet normal {nn[0]:.6e} {nn[1]:.6e} {nn[2]:.6e}\n"
                        "  outer loop\n")
                for v in (a, b, c):
                    f.write(f"   vertex {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
                f.write("  endloop\n endfacet\n")
            f.write("endsolid ocean17\n")

    # TWO PASSES, because writing at 6 decimals can COLLAPSE a sliver the
    # in-memory repair had already accepted: measured here, exactly one
    # degenerate face existed only after quantisation. Repairing the file a
    # second time removes what the first write created; the loop converges
    # because each pass only deletes faces.
    rep = None
    for _ in range(2):
        V, T, rep = _mr.repair(str(stl))
        _rewrite(V, T)
        chk = _mr.diagnose(str(stl))
        # A KEPT DEGENERATE IS NOT A LEAK. `mesh_repair.repair` deliberately
        # KEEPS a zero-area face whose edges pair with real faces -- dropping
        # it would open the shell (its own documented kcs.stl incident). What
        # decides watertightness is boundary/non-manifold/self-intersection,
        # so those are the failure set; kept needles are reported separately.
        bad = {k: v for k, v in chk.found.items() if v and k in
               ("boundary_edges", "nonmanifold_edges", "winding_conflicts",
                "self_intersections")}
        kept = chk.found.get("degenerate_faces", 0)
        if not bad:
            break
    print(f"  STL {stl}  {n} -> {rep.n_tris_after} after repair; "
          f"WATERTIGHT AND MANIFOLD: {not bad}"
          + ("" if not bad else f" STILL FOUND {bad}")
          + (f"  ({kept} load-bearing zero-area face kept, heals topology)"
             if kept else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
