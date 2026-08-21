"""Developable-panel unrolling -> flat plate outlines -> NESTED DXF (original
plan Phase 5: 'structural DXF formats for manufacturing export').

Method: triangle development of the ruled surface between two 3-D edge
curves (keel-chine for the bottom panel, chine-sheer for the topside).
Isometric by construction along edges and one diagonal family; the residual
on the OTHER diagonal family is `dev_error_rel`.

FOUR THINGS THIS MODULE NOW DOES THAT IT CLAIMED TO DO AND DID NOT
------------------------------------------------------------------

1. `dev_error_rel` CANNOT FAIL, and was the only developability metric here.
   It is a per-quad chord residual, i.e. O(h^2) discretisation error for ANY
   smooth surface, so refining the polyline makes anything look developable.
   MEASURED, dev_error_rel vs polyline stations:

       surface                     n=41       n=161      order over 41->161
       true cylinder            5.3e-16     5.3e-16      (exact)
       cone                     2.7e-10     6.8e-11      (exact)
       hyperbolic paraboloid    6.5e-04     4.0e-05      O(h^2.01)
       hull bottom panel        3.2e-04     2.0e-05      O(h^1.99)
       hull topside panel       1.9e-03     1.2e-03      O(h^0.34)

   The hypar z = 1.5xy is DOUBLY RULED and emphatically NOT developable, and
   it scored 6.5e-4 at n=41 — inside the 5e-3 bar the old cylinder test used
   and 77x inside the 5e-2 bar the hull test used. The refinement-convergence
   test that the gap register proposed as the fix ALSO fails to separate it:
   the hypar converges at O(h^2.01), the same rate as the genuinely
   developable-in-the-mean hull bottom.

   What DOES separate them is the classical criterion for a ruled surface
   X(u,v) = A(u) + v*(B(u)-A(u)): it is developable iff A', r and r' are
   coplanar. `ruling_twist` is |det(A', r, r')| normalised by the three
   lengths — a dimensionless sine of the twist angle that does NOT shrink
   under refinement. MEASURED at n=41, max / median over the polyline (and
   every one of these is the SAME at n=161, to 6 figures on the median):

       true cylinder          0.00e+00 / 0.00e+00     developable
       cone                   5.5e-17  / 0.00e+00     developable
       hypar z = 1.5xy        1.000    / 0.555        NOT developable
       hull bottom panel      0.288    / 3.8e-15      developable except the
                                                      bow warp zone
       hull topside panel     0.958    / 0.617        NOT developable

   RECORDED, NOT SOFTENED: by this criterion the hull's TOPSIDE panel is not
   developable at all, and is indistinguishable from the hypar negative
   control. That is a property of taking the rulings at constant station x:
   r then lies in the y-z plane, so det(A', r, r') = A'_x * (r x r')_x, which
   vanishes only where the section shape stops changing. Developable-hull
   design solves for SLANTED rulings; `hull_panels` does not, and no bar here
   is set where the hull would pass and the hypar would fail.

   SUPERSEDED IN PART, 2026-08-11: `hull_panels` DOES now solve for slanted
   rulings — see item 4. The twist figures above are what the CONSTANT-X
   family reads and stay reproducible via `hull_panels(hull, "constant-x")`;
   the fitted family reads 0.029 max / 0.000 median on the bottom and 0.432
   max / 0.0074 median on the topside — the topside's MEDIAN is 83x lower and
   no longer the hypar's, though its peak is not. Conclusion unchanged: item 4.

2. THE REFOLD WAS NEVER TESTED. Gate 6 claims "exported panels re-fold to the
   hull within tolerance" and no code mapped 2-D back to 3-D. `refold` does,
   and the answer is a RED finding — see its docstring.

3. THERE WAS NO NESTING, ONLY STACKING. `export_dxf` offset each panel in y:
   no rotation, no sheet boundaries, no packing, and no splitting. The two
   hull panels measure 10.05 x 1.62 m and 10.54 x 1.44 m against a
   1.22 x 2.44 m marine-ply sheet, so NEITHER FITS ON ANY SHEET, while
   `engineer.assess()` reported "35 ply sheets" from area x a declared 1.30
   waste factor. Panels are now split at scarph joints, packed with rotation
   by MaxRects, and the sheet count is COUNTED off the layout.

4. SLANTED RULINGS HALVE THE REFOLD MISS AND DO NOT CLEAR IT — the hull is not
   developable (gap G4 / Gate 6D, 2026-08-11). The clearing condition on record
   was "solve for SLANTED rulings instead of constant-x ones". That is now
   done (`developable_pairing`), and MEASURED on the reference hull at the
   shipped 41 stations, worst of the two panels, two-sided panel-vs-hull:

       ruling family      bottom-stbd        topside-stbd      worst
       constant-x          140.2 mm            224.5 mm       224.5 mm
       developable          48.1 mm             66.2 mm        66.2 mm

   Better by 3.4x, still 13x outside the 5 mm bar. THREE mechanisms hold the
   rest and NOT ONE of them is a ruling choice:

   (a) NO EXACT DEVELOPABLE SPANS THE BOTTOM PANEL'S TWO EDGES. March the
       planarity condition forward from the transom with the keel at uniform
       stations and it TERMINATES at keel x = 7.25 m: the plane through the
       current ruling and the next keel point no longer meets the chine ahead.
       The fit can still reach machine-zero warp with both ends pinned, and the
       way it does it is to put 1.846 m of chine — 7.4x the mean station
       spacing — into ONE quad, whose chord then misses the chine by 97.5 mm.
       On that panel the edge-only `refold_deviation_mm` reads 0.07 mm.
       `_MAX_RULING_STEP` refuses to buy developability that way and
       `refold_surface_deviation_mm` is two-sided so it cannot be bought again.
   (b) THE SHEER POLYLINE IS ALREADY 65.6 mm OFF THE SHEER CURVE at 41
       stations, before developability is even asked about, and it converges at
       roughly O(h^0.5): 81.0 / 65.6 / 47.3 / 29.9 mm at 21 / 41 / 81 / 161
       stations. `y_sheer = ys * w**0.15` drives dy/dx to infinity at the stem
       (-0.68 at x = 9.7 m, -1.99 at x = 10.0 m and unbounded in the limit), so
       no uniform sampling resolves it. That is the floor the topside panel
       sits on, and it is a GRAMMAR property, not an unroller one.
   (c) THE CHINE AND SHEER HAVE A SLOPE DISCONTINUITY at x = x_mb * L (5.50 m
       here), where the plan-form exponent switches branches and dw/dx jumps
       from 0.1364 to 0 — a CREASE in both edge curves. The fitted topside
       panel refolds to 0.69-0.92 mm everywhere aft of it and steps to
       6.02-6.16 mm at exactly that station (i=22 -> i=23) and stays there. So
       the crease costs the panel a 6 mm floor on its own, and it too is a
       grammar property.

DXF: minimal R12 ASCII (POLYLINE/VERTEX/SEQEND) — the most widely readable
dialect for CNC/nesting shops — in MILLIMETRES, declared via $INSUNITS 4.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path

import re as _re

import numpy as np

from . import grammar
from .geometry import Hull
from .limits import PLY_THICKNESS_M

# Standard marine-plywood sheet [m]. ONE definition: `engineer.py` used to
# carry `SHEET_M2 = 1.22 * 2.44` privately, which is the "a number declared
# twice" defect this codebase keeps finding. Nesting owns the sheet, because
# nesting is the only thing that can be wrong about it.
SHEET_W_M = 1.22
SHEET_L_M = 2.44
SHEET_M2 = SHEET_W_M * SHEET_L_M

# A plywood scarph is cut 8:1 on thickness. The two mating tapers OVERLAP, so
# one joint consumes 8t of extra material in total, i.e. 4t added to each of
# the two pieces that meet there — not 8t each, which would double-count the
# overlap.
SCARPH_RATIO = 8.0


def _tri_place(p: np.ndarray, q: np.ndarray, dp: float, dq: float,
               sign: float) -> np.ndarray:
    """Point at distance dp from p and dq from q, on side `sign` of p->q."""
    d = float(np.linalg.norm(q - p))
    if d < 1e-12:
        return p + np.array([dp, 0.0])
    ex = (q - p) / d
    ey = np.array([-ex[1], ex[0]]) * sign
    x = (dp**2 - dq**2 + d**2) / (2.0 * d)
    y2 = max(dp**2 - x**2, 0.0)
    return p + ex * x + ey * np.sqrt(y2)


def ruling_twist(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """Per-station developability of the ruled strip between A and B.

    For X(u, v) = A(u) + v r(u) with r = B - A, the surface is developable iff
    det(A', r, r') == 0 everywhere. Normalising by |A'| |r| |r'| makes it the
    sine of the angle between A' and the plane of (r, r'): dimensionless, in
    [0, 1], and — unlike the chord residual it replaces — INVARIANT under
    refinement of the polyline. That invariance is the whole point: a metric
    you can drive to zero by adding stations is not a metric.

    Returns the per-station array so a caller can distinguish a locally warped
    panel (hull bottom: median 1.9e-14, max 0.291 in the bow warp zone) from
    a globally warped one (hull topside: median 0.541).
    """
    A = np.asarray(A, dtype=float)
    B = np.asarray(B, dtype=float)
    r = B - A
    u = np.arange(len(A), dtype=float)
    dA = np.gradient(A, u, axis=0)
    dr = np.gradient(r, u, axis=0)
    num = np.abs(np.einsum("ij,ij->i", dA, np.cross(r, dr)))
    den = (np.linalg.norm(dA, axis=1) * np.linalg.norm(r, axis=1)
           * np.linalg.norm(dr, axis=1))
    return np.where(den > 1e-300, num / np.maximum(den, 1e-300), 0.0)


def quad_warp(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """Per-QUAD non-planarity of the strip, normalised. (n-1,) array.

    `ruling_twist` is the continuous criterion; this is its discrete twin, and
    it is the one that predicts the refold, because the development and the
    refold are both operations on QUADS:

      * `develop` splits quad i on the diagonal (A[i+1], B[i]) and lays the two
        triangles out flat. Both triangles are placed EXACTLY, so the flat
        pattern is a perfect isometry of the polyhedral strip. What it cannot
        preserve is the OTHER diagonal (A[i], B[i+1]) — unless the four corners
        were coplanar to begin with.
      * `refold` rebuilds B[i+1] by trilaterating from B[i], A[i+1] and A[i],
        and the third of those three distances is exactly that other diagonal.

    So a planar quad refolds exactly and a warped one does not, and the error
    is fed forward into the next station's datum. This returns
    det(A[i+1]-A[i], B[i]-A[i], B[i+1]-A[i]) over the product of the three edge
    lengths: dimensionless, signed, zero iff the quad is planar.
    """
    A = np.asarray(A, dtype=float)
    B = np.asarray(B, dtype=float)
    d1 = A[1:] - A[:-1]
    d2 = B[:-1] - A[:-1]
    d3 = B[1:] - A[:-1]
    num = np.einsum("ij,ij->i", np.cross(d1, d2), d3)
    den = (np.linalg.norm(d1, axis=1) * np.linalg.norm(d2, axis=1)
           * np.linalg.norm(B[1:] - B[:-1], axis=1))
    return num / np.maximum(den, 1e-300)


@dataclass(frozen=True)
class FlatPanel:
    name: str
    edge_a: np.ndarray        # (n, 2) developed first edge
    edge_b: np.ndarray        # (n, 2) developed second edge
    dev_error_rel: float      # max cross-diagonal mismatch / panel width
    twist_max: float = 0.0    # max  |det(A',r,r')| / (|A'||r||r'|)
    twist_median: float = 0.0
    src_a: np.ndarray | None = field(default=None, compare=False)
    src_b: np.ndarray | None = field(default=None, compare=False)
    # WHICH RULING FAMILY THIS PANEL WAS DEVELOPED ON, and the longitudinal
    # parameters the two edges were sampled at. Recorded rather than implied:
    # the panel's flat outline is the same shape either way, and the only way a
    # reader can tell a constant-x development from a fitted one is if the
    # panel says so.
    rulings: str = "constant-x"
    par_a: np.ndarray | None = field(default=None, compare=False)
    par_b: np.ndarray | None = field(default=None, compare=False)

    @property
    def outline(self) -> np.ndarray:
        return np.vstack([self.edge_a, self.edge_b[::-1]])

    # `perimeter()` WAS HERE AND NOTHING CALLED IT — zero references across
    # navalai/, tests/, scripts/ and ui/. Deleted rather than kept "in case":
    # an unexercised method is an untested one, and a cut plan that reads a
    # perimeter from a method no gate has ever run is worse than one that
    # computes it at the call site. `nesting.py` measures cut length off the
    # nested outline it actually places.

    def area(self) -> float:
        """Developed area [m^2] by the shoelace formula on the flat outline."""
        o = self.outline
        x, y = o[:, 0], o[:, 1]
        return float(abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))
                     / 2.0)


def develop(A: np.ndarray, B: np.ndarray, name: str) -> FlatPanel:
    """Flatten the ruled surface between 3-D polylines A and B (same length)."""
    A = np.asarray(A, dtype=float)
    B = np.asarray(B, dtype=float)
    n = len(A)
    a2 = np.zeros((n, 2))
    b2 = np.zeros((n, 2))
    b2[0] = (0.0, float(np.linalg.norm(B[0] - A[0])))
    for i in range(n - 1):
        a2[i + 1] = _tri_place(a2[i], b2[i],
                               float(np.linalg.norm(A[i + 1] - A[i])),
                               float(np.linalg.norm(A[i + 1] - B[i])), -1.0)
        b2[i + 1] = _tri_place(a2[i + 1], b2[i],
                               float(np.linalg.norm(B[i + 1] - A[i + 1])),
                               float(np.linalg.norm(B[i + 1] - B[i])), -1.0)
    # the diagonal family NOT used in construction: an isometry residual, and
    # O(h^2) for any smooth surface — see the module docstring for why this is
    # NOT a developability verdict.
    err = 0.0
    width = max(float(np.linalg.norm(B[0] - A[0])), 1e-9)
    for i in range(n - 1):
        d3 = float(np.linalg.norm(B[i + 1] - A[i]))
        d2 = float(np.linalg.norm(b2[i + 1] - a2[i]))
        err = max(err, abs(d3 - d2))
        width = max(width, float(np.linalg.norm(B[i] - A[i])))
    tw = ruling_twist(A, B)
    return FlatPanel(name, a2, b2, err / width,
                     float(tw.max()), float(np.median(tw)), A.copy(), B.copy())


# The LAMBDA LADDER for the pairing fit. Each rung is a full LM solve warm-
# started from the previous one, on
#     [ quad_warp ; lam * d2(v)/dx2 ; min-step barrier ; max-step barrier ].
# The planarity condition has several roots, and the smoothing term is what
# keeps the fit on the one that starts at the identity. MEASURED, worst
# two-sided deviation on the reference hull at 41 stations, taking only the
# LAST k rungs (i.e. starting the continuation at a smaller lambda):
#
#     rungs        1      2      3      5      7     10
#     bottom mm  69.9   70.2   70.2   70.2   70.2   48.1
#     topside mm 94.5   81.1   79.3   75.6   75.5   66.2
#
# The full ladder is worth 22 mm on the bottom and 28 mm on the topside over
# ANY truncation of it, and the jump is at the top rung: it is the strong
# smoothing at lambda = 1e-1, not the fine tail, that finds the better branch.
# Starting higher than 1e-1 was not measured.
_PAIRING_LAMBDAS = tuple(10.0 ** (-1 - k) for k in range(9)) + (0.0,)
_PAIRING_ITERS = 60
# Coarsest level of the station-count multigrid (see `developable_pairing`).
_PAIRING_COARSEST = 21
# A ruling may not come closer than this fraction of the mean station spacing
# to its neighbour. Rulings fanning into the stem is real, but a pairing free
# to stack rulings on top of each other can drive the residual down by skipping
# hull instead of by fitting it, and the metric is only evaluated AT the
# rulings — the same shape of defect as measuring a gate at a configuration the
# product never runs.
_MIN_RULING_STEP = 0.05
# ...and it may not SKIP more than this multiple of the mean spacing either.
# The panel edge is a polyline through the paired points, so a ruling that
# jumps 1.8 m of chine draws a chord that misses the chine by 97 mm. Bounding
# only the lower end let the fit buy a machine-zero warp with a panel whose
# boundary was no longer the boundary of the hull — the edge-only
# `refold_deviation_mm` read 0.07 mm on exactly that panel.
#
# CHOSEN ON ONE STATED CRITERION: the WORST-PANEL two-sided deviation
# (`refold_surface_deviation_mm`), over the reference hull and two
# rejection-sampled grammar hulls, at 41 and 161 stations. MEASURED [mm]:
#
#     cap x mean spacing      2.0     3.0     4.0     6.0    none
#     mid    n= 41           93.6    69.3    66.2    74.0    97.5
#     mid    n=161           97.7   106.8   102.2    90.0    97.3
#     rand0  n= 41          454.4   470.0   424.8   437.7   437.7
#     rand0  n=161          447.5  1938.1   435.2   458.0  1755.6
#     rand1  n= 41         1151.7   856.3   885.1   931.3  1012.9
#     rand1  n=161         1447.6   887.7   750.9   897.8  1375.8
#
# 4.0 is best in four of the six rows and never far off in the other two. IT
# IS NOT A SHARP OPTIMUM — this is a CALIBRATED constant, not a derived one,
# and it is stated as such rather than quoted as if the geometry chose it.
_MAX_RULING_STEP = 4.0
# Sampling used for the ACCEPTANCE GUARD only, not for a reported number.
# `hull_panels` is on the path of `engineer.assess`, which the PLM network runs
# per candidate, so the guard cannot afford the reporting resolution: 0.065 s
# against 0.50 s per call, four calls per hull. MEASURED against the reporting
# default over the reference hull and two rejection-sampled hulls, both ruling
# families, both panels — 12 cases: identical to 6 figures in 11 of them and
# 47.995 vs 48.067 mm in the twelfth, i.e. 0.15%. A guard decides a
# COMPARISON, and a 0.15% offset applied to both sides of it does not.
_GUARD_SAMPLING = {"n_hull": 201, "n_along": 4, "n_across": 5}


def _pairing_residual(hull, ia, ib, x, lam, A):
    """residual(d) for the pairing v = x + [0, d, 0]."""
    h = float(x[-1] - x[0]) / (len(x) - 1)

    def f(d):
        v = x.copy()
        # CLIPPED TO THE CURVE'S OWN DOMAIN. The step barriers below are soft,
        # so a trial iterate can put a parameter outside [0, LWL]; the chine
        # plan-form then evaluates (x/x_mb)**p_stern on a negative base and
        # `station_geometry` returns NaN, which an LM reads as "not an
        # improvement" and quietly works around. A hull curve does not exist
        # outside its own length, so the trial point is clamped to where it
        # does, and the final pairing is asserted in range by the caller.
        v[1:-1] = np.clip(x[1:-1] + d, x[0], x[-1])
        B = hull.edge_curves(v)[ib]
        return np.concatenate([
            quad_warp(A, B),
            lam * np.diff(v, 2) / h,
            200.0 * np.maximum(_MIN_RULING_STEP * h - np.diff(v), 0.0) / h,
            200.0 * np.maximum(np.diff(v) - _MAX_RULING_STEP * h, 0.0) / h,
        ])

    return f


def _column_rows(npar: int, nres: int) -> list[np.ndarray]:
    """Rows each pairing parameter can touch, per residual block.

    Parameter k is the offset of v[k+1]. The residual is four banded blocks:
    quad_warp (npar+1 rows, row j reads v[j], v[j+1]), the second difference
    (npar rows, row j reads v[j..j+2]), and the two step barriers (npar+1 rows
    each, row j reads v[j], v[j+1]). Written out rather than inferred, because
    an over-wide mask is what makes a grouped finite difference silently
    ALIAS: with columns perturbed three apart, a mask reaching two rows back
    hands column k a derivative that belongs to column k-3, and the LM then
    proposes steps from a Jacobian nobody measured.
    """
    blocks = ((0, npar + 1, 0, 2),                     # warp:  j in {k, k+1}
              (npar + 1, npar, -1, 2),                 # smooth: j in {k-1..k+1}
              (2 * npar + 1, npar + 1, 0, 2),          # min-step barrier
              (3 * npar + 2, npar + 1, 0, 2))          # max-step barrier
    out = []
    for k in range(npar):
        rows = []
        for off, size, lo, hi in blocks:
            if off >= nres:
                continue
            j = np.arange(max(k + lo, 0), min(k + hi, size))
            rows.append(j + off)
        out.append(np.concatenate(rows) if rows else np.zeros(0, dtype=int))
    return out


def _lm(f, d0, npar, iters):
    """Levenberg-Marquardt with a STRUCTURED Jacobian.

    Every residual block is banded in the pairing parameters, so perturbing
    every third parameter at once touches disjoint rows and the whole Jacobian
    costs 3 residual evaluations instead of `npar`. MEASURED on the reference
    hull's bottom panel at 41 stations: 0.130 s against 0.646 s for a
    column-at-a-time finite difference, i.e. 5.0x, for a Jacobian that agrees
    with the dense one to 0.0. `hull_panels` is on the path of
    `engineer.assess`, which the PLM network runs per candidate.
    """
    d = np.asarray(d0, dtype=float).copy()
    r = f(d)
    cost = 0.5 * float(r @ r)
    mu = 1e-3
    eps = 1e-7
    groups = [np.arange(g, npar, 3) for g in range(3)]
    rows_of = _column_rows(npar, len(r))
    for _ in range(iters):
        J = np.zeros((len(r), npar))
        for g in groups:
            if not len(g):
                continue
            q = d.copy()
            q[g] += eps
            col = (f(q) - r) / eps
            for k in g:
                rows = rows_of[k]
                J[rows, k] = col[rows]
        H = J.T @ J
        g_ = J.T @ r
        moved = False
        step = np.zeros(npar)
        for _ in range(30):
            try:
                step = np.linalg.solve(
                    H + mu * np.diag(np.maximum(np.diag(H), 1e-12)), -g_)
            except np.linalg.LinAlgError:
                mu *= 10.0
                continue
            rq = f(d + step)
            cq = 0.5 * float(rq @ rq)
            if cq < cost:
                d, r, cost = d + step, rq, cq
                mu = max(mu / 3.0, 1e-12)
                moved = True
                break
            mu *= 5.0
        if not moved or float(np.linalg.norm(step)) < 1e-14:
            break
    return d


def developable_pairing(hull: Hull, edge_a: int, edge_b: int) -> np.ndarray:
    """Longitudinal parameters at which edge B is sampled, one per ruling.

    THE FIX FOR GAP G4 / GATE 6D. `hull_panels` used to pair station i of one
    edge with station i of the other, so every ruling lay in a constant-x
    plane. A ruled surface is developable iff det(A', r, r') vanishes, and with
    r confined to the y-z plane that determinant is A'_x (r x r')_x, which is
    zero only where the section shape stops changing. Constant-x rulings are
    therefore developable ONLY on a hull whose sections do not change shape —
    which is why the aft half of the bottom panel (constant deadrise, flat
    keel: a plane) refolded to 0.008 mm while the forefoot, where the deadrise
    warps 8 deg -> 30 deg, refolded 141.0 mm off.

    So the ruling for keel station i is allowed to land at chine parameter
    v[i] != x[i]. v[0] and v[-1] stay pinned at the ends of the curve — the
    panel must still span the whole edge, not a convenient part of it — and the
    interior is solved so that every quad is planar.

    Returns v (n,). The step bounds are PENALTIES rather than constraints, so
    monotonicity is what the solve produces and not what it promises:
    `hull_panels` checks `np.all(np.diff(v) > 0)` and falls back to constant-x
    rulings if it fails. The caller samples edge B with `Hull.edge_curves(v)`,
    i.e. the CLOSED FORM, not an interpolant.
    """
    x = np.asarray(hull.x, dtype=float)
    if len(x) - 2 < 1:
        return x.copy()
    # MULTIGRID IN THE STATION COUNT: solve coarse, interpolate the pairing up,
    # re-solve. It costs about 30% of the runtime and it is kept for ONE
    # measured reason -- it removes a catastrophic local minimum. Worst-panel
    # two-sided deviation [mm], cold start vs multigrid:
    #
    #     hull      n= 41         n=161            n=321
    #     mid     66.3 / 66.2   94.4 / 102.2   113.4 / 104.4
    #     rand0  426.2 / 424.8  435.1 / 435.2   439.3 / 439.3
    #     rand1  885.1 / 885.1 1262.2 / 750.8   452.4 / 452.4
    #
    # So it is a WASH on five of the nine and it is worth 511 mm on rand1 at
    # 161 stations. It also costs 8 mm on mid at 161 and buys 9 mm back at 321,
    # which is the honest shape of the result: this is variance reduction on a
    # non-convex fit, not convergence.
    levels = []
    m = _PAIRING_COARSEST
    while m < len(x):
        levels.append(m)
        m = 2 * m - 1
    levels.append(len(x))
    d = None
    for m in levels:
        xm = np.linspace(float(x[0]), float(x[-1]), m)
        Am = hull.edge_curves(xm)[edge_a]
        dm = (np.zeros(m - 2) if d is None
              else np.interp(xm[1:-1], prev_x, prev_d))
        for lam in _PAIRING_LAMBDAS:
            dm = _lm(_pairing_residual(hull, edge_a, edge_b, xm, lam, Am),
                     dm, m - 2, _PAIRING_ITERS)
        dm = np.clip(xm[1:-1] + dm, xm[0], xm[-1]) - xm[1:-1]
        prev_x, prev_d = xm, np.concatenate([[0.0], dm, [0.0]])
        d = dm
    v = x.copy()
    v[1:-1] = x[1:-1] + d
    if not (v[0] >= x[0] - 1e-12 and v[-1] <= x[-1] + 1e-12
            and np.all(v >= x[0] - 1e-12) and np.all(v <= x[-1] + 1e-12)):
        raise ValueError("developable_pairing left the curve's domain")
    return v


def developable_seams(hull: Hull, edge_a: int, edge_b: int,
                      n_a: int = 200, n_b: int = 1500,
                      jump_tol: float = 0.06) -> list[float]:
    """Longitudinal stations [m] where the developable ruling family BREAKS.

    THE MATH, because the previous approach was solving the wrong problem.
    For X(u,t) = A(u) + t*(B(s(u)) - A(u)) the surface normal is
    (A' + t*rdot) x r, and the surface is developable iff that direction does
    not depend on t, i.e. det[A', rdot, r] = 0. With rdot = B'*s' - A' and
    det[A', A', r] = 0 identically, this collapses to

        s'(u) * det[A'(u), B'(s), B(s) - A(u)] = 0

    so away from s' = 0 the condition is ALGEBRAIC IN s, not a differential
    equation: at each u, a developable ruling exists iff that determinant has a
    root in s. That is an EXISTENCE test, and it is not what `ruling_twist`
    measures -- twist is the residual of one particular pairing.

    MEASURED 2026-08-12 on the seed-0 batch, which is why this function exists
    rather than a grammar constraint:

      * Existence holds almost everywhere. 18 of 25 hulls have a root at EVERY
        chine station; the batch mean obstruction is 2.1%. **The topside is not
        intrinsically undevelopable**, so constraining the hull form -- the
        obvious reading of Gate 6D -- would have been fixing the wrong thing.
      * What fails is MONOTONICITY. Following the root branch by nearest-root
        continuation, a single non-crossing ruling family covers only 49-85% of
        the panel (hull 14 / hull 8 / hull 4). Crossing rulings are not a
        buildable strake regardless of how developable each ruling is.

    So the obstruction is not "this surface cannot be flattened", it is "it
    cannot be flattened as ONE piece". Each break is a STRAKE SEAM, which is
    what a boatbuilder does anyway. Measured seam counts on the batch: median
    2, 23/25 need <= 2, all 25 need <= 3.

    A seam is declared only where the branch genuinely fails -- no root at all,
    a jump over `jump_tol` of LWL, or a reversal of direction (which is where
    rulings would cross). Breaks closer than 3% LWL are ONE seam: a greedy
    "smallest root above the current one" tracker reported six seams at
    x/L 0.31..0.35 on hull 4, which was the tracker restarting and re-breaking,
    not six places to cut. Nearest-root continuation reports the one real seam.
    """
    x = np.asarray(hull.x, dtype=float)
    L = float(x[-1])
    h = 1e-5 * L
    xa = np.linspace(0.03 * L, 0.97 * L, n_a)
    # inset: edge_curves evaluates (x/xm)**p_stern, which is NaN for x < 0, and
    # np.sign(nan) fabricates sign changes -- i.e. roots that are not there.
    xb = np.linspace(0.02 * L, 0.98 * L, n_b)
    A = hull.edge_curves(xa)[edge_a]
    dA = (hull.edge_curves(xa + h)[edge_a]
          - hull.edge_curves(xa - h)[edge_a]) / (2.0 * h)
    B = hull.edge_curves(xb)[edge_b]
    dB = (hull.edge_curves(xb + h)[edge_b]
          - hull.edge_curves(xb - h)[edge_b]) / (2.0 * h)
    r = B[None, :, :] - A[:, None, :]
    d = np.einsum("ak,abk->ab", dA, np.cross(dB[None, :, :], r))
    d /= (np.linalg.norm(dA, axis=1)[:, None]
          * np.linalg.norm(dB, axis=1)[None, :]
          * np.linalg.norm(r, axis=2) + 1e-300)
    if not np.all(np.isfinite(d)):
        raise ValueError("non-finite planarity determinant — the edge curves "
                         "were sampled outside their valid range")

    roots: list[np.ndarray] = []
    for i in range(n_a):
        k = np.flatnonzero(np.diff(np.sign(d[i])) != 0)
        roots.append(np.array(
            [xb[j] + (xb[j + 1] - xb[j]) * abs(d[i, j])
             / (abs(d[i, j]) + abs(d[i, j + 1]) + 1e-300) for j in k]))

    tol = jump_tol * L
    breaks: list[float] = []
    prev: float | None = None
    prev_step = 0.0
    for i in range(n_a):
        if len(roots[i]) == 0:
            if prev is not None:
                breaks.append(float(xa[i]))
            prev = None
            continue
        if prev is None:
            prev = float(roots[i][np.argmin(np.abs(roots[i] - xa[i]))])
            prev_step = 0.0
            continue
        cand = float(roots[i][np.argmin(np.abs(roots[i] - prev))])
        step = cand - prev
        reversed_ = (prev_step != 0.0 and np.sign(step) != np.sign(prev_step)
                     and abs(step) > 0.005 * L)
        if abs(step) > tol or reversed_:
            breaks.append(float(xa[i]))
            prev = float(roots[i][np.argmin(np.abs(roots[i] - xa[i]))])
            prev_step = 0.0
        else:
            prev, prev_step = cand, step

    merged: list[float] = []
    for b in breaks:
        if not merged or b - merged[-1] > 0.03 * L:
            merged.append(b)
    return merged


def strake_pairings(hull: Hull, edge_a: int, edge_b: int,
                    n_b: int = 1500) -> list[tuple[np.ndarray, np.ndarray]]:
    """(par_a, par_b) per STRAKE — the panel cut at its ruling-branch seams.

    The root continuation in `developable_seams` already IS the pairing: at
    each station u the developable ruling lands at the root s of
    det[A'(u), B'(s), B(s) - A(u)], so following that root gives v(u) directly
    and no Levenberg-Marquardt solve is needed. `developable_pairing` fits one
    pairing over the WHOLE panel and is refused by `hull_panels` unless it
    comes out monotone; measured on the seed-0 batch a single monotone family
    covers only 49-85% of the topside, so on most hulls that refusal is the
    only correct answer and the panel falls back to constant-x.

    Cutting at the seams removes the obstruction instead of failing on it.
    Each strake carries its own monotone pairing, and a strake seam is a real
    thing a builder makes: measured seam counts are median 2, 23/25 hulls need
    <= 2, all 25 need <= 3.

    Segments shorter than 8% LWL are absorbed into their neighbour — a 200 mm
    strake on a 12 m hull is a cut line, not a plank, and splitting there would
    trade a refold error for a fabrication one.

    MEASURED 2026-08-12 — THIS DOES NOT WORK YET, AND IT IS RECORDED RATHER
    THAN SHIPPED. Two-sided Hausdorff between the hull's panel surface and the
    UNION of its strakes (charging one strake for what another covers is not a
    measure of the panelisation), against the 5 mm bar:

        hull  panel      constant-x   developable   strakes
           4  bottom          36.2          9.1       112.6
           4  topside        933.6        706.0       709.1
           8  bottom         101.5         54.3       792.1
           8  topside        176.1         71.0       868.6
          14  bottom         727.4        335.1       573.4
          14  topside        407.2        147.4       409.1

    Worse than the fitted pairing in five of six, and it clears the bar in
    none. The diagnosis is in `_branch_pairing`'s monotone clamp: it binds at
    14/28, 19/40 and 11/36 stations INSIDE a segment, so at up to half the
    stations the pairing is not a root of the planarity condition at all — it
    is being forced upward to stay monotone, which destroys planarity exactly
    where the panel needed it.

    So the seams are in the wrong places. The existence result and the seam
    COUNT stand (they are measured on a 200-point auxiliary grid and reproduce
    exactly), but a seam must be placed where the pairing breaks at the 41
    stations the panel is actually developed at, not where the branch breaks on
    the auxiliary grid. Deriving the cut from the same resolution the panel
    uses is the next attempt; until then `hull_panels` keeps "developable" as
    its default and this mode exists to be measured, not adopted.
    """
    x = np.asarray(hull.x, dtype=float)
    L = float(x[-1])
    seams = developable_seams(hull, edge_a, edge_b, n_b=n_b)
    cuts = [0.0] + [s for s in seams] + [L]
    # drop segments too short to be a plank
    keep = [cuts[0]]
    for c in cuts[1:-1]:
        if c - keep[-1] >= 0.08 * L and (L - c) >= 0.08 * L:
            keep.append(c)
    keep.append(L)

    out: list[tuple[np.ndarray, np.ndarray]] = []
    for lo, hi in zip(keep[:-1], keep[1:]):
        xs = x[(x >= lo - 1e-9) & (x <= hi + 1e-9)]
        if len(xs) < 3:
            continue
        v = _branch_pairing(hull, edge_a, edge_b, xs, n_b)
        out.append((xs, v))
    return out


def _branch_pairing(hull: Hull, edge_a: int, edge_b: int,
                    xs: np.ndarray, n_b: int) -> np.ndarray:
    """Follow the planarity root across `xs`, clamped monotone and to the ends.

    Falls back to the station's own x wherever the branch has no root, so the
    result is always a usable sampling parameter — a strake with a hole in its
    pairing is not a panel."""
    L = float(hull.x[-1])
    h = 1e-5 * L
    xb = np.linspace(0.02 * L, 0.98 * L, n_b)
    # one-sided at the ends: edge_curves evaluates (x/xm)**p_stern, which is
    # NaN for x < 0, and a NaN derivative fabricates roots downstream.
    xp = np.minimum(xs + h, L - 1e-9)
    xm_ = np.maximum(xs - h, 1e-9)
    A = hull.edge_curves(xs)[edge_a]
    dA = ((hull.edge_curves(xp)[edge_a] - hull.edge_curves(xm_)[edge_a])
          / (xp - xm_)[:, None])
    B = hull.edge_curves(xb)[edge_b]
    dB = (hull.edge_curves(xb + h)[edge_b]
          - hull.edge_curves(xb - h)[edge_b]) / (2.0 * h)
    r = B[None, :, :] - A[:, None, :]
    d = np.einsum("ak,abk->ab", dA, np.cross(dB[None, :, :], r))
    d /= (np.linalg.norm(dA, axis=1)[:, None]
          * np.linalg.norm(dB, axis=1)[None, :]
          * np.linalg.norm(r, axis=2) + 1e-300)
    v = np.empty(len(xs))
    prev = float(xs[0])
    for i in range(len(xs)):
        k = np.flatnonzero(np.diff(np.sign(d[i])) != 0)
        if len(k) == 0:
            v[i] = prev = max(prev, float(xs[i]))
            continue
        cand = np.array([xb[j] + (xb[j + 1] - xb[j]) * abs(d[i, j])
                         / (abs(d[i, j]) + abs(d[i, j + 1]) + 1e-300)
                         for j in k])
        pick = cand[np.argmin(np.abs(cand - (prev if i else xs[0])))]
        v[i] = prev = max(float(pick), prev + 1e-9)
    # the strake must span its own segment, not a convenient part of it
    v[0], v[-1] = float(xs[0]), float(xs[-1])
    return np.maximum.accumulate(v)


def hull_panels(hull: Hull, rulings: str = "developable") -> list[FlatPanel]:
    """The two shell panels, developed.

    `rulings="constant-x"` is the pre-2026-08-11 behaviour, kept executable so
    the improvement has a control to be measured against rather than a
    remembered number (defect class 3: a guard that was never made to fire).

    `rulings="strakes"` cuts each panel at its ruling-branch seams and develops
    each strake on its own monotone pairing — see `developable_seams` for why a
    single family cannot span the panel.
    """
    if rulings not in ("developable", "constant-x", "strakes"):
        raise ValueError(f"unknown ruling family {rulings!r}")
    # A ROUND BILGE IS REFUSED HERE, NOT APPROXIMATED (plate P2).
    #
    # `_PANEL_EDGES` and every caller below assume the shell is exactly TWO
    # panels meeting at a chine, which was true of every hull the old kernel
    # could draw. With `roundness > 0` the bilge is a fillet: there is no
    # crease to cut on, and the filleted strip is doubly curved and therefore
    # NOT developable from flat sheet — that is a fact about sheet material,
    # not a limitation of this unroller. Developing it anyway would return a
    # `refold_deviation_mm` computed against the chine curve of a hull that has
    # no chine, which is Gate 6D measuring the wrong surface and reporting a
    # number. Gate 6D and Gate F keep operating on hard-chine hulls, where the
    # kernel reproduces the old geometry exactly.
    rho = float(grammar.named(hull.params)["roundness"])
    if rho > 0.0:
        raise ValueError(
            f"unroll: roundness {rho:.3f} — a radiused bilge is not a "
            f"two-panel developable shell. Set roundness = 0 for a "
            f"sheet-built hull, or take this hull to a mould, not a cutter.")
    if rulings == "strakes":
        out: list[FlatPanel] = []
        for name, ia, ib in (("bottom-stbd", 0, 1), ("topside-stbd", 1, 2)):
            segs = strake_pairings(hull, ia, ib)
            for k, (xs, v) in enumerate(segs, 1):
                nm = name if len(segs) == 1 else f"{name}-s{k}"
                out.append(replace(
                    develop(hull.edge_curves(xs)[ia],
                            hull.edge_curves(v)[ib], nm),
                    rulings="strakes", par_a=xs.copy(), par_b=v.copy()))
        return out
    x = np.asarray(hull.x, dtype=float)
    out: list[FlatPanel] = []
    for name, ia, ib in (("bottom-stbd", 0, 1), ("topside-stbd", 1, 2)):
        A = hull.edge_curves(x)[ia]
        base = replace(develop(A, hull.edge_curves(x)[ib], name),
                       rulings="constant-x", par_a=x.copy(), par_b=x.copy())
        if rulings == "constant-x":
            out.append(base)
            continue
        v = developable_pairing(hull, ia, ib)
        fit = replace(develop(A, hull.edge_curves(v)[ib], name),
                      rulings="developable", par_a=x.copy(),
                      par_b=np.asarray(v).copy())
        # REFUSE A FIT THAT IS NOT AN IMPROVEMENT, ON THE METRIC THAT DECIDES.
        # An earlier version of this guard compared max |quad_warp| and it was
        # NOT sufficient: the planarity condition has several roots, and on a
        # rejection-sampled grammar hull at 161 stations a solve that walked
        # onto another branch returned a lower warp and a topside panel
        # **1938 mm** off the hull, against 612 mm for the constant-x family it
        # replaced. A guard that watches a proxy passes the case the proxy
        # cannot see. This one watches `refold_surface_deviation_mm`, which is
        # the gate's own metric, and `panel.rulings` records which family the
        # comparison chose so the answer is never implied.
        if (np.all(np.diff(v) > 0)
                and refold_surface_deviation_mm(hull, fit, **_GUARD_SAMPLING)
                < refold_surface_deviation_mm(hull, base, **_GUARD_SAMPLING)):
            out.append(fit)
        else:
            out.append(base)
    return out


# ---------------- refold: 2-D back to 3-D ----------------

def _trilaterate(p1, p2, p3, r1, r2, r3):
    """The two points at distances r1,r2,r3 from p1,p2,p3 (mirror pair)."""
    ex = p2 - p1
    d = float(np.linalg.norm(ex))
    ex = ex / d
    t = p3 - p1
    i = float(ex @ t)
    ey = t - i * ex
    ny = float(np.linalg.norm(ey))
    if ny < 1e-12:                       # collinear datum: no reconstruction
        raise ValueError("refold: degenerate trilateration triangle")
    ey = ey / ny
    ez = np.cross(ex, ey)
    j = float(ey @ t)
    x = (r1**2 - r2**2 + d**2) / (2.0 * d)
    y = (r1**2 - r3**2 + i**2 + j**2 - 2.0 * i * x) / (2.0 * j)
    base = p1 + x * ex + y * ey
    off = np.sqrt(max(r1**2 - x**2 - y**2, 0.0)) * ez
    return base + off, base - off


def refold(panel: FlatPanel) -> np.ndarray:
    """Roll the flat pattern back up: returns the refolded edge B, (n, 3).

    GATE 6 CLAIMS "exported panels re-fold to the hull within tolerance" AND
    NOTHING TESTED IT. tests/test_stageF.py only ever went 3-D -> 2-D, so the
    clause was prose.

    WHAT THIS CONSUMES, so it cannot be accused of reading the answer: the jig
    datum `src_a` (the keel or chine line, which is what a strongback IS), the
    panel's start point `src_b[0]` (the transom corner), and ONE BIT for which
    way the panel wraps. Everything else — every edge length, every ruling
    length, and the cross diagonal — is read out of the FLAT PATTERN. So each
    station's B is trilaterated from three distances the shop can measure on
    the cut sheet, and the deviation that accumulates is exactly the
    development error the flat pattern carries.

    Branch selection is by smoothness (the candidate nearer the linear
    extrapolation of the previous two points), not by dihedral sign. MEASURED:
    the sign flips 63 times over the hull bottom at n=161 because that panel is
    flat to 1e-14 over its run, so the sign is numerical noise there and a
    sign-continuity rule blows up to 1994 mm on the topside.

    THE MEASURED ANSWER IS RED — see `refold_deviation_mm`.
    """
    if panel.src_a is None or panel.src_b is None:
        raise ValueError(
            "refold needs the 3-D edges this panel was developed from: build "
            "the panel with develop(), do not construct FlatPanel by hand")
    A3 = np.asarray(panel.src_a, dtype=float)
    a2, b2 = panel.edge_a, panel.edge_b
    n = len(a2)
    B = np.zeros((n, 3))
    B[0] = panel.src_b[0]
    for i in range(n - 1):
        r1 = float(np.linalg.norm(b2[i + 1] - b2[i]))       # edge B
        r2 = float(np.linalg.norm(b2[i + 1] - a2[i + 1]))   # ruling
        r3 = float(np.linalg.norm(b2[i + 1] - a2[i]))       # cross diagonal
        c_p, c_m = _trilaterate(B[i], A3[i + 1], A3[i], r1, r2, r3)
        if i == 0:
            # the one bit: which side of the jig the panel wraps to
            ref = np.asarray(panel.src_b[1], dtype=float)
        else:
            ref = 2.0 * B[i] - B[i - 1]
        B[i + 1] = (c_p if np.linalg.norm(c_p - ref)
                    <= np.linalg.norm(c_m - ref) else c_m)
    return B


def refold_deviation_mm(panel: FlatPanel) -> np.ndarray:
    """Per-station |refold - hull| in MILLIMETRES.

    MEASURED on the reference hull (`tests/test_phase0.mid_params`, 41
    stations), max over the panel:

        panel                          n=41      n=161
        true cylinder               0.0000 mm    --      exact, as it must be
        bottom-stbd,  constant-x     141.0 mm   (see below) x=9.0 m, forefoot warp
        topside-stbd, constant-x     225.7 mm   206.1 mm  at the stem
        bottom-stbd,  developable     29.2 mm    64.2 mm
        topside-stbd, developable     66.2 mm   102.9 mm

    143.8 mm stood here until 2026-08-12 and IS NOT A COMPUTABLE NUMBER. `_trilaterate` takes sqrt(max(r1^2 - x^2 - y^2, 0)) and that radicand is zero exactly when the quad is PLANAR, which the aft bottom panel is to machine precision (this file already records it refolding to 0.008 mm and flipping sign 63 times). The sphere intersection is tangential, so d(sqrt a)/da amplifies ~650x per step and `refold` feeds each reconstructed point into the next. MEASURED, 6 one-ULP perturbations of the 3-D datum edges, max over the panel:
        n= 41  140.996 .. 140.997   spread 1.000x   computable
        n=161   24.537 .. 143.799   spread 5.861x   NOT computable
    The same computation in `decimal` at 20..2000 digits returns one of the two values and flips non-monotonically: ILL-POSED, not precision-limited. ONLY THIS CELL is affected -- constant-x topside at 161 (206.074) and BOTH developable panels at 41 and 161 all measure spread 1.000x, so the conclusion the table is here to support survives on the developable family, which is the one the Gate 6D watermark uses.

    The constant-x figures do not shrink with refinement, so they are geometry
    and not discretisation. The aft half of the constant-x BOTTOM panel refolds
    to 0.008 mm — that part of the hull really is developable — and every
    millimetre of its error is in the bow, where `ruling_twist` peaks at 0.288.

    THIS METRIC IS NOT SUFFICIENT ON ITS OWN and must not be quoted alone.
    It watches the far EDGE, so it cannot see a fitted panel whose edge lands
    on the chine while the sheet in between leaves the hull: with the ruling
    step uncapped the bottom panel reads **0.07 mm here and 97.5 mm** under
    `refold_surface_deviation_mm`. Gate 6D's watermark is the two-sided one.
    """
    return np.linalg.norm(refold(panel) - np.asarray(panel.src_b, dtype=float),
                          axis=1) * 1000.0


_PANEL_EDGES = {"bottom-stbd": (0, 1), "topside-stbd": (1, 2)}


def _point_tri_dist(P: np.ndarray, T: np.ndarray) -> np.ndarray:
    """min distance from each point in P (m,3) to the triangle set T (k,3,3)."""
    out = np.full(len(P), np.inf)
    a, b, c = T[:, 0], T[:, 1], T[:, 2]
    ab, ac = b - a, c - a
    d00 = np.einsum("ij,ij->i", ab, ab)
    d01 = np.einsum("ij,ij->i", ab, ac)
    d11 = np.einsum("ij,ij->i", ac, ac)
    den = np.maximum(d00 * d11 - d01 * d01, 1e-300)
    edges = ((a, ab), (a, ac), (b, c - b))
    for k in range(0, len(P), 512):
        q = P[k:k + 512]
        ap = q[:, None, :] - a[None]
        d20 = np.einsum("kij,ij->ki", ap, ab)
        d21 = np.einsum("kij,ij->ki", ap, ac)
        u = (d11 * d20 - d01 * d21) / den
        v = (d00 * d21 - d01 * d20) / den
        inside = (u >= 0) & (v >= 0) & (u + v <= 1)
        proj = a[None] + u[..., None] * ab[None] + v[..., None] * ac[None]
        best = np.where(inside, np.linalg.norm(q[:, None, :] - proj, axis=2),
                        np.inf)
        for p0, e in edges:                    # clamp to each edge
            ee = np.maximum(np.einsum("ij,ij->i", e, e), 1e-300)
            t = np.clip(np.einsum("kij,ij->ki", q[:, None, :] - p0[None], e)
                        / ee, 0.0, 1.0)
            foot = p0[None] + t[..., None] * e[None]
            best = np.minimum(best, np.linalg.norm(q[:, None, :] - foot, axis=2))
        out[k:k + 512] = best.min(axis=1)
    return out


def refold_surface_deviation_mm(hull: Hull, panel: FlatPanel,
                                n_along: int = 20, n_across: int = 9,
                                n_hull: int = 1201) -> float:
    """Two-sided (Hausdorff) max distance [mm] between the REFOLDED PANEL
    SURFACE and the hull's own moulded surface. The edge-only refold cannot see
    this, and it must.

    BOTH DIRECTIONS, because one of them alone is not a distance between
    surfaces. MEASURED when only panel->hull was computed: the developable fit
    on the bottom panel scored 28.3 mm while its chine edge, a 41-point
    polyline over a pairing that takes 1.8 m steps near the stem, CUT THE
    CORNER OF THE CHINE BY 97 mm. Every point of that chord lies between the
    keel and the chine, i.e. ON the hull surface, so a panel->hull test scores
    a panel that covers less than the hull as perfect. Hull->panel is the
    direction that sees a missing strip.

    `refold_deviation_mm` asks whether the panel's far EDGE lands on the chine
    (or the sheer). Slanted rulings can answer that perfectly while the sheet
    between the edges bulges off the shape the ladder floated, because a
    slanted-ruled surface and the constant-x-ruled surface share their two
    boundary curves and differ in the interior. Reporting only the edge after
    changing the ruling family would move the error somewhere the gate's metric
    does not look — this repository's most expensive defect class.

    So this measures the whole strip: the surface ruled between the jig datum
    `src_a` and the REFOLDED far edge, against `Hull.section`'s constant-x
    ruled surface, which is what hydrostatics, the Michell integral and the
    CFD STL all integrate.

    MEASURED on the reference hull (`mid_params`, 41 stations):

        panel          rulings                    edge refold    this
        bottom-stbd    constant-x                    141.0 mm   140.2 mm
        bottom-stbd    developable, step uncapped      0.07 mm    97.5 mm
        bottom-stbd    developable (shipped)          29.2 mm    48.1 mm
        topside-stbd   constant-x                    225.7 mm   224.5 mm
        topside-stbd   developable (shipped)          66.2 mm    66.2 mm

    Row two is the whole reason this function exists.
    """
    if panel.src_a is None or panel.src_b is None:
        raise ValueError("needs the 3-D edges: build the panel with develop()")
    # strakes are named '<panel>-sN'; they share the panel's edge pair
    ia, ib = _PANEL_EDGES[_re.sub(r'-s\d+$', '', panel.name)]
    A = np.asarray(panel.src_a, dtype=float)
    B = refold(panel)
    t = np.linspace(0.0, 1.0, n_along + 1)[:, None]
    s = np.linspace(0.0, 1.0, n_across)[:, None, None]
    P = []
    for i in range(len(A) - 1):
        a = A[i] + t * (A[i + 1] - A[i])
        b = B[i] + t * (B[i + 1] - B[i])
        P.append((a[None] + s * (b - a)[None]).reshape(-1, 3))
    P = np.vstack(P)
    xs = np.linspace(float(hull.x[0]), float(hull.x[-1]), 4001)
    e = hull.edge_curves(xs)
    K, D = e[ia], e[ib] - e[ia]
    dd = np.einsum("ij,ij->i", D, D)
    worst = 0.0
    for k in range(0, len(P), 2000):
        q = P[k:k + 2000]
        w = q[:, None, :] - K[None]
        u = np.clip(np.einsum("kij,ij->ki", w, D)
                    / np.maximum(dd, 1e-300), 0.0, 1.0)
        diff = w - u[..., None] * D[None]
        worst = max(worst, float(np.sqrt((diff ** 2).sum(-1)).min(axis=1).max()))

    # ...and hull -> panel, against the panel's actual triangulation
    tris = np.concatenate([
        np.stack([A[:-1], B[:-1], A[1:]], axis=1),
        np.stack([A[1:], B[:-1], B[1:]], axis=1)])
    xs2 = np.linspace(float(hull.x[0]), float(hull.x[-1]), n_hull)
    e2 = hull.edge_curves(xs2)
    f = np.linspace(0.0, 1.0, n_across)[:, None, None]
    HP = (e2[ia][None] + f * (e2[ib] - e2[ia])[None]).reshape(-1, 3)
    worst = max(worst, float(_point_tri_dist(HP, tris).max()))
    return worst * 1000.0


@dataclass(frozen=True)
class RefoldConvergence:
    """`refold_surface_deviation_mm` measured over a family of station counts.

    Fields: `counts` the station counts, `worst_mm` the worst panel at each,
    `verdict` one of PASSES / REFINING / NON_DEVELOPABLE / REFUSED, `ratios`
    the successive reduction factors, and `order` the observed convergence
    order when the ratios agree well enough to name one (else None).
    """

    counts: tuple[int, ...]
    worst_mm: tuple[float, ...]
    ratios: tuple[float, ...]
    verdict: str
    order: float | None
    bar_mm: float

    @property
    def finest_mm(self) -> float:
        return self.worst_mm[-1]


# A refold family is DECREASING when each level improves on the last by more
# than this. Below it the two levels are the same number and the trend is
# noise, not convergence.
_REFOLD_CONVERGED_TOL = 1.02


#: The station family a refold verdict is measured over. NAMED because it is
#: consumed in two places and this codebase's recurring defect is a number
#: declared twice: `refold_convergence` scores the trend across all of it, and
#: `scripts/design_kit.py` drives its refinement search at `max(...)` — the
#: finest count — so the search optimises the converged deviation rather than
#: the 41-station polyline sagitta it would otherwise be rewarded for.
#: 41 is `geometry._LADDER_STATIONS`, the count the ladder already floats at;
#: the family doubles from there so successive ratios describe one power law.
REFOLD_COUNTS: tuple[int, ...] = (41, 81, 161)


def refold_convergence(params, counts: tuple[int, ...] = REFOLD_COUNTS,
                       bar_mm: float | None = None,
                       rulings: str = "developable") -> RefoldConvergence:
    """Is a refold shortfall DOUBLE CURVATURE, or is it the station count?

    MEASURED 2026-08-21, and it overturns the reading of Gate 6D's watermark.
    `refold_surface_deviation_mm` compares a panel built as straight chords
    between the hull's stations against the hull sampled at 4001 stations. At
    `geometry._LADDER_STATIONS` = 41 the panel is a 40-segment polyline, so
    part of every reported deviation is that polyline's sagitta — a property of
    the DISCRETISATION, not of the surface. The ladder's 41 stations were
    chosen for hydrostatics cost; nothing about manufacturing picked them.

    Same three hulls, LWL 10.5 m, roundness 0, only the station count varying:

        hull                  ndev_frac    n=41    n=81   n=161   n=321
        flare 0                0.000000    17.1     5.8     4.1     1.5
        deadrise warp 2->40    0.063811    40.6    20.5    10.3     5.3
        flare 25               0.275547   379.8   448.3   484.6   503.6

    Row one is a surface whose Gaussian curvature is 7.8e-14 — machine zero,
    developable — and it refolds 17.1 mm at the count Gate 6D reports. It is
    1.5 mm at 321. Row three INCREASES with refinement, which is the signature
    that cannot be discretisation: a finer sample of a doubly-curved surface
    finds MORE of the error it could not represent, never less.

    So the discriminator is the TREND, not the value, and this is the same
    discipline `cfd/post.gci` already applies to a mesh family: a single grid
    is a number, a family is a verdict. A shortfall that falls under refinement
    is measurement; one that rises is geometry, and only the second is a reason
    to change the hull.

    This answers the question `hull_panels`' own history left open — whether the
    grammar admits a sub-bar hull at all. It does: flare 0, forefoot 0, no
    deadrise warp, roundness 0 reaches 1.5 mm against a 5 mm bar.

    COST is why this is a gate instrument and not a slider one: ~9.6 s for
    (41, 81, 161) on one hull, since `hull_panels` is ~1.4 s at 41 stations and
    scales with the count. Do not call it from `evaluate`.

    `params` is a grammar parameter vector or the dict `grammar.named` returns.
    A hull the unroller refuses at every level (a filleted bilge, say) returns
    verdict REFUSED rather than a fabricated number.
    """
    from .limits import REFOLD_BAR_MM
    bar = REFOLD_BAR_MM if bar_mm is None else float(bar_mm)
    v = grammar.vector(params) if isinstance(params, dict) else np.asarray(
        params, dtype=float)
    counts = tuple(int(c) for c in counts)
    if len(counts) < 2 or any(b <= a for a, b in zip(counts, counts[1:])):
        raise ValueError("counts must be at least two, strictly increasing")

    worst: list[float] = []
    for n in counts:
        hull = Hull(v, n_stations=n)
        try:
            panels = hull_panels(hull, rulings=rulings)
        except ValueError:
            return RefoldConvergence(counts, (), (), "REFUSED", None, bar)
        worst.append(max(refold_surface_deviation_mm(hull, p) for p in panels))

    ratios = tuple(worst[i] / worst[i + 1] if worst[i + 1] > 0 else float("inf")
                   for i in range(len(worst) - 1))

    # A level that does not improve on its predecessor is the non-developable
    # signature. Checked pairwise rather than end-to-end so a family that turns
    # over in the middle is caught rather than averaged away.
    if any(r < _REFOLD_CONVERGED_TOL for r in ratios):
        verdict = "NON_DEVELOPABLE"
    elif worst[-1] <= bar:
        verdict = "PASSES"
    else:
        verdict = "REFINING"

    # Observed order, named ONLY when the successive ratios agree. Two ratios
    # that disagree by more than 2x describe no single power law, and printing
    # an order for them would be the same defect as quoting a GCI off a family
    # whose refinement ratio was never measured.
    order = None
    if verdict != "NON_DEVELOPABLE" and len(ratios) >= 2:
        if max(ratios) / max(min(ratios), 1e-12) <= 2.0:
            h = counts[-1] / counts[-2]
            if h > 1.0 and ratios[-1] > 0:
                order = float(np.log(ratios[-1]) / np.log(h))
    return RefoldConvergence(counts, tuple(worst), ratios, verdict, order, bar)


def rulings_that_cross(panel: FlatPanel) -> int:
    """How many neighbouring ruling pairs intersect INSIDE the panel.

    A slanted-ruling fit is only a panel if its rulings sweep the strip once.
    The developability condition has several roots and a solve that hops
    between them can return a strictly monotone pairing whose rulings still
    cross, which is a self-overlapping sheet, not a cut part.
    """
    A = np.asarray(panel.src_a, dtype=float)
    B = np.asarray(panel.src_b, dtype=float)
    bad = 0
    for i in range(len(A) - 1):
        p, r = A[i], B[i] - A[i]
        q, s = A[i + 1], B[i + 1] - A[i + 1]
        M = np.array([[r @ r, -(r @ s)], [-(r @ s), s @ s]])
        if abs(np.linalg.det(M)) < 1e-14:
            continue
        ab = np.linalg.solve(M, np.array([(q - p) @ r, -((q - p) @ s)]))
        gap = float(np.linalg.norm((p + ab[0] * r) - (q + ab[1] * s)))
        if gap < 1e-6 and 0.02 < ab[0] < 0.98 and 0.02 < ab[1] < 0.98:
            bad += 1
    return bad


# ---------------- nesting ----------------

@dataclass(frozen=True)
class Part:
    """One piece to be cut from sheet stock."""

    name: str
    source_panel: str
    thickness_m: float
    material: str
    outline: np.ndarray               # (k, 2) local coords [m]
    qty: int = 1
    scarph_m2: float = 0.0            # extra material for scarph overlaps
    note: str = ""
    # FOOTPRINT the packer must reserve: the piece's min-area box PLUS the
    # scarph flange on each cut edge, per axis. It is stored rather than
    # re-derived because the splitter and the packer MUST use the same number.
    # MEASURED when they did not: `nest` inflated both axes by
    # scarph_m2/(w+h), which on a 2.375 x 0.023 m sliver added 119 mm to the
    # LONG axis and pushed a piece the splitter had cleared at 2.435 m out to
    # 2.494 m — over the 2.44 m sheet. 7 of 40 sampled hulls then raised
    # "no feasible nesting layout", which killed the engineer agent and the
    # PLM network delivered 0 of 3 designs.
    foot_w: float = 0.0
    foot_h: float = 0.0

    def area_m2(self) -> float:
        x, y = self.outline[:, 0], self.outline[:, 1]
        return float(abs(np.dot(x, np.roll(y, -1))
                         - np.dot(y, np.roll(x, -1))) / 2.0)

    def footprint(self) -> tuple[float, float]:
        if self.foot_w > 0.0 and self.foot_h > 0.0:
            return self.foot_w, self.foot_h
        w, h, _ = min_area_rect(self.outline)
        return w, h


@dataclass(frozen=True)
class Placement:
    part: str
    source_panel: str
    sheet: int
    x: float
    y: float
    w: float
    h: float
    rotated: bool
    polygon: np.ndarray               # (k, 2) placed in sheet coords [m]


@dataclass(frozen=True)
class Nesting:
    sheet_w: float
    sheet_l: float
    placements: tuple[Placement, ...]
    sheet_thickness_mm: tuple[float, ...]   # per sheet index
    parts: tuple[Part, ...]

    @property
    def sheets(self) -> int:
        return len(self.sheet_thickness_mm)

    def utilisation(self) -> float:
        used = sum(p.w * p.h for p in self.placements)
        return used / max(self.sheets * self.sheet_w * self.sheet_l, 1e-12)

    def on_sheet(self, i: int) -> list[Placement]:
        return [p for p in self.placements if p.sheet == i]


def _convex_hull(pts: np.ndarray) -> np.ndarray:
    """Monotone chain. Deterministic, dependency-free."""
    p = np.unique(np.round(pts, 12), axis=0)
    p = p[np.lexsort((p[:, 1], p[:, 0]))]
    if len(p) < 3:
        return p

    def half(seq):
        out: list = []
        for q in seq:
            while len(out) >= 2:
                a, b = out[-2], out[-1]
                if (b[0] - a[0]) * (q[1] - a[1]) - (b[1] - a[1]) * (q[0] - a[0]) <= 0:
                    out.pop()
                else:
                    break
            out.append(q)
        return out

    return np.array(half(p)[:-1] + half(p[::-1])[:-1])


def min_area_rect(pts: np.ndarray) -> tuple[float, float, float]:
    """Minimum-area oriented bounding box: (width, height, angle [rad]).

    Rotating calipers over the convex hull. A panel piece is a curved sliver;
    its AXIS-ALIGNED box overstates it badly (the topside piece measures
    1.32 x 0.47 m axis-aligned and 1.31 x 0.40 m oriented), and overstating the
    box is how a nest reports sheets it does not need.
    """
    h = _convex_hull(np.asarray(pts, dtype=float))
    if len(h) < 3:
        w = float(np.ptp(pts[:, 0]))
        d = float(np.ptp(pts[:, 1]))
        return max(w, 1e-9), max(d, 1e-9), 0.0
    best = (np.inf, 0.0, 0.0, 0.0)
    for i in range(len(h)):
        e = h[(i + 1) % len(h)] - h[i]
        n = float(np.linalg.norm(e))
        if n < 1e-12:
            continue
        th = float(np.arctan2(e[1], e[0]))
        c, s = np.cos(-th), np.sin(-th)
        R = np.array([[c, -s], [s, c]])
        q = h @ R.T
        w, d = float(np.ptp(q[:, 0])), float(np.ptp(q[:, 1]))
        if w * d < best[0]:
            best = (w * d, w, d, th)
    return best[1], best[2], best[3]


def _oriented(pts: np.ndarray) -> tuple[np.ndarray, float, float]:
    """Rotate `pts` onto its min-area box, origin at the box corner."""
    w, h, th = min_area_rect(pts)
    c, s = np.cos(-th), np.sin(-th)
    q = np.asarray(pts, dtype=float) @ np.array([[c, -s], [s, c]]).T
    q = q - q.min(axis=0)
    return q, w, h


class _MaxRects:
    """MaxRects bin packing, best-short-side-fit, with 90-degree rotation."""

    def __init__(self, w: float, h: float) -> None:
        self.w, self.h = w, h
        self.free = [(0.0, 0.0, w, h)]

    def insert(self, pw: float, ph: float):
        best = None
        for (fx, fy, fw, fh) in self.free:
            for rot, aw, ah in ((False, pw, ph), (True, ph, pw)):
                if aw <= fw + 1e-9 and ah <= fh + 1e-9:
                    key = (min(fw - aw, fh - ah), max(fw - aw, fh - ah))
                    if best is None or key < best[0]:
                        best = (key, fx, fy, aw, ah, rot)
        if best is None:
            return None
        _, x, y, aw, ah, rot = best
        self._occupy(x, y, aw, ah)
        return x, y, aw, ah, rot

    def _occupy(self, x, y, w, h) -> None:
        out: list = []
        for f in self.free:
            out.extend(self._split(f, (x, y, w, h)))
        pruned: list = []
        for i, a in enumerate(out):
            if not any(i != j and self._contains(b, a) for j, b in enumerate(out)):
                pruned.append(a)
        self.free = pruned

    @staticmethod
    def _contains(outer, inner) -> bool:
        ax, ay, aw, ah = outer
        bx, by, bw, bh = inner
        return (ax <= bx + 1e-9 and ay <= by + 1e-9
                and ax + aw >= bx + bw - 1e-9 and ay + ah >= by + bh - 1e-9)

    @staticmethod
    def _split(free, used):
        fx, fy, fw, fh = free
        ux, uy, uw, uh = used
        if (ux >= fx + fw - 1e-9 or ux + uw <= fx + 1e-9
                or uy >= fy + fh - 1e-9 or uy + uh <= fy + 1e-9):
            return [free]
        out = []
        if uy > fy + 1e-9:
            out.append((fx, fy, fw, uy - fy))
        if uy + uh < fy + fh - 1e-9:
            out.append((fx, uy + uh, fw, fy + fh - (uy + uh)))
        if ux > fx + 1e-9:
            out.append((fx, fy, ux - fx, fh))
        if ux + uw < fx + fw - 1e-9:
            out.append((ux + uw, fy, fx + fw - (ux + uw), fh))
        return out


# `_interp_edge(panel, t)` WAS HERE AND NOTHING CALLED IT — private, zero
# references. It lerped between a panel's two developed edges, which is a
# ruling only if the panel is developable; on a warped panel it produces a
# line that is not on the surface. A private helper that is both unused and
# wrong for the general case is not a spare part.


def _footprint(poly: np.ndarray, allow: float, cuts_a: int, cuts_b: int,
               a_len: float) -> tuple[float, float, float]:
    """(foot_w, foot_h, extra_area) for a piece with scarph flanges.

    `cuts_a` is the number of cut edges across the axis whose extent is about
    `a_len`; `cuts_b` the other. The flange lands on the RIGHT axis, which is
    what the scarph_m2/(w+h) heuristic could not do.
    """
    w, h, _ = min_area_rect(poly)
    if abs(w - a_len) <= abs(h - a_len):
        fw, fh = w + cuts_a * allow, h + cuts_b * allow
    else:
        fw, fh = w + cuts_b * allow, h + cuts_a * allow
    return fw, fh, max(fw * fh - w * h, 0.0)


def _resample(edge: np.ndarray, k: int) -> np.ndarray:
    """Insert k-1 linearly interpolated points into every segment."""
    if k <= 1:
        return edge
    segs = [edge[i] + (edge[i + 1] - edge[i]) * np.linspace(0, 1, k + 1)[:-1, None]
            for i in range(len(edge) - 1)]
    return np.vstack(segs + [edge[-1:]])


def min_strakes(panel: FlatPanel, thickness_m: float,
                sheet: tuple[float, float] = (SHEET_W_M, SHEET_L_M),
                scarph_ratio: float = SCARPH_RATIO) -> int:
    """Fewest longitudinal strakes whose width still fits the sheet.

    Exposed rather than re-derived by callers, because `engineer.assess`
    searches strake counts ABOVE this one and had been recovering it by
    string-splitting a part name — `"bottom-stbd-s1p1".split("s")[1]` is
    `"tbd-"`, so the search always restarted from 1 and two of its five trials
    were the same layout.
    """
    sw = min(sheet)
    allow = scarph_ratio * thickness_m / 2.0
    w_max = float(np.linalg.norm(panel.edge_b - panel.edge_a, axis=1).max())
    k = 1
    while k <= 40:
        if w_max / k + (2 * allow if k > 1 else allow) <= sw:
            return k
        k += 1
    return k


def split_panel(panel: FlatPanel, thickness_m: float, material: str = "marine ply",
                sheet: tuple[float, float] = (SHEET_W_M, SHEET_L_M),
                scarph_ratio: float = SCARPH_RATIO,
                strakes: int | None = None) -> list[Part]:
    """Cut one developed panel into pieces that FIT A SHEET, at scarph joints.

    The two hull panels are 10.05 x 1.62 m and 10.54 x 1.44 m; the sheet is
    1.22 x 2.44 m. Before this, nothing split them and the DXF happily drew a
    part no shop could cut. Splitting is a grid in the panel's own
    parametrisation: `k_v` strakes across the rulings (longitudinal seams) and
    then chunks along the length (transverse scarphs). Each internal cut adds
    scarph_ratio * t / 2 of material to each of the two pieces meeting there —
    half each, because an 8:1 scarph's two tapers OVERLAP and one joint costs
    8t in total, not 16t.

    `strakes` overrides the strake count. The MINIMUM feasible count is the
    fewest seams, which is what a builder wants; it is not what the fewest
    SHEETS wants, because a 0.93 m strake leaves a 0.29 m ribbon of every
    1.22 m sheet unusable. `engineer.assess` searches a few counts and keeps
    the layout that opens fewest sheets — the number it then reports is the
    best layout found, not the first one tried.
    """
    sw, sl = min(sheet), max(sheet)
    allow = scarph_ratio * thickness_m / 2.0
    width = np.linalg.norm(panel.edge_b - panel.edge_a, axis=1)

    k_v = min_strakes(panel, thickness_m, sheet, scarph_ratio)
    if strakes is not None:
        if strakes < k_v:
            raise ValueError(
                f"{panel.name}: {strakes} strake(s) gives a "
                f"{float(width.max()) / strakes:.3f} m strake against a "
                f"{sw:.2f} m sheet — it would not fit")
        k_v = strakes

    # A chunk can never be shorter than ONE station interval, so on a long
    # hull a single quad can exceed the sheet on its own and no chunking can
    # help. Resample the flat pattern instead: cutting between stations is a
    # cut like any other. (18.94 m hull, 41 stations -> 0.47 m quads, fine;
    # the guard is for coarse polylines, where it is the difference between a
    # layout and a ValueError.)
    a2, b2 = panel.edge_a, panel.edge_b
    usable = sl - 2 * allow
    step = float(np.linalg.norm(np.diff(a2, axis=0), axis=1).max())
    if step > usable:
        k = int(np.ceil(step / usable))
        a2, b2 = _resample(a2, k), _resample(b2, k)
    n = len(a2)

    parts: list[Part] = []
    for j in range(k_v):
        lo = a2 + (j / k_v) * (b2 - a2)
        hi = a2 + ((j + 1) / k_v) * (b2 - a2)
        cuts_v = (1 if j > 0 else 0) + (1 if j < k_v - 1 else 0)
        i0 = 0
        chunk = 0
        while i0 < n - 1:
            i1, last_ok = i0 + 1, i0 + 1
            while i1 < n:
                poly = np.vstack([lo[i0:i1 + 1], hi[i0:i1 + 1][::-1]])
                cuts_u = (1 if i0 > 0 else 0) + (1 if i1 < n - 1 else 0)
                a_len = float(np.linalg.norm(np.diff(lo[i0:i1 + 1], axis=0),
                                             axis=1).sum())
                fw, fh, _ = _footprint(poly, allow, cuts_u, cuts_v, a_len)
                if max(fw, fh) <= sl + 1e-12 and min(fw, fh) <= sw + 1e-12:
                    last_ok = i1
                    i1 += 1
                else:
                    break
            poly = np.vstack([lo[i0:last_ok + 1], hi[i0:last_ok + 1][::-1]])
            chunk += 1
            cuts_u = (1 if i0 > 0 else 0) + (1 if last_ok < n - 1 else 0)
            a_len = float(np.linalg.norm(np.diff(lo[i0:last_ok + 1], axis=0),
                                         axis=1).sum())
            fw, fh, extra = _footprint(poly, allow, cuts_u, cuts_v, a_len)
            parts.append(Part(
                name=f"{panel.name}-s{j + 1}p{chunk}",
                source_panel=panel.name, thickness_m=thickness_m,
                material=material, outline=poly, scarph_m2=extra,
                foot_w=fw, foot_h=fh,
                note=(f"strake {j + 1}/{k_v}, station {i0}-{last_ok}, "
                      f"{cuts_u + cuts_v} scarph edge(s)")))
            i0 = last_ok
    return parts


def rect_parts(name: str, length: float, width: float, thickness_m: float,
               material: str = "marine ply", qty: int = 1,
               sheet: tuple[float, float] = (SHEET_W_M, SHEET_L_M),
               scarph_ratio: float = SCARPH_RATIO,
               note: str = "") -> list[Part]:
    """Tile a rectangular item (deck strip, bulkhead blank) into sheet pieces."""
    sw, sl = min(sheet), max(sheet)
    allow = scarph_ratio * thickness_m / 2.0
    nl = max(1, int(np.ceil(length / (sl - 2 * allow))))
    nw = max(1, int(np.ceil(width / (sw - 2 * allow))))
    dl, dw = length / nl, width / nw
    out: list[Part] = []
    for i in range(nl):
        for j in range(nw):
            cuts_l = (1 if i > 0 else 0) + (1 if i < nl - 1 else 0)
            cuts_w = (1 if j > 0 else 0) + (1 if j < nw - 1 else 0)
            poly = np.array([[0.0, 0.0], [dl, 0.0], [dl, dw], [0.0, dw]])
            fw, fh, extra = _footprint(poly, allow, cuts_l, cuts_w, dl)
            out.append(Part(
                name=f"{name}-p{i * nw + j + 1}" if nl * nw > 1 else name,
                source_panel=name, thickness_m=thickness_m, material=material,
                outline=poly, qty=qty, scarph_m2=extra, foot_w=fw, foot_h=fh,
                note=note or f"{nl}x{nw} tiling of {length:.2f}x{width:.2f} m"))
    return out


def nest(parts: list[Part], sheet: tuple[float, float] = (SHEET_W_M, SHEET_L_M)
         ) -> Nesting:
    """Pack parts onto sheets. Sheets are NOT mixed across thicknesses.

    You cannot cut a 21 mm bottom piece out of a 15 mm topside sheet, so the
    layout is a separate bin sequence per thickness and the total is the sum.
    Parts are placed largest-area-first (FFD), rotation allowed, MaxRects
    best-short-side-fit. `ply_sheets` is then a COUNT off this layout, which is
    what retires `engineer.WASTE_FACTOR = 1.30`: measured utilisation replaces
    a declared 77% packing efficiency.
    """
    sw, sl = min(sheet), max(sheet)
    instances: list[tuple[str, Part]] = []
    for p in parts:
        for k in range(max(1, p.qty)):
            instances.append((p.name if k == 0 else f"{p.name}_{k + 1}", p))
    order = sorted(instances, key=lambda ip: -ip[1].area_m2())

    placements: list[Placement] = []
    thickness_of: list[float] = []
    bins: dict[float, list[tuple[int, _MaxRects]]] = {}
    for label, part in order:
        t = round(part.thickness_m, 6)
        poly, rw, rh = _oriented(part.outline)
        # The scarph flange is real material and it lands on the CUT axis, not
        # spread over both — `Part.foot_*` is the single number the splitter
        # cleared and the packer must honour.
        fw, fh = part.footprint()
        if abs(fw - rw) + abs(fh - rh) > abs(fh - rw) + abs(fw - rh):
            fw, fh = fh, fw
        w, h = max(fw, rw), max(fh, rh)
        seq = bins.setdefault(t, [])
        spot = None
        for idx, b in seq:
            r = b.insert(w, h)
            if r is not None:
                spot = (idx, r)
                break
        if spot is None:
            b = _MaxRects(sw, sl)
            idx = len(thickness_of)
            thickness_of.append(part.thickness_m * 1e3)
            seq.append((idx, b))
            r = b.insert(w, h)
            if r is None:
                raise ValueError(
                    f"{part.name}: {w:.3f}x{h:.3f} m does not fit a "
                    f"{sw}x{sl} m sheet even empty — split_panel failed to "
                    f"split it, which is the bug this module exists to fix")
            spot = (idx, r)
        idx, (x, y, aw, ah, rot) = spot
        # A 90-degree ROTATION, not a coordinate swap. Swapping x and y is a
        # REFLECTION: it produces the mirror image of the part, which for a
        # hull strake is a different piece that will not fit the boat.
        pl = np.column_stack([rh - poly[:, 1], poly[:, 0]]) if rot else poly
        placements.append(Placement(
            part=label, source_panel=part.source_panel, sheet=idx,
            x=x, y=y, w=aw, h=ah, rotated=rot,
            polygon=pl + np.array([x, y])))
    return Nesting(sw, sl, tuple(placements), tuple(thickness_of), tuple(parts))


# ---------------- DXF R12 writer ----------------

def _polyline_dxf(pts: np.ndarray, layer: str) -> list[str]:
    out = ["0", "POLYLINE", "8", layer, "66", "1", "70", "1"]
    for x, y in pts:
        out += ["0", "VERTEX", "8", layer, "10", f"{x:.4f}", "20", f"{y:.4f}",
                "30", "0.0"]
    out += ["0", "SEQEND"]
    return out


def export_dxf(layout, path: str | Path, gap: float = 0.1,
               units_mm: bool = True, ev=None,
               thickness_m: float = PLY_THICKNESS_M,
               hull=None, allow_unverified: bool = False) -> Path:
    """Write the NEST — sheets, boundaries and placed parts — in MILLIMETRES.

    THE UNITS WERE UNDECLARED AND THE COORDINATES WERE METRES. The file had no
    HEADER section and therefore no $INSUNITS, while a bottom panel wrote as
    `10.0476 x 1.6160`. Overwhelming DXF/CNC convention is millimetres, so a
    shop importing this cut a **10 mm** part instead of a 10 m one — a scrapped
    sheet, or worse a part that looks plausible until it is offered up to the
    hull. $INSUNITS 4 is millimetres (6 would be metres); the values are scaled
    to match what the header declares, so the two can never disagree.

    AND IT WAS NOT A NEST. Panels were offset in y only: no rotation, no sheet
    boundaries, no packing, no splitting — and the two hull panels fit on no
    sheet at all. `layout` is now a `Nesting`; a bare list of `FlatPanel` is
    accepted and nested here, so no caller can go back to stacking by accident.
    Each sheet is drawn as its own SHEET-<n> boundary rectangle with its parts
    inside it, and every part is inside its sheet BY CONSTRUCTION.
    """
    from .export import refuse_unvalidated
    refuse_unvalidated(ev, 'DXF')

    # ---- GATE 6D AT THE CUT-FILE BOUNDARY (MEASURED 2026-08-21) ----------
    #
    # `refuse_unvalidated` asks whether the LADDER passed. The ladder does not
    # measure refold accuracy -- there is no such row in
    # `evaluate.CONSTRAINT_NAMES` -- so it cannot answer the only question a
    # shop cares about: will these panels close on the hull?
    #
    # MEASURED, on a hull the governed search delivered and the ladder passed
    # (ev.ok True): worst refold deviation 221.5 mm against a 5 mm bar, and
    # this function wrote a 67 kB DXF without complaint. Someone could cut it.
    # The topside would miss the chine by the better part of a quarter metre.
    #
    # Gate 6D is RED and ledgered at 124.1 mm; a red gate whose artefact ships
    # anyway is a gate that has been softened by omission. So the accuracy is
    # checked HERE, where the file is produced.
    from .limits import REFOLD_BAR_MM
    verdict = ("REFOLD NOT VERIFIED - hull not supplied to export_dxf; "
               "this is NOT a production cut file")
    if hull is not None:
        # A FAMILY, NOT ONE COUNT -- and the first version of this guard got
        # that wrong in a way that shipped a bad answer.
        #
        # `refold_surface_deviation_mm` builds the panel as straight chords
        # between the hull's stations, so at `_LADDER_STATIONS` = 41 part of
        # every reading is a 40-segment polyline's sagitta. MEASURED: a surface
        # with Gaussian curvature 7.8e-14 -- machine zero, exactly developable
        # -- reads 17.1 mm at n=41 and 1.5 mm at n=321. So a single count is
        # not a manufacturing verdict, and CLAUDE.md rule 4 names this exactly:
        # a defect measured at a configuration the product never runs.
        #
        # It cuts BOTH ways, which is why this guard changed. A refinement
        # search that optimised the n=41 number produced a hull reading
        # 4.92 / 5.22 / 8.71 mm at 41 / 81 / 161 -- under the bar at the coarse
        # count and RISING. It gamed the metric. Falling under refinement is
        # measurement; rising is geometry, and only the second is a boat you
        # cannot build. `refold_convergence` returns the trend.
        conv = refold_convergence(grammar.named(hull.params),
                                  bar_mm=REFOLD_BAR_MM)
        worst = float(conv.finest_mm)
        if conv.verdict != "PASSES" and not allow_unverified:
            raise ValueError(
                f"export_dxf: refold family {conv.counts} -> "
                f"{tuple(round(v, 2) for v in conv.worst_mm)} mm, verdict "
                f"{conv.verdict!r} against the {REFOLD_BAR_MM:.0f} mm bar "
                f"(limits.REFOLD_BAR_MM, BuildPlan 12.3 / Gate 6D). A verdict "
                f"is the TREND across station counts, never one count: a "
                f"shortfall that FALLS under refinement is the polyline's "
                f"sagitta, one that RISES is double curvature the sheet cannot "
                f"take. Cutting plywood to these produces panels that do not "
                f"close. REFUSED. Pass allow_unverified=True only for geometry "
                f"research, never to hand a shop a file.")
        verdict = (f"REFOLD VERIFIED {worst:.2f} mm at n="
                   f"{conv.counts[-1]} <= {REFOLD_BAR_MM:.0f} mm "
                   f"(family {tuple(round(v, 2) for v in conv.worst_mm)}, "
                   f"{conv.verdict})"
                   if conv.verdict == "PASSES" else
                   f"REFOLD {conv.verdict} - family "
                   f"{tuple(round(v, 2) for v in conv.worst_mm)} mm at "
                   f"{conv.counts} - OVERRIDDEN, NOT a production cut file")
    if isinstance(layout, (list, tuple)):
        parts: list[Part] = []
        for p in layout:
            parts += split_panel(p, thickness_m)
        layout = nest(parts)
    scale = 1000.0 if units_mm else 1.0
    # The standing travels WITH the artefact. A DXF that leaves this process
    # is read by a shop, not by this module's caller, so the one place the
    # verdict cannot be lost is inside the file.
    lines = ["999", verdict,
             "0", "SECTION", "2", "HEADER",
             "9", "$INSUNITS", "70", "4" if units_mm else "6",
             "9", "$MEASUREMENT", "70", "1",
             "0", "ENDSEC",
             "0", "SECTION", "2", "ENTITIES"]
    for i in range(layout.sheets):
        ox = i * (layout.sheet_w + gap)
        corner = np.array([[0.0, 0.0], [layout.sheet_w, 0.0],
                           [layout.sheet_w, layout.sheet_l],
                           [0.0, layout.sheet_l]]) + np.array([ox, 0.0])
        lines += _polyline_dxf(corner * scale, f"SHEET-{i + 1}")
        for pl in layout.on_sheet(i):
            lines += _polyline_dxf((pl.polygon + np.array([ox, 0.0])) * scale,
                                   pl.part)
    lines += ["0", "ENDSEC", "0", "EOF"]
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")
    return path


def parse_dxf_polylines(path: str | Path) -> dict[str, np.ndarray]:
    """Read back our own R12 subset (round-trip verification)."""
    toks = Path(path).read_text().split("\n")
    panels: dict[str, list] = {}
    i, cur, layer = 0, None, None
    while i < len(toks) - 1:
        code, val = toks[i].strip(), toks[i + 1].strip()
        if code == "0" and val == "POLYLINE":
            cur = []
        elif code == "8" and cur is not None and not cur:
            layer = val
            panels.setdefault(layer, [])
        elif code == "0" and val == "VERTEX":
            x = float(toks[i + 5].strip())
            y = float(toks[i + 7].strip())
            panels[layer].append((x, y))
        elif code == "0" and val == "SEQEND":
            cur = None
        i += 2
    return {k: np.array(v) for k, v in panels.items() if v}
