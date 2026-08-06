"""Developable-panel unrolling -> flat plate outlines -> NESTED DXF (original
plan Phase 5: 'structural DXF formats for manufacturing export').

Method: triangle development of the ruled surface between two 3-D edge
curves (keel-chine for the bottom panel, chine-sheer for the topside).
Isometric by construction along edges and one diagonal family; the residual
on the OTHER diagonal family is `dev_error_rel`.

THREE THINGS THIS MODULE NOW DOES THAT IT CLAIMED TO DO AND DID NOT
-------------------------------------------------------------------

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

DXF: minimal R12 ASCII (POLYLINE/VERTEX/SEQEND) — the most widely readable
dialect for CNC/nesting shops — in MILLIMETRES, declared via $INSUNITS 4.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

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

    @property
    def outline(self) -> np.ndarray:
        return np.vstack([self.edge_a, self.edge_b[::-1]])

    def perimeter(self) -> float:
        o = self.outline
        return float(np.linalg.norm(np.diff(np.vstack([o, o[:1]]), axis=0),
                                    axis=1).sum())

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


def hull_panels(hull: Hull) -> list[FlatPanel]:
    keel = np.stack([hull.x, np.zeros_like(hull.x), hull.z_keel], axis=1)
    chine = np.stack([hull.x, hull.y_chine, hull.z_chine], axis=1)
    sheer = np.stack([hull.x, hull.y_sheer, hull.z_sheer], axis=1)
    return [develop(keel, chine, "bottom-stbd"),
            develop(chine, sheer, "topside-stbd")]


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

        panel            n=41      n=161     where
        true cylinder   0.0000 mm  --        exact, as a developable must be
        bottom-stbd      141.0 mm  143.8 mm  x = 9.0 m, in the forefoot warp
        topside-stbd     225.7 mm  206.1 mm  at the stem

    It does not shrink with refinement, so it is geometry and not
    discretisation. The aft half of the BOTTOM panel refolds to 0.0 mm — that
    part of the hull really is developable — and every millimetre of the error
    is in the bow, where `ruling_twist` peaks at 0.291. Against the 5 mm bar in
    `tests/test_stageF.py` this is a FAIL by 28x and 45x, recorded rather than
    softened (honesty rule 6). The fix is slanted rulings, i.e. developable
    surface FITTING, not a wider tolerance.
    """
    return np.linalg.norm(refold(panel) - np.asarray(panel.src_b, dtype=float),
                          axis=1) * 1000.0


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


def _interp_edge(panel: FlatPanel, t: float) -> np.ndarray:
    return panel.edge_a + t * (panel.edge_b - panel.edge_a)


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
               thickness_m: float = PLY_THICKNESS_M) -> Path:
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
    if isinstance(layout, (list, tuple)):
        parts: list[Part] = []
        for p in layout:
            parts += split_panel(p, thickness_m)
        layout = nest(parts)
    scale = 1000.0 if units_mm else 1.0
    lines = ["0", "SECTION", "2", "HEADER",
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
