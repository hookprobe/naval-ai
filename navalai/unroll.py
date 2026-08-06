"""Developable-panel unrolling -> flat plate outlines -> DXF (original plan
Phase 5: 'structural DXF formats for manufacturing export').

Method: triangle development of the ruled surface between two 3-D edge
curves (keel-chine for the bottom panel, chine-sheer for the topside).
Isometric by construction along edges and one diagonal family; the residual
on the OTHER diagonal family is the honest development-error metric (zero
only for a perfectly developable surface).

DXF: minimal R12 ASCII (POLYLINE/VERTEX/SEQEND) — the most widely readable
dialect for CNC/nesting shops.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .geometry import Hull


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


@dataclass(frozen=True)
class FlatPanel:
    name: str
    edge_a: np.ndarray        # (n, 2) developed first edge
    edge_b: np.ndarray        # (n, 2) developed second edge
    dev_error_rel: float      # max cross-diagonal mismatch / panel width

    @property
    def outline(self) -> np.ndarray:
        return np.vstack([self.edge_a, self.edge_b[::-1]])

    def perimeter(self) -> float:
        o = self.outline
        return float(np.linalg.norm(np.diff(np.vstack([o, o[:1]]), axis=0),
                                    axis=1).sum())


def develop(A: np.ndarray, B: np.ndarray, name: str) -> FlatPanel:
    """Flatten the ruled surface between 3-D polylines A and B (same length)."""
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
    # honest metric: the diagonal family NOT used in construction
    err = 0.0
    width = max(float(np.linalg.norm(B[0] - A[0])), 1e-9)
    for i in range(n - 1):
        d3 = float(np.linalg.norm(B[i + 1] - A[i]))
        d2 = float(np.linalg.norm(b2[i + 1] - a2[i]))
        err = max(err, abs(d3 - d2))
        width = max(width, float(np.linalg.norm(B[i] - A[i])))
    return FlatPanel(name, a2, b2, err / width)


def hull_panels(hull: Hull) -> list[FlatPanel]:
    keel = np.stack([hull.x, np.zeros_like(hull.x), hull.z_keel], axis=1)
    chine = np.stack([hull.x, hull.y_chine, hull.z_chine], axis=1)
    sheer = np.stack([hull.x, hull.y_sheer, hull.z_sheer], axis=1)
    return [develop(keel, chine, "bottom-stbd"),
            develop(chine, sheer, "topside-stbd")]


# ---------------- DXF R12 writer ----------------

def _polyline_dxf(pts: np.ndarray, layer: str) -> list[str]:
    out = ["0", "POLYLINE", "8", layer, "66", "1", "70", "1"]
    for x, y in pts:
        out += ["0", "VERTEX", "8", layer, "10", f"{x:.4f}", "20", f"{y:.4f}",
                "30", "0.0"]
    out += ["0", "SEQEND"]
    return out


def export_dxf(panels: list[FlatPanel], path: str | Path,
               gap: float = 0.3, units_mm: bool = True, ev=None) -> Path:
    """All panels laid out on layers named after them, in MILLIMETRES.

    THE UNITS WERE UNDECLARED AND THE COORDINATES WERE METRES. The file had no
    HEADER section and therefore no $INSUNITS, while a bottom panel wrote as
    `10.0476 x 1.6160`. Overwhelming DXF/CNC convention is millimetres, so a
    shop importing this cut a **10 mm** part instead of a 10 m one — a scrapped
    sheet, or worse a part that looks plausible until it is offered up to the
    hull. $INSUNITS 4 is millimetres (6 would be metres); the values are scaled
    to match what the header declares, so the two can never disagree.

    NOTE this is still a LAYOUT, not a nest: panels are offset in y only, with
    no rotation and no sheet boundaries. The two hull panels measure
    10.05 x 1.62 m and 10.54 x 1.44 m against a 1.22 x 2.44 m sheet, so
    NEITHER FITS and nothing splits them at a scarph. `engineer.assess()`
    reporting "35 ply sheets" is an estimate from area x WASTE_FACTOR, not
    from this layout. Real nesting is gap G2 and is still open.
    """
    from .export import refuse_unvalidated
    refuse_unvalidated(ev, 'DXF')
    scale = 1000.0 if units_mm else 1.0
    lines = ["0", "SECTION", "2", "HEADER",
             "9", "$INSUNITS", "70", "4" if units_mm else "6",
             "9", "$MEASUREMENT", "70", "1",
             "0", "ENDSEC",
             "0", "SECTION", "2", "ENTITIES"]
    y_off = 0.0
    for p in panels:
        o = p.outline.copy()
        o[:, 1] += y_off - o[:, 1].min()
        lines += _polyline_dxf(o * scale, p.name)
        y_off = o[:, 1].max() + gap
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
