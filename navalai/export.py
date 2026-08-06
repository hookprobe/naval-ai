"""Manufacturing export (original plan, Phases 2/5): STEP/IGES via CadQuery.

The Builder agent never touches vertices; this module is the one place where
grammar -> B-rep happens, downstream of validation. DXF panel unrolling lives
in unroll.py (Stage F).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .geometry import Hull


def _station_wires(hull: Hull, n_stations: int = 12):
    import cadquery as cq

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


def export_step(hull: Hull, path: str | Path, n_stations: int = 12,
                ev=None) -> Path:
    import cadquery as cq

    refuse_unvalidated(ev, 'STEP')

    wires = _station_wires(hull, n_stations)
    solid = cq.Solid.makeLoft(wires, ruled=True)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(cq.Workplane(obj=solid), str(path),
                        exportType="STEP")
    return path


def export_iges(hull: Hull, path: str | Path, n_stations: int = 12,
                ev=None) -> Path:
    """IGES via the OCP kernel directly (cq.exporters has no IGES type)."""
    import cadquery as cq

    refuse_unvalidated(ev, 'IGES')
    from OCP.IGESControl import IGESControl_Controller, IGESControl_Writer

    wires = _station_wires(hull, n_stations)
    solid = cq.Solid.makeLoft(wires, ruled=True)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    IGESControl_Controller.Init_s()
    writer = IGESControl_Writer()
    writer.AddShape(solid.wrapped)
    if not writer.Write(str(path)):
        raise RuntimeError("IGES write failed")
    return path
