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

# ROWS PER SECTION WHEN THE BILGE IS RADIUSED.
#
# THE EXPORTER READ THE SECTION BY INDEX AND THE GEOMETRY KERNEL REBUILD MADE
# THAT A 99.994% ERROR (MEASURED 2026-08-13). `Hull.section()` returned exactly
# three points — keel, chine, sheer — for every hull the old kernel could draw,
# so `pts[0]`, `pts[1]`, `pts[2]` WERE the three moulded corners. Plate P2 made
# the section a shape function: at `roundness > 0` it returns 257 points and the
# first three are ~4 mm apart at the keel. Both `_station_wires` and
# `moulded_volume_m3` went on reading indices 0, 1 and 2, so the exporter lofted
# a sliver. VERIFIED on `sample_valid(3, MissionSpec(), seed=0)[0]`:
#
#     section() shape                (257, 2)
#     first three points span         0.00862 m
#     full section span               1.90618 m
#     ladder validated volume        11.172241 m^3
#     export.moulded_volume_m3        0.000650 m^3     -99.994%
#
# AND THE RECEIPT AGREED WITH IT. `volume_error_pct` compared the lofted solid
# against `moulded_volume_m3`, which read the section through the SAME broken
# index, so both sides were the sliver and the receipt printed ~0%. That is the
# 12-station loft incident (0.50%) recurring four orders of magnitude larger and
# invisible to the guard built to catch it — docs/LESSONS.md defect class 1, an
# unmeasurable quantity scored as a passing one, with a receipt on top.
#
# Two changes, and the second matters as much as the first: the section is now
# read by MEANING (`Hull.chine_row` gives the bilge row for any sampling, and
# the loft consumes the WHOLE polyline), and the receipt is now cross-checked
# against `hydrostatics.solve`, a different code path, so it can fire.
#
# nz = 64 rows: MEASURED displaced volume of the lofted wires against the
# ladder's own `solve(hull, 0.0).volume` over `sample_valid(6, seed=0)` plus the
# reference hull, at 41 stations —
#
#     nz      worst |error|
#     32          0.168%
#     64          0.042%     <- SHIPPED
#    128          0.011%
#
# against the 0.269-0.758% a deliberately coarse 12-station loft already costs.
# Buying another 0.03% by doubling every station's vertex count would be paying
# for a digit the station discretisation has already spent.
_EXPORT_SECTION_ROWS = 64

# A HARD CHINE IS EXPORTED AS THREE POINTS, EXACTLY AS BEFORE. `chine_row`
# clamps to [1, nz-1], so nz = 2 gives keel / chine / sheer and the wire is
# bit-identical to the one this module lofted before plate P2 — which is what
# keeps every hard-chine STEP, IGES and volume receipt in this tree comparable
# across the rebuild. The extra rows exist for a shape that has something
# between the keel and the sheer to describe.
_EXPORT_SECTION_ROWS_HARD_CHINE = 2

# REFUSAL BAR on the exported solid's displacement against the ladder's.
# Calibrated between measurements, not chosen: the worst legitimate value over
# the seven hulls above is 0.758% (a 12-station loft, i.e. the coarseness the
# receipt exists to report) and the positional-index defect is 99.994%. 2% is
# an order of magnitude above the first and two below the second.
EXPORT_DISPLACEMENT_BAR_PCT = 2.0

