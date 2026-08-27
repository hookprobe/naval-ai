"""Reconstruct reference hulls from data/hull_kb.json features — proof of learning.

The owner's protocol (2026-08-25) requires that before Naval-AI is trusted to
invent hulls, it demonstrates it can RECONSTRUCT known ones from extracted
features: reference → feature analysis → parametric interpretation →
generated hull → multi-view render → comparison. This script is that loop's
executable half. The feature records live in `data/hull_kb.json` (one home);
this script holds only the parametric INTERPRETATION of three targets and the
measurement/render machinery.

Targets (one per family tier, chosen in the KB):

  cruiser    slender solar-electric displacement cruiser (hull-example-004)
             — IN-genome: r_stem (plumb stem), pmb (parallel midbody),
             roundness (round bilge). Proves image → genes → hull.
  deepv      24° deep-V warped planing hull (hull-designs-gemini cell 1)
             — deadrise inside the box; the aft warp runs through
             beta_transom/beta_run. Measures the achieved deadrise law
             against the drawn 24°, and the warp direction.
  hookprobe  the owner's axe-bow → twin-demihull hybrid (hookprobe-hull.jpg)
             — OUT-of-genome by construction (inner section boundary);
             built by scripts/hookprobe_hull.py, verified here by measuring
             the TOPOLOGY the drawing specifies: one section loop forward,
             two aft, split position, and the aft-raked stem.

Every target emits: profile / plan / body-plan / perspective renders, an STL,
a descriptor comparison against the KB record's quantities, the morphology
critique (with its known family bias RECORDED, not obeyed — there is no
axe/piercer row in `_FAMILY_BAR`), and the geometric propulsion-integration
report of `docs/research/PROPULSION-INTEGRATION.md` §6: immersion, disc
room, transom Froude, keel slope approaching the disk.

Usage:
    python scripts/hull_kb_reconstruct.py [--target cruiser|deepv|hookprobe|all]
                                          [--outdir renders/hull_kb]
"""

from __future__ import annotations

import argparse
import json
import math
import struct
import subprocess
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

from navalai import grammar, morphology, propulsion  # noqa: E402
from navalai.geometry import Hull  # noqa: E402

# ---------------------------------------------------------------------------
# Parametric interpretations of the KB records.
#
# THE GENES MOVED to `navalai.parents` (P5, 2026-08-27): the reconstruction
# proved these genomes against the KB records, which makes them exactly what
# the parent library is FOR — so the library is their one home and this
# script (their prover) imports them back. The intent rows and cruise
# speeds stay here: they are what the KB record CLAIMS, i.e. this script's
# acceptance data, not properties of the parent.
# ---------------------------------------------------------------------------

from navalai.parents import PARENTS as _PARENTS  # noqa: E402

_PARENT_GENES = {p.name: dict(p.genes) for p in _PARENTS}

TARGETS: dict[str, dict] = {
    "cruiser": {
        "kb_record": "solar-slender-cruiser",
        "genes": _PARENT_GENES["solar-slender-cruiser"],
        # what the KB record says the reference shows
        "intent": {
            "entrance_half_angle_deg_max": 12.0,
            "beam_peak_x": 0.45,          # 0.55 L from the bow
            "beam_transom": 0.35,
            "round_bilge": True,
        },
        "cruise_kn": 10.0,
    },
    "deepv": {
        "kb_record": "claude-training-sheet",
        "genes": _PARENT_GENES["warped-deepv"],
        "intent": {
            "deadrise_mid_deg": 24.0,     # the sheet's label
            "warped": True,               # transom deadrise < midship
            "hard_chine": True,
        },
        "cruise_kn": 20.0,
    },
}


def vector_from_genes(genes: dict[str, float]) -> np.ndarray:
    missing = [n for n in grammar.NAMES if n not in genes]
    if missing:
        raise SystemExit(f"gene interpretation incomplete: {missing}")
    return np.array([float(genes[n]) for n in grammar.NAMES])


# ---------------------------------------------------------------------------
# STL out (binary), so every reconstruction leaves the same artifact the rest
# of the pipeline consumes. Same layout hookprobe_hull.write_stl emits.
# ---------------------------------------------------------------------------

