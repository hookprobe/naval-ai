"""venv side: serialise a hull CAGE to JSON for the Blender process.

THE GRID IS NOT RESTATED HERE. `admissibility.surface_grid` is already a
vectorised replica of the vertex grid `Hull.closed_mesh` triangulates, and it
is already fenced against `closed_mesh`'s own private helpers by
`tests/test_admissibility.py::test_surface_grid_is_the_closed_mesh_grid`. A
third transcription of the sampling rule inside this file would be defect
class 2 (a number — here a whole surface — declared twice) with three copies
free to drift, so this module imports it and adds nothing but JSON.

The TOPOLOGY (which quads close the deck, the transom and the stem, and in
which winding) is likewise not restated: it is written once in
`build_hull.py`'s `_build_arrays`, transcribed from `closed_mesh`, and
`tests/test_blender_hull.py` asserts the Blender STL and `closed_mesh` bound
the same signed volume — the one statement two agreeing copies cannot both
satisfy while both being wrong about orientation.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from ..admissibility import surface_grid
from ..geometry import Hull
from ..grammar import named

#: MEASURED 2026-08-12: `Blender 5.2.0 LTS, build date 2026-07-14`.
#:
#: A prior session reported "Blender is not installed", inferred from an empty
#: `which blender`, and started a `pip install bpy`. Blender was installed.
#: THE BRIEF THAT CORRECTED IT ALSO GOT A DETAIL WRONG AND IT IS RECORDED
#: RATHER THAN INHERITED: it stated "there is no PATH symlink; that is all".
#: There IS one — `/opt/homebrew/bin/blender`, a Homebrew cask wrapper
#: symlinked 2026-08-12 15:36, resolving to the same 5.2.0 LTS build. So the
#: PATH lookup works on this node today and the original inference was wrong
#: for a simpler reason than either account supposed.
#:
#: The app-bundle path is still what this package invokes, because it names an
#: exact build rather than whatever a cask wrapper currently points at, and
#: because `have_blender()` must not depend on the caller's PATH.
BLENDER_BIN = "/Applications/Blender.app/Contents/MacOS/Blender"


def cage_spec(hull: Hull, nx: int, nz: int, subsurf: int = 0,
              voxel: float | None = None, ascii_stl: bool = True,
              crease_angle_deg: float | None = None) -> dict:
    """The JSON payload the Blender process consumes.

    `subsurf` levels of Catmull-Clark and `voxel` (metres) of the Remesh
    modifier are BOTH recorded in the spec and echoed in the receipt, because
    "which mesh is this" is the question every superseded number in this
    repository failed to answer.

    Units are METRES throughout and `build_hull.py` sets Blender's unit system
    to METRIC with `scale_length = 1.0` explicitly rather than inheriting the
    startup file's.
    """
    S = surface_grid(hull, nx, nz)
    p = named(hull.params)
    return {
        "schema": 1,
        "lwl_m": float(hull.x[-1]),
        "nx": int(nx),
        "nz": int(nz),
        "chine_row": int(hull.chine_row(nz)),
        "x_mb": float(p["x_mb"]),
        "n_stations": int(hull.n_stations),
        "grid_shape": [int(nx), int(nz) + 1, 3],
        # float64 on the wire; Blender stores mesh coordinates in SINGLE
        # precision, and how much that costs is a measurement, not a guess —
        # see docs/research/BLENDER.md.
        "grid": [float(v) for v in S.reshape(-1)],
        "build": {"subsurf": int(subsurf),
                  "voxel_m": None if voxel is None else float(voxel),
                  "ascii_stl": bool(ascii_stl),
                  "crease_angle_deg": (None if crease_angle_deg is None
                                       else float(crease_angle_deg))},
    }


def write_spec(hull: Hull, path: str | Path, nx: int, nz: int,
               subsurf: int = 0, voxel: float | None = None,
               ascii_stl: bool = True,
               crease_angle_deg: float | None = None) -> Path:
    """Write `cage_spec` to `path`; returns the path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cage_spec(hull, nx, nz, subsurf, voxel,
                                         ascii_stl, crease_angle_deg)))
    return path


def shipped_resolution(hull: Hull, scale: float = 1.0) -> tuple[int, int]:
    """The (nx, nz) `write_resistance_case` actually writes for this hull.

    Delegates to `navalai.cfd.case.stl_resolution` with the same background
    cell derivation the case writer uses, so a comparison is made at the
    SHIPPED triangulation rather than at `hull_to_stl`'s bare default. Those
    are different surfaces and a finding on one is not a finding on the other
    (docs/LESSONS.md defect class 6).

    That default USED to be 80x16 and this docstring named the number. It is
    now bilge-derived (`case.stl_girth_resolution`: 16 for a hard chine, 96 for
    a fillet), so the number is gone from here rather than restated — one home
    for it, and this is not the home.
    """
    from ..cfd.case import (_DOMAIN_LENGTH_L, _HULL_REFINE, _NX_BASE,
                            stl_resolution)
    lwl = float(hull.x[-1])
    bg_dx = _DOMAIN_LENGTH_L * lwl / max(int(round(_NX_BASE * scale)), 20)
    return stl_resolution(lwl, 0.5 * bg_dx / 2 ** _HULL_REFINE[1])


def grid_from_spec(spec: dict) -> np.ndarray:
    """(nx, nz+1, 3) starboard grid back out of a spec dict."""
    return np.asarray(spec["grid"], dtype=float).reshape(spec["grid_shape"])