# STATIONS IN THE EXPORTED LOFT, AND WHY THE EXPORT REBUILDS THE HULL.
#
# MEASURED 2026-08-13. `Hull._section_at_rows` LERPS THE CONTROL POINTS between
# the hull's own stations, so the surface a loft describes is fixed by
# `Hull.n_stations` — 41 by default — and sampling that surface more finely
# cannot recover the boat. Area is convex in the control points, so
# `A(lerp p) <= lerp(A p)`: the loft can only ever enclose LESS than the
# trapezoid the ladder integrates, which is why every measured error is
# negative. It localises at maximum beam, where the area curve's curvature is
# highest, exactly as convexity predicts.
#
# Asking the EXPORT for more stations does not fix it, and that is the
# measurement that decided the shape of this constant: with the loft sampling a
# 41-station hull, the ladder-vs-loft gap is unchanged to four decimals at 41,
# 81, 161 and 321 export stations. So the export builds ITS OWN hull from the
# same parameters — the identical move `resistance.total_resistance` already
# makes for the Michell grid, and for the identical reason.
#
# MEASURED, loft volume against the ladder's `solve(Hull(params), 0.0)`, over
# the reference hull plus `sample_valid(6, MissionSpec(), seed=0)`:
#
#     loft hull      41         81        161        321        641
#     worst      -0.0372    +0.0360    +0.0412    +0.0451    +0.0461
#     best       -0.0014    -0.0019    -0.0006    -0.0001    +0.0001
#
# The sign flips because at 41 the LOFT is the coarse one and at 161 it has
# converged onto the true hull, leaving the LADDER's own 41-station trapezoid
# as the residual — which is positive, bounded by +0.046%, and is a separate
# and smaller question than the one this constant closes. 161 is within 0.004%
# of 641 and is station-ALIGNED (161 = 4 x 40 + 1), so the loft grid contains
# the validated hull's stations exactly rather than merely being finer: an
# unaligned count samples across the kinks at those stations and pays for it
# (measured elsewhere in this tree, nx = 81 beats nx = 320 on a 41-station
# hull).
#
# THE COST IS PAID ONCE PER EXPORT, NOT ON THE LADDER'S HOT PATH. Raising
# `Hull.n_stations` itself to 81 was measured and DECLINED: it takes
# `evaluate()` from 22.14 ms to 33.38 ms (+51%) against Gate 1's 50 ms bar, on
# every NSGA-II generation and every surrogate harvest, and it buys the LADDER
# nothing — wetted +0.014%, displaced volume +0.006%. The defect is in the
# export path and it is now fixed in the export path.
_LOFT_STATIONS = 161


def _section_rows(hull: Hull) -> int:
    return (_EXPORT_SECTION_ROWS_HARD_CHINE if hull.roundness <= 0.0
            else _EXPORT_SECTION_ROWS)


def loft_hull(hull: Hull, n_stations: int) -> Hull:
    """The hull the loft is built from — a REBUILD at `n_stations`, not a
    resampling of `hull`.

    Returns `hull` itself when the counts already agree, so a caller that hands
    in an already-dense hull pays nothing.
    """
    if hull.n_stations == n_stations:
        return hull
    return Hull(hull.params, n_stations=n_stations)


def _station_sections(hull: Hull, n_stations: int):
    """(xs, [ (N,2) section polyline per station ]) — the ONE sampling.

    `_station_wires` lofts these and `export_receipt` measures them, so the
    receipt is a statement about the solid that was written rather than about a
    second reading of the geometry.
    """
    lh = loft_hull(hull, n_stations)
    xs = np.asarray(lh.x, dtype=float)
    nz = _section_rows(lh)
    jc = lh.chine_row(nz)
    return xs, [lh._section_at_rows(float(xv), jc, nz - jc) for xv in xs]


def _station_wires(hull: Hull, n_stations: int | None = None):
    import cadquery as cq

    n_stations = _LOFT_STATIONS if n_stations is None else n_stations
    xs, sections = _station_sections(hull, n_stations)
    wires = []
    for xv, pts in zip(xs, sections):
        y = pts[:, 0].astype(float).copy()
        z = pts[:, 1].astype(float)
        # Degenerate stem tip: widen, keep topology. The old three-point form
        # floored the chine and sheer half-breadths at 2 mm and left the keel
        # apex on the centreline; this is the same rule stated for a polyline
        # of any length.
        if float(y.max()) < 5e-3:
            y[1:] = np.maximum(y[1:], 2e-3)
        ring = ([(xv, -float(y[j]), float(z[j])) for j in range(len(y) - 1, 0, -1)]
                + [(xv, 0.0, float(z[0]))]
                + [(xv, float(y[j]), float(z[j])) for j in range(1, len(y))])
        wires.append(cq.Wire.makePolygon([cq.Vector(*p) for p in ring],
                                         close=True))
    return wires


#: Points sampled BETWEEN each pair of loft stations when the receipt measures
#: the exported solid. See `_displaced_volume_of`.
_RECEIPT_SUBSAMPLE = 8