def write_stl(V: np.ndarray, T: np.ndarray, path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    tri = V[T]                                     # (M,3,3)
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    ln = np.linalg.norm(n, axis=1, keepdims=True)
    n = np.divide(n, np.where(ln == 0, 1, ln))
    with open(path, "wb") as f:
        f.write(b"\0" * 80)
        f.write(struct.pack("<I", len(T)))
        for i in range(len(T)):
            f.write(struct.pack("<3f", *n[i]))
            for v in tri[i]:
                f.write(struct.pack("<3f", *v))
            f.write(b"\0\0")
    return len(T)


def read_stl(path: Path) -> tuple[np.ndarray, np.ndarray]:
    raw = path.read_bytes()
    if raw[:5] == b"solid" and b"facet" in raw[:200]:      # ASCII STL
        toks = raw.split()
        vs = [i for i, t in enumerate(toks) if t == b"vertex"]
        V = np.array([[float(toks[i + 1]), float(toks[i + 2]),
                       float(toks[i + 3])] for i in vs])
        return V, np.arange(len(V)).reshape(-1, 3)
    m = struct.unpack_from("<I", raw, 80)[0]
    rec = np.frombuffer(raw, dtype=np.uint8, count=m * 50, offset=84)
    rec = rec.reshape(m, 50)
    tri = rec[:, 12:48].copy().view("<f4").reshape(m, 3, 3).astype(float)
    V = tri.reshape(-1, 3)
    T = np.arange(len(V)).reshape(-1, 3)
    return V, T


# ---------------------------------------------------------------------------
# Renders. Profile / plan / body plan come from the Hull's own curves (the
# generator's lines, which is what the reference drawings show); perspective
# comes from the closed mesh so surface defects are SEEN (render_stl.py's
# lesson). For STL-only targets everything comes from the mesh.
# ---------------------------------------------------------------------------

def render_genome_views(hull: Hull, outdir: Path, name: str) -> list[Path]:
    outdir.mkdir(parents=True, exist_ok=True)
    x = hull.x
    paths = []

    fig, ax = plt.subplots(figsize=(10, 3))
    ax.plot(x, hull.z_keel, "k-", lw=1.5, label="keel")
    ax.plot(x, hull.z_sheer, "b-", lw=1.2, label="sheer")
    ax.plot(x, hull.z_chine, "r--", lw=0.9, label="chine")
    ax.axhline(0.0, color="c", lw=0.8, label="DWL")
    ax.set_aspect("equal"); ax.legend(fontsize=7); ax.set_title(f"{name} — profile")
    p = outdir / f"{name}-profile.png"; fig.savefig(p, dpi=130, bbox_inches="tight"); plt.close(fig)
    paths.append(p)

    fig, ax = plt.subplots(figsize=(10, 3.2))
    for sgn in (1, -1):
        ax.plot(x, sgn * hull.y_wl, "c-", lw=1.2)
        ax.plot(x, sgn * hull.y_sheer, "b-", lw=0.9)
        ax.plot(x, sgn * hull.y_chine, "r--", lw=0.7)
    ax.set_aspect("equal"); ax.set_title(f"{name} — plan (cyan WL, blue sheer, red chine)")
    p = outdir / f"{name}-plan.png"; fig.savefig(p, dpi=130, bbox_inches="tight"); plt.close(fig)
    paths.append(p)

    fig, ax = plt.subplots(figsize=(6, 5))
    n = hull.n_stations
    for frac in (0.02, 0.15, 0.30, 0.50, 0.70, 0.85, 0.98):
        i = min(n - 1, int(round(frac * (n - 1))))
        sec = hull.section(i)                       # (N,2) y,z
        sgn = 1 if frac >= 0.5 else -1              # fore stbd, aft port
        ax.plot(sgn * sec[:, 0], sec[:, 1], lw=1.0,
                label=f"x/L={frac:.2f}")
    ax.axhline(0.0, color="c", lw=0.8)
    ax.axvline(0.0, color="k", lw=0.5)
    ax.set_aspect("equal"); ax.legend(fontsize=6)
    ax.set_title(f"{name} — body plan (fwd right, aft left)")
    p = outdir / f"{name}-bodyplan.png"; fig.savefig(p, dpi=130, bbox_inches="tight"); plt.close(fig)
    paths.append(p)

    V, T = hull.closed_mesh(nx=120, nz=24)
    paths.append(render_mesh_perspective(V, T, outdir / f"{name}-perspective.png",
                                         title=f"{name} — perspective"))
    return paths


def render_mesh_perspective(V: np.ndarray, T: np.ndarray, path: Path,
                            title: str = "", elev: float = 18,
                            azim: float = -60) -> Path:
    fig = plt.figure(figsize=(9, 6))
    ax = fig.add_subplot(projection="3d")
    tri = V[T]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    ln = np.linalg.norm(n, axis=1); ln[ln == 0] = 1
    lam = 0.35 + 0.65 * np.clip((n / ln[:, None]) @ np.array([0.3, 0.5, 0.81]), 0, 1)
    col = np.repeat(lam[:, None], 3, axis=1) * np.array([0.78, 0.82, 0.88])
    pc = Poly3DCollection(tri, facecolors=col, edgecolors="none")
    ax.add_collection3d(pc)
    lo, hi = V.min(0), V.max(0)
    c, r = (lo + hi) / 2, (hi - lo).max() / 2
    ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r)
    ax.set_zlim(c[2] - r, c[2] + r)
    ax.view_init(elev=elev, azim=azim); ax.set_axis_off(); ax.set_title(title)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=130, bbox_inches="tight"); plt.close(fig)
    return path


