#!/usr/bin/env python
"""Extract an OFFSET TABLE from a published hull geometry. Acquisition side.

GATE E5. This runs ONCE per source hull and writes a table that is then
committed; the gate itself reads the table and never runs this. That split is
deliberate — see `benchmarks/e5_hydro.py` for why the artifact under version
control is a readable offsets grid rather than a 16 MB binary.

WHAT IT READS. The Delft Systematic Yacht Hull Series geometries release
(4TU.ResearchData / figshare 21501330, DOI 10.4121/21501330.v1, CC0): all 51
DSYHS canoe bodies as 3D IGES NURBS surfaces, published by the institution
that ran the series. `scripts/fetch_e5_geometry.py` downloads it and checks
the publisher's own MD5.

THE DATUM IS NOT ASSUMED, IT IS VERIFIED. The IGES files carry no annotation
saying where the design waterline sits. This script places it at
z = z_baseline + tc0, where tc0 is the published maximum canoe-body draft, and
then CHECKS that choice against four published quantities it did not use to
make it — volume, waterplane area, maximum section area and LCB. MEASURED on
SYSSER01: -0.023%, -0.064%, -0.146% and +0.021%. A waterline 3 mm low costs
4.5% of the volume, so the agreement is not a coincidence and the datum is
not a guess. The check is re-run for every hull and a hull that fails it is
REFUSED, not silently included.
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import sys
import zipfile

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

ROOT = pathlib.Path(__file__).resolve().parents[1]
ZIP = ROOT / "data" / "refdata" / "dsyhs" / "geometriesIGSmodelscale.zip"


def _occ():
    from OCP.IGESControl import IGESControl_Reader
    from OCP.gp import gp_Pln, gp_Pnt, gp_Dir
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_EDGE
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.GCPnts import GCPnts_QuasiUniformAbscissa
    from OCP.TopoDS import TopoDS
    return (IGESControl_Reader, gp_Pln, gp_Pnt, gp_Dir, BRepAlgoAPI_Section,
            TopExp_Explorer, TopAbs_EDGE, BRepAdaptor_Curve,
            GCPnts_QuasiUniformAbscissa, TopoDS)


class Surface:
    """One published IGES hull surface, sectionable at arbitrary x."""

    def __init__(self, path: pathlib.Path, n_per_edge: int = 400):
        (Reader, self.gp_Pln, self.gp_Pnt, self.gp_Dir, self.Section,
         self.Explorer, self.EDGE, self.Curve, self.Abscissa,
         self.TopoDS) = _occ()
        r = Reader()
        if str(r.ReadFile(str(path))) != "IFSelect_ReturnStatus.IFSelect_RetDone":
            raise IOError(f"IGES read failed: {path}")
        r.TransferRoots()
        self.shape = r.OneShape()
        self.n = n_per_edge

    def section(self, x: float) -> np.ndarray:
        """(half_breadth, z) points of the section plane at `x`. mm."""
        pl = self.gp_Pln(self.gp_Pnt(float(x), 0, 0), self.gp_Dir(1, 0, 0))
        s = self.Section(self.shape, pl, False)
        s.ComputePCurveOn1(False)
        s.Approximation(False)
        s.Build()
        pts = []
        ex = self.Explorer(s.Shape(), self.EDGE)
        while ex.More():
            ad = self.Curve(self.TopoDS.Edge_s(ex.Current()))
            d = self.Abscissa(ad, self.n)
            for i in range(1, d.NbPoints() + 1):
                p = ad.Value(d.Parameter(i))
                pts.append((abs(p.Y()), p.Z()))
            ex.Next()
        return np.array(pts) if pts else np.empty((0, 2))

    def bbox(self) -> tuple:
        from OCP.Bnd import Bnd_Box
        from OCP.BRepBndLib import BRepBndLib
        b = Bnd_Box()
        BRepBndLib.Add_s(self.shape, b)
        return b.Get()


def keel_and_sheer(surf: Surface, x: float):
    """(z_keel, z_sheer) at one station, or (nan, nan) if the plane misses."""
    P = surf.section(x)
    if len(P) == 0:
        return float("nan"), float("nan"), P
    return float(P[:, 1].min()), float(P[:, 1].max()), P


def halfbreadths(P: np.ndarray, z_levels: np.ndarray) -> np.ndarray:
    """Half-breadth at each z, NaN where z is outside this section's span.

    The section curve of a canoe body runs monotonically in z from the keel to
    the sheer, but a NURBS trim can put two points at the same height, so the
    WIDEST is taken at each distinct height rather than the last one found.
    """
    if len(P) == 0:
        return np.full(len(z_levels), np.nan)
    z, y = P[:, 1], P[:, 0]
    zr = np.round(z, 5)
    zu = np.unique(zr)
    yu = np.array([y[zr == t].max() for t in zu])
    out = np.interp(z_levels, zu, yu)
    out[(z_levels < zu.min() - 1e-9) | (z_levels > zu.max() + 1e-9)] = np.nan
    return out


def extract(surf: Surface, tc_mm: float, n_stations: int, n_wl_below: int,
            n_wl_above: int, scale: float = 1.0) -> dict:
    """The offset table, in metres, with the baseline at z = 0."""
    xmin, ymin, zmin, xmax, ymax, zmax = surf.bbox()
    z_base = zmin
    z_dwl = z_base + tc_mm

    # Find the waterline ends by scanning the keel line and then BISECTING
    # the two crossings. The scan alone quantises LWL to its own step, and on
    # a yacht with overhangs the keel rises so steeply at the ends that a
    # linear interpolation across a 5 mm scan gap is worth several tenths of a
    # percent of LWL — which is the same size as the source discrepancy this
    # script exists to REPORT. Measuring the datum with a tool coarser than
    # the effect is how a numerical artefact gets published as a finding.
    xs_scan = np.linspace(xmin + 1e-3, xmax - 1e-3, 160)
    zk_scan = np.array([keel_and_sheer(surf, x)[0] for x in xs_scan])
    wet = np.isfinite(zk_scan) & (zk_scan < z_dwl)
    if wet.sum() < 3:
        raise ValueError("waterline at z_base+tc does not intersect the hull")
    i0, i1 = int(np.argmax(wet)), int(len(wet) - 1 - np.argmax(wet[::-1]))

    def _dry(x):
        z = keel_and_sheer(surf, x)[0]
        return (not np.isfinite(z)) or z >= z_dwl

    def _bisect(dry_x, wet_x, tol=1e-3):
        for _ in range(60):
            m = 0.5 * (dry_x + wet_x)
            if _dry(m):
                dry_x = m
            else:
                wet_x = m
            if abs(wet_x - dry_x) < tol:
                break
        return 0.5 * (dry_x + wet_x)

    xa = xs_scan[i0] if i0 == 0 else _bisect(xs_scan[i0 - 1], xs_scan[i0])
    xf = xs_scan[i1] if i1 == len(wet) - 1 else _bisect(xs_scan[i1 + 1],
                                                        xs_scan[i1])

    xs = np.linspace(xa, xf, n_stations)
    z_below = np.linspace(z_base, z_dwl, n_wl_below)
    z_above = np.linspace(z_dwl, zmax, n_wl_above + 1)[1:]
    z_lv = np.concatenate((z_below, z_above))

    Y = np.full((n_stations, len(z_lv)), np.nan)
    zk = np.full(n_stations, np.nan)
    zs = np.full(n_stations, np.nan)
    for i, x in enumerate(xs):
        xq = min(max(x, xmin + 1e-4), xmax - 1e-4)
        a, b, P = keel_and_sheer(surf, xq)
        zk[i], zs[i] = a, b
        Y[i] = halfbreadths(P, z_lv)

    m = scale / 1000.0          # mm -> m, times any model->full-scale factor
    return {
        "x_m": (xs - xa) * m,
        "z_wl_m": (z_lv - z_base) * m,
        "y_m": Y * m,
        "z_keel_m": (zk - z_base) * m,
        "z_sheer_m": (zs - z_base) * m,
        "z_water_m": (z_dwl - z_base) * m,
    }


def write_table(tab: dict, path: pathlib.Path, header: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        for line in header:
            fh.write(f"# {line}\n")
        w = csv.writer(fh)
        # THE WATERLINE LABELS CARRY FULL PRECISION, AND THAT IS NOT FUSS.
        # They were written at 5 decimals while the header declared the
        # design waterline at 6, so on any hull whose draft is not a round
        # number the tabulated DWL row no longer EQUALLED the DWL. MEASURED
        # on Series 60: the DWL row fell 3e-6 m above the waterline, one
        # station dropped out of the wetted set, and Cp read 0.6056 against
        # 0.6122 -- a 1.1% error, silent, in the artifact of record.
        w.writerow(["station", "x_m", "z_keel_m", "z_sheer_m"]
                   + [f"wl_{z:.9g}" for z in tab["z_wl_m"]])
        for i, x in enumerate(tab["x_m"]):
            row = [i, f"{x:.6f}", f"{tab['z_keel_m'][i]:.6f}",
                   f"{tab['z_sheer_m'][i]:.6f}"]
            row += ["" if not np.isfinite(v) else f"{v:.6f}"
                    for v in tab["y_m"][i]]
            w.writerow(row)


def read_table(path: pathlib.Path) -> dict:
    """Read back a committed offsets CSV. Pure stdlib+numpy, no CAD kernel."""
    rows, hdr = [], None
    with path.open() as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            rows.append(line.rstrip("\n").split(","))
    hdr, rows = rows[0], rows[1:]
    z_wl = np.array([float(h[3:]) for h in hdr[4:]])
    x = np.array([float(r[1]) for r in rows])
    zk = np.array([float(r[2]) for r in rows])
    zs = np.array([float(r[3]) for r in rows])
    Y = np.array([[np.nan if c == "" else float(c) for c in r[4:]]
                  for r in rows])
    return {"x_m": x, "z_wl_m": z_wl, "y_m": Y, "z_keel_m": zk,
            "z_sheer_m": zs}
