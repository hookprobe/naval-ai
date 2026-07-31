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


def mean_resistance(path: str | Path, tail_frac: float = 0.3) -> tuple[float, float]:
    """(mean, std) of drag over the final tail_frac of the run (settled)."""
    t, fx = parse_forces(path)
    if len(t) < 10:
        raise ValueError("force history too short")
    cut = t[0] + (1.0 - tail_frac) * (t[-1] - t[0])
    seg = fx[t >= cut]
    return float(np.mean(seg)), float(np.std(seg))


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