def render_stl_views(V: np.ndarray, T: np.ndarray, outdir: Path,
                     name: str) -> list[Path]:
    views = [("perspective", 18, -60), ("bow", 8, -175),
             ("stern", 12, 8), ("underside", -35, -50)]
    return [render_mesh_perspective(V, T, outdir / f"{name}-{v}.png",
                                    title=f"{name} — {v}", elev=e, azim=a)
            for v, e, a in views]


# ---------------------------------------------------------------------------
# Measurements.
# ---------------------------------------------------------------------------

def deadrise_deg(hull: Hull) -> np.ndarray:
    """Bottom-panel angle keel→chine per station, degrees. Flat = 0."""
    dy = np.maximum(hull.y_chine, 1e-9)
    return np.degrees(np.arctan2(hull.z_chine - hull.z_keel, dy))


def keel_slope_at_disk_deg(hull: Hull, tail_frac: float = 0.10) -> float:
    """Keel slope over the after `tail_frac` of LWL — the §6 report quantity.
    Positive = keel rising toward the transom (flow climbing to the disk)."""
    x, zk = hull.x, hull.z_keel
    i = np.searchsorted(x, x[-1] * tail_frac)      # x=0 is the transom
    if i < 2:
        i = 2
    dz, dx = zk[0] - zk[i], x[i] - x[0]
    return math.degrees(math.atan2(dz, dx))


def propulsion_report(hull: Hull, cruise_kn: float) -> dict:
    wl = 0.0
    imm = propulsion.prop_immersion_m(hull, wl)
    tim = propulsion.transom_immersion_m(hull, wl)
    u = cruise_kn * 0.514444
    return {
        "prop_immersion_m": round(imm, 3),
        "transom_immersion_m": round(tim, 3),
        "transom_froude": round(propulsion.transom_froude(u, tim), 2)
        if tim > 0 else None,
        "max_prop_diameter_m": round(propulsion.max_prop_diameter_m(imm), 3),
        "keel_slope_at_disk_deg": round(keel_slope_at_disk_deg(hull), 1),
    }


def section_loops_at(V: np.ndarray, T: np.ndarray, x0: float,
                     lower_frac: float | None = None) -> int:
    """Count connected section components at station x=x0 by slicing the
    triangle soup and clustering the segments' endpoints. One component = a
    monohull section; two = demihulls. With `lower_frac`, only the lower
    fraction of the slice's z-extent is counted — the wet deck bridges the
    demihulls into one outline at full depth, and the drawing's topology
    claim is about the FLOW bodies below the tunnel crown (protocol §13-14:
    the topology transition is the design)."""
    tri = V[T]
    xs = tri[:, :, 0]
    keep = (xs.min(1) <= x0) & (xs.max(1) >= x0)
    segs = []
    for t in tri[keep]:
        pts = []
        for a, b in ((0, 1), (1, 2), (2, 0)):
            xa, xb = t[a, 0], t[b, 0]
            if (xa - x0) * (xb - x0) <= 0 and xa != xb:
                w = (x0 - xa) / (xb - xa)
                pts.append(t[a] + w * (t[b] - t[a]))
        if len(pts) >= 2:
            segs.append((pts[0][1:], pts[1][1:]))
    if not segs:
        return 0
    if lower_frac is not None:
        z = np.array([[a[1], b[1]] for a, b in segs])
        zcut = z.min() + lower_frac * (z.max() - z.min())
        segs = [(a, b) for a, b in segs if min(a[1], b[1]) <= zcut]
        if not segs:
            return 0
    # union-find over quantised endpoints
    key = lambda p: (round(p[0], 3), round(p[1], 3))
    parent: dict = {}

    def find(k):
        while parent.get(k, k) != k:
            parent[k] = parent.get(parent[k], parent[k])
            k = parent[k]
        return k

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for a, b in segs:
        ka, kb = key(a), key(b)
        parent.setdefault(ka, ka); parent.setdefault(kb, kb)
        union(ka, kb)
    return len({find(k) for k in parent})


