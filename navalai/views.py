"""Canonical hull views — the G-Visual artifact, per MORPHOLOGY-V1.md §6.

WHY THIS MODULE EXISTS. Every shape incident in this repository's record —
the 2026-08-23 plank (four hulls delivered before anyone rendered one), the
2026-08-24 spearhead, the houseboat19 paddle boat — was found by a HUMAN
opening a file, and the render was the last stage of the chain, downstream
of every gate. The audit (docs/audit/HULL-DESIGN-AUDIT.md, ladder level L4)
found visual recognizability had NO enforcement at all. §6 of
MORPHOLOGY-V1.md specified the fix and it sat "SPECIFIED, NOT BUILT" until
2026-08-27: fixed views, identical every time, never an arbitrary camera,
written per hull BESIDE its descriptors, so a plank cannot pass review
unseen.

`canonical_views(hull, outdir, name)` emits the fixed set — profile, plan,
body plan, design-waterline, transverse sections, isometric — from the
Hull's OWN curves (the same surface the STL is built from), plus
`<name>-shape.json`: the 33 descriptors, the critique verdict with named
findings, and the `shape` margin. The sheet is written on REFUSED hulls
too — that is the point: the artifact exists precisely so a refusal can be
SEEN, not only read.

Deterministic: same hull, same bytes-level figure content (matplotlib Agg,
fixed sizes, no timestamps in the figures). PNGs land in the caller's
output directory (build artifacts, normally gitignored); the module has no
side channel and writes nothing else.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

from . import morphology  # noqa: E402

#: The fixed station fractions of the body plan and section strip — the
#: §23-style spread, denser toward the ends where geometry changes fastest.
SECTION_FRACS = (0.02, 0.10, 0.25, 0.40, 0.50, 0.60, 0.75, 0.90, 0.98)


def _profile(hull, path: Path, name: str) -> None:
    fig, ax = plt.subplots(figsize=(10, 3))
    ax.plot(hull.x, hull.z_keel, "k-", lw=1.5, label="keel")
    ax.plot(hull.x, hull.z_sheer, "b-", lw=1.2, label="sheer")
    ax.plot(hull.x, hull.z_chine, "r--", lw=0.9, label="chine")
    ax.axhline(0.0, color="c", lw=0.8, label="DWL")
    ax.set_aspect("equal")
    ax.legend(fontsize=7)
    ax.set_title(f"{name} — profile")
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)


def _plan(hull, path: Path, name: str) -> None:
    fig, ax = plt.subplots(figsize=(10, 3.2))
    for sgn in (1, -1):
        ax.plot(hull.x, sgn * hull.y_sheer, "b-", lw=0.9)
        ax.plot(hull.x, sgn * hull.y_chine, "r--", lw=0.7)
    ax.set_aspect("equal")
    ax.set_title(f"{name} — plan (blue sheer, red chine)")
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)


def _waterline(hull, path: Path, name: str) -> None:
    fig, ax = plt.subplots(figsize=(10, 3.2))
    for sgn in (1, -1):
        ax.plot(hull.x, sgn * hull.y_wl, "c-", lw=1.3)
    ax.set_aspect("equal")
    ax.set_title(f"{name} — design waterline")
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)


def _body_plan(hull, path: Path, name: str) -> None:
    fig, ax = plt.subplots(figsize=(6, 5))
    n = hull.n_stations
    for frac in SECTION_FRACS:
        i = min(n - 1, int(round(frac * (n - 1))))
        sec = np.asarray(hull.section(i), float)
        sgn = 1 if frac >= 0.5 else -1          # forward stbd, aft port
        ax.plot(sgn * sec[:, 0], sec[:, 1], lw=1.0, label=f"x/L={frac:.2f}")
    ax.axhline(0.0, color="c", lw=0.8)
    ax.axvline(0.0, color="k", lw=0.5)
    ax.set_aspect("equal")
    ax.legend(fontsize=6)
    ax.set_title(f"{name} — body plan (fwd right, aft left)")
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)


def _sections_strip(hull, path: Path, name: str) -> None:
    fig, axes = plt.subplots(1, len(SECTION_FRACS),
                             figsize=(2.0 * len(SECTION_FRACS), 2.4))
    n = hull.n_stations
    for ax, frac in zip(axes, SECTION_FRACS):
        i = min(n - 1, int(round(frac * (n - 1))))
        sec = np.asarray(hull.section(i), float)
        ax.plot(sec[:, 0], sec[:, 1], "k-", lw=1.0)
        ax.plot(-sec[:, 0], sec[:, 1], "k-", lw=1.0)
        ax.axhline(0.0, color="c", lw=0.6)
        ax.set_aspect("equal")
        ax.set_title(f"{frac:.2f}", fontsize=7)
        ax.tick_params(labelsize=5)
    fig.suptitle(f"{name} — transverse sections (x/L, transom→bow)")
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)


def _isometric(hull, path: Path, name: str) -> None:
    V, T = hull.closed_mesh(nx=100, nz=20)
    fig = plt.figure(figsize=(9, 6))
    ax = fig.add_subplot(projection="3d")
    tri = V[T]
    nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    ln = np.linalg.norm(nrm, axis=1)
    ln[ln == 0] = 1.0
    lam = 0.35 + 0.65 * np.clip(
        (nrm / ln[:, None]) @ np.array([0.3, 0.5, 0.81]), 0, 1)
    col = np.repeat(lam[:, None], 3, axis=1) * np.array([0.78, 0.82, 0.88])
    ax.add_collection3d(Poly3DCollection(tri, facecolors=col,
                                         edgecolors="none"))
    lo, hi = V.min(0), V.max(0)
    c, r = (lo + hi) / 2, float((hi - lo).max()) / 2
    ax.set_xlim(c[0] - r, c[0] + r)
    ax.set_ylim(c[1] - r, c[1] + r)
    ax.set_zlim(c[2] - r, c[2] + r)
    ax.view_init(elev=18, azim=-60)      # THE fixed camera, never arbitrary
    ax.set_axis_off()
    ax.set_title(f"{name} — isometric")
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)


_VIEWS = (
    ("profile", _profile),
    ("plan", _plan),
    ("waterline", _waterline),
    ("bodyplan", _body_plan),
    ("sections", _sections_strip),
    ("isometric", _isometric),
)


def canonical_views(hull, outdir, name: str = "hull",
                    family: str | None = None) -> dict:
    """Emit the fixed view set + the descriptor sheet; return the sheet.

    The sheet is the machine half of the artifact: descriptors, critique
    findings (named, with measured value and bar), and the `shape` margin —
    the same judgement `evaluate`'s row applies, written beside the views
    a human will actually look at. Never raises on a judgeable hull; a
    hull whose descriptors cannot be measured gets a sheet that SAYS so.
    """
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, str] = {}
    for key, fn in _VIEWS:
        p = outdir / f"{name}-{key}.png"
        fn(hull, p, name)
        paths[key] = str(p)

    sheet: dict = {"name": name, "views": paths, "family": family}
    try:
        d = morphology.describe(morphology.from_hull(hull))
        c = morphology.critique(d, family=family)
        sheet["descriptors"] = {k: (None if isinstance(v, float)
                                    and math.isnan(v) else v)
                                for k, v in d.as_dict().items()}
        sheet["critique_ok"] = bool(c.ok)
        sheet["findings"] = [str(f) for f in c.findings]
        sheet["shape_margin"] = float(morphology.shape_margin(d,
                                                              family=family))
    except Exception as e:                                 # noqa: BLE001
        sheet["critique_ok"] = False
        sheet["findings"] = [f"descriptors unmeasurable: {e}"]
        sheet["shape_margin"] = None
    (outdir / f"{name}-shape.json").write_text(json.dumps(sheet, indent=1))
    return sheet
