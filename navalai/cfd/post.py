"""OpenFOAM forces post-processing + grid-convergence (GCI) — testable
WITHOUT OpenFOAM (synthetic force files in tests; real files on the metal).

Research grounding: 'the uncertainty number you report depends materially on
which V&V method you implement' (Islam & Guedes Soares 2019) — so the method
is named in the output: Roache GCI, factor-of-safety 1.25, Richardson p.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

_NUM = re.compile(r"[-+0-9.eE]+")


def parse_forces(path: str | Path):
    """Parse an OpenFOAM force.dat: rows 'time (fx fy fz) (fx fy fz) ...'.

    Returns (t, fx_total) with pressure+viscous x-components summed.
    """
    t, fx = [], []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        nums = [float(x) for x in _NUM.findall(line)]
        if len(nums) < 7:
            continue
        t.append(nums[0])
        fx.append(nums[1] + nums[4])       # pressure-x + viscous-x
    return np.array(t), np.array(fx)


def forces_path(case: str | Path) -> Path:
    """Force history for a case, merging RESTART segments into one file.

    A run interrupted by thermal sleep and resumed writes a fresh
    postProcessing/forces/<restart-time>/force.dat; reading only the `0/`
    directory would silently analyse the pre-crash fragment and report it as
    the whole run. Segments are concatenated in time order and later samples
    win where they overlap (the resumed run recomputed them).
    """
    root = Path(case) / "postProcessing" / "forces"
    segs = sorted((d for d in root.glob("*/force.dat")),
                  key=lambda p: float(p.parent.name))
    if not segs:
        raise FileNotFoundError(f"no force.dat under {root}")
    if len(segs) == 1:
        return segs[0]

    rows: dict[float, str] = {}
    for seg in segs:
        for line in seg.read_text().splitlines():
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            try:
                rows[float(_NUM.findall(s)[0])] = s
            except (IndexError, ValueError):
                continue
    merged = root / "force.merged.dat"
    merged.write_text("\n".join(rows[t] for t in sorted(rows)) + "\n")
    return merged


def mean_resistance(path: str | Path, tail_frac: float = 0.3) -> tuple[float, float]:
    """(mean, std) of drag over the final tail_frac of the run (settled)."""
    t, fx = parse_forces(path)
    if len(t) < 10:
        raise ValueError("force history too short")
    cut = t[0] + (1.0 - tail_frac) * (t[-1] - t[0])
    seg = fx[t >= cut]
    return float(np.mean(seg)), float(np.std(seg))


def stl_wetted_area(path: str | Path, waterline: float = 0.0) -> float:
    """Submerged area [m^2] of an ascii STL, triangles clipped at z=waterline.

    Gate 2M compares C_t against the Tokyo-2015 scatter, and C_t needs the
    wetted surface the CFD actually saw — taking it from the STL (the same
    geometry snappy meshed) keeps it honest for external benchmark hulls,
    where no analytic hull object exists to ask.
    """
    verts: list = []
    tris: list = []
    for line in Path(path).read_text().splitlines():
        s = line.strip()
        if s.startswith("vertex"):
            verts.append([float(v) for v in s.split()[1:4]])
            if len(verts) == 3:
                tris.append(np.array(verts))
                verts = []

    total = 0.0
    for tri in tris:
        # Sutherland-Hodgman clip of the triangle against the half-space z<=wl
        poly: list = []
        for i in range(3):
            a, b = tri[i], tri[(i + 1) % 3]
            a_in, b_in = a[2] <= waterline, b[2] <= waterline
            if a_in:
                poly.append(a)
            if a_in != b_in:
                t = (waterline - a[2]) / (b[2] - a[2])
                poly.append(a + t * (b - a))
        if len(poly) < 3:
            continue
        p = np.array(poly)
        # fan triangulation of the (planar, convex) clipped polygon
        for i in range(1, len(p) - 1):
            total += 0.5 * float(np.linalg.norm(
                np.cross(p[i] - p[0], p[i + 1] - p[0])))
    return total


def resistance_coefficient(drag: float, wetted_area: float, speed: float,
                           rho: float = 998.8) -> float:
    """C_t = R_t / (0.5 rho S U^2) — the form Tokyo-2015 reports."""
    if wetted_area <= 0 or speed <= 0:
        raise ValueError("wetted_area and speed must be positive")
    return abs(drag) / (0.5 * rho * wetted_area * speed ** 2)


@dataclass(frozen=True)
class GCIReport:
    f_fine: float
    f_extrapolated: float     # Richardson estimate at h -> 0
    p_observed: float         # observed convergence order
    gci_fine_pct: float       # Roache GCI (Fs=1.25), percent of fine value
    method: str


def gci(f_coarse: float, f_medium: float, f_fine: float,
        refinement: float = 2.0 ** 0.5) -> GCIReport:
    """Roache GCI from three systematically refined grids (r = h_c/h_f)."""
    e21 = f_medium - f_fine
    e32 = f_coarse - f_medium
    if abs(e21) < 1e-12 or e32 * e21 <= 0:
        # oscillatory or converged-to-machine: report conservative bound
        spread = max(abs(e21), abs(e32))
        return GCIReport(f_fine, f_fine, float("nan"),
                         100.0 * 1.25 * spread / max(abs(f_fine), 1e-12),
                         "oscillatory: spread bound, Fs=1.25")
    p = math.log(abs(e32 / e21)) / math.log(refinement)
    p = min(max(p, 0.5), 4.0)              # clamp to sane observed orders
    f_exact = f_fine - e21 / (refinement**p - 1.0)
    gci_pct = 100.0 * 1.25 * abs(e21 / f_fine) / (refinement**p - 1.0)
    return GCIReport(f_fine, f_exact, p, gci_pct,
                     "Roache GCI, Fs=1.25, Richardson p (clamped 0.5..4)")