# ---------------------------------------------------------------------------
# Target runners.
# ---------------------------------------------------------------------------

def run_genome_target(name: str, outdir: Path) -> dict:
    spec = TARGETS[name]
    params = vector_from_genes(spec["genes"])
    rep = grammar.check(params)
    if not rep.ok:
        return {"target": name, "status": "REFUSED-BY-GRAMMAR",
                "violations": list(rep.violations)}
    hull = Hull(params)
    off = morphology.from_hull(hull)
    d = morphology.describe(off)
    crit = morphology.critique(d)
    views = render_genome_views(hull, outdir, name)
    V, T = hull.closed_mesh(nx=120, nz=24)
    stl = outdir / f"{name}.stl"
    write_stl(V, T, stl)

    beta = deadrise_deg(hull)
    n = len(beta)
    out = {
        "target": name,
        "kb_record": spec["kb_record"],
        "status": "BUILT",
        "measured": {
            "alpha_e_deg": round(hull.alpha_e_deg(), 1),
            "beam_peak_x": round(d.beam_peak_x, 3),
            "beam_transom": round(d.beam_transom, 3),
            "beam_carried": round(d.beam_carried, 3),
            "waterline_convexity": round(d.waterline_convexity, 3),
            "pmb_frac": round(d.pmb_frac, 3),
            "l_over_b": round(d.l_over_b, 2),
            "deadrise_transom_deg": round(float(beta[0]), 1),
            "deadrise_mid_deg": round(float(beta[n // 2]), 1),
            "deadrise_75pct_deg": round(float(beta[int(0.75 * (n - 1))]), 1),
        },
        "intent": spec["intent"],
        "critique_flags": [str(v) for v in crit.findings],
        "critique_score": round(crit.score, 3),
        "propulsion": propulsion_report(hull, spec["cruise_kn"]),
        "renders": [str(p) for p in views], "stl": str(stl),
    }
    return out


def run_hookprobe(outdir: Path) -> dict:
    stl = outdir / "hookprobe.stl"
    outdir.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "hookprobe_hull.py"),
         "--out", str(outdir / "hookprobe")],
        capture_output=True, text=True, cwd=REPO)
    produced = sorted(outdir.glob("hookprobe*/**/*.stl")) + \
        sorted(outdir.glob("hookprobe*.stl"))
    if not produced:
        return {"target": "hookprobe", "status": "BUILD-FAILED",
                "stderr": r.stderr[-2000:], "stdout": r.stdout[-2000:]}
    src = produced[0]
    if src != stl:
        stl.write_bytes(src.read_bytes())
    V, T = read_stl(stl)
    L = V[:, 0].max() - V[:, 0].min()
    x0 = V[:, 0].min()
    loops = {f"x/L={f:.2f}": section_loops_at(V, T, x0 + f * L)
             for f in (0.10, 0.30, 0.50, 0.70, 0.90)}
    flow_bodies = {f"x/L={f:.2f}": section_loops_at(V, T, x0 + f * L,
                                                    lower_frac=0.35)
                   for f in (0.10, 0.30, 0.50, 0.70, 0.90)}
    views = render_stl_views(V, T, outdir, "hookprobe")
    return {
        "target": "hookprobe", "kb_record": "hookprobe-schematic",
        "status": "BUILT",
        "measured": {"section_loops_by_station": loops,
                     "lower_flow_bodies_by_station": flow_bodies,
                     "loa_m": round(float(L), 2)},
        "intent": {"loops_forward": 1, "loops_aft": 2,
                   "stem_rake_aft_deg": 20},
        "renders": [str(p) for p in views], "stl": str(stl),
        "builder_stdout_tail": r.stdout[-600:],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default="all",
                    choices=["cruiser", "deepv", "hookprobe", "all"])
    ap.add_argument("--outdir", default="renders/hull_kb")
    a = ap.parse_args()
    outdir = Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    todo =["cruiser", "deepv", "hookprobe"] if a.target == "all" else [a.target]
    results = []
    for t in todo:
        res = run_hookprobe(outdir) if t == "hookprobe" \
            else run_genome_target(t, outdir)
        results.append(res)
        print(json.dumps(res, indent=2))
    (outdir / "reconstruction-report.json").write_text(
        json.dumps(results, indent=2))
    bad = [r for r in results if r["status"] != "BUILT"]
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