def _displaced_volume_of(xs: np.ndarray, sections, wl: float = 0.0) -> float:
    """Displaced volume [m^3] of the EXPORTED polylines, cut at `wl`.

    Deliberately computed from the points the loft consumes and nowhere else:
    its whole job is to disagree with `hydrostatics.solve`, which derives the
    same number from `Hull.immersed_section`'s closed form. Two readings that
    share a code path cannot cross-check each other, and that is precisely how
    a 99.994% error came to be reported as 0%.

    IT IS EVALUATED ONLY AT THE STATIONS HANDED IN, WHICH IS THE HALF THIS
    FUNCTION CANNOT SEE — `measure_lofted_displacement` below is what the
    receipt calls, and it exists because of that blindness.
    """
    from .geometry import _polygon

    a = np.empty(len(xs))
    for k, pts in enumerate(sections):
        if float(pts[0, 1]) >= wl:
            a[k] = 0.0
            continue
        m = int(np.count_nonzero(pts[:, 1] < wl))        # z is monotone
        poly = [(float(p[0]), float(p[1])) for p in pts[:m]]
        if m < len(pts):
            prev, cur = pts[m - 1], pts[m]
            t = (wl - float(prev[1])) / (float(cur[1]) - float(prev[1]))
            poly.append((float(prev[0]) + t * (float(cur[0]) - float(prev[0])),
                         wl))
        poly.append((0.0, wl))
        a[k] = _polygon(poly + [poly[0]])[0]
    return 2.0 * float(np.trapezoid(a, xs))


