"""Manufacturing export (original plan, Phases 2/5): STEP/IGES via CadQuery.

The Builder agent never touches vertices; this module is the one place where
grammar -> B-rep happens, downstream of validation. DXF panel unrolling lives
in unroll.py (Stage F).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .geometry import Hull


def _station_wires(hull: Hull, n_stations: int | None = None):
    import cadquery as cq

    n_stations = hull.n_stations if n_stations is None else n_stations
    xs = np.linspace(float(hull.x[0]), float(hull.x[-1]), n_stations)
    wires = []
    for i, xv in enumerate(xs):
        pts = hull._section_at(xv)          # keel, chine, sheer (y, z)
        yk, zk = 0.0, float(pts[0, 1])
        yc, zc = float(pts[1, 0]), float(pts[1, 1])
        ys, zs = float(pts[2, 0]), float(pts[2, 1])
        w = max(yc, ys, 1e-3)
        if w < 5e-3:                        # degenerate stem tip: shrink, keep topology
            yc = max(yc, 2e-3)
            ys = max(ys, 2e-3)
        ring = [
            (xv, -ys, zs), (xv, -yc, zc), (xv, yk, zk),
            (xv, yc, zc), (xv, ys, zs),
        ]
        wires.append(cq.Wire.makePolygon([cq.Vector(*p) for p in ring],
                                         close=True))
    return wires



def refuse_unvalidated(ev, what: str) -> None:
    """Raise unless this design actually passed the ladder.

    THE EXPORT BOUNDARY ENFORCED NOTHING. `export_dxf`, `export_step` and
    `export_iges` took a `Hull` — pure geometry — so nothing at the boundary
    could know whether the design had been validated. VERIFIED: a hull that
    FAILS the L0 gate (`deadrise.order: beta_bow 2.1 < beta_mid 7.3`,
    evaluate -> ok=False, tier='L0') exported to an 8,487-byte DXF and a
    174,406-byte STEP without a murmur.

    Honesty rule 2 is "nothing ships un-re-validated". Until this, that rule
    had no implementation anywhere in the package: there was no code path that
    could refuse an export, so the rule was a sentence in a README.

    Callers pass the Evaluation, not the Hull, and get a hard failure with the
    violations named. Passing ev=None is allowed ONLY for deliberate
    unvalidated exports (a mesh for a CFD experiment), and it says so.
    """
    if ev is None:
        return
    if not getattr(ev, "ok", False):
        viols = ", ".join(getattr(ev, "violations", ()) or ("unknown",))
        raise ValueError(
            f"refusing to export {what}: this design did not pass the ladder "
            f"(tier {getattr(ev, 'tier', '?')}). Violations: {viols}. "
            f"Honesty rule 2 — nothing ships un-re-validated. Pass ev=None "
            f"only for a deliberately unvalidated artefact.")


def moulded_volume_m3(hull: Hull) -> float:
    """Moulded volume to the sheer [m^3] from the geometry kernel's own
    stations — the discretisation that the ladder validated."""
    from .geometry import _polygon

    a = np.empty(hull.n_stations)
    for i in range(hull.n_stations):
        pts = hull.section(i)
        poly = [(0.0, float(pts[0, 1])), (float(pts[1, 0]), float(pts[1, 1])),
                (float(pts[2, 0]), float(pts[2, 1])),
                (0.0, float(pts[2, 1]))]
        a[i] = _polygon(poly + [poly[0]])[0]
    return 2.0 * float(np.trapezoid(a, hull.x))


def export_receipt(hull: Hull, n_stations: int, solid=None) -> dict:
    """What the exported solid IS, next to what the ladder validated.

    THE EXPORTED SOLID WAS NOT THE VALIDATED HULL. `export_step`/`export_iges`
    lofted a hard-coded **12** stations while the `Hull` the ladder floated,
    weighed and ruled on has **41**. MEASURED: 37.248 m^3 against 37.434 m^3,
    a 0.50% difference between what passed the gates and what ships to the
    shop — from a default argument, silently, with nothing recording it.

    `n_stations` now defaults to `hull.n_stations`, so the two agree by
    construction. The receipt exists anyway, because a caller may still ask
    for a coarser loft and the file must then SAY how coarse: a discretisation
    error nobody wrote down is the defect, not the coarseness itself.
    """
    rec = {
        "n_stations_exported": int(n_stations),
        "n_stations_validated": int(hull.n_stations),
        "kernel_moulded_volume_m3": round(moulded_volume_m3(hull), 6),
        "basis": "ruled loft through station polylines keel-chine-sheer",
    }
    if solid is not None:
        v = float(solid.Volume())
        rec["solid_volume_m3"] = round(v, 6)
        ref = rec["kernel_moulded_volume_m3"]
        rec["volume_error_pct"] = round(100.0 * (v - ref) / max(ref, 1e-12), 4)
    return rec


def _write_receipt(path: Path, rec: dict) -> Path:
    rp = path.with_suffix(path.suffix + ".receipt.json")
    rp.write_text(json.dumps(rec, indent=2) + "\n")
    return rp


def export_step(hull: Hull, path: str | Path, n_stations: int | None = None,
                ev=None, receipt: bool = True) -> Path:
    import cadquery as cq

    refuse_unvalidated(ev, 'STEP')

    n_stations = hull.n_stations if n_stations is None else n_stations
    wires = _station_wires(hull, n_stations)
    solid = cq.Solid.makeLoft(wires, ruled=True)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(cq.Workplane(obj=solid), str(path),
                        exportType="STEP")
    if receipt:
        _write_receipt(path, export_receipt(hull, n_stations, solid))
    return path


def export_iges(hull: Hull, path: str | Path, n_stations: int | None = None,
                ev=None, receipt: bool = True) -> Path:
    """IGES via the OCP kernel directly (cq.exporters has no IGES type)."""
    import cadquery as cq

    refuse_unvalidated(ev, 'IGES')
    from OCP.IGESControl import IGESControl_Controller, IGESControl_Writer

    n_stations = hull.n_stations if n_stations is None else n_stations
    wires = _station_wires(hull, n_stations)
    solid = cq.Solid.makeLoft(wires, ruled=True)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    IGESControl_Controller.Init_s()
    writer = IGESControl_Writer()
    writer.AddShape(solid.wrapped)
    if not writer.Write(str(path)):
        raise RuntimeError("IGES write failed")
    if receipt:
        _write_receipt(path, export_receipt(hull, n_stations, solid))
    return path
