"""Blender-native hull generation, SPLIT ACROSS A PROCESS BOUNDARY.

WHY THE SPLIT IS NOT OPTIONAL. Blender embeds its own CPython — 5.2.0 LTS on
this node ships 3.13.13 with numpy 2.3.4 — and the project venv is cp312.
`import navalai` inside Blender therefore cannot work, and no amount of
PYTHONPATH fixes it (the ABI differs, and `bpy` is not importable from cp312
without a `pip install bpy` this project has decided not to take). So:

    venv side  (this package, minus `build_hull`)
        `spec.py`     builds the hull cage from `navalai.geometry` and
                      serialises it to JSON
        `metrics.py`  measures a triangulation against the ANALYTIC hull
        `run.py`      invokes the installed Blender binary on a spec

    Blender side
        `build_hull.py`  imports ONLY `bpy`/`bmesh`/stdlib, consumes the JSON,
                         builds the mesh, applies modifiers, exports STL

`build_hull.py` lives in this package so the two halves are read side by side
and version together, but it must never import anything from `navalai` and
nothing here may import it.

THE BINARY IS `/Applications/Blender.app/Contents/MacOS/Blender`. A prior
session reported "Blender is not installed" from an empty `which blender` and
went down a `pip install bpy` path; MEASURED 2026-08-12, `--version` reports
`Blender 5.2.0 LTS, build date 2026-07-14`, and there IS also a PATH entry
(`/opt/homebrew/bin/blender`, a Homebrew cask wrapper symlinked at 15:36 the
same day). See `spec.BLENDER_BIN` for why the app-bundle path is the one used
anyway.

WHAT THIS PACKAGE IS NOT. It is not in the ladder, not in `pipeline.py`, and
no gate consumes an STL it produces. `docs/research/BLENDER.md` records what
was measured on 2026-08-12 and the answer was NEGATIVE on the hull path: see
that file before wiring any of this into the CFD case writer.
"""

from __future__ import annotations

from .spec import BLENDER_BIN, cage_spec, write_spec
from .metrics import (analytic_probe_points, chine_dihedral_analytic,
                      chine_dihedral_measured, deviation_by_xl, surface_report)
from .run import (blender_version, build_via_blender, have_blender,
                  render_via_blender)

__all__ = ["BLENDER_BIN", "cage_spec", "write_spec", "analytic_probe_points",
           "chine_dihedral_analytic", "chine_dihedral_measured",
           "deviation_by_xl", "surface_report", "blender_version",
           "build_via_blender", "have_blender", "render_via_blender"]
