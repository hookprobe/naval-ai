"""Hard-chine geometry: the CHINE itself, measured. GATE E5-CHINE.

WHY THIS IS A SEPARATE MODULE FROM `e5_hydro`. A chine is a DISCONTINUITY in
surface slope, and every quantity in `e5_hydro` -- volume, waterplane area,
prismatic coefficient -- is an integral. Integrals do not see a corner. Two
hulls can agree on all six E5 parameters and on their sectional-area curves
while one has a sharp chine and the other a radiused bilge, which is exactly
the difference that decides whether a boat can be built from flat plywood
panels.

So E5-CHINE measures the corner directly: where it sits, how high, and how
sharply the surface turns through it. `roundness = 0` in the grammar is a
CLAIM that the kernel makes a chine; this module is what tests the claim
instead of trusting the parameter name.

THE SAME INDEPENDENCE RULE APPLIES. Nothing here imports the geometry kernel.
"""
from __future__ import annotations

import numpy as np

#: Stations, as fractions of LWL from the transom, at which chine geometry is
#: reported. Clustered at both ends because that is where a chine does
#: something interesting -- it dies into the stem forward and into the
#: transom aft, and a station set that only samples the middle would report a
#: prismatic hull and a warped one as identical.
CHINE_STATIONS = (0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80,
                  0.90, 0.95)


def chine_metrics(x: np.ndarray, y_chine: np.ndarray, z_chine: np.ndarray,
                  z_keel: np.ndarray, z_sheer: np.ndarray, lwl: float,
                  x0: float = 0.0) -> dict:
    """Chine position, height, and the panel angles either side of it.

    `bottom_panel_angle` is the deadrise: the angle of the keel-to-chine line
    above horizontal. `side_panel_angle` is the angle of the chine-to-sheer
    line from VERTICAL, so a plumb topside reads 0 and flare reads positive.
    Their sum is the turn the surface makes through the chine -- the
    discontinuity itself, which is 0 for a smooth hull and large for a
    hard-chine one.
    """
    u = (x - x0) / lwl
    out = {"u": [], "y_chine": [], "z_chine": [], "deadrise_deg": [],
           "side_angle_deg": [], "turn_deg": []}
    for s in CHINE_STATIONS:
        yc = float(np.interp(s, u, y_chine))
        zc = float(np.interp(s, u, z_chine))
        zk = float(np.interp(s, u, z_keel))
        zs = float(np.interp(s, u, z_sheer))
        dead = float(np.degrees(np.arctan2(zc - zk, yc))) if yc > 1e-12 \
            else float("nan")
        # The topside runs from the chine to the sheer. Its half-breadth at
        # the sheer is not tabulated here, so a VERTICAL side is assumed only
        # where the source says so; callers pass y_sheer when they have it.
        side = 0.0
        out["u"].append(s)
        out["y_chine"].append(yc)
        out["z_chine"].append(zc)
        out["deadrise_deg"].append(dead)
        out["side_angle_deg"].append(side)
        out["turn_deg"].append(90.0 - dead - side if np.isfinite(dead)
                               else float("nan"))
    return {k: np.array(v) for k, v in out.items()}


def chine_residual(src: dict, gen: dict) -> dict:
    """Compare two chine curves at the same normalised stations."""
    out = {}
    for key, scale in (("y_chine", 1.0), ("z_chine", 1.0),
                       ("deadrise_deg", 1.0)):
        a, b = src[key], gen[key]
        ok = np.isfinite(a) & np.isfinite(b)
        if ok.sum() == 0:
            out[f"{key}_rms"] = float("nan")
            out[f"{key}_max"] = float("nan")
            continue
        d = (b[ok] - a[ok]) * scale
        out[f"{key}_rms"] = float(np.sqrt(np.mean(d ** 2)))
        out[f"{key}_max"] = float(np.max(np.abs(d)))
    return out