def measure_lofted_displacement(hull: Hull, n_stations: int,
                                wl: float = 0.0) -> float:
    """Displaced volume [m^3] of the SOLID THE LOFT DESCRIBES, not of its
    stations.

    A RECEIPT THAT SAMPLES ONLY AT THE STATIONS IS BLIND TO THE ONE THING IT
    IS FOR. `_displaced_volume_of` evaluated at the loft's own stations returns
    the trapezoid of the EXACT section areas there, which is arithmetically the
    ladder's own integral — so at `n_stations == hull.n_stations` it read
    0.0000% and could not see the between-station term at all. That is the
    same shape of defect as the `volume_error_pct` it replaced: a cross-check
    that shares its answer with the thing it is checking.

    A ruled loft is LINEAR IN THE CONTROL POINTS between consecutive stations,
    and `Hull._section_at_rows` reproduces exactly that interpolation, so
    sub-sampling between the stations measures the surface that will be
    written. MEASURED convergence in the sub-sample count on the roundest hull
    of `sample_valid(6, MissionSpec(), seed=0)`, error against the ladder:

        sub    1        2        4        8       16       32
             -0.0321  -0.0080  -0.0020  -0.0005  -0.0001  -0.0000

    8 is shipped: the residual it leaves is 0.0005%, three orders inside the
    2% refusal bar and two inside the tightest volume tolerance in the tree.
    """
    lh = loft_hull(hull, n_stations)
    st = np.asarray(lh.x, dtype=float)
    xs = np.unique(np.concatenate(
        [np.linspace(st[i], st[i + 1], _RECEIPT_SUBSAMPLE + 1)
         for i in range(len(st) - 1)]))
    nz = _section_rows(lh)
    jc = lh.chine_row(nz)
    sections = [lh._section_at_rows(float(xv), jc, nz - jc) for xv in xs]
    return _displaced_volume_of(xs, sections, wl)


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
        pts = np.asarray(hull.section(i), dtype=float)
        # THE WHOLE POLYLINE, not indices 0/1/2. `section()` runs keel -> sheer
        # and its first point is already on the centreline, so the moulded
        # half-section is the polyline closed back to the centreline at the
        # sheer height. This is the same polygon the old three-point form
        # described — for a hard chine it reproduces it exactly — but it is
        # stated for a section of ANY length, which is what the index read
        # could not survive.
        poly = [(float(y), float(z)) for y, z in pts]
        poly.append((0.0, float(pts[-1, 1])))
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

    THE RECEIPT COULD NOT FAIL, AND THAT IS WHY IT DID NOT (2026-08-13).
    `volume_error_pct` divided the lofted solid by `moulded_volume_m3`, and
    both read `Hull.section()` by index — so when plate P2 turned the section
    into a 257-point shape function and the index read collapsed to a sliver,
    BOTH sides collapsed together and the receipt reported a fraction of a
    percent on a 99.994% error. A cross-check between two readings that share a
    code path is not a cross-check; it is the same number printed twice, which
    is this repository's oldest defect wearing a receipt.

    So the receipt now carries an INDEPENDENT reference. `displaced_volume_m3`
    is integrated from the polylines the loft actually consumes; the ladder's
    own `hydrostatics.solve(hull, 0.0).volume` comes from
    `Hull.immersed_section`'s closed-form five-control-point algebra. Nothing
    is shared between them but the hull. `displacement_error_pct` is the
    disagreement, and `export_step`/`export_iges` REFUSE above
    `EXPORT_DISPLACEMENT_BAR_PCT`.
    """
    from . import hydrostatics as _H

    exported = measure_lofted_displacement(hull, n_stations, 0.0)
    ladder = float(_H.solve(hull, 0.0).volume)
    rec = {
        "n_stations_exported": int(n_stations),
        "n_stations_validated": int(hull.n_stations),
        "section_rows": int(_section_rows(hull)),
        "roundness": round(float(hull.roundness), 6),
        "kernel_moulded_volume_m3": round(moulded_volume_m3(hull), 6),
        # the two independent readings, and their disagreement
        "displaced_volume_m3": round(exported, 6),
        "ladder_displaced_volume_m3": round(ladder, 6),
        "displacement_error_pct": round(
            100.0 * (exported - ladder) / max(abs(ladder), 1e-12), 4),
        "displacement_bar_pct": EXPORT_DISPLACEMENT_BAR_PCT,
        "basis": "ruled loft through station polylines, keel -> bilge -> sheer",
    }
    if solid is not None:
        v = float(solid.Volume())
        rec["solid_volume_m3"] = round(v, 6)
        ref = rec["kernel_moulded_volume_m3"]
        rec["volume_error_pct"] = round(100.0 * (v - ref) / max(ref, 1e-12), 4)
    return rec


def refuse_wrong_solid(rec: dict, what: str) -> None:
    """Refuse an export whose displacement is not the one the ladder validated.

    FED THE VERBATIM CASE IT EXISTS TO REJECT by `tests/test_stageC.py` — a
    section read through the pre-plate-P2 three-index form, which reads
    -99.994% here. The bar is calibrated between
    measurements: 0.758% is the worst legitimate value over seven hulls
    (including a deliberately coarse 12-station loft) and 99.994% is the
    defect. See `EXPORT_DISPLACEMENT_BAR_PCT`.
    """
    err = float(rec["displacement_error_pct"])
    if abs(err) > EXPORT_DISPLACEMENT_BAR_PCT:
        raise ValueError(
            f"refusing to export {what}: the lofted solid displaces "
            f"{rec['displaced_volume_m3']:.6f} m^3 against the "
            f"{rec['ladder_displaced_volume_m3']:.6f} m^3 the ladder "
            f"validated — {err:+.4f}%, past the "
            f"{EXPORT_DISPLACEMENT_BAR_PCT}% bar. This is not the boat that "
            f"passed the gates.")


def _write_receipt(path: Path, rec: dict) -> Path:
    rp = path.with_suffix(path.suffix + ".receipt.json")
    rp.write_text(json.dumps(rec, indent=2) + "\n")
    return rp


def export_step(hull: Hull, path: str | Path, n_stations: int | None = None,
                ev=None, receipt: bool = True) -> Path:
    import cadquery as cq

    refuse_unvalidated(ev, 'STEP')

    n_stations = _LOFT_STATIONS if n_stations is None else n_stations
    wires = _station_wires(hull, n_stations)
    solid = cq.Solid.makeLoft(wires, ruled=True)
    # BEFORE THE WRITE, not after. A refusal that leaves the wrong file on disk
    # has refused nothing.
    rec = export_receipt(hull, n_stations, solid)
    refuse_wrong_solid(rec, "STEP")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(cq.Workplane(obj=solid), str(path),
                        exportType="STEP")
    if receipt:
        _write_receipt(path, rec)
    return path


def export_iges(hull: Hull, path: str | Path, n_stations: int | None = None,
                ev=None, receipt: bool = True) -> Path:
    """IGES via the OCP kernel directly (cq.exporters has no IGES type)."""
    import cadquery as cq

    refuse_unvalidated(ev, 'IGES')
    from OCP.IGESControl import IGESControl_Controller, IGESControl_Writer

    n_stations = _LOFT_STATIONS if n_stations is None else n_stations
    wires = _station_wires(hull, n_stations)
    solid = cq.Solid.makeLoft(wires, ruled=True)
    rec = export_receipt(hull, n_stations, solid)
    refuse_wrong_solid(rec, "IGES")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    IGESControl_Controller.Init_s()
    writer = IGESControl_Writer()
    writer.AddShape(solid.wrapped)
    if not writer.Write(str(path)):
        raise RuntimeError("IGES write failed")
    if receipt:
        _write_receipt(path, rec)
    return path
