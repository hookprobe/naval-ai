"""Geometry kernel: parameters -> stations -> sections -> integral properties.

Sections are two straight segments (keel->chine, chine->sheer): every hull the
grammar emits is a pair of near-developable ruled panels per side, buildable
from sheet material. All quantities here are deterministic and fast (vectorised
numpy); this is the geometry substrate for L1 physics and the L2 mesh.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from . import grammar

RHO_WATER = 1000.0  # fresh water (Danube); pass 1025 for salt
G = 9.80665


@dataclass
class Hull:
    """Evaluated hull geometry at n stations."""

    params: np.ndarray
    n_stations: int = 41

    x: np.ndarray = field(init=False)          # station positions [m], 0=transom
    z_keel: np.ndarray = field(init=False)     # keel z per station
    y_chine: np.ndarray = field(init=False)    # chine half-breadth
    z_chine: np.ndarray = field(init=False)
    y_sheer: np.ndarray = field(init=False)
    z_sheer: np.ndarray = field(init=False)

    def __post_init__(self) -> None:
        p = grammar.named(self.params)
        L, B, T, D = p["LWL"], p["BWL"], p["T"], p["D"]
        xm = p["x_mb"] * L
        x = np.linspace(0.0, L, self.n_stations)
        self.x = x

        # keel profile: flat middle, quadratic forefoot rise (bow) and rocker (stern)
        zk = np.full_like(x, -T)
        bow_zone = x > 0.7 * L
        zk[bow_zone] += T * p["forefoot"] * ((x[bow_zone] - 0.7 * L) / (0.3 * L)) ** 2
        st_zone = x < 0.3 * L
        zk[st_zone] += T * p["rocker"] * ((0.3 * L - x[st_zone]) / (0.3 * L)) ** 2
        self.z_keel = zk

        # chine plan-form: fullness exponents fore/aft of max-beam station
        w = np.empty_like(x)
        fwd = x >= xm
        w[fwd] = 1.0 - ((x[fwd] - xm) / (L - xm)) ** p["p_bow"]
        aft = ~fwd
        w[aft] = p["r_transom"] + (1.0 - p["r_transom"]) * (x[aft] / xm) ** p["p_stern"]
        w = np.clip(w, 0.0, 1.0)
        self.y_chine = 0.5 * B * w

        # deadrise warp toward the bow over beta_len*L
        beta = np.full_like(x, math.radians(p["beta_mid"]))
        warp0 = L - p["beta_len"] * L
        wz = x > warp0
        frac = (x[wz] - warp0) / (p["beta_len"] * L)
        beta[wz] += (math.radians(p["beta_bow"]) - math.radians(p["beta_mid"])) * frac**2
        self.z_chine = zk + self.y_chine * np.tan(beta)

        # sheer: freeboard at mid, rising toward bow; half-breadth from flare
        fb = D - T
        zs = np.full_like(x, fb)
        zs[fwd] *= 1.0 + p["sheer_rise"] * ((x[fwd] - xm) / (L - xm)) ** 2 * (D / fb)
        self.z_sheer = zs
        ys = self.y_chine + (zs - self.z_chine) * math.tan(math.radians(p["flare"]))
        # taper the topside to a stem: sheer half-breadth follows w^0.15 envelope
        self.y_sheer = np.maximum(ys, 0.0) * np.maximum(w, 0.0) ** 0.15

    # ---- section machinery -------------------------------------------------

    def section(self, i: int) -> np.ndarray:
        """Section polyline, keel -> chine -> sheer, as (3,2) array of (y, z)."""
        return np.array(
            [
                [0.0, self.z_keel[i]],
                [self.y_chine[i], self.z_chine[i]],
                [self.y_sheer[i], self.z_sheer[i]],
            ]
        )

    def immersed_section(self, i: int, wl: float = 0.0):
        """Clip section at waterline wl. Returns (area_half, b_wl, zc_half).

        area_half: immersed area of the half-section [m^2]
        b_wl:      waterline half-breadth [m]
        zc_half:   z-centroid of immersed half-section [m]
        """
        pts = self.section(i)
        if pts[0, 1] >= wl:  # keel above water: dry station
            return 0.0, 0.0, 0.0
        poly = [(0.0, pts[0, 1])]
        prev = pts[0]
        for kk in range(1, 3):
            cur = pts[kk]
            if prev[1] < wl <= cur[1]:  # segment crosses WL going up
                f = (wl - prev[1]) / (cur[1] - prev[1])
                yw = prev[0] + f * (cur[0] - prev[0])
                poly.append((yw, wl))
                break
            if cur[1] < wl:
                poly.append((cur[0], cur[1]))
            prev = cur
        else:
            # section fully submerged up to the sheer (deck edge under water):
            # close the polygon at sheer level and report sheer as waterline
            poly.append((pts[2, 0], pts[2, 1]))
            poly.append((0.0, pts[2, 1]))
            area, _yc, zc = _polygon(poly + [poly[0]])
            return area, float(pts[2, 0]), zc

        b_wl = poly[-1][0]
        poly.append((0.0, wl))
        area, _yc, zc = _polygon(poly + [poly[0]])
        return area, b_wl, zc

    # ---- integral properties ------------------------------------------------

    def hydro_arrays(self, wl: float = 0.0):
        a = np.empty(self.n_stations)
        b = np.empty(self.n_stations)
        zc = np.empty(self.n_stations)
        for i in range(self.n_stations):
            a[i], b[i], zc[i] = self.immersed_section(i, wl)
        return a, b, zc

    def wetted_surface(self, wl: float = 0.0) -> float:
        """Wetted surface [m^2], strip sum of immersed girth x dx (both sides)."""
        girth = np.empty(self.n_stations)
        for i in range(self.n_stations):
            pts = self.section(i)
            g = 0.0
            prev = pts[0]
            for kk in range(1, 3):
                cur = pts[kk]
                if prev[1] >= wl:
                    break
                if cur[1] > wl:
                    f = (wl - prev[1]) / (cur[1] - prev[1])
                    cur = prev + f * (cur - prev)
                    g += float(np.hypot(*(cur - prev)))
                    break
                g += float(np.hypot(*(cur - prev)))
                prev = cur
            girth[i] = g
        return 2.0 * float(np.trapezoid(girth, self.x))

    def deck_area(self) -> float:
        """Plan-view deck area [m^2] inside the sheer line (solar real estate)."""
        return 2.0 * float(np.trapezoid(self.y_sheer, self.x))

    def offsets_grid(self, nz: int = 12, wl: float = 0.0):
        """y(x, z) half-breadth grid below wl for the Michell integral.

        z points cluster quadratically toward the waterline (the Michell
        kernel decays fastest there — see benchmarks/wigley.py convergence).
        """
        z0 = min(float(self.z_keel.min()), -1e-6)
        s = np.linspace(1.0, 0.0, nz, endpoint=False)
        zs = np.sort(wl + (z0 - wl) * s**2)
        Y = np.zeros((self.n_stations, nz))
        for i in range(self.n_stations):
            pts = self.section(i)
            for j, z in enumerate(zs):
                Y[i, j] = _halfbreadth_at(pts, z)
        return self.x, zs, Y

    def panel_mesh(self, nx: int = 30, nz: int = 8, wl: float = 0.0):
        """Quad panel mesh of the immersed hull (both sides), for Capytaine.

        Returns (vertices (N,3), faces (M,4) int indices).
        """
        xs = np.linspace(self.x[0], self.x[-1], nx)
        verts = []
        for xv in xs:
            pts = self._section_at(xv)
            zk = pts[0, 1]
            zt = np.linspace(min(zk, wl - 1e-9), wl, nz + 1)
            for z in zt:
                verts.append((xv, _halfbreadth_at(pts, z), z))
        verts = np.array(verts)
        faces = []
        for i in range(nx - 1):
            for j in range(nz):
                a = i * (nz + 1) + j
                faces.append((a, a + 1, a + nz + 2, a + nz + 1))
        # mirror to port
        nv = len(verts)
        port = verts * np.array([1.0, -1.0, 1.0])
        verts = np.vstack([verts, port])
        faces_p = [(d + nv, c + nv, b + nv, a + nv) for a, b, c, d in faces]
        return verts, np.array(faces + faces_p, dtype=int)

    def closed_mesh(self, nx: int = 80, nz: int = 16):
        """Watertight triangle mesh of the FULL hull (keel to sheer, both
        sides, deck lid, transom cap) — for CFD, where an open shell lets the
        mesher flood the interior (found by surfaceFeatureExtract: 198 open
        edges on the wetted-only STL).

        Returns (verts (N,3), tris (M,3) int). Degenerate slivers at the stem
        are skipped by area.
        """
        xs = np.linspace(float(self.x[0]), float(self.x[-1]), nx)
        S = np.zeros((nx, nz + 1, 3))
        for i, xv in enumerate(xs):
            pts = self._section_at(xv)
            zs = np.linspace(pts[0, 1], pts[2, 1], nz + 1)
            for j, z in enumerate(zs):
                S[i, j] = (xv, _halfbreadth_at(pts, float(z)), z)
        P = S * np.array([1.0, -1.0, 1.0])

        verts: list = []
        tris: list = []

        def vid(p) -> int:
            verts.append(p)
            return len(verts) - 1

        def quad(a, b, c, d) -> None:
            # split into two triangles; drop degenerate slivers
            for tri in ((a, b, c), (a, c, d)):
                p = np.array(tri)
                area = 0.5 * np.linalg.norm(np.cross(p[1] - p[0], p[2] - p[0]))
                if area > 1e-10:
                    tris.append((vid(p[0]), vid(p[1]), vid(p[2])))

        for i in range(nx - 1):
            for j in range(nz):
                # starboard shell (outward +y), port mirrored winding
                quad(S[i, j], S[i, j + 1], S[i + 1, j + 1], S[i + 1, j])
                quad(P[i + 1, j], P[i + 1, j + 1], P[i, j + 1], P[i, j])
            # deck lid strip (outward +z)
            quad(S[i, nz], S[i + 1, nz], P[i + 1, nz], P[i, nz])
        # transom cap at x = xs[0] (outward -x)
        for j in range(nz):
            quad(S[0, j], P[0, j], P[0, j + 1], S[0, j + 1])
        # stem cap (degenerate for sharp bows; quads self-filter by area)
        for j in range(nz):
            quad(S[-1, j], S[-1, j + 1], P[-1, j + 1], P[-1, j])

        return np.array(verts), np.array(tris, dtype=int)

    def _section_at(self, xv: float) -> np.ndarray:
        i = np.searchsorted(self.x, xv)
        i = min(max(i, 1), self.n_stations - 1)
        f = (xv - self.x[i - 1]) / (self.x[i] - self.x[i - 1])
        return self.section(i - 1) * (1 - f) + self.section(i) * f

    def min_bend_radius(self) -> float:
        """Smallest 3-D bend radius [m] along the keel and chine curves.

        Developable panels bend about their rulings; the tightest curvature a
        sheet must take follows these edge curves. Checked against the marine-
        plywood cold-bend limit (~80 x thickness) in the ladder.
        """
        r_min = np.inf
        for ys, zs in ((np.zeros_like(self.x), self.z_keel),
                       (self.y_chine, self.z_chine)):
            d1 = np.stack([np.gradient(self.x, self.x),
                           np.gradient(ys, self.x),
                           np.gradient(zs, self.x)], axis=1)
            d2 = np.stack([np.gradient(d1[:, 0], self.x),
                           np.gradient(d1[:, 1], self.x),
                           np.gradient(d1[:, 2], self.x)], axis=1)
            cross = np.cross(d1, d2)
            speed = np.linalg.norm(d1, axis=1)
            kappa = np.linalg.norm(cross, axis=1) / np.maximum(speed**3, 1e-12)
            # ignore the stem tip where the chine collapses to a point
            mask = self.y_chine > 0.05 * max(float(self.y_chine.max()), 1e-9)
            k = kappa[mask] if mask.any() else kappa
            if k.size and k.max() > 1e-9:
                r_min = min(r_min, 1.0 / float(k.max()))
        return float(r_min)

    def panel_twist_rate(self) -> float:
        """Max bottom-panel twist [deg/m] — developability honesty metric.

        Only evaluated where the bottom panel has meaningful width (>10% of
        max chine half-breadth); at the stem the panel width -> 0 and the
        deadrise angle is undefined, not twisted.
        """
        mask = self.y_chine > 0.10 * self.y_chine.max()
        ang = np.degrees(np.arctan2(self.z_chine - self.z_keel,
                                    np.maximum(self.y_chine, 1e-9)))
        rate = np.abs(np.diff(ang)) / np.maximum(np.diff(self.x), 1e-9)
        seg = mask[:-1] & mask[1:]
        return float(rate[seg].max()) if seg.any() else 0.0


def _polygon(pts) -> tuple[float, float, float]:
    """Area (abs), y-centroid, z-centroid of a closed polygon (shoelace)."""
    a = 0.0
    cy = 0.0
    cz = 0.0
    for (y1, z1), (y2, z2) in zip(pts[:-1], pts[1:]):
        cross = y1 * z2 - y2 * z1
        a += cross
        cy += (y1 + y2) * cross
        cz += (z1 + z2) * cross
    a *= 0.5
    if abs(a) < 1e-12:
        return 0.0, 0.0, 0.0
    return abs(a), cy / (6.0 * a), cz / (6.0 * a)


def _halfbreadth_at(pts: np.ndarray, z: float) -> float:
    """Half-breadth of a keel->chine->sheer polyline at height z."""
    if z <= pts[0, 1]:
        return 0.0
    prev = pts[0]
    for kk in range(1, 3):
        cur = pts[kk]
        if prev[1] <= z <= cur[1] and cur[1] > prev[1]:
            f = (z - prev[1]) / (cur[1] - prev[1])
            return float(prev[0] + f * (cur[0] - prev[0]))
        prev = cur
    return float(pts[2, 0])
